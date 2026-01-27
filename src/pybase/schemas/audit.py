"""Audit log schemas for request/response validation."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditLogQuery(BaseModel):
    """Schema for audit log query parameters."""

    user_id: Optional[str] = Field(None, description="Filter by user ID")
    user_email: Optional[str] = Field(None, description="Filter by user email")
    action: Optional[str] = Field(None, description="Filter by action type")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_id: Optional[str] = Field(None, description="Filter by resource ID")
    table_id: Optional[str] = Field(None, description="Filter by table ID")
    request_id: Optional[str] = Field(None, description="Filter by request ID")
    start_date: Optional[datetime] = Field(None, description="Filter by start date (inclusive)")
    end_date: Optional[datetime] = Field(None, description="Filter by end date (inclusive)")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""

    id: str
    user_id: Optional[str]
    user_email: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    table_id: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]
    integrity_hash: str
    previous_log_hash: Optional[str]
    meta: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """Schema for audit log list response."""

    items: list[AuditLogResponse]
    total: int
    limit: int
    offset: int
