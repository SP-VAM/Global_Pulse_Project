"""
GlobalPulse Global Events Endpoint
GET /api/v1/global-events
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import get_news_service
from app.api.v1.news import _to_schema as _article_to_schema
from app.domain.news import GlobalEventCategory
from app.schemas.global_event import GlobalEventListResponse, GlobalEventSchema
from app.services.news_service import NewsService

router = APIRouter(tags=["Global Events"])


@router.get(
    "/global-events",
    response_model=GlobalEventListResponse,
    summary="List financially relevant global events",
    description=(
        "Returns news articles that GlobalPulse has classified as potentially financially "
        "relevant real-world events. Only articles that pass the financial relevance filter "
        "appear here — not every news story qualifies.\n\n"
        "**Relevant event types**: WAR_CONFLICT, NATURAL_DISASTER, GEOPOLITICS, SUPPLY_CHAIN, "
        "ENERGY, CENTRAL_BANK, ECONOMY, CORPORATE, FINANCIAL_MARKETS.\n\n"
        "**Important**: This endpoint does NOT predict market impact or India ripple effects. "
        "It only identifies events that are potentially relevant to financial activity. "
        "Ripple analysis is a future GlobalPulse phase.\n\n"
        "The `relevance_score` field is informational — it shows how many financial signals "
        "were detected in the article. It is NOT a market-impact prediction."
    ),
    responses={
        403: {"description": "Feature not available under current NewsAPI plan"},
        429: {"description": "NewsAPI rate limit exceeded"},
        502: {"description": "NewsAPI authentication failure"},
        503: {"description": "NewsAPI provider unavailable"},
    },
)
async def list_global_events(
    category: Optional[GlobalEventCategory] = Query(
        None,
        description="Filter by event category e.g. GEOPOLITICS, WAR_CONFLICT, ENERGY.",
    ),
    country: Optional[str] = Query(
        None,
        description="Filter by ISO 3166-1 alpha-2 country code e.g. 'IN', 'US'.",
    ),
    from_date: Optional[date] = Query(
        None,
        alias="from",
        description="Earliest publication date (YYYY-MM-DD).",
    ),
    to_date: Optional[date] = Query(
        None,
        alias="to",
        description="Latest publication date (YYYY-MM-DD).",
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)."),
    page_size: int = Query(
        20,
        alias="pageSize",
        ge=1,
        le=100,
        description="Events per page.",
    ),
    service: NewsService = Depends(get_news_service),
) -> GlobalEventListResponse:
    events = await service.get_global_events(
        category=category,
        country=country,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    return GlobalEventListResponse(
        events=[
            GlobalEventSchema(
                article=_article_to_schema(e.article),
                is_financially_relevant=e.is_financially_relevant,
                relevance_score=e.relevance_score,
            )
            for e in events
        ],
        total=len(events),
        page=page,
        page_size=page_size,
    )
