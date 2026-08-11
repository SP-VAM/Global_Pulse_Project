"""
GlobalPulse FastAPI Router — Anomalies, Correlations, and Event Detail API.

Exposes:
  - GET /api/v1/anomalies (Critical Alerts UI)
  - GET /api/v1/anomalies/{anomaly_id}
  - GET /api/v1/correlations
  - GET /api/v1/events/{event_id}/correlation

Security hardening (Phase 6):
  - anomaly_id / event_id constrained to max 128 chars, alphanumeric + dash/underscore/dot
  - symbol Query constrained to max 20 chars, alphanumeric + ./- chars
  - /correlations page_size reduced to le=50 (expensive quadratic computation)
  - Rate limiting applied per tier from settings
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, Request

from app.api.v1.dependencies import (
    get_anomaly_service,
    get_correlation_service,
    get_economic_service,
    get_news_service,
    get_severity_service,
)
from app.api.v1.limiter import limiter
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.correlation import DEFAULT_MIN_CONFIDENCE, CorrelatedEventPair
from app.domain.economic_event import NormalizedEconomicEvent
from app.domain.news import NormalizedArticle
from app.schemas.anomaly import (
    AnomalyListResponse,
    AnomalyResponse,
    CorrelatedEventListResponse,
    CorrelatedEventResponse,
    EventCorrelationDetailResponse,
)
from app.schemas.dashboard import PaginationSchema
from app.schemas.news import ArticleSchema
from app.services.anomaly_service import AnomalyDetectionService
from app.services.correlation_service import EventCorrelationService
from app.services.economic_service import EconomicService
from app.services.news_service import NewsService
from app.services.severity_service import SeverityEngineService

router = APIRouter(tags=["Anomalies & Correlations"])

_settings = get_settings()

# ---------------------------------------------------------------------------
# Path parameter constraints (H-3)
# Anomaly IDs follow format ANOM-<SYMBOL>-<COUNTER> e.g. ANOM-BTC-USD-0001.
# Event IDs are article hashes/slugs.
# Pattern covers alphanumeric chars, dashes, underscores, and dots.
# ---------------------------------------------------------------------------
_ANOMALY_ID_PATH = Path(
    ...,
    min_length=1,
    max_length=128,
    pattern=r"^[\w\-\.]+$",
    description="Anomaly identifier (e.g. ANOM-BTC-USD-0001)",
)
_EVENT_ID_PATH = Path(
    ...,
    min_length=1,
    max_length=256,
    description="Event / article identifier",
)

# Symbol Query constraint (M-1)
_SYMBOL_QUERY = Query(
    None,
    max_length=20,
    pattern=r"^[A-Za-z0-9./\-]+$",
    description="Filter by instrument symbol e.g. BTC/USD",
)


def _map_anomaly_domain_to_schema(anomaly) -> AnomalyResponse:
    """Map internal NormalizedAnomaly to API AnomalyResponse schema."""
    return AnomalyResponse(
        anomaly_id=anomaly.id,
        symbol=anomaly.symbol,
        asset_type=anomaly.asset_type,
        metric=anomaly.metric,
        current_value=anomaly.current_value,
        previous_value=anomaly.previous_value,
        change_percent=anomaly.change_percent,
        observation_window=anomaly.observation_window,
        severity=anomaly.severity,
        detection_method=anomaly.detection_method,
        detected_at_utc=anomaly.detected_at_utc,
        detected_at_ist=anomaly.detected_at_ist,
        details=anomaly.details,
    )


def _map_article_domain_to_schema(article: NormalizedArticle) -> ArticleSchema:
    """Map internal NormalizedArticle to API ArticleSchema."""
    from app.schemas.news import CompanyTagSchema
    return ArticleSchema(
        id=article.id,
        headline=article.headline,
        summary=article.summary,
        source_name=article.source_name,
        article_url=article.article_url,
        published_at_utc=article.published_at_utc,
        published_at_ist=article.published_at_ist,
        primary_category=article.primary_category,
        countries=article.countries,
        companies=[
            CompanyTagSchema(name=c.name, sector=c.sector, country=c.country)
            for c in article.companies
        ],
        sectors=article.sectors,
        source=getattr(article, "source", article.source_name),
        financially_relevant=article.relevance_score >= 2,
    )


@router.get(
    "/anomalies",
    response_model=AnomalyListResponse,
    response_model_by_alias=True,
    summary="List detected market anomalies (Critical Alerts UI)",
)
@limiter.limit(_settings.RATE_LIMIT_LIST)
async def get_anomalies(
    request: Request,
    symbol: Optional[str] = _SYMBOL_QUERY,
    asset_type: Optional[str] = Query(None, max_length=20, description="Filter by asset class: EQUITY|COMMODITY|FOREX|BOND|CRYPTO"),
    min_change_percent: Optional[float] = Query(None, description="Minimum percentage change magnitude"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    anomaly_service: AnomalyDetectionService = Depends(get_anomaly_service),
) -> AnomalyListResponse:
    """Retrieve market anomalies detected by the Anomaly Engine."""
    domain_anomalies, total = anomaly_service.get_in_memory_anomalies(
        asset_type=asset_type,
        min_change=min_change_percent,
        symbol=symbol,
        page=page,
        page_size=page_size,
    )

    schema_anomalies = [_map_anomaly_domain_to_schema(a) for a in domain_anomalies]
    has_next = (page * page_size) < total

    return AnomalyListResponse(
        anomalies=schema_anomalies,
        pagination=PaginationSchema(
            page=page,
            page_size=page_size,
            total=total,
            has_next=has_next,
        ),
    )


@router.get(
    "/anomalies/{anomaly_id}",
    response_model=AnomalyResponse,
    response_model_by_alias=True,
    summary="Get single anomaly by ID",
)
@limiter.limit(_settings.RATE_LIMIT_LIST)
async def get_anomaly_by_id_endpoint(
    request: Request,
    anomaly_id: str = _ANOMALY_ID_PATH,
    anomaly_service: AnomalyDetectionService = Depends(get_anomaly_service),
) -> AnomalyResponse:
    """Retrieve a single detected market anomaly. Returns HTTP 404 if not found."""
    anomaly = anomaly_service.get_anomaly_by_id(anomaly_id)
    if not anomaly:
        raise NotFoundError(f"Anomaly '{anomaly_id}' not found")
    return _map_anomaly_domain_to_schema(anomaly)


@router.get(
    "/correlations",
    response_model=CorrelatedEventListResponse,
    response_model_by_alias=True,
    summary="List correlated event-anomaly pairs",
)
@limiter.limit(_settings.RATE_LIMIT_LIST)
async def get_correlations(
    request: Request,
    min_confidence: float = Query(
        DEFAULT_MIN_CONFIDENCE, ge=0.0, le=1.0, description="Minimum correlation confidence threshold (0.00 to 1.00)"
    ),
    symbol: Optional[str] = _SYMBOL_QUERY,
    page: int = Query(1, ge=1, description="Page number"),
    # M-6: Reduced from le=100 to le=50 — correlation is O(anomalies × articles) quadratic cost
    page_size: int = Query(20, ge=1, le=50, description="Items per page (max 50)"),
    anomaly_service: AnomalyDetectionService = Depends(get_anomaly_service),
    correlation_service: EventCorrelationService = Depends(get_correlation_service),
    news_service: NewsService = Depends(get_news_service),
    economic_service: EconomicService = Depends(get_economic_service),
) -> CorrelatedEventListResponse:
    """Retrieve correlated pairs linking market anomalies with news articles or economic calendar events."""
    active_anomalies, _ = anomaly_service.get_in_memory_anomalies(symbol=symbol, page=1, page_size=100)

    articles: List[NormalizedArticle] = []
    try:
        articles = await news_service.search_news(page=1, page_size=50)
    except Exception:
        articles = []

    economic_events: List[NormalizedEconomicEvent] = []
    try:
        economic_events = await economic_service.get_economic_calendar(limit=20)
    except Exception:
        economic_events = []

    all_pairs: List[CorrelatedEventPair] = []
    for anom in active_anomalies:
        pairs = correlation_service.correlate_all_candidates(
            anomaly=anom,
            articles=articles,
            economic_events=economic_events,
            min_confidence=min_confidence,
        )
        all_pairs.extend(pairs)

    # Sort all pairs by confidence score descending
    all_pairs.sort(key=lambda p: p.confidence_score, reverse=True)

    total = len(all_pairs)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_pairs = all_pairs[start_idx:end_idx]

    schema_pairs = []
    for p in paginated_pairs:
        # Construct ArticleSchema representation
        art_schema = _map_article_domain_to_schema(p.article) if p.article else ArticleSchema(
            id=p.economic_event.id if p.economic_event else "econ-event",
            headline=p.economic_event.event if p.economic_event else "Economic Release",
            summary=f"Country: {p.economic_event.country}, Importance: {p.economic_event.importance}" if p.economic_event else "",
            source_name="Trading Economics",
            article_url="https://tradingeconomics.com",
            published_at_utc=p.economic_event.timestamp_utc if p.economic_event else "",
            published_at_ist=p.economic_event.timestamp_ist if p.economic_event else "",
            primary_category=str(p.economic_event.category) if p.economic_event else "ECONOMY",
            countries=[p.economic_event.country] if p.economic_event else [],
            companies=[],
            sectors=[],
            financially_relevant=True,
        )

        schema_pairs.append(
            CorrelatedEventResponse(
                correlation_id=p.correlation_id,
                confidence_score=p.confidence_score,
                match_reasons=p.match_reasons,
                anomaly=_map_anomaly_domain_to_schema(p.anomaly),
                article=art_schema,
            )
        )

    has_next = (page * page_size) < total

    return CorrelatedEventListResponse(
        correlations=schema_pairs,
        pagination=PaginationSchema(
            page=page,
            page_size=page_size,
            total=total,
            has_next=has_next,
        ),
    )


@router.get(
    "/events/{event_id}/correlation",
    response_model=EventCorrelationDetailResponse,
    response_model_by_alias=True,
    summary="Get correlation analysis for a single news or economic event card",
)
@limiter.limit(_settings.RATE_LIMIT_LIST)
async def get_event_correlation_detail(
    request: Request,
    event_id: str = _EVENT_ID_PATH,
    min_confidence: float = Query(DEFAULT_MIN_CONFIDENCE, ge=0.0, le=1.0),
    anomaly_service: AnomalyDetectionService = Depends(get_anomaly_service),
    correlation_service: EventCorrelationService = Depends(get_correlation_service),
    severity_service: SeverityEngineService = Depends(get_severity_service),
    news_service: NewsService = Depends(get_news_service),
) -> EventCorrelationDetailResponse:
    """Retrieve detailed correlation analysis and associated anomalies for a specific event card."""
    articles: List[NormalizedArticle] = []
    try:
        articles = await news_service.search_news(page=1, page_size=100)
    except Exception:
        articles = []

    target_article: Optional[NormalizedArticle] = None
    for a in articles:
        if a.id.lower() == event_id.lower():
            target_article = a
            break

    if not target_article:
        raise NotFoundError(f"Event '{event_id}' not found")

    active_anomalies, _ = anomaly_service.get_in_memory_anomalies(page=1, page_size=100)

    matched_pairs: List[CorrelatedEventPair] = []
    for anom in active_anomalies:
        pair = correlation_service.correlate_anomaly_with_article(
            anomaly=anom, article=target_article, min_confidence=min_confidence
        )
        if pair:
            matched_pairs.append(pair)

    impact = severity_service.calculate_event_impact(
        category=target_article.primary_category.value if hasattr(target_article.primary_category, "value") else str(target_article.primary_category),
        financially_relevant=target_article.relevance_score >= 2,
        correlated_pairs=matched_pairs,
        min_confidence=min_confidence,
    )

    max_conf = max((p.confidence_score for p in matched_pairs), default=None)
    reasons = []
    for p in matched_pairs:
        reasons.extend(p.match_reasons)
    dedup_reasons = list(dict.fromkeys(reasons))

    correlated_anoms_schema = [_map_anomaly_domain_to_schema(p.anomaly) for p in matched_pairs]

    return EventCorrelationDetailResponse(
        event_id=target_article.id,
        headline=target_article.headline,
        primary_category=target_article.primary_category.value if hasattr(target_article.primary_category, "value") else str(target_article.primary_category),
        published_at_utc=target_article.published_at_utc,
        published_at_ist=target_article.published_at_ist,
        impact_level=impact.value,
        correlation_confidence=max_conf,
        match_reasons=dedup_reasons,
        correlated_anomalies=correlated_anoms_schema,
    )
