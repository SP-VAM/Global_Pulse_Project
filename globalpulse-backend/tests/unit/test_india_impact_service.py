"""
Unit tests for Phase 3B India Impact Transmission Engine (IndiaImpactService).
Verifies:
1. Exact mathematical scoring formula and missing-signal weight renormalization.
2. Centralized transmission channel strength coefficients sourced from Phase 3A vulnerability matrix.
3. Frozen asset-type-aware magnitude normalization divisors (EQUITY /6.0, COMMODITY /5.0, FOREX /2.0, CRYPTO /8.0, BOND bps /20.0).
4. Multi-pair defensive filtering at DEFAULT_MIN_CONFIDENCE=0.50 and max accepted confidence.
5. assess_event_impact API and article XOR economic_event enforcement.
6. Exact impact thresholds (HIGH >=75, MEDIUM >=45, LOW >=20, otherwise NEGLIGIBLE).
7. Zero leakage from Phase 2D presentation severity.
"""
import pytest
from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.correlation import CorrelatedEventPair, DEFAULT_MIN_CONFIDENCE
from app.domain.economic_event import NormalizedEconomicEvent
from app.domain.india_impact import (
    CapitalFlowRisk,
    ImpactDirection,
    IndiaExposureStrength,
    IndiaImpactLevel,
    TransmissionChannel,
)
from app.domain.news import GlobalEventCategory, NormalizedArticle

from app.services.classification.india_vulnerability_matrix import (
    TRANSMISSION_CHANNEL_STRENGTH,
    get_channel_strength,
)
from app.services.india_impact_service import IndiaImpactService


@pytest.fixture
def service():
    return IndiaImpactService()


def test_channel_strength_centralized_coefficients():
    assert get_channel_strength(TransmissionChannel.COMMODITY_IMPORT) == 1.00
    assert get_channel_strength(TransmissionChannel.CURRENCY_INR) == 1.00
    assert get_channel_strength(TransmissionChannel.CAPITAL_FLOW_SENSITIVITY) == 0.80
    assert get_channel_strength(TransmissionChannel.INTEREST_RATE_DIFFERENTIAL) == 0.80
    assert get_channel_strength(TransmissionChannel.GLOBAL_DEMAND) == 0.60
    assert get_channel_strength(TransmissionChannel.SUPPLY_CHAIN) == 0.60
    assert get_channel_strength(None) == 0.00


def test_frozen_asset_magnitude_scaling(service):
    # EQUITY: /6.0 -> 3.0 / 6.0 = 0.5
    assert service.calculate_magnitude_score(3.0, "EQUITY") == 0.50
    assert service.calculate_magnitude_score(12.0, "EQUITY") == 1.00  # Capped at 1.0

    # COMMODITY: /5.0 -> 2.5 / 5.0 = 0.5
    assert service.calculate_magnitude_score(2.5, "COMMODITY") == 0.50

    # FOREX: /2.0 -> 1.0 / 2.0 = 0.5
    assert service.calculate_magnitude_score(1.0, "FOREX") == 0.50

    # CRYPTO: /8.0 -> 4.0 / 8.0 = 0.5
    assert service.calculate_magnitude_score(4.0, "CRYPTO") == 0.50

    # BOND: bps / 20.0 -> 10.0 bps / 20.0 = 0.5
    assert service.calculate_magnitude_score(0.10, "BOND") == 0.50  # 0.10% = 10 bps
    assert service.calculate_magnitude_score(20.0, "BOND") == 1.00

    # Missing magnitude returns None
    assert service.calculate_magnitude_score(None, "EQUITY") is None


def test_brent_crude_spike_scoring_and_renormalization(service):
    # BRENT UP: channel=COMMODITY_IMPORT (S=1.0, W=0.35), exposure=DIRECT_HIGH (S=1.0, W=0.30)
    # change_percent = 5.0% COMMODITY (S_mag = 5.0/5.0 = 1.0, W=0.20)
    # No evidence (W_ev active=False) -> sum active weights = 0.35 + 0.30 + 0.20 = 0.85
    # Weighted score sum = (1.0*0.35) + (1.0*0.30) + (1.0*0.20) = 0.85
    # Score = (0.85 / 0.85) * 100.0 = 100.0 -> HIGH
    assessment = service.evaluate_raw_shock("BRENT", change_percent=5.0, asset_type="COMMODITY")

    assert assessment.impact_score == 100.0
    assert assessment.impact_level == IndiaImpactLevel.HIGH
    assert assessment.impact_direction == ImpactDirection.NEGATIVE
    assert TransmissionChannel.COMMODITY_IMPORT in assessment.transmission_channels
    assert any(s.sector_name == "PAINTS" for s in assessment.affected_sectors)



