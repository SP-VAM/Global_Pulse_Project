"""
Model loading, prediction, and feature importance utilities.
"""

import os
import joblib
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# ==========================================================
# MODEL PATHS
# ==========================================================

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(ROOT_DIR, "models")
# Primary production model is the leak-free chronological model (xgboost_model.pkl).
# The leaked improved_model.pkl has been removed.
MODEL_PATH = os.path.join(MODEL_DIR, "xgboost_model.pkl")
LEGACY_MODEL_PATH = os.path.join(MODEL_DIR, "xgboost_model.pkl")
ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")
IMPROVED_ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")
FEATURES_PATH = os.path.join(MODEL_DIR, "model_features.pkl")
IMPROVED_FEATURES_PATH = os.path.join(MODEL_DIR, "model_features.pkl")


def _resolve_existing_path(candidate_paths):
    resolved_paths = []
    for path in candidate_paths:
        if not path:
            continue
        if os.path.isabs(path):
            resolved_paths.append(path)
        else:
            resolved_paths.append(os.path.join(ROOT_DIR, path))

    for path in resolved_paths:
        if os.path.exists(path):
            return path

    return resolved_paths[0] if resolved_paths else None


def load_model(model_path=None):
    """
    Load the trained main model from disk, preferring the improved model.
    """
    candidate_paths = []
    if model_path is not None:
        candidate_paths.append(model_path)
    candidate_paths.extend([MODEL_PATH, LEGACY_MODEL_PATH])

    resolved_path = _resolve_existing_path(candidate_paths)
    if resolved_path is None:
        print(f"Model not found. Checked: {candidate_paths}")
        return None

    try:
        model = joblib.load(resolved_path)
        print(f"Model loaded from {resolved_path}")
        return model
    except Exception as e:
        print(f"Error loading model: {e}")
        return None


def load_label_encoder(encoder_path=None):
    """
    Load the label encoder from disk.
    """
    candidate_paths = []
    if encoder_path is not None:
        candidate_paths.append(encoder_path)
    candidate_paths.extend([IMPROVED_ENCODER_PATH, ENCODER_PATH])

    resolved_path = _resolve_existing_path(candidate_paths)
    if resolved_path is None:
        print(f"Label encoder not found. Checked: {candidate_paths}")
        return None

    try:
        encoder = joblib.load(resolved_path)
        print(f"Label encoder loaded from {resolved_path}")
        return encoder
    except Exception as e:
        print(f"Error loading label encoder: {e}")
        return None


def load_model_features(features_path=None):
    """
    Load the list of feature columns used during training.
    """
    candidate_paths = []
    if features_path is not None:
        candidate_paths.append(features_path)
    candidate_paths.extend([IMPROVED_FEATURES_PATH, FEATURES_PATH])

    resolved_path = _resolve_existing_path(candidate_paths)
    if resolved_path is None:
        print(f"Features file not found. Checked: {candidate_paths}")
        return None

    try:
        features = joblib.load(resolved_path)
        return features
    except Exception as e:
        print(f"Error loading features: {e}")
        return None


def save_model(model, model_path=None):
    """Save a trained model to disk and keep compatibility copies."""
    if model_path is None:
        model_path = MODEL_PATH

    target_paths = []
    if model_path:
        target_paths.append(model_path)
    if os.path.basename(model_path) != os.path.basename(MODEL_PATH):
        target_paths.append(MODEL_PATH)
    if os.path.basename(model_path) != os.path.basename(LEGACY_MODEL_PATH):
        target_paths.append(LEGACY_MODEL_PATH)

    for target in list(dict.fromkeys(target_paths)):
        target_path = target if os.path.isabs(target) else os.path.join(ROOT_DIR, target)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        joblib.dump(model, target_path)
        print(f"Model saved to {target_path}")


def save_label_encoder(encoder, encoder_path=None):
    """Save a label encoder to disk."""
    if encoder_path is None:
        encoder_path = ENCODER_PATH

    target_paths = []
    if encoder_path:
        target_paths.append(encoder_path)
    if os.path.basename(encoder_path) != os.path.basename(ENCODER_PATH):
        target_paths.append(ENCODER_PATH)
    if os.path.basename(encoder_path) != os.path.basename(IMPROVED_ENCODER_PATH):
        target_paths.append(IMPROVED_ENCODER_PATH)

    for target in list(dict.fromkeys(target_paths)):
        target_path = target if os.path.isabs(target) else os.path.join(ROOT_DIR, target)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        joblib.dump(encoder, target_path)
        print(f"Label encoder saved to {target_path}")


def save_model_features(features, features_path=None):
    """Save model feature names to disk."""
    if features_path is None:
        features_path = FEATURES_PATH

    target_paths = []
    if features_path:
        target_paths.append(features_path)
    if os.path.basename(features_path) != os.path.basename(FEATURES_PATH):
        target_paths.append(FEATURES_PATH)
    if os.path.basename(features_path) != os.path.basename(IMPROVED_FEATURES_PATH):
        target_paths.append(IMPROVED_FEATURES_PATH)

    for target in list(dict.fromkeys(target_paths)):
        target_path = target if os.path.isabs(target) else os.path.join(ROOT_DIR, target)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        joblib.dump(features, target_path)
        print(f"Model features saved to {target_path}")


