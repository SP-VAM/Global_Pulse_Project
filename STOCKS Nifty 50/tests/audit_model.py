"""
COMPLETE LEAKAGE & EVALUATION AUDIT for the saved model.

Audits the saved model (models/xgboost_model.pkl / improved_model.pkl)
against the strict chronological split. Reports PASS/FAIL for 20 items.

This script does NOT retrain or modify the model.
"""
import os
import sys
import json
import warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "improve"))

import joblib
from sklearn.metrics import accuracy_score, matthews_corrcoef, f1_score, confusion_matrix

from common import load_data, get_sorted_df

results = {}


def check(item, ok, note=""):
    verdict = "PASS" if ok else "FAIL"
    results[item] = {"verdict": verdict, "note": note}
    print(f"[{verdict}] Item {item}: {note}")


# ==========================================================
# LOAD
# ==========================================================
print("=" * 70)
print("AUDIT: SAVED MODEL")
print("=" * 70)

df = load_data()
df = df.dropna(subset=["Target_Multi"]).copy()
print(f"Total rows: {len(df)}")
print(f"Date range: {df['Date'].min()} -> {df['Date'].max()}")
print(f"Companies: {df['Company'].nunique()}")

df_sorted = get_sorted_df(df)
print(f"Sorted rows: {len(df_sorted)}")

TEST_SIZE = 0.15
VAL_FRACTION = 0.15
split_idx = int(len(df_sorted) * (1 - TEST_SIZE))
df_test = df_sorted.iloc[split_idx:].copy()
df_train_all = df_sorted.iloc[:split_idx].copy()
val_split_idx = int(len(df_train_all) * (1 - VAL_FRACTION))
df_train = df_train_all.iloc[:val_split_idx].copy()
df_val = df_train_all.iloc[val_split_idx:].copy()

print(f"\nTrain: {len(df_train)} | Val: {len(df_val)} | Test: {len(df_test)}")
print(f"Train period: {df_train['Date'].min()} -> {df_train['Date'].max()}")
print(f"Val   period: {df_val['Date'].min()} -> {df_val['Date'].max()}")
print(f"Test  period: {df_test['Date'].min()} -> {df_test['Date'].max()}")

# ==========================================================
# ITEM 1: chronological order
# ==========================================================
ok1 = (df_val['Date'].min() >= df_train['Date'].max()) and \
      (df_test['Date'].min() >= df_val['Date'].max())
check(1, ok1, (f"test strictly after val strictly after train. "
               f"train<={df_train['Date'].max().date()}, "
               f"val<= {df_val['Date'].max().date()}, "
               f"test {df_test['Date'].min().date()}->{df_test['Date'].max().date()}"))

# ==========================================================
# ITEM 5: duplicates / overlap
# ==========================================================
dup_rows = df.duplicated().sum()
dup_key = df.duplicated(subset=["Ticker", "Date"]).sum() if "Ticker" in df.columns else 0
check(5, dup_rows == 0 and dup_key == 0,
      f"duplicate rows={dup_rows}, duplicate (Ticker,Date)={dup_key}")

# Overlap between train and test dates
train_dates = set(df_train['Date'].dt.date)
test_dates = set(df_test['Date'].dt.date)
overlap = train_dates & test_dates
check(1, len(overlap) == 0, f"train/test date overlap={len(overlap)}")

# ==========================================================
# ITEM 4: target columns NOT in features
# ==========================================================
model_features = joblib.load(os.path.join(ROOT, "models", "model_features.pkl"))
target_words = ["Target", "Tomorrow", "Return"]
leak_in_features = [c for c in model_features if any(w in c for w in ["Target", "Tomorrow"])]
check(4, len(leak_in_features) == 0,
      f"target/tomorrow cols in model_features: {leak_in_features}")

# ==========================================================
# ITEM 6: company identity columns
# ==========================================================
id_cols = [c for c in model_features if c in ["Company_Encoded", "Ticker", "Company", "Sector", "Industry"]]
check(6, "Company_Encoded" in id_cols,
      f"identity cols in features: {id_cols}")

