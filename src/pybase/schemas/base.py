"""Base schemas for request/response validation."""

from datetime import datetime
from typing import Any, Optional
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


class ValidationErrorDetail(BaseModel):
    """Schema for individual validation error detail."""

    loc: list[str | int] = Field(..., description="Location of the error (field path)")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type identifier")

    input: Optional[Any] = Field(None, description="Input value that caused the error")
    ctx: Optional[dict[str, Any]] = Field(None, description="Additional error context")


class ValidationErrorResponse(BaseModel):
    """Schema for validation error response."""

    detail: list[ValidationErrorDetail] = Field(
        ..., description="List of validation errors"
    )
    error_code: str = Field(
        "VALIDATION_ERROR", description="Error code for validation failures"
    )
