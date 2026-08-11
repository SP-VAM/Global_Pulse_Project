"""
GlobalPulse Phase 5C — Central Explanation Orchestration Service.
Orchestrates context assembly, cache lookup, primary provider invocation with retries, targeted fallback, and cache storage.

Key Invariants:
1. Depends strictly on interface abstractions (ExplanationContextAssembler, AbstractExplanationCache, AbstractExplanationProvider).
2. Builds cache keys through the cache abstraction interface (`self._cache.build_key(...)`).
3. Limited Retry Loop: Retries transient infrastructure failures (timeout, rate limit, network) up to max_retries.
4. Targeted Fallback: Catches ONLY provider/infrastructure errors (ExplanationProviderError, TimeoutError, OSError).
   Programming bugs (AttributeError, TypeError, ValueError, KeyError) are NEVER swallowed.
5. Cache Integrity: Writes to cache ONLY after an explanation is fully validated. Failed/malformed payloads are NEVER cached.
"""
import logging
import time
from typing import List, Optional

from app.core.exceptions import (
    ExplanationProviderAuthError,
    ExplanationProviderError,
    ExplanationProviderRateLimitError,
    ExplanationProviderResponseError,
    ExplanationProviderTimeoutError,
)
from app.domain.anomaly import NormalizedAnomaly
from app.domain.correlation import CorrelatedEventPair
from app.domain.explanation import ExecutiveSummary, GroundingContextBundle, ShockExplanation
from app.domain.historical import HistoricalTrendAnalytics
from app.domain.india_impact import IndiaImpactAssessment
from app.services.deterministic_template_provider import (
    AbstractExplanationProvider,
    DeterministicTemplateProvider,
)
from app.services.explanation_cache import AbstractExplanationCache
from app.services.explanation_context_assembler import ExplanationContextAssembler

logger = logging.getLogger(__name__)

# Retryable exception types for transient network/provider infrastructure issues
RETRYABLE_EXCEPTIONS = (
    ExplanationProviderTimeoutError,
    ExplanationProviderRateLimitError,
    ExplanationProviderError,
    TimeoutError,
    OSError,
)


class ExplanationService:
    """
    Central orchestration service for Phase 5 explanations.
    Provides zero-downtime execution with cache lookup, transient retries, and targeted deterministic fallback.
    """

    def __init__(
        self,
        assembler: ExplanationContextAssembler,
        cache: AbstractExplanationCache,
        primary_provider: AbstractExplanationProvider,
        fallback_provider: Optional[AbstractExplanationProvider] = None,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.05,
    ) -> None:
        self._assembler = assembler
        self._cache = cache
        self._primary_provider = primary_provider
        self._fallback_provider = fallback_provider or DeterministicTemplateProvider()
        self._max_retries = max(0, max_retries)
        self._retry_backoff_seconds = max(0.0, retry_backoff_seconds)

    def get_shock_explanation(
        self,
        anomaly: NormalizedAnomaly,
        impact_assessment: Optional[IndiaImpactAssessment] = None,
        correlated_pairs: Optional[List[CorrelatedEventPair]] = None,
    ) -> ShockExplanation:
        """
        Orchestrate ShockExplanation generation.
        Assembles context, checks cache, calls primary provider (with retries), falls back on provider error, and caches result.
        """
        context = self._assembler.assemble_shock_context(anomaly, impact_assessment, correlated_pairs)
        cache_key = self._cache.build_key(
            entity_id=anomaly.id,
            provider_type=self._primary_provider.provider_type,
        )

        cached_val = self._cache.get(cache_key)
        if cached_val is not None:
            logger.debug("Explanation cache hit for key: %s", cache_key)
            return cached_val

        explanation: Optional[ShockExplanation] = None

        # Execute primary provider with limited transient retries
        for attempt in range(1, self._max_retries + 2):
            try:
                explanation = self._primary_provider.generate_shock_explanation(context)
                break
            except ExplanationProviderAuthError as exc:
                logger.warning("Primary provider %s authentication failed: %s. Skipping retries.", self._primary_provider.provider_type, exc)
                break
            except ExplanationProviderResponseError as exc:
                logger.warning("Primary provider %s returned unparseable JSON: %s. Skipping retries.", self._primary_provider.provider_type, exc)
                break
            except RETRYABLE_EXCEPTIONS as exc:
                if attempt <= self._max_retries:
                    logger.warning("Primary provider attempt %d/%d failed (%s). Retrying in %.2fs...", attempt, self._max_retries + 1, exc, self._retry_backoff_seconds)
                    time.sleep(self._retry_backoff_seconds)
                else:
                    logger.warning("Primary provider %s max retries exhausted (%s). Invoking fallback provider %s.", self._primary_provider.provider_type, exc, self._fallback_provider.provider_type)

        # Fallback if primary provider failed
        if explanation is None:
            explanation = self._fallback_provider.generate_shock_explanation(context)

        # Cache Integrity Invariant: Only fully validated domain objects are cached
        self._cache.put(cache_key, explanation)
        return explanation

    def get_executive_summary(
        self,
        anomaly: Optional[NormalizedAnomaly] = None,
        impact_assessment: Optional[IndiaImpactAssessment] = None,
        trend_analytics: Optional[HistoricalTrendAnalytics] = None,
    ) -> ExecutiveSummary:
        """
        Orchestrate ExecutiveSummary generation.
        """
        if trend_analytics:
            context = self._assembler.assemble_trend_context(trend_analytics)
            entity_id = f"HIST-TREND-{trend_analytics.total_anomalies_evaluated}"
        elif anomaly:
            context = self._assembler.assemble_shock_context(anomaly, impact_assessment)
            entity_id = f"ANOM-SHOCK-{anomaly.id}"
        else:
            context = GroundingContextBundle(assembled_at_utc=TimezoneService.now_utc().isoformat())
            entity_id = "EMPTY-SUMMARY"

        cache_key = self._cache.build_key(
            entity_id=entity_id,
            provider_type=self._primary_provider.provider_type,
        )

        cached_val = self._cache.get(cache_key)
        if cached_val is not None:
            return cached_val

        summary: Optional[ExecutiveSummary] = None

        for attempt in range(1, self._max_retries + 2):
            try:
                summary = self._primary_provider.generate_executive_summary(context)
                break
            except (ExplanationProviderAuthError, ExplanationProviderResponseError) as exc:
                logger.warning("Primary provider %s summary error: %s", self._primary_provider.provider_type, exc)
                break
            except RETRYABLE_EXCEPTIONS as exc:
                if attempt <= self._max_retries:
                    time.sleep(self._retry_backoff_seconds)
                else:
                    logger.warning("Primary provider %s retries exhausted for summary: %s", self._primary_provider.provider_type, exc)

        if summary is None:
            summary = self._fallback_provider.generate_executive_summary(context)

        self._cache.put(cache_key, summary)
        return summary
