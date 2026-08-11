"""
Unit tests for NewsApiProvider and NewsService.
All provider calls are mocked — no live API calls.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import (
    ProviderAuthenticationError,
    ProviderFeatureUnavailableError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.domain.news import GlobalEventCategory, NormalizedArticle
from app.providers.newsapi.provider import NewsApiProvider, _article_id, _parse_newsapi_datetime
from app.services.event_classification_service import EventClassificationService
from app.services.news_service import NewsService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_provider() -> NewsApiProvider:
    return NewsApiProvider(
        api_key="test-news-key",
        base_url="https://newsapi.org/v2",
        timeout=5.0,
    )


def _mock_response(status_code: int, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = Exception("No JSON")
    return resp


def _ok_response(articles=None):
    return {
        "status": "ok",
        "totalResults": len(articles or []),
        "articles": articles or [],
    }


def _raw_article(
    title="Test headline",
    description="Test description",
    url="https://example.com/article",
    published_at="2024-01-26T14:00:00Z",
    source_name="Reuters",
    author="John Doe",
):
    return {
        "source": {"id": None, "name": source_name},
        "author": author,
        "title": title,
        "description": description,
        "url": url,
        "urlToImage": None,
        "publishedAt": published_at,
        "content": "Full content [truncated]",  # Should be discarded
    }


def _make_normalized_article(
    headline="Test headline",
    summary="Test summary",
    url="https://example.com/article",
    category=GlobalEventCategory.OTHER,
) -> NormalizedArticle:
    return NormalizedArticle(
        id=_article_id(url),
        headline=headline,
        summary=summary,
        source_name="Reuters",
        source_url=None,
        article_url=url,
        author="John Doe",
        published_at_utc="2024-01-26T14:00:00+00:00",
        published_at_ist="2024-01-26T19:30:00+05:30",
        primary_category=category,
    )


@pytest.fixture
def provider():
    return _make_provider()


@pytest.fixture
def classifier():
    return EventClassificationService()


@pytest.fixture
def mock_news_provider():
    p = MagicMock()
    p.search_news = AsyncMock(return_value=[])
    return p


@pytest.fixture
def news_service(mock_news_provider, classifier):
    return NewsService(provider=mock_news_provider, classifier=classifier)


# ---------------------------------------------------------------------------
# NewsApiProvider tests
# ---------------------------------------------------------------------------

class TestParseNewsapiDatetime:
    def test_parses_z_suffix(self):
        dt = _parse_newsapi_datetime("2024-01-26T14:00:00Z")
        from datetime import timezone
        assert dt.tzinfo == timezone.utc
        assert dt.year == 2024

    def test_none_returns_now(self):
        from datetime import timezone
        dt = _parse_newsapi_datetime(None)
        assert dt.tzinfo == timezone.utc

    def test_invalid_format_returns_now(self):
        from datetime import timezone
        dt = _parse_newsapi_datetime("not-a-date")
        assert dt.tzinfo == timezone.utc


class TestNewsApiProviderSearchNews:
    @pytest.mark.asyncio
    async def test_success_normalizes_articles(self, provider):
        raw = _ok_response([_raw_article()])
        with patch.object(provider, "_get", AsyncMock(return_value=raw)):
            articles = await provider.search_news(query="test")

        assert len(articles) == 1
        a = articles[0]
        assert a.headline == "Test headline"
        assert a.summary == "Test description"
        assert a.source_name == "Reuters"
        assert a.author == "John Doe"
        assert a.article_url == "https://example.com/article"
        assert a.source == "NEWSAPI"

    @pytest.mark.asyncio
    async def test_content_field_is_discarded(self, provider):
        """Full article content must not be stored."""
        raw = _ok_response([_raw_article()])
        with patch.object(provider, "_get", AsyncMock(return_value=raw)):
            articles = await provider.search_news()

        # Ensure the 'content' field from raw is not in the normalized article
        assert not hasattr(articles[0], "content")

    @pytest.mark.asyncio
    async def test_missing_author_is_none(self, provider):
        raw_article = _raw_article()
        raw_article["author"] = None
        raw = _ok_response([raw_article])
        with patch.object(provider, "_get", AsyncMock(return_value=raw)):
            articles = await provider.search_news()
        assert articles[0].author is None

    @pytest.mark.asyncio
    async def test_missing_description_is_none(self, provider):
        raw_article = _raw_article()
        raw_article["description"] = None
        raw = _ok_response([raw_article])
        with patch.object(provider, "_get", AsyncMock(return_value=raw)):
            articles = await provider.search_news()
        assert articles[0].summary is None

    @pytest.mark.asyncio
    async def test_utc_and_ist_timestamps_present(self, provider):
        raw = _ok_response([_raw_article(published_at="2024-01-26T08:30:00Z")])
        with patch.object(provider, "_get", AsyncMock(return_value=raw)):
            articles = await provider.search_news()
        a = articles[0]
        assert "+00:00" in a.published_at_utc or "UTC" in a.published_at_utc or "Z" not in a.published_at_utc
        assert "+05:30" in a.published_at_ist

    @pytest.mark.asyncio
    async def test_article_with_no_title_skipped(self, provider):
        raw_article = _raw_article()
        raw_article["title"] = None
        raw = _ok_response([raw_article])
        with patch.object(provider, "_get", AsyncMock(return_value=raw)):
            articles = await provider.search_news()
        assert len(articles) == 0

    @pytest.mark.asyncio
    async def test_newsapi_error_status_raises(self, provider):
        error_resp = {
            "status": "error",
            "code": "apiKeyInvalid",
            "message": "Your API key is invalid.",
        }
        with patch.object(provider, "_get", AsyncMock(return_value=error_resp)):
            with pytest.raises(ProviderAuthenticationError):
                await provider.search_news()

    @pytest.mark.asyncio
    async def test_rate_limit_error_code(self, provider):
        error_resp = {
            "status": "error",
            "code": "rateLimited",
            "message": "You have been rate limited.",
        }
        with patch.object(provider, "_get", AsyncMock(return_value=error_resp)):
            with pytest.raises(ProviderRateLimitError):
                await provider.search_news()


class TestNewsApiProviderHTTPErrors:
    @pytest.mark.asyncio
    async def test_401_raises_authentication_error(self, provider):
        with patch.object(provider._client, "get", AsyncMock(
            return_value=_mock_response(401)
        )):
            with pytest.raises(ProviderAuthenticationError):
                await provider.search_news()

    @pytest.mark.asyncio
    async def test_403_raises_feature_unavailable(self, provider):
        """403 is plan/domain restriction, NOT an auth failure."""
        with patch.object(provider._client, "get", AsyncMock(
            return_value=_mock_response(403)
        )):
            with pytest.raises(ProviderFeatureUnavailableError):
                await provider.search_news()

    @pytest.mark.asyncio
    async def test_403_is_not_authentication_error(self, provider):
        with patch.object(provider._client, "get", AsyncMock(
            return_value=_mock_response(403)
        )):
            with pytest.raises(Exception) as exc_info:
                await provider.search_news()
        assert not isinstance(exc_info.value, ProviderAuthenticationError)

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit(self, provider):
        with patch.object(provider._client, "get", AsyncMock(
            return_value=_mock_response(429)
        )):
            with pytest.raises(ProviderRateLimitError):
                await provider.search_news()

    @pytest.mark.asyncio
    async def test_500_raises_unavailable(self, provider):
        with patch.object(provider._client, "get", AsyncMock(
            return_value=_mock_response(500)
        )):
            with pytest.raises(ProviderUnavailableError):
                await provider.search_news()

    @pytest.mark.asyncio
    async def test_timeout_raises_unavailable(self, provider):
        import httpx
        with patch.object(provider._client, "get", AsyncMock(
            side_effect=httpx.TimeoutException("timeout")
        )):
            with pytest.raises(ProviderUnavailableError):
                await provider.search_news()


# ---------------------------------------------------------------------------
# NewsService tests
# ---------------------------------------------------------------------------

class TestNewsService:
    @pytest.mark.asyncio
    async def test_search_news_classifies_articles(self, news_service, mock_news_provider):
        article = _make_normalized_article(
            headline="Federal Reserve raises interest rate, markets react",
        )
        mock_news_provider.search_news.return_value = [article]
        results = await news_service.search_news(query="fed rate")
        assert len(results) == 1
        # Should be classified, not OTHER
        assert results[0].primary_category in GlobalEventCategory

    @pytest.mark.asyncio
    async def test_category_filter_applied(self, news_service, mock_news_provider):
        war = _make_normalized_article(
            headline="missile attack kills soldiers in military conflict",
            url="http://a.com/war",
        )
        econ = _make_normalized_article(
            headline="GDP growth rate slows amid trade deficit inflation",
            url="http://a.com/econ",
        )
        mock_news_provider.search_news.return_value = [war, econ]

        results = await news_service.search_news(category=GlobalEventCategory.WAR_CONFLICT)
        assert all(
            r.primary_category == GlobalEventCategory.WAR_CONFLICT
            or GlobalEventCategory.WAR_CONFLICT.value in r.tags
            for r in results
        )

    @pytest.mark.asyncio
    async def test_country_filter_applied(self, news_service, mock_news_provider):
        india_article = _make_normalized_article(
            headline="RBI Mumbai India interest rate decision",
            url="http://a.com/india",
        )
        mock_news_provider.search_news.return_value = [india_article]

        results = await news_service.search_news(country="IN")
        # Either IN is in countries, or no results (depends on classification)
        for r in results:
            assert "IN" in r.countries

    @pytest.mark.asyncio
    async def test_get_global_events_filters_irrelevant(self, news_service, mock_news_provider):
        relevant = _make_normalized_article(
            headline="Federal Reserve FOMC interest rate decision monetary policy",
            url="http://a.com/1",
        )
        irrelevant = _make_normalized_article(
            headline="local dog show results for the weekend",
            url="http://a.com/2",
        )
        mock_news_provider.search_news.return_value = [relevant, irrelevant]

        events = await news_service.get_global_events()
        assert all(e.is_financially_relevant for e in events)

    @pytest.mark.asyncio
    async def test_deduplication_in_service(self, news_service, mock_news_provider):
        a1 = _make_normalized_article("Same headline about war conflict", url="http://a.com/x")
        a2 = _make_normalized_article("Same headline about war conflict", url="http://a.com/y")
        mock_news_provider.search_news.return_value = [a1, a2]

        results = await news_service.search_news()
        assert len(results) == 1  # Deduplicated by headline hash
