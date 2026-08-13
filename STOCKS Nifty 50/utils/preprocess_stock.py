"""
Stock data cleaning and feature engineering.
Handles reading raw CSV files from yfinance, cleaning, and computing technical indicators.
"""

import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")


def read_stock_csv(filepath):
    """
    Read a stock CSV file downloaded by yfinance.
    
    The CSVs have a multi-index header (first row=column names, second row=tickers).
    We skip the second row and use standard column names.

    Parameters
    ----------
    filepath : str
        Path to the CSV file

    Returns
    -------
    pd.DataFrame
        Cleaned stock data with proper column names
    """
    # Read the CSV, skip the second row which has ticker sub-headers
    df = pd.read_csv(filepath, header=0)
    
    # Drop the second row if it contains ticker symbols (check if first column is empty)
    if df.iloc[0, 0] == "" or not pd.notna(df.iloc[0, 0]):
        df = df.iloc[1:].reset_index(drop=True)
    
    # Rename columns to standard names
    expected_cols = [
        "Date", "Adj Close", "Close", "High", "Low", "Open", "Volume",
        "Company", "Ticker", "Year", "Quarter", "Month"
    ]
    
    # Only rename if the number of columns matches
    if len(df.columns) == len(expected_cols):
        df.columns = expected_cols
    else:
        # If columns don't match, use the first row as header approach
        df = pd.read_csv(filepath, skiprows=1)
        if len(df.columns) == len(expected_cols):
            df.columns = expected_cols
            
    # Parse dates
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    
    # Drop rows with invalid dates
    df = df.dropna(subset=["Date"])
    
    # Convert numeric columns
    numeric_cols = ["Adj Close", "Close", "High", "Low", "Open", "Volume"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Sort by date
    df = df.sort_values("Date").reset_index(drop=True)
    
    return df


def load_all_stock_data(stock_dir="stock_data"):
    """
    Load all stock CSV files from a directory.

    Parameters
    ----------
    stock_dir : str
        Directory containing stock CSV files

    Returns
    -------
    pd.DataFrame
        Combined stock data for all companies
    """
    all_dfs = []
    
    files = [f for f in os.listdir(stock_dir) if f.endswith(".csv")]
    
    for file in files:
        filepath = os.path.join(stock_dir, file)
        try:
            df = read_stock_csv(filepath)
            if not df.empty:
                all_dfs.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")
    
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        return combined
    else:
        return pd.DataFrame()


def compute_technical_indicators(df):
    """
    Compute technical indicators on a stock DataFrame.
    Assumes df has columns: Date, Close, High, Low, Open, Volume (at minimum).

    Parameters
    ----------
    df : pd.DataFrame
        Stock data with OHLCV columns, sorted by Date

    Returns
    -------
    pd.DataFrame
        DataFrame with technical indicators added
    """
    df = df.copy()
    df = df.sort_values("Date").reset_index(drop=True)
    
    # Moving Averages
    df["SMA20"] = df["Close"].rolling(window=20).mean()
    df["SMA50"] = df["Close"].rolling(window=50).mean()
    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    
    # RSI (Relative Strength Index)
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df["RSI"] = 100 - (100 / (1 + rs))
    
    # MACD (Moving Average Convergence Divergence)
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_SIGNAL"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_HIST"] = df["MACD"] - df["MACD_SIGNAL"]
    
    # Bollinger Bands (20-day, 2 standard deviations)
    df["BB_MIDDLE"] = df["Close"].rolling(window=20).mean()
    bb_std = df["Close"].rolling(window=20).std()
    df["BB_UPPER"] = df["BB_MIDDLE"] + (bb_std * 2)
    df["BB_LOWER"] = df["BB_MIDDLE"] - (bb_std * 2)
    
    # ATR (Average True Range)
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR"] = tr.rolling(window=14).mean()
    
    # OBV (On-Balance Volume)
    obv = (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()
    df["OBV"] = obv
    
    # Stochastic Oscillator (14, 3, 3)
    low_14 = df["Low"].rolling(window=14).min()
    high_14 = df["High"].rolling(window=14).max()
    df["STOCH_K"] = 100 * ((df["Close"] - low_14) / (high_14 - low_14 + 1e-10))
    df["STOCH_D"] = df["STOCH_K"].rolling(window=3).mean()
    
    # ADX (Average Directional Index) — TRUE Wilder's ADX
    # Uses directional movement (+DM/-DM) and smoothed ATR
    up_move = df["High"].diff()
    down_move = -df["Low"].diff()
    
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=df.index
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=df.index
    )
    
    # Smoothed DM and TR using Wilder's smoothing (simple moving average of period)
    atr_smooth = tr.rolling(window=14).mean()
    plus_dm_smooth = plus_dm.rolling(window=14).mean()
    minus_dm_smooth = minus_dm.rolling(window=14).mean()
    
    plus_di = 100 * (plus_dm_smooth / (atr_smooth + 1e-10))
    minus_di = 100 * (minus_dm_smooth / (atr_smooth + 1e-10))
    
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10))
    df["ADX"] = dx.rolling(window=14).mean()
    
    # Daily Return
    df["Daily_Return"] = df["Close"].pct_change()
    
    # Volatility (20-day rolling standard deviation of returns)
    df["Volatility"] = df["Daily_Return"].rolling(window=20).std()
    
    # Price Change
    df["Price_Change"] = df["Close"] - df["Open"]
    df["Price_Change_%"] = ((df["Close"] - df["Open"]) / df["Open"]) * 100
    
    return df


