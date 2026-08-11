"""GlobalPulse Pydantic Schemas — Market status response."""
from typing import Optional
from pydantic import BaseModel, Field

from app.domain.market import MarketStatus


class MarketStatusResponse(BaseModel):
    exchange: str = Field(..., description="Exchange code, e.g. 'SGX'")
    country: str = Field(..., description="Country of the exchange")
    session_status: MarketStatus = Field(
        ...,
        description="Current session status based on weekday + session times. See holiday_calendar_applied.",
    )
    holiday_calendar_applied: bool = Field(
        False,
        description=(
            "Whether a holiday calendar was applied to determine status. "
            "Currently always false (Phase 1C limitation). "
            "OPEN status during a public holiday will not be detected without a calendar."
        ),
    )
    exchange_local_time: str = Field(
        ..., description="Current local time at the exchange (ISO 8601)"
    )
    current_time_utc: str = Field(..., description="Current UTC time (ISO 8601)")
    current_time_ist: str = Field(..., description="Current IST time (ISO 8601)")
    next_open_utc: Optional[str] = Field(
        None, description="Next session open time in UTC (ISO 8601)"
    )
    next_open_ist: Optional[str] = Field(
        None, description="Next session open time in IST (ISO 8601)"
    )
    next_close_utc: Optional[str] = Field(
        None, description="Next session close time in UTC (ISO 8601)"
    )
    next_close_ist: Optional[str] = Field(
        None, description="Next session close time in IST (ISO 8601)"
    )
