"""
Market-wide data processing.

This module downloads/downloads market-wide datasets (India VIX, Nifty,
Sensex, Bank Nifty, NSE sector indices) via yfinance, computes broad
indicator features, and computes market breadth from locally stored
NIFTY-50 stock data. All features are designed to be leak-safe: they are
computed using only past data (rolling windows / pct_change), so no future
information is used.

FII/DII is intentionally NOT implemented (no reliable free programmatic
source available). Market breadth is computed entirely from local stock CSVs.
"""

import os
import warnings
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

DEFAULT_START = "2021-12-01"
DEFAULT_END = "2026-07-01"

# ==========================================================
# TICKER MAPPINGS
# ==========================================================

# Broad market indices (yfinance)
BROAD_INDEX_TICKERS = {
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN",
    "BANKNIFTY": "^NSEBANK",
    "INDIAVIX": "^INDIAVIX",
}

# NSE Sector indices (yfinance ^CNX format)
SECTOR_INDEX_TICKERS = {
    "IT": "^CNXIT",
    "AUTO": "^CNXAUTO",
    "PHARMA": "^CNXPHARMA",
    "FMCG": "^CNXFMCG",
    "METAL": "^CNXMETAL",
    "ENERGY": "^CNXENERGY",
    "REALTY": "^CNXREALTY",
    "BANK": "^NSEBANK",
}

# Stock ticker -> Sector mapping (NSE Nifty-50 constituents)
STOCK_TO_SECTOR = {
    "ADANIENT": "ENERGY",
    "ADANIPORTS": "ENERGY",
    "APOLLOHOSP": "PHARMA",
    "ASIANPAINT": "FMCG",
    "AXISBANK": "BANK",
    "BAJAJ-AUTO": "AUTO",
    "BAJAJFINSV": "BANK",
    "BAJFINANCE": "BANK",
    "BEL": "ENERGY",
    "BHARTIARTL": "IT",
    "CIPLA": "PHARMA",
    "COALINDIA": "ENERGY",
    "DRREDDY": "PHARMA",
    "EICHERMOT": "AUTO",
    "ETERNAL": "FMCG",
    "GRASIM": "METAL",
    "HCLTECH": "IT",
    "HDFCBANK": "BANK",
    "HDFCLIFE": "BANK",
    "HEROMOTOCO": "AUTO",
    "HINDALCO": "METAL",
    "HINDUNILVR": "FMCG",
    "ICICIBANK": "BANK",
    "INDUSINDBK": "BANK",
    "INFY": "IT",
    "ITC": "FMCG",
    "JIOFIN": "BANK",
    "JSWSTEEL": "METAL",
    "KOTAKBANK": "BANK",
    "LT": "ENERGY",
    "M&M": "AUTO",
    "MARUTI": "AUTO",
    "NESTLEIND": "FMCG",
    "NTPC": "ENERGY",
    "ONGC": "ENERGY",
    "POWERGRID": "ENERGY",
    "RELIANCE": "ENERGY",
    "SBILIFE": "BANK",
    "SBIN": "BANK",
    "SHRIRAMFIN": "BANK",
    "SUNPHARMA": "PHARMA",
    "TATACONSUM": "FMCG",
    "TATASTEEL": "METAL",
    "TCS": "IT",
    "TECHM": "IT",
    "TITAN": "FMCG",
    "TRENT": "FMCG",
    "ULTRACEMCO": "METAL",
    "WIPRO": "IT",
}


def get_sector_for_ticker(ticker):
    """Return the sector name for a given ticker (normalized)."""
    t = str(ticker).upper().replace(".NS", "").strip()
    return STOCK_TO_SECTOR.get(t, "ENERGY")


# ==========================================================
# INDICATOR HELPERS
# ==========================================================

def _ema(series, span):
    """Exponential moving average."""
    return series.ewm(span=span, adjust=False).mean()


