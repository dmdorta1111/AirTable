"""Field schemas for request/response validation."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from pybase.models.field import FieldType


class FieldBase(BaseModel):
    """Base schema for field."""

    name: str = Field(..., min_length=1, max_length=255, description="Field name")
    description: Optional[str] = Field(None, max_length=2000, description="Field description")
    field_type: FieldType = Field(..., description="Field type")
    options: Optional[dict[str, Any]] = Field(
        default_factory=dict, description="Type-specific options (JSON)"
    )
    is_required: bool = Field(default=False, description="Whether field is required")
    is_unique: bool = Field(default=False, description="Whether field values must be unique")


class FieldCreate(FieldBase):
    """Schema for creating a field."""

    table_id: UUID = Field(..., description="Table ID")
    position: Optional[int] = Field(None, description="Field position in table")


class FieldUpdate(BaseModel):
    """Schema for updating a field."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Field name")
    description: Optional[str] = Field(None, max_length=2000, description="Field description")
    options: Optional[dict[str, Any]] = Field(None, description="Type-specific options (JSON)")
    is_required: Optional[bool] = Field(None, description="Whether field is required")
    is_unique: Optional[bool] = Field(None, description="Whether field values must be unique")
    width: Optional[int] = Field(None, ge=50, le=1000, description="Field width in pixels")
    is_visible: Optional[bool] = Field(None, description="Whether field is visible")
    is_primary: Optional[bool] = Field(None, description="Whether this is the primary field")


class FieldResponse(FieldBase):
    """Schema for field response."""

    id: UUID
    table_id: UUID
    position: int
    width: int
    is_visible: bool
    is_primary: bool
    is_computed: bool
    is_locked: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FieldListResponse(BaseModel):
    """Schema for field list response."""

    items: list[FieldResponse]
    total: int
    page: int
    page_size: int
