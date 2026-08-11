"""
GlobalPulse Phase 5A — Explanation Context Assembler.
Harvests deterministic outputs from earlier phases (Quotes, Anomalies, Correlations, India Impact, Historical Analytics)
and constructs immutable GroundingContextBundle objects for prompt builders and template generators.

This component contains ZERO business scoring logic — strictly context harvesting and fact assembly.

Security hardening (Phase 6 — M-4):
  All externally-sourced text fields (article headlines, article summaries) are
  sanitized through PromptSanitizer before entering the GroundingContextBundle.
  This prevents adversarial prompt injection payloads embedded in news articles
  from reaching the LLM provider or the DeterministicTemplateProvider.
"""
import logging
from typing import List, Optional, Tuple

from app.core.prompt_sanitizer import prompt_sanitizer
from app.core.timezone import TimezoneService
from app.domain.anomaly import NormalizedAnomaly
from app.domain.correlation import DEFAULT_MIN_CONFIDENCE, CorrelatedEventPair
from app.domain.explanation import GroundingContextBundle
from app.domain.historical import HistoricalTrendAnalytics
from app.domain.india_impact import IndiaImpactAssessment

logger = logging.getLogger(__name__)


class ExplanationContextAssembler:
    """
    Standalone Context Assembler for Phase 5.
    Harvests deterministic outputs from Phases 1-4 to build GroundingContextBundle objects.

    Security note: article headlines and summaries from correlation pairs are
    sanitized by PromptSanitizer (M-4) before being included in the bundle
    to prevent prompt injection via externally-sourced text.
    """

    def assemble_shock_context(
        self,
        anomaly: NormalizedAnomaly,
        impact_assessment: Optional[IndiaImpactAssessment] = None,
        correlated_pairs: Optional[List[CorrelatedEventPair]] = None,
    ) -> GroundingContextBundle:
        """
        Assemble grounding context for a market anomaly shock.
        Only includes accepted correlation pairs satisfying DEFAULT_MIN_CONFIDENCE (>= 0.50).
        Article headlines and summaries are sanitized against prompt injection.
        """
        raw_pairs = correlated_pairs or []
        accepted_pairs_list: List[CorrelatedEventPair] = []

        for pair in raw_pairs:
            if pair.confidence_score < DEFAULT_MIN_CONFIDENCE:
                continue

            # M-4: Sanitize article text before it enters the grounding bundle
            if pair.article is not None:
                sanitized_headline = prompt_sanitizer.sanitize(pair.article.headline, max_length=300)
                sanitized_summary = prompt_sanitizer.sanitize(pair.article.summary, max_length=500)

                if sanitized_headline != pair.article.headline or sanitized_summary != pair.article.summary:
                    logger.debug(
                        "Prompt injection patterns sanitized from article text | article_id=%s",
                        pair.article.id,
                    )
                    # Rebuild article with sanitized text fields using dataclass replace
                    from dataclasses import replace as dc_replace
                    sanitized_article = dc_replace(
                        pair.article,
                        headline=sanitized_headline,
                        summary=sanitized_summary,
                    )
                    pair = dc_replace(pair, article=sanitized_article)

            accepted_pairs_list.append(pair)

        accepted_pairs: Tuple[CorrelatedEventPair, ...] = tuple(accepted_pairs_list)

        now_utc = TimezoneService.now_utc().isoformat()

        return GroundingContextBundle(
            anomaly=anomaly,
            impact_assessment=impact_assessment,
            correlated_pairs=accepted_pairs,
            trend_analytics=None,
            assembled_at_utc=now_utc,
        )

    def assemble_trend_context(
        self,
        trend_analytics: HistoricalTrendAnalytics,
    ) -> GroundingContextBundle:
        """Assemble grounding context for historical trend analytics."""
        now_utc = TimezoneService.now_utc().isoformat()

        return GroundingContextBundle(
            anomaly=None,
            impact_assessment=None,
            correlated_pairs=(),
            trend_analytics=trend_analytics,
            assembled_at_utc=now_utc,
        )
