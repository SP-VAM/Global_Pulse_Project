"""
GlobalPulse FastAPI Application Entry Point
"""
from __future__ import annotations

import os
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

    sms_key = (settings.FAST2SMS_API_KEY or "").strip()
    is_sms_configured = bool(sms_key and sms_key != "YOUR_FAST2SMS_API_KEY_HERE")
    logger.info("SMS provider configured: %s", "YES" if is_sms_configured else "NO")

    smtp_user = (settings.SMTP_USER or "").strip()
    smtp_pass = (settings.SMTP_PASSWORD or "").strip()
    logger.info("SMTP_HOST configured: %s", "YES" if bool(settings.SMTP_HOST) else "NO")
    logger.info("SMTP_PORT configured: %s", "YES" if bool(settings.SMTP_PORT) else "NO")
    logger.info("SMTP_USER configured: %s", "YES" if bool(smtp_user) else "NO")
    logger.info("SMTP_PASSWORD configured: %s", "YES" if bool(smtp_pass) else "NO")
    logger.info("SMTP_FROM_EMAIL configured: %s", "YES" if bool(settings.EMAILS_FROM_EMAIL and settings.EMAILS_FROM_EMAIL.strip()) else "NO")
    logger.info("SMTP_FROM_NAME configured: %s", "YES" if bool(settings.EMAILS_FROM_NAME) else "NO")

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
        news_service=app.state.news_service,
        db_session_factory=AsyncSessionLocal,
    )


    # Check stock model artifacts at startup
    artifact_loader = get_stock_artifact_loader()
    model_download_task = None
    if artifact_loader.validate_artifacts_exist():
        logger.info(
            "Stock ML model artifacts verified on disk (%s). No download required.",
            os.path.basename(artifact_loader.model_path),
        )
    else:
        # Only download if required artifacts are actually missing
        async def _download_models_background() -> None:
            try:
                import subprocess
                loop = asyncio.get_running_loop()
                logger.info("Artifacts missing; checking & downloading from HuggingFace...")
                await loop.run_in_executor(None, subprocess.run, ["python", "scripts/download_models.py"])
                logger.info("Background ML model download check completed.")
            except Exception as e:
                logger.warning("Background ML model download skipped/failed: %s", e)

        model_download_task = asyncio.create_task(_download_models_background())


    # Warm up stock snapshot cache in background on startup
    async def _warmup_snapshot() -> None:
        try:
            await app.state.stock_prediction_service.get_market_snapshot()
            logger.info("Stock market snapshot cache pre-warmed on startup.")
        except Exception as warmup_err:
            logger.debug("Market snapshot warmup background task: %s", warmup_err)

    asyncio.create_task(_warmup_snapshot())

    # Start background Proactive Notification Scheduler Service
    from app.services.notification_scheduler_service import NotificationSchedulerService
    notif_scheduler = NotificationSchedulerService(
        stock_prediction_service=app.state.stock_prediction_service,
        poll_interval_seconds=900,  # 15 minutes
    )
    notif_scheduler.start()
    app.state.notification_scheduler = notif_scheduler

    logger.info(
        "GlobalPulse startup complete. Providers: FinnhubMarketProvider, "
        "TradingEconomicsProvider, NewsApiProvider, StockMarketProvider (%s). Phase 1–6 Ready.",
        settings.STOCK_PROVIDER,
    )

    yield  # Application is running

    # Shutdown — stop scheduler, cancel model download task if still running, and close all HTTP clients
    logger.info("GlobalPulse shutting down...")
    if hasattr(app.state, "notification_scheduler") and app.state.notification_scheduler:
        await app.state.notification_scheduler.stop()

    if model_download_task and not model_download_task.done():
        model_download_task.cancel()

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

    # C-1: CORS — permit frontend localhost (any port) and all onrender origins
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
        "https://globalpulse-frontend-axvx.onrender.com",
        "https://globalpulse-frontend-axvv.onrender.com",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"^https?:\/\/(localhost|127\.0\.0\.1)(:[0-9]+)?$|^https:\/\/.*\.onrender\.com$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # H-5: Trusted host enforcement — accept all hosts on cloud deployments
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])


    # Mount auth router from Final_Frontend (/api/auth)
    from app.auth_routes import router as auth_router
    app.include_router(auth_router)

    # Mount versioned API router (/api/v1)
    app.include_router(v1_router)

    # Root health check endpoint
    @app.get("/", summary="Root Health Check", tags=["Health"])
    async def root_health():
        return {
            "status": "healthy",
            "service": f"{settings.APP_NAME} API",
            "version": settings.APP_VERSION,
        }

    return app



app = create_app()
