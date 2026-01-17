"""
View model - different ways to visualize table data.

Views allow users to see the same data in different formats:
- Grid (spreadsheet-like)
- Kanban (board with cards)
- Calendar (date-based)
- Gallery (card grid with images)
- Form (data entry)
- Gantt (project timeline)
- Timeline (chronological)
"""

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import SoftDeleteModel

if TYPE_CHECKING:
    from pybase.models.table import Table
    from pybase.models.user import User


class ViewType(str, Enum):
    """Supported view types."""

    GRID = "grid"
    KANBAN = "kanban"
    CALENDAR = "calendar"
    GALLERY = "gallery"
    FORM = "form"
    GANTT = "gantt"
    TIMELINE = "timeline"


class View(SoftDeleteModel):
    """
    View model - a specific way to visualize table data.

    Each view has:
    - Type (grid, kanban, calendar, etc.)
    - Field visibility and order
    - Filters, sorts, and groups
    - Type-specific configuration
    """

    __tablename__: str = "views"  # type: ignore[assignment]

    # Foreign keys
    table_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Basic info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    view_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ViewType.GRID.value,
    )

    # Visibility
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Locked views cannot be modified by non-owners",
    )
    is_personal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Personal views are only visible to the creator",
    )

    # Ordering
    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Field configuration (JSON stored as text)
    # Stores: field_order, field_widths, hidden_fields
    field_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Filtering configuration (JSON stored as text)
    # Stores: filter conditions (field, operator, value)
    filters: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="[]",
    )

    # Sorting configuration (JSON stored as text)
    # Stores: sort rules (field, direction)
    sorts: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="[]",
    )

    # Grouping configuration (JSON stored as text)
    # Stores: group_by field, collapse states
    groups: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Row height for grid view
    row_height: Mapped[str] = mapped_column(
        String(20),
        default="medium",  # short, medium, tall, extra_tall
        nullable=False,
    )

    # View-type specific configuration (JSON stored as text)
    # Grid: frozen columns, wrap cells
    # Kanban: stack field, cover field, card fields
    # Calendar: date field, title field, color field
    # Gallery: cover field, card fields, card size
    # Form: form title, submit text, success message
    # Gantt: start field, end field, dependencies
    # Timeline: date field, group field
    type_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Color/theme
    color: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="View accent color",
    )

    # Relationships
    table: Mapped["Table"] = relationship(
        "Table",
        back_populates="views",
    )
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )

    # Indexes
    __table_args__ = (
        Index("ix_views_table_name", "table_id", "name"),
        Index("ix_views_table_position", "table_id", "position"),
        Index("ix_views_table_type", "table_id", "view_type"),
        Index("ix_views_table_default", "table_id", "is_default"),
    )

    def __repr__(self) -> str:
        return f"<View {self.name} ({self.view_type})>"

    @property
    def type_enum(self) -> ViewType:
        """Get view type as enum."""
        return ViewType(self.view_type)

    def get_field_config_dict(self) -> dict:
        """Parse field_config JSON."""
        import json

        try:
            return json.loads(self.field_config or "{}")
        except json.JSONDecodeError:
            return {}

    def set_field_config_dict(self, config: dict) -> None:
        """Set field_config from dict."""
        import json

        self.field_config = json.dumps(config)

    def get_filters_list(self) -> list:
        """Parse filters JSON."""
        import json

        try:
            return json.loads(self.filters or "[]")
        except json.JSONDecodeError:
            return []

    def set_filters_list(self, filters: list) -> None:
        """Set filters from list."""
        import json

        self.filters = json.dumps(filters)

    def get_sorts_list(self) -> list:
        """Parse sorts JSON."""
        import json

        try:
            return json.loads(self.sorts or "[]")
        except json.JSONDecodeError:
            return []

    def set_sorts_list(self, sorts: list) -> None:
        """Set sorts from list."""
        import json

        self.sorts = json.dumps(sorts)

    def get_groups_dict(self) -> dict:
        """Parse groups JSON."""
        import json

        try:
            return json.loads(self.groups or "{}")
        except json.JSONDecodeError:
            return {}

    def set_groups_dict(self, groups: dict) -> None:
        """Set groups from dict."""
        import json

        self.groups = json.dumps(groups)

    def get_type_config_dict(self) -> dict:
        """Parse type_config JSON."""
        import json

        try:
            return json.loads(self.type_config or "{}")
        except json.JSONDecodeError:
            return {}

    def set_type_config_dict(self, config: dict) -> None:
        """Set type_config from dict."""
        import json

        self.type_config = json.dumps(config)


# =============================================================================
# View Configuration Types (for documentation)
# =============================================================================

"""
Field Config Structure:
{
    "field_order": ["field_id_1", "field_id_2", ...],
    "field_widths": {"field_id": 200, ...},
    "hidden_fields": ["field_id_1", ...],
    "frozen_fields": ["field_id_1", ...]  # Grid only
}

Filter Structure:
[
    {
        "field_id": "...",
        "operator": "equals|not_equals|contains|not_contains|is_empty|is_not_empty|gt|lt|gte|lte|between|in|not_in",
        "value": "...",
        "conjunction": "and|or"  # For multiple filters
    },
    ...
]

Sort Structure:
[
    {"field_id": "...", "direction": "asc|desc"},
    ...
]

Group Structure:
{
    "field_id": "...",
    "order": "asc|desc|first_created|last_created",
    "collapsed_groups": ["value1", "value2", ...]
}

Grid Type Config:
{
    "wrap_cells": false,
    "show_row_numbers": true,
    "highlight_rows_on_hover": true
}

Kanban Type Config:
{
    "stack_field_id": "...",  # Single select or status field
    "cover_field_id": "...",  # Attachment field for card images
    "card_fields": ["field_id_1", ...],  # Fields to show on cards
    "hide_empty_stacks": false,
    "card_size": "small|medium|large"
}

Calendar Type Config:
{
    "date_field_id": "...",  # Date or datetime field
    "end_date_field_id": "...",  # Optional for date ranges
    "title_field_id": "...",  # Field for event title
    "color_field_id": "...",  # Single select for event colors
    "default_view": "month|week|day"
}

Gallery Type Config:
{
    "cover_field_id": "...",  # Attachment field
    "card_fields": ["field_id_1", ...],
    "card_size": "small|medium|large",
    "cover_fit": "cover|contain"
}

Form Type Config:
{
    "title": "Form Title",
    "description": "Form description",
    "submit_button_text": "Submit",
    "success_message": "Thank you!",
    "redirect_url": "https://...",
    "show_branding": true,
    "cover_image_url": "https://...",
    "required_fields": ["field_id_1", ...],
    "conditional_fields": [
        {"field_id": "...", "show_when": {"field_id": "...", "operator": "...", "value": "..."}}
    ]
}

Gantt Type Config:
{
    "start_date_field_id": "...",
    "end_date_field_id": "...",
    "dependency_field_id": "...",  # Linked record field
    "progress_field_id": "...",  # Percent or number field
    "color_field_id": "...",
    "row_height": "medium",
    "time_scale": "day|week|month|quarter|year",
    "show_dependencies": true
}

Timeline Type Config:
{
    "date_field_id": "...",
    "end_date_field_id": "...",
    "group_field_id": "...",  # Single select or linked record
    "title_field_id": "...",
    "color_field_id": "...",
    "time_scale": "day|week|month|quarter|year"
}
"""
