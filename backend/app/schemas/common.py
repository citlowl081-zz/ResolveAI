"""Common Pydantic schemas — unified response envelope and pagination."""

from pydantic import BaseModel, Field


class APIResponse[T](BaseModel):
    """Unified API response envelope.

    All API endpoints return this structure, ensuring consistent
    client-side parsing of success/error states.
    """

    success: bool = Field(..., description="Whether the request succeeded")
    code: str = Field(default="OK", description="Machine-readable status code")
    message: str = Field(default="", description="Human-readable description")
    data: T | None = Field(default=None, description="Response payload")
    trace_id: str | None = Field(default=None, description="Request trace ID for debugging")


class Pagination(BaseModel):
    """Pagination metadata."""

    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")


class PaginatedResponse[T](BaseModel):
    """Wrapper for paginated list responses."""

    items: list[T] = Field(default_factory=list)
    pagination: Pagination
