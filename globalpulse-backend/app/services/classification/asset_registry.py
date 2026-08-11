"""
GlobalPulse Centralized Asset & Macro Reference Registry
Separates true asset aliases from macro institutions and sector relationships.
Used by EventCorrelationService for deterministic asset lookup and candidate scoring.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class AssetRegistryEntry:
    """
    Centralized metadata for a tracked financial asset or symbol.

    symbol: Primary ticker code e.g. "AAPL", "BRENT", "USD/INR", "US10Y"
    canonical_name: Human-readable name
    aliases: True asset/name/ticker aliases ONLY (used for direct entity matching)
    asset_type: EQUITY | COMMODITY | FOREX | BOND | CRYPTO
    default_category: Primary event category e.g. "TECHNOLOGY", "ENERGY", "CENTRAL_BANK"
    default_sector: Optional industry sector
    country: Intrinsic national country ISO alpha-2 code (None for global commodities/crypto)
    macro_keywords: Macro institutions and terms (e.g. Fed, OPEC, RBI) for macro relevance scoring
    """

    symbol: str
    canonical_name: str
    aliases: List[str]
    asset_type: str
    default_category: str
    default_sector: Optional[str] = None
    country: Optional[str] = None
    macro_keywords: List[str] = field(default_factory=list)


# Centralized registry mapping upper-cased symbol -> AssetRegistryEntry
ASSET_REGISTRY: Dict[str, AssetRegistryEntry] = {
    "AAPL": AssetRegistryEntry(
        symbol="AAPL",
        canonical_name="Apple Inc",
        aliases=["apple inc", "apple iphone", "apple", "aapl"],
        asset_type="EQUITY",
        default_category="TECHNOLOGY",
        default_sector="Technology",
        country="US",
        macro_keywords=["tech spending", "semiconductors", "consumer tech"],
    ),
    "MSFT": AssetRegistryEntry(
        symbol="MSFT",
        canonical_name="Microsoft Corporation",
        aliases=["microsoft", "azure", "msft"],
        asset_type="EQUITY",
        default_category="TECHNOLOGY",
        default_sector="Technology",
        country="US",
        macro_keywords=["cloud computing", "enterprise software", "ai"],
    ),
    "BRENT": AssetRegistryEntry(
        symbol="BRENT",
        canonical_name="Brent Crude Oil",
        aliases=["brent crude", "brent oil", "crude oil", "brent"],
        asset_type="COMMODITY",
        default_category="ENERGY",
        default_sector="Energy",
        country=None,  # Global commodity benchmark
        macro_keywords=["opec", "oil supply", "petroleum", "energy crisis", "crude"],
    ),
    "GOLD": AssetRegistryEntry(
        symbol="GOLD",
        canonical_name="Gold Spot",
        aliases=["gold spot", "gold bullion", "xau", "gold"],
        asset_type="COMMODITY",
        default_category="COMMODITIES",
        default_sector="Mining",
        country=None,  # Global commodity benchmark
        macro_keywords=["inflation hedge", "safe haven", "precious metals", "central bank gold"],
    ),
    "US10Y": AssetRegistryEntry(
        symbol="US10Y",
        canonical_name="US 10-Year Treasury Note",
        aliases=["us 10-year treasury", "us 10y yield", "10-year treasury", "us10y"],
        asset_type="BOND",
        default_category="CENTRAL_BANK",
        default_sector="Financial Services",
        country="US",
        macro_keywords=["fed", "federal reserve", "fomc", "interest rate", "treasury yield", "monetary policy"],
    ),
    "USD/INR": AssetRegistryEntry(
        symbol="USD/INR",
        canonical_name="USD / INR Exchange Rate",
        aliases=["usd/inr", "us dollar / indian rupee", "indian rupee / usd", "usd-inr"],
        asset_type="FOREX",
        default_category="ECONOMY",
        default_sector="Financial Services",
        country=None,  # Pair spans US and IN
        macro_keywords=["rbi", "reserve bank of india", "fed", "forex reserves", "exchange rate", "rupee"],
    ),
    "BTC/USD": AssetRegistryEntry(
        symbol="BTC/USD",
        canonical_name="Bitcoin / USD",
        aliases=["bitcoin", "btc/usd", "btc"],
        asset_type="CRYPTO",
        default_category="TECHNOLOGY",
        default_sector="Cryptocurrency",
        country=None,  # Decentralized crypto asset
        macro_keywords=["crypto regulation", "blockchain", "digital asset", "sec crypto"],
    ),
}


def get_asset_entry(symbol: str) -> Optional[AssetRegistryEntry]:
    """Retrieve asset registry entry by symbol (case-insensitive)."""
    return ASSET_REGISTRY.get(symbol.upper())
