"""Trash schemas for request/response validation."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TrashItem(BaseModel):
    """Schema for a deleted record in trash."""

    id: str = Field(..., description="Record ID")
    table_id: str = Field(..., description="Table ID")
    data: dict[str, Any] = Field(..., description="Field values as {field_id: value}")
    deleted_at: datetime = Field(..., description="When the record was deleted")
    deleted_by_id: Optional[str] = Field(None, description="User who deleted the record")
    created_at: datetime = Field(..., description="When the record was originally created")
    updated_at: datetime = Field(..., description="When the record was last updated")
    row_height: int = Field(..., description="Row height in pixels")

    model_config = {"from_attributes": True}


class TrashListResponse(BaseModel):
    """Schema for trash list response."""

    items: list[TrashItem]
    total: int
    page: int
    page_size: int


class RestoreResponse(BaseModel):
    """Schema for restore operation response."""

    id: str = Field(..., description="Restored record ID")
    message: str = Field(..., description="Success message")
