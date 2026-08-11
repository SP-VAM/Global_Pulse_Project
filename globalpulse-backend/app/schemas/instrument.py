"""GlobalPulse Pydantic Schemas — Instrument response."""
from typing import Optional
from pydantic import BaseModel, Field


class InstrumentResponse(BaseModel):
    symbol: str = Field(..., description="Ticker symbol as used by the provider")
    name: Optional[str] = Field(None, description="Company or instrument name")
    exchange: Optional[str] = Field(None, description="Exchange where the instrument is listed")
    country: Optional[str] = Field(None, description="Country of the instrument's primary listing")
    asset_type: Optional[str] = Field(None, description="Asset class, e.g. 'EQUITY', 'ETF'")
    currency: Optional[str] = Field(None, description="Trading currency from instrument metadata")
    timezone: Optional[str] = Field(
        None, description="Exchange IANA timezone, e.g. 'America/New_York'"
    )
    source: str = Field(..., description="Data provider source identifier, e.g. 'FINNHUB'")

    model_config = {"json_schema_extra": {
        "example": {
            "symbol": "AAPL",
            "name": "Apple Inc",
            "exchange": "NASDAQ",
            "country": "United States",
            "asset_type": "EQUITY",
            "currency": "USD",
            "timezone": "America/New_York",
            "source": "FINNHUB",
        }
    }}
