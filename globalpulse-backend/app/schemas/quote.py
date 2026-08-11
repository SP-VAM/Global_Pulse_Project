"""GlobalPulse Pydantic Schemas — Quote response."""
from typing import Optional
from pydantic import BaseModel, Field


class QuoteResponse(BaseModel):
    symbol: str = Field(..., description="Instrument ticker symbol")
    price: Optional[float] = Field(None, description="Current market price")
    open: Optional[float] = Field(None, description="Opening price for the session")
    high: Optional[float] = Field(None, description="Intraday high price")
    low: Optional[float] = Field(None, description="Intraday low price")
    previous_close: Optional[float] = Field(None, description="Previous session closing price")
    change: Optional[float] = Field(None, description="Absolute price change from previous close")
    change_percent: Optional[float] = Field(None, description="Percentage change from previous close")
    currency: Optional[str] = Field(
        None,
        description=(
            "Trading currency (e.g. 'USD'). Enriched from instrument metadata; "
            "null if unavailable — Finnhub /quote does not return currency directly."
        ),
    )
    timestamp_utc: str = Field(..., description="Quote timestamp in UTC (ISO 8601)")
    timestamp_ist: str = Field(..., description="Quote timestamp in IST (Asia/Kolkata, ISO 8601)")
    source: str = Field(..., description="Data provider source identifier, e.g. 'FINNHUB'")
