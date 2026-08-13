"""
CLI prediction script.
Loads the trained model and makes predictions for a given company.
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.prediction import (
    load_model, load_label_encoder, load_model_features,
    make_prediction, get_feature_importance
)
from utils.helper import COMPANY_TO_TICKER, TICKER_TO_COMPANY


def load_prediction_data(merged_data_path="merged_data/merged_dataset.csv"):
    """
    Load the merged dataset for prediction.

    Parameters
    ----------
    merged_data_path : str
        Path to merged dataset CSV

    Returns
    -------
    pd.DataFrame
        Merged dataset
    """
    if not os.path.exists(merged_data_path):
        print(f"Merged dataset not found at {merged_data_path}")
        return None
    return pd.read_csv(merged_data_path, parse_dates=["Date"])


def predict_company(
    company_ticker,
    model,
    label_encoder,
    feature_cols,
    merged_data,
    num_days=5
):
    """
    Make predictions for a specific company.

    Parameters
    ----------
    company_ticker : str
        Company ticker symbol (e.g., "RELIANCE")
    model : object
        Trained model
    label_encoder : LabelEncoder
        Fitted label encoder
    feature_cols : list
        Feature column names
    merged_data : pd.DataFrame
        Merged dataset with features
    num_days : int
        Number of recent days to predict

    Returns
    -------
    pd.DataFrame
        Prediction results
    """
    # Normalize ticker
    company_ticker = company_ticker.upper().replace(".NS", "")
    
    # Get company name
    company_name = TICKER_TO_COMPANY.get(company_ticker, company_ticker)
    
    # Filter data for this company
    company_data = merged_data[
        merged_data["Ticker"].str.contains(company_ticker, case=False, na=False)
    ]
    
    if company_data.empty:
        # Try Company name column
        company_data = merged_data[
            merged_data["Company"].str.contains(company_name, case=False, na=False)
        ]
    
    if company_data.empty:
        print(f"No data found for {company_ticker} ({company_name})")
        return None
    
    # Sort by date descending
    company_data = company_data.sort_values("Date", ascending=False)
    
    # Take the most recent rows
    recent_data = company_data.head(num_days).copy()
    
    # Encode company name
    try:
        company_encoded = label_encoder.transform([company_name])[0]
    except:
        # If company not in encoder, use 0
        company_encoded = 0
    
    # Prepare features
    X = pd.DataFrame()
    for col in feature_cols:
        if col == "Company_Encoded":
            X[col] = [company_encoded] * len(recent_data)
        elif col in recent_data.columns:
            X[col] = recent_data[col].values
        else:
            X[col] = [0] * len(recent_data)
    
    # Handle missing values
    X = X.fillna(0)
    X = X.replace([np.inf, -np.inf], 0)
    
    # Make predictions
    predictions = make_prediction(model, X, feature_cols, return_proba=True)
    
    if predictions is not None:
        predictions["Date"] = recent_data["Date"].values
        predictions["Company"] = company_name
        predictions["Ticker"] = company_ticker
        predictions["Close"] = recent_data["Close"].values if "Close" in recent_data.columns else np.nan
    
    return predictions


def main():
    parser = argparse.ArgumentParser(
        description="Stock Market Prediction CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python predict.py RELIANCE
  python predict.py HDFCBANK --days 10
  python predict.py --list-companies
  python predict.py --feature-importance
  python predict.py --all
        """
    )
    
    parser.add_argument(
        "company",
        nargs="?",
        type=str,
        help="Company ticker symbol (e.g., RELIANCE, HDFCBANK, TCS)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=5,
        help="Number of recent days to predict (default: 5)"
    )
    parser.add_argument(
        "--list-companies",
        action="store_true",
        help="List all available companies"
    )
    parser.add_argument(
        "--feature-importance",
        action="store_true",
        help="Show feature importance from the model"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Make predictions for all companies"
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default="merged_data/merged_dataset.csv",
        help="Path to merged dataset CSV"
    )
    
    args = parser.parse_args()
    
    # List companies
    if args.list_companies:
        print("\nAvailable Companies:")
        print("=" * 50)
        for ticker, name in sorted(TICKER_TO_COMPANY.items()):
            print(f"  {ticker:15s} - {name}")
        return
    
    # Load model and data
    print("Loading model...")
    model = load_model()
    if model is None:
        print("No trained model found. Please run utils/improved_model.py first.")
        return
    
    label_encoder = load_label_encoder()
    feature_cols = load_model_features()
    
    if feature_cols is None:
        print("No feature list found. Using default features.")
        from utils.helper import TECHNICAL_FEATURES
        feature_cols = TECHNICAL_FEATURES + ["Sentiment_Mean", "Company_Encoded", "Year", "Month"]
    
    print("Loading data...")
    merged_data = load_prediction_data(args.data_path)
    if merged_data is None:
        return
    
    print(f"Feature columns ({len(feature_cols)}): {feature_cols}")
    
    # Feature importance
    if args.feature_importance:
        print("\n" + "=" * 50)
        print("FEATURE IMPORTANCE")
        print("=" * 50)
        importance_df = get_feature_importance(model, feature_cols, top_n=20)
        if not importance_df.empty:
            print(importance_df.to_string(index=False))
        return
    
    # Predict for all companies
    if args.all:
        predictions_list = []
        for ticker in TICKER_TO_COMPANY.keys():
            result = predict_company(
                ticker, model, label_encoder,
                feature_cols, merged_data, args.days
            )
            if result is not None:
                predictions_list.append(result)
        
        if predictions_list:
            all_preds = pd.concat(predictions_list, ignore_index=True)
            print("\n" + "=" * 50)
            print("PREDICTIONS FOR ALL COMPANIES")
            print("=" * 50)
            cols = ["Date", "Company", "Ticker", "Close", "Prediction", "Direction", "Prob_UP", "Prob_DOWN"]
            cols = [c for c in cols if c in all_preds.columns]
            print(all_preds[cols].to_string(index=False))
        return
    
    # Predict for a specific company
    if args.company:
        company = args.company.upper()
        print(f"\nMaking predictions for {company}...")
        
        result = predict_company(
            company, model, label_encoder,
            feature_cols, merged_data, args.days
        )
        
        if result is not None:
            print("\n" + "=" * 50)
            print(f"PREDICTIONS FOR {company}")
            print("=" * 50)
            cols = ["Date", "Close", "Prediction", "Direction", "Prob_UP", "Prob_DOWN"]
            cols = [c for c in cols if c in result.columns]
            print(result[cols].to_string(index=False))
            
            # Summary
            up_count = result["Prediction"].sum()
            total = len(result)
            print(f"\nSummary: {up_count}/{total} days predicted UP")
            print(f"         {total - up_count}/{total} days predicted DOWN")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
