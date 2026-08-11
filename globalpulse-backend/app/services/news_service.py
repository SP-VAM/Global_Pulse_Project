"""
GlobalPulse News Service
Orchestrates news retrieval, classification, and global event filtering.
Routers call NewsService — never providers or classifiers directly.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from app.domain.global_event import NormalizedGlobalEvent
from app.domain.news import GlobalEventCategory, NormalizedArticle
from app.providers.base.news_provider import NewsProvider
from app.services.event_classification_service import EventClassificationService

logger = logging.getLogger(__name__)


class NewsService:
    """
    Service layer for news and global-events operations.

    Dependency direction:
        Router → NewsService → NewsProvider + EventClassificationService
    """

    def __init__(
        self,
        provider: NewsProvider,
        classifier: EventClassificationService,
    ) -> None:
        self._provider = provider
        self._classifier = classifier

    async def search_news(
        self,
        query: Optional[str] = None,
        category: Optional[GlobalEventCategory] = None,
        country: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[NormalizedArticle]:
        """
        Search for news articles, classify them, and apply optional filters.

        Classification (category, country, company, relevance) is performed on
        every article returned from the provider before filtering is applied.

        Args:
            query:     Free-text search passed to the provider.
            category:  Filter by GlobalEventCategory (post-classification).
            country:   Filter by ISO alpha-2 country code (post-tagging).
            from_date: Publication date range start.
            to_date:   Publication date range end.
            page:      1-indexed page number.
            page_size: Articles per page.
        """
        logger.info(
            "NewsService.search_news | q=%s category=%s country=%s page=%d",
            query, category, country, page,
        )

        # If category is given but no explicit query, use the category as a query hint
        effective_query = query
        if not effective_query and category and category != GlobalEventCategory.OTHER:
            effective_query = category.value.lower().replace("_", " ")

        raw_articles = await self._provider.search_news(
            query=effective_query,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )

        # Classify + deduplicate
        classified = self._classifier.classify_batch(raw_articles)

        # Post-classification filters
        if category:
            classified = [
                a for a in classified
                if a.primary_category == category or category.value in a.tags
            ]

        if country:
            upper = country.upper()
            classified = [a for a in classified if upper in a.countries]

        return classified

    async def get_global_events(
        self,
        category: Optional[GlobalEventCategory] = None,
        country: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[NormalizedGlobalEvent]:
        """
        Return financially relevant global events.

        Retrieves and classifies news, then wraps only financially relevant articles
        in NormalizedGlobalEvent. Relevance is determined by the rule-based filter.
        """
        logger.info(
            "NewsService.get_global_events | category=%s country=%s page=%d",
            category, country, page,
        )

        # Fetch more than page_size because relevance filter may reduce the count
        fetch_size = min(page_size * 3, 100)
        articles = await self.search_news(
            query=None,
            category=category,
            country=country,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=fetch_size,
        )

        return self._classifier.to_global_events(articles)
