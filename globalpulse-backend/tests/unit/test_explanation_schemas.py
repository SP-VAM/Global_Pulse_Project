"""
Unit tests for Phase 5A Explanation Domain Models & Pydantic Schemas.
Verifies camelCase serialization, ExplanationProviderType enum usage, and field validation.
"""
import pytest
from app.domain.explanation import (
    EvidenceConfidenceLevel,
    ExecutiveSummary,
    ExplanationProviderType,
    GroundingContextBundle,
    SectorRiskNarrative,
    ShockExplanation,
)
from app.domain.india_impact import ImpactDirection
from app.schemas.explanation import (
    ExecutiveSummaryResponse,
    SectorRiskNarrativeSchema,
    ShockExplanationResponse,
)



def test_sector_risk_narrative_domain_and_schema():
    domain = SectorRiskNarrative(
        sector_name="PAINTS",
        direction=ImpactDirection.NEGATIVE,
        risk_summary="High crude oil prices increase raw material input costs.",
    )
    schema = SectorRiskNarrativeSchema(
        sector_name=domain.sector_name,
        direction=domain.direction,
        risk_summary=domain.risk_summary,
    )
    dump = schema.model_dump(by_alias=True)
    assert dump["sectorName"] == "PAINTS"
    assert dump["direction"] == "NEGATIVE"
    assert "input costs" in dump["riskSummary"]


def test_shock_explanation_domain_and_schema():
    exp_domain = ShockExplanation(
        explanation_id="EXP-1",
        anomaly_id="ANOM-BRENT-1",
        headline_summary="Brent crude oil spiked 5% due to supply concerns.",
        root_cause_analysis="Middle East supply disruptions pushed oil prices up.",
        transmission_mechanism_narrative="Transmits via higher import bills and CAD pressure.",
        sector_risk_narratives=(
            SectorRiskNarrative("PAINTS", ImpactDirection.NEGATIVE, "Cost up"),
        ),
        key_watch_metrics=("Crude Futures", "USD/INR exchange rate"),
        evidence_confidence_rating=EvidenceConfidenceLevel.HIGH,

        provider_type=ExplanationProviderType.DETERMINISTIC,
        template_version="v1.0",
        generated_at_utc="2026-07-30T10:00:00Z",
        generated_at_ist="2026-07-30T15:30:00+05:30",
    )

    schema = ShockExplanationResponse(
        explanation_id=exp_domain.explanation_id,
        anomaly_id=exp_domain.anomaly_id,
        headline_summary=exp_domain.headline_summary,
        root_cause_analysis=exp_domain.root_cause_analysis,
        transmission_mechanism_narrative=exp_domain.transmission_mechanism_narrative,
        sector_risk_narratives=[
            SectorRiskNarrativeSchema(
                sector_name=s.sector_name,
                direction=s.direction,
                risk_summary=s.risk_summary,
            )
            for s in exp_domain.sector_risk_narratives
        ],
        key_watch_metrics=list(exp_domain.key_watch_metrics),
        evidence_confidence_rating=exp_domain.evidence_confidence_rating,
        provider_type=exp_domain.provider_type,
        template_version=exp_domain.template_version,
        generated_at_utc=exp_domain.generated_at_utc,
        generated_at_ist=exp_domain.generated_at_ist,
    )

    dump = schema.model_dump(by_alias=True)
    assert dump["explanationId"] == "EXP-1"
    assert dump["anomalyId"] == "ANOM-BRENT-1"
    assert dump["providerType"] == "DETERMINISTIC"
    assert dump["evidenceConfidenceRating"] == "HIGH"
    assert len(dump["sectorRiskNarratives"]) == 1
    assert dump["sectorRiskNarratives"][0]["sectorName"] == "PAINTS"


def test_executive_summary_domain_and_schema():
    exec_domain = ExecutiveSummary(
        summary_id="SUMM-1",
        title="India Executive Macro Impact Brief",
        bullet_points=("Oil import bill increased by 5%", "INR faces depreciation pressure"),
        overall_sentiment=ImpactDirection.NEGATIVE,
        provider_type=ExplanationProviderType.LLM_GEMINI,
        template_version="v1.0",
        generated_at_utc="2026-07-30T10:00:00Z",
        generated_at_ist="2026-07-30T15:30:00+05:30",
    )

    schema = ExecutiveSummaryResponse(
        summary_id=exec_domain.summary_id,
        title=exec_domain.title,
        bullet_points=list(exec_domain.bullet_points),
        overall_sentiment=exec_domain.overall_sentiment,
        provider_type=exec_domain.provider_type,
        template_version=exec_domain.template_version,
        generated_at_utc=exec_domain.generated_at_utc,
        generated_at_ist=exec_domain.generated_at_ist,
    )

    dump = schema.model_dump(by_alias=True)
    assert dump["summaryId"] == "SUMM-1"
    assert dump["providerType"] == "LLM_GEMINI"
    assert dump["overallSentiment"] == "NEGATIVE"
    assert len(dump["bulletPoints"]) == 2
