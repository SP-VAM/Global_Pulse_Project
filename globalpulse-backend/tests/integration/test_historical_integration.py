"""
Phase 4D — End-to-End Integration & Regression Verification Test Suite for Phase 4.
Validates real service interaction: Market Quotes -> Anomaly Engine -> Correlation Engine -> India Impact Engine -> Historical Store -> Trend Analytics -> REST APIs & Dashboard.
No mocks used except for external HTTP/provider calls and intentional failure isolation testing.
"""
from datetime import timedelta
from unittest.mock import AsyncMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.api.v1.historical import router as historical_router
from app.core.timezone import TimezoneService
from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.correlation import DEFAULT_MIN_CONFIDENCE, CorrelatedEventPair
from app.domain.india_impact import (
    CapitalFlowRisk,
    ImpactDirection,
    IndiaImpactAssessment,
    IndiaImpactLevel,
    TransmissionChannel,
)

from app.domain.instrument import NormalizedQuote
from app.domain.news import GlobalEventCategory, NormalizedArticle
from app.main import create_app
from app.services.anomaly_service import AnomalyDetectionService
from app.services.correlation_service import EventCorrelationService
from app.services.dashboard_service import DashboardService
from app.services.historical_analytics_service import HistoricalAnalyticsService
from app.services.historical_store import (
    InMemoryHistoricalSnapshotStore,
    create_anomaly_snapshot_from_domain,
    create_impact_snapshot_from_domain,
)
from app.services.india_impact_service import IndiaImpactService


@pytest.fixture
def real_phase4_environment():
    """Wire real Phase 2, 3, and 4 service objects without external mocks."""
    anomaly_service = AnomalyDetectionService()
    correlation_service = EventCorrelationService()
    india_impact_service = IndiaImpactService()
    historical_store = InMemoryHistoricalSnapshotStore(max_anomaly_items=500, max_impact_items=500)
    analytics_service = HistoricalAnalyticsService(store=historical_store)
    mock_news_service = AsyncMock()

    dashboard_service = DashboardService(
        news_service=mock_news_service,
        anomaly_service=anomaly_service,
        correlation_service=correlation_service,
        india_impact_service=india_impact_service,
        historical_analytics_service=analytics_service,
    )

    return {
        "anomaly_service": anomaly_service,
        "correlation_service": correlation_service,
        "india_impact_service": india_impact_service,
        "historical_store": historical_store,
        "analytics_service": analytics_service,
        "dashboard_service": dashboard_service,
        "mock_news_service": mock_news_service,
    }


