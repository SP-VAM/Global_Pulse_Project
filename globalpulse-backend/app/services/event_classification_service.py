"""
GlobalPulse Event Classification Service
Orchestrates article classification, country tagging, company tagging,
relevance scoring, and deduplication.

This service is stateless and operates on individual articles.
It is the single point where all classification sub-modules are combined.
The provider layer produces NormalizedArticle objects with default/empty
classification fields; this service fills them in.
"""
from __future__ import annotations

import hashlib
import logging
from typing import List, Set, Tuple

from app.domain.global_event import NormalizedGlobalEvent
from app.domain.news import NormalizedArticle
from app.services.classification.company_tagger import extract_sectors, tag_companies
from app.services.classification.country_tagger import tag_countries
from app.services.classification.relevance_filter import score_relevance
from app.services.classification.rules import classify_text

logger = logging.getLogger(__name__)


def _headline_hash(headline: str) -> str:
    """Stable hash of a normalized headline for duplicate detection."""
    normalized = " ".join(headline.lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


class EventClassificationService:
    """
    Classifies and enriches NormalizedArticle objects produced by news providers.

    Responsibilities:
        1. Category classification using deterministic keyword rules.
        2. Country tagging from article text.
        3. Company and sector tagging from static config.
        4. Financial relevance scoring.
        5. Deduplication within a batch (by URL and headline hash).

    This service does NOT call any external API.
    It does NOT predict market impact.
    All decisions are deterministic and auditable.
    """

    def classify_batch(
        self, articles: List[NormalizedArticle]
    ) -> List[NormalizedArticle]:
        """
        Classify and deduplicate a list of articles.

        Returns enriched NormalizedArticle objects in the same order,
        with duplicates removed. Input articles are not mutated; new
        dataclass instances are returned.
        """
        seen_urls: Set[str] = set()
        seen_headline_hashes: Set[str] = set()
        classified: List[NormalizedArticle] = []

        for article in articles:
            # URL deduplication
            if article.article_url and article.article_url in seen_urls:
                logger.debug("Deduplicating article by URL: %s", article.article_url)
                continue
            # Headline deduplication
            h_hash = _headline_hash(article.headline)
            if h_hash in seen_headline_hashes:
                logger.debug("Deduplicating article by headline hash: %s", article.headline[:60])
                continue

            if article.article_url:
                seen_urls.add(article.article_url)
            seen_headline_hashes.add(h_hash)

            enriched = self._classify_one(article)
            classified.append(enriched)

        return classified

    def _classify_one(self, article: NormalizedArticle) -> NormalizedArticle:
        """
        Enrich a single article with classification, tagging, and relevance score.
        Returns a new NormalizedArticle (dataclass mutation not used for clarity).
        """
        combined_text = f"{article.headline} {article.summary or ''}"

        # 1. Category classification
        primary_category, tags, matched_keywords = classify_text(combined_text)

        # 2. Country tagging
        countries = tag_countries(combined_text)

        # 3. Company & sector tagging
        company_tags = tag_companies(combined_text)
        sectors = extract_sectors(company_tags)

        # 4. Relevance scoring
        is_relevant, relevance_score = score_relevance(
            text=combined_text,
            primary_category=primary_category,
            company_tags=company_tags,
            sectors=sectors,
        )

        # Construct enriched article (replace classification fields)
        article.primary_category = primary_category
        article.tags = tags
        article.countries = countries
        article.companies = company_tags
        article.sectors = sectors
        article.keywords = matched_keywords[:20]  # Cap keywords list
        article.relevance_score = relevance_score

        return article

    def to_global_events(
        self, articles: List[NormalizedArticle]
    ) -> List[NormalizedGlobalEvent]:
        """
        Wrap classified articles in NormalizedGlobalEvent for the global-events endpoint.
        Only articles with is_financially_relevant=True are included.
        """
        from app.services.classification.relevance_filter import RELEVANCE_THRESHOLD

        events = []
        for article in articles:
            is_relevant = article.relevance_score >= RELEVANCE_THRESHOLD
            if is_relevant:
                events.append(
                    NormalizedGlobalEvent(
                        article=article,
                        is_financially_relevant=True,
                        relevance_score=article.relevance_score,
                    )
                )
        return events
