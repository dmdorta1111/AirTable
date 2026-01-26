"""
UniqueConstraint model for tracking unique field constraints.

This model stores metadata about fields that have unique constraints,
enabling data integrity validation at the application level.
"""

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import BaseModel

if TYPE_CHECKING:
    from pybase.models.field import Field


class UniqueConstraintStatus(str, Enum):
    """Status of a unique constraint."""

    ACTIVE = "active"
    DISABLED = "disabled"
    PENDING = "pending"


class UniqueConstraint(BaseModel):
    """
    UniqueConstraint model - tracks unique field constraints.

    Stores metadata about fields that must have unique values,
    including configuration for case sensitivity and validation rules.
    """

    # Foreign key to field
    field_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("fields.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=UniqueConstraintStatus.ACTIVE.value,
    )

    # Configuration
    case_sensitive: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Optional error message template
    error_message: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Relationships
    field: Mapped["Field"] = relationship(
        "Field",
        back_populates="unique_constraints",
    )

    # Constraints and indexes
    __table_args__ = (
        Index("ix_unique_constraints_field", "field_id"),
        Index("ix_unique_constraints_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<UniqueConstraint field_id={self.field_id} "
            f"status={self.status} case_sensitive={self.case_sensitive}>"
        )

    @property
    def is_active(self) -> bool:
        """Check if constraint is active."""
        return self.status == UniqueConstraintStatus.ACTIVE.value

    @property
    def is_disabled(self) -> bool:
        """Check if constraint is disabled."""
        return self.status == UniqueConstraintStatus.DISABLED.value

    @property
    def is_pending(self) -> bool:
        """Check if constraint is pending activation."""
        return self.status == UniqueConstraintStatus.PENDING.value
