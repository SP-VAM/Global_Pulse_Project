"""
GlobalPulse Phase 5D — AI Explanation REST API Router.
Exposes endpoints for retrieving AI shock explanations and executive natural language summaries.

Endpoints:
- GET /api/v1/anomalies/{anomaly_id}/explanation
- GET /api/v1/india-impact/anomalies/{anomaly_id}/summary
- GET /api/v1/historical/trends/narrative

Security hardening (Phase 6):
  - anomaly_id constrained to max 128 chars, alphanumeric + dash/underscore/dot
  - Rate limiting applied at 30/minute (LLM tier) for explanation endpoints
  - Silent exception swallow replaced with targeted exception handling (M-5)
"""
from datetime import date
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from app.api.v1.dependencies import (
    get_anomaly_service,
    get_correlation_service,
    get_explanation_service,
    get_historical_analytics_service,
    get_historical_store,
    get_india_impact_service,
)
from app.api.v1.limiter import limiter
from app.core.config import get_settings
from app.core.exceptions import ExplanationProviderError, GlobalPulseError
from app.domain.anomaly import AnomalyMetric, AnomalySeverity, DetectionMethod, NormalizedAnomaly
from app.domain.market import AssetType
from app.schemas.explanation import ExecutiveSummaryResponse, SectorRiskNarrativeSchema, ShockExplanationResponse
from app.services.anomaly_service import AnomalyDetectionService
from app.services.correlation_service import EventCorrelationService
from app.services.explanation_service import ExplanationService
from app.services.historical_analytics_service import HistoricalAnalyticsService
from app.services.historical_store import AbstractHistoricalSnapshotStore
from app.services.india_impact_service import IndiaImpactService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["AI Explanation & Summarization"])

_settings = get_settings()

# ---------------------------------------------------------------------------
# Path parameter constraint (H-3)
# ---------------------------------------------------------------------------
_ANOMALY_ID_PATH = Path(
    ...,
    min_length=1,
    max_length=128,
    pattern=r"^[\w\-\.]+$",
    description="Anomaly identifier (e.g. ANOM-BTC-USD-0001)",
)


def _require_explanation_service(explanation_service: Optional[ExplanationService]) -> ExplanationService:
    """Enforce required dependency semantics for explanation endpoints."""
    if not explanation_service:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ExplanationService is not configured",
        )
    return explanation_service


def _validate_date_range(from_date: Optional[date], to_date: Optional[date]) -> None:
    """Deterministic validation raising HTTP 400 if from_date is after to_date."""
    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_date cannot be after to_date",
        )


