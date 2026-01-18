"""Record schemas for request/response validation."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from pybase.models.field import FieldType


class RecordBase(BaseModel):
    """Base schema for record."""

    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Field values as {field_id: value}",
    )
    row_height: Optional[int] = Field(None, ge=16, le=400, description="Row height in pixels")


class RecordCreate(RecordBase):
    """Schema for creating a record."""

    table_id: str = Field(..., description="Table ID")


class RecordUpdate(BaseModel):
    """Schema for updating a record."""

    data: Optional[dict[str, Any]] = Field(None, description="Field values as {field_id: value}")
    row_height: Optional[int] = Field(None, ge=16, le=400, description="Row height in pixels")


class RecordResponse(BaseModel):
    """Schema for record response."""

    id: str
    table_id: str
    data: dict[str, Any]
    row_height: int
    created_by_id: Optional[str]
    last_modified_by_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RecordListResponse(BaseModel):
    """Schema for record list response."""

    items: list[RecordResponse]
    total: int
    page: int
    page_size: int
