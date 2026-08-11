"""
Phase 3D — End-to-End Integration & Regression Verification Test Suite
Validates real service interaction: Market Quotes -> Anomaly Engine -> Correlation Engine -> India Impact Engine -> REST APIs & Dashboard.
No mocks used except for external HTTP/provider calls and intentional failure isolation testing.
"""
from unittest.mock import AsyncMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.india_impact import router as india_impact_router
from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.correlation import CorrelatedEventPair
from app.domain.india_impact import (
    CapitalFlowRisk,
    ImpactDirection,
    IndiaImpactLevel,
    TransmissionChannel,
)
from app.domain.instrument import NormalizedQuote
from app.domain.news import GlobalEventCategory, NormalizedArticle
from app.main import create_app
from app.services.anomaly_service import AnomalyDetectionService
from app.services.classification.india_vulnerability_matrix import (
    SHOCK_DIRECTION_VULNERABILITY_MATRIX,
)
from app.services.correlation_service import EventCorrelationService
from app.services.dashboard_service import DashboardService
from app.services.india_impact_service import IndiaImpactService


@pytest.fixture
def real_services():
    """Wire real Phase 2 and Phase 3 service objects without external mocks."""
    anomaly_service = AnomalyDetectionService()
    correlation_service = EventCorrelationService()
    india_impact_service = IndiaImpactService()
    mock_news_service = AsyncMock()

    dashboard_service = DashboardService(
        news_service=mock_news_service,
        anomaly_service=anomaly_service,
        correlation_service=correlation_service,
        india_impact_service=india_impact_service,
    )

    return {
        "anomaly_service": anomaly_service,
        "correlation_service": correlation_service,
        "india_impact_service": india_impact_service,
        "dashboard_service": dashboard_service,
        "mock_news_service": mock_news_service,
    }


# ───────────────────────────────────────────────────────────────────────────
# Scenario 1: BRENT Crude Oil Shock End-to-End Pipeline
# ───────────────────────────────────────────────────────────────────────────
def test_scenario_1_brent_crude_oil_shock_e2e(real_services):
    anomaly_service = real_services["anomaly_service"]
    correlation_service = real_services["correlation_service"]
    india_impact_service = real_services["india_impact_service"]

    # 1. Ingest deterministic Quote fixture
    quote = NormalizedQuote(
        symbol="BRENT",
        price=84.0,
        open=80.0,
        high=85.0,
        low=79.5,
        previous_close=80.0,
        change=4.0,
        change_percent=5.0,
        currency="USD",
        timestamp_utc="2026-07-30T08:00:00Z",
        timestamp_ist="2026-07-30T13:30:00+05:30",
        source="TEST_FIXTURE",
    )


    anomaly = anomaly_service.detect_quote_anomaly(quote, asset_type="COMMODITY")
    assert anomaly is not None
    assert anomaly.symbol == "BRENT"

    from datetime import timedelta
    from app.core.timezone import TimezoneService

    now_utc = TimezoneService.now_utc()
    pub_utc = now_utc - timedelta(minutes=5)
    pub_ist_str = TimezoneService.now_ist().isoformat()

    # 2. Ingest deterministic Article fixture
    article = NormalizedArticle(
        id="ART-BRENT-SPIKE",
        headline="Brent crude oil surges as supply tightens",
        summary="OPEC output restriction drives sudden international crude price spike.",
        source_name="Financial Times",
        source_url="https://ft.com",
        article_url="https://ft.com/brent-surge",
        author="Energy Desk",
        published_at_utc=pub_utc.isoformat(),
        published_at_ist=pub_ist_str,
        primary_category=GlobalEventCategory.ENERGY,
        tags=["BRENT"],
    )



    # 3. Real EventCorrelationService evaluates confidence
    pair = correlation_service.correlate_anomaly_with_article(anomaly, article)
    assert pair is not None
    assert pair.confidence_score >= 0.50
    c_calculated = pair.confidence_score

    # 4. Real IndiaImpactService evaluates anomaly with matched correlated pair
    assessment = india_impact_service.evaluate_anomaly(anomaly, correlated_pairs=[pair])

    # 5. Verify against authoritative 3A Matrix and 3B scoring equation
    rule_3a = SHOCK_DIRECTION_VULNERABILITY_MATRIX[("BRENT", "UP")]
    assert assessment.transmission_channels == [rule_3a["channel"]]
    assert assessment.impact_direction == rule_3a["overall_direction"]
    assert assessment.capital_flow_risk == rule_3a["capital_flow_risk"]

    # Check affected sectors
    sector_names = [s.sector_name for s in assessment.affected_sectors]
    expected_sectors = [s.sector_name for s in rule_3a["sectors"]]
    assert set(sector_names) == set(expected_sectors)

    # Derived score assertion: (0.35*1.0 + 0.30*1.0 + 0.20*1.0 + 0.15*c_calculated) * 100.0
    expected_score = round((0.35 * 1.0 + 0.30 * 1.0 + 0.20 * 1.0 + 0.15 * c_calculated) * 100.0, 1)
    assert assessment.impact_score == expected_score
    assert assessment.impact_level == IndiaImpactLevel.HIGH


