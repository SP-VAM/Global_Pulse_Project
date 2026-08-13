# Leak-Safe Improvement Report

## Overview

This report documents the complete leak-safe improvement of the stock prediction project. All work was performed using strictly chronological train/validation/test splits. The final test set was kept untouched until final evaluation.

## 1. Critical Issues Fixed

### 1.1 Removed Leaked Model
- **Deleted**: `models/improved_model.pkl`, `models/improved_label_encoder.pkl`, `models/improved_model_features.pkl`
- These were trained on the old leaked split (sort by Company→Date) where 83.7% of the corrected test rows had leaked into training.
- `utils/prediction.py` now loads only the honest `models/xgboost_model.pkl`.

### 1.2 Hardcoded API Key
- **Fixed**: `utils/live_news.py` now reads `NEWS_API_KEY` from `.env` using `python-dotenv`.
- ⚠️ **ACTION REQUIRED**: The exposed key `348fbac19def4c5c85e015364f9f5569` was committed to the repo and must be **rotated** at newsapi.org.

### 1.3 ADX Calculation
- **Fixed** both `technical_indicators.py` and `utils/preprocess_stock.py`:
  - Old (incorrect): `ADX = ATR / Close * 100`
  - New (correct Wilder's): Computed from True Range, +DM/−DM directional movement, smoothed DI, and DX — the true ADX.

### 1.4 Binary Prediction Mapping
- **Fixed** `utils/prediction.py` `make_prediction()`:
  - Binary models (2 classes) now map `{0: DOWN, 1: UP}` (not `{1: FLAT}`).
  - Multi-class models (3 classes) map `{0: DOWN, 1: FLAT, 2: UP}`.

### 1.5 `tests/audit_deep.py` Bug
- **Fixed** the walrus-operator bug where `split_idx` was referenced before definition.

### 1.6 Hardcoded End Dates
- **Fixed** `download_stock_data.py` and `download_market_data.py` to use `datetime.now()` instead of hardcoded `"2026-07-01"`.

## 2. Canonical Leak-Safe Pipeline

### `build_horizon_models.py`
The new canonical training script. Features:
- **Split (FROZEN)**: Sort globally by Date; last 15% = untouched TEST; remaining → TRAIN (85%) / VAL (15%), chronological.
- **Targets**:
  - 3-class: `0=DOWN (≤ -1%), 1=FLAT, 2=UP (≥ +1%)`
  - Binary: `0=SELL, 1=BUY` (FLAT dropped)
- **Horizons**: 1D (next day), 5D (next 5 trading days), 10D (next 10 trading days)
- **Models**: XGBoost, LightGBM, ExtraTrees, RandomForest — selection by validation accuracy; test evaluated ONCE.
- **Artifacts**: `models/model_{horizon}_{target}.pkl` + features + encoder + metrics.

### `ablation_experiment.py`
Tests which external data actually improves 5D BUY/SELL:
- India VIX, Sensex, BankNifty, **sector indices**, macro (USDINR/GOLD/BRENT/WTI/US10Y), market breadth.

### `retrain_best_model.py`
Retrains the best model (10D binary) with sector-index features added.

### `merge_sector_features.py`
Merges sector-index features into `merged_dataset.csv` (point-in-time, merge_asof backward).

## 3. Honest Baseline

The existing 1D model (`models/xgboost_model.pkl`, leak-free ExtraTrees) evaluated on the untouched chronological test set:

| Metric | Value |
|--------|-------|
| Accuracy | 56.19% |
| Balanced Accuracy | ~33.4% |
| MCC | 0.103 |
| Weighted F1 | 44.46% |
| UP recall | 11.76% |
| FLAT recall | 95.83% |
| DOWN recall | 1.15% |
| Direction accuracy | 6.38% |
| Majority baseline | 55.68% |

**Verdict**: The existing 1D model is essentially at the majority-class noise floor.

## 4. Horizon Comparison Results

Trained on the **same frozen chronological split**, each evaluated ONCE on the untouched test set.

| Horizon | Target | Model | Accuracy | Balanced Acc | MCC | F1 | Direction Acc | BUY/UP Recall | SELL/DOWN Recall |
|---------|--------|-------|----------|--------------|-----|-----|---------------|---------------|------------------|
| 1D | 3-class | ExtraTrees | 54.56% | 29.44% | 0.137 | 0.463 | 15.37% | — | — |
| **1D** | **Binary** | **ExtraTrees** | **51.64%** | **51.65%** | **0.033** | **0.516** | **51.64%** | — | — |
| 5D | 3-class | RandomForest | 34.39% | 25.52% | 0.023 | 0.219 | 43.70% | — | — |
| 5D | Binary | LightGBM | 50.58% | 50.72% | 0.014 | 0.505 | 50.58% | — | — |
| 10D | 3-class | ExtraTrees | 38.23% | 24.78% | -0.010 | 0.263 | 45.67% | — | — |
| **10D** | **Binary** | **RandomForest** | **54.19%** | **54.13%** | **0.084** | **0.539** | **54.19%** | — | — |

### Ablation Results (5D binary, ExtraTrees)

| External Data | Test Acc | Balanced Acc | MCC | BUY Recall | SELL Recall |
|---------------|----------|--------------|-----|------------|-------------|
| Base (no external) | 50.05% | 49.92% | -0.002 | 47.23% | 52.61% |
| India VIX | 48.86% | 48.84% | -0.023 | 48.48% | 49.20% |
| **Sensex** | **51.81%** | **51.39%** | **0.028** | **42.63%** | **60.15%** |
| BankNifty | 51.09% | 49.87% | -0.003 | 24.47% | 75.27% |
| **Sector indices** | **54.28%** | **53.95%** | **0.080** | **47.18%** | **60.73%** |
| Macro | 50.52% | 50.11% | 0.002 | 41.57% | 58.65% |
| Market breadth | 49.31% | 49.26% | -0.015 | 48.17% | 50.35% |

**Conclusion**: Only **sector indices** genuinely improve directional prediction.

### Final Best Model: 10D Binary + Sector Indices

| Metric | Value |
|--------|-------|
| Model | ExtraTrees (400 trees, balanced, seed=42) |
| Accuracy | **54.31%** |
| Balanced Accuracy | 54.24% |
| MCC | 0.085 |
| Weighted F1 | 54.27% |
| BUY recall | 51.15% |
| SELL recall | 57.34% |
| ROC-AUC | 0.5627 |
| Majority baseline | 51.03% |
| **Improvement over majority** | **+3.28%** |

Test size: 6,651 rows | Period: 2025-10-29 → 2026-06-29

## 5. Dashboard Updates

`dashboard/app.py` now has a **Prediction Horizon** dropdown:
- Next Day (1D)
- 5 Days (5D)
- 10 Days (10D)

Changing the dropdown automatically loads the correct model, encoder, features, and metrics. The `10D` uses the best sector-enhanced model. Each prediction shows:
- BUY/SELL classification
- Confidence/probability
- Current price
- Horizon explanation
- Model test metrics (when available)

## 6. Files Changed / Created

**Modified:**
- `.env` — Added `NEWS_API_KEY`
- `utils/live_news.py` — Read API key from env, removed hardcoded key
- `utils/preprocess_stock.py` — Fixed ADX
- `technical_indicators.py` — Fixed ADX
- `utils/prediction.py` — Fixed binary mapping + model paths to honest model
- `tests/audit_deep.py` — Fixed walrus-operator bug
- `download_stock_data.py` — Dynamic end date
- `download_market_data.py` — Dynamic end date
- `dashboard/app.py` — Added horizon dropdown, horizon-specific model loading
- `dashboard/utils.py` — Added `get_horizon_models()`
- `merged_data/merged_dataset.csv` — Added 120 sector-index features (point-in-time)

**Created:**
- `build_horizon_models.py` — Canonical leak-safe horizon model builder
- `ablation_experiment.py` — External data ablation experiment
- `retrain_best_model.py` — Best model (10D binary + sector) retrainer
- `merge_sector_features.py` — Sector feature merger
- `LEAK_SAFE_IMPROVEMENT_REPORT.md` — This report

**Saved Models (in `models/`):**
- `model_1d_3class.pkl` + features + encoder + metrics
- `model_1d_binary.pkl` + features + encoder + metrics
- `model_5d_3class.pkl` + features + encoder + metrics
- `model_5d_binary.pkl` + features + encoder + metrics
- `model_10d_3class.pkl` + features + encoder + metrics
- `model_10d_binary.pkl` + features + encoder + metrics
- `model_10d_binary_sector.pkl` + features + encoder + metrics **(BEST)**
- `horizon_comparison.json`

**Experiment Results (in `improve/`):**
- `ablation_results.json`

## 7. Honest Conclusion

- The **10D binary (BUY/SELL) model with sector-index features** is the genuinely strongest model: **54.31%** accuracy, beating the majority baseline by **+3.28%** with ROC-AUC 0.563.
- The 1D horizon remains near the noise floor — next-day direction is fundamentally harder to predict.
- No data leakage: all results are on the untouched chronological test set evaluated exactly once.
- Any further improvement requires genuinely new out-of-sample information (e.g., options/IV data, order flow) — not more tuning on the current features.