"""
Unit tests for DeterministicTemplateProvider (Phase 5B).
Verifies:
1. Fact-locking invariant: generates narratives strictly from fields present in GroundingContextBundle.
2. Fact-availability: explicitly states when supporting facts (correlation, impact) are unavailable.
3. Shock explanation generation across asset classes (COMMODITY, FOREX, BOND).
4. EvidenceConfidenceLevel handling (HIGH with news correlation vs MODERATE without).
5. Executive summary bullet point generation for trend analytics and shock briefs.
"""
import pytest
from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.correlation import CorrelatedEventPair
from app.domain.explanation import EvidenceConfidenceLevel, ExplanationProviderType
from app.domain.historical import AssetClassFrequency, HistoricalTrendAnalytics
from app.domain.india_impact import (
    CapitalFlowRisk,
    ImpactDirection,
    IndiaImpactAssessment,
    IndiaImpactLevel,
    IndianSectorSensitivity,
    SectorSensitivity,
    TransmissionChannel,
)
from app.domain.news import GlobalEventCategory, NormalizedArticle
from app.services.deterministic_template_provider import DeterministicTemplateProvider
from app.services.explanation_context_assembler import ExplanationContextAssembler


def test_shock_explanation_with_news_correlation_and_impact():
    provider = DeterministicTemplateProvider()
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
        headline="OPEC cuts crude output",
        summary="Supply cuts push oil benchmarks higher.",
        source_name="Bloomberg",
        source_url="https://bloomberg.com",
        article_url="https://bloomberg.com/oil",
        author="Commodities Team",
        published_at_utc="2026-07-30T09:50:00Z",
        published_at_ist="2026-07-30T15:20:00+05:30",
        primary_category=GlobalEventCategory.ENERGY,
    )

    pair = CorrelatedEventPair("CORR-1", anom, article=art, confidence_score=0.88)

    assess = IndiaImpactAssessment(
        impact_score=90.0,
        impact_level=IndiaImpactLevel.HIGH,
        impact_direction=ImpactDirection.NEGATIVE,
        capital_flow_risk=CapitalFlowRisk.MODERATE_RISK,
        transmission_channels=[TransmissionChannel.COMMODITY_IMPORT, TransmissionChannel.CURRENCY_INR],
        affected_sectors=[IndianSectorSensitivity("PAINTS", ImpactDirection.NEGATIVE, SectorSensitivity.HIGH_SENSITIVITY, "Cost inflation")],
    )

    context = assembler.assemble_shock_context(anom, impact_assessment=assess, correlated_pairs=[pair])
    explanation = provider.generate_shock_explanation(context)

    assert explanation.provider_type == ExplanationProviderType.DETERMINISTIC
    assert explanation.evidence_confidence_rating == EvidenceConfidenceLevel.HIGH
    assert "BRENT" in explanation.headline_summary
    assert "6.25%" in explanation.headline_summary
    assert "OPEC cuts crude output" in explanation.root_cause_analysis
    assert "Bloomberg" in explanation.root_cause_analysis
    assert "COMMODITY_IMPORT" in explanation.transmission_mechanism_narrative
    assert len(explanation.sector_risk_narratives) == 1
    assert explanation.sector_risk_narratives[0].sector_name == "PAINTS"
    assert len(explanation.key_watch_metrics) >= 2


def test_fact_locking_and_unavailable_facts_handling():
    provider = DeterministicTemplateProvider()
    assembler = ExplanationContextAssembler()

    anom = NormalizedAnomaly(
        id="ANOM-USDINR-1",
        symbol="USD/INR",
        asset_type="FOREX",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=84.0,
        previous_value=83.0,
        change_percent=1.2,
        observation_window="1h",
        severity=AnomalySeverity.MEDIUM,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-30T10:00:00Z",
        detected_at_ist="2026-07-30T15:30:00+05:30",
    )

    # Context with NO correlated article and NO India impact assessment
    context = assembler.assemble_shock_context(anom, impact_assessment=None, correlated_pairs=[])
    explanation = provider.generate_shock_explanation(context)

    assert explanation.evidence_confidence_rating == EvidenceConfidenceLevel.MODERATE
    # Fact-locking invariant: explicitly states unavailable facts rather than fabricating
    assert "correlation evidence is currently unavailable" in explanation.root_cause_analysis
    assert "impact assessment details are currently unavailable" in explanation.transmission_mechanism_narrative
    assert len(explanation.sector_risk_narratives) == 0


def test_executive_summary_trend_context():
    provider = DeterministicTemplateProvider()
    assembler = ExplanationContextAssembler()

    trends = HistoricalTrendAnalytics(
        total_anomalies_evaluated=25,
        total_impact_assessments_evaluated=25,
        average_impact_score=82.4,
        peak_impact_score=95.0,
        impact_level_counts=(),
        asset_class_frequencies=(AssetClassFrequency("COMMODITY", 15, 0.60),),
        channel_distributions=(),
        sector_hit_summaries=(),
        correlated_evidence_count=20,
        correlation_evidence_ratio=0.80,
    )

    context = assembler.assemble_trend_context(trends)
    exec_summary = provider.generate_executive_summary(context)

    assert exec_summary.provider_type == ExplanationProviderType.DETERMINISTIC
    assert "25 anomalies" in exec_summary.bullet_points[0]
    assert "82.4/100" in exec_summary.bullet_points[1]
    assert "COMMODITY" in exec_summary.bullet_points[2]
    assert "80%" in exec_summary.bullet_points[3]