@router.get("/anomalies/{anomaly_id}/explanation", response_model=ShockExplanationResponse)
@limiter.limit(_settings.RATE_LIMIT_LLM)
async def get_anomaly_explanation(
    request: Request,
    anomaly_id: str = _ANOMALY_ID_PATH,
    explanation_service: Optional[ExplanationService] = Depends(get_explanation_service),
    anomaly_service: Optional[AnomalyDetectionService] = Depends(get_anomaly_service),
    correlation_service: Optional[EventCorrelationService] = Depends(get_correlation_service),
    india_impact_service: Optional[IndiaImpactService] = Depends(get_india_impact_service),
    historical_store: Optional[AbstractHistoricalSnapshotStore] = Depends(get_historical_store),
) -> ShockExplanationResponse:
    """
    Retrieve structured natural language shock explanation for a market anomaly.
    Lookup order:
    1. Check active in-memory anomalies first.
    2. Check historical snapshot store.
    3. Return HTTP 404 if not found in either.
    """
    svc = _require_explanation_service(explanation_service)

    anomaly: Optional[NormalizedAnomaly] = None
    impact_assessment = None
    correlated_pairs = []

    # 1. Lookup in active anomalies first
    if anomaly_service:
        anomalies, _ = anomaly_service.get_in_memory_anomalies(page_size=100)
        for a in anomalies:
            if a.id == anomaly_id:
                anomaly = a
                break

    # 2. If not active, lookup in historical snapshot store
    if not anomaly and historical_store:
        snap = historical_store.get_anomaly_snapshot_by_id(anomaly_id)
        if not snap:
            snapshots, _ = historical_store.get_anomaly_snapshots(limit=500)

            for s in snapshots:
                if s.anomaly_id == anomaly_id or s.snapshot_id == anomaly_id:
                    snap = s
                    break

        if snap:
            metric_enum = AnomalyMetric(snap.metric) if isinstance(snap.metric, str) else snap.metric
            anomaly = NormalizedAnomaly(
                id=snap.anomaly_id,
                symbol=snap.symbol,
                asset_type=snap.asset_type,
                metric=metric_enum,
                current_value=snap.current_value,
                previous_value=snap.previous_value,
                change_percent=snap.change_percent,
                observation_window="1h",
                severity=AnomalySeverity.HIGH,
                detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
                detected_at_utc=snap.detected_at_utc,
                detected_at_ist=snap.detected_at_ist,
            )

    # 3. HTTP 404 if not found in active or historical
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly with ID '{anomaly_id}' not found",
        )

    # Resolve India Impact Assessment & Correlation Pairs
    if india_impact_service:
        all_pairs = correlation_service.get_correlated_events() if (correlation_service and hasattr(correlation_service, "get_correlated_events")) else []
        anomaly_pairs = [p for p in all_pairs if p.anomaly.id == anomaly.id]
        if anomaly_pairs:
            correlated_pairs = anomaly_pairs
        # M-5: Targeted exception handling — only catch expected service/infra errors
        try:
            impact_assessment = india_impact_service.evaluate_anomaly(anomaly, correlated_pairs=correlated_pairs)
        except (GlobalPulseError, TimeoutError, OSError) as exc:
            logger.warning(
                "India impact evaluation failed for explanation | anomaly_id=%s | error=%s",
                anomaly_id,
                exc,
            )

    explanation = svc.get_shock_explanation(
        anomaly=anomaly,
        impact_assessment=impact_assessment,
        correlated_pairs=correlated_pairs,
    )

    return ShockExplanationResponse(
        explanation_id=explanation.explanation_id,
        anomaly_id=explanation.anomaly_id,
        headline_summary=explanation.headline_summary,
        root_cause_analysis=explanation.root_cause_analysis,
        transmission_mechanism_narrative=explanation.transmission_mechanism_narrative,
        sector_risk_narratives=[
            SectorRiskNarrativeSchema(
                sector_name=sec.sector_name,
                direction=sec.direction,
                risk_summary=sec.risk_summary,
            )
            for sec in explanation.sector_risk_narratives
        ],
        key_watch_metrics=list(explanation.key_watch_metrics),
        evidence_confidence_rating=explanation.evidence_confidence_rating,
        provider_type=explanation.provider_type,
        template_version=explanation.template_version,
        generated_at_utc=explanation.generated_at_utc,
        generated_at_ist=explanation.generated_at_ist,
    )


