"""
GlobalPulse FastAPI Application Entry Point
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.limiter import limiter
from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import (
    MaxBodySizeMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from app.providers.finnhub.provider import FinnhubMarketProvider
from app.providers.newsapi.provider import NewsApiProvider
from app.providers.trading_economics.provider import TradingEconomicsProvider
from app.services.anomaly_service import AnomalyDetectionService
from app.services.correlation_service import EventCorrelationService
from app.services.dashboard_service import DashboardService
from app.services.economic_service import EconomicService
from app.services.event_classification_service import EventClassificationService
from app.services.india_impact_service import IndiaImpactService
from app.services.market_service import MarketService
from app.services.market_status_service import MarketStatusService
from app.services.news_service import NewsService
from app.services.severity_service import SeverityEngineService


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan manager.
    Initializes shared resources on startup, releases them on shutdown.
    """
    settings = get_settings()
    setup_logging()

    # ── Database Schema Verification ───────────────────────────────────
    from app.db.models import Base
    from app.db.session import async_engine
    async def _init_db() -> None:
        try:
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables verified/created successfully.")
        except Exception as exc:
            logger.warning("Database schema initialization error: %s", exc)

    asyncio.create_task(_init_db())

    # ── Phase 1A–1C: Finnhub market data ──────────────────────────────
    finnhub_provider = FinnhubMarketProvider(
        api_key=settings.FINNHUB_API_KEY,
        base_url=settings.FINNHUB_BASE_URL,
        timeout=settings.FINNHUB_TIMEOUT_SECONDS,
    )
    app.state.market_service = MarketService(provider=finnhub_provider)
    app.state.market_status_service = MarketStatusService()

    # ── Phase 1D: Trading Economics economic/macro data ───────────────
    te_provider = TradingEconomicsProvider(
        api_key=settings.TRADING_ECONOMICS_API_KEY,
        base_url=settings.TRADING_ECONOMICS_BASE_URL,
        timeout=settings.TRADING_ECONOMICS_TIMEOUT_SECONDS,
    )
    app.state.economic_service = EconomicService(provider=te_provider)

    # ── Phase 1E: NewsAPI news & global events ─────────────────────────
    news_provider = NewsApiProvider(
        api_key=settings.NEWS_API_KEY,
        base_url=settings.NEWS_API_BASE_URL,
        timeout=settings.NEWS_API_TIMEOUT_SECONDS,
    )
    classifier = EventClassificationService()
    app.state.news_service = NewsService(provider=news_provider, classifier=classifier)

    # ── Phase 2: Anomaly Engine, Correlation & Severity Services ──────
    app.state.anomaly_service = AnomalyDetectionService()
    app.state.correlation_service = EventCorrelationService()
    app.state.severity_service = SeverityEngineService()

    # ── Phase 3B: India Impact Transmission Engine ─────────────────────
    app.state.india_impact_service = IndiaImpactService()

    # ── Phase 4A & 4B: Historical Store & Analytics Engine ──────────────
    from app.services.historical_analytics_service import HistoricalAnalyticsService
    from app.services.historical_store import InMemoryHistoricalSnapshotStore
    app.state.historical_store = InMemoryHistoricalSnapshotStore()
    app.state.historical_analytics_service = HistoricalAnalyticsService(
        store=app.state.historical_store
    )

    # ── Phase 5: AI Explanation Engine ─────────────────────────────────
    from app.services.deterministic_template_provider import DeterministicTemplateProvider
    from app.services.explanation_cache import InMemoryExplanationCache
    from app.services.explanation_context_assembler import ExplanationContextAssembler
    from app.services.explanation_service import ExplanationService

    assembler = ExplanationContextAssembler()
    exp_cache = InMemoryExplanationCache()
    template_provider = DeterministicTemplateProvider()
    app.state.explanation_service = ExplanationService(
        assembler=assembler,
        cache=exp_cache,
        primary_provider=template_provider,
    )

    # ── Dashboard Service ──────────────────────────────────────────────
    app.state.dashboard_service = DashboardService(
        news_service=app.state.news_service,
        market_service=app.state.market_service,
        anomaly_service=app.state.anomaly_service,
        correlation_service=app.state.correlation_service,
        severity_service=app.state.severity_service,
        india_impact_service=app.state.india_impact_service,
        historical_analytics_service=app.state.historical_analytics_service,
        explanation_service=app.state.explanation_service,
    )

    # ── Stock ML Prediction Engine ─────────────────────────────────────
    from app.providers.stock_provider_factory import get_stock_provider
    from app.services.stock_artifact_loader import get_stock_artifact_loader
    from app.services.stock_prediction_service import StockPredictionService
    from app.services.technical_indicator_service import TechnicalIndicatorService
    from app.db.session import AsyncSessionLocal

    stock_provider = get_stock_provider()
    app.state.stock_provider = stock_provider
    app.state.technical_indicator_service = TechnicalIndicatorService()
    app.state.stock_prediction_service = StockPredictionService(
        provider=stock_provider,
        indicator_service=app.state.technical_indicator_service,
        db_session_factory=AsyncSessionLocal,
    )


    # Validate stock model artifacts at startup
    artifact_loader = get_stock_artifact_loader()
    if not artifact_loader.validate_artifacts_exist():
        logger.warning(
            "Stock ML model artifacts incomplete in %s. Stock predictions may fail.",
            settings.STOCK_MODEL_DIR,
        )

    # Asynchronously warm up the stock market snapshot in the background without blocking server startup
    async def _warmup_market_snapshot() -> None:
        try:
            logger.info("Starting background market snapshot cache warm-up...")
            items = await app.state.stock_prediction_service.get_market_snapshot()
            logger.info("Market snapshot warm-up completed successfully (%d items cached).", len(items))
        except Exception as e:
            logger.warning("Background market snapshot warm-up skipped/failed: %s", e)

    warmup_task = asyncio.create_task(_warmup_market_snapshot())

    # Pre-warm full analysis cache for the 10 most-visited Nifty stocks.
    # This eliminates the cold yfinance fetch delay for the most common user requests.
    _TOP_STOCKS_TO_PREWARM = [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
        "BHARTIARTL", "SBIN", "HCLTECH", "WIPRO", "AXISBANK",
    ]

    async def _prewarm_top_stock_analysis() -> None:
        from app.api.v1.stocks import _full_analysis_cache, _ANALYSIS_CACHE_TTL
        import time as _time
        import pandas as pd

        svc = app.state.stock_prediction_service
        ind_svc = app.state.technical_indicator_service

        logger.info("Starting background analysis pre-warm for top %d stocks...", len(_TOP_STOCKS_TO_PREWARM))

        async def _prewarm_one(sym: str) -> None:
            cache_key = f"{sym}_1y"
            now = _time.time()
            if cache_key in _full_analysis_cache:
                cached_resp, cached_time = _full_analysis_cache[cache_key]
                if now - cached_time < _ANALYSIS_CACHE_TTL:
                    return  # already warm

            try:
                prices_df = await svc.provider.get_historical_prices(sym, period="1y")
                pred_res = await svc.predict_stock_movement(symbol=sym, prices_df=prices_df)
                pred_res.pop("prices_df", None)

                enriched_df = ind_svc.compute_all_indicators(prices_df)
                tech_summary = ind_svc.extract_summary(enriched_df)

                historical_chart_data = []
                for _, row in enriched_df.iterrows():
                    dt_str = str(pd.to_datetime(row["Date"]).strftime("%Y-%m-%d")) if "Date" in row else ""
                    close_val = round(float(row.get("Close", 0.0)), 2)
                    historical_chart_data.append({
                        "date": dt_str,
                        "price": close_val,
                        "open": round(float(row.get("Open", close_val)), 2),
                        "high": round(float(row.get("High", close_val)), 2),
                        "low": round(float(row.get("Low", close_val)), 2),
                        "close": close_val,
                        "volume": round(float(row.get("Volume", 0.0)), 2),
                        "sma20": round(float(row["SMA20"]), 2) if ("SMA20" in row and not pd.isna(row["SMA20"]) and float(row["SMA20"]) > 0) else None,
                        "sma50": round(float(row["SMA50"]), 2) if ("SMA50" in row and not pd.isna(row["SMA50"]) and float(row["SMA50"]) > 0) else None,
                        "sma200": round(float(row["SMA200"]), 2) if ("SMA200" in row and not pd.isna(row["SMA200"]) and float(row["SMA200"]) > 0) else None,
                        "rsi": round(float(row["RSI"]), 2) if ("RSI" in row and not pd.isna(row["RSI"])) else None,
                        "macd": round(float(row["MACD"]), 4) if ("MACD" in row and not pd.isna(row["MACD"])) else None,
                        "macd_signal": round(float(row["MACD_SIGNAL"]), 4) if ("MACD_SIGNAL" in row and not pd.isna(row["MACD_SIGNAL"])) else None,
                        "macd_hist": round(float(row["MACD_HIST"]), 4) if ("MACD_HIST" in row and not pd.isna(row["MACD_HIST"])) else None,
                        "upper_band": round(float(row["BB_UPPER"]), 2) if ("BB_UPPER" in row and not pd.isna(row["BB_UPPER"]) and float(row["BB_UPPER"]) > 0) else None,
                        "middle_band": round(float(row["BB_MIDDLE"]), 2) if ("BB_MIDDLE" in row and not pd.isna(row["BB_MIDDLE"]) and float(row["BB_MIDDLE"]) > 0) else None,
                        "lower_band": round(float(row["BB_LOWER"]), 2) if ("BB_LOWER" in row and not pd.isna(row["BB_LOWER"]) and float(row["BB_LOWER"]) > 0) else None,
                    })

                from app.schemas.stocks import StockFullAnalysisResponse, TechnicalSummarySchema
                response = StockFullAnalysisResponse(
                    symbol=sym,
                    company_name=pred_res["company_name"],
                    period="1y",
                    as_of_date=pred_res["as_of_date"],
                    current_close=pred_res["current_close"],
                    price_change=pred_res.get("price_change", 0.0),
                    price_change_percent=pred_res.get("price_change_percent", 0.0),
                    prediction=pred_res["prediction"],
                    technical_indicators=TechnicalSummarySchema(**tech_summary),
                    top_influencing_features=pred_res["top_influencing_features"],
                    sentiment_source=pred_res["sentiment_source"],
                    price_history=pred_res.get("price_history", []),
                    historical_chart_data=historical_chart_data,
                )
                _full_analysis_cache[cache_key] = (response, _time.time())
                logger.info("[PreWarm] Cached analysis for %s", sym)
            except Exception as e:
                logger.debug("[PreWarm] Skipped %s: %s", sym, e)

        # Fire all 10 concurrently so total wait = slowest single stock, not sum of all
        await asyncio.gather(*[_prewarm_one(s) for s in _TOP_STOCKS_TO_PREWARM], return_exceptions=True)
        logger.info("[PreWarm] Top stock analysis pre-warm complete.")

    prewarm_analysis_task = asyncio.create_task(_prewarm_top_stock_analysis())


    logger.info(
        "GlobalPulse startup complete. Providers: FinnhubMarketProvider, "
        "TradingEconomicsProvider, NewsApiProvider, StockMarketProvider (%s). Phase 1–6 Ready.",
        settings.STOCK_PROVIDER,
    )

    yield  # Application is running

    # Shutdown — cancel warmup if still running, and close all HTTP clients
    logger.info("GlobalPulse shutting down...")
    if not warmup_task.done():
        warmup_task.cancel()
    if not prewarm_analysis_task.done():
        prewarm_analysis_task.cancel()

    await finnhub_provider.close()
    await te_provider.close()
    await news_provider.close()
    await stock_provider.close()
    logger.info("GlobalPulse shutdown complete.")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    # ── C-2: Disable API docs in production ───────────────────────────
    # Swagger UI and OpenAPI schema expose the complete attack surface.
    # Hide them in staging/production; keep accessible in development.
    _is_dev = settings.APP_ENV == "development"
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        description=(
            "GlobalPulse Backend — India-centric global financial intelligence platform.\n\n"
            "**Phase 1A–1C**: Backend foundation, Finnhub market data integration, "
            "and international timezone/market-session engine.\n\n"
            "**Phase 1D**: Economic & macro data via Trading Economics — "
            "economic calendar, commodities, forex, government bond yields.\n\n"
            "**Phase 1E**: News & global event data via NewsAPI — "
            "rule-based event classification, country/company tagging, "
            "financial relevance filtering.\n\n"
            "All timestamps are returned in both UTC and IST (Asia/Kolkata)."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs" if _is_dev else None,
        redoc_url="/redoc" if _is_dev else None,
        openapi_url="/openapi.json" if _is_dev else None,
        lifespan=lifespan,
    )

    # ── C-3: Rate limiting via slowapi ────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Register global exception handlers before routes ─────────────
    register_exception_handlers(app)

    # ── Middleware stack (registered in reverse order of processing) ───
    # Add innermost middleware first; last registered = outermost = first to
    # process the request and last to process the response.

    # H-2: Request body size enforcement (innermost — runs after routing)
    app.add_middleware(
        MaxBodySizeMiddleware,
        max_bytes=settings.MAX_BODY_SIZE_BYTES,
    )

    # H-4: Request / correlation ID tracing
    app.add_middleware(RequestIDMiddleware)

    # H-1: Security response headers
    app.add_middleware(SecurityHeadersMiddleware, app_env=settings.APP_ENV)

    # C-1: CORS — explicit origin list in staging/production
    # In development: permit localhost dev-server origins only.
    # In staging/production: use ALLOWED_ORIGINS from settings.
    if _is_dev:
        cors_origins = ["*"]
    else:
        cors_origins = settings.ALLOWED_ORIGINS

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True if not _is_dev and cors_origins else False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Accept", "Origin"],
    )

    # H-5: Trusted host enforcement (outermost — first to process request)
    # Development uses ["*"] wildcard to allow the Starlette test client,
    # local dev servers, and other tooling without configuration.
    allowed_hosts = ["*"] if _is_dev else settings.ALLOWED_HOSTS
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    # Mount auth router from Final_Frontend (/api/auth)
    from app.auth_routes import router as auth_router
    app.include_router(auth_router)

    # Mount versioned API router (/api/v1)
    app.include_router(v1_router)

    return app


app = create_app()
