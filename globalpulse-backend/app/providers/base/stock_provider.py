"""
GlobalPulse Stock Data Provider Interface
Defines the abstract interface for fetching stock price series and company metadata.
Allows switching seamlessly between providers (yfinance, Finnhub, etc.).
"""
from abc import ABC, abstractmethod
from typing import Optional
try:
    import pandas as pd
except ImportError:
    pd = None


class StockMarketDataProvider(ABC):
    """Abstract base class for stock market data providers."""

    @abstractmethod
    async def get_historical_prices(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch historical price DataFrame for a ticker symbol.
        Must return columns: ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'].
        """
        pass

    async def get_batch_historical_prices(
        self,
        symbols: list[str],
        period: str = "1mo",
        interval: str = "1d",
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch historical price DataFrames in batch for multiple ticker symbols.
        Returns a mapping of symbol -> pd.DataFrame.
        """
        results = {}
        for s in symbols:
            try:
                df = await self.get_historical_prices(s, period=period, interval=interval)
                results[s] = df
            except Exception:
                continue
        return results

    @abstractmethod
    async def close(self) -> None:
        """Close any underlying HTTP/network connections."""
        pass

