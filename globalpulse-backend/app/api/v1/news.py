"""
GlobalPulse News Endpoint
GET /api/v1/news
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import get_news_service
from app.domain.news import GlobalEventCategory
from app.schemas.news import ArticleSchema, CompanyTagSchema, NewsListResponse
from app.services.news_service import NewsService

router = APIRouter(tags=["News"])


def _to_schema(article) -> ArticleSchema:
    return ArticleSchema(
        id=article.id,
        headline=article.headline,
        summary=article.summary,
        source_name=article.source_name,
        source_url=article.source_url,
        article_url=article.article_url,
        author=article.author,
        published_at_utc=article.published_at_utc,
        published_at_ist=article.published_at_ist,
        primary_category=article.primary_category,
        tags=article.tags,
        countries=article.countries,
        companies=[
            CompanyTagSchema(name=c.name, sector=c.sector, country=c.country)
            for c in article.companies
        ],
        sectors=article.sectors,
        keywords=article.keywords,
        source=article.source,
    )


@router.get(
    "/news",
    response_model=NewsListResponse,
    summary="Search global news articles",
    description=(
        "Search and retrieve globally normalized news articles from NewsAPI. "
        "Articles are classified into GlobalPulse event categories using deterministic "
        "keyword rules. Country tags, company tags, and sector tags are extracted from article text. "
        "\n\n**Provider note**: NewsAPI free plan is limited to 100 req/day, 1-month history, "
        "and developer (localhost) access only. Headlines and provider-supplied descriptions "
        "are stored — full article bodies are not (copyright compliance)."
    ),
    responses={
        403: {"description": "Feature not available under current NewsAPI plan"},
        429: {"description": "NewsAPI rate limit exceeded (free plan: 100 req/day)"},
        502: {"description": "NewsAPI authentication failure"},
        503: {"description": "NewsAPI provider unavailable"},
    },
)
async def search_news(
    q: Optional[str] = Query(
        None,
        description="Free-text search query e.g. 'Federal Reserve interest rate'.",
    ),
    category: Optional[GlobalEventCategory] = Query(
        None,
        description="Filter articles by classified GlobalPulse category.",
    ),
    country: Optional[str] = Query(
        None,
        description="Filter by ISO 3166-1 alpha-2 country code e.g. 'IN', 'US', 'SG'.",
    ),
    from_date: Optional[date] = Query(
        None,
        alias="from",
        description="Earliest publication date (YYYY-MM-DD).",
    ),
    to_date: Optional[date] = Query(
        None,
        alias="to",
        description="Latest publication date (YYYY-MM-DD).",
    ),
    page: int = Query(1, ge=1, description="Page number (1-indexed)."),
    page_size: int = Query(
        20,
        alias="pageSize",
        ge=1,
        le=100,
        description="Articles per page.",
    ),
    service: NewsService = Depends(get_news_service),
) -> NewsListResponse:
    articles = await service.search_news(
        query=q,
        category=category,
        country=country,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    return NewsListResponse(
        articles=[_to_schema(a) for a in articles],
        total=len(articles),
        page=page,
        page_size=page_size,
    )
