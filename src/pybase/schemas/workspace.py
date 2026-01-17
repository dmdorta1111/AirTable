"""Workspace schemas for request/response validation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr

from pybase.models.workspace import WorkspaceRole


class WorkspaceBase(BaseModel):
    """Base schema for workspace."""

    name: str = Field(..., min_length=1, max_length=255, description="Workspace name")
    description: Optional[str] = Field(None, max_length=2000, description="Workspace description")


class WorkspaceCreate(WorkspaceBase):
    """Schema for creating a workspace."""

    pass


class WorkspaceUpdate(BaseModel):
    """Schema for updating a workspace."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Workspace name")
    description: Optional[str] = Field(None, max_length=2000, description="Workspace description")


class WorkspaceMemberBase(BaseModel):
    """Base schema for workspace member."""

    user_id: UUID = Field(..., description="User ID")
    role: WorkspaceRole = Field(..., description="Member role")


class WorkspaceMemberCreate(WorkspaceMemberBase):
    """Schema for adding a member to a workspace."""

    pass


class WorkspaceMemberUpdate(BaseModel):
    """Schema for updating a workspace member role."""

    role: WorkspaceRole = Field(..., description="Member role")


class UserSummary(BaseModel):
    """Minimal user information."""

    id: str
    email: EmailStr
    full_name: Optional[str] = None

    model_config = {"from_attributes": True}


class WorkspaceMemberResponse(BaseModel):
    """Schema for workspace member response."""

    id: str
    workspace_id: str
    user: UserSummary
    role: WorkspaceRole
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceResponse(WorkspaceBase):
    """Schema for workspace response."""

    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    members_count: int = Field(default=0, description="Number of members in workspace")

    model_config = {"from_attributes": True}


class WorkspaceDetailResponse(WorkspaceResponse):
    """Detailed workspace response with members."""

    members: list[WorkspaceMemberResponse] = Field(
        default_factory=list, description="Workspace members"
    )


class WorkspaceListResponse(BaseModel):
    """Schema for workspace list response."""

    items: list[WorkspaceResponse]
    total: int
    page: int
    page_size: int
