"""
Canonical, leak-safe pipeline to build and evaluate 1D/5D/10D horizon models.

Methodology (FROZEN, leak-safe):
  - Sort GLOBALLY by Date; last 15% = untouched TEST set.
  - Remaining 85% split chronologically into TRAIN (85%) / VAL (15%).
  - LabelEncoder fit on TRAIN only; transform val/test.
  - Future prices used ONLY to build horizon target labels (shifted backwards).
  - External market data joined by exact Date (merge_asof backward = no future leakage).
  - Validation used ONLY for model/threshold selection. Test evaluated ONCE.

Targets:
  - 3-class: 0=DOWN (<= -1%), 1=FLAT, 2=UP (>= +1%)  [per horizon return]
  - Binary:  0=SELL/DOWN, 1=BUY/UP  (same ±1% threshold, FLAT dropped)

Outputs (per horizon):
  - models/model_1d.pkl / model_5d.pkl / model_10d.pkl
  - models/model_{h}_features.pkl, model_{h}_encoder.pkl, model_{h}_metrics.json
  - models/horizon_config.json (target definitions, thresholds, feature sets)
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

# ==========================================================
# CONFIG
# ==========================================================
TEST_SIZE = 0.15
VAL_FRACTION = 0.15
RANDOM_STATE = 42
UP_TH = 0.01      # +1.0%  -> UP / BUY
DOWN_TH = -0.01   # -1.0%  -> DOWN / SELL

HORIZONS = {
    "1d": {"label": "1D", "days": 1, "target_3class": "Target_1D_3", "target_binary": "Target_1D_bin"},
    "5d": {"label": "5D", "days": 5, "target_3class": "Target_5D_3", "target_binary": "Target_5D_bin"},
    "10d": {"label": "10D", "days": 10, "target_3class": "Target_10D_3", "target_binary": "Target_10D_bin"},
}

# Base feature set (point-in-time: technical + sentiment + fundamentals + NIFTY + FII/DII)
BASE_FEATURES = [
    # Technical
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
    # Sentiment
    "Sentiment_Mean", "Sentiment_Count",
    # Fundamentals
    "PE_Ratio", "PB_Ratio", "Market_Cap", "Dividend_Yield",
    # NIFTY market
    "NIFTY_Daily_Return", "NIFTY_3D_Return", "NIFTY_5D_Return", "NIFTY_10D_Return",
    "NIFTY_EMA20", "NIFTY_EMA50", "NIFTY_RSI", "NIFTY_MACD", "NIFTY_ADX",
    "NIFTY_Trend_Direction", "NIFTY_Rolling_Volatility", "NIFTY_Market_Strength",
    "Stock_vs_Nifty_Return",
    # FII/DII (derivatives-OI proxy)
    "FII_Net", "DII_Net", "FII_DII_Spread", "FII_OI_Index", "DII_OI_Index",
    "FII_Net_3D", "DII_Net_3D", "FII_Net_5D", "DII_Net_5D",
    "FII_Net_10D", "DII_Net_10D", "FII_Net_Momentum_3D", "DII_Net_Momentum_3D",
]

# External market features (from market_features.csv) — point-in-time
EXTERNAL_FEATURE_PREFIXES = {
    "india_vix": ["INDIAVIX_"],
    "sensex": ["SENSEX_"],
    "banknifty": ["BANKNIFTY_"],
    "sector": ["SECTOR_"],
    "macro": ["MACRO_"],
    "breadth": ["Advance", "Decline", "Pct_Above", "Nifty_52Week", "Breadth_Score",
                "Advance_Decline"],
}


def classify_return(ret):
    """Map a horizon return (fraction) to 0=DOWN, 1=FLAT, 2=UP using ±1%."""
    if pd.isna(ret):
        return -1
    if ret >= UP_TH:
        return 2
    elif ret <= DOWN_TH:
        return 0
    else:
        return 1


def add_horizon_targets(df):
    """Build 1D/5D/10D 3-class and binary targets from Close (future only for labels)."""
    df = df.copy()
    df = df.sort_values(["Company", "Date"]).reset_index(drop=True)
    g = df.groupby("Company", group_keys=False)["Close"]
    for hkey, cfg in HORIZONS.items():
        n = cfg["days"]
        future_close = g.shift(-n)
        ret = (future_close / df["Close"]) - 1.0
        # 3-class
        df[cfg["target_3class"]] = ret.apply(classify_return)
        # Binary: drop FLAT (0/1 -> SELL/BUY)
        df[cfg["target_binary"]] = np.where(ret >= UP_TH, 1, np.where(ret <= DOWN_TH, 0, np.nan))
    return df


def load_and_split():
    """Load merged dataset, add horizon targets, return split frames."""
    df = pd.read_csv(os.path.join(ROOT, "merged_data", "merged_dataset.csv"),
                     parse_dates=["Date"])
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).copy()
    df = add_horizon_targets(df)

    # Global date sort (FROZEN)
    df_sorted = df.sort_values("Date").reset_index(drop=True)
    split_idx = int(len(df_sorted) * (1 - TEST_SIZE))
    df_train_all = df_sorted.iloc[:split_idx].copy()
    df_test = df_sorted.iloc[split_idx:].copy()
    val_split_idx = int(len(df_train_all) * (1 - VAL_FRACTION))
    df_train = df_train_all.iloc[:val_split_idx].copy()
    df_val = df_train_all.iloc[val_split_idx:].copy()

    print(f"Train: {len(df_train)} | Val: {len(df_val)} | Test: {len(df_test)}")
    print(f"Train: {df_train['Date'].min().date()} -> {df_train['Date'].max().date()}")
    print(f"Val  : {df_val['Date'].min().date()} -> {df_val['Date'].max().date()}")
    print(f"Test : {df_test['Date'].min().date()} -> {df_test['Date'].max().date()}")
    return df_train, df_val, df_test


def build_feature_matrix(df, feature_cols, fit_encoder=True, le=None):
    """Build X matrix with consistent feature ordering. Encoder fit on train only."""
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
    X = df[cols].copy()
    X = X.fillna(0).replace([np.inf, -np.inf], 0)
    return X, cols, le


def prepare_data_for_target(df_train, df_val, df_test, target_col, feature_cols):
    """Return (X_train, y_train, X_val, y_val, X_test, y_test, used_cols, le)."""
    # Drop rows with no target
    tr = df_train.dropna(subset=[target_col]).copy()
    va = df_val.dropna(subset=[target_col]).copy()
    te = df_test.dropna(subset=[target_col]).copy()

    X_tr, cols, le = build_feature_matrix(tr, feature_cols, fit_encoder=True)
    X_va, _, _ = build_feature_matrix(va, cols, fit_encoder=False, le=le)
    X_te, _, _ = build_feature_matrix(te, cols, fit_encoder=False, le=le)

    y_tr = tr[target_col].astype(int)
    y_va = va[target_col].astype(int)
    y_te = te[target_col].astype(int)
    return X_tr, y_tr, X_va, y_va, X_te, y_te, cols, le


def compute_class_weights(y):
    counts = y.value_counts().sort_index()
    total = len(y)
    return (total / (len(counts) * counts)).to_dict()


def train_xgb(X_tr, y_tr, X_va, y_va):
    n_cls = len(np.unique(y_tr))
    w = compute_class_weights(y_tr)
    sw = y_tr.map(w).values
    obj = "multi:softprob" if n_cls > 2 else "binary:logistic"
    kw = {"num_class": n_cls} if n_cls > 2 else {}
    m = xgb.XGBClassifier(
        objective=obj, n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.85, colsample_bytree=0.85, min_child_weight=3,
        reg_alpha=0.5, reg_lambda=1.0, gamma=0.1,
        random_state=RANDOM_STATE, use_label_encoder=False, verbosity=0, n_jobs=-1,
        early_stopping_rounds=30, **kw,
    )
    m.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], sample_weight=sw, verbose=False)
    return m


def train_lgb(X_tr, y_tr, X_va, y_va):
    n_cls = len(np.unique(y_tr))
    w = compute_class_weights(y_tr)
    sw = y_tr.map(w).values
    obj = "multiclass" if n_cls > 2 else "binary"
    kw = {"num_class": n_cls} if n_cls > 2 else {}
    m = lgb.LGBMClassifier(
        objective=obj, n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.85, colsample_bytree=0.85, min_child_samples=20,
        reg_alpha=0.5, reg_lambda=1.0, num_leaves=48,
        random_state=RANDOM_STATE, verbosity=-1, n_jobs=-1, **kw,
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


def tune_thresholds(y_va, proba_va, y_te, proba_te, grid_size=9):
    """Coordinate search over per-class weights on validation only."""
    n_classes = proba_va.shape[1]
    weights = np.ones(n_classes)
    best_acc = accuracy_score(y_va, np.argmax(proba_va, axis=1))
    for _ in range(2):
        for c in range(n_classes):
            candidates = np.linspace(0.3, 2.2, grid_size)
            best_w = weights[c]
            for w_val in candidates:
                trial = weights.copy()
                trial[c] = w_val
                scaled = proba_va * trial
                pred = np.argmax(scaled, axis=1)
                if len(np.unique(pred)) < 2:
                    continue
                acc = accuracy_score(y_va, pred)
                if acc > best_acc:
                    best_acc = acc
                    best_w = w_val
            weights[c] = best_w
    test_pred = np.argmax(proba_te * weights, axis=1)
    return weights, best_acc, test_pred


def evaluate(y_te, y_pred, y_proba, model_name, n_classes):
    """Comprehensive metrics."""
    m = {"model_name": model_name}
    m["accuracy"] = accuracy_score(y_te, y_pred)
    m["balanced_accuracy"] = balanced_accuracy_score(y_te, y_pred)
    m["mcc"] = matthews_corrcoef(y_te, y_pred)
    m["f1_weighted"] = f1_score(y_te, y_pred, average="weighted", zero_division=0)
    m["precision_weighted"] = precision_score(y_te, y_pred, average="weighted", zero_division=0)
    m["recall_weighted"] = recall_score(y_te, y_pred, average="weighted", zero_division=0)
    cm = confusion_matrix(y_te, y_pred)
    m["confusion_matrix"] = cm.tolist()

    # Per-class recall
    labels = ["DOWN", "FLAT", "UP"] if n_classes > 2 else ["SELL", "BUY"]
    per_class = {}
    for i, name in enumerate(labels):
        rs = cm[i].sum() if i < cm.shape[0] else 0
        per_class[f"{name}_recall"] = round(cm[i, i] / rs, 4) if rs > 0 else 0.0
    m["per_class_recall"] = per_class

    # Direction/BUY-SELL recall
    if n_classes > 2:
        non_flat = y_te != 1
        if non_flat.sum() > 0:
            m["direction_accuracy"] = accuracy_score(y_te[non_flat], y_pred[non_flat])
    else:
        m["direction_accuracy"] = accuracy_score(y_te, y_pred)

    # ROC-AUC
    try:
        if n_classes > 2:
            m["roc_auc_ovr"] = roc_auc_score(y_te, y_proba, multi_class="ovr", average="macro")
        else:
            m["roc_auc"] = roc_auc_score(y_te, y_proba[:, 1])
    except Exception:
        m["roc_auc"] = None

    # Prediction distribution
    uniq, counts = np.unique(y_pred, return_counts=True)
    m["predicted_distribution"] = {int(u): int(c) for u, c in zip(uniq, counts)}
    m["majority_class_accuracy"] = float(max(y_te.value_counts(normalize=True)))
    m["improvement_vs_majority"] = float(m["accuracy"] - m["majority_class_accuracy"])
    m["test_size"] = int(len(y_te))
    return m


def train_and_evaluate_horizon(df_train, df_val, df_test, horizon_key, target_type, feature_cols):
    """Train and evaluate a single horizon+target-type model."""
    cfg = HORIZONS[horizon_key]
    target_col = cfg["target_3class"] if target_type == "3class" else cfg["target_binary"]
    n_classes = 3 if target_type == "3class" else 2

    X_tr, y_tr, X_va, y_va, X_te, y_te, cols, le = prepare_data_for_target(
        df_train, df_val, df_test, target_col, feature_cols)

    print(f"\n=== {cfg['label']} / {target_type} | train={X_tr.shape} val={X_va.shape} test={X_te.shape} | features={len(cols)} ===")
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

    if not candidates:
        return None

    # Select best by validation
    best_name = max(candidates, key=lambda k: candidates[k][1])
    best_model, best_va_acc, _ = candidates[best_name]

    # Threshold tuning (3-class only; binary uses argmax)
    te_proba = best_model.predict_proba(X_te)
    te_pred = best_model.predict(X_te)
    tuned = False
    if n_classes > 2:
        va_proba = best_model.predict_proba(X_va)
        w, tuned_va, tuned_te = tune_thresholds(y_va, va_proba, y_te, te_proba)
        if tuned_va > best_va_acc:
            te_pred = tuned_te
            tuned = True
            print(f"  Threshold tuning: val {best_va_acc:.4f} -> {tuned_va:.4f} (weights {np.round(w,2)})")

    # Evaluate ONCE on test
    metrics = evaluate(y_te, te_pred, te_proba,
                       f"{cfg['label']}_{target_type}_{best_name}", n_classes)
    metrics["val_accuracy"] = float(best_va_acc)
    metrics["tuned_thresholds"] = tuned
    metrics["selected_model"] = best_name
    metrics["horizon"] = cfg["label"]
    metrics["target_type"] = target_type
    metrics["target_col"] = target_col
    metrics["feature_count"] = len(cols)

    print(f"  >>> TEST acc={metrics['accuracy']:.4f} (maj {metrics['majority_class_accuracy']:.4f}) "
          f"bal_acc={metrics['balanced_accuracy']:.4f} mcc={metrics['mcc']:.4f} "
          f"dir_acc={metrics.get('direction_accuracy', 'N/A')}")

    return {"model": best_model, "metrics": metrics, "features": cols,
            "encoder": le, "target_col": target_col}


def save_artifacts(horizon_key, result, target_type):
    """Save model + features + encoder + metrics for a horizon."""
    cfg = HORIZONS[horizon_key]
    if result is None:
        return
    suffix = f"{horizon_key}_{target_type}"
    model_path = os.path.join(ROOT, "models", f"model_{suffix}.pkl")
    feat_path = os.path.join(ROOT, "models", f"model_{suffix}_features.pkl")
    enc_path = os.path.join(ROOT, "models", f"model_{suffix}_encoder.pkl")
    met_path = os.path.join(ROOT, "models", f"model_{suffix}_metrics.json")

    joblib.dump(result["model"], model_path)
    joblib.dump(result["features"], feat_path)
    joblib.dump(result["encoder"], enc_path)
    with open(met_path, "w") as f:
        json.dump(result["metrics"], f, indent=2)

    print(f"  Saved: {model_path}")


def main():
    print("=" * 70)
    print("CANONICAL LEAK-SAFE HORIZON MODEL BUILDER (1D/5D/10D)")
    print("=" * 70)

    # Load + split (frozen)
    df_train, df_val, df_test = load_and_split()

    # Feature selection: use base features present in data
    feature_cols = [c for c in BASE_FEATURES if c in df_train.columns]
    print(f"\nBase features: {len(feature_cols)}")

    # Train each horizon x target-type
    all_results = {}
    for horizon_key in ["1d", "5d", "10d"]:
        for target_type in ["3class", "binary"]:
            key = f"{horizon_key}_{target_type}"
            print("\n" + "=" * 70)
            print(f"TRAINING {key}")
            print("=" * 70)
            result = train_and_evaluate_horizon(
                df_train, df_val, df_test, horizon_key, target_type, feature_cols)
            if result:
                all_results[key] = result["metrics"]
                save_artifacts(horizon_key, result, target_type)

    # Save comparison
    comparison = {k: v for k, v in all_results.items()}
    with open(os.path.join(ROOT, "models", "horizon_comparison.json"), "w") as f:
        json.dump(comparison, f, indent=2)

    # Print final table
    print("\n" + "=" * 90)
    print("FINAL COMPARISON TABLE")
    print("=" * 90)
    hdr = f"{'Horizon':<10}{'Target':<10}{'Model':<12}{'Acc':<8}{'BalAcc':<8}{'MCC':<7}{'F1':<7}{'DirAcc':<9}{'Majority':<10}"
    print(hdr)
    print("-" * len(hdr))
    for key in ["1d_3class", "1d_binary", "5d_3class", "5d_binary", "10d_3class", "10d_binary"]:
        if key in comparison:
            m = comparison[key]
            da = m.get("direction_accuracy")
            print(f"{HORIZONS[key.split('_')[0]]['label']:<10}{key.split('_')[1]:<10}"
                  f"{m['selected_model']:<12}{m['accuracy']*100:<7.2f}%{m['balanced_accuracy']*100:<7.2f}%"
                  f"{m['mcc']:<7.4f}{m['f1_weighted']:<7.4f}"
                  f"{da*100 if da is not None else 0:<8.2f}%{m['majority_class_accuracy']*100:<9.2f}%")

    print(f"\nSaved all artifacts to models/. Summary: models/horizon_comparison.json")


if __name__ == "__main__":
    main()