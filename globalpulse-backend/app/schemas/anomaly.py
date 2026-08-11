"""
GlobalPulse Pydantic Schemas — Anomaly & Event Correlation API Response.

Exposes market anomaly details, detection method metadata, and correlation confidence.
Configured to serialize snake_case Python fields into frontend-friendly camelCase JSON.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod
from app.schemas.news import ArticleSchema
from app.schemas.dashboard import PaginationSchema


class AnomalyResponse(BaseModel):
    """API-facing representation of a detected market anomaly."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    anomaly_id: str = Field(..., description="Unique anomaly identifier e.g. 'anom-btc-20260728-001'")
    symbol: str = Field(..., description="Instrument symbol or ticker e.g. 'BTC/USD', 'AAPL'")
    asset_type: str = Field(..., description="Asset class: EQUITY | COMMODITY | FOREX | BOND | CRYPTO")
    metric: AnomalyMetric = Field(..., description="Anomaly metric e.g. PRICE_SPIKE, YIELD_CHANGE")
    current_value: float = Field(..., description="Price or yield at detection time")
    previous_value: Optional[float] = Field(None, description="Baseline value prior to movement")
    change_percent: float = Field(..., description="Percentage change over the observation window")
    observation_window: str = Field(..., description="Observation timeframe e.g. '15m', '30m', '1h'")
    severity: AnomalySeverity = Field(..., description="Presentation severity: HIGH | MEDIUM | LOW")
    detection_method: DetectionMethod = Field(
        ..., description="Detection method: DETERMINISTIC_THRESHOLD | STATISTICAL_ZSCORE"
    )
    detected_at_utc: str = Field(..., description="Detection timestamp in UTC (ISO 8601)")
    detected_at_ist: str = Field(..., description="Detection timestamp in IST (ISO 8601)")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional detection details")


class AnomalyListResponse(BaseModel):
    """Paginated list of detected market anomalies for Critical Alerts UI."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    anomalies: List[AnomalyResponse] = Field(..., description="List of detected anomalies")
    pagination: PaginationSchema = Field(..., description="Pagination metadata")


class CorrelatedEventResponse(BaseModel):
    """API-facing representation of a correlated anomaly and news event pair."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    correlation_id: str = Field(..., description="Unique correlation pair identifier")
    confidence_score: float = Field(..., description="Correlation confidence score between 0.00 and 1.00")
    match_reasons: List[str] = Field(..., description="Human-readable match explanations")
    anomaly: AnomalyResponse = Field(..., description="Associated market anomaly details")
    article: ArticleSchema = Field(..., description="Associated news article metadata")


class CorrelatedEventListResponse(BaseModel):
    """Paginated list of correlated event-anomaly pairs."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    correlations: List[CorrelatedEventResponse] = Field(..., description="List of correlated pairs")
    pagination: PaginationSchema = Field(..., description="Pagination metadata")


class EventCorrelationDetailResponse(BaseModel):
    """Detailed correlation analysis for a single news event."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    event_id: str = Field(..., description="Article / event identifier")
    headline: str = Field(..., description="Article headline")
    primary_category: str = Field(..., description="Primary classification category")
    published_at_utc: str = Field(..., description="Publication time in UTC (ISO 8601)")
    published_at_ist: str = Field(..., description="Publication time in IST (ISO 8601)")
    impact_level: str = Field(..., description="Calculated impact level: HIGH | MEDIUM | LOW")
    correlation_confidence: Optional[float] = Field(None, description="Max correlation confidence score")
    match_reasons: List[str] = Field(default_factory=list, description="Aggregated match explanations")
    correlated_anomalies: List[AnomalyResponse] = Field(
        default_factory=list, description="Associated market anomalies"
    )
