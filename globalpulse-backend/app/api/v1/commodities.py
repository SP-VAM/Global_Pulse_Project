"""
GlobalPulse Commodities Endpoint
GET /api/v1/commodities
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import get_economic_service
from app.domain.commodity import CommodityCategory
from app.schemas.commodity import CommodityListResponse, CommoditySchema
from app.services.economic_service import EconomicService

router = APIRouter(tags=["Commodities"])


@router.get(
    "/commodities",
    response_model=CommodityListResponse,
    summary="List commodity price snapshots",
    description=(
        "Retrieve latest commodity price data from Trading Economics. "
        "Priority commodities: Crude Oil (WTI & Brent), Gold, Silver, Natural Gas, Copper. "
        "\n\nAll numeric values come from the provider — null is returned when unavailable. "
        "Zero is never substituted for missing data."
        "\n\n**Provider note**: Availability depends on your Trading Economics subscription plan."
    ),
    responses={
        403: {"description": "Feature not available under current Trading Economics plan"},
        429: {"description": "Provider rate limit exceeded"},
        502: {"description": "Provider authentication failure"},
        503: {"description": "Trading Economics provider unavailable"},
    },
)
async def list_commodities(
    category: Optional[CommodityCategory] = Query(
        None,
        description="Filter by commodity category: ENERGY, METALS, AGRICULTURE, OTHER.",
    ),
    symbol: Optional[str] = Query(
        None,
        description="Filter by provider symbol e.g. 'WTICOILNYM', 'XAUUSD'.",
    ),
    service: EconomicService = Depends(get_economic_service),
) -> CommodityListResponse:
    commodities = await service.get_commodities(
        category=category.value if category else None,
        symbol=symbol,
    )
    return CommodityListResponse(
        commodities=[
            CommoditySchema(
                symbol=c.symbol,
                name=c.name,
                category=c.category,
                price=c.price,
                currency=c.currency,
                unit=c.unit,
                change=c.change,
                change_percent=c.change_percent,
                timestamp_utc=c.timestamp_utc,
                timestamp_ist=c.timestamp_ist,
                source=c.source,
            )
            for c in commodities
        ],
        total=len(commodities),
    )
