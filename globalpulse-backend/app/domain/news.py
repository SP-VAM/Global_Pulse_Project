"""
GlobalPulse News & Global Event Domain Models
Internal normalized representations for news articles and classified events.
Raw provider responses are never exposed — these types form the canonical internal contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GlobalEventCategory(str, Enum):
    """
    Event classification used by GlobalPulse across the news pipeline.

    Later phases will use these categories for event detection and ripple analysis.
    Classification is deterministic and rule-based — no AI/LLM.
    """

    FINANCIAL_MARKETS = "FINANCIAL_MARKETS"
    ECONOMY = "ECONOMY"
    CENTRAL_BANK = "CENTRAL_BANK"
    CORPORATE = "CORPORATE"
    GEOPOLITICS = "GEOPOLITICS"
    WAR_CONFLICT = "WAR_CONFLICT"
    NATURAL_DISASTER = "NATURAL_DISASTER"
    SUPPLY_CHAIN = "SUPPLY_CHAIN"
    ENERGY = "ENERGY"
    TECHNOLOGY = "TECHNOLOGY"
    OTHER = "OTHER"


@dataclass(frozen=True)
class CompanyTag:
    """A recognized company mentioned in an article."""

    name: str       # Company name as in the tagging config
    sector: str     # Industry sector e.g. "Technology", "Energy"
    country: str    # Country of headquarters e.g. "United States"


@dataclass
class NormalizedArticle:
    """
    Provider-agnostic news article.

    Full article body is NOT stored — only metadata, headline, and provider-supplied
    description snippet are retained (copyright and fair-use compliance).

    primary_category: single best-fit category determined by priority scoring.
    tags: additional matched category names (for future multi-label use).
    countries: ISO 3166-1 alpha-2 codes detected from text (best-effort).
    companies: recognized company tags matched from static config.
    sectors: unique sectors derived from company tags.
    keywords: matched keyword signals (subset of classification keywords).
    relevance_score: numeric signal from relevance_filter (higher = more relevant).
    """

    id: str                                          # Stable deduplication key (URL hash)
    headline: str
    summary: Optional[str]                           # Provider description; None if absent
    source_name: str                                 # e.g. "Reuters"
    source_url: Optional[str]                        # Source homepage URL
    article_url: str                                 # Full article URL
    author: Optional[str]                            # None if not provided
    published_at_utc: str                            # ISO 8601, UTC
    published_at_ist: str                            # ISO 8601, IST / Asia/Kolkata
    primary_category: GlobalEventCategory            # Single best-fit category
    tags: list[str] = field(default_factory=list)    # Additional matched categories
    countries: list[str] = field(default_factory=list)   # ISO alpha-2 codes
    companies: list[CompanyTag] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)    # Matched classification signals
    relevance_score: int = 0
    source: str = "NEWSAPI"
