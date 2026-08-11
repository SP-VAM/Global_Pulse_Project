"""
GlobalPulse Presentation Severity Engine (Sub-Phase 2D)
Calculates UI presentation impactLevel (HIGH | MEDIUM | LOW | UNKNOWN).

Input Signal Layers:
  1. Market Anomaly Volatility Scale (evaluating abs(change_percent))
  2. Category Baseline Severity (for financially_relevant events)
  3. Provider Importance Signal (publisher presentation signal)
  4. Multi-Asset Scope Escalation (>= 2 distinct asset classes with accepted correlation)

Defensively filters CorrelatedEventPair inputs using DEFAULT_MIN_CONFIDENCE = 0.50.
"""
from __future__ import annotations

import logging
from typing import List, Optional, Set

from app.domain.anomaly import AnomalySeverity, NormalizedAnomaly
from app.domain.correlation import DEFAULT_MIN_CONFIDENCE, CorrelatedEventPair
from app.schemas.dashboard import ImpactLevel

logger = logging.getLogger(__name__)

# Critical Risk Event Categories -> Baseline MEDIUM minimum
CRITICAL_RISK_CATEGORIES = {
    "CENTRAL_BANK",
    "WAR_CONFLICT",
    "CRASH_PANIC",
    "GEOPOLITICS",
    "INTEREST_RATE",
    "INFLATION",
}


class SeverityEngineService:
    """
    Presentation Severity Engine layer.
    Determines UI card impactLevel (HIGH | MEDIUM | LOW | UNKNOWN).
    """

    def calculate_anomaly_severity(self, anomaly: NormalizedAnomaly) -> AnomalySeverity:
        """
        Calculate volatility severity for a single anomaly using absolute magnitude abs().
        """
        abs_change = abs(anomaly.change_percent)
        asset_type = anomaly.asset_type.upper()

        if asset_type == "EQUITY":
            if abs_change >= 5.0:
                return AnomalySeverity.HIGH
            if abs_change >= 3.0:
                return AnomalySeverity.MEDIUM
            return AnomalySeverity.LOW

        elif asset_type == "COMMODITY":
            if abs_change >= 4.0:
                return AnomalySeverity.HIGH
            if abs_change >= 2.5:
                return AnomalySeverity.MEDIUM
            return AnomalySeverity.LOW

        elif asset_type == "FOREX":
            if abs_change >= 2.0:
                return AnomalySeverity.HIGH
            if abs_change >= 1.0:
                return AnomalySeverity.MEDIUM
            return AnomalySeverity.LOW

        elif asset_type == "BOND":
            if abs_change >= 0.20:  # 20 bps
                return AnomalySeverity.HIGH
            if abs_change >= 0.10:  # 10 bps
                return AnomalySeverity.MEDIUM
            return AnomalySeverity.LOW

        elif asset_type == "CRYPTO":
            if abs_change >= 6.0:
                return AnomalySeverity.HIGH
            if abs_change >= 4.0:
                return AnomalySeverity.MEDIUM
            return AnomalySeverity.LOW

        # Fallback default for unrecognized asset class
        if abs_change >= 5.0:
            return AnomalySeverity.HIGH
        if abs_change >= 3.0:
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW

    def calculate_event_impact(
        self,
        category: str,
        financially_relevant: bool = True,
        provider_importance: Optional[str] = None,
        correlated_pairs: Optional[List[CorrelatedEventPair]] = None,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    ) -> ImpactLevel:
        """
        Calculate presentation impact level across all signal layers.

        Defensively filters correlated_pairs using min_confidence before evaluation.
        """
        # Defensive Filtering: keep only accepted correlated pairs
        raw_pairs = correlated_pairs or []
        valid_pairs = [p for p in raw_pairs if p.confidence_score >= min_confidence]

        # Multi-Asset Scope Escalation: >= 2 DISTINCT asset classes
        distinct_asset_classes: Set[str] = {p.anomaly.asset_type.upper() for p in valid_pairs}
        if len(distinct_asset_classes) >= 2:
            return ImpactLevel.HIGH

        has_provider_signal = bool(provider_importance and provider_importance.upper() not in ["UNKNOWN", "NONE", ""])
        has_valid_anomalies = len(valid_pairs) > 0

        # Absence of any usable severity signal -> UNKNOWN
        if not has_valid_anomalies and not has_provider_signal and not financially_relevant:
            return ImpactLevel.UNKNOWN

        # Numeric rank for max aggregation: UNKNOWN=0, LOW=1, MEDIUM=2, HIGH=3
        rank_map = {
            ImpactLevel.UNKNOWN: 0,
            ImpactLevel.LOW: 1,
            ImpactLevel.MEDIUM: 2,
            ImpactLevel.HIGH: 3,
        }

        # 1. Anomaly Volatility Rank
        max_anomaly_rank = 0
        for pair in valid_pairs:
            sev = self.calculate_anomaly_severity(pair.anomaly)
            if sev == AnomalySeverity.HIGH:
                max_anomaly_rank = max(max_anomaly_rank, 3)
            elif sev == AnomalySeverity.MEDIUM:
                max_anomaly_rank = max(max_anomaly_rank, 2)
            else:
                max_anomaly_rank = max(max_anomaly_rank, 1)

        # 2. Category Baseline Rank (Only if financially_relevant=True)
        category_rank = 0
        if financially_relevant:
            upper_cat = category.upper() if category else ""
            if upper_cat in CRITICAL_RISK_CATEGORIES:
                category_rank = 2  # Baseline MEDIUM
            else:
                category_rank = 1  # Baseline LOW

        # 3. Provider Importance Rank
        provider_rank = 0
        if has_provider_signal and provider_importance:
            norm_imp = provider_importance.upper()
            if norm_imp in ["HIGH", "3"]:
                provider_rank = 3
            elif norm_imp in ["MEDIUM", "2"]:
                provider_rank = 2
            elif norm_imp in ["LOW", "1"]:
                provider_rank = 1

        final_rank = max(max_anomaly_rank, category_rank, provider_rank)

        if final_rank == 3:
            return ImpactLevel.HIGH
        elif final_rank == 2:
            return ImpactLevel.MEDIUM
        elif final_rank == 1:
            return ImpactLevel.LOW

        return ImpactLevel.UNKNOWN
