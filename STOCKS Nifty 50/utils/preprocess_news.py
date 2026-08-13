"""
News sentiment preprocessing.
Handles loading the news sentiment CSV and aggregating sentiment by company and date.
"""

import os
import pandas as pd
import numpy as np


# Sentiment value mapping
SENTIMENT_MAP = {
    "Positive": 1,
    "Neutral": 0,
    "Negative": -1,
}


def load_news_sentiment(filepath="news_data/final_news_sentiment_analysis.csv"):
    """
    Load the news sentiment CSV file.

    Parameters
    ----------
    filepath : str
        Path to the news sentiment CSV file

    Returns
    -------
    pd.DataFrame
        News sentiment data with columns:
        Company Name, Symbol, Headline, Publish Date, Sentiment
    """
    if not os.path.exists(filepath):
        print(f"News sentiment file not found: {filepath}")
        return pd.DataFrame()
    
    df = pd.read_csv(filepath)
    
    # Standardize column names (handle variations)
    col_mapping = {
        "Company Name": "Company Name",
        "Symbol": "Symbol",
        "Headline": "Headline",
        "Publish Date": "Publish Date",
        "Sentiment": "Sentiment",
    }
    
    # Only keep columns that exist
    available_cols = {k: v for k, v in col_mapping.items() if k in df.columns}
    df = df[list(available_cols.keys())].copy()
    
    # Rename to standard names
    df.rename(columns=available_cols, inplace=True)
    
    # Parse publish date
    if "Publish Date" in df.columns:
        df["Publish Date"] = pd.to_datetime(df["Publish Date"], errors="coerce")
    
    # Map sentiment text to numeric values
    if "Sentiment" in df.columns:
        df["Sentiment_Value"] = df["Sentiment"].map(SENTIMENT_MAP)
    
    # Drop rows with missing dates
    df = df.dropna(subset=["Publish Date"])
    
    return df


def aggregate_sentiment_by_company_date(
    df,
    company_col="Company Name",
    date_col="Publish Date",
    sentiment_col="Sentiment_Value",
    symbol_col="Symbol"
):
    """
    Aggregate news sentiment by company and date.
    For each company-date pair, compute:
    - Mean sentiment
    - Count of news articles
    - Count of positive, neutral, negative articles

    Parameters
    ----------
    df : pd.DataFrame
        News sentiment data
    company_col : str
        Column name for company name
    date_col : str
        Column name for date
    sentiment_col : str
        Column name for numeric sentiment value (-1, 0, 1)
    symbol_col : str
        Column name for stock symbol

    Returns
    -------
    pd.DataFrame
        Aggregated sentiment by company and date
    """
    if df.empty:
        return pd.DataFrame()
    
    # Map company names to ticker symbols using the helper
    try:
        from utils.helper import COMPANY_TO_TICKER
    except ImportError:
        COMPANY_TO_TICKER = {}
    
    # Add ticker column if symbol column exists
    if symbol_col in df.columns:
        # Ensure ticker column
        df["Ticker"] = df[symbol_col].str.upper().str.replace(".NS", "", regex=False)
    
    # Create date-only column (no time component)
    df["Date"] = pd.to_datetime(df[date_col]).dt.date
    df["Date"] = pd.to_datetime(df["Date"])
    
    # Aggregate by company and date
    agg = df.groupby([company_col, "Date"]).agg(
        Sentiment_Mean=(sentiment_col, "mean"),
        Sentiment_Count=(sentiment_col, "count"),
        Sentiment_Positive=(sentiment_col, lambda x: (x > 0).sum()),
        Sentiment_Neutral=(sentiment_col, lambda x: (x == 0).sum()),
        Sentiment_Negative=(sentiment_col, lambda x: (x < 0).sum()),
        Ticker=(symbol_col, "first"),
    ).reset_index()
    
    # Clean ticker: remove .NS suffix and ensure uppercase
    if "Ticker" in agg.columns:
        agg["Ticker"] = agg["Ticker"].str.upper().str.replace(".NS", "", regex=False)
    
    # Rename company name column for merging
    agg.rename(columns={company_col: "Company"}, inplace=True)
    
    return agg


def preprocess_news_data(
    input_path="news_data/final_news_sentiment_analysis.csv",
    output_path="merged_data/news_sentiment_aggregated.csv"
):
    """
    Full pipeline: load news sentiment, aggregate by company/date, save.

    Parameters
    ----------
    input_path : str
        Path to raw news sentiment CSV
    output_path : str
        Path to save aggregated sentiment CSV

    Returns
    -------
    pd.DataFrame
        Aggregated sentiment data
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    df = load_news_sentiment(input_path)
    
    if df.empty:
        print("No news data loaded.")
        return df
    
    agg = aggregate_sentiment_by_company_date(df)
    
    agg.to_csv(output_path, index=False)
    print(f"Saved aggregated news sentiment to {output_path}")
    print(f"Shape: {agg.shape}")
    print(f"Date range: {agg['Date'].min()} to {agg['Date'].max()}")
    print(f"Companies: {agg['Ticker'].nunique()}")
    
    return agg


if __name__ == "__main__":
    agg = preprocess_news_data()
    print(agg.head())

