"""Cursor pagination schemas for efficient large dataset retrieval."""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class CursorRequest(BaseModel):
    """Schema for cursor-based pagination request."""

    cursor: Optional[str] = Field(None, description="Encoded cursor for pagination (opaque token)")
    limit: int = Field(50, ge=1, le=1000, description="Number of items per page (max 1000)")
    sort_by: Optional[str] = Field("created_at", description="Field to sort by")
    sort_order: Optional[str] = Field("asc", description="Sort order: 'asc' or 'desc'")


class CursorResponse(BaseModel):
    """Schema for cursor-based pagination response metadata."""

    next_cursor: Optional[str] = Field(None, description="Cursor for next page (null if last page)")
    prev_cursor: Optional[str] = Field(None, description="Cursor for previous page (null if first page)")
    has_next: bool = Field(..., description="Whether next page exists")
    has_prev: bool = Field(..., description="Whether previous page exists")
    limit: int = Field(..., description="Number of items per page")
    total_count: Optional[int] = Field(None, description="Total count (null for large datasets)")


class CursorPage(BaseModel, Generic[T]):
    """Generic schema for cursor-paginated response."""

    items: list[T] = Field(default_factory=list, description="Paginated items")
    meta: CursorResponse = Field(..., description="Pagination metadata")

    model_config = {"from_attributes": True}
