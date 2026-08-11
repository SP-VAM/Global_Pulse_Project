"""
GlobalPulse Phase 5 — AI Explanation Domain Models & Enums.
Defines strongly typed provider enums, grounding context bundle, and structured natural language explanation dataclasses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from app.domain.anomaly import NormalizedAnomaly
from app.domain.correlation import CorrelatedEventPair
from app.domain.historical import HistoricalTrendAnalytics
from app.domain.india_impact import ImpactDirection, IndiaImpactAssessment


class ExplanationProviderType(str, Enum):
    """Strongly typed provider identifier enum."""

    DETERMINISTIC = "DETERMINISTIC"
    LLM_GEMINI = "LLM_GEMINI"
    LLM_OPENAI = "LLM_OPENAI"


class EvidenceConfidenceLevel(str, Enum):
    """Evidence confidence rating for shock explanations."""

    HIGH = "HIGH"
    MODERATE = "MODERATE"


@dataclass(frozen=True)
class SectorRiskNarrative:
    """Qualitative narrative explanation for a specific domestic sector."""

    sector_name: str                 # e.g. "PAINTS", "IT_SERVICES", "FINANCIALS"
    direction: ImpactDirection       # POSITIVE | NEGATIVE | MIXED | NEUTRAL
    risk_summary: str                # Qualitative narrative describing sector impact


@dataclass(frozen=True)
class GroundingContextBundle:
    """
    Immutable bundle of factual deterministic outputs harvested from Phases 1–4.
    Acts as the single source of truth for explanation prompt builders and template generators.
    """

    anomaly: Optional[NormalizedAnomaly] = None
    impact_assessment: Optional[IndiaImpactAssessment] = None
    correlated_pairs: Tuple[CorrelatedEventPair, ...] = field(default_factory=tuple)
    trend_analytics: Optional[HistoricalTrendAnalytics] = None
    assembled_at_utc: str = ""


@dataclass(frozen=True)
class ShockExplanation:
    """Complete structured executive natural language explanation for a market shock."""

    explanation_id: str
    anomaly_id: Optional[str]
    headline_summary: str            # 1-sentence executive summary
    root_cause_analysis: str         # Trigger event / market movement explanation
    transmission_mechanism_narrative: str  # Qualitative narrative of transmission to India
    sector_risk_narratives: Tuple[SectorRiskNarrative, ...] = field(default_factory=tuple)
    key_watch_metrics: Tuple[str, ...] = field(default_factory=tuple)  # Bullet points to monitor
    evidence_confidence_rating: EvidenceConfidenceLevel = EvidenceConfidenceLevel.MODERATE
    provider_type: ExplanationProviderType = ExplanationProviderType.DETERMINISTIC
    template_version: str = "v1.0"
    generated_at_utc: str = ""
    generated_at_ist: str = ""



@dataclass(frozen=True)
class ExecutiveSummary:
    """High-level executive bullet point narrative for dashboard integration."""

    summary_id: str
    title: str
    bullet_points: Tuple[str, ...] = field(default_factory=tuple)
    overall_sentiment: ImpactDirection = ImpactDirection.NEUTRAL
    provider_type: ExplanationProviderType = ExplanationProviderType.DETERMINISTIC
    template_version: str = "v1.0"
    generated_at_utc: str = ""
    generated_at_ist: str = ""
