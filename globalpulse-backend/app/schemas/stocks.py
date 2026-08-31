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
    predicted_direction: str = Field(..., description="'UP', 'DOWN', or 'HOLD'")
    confidence_percent: float = Field(..., description="Percentage confidence e.g. 78.4")
    prob_up: float
    prob_down: float
    prob_hold: float = Field(0.0, description="Probability of neutral/hold price movement (Class 2)")
    signal: str = Field(..., description="'BULLISH', 'BEARISH', or 'NEUTRAL'")


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


class StockTopMoverItemSchema(BaseModel):
    symbol: str = Field(..., description="Normalized ticker symbol e.g. RELIANCE")
    yahoo_ticker: str = Field(..., description="Yahoo ticker symbol e.g. RELIANCE.NS")
    company_name: str = Field(..., description="Company name e.g. Reliance Industries Ltd")
    current_price: float = Field(..., description="Current/latest closing price")
    previous_close: float = Field(..., description="Previous session closing price")
    change: float = Field(..., description="Absolute price change")
    change_percent: float = Field(..., description="Percentage price change")
    direction: str = Field(..., description="'up' or 'down'")


class StockTopMoversResponse(BaseModel):
    as_of: str = Field(..., description="ISO 8601 timestamp in IST e.g. 2026-08-24T10:35:00+05:30")
    as_of_formatted: str = Field(..., description="Human-readable timestamp e.g. 24 Aug, 10:35 AM")
    snapshot_timestamp: float = Field(..., description="Snapshot epoch timestamp")
    fetched_at: str = Field(..., description="ISO timestamp when snapshot was fetched")
    market_status: str = Field(..., description="'OPEN' or 'CLOSED'")
    is_stale: bool = Field(False, description="True if snapshot age > cache TTL (300s)")
    market: str = Field("NSE", description="Market identifier")
    universe: str = Field("NIFTY50", description="Stock universe")
    universe_count: int = Field(50, description="Total stocks in universe")
    valid_records: int = Field(..., description="Number of valid stock records in snapshot")
    failed_records: int = Field(0, description="Number of failed/unavailable stock records")
    movers: List[StockTopMoverItemSchema] = Field(default_factory=list, description="Top movers sorted by absolute change_percent descending")


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


class StockNewsArticleSchema(BaseModel):
    id: str = Field(..., description="Unique article ID or hash")
    title: str = Field(..., description="Article title/headline")
    sentiment: str = Field(..., description="'POSITIVE', 'NEGATIVE', or 'NEUTRAL'")
    confidence: str = Field(..., description="Confidence percentage string e.g. '95%'")
    source_date: str = Field(..., description="Source & publication date string e.g. 'Reuters • 3 hours ago'")
    excerpt: str = Field(..., description="Article snippet or summary")
    url: Optional[str] = Field(default="", description="Source article URL")


class StockNewsSentimentResponse(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g. RELIANCE)")
    company_name: str = Field(..., description="Full company name")
    net_sentiment: float = Field(..., description="Calculated net sentiment score in range [-1.0, 1.0]")
    sentiment_label: str = Field(..., description="'Bullish', 'Neutral', or 'Bearish'")
    articles_traced: int = Field(..., description="Total count of articles analyzed")
    positive_articles: int = Field(..., description="Count of positive articles")
    negative_articles: int = Field(..., description="Count of negative articles")
    neutral_articles: int = Field(..., description="Count of neutral articles")
    news_list: List[StockNewsArticleSchema] = Field(
        default_factory=list, description="List of analyzed news items"
    )


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
    news_sentiment: Optional[StockNewsSentimentResponse] = Field(
        default=None, description="Dynamic news sentiment analysis for the company"
    )


class StockMarketSnapshotItemSchema(BaseModel):
    symbol: str
    company_name: str
    current_price: float
    previous_close: float
    change: float
    change_percent: float
    market_cap: Optional[float] = Field(None, description="Live market capitalization in INR")
    volume: Optional[float] = Field(None, description="Latest trading volume")
    high_52w: Optional[float] = Field(None, description="52-week high price")
    low_52w: Optional[float] = Field(None, description="52-week low price")
    price_history: List[PriceHistoryPointSchema] = Field(
        default_factory=list, description="Latest 30 trading days closing price points for Sparkline rendering"
    )


class StockIndexQuoteSchema(BaseModel):
    symbol: str = Field("^NSEI", description="Authoritative index symbol e.g. ^NSEI")
    label: str = Field("NIFTY 50", description="Display index label")
    current_price: Optional[float] = Field(None, description="Authoritative index price level")
    previous_close: Optional[float] = Field(None, description="Index previous close level")
    change: Optional[float] = Field(None, description="Absolute daily change = current_price - previous_close")
    change_percent: Optional[float] = Field(None, description="Percentage daily change = (change / previous_close) * 100")
    timestamp_utc: Optional[str] = Field(None, description="ISO UTC timestamp of the index quote")
    timestamp_ist: Optional[str] = Field(None, description="ISO IST timestamp of the index quote")
    data_state: str = Field("LIVE", description="Data state: 'LIVE', 'STALE', or 'UNAVAILABLE'")
    is_live: bool = Field(True, description="True if quote is live fresh during open market hours")


class StockMarketSnapshotResponse(BaseModel):
    total: int
    items: List[StockMarketSnapshotItemSchema]
    index_quote: Optional[StockIndexQuoteSchema] = Field(None, description="Authoritative Nifty 50 Index quote payload")
    source: str = Field("cache", description="Data source e.g. cache, provider")
    cached: bool = Field(True, description="Whether data was served from cache")
    is_stale: bool = Field(False, description="Whether data is older than target freshness TTL")
    refresh_in_progress: bool = Field(False, description="Whether background provider refresh is running")
    updated_at: Optional[str] = Field(None, description="ISO timestamp of data update")


class StockHealthResponse(BaseModel):
    status: str
    active_provider: str
    model_loaded: bool
    label_encoder_loaded: bool
    feature_count: int
    supported_companies_count: int
    timestamp_utc: str

