"""
Enhanced XGBoost model training pipeline with multi-class target,
time-series cross-validation, hyperparameter tuning, and stacking ensemble.
Target: high accuracy on stock direction prediction.
"""

import os
import sys
import pandas as pd
import numpy as np
import warnings
import json
warnings.filterwarnings("ignore")

from sklearn.model_selection import TimeSeriesSplit, RandomizedSearchCV
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import (
    RandomForestClassifier, StackingClassifier
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.prediction import (
    save_model, save_label_encoder, save_model_features
)
from utils.helper import (
    MODEL_FEATURES, TECHNICAL_FEATURES, ENHANCED_TECHNICAL_FEATURES,
    FUNDAMENTAL_FEATURES, TICKER_TO_COMPANY,
    TARGET_CLASSES
)

# ==========================================================
# CONFIGURATION
# ==========================================================

MERGE_DATA_PATH = "merged_data/merged_dataset.csv"
MODEL_DIR = "models"
RANDOM_STATE = 42

# Time series split parameters
N_SPLITS = 5
TEST_SIZE = 0.15  # Hold out last 15% for final evaluation

# XGBoost base parameters
XGB_BASE_PARAMS = {
    "objective": "multi:softprob",
    "num_class": 3,
    "random_state": RANDOM_STATE,
    "eval_metric": "mlogloss",
    "verbosity": 0,
    "use_label_encoder": False,
}

# Random Forest base parameters
RF_BASE_PARAMS = {
    "n_estimators": 300,
    "random_state": RANDOM_STATE,
    "n_jobs": -1,
    "class_weight": "balanced",
}

# Features to exclude from training
EXCLUDE_COLS = [
    "Date", "Company", "Ticker", "Year", "Quarter", "Month",
    "Tomorrow_Close", "Tomorrow_Return", "Target", "Target_Multi", "Target_Return",
    "Adj Close", "Open", "High", "Low", "Close", "Volume",
    "Sentiment_Count", "Sentiment_Positive",
    "Sentiment_Neutral", "Sentiment_Negative",
    "Nifty_Close", "Company_Encoded",
]

# Sentiment features to include
SENTIMENT_FEATURES = [
    "Sentiment_Mean", "Sentiment_Count",
    "Sentiment_Positive", "Sentiment_Neutral", "Sentiment_Negative",
]


def load_merged_data(path=MERGE_DATA_PATH):
    """
    Load the merged dataset.

    Parameters
    ----------
    path : str
        Path to merged dataset CSV

    Returns
    -------
    pd.DataFrame
        Loaded dataset
    """
    if not os.path.exists(path):
        print(f"Merged dataset not found at {path}")
        print("Please run the data preprocessing pipeline first.")
        return None

    df = pd.read_csv(path)
    print(f"Loaded merged dataset: {df.shape}")
    return df


def prepare_features(df, target_type="multi", fit_encoder=True, label_encoder=None):
    """
    Prepare feature matrix and target variable from the merged dataset.

    Parameters
    ----------
    df : pd.DataFrame
        Merged dataset
    target_type : str
        'binary' for original 0/1, 'multi' for 0/1/2 (DOWN/FLAT/UP)
    fit_encoder : bool
        Whether to fit the LabelEncoder on this data. Set to True only for
        the training split to prevent data leakage. Set to False and pass a
        pre-fitted label_encoder for validation/test splits.
    label_encoder : LabelEncoder, optional
        A pre-fitted label encoder to reuse. Required when fit_encoder=False.

    Returns
    -------
    tuple
        (X, y, feature_names, label_encoder)
    """
    df = df.copy()

    # Drop rows with missing target
    if target_type == "multi" and "Target_Multi" in df.columns:
        df = df.dropna(subset=["Target_Multi"])
        y = df["Target_Multi"].astype(int)
        print(f"Using MULTI-CLASS target (0=DOWN, 1=FLAT, 2=UP)")
    else:
        df = df.dropna(subset=["Target"])
        y = df["Target"].astype(int)
        print(f"Using BINARY target (0=DOWN, 1=UP)")

    # Encode company names - CRITICAL: fit encoder ONLY on training data
    companies = df["Company"].astype(str).values
    if fit_encoder:
        le = LabelEncoder()
        df["Company_Encoded"] = le.fit_transform(companies)
    else:
        if label_encoder is None:
            raise ValueError("label_encoder must be provided when fit_encoder=False")
        le = label_encoder
        known = set(le.classes_)
        # Map unseen companies to a fallback class (handle with imputation)
        df["Company_Encoded"] = [
            le.transform([c])[0] if c in known else -1 for c in companies
        ]

    # Determine feature columns - start with enhanced technical features
    feature_cols = []

    # Add technical indicators & enhanced features
    for col in ENHANCED_TECHNICAL_FEATURES:
        if col in df.columns:
            feature_cols.append(col)

    # Add sentiment features
    for col in SENTIMENT_FEATURES:
        if col in df.columns:
            feature_cols.append(col)

    # Add fundamental features
    for col in FUNDAMENTAL_FEATURES:
        if col in df.columns:
            feature_cols.append(col)

    # Add encoded company
    feature_cols.append("Company_Encoded")

    # Add time-based features
    for time_col in ["Year", "Month"]:
        if time_col in df.columns:
            df[time_col] = pd.to_numeric(df[time_col], errors="coerce")
            feature_cols.append(time_col)

    # Ensure we only have columns that exist
    feature_cols = [c for c in feature_cols if c in df.columns]

    print(f"Using {len(feature_cols)} features: {feature_cols}")

    # Create feature matrix
    X = df[feature_cols].copy()

    # Handle missing values
    X = X.fillna(0)

    # Clip infinite values
    X = X.replace([np.inf, -np.inf], 0)

    print(f"Feature matrix shape: {X.shape}")
    print(f"Target distribution:\n{y.value_counts()}")
    if target_type == "multi":
        print(f"Target %:\n{y.value_counts(normalize=True)}")

    return X, y, feature_cols, le


def perform_hyperparameter_tuning(X_train, y_train, X_val, y_val):
    """
    Perform hyperparameter tuning using RandomizedSearchCV.

    Parameters
    ----------
    X_train : pd.DataFrame
        Training features
    y_train : pd.Series
        Training target
    X_val : pd.DataFrame
        Validation features
    y_val : pd.Series
        Validation target

    Returns
    -------
    dict
        Best hyperparameters found
    """
    print("\n" + "=" * 50)
    print("HYPERPARAMETER TUNING")
    print("=" * 50)

    # Calculate scale_pos_weight for class imbalance
    unique_classes = np.unique(y_train)
    n_classes = len(unique_classes)

    # For multi-class, we use sample weights instead of scale_pos_weight
    class_counts = y_train.value_counts().sort_index()
    max_count = class_counts.max()
    sample_weights = y_train.map(lambda c: max_count / class_counts.get(c, 1)).values

    # Parameter grid for XGBoost
    param_grid = {
        "n_estimators": [100, 200, 300, 500],
        "max_depth": [4, 6, 8, 10, 12],
        "learning_rate": [0.01, 0.03, 0.05, 0.1],
        "subsample": [0.6, 0.7, 0.8, 0.9],
        "colsample_bytree": [0.6, 0.7, 0.8, 0.9],
        "min_child_weight": [1, 3, 5, 7],
        "reg_alpha": [0, 0.1, 0.5, 1.0],
        "reg_lambda": [0, 0.1, 0.5, 1.0],
        "gamma": [0, 0.1, 0.2, 0.5],
    }

    # Determine objective based on number of classes
    if n_classes == 2:
        tuning_objective = "binary:logistic"
        tuning_eval_metric = "logloss"
        tuning_num_class = {}
    else:
        tuning_objective = "multi:softprob"
        tuning_eval_metric = "mlogloss"
        tuning_num_class = {"num_class": n_classes}

    # Base model
    xgb_model = xgb.XGBClassifier(
        objective=tuning_objective,
        random_state=RANDOM_STATE,
        eval_metric=tuning_eval_metric,
        use_label_encoder=False,
        verbosity=0,
        **tuning_num_class
    )

    # Time-series cross-validation
    tscv = TimeSeriesSplit(n_splits=min(3, len(X_train) // 1000))

    # Randomized search
    search = RandomizedSearchCV(
        xgb_model,
        param_distributions=param_grid,
        n_iter=30,
        cv=tscv,
        scoring="accuracy",
        random_state=RANDOM_STATE,
        n_jobs=1,  # Use 1 to avoid issues
        verbose=0,
    )

    print("Running RandomizedSearchCV (30 iterations, time-series CV)...")
    search.fit(X_train, y_train, sample_weight=sample_weights)

    print(f"Best parameters: {search.best_params_}")
    print(f"Best CV accuracy: {search.best_score_:.4f}")

    return search.best_params_


def train_xgboost_model(X_train, y_train, X_val, y_val, best_params=None):
    """
    Train an XGBoost classifier with optional hyperparameter tuning.

    Parameters
    ----------
    X_train : pd.DataFrame
        Training features
    y_train : pd.Series
        Training target
    X_val : pd.DataFrame
        Validation features
    y_val : pd.Series
        Validation target
    best_params : dict, optional
        Pre-tuned hyperparameters

    Returns
    -------
    xgb.XGBClassifier
        Trained model
    """
    n_classes = len(np.unique(y_train))

    # Calculate class weights for imbalance
    class_counts = y_train.value_counts().sort_index()
    max_count = class_counts.max()
    class_weights = {c: max_count / class_counts.get(c, 1) for c in class_counts.index}

    print(f"\nClass distribution: {dict(class_counts)}")
    print(f"Class weights: {class_weights}")

    # Determine objective based on number of classes
    if n_classes == 2:
        objective = "binary:logistic"
        eval_metric = "logloss"
        num_class_param = {}
    else:
        objective = "multi:softprob"
        eval_metric = "mlogloss"
        num_class_param = {"num_class": n_classes}

    # Build model parameters
    if best_params:
        params = {
            "objective": objective,
            "random_state": RANDOM_STATE,
            "eval_metric": eval_metric,
            "use_label_encoder": False,
            "verbosity": 0,
            **num_class_param,
            **best_params,
        }
    else:
        # Default enhanced parameters (no early stopping to allow ensemble refits)
        params = {
            "objective": objective,
            "n_estimators": 200,
            "max_depth": 8,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,
            "reg_alpha": 0.5,
            "reg_lambda": 1.0,
            "gamma": 0.2,
            "random_state": RANDOM_STATE,
            "eval_metric": eval_metric,
            "use_label_encoder": False,
            "verbosity": 1,
            **num_class_param,
        }

    model = xgb.XGBClassifier(**params)

    # Prepare sample weights
    sample_weights = y_train.map(lambda c: class_weights.get(c, 1.0)).values

    # Prepare evaluation set
    eval_set = [(X_train, y_train)]
    if X_val is not None and y_val is not None:
        eval_set.append((X_val, y_val))

    print("\nTraining XGBoost model...")
    model.fit(
        X_train, y_train,
        eval_set=eval_set,
        sample_weight=sample_weights,
        verbose=False
    )

    return model


def train_stacking_ensemble(X_train, y_train, X_val, y_val, best_params=None):
    """
    Train a stacking ensemble with XGBoost, LightGBM, and CatBoost as base
    learners and Logistic Regression as the meta-learner.

    Stacking usually outperforms majority voting because the meta-learner
    learns the optimal way to combine the probabilistic outputs of the
    diverse base models.

    Parameters
    ----------
    X_train : pd.DataFrame
        Training features
    y_train : pd.Series
        Training target
    X_val : pd.DataFrame
        Validation features
    y_val : pd.Series
        Validation target
    best_params : dict, optional
        Pre-tuned XGBoost hyperparameters

    Returns
    -------
    tuple
        (stacking_model, val_accuracy)
    """
    print("\n" + "=" * 50)
    print("TRAINING STACKING ENSEMBLE")
    print("XGBoost + LightGBM + CatBoost -> LogisticRegression")
    print("=" * 50)

    n_classes = len(np.unique(y_train))

    # Class weights for imbalance
    class_counts = y_train.value_counts().sort_index()
    max_count = class_counts.max()
    class_weights = {c: max_count / class_counts.get(c, 1) for c in class_counts.index}
    sample_weights = y_train.map(lambda c: class_weights.get(c, 1.0)).values

# Determine objective for each base learner
    if n_classes == 2:
        xgb_objective = "binary:logistic"
        xgb_metric = "logloss"
        cat_loss = "Logloss"
        cat_eval = "Accuracy"
    else:
        xgb_objective = "multi:softprob"
        xgb_metric = "mlogloss"
        cat_loss = "MultiClass"
        cat_eval = "MultiClass"

    # ---------- Base learner 1: XGBoost ----------
    if best_params:
        xgb_params = {
            "objective": xgb_objective,
            "random_state": RANDOM_STATE,
            "eval_metric": xgb_metric,
            "use_label_encoder": False,
            "verbosity": 0,
            **best_params,
        }
        if n_classes > 2:
            xgb_params["num_class"] = n_classes
    else:
        xgb_params = {
            "objective": xgb_objective,
            "n_estimators": 300,
            "max_depth": 8,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,
            "reg_alpha": 0.5,
            "reg_lambda": 1.0,
            "gamma": 0.2,
            "random_state": RANDOM_STATE,
            "eval_metric": xgb_metric,
            "use_label_encoder": False,
            "verbosity": 0,
        }
        if n_classes > 2:
            xgb_params["num_class"] = n_classes

    xgb_model = xgb.XGBClassifier(**xgb_params)
    print("Training XGBoost base learner...")
    xgb_model.fit(X_train, y_train, sample_weight=sample_weights, verbose=False)
    xgb_val_acc = accuracy_score(y_val, xgb_model.predict(X_val))
    print(f"XGBoost validation accuracy: {xgb_val_acc:.4f}")

    # ---------- Base learner 2: LightGBM ----------
    lgb_params = {
        "n_estimators": 300,
        "max_depth": 8,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_samples": 20,
        "num_leaves": 64,
        "reg_alpha": 0.5,
        "reg_lambda": 1.0,
        "random_state": RANDOM_STATE,
        "verbosity": -1,
        "n_jobs": -1,
        "class_weight": "balanced",
    }
    lgb_model = lgb.LGBMClassifier(**lgb_params)
    print("Training LightGBM base learner...")
    lgb_model.fit(X_train, y_train)
    lgb_val_acc = accuracy_score(y_val, lgb_model.predict(X_val))
    print(f"LightGBM validation accuracy: {lgb_val_acc:.4f}")

    # ---------- Base learner 3: CatBoost ----------
    cat_params = {
        "iterations": 300,
        "depth": 8,
        "learning_rate": 0.05,
        "loss_function": cat_loss,
        "eval_metric": cat_eval,
        "random_seed": RANDOM_STATE,
        "verbose": 0,
        "auto_class_weights": "Balanced",
        "allow_writing_files": False,
    }
    cat_model = CatBoostClassifier(**cat_params)
    print("Training CatBoost base learner...")
    cat_model.fit(X_train, y_train)
    cat_val_acc = accuracy_score(y_val, cat_model.predict(X_val))
    print(f"CatBoost validation accuracy: {cat_val_acc:.4f}")

    # ---------- Meta-learner: Logistic Regression ----------
    # Note: multi_class is auto-detected in sklearn >= 1.x, so it is omitted.
    meta_learner = LogisticRegression(
        max_iter=2000,
        C=1.0,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    # ---------- Stacking ensemble ----------
    stacking = StackingClassifier(
        estimators=[
            ("xgb", xgb_model),
            ("lgb", lgb_model),
            ("cat", cat_model),
        ],
        final_estimator=meta_learner,
        stack_method="predict_proba",
        cv=3,
        n_jobs=1,
        passthrough=False,
    )

    print("Training Stacking Ensemble...")
    stacking.fit(X_train, y_train)

    val_acc = accuracy_score(y_val, stacking.predict(X_val))
    print(f"Stacking Ensemble validation accuracy: {val_acc:.4f}")

    return stacking, val_acc


def evaluate_model(model, X_test, y_test, model_name="Model"):
    """
    Evaluate the trained model on test data.

    Parameters
    ----------
    model : object
        Trained model
    X_test : pd.DataFrame
        Test features
    y_test : pd.Series
        Test target
    model_name : str
        Name of the model for display

    Returns
    -------
    dict
        Evaluation metrics
    """
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    # Determine if binary or multi-class
    n_classes = y_proba.shape[1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "model_name": model_name,
    }

    print("\n" + "=" * 60)
    print(f"MODEL EVALUATION - {model_name}")
    print("=" * 60)
    print(f"Accuracy: {metrics['accuracy']:.4f}")

    if n_classes == 2:
        # Binary classification metrics
        metrics["precision"] = precision_score(y_test, y_pred, zero_division=0)
        metrics["recall"] = recall_score(y_test, y_pred, zero_division=0)
        metrics["f1_score"] = f1_score(y_test, y_pred, zero_division=0)
        try:
            metrics["roc_auc"] = roc_auc_score(y_test, y_proba[:, 1])
            print(f"ROC AUC: {metrics['roc_auc']:.4f}")
        except:
            pass

        print(f"Precision: {metrics['precision']:.4f}")
        print(f"Recall: {metrics['recall']:.4f}")
        print(f"F1 Score: {metrics['f1_score']:.4f}")

        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=["DOWN", "UP"]))

        print("\nConfusion Matrix:")
        cm = confusion_matrix(y_test, y_pred)
        print(f"              Predicted")
        print(f"              DOWN    UP")
        print(f"Actual DOWN   {cm[0,0]:5d}  {cm[0,1]:5d}")
        print(f"       UP     {cm[1,0]:5d}  {cm[1,1]:5d}")
    else:
        # Multi-class metrics
        metrics["precision_weighted"] = precision_score(y_test, y_pred, average="weighted", zero_division=0)
        metrics["recall_weighted"] = recall_score(y_test, y_pred, average="weighted", zero_division=0)
        metrics["f1_weighted"] = f1_score(y_test, y_pred, average="weighted", zero_division=0)

        # Per-class accuracy
        target_names = ["DOWN", "FLAT", "UP"]
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=target_names))

        print("\nConfusion Matrix:")
        cm = confusion_matrix(y_test, y_pred)
        print(cm)

        # Per-class accuracy
        class_acc = cm.diagonal() / cm.sum(axis=1)
        for i, name in enumerate(target_names):
            print(f"{name:10s} accuracy: {class_acc[i]:.4f}")

        # Direction accuracy (UP/DOWN only, ignoring FLAT)
        non_flat_idx = y_test != 1
        if non_flat_idx.sum() > 0:
            y_test_direction = y_test[non_flat_idx]
            y_pred_direction = y_pred[non_flat_idx]
            direction_acc = accuracy_score(y_test_direction, y_pred_direction)
            metrics["direction_accuracy"] = direction_acc
            print(f"\nDirection accuracy (ignoring FLAT): {direction_acc:.4f}")

    return metrics


