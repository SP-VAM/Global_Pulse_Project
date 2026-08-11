"""
GlobalPulse Phase 3B — India Impact Transmission Engine (IndiaImpactService).
Deterministically evaluates market anomalies, price/yield shocks, and correlated global events
against India's macroeconomic vulnerability matrix.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from app.domain.anomaly import NormalizedAnomaly
from app.domain.correlation import CorrelatedEventPair, DEFAULT_MIN_CONFIDENCE
from app.domain.economic_event import NormalizedEconomicEvent
from app.domain.india_impact import (
    CapitalFlowRisk,
    ImpactDirection,
    IndiaExposureStrength,
    IndiaImpactAssessment,
    IndiaImpactLevel,
    IndianSectorSensitivity,
    TransmissionChannel,
)
from app.domain.news import NormalizedArticle
from app.services.classification.india_vulnerability_matrix import (
    TRANSMISSION_CHANNEL_STRENGTH,
    get_channel_strength,
    get_vulnerability_rule,
)

logger = logging.getLogger(__name__)

# Fixed Component Weights (sum = 1.0)
WEIGHT_CHANNEL: float = 0.35
WEIGHT_EXPOSURE: float = 0.30
WEIGHT_MAGNITUDE: float = 0.20
WEIGHT_EVIDENCE: float = 0.15


class IndiaImpactService:
    """
    India Impact Transmission Engine.
    Evaluates global market anomalies, raw price/yield shocks, and correlated event pairs
    to calculate normalized India impact scores, levels, channels, and sector vulnerabilities.
    """

    @staticmethod
    def calculate_magnitude_score(change_percent: Optional[float], asset_type: str = "") -> Optional[float]:
        """
        Calculate normalized asset-type-aware magnitude score S_magnitude in [0.0, 1.0].
        If change_percent is None, returns None (component is inactive).

        Exact Frozen Divisors:
        - EQUITY: min(1.0, abs(change_percent) / 6.0)
        - COMMODITY: min(1.0, abs(change_percent) / 5.0)
        - FOREX: min(1.0, abs(change_percent) / 2.0)
        - CRYPTO: min(1.0, abs(change_percent) / 8.0)
        - BOND: min(1.0, abs(change_bps) / 20.0) where change_bps = abs(change_percent) * 100.0
        """
        if change_percent is None:
            return None

        abs_pct = abs(change_percent)
        asset_upper = (asset_type or "").upper()

        if "BOND" in asset_upper or asset_upper == "YIELD":
            # Canonical convention: change_percent represents percentage-point yield movement (e.g. 0.10 = 10 bps)
            bps = abs_pct * 100.0
            return min(1.0, bps / 20.0)
        elif "FOREX" in asset_upper or "CURRENCY" in asset_upper or "/" in asset_upper:
            return min(1.0, abs_pct / 2.0)
        elif "COMMODITY" in asset_upper:
            return min(1.0, abs_pct / 5.0)
        elif "CRYPTO" in asset_upper:
            return min(1.0, abs_pct / 8.0)
        else:
            return min(1.0, abs_pct / 6.0)

    @staticmethod
    def score_to_level(score: float) -> IndiaImpactLevel:
        """Map normalized score (0.0 to 100.0) to IndiaImpactLevel."""
        if score >= 75.0:
            return IndiaImpactLevel.HIGH
        elif score >= 45.0:
            return IndiaImpactLevel.MEDIUM
        elif score >= 20.0:
            return IndiaImpactLevel.LOW
        else:
            return IndiaImpactLevel.NEGLIGIBLE

    def compute_impact_score(
        self,
        channel: Optional[TransmissionChannel],
        exposure_strength: IndiaExposureStrength,
        change_percent: Optional[float],
        asset_type: str,
        correlated_pairs: Optional[List[CorrelatedEventPair]] = None,
    ) -> float:
        """
        Compute normalized score using explicit formula:
        Score = ( sum(S_i * W_i) / sum(active W_i) ) * 100.0
        """
        active_weighted_scores: float = 0.0
        active_weights_sum: float = 0.0

        # 1. Transmission Channel Component (Weight = 0.35)
        s_channel = get_channel_strength(channel)
        active_weighted_scores += s_channel * WEIGHT_CHANNEL
        active_weights_sum += WEIGHT_CHANNEL

        # 2. Exposure Strength Component (Weight = 0.30)
        s_exposure = float(exposure_strength.value)
        active_weighted_scores += s_exposure * WEIGHT_EXPOSURE
        active_weights_sum += WEIGHT_EXPOSURE

        # 3. Magnitude Component (Weight = 0.20)
        s_magnitude = self.calculate_magnitude_score(change_percent, asset_type)
        if s_magnitude is not None:
            active_weighted_scores += s_magnitude * WEIGHT_MAGNITUDE
            active_weights_sum += WEIGHT_MAGNITUDE

        # 4. Correlation Evidence Component (Weight = 0.15)
        accepted_confidences: List[float] = []
        if correlated_pairs:
            for pair in correlated_pairs:
                if pair and pair.confidence_score >= DEFAULT_MIN_CONFIDENCE:
                    accepted_confidences.append(pair.confidence_score)

        if accepted_confidences:
            s_evidence = max(accepted_confidences)
            active_weighted_scores += s_evidence * WEIGHT_EVIDENCE
            active_weights_sum += WEIGHT_EVIDENCE

        if active_weights_sum == 0.0:
            return 0.0

        raw_score = (active_weighted_scores / active_weights_sum) * 100.0
        return min(100.0, max(0.0, round(raw_score, 1)))

    def evaluate_raw_shock(
        self,
        symbol: str,
        change_percent: Optional[float] = None,
        asset_type: str = "",
        correlated_pairs: Optional[List[CorrelatedEventPair]] = None,
    ) -> IndiaImpactAssessment:
        """Evaluate raw market shock or ticker movement."""
        direction = "UP" if (change_percent is None or change_percent >= 0) else "DOWN"
        rule = get_vulnerability_rule(symbol, direction)

        if rule is None:
            return IndiaImpactAssessment(
                impact_score=0.0,
                impact_level=IndiaImpactLevel.NEGLIGIBLE,
                impact_direction=ImpactDirection.NEUTRAL,
                capital_flow_risk=CapitalFlowRisk.NEGLIGIBLE,
                transmission_channels=[],
                affected_sectors=[],
                summary_rationale=f"No recognized India impact transmission rule for symbol {symbol} ({direction}).",
            )

        channel = rule.get("channel")
        exposure_strength = rule.get("exposure_strength", IndiaExposureStrength.NEGLIGIBLE)
        overall_direction = rule.get("overall_direction", ImpactDirection.NEUTRAL)
        capital_flow_risk = rule.get("capital_flow_risk", CapitalFlowRisk.NEGLIGIBLE)
        summary = rule.get("summary", "")
        sectors = rule.get("sectors", [])

        impact_score = self.compute_impact_score(
            channel=channel,
            exposure_strength=exposure_strength,
            change_percent=change_percent,
            asset_type=asset_type,
            correlated_pairs=correlated_pairs,
        )
        impact_level = self.score_to_level(impact_score)
        channels_list = [channel] if channel else []

        return IndiaImpactAssessment(
            impact_score=impact_score,
            impact_level=impact_level,
            impact_direction=overall_direction,
            capital_flow_risk=capital_flow_risk,
            transmission_channels=channels_list,
            affected_sectors=sectors,
            summary_rationale=summary,
        )

    def evaluate_anomaly(
        self,
        anomaly: NormalizedAnomaly,
        correlated_pairs: Optional[List[CorrelatedEventPair]] = None,
    ) -> IndiaImpactAssessment:
        """Evaluate a NormalizedAnomaly from Phase 2B."""
        return self.evaluate_raw_shock(
            symbol=anomaly.symbol,
            change_percent=anomaly.change_percent,
            asset_type=anomaly.asset_type,
            correlated_pairs=correlated_pairs,
        )

    def evaluate_correlated_pair(self, pair: CorrelatedEventPair) -> IndiaImpactAssessment:
        """Evaluate a CorrelatedEventPair from Phase 2C."""
        return self.evaluate_anomaly(
            anomaly=pair.anomaly,
            correlated_pairs=[pair],
        )

    def assess_event_impact(
        self,
        article: Optional[NormalizedArticle] = None,
        economic_event: Optional[NormalizedEconomicEvent] = None,
        correlated_pairs: Optional[List[CorrelatedEventPair]] = None,
    ) -> IndiaImpactAssessment:
        """
        Assess India impact for news articles or economic calendar events.
        Enforces strict XOR invariant: exactly one of article or economic_event must be non-None.
        Resolves candidate keys in priority order to match against recognized vulnerability rules.
        """
        if (article is None and economic_event is None) or (article is not None and economic_event is not None):
            raise ValueError("assess_event_impact requires exactly one candidate (article XOR economic_event)")

        candidate_keys: List[str] = []
        event_title = ""

        if article:
            event_title = article.headline
            if article.tags:
                candidate_keys.extend(article.tags)
            if article.primary_category:
                cat_val = (
                    article.primary_category.value
                    if hasattr(article.primary_category, "value")
                    else str(article.primary_category)
                )
                candidate_keys.append(cat_val)
        elif economic_event:
            event_title = economic_event.event
            if economic_event.country:
                candidate_keys.append(economic_event.country)
            if economic_event.category:
                cat_val = (
                    economic_event.category.value
                    if hasattr(economic_event.category, "value")
                    else str(economic_event.category)
                )
                candidate_keys.append(cat_val)

        # Priority search for recognized rule in vulnerability matrix
        matched_rule_symbol: Optional[str] = None
        for key in candidate_keys:
            if key and (get_vulnerability_rule(key, "UP") or get_vulnerability_rule(key, "DOWN")):
                matched_rule_symbol = key
                break

        if not matched_rule_symbol:
            matched_rule_symbol = candidate_keys[0] if candidate_keys else "GLOBAL"

        assessment = self.evaluate_raw_shock(
            symbol=matched_rule_symbol,
            change_percent=None,
            asset_type="",
            correlated_pairs=correlated_pairs,
        )

        if event_title and assessment.summary_rationale:
            assessment.summary_rationale = f"[{event_title}] {assessment.summary_rationale}"

        return assessment

