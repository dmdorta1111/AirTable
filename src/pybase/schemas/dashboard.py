"""Dashboard schemas for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PermissionLevel(str, Enum):
    """Permission levels for dashboard sharing."""

    OWNER = "owner"
    EDIT = "edit"
    VIEW = "view"


# =============================================================================
# Dashboard Configuration Schemas
# =============================================================================


class WidgetPosition(BaseModel):
    """Position and size of a widget in the dashboard grid."""

    id: str = Field(..., description="Widget ID")
    x: int = Field(..., ge=0, description="X position in grid")
    y: int = Field(..., ge=0, description="Y position in grid")
    w: int = Field(..., ge=1, description="Width in grid units")
    h: int = Field(..., ge=1, description="Height in grid units")


class LayoutConfig(BaseModel):
    """Dashboard layout configuration."""

    grid_columns: int = Field(default=12, ge=1, le=24, description="Number of grid columns")
    row_height: int = Field(default=60, ge=20, le=200, description="Row height in pixels")
    widgets: list[WidgetPosition] = Field(
        default_factory=list, description="Widget positions and sizes"
    )


class DashboardSettings(BaseModel):
    """Dashboard settings configuration."""

    refresh_interval: Optional[int] = Field(
        None, ge=0, description="Auto-refresh interval in seconds (0 = disabled)"
    )
    auto_refresh_enabled: bool = Field(default=False, description="Enable auto-refresh")
    theme: Optional[str] = Field(None, description="Dashboard theme: light, dark, auto")
    show_grid: bool = Field(default=True, description="Show grid lines in builder mode")
    compact_mode: bool = Field(default=False, description="Compact widget spacing")
    show_filters: bool = Field(default=True, description="Show global filters bar")
    show_title: bool = Field(default=True, description="Show dashboard title")
    show_description: bool = Field(default=False, description="Show dashboard description")


class FilterCondition(BaseModel):
    """A single filter condition for dashboard-wide filtering."""

    field_id: UUID = Field(..., description="Field to filter on")
    operator: str = Field(..., description="Filter operator")
    value: Any = Field(None, description="Value to compare against")


# =============================================================================
# Main Dashboard Schemas
# =============================================================================


class DashboardBase(BaseModel):
    """Base schema for dashboard."""

    name: str = Field(..., min_length=1, max_length=255, description="Dashboard name")
    description: Optional[str] = Field(None, max_length=5000, description="Dashboard description")


class DashboardCreate(DashboardBase):
    """Schema for creating a dashboard."""

    base_id: UUID = Field(..., description="Base ID")
    is_default: bool = Field(default=False, description="Set as default dashboard for base")
    is_personal: bool = Field(
        default=False, description="Personal dashboard (only visible to creator)"
    )
    is_public: bool = Field(default=False, description="Public dashboard (viewable by anyone)")
    is_locked: bool = Field(default=False, description="Lock dashboard from editing by non-owners")
    color: Optional[str] = Field(None, max_length=50, description="Dashboard accent color")
    icon: Optional[str] = Field(None, max_length=100, description="Dashboard icon")
    template_id: Optional[str] = Field(None, description="Template ID if created from template")

    # Configuration
    layout_config: Optional[LayoutConfig] = Field(None, description="Layout configuration")
    settings: Optional[DashboardSettings] = Field(None, description="Dashboard settings")
    global_filters: list[FilterCondition] = Field(
        default_factory=list, description="Global filter conditions"
    )


class DashboardUpdate(BaseModel):
    """Schema for updating a dashboard."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Dashboard name")
    description: Optional[str] = Field(None, max_length=5000, description="Dashboard description")
    is_default: Optional[bool] = Field(None, description="Set as default dashboard")
    is_personal: Optional[bool] = Field(None, description="Personal dashboard")
    is_public: Optional[bool] = Field(None, description="Public dashboard")
    is_locked: Optional[bool] = Field(None, description="Lock dashboard from editing")
    color: Optional[str] = Field(None, max_length=50, description="Dashboard accent color")
    icon: Optional[str] = Field(None, max_length=100, description="Dashboard icon")

    # Configuration updates
    layout_config: Optional[LayoutConfig] = Field(None, description="Layout configuration")
    settings: Optional[DashboardSettings] = Field(None, description="Dashboard settings")
    global_filters: Optional[list[FilterCondition]] = Field(
        None, description="Global filter conditions"
    )


