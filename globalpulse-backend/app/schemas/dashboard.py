"""
GlobalPulse Pydantic Schemas — Dashboard API Response.

Exposes normalized feed items, pagination metadata, and optional market context.
Configured to serialize snake_case Python fields into frontend-friendly camelCase JSON.
"""
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.domain.india_impact import TransmissionChannel
from app.schemas.india_impact import IndiaImpactResponse
from app.schemas.news import CompanyTagSchema


class ImpactLevel(str, Enum):
    """
    Event / article presentation impact level.
    Default is UNKNOWN unless explicit provider importance signal is present.
    """

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class DashboardItemType(str, Enum):
    """Feed item classification type."""

    NEWS = "NEWS"
    GLOBAL_EVENT = "GLOBAL_EVENT"


class DashboardSortOrder(str, Enum):
    """Feed sort ordering."""

    LATEST = "latest"
    OLDEST = "oldest"


class MarketContextSchema(BaseModel):
    """Lightweight quote details attached to a feed item when company symbol is matched."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    symbol: str = Field(..., description="Stock symbol / ticker")
    price: Optional[float] = Field(None, description="Current market price")
    change_percent: Optional[float] = Field(None, description="Percentage change from previous close")
    timestamp_utc: str = Field(..., description="Quote timestamp in UTC (ISO 8601)")
    timestamp_ist: str = Field(..., description="Quote timestamp in IST (Asia/Kolkata, ISO 8601)")


class DashboardFeedItem(BaseModel):
    """API-facing representation of a normalized Dashboard feed item."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str = Field(..., description="Stable deduplication key (URL hash or article ID)")
    type: DashboardItemType = Field(..., description="NEWS or GLOBAL_EVENT")
    headline: str = Field(..., description="Article headline / title")
    summary: Optional[str] = Field(None, description="Provider summary or snippet")
    category: str = Field(..., description="Primary category identifier")
    impact_level: ImpactLevel = Field(
        ImpactLevel.UNKNOWN,
        description="Presentation impact level (HIGH | MEDIUM | LOW | UNKNOWN)",
    )
    countries: List[str] = Field(default_factory=list, description="ISO alpha-2 country codes")
    companies: List[CompanyTagSchema] = Field(default_factory=list, description="Recognized company tags")
    sectors: List[str] = Field(default_factory=list, description="Unique sectors derived from companies")
    published_at_utc: str = Field(..., description="Publication timestamp in UTC (ISO 8601)")
    published_at_ist: str = Field(..., description="Publication timestamp in IST (ISO 8601)")
    source_name: str = Field(..., description="Source publisher name")
    article_url: str = Field(..., description="Original article URL")
    financially_relevant: bool = Field(..., description="True if article passed financial relevance filter")
    market_context: List[MarketContextSchema] = Field(
        default_factory=list, description="Optional real-time quote context for tagged companies"
    )
    correlation_confidence: Optional[float] = Field(
        None, description="Correlation confidence score (0.00 to 1.00) if correlated with an anomaly"
    )
    match_reasons: List[str] = Field(
        default_factory=list, description="Human-readable explanations for event-anomaly correlation"
    )
    correlated_anomalies: List[Any] = Field(
        default_factory=list, description="Associated market anomalies detected around event time"
    )


from app.schemas.pagination import PaginationSchema



class IndiaImpactSummaryWidget(BaseModel):
    """Dashboard summary widget highlighting India impact statistics and top events."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    total_evaluated: int = Field(..., description="Total active anomalies evaluated for India impact")
    high_impact_count: int = Field(..., description="Number of HIGH India impact assessments")
    medium_impact_count: int = Field(..., description="Number of MEDIUM India impact assessments")
    active_channels: List[TransmissionChannel] = Field(
        default_factory=list, description="Unique active transmission channels across high/medium events"
    )
    top_affected_sectors: List[str] = Field(
        default_factory=list, description="Unique domestic sectors affected across high/medium events"
    )
    featured_assessments: List[IndiaImpactResponse] = Field(
        default_factory=list, description="Top high/medium India impact assessments sorted by impactScore DESC"
    )


class HistoricalSummaryWidget(BaseModel):
    """Dashboard summary widget highlighting aggregate historical shock analytics."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    total_anomalies_evaluated: int = Field(..., description="Total historical anomalies evaluated")
    total_impact_assessments_evaluated: int = Field(..., description="Total historical impact assessments evaluated")
    average_impact_score: float = Field(..., description="Average India impact score across snapshots")
    peak_impact_score: float = Field(..., description="Peak India impact score across snapshots")
    most_active_asset_class: Optional[str] = Field(None, description="Asset class with highest anomaly frequency")
    top_transmission_channel: Optional[str] = Field(None, description="Transmission channel with highest prevalence")
    correlation_evidence_ratio: float = Field(..., description="Prevalence ratio of evidence-backed assessments")


from app.schemas.explanation import ExecutiveSummaryResponse


class DashboardResponse(BaseModel):
    """Main response structure for GET /api/v1/dashboard and GET /api/v1/dashboard/search."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    generated_at_utc: str = Field(..., description="Dashboard generation time in UTC (ISO 8601)")
    generated_at_ist: str = Field(..., description="Dashboard generation time in IST (ISO 8601)")
    feed: List[DashboardFeedItem] = Field(..., description="Normalized feed items")
    pagination: PaginationSchema = Field(..., description="Pagination metadata")
    india_impact_summary: Optional[IndiaImpactSummaryWidget] = Field(
        None, description="Optional India impact dashboard widget summary"
    )
    historical_summary: Optional[HistoricalSummaryWidget] = Field(
        None, description="Optional historical trend summary widget"
    )
    executive_narrative: Optional[ExecutiveSummaryResponse] = Field(
        None, description="Optional executive natural language summary widget"
    )



