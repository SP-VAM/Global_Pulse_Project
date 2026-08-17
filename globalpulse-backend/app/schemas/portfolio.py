"""
Pydantic Schemas for Investment Portfolio Management.
Serializes fields to camelCase for frontend compatibility.
"""
import math
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


def validate_max_13_digits(v: Optional[float]) -> Optional[float]:
    if v is not None:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Amount must be a finite number.")
        if v <= 0:
            raise ValueError("Amount must be greater than zero.")
        int_part = str(int(abs(v)))
        if len(int_part) > 13 or abs(v) > 9_999_999_999_999.99:
            raise ValueError("Amount cannot exceed 13 integer digits (max 9,999,999,999,999.99).")
    return v


class InvestmentCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    asset_type: Optional[str] = Field("STOCKS", description="STOCKS, MUTUAL_FUNDS, SIPS, ETFS")
    ticker: str = Field(..., min_length=1, max_length=50, description="Stock ticker e.g. RELIANCE.NS, TCS.NS, AAPL")
    company_name: str = Field(..., min_length=1, max_length=150)
    quantity: float = Field(..., gt=0, le=9_999_999_999_999.99)
    purchase_price: float = Field(..., gt=0, le=9_999_999_999_999.99)
    purchase_date: date
    exchange: Optional[str] = Field("NSE", max_length=20)
    broker_name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("quantity", "purchase_price")
    @classmethod
    def check_amounts(cls, v: float) -> float:
        return validate_max_13_digits(v)


class InvestmentUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    asset_type: Optional[str] = Field(None)
    ticker: Optional[str] = Field(None, min_length=1, max_length=50)
    company_name: Optional[str] = Field(None, min_length=1, max_length=150)
    quantity: Optional[float] = Field(None, gt=0, le=9_999_999_999_999.99)
    purchase_price: Optional[float] = Field(None, gt=0, le=9_999_999_999_999.99)
    purchase_date: Optional[date] = Field(None)
    exchange: Optional[str] = Field(None, max_length=20)
    broker_name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("quantity", "purchase_price")
    @classmethod
    def check_amounts(cls, v: Optional[float]) -> Optional[float]:
        return validate_max_13_digits(v)


class HoldingItem(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    investment_id: int
    user_id: int
    asset_type: str
    ticker: str
    company_name: str
    quantity: float
    purchase_price: float
    purchase_date: date
    exchange: Optional[str] = "NSE"
    broker_name: Optional[str] = None
    investment_source: str = "MANUAL"
    notes: Optional[str] = None
    created_at: datetime

    # Calculated Live Market Metrics
    current_price: float
    invested_value: float
    current_value: float
    total_gain_loss: float
    percentage_return: float
    todays_change: float
    todays_change_pct: float
    sparkline_points: List[float] = Field(default_factory=list)


class PortfolioSummaryResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    portfolio_value: float
    invested_amount: float
    total_profit_loss: float
    percentage_return: float
    todays_change: float
    total_holdings_count: int
    holdings: List[HoldingItem]
