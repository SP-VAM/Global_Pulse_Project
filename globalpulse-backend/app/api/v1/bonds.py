"""
GlobalPulse Bonds Endpoint
GET /api/v1/bonds
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import get_economic_service
from app.schemas.bond import BondListResponse, BondSchema
from app.services.economic_service import EconomicService

router = APIRouter(tags=["Bonds"])

_PRIORITY_BONDS_DOC = "US 10Y, India 10Y, Japan 10Y, Germany 10Y, UK 10Y"


@router.get(
    "/bonds",
    response_model=BondListResponse,
    summary="List government bond yield snapshots",
    description=(
        "Retrieve government bond yield data from Trading Economics. "
        f"Priority bonds: {_PRIORITY_BONDS_DOC}. "
        "\n\n**Important**: Bond data access depends on the Trading Economics subscription plan. "
        "If not available under the configured plan, a `PROVIDER_FEATURE_UNAVAILABLE` (403) "
        "error is returned. No fabricated data is generated."
        "\n\nyield_value is null when unavailable — never substituted with zero."
    ),
    responses={
        403: {"description": "Feature not available under current Trading Economics plan (bond data requires premium access)"},
        429: {"description": "Provider rate limit exceeded"},
        502: {"description": "Provider authentication failure"},
        503: {"description": "Trading Economics provider unavailable"},
    },
)
async def list_bonds(
    country: Optional[str] = Query(
        None,
        description="Filter by country name e.g. 'United States', 'India', 'Japan'.",
    ),
    service: EconomicService = Depends(get_economic_service),
) -> BondListResponse:
    countries: Optional[List[str]] = [country] if country else None
    bonds = await service.get_bond_yields(countries=countries)
    return BondListResponse(
        bonds=[
            BondSchema(
                symbol=b.symbol,
                name=b.name,
                country=b.country,
                maturity=b.maturity,
                yield_value=b.yield_value,
                change=b.change,
                change_percent=b.change_percent,
                timestamp_utc=b.timestamp_utc,
                timestamp_ist=b.timestamp_ist,
                source=b.source,
            )
            for b in bonds
        ],
        total=len(bonds),
    )
