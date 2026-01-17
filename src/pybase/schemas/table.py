"""Table schemas for request/response validation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TableBase(BaseModel):
    """Base schema for table."""

    name: str = Field(..., min_length=1, max_length=255, description="Table name")
    description: Optional[str] = Field(None, max_length=2000, description="Table description")


class TableCreate(TableBase):
    """Schema for creating a table."""

    base_id: UUID = Field(..., description="Base ID")
    primary_field_id: Optional[UUID] = Field(None, description="Primary field ID")


class TableUpdate(BaseModel):
    """Schema for updating a table."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Table name")
    description: Optional[str] = Field(None, max_length=2000, description="Table description")
    primary_field_id: Optional[UUID] = Field(None, description="Primary field ID")


class TableResponse(TableBase):
    """Schema for table response."""

    id: UUID
    base_id: UUID
    primary_field_id: Optional[UUID]
    position: int
    record_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TableListResponse(BaseModel):
    """Schema for table list response."""

    items: list[TableResponse]
    total: int
    page: int
    page_size: int
