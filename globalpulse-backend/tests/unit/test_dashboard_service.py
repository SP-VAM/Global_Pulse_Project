"""
Unit tests for DashboardService.
All dependencies (NewsService, MarketService) are mocked.
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.core.exceptions import ProviderUnavailableError, ValidationError
from app.domain.news import CompanyTag, GlobalEventCategory, NormalizedArticle
from app.domain.instrument import NormalizedQuote
from app.schemas.dashboard import DashboardItemType, ImpactLevel
from app.services.dashboard_service import DashboardService


def _sample_article(
    id="art-1",
    headline=None,
    summary="Crude oil futures rose by 3% following supply chain bottlenecks.",
    source_name="Reuters",
    article_url=None,
    published_utc="2026-07-28T10:00:00Z",
    published_ist="2026-07-28T15:30:00+05:30",
    category=GlobalEventCategory.ENERGY,
    countries=None,
    companies=None,
    sectors=None,
    relevance_score=4,
) -> NormalizedArticle:
    effective_headline = headline or f"Oil prices surge amid Singapore shipping delays {id}"
    effective_url = article_url or f"https://example.com/article-{id}"
    return NormalizedArticle(
        id=id,
        headline=effective_headline,
        summary=summary,
        source_name=source_name,
        source_url="https://example.com",
        article_url=effective_url,
        author="Reporter",
        published_at_utc=published_utc,
        published_at_ist=published_ist,
        primary_category=category,
        tags=["ENERGY", "SUPPLY_CHAIN"],
        countries=countries or ["SG"],
        companies=companies or [CompanyTag(name="Shell", sector="Energy", country="GB")],
        sectors=sectors or ["Energy"],
        keywords=["oil", "crude", "supply chain"],
        relevance_score=relevance_score,
        source="NEWSAPI",
    )



@pytest.fixture
def mock_news_service():
    service = AsyncMock()
    return service


@pytest.fixture
def mock_market_service():
    service = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_get_dashboard_returns_feed_schema(mock_news_service):
    art = _sample_article()
    mock_news_service.search_news.return_value = [art]

    service = DashboardService(news_service=mock_news_service)
    res = await service.get_dashboard(page=1, page_size=20)

    assert res.generated_at_utc is not None
    assert res.generated_at_ist is not None
    assert len(res.feed) == 1
    item = res.feed[0]
    assert item.id == "art-1"
    assert item.headline == art.headline
    assert item.category == "ENERGY"
    assert item.impact_level == ImpactLevel.UNKNOWN
    assert item.type == DashboardItemType.GLOBAL_EVENT  # relevance_score 4 >= threshold 2
    assert item.financially_relevant is True
    assert item.countries == ["SG"]
    assert len(item.companies) == 1
    assert item.companies[0].name == "Shell"
    assert res.pagination.page == 1
    assert res.pagination.page_size == 20
    assert res.pagination.total == 1
    assert res.pagination.has_next is False


@pytest.mark.asyncio
async def test_sorting_latest_and_oldest(mock_news_service):
    art_old = _sample_article(id="1", headline="First event", published_utc="2026-07-28T08:00:00Z")
    art_new = _sample_article(id="2", headline="Second event", published_utc="2026-07-28T12:00:00Z")
    mock_news_service.search_news.return_value = [art_old, art_new]

    service = DashboardService(news_service=mock_news_service)

    res_latest = await service.get_dashboard(sort="latest")
    assert res_latest.feed[0].id == "2"
    assert res_latest.feed[1].id == "1"

    res_oldest = await service.get_dashboard(sort="oldest")
    assert res_oldest.feed[0].id == "1"
    assert res_oldest.feed[1].id == "2"


@pytest.mark.asyncio
async def test_filters_category_country_company_sector_type(mock_news_service):
    art1 = _sample_article(
        id="1",
        category=GlobalEventCategory.ENERGY,
        countries=["SG"],
        companies=[CompanyTag("Apple", "Technology", "US")],
        sectors=["Technology"],
        relevance_score=5,
    )
    art2 = _sample_article(
        id="2",
        category=GlobalEventCategory.GEOPOLITICS,
        countries=["US"],
        companies=[CompanyTag("ExxonMobil", "Energy", "US")],
        sectors=["Energy"],
        relevance_score=0,
    )
    mock_news_service.search_news.return_value = [art1, art2]

    service = DashboardService(news_service=mock_news_service)

    # Category filter
    res_cat = await service.get_dashboard(category="ENERGY")
    assert len(res_cat.feed) == 1
    assert res_cat.feed[0].id == "1"

    # Country filter
    res_country = await service.get_dashboard(country="SG")
    assert len(res_country.feed) == 1
    assert res_country.feed[0].id == "1"

    # Company filter
    res_comp = await service.get_dashboard(company="Apple")
    assert len(res_comp.feed) == 1
    assert res_comp.feed[0].id == "1"

    # Sector filter
    res_sec = await service.get_dashboard(sector="Energy")
    assert len(res_sec.feed) == 1
    assert res_sec.feed[0].id == "2"

    # Type filter (GLOBAL_EVENT vs NEWS)
    res_type = await service.get_dashboard(item_type="NEWS")
    assert len(res_type.feed) == 1
    assert res_type.feed[0].id == "2"
    assert res_type.feed[0].type == DashboardItemType.NEWS


@pytest.mark.asyncio
async def test_date_range_filter(mock_news_service):
    art_july1 = _sample_article(id="1", published_utc="2026-07-01T10:00:00Z")
    art_july15 = _sample_article(id="2", published_utc="2026-07-15T10:00:00Z")
    art_july28 = _sample_article(id="3", published_utc="2026-07-28T10:00:00Z")
    mock_news_service.search_news.return_value = [art_july1, art_july15, art_july28]

    service = DashboardService(news_service=mock_news_service)

    res = await service.get_dashboard(from_date=date(2026, 7, 10), to_date=date(2026, 7, 20))
    assert len(res.feed) == 1
    assert res.feed[0].id == "2"


@pytest.mark.asyncio
async def test_pagination(mock_news_service):
    articles = [
        _sample_article(id=str(i), headline=f"Headline {i}", article_url=f"https://example.com/{i}")
        for i in range(1, 25)
    ]
    mock_news_service.search_news.return_value = articles

    service = DashboardService(news_service=mock_news_service)

    # Page 1 (20 items)
    res_p1 = await service.get_dashboard(page=1, page_size=20)
    assert len(res_p1.feed) == 20
    assert res_p1.pagination.page == 1
    assert res_p1.pagination.total == 24
    assert res_p1.pagination.has_next is True

    # Page 2 (4 items remaining)
    res_p2 = await service.get_dashboard(page=2, page_size=20)
    assert len(res_p2.feed) == 4
    assert res_p2.pagination.page == 2
    assert res_p2.pagination.has_next is False


@pytest.mark.asyncio
async def test_search_success_and_empty_result(mock_news_service):
    art1 = _sample_article(id="1", headline="Semiconductor production shortage hits tech sector")
    art2 = _sample_article(id="2", headline="Unrelated political speech", summary="Nothing about chips")
    mock_news_service.search_news.return_value = [art1, art2]

    service = DashboardService(news_service=mock_news_service)

    # Match search
    res = await service.search_dashboard(query="semiconductor")
    assert len(res.feed) == 1
    assert res.feed[0].id == "1"

    # Empty result search
    res_empty = await service.search_dashboard(query="unmatchedxyzterm")
    assert len(res_empty.feed) == 0
    assert res_empty.pagination.total == 0


@pytest.mark.asyncio
async def test_deduplication_by_url_and_headline(mock_news_service):
    art1 = _sample_article(id="1", article_url="https://example.com/same", headline="Identical Headline")
    art2 = _sample_article(id="2", article_url="https://example.com/same", headline="Identical Headline")
    art3 = _sample_article(id="3", article_url="https://example.com/different", headline="IDENTICAL HEADLINE")
    mock_news_service.search_news.return_value = [art1, art2, art3]

    service = DashboardService(news_service=mock_news_service)

    res = await service.get_dashboard()
    assert len(res.feed) == 1
    assert res.feed[0].id == "1"


@pytest.mark.asyncio
async def test_market_context_enrichment_success_and_failure_isolation(mock_news_service, mock_market_service):
    art = _sample_article(
        id="1",
        companies=[
            CompanyTag(name="Apple", sector="Technology", country="US"),
            CompanyTag(name="Microsoft", sector="Technology", country="US"),
        ],
    )
    mock_news_service.search_news.return_value = [art]

    # Apple quote succeeds, Microsoft quote fails
    mock_market_service.get_quote.side_effect = lambda sym: {
        "AAPL": NormalizedQuote(
            symbol="AAPL",
            price=220.50,
            open=218.0,
            high=222.0,
            low=217.5,
            previous_close=219.0,
            change=1.5,
            change_percent=0.68,
            currency="USD",
            timestamp_utc="2026-07-28T10:00:00Z",
            timestamp_ist="2026-07-28T15:30:00+05:30",
            source="FINNHUB",
        ),
        "MSFT": Exception("Market quote service timeout"),
    }[sym]

    service = DashboardService(news_service=mock_news_service, market_service=mock_market_service)

    res = await service.get_dashboard()
    assert len(res.feed) == 1
    item = res.feed[0]
    # Feed must not fail even though MSFT quote failed!
    assert len(item.market_context) == 1
    assert item.market_context[0].symbol == "AAPL"
    assert item.market_context[0].price == 220.50


@pytest.mark.asyncio
async def test_validation_errors(mock_news_service):
    service = DashboardService(news_service=mock_news_service)

    with pytest.raises(ValidationError, match="Page number"):
        await service.get_dashboard(page=0)

    with pytest.raises(ValidationError, match="Page size"):
        await service.get_dashboard(page_size=150)

    with pytest.raises(ValidationError, match="from_date cannot be after to_date"):
        await service.get_dashboard(from_date=date(2026, 7, 28), to_date=date(2026, 7, 10))

    with pytest.raises(ValidationError, match="cannot be empty"):
        await service.search_dashboard(query="   ")


@pytest.mark.asyncio
async def test_upstream_provider_failure_propagation(mock_news_service):
    mock_news_service.search_news.side_effect = ProviderUnavailableError("News provider offline")
    service = DashboardService(news_service=mock_news_service)

    with pytest.raises(ProviderUnavailableError, match="News provider offline"):
        await service.get_dashboard()
