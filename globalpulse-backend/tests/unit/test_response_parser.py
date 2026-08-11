"""
Unit tests for ExplanationResponseParser (Phase 5C).
Verifies JSON parsing, markdown code block stripping, field validation, and error handling.
"""
import pytest
from app.core.exceptions import ExplanationProviderResponseError
from app.domain.explanation import EvidenceConfidenceLevel, ExplanationProviderType
from app.domain.india_impact import ImpactDirection
from app.services.response_parser import ExplanationResponseParser


def test_parse_valid_shock_explanation_with_markdown_fences():
    parser = ExplanationResponseParser()
    raw = """```json
    {
        "headline_summary": "Brent crude oil prices spiked 6.25% due to Middle East tensions.",
        "root_cause_analysis": "OPEC production cuts and geopolitical risks drove futures higher.",
        "transmission_mechanism_narrative": "Transmits through higher crude import bills and inflation.",
        "sector_risk_narratives": [
            {"sector_name": "PAINTS", "direction": "NEGATIVE", "risk_summary": "Raw material costs surge."}
        ],
        "key_watch_metrics": ["Brent crude futures", "USD/INR exchange rate"]
    }
    ```"""

    explanation = parser.parse_shock_explanation(
        raw_json_str=raw,
        anomaly_id="ANOM-BRENT-1",
        provider_type=ExplanationProviderType.LLM_GEMINI,
        evidence_confidence=EvidenceConfidenceLevel.HIGH,
    )

    assert explanation.anomaly_id == "ANOM-BRENT-1"
    assert explanation.provider_type == ExplanationProviderType.LLM_GEMINI
    assert explanation.evidence_confidence_rating == EvidenceConfidenceLevel.HIGH
    assert "Brent crude oil prices spiked" in explanation.headline_summary
    assert len(explanation.sector_risk_narratives) == 1
    assert explanation.sector_risk_narratives[0].sector_name == "PAINTS"
    assert explanation.sector_risk_narratives[0].direction == ImpactDirection.NEGATIVE


def test_parse_malformed_json_raises_provider_response_error():
    parser = ExplanationResponseParser()
    raw_invalid = "{ headline_summary: invalid json without quotes }"

    with pytest.raises(ExplanationProviderResponseError) as exc_info:
        parser.parse_shock_explanation(raw_invalid, anomaly_id="ANOM-1")

    assert "Invalid JSON payload" in str(exc_info.value)


def test_parse_missing_required_field_raises_provider_response_error():
    parser = ExplanationResponseParser()
    raw_missing = '{"headline_summary": "Summary here"}'  # missing root_cause_analysis & transmission_mechanism_narrative

    with pytest.raises(ExplanationProviderResponseError) as exc_info:
        parser.parse_shock_explanation(raw_missing, anomaly_id="ANOM-1")

    assert "Missing or invalid required field" in str(exc_info.value)
