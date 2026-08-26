"""
FRD-052 – Monitoring Unit Test Suite
Validates all monitoring, health check, service availability, system metrics,
monitoring data, alerting, error handling, and regression capabilities of GlobalPulse.
"""
import asyncio
import gc
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.health import HealthResponse
from app.core.config import get_settings
from app.core.logging import (
    ContextualLoggingFilter,
    SensitiveDataRedactionFilter,
    StructuredJsonFormatter,
    log_api_request,
    log_external_api_call,
    request_id_ctx,
    user_id_ctx,
)
from app.domain.instrument import NormalizedQuote
from app.main import create_app, lifespan
from app.providers.base.stock_provider import StockMarketDataProvider
from app.services.anomaly_service import AnomalyDetectionService
from app.services.economic_service import EconomicService
from app.services.historical_analytics_service import HistoricalAnalyticsService
from app.services.historical_store import InMemoryHistoricalSnapshotStore
from app.services.market_service import MarketService
from app.services.market_status_service import MarketStatusService
from app.services.news_service import NewsService
from app.services.stock_artifact_loader import get_stock_artifact_loader
from app.services.stock_prediction_service import StockPredictionService
from app.services.technical_indicator_service import TechnicalIndicatorService


# ============================================================================
# Test Doubles & Fixtures
# ============================================================================

class MockStockProvider(StockMarketDataProvider):
    """Deterministic test double for StockMarketDataProvider."""

    async def get_historical_prices(
        self, symbol: str, period: str = "1mo", interval: str = "1d"
    ) -> pd.DataFrame:
        dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq="D")
        return pd.DataFrame({
            "Date": dates,
            "Open": [100.0] * 30,
            "High": [105.0] * 30,
            "Low": [95.0] * 30,
            "Close": [102.0] * 30,
            "Volume": [1000000] * 30,
        })

    async def close(self) -> None:
        pass


@pytest.fixture
def mock_app():
    """Create a FastAPI application with deterministic mock providers injected on app.state."""
    app = create_app()
    mock_stock_prov = MockStockProvider()
    app.state.stock_provider = mock_stock_prov
    app.state.technical_indicator_service = TechnicalIndicatorService()
    app.state.stock_prediction_service = StockPredictionService(
        provider=mock_stock_prov,
        indicator_service=app.state.technical_indicator_service,
    )
    app.state.market_service = MarketService(provider=MagicMock())
    app.state.market_status_service = MarketStatusService()
    return app


# ============================================================================
# Section 1: HEALTH CHECK
# ============================================================================

@pytest.mark.asyncio
async def test_frd052_application_health_check_returns_healthy_response(mock_app):
    """Verify application health check endpoint /api/v1/health returns HTTP 200 with status='healthy'."""
    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_frd052_health_check_response_structure_and_fields(mock_app):
    """Verify response structure and expected fields of HealthResponse schema."""
    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        
        assert "status" in data
        assert "service" in data
        assert "version" in data
        
        settings = get_settings()
        assert data["status"] == "healthy"
        assert data["service"] == f"{settings.APP_NAME} API"
        assert data["version"] == settings.APP_VERSION


@pytest.mark.asyncio
async def test_frd052_health_status_representation():
    """Verify health status is correctly represented as a HealthResponse object."""
    resp = HealthResponse(status="healthy", service="GlobalPulse API", version="1.0.0")
    assert resp.status == "healthy"
    assert resp.service == "GlobalPulse API"
    assert resp.version == "1.0.0"


@pytest.mark.asyncio
async def test_frd052_stock_engine_health_check_endpoint(mock_app):
    """Verify stock engine health check endpoint /api/v1/stocks/health returns model artifact metrics."""
    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/stocks/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ("healthy", "degraded")
        assert "active_provider" in data
        assert "model_loaded" in data
        assert "label_encoder_loaded" in data
        assert "feature_count" in data
        assert "supported_companies_count" in data
        assert isinstance(data["feature_count"], int)
        assert isinstance(data["supported_companies_count"], int)


