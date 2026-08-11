"""
Finnhub raw response models.
These Pydantic models represent Finnhub's wire format.
They are NEVER exposed via GlobalPulse APIs — only used internally for parsing.
"""
from typing import Optional
from pydantic import BaseModel, Field


class FinnhubQuote(BaseModel):
    """
    Finnhub GET /quote response.
    https://finnhub.io/docs/api/quote

    Note: Finnhub /quote does NOT return currency.
    Currency must be sourced from the company profile endpoint.
    """

    c: Optional[float] = Field(None, description="Current price")
    d: Optional[float] = Field(None, description="Change")
    dp: Optional[float] = Field(None, description="Percent change")
    h: Optional[float] = Field(None, description="High price of the day")
    l: Optional[float] = Field(None, description="Low price of the day")
    o: Optional[float] = Field(None, description="Open price of the day")
    pc: Optional[float] = Field(None, description="Previous close price")
    t: Optional[int] = Field(None, description="Unix timestamp of the quote")


class FinnhubProfile(BaseModel):
    """
    Finnhub GET /stock/profile2 response.
    https://finnhub.io/docs/api/company-profile2

    Coverage note: Availability depends on the provider plan and exchange.
    If Finnhub returns an empty object {}, InstrumentNotFoundError is raised.
    Data is never invented for missing fields.
    """

    ticker: Optional[str] = None
    name: Optional[str] = None
    exchange: Optional[str] = None
    country: Optional[str] = None
    finnhubIndustry: Optional[str] = None
    currency: Optional[str] = None
    ipo: Optional[str] = None
    logo: Optional[str] = None
    marketCapitalization: Optional[float] = None
    shareOutstanding: Optional[float] = None
    weburl: Optional[str] = None
    phone: Optional[str] = None
