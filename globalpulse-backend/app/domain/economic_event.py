"""
GlobalPulse Economic Event Domain Model
Internal normalized representation of an economic calendar event.
Provider-specific fields are never exposed through this type.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EconomicEventCategory(str, Enum):
    """
    Normalized category for an economic calendar event.

    Mapping is performed deterministically by TradingEconomicsProvider
    using the provider's category string. No AI/LLM is used.
    """

    INTEREST_RATE = "INTEREST_RATE"
    INFLATION = "INFLATION"
    GDP = "GDP"
    EMPLOYMENT = "EMPLOYMENT"
    UNEMPLOYMENT = "UNEMPLOYMENT"
    CENTRAL_BANK = "CENTRAL_BANK"
    MANUFACTURING = "MANUFACTURING"
    SERVICES = "SERVICES"
    TRADE = "TRADE"
    CONSUMER = "CONSUMER"
    HOUSING = "HOUSING"
    GOVERNMENT = "GOVERNMENT"
    OTHER = "OTHER"


class EconomicImportance(str, Enum):
    """
    Normalized importance level for an economic event.

    Trading Economics uses integers 1–3 or strings.
    Absent/unrecognized values map to UNKNOWN rather than defaulting to LOW.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class NormalizedEconomicEvent:
    """
    Provider-agnostic economic calendar event.

    Fields marked Optional are None when the provider does not supply them.
    Missing numeric values are None — never substituted with zero.
    Timestamps are always ISO 8601 strings with timezone information.
    """

    id: str                              # Provider calendar ID or generated stable hash
    country: str                         # Country name as returned by provider
    event: str                           # Original provider event name (preserved)
    category: EconomicEventCategory      # Normalized GlobalPulse category
    importance: EconomicImportance       # Normalized importance level
    actual: Optional[float]              # Reported actual value; None if not yet released
    forecast: Optional[float]            # Analyst forecast; None if unavailable
    previous: Optional[float]            # Prior period value; None if unavailable
    unit: Optional[str]                  # Unit string e.g. "%", "M", "B"; None if absent
    timestamp_utc: str                   # Event datetime in UTC (ISO 8601)
    timestamp_ist: str                   # Event datetime in IST / Asia/Kolkata (ISO 8601)
    source: str                          # Data provider identifier e.g. "TRADING_ECONOMICS"
