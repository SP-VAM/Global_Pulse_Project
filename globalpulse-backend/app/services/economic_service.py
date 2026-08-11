"""
GlobalPulse Economic Service
Orchestrates economic and macro data operations via the provider interface.
Routers call EconomicService — never providers directly.

Responsibilities:
  - Date range validation (domain-level, not HTTP-level).
  - IST-day boundary computation for /economic-events/today.
  - Forwarding filters to the provider.
  - NOT calling providers directly from routers.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from app.core.exceptions import ValidationError
from app.core.timezone import TZ_UTC, TimezoneService
from app.domain.bond import NormalizedBond
from app.domain.commodity import NormalizedCommodity
from app.domain.economic_event import EconomicEventCategory, EconomicImportance, NormalizedEconomicEvent
from app.domain.forex import NormalizedForexPair
from app.providers.base.economic_provider import EconomicDataProvider

logger = logging.getLogger(__name__)

# Maximum date range allowed in a single request (prevents excessive provider calls)
_MAX_DATE_RANGE_DAYS = 90


class EconomicService:
    """
    Service layer for economic and macro data operations.

    Dependency direction:
        Router → EconomicService → EconomicDataProvider → Trading Economics
    """

    def __init__(self, provider: EconomicDataProvider) -> None:
        self._provider = provider

    # ------------------------------------------------------------------
    # Economic Calendar
    # ------------------------------------------------------------------

    async def get_economic_events(
        self,
        country: Optional[str] = None,
        category: Optional[EconomicEventCategory] = None,
        importance: Optional[EconomicImportance] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50,
    ) -> List[NormalizedEconomicEvent]:
        """
        Retrieve normalized economic calendar events with optional filters.

        Validates:
          - Date range does not exceed MAX_DATE_RANGE_DAYS.
          - from_date is not after to_date.
        """
        logger.info(
            "EconomicService.get_economic_events | country=%s category=%s importance=%s",
            country, category, importance,
        )

        if from_date and to_date and from_date > to_date:
            raise ValidationError("'from' date must not be after 'to' date.")

        if from_date and to_date:
            delta = (to_date - from_date).days
            if delta > _MAX_DATE_RANGE_DAYS:
                raise ValidationError(
                    f"Date range exceeds maximum of {_MAX_DATE_RANGE_DAYS} days. "
                    f"Requested range: {delta} days."
                )

        category_str = category.value if category else None
        importance_str = importance.value if importance else None

        return await self._provider.get_calendar(
            country=country,
            category=category_str,
            from_date=from_date,
            to_date=to_date,
            importance=importance_str,
            limit=limit,
        )

    async def get_economic_events_today(self) -> List[NormalizedEconomicEvent]:
        """
        Retrieve economic events for the current IST calendar day.

        "Today" is determined from the Indian user's perspective (Asia/Kolkata).
        The IST day boundaries are converted to UTC for the provider query.
        TimezoneService is used — no manual +05:30 offsets.
        """
        now_ist = TimezoneService.now_ist()
        logger.info(
            "EconomicService.get_economic_events_today | IST date=%s", now_ist.date()
        )

        # IST day: 00:00:00 IST to 23:59:59 IST (both timezone-aware)
        ist_start = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        ist_end = now_ist.replace(hour=23, minute=59, second=59, microsecond=0)

        # Convert IST boundaries to UTC via astimezone (zoneinfo handles DST automatically)
        utc_start_dt = ist_start.astimezone(TZ_UTC)
        utc_end_dt = ist_end.astimezone(TZ_UTC)

        logger.debug(
            "Today IST [%s → %s] → UTC [%s → %s]",
            ist_start.isoformat(), ist_end.isoformat(),
            utc_start_dt.isoformat(), utc_end_dt.isoformat(),
        )

        return await self._provider.get_calendar(
            from_date=utc_start_dt.date(),
            to_date=utc_end_dt.date(),
            limit=200,
        )

    # ------------------------------------------------------------------
    # Commodities
    # ------------------------------------------------------------------

    async def get_commodities(
        self,
        category: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> List[NormalizedCommodity]:
        """Retrieve normalized commodity price snapshots."""
        logger.info("EconomicService.get_commodities | category=%s symbol=%s", category, symbol)
        return await self._provider.get_commodities(category=category, symbol=symbol)

    # ------------------------------------------------------------------
    # Forex
    # ------------------------------------------------------------------

    async def get_forex(
        self,
        symbols: Optional[List[str]] = None,
    ) -> List[NormalizedForexPair]:
        """Retrieve normalized FX pair snapshots."""
        logger.info("EconomicService.get_forex | symbols=%s", symbols)
        return await self._provider.get_forex(symbols=symbols)

    # ------------------------------------------------------------------
    # Bond Yields
    # ------------------------------------------------------------------

    async def get_bond_yields(
        self,
        countries: Optional[List[str]] = None,
    ) -> List[NormalizedBond]:
        """
        Retrieve normalized government bond yield snapshots.
        Raises ProviderFeatureUnavailableError if the provider plan does not support bond data.
        """
        logger.info("EconomicService.get_bond_yields | countries=%s", countries)
        return await self._provider.get_bond_yields(countries=countries)
