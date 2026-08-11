"""
GlobalPulse Company & Sector Tagger
Lightweight deterministic company detection from article text.

Approach:
  - Static mapping of ~50 well-known global companies.
  - Match company name/aliases against article text (case-insensitive).
  - Each entry has: name, aliases, sector, country.
  - Returns CompanyTag objects with sector and country enrichment.
  - Structure designed so Phase 2+ can replace the static config with a database.

Phase 1E MVP scope: static config only — do NOT expand significantly here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set

from app.domain.news import CompanyTag


@dataclass(frozen=True)
class _CompanyConfig:
    """Internal company entry in the static config."""

    name: str            # Canonical company name
    aliases: List[str]   # Alternative names / tickers to match
    sector: str          # Industry sector
    country: str         # ISO alpha-2 headquarters country


# ---------------------------------------------------------------------------
# Static company configuration (~50 globally significant companies)
# ---------------------------------------------------------------------------
# Only companies whose mention is a strong signal of corporate/sector news.
# Ordered by recognition priority (more specific → earlier).

_COMPANY_CONFIG: List[_CompanyConfig] = [
    # Technology — United States
    _CompanyConfig("Apple", ["apple inc", "apple iphone", "aapl"], "Technology", "US"),
    _CompanyConfig("Microsoft", ["microsoft", "msft", "azure"], "Technology", "US"),
    _CompanyConfig("Alphabet", ["alphabet", "google", "googl", "youtube", "deepmind"], "Technology", "US"),
    _CompanyConfig("Amazon", ["amazon", "amzn", "aws", "amazon web services"], "Technology", "US"),
    _CompanyConfig("Meta", ["meta platforms", "facebook", "instagram", "whatsapp", "meta ai"], "Technology", "US"),
    _CompanyConfig("Nvidia", ["nvidia", "nvda", "geforce", "cuda"], "Semiconductors", "US"),
    _CompanyConfig("Intel", ["intel", "intc"], "Semiconductors", "US"),
    _CompanyConfig("Tesla", ["tesla", "tsla", "elon musk"], "Electric Vehicles", "US"),
    _CompanyConfig("Netflix", ["netflix", "nflx"], "Technology", "US"),
    _CompanyConfig("OpenAI", ["openai", "chatgpt", "gpt-4", "gpt4"], "Technology", "US"),
    # Technology — Asia
    _CompanyConfig("TSMC", ["tsmc", "taiwan semiconductor", "taiwan semi"], "Semiconductors", "TW"),
    _CompanyConfig("Samsung", ["samsung", "samsung electronics"], "Technology", "KR"),
    _CompanyConfig("Sony", ["sony", "sony pictures", "playstation"], "Technology", "JP"),
    _CompanyConfig("Foxconn", ["foxconn", "hon hai", "foxconn technology"], "Technology", "TW"),
    _CompanyConfig("Alibaba", ["alibaba", "baba", "taobao", "tmall", "alipay"], "Technology", "CN"),
    _CompanyConfig("Tencent", ["tencent", "wechat", "weixin"], "Technology", "CN"),
    _CompanyConfig("Baidu", ["baidu", "ernie bot"], "Technology", "CN"),
    _CompanyConfig("Infosys", ["infosys", "infy"], "Technology", "IN"),
    _CompanyConfig("Tata Consultancy Services", ["tcs", "tata consultancy"], "Technology", "IN"),
    _CompanyConfig("Wipro", ["wipro"], "Technology", "IN"),
    _CompanyConfig("HCL Technologies", ["hcl technologies", "hcltech"], "Technology", "IN"),
    _CompanyConfig("LG", ["lg electronics", "lg display"], "Technology", "KR"),
    # Finance — Global
    _CompanyConfig("JPMorgan Chase", ["jpmorgan", "jp morgan", "jpm", "chase bank"], "Financial Services", "US"),
    _CompanyConfig("Goldman Sachs", ["goldman sachs", "goldman", "gs"], "Financial Services", "US"),
    _CompanyConfig("Morgan Stanley", ["morgan stanley", "ms"], "Financial Services", "US"),
    _CompanyConfig("BlackRock", ["blackrock"], "Financial Services", "US"),
    _CompanyConfig("HSBC", ["hsbc", "hongkong and shanghai banking"], "Financial Services", "GB"),
    _CompanyConfig("DBS Bank", ["dbs bank", "dbs group", "development bank of singapore"], "Financial Services", "SG"),
    _CompanyConfig("OCBC", ["ocbc", "ocbc bank", "oversea-chinese banking"], "Financial Services", "SG"),
    _CompanyConfig("HDFC Bank", ["hdfc bank", "hdfc"], "Financial Services", "IN"),
    _CompanyConfig("ICICI Bank", ["icici bank", "icici"], "Financial Services", "IN"),
    _CompanyConfig("State Bank of India", ["state bank of india", "sbi"], "Financial Services", "IN"),
    _CompanyConfig("Reliance Industries", ["reliance industries", "reliance jio", "mukesh ambani"], "Conglomerate", "IN"),
    # Energy — Global
    _CompanyConfig("ExxonMobil", ["exxonmobil", "exxon mobil", "exxon"], "Energy", "US"),
    _CompanyConfig("Chevron", ["chevron", "cvx"], "Energy", "US"),
    _CompanyConfig("Shell", ["shell", "royal dutch shell", "shellplc"], "Energy", "GB"),
    _CompanyConfig("BP", ["bp plc", "british petroleum"], "Energy", "GB"),
    _CompanyConfig("Saudi Aramco", ["saudi aramco", "aramco"], "Energy", "SA"),
    _CompanyConfig("TotalEnergies", ["totalenergies", "total sa"], "Energy", "FR"),
    _CompanyConfig("ONGC", ["ongc", "oil and natural gas corporation"], "Energy", "IN"),
    # Automotive — Global
    _CompanyConfig("Toyota", ["toyota", "lexus"], "Automobile", "JP"),
    _CompanyConfig("Volkswagen", ["volkswagen", "vw group", "vw ag", "audi", "porsche"], "Automobile", "DE"),
    _CompanyConfig("Hyundai", ["hyundai", "kia"], "Automobile", "KR"),
    _CompanyConfig("Tata Motors", ["tata motors", "jaguar land rover", "jlr"], "Automobile", "IN"),
    # Consumer / FMCG
    _CompanyConfig("Unilever", ["unilever"], "Consumer Goods", "GB"),
    _CompanyConfig("Nestlé", ["nestle", "nestlé"], "Consumer Goods", "CH"),
    _CompanyConfig("Procter & Gamble", ["procter & gamble", "p&g", "pampers", "tide"], "Consumer Goods", "US"),
    # Pharma
    _CompanyConfig("Pfizer", ["pfizer"], "Pharmaceuticals", "US"),
    _CompanyConfig("Moderna", ["moderna"], "Pharmaceuticals", "US"),
    _CompanyConfig("AstraZeneca", ["astrazeneca", "astra zeneca"], "Pharmaceuticals", "GB"),
    _CompanyConfig("Sun Pharma", ["sun pharma", "sun pharmaceutical"], "Pharmaceuticals", "IN"),
    # Logistics / Trade
    _CompanyConfig("Maersk", ["maersk", "ap moller maersk"], "Logistics", "DK"),
    _CompanyConfig("FedEx", ["fedex"], "Logistics", "US"),
    _CompanyConfig("UPS", ["ups", "united parcel service"], "Logistics", "US"),
]


def _build_index() -> Dict[str, _CompanyConfig]:
    """Build a lowercased alias → CompanyConfig lookup index."""
    index: Dict[str, _CompanyConfig] = {}
    for company in _COMPANY_CONFIG:
        # Index canonical name
        index[company.name.lower()] = company
        # Index each alias
        for alias in company.aliases:
            index[alias.lower()] = company
    return index


_ALIAS_INDEX: Dict[str, _CompanyConfig] = _build_index()

# Pre-sort by alias length descending for longest-match priority
_SORTED_ALIASES: List[tuple[str, _CompanyConfig]] = sorted(
    _ALIAS_INDEX.items(), key=lambda x: len(x[0]), reverse=True
)


def tag_companies(text: str) -> List[CompanyTag]:
    """
    Extract a deduplicated list of recognized company tags from article text.

    Returns:
        List of CompanyTag. Empty list when no recognized company is mentioned.
        At most one entry per company (deduplication by canonical name).
    """
    if not text:
        return []

    lower = text.lower()
    found_names: Set[str] = set()
    tags: List[CompanyTag] = []

    for alias, config in _SORTED_ALIASES:
        if config.name in found_names:
            continue
        if alias in lower:
            found_names.add(config.name)
            tags.append(
                CompanyTag(
                    name=config.name,
                    sector=config.sector,
                    country=config.country,
                )
            )

    return tags


def extract_sectors(company_tags: List[CompanyTag]) -> List[str]:
    """Return a deduplicated sorted list of sectors from matched company tags."""
    seen: Set[str] = set()
    sectors = []
    for tag in company_tags:
        if tag.sector not in seen:
            seen.add(tag.sector)
            sectors.append(tag.sector)
    return sorted(sectors)
