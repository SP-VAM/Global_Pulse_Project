"""
Helper functions and constants for the Stock Market Prediction project.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ==========================================================
# NIFTY INDEX TICKER
# ==========================================================

NIFTY_TICKER = "^NSEI"
NIFTY_TICKER_BS = "NIFTY_50"  # For individual stock downloads as fallback

# ==========================================================
# COMPANY MAPPINGS
# ==========================================================

# Maps Yahoo Finance ticker symbol -> Company Name
TICKER_TO_COMPANY = {
    "ADANIENT": "Adani Enterprises Ltd",
    "ADANIPORTS": "Adani Ports & Special Economic Zone Ltd",
    "APOLLOHOSP": "Apollo Hospitals Enterprise Ltd",
    "ASIANPAINT": "Asian Paints Ltd",
    "AXISBANK": "Axis Bank Ltd",
    "BAJAJ-AUTO": "Bajaj Auto Ltd",
    "BAJFINANCE": "Bajaj Finance Ltd",
    "BAJAJFINSV": "Bajaj Finserv Ltd",
    "BHARTIARTL": "Bharti Airtel Ltd",
    "BEL": "Bharat Electronics Ltd",
    "CIPLA": "Cipla Ltd",
    "COALINDIA": "Coal India Ltd",
    "DRREDDY": "Dr. Reddy's Laboratories Ltd",
    "EICHERMOT": "Eicher Motors Ltd",
    "GRASIM": "Grasim Industries Ltd",
    "HCLTECH": "HCL Technologies Ltd",
    "HDFCBANK": "HDFC Bank Ltd",
    "HDFCLIFE": "HDFC Life Insurance Ltd",
    "HEROMOTOCO": "Hero MotoCorp Ltd",
    "HINDUNILVR": "Hindustan Unilever Ltd",
    "HINDALCO": "Hindalco Industries Ltd",
    "ICICIBANK": "ICICI Bank Ltd",
    "INDUSINDBK": "IndusInd Bank Ltd",
    "INFY": "Infosys Ltd",
    "ITC": "ITC Ltd",
    "JSWSTEEL": "JSW Steel Ltd",
    "KOTAKBANK": "Kotak Mahindra Bank Ltd",
    "LT": "Larsen & Toubro Ltd",
    "M&M": "Mahindra & Mahindra Ltd",
    "MARUTI": "Maruti Suzuki India Ltd",
    "NTPC": "NTPC Ltd",
    "ONGC": "Oil & Natural Gas Corporation Ltd",
    "POWERGRID": "Power Grid Corporation of India Ltd",
    "RELIANCE": "Reliance Industries Ltd",
    "SBIN": "State Bank of India",
    "SHRIRAMFIN": "Shriram Finance Ltd",
    "SUNPHARMA": "Sun Pharmaceutical Industries Ltd",
    "TCS": "Tata Consultancy Services Ltd",
    "TATACONSUM": "Tata Consumer Products Ltd",
    "TATASTEEL": "Tata Steel Ltd",
    "TECHM": "Tech Mahindra Ltd",
    "TITAN": "Titan Company Ltd",
    "TRENT": "Trent Ltd",
    "ULTRACEMCO": "UltraTech Cement Ltd",
    "WIPRO": "Wipro Ltd",
    "NESTLEIND": "Nestle India Ltd",
    "SBILIFE": "SBI Life Insurance Ltd",
    "ETERNAL": "Eternal Ltd",
    "JIOFIN": "Jio Financial Services Ltd",
}

# Reverse mapping: Company Name -> Ticker
COMPANY_TO_TICKER = {v: k for k, v in TICKER_TO_COMPANY.items()}

# ==========================================================
# FEATURE COLUMNS - ENHANCED
# ==========================================================

# Price-based features
PRICE_FEATURES = [
    "Open", "High", "Low", "Close", "Volume", "Adj Close"
]

# Original technical indicator features
TECHNICAL_FEATURES = [
    "SMA20", "SMA50", "EMA20", "EMA50",
    "RSI",
    "MACD", "MACD_SIGNAL", "MACD_HIST",
    "BB_UPPER", "BB_MIDDLE", "BB_LOWER",
    "ATR", "OBV",
    "STOCH_K", "STOCH_D",
    "ADX",
    "Daily_Return", "Volatility",
    "Price_Change", "Price_Change_%",
]

# ==========================================================
# ENHANCED / NEW FEATURES (for accuracy improvement)
# ==========================================================

# Advanced indicator features
ADVANCED_INDICATORS = [
    "WILLIAMS_R",       # Williams %R
    "MFI",              # Money Flow Index
    "ROC",              # Price Rate of Change
    "CCI",              # Commodity Channel Index
]

# Ratio features (normalized indicators)
RATIO_FEATURES = [
    "Close_SMA20_Ratio",
    "Close_SMA50_Ratio",
    "Close_BB_Width_Ratio",
    "Volume_SMA20_Ratio",
    "RSI_Normalized",       # RSI/100
    "ATR_Normalized",       # ATR/Close
]

# Lag features (previous day values of key indicators)
LAG_FEATURES_1D = [
    "RSI_lag1", "MACD_lag1", "MACD_HIST_lag1",
    "Daily_Return_lag1",
    "ATR_lag1", "ADX_lag1",
    "Close_lag1", "Close_lag2", "Close_lag3",
    "Volume_lag1", "Volume_lag2", "Volume_lag3",
]

# Rolling features (min/max/mean over windows)
ROLLING_FEATURES = [
    "Close_5d_max", "Close_5d_min",
    "High_5d_max", "Low_5d_min",
    "Volume_5d_mean",
    "Close_10d_max", "Close_10d_min",
    "Daily_Return_5d_mean",
    "Daily_Return_10d_mean",
]

# Nifty market-relative features
MARKET_RELATIVE_FEATURES = [
    "Nifty_Daily_Return", 
    "Stock_vs_Nifty_Return",
]

# Fundamental features
FUNDAMENTAL_FEATURES = [
    "PE_Ratio",
    "PB_Ratio",
    "Market_Cap",
    "Dividend_Yield",
    "Valuation_Category_Overvalued",
    "Valuation_Category_Undervalued",
    "Valuation_Category_Correct",
    "PE_Sector_Relative",
]

# All enhanced technical features combined
ENHANCED_TECHNICAL_FEATURES = (
    TECHNICAL_FEATURES + 
    ADVANCED_INDICATORS + 
    RATIO_FEATURES + 
    LAG_FEATURES_1D + 
    ROLLING_FEATURES + 
    MARKET_RELATIVE_FEATURES
)

# Derived features
DERIVED_FEATURES = [
    "Daily_Return", "Volatility",
    "Price_Change", "Price_Change_%",
]

# All features used for model training (enhanced)
MODEL_FEATURES = TECHNICAL_FEATURES + ADVANCED_INDICATORS + RATIO_FEATURES + \
    LAG_FEATURES_1D + ROLLING_FEATURES + MARKET_RELATIVE_FEATURES + FUNDAMENTAL_FEATURES + [
    "Sentiment_Mean", "Sentiment_Count",
    "Sentiment_Positive", "Sentiment_Neutral", "Sentiment_Negative",
]

# ==========================================================
# VALUATION CATEGORIES (based on P/E percentile)
# ==========================================================

VALUATION_LABELS = ["Undervalued", "Correctly Valued", "Overvalued"]

def classify_valuation(pe_ratio, sector_pe_percentile):
    """
    Classify a stock's valuation based on its P/E ratio percentile within sector.
    
    Parameters
    ----------
    pe_ratio : float
        Company's P/E ratio
    sector_pe_percentile : float
        Percentile rank of P/E within sector (0-100)
    
    Returns
    -------
    str
        'Overvalued', 'Undervalued', or 'Correctly Valued'
    """
    if pd.isna(pe_ratio) or pe_ratio <= 0:
        return "Correctly Valued"
    
    if sector_pe_percentile >= 80:
        return "Overvalued"
    elif sector_pe_percentile <= 20:
        return "Undervalued"
    else:
        return "Correctly Valued"

# ==========================================================
# SENTIMENT MAPPING
# ==========================================================

SENTIMENT_MAP = {
    "Positive": 1,
    "Neutral": 0,
    "Negative": -1,
}

SENTIMENT_LABELS = ["Negative", "Neutral", "Positive"]

# ==========================================================
# TARGET DEFINITIONS (Multi-class)
# ==========================================================

# Multi-class target thresholds (percent change)
TARGET_THRESHOLDS = {
    "Strong_UP": 0.02,      # > 2% rise
    "Mild_UP": 0.001,       # 0.1% to 2% rise
    "Mild_DOWN": -0.001,    # -0.1% to -2% drop
    "Strong_DOWN": -0.02,   # > 2% drop
}

TARGET_CLASSES = ["Strong_DOWN", "Mild_DOWN", "Mild_UP", "Strong_UP"]

# ==========================================================
# DATE UTILITIES
# ==========================================================

def parse_date(date_str):
    """Parse a date string into a datetime object."""
    if isinstance(date_str, pd.Timestamp):
        return date_str
    if isinstance(date_str, datetime):
        return date_str
    return pd.to_datetime(date_str)


def get_date_range(start_date, end_date):
    """Get a list of dates between start and end (inclusive)."""
    start = parse_date(start_date)
    end = parse_date(end_date)
    return pd.date_range(start=start, end=end, freq="D")


def get_default_date_range():
    """Get the default date range for the project."""
    return "2022-01-01", "2026-06-30"


# ==========================================================
# STOCK DATA COLUMNS (for CSV reading)
# ==========================================================

# The stock CSV files have a multi-index header issue from yfinance
# First row: standard column names
# Second row: ticker symbols (sub-columns)
# We need to skip the second row and use the first row as column names

STOCK_COLUMNS = [
    "Date", "Adj Close", "Close", "High", "Low", "Open", "Volume",
    "Company", "Ticker", "Year", "Quarter", "Month"
]

# News sentiment CSV columns
NEWS_COLUMNS = [
    "Company Name", "Symbol", "Headline", "Publish Date", "Sentiment"
]
