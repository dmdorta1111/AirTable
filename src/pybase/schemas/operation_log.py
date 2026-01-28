"""OperationLog schemas for request/response validation."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class OperationLogBase(BaseModel):
    """Base schema for operation log."""

    operation_type: str = Field(..., description="Type of operation (create, update, delete)")
    entity_type: str = Field(..., description="Type of entity (record, field, view)")
    entity_id: str = Field(..., description="ID of the entity")
    before_data: Optional[dict[str, Any]] = Field(None, description="State before operation")
    after_data: Optional[dict[str, Any]] = Field(None, description="State after operation")


class OperationLogCreate(OperationLogBase):
    """Schema for creating an operation log."""

    user_id: str = Field(..., description="User who performed the operation")


class OperationLogResponse(BaseModel):
    """Schema for operation log response."""

    id: str
    user_id: str
    operation_type: str
    entity_type: str
    entity_id: str
    before_data: Optional[dict[str, Any]]
    after_data: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OperationLogListResponse(BaseModel):
    """Schema for operation log list response."""

    items: list[OperationLogResponse]
    total: int
    page: int
    page_size: int


class UndoRequest(BaseModel):
    """Schema for undo request."""

    operation_id: str = Field(..., description="Operation ID to undo")


class RedoRequest(BaseModel):
    """Schema for redo request."""

    operation_id: str = Field(..., description="Operation ID to redo")
