"""
Table model - container for fields and records.

A table defines a schema (fields) and contains records.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import SoftDeleteModel

if TYPE_CHECKING:
    from pybase.models.base import Base
    from pybase.models.field import Field
    from pybase.models.record import Record
    from pybase.models.view import View


class Table(SoftDeleteModel):
    """
    Table model - defines schema and contains records.

    Similar to a database table or spreadsheet.
    Has a defined set of fields and contains records.
    """

    __tablename__ = "tables"

    # Foreign key to base
    base_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("bases.id", ondelete="CASCADE"),
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

    # Ordering
    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Primary field (the main identifying field for records)
    primary_field_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )

    # Settings (JSON stored as text)
    settings: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Relationships
    base: Mapped["Base"] = relationship(
        "Base",
        back_populates="tables",
    )
    fields: Mapped[list["Field"]] = relationship(
        "Field",
        back_populates="table",
        cascade="all, delete-orphan",
        order_by="Field.position",
    )
    records: Mapped[list["Record"]] = relationship(
        "Record",
        back_populates="table",
        cascade="all, delete-orphan",
    )
    views: Mapped[list["View"]] = relationship(
        "View",
        back_populates="table",
        cascade="all, delete-orphan",
        order_by="View.position",
    )

    # Indexes
    __table_args__ = (
        Index("ix_tables_base_name", "base_id", "name"),
        Index("ix_tables_base_position", "base_id", "position"),
    )

    def __repr__(self) -> str:
        return f"<Table {self.name}>"

    @property
    def field_count(self) -> int:
        """Get number of fields in table."""
        return len(self.fields) if self.fields else 0

    @property
    def record_count(self) -> int:
        """Get number of records in table."""
        return len(self.records) if self.records else 0
