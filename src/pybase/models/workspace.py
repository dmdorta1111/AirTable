"""
Workspace and WorkspaceMember models.

Workspaces are the top-level organizational unit containing bases.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import BaseModel, SoftDeleteModel, utc_now

if TYPE_CHECKING:
    from pybase.models.user import User
    from pybase.models.base import Base


class WorkspaceRole(str, Enum):
    """Roles within a workspace."""

    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    COMMENTER = "commenter"
    VIEWER = "viewer"


class Workspace(SoftDeleteModel):
    """
    Workspace model - top-level container for bases.

    A workspace contains multiple bases and has members with different roles.
    """

    # Owner
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
    icon: Mapped[str | None] = mapped_column(
        String(100),  # Emoji or icon identifier
        nullable=True,
    )
    color: Mapped[str | None] = mapped_column(
        String(20),  # Hex color code
        nullable=True,
    )

    # Settings (JSON stored as text)
    settings: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Relationships
    members: Mapped[list["WorkspaceMember"]] = relationship(
        "WorkspaceMember",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    bases: Mapped[list["Base"]] = relationship(
        "Base",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Workspace {self.name}>"


class WorkspaceMember(BaseModel):
    """
    Workspace membership - links users to workspaces with roles.

    A user can be a member of multiple workspaces with different roles.
    """

    # Foreign keys
    workspace_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Role
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=WorkspaceRole.VIEWER.value,
    )

    # Invitation tracking
    invited_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="workspace_memberships",
        foreign_keys=[user_id],
    )
    invited_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[invited_by_id],
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
        Index("ix_workspace_members_workspace", "workspace_id"),
        Index("ix_workspace_members_user", "user_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<WorkspaceMember workspace={self.workspace_id} user={self.user_id} role={self.role}>"
        )

    @property
    def is_owner(self) -> bool:
        """Check if member is workspace owner."""
        return self.role == WorkspaceRole.OWNER.value

    @property
    def is_admin(self) -> bool:
        """Check if member is admin or higher."""
        return self.role in (WorkspaceRole.OWNER.value, WorkspaceRole.ADMIN.value)

    @property
    def can_edit(self) -> bool:
        """Check if member can edit content."""
        return self.role in (
            WorkspaceRole.OWNER.value,
            WorkspaceRole.ADMIN.value,
            WorkspaceRole.EDITOR.value,
        )

    @property
    def can_comment(self) -> bool:
        """Check if member can comment."""
        return self.role != WorkspaceRole.VIEWER.value
