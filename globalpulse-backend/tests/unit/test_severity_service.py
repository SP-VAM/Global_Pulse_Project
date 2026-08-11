"""
Unit tests for SeverityEngineService (Sub-Phase 2D).
Verifies absolute movement magnitude, defensive correlation filtering, multi-asset scope escalation,
LOW vs UNKNOWN distinction, category baselines, and provider importance signals.
"""
import pytest

from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.correlation import CorrelatedEventPair
from app.domain.news import GlobalEventCategory, NormalizedArticle
from app.schemas.dashboard import ImpactLevel
from app.services.severity_service import SeverityEngineService


@pytest.fixture
def severity_service():
    return SeverityEngineService()


def _make_anomaly(symbol="AAPL", asset_type="EQUITY", change_pct=5.0) -> NormalizedAnomaly:
    return NormalizedAnomaly(
        id=f"anom-{symbol}",
        symbol=symbol,
        asset_type=asset_type,
        metric=AnomalyMetric.PRICE_DROP if change_pct < 0 else AnomalyMetric.PRICE_SPIKE,
        current_value=190.0,
        previous_value=200.0,
        change_percent=change_pct,
        observation_window="15m",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-29T12:00:00Z",
        detected_at_ist="2026-07-29T17:30:00+05:30",
    )


def _make_article() -> NormalizedArticle:
    return NormalizedArticle(
        id="art-1",
        headline="Market Update",
        summary="Summary",
        source_name="Reuters",
        source_url="https://reuters.com",
        article_url="https://reuters.com/art-1",
        author="Reporter",
        published_at_utc="2026-07-29T12:00:00Z",
        published_at_ist="2026-07-29T17:30:00+05:30",
        primary_category=GlobalEventCategory.TECHNOLOGY,
        tags=[],
        countries=["US"],
        companies=[],
        sectors=["Technology"],
        keywords=[],
        relevance_score=5,
        source="NEWSAPI",
    )


def _make_pair(anomaly: NormalizedAnomaly, confidence: float) -> CorrelatedEventPair:
    return CorrelatedEventPair(
        correlation_id=f"corr-{anomaly.id}",
        anomaly=anomaly,
        article=_make_article(),
        economic_event=None,
        candidate_type="ARTICLE",
        confidence_score=confidence,
        match_reasons=["Time proximity"],
    )


# ---------------------------------------------------------------------------
# 1. Absolute Magnitude & Negative Movements Tests
# ---------------------------------------------------------------------------


def test_absolute_magnitude_negative_drop_evaluated(severity_service):
    # -5.2% equity crash -> HIGH
    anom_drop = _make_anomaly(symbol="AAPL", asset_type="EQUITY", change_pct=-5.2)
    assert severity_service.calculate_anomaly_severity(anom_drop) == AnomalySeverity.HIGH

    # +5.2% equity spike -> HIGH
    anom_spike = _make_anomaly(symbol="AAPL", asset_type="EQUITY", change_pct=5.2)
    assert severity_service.calculate_anomaly_severity(anom_spike) == AnomalySeverity.HIGH

    # -4.1% commodity crash -> HIGH
    anom_comm = _make_anomaly(symbol="BRENT", asset_type="COMMODITY", change_pct=-4.1)
    assert severity_service.calculate_anomaly_severity(anom_comm) == AnomalySeverity.HIGH

    # -2.1% forex crash -> HIGH
    anom_forex = _make_anomaly(symbol="USD/INR", asset_type="FOREX", change_pct=-2.1)
    assert severity_service.calculate_anomaly_severity(anom_forex) == AnomalySeverity.HIGH

    # -0.21% bond yield drop -> HIGH
    anom_bond = _make_anomaly(symbol="US10Y", asset_type="BOND", change_pct=-0.21)
    assert severity_service.calculate_anomaly_severity(anom_bond) == AnomalySeverity.HIGH


# ---------------------------------------------------------------------------
# 2. Defensive Filtering & Multi-Asset Scope Tests
# ---------------------------------------------------------------------------


