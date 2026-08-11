"""
GlobalPulse Event Classification Rules
Deterministic keyword-based rules for classifying news articles into GlobalEventCategory.

Design principles:
  - Rules are pure data (no logic scattered in routers or providers).
  - Each category has an explicit keyword list — no regex, no AI.
  - Priority ordering determines the primary category when multiple match.
  - Keywords are matched as lowercase substrings against headline + summary combined.
  - This module is the single source of truth for classification; easy to test and extend.

Phase 1E MVP scope: rule-based foundation only.
Phase 2+: replace or augment with richer event intelligence.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from app.domain.news import GlobalEventCategory


# ---------------------------------------------------------------------------
# Keyword lists per category
# ---------------------------------------------------------------------------
# Each entry is a lowercase keyword or phrase.
# Matching is substring-based (keyword in text).
# Keep lists focused — avoid overly generic words that cause false positives.

CATEGORY_KEYWORDS: Dict[GlobalEventCategory, List[str]] = {
    GlobalEventCategory.WAR_CONFLICT: [
        # Note: keywords are matched as substrings, so keep specific enough to avoid false hits.
        # "war" is handled as a whole-word match in classify_text to avoid matching "warning".
        "[WAR_BOUNDARY]",  # placeholder — war is special-cased in classify_text
        "missile",
        "airstrike",
        "air strike",
        "military strike",
        "invasion",
        "military conflict",
        "troops",
        "ceasefire",
        "cease-fire",
        "bombardment",
        "bombing",
        "rocket attack",
        "ground offensive",
        "armed forces",
        "coalition forces",
        "drone strike",
        "shelling",
        "siege",
        "occupation",
        "regime change",
        "coup",
        "civil war",
        "insurgency",
        "guerrilla",
        "terrorist attack",
        "terrorism",
    ],
    GlobalEventCategory.NATURAL_DISASTER: [
        "earthquake",
        "flood",
        "flooding",
        "cyclone",
        "hurricane",
        "typhoon",
        "tsunami",
        "wildfire",
        "forest fire",
        "drought",
        "landslide",
        "volcanic eruption",
        "avalanche",
        "tornado",
        "heat wave",
        "heatwave",
        "extreme weather",
        "natural disaster",
        "magnitude",
        "richter",
        "seismic",
    ],
    GlobalEventCategory.CENTRAL_BANK: [
        "central bank",
        "federal reserve",
        "fed rate",
        "fed decision",
        "fomc",
        "ecb",
        "european central bank",
        "bank of japan",
        "boj",
        "bank of england",
        "boe",
        "reserve bank of india",
        "rbi",
        "people's bank of china",
        "pboc",
        "monetary policy",
        "interest rate decision",
        "rate hike",
        "rate cut",
        "quantitative easing",
        "qe",
        "tapering",
        "liquidity",
        "open market",
        "forward guidance",
        "jerome powell",
        "christine lagarde",
        "shaktikanta das",
        "governor",
    ],
    GlobalEventCategory.SUPPLY_CHAIN: [
        "supply chain",
        "port closure",
        "port disruption",
        "shipping disruption",
        "container shortage",
        "factory shutdown",
        "plant shutdown",
        "logistics disruption",
        "export restriction",
        "import ban",
        "trade embargo",
        "sanctions",
        "chip shortage",
        "semiconductor shortage",
        "inventory shortage",
        "production halt",
        "suez canal",
        "panama canal",
        "strait of hormuz",
        "chokepoint",
        "freight",
        "bulk carrier",
    ],
    GlobalEventCategory.ENERGY: [
        "crude oil",
        "oil price",
        "brent",
        "wti",
        "opec",
        "opec+",
        "natural gas",
        "lng",
        "liquefied natural gas",
        "coal",
        "refinery",
        "pipeline",
        "energy supply",
        "energy crisis",
        "blackout",
        "power cut",
        "electricity shortage",
        "nuclear plant",
        "renewable energy",
        "solar panel",
        "wind farm",
        "energy transition",
        "oil field",
        "gas field",
        "oil production",
        "energy security",
    ],
    GlobalEventCategory.GEOPOLITICS: [
        "geopolitical",
        "geopolitics",
        "diplomatic",
        "diplomat",
        "sanctions",
        "tariff",
        "trade war",
        "trade dispute",
        "bilateral",
        "multilateral",
        "nato",
        "g7",
        "g20",
        "united nations",
        "un security council",
        "imf",
        "world bank",
        "summit",
        "treaty",
        "alliance",
        "tensions",
        "espionage",
        "cyber attack",
        "hacking",
        "election interference",
        "territory dispute",
        "sovereignty",
        "blockade",
    ],
    GlobalEventCategory.CORPORATE: [
        "earnings",
        "quarterly results",
        "profit warning",
        "revenue",
        "acquisition",
        "merger",
        "takeover",
        "ipo",
        "initial public offering",
        "bankruptcy",
        "chapter 11",
        "insolvency",
        "ceo",
        "cfo",
        "layoffs",
        "job cuts",
        "restructuring",
        "spinoff",
        "dividend",
        "buyback",
        "share repurchase",
        "annual general meeting",
        "agm",
        "board",
        "shareholder",
        "listing",
        "delisting",
        "regulatory fine",
        "antitrust",
    ],
    GlobalEventCategory.ECONOMY: [
        "gdp growth",
        "gross domestic product",
        "inflation rate",
        "cpi",
        "consumer price",
        "unemployment rate",
        "jobless",
        "payrolls",
        "nonfarm",
        "trade balance",
        "current account",
        "budget deficit",
        "fiscal policy",
        "stimulus package",
        "recession",
        "economic growth",
        "economic slowdown",
        "economic crisis",
        "austerity",
        "debt ceiling",
        "sovereign debt",
        "credit rating",
        "moody's",
        "fitch rating",
        "downgrade",
    ],
    GlobalEventCategory.FINANCIAL_MARKETS: [
        "stock market",
        "stock exchange",
        "wall street",
        "dow jones",
        "s&p 500",
        "nasdaq",
        "nifty",
        "sensex",
        "nikkei",
        "hang seng",
        "dax",
        "ftse",
        "market crash",
        "market rally",
        "bull market",
        "bear market",
        "equity market",
        "bond market",
        "treasury yield",
        "yield curve",
        "forex market",
        "gold price",
        "bitcoin",
        "cryptocurrency",
        "crypto",
        "hedge fund",
        "fund manager",
        "institutional investor",
        "etf",
        "options market",
        "futures market",
    ],
    GlobalEventCategory.TECHNOLOGY: [
        "artificial intelligence",
        "ai model",
        "machine learning",
        "semiconductor",
        "chip maker",
        "data center",
        "cloud computing",
        "cybersecurity",
        "data breach",
        "tech giant",
        "big tech",
        "silicon valley",
        "startup",
        "generative ai",
        "chatgpt",
        "openai",
        "5g",
        "quantum computing",
        "space launch",
        "electric vehicle",
        "ev battery",
        "autonomous vehicle",
    ],
    # OTHER has no keywords — it's the catch-all
    GlobalEventCategory.OTHER: [],
}


# ---------------------------------------------------------------------------
# Priority order for primary category selection
# ---------------------------------------------------------------------------
# When an article matches multiple categories, the first matching category in
# this list wins as the primary. Additional matches become tags.

CATEGORY_PRIORITY: List[GlobalEventCategory] = [
    GlobalEventCategory.WAR_CONFLICT,
    GlobalEventCategory.NATURAL_DISASTER,
    GlobalEventCategory.CENTRAL_BANK,
    GlobalEventCategory.SUPPLY_CHAIN,
    GlobalEventCategory.ENERGY,
    GlobalEventCategory.GEOPOLITICS,
    GlobalEventCategory.CORPORATE,
    GlobalEventCategory.ECONOMY,
    GlobalEventCategory.FINANCIAL_MARKETS,
    GlobalEventCategory.TECHNOLOGY,
    GlobalEventCategory.OTHER,
]


import re as _re


def classify_text(text: str) -> Tuple[GlobalEventCategory, List[str], List[str]]:
    """
    Classify a piece of text (headline + summary combined) using keyword rules.

    Returns:
        primary_category: The highest-priority matching category.
        tags: Additional matching category names (beyond primary).
        matched_keywords: All keywords that fired (for transparency/debugging).

    No AI, no randomness. Fully deterministic given the same text and rules.

    Note: "war" uses word-boundary matching to avoid false hits like "warning" or "award".
    All other keywords use substring matching.
    """
    lower = text.lower()
    matched_categories: List[GlobalEventCategory] = []
    matched_keywords: List[str] = []

    # Special word-boundary keywords that cannot be simple substrings
    _WORD_BOUNDARY_KEYWORDS: dict[GlobalEventCategory, list[str]] = {
        GlobalEventCategory.WAR_CONFLICT: ["war"],
    }

    # First pass: word-boundary keywords
    for category, wb_keywords in _WORD_BOUNDARY_KEYWORDS.items():
        for kw in wb_keywords:
            pattern = r"\b" + _re.escape(kw) + r"\b"
            if _re.search(pattern, lower):
                if category not in matched_categories:
                    matched_categories.append(category)
                if kw not in matched_keywords:
                    matched_keywords.append(kw)

    # Second pass: standard substring keywords
    for category, keywords in CATEGORY_KEYWORDS.items():
        if category == GlobalEventCategory.OTHER:
            continue
        for keyword in keywords:
            # Skip placeholder entries
            if keyword.startswith("[") and keyword.endswith("]"):
                continue
            if keyword in lower:
                if category not in matched_categories:
                    matched_categories.append(category)
                if keyword not in matched_keywords:
                    matched_keywords.append(keyword)

    if not matched_categories:
        return GlobalEventCategory.OTHER, [], matched_keywords

    # Sort matched categories by priority order
    matched_categories.sort(key=lambda c: CATEGORY_PRIORITY.index(c))

    primary = matched_categories[0]
    tags = [c.value for c in matched_categories[1:]]

    return primary, tags, matched_keywords