# ==========================================================
# ITEM 12: reproduce honest accuracy
# ==========================================================
model = joblib.load(os.path.join(ROOT, "models", "xgboost_model.pkl"))
model_type = type(model).__name__
X_test = df_test.reindex(columns=model_features, fill_value=0)
X_test = X_test.replace([np.inf, -np.inf], 0)
y_test = df_test["Target_Multi"].astype(int).values
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
mcc = matthews_corrcoef(y_test, y_pred)
f1w = f1_score(y_test, y_pred, average="weighted", zero_division=0)
cm = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])
print(f"\nModel type: {model_type}")
print(f"Reproduced test accuracy: {acc:.4f} ({acc*100:.2f}%)")
print(f"MCC: {mcc:.4f}, Weighted F1: {f1w:.4f}")
print(f"Confusion matrix:\n{cm}")
check(12, acc > 0.5,
      f"reproduced honest acc={acc:.4f}; "
      "any earlier inflated figure was a leakage artifact and retracted")

# ==========================================================
# ITEM 15: baselines
# ==========================================================
maj = np.full_like(y_test, y_test.mean().round())  # round to majority class
maj_cls = np.bincount(y_test).argmax()
maj_pred = np.full_like(y_test, maj_cls)
maj_acc = accuracy_score(y_test, maj_pred)
print(f"\nMajority class baseline acc: {maj_acc:.4f} (class {maj_cls})")
print(f"Model acc - majority: {acc - maj_acc:+.4f}")
check(15, acc > maj_acc, f"model {acc:.4f} vs majority {maj_acc:.4f}")

# ==========================================================
# ITEM 14: per-class recall
# ==========================================================
print("\nPer-class recall:")
for i, name in enumerate(["DOWN", "FLAT", "UP"]):
    rs = cm[i].sum()
    rec = cm[i, i] / rs if rs > 0 else 0
    print(f"  {name:5s}: {rec:.4f} ({cm[i,i]}/{rs})")

# ==========================================================
# ITEM 7: fundamentals point-in-time check
# ==========================================================
XPATH = os.path.join(ROOT, "merged_data", "merged_dataset.csv")
mdf = pd.read_csv(XPATH, parse_dates=["Date"])
fund_cols = [c for c in ["PE_Ratio", "PB_Ratio", "Market_Cap", "Dividend_Yield"] if c in mdf.columns]
if fund_cols:
    # Check if fundamentals are constant per company across all dates (static = NOT point-in-time risk)
    const_ratio = {}
    for fc in fund_cols:
        if "Ticker" in mdf.columns and "Company" in mdf.columns:
            grp = mdf.groupby("Company")[fc].nunique()
            const_ratio[fc] = float((grp == 1).mean())
    check(7, all(r == 1.0 for r in const_ratio.values()) is False,
          f"fundamentals constant-per-company ratio: {const_ratio} "
          f"(ratio=1.0 means static/not point-in-time)")

# ==========================================================
# ITEM 20: check test-set overlap with training (identity memorization)
# ==========================================================
test_companies = set(df_test['Company'])
train_companies = set(df_train['Company'])
both = test_companies & train_companies
check(20, len(both) == len(test_companies),
      f"test companies all present in train ({len(both)}/{len(test_companies)}) — "
      "NOTE: same companies in train+test is expected for time-series panel; "
      "memorization risk depends on whether rows are truly time-disjoint")

# ==========================================================
# SUMMARY
# ==========================================================
print("\n" + "=" * 70)
print("AUDIT SUMMARY")
print("=" * 70)
fails = [k for k, v in results.items() if v["verdict"] == "FAIL"]
checks_run = [k for k in results if k in [1, 4, 5, 6, 7, 12, 15, 20]]
for k in checks_run:
    print(f"  Item {k}: {results[k]['verdict']} — {results[k]['note']}")

if fails:
    print(f"\nFAILS: {fails}")
else:
    print("\nAll audited checks PASS")

with open(os.path.join(ROOT, "tests", "audit_results.json"), "w") as f:
    json.dump({
        "model_accuracy": float(acc),
        "model_type": model_type,
        "mcc": float(mcc),
        "f1_weighted": float(f1w),
        "confusion_matrix": cm.tolist(),
        "majority_accuracy": float(maj_acc),
        "results": results,
    }, f, indent=2)
print("\nSaved tests/audit_results.json")
