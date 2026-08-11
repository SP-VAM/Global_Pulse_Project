"""
GlobalPulse MarketStatusService
Determines market open/closed status for all supported exchanges.

Phase 1C implementation:
  - OPEN / CLOSED based on: weekday + multi-session windows (local exchange time).
  - DST handled automatically via zoneinfo (America/New_York, Europe/London, etc.).
  - Multi-session exchanges (TSE, HKEX) correctly modeled with TradingSession[].
  - holiday_calendar_applied is always False in Phase 1C — no holiday calendar engine.
    This flag is surfaced in the API response for consumer transparency.

Phase 1C known limitation:
  - Public holidays will not be detected. A weekday exchange session that coincides
    with a public holiday will report OPEN incorrectly.
  - Future phase: Holiday calendar engine with per-exchange holiday lists.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.timezone import TimezoneService
from app.domain.exchange import (
    ExchangeMetadata,
    get_all_exchanges,
    get_exchange_by_code,
)
from app.domain.market import MarketStatus, TradingSession
from app.core.exceptions import InvalidExchangeError
from app.schemas.market_status import MarketStatusResponse
from app.utils.datetime_utils import to_iso

logger = logging.getLogger(__name__)

# Phase 1C: Holiday calendar is not applied
_HOLIDAY_CALENDAR_APPLIED = False


class MarketStatusService:
    """
    Determines real-time market status for GlobalPulse supported exchanges.

    Status is computed from:
        1. Current UTC time → converted to exchange local time (via zoneinfo, DST-aware)
        2. ISO weekday check against exchange trading_days
        3. Local time check against each TradingSession window
    """

    def get_all_statuses(self) -> list[MarketStatusResponse]:
        """Return status for all supported exchanges."""
        return [self._compute_status(ex) for ex in get_all_exchanges()]

    def get_status_by_exchange(self, exchange_code: str) -> MarketStatusResponse:
        """
        Return status for a single exchange by code.

        Raises:
            InvalidExchangeError: If the exchange code is not in the registry.
        """
        exchange = get_exchange_by_code(exchange_code.upper())
        if exchange is None:
            raise InvalidExchangeError(
                f"Exchange '{exchange_code}' is not supported by GlobalPulse. "
                "Check /api/v1/markets for the list of supported exchanges."
            )
        return self._compute_status(exchange)

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    def _compute_status(self, exchange: ExchangeMetadata) -> MarketStatusResponse:
        """Compute the full market status payload for a single exchange."""
        now_utc = datetime.now(tz=timezone.utc)
        now_local = TimezoneService.utc_to_local(now_utc, exchange.timezone)
        now_ist = TimezoneService.utc_to_ist(now_utc)

        local_time = now_local.time()
        weekday = now_local.weekday()  # 0=Mon … 6=Sun

        is_trading_day = exchange.is_trading_day(weekday)
        active_session = exchange.active_session_for(local_time) if is_trading_day else None

        if active_session is not None:
            status = MarketStatus.OPEN
            next_open_utc = None
            next_open_ist = None
            next_close_utc, next_close_ist = self._next_close(
                exchange, now_local, active_session
            )
        else:
            status = MarketStatus.CLOSED
            next_close_utc = None
            next_close_ist = None
            next_open_utc, next_open_ist = self._next_open(exchange, now_local)

        logger.debug(
            "MarketStatus | exchange=%s | status=%s | local=%s",
            exchange.exchange_code,
            status,
            now_local.isoformat(),
        )

        return MarketStatusResponse(
            exchange=exchange.exchange_code,
            country=exchange.country,
            session_status=status,
            holiday_calendar_applied=_HOLIDAY_CALENDAR_APPLIED,
            exchange_local_time=to_iso(now_local),
            current_time_utc=to_iso(now_utc),
            current_time_ist=to_iso(now_ist),
            next_open_utc=next_open_utc,
            next_open_ist=next_open_ist,
            next_close_utc=next_close_utc,
            next_close_ist=next_close_ist,
        )

    def _next_close(
        self,
        exchange: ExchangeMetadata,
        now_local: datetime,
        active_session: TradingSession,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Compute the next session close time (current active session close).
        Returns (utc_iso, ist_iso).
        """
        close_local = now_local.replace(
            hour=active_session.close_time.hour,
            minute=active_session.close_time.minute,
            second=0,
            microsecond=0,
        )
        close_utc = TimezoneService.local_to_utc(close_local, exchange.timezone)
        close_ist = TimezoneService.utc_to_ist(close_utc)
        return to_iso(close_utc), to_iso(close_ist)

    def _next_open(
        self,
        exchange: ExchangeMetadata,
        now_local: datetime,
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Compute the next session open time.
        Searches forward up to 7 days to find the next trading day with sessions.
        Returns (utc_iso, ist_iso), or (None, None) if no sessions are configured.
        """
        if not exchange.sessions:
            return None, None

        # First check: is there a later session today (handles intraday breaks)?
        local_time = now_local.time()
        for session in exchange.sessions:
            if session.open_time > local_time and exchange.is_trading_day(now_local.weekday()):
                open_local = now_local.replace(
                    hour=session.open_time.hour,
                    minute=session.open_time.minute,
                    second=0,
                    microsecond=0,
                )
                open_utc = TimezoneService.local_to_utc(open_local, exchange.timezone)
                open_ist = TimezoneService.utc_to_ist(open_utc)
                return to_iso(open_utc), to_iso(open_ist)

        # Search forward for the next trading day
        first_session = exchange.sessions[0]
        candidate = now_local + timedelta(days=1)
        for _ in range(7):
            if exchange.is_trading_day(candidate.weekday()):
                open_local = candidate.replace(
                    hour=first_session.open_time.hour,
                    minute=first_session.open_time.minute,
                    second=0,
                    microsecond=0,
                )
                open_utc = TimezoneService.local_to_utc(open_local, exchange.timezone)
                open_ist = TimezoneService.utc_to_ist(open_utc)
                return to_iso(open_utc), to_iso(open_ist)
            candidate += timedelta(days=1)

        return None, None
