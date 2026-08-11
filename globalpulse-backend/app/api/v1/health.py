"""
GlobalPulse Health Endpoint
GET /api/v1/health
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.api.v1.limiter import limiter
from app.core.config import get_settings

router = APIRouter(tags=["Health"])

_settings = get_settings()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the current health status of the GlobalPulse API.",
)
@limiter.limit(_settings.RATE_LIMIT_HEALTH)
async def health_check(request: Request) -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service=_settings.APP_NAME + " API",
        version=_settings.APP_VERSION,
    )