def prepare_prediction_features(
    row,
    feature_cols,
    expected_features=None
):
    """
    Prepare a single row or DataFrame for prediction by selecting 
    and ordering features as the model expects.

    Parameters
    ----------
    row : pd.DataFrame or pd.Series
        Input data with feature columns
    feature_cols : list
        List of feature column names to use
    expected_features : list, optional
        Expected feature order from training (from model_features.pkl)

    Returns
    -------
    pd.DataFrame
        Features ready for model prediction
    """
    if isinstance(row, pd.Series):
        row = row.to_frame().T
    
    # Check which features are available
    available_features = [c for c in feature_cols if c in row.columns]
    
    if len(available_features) == 0:
        print("Warning: No feature columns found in input data.")
        return None
    
    # Select features
    X = row[available_features].copy()
    
    # Fill any remaining NaN values
    X = X.fillna(0)
    
    return X


def predict(model, X):
    """
    Make predictions using the trained model.

    Parameters
    ----------
    model : object
        Trained XGBoost classifier
    X : pd.DataFrame
        Feature matrix

    Returns
    -------
    np.array
        Predicted class labels (0 or 1)
    """
    if model is None:
        print("No model provided for prediction.")
        return None
    return model.predict(X)


def predict_proba(model, X):
    """
    Get prediction probabilities.

    Parameters
    ----------
    model : object
        Trained XGBoost classifier
    X : pd.DataFrame
        Feature matrix

    Returns
    -------
    np.array
        Prediction probabilities [prob_down, prob_up]
    """
    if model is None:
        print("No model provided for prediction.")
        return None
    return model.predict_proba(X)


def get_feature_importance(model, feature_names, top_n=20):
    """
    Get feature importance from the trained model.

    Parameters
    ----------
    model : object
        Trained XGBoost model
    feature_names : list
        List of feature column names
    top_n : int
        Number of top features to return

    Returns
    -------
    pd.DataFrame
        DataFrame with Feature and Importance columns, sorted by importance
    """
    if model is None:
        print("No model provided.")
        return pd.DataFrame()
    
    if hasattr(model, "feature_importances_"):
        importance = model.feature_importances_
    else:
        print("Model does not have feature_importances_ attribute.")
        return pd.DataFrame()
    
    # Create DataFrame
    df = pd.DataFrame({
        "Feature": feature_names,
        "Importance": importance
    })
    
    # Sort by importance (descending)
    df = df.sort_values("Importance", ascending=False).reset_index(drop=True)
    
    return df.head(top_n)


def make_prediction(
    model,
    features_df,
    feature_cols,
    return_proba=True
):
    """
    End-to-end prediction: prepare features, predict, format results.

    Parameters
    ----------
    model : object
        Trained model
    features_df : pd.DataFrame
        Input features
    feature_cols : list
        Feature column names
    return_proba : bool
        Whether to return probabilities as well

    Returns
    -------
    dict or pd.DataFrame
        Prediction results
    """
    X = prepare_prediction_features(features_df, feature_cols)
    
    if X is None:
        return None
    
    preds = predict(model, X)
    
    result = features_df.copy()
    result["Prediction"] = preds
    # Determine if model is binary (2 classes) or multi-class (3 classes)
    n_classes_model = None
    if hasattr(model, "classes_"):
        n_classes_model = len(model.classes_)
    if return_proba:
        _probe = predict_proba(model, X)
        if _probe is not None:
            n_classes_model = _probe.shape[1]
    if n_classes_model == 2:
        # Binary model: 0=DOWN, 1=UP (no FLAT)
        result["Direction"] = result["Prediction"].map({0: "DOWN", 1: "UP"})
    else:
        # Multi-class: 0=DOWN, 1=FLAT, 2=UP
        result["Direction"] = result["Prediction"].map({0: "DOWN", 1: "FLAT", 2: "UP"})
    
    if return_proba:
        proba = predict_proba(model, X)
        if proba.ndim == 2 and proba.shape[1] >= 3:
            result["Prob_DOWN"] = proba[:, 0]
            result["Prob_FLAT"] = proba[:, 1]
            result["Prob_UP"] = proba[:, 2]
        elif proba.ndim == 2 and proba.shape[1] == 2:
            result["Prob_DOWN"] = proba[:, 0]
            result["Prob_UP"] = proba[:, 1]
    
    return result


def get_latest_features_for_company(
    merged_data,
    company_ticker,
    feature_cols
):
    """
    Get the latest feature values for a specific company.

    Parameters
    ----------
    merged_data : pd.DataFrame
        Merged dataset with features
    company_ticker : str
        Company ticker symbol (e.g., "RELIANCE")
    feature_cols : list
        Feature column names

    Returns
    -------
    pd.DataFrame
        Latest features for the company
    """
    # Filter by company
    company_data = merged_data[
        merged_data["Ticker"].str.contains(company_ticker, case=False, na=False)
    ]
    
    if company_data.empty:
        # Try by Company name column
        company_data = merged_data[
            merged_data["Company"].str.contains(company_ticker, case=False, na=False)
        ]
    
    if company_data.empty:
        print(f"No data found for {company_ticker}")
        return None
    
    # Get the latest row
    company_data = company_data.sort_values("Date", ascending=False)
    
    return company_data.head(1)


if __name__ == "__main__":
    # Test model loading
    model = load_model()
    encoder = load_label_encoder()
    features = load_model_features()
    
    print(f"Model loaded: {model is not None}")
    print(f"Encoder loaded: {encoder is not None}")
    print(f"Features loaded: {features is not None}")
    
    if features:
        print(f"Number of features: {len(features)}")
        print(f"Features: {features[:5]}...")

