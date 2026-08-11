"""
GlobalPulse Financial Relevance Filter
Determines whether a news article is potentially relevant to financial or economic activity.

Goal:
    NOT to predict market impact — only to answer:
    "Is this article/event potentially relevant to financial or economic activity?"

Approach:
  - Scoring: each matched signal adds to a relevance score.
  - Threshold: articles with score >= RELEVANCE_THRESHOLD are considered relevant.
  - Signals are transparent and deterministic — no AI, no randomness.
  - This module is the single source of truth for relevance; easy to test and extend.

Phase 1E MVP scope: keyword + company/sector signals only.
"""
from __future__ import annotations

from typing import List, Tuple

from app.domain.news import CompanyTag, GlobalEventCategory

# ---------------------------------------------------------------------------
# Relevance threshold
# ---------------------------------------------------------------------------

RELEVANCE_THRESHOLD = 2  # Minimum score to be considered financially relevant

# ---------------------------------------------------------------------------
# Signal weights
# ---------------------------------------------------------------------------

# Categories that are inherently financially relevant (regardless of keywords)
_ALWAYS_RELEVANT_CATEGORIES = {
    GlobalEventCategory.FINANCIAL_MARKETS,
    GlobalEventCategory.ECONOMY,
    GlobalEventCategory.CENTRAL_BANK,
    GlobalEventCategory.CORPORATE,
    GlobalEventCategory.SUPPLY_CHAIN,
    GlobalEventCategory.ENERGY,
}

# Categories that are often relevant (may depend on context)
_LIKELY_RELEVANT_CATEGORIES = {
    GlobalEventCategory.WAR_CONFLICT,
    GlobalEventCategory.NATURAL_DISASTER,
    GlobalEventCategory.GEOPOLITICS,
    GlobalEventCategory.TECHNOLOGY,
}

# Financial keyword signals and their weights
_FINANCIAL_SIGNALS: list[tuple[str, int]] = [
    # High-weight financial terms
    ("stock market", 3),
    ("bond market", 3),
    ("currency", 2),
    ("interest rate", 3),
    ("inflation", 2),
    ("gdp", 2),
    ("recession", 3),
    ("monetary policy", 3),
    ("quantitative easing", 3),
    ("yield", 2),
    ("trade deficit", 2),
    ("current account", 2),
    ("export", 1),
    ("import", 1),
    ("tariff", 2),
    ("sanctions", 2),
    ("oil price", 3),
    ("crude", 2),
    ("opec", 3),
    ("energy supply", 2),
    ("supply chain", 3),
    ("shipping", 1),
    ("port", 1),
    ("logistics", 1),
    ("semiconductor", 2),
    ("chip", 1),
    ("earnings", 2),
    ("revenue", 1),
    ("profit", 1),
    ("ipo", 2),
    ("merger", 2),
    ("acquisition", 2),
    ("bankruptcy", 3),
    ("layoffs", 2),
    ("central bank", 3),
    ("federal reserve", 3),
    ("rbi", 2),
    ("ecb", 2),
    ("investment", 1),
    ("fund", 1),
    ("equity", 2),
    ("debt", 1),
    ("sovereign", 2),
    ("credit rating", 2),
    ("downgrade", 2),
    ("upgrade", 1),
    ("gold", 1),
    ("bitcoin", 1),
    ("cryptocurrency", 1),
    ("forex", 2),
    ("exchange rate", 2),
]

# Sector signals (recognized sector name → weight)
_SECTOR_WEIGHTS: dict[str, int] = {
    "Financial Services": 3,
    "Energy": 3,
    "Technology": 2,
    "Semiconductors": 3,
    "Pharmaceuticals": 2,
    "Automobile": 2,
    "Conglomerate": 2,
    "Consumer Goods": 1,
    "Logistics": 2,
    "Electric Vehicles": 2,
}


def score_relevance(
    text: str,
    primary_category: GlobalEventCategory,
    company_tags: List[CompanyTag],
    sectors: List[str],
) -> Tuple[bool, int]:
    """
    Compute a financial relevance score for an article.

    Args:
        text:             Combined headline + summary (lowercased by caller).
        primary_category: Article's primary classified category.
        company_tags:     Company tags detected in the article.
        sectors:          Unique sector names from company tags.

    Returns:
        (is_financially_relevant, relevance_score)
        is_financially_relevant is True when score >= RELEVANCE_THRESHOLD.
    """
    score = 0
    lower = text.lower()

    # Category contribution
    if primary_category in _ALWAYS_RELEVANT_CATEGORIES:
        score += 3
    elif primary_category in _LIKELY_RELEVANT_CATEGORIES:
        score += 1

    # Financial keyword signals
    for keyword, weight in _FINANCIAL_SIGNALS:
        if keyword in lower:
            score += weight

    # Company presence: any recognized company is a relevance signal
    if company_tags:
        score += min(len(company_tags) * 2, 6)  # Cap company contribution at 6

    # Sector contribution
    for sector in sectors:
        score += _SECTOR_WEIGHTS.get(sector, 0)

    is_relevant = score >= RELEVANCE_THRESHOLD
    return is_relevant, score
