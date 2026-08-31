"""
GlobalPulse Technical Indicator Calculation Service
Calculates 20+ technical indicators mathematically from raw price DataFrames.
"""
from typing import Dict, Any
try:
    import numpy as np
except ImportError:
    np = None

try:
    import pandas as pd
except ImportError:
    pd = None


class TechnicalIndicatorService:
    """Computes technical analysis indicators on stock price series."""

    def compute_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute 20 technical indicators on a DataFrame containing
        ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'].
        Returns an enriched DataFrame.
        """
        if df.empty or len(df) < 5:
            return df

        data = df.copy()
        data = data.sort_values("Date").reset_index(drop=True)

        close = data["Close"].astype(float)
        high = data["High"].astype(float)
        low = data["Low"].astype(float)
        volume = data["Volume"].astype(float)

        # 1. Moving Averages
        data["SMA20"] = close.rolling(window=min(20, len(data)), min_periods=1).mean()
        data["SMA50"] = close.rolling(window=min(50, len(data)), min_periods=1).mean()
        data["SMA200"] = close.rolling(window=200, min_periods=50).mean()
        data["EMA20"] = close.ewm(span=min(20, len(data)), adjust=False).mean()
        data["EMA50"] = close.ewm(span=min(50, len(data)), adjust=False).mean()

        # 2. RSI (14)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14, min_periods=1).mean()
        avg_loss = loss.rolling(window=14, min_periods=1).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        data["RSI"] = 100 - (100 / (1 + rs))

        # 3. MACD
        ema12 = close.ewm(span=min(12, len(data)), adjust=False).mean()
        ema26 = close.ewm(span=min(26, len(data)), adjust=False).mean()
        data["MACD"] = ema12 - ema26
        data["MACD_SIGNAL"] = data["MACD"].ewm(span=min(9, len(data)), adjust=False).mean()
        data["MACD_HIST"] = data["MACD"] - data["MACD_SIGNAL"]

        # 4. Bollinger Bands (20, 2)
        std20 = close.rolling(window=min(20, len(data)), min_periods=1).std().fillna(0)
        data["BB_MIDDLE"] = data["SMA20"]
        data["BB_UPPER"] = data["BB_MIDDLE"] + (std20 * 2)
        data["BB_LOWER"] = data["BB_MIDDLE"] - (std20 * 2)

        # 5. ATR (14)
        prev_close = close.shift(1).fillna(close)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        data["ATR"] = tr.rolling(window=14, min_periods=1).mean()

        # 6. OBV (On-Balance Volume)
        direction = np.where(close > prev_close, 1, np.where(close < prev_close, -1, 0))
        data["OBV"] = (direction * volume).cumsum()

        # 7. Stochastic Oscillator (14, 3)
        low14 = low.rolling(window=14, min_periods=1).min()
        high14 = high.rolling(window=14, min_periods=1).max()
        stoch_k = 100 * (close - low14) / ((high14 - low14) + 1e-10)
        data["STOCH_K"] = stoch_k
        data["STOCH_D"] = stoch_k.rolling(window=3, min_periods=1).mean()

        # 8. ADX (14)
        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        tr_smooth = tr.rolling(window=14, min_periods=1).sum()
        plus_di = 100 * (pd.Series(plus_dm).rolling(window=14, min_periods=1).sum() / (tr_smooth + 1e-10))
        minus_di = 100 * (pd.Series(minus_dm).rolling(window=14, min_periods=1).sum() / (tr_smooth + 1e-10))
        dx = 100 * (plus_di - minus_di).abs() / ((plus_di + minus_di) + 1e-10)
        data["ADX"] = dx.rolling(window=14, min_periods=1).mean()

        # 9. Derived Returns & Volatility
        data["Daily_Return"] = close.pct_change().fillna(0) * 100
        data["Volatility"] = data["Daily_Return"].rolling(window=20, min_periods=1).std().fillna(0)
        data["Price_Change"] = close.diff().fillna(0)
        data["Price_Change_%"] = data["Daily_Return"]

        # Clean any Inf / NaN with warning logging
        nan_count = data.isnull().sum().sum()
        inf_count = np.isinf(data.select_dtypes(include=[np.number])).sum().sum()
        if nan_count > 0 or inf_count > 0:
            import logging
            logging.getLogger(__name__).debug(
                "Sanitizing %d NaN and %d Inf values in technical indicators dataframe",
                nan_count,
                inf_count,
            )
        data = data.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        return data

    def extract_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract latest technical indicators summary dict from enriched DataFrame."""
        if df.empty:
            return {}

        latest = df.iloc[-1]
        rsi = float(latest.get("RSI", 50.0))
        rsi_status = "OVERBOUGHT" if rsi >= 70 else ("OVERSOLD" if rsi <= 30 else "NEUTRAL")

        close = float(latest.get("Close", 0.0))
        sma20 = float(latest.get("SMA20", 0.0))
        sma50 = float(latest.get("SMA50", 0.0))
        trend_signal = "BULLISH" if close > sma20 >= sma50 else ("BEARISH" if close < sma20 <= sma50 else "NEUTRAL")

        return {
            "rsi_14": round(rsi, 2),
            "rsi_status": rsi_status,
            "macd": round(float(latest.get("MACD", 0.0)), 4),
            "macd_signal": round(float(latest.get("MACD_SIGNAL", 0.0)), 4),
            "macd_histogram": round(float(latest.get("MACD_HIST", 0.0)), 4),
            "bollinger_bands": {
                "upper": round(float(latest.get("BB_UPPER", 0.0)), 2),
                "middle": round(float(latest.get("BB_MIDDLE", 0.0)), 2),
                "lower": round(float(latest.get("BB_LOWER", 0.0)), 2),
            },
            "moving_averages": {
                "sma20": round(sma20, 2),
                "sma50": round(sma50, 2),
                "ema20": round(float(latest.get("EMA20", 0.0)), 2),
                "ema50": round(float(latest.get("EMA50", 0.0)), 2),
                "sma200": round(float(latest["SMA200"]), 2) if ("SMA200" in latest and not pd.isna(latest["SMA200"]) and float(latest["SMA200"]) > 0) else None,
            },
            "adx_14": round(float(latest.get("ADX", 0.0)), 2),
            "trend_signal": trend_signal,
        }
