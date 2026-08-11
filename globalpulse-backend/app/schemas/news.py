"""GlobalPulse Pydantic Schemas — News article response."""
from typing import Optional, List

from pydantic import BaseModel, Field

from app.domain.news import GlobalEventCategory


class CompanyTagSchema(BaseModel):
    """A recognized company mentioned in the article."""

    name: str = Field(..., description="Company name")
    sector: str = Field(..., description="Industry sector e.g. 'Technology'")
    country: str = Field(..., description="Country of headquarters")


class ArticleSchema(BaseModel):
    """API-facing representation of a normalized news article."""

    id: str = Field(..., description="Stable deduplication key (URL hash)")
    headline: str = Field(..., description="Article headline / title")
    summary: Optional[str] = Field(
        None,
        description=(
            "Provider-supplied description snippet. "
            "Full article body is not stored (copyright compliance)."
        ),
    )
    source_name: str = Field(..., description="News source name e.g. 'Reuters'")
    source_url: Optional[str] = Field(None, description="News source homepage URL")
    article_url: str = Field(..., description="Full article URL")
    author: Optional[str] = Field(None, description="Author name; null if not provided")
    published_at_utc: str = Field(..., description="Publication time in UTC (ISO 8601)")
    published_at_ist: str = Field(..., description="Publication time in IST / Asia/Kolkata (ISO 8601)")
    primary_category: GlobalEventCategory = Field(
        ..., description="Primary classification category"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Additional matched category names beyond the primary",
    )
    countries: List[str] = Field(
        default_factory=list,
        description="ISO 3166-1 alpha-2 country codes detected in the article",
    )
    companies: List[CompanyTagSchema] = Field(
        default_factory=list,
        description="Recognized company tags matched from static config",
    )
    sectors: List[str] = Field(
        default_factory=list,
        description="Unique sectors derived from matched companies",
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Matched keyword signals from classification rules",
    )
    source: str = Field(..., description="Data provider identifier e.g. 'NEWSAPI'")


class NewsListResponse(BaseModel):
    """Paginated list of normalized news articles."""

    articles: List[ArticleSchema]
    total: int = Field(..., description="Total articles in this response page")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Articles per page")
