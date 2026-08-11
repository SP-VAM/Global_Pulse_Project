"""
GlobalPulse Phase 5 — AI Explanation & Natural Language Summarization Pydantic Schemas.
Configured with camelCase aliases for API response contracts.
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.domain.explanation import EvidenceConfidenceLevel, ExplanationProviderType
from app.domain.india_impact import ImpactDirection


class SectorRiskNarrativeSchema(BaseModel):
    """API-facing qualitative narrative explanation for a specific domestic sector."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    sector_name: str = Field(..., description="Domestic industry sector e.g. PAINTS, IT_SERVICES")
    direction: ImpactDirection = Field(..., description="Sector impact direction e.g. NEGATIVE, POSITIVE")
    risk_summary: str = Field(..., description="Qualitative narrative describing sector vulnerability")


class ShockExplanationResponse(BaseModel):
    """API-facing representation of a complete executive natural language shock explanation."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    explanation_id: str = Field(..., description="Unique explanation identifier")
    anomaly_id: Optional[str] = Field(None, description="Source anomaly ID if evaluated from market anomaly")
    headline_summary: str = Field(..., description="1-sentence executive summary")
    root_cause_analysis: str = Field(..., description="Trigger event and market movement analysis")
    transmission_mechanism_narrative: str = Field(..., description="Qualitative transmission path narrative to India")
    sector_risk_narratives: List[SectorRiskNarrativeSchema] = Field(default_factory=list, description="Sector vulnerability narratives")
    key_watch_metrics: List[str] = Field(default_factory=list, description="Bullet points of key indicators to monitor")
    evidence_confidence_rating: EvidenceConfidenceLevel = Field(..., description="Confidence rating enum: HIGH or MODERATE")
    provider_type: ExplanationProviderType = Field(..., description="Strongly typed provider identifier enum")

    template_version: str = Field(..., description="Template or prompt version identifier e.g. v1.0")
    generated_at_utc: str = Field(..., description="Generation timestamp in UTC (ISO 8601)")
    generated_at_ist: str = Field(..., description="Generation timestamp in IST (ISO 8601)")


class ExecutiveSummaryResponse(BaseModel):
    """API-facing representation of a high-level executive bullet point narrative."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    summary_id: str = Field(..., description="Unique summary identifier")
    title: str = Field(..., description="Executive narrative title")
    bullet_points: List[str] = Field(..., description="Executive key takeaway bullet points")
    overall_sentiment: ImpactDirection = Field(..., description="Overall macro sentiment direction")
    provider_type: ExplanationProviderType = Field(..., description="Strongly typed provider identifier enum")
    template_version: str = Field(..., description="Template or prompt version identifier")
    generated_at_utc: str = Field(..., description="Generation timestamp in UTC (ISO 8601)")
    generated_at_ist: str = Field(..., description="Generation timestamp in IST (ISO 8601)")