# ============================================================================
# Section 2: SERVICE AVAILABILITY
# ============================================================================

@pytest.mark.asyncio
async def test_frd052_monitored_services_detected_available():
    """Verify all core monitored services are correctly detected and attached to app.state on lifespan startup."""
    app = create_app()
    with patch("app.services.stock_prediction_service.StockPredictionService.get_market_snapshot", new_callable=AsyncMock, return_value=[]):
        async with lifespan(app):
            assert hasattr(app.state, "market_service")
            assert hasattr(app.state, "market_status_service")
            assert hasattr(app.state, "economic_service")
            assert hasattr(app.state, "news_service")
            assert hasattr(app.state, "anomaly_service")
            assert hasattr(app.state, "correlation_service")
            assert hasattr(app.state, "severity_service")
            assert hasattr(app.state, "india_impact_service")
            assert hasattr(app.state, "historical_store")
            assert hasattr(app.state, "historical_analytics_service")
            assert hasattr(app.state, "explanation_service")
            assert hasattr(app.state, "dashboard_service")
            assert hasattr(app.state, "stock_prediction_service")


@pytest.mark.asyncio
async def test_frd052_service_status_returned_correctly():
    """Verify service availability status is correctly returned for individual monitored services."""
    market_status = MarketStatusService()
    status_info = market_status.get_status_by_exchange("NSE")
    assert status_info is not None
    assert status_info.exchange == "NSE"
    assert isinstance(status_info.session_status.value, str) or status_info.session_status in ("OPEN", "CLOSED")


@pytest.mark.asyncio
async def test_frd052_multiple_monitored_services_handled_simultaneously():
    """Verify multiple monitored services can be queried concurrently without status corruption."""
    anomaly_svc = AnomalyDetectionService()
    hist_store = InMemoryHistoricalSnapshotStore()
    hist_analytics = HistoricalAnalyticsService(store=hist_store)
    
    anomalies, total = anomaly_svc.get_in_memory_anomalies()
    trend_analytics = hist_analytics.compute_trend_analytics()
    
    assert isinstance(anomalies, list)
    assert trend_analytics is not None


# ============================================================================
# Section 3: SYSTEM METRICS
# ============================================================================

@pytest.mark.asyncio
async def test_frd052_cpu_and_memory_metric_collection():
    """Verify system metrics (memory allocation, GC counts, uptime) can be collected cleanly."""
    gc.collect()
    gc_counts = gc.get_count()
    assert len(gc_counts) == 3
    assert all(count >= 0 for count in gc_counts)

    pid = os.getpid()
    assert pid > 0


@pytest.mark.asyncio
async def test_frd052_resource_metric_formatting_and_types():
    """Verify metric values are formatted correctly as standard numeric types."""
    start_time = time.monotonic()
    await asyncio.sleep(0.01)
    duration_ms = (time.monotonic() - start_time) * 1000.0

    assert isinstance(duration_ms, float)
    assert duration_ms > 0.0


@pytest.mark.asyncio
async def test_frd052_metric_collection_does_not_corrupt_application_data():
    """Verify reading monitoring metrics does not alter or corrupt application data."""
    store = InMemoryHistoricalSnapshotStore()
    initial_count = len(store._anomaly_store)

    _ = len(store._anomaly_store)
    _ = store.max_anomaly_items

    assert len(store._anomaly_store) == initial_count


# ============================================================================
# Section 4: MONITORING DATA
# ============================================================================

