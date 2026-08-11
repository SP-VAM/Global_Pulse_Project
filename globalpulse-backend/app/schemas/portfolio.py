"""
Pydantic Schemas for Investment Portfolio Management.
Serializes fields to camelCase for frontend compatibility.
"""
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class InvestmentCreate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    asset_type: Optional[str] = Field("STOCKS", description="STOCKS, MUTUAL_FUNDS, SIPS, ETFS")
    ticker: str = Field(..., description="Stock ticker e.g. RELIANCE.NS, TCS.NS, AAPL")
    company_name: str = Field(...)
    quantity: float = Field(..., gt=0)
    purchase_price: float = Field(..., gt=0)
    purchase_date: date
    exchange: Optional[str] = Field("NSE")
    broker_name: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)


class InvestmentUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    asset_type: Optional[str] = Field(None)
    ticker: Optional[str] = Field(None)
    company_name: Optional[str] = Field(None)
    quantity: Optional[float] = Field(None, gt=0)
    purchase_price: Optional[float] = Field(None, gt=0)
    purchase_date: Optional[date] = Field(None)
    exchange: Optional[str] = Field(None)
    broker_name: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)


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