# ───────────────────────────────────────────────────────────────────────────
# Scenario 2: USD/INR Forex Shock End-to-End Pipeline
# ───────────────────────────────────────────────────────────────────────────
def test_scenario_2_usd_inr_forex_shock_e2e(real_services):
    anomaly_service = real_services["anomaly_service"]
    india_impact_service = real_services["india_impact_service"]

    quote = NormalizedQuote(
        symbol="USD/INR",
        price=84.245,
        open=83.0,
        high=84.5,
        low=82.9,
        previous_close=83.0,
        change=1.245,
        change_percent=1.5,
        currency="INR",
        timestamp_utc="2026-07-30T08:30:00Z",
        timestamp_ist="2026-07-30T14:00:00+05:30",
        source="TEST_FIXTURE",
    )
    anomaly = anomaly_service.detect_quote_anomaly(quote, asset_type="FOREX")
    assert anomaly is not None

    assessment = india_impact_service.evaluate_anomaly(anomaly, correlated_pairs=[])

    rule_3a = SHOCK_DIRECTION_VULNERABILITY_MATRIX[("USD/INR", "UP")]
    assert assessment.transmission_channels == [rule_3a["channel"]]
    assert assessment.impact_direction == rule_3a["overall_direction"]
    assert assessment.capital_flow_risk == rule_3a["capital_flow_risk"]

    sector_names = [s.sector_name for s in assessment.affected_sectors]
    expected_sectors = [s.sector_name for s in rule_3a["sectors"]]
    assert set(sector_names) == set(expected_sectors)

    # Formula without evidence: ((0.35*1.0 + 0.30*1.0 + 0.20*0.75) / 0.85) * 100 = 94.1
    assert assessment.impact_score == 94.1
    assert assessment.impact_level == IndiaImpactLevel.HIGH


# ───────────────────────────────────────────────────────────────────────────
# Scenario 3: US10Y Bond Yield Shock End-to-End Pipeline
# ───────────────────────────────────────────────────────────────────────────
def test_scenario_3_us10y_bond_yield_shock_e2e(real_services):
    anomaly_service = real_services["anomaly_service"]
    india_impact_service = real_services["india_impact_service"]

    # Yield move of 0.25% (25 bps) triggers threshold (>= 10 bps)
    quote = NormalizedQuote(
        symbol="US10Y",
        price=4.25,
        open=4.0,
        high=4.30,
        low=3.98,
        previous_close=4.00,
        change=0.25,
        change_percent=0.25,
        currency="USD",
        timestamp_utc="2026-07-30T09:00:00Z",
        timestamp_ist="2026-07-30T14:30:00+05:30",
        source="TEST_FIXTURE",
    )
    anomaly = anomaly_service.detect_quote_anomaly(quote, asset_type="BOND")
    assert anomaly is not None

    assessment = india_impact_service.evaluate_anomaly(anomaly, correlated_pairs=[])

    rule_3a = SHOCK_DIRECTION_VULNERABILITY_MATRIX[("US10Y", "UP")]
    assert assessment.transmission_channels == [rule_3a["channel"]]
    assert assessment.impact_direction == rule_3a["overall_direction"]
    assert assessment.capital_flow_risk == rule_3a["capital_flow_risk"]

    sector_names = [s.sector_name for s in assessment.affected_sectors]
    expected_sectors = [s.sector_name for s in rule_3a["sectors"]]
    assert set(sector_names) == set(expected_sectors)

    # Formula without evidence: ((0.35*0.8 + 0.30*0.8 + 0.20*1.0) / 0.85) * 100 = 84.7
    assert assessment.impact_score == 84.7
    assert assessment.impact_level == IndiaImpactLevel.HIGH


