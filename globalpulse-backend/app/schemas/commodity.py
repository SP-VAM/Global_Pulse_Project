"""GlobalPulse Pydantic Schemas — Commodity response."""
from typing import Optional, List

from pydantic import BaseModel, Field

from app.domain.commodity import CommodityCategory


class CommoditySchema(BaseModel):
    """API-facing representation of a normalized commodity price snapshot."""

    symbol: str = Field(..., description="Provider symbol e.g. 'WTICOILNYM', 'BRENT', 'XAUUSD'")
    name: str = Field(..., description="Human-readable name e.g. 'WTI Crude Oil'")
    category: CommodityCategory = Field(..., description="Normalized commodity category")
    price: Optional[float] = Field(None, description="Latest price; null if unavailable")
    currency: str = Field(..., description="Trading currency e.g. 'USD'")
    unit: Optional[str] = Field(None, description="Unit string e.g. 'barrel', 'troy oz'; null if absent")
    change: Optional[float] = Field(None, description="Absolute price change; null if unavailable")
    change_percent: Optional[float] = Field(None, description="Percentage change; null if unavailable")
    timestamp_utc: str = Field(..., description="Snapshot time in UTC (ISO 8601)")
    timestamp_ist: str = Field(..., description="Snapshot time in IST / Asia/Kolkata (ISO 8601)")
    source: str = Field(..., description="Data provider identifier")


class CommodityListResponse(BaseModel):
    """List of normalized commodity price snapshots."""

    commodities: List[CommoditySchema]
    total: int = Field(..., description="Total number of commodities in this response")
