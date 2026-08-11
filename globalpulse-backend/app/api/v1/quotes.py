"""
GlobalPulse Quotes Endpoint
GET /api/v1/quotes/{symbol}
"""
from fastapi import APIRouter, Depends, Path

from app.schemas.quote import QuoteResponse
from app.services.market_service import MarketService
from app.api.v1.dependencies import get_market_service

router = APIRouter(tags=["Quotes"])


@router.get(
    "/quotes/{symbol}",
    response_model=QuoteResponse,
    summary="Get real-time market quote",
    description=(
        "Returns a normalized market quote for the given ticker symbol. "
        "Currency is enriched from instrument metadata; it will be null if unavailable "
        "— Finnhub's /quote endpoint does not return currency directly. "
        "Prices of 0 are returned as null to distinguish from a valid zero-price."
    ),
)
async def get_quote(
    symbol: str = Path(
        ...,
        description="Ticker symbol, e.g. 'AAPL', 'MSFT'.",
        examples={"apple": {"value": "AAPL"}, "microsoft": {"value": "MSFT"}},
    ),
    service: MarketService = Depends(get_market_service),
) -> QuoteResponse:
    quote = await service.get_quote(symbol)
    return QuoteResponse(
        symbol=quote.symbol,
        price=quote.price,
        open=quote.open,
        high=quote.high,
        low=quote.low,
        previous_close=quote.previous_close,
        change=quote.change,
        change_percent=quote.change_percent,
        currency=quote.currency,
        timestamp_utc=quote.timestamp_utc,
        timestamp_ist=quote.timestamp_ist,
        source=quote.source,
    )
