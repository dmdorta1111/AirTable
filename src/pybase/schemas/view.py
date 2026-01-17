"""View schemas for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ViewType(str, Enum):
    """Supported view types."""

    GRID = "grid"
    KANBAN = "kanban"
    CALENDAR = "calendar"
    GALLERY = "gallery"
    FORM = "form"
    GANTT = "gantt"
    TIMELINE = "timeline"


class RowHeight(str, Enum):
    """Row height options for grid view."""

    SHORT = "short"
    MEDIUM = "medium"
    TALL = "tall"
    EXTRA_TALL = "extra_tall"


class FilterOperator(str, Enum):
    """Filter operators."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN_OR_EQUAL = "lte"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_BEFORE = "is_before"
    IS_AFTER = "is_after"
    IS_TODAY = "is_today"
    IS_THIS_WEEK = "is_this_week"
    IS_THIS_MONTH = "is_this_month"


class SortDirection(str, Enum):
    """Sort direction."""

    ASC = "asc"
    DESC = "desc"


class Conjunction(str, Enum):
    """Filter conjunction."""

    AND = "and"
    OR = "or"


# =============================================================================
# Filter/Sort/Group Schemas
# =============================================================================


class FilterCondition(BaseModel):
    """A single filter condition."""

    field_id: UUID = Field(..., description="Field to filter on")
    operator: FilterOperator = Field(..., description="Filter operator")
    value: Any = Field(None, description="Value to compare against")
    conjunction: Conjunction = Field(
        default=Conjunction.AND, description="How to combine with other filters"
    )


class SortRule(BaseModel):
    """A single sort rule."""

    field_id: UUID = Field(..., description="Field to sort by")
    direction: SortDirection = Field(default=SortDirection.ASC, description="Sort direction")


class GroupConfig(BaseModel):
    """Grouping configuration."""

    field_id: Optional[UUID] = Field(None, description="Field to group by")
    order: SortDirection = Field(default=SortDirection.ASC, description="Group order")
    collapsed_groups: list[str] = Field(default_factory=list, description="Collapsed group values")


class FieldConfig(BaseModel):
    """Field display configuration for a view."""

    field_order: list[UUID] = Field(default_factory=list, description="Order of fields")
    field_widths: dict[str, int] = Field(default_factory=dict, description="Field widths in pixels")
    hidden_fields: list[UUID] = Field(default_factory=list, description="Hidden field IDs")
    frozen_fields: list[UUID] = Field(
        default_factory=list, description="Frozen field IDs (grid only)"
    )


# =============================================================================
# View Type Specific Configs
# =============================================================================


class GridConfig(BaseModel):
    """Grid view specific configuration."""

    wrap_cells: bool = Field(default=False, description="Wrap text in cells")
    show_row_numbers: bool = Field(default=True, description="Show row numbers")
    highlight_rows_on_hover: bool = Field(default=True, description="Highlight rows on hover")


class KanbanConfig(BaseModel):
    """Kanban view specific configuration."""

    stack_field_id: Optional[UUID] = Field(
        None, description="Field to stack cards by (single select/status)"
    )
    cover_field_id: Optional[UUID] = Field(None, description="Attachment field for card cover")
    card_fields: list[UUID] = Field(default_factory=list, description="Fields to show on cards")
    hide_empty_stacks: bool = Field(default=False, description="Hide columns with no cards")
    card_size: str = Field(default="medium", description="Card size: small, medium, large")


class CalendarConfig(BaseModel):
    """Calendar view specific configuration."""

    date_field_id: Optional[UUID] = Field(None, description="Date field for events")
    end_date_field_id: Optional[UUID] = Field(None, description="End date for date ranges")
    title_field_id: Optional[UUID] = Field(None, description="Field for event title")
    color_field_id: Optional[UUID] = Field(None, description="Single select for event colors")
    default_view: str = Field(default="month", description="Default view: month, week, day")


class GalleryConfig(BaseModel):
    """Gallery view specific configuration."""

    cover_field_id: Optional[UUID] = Field(None, description="Attachment field for card cover")
    card_fields: list[UUID] = Field(default_factory=list, description="Fields to show on cards")
    card_size: str = Field(default="medium", description="Card size: small, medium, large")
    cover_fit: str = Field(default="cover", description="Cover fit: cover, contain")


class FormConfig(BaseModel):
    """Form view specific configuration."""

    title: Optional[str] = Field(None, description="Form title")
    description: Optional[str] = Field(None, description="Form description")
    submit_button_text: str = Field(default="Submit", description="Submit button text")
    success_message: str = Field(
        default="Thank you for your submission!", description="Success message"
    )
    redirect_url: Optional[str] = Field(None, description="URL to redirect after submission")
    show_branding: bool = Field(default=True, description="Show PyBase branding")
    cover_image_url: Optional[str] = Field(None, description="Cover image URL")
    required_fields: list[UUID] = Field(default_factory=list, description="Required field IDs")


class GanttConfig(BaseModel):
    """Gantt view specific configuration."""

    start_date_field_id: Optional[UUID] = Field(None, description="Start date field")
    end_date_field_id: Optional[UUID] = Field(None, description="End date field")
    dependency_field_id: Optional[UUID] = Field(
        None, description="Linked record field for dependencies"
    )
    progress_field_id: Optional[UUID] = Field(None, description="Percent/number field for progress")
    color_field_id: Optional[UUID] = Field(None, description="Single select for bar colors")
    time_scale: str = Field(
        default="day", description="Time scale: day, week, month, quarter, year"
    )
    show_dependencies: bool = Field(default=True, description="Show dependency lines")