def test_no_presentation_severity_dependency(service):
    # Verify AnomalySeverity does not change India impact score
    base_kwargs = dict(
        id="ANOM-1",
        symbol="BRENT",
        asset_type="COMMODITY",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=85.0,
        previous_value=80.0,
        change_percent=4.0,
        observation_window="1h",
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-29T10:00:00Z",
        detected_at_ist="2026-07-29T15:30:00+05:30",
    )

    anom_high = NormalizedAnomaly(severity=AnomalySeverity.HIGH, **base_kwargs)
    anom_low = NormalizedAnomaly(severity=AnomalySeverity.LOW, **base_kwargs)

    res_high = service.evaluate_anomaly(anom_high)
    res_low = service.evaluate_anomaly(anom_low)

    assert res_high.impact_score == res_low.impact_score
    assert res_high.impact_level == res_low.impact_level


def test_multi_pair_filtering_and_max_evidence(service):
    anomaly = NormalizedAnomaly(
        id="ANOM-US10Y",
        symbol="US10Y",
        asset_type="BOND",
        metric=AnomalyMetric.YIELD_CHANGE,
        current_value=4.5,
        previous_value=4.3,
        change_percent=0.20,  # 20 bps -> S_mag = 20/20 = 1.0
        observation_window="1h",
        severity=AnomalySeverity.MEDIUM,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-29T10:00:00Z",
        detected_at_ist="2026-07-29T15:30:00+05:30",
    )

    article1 = NormalizedArticle(
        id="ART-1",
        headline="US Treasury yields surge",
        summary=None,
        source_name="Reuters",
        source_url=None,
        article_url="https://example.com/1",
        author=None,
        published_at_utc="2026-07-29T09:50:00Z",
        published_at_ist="2026-07-29T15:20:00+05:30",
        primary_category=GlobalEventCategory.FINANCIAL_MARKETS,
    )
    article2 = NormalizedArticle(
        id="ART-2",
        headline="Fed rate expectations shift",
        summary=None,
        source_name="Bloomberg",
        source_url=None,
        article_url="https://example.com/2",
        author=None,
        published_at_utc="2026-07-29T09:45:00Z",
        published_at_ist="2026-07-29T15:15:00+05:30",
        primary_category=GlobalEventCategory.CENTRAL_BANK,
    )

    pair_low = CorrelatedEventPair(
        correlation_id="CORR-1",
        anomaly=anomaly,
        article=article1,
        confidence_score=0.40,  # Below DEFAULT_MIN_CONFIDENCE (0.50) -> Filtered out
    )
    pair_high = CorrelatedEventPair(
        correlation_id="CORR-2",
        anomaly=anomaly,
        article=article2,
        confidence_score=0.85,  # Accepted -> Max evidence = 0.85
    )

    assessment = service.evaluate_anomaly(anomaly, correlated_pairs=[pair_low, pair_high])

    # Channel CAPITAL_FLOW_SENSITIVITY (S=0.80, W=0.35)
    # Exposure HIGH (S=0.80, W=0.30)
    # Magnitude (S=1.0, W=0.20)
    # Evidence (S=0.85, W=0.15)
    # Weighted sum = (0.80*0.35) + (0.80*0.30) + (1.0*0.20) + (0.85*0.15) = 0.28 + 0.24 + 0.20 + 0.1275 = 0.8475
    # Total active weight = 1.0
    # Score = 0.8475 / 1.0 * 100.0 = 84.8 -> HIGH
    assert assessment.impact_score == 84.8
    assert assessment.impact_level == IndiaImpactLevel.HIGH
    assert assessment.capital_flow_risk == CapitalFlowRisk.HIGH_RISK


from app.domain.economic_event import EconomicEventCategory, EconomicImportance, NormalizedEconomicEvent


