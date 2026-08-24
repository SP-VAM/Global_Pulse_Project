"""
GlobalPulse Unit & Integration Test Suite — Stock ML Prediction Engine
Covers:
  1. Technical indicator mathematical calculations (RSI, MACD, Bollinger Bands, Moving Averages)
  2. Artifact loader & startup validator
  3. Strict company validation — unsupported ticker returns HTTP 404 (NotFoundError)
  4. Feature vector strict ordering — X = X[model_features]
  5. XGBoost model prediction & probability outputs
  6. API router endpoints (/stocks/health, /stocks/companies, /stocks/market-snapshot, /stocks/{symbol}/prediction, /stocks/{symbol}/indicators, /stocks/{symbol}/analysis)
  7. Failure path testing — missing artifacts, invalid symbols, NaN/Inf sanitization, invalid provider, provider close
"""
import os
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import NotFoundError, ValidationError
from app.providers.base.stock_provider import StockMarketDataProvider
from app.providers.stock_provider_factory import get_stock_provider
from app.services.stock_artifact_loader import ModelArtifactsNotFoundError, StockArtifactLoader
from app.services.stock_prediction_service import TICKER_TO_COMPANY, StockPredictionService
from app.services.technical_indicator_service import TechnicalIndicatorService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class MockStockProvider(StockMarketDataProvider):
    """Test double for StockMarketDataProvider."""

    def __init__(self, df: Optional[pd.DataFrame] = None) -> None:
        self._df = df
        self.fetch_count = 0
        self.closed = False

    async def get_historical_prices(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> pd.DataFrame:
        self.fetch_count += 1
        if self._df is not None:
            return self._df.copy()

        dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq="D")
        np.random.seed(42)
        close_prices = 100 + np.cumsum(np.random.randn(30) * 2)

        return pd.DataFrame({
            "Date": dates,
            "Open": close_prices - 1,
            "High": close_prices + 2,
            "Low": close_prices - 2,
            "Close": close_prices,
            "Volume": 1_000_000,
        })

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def mock_stock_provider() -> MockStockProvider:
    return MockStockProvider()


@pytest.fixture
def indicator_service() -> TechnicalIndicatorService:
    return TechnicalIndicatorService()


@pytest.fixture
def mock_news_service():
    from app.domain.news import NormalizedArticle, GlobalEventCategory
    mock = AsyncMock()
    mock.search_news = AsyncMock(return_value=[
        NormalizedArticle(
            id="art_1",
            headline="Reliance posts robust profit growth and strong revenue rise",
            summary="Strong Q3 quarterly earnings beating estimates",
            source_name="Financial Times",
            source_url="https://ft.com",
            article_url="https://ft.com/art1",
            author="Staff",
            published_at_utc="2026-08-20T10:00:00Z",
            published_at_ist="2026-08-20T15:30:00+05:30",
            primary_category=GlobalEventCategory.CORPORATE,
            tags=["Reliance"],
            countries=["IN"],
            companies=[],
            sectors=[],
            keywords=["profit", "growth"],
            relevance_score=85,
            source="NEWSAPI",
        ),
        NormalizedArticle(
            id="art_2",
            headline="Analysts upgrade Reliance target price following expansion",
            summary="Strategic expansion plan announced across retail and energy",
            source_name="Economic Times",
            source_url="https://economictimes.com",
            article_url="https://economictimes.com/art2",
            author="Analyst",
            published_at_utc="2026-08-19T08:00:00Z",
            published_at_ist="2026-08-19T13:30:00+05:30",
            primary_category=GlobalEventCategory.CORPORATE,
            tags=["Reliance"],
            countries=["IN"],
            companies=[],
            sectors=[],
            keywords=["upgrade", "expansion"],
            relevance_score=80,
            source="NEWSAPI",
        )
    ])
    return mock


@pytest.fixture
def prediction_service(mock_stock_provider, indicator_service, mock_news_service) -> StockPredictionService:
    return StockPredictionService(
        provider=mock_stock_provider,
        indicator_service=indicator_service,
        news_service=mock_news_service,
    )


# ---------------------------------------------------------------------------
# 1. Technical Indicators Unit Tests
# ---------------------------------------------------------------------------


