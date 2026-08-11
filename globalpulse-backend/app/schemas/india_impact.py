"""
GlobalPulse Pydantic Schemas — India Impact API Response.

Exposes India impact score, impact level, direction, transmission channels, and affected sectors.
Configured to serialize snake_case Python fields into frontend-friendly camelCase JSON.
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.domain.india_impact import (
    CapitalFlowRisk,
    ImpactDirection,
    IndiaImpactLevel,
    SectorSensitivity,
    TransmissionChannel,
)
from app.domain.market import AssetType
from app.schemas.pagination import PaginationSchema




class IndianSectorImpactSchema(BaseModel):
    """API-facing representation of an affected Indian industry sector."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    sector_name: str = Field(..., description="Indian industry sector e.g. 'PAINTS', 'IT_SERVICES'")
    direction: ImpactDirection = Field(..., description="Impact direction: POSITIVE | NEGATIVE | MIXED | NEUTRAL")
    sensitivity: SectorSensitivity = Field(..., description="Historical sector sensitivity rating")
    transmission_rationale: str = Field(..., description="Qualitative rationale for sector sensitivity")


class IndiaImpactResponse(BaseModel):
    """API-facing representation of an India impact assessment."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    anomaly_id: Optional[str] = Field(None, description="Associated anomaly ID if evaluated from market anomaly")
    symbol: Optional[str] = Field(None, description="Ticker symbol or asset identifier evaluated")
    impact_score: float = Field(..., description="Normalized India impact score between 0.0 and 100.0")
    impact_level: IndiaImpactLevel = Field(..., description="India impact magnitude: HIGH | MEDIUM | LOW | NEGLIGIBLE")
    impact_direction: ImpactDirection = Field(..., description="Overall direction: POSITIVE | NEGATIVE | MIXED | NEUTRAL")
    capital_flow_risk: CapitalFlowRisk = Field(..., description="Capital flow risk: HIGH_RISK | MODERATE_RISK | LOW_RISK | NEGLIGIBLE")
    transmission_channels: List[TransmissionChannel] = Field(..., description="Active economic transmission channels")
    affected_sectors: List[IndianSectorImpactSchema] = Field(..., description="Affected Indian sectors")
    summary_rationale: str = Field(..., description="Qualitative summary explanation")
    detected_at_utc: Optional[str] = Field(None, description="Detection / assessment timestamp in UTC (ISO 8601)")
    detected_at_ist: Optional[str] = Field(None, description="Detection / assessment timestamp in IST (ISO 8601)")


class EvaluateRawShockRequest(BaseModel):
    """Payload for POST /api/v1/india-impact/evaluate-shock."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    symbol: str = Field(..., description="Ticker symbol or asset identifier e.g. 'BRENT', 'USD/INR', 'US10Y'")
    change_percent: Optional[float] = Field(None, description="Percentage change or yield delta for bonds")
    asset_type: Optional[AssetType] = Field(
        None,
        description="Asset category: EQUITY | COMMODITY | FOREX | BOND | CRYPTO | ETF | INDEX | FUND | UNKNOWN",
    )


class IndiaImpactListResponse(BaseModel):
    """Paginated list of events/anomalies evaluated for India impact."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[IndiaImpactResponse] = Field(..., description="List of India impact assessments")
    pagination: PaginationSchema = Field(..., description="Pagination metadata")


