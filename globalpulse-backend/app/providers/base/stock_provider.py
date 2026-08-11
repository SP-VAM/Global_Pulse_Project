"""
GlobalPulse Stock Data Provider Interface
Defines the abstract interface for fetching stock price series and company metadata.
Allows switching seamlessly between providers (yfinance, Finnhub, etc.).
"""
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


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

    @abstractmethod
    async def close(self) -> None:
        """Close any underlying HTTP/network connections."""
        pass
