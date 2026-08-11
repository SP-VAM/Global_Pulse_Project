"""
GlobalPulse Phase 4A & 4B — Historical Domain Models
Frozen domain snapshot representations and analytical trend outputs.

Guarantees true immutability via frozen dataclasses and immutable tuple collections.
Preserves complete provenance without retaining live third-party object graphs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.domain.anomaly import AnomalyMetric
from app.domain.india_impact import (
    CapitalFlowRisk,
    ImpactDirection,
    IndiaImpactLevel,
    IndianSectorSensitivity,
    TransmissionChannel,
)


@dataclass(frozen=True)
class HistoricalAnomalySnapshot:
    """
    Immutable historical snapshot of a detected market anomaly (Phase 2B).
    Preserves exact provenance metrics at detection time.
    """

    snapshot_id: str
    anomaly_id: str
    symbol: str
    asset_type: str
    metric: AnomalyMetric
    current_value: float
    previous_value: Optional[float]
    change_percent: float
    detected_at_utc: str
    detected_at_ist: str
    created_at_utc: str


@dataclass(frozen=True)
class HistoricalImpactSnapshot:
    """
    Immutable historical snapshot of an evaluated India impact assessment (Phase 3B).
    Preserves shock transmission channels, sector vulnerabilities, and correlation evidence metadata.
    """

    snapshot_id: str
    source_anomaly_id: Optional[str]
    source_event_id: Optional[str]
    symbol: Optional[str]
    asset_type: Optional[str]
    impact_score: float
    impact_level: IndiaImpactLevel
    impact_direction: ImpactDirection
    capital_flow_risk: CapitalFlowRisk
    transmission_channels: tuple[TransmissionChannel, ...]
    affected_sectors: tuple[IndianSectorSensitivity, ...]
    has_correlation_evidence: bool
    correlated_event_ids: tuple[str, ...]
    correlation_count: int
    top_correlation_confidence: Optional[float]
    assessed_at_utc: str
    assessed_at_ist: str
    created_at_utc: str


# ---------------------------------------------------------------------------
# Phase 4B Analytics Domain Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssetClassFrequency:
    """Historical anomaly frequency and ratio per asset class."""

    asset_type: str                  # e.g. "COMMODITY", "FOREX", "BOND", "EQUITY", "CRYPTO"
    count: int                       # Anomaly count in query window
    ratio: float                     # Fraction of total anomalies (0.00 to 1.00, rounded 2 decimals)


@dataclass(frozen=True)
class ChannelDistribution:
    """Historical prevalence ratio for a transmission channel across assessments."""

    channel: TransmissionChannel     # e.g. COMMODITY_IMPORT, CAPITAL_FLOW_SENSITIVITY
    count: int                       # Number of assessments containing this channel
    assessment_ratio: float          # Prevalence ratio = count / total_impact_assessments (0.00 to 1.00)


@dataclass(frozen=True)
class SectorHitSummary:
    """Aggregated directional impact hit count per Indian domestic sector."""

    sector_name: str                 # e.g. "PAINTS", "IT_SERVICES", "FINANCIALS", "AVIATION"
    total_hits: int                  # Total = positive_hits + negative_hits + mixed_hits + neutral_hits
    negative_hits: int               # Count of NEGATIVE impacts
    positive_hits: int               # Count of POSITIVE impacts
    mixed_hits: int                  # Count of MIXED impacts
    neutral_hits: int                # Count of NEUTRAL impacts
    primary_direction: ImpactDirection  # Deterministic primary impact direction


@dataclass(frozen=True)
class ImpactLevelCount:
    """Immutable impact level frequency count."""

    impact_level: IndiaImpactLevel   # HIGH | MEDIUM | LOW | NEGLIGIBLE
    count: int


@dataclass(frozen=True)
class HistoricalTrendAnalytics:
    """Complete aggregated analytical summary over a historical time window."""

    total_anomalies_evaluated: int
    total_impact_assessments_evaluated: int
    average_impact_score: float      # Rounded to 1 decimal place (0.0 if empty)
    peak_impact_score: float         # Max score (0.0 if empty)
    impact_level_counts: tuple[ImpactLevelCount, ...]
    asset_class_frequencies: tuple[AssetClassFrequency, ...]
    channel_distributions: tuple[ChannelDistribution, ...]
    sector_hit_summaries: tuple[SectorHitSummary, ...]
    correlated_evidence_count: int   # Count of assessments backed by accepted correlation evidence
    correlation_evidence_ratio: float  # Prevalence ratio (0.00 to 1.00) of evidence-backed assessments
