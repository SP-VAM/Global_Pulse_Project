"""
GlobalPulse Phase 5B — Abstract Provider & Deterministic Template Engine.
Implements AbstractExplanationProvider and DeterministicTemplateProvider.

Fact-Locking Invariant:
DeterministicTemplateProvider generates narratives ONLY from facts present in GroundingContextBundle.
If a supporting fact is unavailable (e.g. no correlated article or no India impact assessment),
it explicitly states that evidence/assessment is unavailable rather than inferring or fabricating information.
"""
from abc import ABC, abstractmethod
import logging
from typing import List, Optional

from app.core.timezone import TimezoneService
from app.domain.explanation import (
    EvidenceConfidenceLevel,
    ExecutiveSummary,
    ExplanationProviderType,
    GroundingContextBundle,
    SectorRiskNarrative,
    ShockExplanation,
)
from app.domain.india_impact import ImpactDirection

logger = logging.getLogger(__name__)


class AbstractExplanationProvider(ABC):
    """Abstract provider interface for natural language explanation generators."""

    @property
    @abstractmethod
    def provider_type(self) -> ExplanationProviderType:
        """Return the strongly typed provider enum identifier."""
        ...

    @abstractmethod
    def generate_shock_explanation(self, context: GroundingContextBundle) -> ShockExplanation:
        """Synthesize structured ShockExplanation from grounded context bundle."""
        ...

    @abstractmethod
    def generate_executive_summary(self, context: GroundingContextBundle) -> ExecutiveSummary:
        """Synthesize high-level ExecutiveSummary bullet points from grounded context bundle."""
        ...


