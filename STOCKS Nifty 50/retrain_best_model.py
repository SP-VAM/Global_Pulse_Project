"""
Retrain the best model (10D binary BUY/SELL) with sector-index features added.
The ablation experiment showed sector indices are the only external data that
genuinely improves directional prediction (5D binary: 54.28% vs base 50.05%).

This script:
  1. Loads merged dataset + market_features.csv
  2. Adds sector-index features (point-in-time, merge_asof backward)
  3. Builds 10D binary target (0=SELL, 1=BUY, ±1% threshold)
  4. Trains RandomForest + ExtraTrees + XGBoost + LightGBM
  5. Selects best by validation, evaluates ONCE on untouched test
  6. Saves as models/model_10d_binary_sector.pkl + artifacts
"""
import os
import sys
import json
import time
import warnings
import numpy as np
import pandas as pd
import joblib
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "improve"))

from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, matthews_corrcoef, f1_score,
    precision_score, recall_score, confusion_matrix, roc_auc_score
)
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
import xgboost as xgb
import lightgbm as lgb

TEST_SIZE = 0.15
VAL_FRACTION = 0.15
RANDOM_STATE = 42
UP_TH = 0.01
DOWN_TH = -0.01

BASE_FEATURES = [
    "SMA20", "SMA50", "EMA20", "EMA50", "RSI", "MACD", "MACD_SIGNAL", "MACD_HIST",
    "BB_UPPER", "BB_MIDDLE", "BB_LOWER", "ATR", "OBV", "STOCH_K", "STOCH_D", "ADX",
    "Daily_Return", "Volatility", "Price_Change", "Price_Change_%",
    "WILLIAMS_R", "MFI", "ROC", "CCI",
    "Close_SMA20_Ratio", "Close_SMA50_Ratio", "Close_BB_Width_Ratio",
    "Volume_SMA20_Ratio", "RSI_Normalized", "ATR_Normalized",
    "Close_lag1", "Close_lag2", "Close_lag3", "RSI_lag1", "MACD_lag1", "MACD_HIST_lag1",
    "Daily_Return_lag1", "ATR_lag1", "ADX_lag1",
    "Close_5d_max", "Close_5d_min", "High_5d_max", "Low_5d_min",
    "Volume_5d_mean", "Close_10d_max", "Close_10d_min",
    "Daily_Return_5d_mean", "Daily_Return_10d_mean",
    "Sentiment_Mean", "Sentiment_Count",
    "PE_Ratio", "PB_Ratio", "Market_Cap", "Dividend_Yield",
    "NIFTY_Daily_Return", "NIFTY_3D_Return", "NIFTY_5D_Return", "NIFTY_10D_Return",
    "NIFTY_EMA20", "NIFTY_EMA50", "NIFTY_RSI", "NIFTY_MACD", "NIFTY_ADX",
    "NIFTY_Trend_Direction", "NIFTY_Rolling_Volatility", "NIFTY_Market_Strength",
    "Stock_vs_Nifty_Return",
    "FII_Net", "DII_Net", "FII_DII_Spread", "FII_OI_Index", "DII_OI_Index",
    "FII_Net_3D", "DII_Net_3D", "FII_Net_5D", "DII_Net_5D",
    "FII_Net_10D", "DII_Net_10D", "FII_Net_Momentum_3D", "DII_Net_Momentum_3D",
]


def load_data():
    df = pd.read_csv(os.path.join(ROOT, "merged_data", "merged_dataset.csv"),
                     parse_dates=["Date"])
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).copy()

    mf = pd.read_csv(os.path.join(ROOT, "market_data", "market_features.csv"),
                     parse_dates=["Date"])
    mf = mf.drop_duplicates(subset=["Date"]).set_index("Date").sort_index()
    return df, mf


def add_horizon_target(df, days):
    df = df.copy()
    df = df.sort_values(["Company", "Date"]).reset_index(drop=True)
    g = df.groupby("Company", group_keys=False)["Close"]
    future_close = g.shift(-days)
    ret = (future_close / df["Close"]) - 1.0
    return np.where(ret >= UP_TH, 1, np.where(ret <= DOWN_TH, 0, np.nan))


