"""GlobalPulse Pydantic Schemas — Market listing response."""
from typing import Optional
from pydantic import BaseModel, Field


class TradingSessionSchema(BaseModel):
    open_time: str = Field(..., description="Session open time (local exchange time, HH:MM)")
    close_time: str = Field(..., description="Session close time (local exchange time, HH:MM)")


class ExchangeSchema(BaseModel):
    exchange_code: str = Field(..., description="Short exchange code, e.g. 'NSE'")
    exchange_name: str = Field(..., description="Full exchange name")
    country: str = Field(..., description="Country where the exchange is located")
    timezone: str = Field(..., description="IANA timezone string, e.g. 'Asia/Kolkata'")
    currency: str = Field(..., description="Primary trading currency, e.g. 'INR'")
    trading_days: list[int] = Field(..., description="ISO weekday integers (0=Mon … 4=Fri)")
    sessions: list[TradingSessionSchema] = Field(
        ..., description="Trading session windows (multiple = intraday breaks supported)"
    )


class MarketListResponse(BaseModel):
    exchanges: list[ExchangeSchema]
    total: int
