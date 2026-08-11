"""
FastAPI dependency injection for v1 routes.
Services are resolved from the application state set during lifespan.
"""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token, oauth2_scheme
from app.db.session import get_db_session
from app.db.models.user_model import UserModel
from app.repositories.user_repository import UserRepository
from app.services.anomaly_service import AnomalyDetectionService
from app.services.correlation_service import EventCorrelationService
from app.services.dashboard_service import DashboardService
from app.services.economic_service import EconomicService
from app.services.explanation_service import ExplanationService
from app.services.historical_analytics_service import HistoricalAnalyticsService
from app.services.historical_store import AbstractHistoricalSnapshotStore
from app.services.india_impact_service import IndiaImpactService
from app.services.market_service import MarketService
from app.services.market_status_service import MarketStatusService
from app.services.news_service import NewsService
from app.services.severity_service import SeverityEngineService


# ---------------------------------------------------------------------------
# Service resolver dependencies (resolved from app.state set in lifespan)
# ---------------------------------------------------------------------------


def get_market_service(request: Request) -> MarketService:
    """Resolve MarketService from app state."""
    return request.app.state.market_service


def get_market_status_service(request: Request) -> MarketStatusService:
    """Resolve MarketStatusService from app state."""
    return request.app.state.market_status_service


def get_economic_service(request: Request) -> EconomicService:
    """Resolve EconomicService from app state."""
    return request.app.state.economic_service


def get_news_service(request: Request) -> NewsService:
    """Resolve NewsService from app state."""
    return request.app.state.news_service


def get_anomaly_service(request: Request) -> AnomalyDetectionService:
    """Resolve AnomalyDetectionService from app state."""
    return getattr(request.app.state, "anomaly_service", None)


def get_correlation_service(request: Request) -> EventCorrelationService:
    """Resolve EventCorrelationService from app state."""
    return getattr(request.app.state, "correlation_service", None)


def get_severity_service(request: Request) -> SeverityEngineService:
    """Resolve SeverityEngineService from app state."""
    return getattr(request.app.state, "severity_service", None)


def get_dashboard_service(request: Request) -> DashboardService:
    """Resolve DashboardService from app state."""
    return request.app.state.dashboard_service


def get_india_impact_service(request: Request):
    """Resolve IndiaImpactService from app state."""
    return getattr(request.app.state, "india_impact_service", None)


def get_historical_store(request: Request) -> AbstractHistoricalSnapshotStore:
    """Resolve AbstractHistoricalSnapshotStore repository from app state."""
    return getattr(request.app.state, "historical_store", None)


def get_historical_analytics_service(request: Request) -> HistoricalAnalyticsService:
    """Resolve HistoricalAnalyticsService from app state."""
    return getattr(request.app.state, "historical_analytics_service", None)


def get_explanation_service(request: Request) -> ExplanationService:
    """Resolve ExplanationService from app state."""
    return getattr(request.app.state, "explanation_service", None)


# ---------------------------------------------------------------------------
# Auth dependencies — JWT token decoding and user resolution
# ---------------------------------------------------------------------------


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> UserModel:
    """FastAPI Dependency: decode JWT token and return authenticated user."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub") or payload.get("user_id") or 0)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_active_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """FastAPI Dependency: enforce active user status."""
    if current_user.account_status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")
    return current_user
