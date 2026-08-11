"""
GlobalPulse Phase 4C — Historical REST API Router.
Exposes endpoints for querying historical market anomalies, India impact assessments, and trend analytics.

Endpoints:
- GET /api/v1/historical/anomalies
- GET /api/v1/historical/impacts
- GET /api/v1/historical/trends

Security hardening (Phase 6):
  - symbol Query constrained to max 20 chars, alphanumeric + ./- (M-1)
  - limit max reduced from 100 to 50 on list endpoints (M-6)
  - Rate limiting applied per tier from settings (C-3)
"""
from datetime import date
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.v1.dependencies import (
    get_historical_analytics_service,
    get_historical_store,
)
from app.api.v1.limiter import limiter
from app.core.config import get_settings
from app.domain.india_impact import IndiaImpactLevel, TransmissionChannel
from app.domain.market import AssetType
from app.schemas.historical import (
    AssetClassFrequencySchema,
    ChannelDistributionSchema,
    HistoricalAnomalyListResponse,
    HistoricalAnomalyResponse,
    HistoricalImpactListResponse,
    HistoricalImpactResponse,
    HistoricalTrendAnalyticsResponse,
    ImpactLevelCountSchema,
    SectorHitSummarySchema,
)
from app.schemas.india_impact import IndianSectorImpactSchema
from app.schemas.pagination import PaginationSchema
from app.services.historical_analytics_service import HistoricalAnalyticsService
from app.services.historical_store import AbstractHistoricalSnapshotStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/historical", tags=["Historical Data & Analytics"])

_settings = get_settings()

# Symbol Query constraint (M-1)
_SYMBOL_QUERY = Query(
    None,
    max_length=20,
    pattern=r"^[A-Za-z0-9./\-]+$",
    description="Filter by instrument symbol e.g. BRENT, USD/INR",
)


def _validate_date_range(from_date: Optional[date], to_date: Optional[date]) -> None:
    """Deterministic validation raising HTTP 400 if from_date is after to_date."""
    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_date cannot be after to_date",
        )