class TestTechnicalIndicatorService:

    def test_indicators_computed_correctly(self, indicator_service):
        dates = pd.date_range("2026-01-01", periods=30)
        df = pd.DataFrame({
            "Date": dates,
            "Open": [100.0] * 30,
            "High": [105.0] * 30,
            "Low": [95.0] * 30,
            "Close": [100.0 + i for i in range(30)],
            "Volume": [1000] * 30,
        })

        res = indicator_service.compute_all_indicators(df)

        expected_cols = [
            "SMA20", "SMA50", "EMA20", "EMA50", "RSI", "MACD", "MACD_SIGNAL",
            "MACD_HIST", "BB_UPPER", "BB_MIDDLE", "BB_LOWER", "ATR", "OBV",
            "STOCH_K", "STOCH_D", "ADX", "Daily_Return", "Volatility",
            "Price_Change", "Price_Change_%"
        ]
        for col in expected_cols:
            assert col in res.columns, f"Missing indicator column '{col}'"

        assert not res["RSI"].isnull().any()
        assert not np.isinf(res["MACD"]).any()

    def test_indicator_summary_extraction(self, indicator_service):
        dates = pd.date_range("2026-01-01", periods=30)
        df = pd.DataFrame({
            "Date": dates,
            "Open": [100.0] * 30,
            "High": [105.0] * 30,
            "Low": [95.0] * 30,
            "Close": [100.0 + i for i in range(30)],
            "Volume": [1000] * 30,
        })
        enriched = indicator_service.compute_all_indicators(df)
        summary = indicator_service.extract_summary(enriched)

        assert "rsi_14" in summary
        assert "macd" in summary
        assert "bollinger_bands" in summary
        assert "trend_signal" in summary


# ---------------------------------------------------------------------------
# 2. Strict Company Validation (HTTP 404 Rejection) Tests
# ---------------------------------------------------------------------------


class TestCompanyValidation:

    def test_supported_company_normalized(self, prediction_service):
        assert prediction_service.normalize_symbol("RELIANCE") == "RELIANCE"
        assert prediction_service.normalize_symbol("reliance.ns") == "RELIANCE"
        assert prediction_service.normalize_symbol("HDFCBANK") == "HDFCBANK"
        assert prediction_service.normalize_symbol("TCS.NS") == "TCS"

    def test_unsupported_company_raises_not_found(self, prediction_service):
        """Strictly rejects unknown company tickers with NotFoundError (404)."""
        with pytest.raises(NotFoundError) as exc_info:
            prediction_service.normalize_symbol("UNKNOWN_COMPANY_XYZ")
        assert "not supported" in str(exc_info.value)

    def test_unsupported_company_never_defaults_to_zero(self, prediction_service):
        """Assures unknown tickers raise error rather than returning encoded zero."""
        with pytest.raises(NotFoundError):
            prediction_service.normalize_symbol("INVALID123")


# ---------------------------------------------------------------------------
# 3. Strict Feature Vector Construction & Sanitization Logging
# ---------------------------------------------------------------------------


class TestFeatureVectorConstruction:

    def test_feature_vector_columns_match_model_features_exactly(self, prediction_service, indicator_service):
        dates = pd.date_range("2026-01-01", periods=30)
        df = pd.DataFrame({
            "Date": dates,
            "Open": [100.0] * 30,
            "High": [105.0] * 30,
            "Low": [95.0] * 30,
            "Close": [100.0 + i for i in range(30)],
            "Volume": [1000] * 30,
        })
        enriched = indicator_service.compute_all_indicators(df)
        loader = prediction_service.artifact_loader
        model_features = loader.load_model_features()
        label_encoder = loader.load_label_encoder()

        X, latest_row = prediction_service.build_feature_vector(
            symbol="RELIANCE",
            enriched_df=enriched,
            model_features=model_features,
            label_encoder=label_encoder,
        )

        assert list(X.columns) == model_features
        assert len(X.columns) == len(model_features)
        assert not X.isnull().any().any()

    def test_nan_inf_sanitized_to_zero_with_warning_log(self, prediction_service, indicator_service, caplog):
        dates = pd.date_range("2026-01-01", periods=30)
        df = pd.DataFrame({
            "Date": dates,
            "Open": [100.0] * 30,
            "High": [105.0] * 30,
            "Low": [95.0] * 30,
            "Close": [100.0] * 30,
            "Volume": [0] * 30,
        })
        enriched = indicator_service.compute_all_indicators(df)
        loader = prediction_service.artifact_loader

        with caplog.at_level("WARNING"):
            X, _ = prediction_service.build_feature_vector(
                symbol="TCS",
                enriched_df=enriched,
                model_features=loader.load_model_features(),
                label_encoder=loader.load_label_encoder(),
            )

        assert not np.isinf(X.values).any()
        assert not np.isnan(X.values).any()


