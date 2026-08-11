"""
GlobalPulse Commodity Domain Model
Internal normalized representation of a commodity price record.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CommodityCategory(str, Enum):
    """Broad commodity classification used by GlobalPulse."""

    ENERGY = "ENERGY"
    METALS = "METALS"
    AGRICULTURE = "AGRICULTURE"
    OTHER = "OTHER"


@dataclass(frozen=True)
class NormalizedCommodity:
    """
    Provider-agnostic commodity snapshot.

    price is None when unavailable — never defaulted to zero.
    change and change_percent may be None when intraday data is absent.
    """

    symbol: str                        # e.g. "WTICOILNYM", "BRENT", "XAUUSD"
    name: str                          # Human-readable name e.g. "WTI Crude Oil"
    category: CommodityCategory        # Normalized GlobalPulse category
    price: Optional[float]             # Latest price; None if unavailable
    currency: str                      # Trading currency e.g. "USD"
    unit: Optional[str]                # Unit string e.g. "barrel", "troy oz"; None if absent
    change: Optional[float]            # Absolute price change; None if unavailable
    change_percent: Optional[float]    # Percentage change; None if unavailable
    timestamp_utc: str                 # Snapshot time in UTC (ISO 8601)
    timestamp_ist: str                 # Snapshot time in IST / Asia/Kolkata (ISO 8601)
    source: str                        # e.g. "TRADING_ECONOMICS"