def compute_enhanced_features(df):
    """
    Compute enhanced features on a stock DataFrame.
    Adds advanced indicators, ratio features, lag features, rolling features.
    Must be called AFTER compute_technical_indicators.

    Parameters
    ----------
    df : pd.DataFrame
        Stock data with technical indicators already computed

    Returns
    -------
    pd.DataFrame
        DataFrame with enhanced features added
    """
    df = df.copy()
    
    # Advanced Indicators
    
    # Williams %R
    high_14 = df["High"].rolling(window=14).max()
    low_14 = df["Low"].rolling(window=14).min()
    df["WILLIAMS_R"] = -100 * ((high_14 - df["Close"]) / (high_14 - low_14 + 1e-10))
    
    # Money Flow Index (MFI)
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    money_flow = typical_price * df["Volume"]
    positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(window=14).sum()
    negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(window=14).sum()
    mfi_ratio = positive_flow / (negative_flow + 1e-10)
    df["MFI"] = 100 - (100 / (1 + mfi_ratio))
    
    # Price Rate of Change (ROC)
    df["ROC"] = df["Close"].pct_change(periods=10) * 100
    
    # Commodity Channel Index (CCI)
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    sma_tp = tp.rolling(window=20).mean()
    mad_tp = tp.rolling(window=20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    df["CCI"] = (tp - sma_tp) / (0.015 * mad_tp + 1e-10)
    
    # Ratio Features (Normalized)
    df["Close_SMA20_Ratio"] = df["Close"] / (df["SMA20"] + 1e-10)
    df["Close_SMA50_Ratio"] = df["Close"] / (df["SMA50"] + 1e-10)
    df["Close_BB_Width_Ratio"] = (df["Close"] - df["BB_LOWER"]) / (df["BB_UPPER"] - df["BB_LOWER"] + 1e-10)
    df["Volume_SMA20_Ratio"] = df["Volume"] / (df["Volume"].rolling(window=20).mean() + 1e-10)
    df["RSI_Normalized"] = df["RSI"] / 100.0
    df["ATR_Normalized"] = df["ATR"] / (df["Close"] + 1e-10)
    
    # Lag Features (1-day, 2-day, 3-day lags)
    df["Close_lag1"] = df["Close"].shift(1)
    df["Close_lag2"] = df["Close"].shift(2)
    df["Close_lag3"] = df["Close"].shift(3)
    df["RSI_lag1"] = df["RSI"].shift(1)
    df["MACD_lag1"] = df["MACD"].shift(1)
    df["MACD_HIST_lag1"] = df["MACD_HIST"].shift(1)
    df["Daily_Return_lag1"] = df["Daily_Return"].shift(1)
    df["Volume_lag1"] = df["Volume"].shift(1)
    df["Volume_lag2"] = df["Volume"].shift(2)
    df["Volume_lag3"] = df["Volume"].shift(3)
    df["ATR_lag1"] = df["ATR"].shift(1)
    df["ADX_lag1"] = df["ADX"].shift(1)
    
    # Rolling Features (Min/Max/Mean over windows)
    df["Close_5d_max"] = df["Close"].rolling(window=5).max()
    df["Close_5d_min"] = df["Close"].rolling(window=5).min()
    df["High_5d_max"] = df["High"].rolling(window=5).max()
    df["Low_5d_min"] = df["Low"].rolling(window=5).min()
    df["Volume_5d_mean"] = df["Volume"].rolling(window=5).mean()
    df["Close_10d_max"] = df["Close"].rolling(window=10).max()
    df["Close_10d_min"] = df["Close"].rolling(window=10).min()
    df["Daily_Return_5d_mean"] = df["Daily_Return"].rolling(window=5).mean()
    df["Daily_Return_10d_mean"] = df["Daily_Return"].rolling(window=10).mean()
    
    return df


def compute_targets(df):
    """
    Compute multi-class targets (strong/mild up/down) and regression target.
    
    Parameters
    ----------
    df : pd.DataFrame
        Stock data with Daily_Return column
    
    Returns
    -------
    pd.DataFrame
        DataFrame with multi-class target added
    """
    df = df.copy()
    
    # Tomorrow's close for computing returns
    df["Tomorrow_Close"] = df["Close"].shift(-1)
    df["Tomorrow_Return"] = (df["Tomorrow_Close"] / df["Close"] - 1) * 100
    
    # Binary direction target (original)
    df["Target"] = (df["Tomorrow_Close"] > df["Close"]).astype(int)
    
    # Multi-class target: 0=DOWN (<= -1%), 1=FLAT (between -1% and +1%), 2=UP (>= 1%)
    def classify_multi(ret):
        if pd.isna(ret):
            return -1
        if ret >= 1.0:
            return 2  # UP
        elif ret <= -1.0:
            return 0  # DOWN
        else:
            return 1  # FLAT
    
    df["Target_Multi"] = df["Tomorrow_Return"].apply(classify_multi)
    
    # Regression target: actual % return
    df["Target_Return"] = df["Tomorrow_Return"]
    
    # Remove the last row (no target available for the last day)
    df = df.iloc[:-1].copy()
    
    return df


def preprocess_stock_data(stock_dir="stock_data", save_dir="technical_indicators"):
    """
    Full pipeline: load all stock data, compute indicators, and save.
    
    Parameters
    ----------
    stock_dir : str
        Directory containing raw stock CSVs
    save_dir : str
        Directory to save indicator CSVs

    Returns
    -------
    pd.DataFrame
        Combined DataFrame with all indicators
    """
    os.makedirs(save_dir, exist_ok=True)
    
    all_data = []
    
    files = [f for f in os.listdir(stock_dir) if f.endswith(".csv")]
    
    for file in files:
        filepath = os.path.join(stock_dir, file)
        try:
            df = read_stock_csv(filepath)
            if df.empty:
                continue
            
            df = compute_technical_indicators(df)
            df = compute_enhanced_features(df)
            df = compute_targets(df)
            
            # Save individual file
            output_file = file.replace(".csv", "_indicators.csv")
            output_path = os.path.join(save_dir, output_file)
            df.to_csv(output_path, index=False)
            
            all_data.append(df)
            print(f"Processed {file} -> {output_file}")
        except Exception as e:
            print(f"Error processing {file}: {e}")
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        return combined
    
    return pd.DataFrame()


if __name__ == "__main__":
    combined = preprocess_stock_data()
    print(f"\nProcessed {len(combined)} rows across all companies.")
    print(f"Columns: {list(combined.columns)}")

