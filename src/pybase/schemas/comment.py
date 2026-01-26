"""Comment schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CommentBase(BaseModel):
    """Base schema for comment."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Comment content text",
    )


class CommentCreate(CommentBase):
    """Schema for creating a comment."""

    record_id: str = Field(..., description="Record ID to comment on")


class CommentUpdate(BaseModel):
    """Schema for updating a comment."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Updated comment content",
    )


class CommentResponse(BaseModel):
    """Schema for comment response."""

    id: str
    record_id: str
    user_id: str
    content: str
    is_edited: bool
    edited_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CommentListResponse(BaseModel):
    """Schema for comment list response."""

    items: list[CommentResponse]
    total: int
    page: int
    page_size: int
