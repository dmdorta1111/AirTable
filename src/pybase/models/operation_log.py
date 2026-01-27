"""
OperationLog model - stores operation history for undo/redo functionality.

Tracks all operations for 24 hours to enable users to undo/redo changes.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import BaseModel

if TYPE_CHECKING:
    from pybase.models.user import User


class OperationLog(BaseModel):
    """
    OperationLog model - tracks operations for undo/redo functionality.

    Stores the before/after state of operations to enable reversibility.
    Operations are retained for 24 hours and limited to 100 per user.
    """

    __tablename__: str = "operation_logs"  # type: ignore[assignment]

    # Foreign key to user who performed the operation
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Operation metadata
    operation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Operation data (JSON stored as text)
    # Format: JSON string representation of entity state
    before_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )
    after_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="operation_logs",
    )

    # Indexes
    __table_args__ = (
        Index("ix_operation_logs_user", "user_id"),
        Index("ix_operation_logs_user_created", "user_id", "created_at"),
        Index("ix_operation_logs_operation", "operation_type"),
        Index("ix_operation_logs_entity", "entity_type", "entity_id"),
    )

    def __repr__(self) -> str:
        return f"<OperationLog {self.id}: {self.operation_type} on {self.entity_type} {self.entity_id}>"

    def get_before_data(self) -> dict:
        """
        Get before data as dictionary.

        Returns:
            Dictionary representation of before data or empty dict if None
        """
        import json

        try:
            return json.loads(self.before_data) if self.before_data else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_after_data(self) -> dict:
        """
        Get after data as dictionary.

        Returns:
            Dictionary representation of after data or empty dict if None
        """
        import json

        try:
            return json.loads(self.after_data) if self.after_data else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_before_data(self, data: dict) -> None:
        """
        Set before data from dictionary.

        Args:
            data: Dictionary to serialize as JSON
        """
        import json

        self.before_data = json.dumps(data) if data else None

    def set_after_data(self, data: dict) -> None:
        """
        Set after data from dictionary.

        Args:
            data: Dictionary to serialize as JSON
        """
        import json

        self.after_data = json.dumps(data) if data else None