@router.get("/anomalies", response_model=HistoricalAnomalyListResponse)
@limiter.limit(_settings.RATE_LIMIT_LIST)
async def list_historical_anomalies(
    request: Request,
    symbol: Optional[str] = _SYMBOL_QUERY,
    asset_type: Optional[AssetType] = Query(None, description="Filter by asset type: EQUITY|COMMODITY|FOREX|BOND|CRYPTO"),
    from_date: Optional[date] = Query(None, description="Filter start date (inclusive, UTC)"),
    to_date: Optional[date] = Query(None, description="Filter end date (inclusive, UTC)"),
    # M-6: Reduced from le=100 to le=50 to limit memory enumeration
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    historical_store: Optional[AbstractHistoricalSnapshotStore] = Depends(get_historical_store),
) -> HistoricalAnomalyListResponse:
    """
    Query historical market anomaly snapshots.
    Supports UTC date windowing, symbol, asset type filtering, and pagination.
    """
    _validate_date_range(from_date, to_date)

    if not historical_store:
        return HistoricalAnomalyListResponse(
            items=[],
            pagination=PaginationSchema(page=1, page_size=limit, total=0, has_next=False),
        )

    asset_type_str = asset_type.value if asset_type else None
    snapshots, total = historical_store.get_anomaly_snapshots(
        symbol=symbol,
        asset_type=asset_type_str,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )

    items = [
        HistoricalAnomalyResponse(
            snapshot_id=s.snapshot_id,
            anomaly_id=s.anomaly_id,
            symbol=s.symbol,
            asset_type=s.asset_type,
            metric=s.metric,
            current_value=s.current_value,
            previous_value=s.previous_value,
            change_percent=s.change_percent,
            detected_at_utc=s.detected_at_utc,
            detected_at_ist=s.detected_at_ist,
            created_at_utc=s.created_at_utc,
        )
        for s in snapshots
    ]

    has_next = (offset + limit) < total
    page_num = (offset // limit) + 1 if limit > 0 else 1

    return HistoricalAnomalyListResponse(
        items=items,
        pagination=PaginationSchema(
            page=page_num,
            page_size=limit,
            total=total,
            has_next=has_next,
        ),
    )


@router.get("/impacts", response_model=HistoricalImpactListResponse)
@limiter.limit(_settings.RATE_LIMIT_LIST)
async def list_historical_impacts(
    request: Request,
    symbol: Optional[str] = _SYMBOL_QUERY,
    asset_type: Optional[AssetType] = Query(None, description="Filter by asset type"),
    channel: Optional[TransmissionChannel] = Query(None, description="Filter by active transmission channel"),
    min_impact_level: Optional[IndiaImpactLevel] = Query(None, description="Minimum impact level filter (ordered hierarchy)"),
    from_date: Optional[date] = Query(None, description="Filter start date (inclusive, UTC)"),
    to_date: Optional[date] = Query(None, description="Filter end date (inclusive, UTC)"),
    # M-6: Reduced from le=100 to le=50 to limit memory enumeration
    limit: int = Query(20, ge=1, le=50, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    historical_store: Optional[AbstractHistoricalSnapshotStore] = Depends(get_historical_store),
) -> HistoricalImpactListResponse:
    """
    Query historical India impact assessment snapshots.
    Supports ordered impact level filtering, transmission channel filtering, date range filtering, and pagination.
    """
    _validate_date_range(from_date, to_date)

    if not historical_store:
        return HistoricalImpactListResponse(
            items=[],
            pagination=PaginationSchema(page=1, page_size=limit, total=0, has_next=False),
        )

    asset_type_str = asset_type.value if asset_type else None
    snapshots, total = historical_store.get_impact_snapshots(
        symbol=symbol,
        asset_type=asset_type_str,
        channel=channel,
        min_impact_level=min_impact_level,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )

    items = [
        HistoricalImpactResponse(
            snapshot_id=s.snapshot_id,
            source_anomaly_id=s.source_anomaly_id,
            source_event_id=s.source_event_id,
            symbol=s.symbol,
            asset_type=s.asset_type,
            impact_score=s.impact_score,
            impact_level=s.impact_level,
            impact_direction=s.impact_direction,
            capital_flow_risk=s.capital_flow_risk,
            transmission_channels=list(s.transmission_channels),
            affected_sectors=[
                IndianSectorImpactSchema(
                    sector_name=sec.sector_name,
                    direction=sec.direction,
                    sensitivity=sec.sensitivity,
                    transmission_rationale=sec.transmission_rationale,
                )
                for sec in s.affected_sectors
            ],
            has_correlation_evidence=s.has_correlation_evidence,
            correlated_event_ids=list(s.correlated_event_ids),
            correlation_count=s.correlation_count,
            top_correlation_confidence=s.top_correlation_confidence,
            assessed_at_utc=s.assessed_at_utc,
            assessed_at_ist=s.assessed_at_ist,
            created_at_utc=s.created_at_utc,
        )
        for s in snapshots
    ]

    has_next = (offset + limit) < total
    page_num = (offset // limit) + 1 if limit > 0 else 1

    return HistoricalImpactListResponse(
        items=items,
        pagination=PaginationSchema(
            page=page_num,
            page_size=limit,
            total=total,
            has_next=has_next,
        ),
    )


@router.get("/trends", response_model=HistoricalTrendAnalyticsResponse)
@limiter.limit(_settings.RATE_LIMIT_LIST)
async def get_historical_trends(
    request: Request,
    symbol: Optional[str] = _SYMBOL_QUERY,
    asset_type: Optional[AssetType] = Query(None, description="Filter by asset type"),
    from_date: Optional[date] = Query(None, description="Filter start date (inclusive, UTC)"),
    to_date: Optional[date] = Query(None, description="Filter end date (inclusive, UTC)"),
    analytics_service: Optional[HistoricalAnalyticsService] = Depends(get_historical_analytics_service),
) -> HistoricalTrendAnalyticsResponse:
    """
    Retrieve aggregate time-series trend analytics over historical market shocks.
    Exhaustively calculates analytics over all matching historical snapshots.
    """
    _validate_date_range(from_date, to_date)

    if not analytics_service:
        return HistoricalTrendAnalyticsResponse(
            total_anomalies_evaluated=0,
            total_impact_assessments_evaluated=0,
            average_impact_score=0.0,
            peak_impact_score=0.0,
            impact_level_counts=[],
            asset_class_frequencies=[],
            channel_distributions=[],
            sector_hit_summaries=[],
            correlated_evidence_count=0,
            correlation_evidence_ratio=0.0,
        )

    asset_type_str = asset_type.value if asset_type else None
    domain_analytics = analytics_service.compute_trend_analytics(
        symbol=symbol,
        asset_type=asset_type_str,
        from_date=from_date,
        to_date=to_date,
    )

    return HistoricalTrendAnalyticsResponse(
        total_anomalies_evaluated=domain_analytics.total_anomalies_evaluated,
        total_impact_assessments_evaluated=domain_analytics.total_impact_assessments_evaluated,
        average_impact_score=domain_analytics.average_impact_score,
        peak_impact_score=domain_analytics.peak_impact_score,
        impact_level_counts=[
            ImpactLevelCountSchema(impact_level=ilc.impact_level, count=ilc.count)
            for ilc in domain_analytics.impact_level_counts
        ],
        asset_class_frequencies=[
            AssetClassFrequencySchema(asset_type=acf.asset_type, count=acf.count, ratio=acf.ratio)
            for acf in domain_analytics.asset_class_frequencies
        ],
        channel_distributions=[
            ChannelDistributionSchema(channel=cd.channel, count=cd.count, assessment_ratio=cd.assessment_ratio)
            for cd in domain_analytics.channel_distributions
        ],
        sector_hit_summaries=[
            SectorHitSummarySchema(
                sector_name=shs.sector_name,
                total_hits=shs.total_hits,
                negative_hits=shs.negative_hits,
                positive_hits=shs.positive_hits,
                mixed_hits=shs.mixed_hits,
                neutral_hits=shs.neutral_hits,
                primary_direction=shs.primary_direction,
            )
            for shs in domain_analytics.sector_hit_summaries
        ],
        correlated_evidence_count=domain_analytics.correlated_evidence_count,
        correlation_evidence_ratio=domain_analytics.correlation_evidence_ratio,
    )
