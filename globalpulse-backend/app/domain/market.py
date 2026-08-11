"""
GlobalPulse Exchange Domain Models
Represents exchange metadata and trading session windows.
Multi-session design supports exchanges with lunch breaks (TSE, HKEX, etc.)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from enum import Enum


class AssetType(str, Enum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    INDEX = "INDEX"
    FUND = "FUND"
    BOND = "BOND"
    CRYPTO = "CRYPTO"
    FOREX = "FOREX"
    COMMODITY = "COMMODITY"
    UNKNOWN = "UNKNOWN"


class MarketStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    # Reserved for future phases:
    # HOLIDAY = "HOLIDAY"
    # PRE_MARKET = "PRE_MARKET"
    # POST_MARKET = "POST_MARKET"
    # TRADING_BREAK = "TRADING_BREAK"


@dataclass(frozen=True)
class TradingSession:
    """
    Represents a single continuous trading session window (local exchange time).
    Multiple TradingSessions per exchange model intraday breaks.

    Example (TSE):
        sessions = [
            TradingSession(time(9, 0), time(11, 30)),   # Morning session
            TradingSession(time(12, 30), time(15, 30)), # Afternoon session
        ]
    """

    open_time: time   # Local exchange time
    close_time: time  # Local exchange time

    def is_within(self, local_time: time) -> bool:
        """Return True if local_time falls within this session window."""
        return self.open_time <= local_time < self.close_time


@dataclass(frozen=True)
class ExchangeMetadata:
    """
    Complete metadata for a supported exchange.

    trading_days: List of ISO weekday integers (Monday=0 … Sunday=6).
    sessions: Ordered list of TradingSession windows.
               Phase 1C: multi-session model supported;
               complete intraday break accuracy is not guaranteed for all exchanges.
    """

    exchange_code: str
    exchange_name: str
    country: str
    timezone: str          # IANA timezone key
    currency: str
    trading_days: list[int] = field(default_factory=list)
    sessions: list[TradingSession] = field(default_factory=list)

    def is_trading_day(self, weekday: int) -> bool:
        """Return True if ISO weekday (0=Mon … 6=Sun) is a trading day."""
        return weekday in self.trading_days

    def active_session_for(self, local_time: time) -> TradingSession | None:
        """Return the active TradingSession for a given local time, or None if closed."""
        for session in self.sessions:
            if session.is_within(local_time):
                return session
        return None
