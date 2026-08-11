"""
GlobalPulse Phase 4A & 4C — Historical Data Pydantic Schemas.
Configured with camelCase aliases for API response contracts.
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.domain.anomaly import AnomalyMetric
from app.domain.india_impact import (
    CapitalFlowRisk,
    ImpactDirection,
    IndiaImpactLevel,
    TransmissionChannel,
)
from app.schemas.india_impact import IndianSectorImpactSchema
from app.schemas.pagination import PaginationSchema


class HistoricalAnomalyResponse(BaseModel):
    """API-facing representation of a historical market anomaly snapshot."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    snapshot_id: str = Field(..., description="Unique historical snapshot identifier")
    anomaly_id: str = Field(..., description="Source anomaly ID from Phase 2B")
    symbol: str = Field(..., description="Ticker symbol e.g. 'BRENT', 'USD/INR'")
    asset_type: str = Field(..., description="Asset class e.g. COMMODITY, FOREX, BOND, EQUITY")
    metric: AnomalyMetric = Field(..., description="Anomaly metric e.g. PRICE_SPIKE, PRICE_DROP")
    current_value: float = Field(..., description="Observed market price or yield")
    previous_value: Optional[float] = Field(None, description="Previous benchmark value")
    change_percent: float = Field(..., description="Percentage change or yield delta")
    detected_at_utc: str = Field(..., description="Detection timestamp in UTC (ISO 8601)")
    detected_at_ist: str = Field(..., description="Detection timestamp in IST (ISO 8601)")
    created_at_utc: str = Field(..., description="Snapshot archive creation timestamp in UTC")


class HistoricalImpactResponse(BaseModel):
    """API-facing representation of a historical India impact snapshot."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    snapshot_id: str = Field(..., description="Unique historical snapshot identifier")
    source_anomaly_id: Optional[str] = Field(None, description="Source anomaly ID if evaluated from market anomaly")
    source_event_id: Optional[str] = Field(None, description="Source event ID if evaluated from news/economic event")
    symbol: Optional[str] = Field(None, description="Ticker symbol evaluated")
    asset_type: Optional[str] = Field(None, description="Asset class evaluated")
    impact_score: float = Field(..., description="India impact score between 0.0 and 100.0")
    impact_level: IndiaImpactLevel = Field(..., description="India impact magnitude level")
    impact_direction: ImpactDirection = Field(..., description="Overall impact direction")
    capital_flow_risk: CapitalFlowRisk = Field(..., description="Capital flow risk assessment")
    transmission_channels: List[TransmissionChannel] = Field(..., description="Active transmission channels")
    affected_sectors: List[IndianSectorImpactSchema] = Field(..., description="Affected domestic sectors")
    has_correlation_evidence: bool = Field(..., description="True if accepted correlation evidence was present")
    correlated_event_ids: List[str] = Field(default_factory=list, description="IDs of accepted correlated events")
    correlation_count: int = Field(..., description="Count of accepted correlated events")
    top_correlation_confidence: Optional[float] = Field(None, description="Highest accepted correlation confidence score")
    assessed_at_utc: str = Field(..., description="Assessment timestamp in UTC (ISO 8601)")
    assessed_at_ist: str = Field(..., description="Assessment timestamp in IST (ISO 8601)")
    created_at_utc: str = Field(..., description="Snapshot archive creation timestamp in UTC")


class HistoricalAnomalyListResponse(BaseModel):
    """Paginated list of historical anomaly snapshots."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[HistoricalAnomalyResponse] = Field(..., description="List of historical anomaly snapshots")
    pagination: PaginationSchema = Field(..., description="Pagination metadata")


class HistoricalImpactListResponse(BaseModel):
    """Paginated list of historical India impact snapshots."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[HistoricalImpactResponse] = Field(..., description="List of historical impact snapshots")
    pagination: PaginationSchema = Field(..., description="Pagination metadata")


# ---------------------------------------------------------------------------
# Phase 4C Analytics Response Schemas
# ---------------------------------------------------------------------------


class AssetClassFrequencySchema(BaseModel):
    """API-facing asset class shock frequency and ratio."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    asset_type: str = Field(..., description="Asset class e.g. COMMODITY, FOREX, BOND, EQUITY")
    count: int = Field(..., description="Anomaly count in query window")
    ratio: float = Field(..., description="Prevalence ratio (0.00 to 1.00)")


class ChannelDistributionSchema(BaseModel):
    """API-facing transmission channel prevalence ratio."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    channel: TransmissionChannel = Field(..., description="Transmission channel identifier")
    count: int = Field(..., description="Number of assessments containing this channel")
    assessment_ratio: float = Field(..., description="Prevalence ratio across assessments (0.00 to 1.00)")


class SectorHitSummarySchema(BaseModel):
    """API-facing aggregate directional impact summary per domestic sector."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    sector_name: str = Field(..., description="Domestic industry sector e.g. PAINTS, IT_SERVICES")
    total_hits: int = Field(..., description="Total impact evaluations affecting this sector")
    negative_hits: int = Field(..., description="Count of NEGATIVE impacts")
    positive_hits: int = Field(..., description="Count of POSITIVE impacts")
    mixed_hits: int = Field(..., description="Count of MIXED impacts")
    neutral_hits: int = Field(..., description="Count of NEUTRAL impacts")
    primary_direction: ImpactDirection = Field(..., description="Deterministic primary impact direction")


class ImpactLevelCountSchema(BaseModel):
    """API-facing impact level count."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    impact_level: IndiaImpactLevel = Field(..., description="India impact level")
    count: int = Field(..., description="Occurrence count")


class HistoricalTrendAnalyticsResponse(BaseModel):
    """API-facing representation of complete aggregate trend analytics."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    total_anomalies_evaluated: int = Field(..., description="Total historical anomalies in window")
    total_impact_assessments_evaluated: int = Field(..., description="Total historical assessments in window")
    average_impact_score: float = Field(..., description="Average India impact score (0.0 to 100.0)")
    peak_impact_score: float = Field(..., description="Peak (maximum) India impact score")
    impact_level_counts: List[ImpactLevelCountSchema] = Field(..., description="Impact level breakdown")
    asset_class_frequencies: List[AssetClassFrequencySchema] = Field(..., description="Asset class shock frequencies")
    channel_distributions: List[ChannelDistributionSchema] = Field(..., description="Transmission channel distributions")
    sector_hit_summaries: List[SectorHitSummarySchema] = Field(..., description="Sector vulnerability hit summaries")
    correlated_evidence_count: int = Field(..., description="Count of evidence-backed assessments")
    correlation_evidence_ratio: float = Field(..., description="Prevalence ratio of evidence-backed assessments")
