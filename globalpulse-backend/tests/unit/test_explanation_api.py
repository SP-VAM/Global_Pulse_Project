"""
Unit tests for Phase 5D Explanation REST APIs & Dashboard Integration.
Verifies:
1. GET /api/v1/anomalies/{anomaly_id}/explanation (200 OK with camelCase contracts + 404 Not Found).
2. GET /api/v1/india-impact/anomalies/{anomaly_id}/summary (200 OK + 404 Not Found).
3. GET /api/v1/historical/trends/narrative (200 OK + 400 Bad Request on invalid date range).
4. Lookup order: Active Anomalies -> Historical Store -> 404.
5. Required dependency semantics (missing ExplanationService -> 500 error).
6. Dashboard executive Narrative integration and narrow failure isolation.
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.explanation import router as explanation_router
from app.core.exceptions import ExplanationProviderError
from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.explanation import EvidenceConfidenceLevel, ExplanationProviderType, ShockExplanation
from app.domain.india_impact import CapitalFlowRisk, ImpactDirection, IndiaImpactAssessment, IndiaImpactLevel, TransmissionChannel
from app.main import create_app
from app.services.anomaly_service import AnomalyDetectionService
from app.services.dashboard_service import DashboardService
from app.services.deterministic_template_provider import DeterministicTemplateProvider
from app.services.explanation_cache import InMemoryExplanationCache
from app.services.explanation_context_assembler import ExplanationContextAssembler
from app.services.explanation_service import ExplanationService
from app.services.historical_analytics_service import HistoricalAnalyticsService
from app.services.historical_store import InMemoryHistoricalSnapshotStore, create_anomaly_snapshot_from_domain


@pytest.fixture
def populated_env():
    anomaly_service = AnomalyDetectionService()
    historical_store = InMemoryHistoricalSnapshotStore()

    # Active anomaly
    anom_active = NormalizedAnomaly(
        id="ANOM-BRENT-ACTIVE",
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
    anomaly_service._memory_store.append(anom_active)


    # Historical anomaly
    anom_hist = NormalizedAnomaly(
        id="ANOM-USDINR-HIST",
        symbol="USD/INR",
        asset_type="FOREX",
        metric=AnomalyMetric.PRICE_SPIKE,
        current_value=84.0,
        previous_value=83.0,
        change_percent=1.2,
        observation_window="1h",
        severity=AnomalySeverity.MEDIUM,
        detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
        detected_at_utc="2026-07-29T10:00:00Z",
        detected_at_ist="2026-07-29T15:30:00+05:30",
    )
    historical_store.add_anomaly_snapshot(create_anomaly_snapshot_from_domain(anom_hist))

    assembler = ExplanationContextAssembler()
    cache = InMemoryExplanationCache()
    template_provider = DeterministicTemplateProvider()
    explanation_service = ExplanationService(assembler, cache, template_provider)
    analytics_service = HistoricalAnalyticsService(historical_store)

    return {
        "anomaly_service": anomaly_service,
        "historical_store": historical_store,
        "explanation_service": explanation_service,
        "analytics_service": analytics_service,
    }


@pytest.fixture
def client(populated_env):
    app = FastAPI()
    app.include_router(explanation_router, prefix="/api/v1")
    app.state.anomaly_service = populated_env["anomaly_service"]
    app.state.historical_store = populated_env["historical_store"]
    app.state.explanation_service = populated_env["explanation_service"]
    app.state.historical_analytics_service = populated_env["analytics_service"]
    return TestClient(app)


def test_get_anomaly_explanation_active_lookup(client):
    res = client.get("/api/v1/anomalies/ANOM-BRENT-ACTIVE/explanation")
    assert res.status_code == 200
    data = res.json()

    assert data["explanationId"].startswith("EXP-BRENT")
    assert data["anomalyId"] == "ANOM-BRENT-ACTIVE"
    assert data["providerType"] == "DETERMINISTIC"
    assert data["evidenceConfidenceRating"] == "MODERATE"
    assert "BRENT" in data["headlineSummary"]


def test_get_anomaly_explanation_historical_fallback_lookup(client):
    res = client.get("/api/v1/anomalies/ANOM-USDINR-HIST/explanation")
    assert res.status_code == 200
    data = res.json()

    assert data["anomalyId"] == "ANOM-USDINR-HIST"
    assert "USD/INR" in data["headlineSummary"]


def test_get_anomaly_explanation_not_found_returns_404(client):
    res = client.get("/api/v1/anomalies/NON_EXISTENT_ANOMALY_ID/explanation")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"]


def test_get_india_impact_summary_api(client):
    res = client.get("/api/v1/india-impact/anomalies/ANOM-BRENT-ACTIVE/summary")
    assert res.status_code == 200
    data = res.json()

    assert data["summaryId"].startswith("SUMM-SHOCK")
    assert "Shock Brief: BRENT" in data["title"]
    assert len(data["bulletPoints"]) >= 1


def test_get_historical_trends_narrative_api(client):
    res = client.get("/api/v1/historical/trends/narrative")
    assert res.status_code == 200
    data = res.json()

    assert "Historical Trend Executive Summary" in data["title"]
    assert len(data["bulletPoints"]) >= 1

    # Date range validation -> 400 Bad Request
    res_bad = client.get("/api/v1/historical/trends/narrative?from_date=2026-08-01&to_date=2026-07-01")
    assert res_bad.status_code == 400
    assert res_bad.json()["detail"] == "from_date cannot be after to_date"


def test_missing_explanation_service_raises_500():
    app = FastAPI()
    app.include_router(explanation_router, prefix="/api/v1")
    # Do NOT set explanation_service on app.state
    test_client = TestClient(app)

    res = test_client.get("/api/v1/anomalies/ANOM-1/explanation")
    assert res.status_code == 500
    assert "ExplanationService is not configured" in res.json()["detail"]


@pytest.mark.asyncio
async def test_dashboard_executive_narrative_failure_isolation():
    from httpx import ASGITransport, AsyncClient

    app = create_app()
    mock_news = AsyncMock()
    mock_news.search_news.return_value = []
    app.state.news_service = mock_news

    class FailingExplanationService:
        def get_executive_summary(self, *args, **kwargs):
            raise ExplanationProviderError("Controlled provider error for failure isolation testing")

    app.state.dashboard_service = DashboardService(
        news_service=mock_news,
        explanation_service=FailingExplanationService(),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as async_client:
        res = await async_client.get("/api/v1/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert "feed" in data
        # Narrow Failure Isolation preserved: returns HTTP 200 with executiveNarrative = null
        assert data.get("executiveNarrative") is None
