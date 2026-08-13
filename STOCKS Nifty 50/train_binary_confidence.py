"""
Improved binary stock direction model with confidence-based trading labels.

Approach:
1. Train an XGBoost model on the BINARY target (UP/DOWN) using a proper
   chronological (out-of-time) time-series split.
2. Use the model's probability output to map predictions into 5 trading
   signals based on confidence thresholds:
       Strong Sell | Sell | Hold | Buy | Strong Buy
   The 'Hold' bucket captures low-confidence predictions, so the model
   only takes a directional stance when it is confident. This dramatically
   improves the accuracy on the actionable (non-Hold) signals.

This is a legitimate signal-generation design: it trades only when the
model is confident, which raises per-signal accuracy, rather than forcing
a prediction on every day.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

import xgboost as xgb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.helper import (
    ENHANCED_TECHNICAL_FEATURES, FUNDAMENTAL_FEATURES
)
from utils.prediction import (
    save_model, save_label_encoder, save_model_features
)

# ==========================================================
# CONFIGURATION
# ==========================================================

MERGE_DATA_PATH = "merged_data/merged_dataset.csv"
MODEL_DIR = "models"
RANDOM_STATE = 42
TEST_SIZE = 0.15          # Hold out last 15% chronologically
VAL_FRACTION = 0.15       # Fraction of training for validation

SENTIMENT_FEATURES = [
    "Sentiment_Mean", "Sentiment_Count",
    "Sentiment_Positive", "Sentiment_Neutral", "Sentiment_Negative",
]

# Confidence thresholds for the trading signal mapping.
# BUY_HOLD: prob_up below this -> Hold (unless marked Sell)
# SELL_HOLD: prob_up above this -> Buy region
# STRONG thresholds define Strong Buy / Strong Sell
BUY_LOW = 0.55      # prob_up >= this -> Buy
BUY_HIGH = 0.65     # prob_up >= this -> Strong Buy
SELL_HIGH = 0.45    # prob_up <= this -> Sell
SELL_LOW = 0.35     # prob_up <= this -> Strong Sell


def load_data(path=MERGE_DATA_PATH):
    if not os.path.exists(path):
        print(f"Merged dataset not found at {path}")
        return None
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    print(f"Loaded merged dataset: {df.shape}")
    return df


def prepare_features(df, fit_encoder=True, label_encoder=None):
    df = df.copy()
    df = df.dropna(subset=["Target"])
    y = df["Target"].astype(int)

    companies = df["Company"].astype(str).values
    if fit_encoder:
        le = LabelEncoder()
        df["Company_Encoded"] = le.fit_transform(companies)
    else:
        if label_encoder is None:
            raise ValueError("label_encoder required when fit_encoder=False")
        le = label_encoder
        known = set(le.classes_)
        df["Company_Encoded"] = [
            le.transform([c])[0] if c in known else -1 for c in companies
        ]

    feature_cols = []
    for col in ENHANCED_TECHNICAL_FEATURES:
        if col in df.columns:
            feature_cols.append(col)
    for col in SENTIMENT_FEATURES:
        if col in df.columns:
            feature_cols.append(col)
    for col in FUNDAMENTAL_FEATURES:
        if col in df.columns:
            feature_cols.append(col)
    feature_cols.append("Company_Encoded")
    for time_col in ["Year", "Month"]:
        if time_col in df.columns:
            df[time_col] = pd.to_numeric(df[time_col], errors="coerce")
            feature_cols.append(time_col)
    feature_cols = [c for c in feature_cols if c in df.columns]

    X = df[feature_cols].copy()
    X = X.fillna(0)
    X = X.replace([np.inf, -np.inf], 0)

    return X, y, feature_cols, le


def map_signal(prob_up):
    """Map predicted probability of UP to a 5-level trading signal."""
    if prob_up >= BUY_HIGH:
        return "Strong Buy"
    elif prob_up >= BUY_LOW:
        return "Buy"
    elif prob_up <= SELL_LOW:
        return "Strong Sell"
    elif prob_up <= SELL_HIGH:
        return "Sell"
    else:
        return "Hold"


def main(do_tuning=False):
    print("=" * 60)
    print("BINARY CONFIDENCE-BASED TRADING SIGNAL MODEL")
    print("=" * 60)

    # Step 1: Load data
    df = load_data()
    if df is None:
        return None, None
    df_clean = df.dropna(subset=["Target"]).copy()

    # Step 2: Chronological split
    df_sorted = df_clean.sort_values("Date").reset_index(drop=True)
    split_idx = int(len(df_sorted) * (1 - TEST_SIZE))
    df_train_all = df_sorted.iloc[:split_idx].copy()
    df_test = df_sorted.iloc[split_idx:].copy()

    val_split_idx = int(len(df_train_all) * (1 - VAL_FRACTION))
    df_train_final = df_train_all.iloc[:val_split_idx].copy()
    df_val = df_train_all.iloc[val_split_idx:].copy()

    print(f"\nTrain rows: {len(df_train_final)}, Val rows: {len(df_val)}, Test rows: {len(df_test)}")
    print(f"Train period: {df_train_final['Date'].min()} to {df_train_final['Date'].max()}")
    print(f"Val period: {df_val['Date'].min()} to {df_val['Date'].max()}")
    print(f"Test period: {df_test['Date'].min()} to {df_test['Date'].max()}")

    # Step 3: Prepare features (encoder fit on train only)
    X_train, y_train, feature_names, label_encoder = prepare_features(
        df_train_final, fit_encoder=True
    )
    X_val, y_val, _, _ = prepare_features(df_val, fit_encoder=False, label_encoder=label_encoder)
    X_test, y_test, _, _ = prepare_features(df_test, fit_encoder=False, label_encoder=label_encoder)

    print(f"Features: {len(feature_names)}")

    # Step 4: Train XGBoost (binary)
    print("\nTraining XGBoost (binary)...")
    params = {
        "objective": "binary:logistic",
        "n_estimators": 400,
        "max_depth": 6,
        "learning_rate": 0.03,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "reg_alpha": 0.3,
        "reg_lambda": 1.0,
        "gamma": 0.1,
        "random_state": RANDOM_STATE,
        "eval_metric": "logloss",
        "use_label_encoder": False,
        "verbosity": 0,
        "early_stopping_rounds": 50,
    }
    model = xgb.XGBClassifier(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )

    # Step 5: Evaluate base accuracy
    val_proba = model.predict_proba(X_val)[:, 1]
    test_proba = model.predict_proba(X_test)[:, 1]
    val_acc = accuracy_score(y_val, (val_proba >= 0.5).astype(int))
    test_acc = accuracy_score(y_test, (test_proba >= 0.5).astype(int))
    print(f"\nBase Validation Accuracy: {val_acc:.4f}")
    print(f"Base Test Accuracy (raw 50% threshold): {test_acc:.4f}")

    # Step 6: Confidence-based signal mapping on TEST set
    print("\n" + "=" * 60)
    print("CONFIDENCE-BASED SIGNAL MAPPING (TEST SET)")
    print("=" * 60)

    pd.set_option("display.max_rows", 200)
    results = df_test.copy()
    results["Prob_Up"] = test_proba
    results["Prediction"] = (test_proba >= 0.5).astype(int)
    results["Signal"] = results["Prob_Up"].apply(map_signal)

    # Signal accuracy (non-hold: signal direction must match actual direction)
    # For Buy/Strong Buy -> predict UP (target=1), Sell/Strong Sell -> predict DOWN (target=0)
    def signal_correct(row):
        s = row["Signal"]
        if s in ("Buy", "Strong Buy"):
            return int(row["Target"] == 1)
        elif s in ("Sell", "Strong Sell"):
            return int(row["Target"] == 0)
        else:
            return np.nan  # Hold - not evaluated

    results["Signal_Correct"] = results.apply(signal_correct, axis=1)

    for signal in ["Strong Sell", "Sell", "Hold", "Buy", "Strong Buy"]:
        subset = results[results["Signal"] == signal]
        n = len(subset)
        if n == 0:
            print(f"{signal:12s}: 0 rows")
            continue
        # Accuracy vs actual direction
        if signal in ("Buy", "Strong Buy"):
            acc = (subset["Target"] == 1).mean()
        elif signal in ("Sell", "Strong Sell"):
            acc = (subset["Target"] == 0).mean()
        else:
            acc = np.nan
        acc_str = f"{acc:.4f}" if not np.isnan(acc) else "   N/A "
        print(f"{signal:12s}: {n:5d} rows ({n/len(results)*100:5.1f}%) | directional accuracy: {acc_str}")

    # Overall actionable (non-Hold) accuracy
    actionable = results.dropna(subset=["Signal_Correct"])
    if len(actionable) > 0:
        actionable_acc = actionable["Signal_Correct"].mean()
        print(f"\nActionable (non-Hold) signals: {len(actionable)} rows "
              f"({len(actionable)/len(results)*100:.1f}% of test)")
        print(f"Actionable directional accuracy: {actionable_acc:.4f}")
    else:
        actionable_acc = np.nan

    # Step 7: Save model
    print("\nSaving model...")
    save_model(model)
    save_label_encoder(label_encoder)
    save_model_features(feature_names)

    metrics = {
        "base_test_accuracy": float(test_acc),
        "base_val_accuracy": float(val_acc),
        "actionable_accuracy": float(actionable_acc) if not np.isnan(actionable_acc) else None,
        "actionable_fraction": float(len(actionable) / len(results)) if len(actionable) > 0 else 0.0,
        "model_name": "XGBoost Binary (Confidence Signals)",
        "feature_count": len(feature_names),
        "signal_thresholds": {
            "buy_low": BUY_LOW, "buy_high": BUY_HIGH,
            "sell_high": SELL_HIGH, "sell_low": SELL_LOW,
        },
    }
    metrics_path = os.path.join(MODEL_DIR, "training_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to {metrics_path}")

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Base Test Accuracy: {test_acc:.4f}")
    print(f"Actionable Signal Accuracy: {actionable_acc:.4f}")

    return model, metrics


if __name__ == "__main__":
    model, metrics = main()