class TimelineConfig(BaseModel):
    """Timeline view specific configuration."""

    date_field_id: Optional[UUID] = Field(None, description="Date field")
    end_date_field_id: Optional[UUID] = Field(None, description="End date for ranges")
    group_field_id: Optional[UUID] = Field(None, description="Field to group by")
    title_field_id: Optional[UUID] = Field(None, description="Field for event title")
    color_field_id: Optional[UUID] = Field(None, description="Single select for colors")
    time_scale: str = Field(
        default="month", description="Time scale: day, week, month, quarter, year"
    )


# =============================================================================
# Main View Schemas
# =============================================================================


class ViewBase(BaseModel):
    """Base schema for view."""

    name: str = Field(..., min_length=1, max_length=255, description="View name")
    description: Optional[str] = Field(None, max_length=2000, description="View description")
    view_type: ViewType = Field(default=ViewType.GRID, description="View type")


class ViewCreate(ViewBase):
    """Schema for creating a view."""

    table_id: UUID = Field(..., description="Table ID")
    is_default: bool = Field(default=False, description="Set as default view")
    is_locked: bool = Field(default=False, description="Lock view from editing")
    is_personal: bool = Field(default=False, description="Personal view (only visible to creator)")
    position: Optional[int] = Field(None, description="Position in view list")
    color: Optional[str] = Field(None, max_length=50, description="View accent color")
    row_height: RowHeight = Field(default=RowHeight.MEDIUM, description="Row height for grid view")

    # Configuration
    field_config: Optional[FieldConfig] = Field(None, description="Field display configuration")
    filters: list[FilterCondition] = Field(default_factory=list, description="Filter conditions")
    sorts: list[SortRule] = Field(default_factory=list, description="Sort rules")
    groups: Optional[GroupConfig] = Field(None, description="Grouping configuration")

    # Type-specific config (only one should be set based on view_type)
    grid_config: Optional[GridConfig] = Field(None, description="Grid-specific config")
    kanban_config: Optional[KanbanConfig] = Field(None, description="Kanban-specific config")
    calendar_config: Optional[CalendarConfig] = Field(None, description="Calendar-specific config")
    gallery_config: Optional[GalleryConfig] = Field(None, description="Gallery-specific config")
    form_config: Optional[FormConfig] = Field(None, description="Form-specific config")
    gantt_config: Optional[GanttConfig] = Field(None, description="Gantt-specific config")
    timeline_config: Optional[TimelineConfig] = Field(None, description="Timeline-specific config")


class ViewUpdate(BaseModel):
    """Schema for updating a view."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="View name")
    description: Optional[str] = Field(None, max_length=2000, description="View description")
    is_default: Optional[bool] = Field(None, description="Set as default view")
    is_locked: Optional[bool] = Field(None, description="Lock view from editing")
    is_personal: Optional[bool] = Field(None, description="Personal view")
    position: Optional[int] = Field(None, description="Position in view list")
    color: Optional[str] = Field(None, max_length=50, description="View accent color")
    row_height: Optional[RowHeight] = Field(None, description="Row height for grid view")

    # Configuration updates
    field_config: Optional[FieldConfig] = Field(None, description="Field display configuration")
    filters: Optional[list[FilterCondition]] = Field(None, description="Filter conditions")
    sorts: Optional[list[SortRule]] = Field(None, description="Sort rules")
    groups: Optional[GroupConfig] = Field(None, description="Grouping configuration")

    # Type-specific config updates
    grid_config: Optional[GridConfig] = Field(None, description="Grid-specific config")
    kanban_config: Optional[KanbanConfig] = Field(None, description="Kanban-specific config")
    calendar_config: Optional[CalendarConfig] = Field(None, description="Calendar-specific config")
    gallery_config: Optional[GalleryConfig] = Field(None, description="Gallery-specific config")
    form_config: Optional[FormConfig] = Field(None, description="Form-specific config")
    gantt_config: Optional[GanttConfig] = Field(None, description="Gantt-specific config")
    timeline_config: Optional[TimelineConfig] = Field(None, description="Timeline-specific config")


class ViewResponse(ViewBase):
    """Schema for view response."""

    id: UUID
    table_id: UUID
    created_by_id: Optional[UUID]
    is_default: bool
    is_locked: bool
    is_personal: bool
    position: int
    color: Optional[str]
    row_height: str

    # Parsed configuration
    field_config: Optional[dict[str, Any]] = None
    filters: list[dict[str, Any]] = Field(default_factory=list)
    sorts: list[dict[str, Any]] = Field(default_factory=list)
    groups: Optional[dict[str, Any]] = None
    type_config: Optional[dict[str, Any]] = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ViewListResponse(BaseModel):
    """Schema for view list response."""

    items: list[ViewResponse]
    total: int
    page: int
    page_size: int


# =============================================================================
# View Data Response (records with view filters/sorts applied)
# =============================================================================


class ViewDataRequest(BaseModel):
    """Request for fetching view data."""

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=100, ge=1, le=1000, description="Records per page")
    override_filters: Optional[list[FilterCondition]] = Field(
        None, description="Additional filters to apply"
    )
    override_sorts: Optional[list[SortRule]] = Field(None, description="Override view sorts")
    search: Optional[str] = Field(None, description="Search query across all fields")


class ViewDataResponse(BaseModel):
    """Response containing view data (records)."""

    view_id: UUID
    records: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    has_more: bool


# =============================================================================
# Duplicate View
# =============================================================================


class ViewDuplicate(BaseModel):
    """Schema for duplicating a view."""

    name: str = Field(..., min_length=1, max_length=255, description="Name for the duplicate")
    include_filters: bool = Field(default=True, description="Copy filters")
    include_sorts: bool = Field(default=True, description="Copy sorts")
    include_groups: bool = Field(default=True, description="Copy groups")
    include_field_config: bool = Field(default=True, description="Copy field configuration")
