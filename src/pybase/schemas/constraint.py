"""Constraint schemas for request/response validation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from pybase.models.unique_constraint import UniqueConstraintStatus


class UniqueConstraintBase(BaseModel):
    """Base schema for unique constraint."""

    status: str = Field(
        default=UniqueConstraintStatus.ACTIVE.value,
        description="Constraint status (active, disabled, pending)",
    )
    case_sensitive: bool = Field(
        default=True,
        description="Whether uniqueness check is case-sensitive",
    )
    error_message: Optional[str] = Field(
        None,
        max_length=500,
        description="Custom error message for constraint violations",
    )


class UniqueConstraintCreate(UniqueConstraintBase):
    """Schema for creating a unique constraint."""

    field_id: UUID = Field(..., description="Field ID to apply constraint to")


class UniqueConstraintUpdate(BaseModel):
    """Schema for updating a unique constraint."""

    status: Optional[str] = Field(
        None,
        description="Constraint status (active, disabled, pending)",
    )
    case_sensitive: Optional[bool] = Field(
        None,
        description="Whether uniqueness check is case-sensitive",
    )
    error_message: Optional[str] = Field(
        None,
        max_length=500,
        description="Custom error message for constraint violations",
    )


class UniqueConstraintResponse(UniqueConstraintBase):
    """Schema for unique constraint response."""

    id: UUID
    field_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UniqueConstraintListResponse(BaseModel):
    """Schema for unique constraint list response."""

    items: list[UniqueConstraintResponse]
    total: int
    page: int
    page_size: int
