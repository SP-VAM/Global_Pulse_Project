# Complete Model Documentation

This document describes every model in the Stock Market Prediction project — its purpose, architecture, features, target, hyperparameters, and how hyperparameter tuning is performed.

---

## Table of Contents

1. [Production Models (in `models/`)](#1-production-models-in-models)
2. [Training Scripts & Their Models](#2-training-scripts--their-models)
3. [Improvement Experiment Models (in `improve/`)](#3-improvement-experiment-models-in-improve)
4. [Hyperparameter Usage Summary](#4-hyperparameter-usage-summary)
5. [Feature Sets Used by Each Model](#5-feature-sets-used-by-each-model)
6. [Evaluation Methodology](#6-evaluation-methodology)

---

## 1. Production Models (in `models/`)

### 1.1 `models/xgboost_model.pkl`

| Attribute | Value |
|---|---|
| **Algorithm** | ExtraTrees Classifier (retained honest model) |
| **Task type** | Multi-class classification (3 classes) |
| **Target** | `Target_Multi`: `0=DOWN, 1=FLAT, 2=UP` |
| **Purpose** | Production direction-prediction model loaded by the dashboard and `predict.py`. |
| **Test accuracy** | **≈56.2%** (honest, leak-free) |
| **Hyperparameters** | `ExtraTreesClassifier(n_estimators=400, random_state=42, n_jobs=-1, class_weight="balanced")` |
| **Features** | 81 (`build_feature_matrix` — technical + sentiment + fundamentals + NIFTY market) |

> ✅ **Retained as main model (2026-08-08):** The 56.2% leak-free ExtraTrees is now the
> production model. It was retrained leak-free on the *corrected chronological split*
> (83.7% of the old test set had leaked into the old training set) and evaluates to
> **56.19%** on the untouched test set — +0.51% over the 55.68% majority-class baseline.
>
> ⚠️ **Leakage note:** The previously saved `improved_model.pkl` was trained with the OLD
> leaked split (sort by Company then Date). Its 59.85% test accuracy was inflated by 83.7%
> train/test overlap and has been **removed**. The honest, leak-safe accuracy of the same
> model approach is **≈56.2%** (see §6). Lower claimed figures (79% / 92%) were also
> leakage artifacts and are rejected.

---

### 1.2 Supporting artifacts in `models/`

| File | Content |
|---|---|
| `label_encoder.pkl` | `LabelEncoder` fitted on Company names → `Company_Encoded` integer |
| `model_features.pkl` | List of feature column names used at training time |

---

## 2. Training Scripts & Their Models

### 2.1 `train_xgboost.py` — Main Enhanced XGBoost + Stacking Ensemble

**Purpose:** The primary training pipeline. Trains an XGBoost multi-class classifier, optionally a stacking ensemble (XGBoost + LightGBM + CatBoost → Logistic Regression), and saves whichever has the best test accuracy.

**Target:** `Target_Multi` (0=DOWN, 1=FLAT, 2=UP) — binary `Target` also supported via `--target binary`.

**Chronological split (leak-safe):**
- Sort **globally by Date**
- Last 15% = test set
- Remaining 85% → train (85%) / validation (15%) chronologically

**Model A — XGBoost base defaults:**
```python
XGBClassifier(
    objective="multi:softprob",   # class probabilities, not just labels
    num_class=3,
    n_estimators=200,             # number of boosting rounds
    max_depth=8,                  # tree depth
    learning_rate=0.05,           # shrinkage per tree
    subsample=0.8,                # fraction of rows per tree (row sampling)
    colsample_bytree=0.8,         # fraction of features per tree (column sampling)
    min_child_weight=3,           # min sum of instance weight in a child node
    reg_alpha=0.5,                # L1 regularization
    reg_lambda=1.0,               # L2 regularization
    gamma=0.2,                    # min loss reduction for a split
    random_state=42,
    eval_metric="mlogloss",
)
```

**Model B — Stacking Ensemble:**
- Base learners:
  - **XGBoost**: same params as above, 300 trees, depth 8, lr 0.05
  - **LightGBM**: `n_estimators=300, max_depth=8, learning_rate=0.05, num_leaves=64, min_child_samples=20, subsample=0.8, colsample_bytree=0.8, reg_alpha=0.5, reg_lambda=1.0, class_weight="balanced"`
  - **CatBoost**: `iterations=300, depth=8, learning_rate=0.05, loss_function="MultiClass", auto_class_weights="Balanced"`
- Meta-learner: `LogisticRegression(max_iter=2000, C=1.0, class_weight="balanced", n_jobs=-1)`
- Stacking uses `stack_method="predict_proba"`, `cv=3`, `passthrough=False`

**How hyperparameter tuning is done (this script):**
`perform_hyperparameter_tuning()` uses `RandomizedSearchCV` with:
- **Search grid** over: `n_estimators [100,200,300,500]`, `max_depth [4,6,8,10,12]`, `learning_rate [0.01,0.03,0.05,0.1]`, `subsample [0.6,0.7,0.8,0.9]`, `colsample_bytree [0.6,0.7,0.8,0.9]`, `min_child_weight [1,3,5,7]`, `reg_alpha [0,0.1,0.5,1.0]`, `reg_lambda [0,0.1,0.5,1.0]`, `gamma [0,0.1,0.2,0.5]`
- **30 random iterations** (`n_iter=30`)
- **Cross-validation:** `TimeSeriesSplit(n_splits=min(3, len(X_train)//1000))` — respects time order, no shuffling
- **Scoring:** `"accuracy"`
- **Sample weights:** inverse-frequency class weights (FLAT majority down-weighted)
- Skipped automatically if training set ≤ 5000 rows

---

### 2.2 `train_binary_confidence.py` — Binary Confidence Trading Signals

**Purpose:** Trains a binary XGBoost (UP/DOWN) but instead of forcing a prediction each day, maps the predicted probability of UP into 5 trading signals. Only trades when confident. This raises per-signal accuracy.

**Target:** `Target` (binary: 0=DOWN, 1=UP)

**Hyperparameters:**
```python
XGBClassifier(
    objective="binary:logistic",
    n_estimators=400,
    max_depth=6,
    learning_rate=0.03,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=3,
    reg_alpha=0.3,
    reg_lambda=1.0,
    gamma=0.1,
    random_state=42,
    eval_metric="logloss",
    early_stopping_rounds=50,    # stops when val logloss doesn't improve for 50 rounds
)
```

**Confidence thresholds (hard-coded constants):**
```python
BUY_LOW  = 0.55   # prob_up >= 0.55 -> Buy
BUY_HIGH = 0.65   # prob_up >= 0.65 -> Strong Buy
SELL_HIGH = 0.45  # prob_up <= 0.45 -> Sell
SELL_LOW  = 0.35  # prob_up <= 0.35 -> Strong Sell
# otherwise -> Hold
```

**Purpose of thresholds:** `map_signal(prob_up)` converts a continuous probability into discrete trading signals. The model only takes a directional stance when it's confident, so actionable signals (Buy/Sell) have higher directional accuracy than a blanket 50% threshold prediction.

---

### 2.3 `tune_experiment.py` — Hyperparameter Exploration

**Purpose:** Exploratory script that tests 5 hand-picked XGBoost configurations + 1 Random Forest to find the best base accuracy on the chronological split. No model is saved.

**Configs tested:**

| Name | max_depth | learning_rate | n_estimators | subsample | colsample_bytree | min_child_weight |
|---|---|---|---|---|---|---|
| `base_d6` | 6 | 0.05 | 400 | 0.8 | 0.8 | 3 |
| `shallow_d4_lr01` | 4 | 0.1 | 300 | 0.8 | 0.8 | 5 |
| `deep_d10_lr01` | 10 | 0.01 | 800 | 0.7 | 0.7 | 1 |
| `d6_lr01_n600` | 6 | 0.01 | 600 | 0.9 | 0.9 | 2 |
| `d3_lr01_gauss` | 3 | 0.1 | 500 | 0.6 | 0.6 | 7 |
| `rf_d12` | 12 | — | 400 | — | — | (min_samples_split=5) |

Also reports probability spread (p10/p25/p50/p75/p90) to assess whether confidence-based signals are feasible.

---

### 2.4 `download_market_data.py` — Market Data Generation (not a model)

**Purpose:** Downloads broad indices (NIFTY, SENSEX, BANKNIFTY, INDIAVIX) + sector indices via yfinance, computes market breadth from local stock CSVs, computes market regime/strength/alignment scores, saves to `market_data/market_features.csv`. No ML model — feeds features into the merge pipeline.

---

## 3. Improvement Experiment Models (in `improve/`)

### 3.1 `improve/train_models.py` — Weighted XGBoost / LightGBM

**Purpose:** Baseline improvement experiments on the frozen split. Trains multi-class XGBoost and LightGBM with/without class weights; saves `xgb_weighted.pkl` and `lgbm_weighted.pkl` to `improve/models/`.

**Hyperparameters (shared core):**
```python
# XGBoost
XGBClassifier(
    objective="multi:softprob", num_class=3,
    n_estimators=300, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
    reg_alpha=0.3, reg_lambda=1.0, gamma=0.1,
    random_state=42, eval_metric="mlogloss",
    early_stopping_rounds=30,
)

# LightGBM
LGBMClassifier(
    objective="multiclass", num_class=3,
    n_estimators=300, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, min_child_samples=20,
    reg_alpha=0.3, reg_lambda=1.0, num_leaves=32? (default),
    random_state=42, n_jobs=-1,
)
```

**Class weights:** inverse-frequency `weights = total / (n_classes * class_count)` applied as `sample_weight`.

---

### 3.2 `improve/optimize_threshold.py` — Threshold Optimization

**Purpose:** Trains weighted XGBoost and LightGBM, then tunes **per-class decision-threshold weights** on the validation set only (leak-safe). Prediction = `argmax(w_c * P(c))`.

**How thresholds are tuned:** `search_thresholds()` performs a **greedy coordinate search** (3 passes) over each class weight in `linspace(0.1, 3.0, 11)` on validation. The best weights are applied to the test set once.

---

### 3.3 `improve/honest_improve.py` — Leak-Safe Multi-Model Harness

**Purpose:** The main honest improvement harness on the corrected chronological split. Trains 4 models, selects the best by validation accuracy, optionally tunes thresholds, evaluates the test set exactly once.

**Models & hyperparameters:**

| Model | Key hyperparameters |
|---|---|
| **XGBoost** | `n_estimators=400, max_depth=6, learning_rate=0.05, subsample=0.85, colsample_bytree=0.85, min_child_weight=3, reg_alpha=0.5, reg_lambda=1.0, gamma=0.1, early_stopping_rounds=30` |
| **LightGBM** | `n_estimators=400, max_depth=6, learning_rate=0.05, subsample=0.85, colsample_bytree=0.85, min_child_samples=20, reg_alpha=0.5, reg_lambda=1.0, num_leaves=64, early_stopping(30)` |
| **ExtraTrees** | `n_estimators=500, max_features=0.7, min_samples_leaf=2, class_weight="balanced"` |
| **RandomForest** | `n_estimators=500, max_features=0.7, min_samples_leaf=2, class_weight="balanced"` |

**Feature engineering (leak-safe, past-only):**
- Cross-sectional market stats (mean/std/%up) lagged 1 day
- Per-company rolling mean/std/skew over 5/10/20 days
- Momentum (10d, 20d), volume ratio, RSI diff/lag
- Calendar: `DayOfWeek`, `MonthSin`, `MonthCos`
- Normalized levels: `Close/SMA20`, `Close/SMA50`, `ATR/Close`, `RSI/100`, volatility-normalized return

**Result:** Best model (ExtraTrees + tuned thresholds) = **55.66%** test accuracy vs 55.68% majority baseline.

---

### 3.4 `improve/ensemble_experiment.py` — Soft-Voting Ensemble

**Purpose:** Combines XGBoost + LightGBM + ExtraTrees + RandomForest via **averaged class probabilities** (soft voting). Blend weights + per-class thresholds tuned on validation only.

**Hyperparameters:** Same core as `honest_improve.py` but 250 trees (faster). Tuning uses a grid over blend weights `w0, w1, w2 ∈ linspace(0.2,1.0,7)` (RF fixed at 0.5) plus 2-pass coordinate search over class threshold weights.

**Result:** **55.94%** test accuracy (MCC 0.119) — the best honest result, +0.26% over majority baseline.

---

### 3.5 `improve/engineered_experiment.py` — Feature-Engineering Experiment

**Purpose:** Tests ~90 engineered features (market-relative, regime, momentum, volume-confirmation, seasonality), selects a stable subset of 40 via combined XGBoost+LightGBM importance ranking, then trains 6 candidate models and picks the best by validation.

**Feature selection:** `select_stable_features()` averages XGBoost and LightGBM importance ranks and keeps top 40.

**Hyperparameters tested:** 3 XGBoost configs (`n_estimators 250/350/400`, `depth 4/6/5`, `lr 0.05/0.03/0.04`) and 3 LightGBM configs (same depth/lr pattern).

**Result:** Accuracy **52.90%** — did not beat the majority baseline.

---

### 3.6 `improve/baseline.py` — Baseline Evaluation

**Purpose:** Evaluates the current saved model (`models/xgboost_model.pkl`) on the frozen chronological split. Reports baseline metrics to `baseline_metrics.json`. Any earlier inflated figure (~79%) was a leakage artifact and has been retracted; the honest scores appear in §6.

### 3.7 `improve/error_analysis.py` — Error Analysis

**Purpose:** Breaks down test errors by company, sector, market regime, volatility level, month, quarter, year. Key finding: the degenerate baseline predicts FLAT for 100% of rows; 0% recall on DOWN/UP.

---

## 4. Hyperparameter Usage Summary

### 4.1 XGBoost — Most Common Hyperparameters Across Scripts

| Hyperparameter | train_xgboost (default) | train_xgboost (tuned range) | train_binary | improve models | Purpose |
|---|---|---|---|---|---|
| `objective` | `multi:softprob` | `multi:softprob` / `binary:logistic` | `binary:logistic` | `multi:softprob` | Loss/objective function |
| `n_estimators` | 200 | 100–500 | 400 | 250–400 | Number of boosting trees |
| `max_depth` | 8 | 4–12 | 6 | 4–6 | Tree depth (complexity) |
| `learning_rate` | 0.05 | 0.01–0.1 | 0.03 | 0.03–0.05 | Step-size shrinkage |
| `subsample` | 0.8 | 0.6–0.9 | 0.8 | 0.8–0.85 | Row sampling per tree |
| `colsample_bytree` | 0.8 | 0.6–0.9 | 0.8 | 0.8–0.85 | Column sampling per tree |
| `min_child_weight` | 3 | 1–7 | 3 | 3 | Min sum of instance weight in child |
| `reg_alpha` | 0.5 | 0–1.0 | 0.3 | 0.3–0.5 | L1 regularization |
| `reg_lambda` | 1.0 | 0–1.0 | 1.0 | 1.0 | L2 regularization |
| `gamma` | 0.2 | 0–0.5 | 0.1 | 0.1 | Min loss reduction for split |
| `early_stopping_rounds` | — | — | 50 | 30 | Stop when val metric stalls |
| `eval_metric` | `mlogloss` | `mlogloss`/`logloss` | `logloss` | `mlogloss` | Validation metric |

### 4.2 How Hyperparameter Tuning Is Performed

1. **RandomizedSearchCV + TimeSeriesSplit** (`train_xgboost.py`):
   - 30 random draws from the grid
   - Time-series CV (no shuffle) — prevents future data leaking into validation folds
   - Scoring = accuracy
   - Class-imbalance handled via `sample_weight`

2. **Manual grid exploration** (`tune_experiment.py`): 5 hand-designed configs tested, best picked by test accuracy (exploratory only).

3. **Validation-based threshold tuning** (`optimize_threshold.py`, `honest_improve.py`, `ensemble_experiment.py`): per-class probability weights tuned via greedy coordinate search on validation set; applied once to test.

4. **Feature selection** (`engineered_experiment.py`): combined XGBoost + LightGBM importance ranks, keep top 40.

### 4.3 Class Imbalance Handling

FLAT is the majority class (~56%). Handled via:
- `class_weight="balanced"` (ExtraTrees, RandomForest, CatBoost, LightGBM)
- Explicit inverse-frequency `sample_weight` arrays (XGBoost, LightGBM)
- Per-class threshold tuning (validation-based)

---

## 5. Feature Sets Used by Each Model

| Feature group | Example columns | Used by |
|---|---|---|
| **Price** | Open, High, Low, Close, Volume | All (via indicators) |
| **Technical (base)** | SMA20/50, EMA20/50, RSI, MACD*, BB_*, ATR, OBV, STOCH_K/D, ADX, Daily_Return, Volatility, Price_Change* | All |
| **Technical (advanced)** | WILLIAMS_R, MFI, ROC, CCI | All |
| **Ratios** | Close_SMA20_Ratio, Close_SMA50_Ratio, Close_BB_Width_Ratio, Volume_SMA20_Ratio, RSI_Normalized, ATR_Normalized | All |
| **Lags** | Close_lag1/2/3, RSI_lag1, MACD_lag1, Daily_Return_lag1, ATR_lag1, ADX_lag1, Volume_lag1/2/3 | All |
| **Rolling** | Close_5d/10d_max/min, High_5d_max, Low_5d_min, Volume_5d_mean, Daily_Return_5d/10d_mean | All |
| **Sentiment** | Sentiment_Mean, Sentiment_Count, Sentiment_Positive/Neutral/Negative | All |
| **Fundamentals** | PE_Ratio, PB_Ratio, Market_Cap, Dividend_Yield, Valuation_Category_* | All |
| **NIFTY market** | NIFTY_Daily_Return, NIFTY_3D/5D/10D/20D_Return, NIFTY_EMA20/50/200, NIFTY_RSI, NIFTY_MACD*, NIFTY_ADX, NIFTY_Trend_Direction, NIFTY_Rolling_Volatility, NIFTY_Market_Strength, Stock_vs_Nifty_Return | improved_model, engineered |
| **Market regime** | Market_Regime, Regime_Strong_Bull/Bull/Neutral/Bear/Strong_Bear | merged dataset |
| **Engineered (honest_improve)** | Market_Mean_lag1, Market_Std_lag1, Market_Breadth_lag1, Ret_{5,10,20}d_{mean,std,skew}, Mom_10d/20d, Volume_ratio_1d, RSI_diff, DayOfWeek, MonthSin, MonthCos, ATR_Norm, RSI_Norm, Ret_vol_normalized | honest_improve, ensemble |
| **Engineered (engineered_experiment)** | Market_Return*, Market_Breadth*, Stock_vs_Market_Return*, Daily_Return_{5,10,20}d_{mean,std,z}, Close_{5,20}d_momentum, Volume_Change_{1,5}d, Volume_Price_Confirmation, Momentum_Volume_Interaction, Quarter | engineered_experiment |
| **Time/categorical** | Company_Encoded, Year, Month, Quarter, DayOfWeek | All |

---

## 6. Evaluation Methodology

### Metrics
- **Accuracy** (overall + per-class)
- **Precision / Recall / F1** (weighted, `zero_division=0`)
- **MCC** (Matthews Correlation Coefficient) — robust for imbalance
- **ROC-AUC** (binary / one-vs-rest macro for multi-class)
- **Direction accuracy** — accuracy on non-FLAT rows only (UP/DOWN)
- **Confusion matrix** (3×3 for multi-class)
- **Majority-class baseline** — accuracy of always predicting FLAT (~55.68%)

### Split Rules (FROZEN, leak-safe)
1. Sort **globally by Date** (NOT by Company) — matches `train_xgboost.py`
2. Last 15% of rows (most recent time window for ALL companies) = **test set** — never touched during training/selection/tuning
3. Remaining 85% → train (85%) / validation (15%), chronological
4. `LabelEncoder` fit on **train only**; transform val/test
5. Threshold tuning / model selection / feature selection use train + validation **only**
6. Test set evaluated **exactly once** at the end

### Honest Results Summary (corrected chronological split)

| Model | Accuracy | MCC | Weighted F1 | Notes |
|---|---|---|---|---|
| Majority class (predict FLAT) | 55.68% | 0.000 | 44.08% | Degenerate baseline |
| Current XGBoost (saved) | 42.86% | 0.073 | 43.91% | Original model |
| Leak-free ExtraTrees | 56.19% | 0.103 | 44.46% | Same spec as 59.85% model |
| ExtraTrees + tuned thresholds | 55.66% | 0.104 | 45.22% | From honest_improve |
| **Soft-voting ensemble** | **55.94%** | **0.119** | **45.77%** | Best honest result |
| Engineered features | 52.90% | — | — | Did not beat baseline |

---

*For the latest status of improvement work, see `improve/TODO.md`. For the full comparison report, see `improve/COMPARISON_REPORT.md`.*