# ───────────────────────────────────────────────────────────────────────────
# Scenario 1: True End-to-End Historical Pipeline Flow
# ───────────────────────────────────────────────────────────────────────────
def test_scenario_1_true_e2e_historical_pipeline_flow(real_phase4_environment):
    anomaly_service = real_phase4_environment["anomaly_service"]
    correlation_service = real_phase4_environment["correlation_service"]
    india_impact_service = real_phase4_environment["india_impact_service"]
    historical_store = real_phase4_environment["historical_store"]
    analytics_service = real_phase4_environment["analytics_service"]

    # 1. Ingest market quote for BRENT crude oil
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

    # 2. Correlate with dynamic news article
    now_utc = TimezoneService.now_utc()
    pub_utc = now_utc - timedelta(minutes=5)
    pub_ist = TimezoneService.now_ist()

    article = NormalizedArticle(
        id="ART-BRENT-CRUDE-1",
        headline="Brent crude surges on supply tightness",
        summary="Crude oil benchmark spikes sharply.",
        source_name="Reuters",
        source_url="https://reuters.com",
        article_url="https://reuters.com/brent",
        author="Energy Desk",
        published_at_utc=pub_utc.isoformat(),
        published_at_ist=pub_ist.isoformat(),
        primary_category=GlobalEventCategory.ENERGY,
        tags=["BRENT"],
    )
    pair = correlation_service.correlate_anomaly_with_article(anomaly, article)
    assert pair is not None
    assert pair.confidence_score >= DEFAULT_MIN_CONFIDENCE

    # 3. Evaluate India Impact
    assessment = india_impact_service.evaluate_anomaly(anomaly, correlated_pairs=[pair])
    assert assessment.impact_score > 0.0

    # 4. Capture historical snapshots into store
    anom_snap = create_anomaly_snapshot_from_domain(anomaly)
    imp_snap = create_impact_snapshot_from_domain(assessment, anomaly=anomaly, correlated_pairs=[pair])

    historical_store.add_anomaly_snapshot(anom_snap)
    historical_store.add_impact_snapshot(imp_snap)

    # 5. Query via REST API client
    app = FastAPI()
    app.include_router(historical_router, prefix="/api/v1")
    app.state.historical_store = historical_store
    app.state.historical_analytics_service = analytics_service

    client = TestClient(app)

    res_anom = client.get("/api/v1/historical/anomalies?symbol=BRENT")
    assert res_anom.status_code == 200
    assert res_anom.json()["items"][0]["anomalyId"] == anomaly.id

    res_imp = client.get("/api/v1/historical/impacts?symbol=BRENT")
    assert res_imp.status_code == 200
    assert res_imp.json()["items"][0]["symbol"] == "BRENT"
    assert res_imp.json()["items"][0]["hasCorrelationEvidence"] is True

    res_trends = client.get("/api/v1/historical/trends")
    assert res_trends.status_code == 200
    assert res_trends.json()["totalAnomaliesEvaluated"] == 1
    assert res_trends.json()["totalImpactAssessmentsEvaluated"] == 1


