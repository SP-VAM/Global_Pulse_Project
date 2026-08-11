"""
GlobalPulse Country Tagger
Lightweight deterministic country detection from article text.

Approach:
  - Match country names, common aliases, and selected major unambiguous cities.
  - Returns ISO 3166-1 alpha-2 codes.
  - Does NOT attempt NLP/NER.
  - When uncertain, returns nothing rather than making geographic claims.
  - Empty list is a valid result.

Phase 1E MVP scope: static mapping only.
"""
from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple


# ---------------------------------------------------------------------------
# Country mapping: (phrase → ISO alpha-2)
# ---------------------------------------------------------------------------
# Format: lowercased text pattern → ISO alpha-2
# Longest-match takes priority implicitly via iteration order (dict is ordered).
# Phrases with spaces must appear before shorter single-word entries to
# avoid partial matches shadowing them.

_COUNTRY_PHRASES: Dict[str, str] = {
    # United States — many aliases
    "united states of america": "US",
    "united states": "US",
    "u.s.a.": "US",
    "u.s.": "US",
    "usa": "US",
    "american": "US",
    "america": "US",
    "washington d.c.": "US",
    "washington dc": "US",
    "new york": "US",
    "wall street": "US",
    "silicon valley": "US",
    "federal reserve": "US",
    "the fed": "US",
    # India
    "india": "IN",
    "indian": "IN",
    "new delhi": "IN",
    "delhi": "IN",
    "mumbai": "IN",
    "bengaluru": "IN",
    "bangalore": "IN",
    "hyderabad": "IN",
    "reserve bank of india": "IN",
    "rbi": "IN",
    "nse": "IN",
    "bse": "IN",
    "sensex": "IN",
    "nifty": "IN",
    # China
    "china": "CN",
    "chinese": "CN",
    "beijing": "CN",
    "shanghai": "CN",
    "shenzhen": "CN",
    "hong kong": "HK",
    "people's bank of china": "CN",
    "pboc": "CN",
    # Japan
    "japan": "JP",
    "japanese": "JP",
    "tokyo": "JP",
    "osaka": "JP",
    "bank of japan": "JP",
    "boj": "JP",
    "nikkei": "JP",
    # Germany
    "germany": "DE",
    "german": "DE",
    "berlin": "DE",
    "frankfurt": "DE",
    "bundesbank": "DE",
    "dax": "DE",
    # United Kingdom
    "united kingdom": "GB",
    "u.k.": "GB",
    "uk": "GB",
    "britain": "GB",
    "british": "GB",
    "england": "GB",
    "london": "GB",
    "bank of england": "GB",
    "boe": "GB",
    "ftse": "GB",
    # Europe / EU
    "european union": "EU",
    "eurozone": "EU",
    "euro area": "EU",
    "ecb": "EU",
    "european central bank": "EU",
    # France
    "france": "FR",
    "french": "FR",
    "paris": "FR",
    # Singapore
    "singapore": "SG",
    "mas": "SG",
    "monetary authority of singapore": "SG",
    # Australia
    "australia": "AU",
    "australian": "AU",
    "sydney": "AU",
    "reserve bank of australia": "AU",
    "rba": "AU",
    "asx": "AU",
    # Russia
    "russia": "RU",
    "russian": "RU",
    "moscow": "RU",
    "kremlin": "RU",
    # Ukraine
    "ukraine": "UA",
    "ukrainian": "UA",
    "kyiv": "UA",
    "kiev": "UA",
    # South Korea
    "south korea": "KR",
    "korea": "KR",
    "korean": "KR",
    "seoul": "KR",
    "bank of korea": "KR",
    # Taiwan
    "taiwan": "TW",
    "taiwanese": "TW",
    "taipei": "TW",
    # Canada
    "canada": "CA",
    "canadian": "CA",
    "toronto": "CA",
    "bank of canada": "CA",
    # Brazil
    "brazil": "BR",
    "brazilian": "BR",
    "são paulo": "BR",
    "sao paulo": "BR",
    "brasilia": "BR",
    # Saudi Arabia
    "saudi arabia": "SA",
    "saudi": "SA",
    "riyadh": "SA",
    "aramco": "SA",
    "opec": "SA",  # OPEC is Saudi-led; approximate
    # UAE
    "united arab emirates": "AE",
    "uae": "AE",
    "dubai": "AE",
    "abu dhabi": "AE",
    # Indonesia
    "indonesia": "ID",
    "indonesian": "ID",
    "jakarta": "ID",
    # Malaysia
    "malaysia": "MY",
    "kuala lumpur": "MY",
    # Thailand
    "thailand": "TH",
    "thai": "TH",
    "bangkok": "TH",
    # Vietnam
    "vietnam": "VN",
    "hanoi": "VN",
    "ho chi minh": "VN",
    # Pakistan
    "pakistan": "PK",
    "islamabad": "PK",
    "karachi": "PK",
    # Israel
    "israel": "IL",
    "israeli": "IL",
    "tel aviv": "IL",
    # Iran
    "iran": "IR",
    "iranian": "IR",
    "tehran": "IR",
    # Turkey
    "turkey": "TR",
    "turkish": "TR",
    "ankara": "TR",
    "istanbul": "TR",
    # Mexico
    "mexico": "MX",
    "mexican": "MX",
    "mexico city": "MX",
    # Argentina
    "argentina": "AR",
    "argentine": "AR",
    "buenos aires": "AR",
    # South Africa
    "south africa": "ZA",
    "johannesburg": "ZA",
    # Nigeria
    "nigeria": "NG",
    "lagos": "NG",
    # Egypt
    "egypt": "EG",
    "cairo": "EG",
    "suez": "EG",
    # Switzerland
    "switzerland": "CH",
    "swiss": "CH",
    "zurich": "CH",
    "geneva": "CH",
    # Netherlands
    "netherlands": "NL",
    "dutch": "NL",
    "amsterdam": "NL",
    # Italy
    "italy": "IT",
    "italian": "IT",
    "rome": "IT",
    "milan": "IT",
    # Spain
    "spain": "ES",
    "spanish": "ES",
    "madrid": "ES",
    # Philippines
    "philippines": "PH",
    "manila": "PH",
}

# Pre-sort by phrase length descending to ensure longest match wins
_SORTED_PHRASES: List[Tuple[str, str]] = sorted(
    _COUNTRY_PHRASES.items(), key=lambda x: len(x[0]), reverse=True
)


def tag_countries(text: str) -> List[str]:
    """
    Extract a deduplicated list of ISO 3166-1 alpha-2 country codes from text.

    Uses simple substring matching (case-insensitive, word-boundary aware for
    short codes like 'US', 'UK' to avoid false positives from words like 'bus').

    Returns an empty list when no countries can be determined.
    """
    if not text:
        return []

    lower = text.lower()
    found: Set[str] = set()

    for phrase, iso in _SORTED_PHRASES:
        # For very short phrases (≤3 chars), require word boundaries to avoid false hits
        if len(phrase) <= 3:
            pattern = r"\b" + re.escape(phrase) + r"\b"
            if re.search(pattern, lower):
                found.add(iso)
        else:
            if phrase in lower:
                found.add(iso)

    return sorted(found)  # Stable ordering
