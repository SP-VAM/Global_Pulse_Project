"""
Unit tests for Phase 4C Historical REST APIs & Dashboard Integration.
Verifies:
1. GET /api/v1/historical/anomalies with camelCase contracts and automatic AssetType 422 validation.
2. GET /api/v1/historical/impacts with ordered min_impact_level hierarchy filtering.
3. GET /api/v1/historical/trends with complete aggregate analytics response.
4. HTTP 400 Bad Request when from_date > to_date.
5. Controlled failure isolation for Dashboard GET /api/v1/dashboard (returns HTTP 200 with historicalSummary = null on error).
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.historical import router as historical_router
from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.india_impact import (
    CapitalFlowRisk,
    ImpactDirection,
    IndiaImpactAssessment,
    IndiaImpactLevel,
    IndianSectorSensitivity,
    SectorSensitivity,
    TransmissionChannel,
)
from app.main import create_app
from app.services.dashboard_service import DashboardService
from app.services.historical_analytics_service import HistoricalAnalyticsService
from app.services.historical_store import (
    InMemoryHistoricalSnapshotStore,
    create_anomaly_snapshot_from_domain,
    create_impact_snapshot_from_domain,
)


@pytest.fixture
def populated_store():
    store = InMemoryHistoricalSnapshotStore()

    # Ingest 2 anomalies (1 COMMODITY HIGH impact, 1 FOREX MEDIUM impact)
    anom1 = NormalizedAnomaly(
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
    snap1 = create_anomaly_snapshot_from_domain(anom1, "HIST-ANOM-1")

    anom2 = NormalizedAnomaly(
        id="ANOM-USDINR-1",
        symbol="USD/INR",
        asset_type="FOREX",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=84.0,
        previous_value=83.0,
        change_percent=1.2,
        observation_window="1h",
        severity=AnomalySeverity.MEDIUM,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-30T09:00:00Z",
        detected_at_ist="2026-07-30T14:30:00+05:30",
    )
    snap2 = create_anomaly_snapshot_from_domain(anom2, "HIST-ANOM-2")

    store.add_anomaly_snapshot(snap1)
    store.add_anomaly_snapshot(snap2)

    assess1 = IndiaImpactAssessment(
        impact_score=90.0,
        impact_level=IndiaImpactLevel.HIGH,
        impact_direction=ImpactDirection.NEGATIVE,
        capital_flow_risk=CapitalFlowRisk.MODERATE_RISK,
        transmission_channels=[TransmissionChannel.COMMODITY_IMPORT],
        affected_sectors=[IndianSectorSensitivity("PAINTS", ImpactDirection.NEGATIVE, SectorSensitivity.HIGH_SENSITIVITY, "Cost up")],
    )
    imp_snap1 = create_impact_snapshot_from_domain(assess1, anomaly=anom1, snapshot_id="HIST-IMP-1")

    assess2 = IndiaImpactAssessment(
        impact_score=65.0,
        impact_level=IndiaImpactLevel.MEDIUM,
        impact_direction=ImpactDirection.MIXED,
        capital_flow_risk=CapitalFlowRisk.LOW_RISK,
        transmission_channels=[TransmissionChannel.CURRENCY_INR],
        affected_sectors=[IndianSectorSensitivity("IT_SERVICES", ImpactDirection.POSITIVE, SectorSensitivity.HIGH_SENSITIVITY, "Revenue up")],
    )
    imp_snap2 = create_impact_snapshot_from_domain(assess2, anomaly=anom2, snapshot_id="HIST-IMP-2")

    store.add_impact_snapshot(imp_snap1)
    store.add_impact_snapshot(imp_snap2)

    return store


@pytest.fixture
def client(populated_store):
    app = FastAPI()
    app.include_router(historical_router, prefix="/api/v1")
    app.state.historical_store = populated_store
    app.state.historical_analytics_service = HistoricalAnalyticsService(store=populated_store)
    return TestClient(app)


def test_get_historical_anomalies_contracts_and_validation(client):
    # 1. Successful query
    response = client.get("/api/v1/historical/anomalies?symbol=BRENT")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "pagination" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["snapshotId"] == "HIST-ANOM-1"
    assert data["items"][0]["symbol"] == "BRENT"
    assert data["items"][0]["assetType"] == "COMMODITY"

    # 2. Automatic AssetType enum 422 validation
    invalid_res = client.get("/api/v1/historical/anomalies?asset_type=INVALID_ASSET")
    assert invalid_res.status_code == 422


def test_get_historical_impacts_ordered_hierarchy_filtering(client):
    # Filter min_impact_level=MEDIUM -> returns MEDIUM + HIGH (both 2 items)
    res_medium = client.get("/api/v1/historical/impacts?min_impact_level=MEDIUM")
    assert res_medium.status_code == 200
    data_med = res_medium.json()
    assert len(data_med["items"]) == 2

    # Filter min_impact_level=HIGH -> returns HIGH only (1 item)
    res_high = client.get("/api/v1/historical/impacts?min_impact_level=HIGH")
    assert res_high.status_code == 200
    data_high = res_high.json()
    assert len(data_high["items"]) == 1
    assert data_high["items"][0]["impactLevel"] == "HIGH"


def test_get_historical_trends_analytics_response(client):
    response = client.get("/api/v1/historical/trends")
    assert response.status_code == 200
    data = response.json()

    assert data["totalAnomaliesEvaluated"] == 2
    assert data["totalImpactAssessmentsEvaluated"] == 2
    assert data["averageImpactScore"] == 77.5
    assert data["peakImpactScore"] == 90.0
    assert "assetClassFrequencies" in data
    assert "channelDistributions" in data
    assert "sectorHitSummaries" in data


def test_invalid_date_range_returns_http_400(client):
    res = client.get("/api/v1/historical/anomalies?from_date=2026-08-01&to_date=2026-07-01")
    assert res.status_code == 400
    assert res.json()["detail"] == "from_date cannot be after to_date"


@pytest.mark.asyncio
async def test_dashboard_historical_failure_isolation():
    from httpx import ASGITransport, AsyncClient

    app = create_app()
    mock_news = AsyncMock()
    mock_news.search_news.return_value = []
    app.state.news_service = mock_news

    # Mock a failing HistoricalAnalyticsService
    class FailingAnalyticsService:
        def compute_trend_analytics(self, *args, **kwargs):
            raise RuntimeError("Controlled historical model failure for isolation testing")

    app.state.dashboard_service = DashboardService(
        news_service=mock_news,
        historical_analytics_service=FailingAnalyticsService(),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        res = await async_client.get("/api/v1/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert "feed" in data
        # Failure isolation preserved: returns HTTP 200 with historicalSummary = null
        assert data.get("historicalSummary") is None
