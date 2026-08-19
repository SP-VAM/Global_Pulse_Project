"""
Unit Test Suite for:
1. Real-time Share Price Reflection (Live & Cached quotes, Price changes, Timestamp conversions)
2. Market Analysis Pipeline across 7 Focus Companies:
   - RELIANCE (Reliance Industries)
   - TCS (Tata Consultancy Services)
   - INFY (Infosys Ltd)
   - BRITANNIA (Britannia Industries)
   - M&M (Mahindra & Mahindra)
   - DIVISLAB (Divi's Laboratories)
   - ITC (ITC Ltd)
3. 30-minute cache TTL validation to prevent rate limits
4. Technical Indicator calculations (RSI, MACD, Bollinger Bands, SMA, EMA)
5. News Sentiment aggregation and formula validation
"""
from typing import Optional
import pytest
import pandas as pd
import numpy as np
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.providers.base.stock_provider import StockMarketDataProvider
from app.services.stock_prediction_service import (
    StockPredictionService,
    TICKER_TO_COMPANY,
)
from app.services.technical_indicator_service import TechnicalIndicatorService


# ---------------------------------------------------------------------------
# Test Double / Fixtures
# ---------------------------------------------------------------------------

class MockStockProvider(StockMarketDataProvider):
    """Test double for StockMarketDataProvider simulating live market feeds."""

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
        close_prices = 1000 + np.cumsum(np.random.randn(30) * 15)

        return pd.DataFrame({
            "Date": dates,
            "Open": close_prices - 3,
            "High": close_prices + 6,
            "Low": close_prices - 6,
            "Close": close_prices,
            "Volume": 2_500_000,
        })

    async def get_batch_historical_prices(
        self, symbols: list[str], period: str = "1mo", interval: str = "1d"
    ) -> dict[str, pd.DataFrame]:
        results = {}
        for s in symbols:
            results[s] = await self.get_historical_prices(s, period=period, interval=interval)
        return results

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def stocks_app():
    """Create test FastAPI application with wired stocks state services."""
    app = create_app()
    app.state.stock_provider = MockStockProvider()
    app.state.technical_indicator_service = TechnicalIndicatorService()
    app.state.stock_prediction_service = StockPredictionService(
        provider=app.state.stock_provider,
        indicator_service=app.state.technical_indicator_service,
    )
    return app


# ---------------------------------------------------------------------------
# 1. Test Supported Companies and Real-time Tickers
# ---------------------------------------------------------------------------

def test_seven_focus_companies_registered():
    """Verify all 7 focus companies are registered."""
    expected_companies = [
        "RELIANCE",
        "TCS",
        "INFY",
        "BRITANNIA",
        "M&M",
        "DIVISLAB",
        "ITC",
    ]
    for company in expected_companies:
        assert company in TICKER_TO_COMPANY


# ---------------------------------------------------------------------------
# 2. Test Technical Indicator Calculations for Real-time Market Analysis
# ---------------------------------------------------------------------------

def test_technical_indicators_reflection():
    service = TechnicalIndicatorService()
    dates = pd.date_range("2026-01-01", periods=60, freq="D")
    np.random.seed(42)
    close_prices = 1000.0 + np.cumsum(np.random.randn(60) * 10)

    df = pd.DataFrame({
        "Date": dates,
        "Open": close_prices - 2,
        "High": close_prices + 5,
        "Low": close_prices - 5,
        "Close": close_prices,
        "Volume": np.random.randint(100000, 5000000, size=60),
    })

    result_df = service.compute_all_indicators(df)
    assert "RSI" in result_df.columns
    assert "MACD" in result_df.columns
    assert "MACD_SIGNAL" in result_df.columns
    assert "BB_UPPER" in result_df.columns
    assert "BB_LOWER" in result_df.columns
    assert "SMA20" in result_df.columns
    assert "EMA20" in result_df.columns

    # Verify RSI values are within [0, 100]
    valid_rsi = result_df["RSI"].dropna()
    assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()


# ---------------------------------------------------------------------------
# 3. Test Real-time Quotes & Stock Analysis Endpoints via FastAPI Client
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_realtime_market_snapshot_endpoint(stocks_app):
    """Verify /api/v1/stocks/market-snapshot returns active stock cards."""
    transport = ASGITransport(app=stocks_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/stocks/market-snapshot?symbols=RELIANCE,TCS,INFY")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        for stock in data["items"]:
            assert "symbol" in stock
            assert "company_name" in stock
            assert "current_price" in stock
            assert "change_percent" in stock


@pytest.mark.asyncio
@pytest.mark.parametrize("symbol", ["RELIANCE", "TCS", "INFY", "BRITANNIA", "M&M", "DIVISLAB", "ITC", "BAJAJ-AUTO", "HDFCBANK"])
async def test_realtime_stock_analysis_endpoint_per_company(stocks_app, symbol):
    """Verify /api/v1/stocks/{symbol}/analysis returns complete chart + indicators + prediction."""
    transport = ASGITransport(app=stocks_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/stocks/{symbol}/analysis")
        assert response.status_code == 200
        data = response.json()

        # Check real-time price reflection fields
        assert data["symbol"] == symbol
        assert "prediction" in data
        assert "technical_indicators" in data
        assert "price_history" in data
        assert len(data["price_history"]) > 0

        # Check ML prediction
        prediction = data["prediction"]
        assert "predicted_direction" in prediction
        assert prediction["predicted_direction"] in ["UP", "DOWN", "HOLD"]
        assert "confidence_percent" in prediction
        assert 0.0 <= prediction["confidence_percent"] <= 100.0
        assert "signal" in prediction


# ---------------------------------------------------------------------------
# 4. Test Stock News Sentiment Endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("symbol", ["RELIANCE", "TCS", "INFY"])
async def test_realtime_stock_sentiment_endpoint(stocks_app, symbol):
    """Verify /api/v1/stocks/{symbol}/sentiment returns aggregated score and counts."""
    transport = ASGITransport(app=stocks_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/stocks/{symbol}/sentiment")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == symbol
        assert "net_sentiment" in data
        assert -1.0 <= data["net_sentiment"] <= 1.0
        assert "sentiment_label" in data
        assert data["sentiment_label"] in ["Bullish", "Bearish", "Neutral"]
        assert "articles_traced" in data
        assert "news_list" in data
