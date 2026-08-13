"""
Ablation experiment: which external data actually helps directional prediction?
Tests each external dataset family (India VIX, Sensex, BankNifty, sector indices,
macro, market breadth, FII/DII) added to the base feature set, on the 5D binary
(BUY/SELL) target — the most promising horizon+formulation.

Methodology (FROZEN, leak-safe):
  - Same strict chronological split as build_horizon_models.py
  - External data joined by exact Date (merge_asof backward)
  - Validation for model selection only; test evaluated ONCE per experiment
  - Reports improvement vs base + majority baseline
"""
import os
import sys
import json
import time
import warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "improve"))

from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, balanced_accuracy_score, matthews_corrcoef, f1_score
from sklearn.ensemble import ExtraTreesClassifier
import xgboost as xgb

MARKET_FEATURES_PATH = os.path.join(ROOT, "market_data", "market_features.csv")
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

# External feature families
EXTERNAL_FAMILIES = {
    "india_vix": lambda cols: [c for c in cols if c.startswith("INDIAVIX_")],
    "sensex": lambda cols: [c for c in cols if c.startswith("SENSEX_")],
    "banknifty": lambda cols: [c for c in cols if c.startswith("BANKNIFTY_")],
    "sector": lambda cols: [c for c in cols if c.startswith("SECTOR_")],
    "macro": lambda cols: [c for c in cols if c.startswith("MACRO_")],
    "breadth": lambda cols: [c for c in cols if any(k in c for k in
        ["Advance", "Decline", "Pct_Above", "52Week", "Breadth", "A/D"])],
}


def load_data():
    """Load merged dataset + external market features."""
    df = pd.read_csv(os.path.join(ROOT, "merged_data", "merged_dataset.csv"),
                     parse_dates=["Date"])
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).copy()

    # Load external market features (point-in-time)
    mf = pd.read_csv(MARKET_FEATURES_PATH, parse_dates=["Date"])
    mf = mf.drop_duplicates(subset=["Date"]).set_index("Date").sort_index()
    return df, mf


def add_horizon_targets(df):
    """5D binary target: 0=SELL/DOWN, 1=BUY/UP (FLAT dropped)."""
    df = df.copy()
    df = df.sort_values(["Company", "Date"]).reset_index(drop=True)
    g = df.groupby("Company", group_keys=False)["Close"]
    future_close = g.shift(-5)
    ret = (future_close / df["Close"]) - 1.0
    df["Target_5D_bin"] = np.where(ret >= UP_TH, 1, np.where(ret <= DOWN_TH, 0, np.nan))
    return df


def attach_market_features(df, mf, family_name):
    """Merge only the external family columns by exact Date (backward)."""
    df = df.copy()
    mf_flat = mf.reset_index()
    mf_flat["Date"] = pd.to_datetime(mf_flat["Date"])
    all_market_cols = mf_flat.columns.tolist()
    base_cols = set(df.columns)

    if family_name == "base":
        return df, []

    family_fn = EXTERNAL_FAMILIES[family_name]
    family_cols = family_fn(all_market_cols)
    # Drop cols already in df
    family_cols = [c for c in family_cols if c not in base_cols]
    if not family_cols:
        return df, []

    mf_for_merge = mf_flat[["Date"] + family_cols].copy()
    df = df.sort_values("Date").reset_index(drop=True)
    merged = pd.merge_asof(df, mf_for_merge, on="Date", direction="backward")
    return merged, family_cols


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


