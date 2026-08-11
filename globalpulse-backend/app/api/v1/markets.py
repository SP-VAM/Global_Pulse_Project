"""
GlobalPulse Markets Endpoint
GET /api/v1/markets
GET /api/v1/markets?country=Singapore
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.schemas.market import ExchangeSchema, MarketListResponse, TradingSessionSchema
from app.services.market_service import MarketService
from app.api.v1.dependencies import get_market_service

router = APIRouter(tags=["Markets"])


@router.get(
    "/markets",
    response_model=MarketListResponse,
    summary="List supported exchanges",
    description=(
        "Returns metadata for all GlobalPulse-supported exchanges. "
        "Optionally filter by country name."
    ),
)
async def list_markets(
    country: Optional[str] = Query(
        None,
        description="Filter by country name (case-insensitive), e.g. 'Singapore', 'India'.",
        examples={"singapore": {"value": "Singapore"}, "india": {"value": "India"}},
    ),
    service: MarketService = Depends(get_market_service),
) -> MarketListResponse:
    exchanges = service.list_markets(country=country)
    schemas = [
        ExchangeSchema(
            exchange_code=ex.exchange_code,
            exchange_name=ex.exchange_name,
            country=ex.country,
            timezone=ex.timezone,
            currency=ex.currency,
            trading_days=ex.trading_days,
            sessions=[
                TradingSessionSchema(
                    open_time=s.open_time.strftime("%H:%M"),
                    close_time=s.close_time.strftime("%H:%M"),
                )
                for s in ex.sessions
            ],
        )
        for ex in exchanges
    ]
    return MarketListResponse(exchanges=schemas, total=len(schemas))
