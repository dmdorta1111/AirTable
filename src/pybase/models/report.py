"""
Report model - scheduled report generation and delivery.

Reports allow users to:
- Generate PDF/Excel exports of dashboards
- Schedule automatic report generation (daily, weekly, monthly)
- Email reports to stakeholders
- Track report generation history
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import BaseModel, SoftDeleteModel, utc_now

if TYPE_CHECKING:
    from pybase.models.base import Base
    from pybase.models.dashboard import Dashboard
    from pybase.models.user import User


# =============================================================================
# Enums
# =============================================================================


class ReportFormat(str, Enum):
    """Supported report output formats."""

    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    HTML = "html"
    JSON = "json"


class ScheduleFrequency(str, Enum):
    """Report scheduling frequencies."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    CUSTOM = "custom"  # Uses cron expression
    MANUAL = "manual"  # No automatic scheduling


class ReportStatus(str, Enum):
    """Status of a report generation run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# Models
# =============================================================================


class Report(SoftDeleteModel):
    """
    Report model - scheduled report generation configuration.

    Each report has:
    - Reference to a dashboard to export
    - Output format (PDF, Excel, CSV, etc.)
    - Schedule configuration (frequency, cron, time)
    - Delivery settings (email recipients, subject, message)
    - Run history tracking
    """

    __tablename__: str = "reports"  # type: ignore[assignment]

    # Foreign keys
    base_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dashboard_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Dashboard to generate report from",
    )
    created_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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

    # Format
    format: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ReportFormat.PDF.value,
    )

    # Schedule configuration
    frequency: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ScheduleFrequency.MANUAL.value,
        doc="How often to generate report",
    )

    # Cron expression for CUSTOM frequency
    # Format: "0 9 * * 1" (every Monday at 9am)
    cron_expression: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Cron expression for custom scheduling",
    )

    # Schedule settings (JSON stored as text)
    # Stores: time_of_day, day_of_week, day_of_month, timezone
    # Format: {
    #   "time_of_day": "09:00",
    #   "day_of_week": "monday",  # For weekly
    #   "day_of_month": 1,        # For monthly
    #   "timezone": "America/New_York"
    # }
    schedule_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Delivery configuration (JSON stored as text)
    # Stores: recipients, subject, message, reply_to
    # Format: {
    #   "recipients": ["email@example.com", "other@example.com"],
    #   "subject": "Weekly Dashboard Report",
    #   "message": "Please find attached the weekly dashboard report.",
    #   "reply_to": "noreply@example.com",
    #   "cc": ["manager@example.com"],
    #   "bcc": []
    # }
    delivery_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Export settings (JSON stored as text)
    # Stores format-specific options
    # PDF: {
    #   "page_size": "A4",
    #   "orientation": "portrait",
    #   "include_filters": true,
    #   "include_timestamp": true
    # }
    # Excel: {
    #   "include_charts": true,
    #   "separate_sheets": false
    # }
    export_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Active reports will be generated on schedule",
    )
    is_paused: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Temporarily paused by user",
    )

    # Rate limiting
    max_runs_per_day: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
        doc="Maximum report generations per day",
    )

    # Notification settings
    notify_on_success: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Send notification when report generation succeeds",
    )
    notify_on_failure: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Send notification when report generation fails",
    )
    notification_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Email to notify for errors (defaults to created_by email)",
    )

    # Execution statistics
    total_runs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    successful_runs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    failed_runs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Timing tracking
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last time report was generated",
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Next scheduled run time",
    )
    average_duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Average report generation time in seconds",
    )

    # File storage
    last_output_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Path to most recent generated report file",
    )
    last_output_size_bytes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Size of last generated report in bytes",
    )

    # Retention policy
    retention_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False,
        doc="Number of days to keep generated report files",
    )

    # Relationships
    base: Mapped["Base"] = relationship(
        "Base",
    )
    dashboard: Mapped["Dashboard"] = relationship(
        "Dashboard",
        backref="reports",
    )
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    schedules: Mapped[list["ReportSchedule"]] = relationship(
        "ReportSchedule",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportSchedule.scheduled_at.desc()",
    )

    # Indexes
    __table_args__ = (
        Index("ix_reports_base_dashboard", "base_id", "dashboard_id"),
        Index("ix_reports_frequency", "frequency"),
        Index("ix_reports_active", "is_active", "is_paused"),
        Index("ix_reports_next_run", "next_run_at"),
        Index("ix_reports_last_run", "last_run_at"),
    )

    def __repr__(self) -> str:
        return f"<Report {self.name} ({self.frequency})>"

    @property
    def format_enum(self) -> ReportFormat:
        """Get report format as enum."""
        return ReportFormat(self.format)

    @property
    def frequency_enum(self) -> ScheduleFrequency:
        """Get schedule frequency as enum."""
        return ScheduleFrequency(self.frequency)

    def get_schedule_config_dict(self) -> dict:
        """Parse schedule_config JSON."""
        import json

        try:
            return json.loads(self.schedule_config or "{}")
        except json.JSONDecodeError:
            return {}

    def get_delivery_config_dict(self) -> dict:
        """Parse delivery_config JSON."""
        import json

        try:
            return json.loads(self.delivery_config or "{}")
        except json.JSONDecodeError:
            return {}

    def get_export_config_dict(self) -> dict:
        """Parse export_config JSON."""
        import json

        try:
            return json.loads(self.export_config or "{}")
        except json.JSONDecodeError:
            return {}

    @property
    def is_scheduled(self) -> bool:
        """Check if report has automatic scheduling enabled."""
        return (
            self.is_active
            and not self.is_paused
            and self.frequency != ScheduleFrequency.MANUAL.value
        )

    @property
    def is_overdue(self) -> bool:
        """Check if scheduled report is overdue."""
        if not self.next_run_at or not self.is_scheduled:
            return False
        return utc_now() > self.next_run_at

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_runs == 0:
            return 0.0
        return (self.successful_runs / self.total_runs) * 100

    def update_stats(self, success: bool, duration_seconds: int | None = None) -> None:
        """Update run statistics after a report generation."""
        self.total_runs += 1
        if success:
            self.successful_runs += 1
        else:
            self.failed_runs += 1

        self.last_run_at = utc_now()

        # Update average duration
        if duration_seconds is not None:
            if self.average_duration_seconds is None:
                self.average_duration_seconds = duration_seconds
            else:
                # Rolling average
                self.average_duration_seconds = (
                    self.average_duration_seconds * (self.total_runs - 1)
                    + duration_seconds
                ) // self.total_runs

    def calculate_next_run(self) -> datetime | None:
        """Calculate next scheduled run time based on frequency and config."""
        if not self.is_scheduled:
            return None

        from datetime import timedelta

        config = self.get_schedule_config_dict()
        now = utc_now()

        if self.frequency == ScheduleFrequency.DAILY.value:
            # Schedule for next day at configured time
            return now + timedelta(days=1)
        elif self.frequency == ScheduleFrequency.WEEKLY.value:
            # Schedule for next week same day
            return now + timedelta(weeks=1)
        elif self.frequency == ScheduleFrequency.MONTHLY.value:
            # Schedule for next month same day
            return now + timedelta(days=30)
        elif self.frequency == ScheduleFrequency.QUARTERLY.value:
            # Schedule for next quarter
            return now + timedelta(days=90)
        elif self.frequency == ScheduleFrequency.CUSTOM.value:
            # Would need cron parser library to calculate next run
            # Placeholder - implement with croniter or similar
            return now + timedelta(days=1)

        return None


class ReportSchedule(BaseModel):
    """
    Report schedule run - tracks individual report generation executions.

    Each run records:
    - When it was scheduled and executed
    - Status and result
    - Output file location
    - Error information if failed
    """

    __tablename__: str = "report_schedules"  # type: ignore[assignment]

    # Foreign key
    report_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    triggered_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who manually triggered this run (if not scheduled)",
    )

    # Timing
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="When this run was scheduled to execute",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When report generation actually started",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When report generation finished",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ReportStatus.PENDING.value,
    )

    # Result
    output_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Path to generated report file",
    )
    output_size_bytes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Size of generated report in bytes",
    )

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if generation failed",
    )
    error_details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed error information (stack trace, etc.)",
    )

    # Delivery tracking
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When report was successfully delivered via email",
    )
    delivery_status: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Email delivery status message",
    )
    recipients_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of recipients report was sent to",
    )

    # Performance tracking
    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Total time taken to generate report",
    )
    record_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Number of records included in report",
    )

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of times this run was retried",
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        doc="Maximum number of retry attempts",
    )

    # Relationships
    report: Mapped["Report"] = relationship(
        "Report",
        back_populates="schedules",
    )
    triggered_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[triggered_by_id],
    )

    # Indexes
    __table_args__ = (
        Index("ix_report_schedules_report", "report_id"),
        Index("ix_report_schedules_status", "status"),
        Index("ix_report_schedules_scheduled_at", "scheduled_at"),
        Index("ix_report_schedules_report_status", "report_id", "status"),
        Index(
            "ix_report_schedules_report_scheduled",
            "report_id",
            "scheduled_at",
        ),
    )

    def __repr__(self) -> str:
        return f"<ReportSchedule report={self.report_id} status={self.status}>"

    @property
    def status_enum(self) -> ReportStatus:
        """Get status as enum."""
        return ReportStatus(self.status)

    @property
    def is_complete(self) -> bool:
        """Check if run has completed (successfully or failed)."""
        return self.status in (
            ReportStatus.COMPLETED.value,
            ReportStatus.FAILED.value,
            ReportStatus.CANCELLED.value,
        )

    @property
    def is_successful(self) -> bool:
        """Check if run completed successfully."""
        return self.status == ReportStatus.COMPLETED.value

    @property
    def can_retry(self) -> bool:
        """Check if run can be retried."""
        return (
            self.status == ReportStatus.FAILED.value
            and self.retry_count < self.max_retries
        )

    @property
    def execution_time(self) -> int | None:
        """Calculate execution time in seconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds())
        return self.duration_seconds

    def start(self) -> None:
        """Mark run as started."""
        self.status = ReportStatus.RUNNING.value
        self.started_at = utc_now()

    def complete(
        self,
        output_path: str | None = None,
        output_size_bytes: int | None = None,
        record_count: int | None = None,
    ) -> None:
        """Mark run as completed successfully."""
        self.status = ReportStatus.COMPLETED.value
        self.completed_at = utc_now()
        self.output_path = output_path
        self.output_size_bytes = output_size_bytes
        self.record_count = record_count

        if self.started_at:
            self.duration_seconds = int(
                (self.completed_at - self.started_at).total_seconds()
            )

    def fail(self, error_message: str, error_details: str | None = None) -> None:
        """Mark run as failed."""
        self.status = ReportStatus.FAILED.value
        self.completed_at = utc_now()
        self.error_message = error_message
        self.error_details = error_details

        if self.started_at:
            self.duration_seconds = int(
                (self.completed_at - self.started_at).total_seconds()
            )

    def cancel(self) -> None:
        """Mark run as cancelled."""
        self.status = ReportStatus.CANCELLED.value
        self.completed_at = utc_now()

        if self.started_at:
            self.duration_seconds = int(
                (self.completed_at - self.started_at).total_seconds()
            )

    def mark_delivered(self, recipients_count: int, delivery_status: str) -> None:
        """Mark report as successfully delivered."""
        self.delivered_at = utc_now()
        self.recipients_count = recipients_count
        self.delivery_status = delivery_status
