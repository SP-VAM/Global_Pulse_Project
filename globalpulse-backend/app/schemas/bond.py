"""GlobalPulse Pydantic Schemas — Government bond / yield response."""
from typing import Optional, List

from pydantic import BaseModel, Field


class BondSchema(BaseModel):
    """API-facing representation of a normalized government bond yield snapshot."""

    symbol: str = Field(..., description="Provider symbol e.g. 'USGG10YR'")
    name: str = Field(..., description="Human-readable name e.g. 'United States 10-Year'")
    country: str = Field(..., description="Issuing country name")
    maturity: str = Field(..., description="Bond maturity e.g. '10Y', '2Y', '30Y'")
    yield_value: Optional[float] = Field(
        None, alias="yield",
        description="Yield in percent; null if unavailable",
    )
    change: Optional[float] = Field(None, description="Absolute yield change; null if unavailable")
    change_percent: Optional[float] = Field(None, description="Percentage change; null if unavailable")
    timestamp_utc: str = Field(..., description="Snapshot time in UTC (ISO 8601)")
    timestamp_ist: str = Field(..., description="Snapshot time in IST / Asia/Kolkata (ISO 8601)")
    source: str = Field(..., description="Data provider identifier")

    model_config = {"populate_by_name": True}


class BondListResponse(BaseModel):
    """List of normalized government bond yield snapshots."""

    bonds: List[BondSchema]
    total: int = Field(..., description="Total number of bonds in this response")
