"""
API unit tests for GET /api/v1/dashboard and GET /api/v1/dashboard/search endpoints.
Uses AsyncClient and FastAPI dependency injection.
"""
from unittest.mock import AsyncMock, patch
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import ProviderUnavailableError
from app.domain.news import CompanyTag, GlobalEventCategory, NormalizedArticle
from app.main import create_app
from app.services.dashboard_service import DashboardService
from app.services.news_service import NewsService


def _sample_article(
    id="art-100",
    headline="Global oil supplies tighten as Singapore port congestion grows",
    summary="Energy markets react to logistics bottlenecks.",
    published_utc="2026-07-28T12:00:00Z",
    published_ist="2026-07-28T17:30:00+05:30",
) -> NormalizedArticle:
    return NormalizedArticle(
        id=id,
        headline=headline,
        summary=summary,
        source_name="Financial Times",
        source_url="https://ft.com",
        article_url=f"https://ft.com/article-{id}",
        author="Energy Desk",
        published_at_utc=published_utc,
        published_at_ist=published_ist,
        primary_category=GlobalEventCategory.ENERGY,
        tags=["ENERGY"],
        countries=["SG"],
        companies=[CompanyTag(name="Shell", sector="Energy", country="GB")],
        sectors=["Energy"],
        keywords=["oil", "shipping"],
        relevance_score=5,
        source="NEWSAPI",
    )



@pytest.fixture
def mock_news_service():
    service = AsyncMock(spec=NewsService)
    return service


@pytest_asyncio.fixture
async def dashboard_client(mock_news_service) -> AsyncClient:
    """AsyncClient fixture with mocked DashboardService attached to app state."""
    app = create_app()
    dashboard_service = DashboardService(news_service=mock_news_service)
    app.state.dashboard_service = dashboard_service
    app.state.news_service = mock_news_service

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac



@pytest.mark.asyncio
async def test_get_dashboard_endpoint_returns_200(dashboard_client, mock_news_service):
    art = _sample_article()
    mock_news_service.search_news.return_value = [art]

    response = await dashboard_client.get("/api/v1/dashboard")
    assert response.status_code == 200

    body = response.json()
    assert "generatedAtUtc" in body
    assert "generatedAtIst" in body
    assert "feed" in body
    assert "pagination" in body

    feed = body["feed"]
    assert len(feed) == 1
    item = feed[0]
    assert item["id"] == "art-100"
    assert item["type"] == "GLOBAL_EVENT"
    assert item["headline"] == art.headline
    assert item["impactLevel"] == "UNKNOWN"
    assert item["publishedAtUtc"] == art.published_at_utc
    assert item["publishedAtIst"] == art.published_at_ist
    assert item["financiallyRelevant"] is True


@pytest.mark.asyncio
async def test_get_dashboard_query_filters(dashboard_client, mock_news_service):
    art = _sample_article()
    mock_news_service.search_news.return_value = [art]

    response = await dashboard_client.get(
        "/api/v1/dashboard?category=ENERGY&country=Singapore&company=Shell&sector=Energy&type=GLOBAL_EVENT&sort=oldest&page=1&pageSize=10"
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["feed"]) == 1


@pytest.mark.asyncio
async def test_search_dashboard_endpoint_returns_200(dashboard_client, mock_news_service):
    art = _sample_article()
    mock_news_service.search_news.return_value = [art]

    response = await dashboard_client.get("/api/v1/dashboard/search?q=oil")
    assert response.status_code == 200

    body = response.json()
    assert len(body["feed"]) == 1
    assert body["feed"][0]["id"] == "art-100"


@pytest.mark.asyncio
async def test_search_dashboard_empty_result(dashboard_client, mock_news_service):
    art = _sample_article()
    mock_news_service.search_news.return_value = [art]

    response = await dashboard_client.get("/api/v1/dashboard/search?q=nonexistentterm")
    assert response.status_code == 200

    body = response.json()
    assert len(body["feed"]) == 0
    assert body["pagination"]["total"] == 0


@pytest.mark.asyncio
async def test_dashboard_invalid_pagination_returns_422(dashboard_client):
    response = await dashboard_client.get("/api/v1/dashboard?page=0")
    assert response.status_code in (400, 422)

    response_size = await dashboard_client.get("/api/v1/dashboard?pageSize=500")
    assert response_size.status_code in (400, 422)


@pytest.mark.asyncio
async def test_dashboard_invalid_date_range_returns_422(dashboard_client):
    response = await dashboard_client.get("/api/v1/dashboard?from=2026-07-28&to=2026-07-10")
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_dashboard_provider_failure_returns_503(dashboard_client, mock_news_service):
    mock_news_service.search_news.side_effect = ProviderUnavailableError("News provider unreachable")

    response = await dashboard_client.get("/api/v1/dashboard")
    assert response.status_code == 503

    body = response.json()
    assert body["error"]["code"] == "PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_dashboard_india_impact_failure_isolation(mock_news_service):
    mock_news_service.search_news.return_value = [_sample_article()]

    class FailingIndiaImpactService:
        def evaluate_anomaly(self, *args, **kwargs):
            raise RuntimeError("Database or model calculation unexpected error")

    from unittest.mock import MagicMock
    mock_anom_service = MagicMock()
    mock_anom_service.get_in_memory_anomalies.return_value = (
        [MagicMock(id="A1", symbol="BRENT", detected_at_utc="2026-07-29T10:00:00Z")],
        1,
    )

    app = create_app()
    dashboard_service = DashboardService(
        news_service=mock_news_service,
        anomaly_service=mock_anom_service,
        india_impact_service=FailingIndiaImpactService(),
    )
    app.state.dashboard_service = dashboard_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/dashboard")
        assert response.status_code == 200
        body = response.json()
        assert "feed" in body
        # India Impact failure isolation: request succeeds and returns indiaImpactSummary as None/null
        assert body.get("indiaImpactSummary") is None


