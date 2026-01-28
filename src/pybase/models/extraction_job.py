"""
ExtractionJob models for CAD/PDF bulk extraction tasks.

ExtractionJobs track:
- File extraction progress and status
- Retry logic with exponential backoff
- Worker task coordination via Celery
- Results and error tracking
"""

import json
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from pybase.db.base import BaseModel

if TYPE_CHECKING:
    from pybase.models.user import User


# =============================================================================
# Enums
# =============================================================================


class ExtractionJobStatus(str, Enum):
    """Status of an extraction job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ExtractionFormat(str, Enum):
    """Types of extraction formats supported."""

    PDF = "pdf"
    DXF = "dxf"
    IFC = "ifc"
    STEP = "step"
    WERK24 = "werk24"
    BOM = "bom"


# =============================================================================
# Models
# =============================================================================


class ExtractionJob(BaseModel):
    """
    ExtractionJob - a CAD/PDF extraction task.

    Tracks file extraction progress with database persistence
    for reliability across worker restarts.
    """

    __tablename__: str = "extraction_jobs"  # type: ignore[assignment]

    # Foreign keys
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User who created the job",
    )
    created_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Creator user ID (alias for user_id)",
    )

    # File identification (for single-file jobs)
    filename: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="Original filename",
    )
    file_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        unique=False,
        index=True,
        doc="S3/B2 URL to file",
    )
    file_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="File size in bytes",
    )

    # Optional linking to records/attachments
    record_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        index=True,
        doc="Optional FK to records.id",
    )
    field_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Optional field ID",
    )
    attachment_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Optional attachment object ID",
    )
    cloud_file_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="Link to CloudFiles table",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=ExtractionJobStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    # Job type
    extraction_format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Format: pdf, dxf, ifc, step, werk24, bom",
    )

    # File paths
    file_path: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        doc="Path to input file",
    )
    result_path: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        doc="Path to results file or S3 location",
    )

    # Progress tracking
    progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Progress percentage (0-100)",
    )
    total_items: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Total items to process (for bulk jobs)",
    )
    processed_items: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of items successfully processed",
    )
    failed_items: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of items that failed",
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
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="Scheduled time for next retry attempt",
    )

    # Celery task tracking
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        doc="Celery task ID for worker coordination",
    )

    # Job options (JSON)
    # Stores: extraction options, field mappings, etc.
    options: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Results (JSON)
    # Stores: extracted data, metadata, statistics
    results: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )
    result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
        doc="Alias for results field (singular form)",
    )

    # Synonyms for backward compatibility
    format = synonym("extraction_format")

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

    # Relationships
    user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[user_id],
    )

    # Indexes
    __table_args__ = (
        Index("ix_extraction_jobs_status_created", "status", "created_at"),
        Index("ix_extraction_jobs_user_created", "user_id", "created_at"),
        Index("ix_extraction_jobs_format_status", "extraction_format", "status"),
        Index("ix_extraction_jobs_status_retry", "status", "next_retry_at"),
        Index("ix_extraction_jobs_file_url", "file_url"),
        Index("ix_extraction_jobs_cloud_file", "cloud_file_id"),
    )

    def __repr__(self) -> str:
        return f"<ExtractionJob {self.id} ({self.status})>"

    @property
    def status_enum(self) -> ExtractionJobStatus:
        """Get status as enum."""
        return ExtractionJobStatus(self.status)

    @property
    def format_enum(self) -> ExtractionFormat:
        """Get format as enum."""
        return ExtractionFormat(self.extraction_format)

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

    def get_result(self) -> dict[str, Any]:
        """Parse result JSON (alias for get_results)."""
        return self.get_results()

    def set_result(self, result: dict[str, Any]) -> None:
        """Set result from dict (alias for set_results)."""
        self.set_results(result)
        # Keep both fields in sync
        self.result = json.dumps(result)

    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return (
            self.status_enum in [ExtractionJobStatus.FAILED, ExtractionJobStatus.RETRYING]
            and self.retry_count < self.max_retries
        )

    def increment_retry(self) -> None:
        """Increment retry count and update timestamp."""
        self.retry_count += 1
        self.last_retry_at = datetime.now()
        if self.retry_count >= self.max_retries:
            self.status = ExtractionJobStatus.FAILED.value
        else:
            self.status = ExtractionJobStatus.RETRYING.value

    def calculate_progress(self) -> int:
        """Calculate progress percentage based on items processed."""
        if self.total_items is None or self.total_items == 0:
            return self.progress
        return int((self.processed_items / self.total_items) * 100)
