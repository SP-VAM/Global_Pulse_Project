"""
GlobalPulse Dashboard Service
Orchestrates news/events processing, filtering, search, sorting, pagination,
deduplication, and optional market context quote enrichment.

Dependency direction:
    Dashboard Router → DashboardService → NewsService + MarketService (optional)
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import date, datetime, timezone
import hashlib
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.exceptions import ExplanationProviderError, GlobalPulseError, ValidationError

from app.core.timezone import TimezoneService
from app.domain.correlation import DEFAULT_MIN_CONFIDENCE, CorrelatedEventPair
from app.domain.news import GlobalEventCategory, NormalizedArticle
from app.schemas.dashboard import (
    DashboardFeedItem,
    DashboardItemType,
    DashboardResponse,
    DashboardSortOrder,
    HistoricalSummaryWidget,
    ImpactLevel,
    IndiaImpactSummaryWidget,
    MarketContextSchema,
    PaginationSchema,
)

from app.schemas.news import CompanyTagSchema
from app.services.classification.relevance_filter import RELEVANCE_THRESHOLD
from app.services.market_service import MarketService
from app.services.news_service import NewsService

logger = logging.getLogger(__name__)

# Confident static mapping from recognized company name to stock ticker
COMPANY_SYMBOL_MAP: Dict[str, str] = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Alphabet": "GOOGL",
    "Amazon": "AMZN",
    "Meta": "META",
    "Nvidia": "NVDA",
    "Intel": "INTC",
    "Tesla": "TSLA",
    "Netflix": "NFLX",
    "Infosys": "INFY",
    "Alibaba": "BABA",
}


def _headline_hash(headline: str) -> str:
    """Compute stable hash for headline deduplication."""
    normalized = " ".join(headline.lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _parse_utc_datetime(iso_str: str) -> Optional[datetime]:
    """Parse ISO timestamp string into timezone-aware datetime."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


