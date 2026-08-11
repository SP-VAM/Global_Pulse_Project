"""
GlobalPulse Market Status Endpoints
GET /api/v1/market-status
GET /api/v1/market-status/{exchange}
"""
from fastapi import APIRouter, Depends, Path

from app.schemas.market_status import MarketStatusResponse
from app.services.market_status_service import MarketStatusService
from app.api.v1.dependencies import get_market_status_service

router = APIRouter(tags=["Market Status"])


@router.get(
    "/market-status",
    response_model=list[MarketStatusResponse],
    summary="Get status of all supported exchanges",
    description=(
        "Returns real-time open/closed status for all GlobalPulse-supported exchanges. "
        "Status is based on exchange timezone, weekday, and configured session windows. "
        "holiday_calendar_applied=false means public holidays are NOT currently detected — "
        "an exchange may report OPEN during a public holiday (Phase 1C limitation)."
    ),
)
async def get_all_market_statuses(
    service: MarketStatusService = Depends(get_market_status_service),
) -> list[MarketStatusResponse]:
    return service.get_all_statuses()


@router.get(
    "/market-status/{exchange}",
    response_model=MarketStatusResponse,
    summary="Get status of a specific exchange",
    description=(
        "Returns the current open/closed status for a specific exchange by its code. "
        "Example: /api/v1/market-status/SGX"
    ),
)
async def get_market_status(
    exchange: str = Path(
        ...,
        description="Exchange code, e.g. 'NSE', 'NYSE', 'SGX', 'TSE', 'HKEX'.",
        examples={"sgx": {"value": "SGX"}, "nse": {"value": "NSE"}, "nyse": {"value": "NYSE"}},
    ),
    service: MarketStatusService = Depends(get_market_status_service),
) -> MarketStatusResponse:
    return service.get_status_by_exchange(exchange)