def run_experiment(df, mf, family_name):
    """Train ExtraTrees on 5D binary target with a feature family."""
    print(f"\n{'='*60}")
    print(f"ABLATION: {family_name}")
    print(f"{'='*60}")

    merged, new_cols = attach_market_features(df, mf, family_name)
    if family_name != "base" and not new_cols:
        print("  No new external cols found for this family.")
        return None

    # Drop NaN targets
    merged = merged.dropna(subset=["Target_5D_bin"]).copy()
    df_sorted = merged.sort_values("Date").reset_index(drop=True)
    split_idx = int(len(df_sorted) * (1 - TEST_SIZE))
    df_train_all = df_sorted.iloc[:split_idx].copy()
    df_test = df_sorted.iloc[split_idx:].copy()
    val_split_idx = int(len(df_train_all) * (1 - VAL_FRACTION))
    df_train = df_train_all.iloc[:val_split_idx].copy()
    df_val = df_train_all.iloc[val_split_idx:].copy()

    feature_cols = [c for c in BASE_FEATURES if c in df_train.columns] + new_cols
    feature_cols = list(dict.fromkeys(feature_cols))

    X_tr, cols, le = build_features(df_train, feature_cols, fit_encoder=True)
    X_va, _, _ = build_features(df_val, cols, fit_encoder=False, le=le)
    X_te, _, _ = build_features(df_test, cols, fit_encoder=False, le=le)
    y_tr = df_train["Target_5D_bin"].astype(int)
    y_va = df_val["Target_5D_bin"].astype(int)
    y_te = df_test["Target_5D_bin"].astype(int)

    # Train ExtraTrees (fast, robust)
    model = ExtraTreesClassifier(
        n_estimators=300, random_state=RANDOM_STATE, n_jobs=-1,
        class_weight="balanced", max_features=0.7, min_samples_leaf=2,
    )
    model.fit(X_tr, y_tr)

    va_pred = model.predict(X_va)
    va_acc = accuracy_score(y_va, va_pred)
    te_pred = model.predict(X_te)
    te_acc = accuracy_score(y_te, te_pred)
    te_bal = balanced_accuracy_score(y_te, te_pred)
    mcc = matthews_corrcoef(y_te, te_pred)
    f1w = f1_score(y_te, te_pred, average="weighted", zero_division=0)
    maj_acc = max(y_te.value_counts(normalize=True))

    # Per-class recall
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(y_te, te_pred, labels=[0, 1])
    buy_recall = cm[1, 1] / cm[1].sum() if cm[1].sum() > 0 else 0
    sell_recall = cm[0, 0] / cm[0].sum() if cm[0].sum() > 0 else 0

    result = {
        "family": family_name,
        "added_features": len(new_cols),
        "total_features": len(cols),
        "val_accuracy": float(va_acc),
        "accuracy": float(te_acc),
        "balanced_accuracy": float(te_bal),
        "mcc": float(mcc),
        "f1_weighted": float(f1w),
        "direction_accuracy": float(te_acc),
        "buy_recall": float(buy_recall),
        "sell_recall": float(sell_recall),
        "majority_class_accuracy": float(maj_acc),
        "improvement_vs_majority": float(te_acc - maj_acc),
        "test_size": int(len(y_te)),
    }
    print(f"  Features: {len(cols)} (+{len(new_cols)}) | Val: {va_acc:.4f} | "
          f"Test: {te_acc:.4f} (maj {maj_acc:.4f}) | bal {te_bal:.4f} | mcc {mcc:.4f}"
          f" | BUY recall {buy_recall:.4f} SELL recall {sell_recall:.4f}")
    return result


def main():
    print("=" * 70)
    print("ABLATION EXPERIMENT: which external data improves 5D BUY/SELL?")
    print("=" * 70)
    df, mf = load_data()
    df = add_horizon_targets(df)
    print(f"Data rows: {len(df)}, Market features: {mf.shape}")

    results = {}
    # First run base (no external)
    results["base"] = run_experiment(df, mf, "base")
    # Then each external family
    for fam in EXTERNAL_FAMILIES.keys():
        res = run_experiment(df, mf, fam)
        if res:
            results[fam] = res

    # Save
    with open(os.path.join(ROOT, "improve", "ablation_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("\n" + "=" * 70)
    print("SUMMARY (5D Binary BUY/SELL)")
    print("=" * 70)
    hdr = f"{'Family':<12}{'Features':<10}{'TestAcc':<9}{'BalAcc':<9}{'MCC':<7}{'Dir':<8}{'BUY_recall':<12}{'Sell_recall':<12}"
    print(hdr)
    print("-" * len(hdr))
    for k, v in results.items():
        if v:
            da = v.get("direction_accuracy", 0)
            print(f"{k:<12}{v['total_features']:<10}{v['accuracy']*100:<8.2f}%{v['balanced_accuracy']*100:<8.2f}%"
                  f"{v['mcc']:<7.4f}{da*100 if da else 0:<7.2f}%{v['buy_recall']*100:<11.2f}%{v['sell_recall']*100:<11.2f}%")

    print("\nSaved to improve/ablation_results.json")


if __name__ == "__main__":
    main()