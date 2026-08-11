"""
GlobalPulse Instrument Domain Model
Internal normalized representation of a financial instrument.
Never expose provider-raw models directly through this type.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.domain.market import AssetType


@dataclass(frozen=True)
class NormalizedInstrument:
    """
    Provider-agnostic instrument representation.

    Fields marked Optional may be null if the provider does not supply them.
    Never substitute invented values for missing data.
    """

    symbol: str
    name: Optional[str]
    exchange: Optional[str]
    country: Optional[str]
    asset_type: Optional[AssetType]
    currency: Optional[str]
    timezone: Optional[str]
    source: str  # e.g. "FINNHUB"


@dataclass(frozen=True)
class NormalizedQuote:
    """
    Provider-agnostic real-time quote representation.

    currency is NOT returned by Finnhub's /quote endpoint.
    It must be enriched from instrument/profile metadata when available.
    If unavailable, currency is None — never defaulted.

    timestampUtc and timestampIst are always timezone-aware ISO strings.
    """

    symbol: str
    price: Optional[float]
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    previous_close: Optional[float]
    change: Optional[float]
    change_percent: Optional[float]
    currency: Optional[str]      # Enriched from instrument metadata; null if unavailable
    timestamp_utc: str           # ISO 8601, UTC
    timestamp_ist: str           # ISO 8601, IST (Asia/Kolkata)
    source: str                  # e.g. "FINNHUB"
