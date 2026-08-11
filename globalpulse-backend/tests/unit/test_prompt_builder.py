"""
Unit tests for ExplanationPromptBuilder (Phase 5C).
Verifies prompt construction and fact-locking directives.
"""
import pytest
from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.india_impact import CapitalFlowRisk, ImpactDirection, IndiaImpactAssessment, IndiaImpactLevel, TransmissionChannel
from app.services.explanation_context_assembler import ExplanationContextAssembler
from app.services.prompt_builder import ExplanationPromptBuilder


def test_build_shock_explanation_prompt_fact_locking():
    builder = ExplanationPromptBuilder()
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

    assess = IndiaImpactAssessment(
        impact_score=90.0,
        impact_level=IndiaImpactLevel.HIGH,
        impact_direction=ImpactDirection.NEGATIVE,
        capital_flow_risk=CapitalFlowRisk.MODERATE_RISK,
        transmission_channels=[TransmissionChannel.COMMODITY_IMPORT],
    )

    context = assembler.assemble_shock_context(anom, impact_assessment=assess)
    system_prompt, user_prompt = builder.build_shock_explanation_prompt(context)

    assert "FACT-LOCKING MANDATE" in system_prompt
    assert "BRENT" in user_prompt
    assert "6.25%" in user_prompt
    assert "90.0/100" in user_prompt
    assert "COMMODITY_IMPORT" in user_prompt
