"""
Dashboard model - custom analytics dashboards with widgets and charts.

Dashboards provide a visual overview of data through configurable widgets.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import BaseModel, SoftDeleteModel, utc_now

if TYPE_CHECKING:
    from pybase.models.base import Base
    from pybase.models.user import User


class PermissionLevel(str, Enum):
    """Permission levels for dashboard sharing."""

    OWNER = "owner"
    EDIT = "edit"
    VIEW = "view"


class Dashboard(SoftDeleteModel):
    """
    Dashboard model - a custom analytics dashboard with widgets.

    Each dashboard has:
    - Name and description
    - Layout configuration for widgets
    - Sharing and permission settings
    - Color/theme customization
    """

    __tablename__: str = "dashboards"  # type: ignore[assignment]

    # Foreign keys
    base_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("bases.id", ondelete="CASCADE"),
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

    # Visibility and sharing
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Default dashboard shown when opening base analytics",
    )
    is_personal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Personal dashboards are only visible to the creator",
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Public dashboards can be viewed by anyone with the link",
    )
    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Locked dashboards cannot be modified by non-owners",
    )

    # Layout configuration (JSON stored as text)
    # Stores: widget positions, sizes, grid layout
    # Format: {
    #   "grid_columns": 12,
    #   "row_height": 60,
    #   "widgets": [
    #     {"id": "widget-1", "x": 0, "y": 0, "w": 6, "h": 4},
    #     {"id": "widget-2", "x": 6, "y": 0, "w": 6, "h": 4}
    #   ]
    # }
    layout_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Dashboard settings (JSON stored as text)
    # Stores: refresh interval, auto-refresh enabled, theme settings
    settings: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Filters that apply to entire dashboard (JSON stored as text)
    # Stores: global filter conditions applied to all widgets
    global_filters: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="[]",
    )

    # Color/theme
    color: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Dashboard accent color",
    )
    icon: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Dashboard icon (emoji or icon identifier)",
    )

    # Template reference (if created from template)
    template_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Template ID if dashboard was created from a template",
    )

    # Sharing link
    share_token: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        doc="Unique token for sharing dashboard publicly",
    )

    # Last viewed tracking
    last_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last time dashboard was viewed",
    )

    # Relationships
    base: Mapped["Base"] = relationship(
        "Base",
        back_populates="dashboards",
    )
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    members: Mapped[list["DashboardMember"]] = relationship(
        "DashboardMember",
        back_populates="dashboard",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_dashboards_base_name", "base_id", "name"),
        Index("ix_dashboards_base_default", "base_id", "is_default"),
        Index("ix_dashboards_share_token", "share_token"),
        Index("ix_dashboards_template", "template_id"),
    )

    def __repr__(self) -> str:
        return f"<Dashboard {self.name}>"

    def get_layout_config_dict(self) -> dict:
        """Parse layout_config JSON."""
        import json

        try:
            return json.loads(self.layout_config or "{}")
        except json.JSONDecodeError:
            return {}

    def get_settings_dict(self) -> dict:
        """Parse settings JSON."""
        import json

        try:
            return json.loads(self.settings or "{}")
        except json.JSONDecodeError:
            return {}

    def get_global_filters_list(self) -> list:
        """Parse global_filters JSON."""
        import json

        try:
            return json.loads(self.global_filters or "[]")
        except json.JSONDecodeError:
            return []

    def update_last_viewed(self) -> None:
        """Update last viewed timestamp."""
        self.last_viewed_at = utc_now()

    @property
    def is_shared(self) -> bool:
        """Check if dashboard has been shared with others."""
        return (
            self.is_public
            or (self.members and len(self.members) > 0)
            or self.share_token is not None
        )


class DashboardMember(BaseModel):
    """
    Dashboard membership - links users to dashboards with permissions.

    A user can have access to multiple dashboards with different permission levels.
    """

    # Foreign keys
    dashboard_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Permission level
    permission: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=PermissionLevel.VIEW.value,
    )

    # Sharing tracking
    shared_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    shared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    dashboard: Mapped["Dashboard"] = relationship(
        "Dashboard",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="dashboard_memberships",
        foreign_keys=[user_id],
    )
    shared_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[shared_by_id],
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("dashboard_id", "user_id", name="uq_dashboard_member"),
        Index("ix_dashboard_members_dashboard", "dashboard_id"),
        Index("ix_dashboard_members_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<DashboardMember dashboard={self.dashboard_id} user={self.user_id} permission={self.permission}>"

    @property
    def permission_enum(self) -> PermissionLevel:
        """Get permission level as enum."""
        return PermissionLevel(self.permission)

    @property
    def is_owner(self) -> bool:
        """Check if member is dashboard owner."""
        return self.permission == PermissionLevel.OWNER.value

    @property
    def can_edit(self) -> bool:
        """Check if member can edit dashboard."""
        return self.permission in (
            PermissionLevel.OWNER.value,
            PermissionLevel.EDIT.value,
        )

    @property
    def can_view(self) -> bool:
        """Check if member can view dashboard."""
        return True  # All members can view
