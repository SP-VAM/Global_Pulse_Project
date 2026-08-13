"""
Retain the best HONEST (leak-free) model as the main production model.

This retrains the leak-free ExtraTrees classifier (the model that achieves
~56.2% honest test accuracy on the corrected chronological split) using ONLY
data before the untouched test window, then saves it as the primary model
that the dashboard and predict.py load.

The 56% model is the honest ceiling for the current feature set — it
minimally beats the majority-class baseline (55.68%) and is the best
legitimate model produced by the improvement experiments. Higher claimed
figures (59.85% / 79% / 92%) were data-leakage artifacts and are rejected.

Saved artifacts (same paths used by utils/prediction.py):
  - models/xgboost_model.pkl        -> the 56% ExtraTrees model
  - models/label_encoder.pkl         -> LabelEncoder fit on TRAIN only
  - models/model_features.pkl        -> feature list used at training time
"""

import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
import joblib
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "improve"))

from sklearn.ensemble import ExtraTreesClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score, matthews_corrcoef, f1_score, confusion_matrix,
    precision_score, recall_score
)
from common import load_data, get_sorted_df

# Reuse the exact feature builder from utils/improved_model.py
sys.path.insert(0, os.path.join(ROOT, "utils"))
from improved_model import build_feature_matrix

TEST_SIZE = 0.15
RANDOM_STATE = 42


def main():
    print("=" * 70)
    print("RETAIN HONEST MODEL AS MAIN PRODUCTION MODEL")
    print("(leak-free ExtraTrees, ~56% test accuracy)")
    print("=" * 70)

    # ---- Load & split (corrected strict chronological split) ----
    df = load_data()
    df = df.dropna(subset=["Target_Multi"]).copy()
    df_sorted = get_sorted_df(df)  # global Date sort

    split_idx = int(len(df_sorted) * (1 - TEST_SIZE))
    df_train = df_sorted.iloc[:split_idx].copy()
    df_test = df_sorted.iloc[split_idx:].copy()

    print(f"\nTrain rows: {len(df_train)} ({df_train['Date'].min()} -> {df_train['Date'].max()})")
    print(f"Test rows : {len(df_test)} ({df_test['Date'].min()} -> {df_test['Date'].max()})")

    # ---- Build features (identical to the 56.19% spec) ----
    feature_cols = build_feature_matrix(df)

    le = LabelEncoder()
    df_train["Company_Encoded"] = le.fit_transform(df_train["Company"].astype(str))
    df_test["Company_Encoded"] = df_test["Company"].astype(str).map(
        lambda x: le.transform([x])[0] if x in le.classes_ else -1)
    if "Company_Encoded" not in feature_cols:
        feature_cols = feature_cols + ["Company_Encoded"]

    X_train = df_train[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
    X_test = df_test[feature_cols].fillna(0).replace([np.inf, -np.inf], 0)
    y_train = df_train["Target_Multi"].astype(int)
    y_test = df_test["Target_Multi"].astype(int)

    print(f"\nFeatures: {len(feature_cols)}")
    print(f"X_train: {X_train.shape}, X_test: {X_test.shape}")

    # ---- Train the SAME honest model spec ----
    model = ExtraTreesClassifier(
        n_estimators=400, random_state=RANDOM_STATE, n_jobs=-1, class_weight="balanced")
    print("\nTraining ExtraTrees (400 trees, balanced, seed=42)...")
    model.fit(X_train, y_train)

    # ---- Evaluate ONCE on untouched test ----
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    acc = accuracy_score(y_test, y_pred)
    mcc = matthews_corrcoef(y_test, y_pred)
    f1w = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    pw = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    rw = recall_score(y_test, y_pred, average="weighted", zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])
    non_flat = y_test != 1
    dir_acc = accuracy_score(y_test[non_flat], y_pred[non_flat]) if non_flat.sum() > 0 else None
    maj_acc = max(y_test.value_counts(normalize=True))

    print("\n" + "=" * 60)
    print("HONEST TEST SCORE (main model)")
    print("=" * 60)
    print(f"Accuracy           : {acc:.4f} ({acc*100:.2f}%)  (majority: {maj_acc:.4f})")
    print(f"MCC                : {mcc:.4f}")
    print(f"Weighted F1        : {f1w:.4f}")
    print(f"Weighted Precision : {pw:.4f}")
    print(f"Weighted Recall    : {rw:.4f}")
    print(f"Direction accuracy : {dir_acc:.4f}" if dir_acc is not None else "Direction accuracy : N/A")
    print("\nConfusion Matrix [rows=actual, cols=pred] [0=DOWN,1=FLAT,2=UP]:")
    print(cm)

    # ---- Save as the MAIN production model ----
    print("\nSaving as main production model...")
    os.makedirs(os.path.join(ROOT, "models"), exist_ok=True)
    joblib.dump(model, os.path.join(ROOT, "models", "xgboost_model.pkl"))
    joblib.dump(le, os.path.join(ROOT, "models", "label_encoder.pkl"))
    joblib.dump(feature_cols, os.path.join(ROOT, "models", "model_features.pkl"))
    print("Saved to models/xgboost_model.pkl, models/label_encoder.pkl, models/model_features.pkl")

    # ---- Save metrics ----
    out = {
        "model": "ExtraTrees (400 trees, balanced, seed=42)",
        "split": "corrected strict chronological (global Date sort, last 15% test)",
        "retained_as_main": True,
        "test_size": int(len(y_test)),
        "test_period": [str(df_test['Date'].min()), str(df_test['Date'].max())],
        "accuracy": float(acc),
        "mcc": float(mcc),
        "f1_weighted": float(f1w),
        "precision_weighted": float(pw),
        "recall_weighted": float(rw),
        "direction_accuracy": float(dir_acc) if dir_acc is not None else None,
        "confusion_matrix": cm.tolist(),
        "majority_class_accuracy": float(maj_acc),
        "improvement_vs_majority": float(acc - maj_acc),
        "feature_count": len(feature_cols),
    }
    with open(os.path.join(ROOT, "models", "main_model_metrics.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("Metrics saved to models/main_model_metrics.json")


if __name__ == "__main__":
    main()
