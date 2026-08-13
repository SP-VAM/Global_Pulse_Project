"""
GlobalPulse YFinance Stock Market Provider Implementation
Concrete implementation of StockMarketDataProvider wrapping yfinance with resilience.
"""
import asyncio
import logging
from typing import Optional
import pandas as pd
import yfinance as yf

from app.core.exceptions import NotFoundError, ProviderUnavailableError
from app.providers.base.stock_provider import StockMarketDataProvider

logger = logging.getLogger(__name__)


import time

class YFinanceMarketDataProvider(StockMarketDataProvider):
    """Fetches live and historical price data from Yahoo Finance."""

    def __init__(self) -> None:
        self._df_cache: dict = {}
        self._cache_ttl_seconds: float = 300.0  # 5 minutes cache TTL for fast responses

    async def get_historical_prices(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch historical price DataFrame for an Indian stock ticker (e.g., RELIANCE.NS).
        """
        cache_key = f"{symbol}_{period}_{interval}"
        now = time.time()
        if cache_key in self._df_cache:
            cached_df, cached_time = self._df_cache[cache_key]
            if now - cached_time < self._cache_ttl_seconds:
                return cached_df.copy()

        ticker_symbol = symbol if symbol.endswith(".NS") else f"{symbol}.NS"

        def _fetch_sync() -> pd.DataFrame:
            try:
                ticker = yf.Ticker(ticker_symbol)
                df = ticker.history(period=period, interval=interval)
                if df.empty:
                    # Retry without .NS if raw symbol provided
                    ticker_alt = yf.Ticker(symbol)
                    df = ticker_alt.history(period=period, interval=interval)
                return df
            except Exception as e:
                logger.warning("Error fetching yfinance data for %s: %s", ticker_symbol, e)
                return pd.DataFrame()

        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, _fetch_sync)

        if df.empty:
            raise NotFoundError(
                f"No price history found for stock symbol '{symbol}' (ticker '{ticker_symbol}')."
            )

        df = df.reset_index()
        # Standardize date column
        date_col = "Date" if "Date" in df.columns else df.columns[0]
        df.rename(columns={date_col: "Date"}, inplace=True)
        df["Date"] = pd.to_datetime(df["Date"])

        required_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
        for col in required_cols:
            if col not in df.columns:
                raise ProviderUnavailableError(
                    f"Required column '{col}' missing from price data for '{symbol}'"
                )

        result_df = df[required_cols].copy()
        self._df_cache[cache_key] = (result_df, now)
        return result_df

    async def close(self) -> None:
        """No persistent connection needed for yfinance."""
        pass
