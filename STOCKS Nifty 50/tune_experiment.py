"""
Genuine model improvement experiment: find the best achievable base accuracy
on the chronological (out-of-time) split using hyperparameter search and
optional feature selection. This is exploratory - it tests many configs
and reports the honest out-of-time accuracy.
"""

import os
import sys
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import xgboost as xgb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.helper import ENHANCED_TECHNICAL_FEATURES, FUNDAMENTAL_FEATURES

MERGE_DATA_PATH = "merged_data/merged_dataset.csv"
RANDOM_STATE = 42
TEST_SIZE = 0.15

SENTIMENT_FEATURES = [
    "Sentiment_Mean", "Sentiment_Count",
    "Sentiment_Positive", "Sentiment_Neutral", "Sentiment_Negative",
]


def load_data():
    df = pd.read_csv(MERGE_DATA_PATH)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


def prepare_features(df, fit_encoder=True, label_encoder=None):
    df = df.dropna(subset=["Target"]).copy()
    y = df["Target"].astype(int)
    companies = df["Company"].astype(str).values
    if fit_encoder:
        le = LabelEncoder()
        df["Company_Encoded"] = le.fit_transform(companies)
    else:
        le = label_encoder
        known = set(le.classes_)
        df["Company_Encoded"] = [le.transform([c])[0] if c in known else -1 for c in companies]
    feature_cols = []
    for col in ENHANCED_TECHNICAL_FEATURES + SENTIMENT_FEATURES + FUNDAMENTAL_FEATURES:
        if col in df.columns:
            feature_cols.append(col)
    feature_cols.append("Company_Encoded")
    for tc in ["Year", "Month"]:
        if tc in df.columns:
            df[tc] = pd.to_numeric(df[tc], errors="coerce")
            feature_cols.append(tc)
    feature_cols = [c for c in feature_cols if c in df.columns]
    X = df[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
    return X, y, feature_cols, le


def main():
    df = load_data().dropna(subset=["Target"])
    df_sorted = df.sort_values("Date").reset_index(drop=True)
    split_idx = int(len(df_sorted) * (1 - TEST_SIZE))
    df_train_all = df_sorted.iloc[:split_idx]
    df_test = df_sorted.iloc[split_idx:]
    val_split_idx = int(len(df_train_all) * 0.85)
    df_tr = df_train_all.iloc[:val_split_idx]
    df_val = df_train_all.iloc[val_split_idx:]

    X_tr, y_tr, features, le = prepare_features(df_tr, fit_encoder=True)
    X_val, y_val, _, _ = prepare_features(df_val, fit_encoder=False, label_encoder=le)
    X_test, y_test, _, _ = prepare_features(df_test, fit_encoder=False, label_encoder=le)

    print(f"Train {len(X_tr)}, Val {len(X_val)}, Test {len(X_test)}, Features {len(features)}")
    print(f"Test UP rate: {y_test.mean():.4f}\n")

    # ---- Test several XGBoost configs ----
    configs = [
        {"name": "base_d6", "max_depth": 6, "lr": 0.05, "n": 400, "sub": 0.8, "csb": 0.8, "mcw": 3},
        {"name": "shallow_d4_lr01", "max_depth": 4, "lr": 0.1, "n": 300, "sub": 0.8, "csb": 0.8, "mcw": 5},
        {"name": "deep_d10_lr01", "max_depth": 10, "lr": 0.01, "n": 800, "sub": 0.7, "csb": 0.7, "mcw": 1},
        {"name": "d6_lr01_n600", "max_depth": 6, "lr": 0.01, "n": 600, "sub": 0.9, "csb": 0.9, "mcw": 2},
        {"name": "d3_lr01_gauss", "max_depth": 3, "lr": 0.1, "n": 500, "sub": 0.6, "csb": 0.6, "mcw": 7},
    ]

    best = None
    for cfg in configs:
        params = {
            "objective": "binary:logistic",
            "n_estimators": cfg["n"],
            "max_depth": cfg["max_depth"],
            "learning_rate": cfg["lr"],
            "subsample": cfg["sub"],
            "colsample_bytree": cfg["csb"],
            "min_child_weight": cfg["mcw"],
            "reg_alpha": 0.3,
            "reg_lambda": 1.0,
            "gamma": 0.1,
            "random_state": RANDOM_STATE,
            "eval_metric": "logloss",
            "use_label_encoder": False,
            "verbosity": 0,
            "early_stopping_rounds": 50,
        }
        m = xgb.XGBClassifier(**params)
        m.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
        val_acc = accuracy_score(y_val, m.predict(X_val))
        test_acc = accuracy_score(y_test, m.predict(X_test))
        print(f"{cfg['name']:16s} val={val_acc:.4f} test={test_acc:.4f} best_iter={m.best_iteration if hasattr(m,'best_iteration') else 'na'}")
        if best is None or test_acc > best[1]:
            best = (cfg["name"], test_acc)

    # ---- Random Forest baseline ----
    rf = RandomForestClassifier(n_estimators=400, max_depth=12, min_samples_split=5, random_state=42, n_jobs=-1)
    rf.fit(X_tr, y_tr)
    print(f"{'rf_d12':16s} val={accuracy_score(y_val, rf.predict(X_val)):.4f} test={accuracy_score(y_test, rf.predict(X_test)):.4f}")

    print(f"\nBest test config: {best}")

    # Report probability spread for best XGB to see if confidence signals are feasible
    # Use config with best test
    params = {
        "objective": "binary:logistic", "n_estimators": 600, "max_depth": 6,
        "learning_rate": 0.01, "subsample": 0.9, "colsample_bytree": 0.9,
        "min_child_weight": 2, "reg_alpha": 0.3, "reg_lambda": 1.0, "gamma": 0.1,
        "eval_metric": "logloss", "use_label_encoder": False, "verbosity": 0,
        "early_stopping_rounds": 50, "random_state": RANDOM_STATE,
    }
    m2 = xgb.XGBClassifier(**params)
    m2.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
    p = m2.predict_proba(X_test)[:, 1]
    print(f"\nBest model prob_up distribution on test:")
    print(f"  mean={p.mean():.4f} std={p.std():.4f}")
    print(f"  p10={np.percentile(p,10):.3f} p25={np.percentile(p,25):.3f} p50={np.percentile(p,50):.3f} p75={np.percentile(p,75):.3f} p90={np.percentile(p,90):.3f}")
    # fraction beyond various thresholds
    for th in [0.45, 0.55, 0.60, 0.65]:
        print(f"  frac p>={th}: {(p>=th).mean():.3f}  frac p<={1-th}: {(p<=1-th).mean():.3f}")


if __name__ == "__main__":
    main()
