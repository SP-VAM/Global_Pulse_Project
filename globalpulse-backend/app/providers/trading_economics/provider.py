"""
Trading Economics Economic Data Provider
Implements EconomicDataProvider using the Trading Economics REST API.

Key design decisions:
  - Single shared httpx.AsyncClient (same pattern as FinnhubMarketProvider).
  - API key passed as query parameter 'c'; never logged.
  - 401 → ProviderAuthenticationError (invalid/missing key).
  - 403 → ProviderFeatureUnavailableError (feature not available under current plan).
  - 429 → ProviderRateLimitError.
  - 5xx / timeout → ProviderUnavailableError.
  - Raw TE JSON is never returned — always normalized to GlobalPulse domain models.
  - Missing numeric values are None, never substituted with zero.
  - Timestamps are normalized through TimezoneService (no manual +offset).
"""
from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timezone
from typing import Any, List, Optional

import httpx
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import (
    ProviderAuthenticationError,
    ProviderFeatureUnavailableError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.core.timezone import TimezoneService
from app.domain.bond import NormalizedBond
from app.domain.commodity import CommodityCategory, NormalizedCommodity
from app.domain.economic_event import (
    EconomicEventCategory,
    EconomicImportance,
    NormalizedEconomicEvent,
)
from app.domain.forex import NormalizedForexPair
from app.providers.base.economic_provider import EconomicDataProvider
from app.providers.trading_economics.models import TECalendarEvent, TEMarketItem

logger = logging.getLogger(__name__)

SOURCE = "TRADING_ECONOMICS"

# ---------------------------------------------------------------------------
# Category mapping (deterministic keyword → EconomicEventCategory)
# Keys are lowercased substrings of the provider category field.
# ---------------------------------------------------------------------------

_CATEGORY_MAP: list[tuple[str, EconomicEventCategory]] = [
    ("interest rate", EconomicEventCategory.INTEREST_RATE),
    ("inflation", EconomicEventCategory.INFLATION),
    ("cpi", EconomicEventCategory.INFLATION),
    ("ppi", EconomicEventCategory.INFLATION),
    ("gdp", EconomicEventCategory.GDP),
    ("gross domestic", EconomicEventCategory.GDP),
    ("employment change", EconomicEventCategory.EMPLOYMENT),
    ("nonfarm", EconomicEventCategory.EMPLOYMENT),
    ("payroll", EconomicEventCategory.EMPLOYMENT),
    ("unemployment", EconomicEventCategory.UNEMPLOYMENT),
    ("jobless", EconomicEventCategory.UNEMPLOYMENT),
    ("central bank", EconomicEventCategory.CENTRAL_BANK),
    ("monetary policy", EconomicEventCategory.CENTRAL_BANK),
    ("manufacturing", EconomicEventCategory.MANUFACTURING),
    ("pmi", EconomicEventCategory.MANUFACTURING),
    ("industrial production", EconomicEventCategory.MANUFACTURING),
    ("services", EconomicEventCategory.SERVICES),
    ("service sector", EconomicEventCategory.SERVICES),
    ("trade balance", EconomicEventCategory.TRADE),
    ("imports", EconomicEventCategory.TRADE),
    ("exports", EconomicEventCategory.TRADE),
    ("current account", EconomicEventCategory.TRADE),
    ("consumer", EconomicEventCategory.CONSUMER),
    ("retail", EconomicEventCategory.CONSUMER),
    ("housing", EconomicEventCategory.HOUSING),
    ("building permit", EconomicEventCategory.HOUSING),
    ("construction", EconomicEventCategory.HOUSING),
    ("government", EconomicEventCategory.GOVERNMENT),
    ("budget", EconomicEventCategory.GOVERNMENT),
    ("fiscal", EconomicEventCategory.GOVERNMENT),
]

# ---------------------------------------------------------------------------
# Commodity symbol → category mapping
# ---------------------------------------------------------------------------

_COMMODITY_CATEGORY_MAP: dict[str, CommodityCategory] = {
    # Energy
    "WTICOILNYM": CommodityCategory.ENERGY,
    "LOUISIANASW": CommodityCategory.ENERGY,
    "NGASUS": CommodityCategory.ENERGY,
    "COAL": CommodityCategory.ENERGY,
    "BRENTOIL": CommodityCategory.ENERGY,
    # Metals
    "XAUUSD": CommodityCategory.METALS,
    "XAGUSD": CommodityCategory.METALS,
    "COPPER": CommodityCategory.METALS,
    "PLATINUM": CommodityCategory.METALS,
    "PALLADIUM": CommodityCategory.METALS,
    "ALUM": CommodityCategory.METALS,
    "NICKEL": CommodityCategory.METALS,
    "ZINC": CommodityCategory.METALS,
    "LEAD": CommodityCategory.METALS,
    "TIN": CommodityCategory.METALS,
    # Agriculture
    "WHEAT": CommodityCategory.AGRICULTURE,
    "CORN": CommodityCategory.AGRICULTURE,
    "SOYBEAN": CommodityCategory.AGRICULTURE,
    "COFFEE": CommodityCategory.AGRICULTURE,
    "SUGAR": CommodityCategory.AGRICULTURE,
    "COTTON": CommodityCategory.AGRICULTURE,
    "COCOA": CommodityCategory.AGRICULTURE,
    "RICE": CommodityCategory.AGRICULTURE,
}

# Priority FX pairs — only these are returned if no explicit filter is given
_PRIORITY_FX_SYMBOLS = {
    "USDINR", "USDJPY", "USDSGD", "USDCNY", "USDCNH",
    "EURUSD", "GBPUSD", "USDCHF", "AUDUSD",
}

# Priority bond symbols
_PRIORITY_BOND_SYMBOLS = {
    "USGG10YR",   # US 10Y
    "INGB10YR",   # India 10Y
    "GJGB10",     # Japan 10Y
    "GDBR10",     # Germany 10Y
    "GUKG10",     # UK 10Y
}

# Known bond country associations (symbol → country, maturity)
_BOND_META: dict[str, tuple[str, str]] = {
    "USGG10YR": ("United States", "10Y"),
    "USGG2YR": ("United States", "2Y"),
    "USGG30YR": ("United States", "30Y"),
    "INGB10YR": ("India", "10Y"),
    "INGB2YR": ("India", "2Y"),
    "GJGB10": ("Japan", "10Y"),
    "GDBR10": ("Germany", "10Y"),
    "GUKG10": ("United Kingdom", "10Y"),
    "GBTPGR10": ("Italy", "10Y"),
    "GFRA10YR": ("France", "10Y"),
}


def _map_category(raw_category: Optional[str]) -> EconomicEventCategory:
    """Deterministically map a TE category string to EconomicEventCategory."""
    if not raw_category:
        return EconomicEventCategory.OTHER
    lower = raw_category.lower()
    for keyword, category in _CATEGORY_MAP:
        if keyword in lower:
            return category
    return EconomicEventCategory.OTHER


def _map_importance(raw_importance: Any) -> EconomicImportance:
    """
    Map Trading Economics importance (int 1–3 or string) to EconomicImportance.
    Absent/unrecognized values → UNKNOWN (never defaulted to LOW).
    """
    if raw_importance is None:
        return EconomicImportance.UNKNOWN
    try:
        val = int(raw_importance)
    except (TypeError, ValueError):
        lower = str(raw_importance).lower().strip()
        mapping = {"high": EconomicImportance.HIGH, "medium": EconomicImportance.MEDIUM, "low": EconomicImportance.LOW}
        return mapping.get(lower, EconomicImportance.UNKNOWN)
    return {3: EconomicImportance.HIGH, 2: EconomicImportance.MEDIUM, 1: EconomicImportance.LOW}.get(
        val, EconomicImportance.UNKNOWN
    )


def _parse_numeric(value: Any) -> Optional[float]:
    """
    Parse a TE numeric field that may be a string, float, int, or None.
    Returns None on any parse failure — never substitutes zero.
    """
    if value is None:
        return None
    try:
        f = float(value)
        return f
    except (TypeError, ValueError):
        return None


def _parse_te_datetime_utc(raw: Optional[str]) -> datetime:
    """
    Parse a Trading Economics datetime string to a UTC-aware datetime.
    TE returns naive ISO strings that are treated as UTC.
    Falls back to current UTC if parsing fails.
    """
    if raw:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                dt = datetime.strptime(raw, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return datetime.now(tz=timezone.utc)


def _stable_event_id(calendar_id: Optional[str], country: str, event: str, raw_date: Optional[str]) -> str:
    """Generate a stable deterministic ID for deduplication."""
    if calendar_id:
        return calendar_id
    raw = f"{country}|{event}|{raw_date or ''}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


class TradingEconomicsProvider(EconomicDataProvider):
    """
    Trading Economics-backed implementation of EconomicDataProvider.

    Lifecycle (same pattern as FinnhubMarketProvider):
        provider = TradingEconomicsProvider(api_key="...", base_url="...", timeout=10.0)
        # Use provider ...
        await provider.close()

    Plan limitations:
        403 responses from Trading Economics indicate that a feature or data set
        is not available under the configured subscription. These raise
        ProviderFeatureUnavailableError rather than ProviderAuthenticationError.
    """

    def __init__(self, api_key: str, base_url: str, timeout: float = 10.0) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": "GlobalPulse/0.1.0"},
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def get_calendar(
        self,
        country: Optional[str] = None,
        category: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        importance: Optional[str] = None,
        limit: int = 50,
    ) -> List[NormalizedEconomicEvent]:
        """Fetch and normalize economic calendar events."""
        logger.info(
            "Fetching TE calendar | country=%s category=%s from=%s to=%s",
            country, category, from_date, to_date,
        )

        # Build path: /calendar or /calendar/country/{country}
        if country:
            path = f"/calendar/country/{country.lower().replace(' ', '%20')}"
        else:
            path = "/calendar"

        params: dict = {}
        if from_date:
            params["d1"] = from_date.strftime("%Y-%m-%d")
        if to_date:
            params["d2"] = to_date.strftime("%Y-%m-%d")
        if category:
            params["c"] = self._api_key  # will be added by _get
            # category filter added below as 'category' param
            params["category"] = category

        raw_list = await self._get(path, params=params)

        if not isinstance(raw_list, list):
            logger.error("TE calendar returned non-list response")
            raise ProviderUnavailableError(
                "Trading Economics returned an unexpected response format for /calendar."
            )

        events: List[NormalizedEconomicEvent] = []
        for raw in raw_list:
            try:
                item = TECalendarEvent.model_validate(raw)
            except PydanticValidationError as exc:
                logger.warning("Skipping malformed TE calendar item: %s", exc)
                continue

            importance_level = _map_importance(item.Importance)

            # Apply importance filter
            if importance and importance.upper() != importance_level.value:
                continue

            event_utc = _parse_te_datetime_utc(item.Date)
            event_ist = TimezoneService.utc_to_ist(event_utc)

            events.append(
                NormalizedEconomicEvent(
                    id=_stable_event_id(item.CalendarId, item.Country or "", item.Event or "", item.Date),
                    country=item.Country or "",
                    event=item.Event or "",
                    category=_map_category(item.Category),
                    importance=importance_level,
                    actual=_parse_numeric(item.Actual),
                    forecast=_parse_numeric(item.Forecast),
                    previous=_parse_numeric(item.Previous),
                    unit=item.Unit or None,
                    timestamp_utc=event_utc.isoformat(),
                    timestamp_ist=event_ist.isoformat(),
                    source=SOURCE,
                )
            )

            if len(events) >= limit:
                break

        return events

    async def get_commodities(
        self,
        category: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> List[NormalizedCommodity]:
        """Fetch and normalize commodity price snapshots."""
        logger.info("Fetching TE commodities | category=%s symbol=%s", category, symbol)

        raw_list = await self._get("/markets/commodities")

        if not isinstance(raw_list, list):
            raise ProviderUnavailableError(
                "Trading Economics returned an unexpected response format for /markets/commodities."
            )

        now_utc = datetime.now(tz=timezone.utc)
        commodities: List[NormalizedCommodity] = []

        for raw in raw_list:
            try:
                item = TEMarketItem.model_validate(raw)
            except PydanticValidationError:
                continue

            sym = (item.Symbol or "").upper()

            # Symbol filter
            if symbol and sym.lower() != symbol.lower():
                continue

            # Determine category from symbol map, then from TE Type field
            cat = _COMMODITY_CATEGORY_MAP.get(sym)
            if cat is None:
                te_type = (item.Type or "").lower()
                if "energy" in te_type or "oil" in te_type or "gas" in te_type:
                    cat = CommodityCategory.ENERGY
                elif "metal" in te_type or "gold" in te_type or "silver" in te_type:
                    cat = CommodityCategory.METALS
                elif "agri" in te_type or "grain" in te_type or "food" in te_type:
                    cat = CommodityCategory.AGRICULTURE
                else:
                    cat = CommodityCategory.OTHER

            # Category filter
            if category and cat.value.upper() != category.upper():
                continue

            ts_utc = _parse_te_datetime_utc(item.Date) if item.Date else now_utc
            ts_ist = TimezoneService.utc_to_ist(ts_utc)

            commodities.append(
                NormalizedCommodity(
                    symbol=sym,
                    name=item.Name or sym,
                    category=cat,
                    price=item.Close,
                    currency=item.Currency or "USD",
                    unit=item.unit or None,
                    change=item.Change,
                    change_percent=item.PercentualChange,
                    timestamp_utc=ts_utc.isoformat(),
                    timestamp_ist=ts_ist.isoformat(),
                    source=SOURCE,
                )
            )

        return commodities

    async def get_forex(
        self,
        symbols: Optional[List[str]] = None,
    ) -> List[NormalizedForexPair]:
        """Fetch and normalize FX pair snapshots."""
        logger.info("Fetching TE forex | symbols=%s", symbols)

        raw_list = await self._get("/markets/currency")

        if not isinstance(raw_list, list):
            raise ProviderUnavailableError(
                "Trading Economics returned an unexpected response format for /markets/currency."
            )

        now_utc = datetime.now(tz=timezone.utc)
        pairs: List[NormalizedForexPair] = []
        filter_set = {s.upper() for s in symbols} if symbols else None

        for raw in raw_list:
            try:
                item = TEMarketItem.model_validate(raw)
            except PydanticValidationError:
                continue

            sym = (item.Symbol or "").upper()

            # If no filter supplied, only return priority pairs to avoid noise
            if filter_set:
                if sym not in filter_set:
                    continue
            elif sym not in _PRIORITY_FX_SYMBOLS:
                continue

            # Derive base/quote from symbol (standard 6-char FX notation)
            if len(sym) == 6:
                base = sym[:3]
                quote = sym[3:]
            else:
                base = sym
                quote = ""

            ts_utc = _parse_te_datetime_utc(item.Date) if item.Date else now_utc
            ts_ist = TimezoneService.utc_to_ist(ts_utc)

            pairs.append(
                NormalizedForexPair(
                    symbol=sym,
                    base_currency=base,
                    quote_currency=quote,
                    rate=item.Close,
                    change=item.Change,
                    change_percent=item.PercentualChange,
                    timestamp_utc=ts_utc.isoformat(),
                    timestamp_ist=ts_ist.isoformat(),
                    source=SOURCE,
                )
            )

        return pairs

    async def get_bond_yields(
        self,
        countries: Optional[List[str]] = None,
    ) -> List[NormalizedBond]:
        """
        Fetch and normalize government bond yield snapshots.

        Note: Bond data access depends heavily on the configured Trading Economics
        subscription plan. If the plan does not include bond data, this method raises
        ProviderFeatureUnavailableError.
        """
        logger.info("Fetching TE bond yields | countries=%s", countries)

        raw_list = await self._get("/markets/bond")

        if not isinstance(raw_list, list):
            raise ProviderUnavailableError(
                "Trading Economics returned an unexpected response format for /markets/bond."
            )

        now_utc = datetime.now(tz=timezone.utc)
        bonds: List[NormalizedBond] = []
        country_filter = {c.lower() for c in countries} if countries else None

        for raw in raw_list:
            try:
                item = TEMarketItem.model_validate(raw)
            except PydanticValidationError:
                continue

            sym = (item.Symbol or "").upper()

            # Only process known/priority bonds unless caller supplied a symbol hint
            if sym not in _BOND_META and sym not in _PRIORITY_BOND_SYMBOLS:
                continue

            country_name, maturity = _BOND_META.get(sym, (item.Name or sym, "?"))

            if country_filter and country_name.lower() not in country_filter:
                continue

            ts_utc = _parse_te_datetime_utc(item.Date) if item.Date else now_utc
            ts_ist = TimezoneService.utc_to_ist(ts_utc)

            bonds.append(
                NormalizedBond(
                    symbol=sym,
                    name=item.Name or sym,
                    country=country_name,
                    maturity=maturity,
                    yield_value=item.Close,
                    change=item.Change,
                    change_percent=item.PercentualChange,
                    timestamp_utc=ts_utc.isoformat(),
                    timestamp_ist=ts_ist.isoformat(),
                    source=SOURCE,
                )
            )

        return bonds

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._client.aclose()
        logger.info("TradingEconomicsProvider HTTP client closed.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: Optional[dict] = None) -> Any:
        """
        Execute a GET request against the Trading Economics API.

        API key is injected as the 'c' query parameter — never logged.

        HTTP error mapping:
          401 → ProviderAuthenticationError   (invalid/missing API key)
          403 → ProviderFeatureUnavailableError (endpoint not in subscription plan)
          429 → ProviderRateLimitError
          5xx → ProviderUnavailableError
        """
        request_params = {"c": self._api_key}
        if params:
            # Avoid overriding 'c' if caller accidentally included it
            for k, v in params.items():
                if k != "c":
                    request_params[k] = v

        # Log path only — never log the API key
        logger.debug("Trading Economics GET %s | params_keys=%s", path, list((params or {}).keys()))

        try:
            response = await self._client.get(path, params=request_params)
        except httpx.TimeoutException as exc:
            logger.warning("Trading Economics request timed out | path=%s", path)
            raise ProviderUnavailableError(
                f"Trading Economics API request timed out for path '{path}'. Please try again later."
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Trading Economics network error | path=%s | error=%s", path, exc)
            raise ProviderUnavailableError(
                f"Could not reach Trading Economics API: {exc}"
            ) from exc

        if response.status_code == 401:
            logger.error("TE authentication failure | status=401 | path=%s", path)
            raise ProviderAuthenticationError(
                "Trading Economics API key is invalid or missing. "
                "Check your TRADING_ECONOMICS_API_KEY configuration."
            )

        if response.status_code == 403:
            logger.warning(
                "TE access forbidden | status=403 | path=%s — "
                "likely not available under the current subscription plan.", path
            )
            raise ProviderFeatureUnavailableError(
                f"The Trading Economics endpoint '{path}' is not available under the current "
                "subscription plan. Upgrade your plan or use an alternative data source."
            )

        if response.status_code == 429:
            logger.warning("Trading Economics rate limit exceeded | path=%s", path)
            raise ProviderRateLimitError(
                "Trading Economics API rate limit exceeded. Please wait before making further requests."
            )

        if response.status_code >= 500:
            logger.error("TE server error | status=%d | path=%s", response.status_code, path)
            raise ProviderUnavailableError(
                f"Trading Economics API returned a server error (HTTP {response.status_code})."
            )

        try:
            return response.json()
        except Exception as exc:
            logger.error("Trading Economics returned non-JSON response | path=%s", path)
            raise ProviderUnavailableError(
                "Trading Economics API returned a non-JSON response. Provider may be experiencing issues."
            ) from exc
