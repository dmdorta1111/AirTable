"""
Comment model - stores comments on records.

Comments support the activity feed and collaboration features.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import SoftDeleteModel

if TYPE_CHECKING:
    from pybase.models.record import Record
    from pybase.models.user import User


class Comment(SoftDeleteModel):
    """
    Comment model - a comment on a record.

    Comments provide collaboration and activity tracking on records.
    Users can create, edit, and delete their own comments.
    """

    __tablename__: str = "comments"  # type: ignore[assignment]

    # Foreign key to record
    record_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Foreign key to user (comment author)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Comment content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Edit tracking
    is_edited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    record: Mapped["Record"] = relationship(
        "Record",
        back_populates="comments",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="comments",
    )

    # Indexes
    __table_args__ = (
        Index("ix_comments_record", "record_id"),
        Index("ix_comments_user", "user_id"),
        Index("ix_comments_record_created", "record_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Comment {self.id} by user {self.user_id} on record {self.record_id}>"

    def mark_as_edited(self, edited_at: datetime) -> None:
        """
        Mark comment as edited with timestamp.

        Args:
            edited_at: Timestamp when the comment was edited
        """
        self.is_edited = True
        self.edited_at = edited_at
