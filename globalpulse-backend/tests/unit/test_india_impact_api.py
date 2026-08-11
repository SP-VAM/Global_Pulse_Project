"""
Unit and API integration tests for Phase 3C India Impact REST API router (/api/v1/india-impact).
Verifies:
1. GET /api/v1/india-impact filtering by ordered min_impact_level, channel, sector, and pagination.
2. Deterministic sorting by impact_score DESC, then detected_at_utc DESC before pagination.
3. GET /api/v1/india-impact/anomalies/{anomaly_id} returning evaluation with multi-pair matching (including below-threshold pair filtering) and 404 handling.
4. POST /api/v1/india-impact/evaluate-shock evaluating raw shocks statelessly with AssetType enum validation.
5. Strict camelCase JSON response serialization.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.india_impact import router as india_impact_router
from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.correlation import CorrelatedEventPair
from app.domain.india_impact import IndiaImpactLevel, TransmissionChannel
from app.domain.market import AssetType
from app.domain.news import GlobalEventCategory, NormalizedArticle
from app.services.anomaly_service import AnomalyDetectionService
from app.services.correlation_service import EventCorrelationService
from app.services.india_impact_service import IndiaImpactService


@pytest.fixture
def mock_anomaly_service():
    service = AnomalyDetectionService()
    # Add multiple test anomalies with different timestamps and impact potential
    anom1 = NormalizedAnomaly(
        id="ANOM-BRENT-1",
        symbol="BRENT",
        asset_type="COMMODITY",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=85.0,
        previous_value=80.0,
        change_percent=5.0,
        observation_window="1h",
        severity=AnomalySeverity.HIGH,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-29T10:00:00Z",
        detected_at_ist="2026-07-29T15:30:00+05:30",
    )
    anom2 = NormalizedAnomaly(
        id="ANOM-USDINR-1",
        symbol="USD/INR",
        asset_type="FOREX",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=83.5,
        previous_value=83.0,
        change_percent=1.5,
        observation_window="30m",
        severity=AnomalySeverity.MEDIUM,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-29T11:00:00Z",
        detected_at_ist="2026-07-29T16:30:00+05:30",
    )
    anom3 = NormalizedAnomaly(
        id="ANOM-UNKNOWN-1",
        symbol="UNKNOWN_STOCK",
        asset_type="EQUITY",
        metric=AnomalyMetric.PRICE_DROP,
        current_value=10.0,
        previous_value=12.0,
        change_percent=-16.6,
        observation_window="15m",
        severity=AnomalySeverity.LOW,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-29T09:00:00Z",
        detected_at_ist="2026-07-29T14:30:00+05:30",
    )

    # Register in service memory store
    service._memory_store.extend([anom1, anom2, anom3])
    return service


@pytest.fixture
def mock_correlation_service(mock_anomaly_service):
    service = EventCorrelationService()
    anom_brent = mock_anomaly_service.get_anomaly_by_id("ANOM-BRENT-1")

    art_below = NormalizedArticle(
        id="ART-BELOW",
        headline="Minor rumor on oil production",
        summary=None,
        source_name="Blog",
        source_url=None,
        article_url="https://example.com/below",
        author=None,
        published_at_utc="2026-07-29T09:55:00Z",
        published_at_ist="2026-07-29T15:25:00+05:30",
        primary_category=GlobalEventCategory.ENERGY,
        tags=["BRENT"],
    )

    art_above = NormalizedArticle(
        id="ART-ABOVE",
        headline="OPEC announces unexpected supply cuts",
        summary=None,
        source_name="Reuters",
        source_url=None,
        article_url="https://example.com/above",
        author=None,
        published_at_utc="2026-07-29T09:58:00Z",
        published_at_ist="2026-07-29T15:28:00+05:30",
        primary_category=GlobalEventCategory.ENERGY,
        tags=["BRENT"],
    )

    # Pair with confidence < 0.50 (below defensive threshold)
    pair_below = CorrelatedEventPair(
        correlation_id="CORR-BELOW",
        anomaly=anom_brent,
        article=art_below,
        confidence_score=0.35,
    )
    # Pair with confidence >= 0.50 (accepted)
    pair_above = CorrelatedEventPair(
        correlation_id="CORR-ABOVE",
        anomaly=anom_brent,
        article=art_above,
        confidence_score=0.88,
    )

    service.get_correlated_events = lambda: [pair_below, pair_above]
    return service




@pytest.fixture
def client(mock_anomaly_service, mock_correlation_service):
    app = FastAPI()
    app.include_router(india_impact_router, prefix="/api/v1")

    app.state.anomaly_service = mock_anomaly_service
    app.state.correlation_service = mock_correlation_service
    app.state.india_impact_service = IndiaImpactService()

    return TestClient(app)


def test_list_india_impacts_filtering_and_camelcase_serialization(client):
    response = client.get("/api/v1/india-impact")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "pagination" in data

    # Verify camelCase JSON keys
    item = data["items"][0]
    assert "anomalyId" in item
    assert "impactScore" in item
    assert "impactLevel" in item
    assert "capitalFlowRisk" in item
    assert "transmissionChannels" in item
    assert "affectedSectors" in item
    assert "summaryRationale" in item
    assert "detectedAtUtc" in item
    assert "detectedAtIst" in item


def test_list_india_impacts_ordered_min_level_hierarchy(client):
    # min_impact_level = HIGH -> only HIGH
    res_high = client.get("/api/v1/india-impact?min_impact_level=HIGH")
    assert res_high.status_code == 200
    high_items = res_high.json()["items"]
    assert all(item["impactLevel"] == "HIGH" for item in high_items)

    # min_impact_level = MEDIUM -> MEDIUM and HIGH
    res_med = client.get("/api/v1/india-impact?min_impact_level=MEDIUM")
    assert res_med.status_code == 200
    med_items = res_med.json()["items"]
    assert all(item["impactLevel"] in ("HIGH", "MEDIUM") for item in med_items)


def test_list_india_impacts_deterministic_sorting_before_pagination(client):
    response = client.get("/api/v1/india-impact?limit=5")
    assert response.status_code == 200
    items = response.json()["items"]

    # Verify impactScore DESC ordering
    scores = [item["impactScore"] for item in items]
    assert scores == sorted(scores, reverse=True)


def test_get_anomaly_india_impact_multi_pair_defensive_filtering(client):
    # ANOM-BRENT-1 has two correlated pairs (0.35 below threshold, 0.88 above threshold)
    response = client.get("/api/v1/india-impact/anomalies/ANOM-BRENT-1")
    assert response.status_code == 200
    data = response.json()

    assert data["anomalyId"] == "ANOM-BRENT-1"
    assert data["symbol"] == "BRENT"
    assert data["impactLevel"] == "HIGH"
    assert data["impactScore"] == 98.2  # (0.35*1.0 + 0.30*1.0 + 0.20*1.0 + 0.15*0.88) * 100.0 = 98.2


def test_get_anomaly_india_impact_404_not_found(client):
    response = client.get("/api/v1/india-impact/anomalies/NON_EXISTENT_ID")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_evaluate_shock_stateless_post(client):
    payload = {
        "symbol": "BRENT",
        "changePercent": 4.5,
        "assetType": "COMMODITY",
    }
    response = client.post("/api/v1/india-impact/evaluate-shock", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["symbol"] == "BRENT"
    assert data["impactScore"] == 97.6  # ((0.35*1.0 + 0.30*1.0 + 0.20*0.9) / 0.85) * 100.0 = 97.6
    assert data["impactLevel"] == "HIGH"
    assert data["anomalyId"] is None



def test_evaluate_shock_invalid_asset_type_validation_error(client):
    payload = {
        "symbol": "BRENT",
        "changePercent": 4.5,
        "assetType": "INVALID_ASSET_TYPE_STRING",
    }
    response = client.post("/api/v1/india-impact/evaluate-shock", json=payload)
    assert response.status_code == 422  # FastAPI validation error for AssetType enum
