"""
GlobalPulse Forex Domain Model
Internal normalized representation of a foreign exchange rate pair.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class NormalizedForexPair:
    """
    Provider-agnostic FX pair snapshot.

    rate is None when the provider does not return a valid price.
    Never substitute zero for a missing rate.
    """

    symbol: str                        # Concatenated pair e.g. "USDINR", "EURUSD"
    base_currency: str                 # e.g. "USD"
    quote_currency: str                # e.g. "INR"
    rate: Optional[float]              # Exchange rate; None if unavailable
    change: Optional[float]            # Absolute change; None if unavailable
    change_percent: Optional[float]    # Percentage change; None if unavailable
    timestamp_utc: str                 # Snapshot time in UTC (ISO 8601)
    timestamp_ist: str                 # Snapshot time in IST / Asia/Kolkata (ISO 8601)
    source: str                        # e.g. "TRADING_ECONOMICS"