# ───────────────────────────────────────────────────────────────────────────
# Scenario 4: Direction-Aware Transmission Rules (BRENT UP vs DOWN)
# ───────────────────────────────────────────────────────────────────────────
def test_scenario_4_direction_aware_brent_up_vs_down(real_services):
    india_impact_service = real_services["india_impact_service"]

    shock_up = india_impact_service.evaluate_raw_shock(symbol="BRENT", change_percent=5.0, asset_type="COMMODITY")
    shock_down = india_impact_service.evaluate_raw_shock(symbol="BRENT", change_percent=-5.0, asset_type="COMMODITY")

    rule_up = SHOCK_DIRECTION_VULNERABILITY_MATRIX[("BRENT", "UP")]
    rule_down = SHOCK_DIRECTION_VULNERABILITY_MATRIX[("BRENT", "DOWN")]

    # Magnitudes match
    assert shock_up.impact_score == shock_down.impact_score

    # Directions and capital flow risks reverse
    assert shock_up.impact_direction == rule_up["overall_direction"]  # NEGATIVE
    assert shock_down.impact_direction == rule_down["overall_direction"]  # POSITIVE

    assert shock_up.capital_flow_risk == rule_up["capital_flow_risk"]  # MODERATE_RISK
    assert shock_down.capital_flow_risk == rule_down["capital_flow_risk"]  # LOW_RISK


# ───────────────────────────────────────────────────────────────────────────
# Scenario 5: Correlation Confidence Boundary Verification (0.4999 vs 0.5000)
# ───────────────────────────────────────────────────────────────────────────
def test_scenario_5_correlation_confidence_boundary_filtering(real_services):
    india_impact_service = real_services["india_impact_service"]

    anomaly = NormalizedAnomaly(
        id="ANOM-BOUNDARY-TEST",
        symbol="BRENT",
        asset_type="COMMODITY",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=85.0,
        previous_value=80.0,
        change_percent=5.0,
        observation_window="1h",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-30T08:00:00Z",
        detected_at_ist="2026-07-30T13:30:00+05:30",
    )

    art_below = NormalizedArticle(
        id="ART-04999",
        headline="Unrelated energy report",
        summary=None,
        source_name="Blog",
        source_url=None,
        article_url="https://example.com/04999",
        author=None,
        published_at_utc="2026-07-30T07:50:00Z",
        published_at_ist="2026-07-30T13:20:00+05:30",
        primary_category=GlobalEventCategory.ENERGY,
    )

    art_exact = NormalizedArticle(
        id="ART-05000",
        headline="Exact boundary energy report",
        summary=None,
        source_name="News",
        source_url=None,
        article_url="https://example.com/05000",
        author=None,
        published_at_utc="2026-07-30T07:50:00Z",
        published_at_ist="2026-07-30T13:20:00+05:30",
        primary_category=GlobalEventCategory.ENERGY,
    )

    art_high = NormalizedArticle(
        id="ART-07500",
        headline="High confidence energy report",
        summary=None,
        source_name="Reuters",
        source_url=None,
        article_url="https://example.com/07500",
        author=None,
        published_at_utc="2026-07-30T07:55:00Z",
        published_at_ist="2026-07-30T13:25:00+05:30",
        primary_category=GlobalEventCategory.ENERGY,
    )

    pair_rejected = CorrelatedEventPair(
        correlation_id="CORR-REJECT", anomaly=anomaly, article=art_below, confidence_score=0.4999
    )
    pair_exact = CorrelatedEventPair(
        correlation_id="CORR-EXACT", anomaly=anomaly, article=art_exact, confidence_score=0.5000
    )
    pair_accepted = CorrelatedEventPair(
        correlation_id="CORR-HIGH", anomaly=anomaly, article=art_high, confidence_score=0.7500
    )

    # 1. Evaluate with pair at 0.4999 -> pair rejected, evidence component treated as inactive
    assess_rejected = india_impact_service.evaluate_anomaly(anomaly, correlated_pairs=[pair_rejected])
    score_no_evidence = round(((0.35 * 1.0 + 0.30 * 1.0 + 0.20 * 1.0) / 0.85) * 100.0, 1)
    assert assess_rejected.impact_score == score_no_evidence

    # 2. Evaluate with pair at 0.5000 -> accepted! Evidence = 0.50
    assess_exact = india_impact_service.evaluate_anomaly(anomaly, correlated_pairs=[pair_exact])
    score_exact_evidence = round((0.35 * 1.0 + 0.30 * 1.0 + 0.20 * 1.0 + 0.15 * 0.50) * 100.0, 1)
    assert assess_exact.impact_score == score_exact_evidence

    # 3. Evaluate with all pairs -> Pair A rejected, max(0.5000, 0.7500) = 0.7500 used for evidence
    assess_multi = india_impact_service.evaluate_anomaly(
        anomaly, correlated_pairs=[pair_rejected, pair_exact, pair_accepted]
    )
    score_multi_evidence = round((0.35 * 1.0 + 0.30 * 1.0 + 0.20 * 1.0 + 0.15 * 0.75) * 100.0, 1)
    assert assess_multi.impact_score == score_multi_evidence


