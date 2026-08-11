"""
NewsAPI News Provider
Implements NewsProvider using the NewsAPI v2 REST API.

Key design decisions:
  - Single shared httpx.AsyncClient (same pattern as other providers).
  - API key sent in X-Api-Key header — never in logs or response bodies.
  - 401 → ProviderAuthenticationError (invalid API key).
  - 403 → ProviderFeatureUnavailableError (plan restriction, e.g. dev-only domain).
  - 429 → ProviderRateLimitError.
  - NewsAPI sometimes returns status='error' with HTTP 200; these are translated.
  - Full article body (content field) is intentionally discarded (copyright compliance).
  - Classification is NOT performed here — that is EventClassificationService's job.
  - All timestamps are normalized through TimezoneService.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timezone
from typing import List, Optional

import httpx
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import (
    ProviderAuthenticationError,
    ProviderFeatureUnavailableError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from app.core.timezone import TimezoneService
from app.domain.news import GlobalEventCategory, NormalizedArticle
from app.providers.base.news_provider import NewsProvider
from app.providers.newsapi.models import NewsAPIArticle, NewsAPIResponse

logger = logging.getLogger(__name__)

SOURCE = "NEWSAPI"

# NewsAPI error codes that indicate plan-level restrictions
_PLAN_RESTRICTION_CODES = {
    "apiKeyExhausted",
    "apiKeyDisabled",
    "maximumResultsReached",
    "sourcesTooMany",
    "sourceDoesNotExist",
}


def _parse_newsapi_datetime(raw: Optional[str]) -> datetime:
    """
    Parse a NewsAPI ISO datetime string (e.g. '2024-01-26T14:00:00Z') to UTC-aware datetime.
    Falls back to current UTC on any parse failure.
    """
    if raw:
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                dt = datetime.strptime(raw, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue
    return datetime.now(tz=timezone.utc)


def _article_id(url: Optional[str]) -> str:
    """Generate a stable deduplication key from the article URL."""
    if url:
        return hashlib.sha256(url.encode()).hexdigest()[:16]
    return hashlib.sha256(b"unknown").hexdigest()[:16]


def _normalize_article(raw: NewsAPIArticle) -> Optional[NormalizedArticle]:
    """
    Convert a raw NewsAPI article into a NormalizedArticle.

    Returns None if the article is missing both title and URL (unprocessable).
    Classification fields (primary_category, countries, companies, etc.) are
    set to their defaults here and populated by EventClassificationService later.
    """
    if not raw.title and not raw.url:
        return None

    headline = (raw.title or "").strip()
    if not headline:
        return None

    published_utc = _parse_newsapi_datetime(raw.publishedAt)
    published_ist = TimezoneService.utc_to_ist(published_utc)

    source_name = ""
    source_url: Optional[str] = None
    if raw.source:
        source_name = raw.source.name or ""

    return NormalizedArticle(
        id=_article_id(raw.url),
        headline=headline,
        summary=raw.description or None,
        source_name=source_name,
        source_url=source_url,
        article_url=raw.url or "",
        author=raw.author or None,
        published_at_utc=published_utc.isoformat(),
        published_at_ist=published_ist.isoformat(),
        primary_category=GlobalEventCategory.OTHER,  # Will be overwritten by classifier
        tags=[],
        countries=[],
        companies=[],
        sectors=[],
        keywords=[],
        relevance_score=0,
        source=SOURCE,
    )


class NewsApiProvider(NewsProvider):
    """
    NewsAPI-backed implementation of NewsProvider.

    Lifecycle:
        provider = NewsApiProvider(api_key="...", base_url="...", timeout=10.0)
        # Use provider ...
        await provider.close()

    Free-plan limitations:
        - 100 requests/day
        - 1-month history
        - No full article bodies (content is truncated by NewsAPI itself)
        - Non-commercial use only
    """

    def __init__(self, api_key: str, base_url: str, timeout: float = 10.0) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout),
            # API key in header — never in URL or logs
            headers={
                "User-Agent": "GlobalPulse/0.1.0",
                "X-Api-Key": self._api_key,
            },
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def search_news(
        self,
        query: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        language: str = "en",
        page: int = 1,
        page_size: int = 20,
    ) -> List[NormalizedArticle]:
        """Fetch and minimally normalize news articles from NewsAPI /everything."""
        logger.info(
            "Fetching news from NewsAPI | q=%s from=%s to=%s page=%d",
            query, from_date, to_date, page,
        )

        params: dict = {
            "language": language,
            "pageSize": min(page_size, 100),  # NewsAPI caps at 100
            "page": page,
            "sortBy": "publishedAt",
        }
        if query:
            params["q"] = query
        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()

        raw = await self._get("/everything", params=params)

        try:
            response = NewsAPIResponse.model_validate(raw)
        except PydanticValidationError as exc:
            logger.error("Malformed NewsAPI response: %s", exc)
            raise ProviderUnavailableError(
                "NewsAPI returned a malformed response structure."
            ) from exc

        # NewsAPI can return status='error' with HTTP 200
        if response.status and response.status.lower() != "ok":
            self._handle_newsapi_error(response.code, response.message)

        articles: List[NormalizedArticle] = []
        for raw_article in response.articles:
            normalized = _normalize_article(raw_article)
            if normalized is not None:
                articles.append(normalized)

        logger.debug("NewsAPI returned %d articles (normalized)", len(articles))
        return articles

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._client.aclose()
        logger.info("NewsApiProvider HTTP client closed.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """
        Execute a GET request against the NewsAPI.

        API key is in the X-Api-Key header — never logged.

        HTTP error mapping:
          401 → ProviderAuthenticationError   (invalid/missing key)
          403 → ProviderFeatureUnavailableError (plan restriction)
          429 → ProviderRateLimitError
          5xx → ProviderUnavailableError
        """
        # Log only params keys, never values that might contain sensitive data
        logger.debug("NewsAPI GET %s | params_keys=%s", path, list((params or {}).keys()))

        try:
            response = await self._client.get(path, params=params)
        except httpx.TimeoutException as exc:
            logger.warning("NewsAPI request timed out | path=%s", path)
            raise ProviderUnavailableError(
                f"NewsAPI request timed out for path '{path}'. Please try again later."
            ) from exc
        except httpx.RequestError as exc:
            logger.error("NewsAPI network error | path=%s | error=%s", path, exc)
            raise ProviderUnavailableError(
                f"Could not reach NewsAPI: {exc}"
            ) from exc

        if response.status_code == 401:
            logger.error("NewsAPI authentication failure | status=401 | path=%s", path)
            raise ProviderAuthenticationError(
                "NewsAPI key is invalid or missing. Check your NEWS_API_KEY configuration."
            )

        if response.status_code == 403:
            logger.warning(
                "NewsAPI access forbidden | status=403 | path=%s — "
                "may be a plan or domain restriction.", path
            )
            raise ProviderFeatureUnavailableError(
                f"NewsAPI endpoint '{path}' returned 403. "
                "This may be a developer-plan restriction (e.g. non-localhost access) "
                "or a feature not included in your subscription."
            )

        if response.status_code == 429:
            logger.warning("NewsAPI rate limit exceeded | path=%s", path)
            raise ProviderRateLimitError(
                "NewsAPI rate limit exceeded. The free plan allows 100 requests/day."
            )

        if response.status_code >= 500:
            logger.error("NewsAPI server error | status=%d | path=%s", response.status_code, path)
            raise ProviderUnavailableError(
                f"NewsAPI returned a server error (HTTP {response.status_code})."
            )

        try:
            return response.json()
        except Exception as exc:
            logger.error("NewsAPI returned non-JSON response | path=%s", path)
            raise ProviderUnavailableError(
                "NewsAPI returned a non-JSON response. Provider may be experiencing issues."
            ) from exc

    @staticmethod
    def _handle_newsapi_error(code: Optional[str], message: Optional[str]) -> None:
        """Translate NewsAPI application-level error codes to domain exceptions."""
        code = code or ""
        message = message or "Unknown NewsAPI error."

        if code in ("apiKeyInvalid", "apiKeyMissing"):
            raise ProviderAuthenticationError(
                f"NewsAPI authentication error: {message}"
            )

        if code in _PLAN_RESTRICTION_CODES:
            raise ProviderFeatureUnavailableError(
                f"NewsAPI plan restriction: {message}"
            )

        if code == "rateLimited":
            raise ProviderRateLimitError(
                f"NewsAPI rate limited: {message}"
            )

        # Generic fallback
        raise ProviderUnavailableError(
            f"NewsAPI error [{code}]: {message}"
        )
