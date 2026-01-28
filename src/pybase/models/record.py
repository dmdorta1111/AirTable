"""
Record model - stores actual data rows in a table.

Records store field values as JSON for flexibility.
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import SoftDeleteModel

if TYPE_CHECKING:
    from pybase.models.comment import Comment
    from pybase.models.table import Table
    from pybase.models.user import User


class Record(SoftDeleteModel):
    """
    Record model - a single row in a table.

    Field values are stored as JSON for schema flexibility.
    This allows adding/removing fields without migrations.
    """

    __tablename__: str = "records"  # type: ignore[assignment]

    # Foreign key to table
    table_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Field values (JSON stored as text)
    # Format: {"field_id": value, ...}
    # Values are stored in their JSON representation
    data: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    # Audit trail
    created_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_modified_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Row height for display
    row_height: Mapped[int] = mapped_column(
        default=32,
        nullable=False,
    )

    # Relationships
    table: Mapped["Table"] = relationship(
        "Table",
        back_populates="records",
    )
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    last_modified_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[last_modified_by_id],
    )
    deleted_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[deleted_by_id],
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="record",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_records_table", "table_id"),
        Index("ix_records_table_created", "table_id", "created_at"),
        Index("ix_records_created_by", "created_by_id"),
        Index("ix_records_deleted_by", "deleted_by_id"),
    )

    def __repr__(self) -> str:
        return f"<Record {self.id} in table {self.table_id}>"

    def get_field_value(self, field_id: str) -> Any:
        """
        Get value for a specific field.

        Args:
            field_id: ID of the field

        Returns:
            Field value or None if not set
        """
        import json

        try:
            data = json.loads(self.data)
            return data.get(field_id)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_field_value(self, field_id: str, value: Any) -> None:
        """
        Set value for a specific field.

        Args:
            field_id: ID of the field
            value: Value to set
        """
        import json

        try:
            data = json.loads(self.data)
        except (json.JSONDecodeError, TypeError):
            data = {}

        data[field_id] = value
        self.data = json.dumps(data)

    def get_all_values(self) -> dict:
        """
        Get all field values.

        Returns:
            Dictionary of field_id -> value
        """
        import json

        try:
            return json.loads(self.data)
        except (json.JSONDecodeError, TypeError):
            return {}