class DashboardService:
    """
    Service layer for Dashboard operations.

    Orchestrates NewsService and MarketService to build normalized,
    frontend-friendly responses with optional quote context and India impact summaries.
    """

    def __init__(
        self,
        news_service: NewsService,
        market_service: Optional[MarketService] = None,
        anomaly_service: Optional[Any] = None,
        correlation_service: Optional[Any] = None,
        severity_service: Optional[Any] = None,
        india_impact_service: Optional[IndiaImpactService] = None,
        historical_analytics_service: Optional[Any] = None,
        explanation_service: Optional[Any] = None,
    ) -> None:
        self._news_service = news_service
        self._market_service = market_service
        self._anomaly_service = anomaly_service
        self._correlation_service = correlation_service
        self._severity_service = severity_service
        self._india_impact_service = india_impact_service
        self._historical_analytics_service = historical_analytics_service
        self._explanation_service = explanation_service

    def _build_executive_narrative(self) -> Optional[ExecutiveSummaryResponse]:
        """
        Build optional executive natural language summary widget for the main dashboard.
        Narrow Failure Isolation: Catches expected provider/service exceptions (ExplanationProviderError, GlobalPulseError, TimeoutError, OSError)
        so provider errors never fail the main Dashboard request. Programming errors surface during development.
        """
        if not self._explanation_service:
            return None

        try:
            anomalies = []
            if self._anomaly_service:
                anomalies, _ = self._anomaly_service.get_in_memory_anomalies(page_size=1)

            top_anomaly = anomalies[0] if anomalies else None
            impact_assessment = None
            if top_anomaly and self._india_impact_service:
                try:
                    impact_assessment = self._india_impact_service.evaluate_anomaly(top_anomaly)
                except Exception:
                    pass

            summary = self._explanation_service.get_executive_summary(
                anomaly=top_anomaly,
                impact_assessment=impact_assessment,
            )

            from app.schemas.explanation import ExecutiveSummaryResponse
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
        except (ExplanationProviderError, GlobalPulseError, TimeoutError, OSError) as exc:
            logger.warning("Executive narrative generation failed gracefully for dashboard: %s", exc)
            return None


    def _build_historical_summary(self) -> Optional[HistoricalSummaryWidget]:
        """
        Build aggregate historical trend summary widget for the main dashboard.
        Failure isolation: Wrapped in try-except so Historical Analytics errors never break Dashboard responses.
        """
        if not self._historical_analytics_service:
            return None

        try:
            analytics = self._historical_analytics_service.compute_trend_analytics()
            if analytics.total_anomalies_evaluated == 0 and analytics.total_impact_assessments_evaluated == 0:
                return HistoricalSummaryWidget(
                    total_anomalies_evaluated=0,
                    total_impact_assessments_evaluated=0,
                    average_impact_score=0.0,
                    peak_impact_score=0.0,
                    most_active_asset_class=None,
                    top_transmission_channel=None,
                    correlation_evidence_ratio=0.0,
                )

            most_active_asset = (
                analytics.asset_class_frequencies[0].asset_type
                if analytics.asset_class_frequencies
                else None
            )
            top_channel = (
                analytics.channel_distributions[0].channel.value
                if analytics.channel_distributions
                else None
            )

            return HistoricalSummaryWidget(
                total_anomalies_evaluated=analytics.total_anomalies_evaluated,
                total_impact_assessments_evaluated=analytics.total_impact_assessments_evaluated,
                average_impact_score=analytics.average_impact_score,
                peak_impact_score=analytics.peak_impact_score,
                most_active_asset_class=most_active_asset,
                top_transmission_channel=top_channel,
                correlation_evidence_ratio=analytics.correlation_evidence_ratio,
            )
        except Exception as exc:
            logger.warning("Historical summary generation failed for dashboard: %s", exc)
            return None


    def _build_india_impact_summary(self) -> Optional[IndiaImpactSummaryWidget]:
        """
        Build high-level India Impact summary widget for the main dashboard.
        Failure isolation: Wrapped in try-except so India Impact evaluation errors never break Dashboard responses.
        """
        if not self._india_impact_service or not self._anomaly_service:
            return None

        try:
            anomalies, _ = self._anomaly_service.get_in_memory_anomalies(page_size=100)
            if not anomalies:

                return IndiaImpactSummaryWidget(
                    total_evaluated=0,
                    high_impact_count=0,
                    medium_impact_count=0,
                    active_channels=[],
                    top_affected_sectors=[],
                    featured_assessments=[],
                )

            all_pairs = self._correlation_service.get_correlated_events() if self._correlation_service else []

            high_count = 0
            medium_count = 0
            active_channels_set: Set[TransmissionChannel] = set()
            top_sectors_set: Set[str] = set()
            featured_items: List[Tuple[Any, Any]] = []

            for anomaly in anomalies:
                matched_pairs = [p for p in all_pairs if p.anomaly.id == anomaly.id]
                assessment = self._india_impact_service.evaluate_anomaly(anomaly, correlated_pairs=matched_pairs)

                if assessment.impact_level == IndiaImpactLevel.HIGH:
                    high_count += 1
                elif assessment.impact_level == IndiaImpactLevel.MEDIUM:
                    medium_count += 1

                if assessment.impact_level in (IndiaImpactLevel.HIGH, IndiaImpactLevel.MEDIUM):
                    active_channels_set.update(assessment.transmission_channels)
                    for sec in assessment.affected_sectors:
                        top_sectors_set.add(sec.sector_name)
                    featured_items.append((anomaly, assessment))

            # Deterministic sort featured items by impact_score DESC, then detected_at_utc DESC
            featured_items.sort(key=lambda x: (x[1].impact_score, x[0].detected_at_utc), reverse=True)

            featured_responses: List[IndiaImpactResponse] = []
            for anomaly, assessment in featured_items[:5]:
                featured_responses.append(
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

            return IndiaImpactSummaryWidget(
                total_evaluated=len(anomalies),
                high_impact_count=high_count,
                medium_impact_count=medium_count,
                active_channels=sorted(list(active_channels_set)),
                top_affected_sectors=sorted(list(top_sectors_set)),
                featured_assessments=featured_responses,
            )
        except Exception as exc:
            logger.warning("India impact summary generation failed for dashboard: %s", exc)
            return None


    async def get_dashboard(
        self,
        category: Optional[str] = None,
        country: Optional[str] = None,
        company: Optional[str] = None,
        sector: Optional[str] = None,
        item_type: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
        sort: str = "latest",
    ) -> DashboardResponse:
        """
        Generate main Dashboard feed response with filtering, sorting, and pagination.
        """
        self._validate_params(page=page, page_size=page_size, from_date=from_date, to_date=to_date)

        # Parse category Enum if valid string supplied
        category_enum: Optional[GlobalEventCategory] = None
        if category:
            try:
                category_enum = GlobalEventCategory(category.upper())
            except ValueError:
                # Allow string matching if category is custom/not in enum
                pass

        # Fetch articles in a single pass from NewsService
        fetch_size = min(max(page_size * 5, 100), 200)
        articles = await self._news_service.search_news(
            query=None,
            category=category_enum,
            country=country,
            from_date=from_date,
            to_date=to_date,
            page=1,
            page_size=fetch_size,
        )

        # Apply filtering, deduplication, and sorting in service layer
        filtered_items = self._process_articles(
            articles=articles,
            category_filter=category,
            country_filter=country,
            company_filter=company,
            sector_filter=sector,
            type_filter=item_type,
            from_date=from_date,
            to_date=to_date,
            sort=sort,
        )

        return await self._build_response(filtered_items, page=page, page_size=page_size)

    async def search_dashboard(
        self,
        query: str,
        category: Optional[str] = None,
        country: Optional[str] = None,
        company: Optional[str] = None,
        sector: Optional[str] = None,
        item_type: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
        sort: str = "latest",
    ) -> DashboardResponse:
        """
        Search Dashboard content matching free-text query.
        """
        if not query or not query.strip():
            raise ValidationError("Search query parameter 'q' cannot be empty")

        clean_query = query.strip()
        self._validate_params(page=page, page_size=page_size, from_date=from_date, to_date=to_date)

        category_enum: Optional[GlobalEventCategory] = None
        if category:
            try:
                category_enum = GlobalEventCategory(category.upper())
            except ValueError:
                pass

        fetch_size = min(max(page_size * 5, 100), 200)
        raw_articles = await self._news_service.search_news(
            query=clean_query,
            category=category_enum,
            country=country,
            from_date=from_date,
            to_date=to_date,
            page=1,
            page_size=fetch_size,
        )

        # Post-process with search query substring matching across fields
        filtered_items = self._process_articles(
            articles=raw_articles,
            search_query=clean_query,
            category_filter=category,
            country_filter=country,
            company_filter=company,
            sector_filter=sector,
            type_filter=item_type,
            from_date=from_date,
            to_date=to_date,
            sort=sort,
        )

        return await self._build_response(filtered_items, page=page, page_size=page_size)

    def _validate_params(
        self,
        page: int,
        page_size: int,
        from_date: Optional[date],
        to_date: Optional[date],
    ) -> None:
        if page < 1:
            raise ValidationError("Page number must be greater than or equal to 1")
        if page_size < 1 or page_size > 100:
            raise ValidationError("Page size must be between 1 and 100")
        if from_date and to_date and from_date > to_date:
            raise ValidationError("from_date cannot be after to_date")

    def _process_articles(
        self,
        articles: List[NormalizedArticle],
        search_query: Optional[str] = None,
        category_filter: Optional[str] = None,
        country_filter: Optional[str] = None,
        company_filter: Optional[str] = None,
        sector_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        sort: str = "latest",
    ) -> List[DashboardFeedItem]:
        """
        Convert articles into DashboardFeedItems with deduplication, filtering, and sorting.
        """
        seen_urls: Set[str] = set()
        seen_hashes: Set[str] = set()
        feed_items: List[DashboardFeedItem] = []

        q_lower = search_query.lower() if search_query else None
        cat_filter_upper = category_filter.upper() if category_filter else None
        company_filter_lower = company_filter.lower() if company_filter else None
        sector_filter_lower = sector_filter.lower() if sector_filter else None
        type_filter_upper = type_filter.upper() if type_filter else None

        # Resolve country filter into ISO codes (e.g. Singapore -> SG) or uppercase string
        country_filter_codes: Set[str] = set()
        if country_filter:
            from app.services.classification.country_tagger import tag_countries
            country_filter_codes = set(tag_countries(country_filter))
            country_filter_codes.add(country_filter.upper())

        for art in articles:
            # URL and Headline deduplication
            if art.article_url in seen_urls:
                continue
            h_hash = _headline_hash(art.headline)
            if h_hash in seen_hashes:
                continue

            seen_urls.add(art.article_url)
            seen_hashes.add(h_hash)

            # Determine financial relevance & item type
            is_relevant = art.relevance_score >= RELEVANCE_THRESHOLD
            item_type = DashboardItemType.GLOBAL_EVENT if is_relevant else DashboardItemType.NEWS

            # Filter by type
            if type_filter_upper and item_type.value != type_filter_upper:
                continue

            # Filter by category
            category_val = (
                art.primary_category.value
                if isinstance(art.primary_category, GlobalEventCategory)
                else str(art.primary_category)
            )
            if cat_filter_upper and category_val.upper() != cat_filter_upper:
                continue

            # Filter by country (matches ISO code or country name)
            if country_filter_codes:
                matched_country = any(
                    c.upper() in country_filter_codes for c in art.countries
                )
                if not matched_country:
                    continue


            # Filter by company
            if company_filter_lower:
                matched_company = any(
                    company_filter_lower in comp.name.lower()
                    or company_filter_lower in COMPANY_SYMBOL_MAP.get(comp.name, "").lower()
                    for comp in art.companies
                )
                if not matched_company:
                    continue

            # Filter by sector
            if sector_filter_lower:
                matched_sector = any(
                    sector_filter_lower in sec.lower() for sec in art.sectors
                )
                if not matched_sector:
                    continue

            # Filter by date range
            pub_dt = _parse_utc_datetime(art.published_at_utc)
            if pub_dt:
                pub_d = pub_dt.date()
                if from_date and pub_d < from_date:
                    continue
                if to_date and pub_d > to_date:
                    continue

            # Free-text search match (headline, summary, tags, countries, companies, sectors)
            if q_lower:
                summary_text = art.summary.lower() if art.summary else ""
                in_headline = q_lower in art.headline.lower()
                in_summary = q_lower in summary_text
                in_category = q_lower in category_val.lower()
                in_countries = any(q_lower in c.lower() for c in art.countries)
                in_companies = any(
                    q_lower in comp.name.lower() or q_lower in comp.sector.lower()
                    for comp in art.companies
                )
                in_sectors = any(q_lower in sec.lower() for sec in art.sectors)

                if not (in_headline or in_summary or in_category or in_countries or in_companies or in_sectors):
                    continue

            # Convert CompanyTag domain objects to CompanyTagSchema
            company_schemas = [
                CompanyTagSchema(
                    name=comp.name,
                    sector=comp.sector,
                    country=comp.country,
                )
                for comp in art.companies
            ]

            # Create Dashboard feed item
            item = DashboardFeedItem(
                id=art.id,
                type=item_type,
                headline=art.headline,
                summary=art.summary,
                category=category_val,
                impact_level=ImpactLevel.UNKNOWN,  # Default UNKNOWN unless explicit provider signal
                countries=art.countries,
                companies=company_schemas,
                sectors=art.sectors,
                published_at_utc=art.published_at_utc,
                published_at_ist=art.published_at_ist,
                source_name=art.source_name,
                article_url=art.article_url,
                financially_relevant=is_relevant,
                market_context=[],
            )
            feed_items.append(item)

        # Apply Phase 2 batch correlation & presentation severity enrichment
        self._enrich_phase2_metadata(feed_items, articles)

        # Sorting
        if sort == DashboardSortOrder.OLDEST.value:
            feed_items.sort(key=lambda x: x.published_at_utc)
        else:
            # Default latest first
            feed_items.sort(key=lambda x: x.published_at_utc, reverse=True)

        return feed_items

    def _enrich_phase2_metadata(
        self, items: List[DashboardFeedItem], raw_articles: List[NormalizedArticle]
    ) -> None:
        """
        Enrich feed items with batch Phase 2 correlation metadata and presentation severity.
        Failure isolation: Wrapped in try-except block so Phase 2 failures do not break Phase 1 feed.
        """
        try:
            if not self._anomaly_service or not self._correlation_service or not self._severity_service:
                return

            active_anomalies, _ = self._anomaly_service.get_in_memory_anomalies(page=1, page_size=200)
            pairs_by_article_id: Dict[str, List[CorrelatedEventPair]] = defaultdict(list)

            if active_anomalies and raw_articles:
                for anomaly in active_anomalies:
                    pairs = self._correlation_service.correlate_all_candidates(
                        anomaly=anomaly,
                        articles=raw_articles,
                        min_confidence=DEFAULT_MIN_CONFIDENCE,
                    )
                    for p in pairs:
                        if p.article:
                            pairs_by_article_id[p.article.id].append(p)

            for item in items:
                item_pairs = pairs_by_article_id.get(item.id, [])
                impact = self._severity_service.calculate_event_impact(
                    category=item.category,
                    financially_relevant=item.financially_relevant,
                    correlated_pairs=item_pairs,
                    min_confidence=DEFAULT_MIN_CONFIDENCE,
                )
                item.impact_level = impact

                if item_pairs:
                    max_conf = max(p.confidence_score for p in item_pairs)
                    item.correlation_confidence = max_conf

                    reasons = []
                    for p in item_pairs:
                        reasons.extend(p.match_reasons)
                    item.match_reasons = list(dict.fromkeys(reasons))

                    item.correlated_anomalies = [
                        {
                            "anomalyId": p.anomaly.id,
                            "symbol": p.anomaly.symbol,
                            "assetType": p.anomaly.asset_type,
                            "metric": p.anomaly.metric,
                            "currentValue": p.anomaly.current_value,
                            "previousValue": p.anomaly.previous_value,
                            "changePercent": p.anomaly.change_percent,
                            "observationWindow": p.anomaly.observation_window,
                            "severity": p.anomaly.severity,
                            "detectionMethod": p.anomaly.detection_method,
                            "detectedAtUtc": p.anomaly.detected_at_utc,
                            "detectedAtIst": p.anomaly.detected_at_ist,
                        }
                        for p in item_pairs
                    ]
        except Exception as exc:
            logger.warning(f"Phase 2 Dashboard enrichment failed gracefully: {exc}")


    async def _build_response(
        self,
        items: List[DashboardFeedItem],
        page: int,
        page_size: int,
    ) -> DashboardResponse:
        """
        Paginate feed items, apply optional market quote enrichment, and return DashboardResponse.
        """
        total = len(items)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_items = items[start_idx:end_idx]
        has_next = end_idx < total

        # Enrich page items with optional market quotes concurrently
        if self._market_service and page_items:
            await self._enrich_market_context(page_items)

        now_utc = TimezoneService.now_utc().isoformat()
        now_ist = TimezoneService.now_ist().isoformat()

        pagination = PaginationSchema(
            page=page,
            page_size=page_size,
            total=total,
            has_next=has_next,
        )

        india_summary = self._build_india_impact_summary()
        hist_summary = self._build_historical_summary()
        exec_narrative = self._build_executive_narrative()

        return DashboardResponse(
            generated_at_utc=now_utc,
            generated_at_ist=now_ist,
            feed=page_items,
            pagination=pagination,
            india_impact_summary=india_summary,
            historical_summary=hist_summary,
            executive_narrative=exec_narrative,
        )




    async def _enrich_market_context(self, items: List[DashboardFeedItem]) -> None:
        """
        Optional lightweight market context enrichment for feed items with tagged companies.
        Bound quote calls so failures never fail the main Dashboard request.
        """
        # Collect symbols to fetch (max 3 per item, max 10 total unique per page)
        symbol_to_items: Dict[str, List[DashboardFeedItem]] = {}
        total_symbols = 0

        for item in items:
            item_symbols = 0
            for comp in item.companies:
                symbol = COMPANY_SYMBOL_MAP.get(comp.name)
                if symbol:
                    if symbol not in symbol_to_items:
                        if total_symbols >= 10:
                            break
                        symbol_to_items[symbol] = []
                        total_symbols += 1
                    symbol_to_items[symbol].append(item)
                    item_symbols += 1
                    if item_symbols >= 3:
                        break

        if not symbol_to_items:
            return

        # Fetch quotes concurrently with isolation
        async def _fetch_safe_quote(sym: str) -> Tuple[str, Optional[MarketContextSchema]]:
            try:
                quote = await self._market_service.get_quote(sym)
                if quote and quote.price is not None:
                    ctx = MarketContextSchema(
                        symbol=sym,
                        price=quote.price,
                        change_percent=quote.change_percent,
                        timestamp_utc=quote.timestamp_utc,
                        timestamp_ist=quote.timestamp_ist,
                    )
                    return sym, ctx
            except Exception as exc:
                logger.warning("Market context quote enrichment failed for %s: %s", sym, exc)
            return sym, None

        tasks = [_fetch_safe_quote(sym) for sym in symbol_to_items.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, tuple) and res[1] is not None:
                sym, ctx = res
                for item in symbol_to_items.get(sym, []):
                    # Prevent duplicate symbols in same item's market_context list
                    if not any(mc.symbol == sym for mc in item.market_context):
                        item.market_context.append(ctx)