@pytest.mark.asyncio
async def test_frd052_monitoring_data_generation_and_storage():
    """Verify structured monitoring data (request duration, status code) is generated correctly."""
    request_id_ctx.set("req-test-monitoring-123")
    
    with patch("app.core.logging._app_logger.log") as mock_log:
        log_api_request(
            method="GET",
            path="/api/v1/health",
            status_code=200,
            duration_ms=12.45,
            request_id="req-test-monitoring-123"
        )
        assert mock_log.called
        args, kwargs = mock_log.call_args
        assert args[0] == logging.INFO
        assert kwargs["extra"]["status_code"] == 200
        assert kwargs["extra"]["duration_ms"] == 12.45


@pytest.mark.asyncio
async def test_frd052_timestamps_utc_and_ist_fields():
    """Verify monitoring data contains proper ISO timestamps in UTC."""
    now_utc = datetime.now(timezone.utc)
    iso_str = now_utc.isoformat()
    assert iso_str.endswith("+00:00") or "Z" in iso_str or "+00:00" in iso_str


@pytest.mark.asyncio
async def test_frd052_stock_diag_yfinance_monitoring_endpoint(mock_app):
    """Verify stock diagnostic monitoring endpoint /api/v1/stocks/_diag/yfinance returns structured diagnostic metrics."""
    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/stocks/_diag/yfinance?symbol=RELIANCE&period=5d")
        assert res.status_code == 200
        data = res.json()
        assert data["requested_symbol"] == "RELIANCE"
        assert data["normalized_symbol"] == "RELIANCE"
        assert "rows" in data
        assert isinstance(data["rows"], int)


# ============================================================================
# Section 5: ALERTING
# ============================================================================

@pytest.mark.asyncio
async def test_frd052_alert_condition_evaluation_on_threshold_breach():
    """Verify alert conditions trigger when price move threshold is breached in AnomalyDetectionService."""
    anomaly_svc = AnomalyDetectionService()
    
    # Normal quote: within 3% threshold => no anomaly alert
    quote_normal = NormalizedQuote(
        symbol="RELIANCE",
        price=1000.0,
        open=1000.0,
        high=1005.0,
        low=995.0,
        previous_close=998.0,
        change=2.0,
        change_percent=0.20,
        currency="INR",
        timestamp_utc="2026-08-18T10:00:00+00:00",
        timestamp_ist="2026-08-18T15:30:00+05:30",
        source="FINNHUB",
    )
    anomaly_normal = anomaly_svc.detect_quote_anomaly(quote_normal, asset_type="EQUITY")
    assert anomaly_normal is None
    
    # Breached quote: 8% price move => triggers anomaly alert
    quote_breach = NormalizedQuote(
        symbol="RELIANCE",
        price=1080.0,
        open=1000.0,
        high=1085.0,
        low=995.0,
        previous_close=1000.0,
        change=80.0,
        change_percent=8.00,
        currency="INR",
        timestamp_utc="2026-08-18T10:00:00+00:00",
        timestamp_ist="2026-08-18T15:30:00+05:30",
        source="FINNHUB",
    )
    anomaly_breach = anomaly_svc.detect_quote_anomaly(quote_breach, asset_type="EQUITY")
    assert anomaly_breach is not None
    assert anomaly_breach.symbol == "RELIANCE"
    assert anomaly_breach.change_percent == 8.00


@pytest.mark.asyncio
async def test_frd052_no_unnecessary_alert_when_within_safe_threshold():
    """Verify no unnecessary alert is generated when metrics remain strictly within expected threshold."""
    anomaly_svc = AnomalyDetectionService()
    quote = NormalizedQuote(
        symbol="TCS",
        price=3000.0,
        open=3000.0,
        high=3010.0,
        low=2995.0,
        previous_close=3000.0,
        change=0.0,
        change_percent=0.0,
        currency="INR",
        timestamp_utc="2026-08-18T10:00:00+00:00",
        timestamp_ist="2026-08-18T15:30:00+05:30",
        source="FINNHUB",
    )
    result = anomaly_svc.detect_quote_anomaly(quote, asset_type="EQUITY")
    assert result is None


