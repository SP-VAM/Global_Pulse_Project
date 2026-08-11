"""
Finnhub Market Data Provider
Implements MarketDataProvider using the Finnhub REST API.

Key design decisions:
  - Single shared httpx.AsyncClient (connection reuse, no per-request instantiation).
  - All provider-specific exceptions are translated to GlobalPulse domain exceptions.
  - Raw Finnhub JSON is never returned — always normalized to domain models.
  - Currency for quotes is enriched from /stock/profile2 (Finnhub /quote has no currency field).
  - If profile endpoint returns empty {}, InstrumentNotFoundError is raised with a
    clear provider-limitation message. Data is never invented.
  - API key is never logged.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import (
    InstrumentNotFoundError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.core.timezone import TimezoneService
from app.domain.instrument import NormalizedInstrument, NormalizedQuote
from app.domain.market import AssetType
from app.providers.base.market_provider import MarketDataProvider
from app.providers.finnhub.models import FinnhubProfile, FinnhubQuote

logger = logging.getLogger(__name__)

SOURCE = "FINNHUB"


class FinnhubMarketProvider(MarketDataProvider):
    """
    Finnhub-backed implementation of MarketDataProvider.

    Lifecycle:
        provider = FinnhubMarketProvider(api_key="...", base_url="...", timeout=10.0)
        # Use provider ...
        await provider.close()

    In FastAPI, manage via application lifespan so the client is shared across requests.
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

    async def get_quote(self, symbol: str) -> NormalizedQuote:
        """
        Fetch a real-time quote for symbol.
        Currency is enriched from /stock/profile2 because /quote has no currency field.
        If the profile fetch fails, currency is set to None rather than defaulted.
        """
        logger.info("Fetching quote from Finnhub | symbol=%s", symbol)

        raw = await self._get("/quote", params={"symbol": symbol})

        try:
            fq = FinnhubQuote.model_validate(raw)
        except PydanticValidationError as exc:
            logger.error("Malformed Finnhub quote response | symbol=%s | error=%s", symbol, exc)
            raise ProviderUnavailableError(
                f"Finnhub returned a malformed quote response for '{symbol}'."
            ) from exc

        # Finnhub returns c=0 when the symbol is invalid or market is closed with no data.
        # A completely null/zero quote with no timestamp is treated as not-found.
        if fq.c is None and fq.t is None and fq.pc is None:
            raise InstrumentNotFoundError(
                f"No quote data found for symbol '{symbol}'. "
                "Verify the symbol is correct and supported by your Finnhub plan."
            )

        # Enrich currency from profile (best-effort; null if unavailable)
        currency = await self._get_currency_for(symbol)

        # Build timestamps
        now_utc = datetime.now(tz=timezone.utc)
        if fq.t:
            quote_utc = datetime.fromtimestamp(fq.t, tz=timezone.utc)
        else:
            quote_utc = now_utc

        quote_ist = TimezoneService.utc_to_ist(quote_utc)

        return NormalizedQuote(
            symbol=symbol.upper(),
            price=fq.c if fq.c != 0 else None,
            open=fq.o if fq.o != 0 else None,
            high=fq.h if fq.h != 0 else None,
            low=fq.l if fq.l != 0 else None,
            previous_close=fq.pc if fq.pc != 0 else None,
            change=fq.d,
            change_percent=fq.dp,
            currency=currency,
            timestamp_utc=quote_utc.isoformat(),
            timestamp_ist=quote_ist.isoformat(),
            source=SOURCE,
        )

    async def get_instrument(self, symbol: str) -> NormalizedInstrument:
        """
        Fetch normalized instrument profile for symbol.

        Finnhub endpoint: GET /stock/profile2
        Coverage depends on provider plan and exchange.
        If Finnhub returns an empty object, InstrumentNotFoundError is raised.
        Fields absent from the provider response are set to None, never invented.
        """
        logger.info("Fetching instrument profile from Finnhub | symbol=%s", symbol)

        raw = await self._get("/stock/profile2", params={"symbol": symbol})

        # Finnhub returns {} for unknown/unsupported symbols
        if not raw or not raw.get("ticker") and not raw.get("name"):
            raise InstrumentNotFoundError(
                f"Instrument profile not found for symbol '{symbol}'. "
                "This may be due to provider plan coverage limitations or an invalid symbol."
            )

        try:
            profile = FinnhubProfile.model_validate(raw)
        except PydanticValidationError as exc:
            logger.error(
                "Malformed Finnhub profile response | symbol=%s | error=%s", symbol, exc
            )
            raise ProviderUnavailableError(
                f"Finnhub returned a malformed profile response for '{symbol}'."
            ) from exc

        asset_type = self._map_asset_type(profile.finnhubIndustry)

        return NormalizedInstrument(
            symbol=symbol.upper(),
            name=profile.name or None,
            exchange=profile.exchange or None,
            country=profile.country or None,
            asset_type=asset_type,
            currency=profile.currency or None,
            timezone=None,   # Finnhub profile does not supply IANA timezone
            source=SOURCE,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._client.aclose()
        logger.info("FinnhubMarketProvider HTTP client closed.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: dict | None = None) -> dict:
        """
        Execute a GET request against the Finnhub API.
        Translates HTTP-level errors to GlobalPulse domain exceptions.
        API key is injected as a query parameter — never logged.
        """
        request_params = {"token": self._api_key}
        if params:
            request_params.update(params)

        # Log path only; do NOT log token or full URL containing token
        logger.debug("Finnhub GET %s | params=%s", path, {k: v for k, v in (params or {}).items()})

        try:
            response = await self._client.get(path, params=request_params)
        except httpx.TimeoutException as exc:
            logger.warning("Finnhub request timed out | path=%s", path)
            raise ProviderUnavailableError(
                f"Finnhub API request timed out for path '{path}'. Please try again later."
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Finnhub network error | path=%s | error=%s", path, exc)
            raise ProviderUnavailableError(
                f"Could not reach Finnhub API: {exc}"
            ) from exc

        if response.status_code == 401 or response.status_code == 403:
            logger.error("Finnhub authentication failure | status=%d | path=%s", response.status_code, path)
            raise ProviderAuthenticationError(
                "Finnhub API key is invalid or unauthorized. "
                "Check your FINNHUB_API_KEY configuration."
            )

        if response.status_code == 429:
            logger.warning("Finnhub rate limit exceeded | path=%s", path)
            raise ProviderRateLimitError(
                "Finnhub API rate limit exceeded. Please wait before making further requests."
            )

        if response.status_code >= 500:
            logger.error("Finnhub server error | status=%d | path=%s", response.status_code, path)
            raise ProviderUnavailableError(
                f"Finnhub API returned a server error (HTTP {response.status_code})."
            )

        try:
            return response.json()
        except Exception as exc:
            logger.error("Finnhub returned non-JSON response | path=%s", path)
            raise ProviderUnavailableError(
                "Finnhub API returned a non-JSON response. Provider may be experiencing issues."
            ) from exc

    async def _get_currency_for(self, symbol: str) -> Optional[str]:
        """
        Best-effort currency lookup from Finnhub profile endpoint.
        Returns None if the profile is unavailable or empty — never defaults.
        Swallows all provider errors silently (currency is enrichment, not critical path).
        """
        try:
            raw = await self._get("/stock/profile2", params={"symbol": symbol})
            if raw and raw.get("currency"):
                return raw["currency"]
        except Exception:
            logger.debug("Could not enrich currency for '%s' from profile; returning null.", symbol)
        return None

    @staticmethod
    def _map_asset_type(finnhub_industry: Optional[str]) -> Optional[AssetType]:
        """
        Map Finnhub industry string to GlobalPulse AssetType.
        Finnhub does not expose a direct asset-type field via /stock/profile2;
        the finnhubIndustry field is best-effort context only.
        Returns EQUITY as a reasonable default for stock profiles, or None.
        """
        if finnhub_industry is not None:
            return AssetType.EQUITY
        return None