def _rsi(series, period=14):
    """Relative Strength Index."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-12)
    return 100 - (100 / (1 + rs))


def _macd(series, fast=12, slow=26, signal=9):
    """MACD line, signal, histogram."""
    macd_line = _ema(series, fast) - _ema(series, slow)
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _adx(high, low, close, period=14):
    """Average Directional Index."""
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=high.index)
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, adjust=False).mean() / (atr + 1e-12))
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, adjust=False).mean() / (atr + 1e-12))
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-12))
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    return adx


def _rolling_vol(close, period=20):
    """Rolling annualized volatility (percent)."""
    ret = close.pct_change()
    return ret.rolling(period).std() * np.sqrt(252) * 100


def compute_index_features(df, prefix="NIFTY"):
    """
    Compute broad indicator features for an index DataFrame.

    Expects df with columns: Date, Open, High, Low, Close, Volume.
    Returns a DataFrame indexed-safe with prefixed feature columns.
    """
    df = df.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    # Returns
    df[f"{prefix}_Daily_Return"] = close.pct_change() * 100
    df[f"{prefix}_3D_Return"] = close.pct_change(3) * 100
    df[f"{prefix}_5D_Return"] = close.pct_change(5) * 100
    df[f"{prefix}_10D_Return"] = close.pct_change(10) * 100
    df[f"{prefix}_20D_Return"] = close.pct_change(20) * 100

    # EMAs
    df[f"{prefix}_EMA20"] = _ema(close, 20)
    df[f"{prefix}_EMA50"] = _ema(close, 50)
    df[f"{prefix}_EMA200"] = _ema(close, 200)

    # RSI
    df[f"{prefix}_RSI"] = _rsi(close, 14)

    # MACD
    macd_line, signal_line, hist = _macd(close)
    df[f"{prefix}_MACD"] = macd_line
    df[f"{prefix}_MACD_SIGNAL"] = signal_line
    df[f"{prefix}_MACD_HIST"] = hist

    # ADX
    df[f"{prefix}_ADX"] = _adx(high, low, close, 14)

    # Trend direction: +1 if close > EMA50, -1 if below
    df[f"{prefix}_Trend_Direction"] = np.sign(close - df[f"{prefix}_EMA50"])

    # Rolling volatility
    df[f"{prefix}_Rolling_Volatility"] = _rolling_vol(close, 20)

    return df


def compute_vix_features(df, prefix="INDIAVIX"):
    """
    Compute India VIX features.

    VIX is a volatility index; its level matters more than its "Close".
    """
    df = df.copy()
    close = df["Close"]

    df[f"{prefix}_Daily_Return"] = close.pct_change() * 100
    df[f"{prefix}_5D_Return"] = close.pct_change(5) * 100
    df[f"{prefix}_10D_Return"] = close.pct_change(10) * 100
    df[f"{prefix}_20D_Return"] = close.pct_change(20) * 100
    df[f"{prefix}_EMA20"] = _ema(close, 20)
    df[f"{prefix}_EMA50"] = _ema(close, 50)
    df[f"{prefix}_RSI"] = _rsi(close, 14)
    macd_line, signal_line, hist = _macd(close)
    df[f"{prefix}_MACD"] = macd_line
    df[f"{prefix}_MACD_SIGNAL"] = signal_line
    df[f"{prefix}_MACD_HIST"] = hist
    # Volatility trend: 20d vol vs its 20d MA -> rising/falling fear
    df[f"{prefix}_Volatility_Trend"] = close - df[f"{prefix}_EMA20"]
    return df


# ==========================================================
# DOWNLOADING
# ==========================================================

def download_index(ticker, start=DEFAULT_START, end=DEFAULT_END):
    """Download daily OHLCV for an index ticker via yfinance."""
    try:
        data = yf.download(ticker, start=start, end=end, interval="1d",
                           auto_adjust=False, progress=False)
    except Exception as e:
        print(f"  Download error for {ticker}: {e}")
        return pd.DataFrame()
    if data is None or data.empty:
        print(f"  No data for {ticker}")
        return pd.DataFrame()
    data.reset_index(inplace=True)
    # Flatten multi-index columns if present (Price, Ticker)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [c[0] for c in data.columns]
    else:
        data.columns = [str(c).split(",")[0].strip() for c in data.columns]
    if "Date" not in data.columns:
        data = data.rename(columns={"index": "Date"})
    return data


def download_all_indices(start=DEFAULT_START, end=DEFAULT_END):
    """
    Download broad indices and sector indices, compute features.

    Returns dict: {"broad": {prefix: df}, "sector": {sector: df}}
    """
    broad = {}
    for name, ticker in BROAD_INDEX_TICKERS.items():
        print(f"Downloading {name} ({ticker})...")
        df = download_index(ticker, start, end)
        if df.empty:
            continue
        if name == "INDIAVIX":
            df = compute_vix_features(df, prefix="INDIAVIX")
        else:
            df = compute_index_features(df, prefix=name)
        broad[name] = df

    sector = {}
    for sector_name, ticker in SECTOR_INDEX_TICKERS.items():
        if sector_name == "BANK":
            # BankNifty already downloaded; reuse
            if "BANKNIFTY" in broad:
                sector[sector_name] = broad["BANKNIFTY"].copy()
                continue
        print(f"Downloading sector {sector_name} ({ticker})...")
        df = download_index(ticker, start, end)
        if df.empty:
            continue
        df = compute_index_features(df, prefix=f"SECTOR_{sector_name}")
        sector[sector_name] = df

    return {"broad": broad, "sector": sector}


# ==========================================================
# MARKET BREADTH (from local Nifty-50 stock CSVs)
# ==========================================================

def compute_market_breadth(stocks_dir="stock_data"):
    """
    Compute market breadth daily values from locally stored NIFTY-50 stock
    CSVs. No web scraping.

    Returns DataFrame indexed by Date with columns:
      Advance_Count, Decline_Count, Advance_Decline_Ratio,
      Pct_Above_EMA20, Pct_Above_EMA50,
      Nifty_52Week_High_Count, Nifty_52Week_Low_Count,
      Breadth_Score
    """
    files = [f for f in os.listdir(stocks_dir) if f.endswith(".csv")]
    closes = {}
    ema20s = {}
    ema50s = {}
    highs_52w = {}
    lows_52w = {}

    for f in files:
        path = os.path.join(stocks_dir, f)
        try:
            df = pd.read_csv(path)
        except Exception as e:
            print(f"  Breadth: skip {f}: {e}")
            continue
        if "Date" not in df.columns or "Close" not in df.columns:
            continue
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        # Coerce numeric columns (yfinance may return strings after reload)
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["Date", "Close"]).sort_values("Date")
        df = df.set_index("Date")
        closes[f] = df["Close"]
        ema20s[f] = _ema(df["Close"], 20)
        ema50s[f] = _ema(df["Close"], 50)
        highs_52w[f] = df["High"].rolling(252).max() if "High" in df.columns else pd.Series(index=df.index)
        lows_52w[f] = df["Low"].rolling(252).min() if "Low" in df.columns else pd.Series(index=df.index)

    if not closes:
        return pd.DataFrame()

    dates = pd.concat(list(closes.values())).index.unique().sort_values()

    adv = []
    decl = []
    pct_ema20 = []
    pct_ema50 = []
    hi52 = []
    lo52 = []

    for d in dates:
        a = 0
        de = 0
        n20 = 0
        n50 = 0
        nh = 0
        nl = 0
        count = 0
        for f in closes:
            if d not in closes[f].index:
                continue
            count += 1
            ret_today = closes[f].loc[d] - closes[f].shift(1).loc[d]
            if ret_today > 0:
                a += 1
            elif ret_today < 0:
                de += 1
            if d in ema20s[f].index and closes[f].loc[d] > ema20s[f].loc[d]:
                n20 += 1
            if d in ema50s[f].index and closes[f].loc[d] > ema50s[f].loc[d]:
                n50 += 1
            if d in highs_52w[f].index and not np.isnan(highs_52w[f].loc[d]) and closes[f].loc[d] >= highs_52w[f].loc[d]:
                nh += 1
            if d in lows_52w[f].index and not np.isnan(lows_52w[f].loc[d]) and closes[f].loc[d] <= lows_52w[f].loc[d]:
                nl += 1
        if count > 0:
            adv.append(a)
            decl.append(de)
            pct_ema20.append(n20 / count)
            pct_ema50.append(n50 / count)
            hi52.append(nh)
            lo52.append(nl)
        else:
            adv.append(np.nan)
            decl.append(np.nan)
            pct_ema20.append(np.nan)
            pct_ema50.append(np.nan)
            hi52.append(np.nan)
            lo52.append(np.nan)

    breadth = pd.DataFrame({
        "Date": dates,
        "Advance_Count": adv,
        "Decline_Count": decl,
        "Pct_Above_EMA20": pct_ema20,
        "Pct_Above_EMA50": pct_ema50,
        "Nifty_52Week_High_Count": hi52,
        "Nifty_52Week_Low_Count": lo52,
    })
    breadth["Advance_Decline_Ratio"] = breadth["Advance_Count"] / (breadth["Decline_Count"] + 1e-6)
    # Breadth Score: combination of breadth indicators scaled to ~0-100
    breadth["Breadth_Score"] = (
        40 * breadth["Pct_Above_EMA50"]
        + 30 * breadth["Pct_Above_EMA20"]
        + 15 * (breadth["Advance_Count"] / (breadth["Advance_Count"] + breadth["Decline_Count"] + 1e-6))
        + 15 * (breadth["Nifty_52Week_High_Count"] / (breadth["Nifty_52Week_High_Count"] + breadth["Nifty_52Week_Low_Count"] + 1e-6))
).fillna(0)
    # Set Date as index so breadth can be merged by date
    breadth = breadth.set_index("Date")
    return breadth


# ==========================================================
# MARKET REGIME / SCORES
# ==========================================================

def compute_market_regime(nifty_features, breadth_df):
    """
    Compute 5-level market regime from Nifty trend + breadth + volatility.

    Returns Series with values in {Strong Bull, Bull, Neutral, Bear, Strong Bear}.
    """
    if nifty_features.empty:
        return pd.Series(dtype=str)

    df = nifty_features.copy()
    df["_vol"] = df.get("NIFTY_Rolling_Volatility", pd.Series(20 * np.ones(len(df)), index=df.index))
    # Trend score based on EMA20 vs EMA50 and returns
    trend = np.sign(df["NIFTY_Close"].sub(df["NIFTY_EMA50"])).fillna(0)
    short = np.sign(df["NIFTY_Close"].sub(df["NIFTY_EMA20"])).fillna(0)
    m20 = df["NIFTY_20D_Return"].fillna(0)
    vol = df["_vol"].fillna(20)

    score = 0.0
    score += 2 * trend
    score += 1 * short
    score += 0.5 * np.sign(m20)
    score += -0.02 * (vol - 20)

    def label(s):
        if s >= 2.5:
            return "Strong_Bull"
        elif s >= 1.0:
            return "Bull"
        elif s <= -2.5:
            return "Strong_Bear"
        elif s <= -1.0:
            return "Bear"
        else:
            return "Neutral"

    regime = score.apply(label)
    df["Market_Regime"] = regime
    # One-hot regime features
    for r in ["Strong_Bull", "Bull", "Neutral", "Bear", "Strong_Bear"]:
        df[f"Regime_{r}"] = (regime == r).astype(int)
    return df


def compute_market_strength(nifty_features, breadth_df):
    """Market Strength Score (0-100)."""
    if nifty_features.empty:
        return pd.Series(dtype=float)
    df = nifty_features.copy()
    es = 0.0
    es += 40 * np.sign(df["NIFTY_Close"].sub(df["NIFTY_EMA50"])).fillna(0)
    es += 20 * np.sign(df["NIFTY_Close"].sub(df["NIFTY_EMA20"])).fillna(0)
    es += 20 * np.sign(df["NIFTY_20D_Return"]).fillna(0)
    es += 10 * (df["NIFTY_RSI"].sub(50).div(50)).clip(-1, 1).fillna(0)
    mss = 50 + es
    return mss.clip(0, 100)


def compute_market_alignment(stock_df, sector_df=None, market_df=None):
    """
    Market Alignment Score: how aligned stock trend, sector trend, market trend are.
    Returns Series in [-3, 3].
    """
    score = pd.Series(0.0, index=stock_df.index)
    if "Close" in stock_df.columns:
        score += np.sign(stock_df["Close"].sub(stock_df.get("EMA50", stock_df["Close"]))).fillna(0)
    if sector_df is not None and "SECTOR_Close" in sector_df.columns:
        score += np.sign(sector_df["SECTOR_Close"].sub(sector_df.get("SECTOR_EMA50", sector_df["SECTOR_Close"]))).fillna(0)
    if market_df is not None and "NIFTY_Close" in market_df.columns:
        score += np.sign(market_df["NIFTY_Close"].sub(market_df.get("NIFTY_EMA50", market_df["NIFTY_Close"]))).fillna(0)
    return score


def compute_trend_consensus(stock_df, market_df=None):
    """
    Trend Consensus Score: combine EMA alignment, RSI, MACD, relative strength.
    Returns Series in [-1, 1].
    """
    score = pd.Series(0.0, index=stock_df.index)
    if "EMA20" in stock_df and "EMA50" in stock_df:
        score += np.sign(stock_df["EMA20"].sub(stock_df["EMA50"])).fillna(0)
    if "RSI" in stock_df:
        score += np.sign(stock_df["RSI"].sub(50)).fillna(0)
    if "MACD_HIST" in stock_df:
        score += np.sign(stock_df["MACD_HIST"]).fillna(0)
    if "ADX" in stock_df:
        score += np.sign(stock_df["ADX"].sub(20)).fillna(0)
    # Normalize to [-1, 1]
    return score / 4.0
