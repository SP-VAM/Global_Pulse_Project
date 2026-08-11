"""GlobalPulse Pydantic Schemas — Forex pair response."""
from typing import Optional, List

from pydantic import BaseModel, Field


class ForexPairSchema(BaseModel):
    """API-facing representation of a normalized FX pair snapshot."""

    symbol: str = Field(..., description="Concatenated pair symbol e.g. 'USDINR', 'EURUSD'")
    base_currency: str = Field(..., description="Base currency ISO code e.g. 'USD'")
    quote_currency: str = Field(..., description="Quote currency ISO code e.g. 'INR'")
    rate: Optional[float] = Field(None, description="Exchange rate; null if unavailable")
    change: Optional[float] = Field(None, description="Absolute rate change; null if unavailable")
    change_percent: Optional[float] = Field(None, description="Percentage change; null if unavailable")
    timestamp_utc: str = Field(..., description="Snapshot time in UTC (ISO 8601)")
    timestamp_ist: str = Field(..., description="Snapshot time in IST / Asia/Kolkata (ISO 8601)")
    source: str = Field(..., description="Data provider identifier")


class ForexListResponse(BaseModel):
    """List of normalized FX pair snapshots."""

    pairs: List[ForexPairSchema]
    total: int = Field(..., description="Total number of pairs in this response")