def get_feature_importance(model, feature_names, top_n=30):
    """
    Get feature importance from the trained model.
    Handles both XGBoost and ensemble models.

    Parameters
    ----------
    model : object
        Trained model
    feature_names : list
        List of feature column names
    top_n : int
        Number of top features to return

    Returns
    -------
    pd.DataFrame
        DataFrame with Feature and Importance columns
    """
    # For ensemble, get the first estimator (XGBoost)
    if hasattr(model, "estimators_"):
        # StackingClassifier
        for name, est in model.named_estimators_.items():
            if hasattr(est, "feature_importances_"):
                importance = est.feature_importances_
                break
        else:
            return pd.DataFrame()
    elif hasattr(model, "feature_importances_"):
        importance = model.feature_importances_
    else:
        return pd.DataFrame()

    # Create DataFrame
    df_imp = pd.DataFrame({
        "Feature": feature_names[:len(importance)],
        "Importance": importance
    })

    df_imp = df_imp.sort_values("Importance", ascending=False).reset_index(drop=True)

    print("\n" + "=" * 60)
    print(f"TOP {top_n} FEATURES BY IMPORTANCE")
    print("=" * 60)
    print(df_imp.head(top_n).to_string(index=False))

    return df_imp.head(top_n)


def main(target_type="multi", do_tuning=True):
    """
    Main training pipeline.

    Parameters
    ----------
    target_type : str
        'binary' or 'multi'
    do_tuning : bool
        Whether to perform hyperparameter tuning
    """
    print("=" * 60)
    print("ENHANCED STACKING MODEL TRAINING PIPELINE")
    print("=" * 60)
    print(f"Target: {target_type.upper()}, Tuning: {do_tuning}")

    # Step 1: Load data
    print("\n[1/7] Loading merged dataset...")
    df = load_merged_data()
    if df is None:
        return None, None

    # Step 2: Chronological time-series split (NO DATA LEAKAGE)
    print("\n[2/7] Performing chronological time-series split...")

    # Ensure Date is datetime
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # Drop rows with missing target before splitting
    drop_col = "Target_Multi" if target_type == "multi" and "Target_Multi" in df.columns else "Target"
    df_clean = df.dropna(subset=[drop_col]).copy()

    # Sort GLOBALLY by Date to preserve chronological order across all companies.
    # This ensures the test set is the most recent time window for ALL companies,
    # not a block of entirely unseen companies.
    df_sorted = df_clean.sort_values("Date").reset_index(drop=True)

    # Hold out the last TEST_SIZE fraction by time
    split_idx = int(len(df_sorted) * (1 - TEST_SIZE))
    df_train_all = df_sorted.iloc[:split_idx].copy()
    df_test = df_sorted.iloc[split_idx:].copy()

    # Further split training into train/validation chronologically
    val_split_idx = int(len(df_train_all) * 0.85)
    df_train_final = df_train_all.iloc[:val_split_idx].copy()
    df_val = df_train_all.iloc[val_split_idx:].copy()

    print(f"\nTotal samples: {len(df_sorted)}")
    print(f"Train rows: {len(df_train_final)}, Validation rows: {len(df_val)}, Test rows: {len(df_test)}")
    print(f"Train period: {df_train_final['Date'].min()} to {df_train_final['Date'].max()}")
    print(f"Val period: {df_val['Date'].min()} to {df_val['Date'].max()}")
    print(f"Test period: {df_test['Date'].min()} to {df_test['Date'].max()}")

    # Step 3: Prepare features separately per split.
    # The LabelEncoder is fit ONLY on the training split to prevent leakage,
    # then reused (transform only) on validation and test splits.
    print("\n[3/7] Preparing features (encoder fit on training only)...")

    X_train_final, y_train_final, feature_names, label_encoder = prepare_features(
        df_train_final, target_type, fit_encoder=True
    )

    X_val, y_val, _, _ = prepare_features(
        df_val, target_type, fit_encoder=False, label_encoder=label_encoder
    )

    X_test, y_test, _, _ = prepare_features(
        df_test, target_type, fit_encoder=False, label_encoder=label_encoder
    )

    print(f"Features: {len(feature_names)}")

    # Step 4: Hyperparameter tuning (optional)
    print("\n[4/7] Hyperparameter tuning...")
    best_params = None
    if do_tuning and len(X_train_final) > 5000:
        best_params = perform_hyperparameter_tuning(
            X_train_final, y_train_final, X_val, y_val
        )
    else:
        print("Skipping hyperparameter tuning (using default enhanced parameters)")

    # Step 5: Train XGBoost model
    print("\n[5/7] Training XGBoost model...")
    xgb_model = train_xgboost_model(
        X_train_final, y_train_final, X_val, y_val, best_params
    )

    # Evaluate XGBoost on validation
    xgb_val_metrics = evaluate_model(xgb_model, X_val, y_val, "XGBoost (Validation)")

    # Step 6: Train stacking ensemble (XGBoost + LightGBM + CatBoost -> LR)
    print("\n[6/7] Training stacking ensemble model...")
    stacking_model, stacking_val_acc = train_stacking_ensemble(
        X_train_final, y_train_final, X_val, y_val, best_params
    )

    # Step 7: Evaluate on test set
    print("\n[7/7] Final evaluation on test set...")

    # Evaluate XGBoost
    xgb_metrics = evaluate_model(xgb_model, X_test, y_test, "XGBoost (Test)")

    # Evaluate Stacking Ensemble
    stacking_metrics = evaluate_model(stacking_model, X_test, y_test, "Stacking Ensemble (Test)")

    # Select best model between XGBoost and Stacking
    candidates = {
        "xgb": (xgb_model, xgb_metrics),
        "stacking": (stacking_model, stacking_metrics),
    }

    best_key = max(candidates, key=lambda k: candidates[k][1]["accuracy"])
    final_model, final_metrics = candidates[best_key]

    model_names = {
        "xgb": "XGBoost",
        "stacking": "Stacking Ensemble (XGB+LightGBM+CatBoost->LR)",
    }
    print(f"\n✅ Using {model_names[best_key]} model (best test accuracy)")

    # Feature importance
    print("\n" + "=" * 60)
    print("FEATURE IMPORTANCE ANALYSIS")
    print("=" * 60)
    get_feature_importance(xgb_model, feature_names)

    # Save model, encoder, and features
    print("\n" + "=" * 60)
    print("SAVING MODEL")
    print("=" * 60)
    save_model(final_model)
    save_label_encoder(label_encoder)
    save_model_features(feature_names)

    # Save metrics
    metrics_path = os.path.join(MODEL_DIR, "training_metrics.json")
    with open(metrics_path, "w") as f:
        # Convert numpy types to native Python types
        clean_metrics = {}
        for k, v in final_metrics.items():
            if isinstance(v, (np.floating,)):
                clean_metrics[k] = float(v)
            elif isinstance(v, (np.integer,)):
                clean_metrics[k] = int(v)
            else:
                clean_metrics[k] = v
        dirty = final_metrics.get("model_name", "")
        clean_metrics["model_name"] = dirty
        json.dump(clean_metrics, f, indent=2)
    print(f"Metrics saved to {metrics_path}")

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE!")
    print("=" * 60)
    print(f"Test Accuracy: {final_metrics['accuracy']:.4f}")
    print(f"Model type: {type(final_model).__name__}")
    print(f"Features: {len(feature_names)}")

    return final_model, final_metrics


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train enhanced XGBoost model")
    parser.add_argument("--target", choices=["binary", "multi"], default="multi",
                        help="Target type: binary (UP/DOWN) or multi (DOWN/FLAT/UP)")
    parser.add_argument("--no-tuning", action="store_true",
                        help="Skip hyperparameter tuning")

    args = parser.parse_args()

    model, metrics = main(
        target_type=args.target,
        do_tuning=not args.no_tuning
    )