@router.get("/india-impact/anomalies/{anomaly_id}/summary", response_model=ExecutiveSummaryResponse)
@limiter.limit(_settings.RATE_LIMIT_LLM)
async def get_anomaly_executive_summary(
    request: Request,
    anomaly_id: str = _ANOMALY_ID_PATH,
    explanation_service: Optional[ExplanationService] = Depends(get_explanation_service),
    anomaly_service: Optional[AnomalyDetectionService] = Depends(get_anomaly_service),
    correlation_service: Optional[EventCorrelationService] = Depends(get_correlation_service),
    india_impact_service: Optional[IndiaImpactService] = Depends(get_india_impact_service),
    historical_store: Optional[AbstractHistoricalSnapshotStore] = Depends(get_historical_store),
) -> ExecutiveSummaryResponse:
    """
    Retrieve executive summary narrative for India impact of an anomaly.
    Lookup order:
    1. Check active in-memory anomalies first.
    2. Check historical snapshot store.
    3. Return HTTP 404 if not found in either.
    """
    svc = _require_explanation_service(explanation_service)

    anomaly: Optional[NormalizedAnomaly] = None
    impact_assessment = None

    if anomaly_service:
        anomalies, _ = anomaly_service.get_in_memory_anomalies(page_size=100)
        for a in anomalies:
            if a.id == anomaly_id:
                anomaly = a
                break

    if not anomaly and historical_store:
        snap = historical_store.get_anomaly_snapshot_by_id(anomaly_id)
        if not snap:
            snapshots, _ = historical_store.get_anomaly_snapshots(limit=500)

            for s in snapshots:
                if s.anomaly_id == anomaly_id or s.snapshot_id == anomaly_id:
                    snap = s
                    break

        if snap:
            metric_enum = AnomalyMetric(snap.metric) if isinstance(snap.metric, str) else snap.metric
            anomaly = NormalizedAnomaly(
                id=snap.anomaly_id,
                symbol=snap.symbol,
                asset_type=snap.asset_type,
                metric=metric_enum,
                current_value=snap.current_value,
                previous_value=snap.previous_value,
                change_percent=snap.change_percent,
                observation_window="1h",
                severity=AnomalySeverity.HIGH,
                detection_method=DetectionMethod.DETERMINISTIC_THRESHOLD,
                detected_at_utc=snap.detected_at_utc,
                detected_at_ist=snap.detected_at_ist,
            )

    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly with ID '{anomaly_id}' not found",
        )

    if india_impact_service:
        # M-5: Targeted exception handling instead of silent `except Exception: pass`
        try:
            impact_assessment = india_impact_service.evaluate_anomaly(anomaly)
        except (GlobalPulseError, TimeoutError, OSError) as exc:
            logger.warning(
                "India impact evaluation failed for executive summary | anomaly_id=%s | error=%s",
                anomaly_id,
                exc,
            )

    summary = svc.get_executive_summary(anomaly=anomaly, impact_assessment=impact_assessment)

    return ExecutiveSummaryResponse(
        summary_id=summary.summary_id,
        title=summary.title,
        bullet_points=list(summary.bullet_points),
        overall_sentiment=summary.overall_sentiment,
        provider_type=summary.provider_type,
        template_version=summary.template_version,
        generated_at_utc=summary.generated_at_utc,
        generated_at_ist=summary.generated_at_ist,
    )


@router.get("/historical/trends/narrative", response_model=ExecutiveSummaryResponse)
@limiter.limit(_settings.RATE_LIMIT_LLM)
async def get_historical_trends_narrative(
    request: Request,
    symbol: Optional[str] = Query(None, max_length=20, pattern=r"^[A-Za-z0-9./\-]+$", description="Filter by instrument symbol"),
    asset_type: Optional[AssetType] = Query(None, description="Filter by asset type"),
    from_date: Optional[date] = Query(None, description="Filter start date (inclusive, UTC)"),
    to_date: Optional[date] = Query(None, description="Filter end date (inclusive, UTC)"),
    explanation_service: Optional[ExplanationService] = Depends(get_explanation_service),
    analytics_service: Optional[HistoricalAnalyticsService] = Depends(get_historical_analytics_service),
) -> ExecutiveSummaryResponse:
    """
    Retrieve executive natural language summary narrative over historical trend analytics.
    Supports symbol, asset type, and UTC date window filtering.
    """
    svc = _require_explanation_service(explanation_service)
    _validate_date_range(from_date, to_date)

    trend_analytics = None
    if analytics_service:
        asset_type_str = asset_type.value if asset_type else None
        trend_analytics = analytics_service.compute_trend_analytics(
            symbol=symbol,
            asset_type=asset_type_str,
            from_date=from_date,
            to_date=to_date,
        )

    summary = svc.get_executive_summary(trend_analytics=trend_analytics)

    return ExecutiveSummaryResponse(
        summary_id=summary.summary_id,
        title=summary.title,
        bullet_points=list(summary.bullet_points),
        overall_sentiment=summary.overall_sentiment,
        provider_type=summary.provider_type,
        template_version=summary.template_version,
        generated_at_utc=summary.generated_at_utc,
        generated_at_ist=summary.generated_at_ist,
    )
