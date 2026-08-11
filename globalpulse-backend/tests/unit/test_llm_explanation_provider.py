"""
Unit tests for LLMExplanationProvider (Phase 5C).
Verifies missing API key error translation, LLM execution, and exception handling.
"""
import pytest
from app.core.exceptions import ExplanationProviderAuthError, ExplanationProviderTimeoutError
from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.explanation import ExplanationProviderType
from app.services.explanation_context_assembler import ExplanationContextAssembler
from app.services.llm_explanation_provider import LLMExplanationProvider


def test_llm_provider_missing_api_key_raises_auth_error():
    provider = LLMExplanationProvider(api_key=None)
    assembler = ExplanationContextAssembler()

    anom = NormalizedAnomaly("A1", "BRENT", "COMMODITY", AnomalyMetric.PRICE_SPIKE, 85.0, 80.0, 5.0, "1h", AnomalySeverity.HIGH, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-30T10:00:00Z", "2026-07-30T15:30:00+05:30")
    context = assembler.assemble_shock_context(anom)

    with pytest.raises(ExplanationProviderAuthError) as exc_info:
        provider.generate_shock_explanation(context)

    assert "API key is not configured" in str(exc_info.value)


def test_llm_provider_mock_caller_execution():
    def mock_caller(system_prompt: str, user_prompt: str) -> str:
        return """{
            "headline_summary": "Mock LLM Summary",
            "root_cause_analysis": "Mock Cause",
            "transmission_mechanism_narrative": "Mock Transmission",
            "sector_risk_narratives": [],
            "key_watch_metrics": ["Crude"]
        }"""

    provider = LLMExplanationProvider(api_key="TEST_KEY", raw_llm_caller=mock_caller)
    assembler = ExplanationContextAssembler()

    anom = NormalizedAnomaly("A1", "BRENT", "COMMODITY", AnomalyMetric.PRICE_SPIKE, 85.0, 80.0, 5.0, "1h", AnomalySeverity.HIGH, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-30T10:00:00Z", "2026-07-30T15:30:00+05:30")
    context = assembler.assemble_shock_context(anom)

    explanation = provider.generate_shock_explanation(context)
    assert explanation.headline_summary == "Mock LLM Summary"
    assert explanation.provider_type == ExplanationProviderType.LLM_GEMINI


def test_llm_provider_timeout_translation():
    def mock_timeout(system_prompt: str, user_prompt: str) -> str:
        raise TimeoutError("Network timeout connecting to Gemini API")

    provider = LLMExplanationProvider(api_key="TEST_KEY", raw_llm_caller=mock_timeout)
    assembler = ExplanationContextAssembler()

    anom = NormalizedAnomaly("A1", "BRENT", "COMMODITY", AnomalyMetric.PRICE_SPIKE, 85.0, 80.0, 5.0, "1h", AnomalySeverity.HIGH, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-30T10:00:00Z", "2026-07-30T15:30:00+05:30")
    context = assembler.assemble_shock_context(anom)

    with pytest.raises(ExplanationProviderTimeoutError) as exc_info:
        provider.generate_shock_explanation(context)

    assert "LLM provider request timed out" in str(exc_info.value)
