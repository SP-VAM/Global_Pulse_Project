"""
GlobalPulse Bond / Government Yield Domain Model
Internal normalized representation of a government bond yield snapshot.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class NormalizedBond:
    """
    Provider-agnostic government bond yield snapshot.

    yield_value is None when unavailable — never substituted with zero.
    Availability depends heavily on the configured provider subscription plan.
    If the provider plan does not support bond data, the endpoint raises
    ProviderFeatureUnavailableError instead of returning fake data.
    """

    symbol: str                        # e.g. "USGG10YR", "INGB10YR"
    name: str                          # Human-readable e.g. "United States 10-Year"
    country: str                       # Country name
    maturity: str                      # e.g. "10Y", "2Y", "30Y"
    yield_value: Optional[float]       # Yield in percent; None if unavailable
    change: Optional[float]            # Absolute change in basis points; None if unavailable
    change_percent: Optional[float]    # Percentage change; None if unavailable
    timestamp_utc: str                 # Snapshot time in UTC (ISO 8601)
    timestamp_ist: str                 # Snapshot time in IST / Asia/Kolkata (ISO 8601)
    source: str                        # e.g. "TRADING_ECONOMICS"
