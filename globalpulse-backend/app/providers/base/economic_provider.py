"""
GlobalPulse Abstract Economic Data Provider
All economic/macro data providers must implement this interface.
The service layer interacts only with EconomicDataProvider — never directly with Trading Economics.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from app.domain.bond import NormalizedBond
from app.domain.commodity import NormalizedCommodity
from app.domain.economic_event import NormalizedEconomicEvent
from app.domain.forex import NormalizedForexPair


class EconomicDataProvider(ABC):
    """
    Abstract interface for economic and macro data providers.

    Implementations:
        - TradingEconomicsProvider

    Future providers (e.g. FRED, World Bank, Alpha Vantage) can be added
    without changing the service layer.

    Important: Do not create stub/fake implementations of methods that are
    not supported by the configured subscription. Raise ProviderFeatureUnavailableError
    instead of returning fabricated data.
    """

    @abstractmethod
    async def get_calendar(
        self,
        country: Optional[str] = None,
        category: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        importance: Optional[str] = None,
        limit: int = 50,
    ) -> List[NormalizedEconomicEvent]:
        """
        Fetch economic calendar events.

        Args:
            country:    Filter by country name (provider-accepted format).
            category:   Filter by event category (provider-accepted format).
            from_date:  Start of date range (inclusive).
            to_date:    End of date range (inclusive).
            importance: Filter by importance level (LOW/MEDIUM/HIGH).
            limit:      Maximum number of events to return.

        Returns:
            List of NormalizedEconomicEvent. Empty list if no events match.

        Raises:
            ProviderFeatureUnavailableError: Endpoint not available under current plan.
            ProviderUnavailableError:        Network error, timeout, or malformed response.
            ProviderRateLimitError:          Provider returned HTTP 429.
            ProviderAuthenticationError:     Provider rejected the API key (HTTP 401).
        """
        ...

    @abstractmethod
    async def get_commodities(
        self,
        category: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> List[NormalizedCommodity]:
        """
        Fetch commodity price snapshots.

        Args:
            category: Optional CommodityCategory filter (ENERGY/METALS/AGRICULTURE/OTHER).
            symbol:   Optional specific commodity symbol.

        Raises:
            ProviderFeatureUnavailableError: Endpoint not available under current plan.
            ProviderUnavailableError:        Network/timeout/malformed response.
            ProviderRateLimitError:          HTTP 429.
            ProviderAuthenticationError:     HTTP 401.
        """
        ...

    @abstractmethod
    async def get_forex(
        self,
        symbols: Optional[List[str]] = None,
    ) -> List[NormalizedForexPair]:
        """
        Fetch foreign exchange rate snapshots.

        Args:
            symbols: Optional list of pair symbols to filter e.g. ['USDINR', 'EURUSD'].

        Raises:
            ProviderFeatureUnavailableError: Endpoint not available under current plan.
            ProviderUnavailableError:        Network/timeout/malformed response.
            ProviderRateLimitError:          HTTP 429.
            ProviderAuthenticationError:     HTTP 401.
        """
        ...

    @abstractmethod
    async def get_bond_yields(
        self,
        countries: Optional[List[str]] = None,
    ) -> List[NormalizedBond]:
        """
        Fetch government bond yield snapshots.

        Args:
            countries: Optional list of country names to filter.

        Raises:
            ProviderFeatureUnavailableError: Endpoint not available under current plan.
                                             This is the expected error on basic plans.
            ProviderUnavailableError:        Network/timeout/malformed response.
            ProviderRateLimitError:          HTTP 429.
            ProviderAuthenticationError:     HTTP 401.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release underlying HTTP client resources."""
        ...
