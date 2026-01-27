"""
ExportJob models for bulk data export tasks.

ExportJobs track:
- Table export progress and status
- Export format handling (CSV, Excel, JSON, XML)
- Worker task coordination via Celery
- Download link generation and expiry
- Field selection, filtering, and attachment export
"""

import json
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import BaseModel

if TYPE_CHECKING:
    from pybase.models.user import User


# =============================================================================
# Enums
# =============================================================================


class ExportJobStatus(str, Enum):
    """Status of an export job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    EXPIRED = "expired"


class ExportFormat(str, Enum):
    """Types of export formats supported."""

    CSV = "csv"
    XLSX = "xlsx"
    JSON = "json"
    XML = "xml"


# =============================================================================
# Models
# =============================================================================


class ExportJob(BaseModel):
    """
    ExportJob - a table data export task.

    Tracks table export progress with database persistence
    for reliability across worker restarts.
    """

    __tablename__: str = "export_jobs"  # type: ignore[assignment]

    # Foreign keys
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User who created the job",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=ExportJobStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    # Export type
    export_format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Format: csv, xlsx, json, xml",
    )

    # Table reference
    table_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Table being exported",
    )

    # View reference (optional - for filtered/sorted exports)
    view_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("views.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="View defining filters/sorts for export",
    )

    # File paths
    file_path: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        doc="Path to exported file or S3 location",
    )
    download_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        doc="Temporary download URL for exported file",
    )

    # Progress tracking
    progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Progress percentage (0-100)",
    )
    total_records: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Total records to export",
    )
    processed_records: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of records successfully exported",
    )

    # Retry logic
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of retry attempts",
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        doc="Maximum number of retry attempts",
    )
    last_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last retry attempt",
    )

    # Celery task tracking
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        doc="Celery task ID for worker coordination",
    )

    # Export options (JSON)
    # Stores: field_ids, flatten_linked_records, include_attachments, etc.
    options: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Export results (JSON)
    # Stores: record_count, file_size, attachment_count, etc.
    results: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Human-readable error message",
    )
    error_stack_trace: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Full error stack trace for debugging",
    )

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Total execution duration in milliseconds",
    )

    # Download expiry
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Download link expiration time",
    )

    # Relationships
    user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[user_id],
    )

    # Indexes
    __table_args__ = (
        Index("ix_export_jobs_status_created", "status", "created_at"),
        Index("ix_export_jobs_user_created", "user_id", "created_at"),
        Index("ix_export_jobs_table_status", "table_id", "status"),
        Index("ix_export_jobs_format_status", "export_format", "status"),
    )

    def __repr__(self) -> str:
        return f"<ExportJob {self.id} ({self.status})>"

    @property
    def status_enum(self) -> ExportJobStatus:
        """Get status as enum."""
        return ExportJobStatus(self.status)

    @property
    def format_enum(self) -> ExportFormat:
        """Get format as enum."""
        return ExportFormat(self.export_format)

    def get_options(self) -> dict[str, Any]:
        """Parse options JSON."""
        try:
            return json.loads(self.options or "{}")
        except json.JSONDecodeError:
            return {}

    def set_options(self, options: dict[str, Any]) -> None:
        """Set options from dict."""
        self.options = json.dumps(options)

    def get_results(self) -> dict[str, Any]:
        """Parse results JSON."""
        try:
            return json.loads(self.results or "{}")
        except json.JSONDecodeError:
            return {}

    def set_results(self, results: dict[str, Any]) -> None:
        """Set results from dict."""
        self.results = json.dumps(results)

    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return (
            self.status_enum in [ExportJobStatus.FAILED, ExportJobStatus.RETRYING]
            and self.retry_count < self.max_retries
        )

    def increment_retry(self) -> None:
        """Increment retry count and update timestamp."""
        self.retry_count += 1
        self.last_retry_at = datetime.now()
        if self.retry_count >= self.max_retries:
            self.status = ExportJobStatus.FAILED.value
        else:
            self.status = ExportJobStatus.RETRYING.value

    def calculate_progress(self) -> int:
        """Calculate progress percentage based on records processed."""
        if self.total_records is None or self.total_records == 0:
            return self.progress
        return int((self.processed_records / self.total_records) * 100)

    def is_expired(self) -> bool:
        """Check if download link has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