def attach_sector_features(df, mf):
    """Merge sector-index features by exact Date (backward)."""
    df = df.copy()
    mf_flat = mf.reset_index()
    mf_flat["Date"] = pd.to_datetime(mf_flat["Date"])
    sector_cols = [c for c in mf_flat.columns if c.startswith("SECTOR_")]
    base_cols = set(df.columns)
    sector_cols = [c for c in sector_cols if c not in base_cols]
    if not sector_cols:
        return df, []
    mf_for_merge = mf_flat[["Date"] + sector_cols].copy()
    df = df.sort_values("Date").reset_index(drop=True)
    merged = pd.merge_asof(df, mf_for_merge, on="Date", direction="backward")
    return merged, sector_cols


def build_features(df, feature_cols, fit_encoder=True, le=None):
    comps = df["Company"].astype(str).values
    if fit_encoder:
        le = LabelEncoder()
        df = df.copy()
        df["Company_Encoded"] = le.fit_transform(comps)
    else:
        df = df.copy()
        known = set(le.classes_)
        df["Company_Encoded"] = [le.transform([c])[0] if c in known else -1 for c in comps]
    cols = [c for c in feature_cols if c in df.columns]
    if "Company_Encoded" not in cols:
        cols = cols + ["Company_Encoded"]
    X = df[cols].fillna(0).replace([np.inf, -np.inf], 0)
    return X, cols, le


def compute_class_weights(y):
    counts = y.value_counts().sort_index()
    total = len(y)
    return (total / (len(counts) * counts)).to_dict()


def train_xgb(X_tr, y_tr, X_va, y_va):
    w = compute_class_weights(y_tr)
    sw = y_tr.map(w).values
    m = xgb.XGBClassifier(
        objective="binary:logistic", n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.85, colsample_bytree=0.85, min_child_weight=3,
        reg_alpha=0.5, reg_lambda=1.0, gamma=0.1,
        random_state=RANDOM_STATE, use_label_encoder=False, verbosity=0, n_jobs=-1,
        early_stopping_rounds=30,
    )
    m.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], sample_weight=sw, verbose=False)
    return m


def train_lgb(X_tr, y_tr, X_va, y_va):
    w = compute_class_weights(y_tr)
    sw = y_tr.map(w).values
    m = lgb.LGBMClassifier(
        objective="binary", n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.85, colsample_bytree=0.85, min_child_samples=20,
        reg_alpha=0.5, reg_lambda=1.0, num_leaves=48,
        random_state=RANDOM_STATE, verbosity=-1, n_jobs=-1,
    )
    m.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], sample_weight=sw,
          callbacks=[lgb.early_stopping(30, verbose=False)])
    return m


def train_et(X_tr, y_tr):
    return ExtraTreesClassifier(
        n_estimators=400, random_state=RANDOM_STATE, n_jobs=-1,
        class_weight="balanced", max_features=0.7, min_samples_leaf=2,
    ).fit(X_tr, y_tr)


def train_rf(X_tr, y_tr):
    return RandomForestClassifier(
        n_estimators=400, random_state=RANDOM_STATE, n_jobs=-1,
        class_weight="balanced", max_features=0.7, min_samples_leaf=2,
    ).fit(X_tr, y_tr)


