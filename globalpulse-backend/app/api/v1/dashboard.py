"""
GlobalPulse Dashboard API Router
Provides GET /api/v1/dashboard and GET /api/v1/dashboard/search
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status

from app.api.v1.dependencies import get_dashboard_service
from app.api.v1.limiter import limiter
from app.core.config import get_settings
from app.schemas.dashboard import DashboardResponse, DashboardSortOrder
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

_settings = get_settings()


@router.get(
    "",
    response_model=DashboardResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Get GlobalPulse Dashboard Feed",
    description=(
        "Main Dashboard endpoint aggregating market news, financial developments, "
        "and global events. Supports filtering by category, country, company, sector, "
        "type, date range, sorting (latest/oldest), and pagination."
    ),
)
@limiter.limit(_settings.RATE_LIMIT_LIST)
async def get_dashboard(
    request: Request,
    category: Optional[str] = Query(None, max_length=60, description="Filter by event/news category (e.g. GEOPOLITICS, FINANCIAL_MARKETS)"),
    country: Optional[str] = Query(None, max_length=60, description="Filter by ISO country code or country name (e.g. Singapore, SG)"),
    company: Optional[str] = Query(None, max_length=100, description="Filter by company tag or symbol (e.g. Apple, AAPL)"),
    sector: Optional[str] = Query(None, max_length=60, description="Filter by industry sector (e.g. Technology, Energy)"),
    type: Optional[str] = Query(None, max_length=30, description="Filter by item type (NEWS | GLOBAL_EVENT)"),
    from_date: Optional[date] = Query(None, alias="from", description="Publication date range start (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, alias="to", description="Publication date range end (YYYY-MM-DD)"),
    sort: DashboardSortOrder = Query(DashboardSortOrder.LATEST, description="Sort order: 'latest' (default) or 'oldest'"),
    page: int = Query(1, ge=1, description="1-indexed page number"),
    pageSize: int = Query(20, ge=1, le=100, alias="pageSize", description="Items per page (max 100)"),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    return await dashboard_service.get_dashboard(
        category=category,
        country=country,
        company=company,
        sector=sector,
        item_type=type,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=pageSize,
        sort=sort.value,
    )


@router.get(
    "/search",
    response_model=DashboardResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Search Dashboard Content",
    description=(
        "Search normalized Dashboard content matching a free-text query string. "
        "Searches headline, summary, category, country, company, and sector tags."
    ),
)
@limiter.limit(_settings.RATE_LIMIT_LIST)
async def search_dashboard(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200, description="Search query string (e.g. 'oil', 'semiconductor')"),
    category: Optional[str] = Query(None, max_length=60, description="Filter search results by category"),
    country: Optional[str] = Query(None, max_length=60, description="Filter search results by country"),
    company: Optional[str] = Query(None, max_length=100, description="Filter search results by company"),
    sector: Optional[str] = Query(None, max_length=60, description="Filter search results by sector"),
    type: Optional[str] = Query(None, max_length=30, description="Filter search results by item type (NEWS | GLOBAL_EVENT)"),
    from_date: Optional[date] = Query(None, alias="from", description="Publication date range start"),
    to_date: Optional[date] = Query(None, alias="to", description="Publication date range end"),
    sort: DashboardSortOrder = Query(DashboardSortOrder.LATEST, description="Sort order: 'latest' (default) or 'oldest'"),
    page: int = Query(1, ge=1, description="1-indexed page number"),
    pageSize: int = Query(20, ge=1, le=100, alias="pageSize", description="Items per page (max 100)"),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    return await dashboard_service.search_dashboard(
        query=q,
        category=category,
        country=country,
        company=company,
        sector=sector,
        item_type=type,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=pageSize,
        sort=sort.value,
    )