class DashboardResponse(DashboardBase):
    """Schema for dashboard response."""

    id: UUID
    base_id: UUID
    created_by_id: Optional[UUID]
    is_default: bool
    is_personal: bool
    is_public: bool
    is_locked: bool
    is_shared: bool = Field(description="Dashboard has been shared with others")
    color: Optional[str]
    icon: Optional[str]
    template_id: Optional[str]
    share_token: Optional[str]
    last_viewed_at: Optional[datetime]

    # Parsed configuration
    layout_config: Optional[dict[str, Any]] = None
    settings: Optional[dict[str, Any]] = None
    global_filters: list[dict[str, Any]] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DashboardListResponse(BaseModel):
    """Schema for dashboard list response."""

    items: list[DashboardResponse]
    total: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)


# =============================================================================
# Dashboard Sharing Schemas
# =============================================================================


class DashboardMemberResponse(BaseModel):
    """Schema for dashboard member response."""

    id: UUID
    dashboard_id: UUID
    user_id: UUID
    permission: PermissionLevel
    shared_by_id: Optional[UUID]
    shared_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardShareRequest(BaseModel):
    """Schema for sharing a dashboard with users."""

    user_ids: list[UUID] = Field(..., min_length=1, description="User IDs to share with")
    permission: PermissionLevel = Field(
        default=PermissionLevel.VIEW, description="Permission level"
    )
    message: Optional[str] = Field(None, max_length=500, description="Optional message to users")


class DashboardUnshareRequest(BaseModel):
    """Schema for removing dashboard access from users."""

    user_ids: list[UUID] = Field(..., min_length=1, description="User IDs to remove access from")


class DashboardPermissionUpdate(BaseModel):
    """Schema for updating dashboard member permissions."""

    user_id: UUID = Field(..., description="User ID")
    permission: PermissionLevel = Field(..., description="New permission level")


# =============================================================================
# Dashboard Duplication Schema
# =============================================================================


class DashboardDuplicate(BaseModel):
    """Schema for duplicating a dashboard."""

    name: str = Field(..., min_length=1, max_length=255, description="Name for the duplicate")
    include_layout: bool = Field(default=True, description="Copy layout configuration")
    include_settings: bool = Field(default=True, description="Copy dashboard settings")
    include_filters: bool = Field(default=True, description="Copy global filters")
    include_charts: bool = Field(default=True, description="Copy all charts/widgets")


# =============================================================================
# Dashboard Templates Schema
# =============================================================================


class DashboardTemplateResponse(BaseModel):
    """Schema for dashboard template response."""

    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category")
    preview_url: Optional[str] = Field(None, description="Preview image URL")
    tags: list[str] = Field(default_factory=list, description="Template tags")
    use_count: int = Field(default=0, description="Number of times template has been used")
    layout_config: dict[str, Any] = Field(..., description="Template layout configuration")
    settings: dict[str, Any] = Field(..., description="Template settings")


class DashboardCreateFromTemplate(BaseModel):
    """Schema for creating a dashboard from a template."""

    base_id: UUID = Field(..., description="Base ID")
    template_id: str = Field(..., description="Template ID to use")
    name: str = Field(..., min_length=1, max_length=255, description="Dashboard name")
    description: Optional[str] = Field(
        None, max_length=5000, description="Custom dashboard description (overrides template)"
    )
    is_personal: bool = Field(default=False, description="Create as personal dashboard")
