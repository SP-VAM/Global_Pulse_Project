"""
NewsAPI raw response models.
These Pydantic models represent the NewsAPI wire format.
They are NEVER exposed via GlobalPulse APIs — only used internally for parsing.

Field names follow the NewsAPI v2 response conventions.
All fields are Optional to handle plan-level and source-level gaps.
"""
from typing import Any, List, Optional

from pydantic import BaseModel


class NewsAPISource(BaseModel):
    """Embedded source object in a NewsAPI article."""

    id: Optional[str] = None      # NewsAPI source ID; null for many sources
    name: Optional[str] = None    # Display name e.g. "Reuters"


class NewsAPIArticle(BaseModel):
    """
    Raw NewsAPI article.

    Free-plan limitation: description is a short snippet (≤160 chars).
    The 'content' field is truncated and should not be stored or re-served.
    """

    source: Optional[NewsAPISource] = None
    author: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None     # Short snippet — never the full body
    url: Optional[str] = None
    urlToImage: Optional[str] = None
    publishedAt: Optional[str] = None     # ISO 8601 string with 'Z' suffix
    content: Optional[Any] = None         # Present but intentionally not stored


class NewsAPIResponse(BaseModel):
    """
    Root response from NewsAPI /everything or /top-headlines.

    status: 'ok' on success, 'error' on failure (sometimes with 200 HTTP status).
    totalResults: may exceed what the plan allows to retrieve.
    """

    status: Optional[str] = None
    totalResults: Optional[int] = None
    articles: List[NewsAPIArticle] = []
    code: Optional[str] = None      # Error code when status != 'ok'
    message: Optional[str] = None   # Error message when status != 'ok'
