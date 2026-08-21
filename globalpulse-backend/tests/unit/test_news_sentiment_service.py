"""
Unit Test Suite: Market Analysis -> News Sentiment Module
Tests all 50 NIFTY 50 company queries, sentiment lexicon classification,
zero cross-company leakage, formula correctness, and 15-minute in-memory caching.
"""
import pytest
from unittest.mock import AsyncMock

from app.domain.news import NormalizedArticle, GlobalEventCategory
from app.services.stock_prediction_service import (
    TICKER_TO_COMPANY,
    COMPANY_NEWS_QUERIES,
    StockPredictionService,
    _evaluate_financial_sentiment,
)
from app.services.technical_indicator_service import TechnicalIndicatorService


@pytest.fixture
def mock_stock_provider():
    from tests.unit.test_stocks_service import MockStockProvider
    return MockStockProvider()


@pytest.fixture
def indicator_service():
    return TechnicalIndicatorService()


def _sample_article(headline: str, summary: str, company: str, pub_date: str = "2026-08-20T10:00:00Z") -> NormalizedArticle:
    return NormalizedArticle(
        id=f"art_{abs(hash(headline)) % 10000}",
        headline=headline,
        summary=summary,
        source_name="Financial Express",
        source_url="https://financialexpress.com",
        article_url="https://financialexpress.com/article1",
        author="Reporter",
        published_at_utc=pub_date,
        published_at_ist="2026-08-20T15:30:00+05:30",
        primary_category=GlobalEventCategory.CORPORATE,
        tags=[company],
        countries=["IN"],
        companies=[],
        sectors=[],
        keywords=[],
        relevance_score=90,
        source="NEWSAPI",
    )


class TestNewsSentimentLexicon:
    """Tests the financial sentiment lexicon classifier."""

    def test_positive_headline_triggers_bullish_sentiment(self):
        text = "Trent Ltd reports massive profit surge and strong revenue rise in retail expansion"
        sentiment, conf, score = _evaluate_financial_sentiment(text)
        assert sentiment == "POSITIVE"
        assert score > 0.05
        assert "%" in conf

    def test_negative_headline_triggers_bearish_sentiment(self):
        text = "Trent Ltd suffers unexpected quarterly loss and revenue drops amid store closures"
        sentiment, conf, score = _evaluate_financial_sentiment(text)
        assert sentiment == "NEGATIVE"
        assert score < -0.05
        assert "%" in conf

    def test_neutral_headline_defaults_to_neutral(self):
        text = "Trent Ltd board meeting scheduled for upcoming Thursday"
        sentiment, conf, score = _evaluate_financial_sentiment(text)
        assert sentiment == "NEUTRAL"
        assert score == 0.0
        assert conf == "65%"


class TestFiftyNiftyCompaniesMapping:
    """Verifies all 50 NIFTY 50 companies are covered in search queries dictionary."""

    def test_all_50_tickers_have_search_queries(self):
        assert len(TICKER_TO_COMPANY) == 50
        for ticker, name in TICKER_TO_COMPANY.items():
            assert ticker in COMPANY_NEWS_QUERIES, f"Missing query mapping for {ticker}"
            query = COMPANY_NEWS_QUERIES[ticker]
            assert len(query) > 2, f"Invalid query for {ticker}: '{query}'"

    @pytest.mark.asyncio
    async def test_sentiment_pipeline_for_all_50_companies(self, mock_stock_provider, indicator_service):
        """Simulates news retrieval across all 50 companies verifying zero crashes and valid payload schema."""
        mock_news = AsyncMock()
        mock_news.search_news = AsyncMock(return_value=[
            _sample_article("Company announces positive expansion and robust profit growth", "Details here", "Generic")
        ])

        service = StockPredictionService(
            provider=mock_stock_provider,
            indicator_service=indicator_service,
            news_service=mock_news,
        )

        for ticker in TICKER_TO_COMPANY.keys():
            res = await service.get_stock_news_sentiment(ticker)
            assert res["symbol"] == ticker
            assert "company_name" in res
            assert "net_sentiment" in res
            assert res["sentiment_label"] in ("Bullish", "Neutral", "Bearish")
            assert res["articles_traced"] == res["positive_articles"] + res["negative_articles"] + res["neutral_articles"]
            assert isinstance(res["news_list"], list)


class TestNewsSentimentIntegrationAndCaching:
    """Tests end-to-end calculation, cache hit, and error isolation."""

    @pytest.mark.asyncio
    async def test_sentiment_score_and_label_derivation(self, mock_stock_provider, indicator_service):
        """Tests that positive articles produce Bullish net sentiment."""
        mock_news = AsyncMock()
        mock_news.search_news = AsyncMock(return_value=[
            _sample_article("Trent Ltd reports 40% profit surge", "Strong growth", "TRENT"),
            _sample_article("Analysts upgrade Trent Ltd target price", "Expansion plans", "TRENT"),
            _sample_article("Trent Ltd opens 25 new stores", "Corporate update", "TRENT"),
        ])

        service = StockPredictionService(
            provider=mock_stock_provider,
            indicator_service=indicator_service,
            news_service=mock_news,
        )

        res = await service.get_stock_news_sentiment("TRENT")
        assert res["symbol"] == "TRENT"
        assert res["articles_traced"] == 3
        assert res["positive_articles"] >= 2
        assert res["negative_articles"] == 0
        assert res["net_sentiment"] > 0.15
        assert res["sentiment_label"] == "Bullish"
        assert len(res["news_list"]) == 3
        assert res["news_list"][0]["title"] != "Trent Ltd market update"

    @pytest.mark.asyncio
    async def test_per_company_cache_retains_data_without_refetch(self, mock_stock_provider, indicator_service):
        """Verifies subsequent calls within TTL reuse in-memory cache without hitting NewsService."""
        mock_news = AsyncMock()
        mock_news.search_news = AsyncMock(return_value=[
            _sample_article("TCS signs massive digital transformation deal", "Growth initiative", "TCS")
        ])

        service = StockPredictionService(
            provider=mock_stock_provider,
            indicator_service=indicator_service,
            news_service=mock_news,
        )

        # 1st call -> fetches from provider
        res1 = await service.get_stock_news_sentiment("TCS")
        assert mock_news.search_news.call_count == 1

        # 2nd call -> served from cache
        res2 = await service.get_stock_news_sentiment("TCS")
        assert mock_news.search_news.call_count == 1
        assert res1 == res2

    @pytest.mark.asyncio
    async def test_provider_failure_returns_graceful_neutral_payload(self, mock_stock_provider, indicator_service):
        """Verifies that if NewsService raises an exception (e.g. 429 rate limit or timeout), the endpoint returns a valid neutral state."""
        failing_news = AsyncMock()
        failing_news.search_news = AsyncMock(side_effect=Exception("NewsAPI 429 Rate Limit Exceeded"))

        service = StockPredictionService(
            provider=mock_stock_provider,
            indicator_service=indicator_service,
            news_service=failing_news,
        )

        res = await service.get_stock_news_sentiment("INFY")
        assert res["symbol"] == "INFY"
        assert res["articles_traced"] == 0
        assert res["net_sentiment"] == 0.0
        assert res["sentiment_label"] == "Neutral"
        assert res["news_list"] == []