# ───────────────────────────────────────────────────────────────────────────
# Scenario 6: Unsupported Asset Fallback Verification
# ───────────────────────────────────────────────────────────────────────────
def test_scenario_6_unsupported_asset_fallback(real_services):
    india_impact_service = real_services["india_impact_service"]

    assessment = india_impact_service.evaluate_raw_shock(
        symbol="UNSUPPORTED_TICKER_XYZ", change_percent=15.0, asset_type="EQUITY"
    )

    assert assessment.impact_score == 0.0
    assert assessment.impact_level == IndiaImpactLevel.NEGLIGIBLE
    assert assessment.impact_direction == ImpactDirection.NEUTRAL
    assert assessment.capital_flow_risk == CapitalFlowRisk.NEGLIGIBLE
    assert assessment.transmission_channels == []
    assert assessment.affected_sectors == []


# ───────────────────────────────────────────────────────────────────────────
# Scenario 7: REST API Contracts, Ordered Filtering, Sorting & Pagination
# ───────────────────────────────────────────────────────────────────────────
def test_scenario_7_rest_api_contracts_filtering_sorting(real_services):
    anomaly_service = real_services["anomaly_service"]
    correlation_service = real_services["correlation_service"]
    india_impact_service = real_services["india_impact_service"]

    app = FastAPI()
    app.include_router(india_impact_router, prefix="/api/v1")
    app.state.anomaly_service = anomaly_service
    app.state.correlation_service = correlation_service
    app.state.india_impact_service = india_impact_service

    client = TestClient(app)

    # Ingest 2 anomalies into real AnomalyDetectionService
    q1 = NormalizedQuote("BRENT", 84.0, 80.0, 85.0, 79.0, 80.0, 4.0, 5.0, "USD", "2026-07-30T08:00:00Z", "2026-07-30T13:30:00+05:30", "TEST")
    q2 = NormalizedQuote("USD/INR", 84.245, 83.0, 84.5, 82.9, 83.0, 1.245, 1.5, "INR", "2026-07-30T09:00:00Z", "2026-07-30T14:30:00+05:30", "TEST")

    anomaly_service.detect_quote_anomaly(q1, asset_type="COMMODITY")
    anomaly_service.detect_quote_anomaly(q2, asset_type="FOREX")


    response = client.get("/api/v1/india-impact?min_impact_level=HIGH")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "pagination" in data

    # Verify camelCase keys
    for item in data["items"]:
        assert "anomalyId" in item
        assert "impactScore" in item
        assert "impactLevel" in item
        assert "capitalFlowRisk" in item
        assert "transmissionChannels" in item
        assert "affectedSectors" in item
        assert "summaryRationale" in item

    # Verify sorting: impactScore DESC
    scores = [item["impactScore"] for item in data["items"]]
    assert scores == sorted(scores, reverse=True)


# ───────────────────────────────────────────────────────────────────────────
# Scenario 8: Dashboard Integration & Controlled Failure Isolation
# ───────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scenario_8_dashboard_integration_and_failure_isolation(real_services):
    from httpx import ASGITransport, AsyncClient

    app = create_app()

    # 1. Normal execution: dashboard renders indiaImpactSummary widget
    app.state.anomaly_service = real_services["anomaly_service"]
    app.state.correlation_service = real_services["correlation_service"]
    app.state.india_impact_service = real_services["india_impact_service"]
    app.state.news_service = real_services["mock_news_service"]
    app.state.news_service.search_news.return_value = []

    app.state.dashboard_service = DashboardService(
        news_service=app.state.news_service,
        anomaly_service=app.state.anomaly_service,
        correlation_service=app.state.correlation_service,
        india_impact_service=app.state.india_impact_service,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert "indiaImpactSummary" in data

    # Ingest an anomaly so india_impact_service.evaluate_anomaly is invoked
    q_brent = NormalizedQuote("BRENT", 85.0, 80.0, 86.0, 79.0, 80.0, 5.0, 6.25, "USD", "2026-07-30T10:00:00Z", "2026-07-30T15:30:00+05:30", "TEST")
    app.state.anomaly_service.detect_quote_anomaly(q_brent, asset_type="COMMODITY")

    # 2. Controlled failure isolation test: mock failing IndiaImpactService
    class FailingIndiaImpactService:
        def evaluate_anomaly(self, *args, **kwargs):
            raise RuntimeError("Controlled model failure for testing isolation")

    app.state.dashboard_service = DashboardService(
        news_service=app.state.news_service,
        anomaly_service=app.state.anomaly_service,
        correlation_service=app.state.correlation_service,
        india_impact_service=FailingIndiaImpactService(),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res_fail = await client.get("/api/v1/dashboard")
        assert res_fail.status_code == 200
        data_fail = res_fail.json()
        assert "feed" in data_fail
        # Failure isolation preserved: returns HTTP 200 with indiaImpactSummary = null
        assert data_fail.get("indiaImpactSummary") is None

