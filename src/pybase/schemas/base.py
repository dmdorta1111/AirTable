"""Base schemas for request/response validation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BaseBase(BaseModel):
    """Base schema for base (Airtable base)."""

    name: str = Field(..., min_length=1, max_length=255, description="Base name")
    description: Optional[str] = Field(None, max_length=2000, description="Base description")
    icon: Optional[str] = Field(None, max_length=255, description="Base icon URL or emoji")


class BaseCreate(BaseBase):
    """Schema for creating a base."""

    workspace_id: str = Field(..., description="Workspace ID")


class BaseUpdate(BaseModel):
    """Schema for updating a base."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Base name")
    description: Optional[str] = Field(None, max_length=2000, description="Base description")
    icon: Optional[str] = Field(None, max_length=255, description="Base icon URL or emoji")


class BaseResponse(BaseBase):
    """Schema for base response."""

    id: str
    workspace_id: str
    schema_version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BaseListResponse(BaseModel):
    """Schema for base list response."""

    items: list[BaseResponse]
    total: int
    page: int
    page_size: int