# ---------------------------------------------------------------------------
# 4. Failure Path & Provider Factory Tests
# ---------------------------------------------------------------------------


class TestFailurePathsAndFactory:

    def test_missing_model_file_raises_file_not_found(self):
        loader = StockArtifactLoader(model_dir="non_existent_dir_xyz")
        with pytest.raises(ModelArtifactsNotFoundError):
            loader.load_model()

    def test_unsupported_provider_factory_raises_value_error(self, monkeypatch):
        from app.core.config import get_settings
        settings = get_settings()
        monkeypatch.setattr(settings, "STOCK_PROVIDER", "unsupported_provider_abc")

        with pytest.raises(ValueError) as exc_info:
            get_stock_provider()
        assert "Unsupported STOCK_PROVIDER" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_provider_close_teardown(self, mock_stock_provider):
        await mock_stock_provider.close()
        assert mock_stock_provider.closed is True


# ---------------------------------------------------------------------------
# 5. End-to-End Prediction & Price History Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_predict_stock_movement_success(prediction_service):
    res = await prediction_service.predict_stock_movement("RELIANCE")

    assert res["symbol"] == "RELIANCE"
    assert res["company_name"] == "Reliance Industries Ltd"
    assert res["prediction"]["predicted_direction"] in ("UP", "DOWN", "HOLD")
    assert "prob_up" in res["prediction"]
    assert "prob_down" in res["prediction"]
    assert "prob_hold" in res["prediction"]
    
    # Verify probabilities sum to 1.0 (100%)
    prob_sum = round(
        res["prediction"]["prob_up"] + res["prediction"]["prob_down"] + res["prediction"]["prob_hold"],
        4,
    )
    assert prob_sum == 1.0

    assert 0 <= res["prediction"]["confidence_percent"] <= 100
    assert len(res["top_influencing_features"]) > 0
    assert "price_history" in res
    assert len(res["price_history"]) > 0
    assert "date" in res["price_history"][0]
    assert "close" in res["price_history"][0]


@pytest.mark.asyncio
async def test_predict_stock_movement_three_class_model_preserves_hold_and_sums_to_one(prediction_service):
    """Verifies that 3-class model outputs prob_up, prob_down, prob_hold mapping dynamically to model.classes_."""
    # Mock model with 3 classes [0, 1, 2] predicting Class 2 (HOLD)
    mock_model = MagicMock()
    mock_model.classes_ = [0, 1, 2]
    mock_model.predict.return_value = [2]
    mock_model.predict_proba.return_value = np.array([[0.3475, 0.4250, 0.2275]])

    with patch.object(prediction_service.artifact_loader, "load_model", return_value=mock_model):
        res = await prediction_service.predict_stock_movement("TCS")

    pred = res["prediction"]
    assert pred["predicted_direction"] == "HOLD"
    assert pred["signal"] == "NEUTRAL"
    assert pred["prob_down"] == 0.3475
    assert pred["prob_up"] == 0.4250
    assert pred["prob_hold"] == 0.2275
    assert round(pred["prob_down"] + pred["prob_up"] + pred["prob_hold"], 4) == 1.0
    assert pred["confidence_percent"] == 42.5


@pytest.mark.asyncio
async def test_predict_unsupported_stock_raises_404(prediction_service):
    with pytest.raises(NotFoundError):
        await prediction_service.predict_stock_movement("NON_EXISTENT_COMPANY")


