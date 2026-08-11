"""
Category 4: External API Failure Testing — Backend Hardening Phase 2

Tests that every external provider correctly handles all failure modes:
  - Network timeout          → ProviderUnavailableError
  - Network error            → ProviderUnavailableError
  - HTTP 401                 → ProviderAuthenticationError
  - HTTP 403                 → ProviderFeatureUnavailableError
  - HTTP 429                 → ProviderRateLimitError
  - HTTP 500 / 503           → ProviderUnavailableError
  - Non-JSON response        → ProviderUnavailableError
  - Malformed JSON structure → ProviderUnavailableError
  - Empty / null data        → InstrumentNotFoundError or ProviderUnavailableError
  - App-level error codes    → correct domain exception (NewsAPI status=error with HTTP 200)
  - API keys never logged

Providers covered:
  - FinnhubMarketProvider      (Finnhub REST API)
  - NewsApiProvider            (NewsAPI REST API)
  - TradingEconomicsProvider   (Trading Economics REST API)
  - YFinanceMarketDataProvider (Yahoo Finance / yfinance library)
  - MarketService              (service-layer propagation)

Pattern: mock httpx.AsyncClient.get — no real HTTP calls made.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code: int, json_data=None, text: str = "") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if json_data is not None:
        resp.json = MagicMock(return_value=json_data)
    else:
        resp.json = MagicMock(side_effect=Exception("Not JSON"))
    resp.text = text
    return resp


def _make_finnhub(api_key: str = "test-key"):
    from app.providers.finnhub.provider import FinnhubMarketProvider
    return FinnhubMarketProvider(api_key=api_key, base_url="https://finnhub.io/api/v1", timeout=5.0)


def _make_newsapi(api_key: str = "test-key"):
    from app.providers.newsapi.provider import NewsApiProvider
    return NewsApiProvider(api_key=api_key, base_url="https://newsapi.org/v2", timeout=5.0)


def _make_te(api_key: str = "test-key"):
    from app.providers.trading_economics.provider import TradingEconomicsProvider
    return TradingEconomicsProvider(api_key=api_key, base_url="https://api.tradingeconomics.com", timeout=5.0)


# ===========================================================================
# FINNHUB PROVIDER
# ===========================================================================

class TestFinnhubProviderFailures:

    @pytest.mark.asyncio
    async def test_timeout_raises_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        p = _make_finnhub()
        p._client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        with pytest.raises(ProviderUnavailableError, match="timed out"):
            await p.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_network_error_raises_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        p = _make_finnhub()
        p._client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        with pytest.raises(ProviderUnavailableError, match="Could not reach Finnhub"):
            await p.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_http_401_raises_provider_auth_error(self):
        from app.core.exceptions import ProviderAuthenticationError
        p = _make_finnhub()
        p._client.get = AsyncMock(return_value=_mock_response(401))
        with pytest.raises(ProviderAuthenticationError, match="API key"):
            await p.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_http_403_raises_provider_auth_error(self):
        from app.core.exceptions import ProviderAuthenticationError
        p = _make_finnhub()
        p._client.get = AsyncMock(return_value=_mock_response(403))
        with pytest.raises(ProviderAuthenticationError):
            await p.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_http_429_raises_provider_rate_limit(self):
        from app.core.exceptions import ProviderRateLimitError
        p = _make_finnhub()
        p._client.get = AsyncMock(return_value=_mock_response(429))
        with pytest.raises(ProviderRateLimitError, match="rate limit"):
            await p.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_http_500_raises_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        p = _make_finnhub()
        p._client.get = AsyncMock(return_value=_mock_response(500))
        with pytest.raises(ProviderUnavailableError, match="server error"):
            await p.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_http_503_raises_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        p = _make_finnhub()
        p._client.get = AsyncMock(return_value=_mock_response(503))
        with pytest.raises(ProviderUnavailableError, match="server error"):
            await p.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_non_json_response_raises_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        p = _make_finnhub()
        p._client.get = AsyncMock(return_value=_mock_response(200, json_data=None, text="<html>Error</html>"))
        with pytest.raises(ProviderUnavailableError, match="non-JSON"):
            await p.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_empty_quote_data_raises_instrument_not_found(self):
        from app.core.exceptions import InstrumentNotFoundError
        p = _make_finnhub()
        p._client.get = AsyncMock(return_value=_mock_response(200, json_data={
            "c": None, "t": None, "pc": None, "o": None, "h": None, "l": None, "d": None, "dp": None
        }))
        with pytest.raises(InstrumentNotFoundError):
            await p.get_quote("INVALID.TICKER")

    @pytest.mark.asyncio
    async def test_empty_instrument_profile_raises_not_found(self):
        from app.core.exceptions import InstrumentNotFoundError
        p = _make_finnhub()
        p._client.get = AsyncMock(return_value=_mock_response(200, json_data={}))
        with pytest.raises(InstrumentNotFoundError, match="not found"):
            await p.get_instrument("INVALID.TICKER")

    @pytest.mark.asyncio
    async def test_api_key_not_in_debug_logs(self):
        p = _make_finnhub(api_key="SUPER_SECRET_KEY_12345")
        p._client.get = AsyncMock(return_value=_mock_response(200, json_data={"c": 0, "t": 0, "pc": 0}))
        import logging
        with patch.object(logging.getLogger("app.providers.finnhub.provider"), "debug") as mock_log:
            try:
                await p._get("/quote", params={"symbol": "AAPL"})
            except Exception:
                pass
            for call in mock_log.call_args_list:
                assert "SUPER_SECRET_KEY_12345" not in str(call), "API key leaked in debug log!"


# ===========================================================================
# NEWSAPI PROVIDER
# ===========================================================================

class TestNewsApiProviderFailures:

    @pytest.mark.asyncio
    async def test_timeout_raises_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        p = _make_newsapi()
        p._client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        with pytest.raises(ProviderUnavailableError, match="timed out"):
            await p.search_news(query="india economy")

    @pytest.mark.asyncio
    async def test_network_error_raises_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        p = _make_newsapi()
        p._client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        with pytest.raises(ProviderUnavailableError, match="Could not reach NewsAPI"):
            await p.search_news(query="market news")

    @pytest.mark.asyncio
    async def test_http_401_raises_provider_auth_error(self):
        from app.core.exceptions import ProviderAuthenticationError
        p = _make_newsapi()
        p._client.get = AsyncMock(return_value=_mock_response(401))
        with pytest.raises(ProviderAuthenticationError, match="API key"):
            await p.search_news(query="test")

    @pytest.mark.asyncio
    async def test_http_403_raises_feature_unavailable(self):
        from app.core.exceptions import ProviderFeatureUnavailableError
        p = _make_newsapi()
        p._client.get = AsyncMock(return_value=_mock_response(403))
        with pytest.raises(ProviderFeatureUnavailableError, match="403"):
            await p.search_news(query="test")

    @pytest.mark.asyncio
    async def test_http_429_raises_rate_limit(self):
        from app.core.exceptions import ProviderRateLimitError
        p = _make_newsapi()
        p._client.get = AsyncMock(return_value=_mock_response(429))
        with pytest.raises(ProviderRateLimitError, match="rate limit"):
            await p.search_news(query="test")

    @pytest.mark.asyncio
    async def test_http_500_raises_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        p = _make_newsapi()
        p._client.get = AsyncMock(return_value=_mock_response(500))
        with pytest.raises(ProviderUnavailableError, match="server error"):
            await p.search_news(query="test")

    @pytest.mark.asyncio
    async def test_non_json_response_raises_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        p = _make_newsapi()
        p._client.get = AsyncMock(return_value=_mock_response(200, json_data=None))
        with pytest.raises(ProviderUnavailableError, match="non-JSON"):
            await p.search_news(query="test")

    @pytest.mark.asyncio
    async def test_app_error_apikey_invalid_raises_auth_error(self):
        from app.core.exceptions import ProviderAuthenticationError
        p = _make_newsapi()
        p._client.get = AsyncMock(return_value=_mock_response(200, json_data={
            "status": "error", "code": "apiKeyInvalid", "message": "Your API key is invalid.", "articles": []
        }))
        with pytest.raises(ProviderAuthenticationError, match="authentication error"):
            await p.search_news(query="test")

    @pytest.mark.asyncio
    async def test_app_error_rate_limited_raises_rate_limit(self):
        from app.core.exceptions import ProviderRateLimitError
        p = _make_newsapi()
        p._client.get = AsyncMock(return_value=_mock_response(200, json_data={
            "status": "error", "code": "rateLimited", "message": "Too many requests.", "articles": []
        }))
        with pytest.raises(ProviderRateLimitError, match="rate limited"):
            await p.search_news(query="test")

    @pytest.mark.asyncio
    async def test_app_error_plan_restriction_raises_feature_unavailable(self):
        from app.core.exceptions import ProviderFeatureUnavailableError
        p = _make_newsapi()
        p._client.get = AsyncMock(return_value=_mock_response(200, json_data={
            "status": "error", "code": "maximumResultsReached", "message": "Plan limit.", "articles": []
        }))
        with pytest.raises(ProviderFeatureUnavailableError, match="plan restriction"):
            await p.search_news(query="test")

    @pytest.mark.asyncio
    async def test_ok_empty_articles_returns_empty_list(self):
        p = _make_newsapi()
        p._client.get = AsyncMock(return_value=_mock_response(200, json_data={
            "status": "ok", "totalResults": 0, "articles": []
        }))
        result = await p.search_news(query="noresults")
        assert result == []

    @pytest.mark.asyncio
    async def test_api_key_not_in_logs(self):
        p = _make_newsapi(api_key="SECRET_NEWSAPI_KEY_XYZ")
        p._client.get = AsyncMock(return_value=_mock_response(200, json_data={"status": "ok", "totalResults": 0, "articles": []}))
        import logging
        with patch.object(logging.getLogger("app.providers.newsapi.provider"), "debug") as mock_log:
            await p.search_news(query="test")
            for call in mock_log.call_args_list:
                assert "SECRET_NEWSAPI_KEY_XYZ" not in str(call), "API key leaked in debug log!"


# ===========================================================================
# TRADING ECONOMICS PROVIDER
# ===========================================================================

class TestTradingEconomicsProviderFailures:

    @pytest.mark.asyncio
    async def test_timeout_raises_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        p = _make_te()
        p._client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        with pytest.raises(ProviderUnavailableError, match="timed out"):
            await p.get_calendar()

    @pytest.mark.asyncio
    async def test_network_error_raises_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        p = _make_te()
        p._client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        with pytest.raises(ProviderUnavailableError, match="Could not reach Trading Economics"):
            await p.get_calendar()

    @pytest.mark.asyncio
    async def test_http_401_raises_provider_auth_error(self):
        from app.core.exceptions import ProviderAuthenticationError
        p = _make_te()
        p._client.get = AsyncMock(return_value=_mock_response(401))
        with pytest.raises(ProviderAuthenticationError, match="API key"):
            await p.get_calendar()

    @pytest.mark.asyncio
    async def test_http_403_raises_feature_unavailable(self):
        from app.core.exceptions import ProviderFeatureUnavailableError
        p = _make_te()
        p._client.get = AsyncMock(return_value=_mock_response(403))
        with pytest.raises(ProviderFeatureUnavailableError, match="subscription plan"):
            await p.get_calendar()

    @pytest.mark.asyncio
    async def test_http_429_raises_rate_limit(self):
        from app.core.exceptions import ProviderRateLimitError
        p = _make_te()
        p._client.get = AsyncMock(return_value=_mock_response(429))
        with pytest.raises(ProviderRateLimitError, match="rate limit"):
            await p.get_calendar()

    @pytest.mark.asyncio
    async def test_http_500_raises_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        p = _make_te()
        p._client.get = AsyncMock(return_value=_mock_response(500))
        with pytest.raises(ProviderUnavailableError, match="server error"):
            await p.get_calendar()

    @pytest.mark.asyncio
    async def test_non_json_response_raises_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        p = _make_te()
        p._client.get = AsyncMock(return_value=_mock_response(200, json_data=None))
        with pytest.raises(ProviderUnavailableError, match="non-JSON"):
            await p.get_calendar()

    @pytest.mark.asyncio
    async def test_non_list_calendar_response_raises_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        p = _make_te()
        p._client.get = AsyncMock(return_value=_mock_response(200, json_data={"error": "unexpected"}))
        with pytest.raises(ProviderUnavailableError, match="unexpected response format"):
            await p.get_calendar()

    @pytest.mark.asyncio
    async def test_empty_calendar_list_returns_empty(self):
        p = _make_te()
        p._client.get = AsyncMock(return_value=_mock_response(200, json_data=[]))
        result = await p.get_calendar()
        assert result == []

    @pytest.mark.asyncio
    async def test_api_key_not_in_logs(self):
        p = _make_te(api_key="SECRET_TE_KEY_ABCDEF")
        p._client.get = AsyncMock(return_value=_mock_response(200, json_data=[]))
        import logging
        with patch.object(logging.getLogger("app.providers.trading_economics.provider"), "debug") as mock_log:
            await p.get_calendar()
            for call in mock_log.call_args_list:
                assert "SECRET_TE_KEY_ABCDEF" not in str(call), "TE API key leaked in debug log!"


# ===========================================================================
# YFINANCE PROVIDER
# ===========================================================================

class TestYFinanceProviderFailures:

    @pytest.mark.asyncio
    async def test_empty_dataframe_raises_not_found(self):
        import pandas as pd
        from app.core.exceptions import NotFoundError
        from app.providers.yfinance.provider import YFinanceMarketDataProvider
        p = YFinanceMarketDataProvider()
        with patch("app.providers.yfinance.provider.yf.Ticker") as mock_cls:
            mock_t = MagicMock()
            mock_t.history = MagicMock(return_value=pd.DataFrame())
            mock_cls.return_value = mock_t
            with pytest.raises(NotFoundError, match="No price history"):
                await p.get_historical_prices("INVALID.NS")

    @pytest.mark.asyncio
    async def test_yfinance_exception_then_raises_not_found(self):
        import pandas as pd
        from app.core.exceptions import NotFoundError
        from app.providers.yfinance.provider import YFinanceMarketDataProvider
        p = YFinanceMarketDataProvider()
        with patch("app.providers.yfinance.provider.yf.Ticker") as mock_cls:
            mock_t = MagicMock()
            mock_t.history = MagicMock(side_effect=Exception("yfinance internal error"))
            mock_cls.return_value = mock_t
            with pytest.raises(NotFoundError):
                await p.get_historical_prices("BROKEN.NS")

    @pytest.mark.asyncio
    async def test_missing_required_column_raises_provider_unavailable(self):
        import pandas as pd
        from app.core.exceptions import ProviderUnavailableError
        from app.providers.yfinance.provider import YFinanceMarketDataProvider
        p = YFinanceMarketDataProvider()
        incomplete_df = pd.DataFrame({"Date": ["2026-01-01"], "Open": [100.0]})
        with patch("app.providers.yfinance.provider.yf.Ticker") as mock_cls:
            mock_t = MagicMock()
            mock_t.history = MagicMock(return_value=incomplete_df)
            mock_cls.return_value = mock_t
            with pytest.raises(ProviderUnavailableError, match="missing"):
                await p.get_historical_prices("RELIANCE.NS")


# ===========================================================================
# SERVICE LAYER PROPAGATION
# ===========================================================================

class TestProviderErrorsViaServiceLayer:

    @pytest.mark.asyncio
    async def test_market_service_propagates_provider_unavailable(self):
        from app.core.exceptions import ProviderUnavailableError
        from app.services.market_service import MarketService
        mock_provider = MagicMock()
        mock_provider.get_quote = AsyncMock(side_effect=ProviderUnavailableError("timed out"))
        svc = MarketService(provider=mock_provider)
        with pytest.raises(ProviderUnavailableError):
            await svc.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_market_service_propagates_rate_limit(self):
        from app.core.exceptions import ProviderRateLimitError
        from app.services.market_service import MarketService
        mock_provider = MagicMock()
        mock_provider.get_quote = AsyncMock(side_effect=ProviderRateLimitError("rate limited"))
        svc = MarketService(provider=mock_provider)
        with pytest.raises(ProviderRateLimitError):
            await svc.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_market_service_propagates_instrument_not_found(self):
        from app.core.exceptions import InstrumentNotFoundError
        from app.services.market_service import MarketService
        mock_provider = MagicMock()
        mock_provider.get_quote = AsyncMock(side_effect=InstrumentNotFoundError("not found"))
        svc = MarketService(provider=mock_provider)
        with pytest.raises(InstrumentNotFoundError):
            await svc.get_quote("UNKNOWNSYM")
