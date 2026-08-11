"""
GlobalPulse Abstract News Provider
All news data providers must implement this interface.
The service layer interacts only with NewsProvider — never directly with NewsAPI.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from app.domain.news import NormalizedArticle


class NewsProvider(ABC):
    """
    Abstract interface for news data providers.

    Implementations:
        - NewsApiProvider

    Future providers (e.g. GDELT, Reuters, Bloomberg) can be substituted
    without changing the service or classification layers.
    """

    @abstractmethod
    async def search_news(
        self,
        query: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        language: str = "en",
        page: int = 1,
        page_size: int = 20,
    ) -> List[NormalizedArticle]:
        """
        Search for news articles matching the given query.

        Args:
            query:      Free-text search query. Passed to provider as-is.
            from_date:  Earliest publication date (inclusive).
            to_date:    Latest publication date (inclusive).
            language:   ISO 639-1 language code (default 'en').
            page:       1-indexed page number.
            page_size:  Articles per page (provider limits may cap this).

        Returns:
            List of NormalizedArticle. Classification is NOT performed here —
            that is the responsibility of EventClassificationService.

        Raises:
            ProviderFeatureUnavailableError: Endpoint not available under current plan.
            ProviderUnavailableError:        Network error, timeout, or malformed response.
            ProviderRateLimitError:          Provider returned HTTP 429.
            ProviderAuthenticationError:     Provider rejected the API key (HTTP 401).
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release underlying HTTP client resources."""
        ...
