"""
Werk24 API usage tracking model.

Tracks API calls to Werk24 for quota management and usage analytics.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import BaseModel

if TYPE_CHECKING:
    from pybase.models.user import User
    from pybase.models.workspace import Workspace


class Werk24Usage(BaseModel):
    """
    Werk24 API usage tracking model.

    Records each API call to Werk24 for quota management and analytics.
    Tracks request details, response status, and resource consumption.
    """

    __tablename__ = "werk24_usages"

    # Foreign keys
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Request details
    request_type: Mapped[str] = mapped_column(
        String(100),  # e.g., "extract_async"
        nullable=False,
    )
    ask_types: Mapped[str] = mapped_column(
        Text,  # JSON array of ask types requested
        nullable=False,
        default="[]",
    )
    source_file: Mapped[str | None] = mapped_column(
        String(500),  # File path or name
        nullable=True,
    )
    file_size_bytes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    file_type: Mapped[str | None] = mapped_column(
        String(50),  # e.g., "pdf", "png"
        nullable=True,
    )

    # Response details
    success: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    status_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Resource consumption
    api_calls_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    tokens_used: Mapped[int | None] = mapped_column(
        Integer,  # If Werk24 provides token usage
        nullable=True,
    )
    processing_time_ms: Mapped[int | None] = mapped_column(
        Integer,  # Duration in milliseconds
        nullable=True,
    )

    # Results summary
    dimensions_extracted: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    gdts_extracted: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    materials_extracted: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    threads_extracted: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Request metadata
    api_key_used: Mapped[str | None] = mapped_column(
        String(50),  # Prefix or identifier of API key used
        nullable=True,
    )
    request_ip: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Billing/quota info
    cost_units: Mapped[float | None] = mapped_column(
        Float,  # Werk24 API cost units if available
        nullable=True,
    )
    quota_remaining: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Request timestamp (additional to created_at from BaseModel)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
    )
    workspace: Mapped["Workspace | None"] = relationship(
        "Workspace",
        foreign_keys=[workspace_id],
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_werk24_usage_user_created", "user_id", "created_at"),
        Index("ix_werk24_usage_workspace_created", "workspace_id", "created_at"),
        Index("ix_werk24_usage_success", "success"),
        Index("ix_werk24_usage_request_type", "request_type"),
    )

    def __repr__(self) -> str:
        return f"<Werk24Usage {self.request_type} by user {self.user_id}>"

    @property
    def is_successful(self) -> bool:
        """Check if the API call was successful."""
        return self.success

    @property
    def total_extractions(self) -> int:
        """Get total number of items extracted."""
        return (
            self.dimensions_extracted
            + self.gdts_extracted
            + self.materials_extracted
            + self.threads_extracted
        )

    def mark_completed(self, success: bool = True, error: str | None = None) -> None:
        """Mark the usage record as completed.

        Args:
            success: Whether the API call was successful.
            error: Error message if the call failed.
        """
        from pybase.db.base import utc_now

        self.completed_at = utc_now()
        self.success = success
        if error:
            self.error_message = error

    def record_extraction_counts(
        self,
        dimensions: int = 0,
        gdts: int = 0,
        materials: int = 0,
        threads: int = 0,
    ) -> None:
        """Record the counts of extracted items.

        Args:
            dimensions: Number of dimensions extracted.
            gdts: Number of GD&T features extracted.
            materials: Number of material callouts extracted.
            threads: Number of thread specifications extracted.
        """
        self.dimensions_extracted = dimensions
        self.gdts_extracted = gdts
        self.materials_extracted = materials
        self.threads_extracted = threads
