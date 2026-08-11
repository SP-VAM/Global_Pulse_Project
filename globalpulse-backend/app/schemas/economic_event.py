"""GlobalPulse Pydantic Schemas — Economic event response."""
from typing import Optional, List

from pydantic import BaseModel, Field

from app.domain.economic_event import EconomicEventCategory, EconomicImportance


class EconomicEventSchema(BaseModel):
    """API-facing representation of a normalized economic calendar event."""

    id: str = Field(..., description="Provider calendar ID or generated stable identifier")
    country: str = Field(..., description="Country the event belongs to")
    event: str = Field(..., description="Original provider event name (preserved verbatim)")
    category: EconomicEventCategory = Field(
        ..., description="Normalized GlobalPulse event category"
    )
    importance: EconomicImportance = Field(
        ..., description="Normalized event importance level"
    )
    actual: Optional[float] = Field(None, description="Reported actual value; null if not yet released")
    forecast: Optional[float] = Field(None, description="Analyst consensus forecast; null if unavailable")
    previous: Optional[float] = Field(None, description="Prior period value; null if unavailable")
    unit: Optional[str] = Field(None, description="Unit string e.g. '%', 'M'; null if absent")
    timestamp_utc: str = Field(..., description="Event datetime in UTC (ISO 8601)")
    timestamp_ist: str = Field(..., description="Event datetime in IST / Asia/Kolkata (ISO 8601)")
    source: str = Field(..., description="Data provider identifier e.g. 'TRADING_ECONOMICS'")


class EconomicEventListResponse(BaseModel):
    """Paginated list of economic calendar events."""

    events: List[EconomicEventSchema]
    total: int = Field(..., description="Total number of events in this response")
