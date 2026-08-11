"""
GlobalPulse Phase 3C — India Impact REST API Router
Exposes endpoints for evaluating India market impact, shock transmission, and vulnerability models.

Security hardening (Phase 6):
  - anomaly_id constrained to max 128 chars, alphanumeric + dash/underscore/dot (H-3)
  - sector Query constrained to max 60 chars (M-1)
  - Rate limiting applied per tier from settings (C-3)
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from app.api.v1.dependencies import (
    get_anomaly_service,
    get_correlation_service,
    get_india_impact_service,
)
from app.api.v1.limiter import limiter
from app.core.config import get_settings
from app.domain.india_impact import IndiaImpactLevel, TransmissionChannel
from app.schemas.dashboard import PaginationSchema
from app.schemas.india_impact import (
    EvaluateRawShockRequest,
    IndiaImpactListResponse,
    IndiaImpactResponse,
    IndianSectorImpactSchema,
)
from app.services.anomaly_service import AnomalyDetectionService
from app.services.correlation_service import EventCorrelationService
from app.services.india_impact_service import IndiaImpactService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/india-impact", tags=["India Impact"])

_settings = get_settings()

# Path parameter constraint (H-3)
_ANOMALY_ID_PATH = Path(
    ...,
    min_length=1,
    max_length=128,
    pattern=r"^[\w\-\.]+$",
    description="Anomaly identifier (e.g. ANOM-BTC-USD-0001)",
)


def _map_level_hierarchy(min_level: Optional[IndiaImpactLevel]) -> set[IndiaImpactLevel]:
    """
    Ordered min_impact_level filter semantics:
    - HIGH -> {HIGH}
    - MEDIUM -> {MEDIUM, HIGH}
    - LOW -> {LOW, MEDIUM, HIGH}
    - NEGLIGIBLE / None -> {NEGLIGIBLE, LOW, MEDIUM, HIGH}
    """
    if min_level == IndiaImpactLevel.HIGH:
        return {IndiaImpactLevel.HIGH}
    elif min_level == IndiaImpactLevel.MEDIUM:
        return {IndiaImpactLevel.MEDIUM, IndiaImpactLevel.HIGH}
    elif min_level == IndiaImpactLevel.LOW:
        return {IndiaImpactLevel.LOW, IndiaImpactLevel.MEDIUM, IndiaImpactLevel.HIGH}
    else:
        return {
            IndiaImpactLevel.NEGLIGIBLE,
            IndiaImpactLevel.LOW,
            IndiaImpactLevel.MEDIUM,
            IndiaImpactLevel.HIGH,
        }


@router.get("", response_model=IndiaImpactListResponse)
@limiter.limit(_settings.RATE_LIMIT_LIST)
async def list_india_impacts(
    request: Request,
    min_impact_level: Optional[IndiaImpactLevel] = Query(
        None, description="Minimum impact level filter (ordered hierarchy)"
    ),
    channel: Optional[TransmissionChannel] = Query(None, description="Filter by active transmission channel"),
    # M-1: sector constrained to prevent injection via long free-text filter
    sector: Optional[str] = Query(None, max_length=60, description="Filter by affected domestic industry sector"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    anomaly_service: Optional[AnomalyDetectionService] = Depends(get_anomaly_service),
    correlation_service: Optional[EventCorrelationService] = Depends(get_correlation_service),
    india_impact_service: Optional[IndiaImpactService] = Depends(get_india_impact_service),
) -> IndiaImpactListResponse:
    """
    List and filter active market anomalies evaluated for India impact.
    Sorted deterministically by impact_score DESC, then detected_at_utc DESC before pagination.
    """
    if not india_impact_service or not anomaly_service:
        return IndiaImpactListResponse(
            items=[],
            pagination=PaginationSchema(page=1, page_size=limit, total=0, has_next=False),
        )

    # 1. Fetch active anomalies
    anomalies, _ = anomaly_service.get_in_memory_anomalies(page_size=100)

    # 2. Fetch correlated pairs if correlation service supports pair retrieval
    all_pairs = (
        correlation_service.get_correlated_events()
        if (correlation_service and hasattr(correlation_service, "get_correlated_events"))
        else []
    )

    # 3. Evaluate each anomaly
    evaluated_tuples = []
    allowed_levels = _map_level_hierarchy(min_impact_level)

    for anomaly in anomalies:
        matched_pairs = [p for p in all_pairs if p.anomaly.id == anomaly.id]
        assessment = india_impact_service.evaluate_anomaly(anomaly, correlated_pairs=matched_pairs)

        # 4. Filter checks
        if assessment.impact_level not in allowed_levels:
            continue

        if channel and channel not in assessment.transmission_channels:
            continue

        if sector:
            sector_upper = sector.upper()
            if not any(sector_upper in s.sector_name.upper() for s in assessment.affected_sectors):
                continue

        evaluated_tuples.append((anomaly, assessment))

    # 5. Deterministic sorting: impact_score DESC, detected_at_utc DESC
    evaluated_tuples.sort(
        key=lambda x: (x[1].impact_score, x[0].detected_at_utc),
        reverse=True,
    )

    total_count = len(evaluated_tuples)
    paginated_tuples = evaluated_tuples[offset : offset + limit]

    items: List[IndiaImpactResponse] = []
    for anomaly, assessment in paginated_tuples:
        items.append(
            IndiaImpactResponse(
                anomaly_id=anomaly.id,
                symbol=anomaly.symbol,
                impact_score=assessment.impact_score,
                impact_level=assessment.impact_level,
                impact_direction=assessment.impact_direction,
                capital_flow_risk=assessment.capital_flow_risk,
                transmission_channels=assessment.transmission_channels,
                affected_sectors=[
                    IndianSectorImpactSchema(
                        sector_name=s.sector_name,
                        direction=s.direction,
                        sensitivity=s.sensitivity,
                        transmission_rationale=s.transmission_rationale,
                    )
                    for s in assessment.affected_sectors
                ],
                summary_rationale=assessment.summary_rationale,
                detected_at_utc=anomaly.detected_at_utc,
                detected_at_ist=anomaly.detected_at_ist,
            )
        )

    current_page = (offset // limit) + 1
    has_next = (offset + limit) < total_count

    return IndiaImpactListResponse(
        items=items,
        pagination=PaginationSchema(
            page=current_page,
            page_size=limit,
            total=total_count,
            has_next=has_next,
        ),
    )


@router.get("/anomalies/{anomaly_id}", response_model=IndiaImpactResponse)
@limiter.limit(_settings.RATE_LIMIT_LIST)
async def get_anomaly_india_impact(
    request: Request,
    anomaly_id: str = _ANOMALY_ID_PATH,
    anomaly_service: Optional[AnomalyDetectionService] = Depends(get_anomaly_service),
    correlation_service: Optional[EventCorrelationService] = Depends(get_correlation_service),
    india_impact_service: Optional[IndiaImpactService] = Depends(get_india_impact_service),
) -> IndiaImpactResponse:
    """
    Retrieve India impact assessment for a specific market anomaly ID.
    Retrieves active correlated pairs strictly matching anomaly_id.
    """
    if not anomaly_service or not india_impact_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="India Impact service or Anomaly engine unavailable",
        )

    anomaly = anomaly_service.get_anomaly_by_id(anomaly_id)
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly with ID '{anomaly_id}' not found",
        )

    all_pairs = (
        correlation_service.get_correlated_events()
        if (correlation_service and hasattr(correlation_service, "get_correlated_events"))
        else []
    )

    matched_pairs = [p for p in all_pairs if p.anomaly.id == anomaly.id]

    assessment = india_impact_service.evaluate_anomaly(anomaly, correlated_pairs=matched_pairs)

    return IndiaImpactResponse(
        anomaly_id=anomaly.id,
        symbol=anomaly.symbol,
        impact_score=assessment.impact_score,
        impact_level=assessment.impact_level,
        impact_direction=assessment.impact_direction,
        capital_flow_risk=assessment.capital_flow_risk,
        transmission_channels=assessment.transmission_channels,
        affected_sectors=[
            IndianSectorImpactSchema(
                sector_name=s.sector_name,
                direction=s.direction,
                sensitivity=s.sensitivity,
                transmission_rationale=s.transmission_rationale,
            )
            for s in assessment.affected_sectors
        ],
        summary_rationale=assessment.summary_rationale,
        detected_at_utc=anomaly.detected_at_utc,
        detected_at_ist=anomaly.detected_at_ist,
    )


@router.post("/evaluate-shock", response_model=IndiaImpactResponse)
@limiter.limit(_settings.RATE_LIMIT_DATA)
async def evaluate_shock(
    request: Request,
    request_body: EvaluateRawShockRequest,
    india_impact_service: Optional[IndiaImpactService] = Depends(get_india_impact_service),
) -> IndiaImpactResponse:
    """
    Stateless evaluation of hypothetical or custom market shocks.
    Does not mutate or store any state.
    """
    if not india_impact_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="India Impact service unavailable",
        )

    asset_type_str = request_body.asset_type.value if request_body.asset_type else ""

    assessment = india_impact_service.evaluate_raw_shock(
        symbol=request_body.symbol,
        change_percent=request_body.change_percent,
        asset_type=asset_type_str,
    )

    return IndiaImpactResponse(
        anomaly_id=None,
        symbol=request_body.symbol,
        impact_score=assessment.impact_score,
        impact_level=assessment.impact_level,
        impact_direction=assessment.impact_direction,
        capital_flow_risk=assessment.capital_flow_risk,
        transmission_channels=assessment.transmission_channels,
        affected_sectors=[
            IndianSectorImpactSchema(
                sector_name=s.sector_name,
                direction=s.direction,
                sensitivity=s.sensitivity,
                transmission_rationale=s.transmission_rationale,
            )
            for s in assessment.affected_sectors
        ],
        summary_rationale=assessment.summary_rationale,
        detected_at_utc=None,
        detected_at_ist=None,
    )
