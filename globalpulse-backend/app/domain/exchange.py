"""
GlobalPulse Exchange Registry
Authoritative in-memory registry of all supported exchanges with metadata.

Phase 1C note:
  - Multi-session model (TradingSession[]) is fully supported.
  - TSE and HKEX are configured with actual session windows (morning + afternoon).
  - Complete intraday break accuracy across all exchanges is not guaranteed —
    that requires a full holiday/calendar engine (future phase).
  - Holiday calendars are NOT applied. market-status responses include
    holiday_calendar_applied=False to communicate this transparently.
"""
from __future__ import annotations

from datetime import time

from app.domain.market import ExchangeMetadata, TradingSession

# Weekday constants (ISO: Monday=0 ... Friday=4, Saturday=5, Sunday=6)
MON, TUE, WED, THU, FRI = 0, 1, 2, 3, 4
WEEKDAYS = [MON, TUE, WED, THU, FRI]


# ---------------------------------------------------------------------------
# Exchange Definitions
# ---------------------------------------------------------------------------

_EXCHANGES: list[ExchangeMetadata] = [
    # ── India ──────────────────────────────────────────────────────────────
    ExchangeMetadata(
        exchange_code="NSE",
        exchange_name="National Stock Exchange of India",
        country="India",
        timezone="Asia/Kolkata",
        currency="INR",
        trading_days=WEEKDAYS,
        sessions=[TradingSession(time(9, 15), time(15, 30))],
    ),
    ExchangeMetadata(
        exchange_code="BSE",
        exchange_name="BSE Limited (Bombay Stock Exchange)",
        country="India",
        timezone="Asia/Kolkata",
        currency="INR",
        trading_days=WEEKDAYS,
        sessions=[TradingSession(time(9, 15), time(15, 30))],
    ),
    # ── Singapore ──────────────────────────────────────────────────────────
    ExchangeMetadata(
        exchange_code="SGX",
        exchange_name="Singapore Exchange",
        country="Singapore",
        timezone="Asia/Singapore",
        currency="SGD",
        trading_days=WEEKDAYS,
        sessions=[TradingSession(time(9, 0), time(17, 0))],
    ),
    # ── Japan ──────────────────────────────────────────────────────────────
    # TSE has a lunch break: 09:00–11:30 and 12:30–15:30 local time.
    ExchangeMetadata(
        exchange_code="TSE",
        exchange_name="Tokyo Stock Exchange",
        country="Japan",
        timezone="Asia/Tokyo",
        currency="JPY",
        trading_days=WEEKDAYS,
        sessions=[
            TradingSession(time(9, 0), time(11, 30)),    # Morning session
            TradingSession(time(12, 30), time(15, 30)),  # Afternoon session
        ],
    ),
    # ── Hong Kong ──────────────────────────────────────────────────────────
    # HKEX has a lunch break: 09:30–12:00 and 13:00–16:00 local time.
    ExchangeMetadata(
        exchange_code="HKEX",
        exchange_name="Hong Kong Exchanges and Clearing",
        country="Hong Kong",
        timezone="Asia/Hong_Kong",
        currency="HKD",
        trading_days=WEEKDAYS,
        sessions=[
            TradingSession(time(9, 30), time(12, 0)),   # Morning session
            TradingSession(time(13, 0), time(16, 0)),   # Afternoon session
        ],
    ),
    # ── United States ──────────────────────────────────────────────────────
    # Offset handled by zoneinfo (EDT/EST transitions automatically).
    ExchangeMetadata(
        exchange_code="NYSE",
        exchange_name="New York Stock Exchange",
        country="United States",
        timezone="America/New_York",
        currency="USD",
        trading_days=WEEKDAYS,
        sessions=[TradingSession(time(9, 30), time(16, 0))],
    ),
    ExchangeMetadata(
        exchange_code="NASDAQ",
        exchange_name="Nasdaq Stock Market",
        country="United States",
        timezone="America/New_York",
        currency="USD",
        trading_days=WEEKDAYS,
        sessions=[TradingSession(time(9, 30), time(16, 0))],
    ),
    # ── United Kingdom ─────────────────────────────────────────────────────
    # Offset handled by zoneinfo (BST/GMT transitions automatically).
    ExchangeMetadata(
        exchange_code="LSE",
        exchange_name="London Stock Exchange",
        country="United Kingdom",
        timezone="Europe/London",
        currency="GBP",
        trading_days=WEEKDAYS,
        sessions=[TradingSession(time(8, 0), time(16, 30))],
    ),
    # ── Germany ────────────────────────────────────────────────────────────
    # Offset handled by zoneinfo (CEST/CET transitions automatically).
    ExchangeMetadata(
        exchange_code="XETRA",
        exchange_name="Deutsche Börse Xetra",
        country="Germany",
        timezone="Europe/Berlin",
        currency="EUR",
        trading_days=WEEKDAYS,
        sessions=[TradingSession(time(9, 0), time(17, 30))],
    ),
    # ── France ─────────────────────────────────────────────────────────────
    ExchangeMetadata(
        exchange_code="EURONEXT_PARIS",
        exchange_name="Euronext Paris",
        country="France",
        timezone="Europe/Paris",
        currency="EUR",
        trading_days=WEEKDAYS,
        sessions=[TradingSession(time(9, 0), time(17, 30))],
    ),
]


# ---------------------------------------------------------------------------
# Registry Interface
# ---------------------------------------------------------------------------

_CODE_INDEX: dict[str, ExchangeMetadata] = {
    ex.exchange_code: ex for ex in _EXCHANGES
}


def get_all_exchanges() -> list[ExchangeMetadata]:
    """Return all supported exchanges."""
    return list(_EXCHANGES)


def get_exchange_by_code(code: str) -> ExchangeMetadata | None:
    """
    Look up an exchange by its code (case-insensitive).
    Returns None if not found.
    """
    return _CODE_INDEX.get(code.upper())


def get_exchanges_by_country(country: str) -> list[ExchangeMetadata]:
    """Return all exchanges for a given country (case-insensitive match)."""
    country_lower = country.lower()
    return [ex for ex in _EXCHANGES if ex.country.lower() == country_lower]
