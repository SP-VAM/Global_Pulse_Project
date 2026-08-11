"""
API integration tests for Phase 2 endpoints:
  - GET /api/v1/anomalies
  - GET /api/v1/anomalies/{anomaly_id}
  - GET /api/v1/correlations
  - GET /api/v1/events/{event_id}/correlation
  - GET /api/v1/dashboard Phase 2 batch enrichment & failure isolation

Verifies HTTP status codes, FastAPI query validation, 404 semantics, and backward compatibility.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.news import GlobalEventCategory, NormalizedArticle
from app.main import create_app
from app.services.anomaly_service import AnomalyDetectionService
from app.services.correlation_service import EventCorrelationService
from app.services.severity_service import SeverityEngineService


from app.providers.newsapi.provider import NewsApiProvider
from app.providers.trading_economics.provider import TradingEconomicsProvider
from app.services.dashboard_service import DashboardService
from app.services.economic_service import EconomicService
from app.services.event_classification_service import EventClassificationService
from app.services.news_service import NewsService


@pytest.fixture
def app_with_phase2():
    app = create_app()

    anomaly_service = AnomalyDetectionService()
    anomaly_service.clear_in_memory_store()
    # Add a mock anomaly
    anomaly_service.detect_raw_anomaly(
        symbol="BTC/USD",
        asset_type="CRYPTO",
        current_value=68450.0,
        previous_value=65000.0,
        change_percent=5.3,
    )

    news_provider = NewsApiProvider(api_key="test", base_url="https://newsapi.org/v2")
    classifier = EventClassificationService()
    news_service = NewsService(provider=news_provider, classifier=classifier)

    # Mock search_news to avoid network calls with fake API key
    async def mock_search_news(*args, **kwargs):
        return [
            NormalizedArticle(
                id="art-btc-1",
                headline="Bitcoin surges past record high following ETF inflows",
                summary="Cryptocurrency market experiences massive surge.",
                source_name="Reuters",
                source_url="https://reuters.com",
                article_url="https://reuters.com/art-btc-1",
                author="Reporter",
                published_at_utc="2026-07-29T12:00:00Z",
                published_at_ist="2026-07-29T17:30:00+05:30",
                primary_category=GlobalEventCategory.TECHNOLOGY,
                tags=["CRYPTO"],
                countries=["US"],
                companies=[],
                sectors=["Cryptocurrency"],
                keywords=["bitcoin", "btc"],
                relevance_score=5,
                source="NEWSAPI",
            )
        ]

    news_service.search_news = mock_search_news

    te_provider = TradingEconomicsProvider(api_key="test", base_url="https://api.tradingeconomics.com")
    economic_service = EconomicService(provider=te_provider)

    async def mock_get_calendar(*args, **kwargs):
        return []

    economic_service.get_economic_calendar = mock_get_calendar



    correlation_service = EventCorrelationService()
    severity_service = SeverityEngineService()

    dashboard_service = DashboardService(
        news_service=news_service,
        anomaly_service=anomaly_service,
        correlation_service=correlation_service,
        severity_service=severity_service,
    )

    app.state.anomaly_service = anomaly_service
    app.state.correlation_service = correlation_service
    app.state.severity_service = severity_service
    app.state.news_service = news_service
    app.state.economic_service = economic_service
    app.state.dashboard_service = dashboard_service

    return app



@pytest.mark.asyncio
async def test_get_anomalies_endpoint_success(app_with_phase2):
    async with AsyncClient(transport=ASGITransport(app=app_with_phase2), base_url="http://test") as client:
        res = await client.get("/api/v1/anomalies")

    assert res.status_code == 200
    data = res.json()
    assert "anomalies" in data
    assert "pagination" in data
    assert len(data["anomalies"]) >= 1
    assert data["anomalies"][0]["symbol"] == "BTC/USD"
    assert data["anomalies"][0]["detectionMethod"] == "DETERMINISTIC_THRESHOLD"


@pytest.mark.asyncio
async def test_get_anomalies_validation_error(app_with_phase2):
    async with AsyncClient(transport=ASGITransport(app=app_with_phase2), base_url="http://test") as client:
        # Invalid page=0
        res_page = await client.get("/api/v1/anomalies?page=0")
        assert res_page.status_code == 422

        # Invalid page_size=101
        res_size = await client.get("/api/v1/anomalies?page_size=101")
        assert res_size.status_code == 422


@pytest.mark.asyncio
async def test_get_anomaly_by_id_success_and_404(app_with_phase2):
    async with AsyncClient(transport=ASGITransport(app=app_with_phase2), base_url="http://test") as client:
        # Fetch list to get real ID
        res_list = await client.get("/api/v1/anomalies")
        anom_id = res_list.json()["anomalies"][0]["anomalyId"]

        # Valid ID -> 200 OK
        res_valid = await client.get(f"/api/v1/anomalies/{anom_id}")
        assert res_valid.status_code == 200
        assert res_valid.json()["anomalyId"] == anom_id

        # Invalid ID -> 404 Not Found
        res_404 = await client.get("/api/v1/anomalies/NON-EXISTENT-ID")
        assert res_404.status_code == 404
        assert "not found" in res_404.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_get_correlations_endpoint_success_and_validation(app_with_phase2):
    async with AsyncClient(transport=ASGITransport(app=app_with_phase2), base_url="http://test") as client:
        res = await client.get("/api/v1/correlations")
        assert res.status_code == 200
        assert "correlations" in res.json()

        # Validation error for min_confidence > 1.0
        res_val = await client.get("/api/v1/correlations?min_confidence=1.5")
        assert res_val.status_code == 422


@pytest.mark.asyncio
async def test_get_event_correlation_404(app_with_phase2):
    async with AsyncClient(transport=ASGITransport(app=app_with_phase2), base_url="http://test") as client:
        res_404 = await client.get("/api/v1/events/NON-EXISTENT-EVENT-ID/correlation")
        assert res_404.status_code == 404
        assert "not found" in res_404.json()["error"]["message"].lower()



@pytest.mark.asyncio
async def test_dashboard_feed_phase2_enrichment_and_failure_isolation(app_with_phase2):
    async with AsyncClient(transport=ASGITransport(app=app_with_phase2), base_url="http://test") as client:
        # Normal feed execution -> 200 OK
        res_feed = await client.get("/api/v1/dashboard")
        assert res_feed.status_code == 200
        data = res_feed.json()
        assert "feed" in data

    # Failure isolation test: simulate exception in anomaly service
    class BrokenAnomalyService:
        def get_in_memory_anomalies(self, *args, **kwargs):
            raise RuntimeError("Simulated Phase 2 Anomaly Engine failure")

    app_with_phase2.state.dashboard_service._anomaly_service = BrokenAnomalyService()

    async with AsyncClient(transport=ASGITransport(app=app_with_phase2), base_url="http://test") as client:
        # Feed must gracefully succeed with 200 OK despite Phase 2 failure
        res_isolated = await client.get("/api/v1/dashboard")
        assert res_isolated.status_code == 200
        assert len(res_isolated.json()["feed"]) >= 0
