"""
Trading Economics raw response models.
These Pydantic models represent the Trading Economics wire format.
They are NEVER exposed via GlobalPulse APIs — only used internally for parsing.

Field names follow Trading Economics API conventions (PascalCase).
All fields are Optional because provider plan and endpoint availability varies.
"""
from typing import Any, Optional

from pydantic import BaseModel, Field


class TECalendarEvent(BaseModel):
    """
    Raw Trading Economics calendar event.
    Endpoint: GET /calendar

    Note: Trading Economics returns dates as ISO strings without timezone info.
    The provider normalizes these to UTC using the assumption that TE dates are UTC.
    """

    CalendarId: Optional[str] = None
    Date: Optional[str] = None           # ISO string e.g. "2024-01-26T14:00:00"
    Country: Optional[str] = None
    Category: Optional[str] = None       # e.g. "Interest Rate", "Inflation Rate"
    Event: Optional[str] = None
    Reference: Optional[str] = None
    Source: Optional[str] = None
    Actual: Optional[Any] = None         # str or float depending on TE version
    Previous: Optional[Any] = None
    Forecast: Optional[Any] = None
    TEForecast: Optional[Any] = None
    URL: Optional[str] = None
    Importance: Optional[Any] = None     # int (1–3) or str
    Unit: Optional[str] = None
    Ticker: Optional[str] = None
    Symbol: Optional[str] = None


class TEMarketItem(BaseModel):
    """
    Raw Trading Economics market indicator item.
    Used for /markets/commodities, /markets/currency, /markets/bond.

    Close is the latest price/rate/yield value.
    """

    Symbol: Optional[str] = None
    Name: Optional[str] = None
    Date: Optional[str] = None           # ISO string
    Close: Optional[float] = None        # Latest value
    Open: Optional[float] = None
    High: Optional[float] = None
    Low: Optional[float] = None
    Change: Optional[float] = None       # Absolute change
    PercentualChange: Optional[float] = None   # Percentage change
    WeeklyChange: Optional[float] = None
    WeeklyPercentualChange: Optional[float] = None
    MonthlyChange: Optional[float] = None
    MonthlyPercentualChange: Optional[float] = None
    YearlyChange: Optional[float] = None
    YearlyPercentualChange: Optional[float] = None
    unit: Optional[str] = Field(None, alias="unit")   # Trading unit
    frequency: Optional[str] = None
    Type: Optional[str] = None           # e.g. "energy", "currency", "bond"
    Currency: Optional[str] = None

    model_config = {"populate_by_name": True}
