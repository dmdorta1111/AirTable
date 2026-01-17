"""
SQLAlchemy Base class and common model mixins.

All models should inherit from Base to be included in migrations.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid4())


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Provides common configuration and type annotations.
    """

    # Use PostgreSQL UUID type for primary keys
    type_annotation_map = {
        str: String,
    }

    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        """Generate table name from class name (snake_case)."""
        name = cls.__name__
        # Convert CamelCase to snake_case
        result = [name[0].lower()]
        for char in name[1:]:
            if char.isupper():
                result.extend(["_", char.lower()])
            else:
                result.append(char)
        return "".join(result) + "s"  # Pluralize

    # Schema configuration handled by alembic env.py


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamps.

    Timestamps are automatically set on insert and update.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
        nullable=False,
    )


class UUIDMixin:
    """
    Mixin that adds a UUID primary key.

    Uses PostgreSQL's native UUID type for efficient storage.
    """

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Mixin that adds soft delete functionality.

    Records are marked as deleted instead of being removed from the database.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark record as deleted."""
        self.deleted_at = utc_now()

    def restore(self) -> None:
        """Restore soft-deleted record."""
        self.deleted_at = None


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """
    Abstract base model with UUID primary key and timestamps.

    Most models should inherit from this class.
    """

    __abstract__ = True

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    def update(self, **kwargs: Any) -> None:
        """Update model attributes from kwargs."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class SoftDeleteModel(BaseModel, SoftDeleteMixin):
    """
    Abstract base model with soft delete support.

    Use this for models where data should be preserved after deletion.
    """

    __abstract__ = True
