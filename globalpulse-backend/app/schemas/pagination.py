"""
GlobalPulse Common Pagination Pydantic Schema.
"""
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class PaginationSchema(BaseModel):
    """Pagination details for API responses."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total: int = Field(..., description="Total items available matching criteria")
    has_next: bool = Field(..., description="True if subsequent pages exist")
