"""
Build a leak-safe, vertically stacked dataset for all companies.

The pipeline keeps one row per company-date, removes duplicate/corrupt rows,
strips future-looking columns such as Tomorrow_* and Target_Return, and adds
only point-in-time market context from the Nifty index.
"""

import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from utils.market_data import (
    compute_index_features,
    compute_market_regime,
    compute_market_strength,
    download_index,
)


LEAKAGE_COLUMNS = {
    "Company_Encoded",
    "y_true",
    "y_pred",
    "Target",
    "Target_Return",
}


def normalize_ticker(series):
    """Normalize ticker values to uppercase without .NS suffix."""
    return (
        series.astype(str)
        .str.upper()
        .str.replace(".NS", "", regex=False)
        .str.strip()
    )


def normalize_company(series):
    """Normalize company names by trimming whitespace and collapsing repeats."""
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )


def _resolve_path(path):
    if path is None:
        return None
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_ROOT, path)


def _clean_panel_frame(df, expected_cols=None):
    """Standardise panel data with one row per company-date."""
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if "Ticker" in df.columns:
        df["Ticker"] = normalize_ticker(df["Ticker"])
    if "Company" in df.columns:
        df["Company"] = normalize_company(df["Company"])
    elif "Ticker" in df.columns:
        df["Company"] = df["Ticker"]

    df = df.dropna(subset=["Date", "Ticker"])
    df = df.drop_duplicates(subset=["Ticker", "Date"], keep="last")
    df = df.sort_values(["Ticker", "Date"]).reset_index(drop=True)

    if expected_cols:
        for col in expected_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def _drop_leakage_columns(df):
    """Remove future-looking or model-artifact columns from the feature set."""
    if df is None or df.empty:
        return df

    drop_cols = []
    for col in df.columns:
        if col in LEAKAGE_COLUMNS:
            drop_cols.append(col)
        elif col.startswith("Tomorrow_"):
            drop_cols.append(col)
        elif col.startswith("Target") and col != "Target_Multi":
            drop_cols.append(col)
        elif any(token in col.lower() for token in ["y_true", "y_pred"]):
            drop_cols.append(col)

    drop_cols = [col for col in drop_cols if col in df.columns]
    return df.drop(columns=drop_cols) if drop_cols else df


def load_technical_indicators(indicators_dir="technical_indicators"):
    """Load and clean all technical-indicator CSVs for the panel dataset."""
    indicators_dir = _resolve_path(indicators_dir)
    if not os.path.exists(indicators_dir):
        print(f"Technical indicators directory not found: {indicators_dir}")
        return pd.DataFrame()

    all_dfs = []
    files = [f for f in os.listdir(indicators_dir) if f.endswith(".csv")]
    for file in files:
        filepath = os.path.join(indicators_dir, file)
        try:
            df = pd.read_csv(filepath)
            all_dfs.append(_clean_panel_frame(df))
        except Exception as e:
            print(f"Error loading {file}: {e}")

    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        return _clean_panel_frame(combined)
    return pd.DataFrame()


def load_aggregated_news(news_path="merged_data/news_sentiment_aggregated.csv"):
    """Load aggregated news sentiment, keeping one row per company-date."""
    news_path = _resolve_path(news_path)
    if not os.path.exists(news_path):
        print(f"Aggregated news data not found: {news_path}")
        return pd.DataFrame()

    df = pd.read_csv(news_path)
    return _clean_panel_frame(df)