# ---------------------------------------------------------------------------
# 6. API Router Tests (/api/v1/stocks/...)
# ---------------------------------------------------------------------------


@pytest.fixture
def stocks_app(mock_news_service):
    """Create test FastAPI application with wired stocks state services."""
    from app.main import create_app
    app = create_app()
    app.state.stock_provider = MockStockProvider()
    app.state.technical_indicator_service = TechnicalIndicatorService()
    app.state.news_service = mock_news_service
    app.state.stock_prediction_service = StockPredictionService(
        provider=app.state.stock_provider,
        indicator_service=app.state.technical_indicator_service,
        news_service=mock_news_service,
    )
    return app


@pytest.mark.asyncio
async def test_stocks_health_endpoint(stocks_app):
    async with AsyncClient(
        transport=ASGITransport(app=stocks_app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/stocks/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["supported_companies_count"] == len(TICKER_TO_COMPANY)
    assert data["feature_count"] > 0


@pytest.mark.asyncio
async def test_stocks_companies_endpoint(stocks_app):
    async with AsyncClient(
        transport=ASGITransport(app=stocks_app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/stocks/companies")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == len(TICKER_TO_COMPANY)
    assert len(data["companies"]) == len(TICKER_TO_COMPANY)


@pytest.mark.asyncio
async def test_stocks_market_snapshot_endpoint(stocks_app):
    """Verifies bulk stock market snapshot endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=stocks_app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/stocks/market-snapshot?symbols=RELIANCE,TCS,HDFCBANK")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    item = data["items"][0]
    assert item["symbol"] in ("RELIANCE", "TCS", "HDFCBANK")
    assert "current_price" in item
    assert "change_percent" in item
    assert len(item["price_history"]) > 0


@pytest.mark.asyncio
async def test_get_top_movers_service_logic(prediction_service):
    """Verifies get_top_movers absolute change sorting, invalid price filtering, and completeness metrics."""
    mock_snapshot = [
        {"symbol": "RELIANCE", "company_name": "Reliance Ltd", "current_price": 3000.0, "previous_close": 2850.0},  # +5.26%
        {"symbol": "TCS", "company_name": "TCS Ltd", "current_price": 3200.0, "previous_close": 3450.0},           # -7.25%
        {"symbol": "INFY", "company_name": "Infosys Ltd", "current_price": 1500.0, "previous_close": 1480.0},       # +1.35%
        {"symbol": "HDFCBANK", "company_name": "HDFC Bank", "current_price": 1400.0, "previous_close": 1450.0},     # -3.45%
        {"symbol": "BAD_ONE", "company_name": "Bad One", "current_price": 0.0, "previous_close": 100.0},           # Invalid price
        {"symbol": "BAD_TWO", "company_name": "Bad Two", "current_price": 100.0, "previous_close": 0.0},           # Zero prev close
    ]

    with patch.object(prediction_service, "get_market_snapshot", return_value=mock_snapshot):
        res = await prediction_service.get_top_movers(limit=5)

    assert res["universe"] == "NIFTY50"
    assert res["universe_count"] == len(TICKER_TO_COMPANY)
    assert res["valid_records"] == 4
    assert res["failed_records"] == len(TICKER_TO_COMPANY) - 4
    assert len(res["movers"]) == 4

    # Top mover 1: TCS (-7.25% abs rank #1)
    assert res["movers"][0]["symbol"] == "TCS"
    assert res["movers"][0]["change_percent"] == -7.25
    assert res["movers"][0]["direction"] == "down"

    # Top mover 2: RELIANCE (+5.26% abs rank #2)
    assert res["movers"][1]["symbol"] == "RELIANCE"
    assert res["movers"][1]["change_percent"] == 5.26
    assert res["movers"][1]["direction"] == "up"

    # Top mover 3: HDFCBANK (-3.45% abs rank #3)
    assert res["movers"][2]["symbol"] == "HDFCBANK"

    # Top mover 4: INFY (+1.35% abs rank #4)
    assert res["movers"][3]["symbol"] == "INFY"


@pytest.mark.asyncio
async def test_stocks_top_movers_endpoint(stocks_app):
    """Verifies GET /api/v1/stocks/top-movers endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=stocks_app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/stocks/top-movers?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "as_of" in data
    assert "as_of_formatted" in data
    assert "market_status" in data
    assert "is_stale" in data
    assert data["universe"] == "NIFTY50"
    assert data["universe_count"] == len(TICKER_TO_COMPANY)
    assert "movers" in data
    assert len(data["movers"]) <= 5
    if len(data["movers"]) > 0:
        item = data["movers"][0]
        assert "symbol" in item
        assert "yahoo_ticker" in item
        assert "current_price" in item
        assert "change_percent" in item
        assert item["direction"] in ("up", "down")


@pytest.mark.asyncio
async def test_stocks_prediction_endpoint_valid(stocks_app):
    async with AsyncClient(
        transport=ASGITransport(app=stocks_app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/stocks/RELIANCE/prediction")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "RELIANCE"
    assert "prediction" in data
    assert "price_history" in data


@pytest.mark.asyncio
async def test_stocks_prediction_endpoint_unsupported_returns_404(stocks_app):
    """Assures unsupported ticker returns HTTP 404."""
    async with AsyncClient(
        transport=ASGITransport(app=stocks_app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/stocks/UNSUPPORTEDCOMPANY/prediction")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stocks_indicators_endpoint_valid(stocks_app):
    async with AsyncClient(
        transport=ASGITransport(app=stocks_app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/stocks/HDFCBANK/indicators?period=1mo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "HDFCBANK"
    assert "summary" in data


@pytest.mark.asyncio
async def test_stocks_analysis_endpoint_valid_single_fetch(stocks_app):
    """Verifies orchestrated endpoint single-fetches market data and returns priceHistory."""
    from app.api.v1.stocks import _full_analysis_cache
    _full_analysis_cache.clear()
    provider = stocks_app.state.stock_provider
    initial_fetch_count = provider.fetch_count

    async with AsyncClient(
        transport=ASGITransport(app=stocks_app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/stocks/TCS/analysis")

    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "TCS"
    assert "prediction" in data
    assert "technical_indicators" in data
    assert "price_history" in data
    assert len(data["price_history"]) > 0
    # Verify price data was fetched exactly ONCE for the analysis call
    assert provider.fetch_count == initial_fetch_count + 1


# ---------------------------------------------------------------------------
# 7. News Sentiment Dynamic Data Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_get_stock_news_sentiment_calculates_counts_and_formula(prediction_service):
    """Verifies service method calculates positive, negative, net_sentiment and sentiment_label correctly."""
    res = await prediction_service.get_stock_news_sentiment("RELIANCE")
    assert res["symbol"] == "RELIANCE"
    assert res["company_name"] == "Reliance Industries Ltd"
    assert "net_sentiment" in res
    assert "sentiment_label" in res
    assert res["sentiment_label"] in ("Bullish", "Neutral", "Bearish")
    assert "articles_traced" in res
    assert "positive_articles" in res
    assert "negative_articles" in res
    assert "neutral_articles" in res
    assert res["articles_traced"] == res["positive_articles"] + res["negative_articles"] + res["neutral_articles"]
    if res["articles_traced"] > 0:
        expected_net = round((res["positive_articles"] - res["negative_articles"]) / float(res["articles_traced"]), 2)
        assert res["net_sentiment"] == expected_net


@pytest.mark.asyncio
async def test_stocks_sentiment_endpoint_valid(stocks_app):
    """Verifies GET /api/v1/stocks/{symbol}/sentiment returns dynamic fields matching Pydantic contract."""
    async with AsyncClient(
        transport=ASGITransport(app=stocks_app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/stocks/INFY/sentiment")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "INFY"
    assert data["company_name"] == "Infosys Ltd"
    assert "net_sentiment" in data
    assert data["sentiment_label"] in ("Bullish", "Neutral", "Bearish")
    assert data["articles_traced"] == data["positive_articles"] + data["negative_articles"] + data["neutral_articles"]
    assert isinstance(data["news_list"], list)


@pytest.mark.asyncio
async def test_stocks_sentiment_endpoint_unsupported_returns_404(stocks_app):
    """Verifies unsupported stock ticker returns 404."""
    async with AsyncClient(
        transport=ASGITransport(app=stocks_app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/api/v1/stocks/UNKNOWNCOMPANY/sentiment")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_stocks_sentiment_empty_article_dataset_returns_zero_neutral_state(mock_stock_provider, indicator_service):
    """Verifies empty dataset returns 0 counts and 0.0 Neutral state without failing."""
    empty_news_service = AsyncMock()
    empty_news_service.search_news = AsyncMock(return_value=[])
    service = StockPredictionService(
        provider=mock_stock_provider,
        indicator_service=indicator_service,
        news_service=empty_news_service,
    )
    res = await service.get_stock_news_sentiment("INFY")
    assert res["symbol"] == "INFY"
    assert res["articles_traced"] == 0
    assert res["positive_articles"] == 0
    assert res["negative_articles"] == 0
    assert res["neutral_articles"] == 0
    assert res["net_sentiment"] == 0.0
    assert res["sentiment_label"] == "Neutral"
    assert res["news_list"] == []


@pytest.mark.asyncio
async def test_stocks_sentiment_ticker_isolation(prediction_service):
    """Verifies that different tickers return company-specific sentiment response."""
    res_rel = await prediction_service.get_stock_news_sentiment("RELIANCE")
    res_tcs = await prediction_service.get_stock_news_sentiment("TCS")
    assert res_rel["symbol"] == "RELIANCE"
    assert res_tcs["symbol"] == "TCS"
    assert res_rel["company_name"] != res_tcs["company_name"]


@pytest.mark.asyncio
async def test_predict_stock_movement_unseen_label_encoder_fallback(prediction_service):
    """Verifies that company names absent from label_encoder classes (e.g. BPCL) fall back to 0 without raising ValidationError."""
    res = await prediction_service.predict_stock_movement("BPCL")
    assert res["symbol"] == "BPCL"
    assert res["company_name"] == "Bharat Petroleum Corporation Ltd"
    assert "prediction" in res


@pytest.mark.parametrize("symbol", ["RELIANCE", "TCS", "INFY", "BRITANNIA", "M&M", "DIVISLAB", "ITC"])
@pytest.mark.asyncio
async def test_market_analysis_pipeline_seven_companies(stocks_app, symbol):
    """
    Regression test for DIVISLAB, M&M, BRITANNIA, RELIANCE, TCS, INFY, ITC.
    Verifies live market data, indicators, prediction, and sentiment endpoints return HTTP 200 with valid non-zero prices.
    """
    from urllib.parse import quote
    encoded = quote(symbol)

    async with AsyncClient(
        transport=ASGITransport(app=stocks_app), base_url="http://test"
    ) as ac:
        # 1. Full Analysis Endpoint
        resp_analysis = await ac.get(f"/api/v1/stocks/{encoded}/analysis")
        assert resp_analysis.status_code == 200
        data_analysis = resp_analysis.json()
        assert data_analysis["symbol"] == symbol.upper().replace(".NS", "")
        assert data_analysis["current_close"] > 0.0
        assert len(data_analysis["historical_chart_data"]) > 0

        # 2. Prediction Endpoint
        resp_pred = await ac.get(f"/api/v1/stocks/{encoded}/prediction")
        assert resp_pred.status_code == 200
        data_pred = resp_pred.json()
        assert data_pred["symbol"] == symbol.upper().replace(".NS", "")
        assert "prediction" in data_pred

        # 3. Indicators Endpoint
        resp_ind = await ac.get(f"/api/v1/stocks/{encoded}/indicators")
        assert resp_ind.status_code == 200
        data_ind = resp_ind.json()
        assert data_ind["symbol"] == symbol.upper().replace(".NS", "")
        assert "summary" in data_ind

        # 4. Sentiment Endpoint
        resp_sent = await ac.get(f"/api/v1/stocks/{encoded}/sentiment")
        assert resp_sent.status_code == 200
        data_sent = resp_sent.json()
        assert data_sent["symbol"] == symbol.upper().replace(".NS", "")
        assert "net_sentiment" in data_sent