def test_assess_event_impact_xor_invariant(service):
    article = NormalizedArticle(
        id="ART-100",
        headline="Oil prices surge globally",
        summary=None,
        source_name="FT",
        source_url=None,
        article_url="https://example.com/100",
        author=None,
        published_at_utc="2026-07-29T10:00:00Z",
        published_at_ist="2026-07-29T15:30:00+05:30",
        primary_category=GlobalEventCategory.ENERGY,
        tags=["BRENT"],
    )
    econ_event = NormalizedEconomicEvent(
        id="EVT-100",
        country="US",
        event="US CPI Inflation",
        category=EconomicEventCategory.INFLATION,
        importance=EconomicImportance.HIGH,
        actual=3.4,
        forecast=3.2,
        previous=3.1,
        unit="%",
        timestamp_utc="2026-07-29T12:00:00Z",
        timestamp_ist="2026-07-29T17:30:00+05:30",
        source="TRADING_ECONOMICS",
    )


    # Valid Article XOR EconomicEvent calls
    res_art = service.assess_event_impact(article=article)
    assert res_art.impact_score > 0.0
    assert "[Oil prices surge globally]" in res_art.summary_rationale

    res_econ = service.assess_event_impact(economic_event=econ_event)
    assert res_econ is not None

    # Invalid: neither provided
    with pytest.raises(ValueError, match="article XOR economic_event"):
        service.assess_event_impact(article=None, economic_event=None)

    # Invalid: both provided
    with pytest.raises(ValueError, match="article XOR economic_event"):
        service.assess_event_impact(article=article, economic_event=econ_event)


def test_unsupported_rule_immediate_zero_impact_fallback(service):
    # Unrecognized symbol even with a massive change_percent returns canonical zero impact
    assessment = service.evaluate_raw_shock("UNKNOWN_XYZ", change_percent=50.0, asset_type="EQUITY")
    assert assessment.impact_score == 0.0
    assert assessment.impact_level == IndiaImpactLevel.NEGLIGIBLE
    assert assessment.impact_direction == ImpactDirection.NEUTRAL
    assert assessment.capital_flow_risk == CapitalFlowRisk.NEGLIGIBLE
    assert assessment.transmission_channels == []
    assert assessment.affected_sectors == []
    assert "No recognized India impact transmission rule" in assessment.summary_rationale


def test_event_rule_priority_candidate_resolution(service):
    # Article with multiple tags: first tag UNMAPPED, second tag BRENT -> resolves BRENT
    article = NormalizedArticle(
        id="ART-200",
        headline="OPEC meeting affects oil markets",
        summary=None,
        source_name="Reuters",
        source_url=None,
        article_url="https://example.com/200",
        author=None,
        published_at_utc="2026-07-29T10:00:00Z",
        published_at_ist="2026-07-29T15:30:00+05:30",
        primary_category=GlobalEventCategory.ENERGY,
        tags=["UNMAPPED_TAG", "BRENT"],
    )

    assessment = service.assess_event_impact(article=article)
    assert assessment.impact_score > 0.0
    assert TransmissionChannel.COMMODITY_IMPORT in assessment.transmission_channels

    # Economic event with country="US10Y" -> resolves US10Y
    econ_event = NormalizedEconomicEvent(
        id="EVT-200",
        country="US10Y",
        event="US Treasury Auction",
        category=EconomicEventCategory.INTEREST_RATE,
        importance=EconomicImportance.HIGH,
        actual=4.2,
        forecast=4.1,
        previous=4.0,
        unit="%",
        timestamp_utc="2026-07-29T12:00:00Z",
        timestamp_ist="2026-07-29T17:30:00+05:30",
        source="TRADING_ECONOMICS",
    )
    assessment_econ = service.assess_event_impact(economic_event=econ_event)
    assert assessment_econ.impact_score > 0.0
    assert TransmissionChannel.CAPITAL_FLOW_SENSITIVITY in assessment_econ.transmission_channels


def test_bond_canonical_yield_movement_contract(service):
    # 0.10 percentage points = 10 bps -> 10 / 20 = 0.50
    assert service.calculate_magnitude_score(0.10, "BOND") == 0.50
    # 0.20 percentage points = 20 bps -> 20 / 20 = 1.00
    assert service.calculate_magnitude_score(0.20, "BOND") == 1.00
    # 0.05 percentage points = 5 bps -> 5 / 20 = 0.25
    assert service.calculate_magnitude_score(0.05, "YIELD") == 0.25


def test_unknown_symbol_fallback_to_negligible(service):
    assessment = service.evaluate_raw_shock("UNKNOWN_TICKER", change_percent=1.0, asset_type="EQUITY")
    assert assessment.impact_score == 0.0
    assert assessment.impact_level == IndiaImpactLevel.NEGLIGIBLE

