"""
Dashboard data loading utilities.
Handles loading merged datasets, fetching live data, and caching.
"""

import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st
import warnings
warnings.filterwarnings("ignore")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.prediction import (
    load_model, load_label_encoder, load_model_features,
    make_prediction, get_feature_importance
)
from utils.helper import TICKER_TO_COMPANY, COMPANY_TO_TICKER
from utils.live_stock import get_live_market_data
from utils.live_news import get_filtered_sentiment_news

# ==========================================================
# DATA PATHS
# ==========================================================

MERGED_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "merged_data/merged_dataset.csv"
)


def load_merged_data():
    """
    Load the merged dataset (historical data for training, no cache).

    Returns
    -------
    pd.DataFrame
        Merged dataset with stock data, indicators, and sentiment
    """
    if not os.path.exists(MERGED_DATA_PATH):
        st.error(f"Merged dataset not found at {MERGED_DATA_PATH}")
        st.info("Please run the preprocessing pipeline first.")
        return pd.DataFrame()
    
    df = pd.read_csv(MERGED_DATA_PATH, parse_dates=["Date"])
    
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    
    return df


def load_live_data(ticker, period="1d", interval="1m"):
    """
    Fetch LIVE stock data on every call (no caching).
    Uses NSE API with Yahoo Finance fallback for accuracy.

    Parameters
    ----------
    ticker : str
        Yahoo Finance ticker symbol (e.g., "RELIANCE.NS")
    period : str, unused
        Kept for backwards compatibility
    interval : str, unused
        Kept for backwards compatibility

    Returns
    -------
    dict
        Live market data with current_price, open, high, low, volume, etc.
    """
    return get_live_market_data(ticker)


def load_live_dataframe(ticker, period="1mo", interval="1d"):
    """
    Fetch live stock data as DataFrame for charting.
    Cached briefly for chart stability.

    Parameters
    ----------
    ticker : str
        Yahoo Finance ticker symbol
    period : str
        Period to fetch
    interval : str
        Data interval

    Returns
    -------
    pd.DataFrame
        Live stock data
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        if not df.empty:
            df.reset_index(inplace=True)
            df["Ticker"] = ticker.replace(".NS", "")
            return df
    except Exception:
        pass
    return pd.DataFrame()


def load_news_sentiment():
    """
    Load aggregated historical news sentiment data.

    Returns
    -------
    pd.DataFrame
        Aggregated news sentiment from historical data
    """
    news_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "merged_data/news_sentiment_aggregated.csv"
    )
    if os.path.exists(news_path):
        df = pd.read_csv(news_path, parse_dates=["Date"])
        return df
    return pd.DataFrame()


def load_live_news_sentiment(company_ticker=None):
    """
    Fetch, filter, and analyze live news sentiment via NewsAPI.

    Parameters
    ----------
    company_ticker : str, optional
        Company ticker to focus on

    Returns
    -------
    pd.DataFrame
        Live news with sentiment analysis
    """
    return get_filtered_sentiment_news(company_ticker, max_articles=30)


@st.cache_resource
def get_models():
    """
    Load trained model, label encoder, and feature columns.

    Returns
    -------
    tuple
        (model, label_encoder, feature_cols)
    """
    model = load_model()
    le = load_label_encoder()
    features = load_model_features()
    return model, le, features


@st.cache_resource
def get_horizon_models(horizon="1d", target_type="binary"):
    """
    Load a horizon-specific model, encoder, and features.

    Parameters
    ----------
    horizon : str
        '1d', '5d', or '10d'
    target_type : str
        'binary' (UP/DOWN) — the FLAT/HOLD class is not used.

    Returns
    -------
    tuple
        (model, label_encoder, feature_cols, metrics)
    """
    import joblib
    import json
    models_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_dir = os.path.join(models_dir, "models")

    # For 10D binary, prefer the sector-enhanced model (best result)
    suffix = f"{horizon}_{target_type}"
    if horizon == "10d" and target_type == "binary":
        sector_path = os.path.join(models_dir, "model_10d_binary_sector.pkl")
        if os.path.exists(sector_path):
            model = joblib.load(sector_path)
            features = joblib.load(os.path.join(models_dir, "model_10d_binary_sector_features.pkl"))
            le = joblib.load(os.path.join(models_dir, "model_10d_binary_sector_encoder.pkl"))
            with open(os.path.join(models_dir, "model_10d_binary_sector_metrics.json")) as f:
                metrics = json.load(f)
            return model, le, features, metrics

    model_path = os.path.join(models_dir, f"model_{suffix}.pkl")
    feat_path = os.path.join(models_dir, f"model_{suffix}_features.pkl")
    enc_path = os.path.join(models_dir, f"model_{suffix}_encoder.pkl")
    met_path = os.path.join(models_dir, f"model_{suffix}_metrics.json")

    model = None
    le = None
    features = None
    metrics = None

    if os.path.exists(model_path):
        model = joblib.load(model_path)
    if os.path.exists(feat_path):
        features = joblib.load(feat_path)
    if os.path.exists(enc_path):
        le = joblib.load(enc_path)
    if os.path.exists(met_path):
        with open(met_path) as f:
            metrics = json.load(f)

    return model, le, features, metrics


def get_company_list():
    """
    Get the list of available companies for the dropdown.

    Returns
    -------
    list
        List of company ticker symbols
    """
    return sorted(TICKER_TO_COMPANY.keys())


def get_company_data(df, company_ticker):
    """
    Filter merged data for a specific company.

    Parameters
    ----------
    df : pd.DataFrame
        Merged dataset
    company_ticker : str
        Company ticker symbol

    Returns
    -------
    pd.DataFrame
        Data for the specified company, sorted by date
    """
    company_ticker = company_ticker.upper().replace(".NS", "")
    
    company_df = df[df["Ticker"].str.contains(company_ticker, case=False, na=False)]
    
    if company_df.empty:
        company_name = TICKER_TO_COMPANY.get(company_ticker, "")
        company_df = df[df["Company"].str.contains(company_name, case=False, na=False)]
    
    if not company_df.empty:
        company_df = company_df.sort_values("Date")
    
    return company_df


def get_latest_data_for_prediction(company_df, feature_cols, label_encoder):
    """
    Get the latest data point for making a prediction.

    Parameters
    ----------
    company_df : pd.DataFrame
        Company-specific data
    feature_cols : list
        Feature column names
    label_encoder : LabelEncoder
        Fitted label encoder

    Returns
    -------
    pd.DataFrame
        Single row of features ready for prediction
    """
    if company_df.empty:
        return None
    
    latest = company_df.iloc[-1:].copy()
    
    X = pd.DataFrame()
    for col in feature_cols:
        if col == "Company_Encoded":
            company_name = latest["Company"].values[0]
            try:
                X[col] = [label_encoder.transform([company_name])[0]]
            except:
                X[col] = [0]
        elif col in latest.columns:
            X[col] = latest[col].values
        else:
            X[col] = [0]
    
    X = X.fillna(0)
    X = X.replace([np.inf, -np.inf], 0)
    
    return X


def get_ticker_symbol(company_ticker):
    """
    Get the full Yahoo Finance ticker symbol.

    Parameters
    ----------
    company_ticker : str
        Company ticker (e.g., "RELIANCE")

    Returns
    -------
    str
        Full Yahoo Finance ticker (e.g., "RELIANCE.NS")
    """
    company_ticker = company_ticker.upper().replace(".NS", "")
    return f"{company_ticker}.NS"

