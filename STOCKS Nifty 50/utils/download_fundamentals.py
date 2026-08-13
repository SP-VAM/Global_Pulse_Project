"""
Download fundamental data (P/E, P/B, Market Cap, Dividend Yield) from Yahoo Finance.
This provides valuation context for each stock.
"""

import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
import warnings
warnings.filterwarnings("ignore")

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.helper import TICKER_TO_COMPANY, COMPANY_TO_TICKER, classify_valuation


def download_fundamentals_for_company(ticker_symbol):
    """
    Download fundamental data for a single company.

    Parameters
    ----------
    ticker_symbol : str
        Yahoo Finance ticker (e.g., "RELIANCE.NS")

    Returns
    -------
    dict
        Dictionary with fundamental metrics
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        
        # Extract key fundamentals
        fundamentals = {
            "Ticker": ticker_symbol.replace(".NS", ""),
            "PE_Ratio": info.get("trailingPE", np.nan),
            "PB_Ratio": info.get("priceToBook", np.nan),
            "Market_Cap": info.get("marketCap", np.nan),
            "Dividend_Yield": info.get("dividendYield", np.nan),
            "Forward_PE": info.get("forwardPE", np.nan),
            "PEG_Ratio": info.get("pegRatio", np.nan),
            "EPS": info.get("trailingEps", np.nan),
            "Debt_To_Equity": info.get("debtToEquity", np.nan),
            "ROE": info.get("returnOnEquity", np.nan),
            "Sector": info.get("sector", "Unknown"),
            "Industry": info.get("industry", "Unknown"),
        }
        
        return fundamentals
    except Exception as e:
        print(f"  Error fetching fundamentals for {ticker_symbol}: {e}")
        return {
            "Ticker": ticker_symbol.replace(".NS", ""),
            "PE_Ratio": np.nan,
            "PB_Ratio": np.nan,
            "Market_Cap": np.nan,
            "Dividend_Yield": np.nan,
            "Forward_PE": np.nan,
            "PEG_Ratio": np.nan,
            "EPS": np.nan,
            "Debt_To_Equity": np.nan,
            "ROE": np.nan,
            "Sector": "Unknown",
            "Industry": "Unknown",
        }


def download_all_fundamentals():
    """
    Download fundamental data for all companies in the project.

    Returns
    -------
    pd.DataFrame
        DataFrame with fundamental data for all companies
    """
    all_fundamentals = []
    
    for ticker in TICKER_TO_COMPANY.keys():
        yahoo_ticker = f"{ticker}.NS"
        print(f"Fetching fundamentals for {ticker} ({TICKER_TO_COMPANY[ticker]})...")
        
        fund = download_fundamentals_for_company(yahoo_ticker)
        all_fundamentals.append(fund)
    
    df = pd.DataFrame(all_fundamentals)
    
    # Add valuation categories based on P/E percentile
    if "PE_Ratio" in df.columns:
        # Filter valid P/E ratios
        valid_pe = df["PE_Ratio"].dropna()
        valid_pe = valid_pe[valid_pe > 0]
        
        if len(valid_pe) > 5:
            # Calculate percentile rank for each company
            df["PE_Percentile"] = df["PE_Ratio"].rank(pct=True) * 100
            
            # Classify valuation
            df["Valuation_Category"] = df.apply(
                lambda row: classify_valuation(row["PE_Ratio"], row["PE_Percentile"]),
                axis=1
            )
        else:
            df["PE_Percentile"] = 50
            df["Valuation_Category"] = "Correctly Valued"
    
    print(f"\nFundamentals fetched for {len(df)} companies.")
    print(f"Columns: {list(df.columns)}")
    
    return df


def save_fundamentals(output_path="merged_data/fundamentals_data.csv"):
    """
    Download and save fundamental data for all companies.

    Parameters
    ----------
    output_path : str
        Path to save the fundamentals CSV

    Returns
    -------
    pd.DataFrame
        Fundamental data
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    df = download_all_fundamentals()
    df.to_csv(output_path, index=False)
    print(f"Saved fundamentals to {output_path}")
    
    # Print valuation summary
    if "Valuation_Category" in df.columns:
        print("\nValuation Summary:")
        print(df["Valuation_Category"].value_counts())
    
    return df


def load_fundamentals(filepath="merged_data/fundamentals_data.csv"):
    """
    Load pre-downloaded fundamental data.

    Parameters
    ----------
    filepath : str
        Path to fundamentals CSV

    Returns
    -------
    pd.DataFrame
        Fundamental data
    """
    if os.path.exists(filepath):
        return pd.read_csv(filepath)
    return pd.DataFrame()


if __name__ == "__main__":
    df = save_fundamentals()
    print("\nSample data:")
    cols = ["Ticker", "PE_Ratio", "PB_Ratio", "Market_Cap", "Valuation_Category"]
    cols = [c for c in cols if c in df.columns]
    print(df[cols].to_string(index=False))