# ───────────────────────────────────────────────────────────────────────────
# Scenario 2: Multi-Asset Historical Trend Aggregation
# ───────────────────────────────────────────────────────────────────────────
def test_scenario_2_multi_asset_trend_aggregation(real_phase4_environment):
    store = real_phase4_environment["historical_store"]
    analytics_service = real_phase4_environment["analytics_service"]

    # Ingest 3 asset snapshots: BRENT (COMMODITY), USD/INR (FOREX), US10Y (BOND)
    anom_comm = NormalizedAnomaly("A1", "BRENT", "COMMODITY", AnomalyMetric.PRICE_SPIKE, 85.0, 80.0, 5.0, "1h", AnomalySeverity.HIGH, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-30T10:00:00Z", "2026-07-30T15:30:00+05:30")
    anom_forex = NormalizedAnomaly("A2", "USD/INR", "FOREX", AnomalyMetric.PRICE_SPIKE, 84.0, 83.0, 1.2, "1h", AnomalySeverity.MEDIUM, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-30T11:00:00Z", "2026-07-30T16:30:00+05:30")
    anom_bond = NormalizedAnomaly("A3", "US10Y", "BOND", AnomalyMetric.PRICE_SPIKE, 4.25, 4.0, 0.25, "1h", AnomalySeverity.HIGH, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-30T12:00:00Z", "2026-07-30T17:30:00+05:30")

    store.add_anomaly_snapshot(create_anomaly_snapshot_from_domain(anom_comm))
    store.add_anomaly_snapshot(create_anomaly_snapshot_from_domain(anom_forex))
    store.add_anomaly_snapshot(create_anomaly_snapshot_from_domain(anom_bond))

    assess_comm = IndiaImpactAssessment(90.0, IndiaImpactLevel.HIGH, ImpactDirection.NEGATIVE, CapitalFlowRisk.MODERATE_RISK, [TransmissionChannel.COMMODITY_IMPORT])
    assess_forex = IndiaImpactAssessment(94.1, IndiaImpactLevel.HIGH, ImpactDirection.MIXED, CapitalFlowRisk.MODERATE_RISK, [TransmissionChannel.CURRENCY_INR])
    assess_bond = IndiaImpactAssessment(84.7, IndiaImpactLevel.HIGH, ImpactDirection.NEGATIVE, CapitalFlowRisk.HIGH_RISK, [TransmissionChannel.CAPITAL_FLOW_SENSITIVITY])

    store.add_impact_snapshot(create_impact_snapshot_from_domain(assess_comm, anomaly=anom_comm))
    store.add_impact_snapshot(create_impact_snapshot_from_domain(assess_forex, anomaly=anom_forex))
    store.add_impact_snapshot(create_impact_snapshot_from_domain(assess_bond, anomaly=anom_bond))

    trends = analytics_service.compute_trend_analytics()

    assert trends.total_anomalies_evaluated == 3
    assert trends.total_impact_assessments_evaluated == 3
    # Average score = (90.0 + 94.1 + 84.7) / 3 = 89.6
    assert trends.average_impact_score == 89.6
    assert trends.peak_impact_score == 94.1

    # Deterministic sort for asset_class_frequencies: (count DESC, asset_type ASC)
    # Counts are all 1 -> sort alphabetical asset_type ASC: BOND < COMMODITY < FOREX
    asset_types = [a.asset_type for a in trends.asset_class_frequencies]
    assert asset_types == ["BOND", "COMMODITY", "FOREX"]


# ───────────────────────────────────────────────────────────────────────────
# Scenario 3: Date Boundary Filtering & Invalid Range HTTP 400
# ───────────────────────────────────────────────────────────────────────────
def test_scenario_3_date_boundary_filtering_and_http_400(real_phase4_environment):
    store = real_phase4_environment["historical_store"]

    anom1 = NormalizedAnomaly("A1", "BRENT", "COMMODITY", AnomalyMetric.PRICE_SPIKE, 85.0, 80.0, 5.0, "1h", AnomalySeverity.HIGH, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-01T10:00:00Z", "2026-07-01T15:30:00+05:30")
    anom2 = NormalizedAnomaly("A2", "BRENT", "COMMODITY", AnomalyMetric.PRICE_SPIKE, 88.0, 85.0, 3.5, "1h", AnomalySeverity.HIGH, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-15T10:00:00Z", "2026-07-15T15:30:00+05:30")
    anom3 = NormalizedAnomaly("A3", "BRENT", "COMMODITY", AnomalyMetric.PRICE_SPIKE, 90.0, 88.0, 2.2, "1h", AnomalySeverity.HIGH, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-30T10:00:00Z", "2026-07-30T15:30:00+05:30")

    store.add_anomaly_snapshot(create_anomaly_snapshot_from_domain(anom1))
    store.add_anomaly_snapshot(create_anomaly_snapshot_from_domain(anom2))
    store.add_anomaly_snapshot(create_anomaly_snapshot_from_domain(anom3))

    app = FastAPI()
    app.include_router(historical_router, prefix="/api/v1")
    app.state.historical_store = store

    client = TestClient(app)

    # 1. Valid range 2026-07-10 to 2026-07-20 -> returns only 2026-07-15 snapshot
    res_valid = client.get("/api/v1/historical/anomalies?from_date=2026-07-10&to_date=2026-07-20")
    assert res_valid.status_code == 200
    data_valid = res_valid.json()
    assert len(data_valid["items"]) == 1
    assert data_valid["items"][0]["anomalyId"] == "A2"

    # 2. Invalid range from_date > to_date -> HTTP 400 Bad Request
    res_invalid = client.get("/api/v1/historical/anomalies?from_date=2026-08-01&to_date=2026-07-01")
    assert res_invalid.status_code == 400
    assert res_invalid.json()["detail"] == "from_date cannot be after to_date"


# ───────────────────────────────────────────────────────────────────────────
# Scenario 4: Repository Page Exhaustion Beyond 1 Page (250 Snapshots)
# ───────────────────────────────────────────────────────────────────────────
def test_scenario_4_repository_page_exhaustion_over_250_snapshots():
    store = InMemoryHistoricalSnapshotStore(max_anomaly_items=300, max_impact_items=300)
    analytics_service = HistoricalAnalyticsService(store=store)

    # Populate 250 matching anomaly snapshots and 250 matching impact snapshots
    for i in range(1, 251):
        anom = NormalizedAnomaly(
            id=f"ANOM-E2E-{i}",
            symbol="BRENT",
            asset_type="COMMODITY",
            metric=AnomalyMetric.PRICE_SPIKE,
            current_value=80.0 + i * 0.1,
            previous_value=80.0,
            change_percent=4.0,
            observation_window="1h",
            severity=AnomalySeverity.HIGH,
            detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
            detected_at_utc="2026-07-30T10:00:00Z",
            detected_at_ist="2026-07-30T15:30:00+05:30",
        )
        store.add_anomaly_snapshot(create_anomaly_snapshot_from_domain(anom, f"HIST-ANOM-{i}"))

        assess = IndiaImpactAssessment(
            impact_score=80.0,
            impact_level=IndiaImpactLevel.HIGH,
            impact_direction=ImpactDirection.NEGATIVE,
            capital_flow_risk=CapitalFlowRisk.MODERATE_RISK,
            transmission_channels=[TransmissionChannel.COMMODITY_IMPORT],
        )
        store.add_impact_snapshot(create_impact_snapshot_from_domain(assess, anomaly=anom, snapshot_id=f"HIST-IMP-{i}"))

    app = FastAPI()
    app.include_router(historical_router, prefix="/api/v1")
    app.state.historical_store = store
    app.state.historical_analytics_service = analytics_service

    client = TestClient(app)

    res = client.get("/api/v1/historical/trends")
    assert res.status_code == 200
    data = res.json()

    # Exhaustion check: evaluated all 250 records across 3 pages (100 + 100 + 50)
    assert data["totalAnomaliesEvaluated"] == 250
    assert data["totalImpactAssessmentsEvaluated"] == 250


# ───────────────────────────────────────────────────────────────────────────
# Scenario 5: API Contracts & Automatic AssetType 422 Validation
# ───────────────────────────────────────────────────────────────────────────
def test_scenario_5_api_contracts_and_asset_type_validation(real_phase4_environment):
    store = real_phase4_environment["historical_store"]

    anom = NormalizedAnomaly("A1", "BRENT", "COMMODITY", AnomalyMetric.PRICE_SPIKE, 85.0, 80.0, 5.0, "1h", AnomalySeverity.HIGH, DetectionMethod.DETERMINISTIC_THRESHOLD, "2026-07-30T10:00:00Z", "2026-07-30T15:30:00+05:30")
    store.add_anomaly_snapshot(create_anomaly_snapshot_from_domain(anom))

    app = FastAPI()
    app.include_router(historical_router, prefix="/api/v1")
    app.state.historical_store = store

    client = TestClient(app)

    # 1. Invalid asset type string returns 422 HTTP
    res_422 = client.get("/api/v1/historical/anomalies?asset_type=INVALID_TYPE")
    assert res_422.status_code == 422

    # 2. Valid response serializes camelCase keys
    res_200 = client.get("/api/v1/historical/anomalies?asset_type=COMMODITY")
    assert res_200.status_code == 200
    item = res_200.json()["items"][0]
    assert "snapshotId" in item
    assert "anomalyId" in item
    assert "detectedAtUtc" in item
    assert "changePercent" in item


# ───────────────────────────────────────────────────────────────────────────
# Scenario 6: Ordered min_impact_level Hierarchy Filtering
# ───────────────────────────────────────────────────────────────────────────
def test_scenario_6_ordered_min_impact_level_hierarchy(real_phase4_environment):
    store = real_phase4_environment["historical_store"]

    assess_high = IndiaImpactAssessment(90.0, IndiaImpactLevel.HIGH, ImpactDirection.NEGATIVE, CapitalFlowRisk.MODERATE_RISK, [TransmissionChannel.COMMODITY_IMPORT])
    assess_med = IndiaImpactAssessment(65.0, IndiaImpactLevel.MEDIUM, ImpactDirection.MIXED, CapitalFlowRisk.LOW_RISK, [TransmissionChannel.CURRENCY_INR])

    store.add_impact_snapshot(create_impact_snapshot_from_domain(assess_high, snapshot_id="HIST-HIGH"))
    store.add_impact_snapshot(create_impact_snapshot_from_domain(assess_med, snapshot_id="HIST-MED"))

    app = FastAPI()
    app.include_router(historical_router, prefix="/api/v1")
    app.state.historical_store = store

    client = TestClient(app)

    # min_impact_level=MEDIUM -> returns MEDIUM + HIGH (2 items)
    res_med = client.get("/api/v1/historical/impacts?min_impact_level=MEDIUM")
    assert res_med.status_code == 200
    assert len(res_med.json()["items"]) == 2

    # min_impact_level=HIGH -> returns HIGH only (1 item)
    res_high = client.get("/api/v1/historical/impacts?min_impact_level=HIGH")
    assert res_high.status_code == 200
    assert len(res_high.json()["items"]) == 1
    assert res_high.json()["items"][0]["impactLevel"] == "HIGH"


# ───────────────────────────────────────────────────────────────────────────
# Scenario 7: Dashboard Integration & Controlled Failure Isolation
# ───────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_scenario_7_dashboard_historical_integration_and_failure_isolation(real_phase4_environment):
    app = create_app()

    # 1. Normal execution: dashboard renders historicalSummary widget
    app.state.anomaly_service = real_phase4_environment["anomaly_service"]
    app.state.correlation_service = real_phase4_environment["correlation_service"]
    app.state.india_impact_service = real_phase4_environment["india_impact_service"]
    app.state.historical_store = real_phase4_environment["historical_store"]
    app.state.historical_analytics_service = real_phase4_environment["analytics_service"]
    app.state.news_service = real_phase4_environment["mock_news_service"]
    app.state.news_service.search_news.return_value = []

    app.state.dashboard_service = DashboardService(
        news_service=app.state.news_service,
        anomaly_service=app.state.anomaly_service,
        correlation_service=app.state.correlation_service,
        india_impact_service=app.state.india_impact_service,
        historical_analytics_service=app.state.historical_analytics_service,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        res = await async_client.get("/api/v1/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert "historicalSummary" in data

    # 2. Controlled failure isolation test: mock failing HistoricalAnalyticsService
    class FailingHistoricalAnalyticsService:
        def compute_trend_analytics(self, *args, **kwargs):
            raise RuntimeError("Controlled historical analytics model failure for isolation testing")

    app.state.dashboard_service = DashboardService(
        news_service=app.state.news_service,
        anomaly_service=app.state.anomaly_service,
        correlation_service=app.state.correlation_service,
        india_impact_service=app.state.india_impact_service,
        historical_analytics_service=FailingHistoricalAnalyticsService(),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        res_fail = await async_client.get("/api/v1/dashboard")
        assert res_fail.status_code == 200
        data_fail = res_fail.json()
        assert "feed" in data_fail
        # Failure isolation preserved: returns HTTP 200 with historicalSummary = null
        assert data_fail.get("historicalSummary") is None


# ───────────────────────────────────────────────────────────────────────────
# Scenario 8: Empty Store Fallback Safety
# ───────────────────────────────────────────────────────────────────────────
def test_scenario_8_empty_store_fallback_safety():
    store = InMemoryHistoricalSnapshotStore()
    analytics_service = HistoricalAnalyticsService(store=store)

    app = FastAPI()
    app.include_router(historical_router, prefix="/api/v1")
    app.state.historical_store = store
    app.state.historical_analytics_service = analytics_service

    client = TestClient(app)

    res = client.get("/api/v1/historical/trends")
    assert res.status_code == 200
    data = res.json()

    assert data["totalAnomaliesEvaluated"] == 0
    assert data["totalImpactAssessmentsEvaluated"] == 0
    assert data["averageImpactScore"] == 0.0
    assert data["peakImpactScore"] == 0.0
    assert data["assetClassFrequencies"] == []
    assert data["channelDistributions"] == []
    assert data["sectorHitSummaries"] == []
    assert len(data["impactLevelCounts"]) == 4
