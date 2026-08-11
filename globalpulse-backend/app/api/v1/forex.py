"""
GlobalPulse Forex Endpoint
GET /api/v1/forex
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import get_economic_service
from app.schemas.forex import ForexListResponse, ForexPairSchema
from app.services.economic_service import EconomicService

router = APIRouter(tags=["Forex"])

_PRIORITY_PAIRS_DOC = "USD/INR, USD/JPY, USD/SGD, USD/CNY, EUR/USD, GBP/USD"


@router.get(
    "/forex",
    response_model=ForexListResponse,
    summary="List foreign exchange rate snapshots",
    description=(
        "Retrieve latest FX pair data from Trading Economics. "
        f"When no symbol filter is provided, returns priority pairs: {_PRIORITY_PAIRS_DOC}. "
        "\n\nPair availability depends on the provider subscription plan. "
        "rate is null when unavailable — never substituted with zero."
    ),
    responses={
        403: {"description": "Feature not available under current Trading Economics plan"},
        429: {"description": "Provider rate limit exceeded"},
        502: {"description": "Provider authentication failure"},
        503: {"description": "Trading Economics provider unavailable"},
    },
)
async def list_forex(
    symbol: Optional[str] = Query(
        None,
        description=(
            "Comma-separated pair symbols to filter e.g. 'USDINR,EURUSD'. "
            "When omitted, priority pairs are returned."
        ),
    ),
    service: EconomicService = Depends(get_economic_service),
) -> ForexListResponse:
    symbols: Optional[List[str]] = None
    if symbol:
        symbols = [s.strip().upper() for s in symbol.split(",") if s.strip()]

    pairs = await service.get_forex(symbols=symbols)
    return ForexListResponse(
        pairs=[
            ForexPairSchema(
                symbol=p.symbol,
                base_currency=p.base_currency,
                quote_currency=p.quote_currency,
                rate=p.rate,
                change=p.change,
                change_percent=p.change_percent,
                timestamp_utc=p.timestamp_utc,
                timestamp_ist=p.timestamp_ist,
                source=p.source,
            )
            for p in pairs
        ],
        total=len(pairs),
    )