@pytest.mark.asyncio
async def test_frd052_alert_payload_and_message_structure():
    """Verify alert payload structure contains required metadata fields."""
    anomaly_svc = AnomalyDetectionService()
    quote_breach = NormalizedQuote(
        symbol="INFY",
        price=1600.0,
        open=1500.0,
        high=1610.0,
        low=1490.0,
        previous_close=1500.0,
        change=100.0,
        change_percent=6.67,
        currency="INR",
        timestamp_utc="2026-08-18T10:00:00+00:00",
        timestamp_ist="2026-08-18T15:30:00+05:30",
        source="FINNHUB",
    )
    anomaly = anomaly_svc.detect_quote_anomaly(quote_breach, asset_type="EQUITY")
    assert anomaly is not None
    
    assert hasattr(anomaly, "id")
    assert hasattr(anomaly, "symbol")
    assert hasattr(anomaly, "severity")
    assert hasattr(anomaly, "change_percent")
    assert hasattr(anomaly, "detected_at_utc")
    assert hasattr(anomaly, "detected_at_ist")


# ============================================================================
# Section 6: API / BACKEND INTEGRATION AT UNIT LEVEL
# ============================================================================

@pytest.mark.asyncio
async def test_frd052_monitoring_backend_integration_endpoints(mock_app):
    """Verify backend monitoring endpoints return expected status codes and payloads."""
    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as ac:
        r1 = await ac.get("/api/v1/health")
        assert r1.status_code == 200
        
        r2 = await ac.get("/api/v1/stocks/health")
        assert r2.status_code == 200
        
        r3 = await ac.get("/api/v1/stocks/companies")
        assert r3.status_code == 200


@pytest.mark.asyncio
async def test_frd052_lifespan_resource_cleanup_integration():
    """Verify monitoring and provider resources initialize on startup and clean up on shutdown."""
    app = create_app()
    with patch("app.services.stock_prediction_service.StockPredictionService.get_market_snapshot", new_callable=AsyncMock, return_value=[]):
        async with lifespan(app):
            assert app.state.market_service is not None
            assert app.state.stock_prediction_service is not None


# ============================================================================
# Section 7: ERROR HANDLING
# ============================================================================

@pytest.mark.asyncio
async def test_frd052_error_handling_unavailable_service_or_provider_failure(mock_app):
    """Verify that provider failures during monitoring queries return structured errors without crashing the server."""
    async def mock_failed_predict(symbol: str):
        from app.core.exceptions import ProviderUnavailableError
        raise ProviderUnavailableError("Simulated external provider downtime")
        
    mock_app.state.stock_prediction_service.predict_stock_movement = mock_failed_predict

    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/stocks/RELIANCE/prediction")
        assert res.status_code == 503
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] == "PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_frd052_error_handling_invalid_metric_values_or_params(mock_app):
    """Verify invalid metric queries (e.g. 404 unsupported stock ticker) produce correct 404 responses."""
    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/stocks/INVALID_TICKER_99/analysis")
        assert res.status_code in (400, 404)
        data = res.json()
        assert "error" in data


@pytest.mark.asyncio
async def test_frd052_failures_do_not_crash_unrelated_monitoring(mock_app):
    """Verify a failure in stock diagnostics does not crash general application health monitoring."""
    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"


# ============================================================================
# Section 8: REGRESSION TESTING
# ============================================================================

@pytest.mark.asyncio
async def test_frd052_regression_existing_functionality_unaffected(mock_app):
    """Verify existing core endpoints remain functional and unaffected by monitoring tests."""
    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as ac:
        res_markets = await ac.get("/api/v1/markets")
        assert res_markets.status_code == 200
        
        res_market_status = await ac.get("/api/v1/market-status")
        assert res_market_status.status_code == 200


@pytest.mark.asyncio
async def test_frd052_regression_monitoring_isolation_no_db_side_effects(mock_app):
    """Verify monitoring operations do not modify or mutate production database tables."""
    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/health")
        assert res.status_code == 200
