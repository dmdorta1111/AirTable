"""
Base model - container for tables (like an Airtable base).

A base is a collection of related tables within a workspace.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import SoftDeleteModel

if TYPE_CHECKING:
    from pybase.models.workspace import Workspace
    from pybase.models.table import Table
    from pybase.models.automation import Automation


class Base(SoftDeleteModel):
    """
    Base model - a collection of related tables.

    Similar to a database or an Airtable base.
    Contains multiple tables that can reference each other.
    """

    __tablename__ = "bases"

    # Foreign key to workspace
    workspace_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
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

    # Schema version for migrations
    schema_version: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
    )

    # Settings (JSON stored as text)
    settings: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="bases",
    )
    tables: Mapped[list["Table"]] = relationship(
        "Table",
        back_populates="base",
        cascade="all, delete-orphan",
        order_by="Table.position",
    )
    automations: Mapped[list["Automation"]] = relationship(
        "Automation",
        back_populates="base",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (Index("ix_bases_workspace_name", "workspace_id", "name"),)

    def __repr__(self) -> str:
        return f"<Base {self.name}>"

    @property
    def table_count(self) -> int:
        """Get number of tables in base."""
        return len(self.tables) if self.tables else 0