class DeterministicTemplateProvider(AbstractExplanationProvider):
    """
    Production-grade rule-based natural language template engine.
    Generates structured, professional executive explanations using ground truth facts.
    Zero external API dependencies; 100% deterministic and reliable production fallback.
    """

    @property
    def provider_type(self) -> ExplanationProviderType:
        return ExplanationProviderType.DETERMINISTIC

    def generate_shock_explanation(self, context: GroundingContextBundle) -> ShockExplanation:
        """
        Synthesizes structured ShockExplanation strictly from fields present in context.
        Enforces fact-locking: states unavailable facts explicitly without inferring or fabricating.
        """
        now_utc = TimezoneService.now_utc().isoformat()
        now_ist = TimezoneService.now_ist().isoformat()

        anom = context.anomaly
        impact = context.impact_assessment
        corr_pairs = context.correlated_pairs or ()

        # 1. Anomaly Check & Headline
        if not anom:
            return ShockExplanation(
                explanation_id="EXP-FALLBACK-NONE",
                anomaly_id=None,
                headline_summary="Market anomaly details are currently unavailable.",
                root_cause_analysis="No market anomaly context was provided for evaluation.",
                transmission_mechanism_narrative="Transmission mechanism analysis is unavailable without market anomaly data.",
                sector_risk_narratives=(),
                key_watch_metrics=("Market baseline indicators",),
                evidence_confidence_rating=EvidenceConfidenceLevel.MODERATE,
                provider_type=self.provider_type,
                template_version="v1.0",
                generated_at_utc=now_utc,
                generated_at_ist=now_ist,
            )

        symbol = anom.symbol
        asset_type = anom.asset_type
        metric_str = anom.metric.value if hasattr(anom.metric, "value") else str(anom.metric)
        change_pct = anom.change_percent
        window = anom.observation_window

        headline = f"{symbol} ({asset_type}) experienced a {metric_str.lower().replace('_', ' ')} of {abs(change_pct):.2f}% over a {window} observation window."

        # 2. Root Cause Analysis
        if corr_pairs:
            top_pair = corr_pairs[0]
            if top_pair.article:
                headline_title = top_pair.article.headline
                source = top_pair.article.source_name
                conf_pct = int(round(top_pair.confidence_score * 100))
                root_cause = f"The shock correlates with major headline '{headline_title}' reported by {source} ({conf_pct}% confidence match)."
            elif top_pair.economic_event:
                ev_name = top_pair.economic_event.event_name
                act = top_pair.economic_event.actual
                fc = top_pair.economic_event.forecast or "N/A"
                root_cause = f"The shock correlates with macro economic release '{ev_name}' (Actual: {act}, Forecast: {fc})."
            else:
                root_cause = "Correlated external event evidence is unavailable for this anomaly."
            confidence_level = EvidenceConfidenceLevel.HIGH
        else:
            root_cause = "Direct external news or economic event correlation evidence is currently unavailable. Shock reflects standalone market movement."
            confidence_level = EvidenceConfidenceLevel.MODERATE

        # 3. Transmission Mechanism Narrative
        if impact and impact.transmission_channels:
            channels_str = ", ".join(ch.value for ch in impact.transmission_channels)
            impact_lvl = impact.impact_level.value if hasattr(impact.impact_level, "value") else str(impact.impact_level)
            direction_str = impact.impact_direction.value if hasattr(impact.impact_direction, "value") else str(impact.impact_direction)
            flow_risk = impact.capital_flow_risk.value if hasattr(impact.capital_flow_risk, "value") else str(impact.capital_flow_risk)

            transmission = (
                f"India impact is assessed at {impact_lvl} magnitude ({impact.impact_score:.1f}/100) with a {direction_str} direction. "
                f"Active transmission channels: {channels_str}. Capital flow risk is evaluated as {flow_risk}."
            )
        elif impact:
            transmission = f"India impact magnitude is assessed at {impact.impact_level.value} ({impact.impact_score:.1f}/100)."
        else:
            transmission = "India impact assessment details are currently unavailable for this shock."

        # 4. Sector Risk Narratives
        sector_narratives: List[SectorRiskNarrative] = []
        if impact and impact.affected_sectors:
            for s in impact.affected_sectors:
                dir_enum = s.direction if isinstance(s.direction, ImpactDirection) else ImpactDirection.NEUTRAL
                rationale = s.transmission_rationale or f"Sector sensitivity evaluated as {s.sensitivity.value}."
                sector_narratives.append(
                    SectorRiskNarrative(
                        sector_name=s.sector_name,
                        direction=dir_enum,
                        risk_summary=rationale,
                    )
                )

        # 5. Key Watch Metrics
        watch_metrics: List[str] = [f"{symbol} market benchmark price/yield"]
        if impact and impact.transmission_channels:
            for ch in impact.transmission_channels:
                ch_val = ch.value if hasattr(ch, "value") else str(ch)
                if "COMMODITY" in ch_val:
                    watch_metrics.append("Brent crude futures & commodity input costs")
                elif "CURRENCY" in ch_val:
                    watch_metrics.append("USD/INR exchange rate & RBI intervention stance")
                elif "CAPITAL_FLOW" in ch_val:
                    watch_metrics.append("FPI net capital inflow/outflow data")
                elif "INTEREST_RATE" in ch_val:
                    watch_metrics.append("US 10Y Treasury yield & India 10Y benchmark yield spread")

        exp_id = f"EXP-{symbol}-{anom.id}"

        return ShockExplanation(
            explanation_id=exp_id,
            anomaly_id=anom.id,
            headline_summary=headline,
            root_cause_analysis=root_cause,
            transmission_mechanism_narrative=transmission,
            sector_risk_narratives=tuple(sector_narratives),
            key_watch_metrics=tuple(dict.fromkeys(watch_metrics)),
            evidence_confidence_rating=confidence_level,
            provider_type=self.provider_type,
            template_version="v1.0",
            generated_at_utc=now_utc,
            generated_at_ist=now_ist,
        )

    def generate_executive_summary(self, context: GroundingContextBundle) -> ExecutiveSummary:
        """Synthesizes high-level ExecutiveSummary bullet points strictly from context."""
        now_utc = TimezoneService.now_utc().isoformat()
        now_ist = TimezoneService.now_ist().isoformat()

        anom = context.anomaly
        impact = context.impact_assessment
        trends = context.trend_analytics

        bullets: List[str] = []
        overall_dir = ImpactDirection.NEUTRAL

        if trends:
            title = "Historical Trend Executive Summary"
            bullets.append(f"Evaluated {trends.total_anomalies_evaluated} anomalies and {trends.total_impact_assessments_evaluated} India impact assessments.")
            bullets.append(f"Average India impact score: {trends.average_impact_score:.1f}/100 (Peak: {trends.peak_impact_score:.1f}/100).")
            if trends.asset_class_frequencies:
                top_asset = trends.asset_class_frequencies[0]
                bullets.append(f"Primary shock source asset class: {top_asset.asset_type} ({top_asset.count} shocks, {top_asset.ratio:.0%} of total).")
            if trends.correlation_evidence_ratio > 0:
                bullets.append(f"Evidence-backed assessment prevalence: {trends.correlation_evidence_ratio:.0%}.")
            summ_id = f"SUMM-TREND-{trends.total_anomalies_evaluated}"

        elif anom:
            title = f"Shock Brief: {anom.symbol}"
            metric_str = anom.metric.value if hasattr(anom.metric, "value") else str(anom.metric)
            bullets.append(f"{anom.symbol} ({anom.asset_type}) experienced a {anom.change_percent:.2f}% {metric_str.lower().replace('_', ' ')}.")
            if impact:
                overall_dir = impact.impact_direction if isinstance(impact.impact_direction, ImpactDirection) else ImpactDirection.NEUTRAL
                bullets.append(f"India impact assessed at {impact.impact_level.value} level ({impact.impact_score:.1f}/100).")
                if impact.transmission_channels:
                    ch_str = ", ".join(c.value for c in impact.transmission_channels)
                    bullets.append(f"Active transmission channels: {ch_str}.")
            else:
                bullets.append("India impact assessment details are currently unavailable.")
            summ_id = f"SUMM-SHOCK-{anom.id}"

        else:
            title = "Executive Summary"
            bullets.append("Grounded market context details are currently unavailable.")
            summ_id = "SUMM-EMPTY"

        return ExecutiveSummary(
            summary_id=summ_id,
            title=title,
            bullet_points=tuple(bullets),
            overall_sentiment=overall_dir,
            provider_type=self.provider_type,
            template_version="v1.0",
            generated_at_utc=now_utc,
            generated_at_ist=now_ist,
        )
