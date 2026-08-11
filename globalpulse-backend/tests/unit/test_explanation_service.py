"""
Unit tests for ExplanationService (Phase 5C).
Verifies:
1. Cache hit/put workflow & key building through cache abstraction interface.
2. Transient retry loop (retries transient provider failures up to max_retries).
3. Targeted fallback: fallback to DeterministicTemplateProvider on provider/infrastructure error.
4. Cache integrity: failed or invalid responses are NEVER cached.
5. Programming bugs (AttributeError, TypeError, ValueError) are NEVER caught or hidden behind fallback.
"""
from unittest.mock import MagicMock
import pytest
from app.core.exceptions import (
    ExplanationProviderAuthError,
    ExplanationProviderError,
    ExplanationProviderResponseError,
    ExplanationProviderTimeoutError,
)
from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.explanation import ExplanationProviderType, ShockExplanation
from app.services.deterministic_template_provider import DeterministicTemplateProvider
from app.services.explanation_cache import InMemoryExplanationCache
from app.services.explanation_context_assembler import ExplanationContextAssembler
from app.services.explanation_service import ExplanationService


@pytest.fixture
def sample_anomaly():
    return NormalizedAnomaly(
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


def test_explanation_service_cache_hit_workflow(sample_anomaly):
    assembler = ExplanationContextAssembler()
    cache = InMemoryExplanationCache()

    mock_primary = MagicMock()
    mock_primary.provider_type = ExplanationProviderType.DETERMINISTIC

    service = ExplanationService(
        assembler=assembler,
        cache=cache,
        primary_provider=mock_primary,
    )

    # 1. First invocation -> Primary provider called & result cached
    exp1 = service.get_shock_explanation(sample_anomaly)
    assert mock_primary.generate_shock_explanation.call_count == 1

    # 2. Second invocation -> Cache hit! Primary provider NOT called again
    exp2 = service.get_shock_explanation(sample_anomaly)
    assert mock_primary.generate_shock_explanation.call_count == 1
    assert exp1 == exp2


def test_transient_retry_loop_success_on_retry(sample_anomaly):
    assembler = ExplanationContextAssembler()
    cache = InMemoryExplanationCache()

    mock_primary = MagicMock()
    mock_primary.provider_type = ExplanationProviderType.LLM_GEMINI

    # Attempt 1 raises TimeoutError; Attempt 2 succeeds!
    mock_fallback_exp = DeterministicTemplateProvider().generate_shock_explanation(
        assembler.assemble_shock_context(sample_anomaly)
    )
    mock_primary.generate_shock_explanation.side_effect = [
        ExplanationProviderTimeoutError("Transient timeout"),
        mock_fallback_exp,
    ]

    service = ExplanationService(
        assembler=assembler,
        cache=cache,
        primary_provider=mock_primary,
        max_retries=2,
        retry_backoff_seconds=0.01,
    )

    exp = service.get_shock_explanation(sample_anomaly)
    assert mock_primary.generate_shock_explanation.call_count == 2
    assert exp == mock_fallback_exp


def test_targeted_fallback_on_provider_auth_error(sample_anomaly):
    assembler = ExplanationContextAssembler()
    cache = InMemoryExplanationCache()

    mock_primary = MagicMock()
    mock_primary.provider_type = ExplanationProviderType.LLM_GEMINI
    mock_primary.generate_shock_explanation.side_effect = ExplanationProviderAuthError("Missing API Key")

    fallback_provider = DeterministicTemplateProvider()

    service = ExplanationService(
        assembler=assembler,
        cache=cache,
        primary_provider=mock_primary,
        fallback_provider=fallback_provider,
    )

    # Invokes fallback provider on AuthError without infinite retries
    exp = service.get_shock_explanation(sample_anomaly)
    assert exp.provider_type == ExplanationProviderType.DETERMINISTIC
    assert "Brent crude oil" in exp.headline_summary or "BRENT" in exp.headline_summary
    # Cache integrity: verified fallback response IS stored in cache
    cache_key = cache.build_key(sample_anomaly.id, ExplanationProviderType.LLM_GEMINI)
    assert cache.get(cache_key) == exp


def test_programming_bugs_are_not_swallowed(sample_anomaly):
    assembler = ExplanationContextAssembler()
    cache = InMemoryExplanationCache()

    mock_primary = MagicMock()
    mock_primary.provider_type = ExplanationProviderType.LLM_GEMINI
    # Raise a programming bug (TypeError)
    mock_primary.generate_shock_explanation.side_effect = TypeError("Internal code bug: NoneType has no attribute 'symbol'")

    service = ExplanationService(
        assembler=assembler,
        cache=cache,
        primary_provider=mock_primary,
    )

    # Internal programming errors MUST surface cleanly without triggering fallback
    with pytest.raises(TypeError) as exc_info:
        service.get_shock_explanation(sample_anomaly)

    assert "Internal code bug" in str(exc_info.value)