def main():
    print("=" * 70)
    print("RETRAIN BEST MODEL: 10D BINARY + SECTOR FEATURES")
    print("=" * 70)

    df, mf = load_data()
    df["Target_10D_bin"] = add_horizon_target(df, 10)
    df, sector_cols = attach_sector_features(df, mf)
    print(f"Sector features added: {len(sector_cols)}")

    # Drop NaN targets
    df = df.dropna(subset=["Target_10D_bin"]).copy()
    df_sorted = df.sort_values("Date").reset_index(drop=True)
    split_idx = int(len(df_sorted) * (1 - TEST_SIZE))
    df_train_all = df_sorted.iloc[:split_idx].copy()
    df_test = df_sorted.iloc[split_idx:].copy()
    val_split_idx = int(len(df_train_all) * (1 - VAL_FRACTION))
    df_train = df_train_all.iloc[:val_split_idx].copy()
    df_val = df_train_all.iloc[val_split_idx:].copy()

    print(f"Train: {len(df_train)} | Val: {len(df_val)} | Test: {len(df_test)}")

    feature_cols = [c for c in BASE_FEATURES if c in df_train.columns] + sector_cols
    feature_cols = list(dict.fromkeys(feature_cols))

    X_tr, cols, le = build_features(df_train, feature_cols, fit_encoder=True)
    X_va, _, _ = build_features(df_val, cols, fit_encoder=False, le=le)
    X_te, _, _ = build_features(df_test, cols, fit_encoder=False, le=le)
    y_tr = df_train["Target_10D_bin"].astype(int)
    y_va = df_val["Target_10D_bin"].astype(int)
    y_te = df_test["Target_10D_bin"].astype(int)

    print(f"Features: {len(cols)} | Train: {X_tr.shape} | Test: {X_te.shape}")
    print(f"Target dist (train): {dict(y_tr.value_counts().sort_index())}")

    # Train candidates
    candidates = {}
    for name, fn in [
        ("XGBoost", lambda: train_xgb(X_tr, y_tr, X_va, y_va)),
        ("LightGBM", lambda: train_lgb(X_tr, y_tr, X_va, y_va)),
        ("ExtraTrees", lambda: train_et(X_tr, y_tr)),
        ("RandomForest", lambda: train_rf(X_tr, y_tr)),
    ]:
        t0 = time.time()
        try:
            m = fn()
            va_acc = accuracy_score(y_va, m.predict(X_va))
            candidates[name] = (m, va_acc, time.time() - t0)
            print(f"  {name:12s}: val acc={va_acc:.4f} ({time.time()-t0:.1f}s)")
        except Exception as e:
            print(f"  {name:12s}: FAILED {e}")

    best_name = max(candidates, key=lambda k: candidates[k][1])
    best_model, best_va_acc, _ = candidates[best_name]
    print(f"\nBest model: {best_name} (val {best_va_acc:.4f})")

    # Evaluate ONCE on test
    te_pred = best_model.predict(X_te)
    te_proba = best_model.predict_proba(X_te)
    acc = accuracy_score(y_te, te_pred)
    bal = balanced_accuracy_score(y_te, te_pred)
    mcc = matthews_corrcoef(y_te, te_pred)
    f1w = f1_score(y_te, te_pred, average="weighted", zero_division=0)
    cm = confusion_matrix(y_te, te_pred, labels=[0, 1])
    buy_recall = cm[1, 1] / cm[1].sum() if cm[1].sum() > 0 else 0
    sell_recall = cm[0, 0] / cm[0].sum() if cm[0].sum() > 0 else 0
    maj_acc = max(y_te.value_counts(normalize=True))
    try:
        roc_auc = roc_auc_score(y_te, te_proba[:, 1])
    except Exception:
        roc_auc = None

    print("\n" + "=" * 60)
    print("FINAL TEST EVALUATION (10D binary + sector)")
    print("=" * 60)
    print(f"Accuracy           : {acc:.4f} ({acc*100:.2f}%)  (majority: {maj_acc:.4f})")
    print(f"Balanced accuracy  : {bal:.4f}")
    print(f"MCC                : {mcc:.4f}")
    print(f"Weighted F1        : {f1w:.4f}")
    print(f"BUY recall         : {buy_recall:.4f}")
    print(f"SELL recall        : {sell_recall:.4f}")
    print(f"ROC-AUC            : {roc_auc:.4f}" if roc_auc else "ROC-AUC: N/A")
    print(f"Confusion matrix   : {cm.tolist()}")

    # Save artifacts
    model_path = os.path.join(ROOT, "models", "model_10d_binary_sector.pkl")
    feat_path = os.path.join(ROOT, "models", "model_10d_binary_sector_features.pkl")
    enc_path = os.path.join(ROOT, "models", "model_10d_binary_sector_encoder.pkl")
    met_path = os.path.join(ROOT, "models", "model_10d_binary_sector_metrics.json")

    joblib.dump(best_model, model_path)
    joblib.dump(cols, feat_path)
    joblib.dump(le, enc_path)

    metrics = {
        "model": best_name,
        "horizon": "10D",
        "target": "binary BUY/SELL (±1% threshold)",
        "features": len(cols),
        "sector_features_added": len(sector_cols),
        "accuracy": float(acc),
        "balanced_accuracy": float(bal),
        "mcc": float(mcc),
        "f1_weighted": float(f1w),
        "buy_recall": float(buy_recall),
        "sell_recall": float(sell_recall),
        "roc_auc": float(roc_auc) if roc_auc else None,
        "confusion_matrix": cm.tolist(),
        "majority_class_accuracy": float(maj_acc),
        "improvement_vs_majority": float(acc - maj_acc),
        "test_size": int(len(y_te)),
        "val_accuracy": float(best_va_acc),
    }
    with open(met_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nSaved: {model_path}")
    print(f"Saved: {met_path}")


if __name__ == "__main__":
    main()