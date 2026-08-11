"""GlobalPulse Pydantic Schemas — Global event response."""
from typing import List

from pydantic import BaseModel, Field

from app.schemas.news import ArticleSchema


class GlobalEventSchema(BaseModel):
    """
    API-facing representation of a financially relevant global event.

    Wraps a normalized article with a relevance annotation.
    Only articles that pass the financial relevance filter appear here.
    """

    article: ArticleSchema = Field(..., description="Normalized news article")
    is_financially_relevant: bool = Field(
        ..., description="True when the article passed the financial relevance filter"
    )
    relevance_score: int = Field(
        ...,
        description=(
            "Raw relevance score from the rule-based filter "
            "(higher = more financial signals detected). "
            "This is informational — do NOT treat as market-impact prediction."
        ),
    )


class GlobalEventListResponse(BaseModel):
    """Paginated list of financially relevant global events."""

    events: List[GlobalEventSchema]
    total: int = Field(..., description="Total events in this response page")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Events per page")