def test_defensive_filtering_weak_pair_ignored(severity_service):
    # EQUITY @ 0.80 + COMMODITY @ 0.30 -> COMMODITY is discarded (0.30 < 0.50). Multi-asset HIGH does NOT trigger!
    pair_eq = _make_pair(_make_anomaly("AAPL", "EQUITY", 3.2), confidence=0.80)
    pair_comm_weak = _make_pair(_make_anomaly("BRENT", "COMMODITY", 2.6), confidence=0.30)

    impact = severity_service.calculate_event_impact(
        category="TECHNOLOGY",
        financially_relevant=True,
        correlated_pairs=[pair_eq, pair_comm_weak],
    )
    # Only 1 valid asset class remains (EQUITY @ MEDIUM 3.2%) -> ImpactLevel.MEDIUM
    assert impact == ImpactLevel.MEDIUM


def test_multi_asset_scope_escalation_triggers_high(severity_service):
    # EQUITY @ 0.80 + COMMODITY @ 0.75 -> both pass (>= 0.50). 2 distinct asset classes -> ImpactLevel.HIGH
    pair_eq = _make_pair(_make_anomaly("AAPL", "EQUITY", 3.2), confidence=0.80)
    pair_comm = _make_pair(_make_anomaly("BRENT", "COMMODITY", 2.6), confidence=0.75)

    impact = severity_service.calculate_event_impact(
        category="TECHNOLOGY",
        financially_relevant=True,
        correlated_pairs=[pair_eq, pair_comm],
    )
    assert impact == ImpactLevel.HIGH


def test_same_asset_class_duplicates_do_not_trigger_multi_asset_high(severity_service):
    # AAPL (EQUITY @ 3.2%) + MSFT (EQUITY @ 3.5%) -> Same asset class (EQUITY). Does NOT escalate to HIGH!
    pair_aapl = _make_pair(_make_anomaly("AAPL", "EQUITY", 3.2), confidence=0.80)
    pair_msft = _make_pair(_make_anomaly("MSFT", "EQUITY", 3.5), confidence=0.80)

    impact = severity_service.calculate_event_impact(
        category="TECHNOLOGY",
        financially_relevant=True,
        correlated_pairs=[pair_aapl, pair_msft],
    )
    assert impact == ImpactLevel.MEDIUM


# ---------------------------------------------------------------------------
# 3. LOW vs UNKNOWN Distinction Tests
# ---------------------------------------------------------------------------


def test_low_impact_vs_unknown_impact(severity_service):
    # Evaluated financially relevant event with LOW signals -> ImpactLevel.LOW
    pair_low = _make_pair(_make_anomaly("AAPL", "EQUITY", 1.2), confidence=0.80)
    impact_low = severity_service.calculate_event_impact(
        category="TECHNOLOGY",
        financially_relevant=True,
        correlated_pairs=[pair_low],
    )
    assert impact_low == ImpactLevel.LOW

    # Unclassified non-financial event with NO signals -> ImpactLevel.UNKNOWN
    impact_unknown = severity_service.calculate_event_impact(
        category="OTHER",
        financially_relevant=False,
        provider_importance=None,
        correlated_pairs=[],
    )
    assert impact_unknown == ImpactLevel.UNKNOWN


# ---------------------------------------------------------------------------
# 4. Category Baseline & Provider Importance Tests
# ---------------------------------------------------------------------------


def test_category_baseline_for_financial_events(severity_service):
    # WAR_CONFLICT with financially_relevant=True -> minimum MEDIUM
    impact_war = severity_service.calculate_event_impact(
        category="WAR_CONFLICT",
        financially_relevant=True,
    )
    assert impact_war == ImpactLevel.MEDIUM

    # WAR_CONFLICT with financially_relevant=False -> UNKNOWN (no category boost)
    impact_war_non_fin = severity_service.calculate_event_impact(
        category="WAR_CONFLICT",
        financially_relevant=False,
    )
    assert impact_war_non_fin == ImpactLevel.UNKNOWN


def test_provider_importance_signal(severity_service):
    impact_prov_high = severity_service.calculate_event_impact(
        category="TECHNOLOGY",
        financially_relevant=True,
        provider_importance="HIGH",
    )
    assert impact_prov_high == ImpactLevel.HIGH
