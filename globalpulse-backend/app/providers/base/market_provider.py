"""
GlobalPulse Abstract Market Data Provider
All market data providers must implement this interface.
The rest of GlobalPulse interacts only with MarketDataProvider — never directly with Finnhub.
"""
from abc import ABC, abstractmethod

from app.domain.instrument import NormalizedInstrument, NormalizedQuote


class MarketDataProvider(ABC):
    """
    Abstract interface for market data providers.

    Implementations:
        - FinnhubMarketProvider

    Future providers can be added (e.g., Alpha Vantage, Polygon.io) without
    changing the service layer.
    """

    @abstractmethod
    async def get_quote(self, symbol: str) -> NormalizedQuote:
        """
        Fetch a real-time or delayed quote for the given symbol.

        Args:
            symbol: Ticker symbol, e.g. 'AAPL', 'RELIANCE.NS'.

        Returns:
            NormalizedQuote with currency=None if not available from the provider.

        Raises:
            InstrumentNotFoundError: Symbol not found or provider returned empty data.
            ProviderUnavailableError: Network error, timeout, or malformed response.
            ProviderRateLimitError: Provider returned HTTP 429.
            ProviderAuthenticationError: Provider rejected the API key.
        """
        ...

    @abstractmethod
    async def get_instrument(self, symbol: str) -> NormalizedInstrument:
        """
        Fetch normalized instrument/company profile for the given symbol.

        Args:
            symbol: Ticker symbol, e.g. 'AAPL'.

        Returns:
            NormalizedInstrument with nullable fields where provider data is absent.

        Raises:
            InstrumentNotFoundError: Symbol not found or provider returned empty profile.
                                     May occur due to exchange/plan coverage limitations.
            ProviderUnavailableError: Network error, timeout, or malformed response.
            ProviderRateLimitError: Provider returned HTTP 429.
            ProviderAuthenticationError: Provider rejected the API key.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release underlying HTTP client resources."""
        ...
