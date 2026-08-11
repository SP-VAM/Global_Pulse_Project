"""
GlobalPulse Instruments Endpoint
GET /api/v1/instruments/{symbol}
"""
from fastapi import APIRouter, Depends, Path

from app.schemas.instrument import InstrumentResponse
from app.services.market_service import MarketService
from app.api.v1.dependencies import get_market_service

router = APIRouter(tags=["Instruments"])


@router.get(
    "/instruments/{symbol}",
    response_model=InstrumentResponse,
    summary="Get instrument profile",
    description=(
        "Returns normalized instrument metadata for the given ticker symbol. "
        "Provider coverage depends on the Finnhub plan. "
        "Unavailable fields are returned as null, never as invented values."
    ),
)
async def get_instrument(
    symbol: str = Path(
        ...,
        description="Ticker symbol, e.g. 'AAPL', 'RELIANCE.NS'.",
        examples={"apple": {"value": "AAPL"}, "reliance": {"value": "RELIANCE.NS"}},
    ),
    service: MarketService = Depends(get_market_service),
) -> InstrumentResponse:
    instrument = await service.get_instrument(symbol)
    return InstrumentResponse(
        symbol=instrument.symbol,
        name=instrument.name,
        exchange=instrument.exchange,
        country=instrument.country,
        asset_type=instrument.asset_type.value if instrument.asset_type else None,
        currency=instrument.currency,
        timezone=instrument.timezone,
        source=instrument.source,
    )
