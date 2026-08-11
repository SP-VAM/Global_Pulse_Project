"""
GlobalPulse Economic Events Endpoints
GET /api/v1/economic-events
GET /api/v1/economic-events/today
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import get_economic_service
from app.domain.economic_event import EconomicEventCategory, EconomicImportance
from app.schemas.economic_event import EconomicEventListResponse, EconomicEventSchema
from app.services.economic_service import EconomicService

router = APIRouter(tags=["Economics"])


def _to_schema(event) -> EconomicEventSchema:
    return EconomicEventSchema(
        id=event.id,
        country=event.country,
        event=event.event,
        category=event.category,
        importance=event.importance,
        actual=event.actual,
        forecast=event.forecast,
        previous=event.previous,
        unit=event.unit,
        timestamp_utc=event.timestamp_utc,
        timestamp_ist=event.timestamp_ist,
        source=event.source,
    )


@router.get(
    "/economic-events",
    response_model=EconomicEventListResponse,
    summary="List economic calendar events",
    description=(
        "Retrieve global economic calendar events from Trading Economics. "
        "Events are normalized into GlobalPulse categories and importance levels. "
        "All timestamps are returned in both UTC and IST (Asia/Kolkata). "
        "\n\n**Provider note**: Availability depends on your Trading Economics subscription plan. "
        "If an endpoint is not available under your plan, a `PROVIDER_FEATURE_UNAVAILABLE` "
        "error is returned instead of fabricated data."
    ),
    responses={
        403: {"description": "Feature not available under current Trading Economics plan"},
        429: {"description": "Provider rate limit exceeded"},
        502: {"description": "Provider authentication failure"},
        503: {"description": "Trading Economics provider unavailable"},
    },
)
async def list_economic_events(
    country: Optional[str] = Query(
        None,
        description="Filter by country name e.g. 'United States', 'India'.",
    ),
    category: Optional[EconomicEventCategory] = Query(
        None,
        description="Filter by normalized event category.",
    ),
    importance: Optional[EconomicImportance] = Query(
        None,
        description="Filter by importance level: LOW, MEDIUM, HIGH.",
    ),
    from_date: Optional[date] = Query(
        None,
        alias="from",
        description="Start date (inclusive) in YYYY-MM-DD format.",
    ),
    to_date: Optional[date] = Query(
        None,
        alias="to",
        description="End date (inclusive) in YYYY-MM-DD format.",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum number of events to return.",
    ),
    service: EconomicService = Depends(get_economic_service),
) -> EconomicEventListResponse:
    events = await service.get_economic_events(
        country=country,
        category=category,
        importance=importance,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )
    return EconomicEventListResponse(
        events=[_to_schema(e) for e in events],
        total=len(events),
    )


@router.get(
    "/economic-events/today",
    response_model=EconomicEventListResponse,
    summary="Economic events for today (IST)",
    description=(
        "Returns economic calendar events for the current calendar day as seen from India "
        "(Asia/Kolkata timezone). 'Today' is computed in IST and the IST day boundaries are "
        "correctly converted to UTC for the provider query. "
        "No manual offset arithmetic is used — GlobalPulse TimezoneService handles this."
    ),
    responses={
        403: {"description": "Feature not available under current Trading Economics plan"},
        429: {"description": "Provider rate limit exceeded"},
        502: {"description": "Provider authentication failure"},
        503: {"description": "Trading Economics provider unavailable"},
    },
)
async def list_economic_events_today(
    service: EconomicService = Depends(get_economic_service),
) -> EconomicEventListResponse:
    events = await service.get_economic_events_today()
    return EconomicEventListResponse(
        events=[_to_schema(e) for e in events],
        total=len(events),
    )