def load_nifty_data(nifty_path=None):
    """Load or download leak-safe Nifty market features for point-in-time merge."""
    if nifty_path is not None:
        nifty_path = _resolve_path(nifty_path)
        if os.path.exists(nifty_path):
            df = pd.read_csv(nifty_path)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.dropna(subset=["Date"])
            if "Close" in df.columns:
                df = df[["Date", "Close"]].copy()
                df["Nifty_Daily_Return"] = df["Close"].pct_change() * 100
                df = df.rename(columns={"Close": "Nifty_Close"})
            return df.sort_values("Date").reset_index(drop=True)

    print("Downloading current Nifty market context via yfinance...")
    try:
        index_df = download_index("^NSEI", start="2021-12-01", end="2026-07-01")
    except Exception as exc:
        print(f"Failed to download Nifty data: {exc}")
        return pd.DataFrame()

    if index_df.empty:
        return pd.DataFrame()

    index_df = index_df.copy()
    index_df["Date"] = pd.to_datetime(index_df["Date"], errors="coerce")
    index_df = index_df.dropna(subset=["Date"])
    index_df = index_df[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
    index_df = compute_index_features(index_df, prefix="NIFTY")
    index_df = index_df.rename(columns={"Close": "NIFTY_Close"})
    index_df = index_df.drop(columns=["Open", "High", "Low", "Volume"])
    index_df = compute_market_regime(index_df, None)
    index_df["NIFTY_Market_Strength"] = compute_market_strength(index_df, None)
    return index_df.sort_values("Date").reset_index(drop=True)


def load_fundamentals(fundamentals_path="merged_data/fundamentals_data.csv"):
    """Load fundamentals per ticker and clean them for a point-in-time merge."""
    fundamentals_path = _resolve_path(fundamentals_path)
    if not os.path.exists(fundamentals_path):
        print(f"Fundamentals data not found at {fundamentals_path}")
        return pd.DataFrame()

    df = pd.read_csv(fundamentals_path)
    if "Ticker" in df.columns:
        df["Ticker"] = normalize_ticker(df["Ticker"])
    if "Company" in df.columns:
        df["Company"] = normalize_company(df["Company"])
    return df.drop_duplicates(subset=["Ticker"], keep="last").reset_index(drop=True)


def merge_datasets(
    indicators_df,
    news_df,
    nifty_df=None,
    fundamentals_df=None,
    on_columns=["Ticker", "Date"],
    indicator_suffix="_indicator",
    news_suffix="_news",
):
    """Merge indicators, news, market context and fundamentals into one panel dataset."""
    if indicators_df is None or indicators_df.empty:
        print("No indicators data to merge.")
        return pd.DataFrame()

    indicators_df = _clean_panel_frame(indicators_df)
    news_df = _clean_panel_frame(news_df)

    if "Ticker" in indicators_df.columns:
        indicators_df["Ticker"] = normalize_ticker(indicators_df["Ticker"])
    if "Ticker" in news_df.columns:
        news_df["Ticker"] = normalize_ticker(news_df["Ticker"])

    merged = pd.merge(
        indicators_df,
        news_df,
        on=on_columns,
        how="left",
        suffixes=(indicator_suffix, news_suffix),
    )

    merged = merged.loc[:, ~merged.columns.duplicated()]

    if "Company_indicator" in merged.columns:
        merged = merged.rename(columns={"Company_indicator": "Company"})
    if "Company_news" in merged.columns:
        merged = merged.drop(columns=["Company_news"])

    if "Company" not in merged.columns and "Ticker" in merged.columns:
        merged["Company"] = merged["Ticker"]

    sentiment_cols = [
        "Sentiment_Mean",
        "Sentiment_Count",
        "Sentiment_Positive",
        "Sentiment_Neutral",
        "Sentiment_Negative",
    ]
    for col in sentiment_cols:
        if col in merged.columns:
            merged[col] = merged[col].fillna(0)

    if nifty_df is not None and not nifty_df.empty:
        print("Adding Nifty market-relative features...")
        nifty_df = nifty_df.copy()
        nifty_df["Date"] = pd.to_datetime(nifty_df["Date"], errors="coerce")
        nifty_df = nifty_df.dropna(subset=["Date"]).drop_duplicates(subset=["Date"], keep="last")
        merged = pd.merge(merged, nifty_df, on="Date", how="left")

        if "Daily_Return" in merged.columns and "NIFTY_Daily_Return" in merged.columns:
            merged["NIFTY_Daily_Return"] = merged["NIFTY_Daily_Return"].fillna(0)
            merged["Stock_vs_Nifty_Return"] = (
                merged["Daily_Return"].fillna(0) * 100
            ) - merged["NIFTY_Daily_Return"].fillna(0)

    if fundamentals_df is not None and not fundamentals_df.empty:
        print("Adding fundamental features...")
        fundamentals_df = fundamentals_df.copy()
        fundamentals_df["Ticker"] = normalize_ticker(fundamentals_df["Ticker"])
        fund_cols = [
            "Ticker",
            "PE_Ratio",
            "PB_Ratio",
            "Market_Cap",
            "Dividend_Yield",
            "Valuation_Category",
        ]
        fund_cols = [c for c in fund_cols if c in fundamentals_df.columns]
        merged = pd.merge(merged, fundamentals_df[fund_cols], on="Ticker", how="left")

        if "Valuation_Category" in merged.columns:
            merged["Valuation_Category_Overvalued"] = (
                merged["Valuation_Category"] == "Overvalued"
            ).astype(int)
            merged["Valuation_Category_Undervalued"] = (
                merged["Valuation_Category"] == "Undervalued"
            ).astype(int)
            merged["Valuation_Category_Correct"] = (
                merged["Valuation_Category"] == "Correctly Valued"
            ).astype(int)
            merged = merged.drop(columns=["Valuation_Category"])

        numeric_cols = ["PE_Ratio", "PB_Ratio", "Market_Cap", "Dividend_Yield"]
        for col in numeric_cols:
            if col in merged.columns:
                merged[col] = pd.to_numeric(merged[col], errors="coerce")
                merged[col] = merged[col].fillna(merged[col].median())

    merged = merged.dropna(subset=["Date"])
    if "Target_Multi" not in merged.columns and "Target" in merged.columns:
        merged["Target_Multi"] = merged["Target"].astype(int)
    if "Target_Multi" in merged.columns:
        merged = merged.dropna(subset=["Target_Multi"])

    merged = merged.sort_values(["Company", "Date"]).reset_index(drop=True)
    merged = _drop_leakage_columns(merged)
    if "Market_Regime" in merged.columns:
        merged = merged.drop(columns=["Market_Regime"])

    return merged


def create_merged_dataset(
    indicators_dir="technical_indicators",
    news_path="merged_data/news_sentiment_aggregated.csv",
    nifty_path=None,
    fundamentals_path="merged_data/fundamentals_data.csv",
    output_path="merged_data/merged_dataset.csv",
):
    """Build the full leak-safe panel dataset and save it to disk."""
    output_path = _resolve_path(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print("Loading technical indicators...")
    indicators = load_technical_indicators(indicators_dir)
    print(f"Loaded {len(indicators)} rows of indicator data")

    print("Loading aggregated news sentiment...")
    news = load_aggregated_news(news_path)
    print(f"Loaded {len(news)} rows of news sentiment data")

    print("Loading Nifty market context...")
    nifty = load_nifty_data(nifty_path)
    if nifty.empty:
        print("Nifty market context unavailable. Market-relative features will be skipped.")
    else:
        print(f"Loaded {len(nifty)} rows of Nifty data")

    print("Loading fundamentals data...")
    fundamentals = load_fundamentals(fundamentals_path)
    if fundamentals.empty:
        print("Fundamentals data unavailable. Fundamental features will be skipped.")
    else:
        print(f"Loaded {len(fundamentals)} rows of fundamentals data")

    print("Merging datasets...")
    merged = merge_datasets(indicators, news, nifty, fundamentals)
    print(f"Merged dataset shape: {merged.shape}")

    merged.to_csv(output_path, index=False)
    print(f"Saved merged dataset to {output_path}")

    print(f"\nColumns ({len(merged.columns)}):")
    for col in merged.columns:
        print(f"  - {col}")

    return merged


if __name__ == "__main__":
    df = create_merged_dataset()
    print(f"\nFirst 3 rows:")
    print(df.head(3))
    print(f"\nDate range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"Companies: {df['Company'].nunique()}")
    if "Target_Multi" in df.columns:
        print(f"Multi-class target distribution:\n{df['Target_Multi'].value_counts()}")
    leak_cols = [c for c in ["Tomorrow_Close", "Tomorrow_Return", "Target_Return", "Target", "Company_Encoded"] if c in df.columns]
    if leak_cols:
        print(f"Leakage columns still present: {leak_cols}")
