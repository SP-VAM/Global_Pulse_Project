"""
Unit tests for ExplanationContextAssembler (Phase 5A).
Verifies harvesting of deterministic outputs from Phases 1-4 and creation of immutable GroundingContextBundle.
"""
import pytest
from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.correlation import CorrelatedEventPair
from app.domain.historical import HistoricalTrendAnalytics
from app.domain.india_impact import CapitalFlowRisk, ImpactDirection, IndiaImpactAssessment, IndiaImpactLevel, TransmissionChannel
from app.domain.news import GlobalEventCategory, NormalizedArticle
from app.services.explanation_context_assembler import ExplanationContextAssembler


def test_assemble_shock_context_with_correlation_and_impact():
    assembler = ExplanationContextAssembler()

    anom = NormalizedAnomaly(
        id="ANOM-BRENT-1",
        symbol="BRENT",
        asset_type="COMMODITY",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=85.0,
        previous_value=80.0,
        change_percent=6.25,
        observation_window="1h",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-30T10:00:00Z",
        detected_at_ist="2026-07-30T15:30:00+05:30",
    )

    art = NormalizedArticle(
        id="ART-1",
        headline="Oil jumps on tight supply",
        summary="Crude oil benchmark surges.",
        source_name="Reuters",
        source_url="https://reuters.com",
        article_url="https://reuters.com/oil",
        author="Energy Desk",
        published_at_utc="2026-07-30T09:50:00Z",
        published_at_ist="2026-07-30T15:20:00+05:30",
        primary_category=GlobalEventCategory.ENERGY,
    )


    pair_accepted = CorrelatedEventPair("CORR-1", anom, article=art, confidence_score=0.85)
    pair_rejected = CorrelatedEventPair("CORR-2", anom, article=art, confidence_score=0.40)

    assess = IndiaImpactAssessment(
        impact_score=90.0,
        impact_level=IndiaImpactLevel.HIGH,
        impact_direction=ImpactDirection.NEGATIVE,
        capital_flow_risk=CapitalFlowRisk.MODERATE_RISK,
        transmission_channels=[TransmissionChannel.COMMODITY_IMPORT],
    )

    bundle = assembler.assemble_shock_context(
        anomaly=anom,
        impact_assessment=assess,
        correlated_pairs=[pair_accepted, pair_rejected],
    )

    assert bundle.anomaly.id == "ANOM-BRENT-1"
    assert bundle.impact_assessment.impact_score == 90.0
    # Only correlation pairs >= 0.50 are included in GroundingContextBundle
    assert len(bundle.correlated_pairs) == 1
    assert bundle.correlated_pairs[0].confidence_score == 0.85
    assert bundle.assembled_at_utc != ""


def test_assemble_trend_context():
    assembler = ExplanationContextAssembler()

    trends = HistoricalTrendAnalytics(
        total_anomalies_evaluated=10,
        total_impact_assessments_evaluated=10,
        average_impact_score=75.0,
        peak_impact_score=92.0,
        impact_level_counts=(),
        asset_class_frequencies=(),
        channel_distributions=(),
        sector_hit_summaries=(),
        correlated_evidence_count=8,
        correlation_evidence_ratio=0.8,
    )

    bundle = assembler.assemble_trend_context(trends)

    assert bundle.anomaly is None
    assert bundle.impact_assessment is None
    assert bundle.trend_analytics.total_anomalies_evaluated == 10
    assert bundle.trend_analytics.average_impact_score == 75.0
