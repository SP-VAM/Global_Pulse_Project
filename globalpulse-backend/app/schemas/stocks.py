"""
GlobalPulse Stock Prediction API Pydantic Schemas
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CompanyItemSchema(BaseModel):
    symbol: str
    company_name: str
    yahoo_ticker: str


class StockCompanyListResponse(BaseModel):
    total: int
    companies: List[CompanyItemSchema]


class PriceHistoryPointSchema(BaseModel):
    date: str = Field(..., description="Trading date (YYYY-MM-DD)")
    close: float = Field(..., description="Daily closing price")


class FeatureImportanceSchema(BaseModel):
    feature: str
    importance: float


class PredictionDetailSchema(BaseModel):
    predicted_direction: str = Field(..., description="'UP' or 'DOWN'")
    confidence_percent: float = Field(..., description="Percentage confidence e.g. 78.4")
    prob_up: float
    prob_down: float
    signal: str = Field(..., description="'BULLISH' or 'BEARISH'")


class StockPredictionResponse(BaseModel):
    symbol: str
    company_name: str
    as_of_date: str
    current_close: float
    price_change: float = Field(0.0, description="Absolute daily price change")
    price_change_percent: float = Field(0.0, description="Daily percentage price change")
    prediction: PredictionDetailSchema
    top_influencing_features: List[FeatureImportanceSchema]
    sentiment_source: str
    price_history: List[PriceHistoryPointSchema] = Field(
        default_factory=list, description="Latest 30 trading days closing price points for Sparkline rendering"
    )


class BollingerBandsSchema(BaseModel):
    upper: float
    middle: float
    lower: float


class MovingAveragesSchema(BaseModel):
    sma20: float
    sma50: float
    ema20: float
    ema50: float
    sma200: Optional[float] = None


class TechnicalSummarySchema(BaseModel):
    rsi_14: float
    rsi_status: str
    macd: float
    macd_signal: float
    macd_histogram: float
    bollinger_bands: BollingerBandsSchema
    moving_averages: MovingAveragesSchema
    adx_14: float
    trend_signal: str


class TechnicalIndicatorsResponse(BaseModel):
    symbol: str
    period: str
    as_of_date: str
    summary: TechnicalSummarySchema


class HistoricalCandleSchema(BaseModel):
    date: str = Field(..., description="Trading date (YYYY-MM-DD)")
    price: float = Field(..., description="Daily closing price")
    open: float
    high: float
    low: float
    close: float
    volume: float
    sma20: Optional[float] = None
    sma50: Optional[float] = None
    sma200: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    upper_band: Optional[float] = None
    middle_band: Optional[float] = None
    lower_band: Optional[float] = None


class StockFullAnalysisResponse(BaseModel):
    symbol: str
    company_name: str
    period: str = Field("1y", description="Requested historical period e.g. 1d, 5d, 1mo, 3mo, 6mo, 1y, 5y")
    as_of_date: str
    current_close: float
    price_change: float = Field(0.0, description="Absolute daily price change")
    price_change_percent: float = Field(0.0, description="Daily percentage price change")
    prediction: PredictionDetailSchema
    technical_indicators: TechnicalSummarySchema
    top_influencing_features: List[FeatureImportanceSchema]
    sentiment_source: str
    price_history: List[PriceHistoryPointSchema] = Field(
        default_factory=list, description="Latest 30 trading days closing price points for Sparkline rendering"
    )
    historical_chart_data: List[HistoricalCandleSchema] = Field(
        default_factory=list, description="Full historical OHLCV candles with technical indicators for range charting"
    )


class StockMarketSnapshotItemSchema(BaseModel):
    symbol: str
    company_name: str
    current_price: float
    previous_close: float
    change: float
    change_percent: float
    market_cap: Optional[float] = Field(None, description="Live market capitalization in INR")
    price_history: List[PriceHistoryPointSchema] = Field(
        default_factory=list, description="Latest 30 trading days closing price points for Sparkline rendering"
    )


class StockMarketSnapshotResponse(BaseModel):
    total: int
    items: List[StockMarketSnapshotItemSchema]


class StockHealthResponse(BaseModel):
    status: str
    active_provider: str
    model_loaded: bool
    label_encoder_loaded: bool
    feature_count: int
    supported_companies_count: int
    timestamp_utc: str
