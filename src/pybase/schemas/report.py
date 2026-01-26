"""Pydantic schemas for reports and scheduled report generation."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from pybase.models.report import ReportFormat, ReportStatus, ScheduleFrequency


# =============================================================================
# Schedule Config Schemas
# =============================================================================


class ReportScheduleConfig(BaseModel):
    """Schedule configuration for report generation."""

    time_of_day: str = Field(
        default="09:00",
        description="Time to generate report (HH:MM format)",
        pattern=r"^([01]\d|2[0-3]):([0-5]\d)$",
    )
    day_of_week: Optional[str] = Field(
        None,
        description="Day of week for weekly reports (monday-sunday)",
    )
    day_of_month: Optional[int] = Field(
        None,
        ge=1,
        le=31,
        description="Day of month for monthly reports (1-31)",
    )
    timezone: str = Field(
        default="UTC",
        description="Timezone for scheduling",
    )

    @field_validator("day_of_week")
    @classmethod
    def validate_day_of_week(cls, v: Optional[str]) -> Optional[str]:
        """Validate day_of_week is valid."""
        if v is None:
            return v
        valid_days = [
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ]
        if v.lower() not in valid_days:
            raise ValueError(f"day_of_week must be one of {valid_days}")
        return v.lower()


class DeliveryConfig(BaseModel):
    """Email delivery configuration for reports."""

    recipients: list[str] = Field(
        default_factory=list,
        description="Email addresses to send report to",
    )
    cc: list[str] = Field(
        default_factory=list,
        description="CC email addresses",
    )
    bcc: list[str] = Field(
        default_factory=list,
        description="BCC email addresses",
    )
    subject: str = Field(
        default="Scheduled Report",
        description="Email subject line",
    )
    message: str = Field(
        default="Please find the attached report.",
        description="Email body message",
    )
    reply_to: Optional[str] = Field(
        None,
        description="Reply-to email address",
    )

    @field_validator("recipients", "cc", "bcc")
    @classmethod
    def validate_emails(cls, v: list[str]) -> list[str]:
        """Validate email addresses."""
        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        for email in v:
            if not re.match(email_pattern, email):
                raise ValueError(f"Invalid email address: {email}")
        return v


class PDFExportConfig(BaseModel):
    """PDF export configuration."""

    page_size: str = Field(
        default="A4",
        description="Page size (A4, Letter, Legal, etc.)",
    )
    orientation: str = Field(
        default="portrait",
        description="Page orientation (portrait/landscape)",
    )
    include_filters: bool = Field(
        default=True,
        description="Include applied filters in report",
    )
    include_timestamp: bool = Field(
        default=True,
        description="Include generation timestamp",
    )
    include_summary: bool = Field(
        default=True,
        description="Include summary statistics",
    )

    @field_validator("orientation")
    @classmethod
    def validate_orientation(cls, v: str) -> str:
        """Validate orientation value."""
        if v.lower() not in ["portrait", "landscape"]:
            raise ValueError("orientation must be 'portrait' or 'landscape'")
        return v.lower()


class ExcelExportConfig(BaseModel):
    """Excel export configuration."""

    include_charts: bool = Field(
        default=True,
        description="Include charts in Excel export",
    )
    separate_sheets: bool = Field(
        default=False,
        description="Export charts to separate sheets",
    )
    freeze_header: bool = Field(
        default=True,
        description="Freeze header row",
    )
    auto_filter: bool = Field(
        default=True,
        description="Enable auto-filter on columns",
    )


class CSVExportConfig(BaseModel):
    """CSV export configuration."""

    delimiter: str = Field(
        default=",",
        description="CSV delimiter character",
    )
    include_header: bool = Field(
        default=True,
        description="Include column headers",
    )
    quote_all: bool = Field(
        default=False,
        description="Quote all fields",
    )

    @field_validator("delimiter")
    @classmethod
    def validate_delimiter(cls, v: str) -> str:
        """Validate delimiter is single character."""
        if len(v) != 1:
            raise ValueError("delimiter must be a single character")
        return v


class ExportConfig(BaseModel):
    """Export configuration (format-specific)."""

    pdf: Optional[PDFExportConfig] = Field(
        default_factory=PDFExportConfig,
        description="PDF export settings",
    )
    excel: Optional[ExcelExportConfig] = Field(
        default_factory=ExcelExportConfig,
        description="Excel export settings",
    )
    csv: Optional[CSVExportConfig] = Field(
        default_factory=CSVExportConfig,
        description="CSV export settings",
    )


# =============================================================================
# Base Schemas
# =============================================================================


class ReportBase(BaseModel):
    """Base schema for Report."""

    name: str = Field(..., min_length=1, max_length=255, description="Report name")
    description: Optional[str] = Field(None, description="Report description")
    format: ReportFormat = Field(
        default=ReportFormat.PDF,
        description="Report output format",
    )
    frequency: ScheduleFrequency = Field(
        default=ScheduleFrequency.MANUAL,
        description="Report generation frequency",
    )
    cron_expression: Optional[str] = Field(
        None,
        description="Cron expression for custom scheduling",
    )
    is_active: bool = Field(
        default=True,
        description="Active reports will be generated on schedule",
    )
    is_paused: bool = Field(
        default=False,
        description="Temporarily paused by user",
    )
    max_runs_per_day: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum report generations per day",
    )
    notify_on_success: bool = Field(
        default=True,
        description="Send notification when report generation succeeds",
    )
    notify_on_failure: bool = Field(
        default=True,
        description="Send notification when report generation fails",
    )
    notification_email: Optional[str] = Field(
        None,
        description="Email to notify for errors",
    )
    retention_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Number of days to keep generated report files",
    )

    @field_validator("cron_expression")
    @classmethod
    def validate_cron_expression(cls, v: Optional[str]) -> Optional[str]:
        """Validate cron expression format."""
        if v is None:
            return v
        # Basic validation: 5 parts separated by spaces
        parts = v.split()
        if len(parts) != 5:
            raise ValueError(
                "cron_expression must have 5 parts: minute hour day month weekday"
            )
        return v


class ReportScheduleBase(BaseModel):
    """Base schema for ReportSchedule."""

    scheduled_at: datetime = Field(..., description="When this run was scheduled")
    status: ReportStatus = Field(
        default=ReportStatus.PENDING,
        description="Status of report generation",
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Number of times this run was retried",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts",
    )


# =============================================================================
# Create Schemas
# =============================================================================


class ReportCreate(ReportBase):
    """Schema for creating a new report."""

    dashboard_id: str = Field(..., description="Dashboard to generate report from")
    schedule_config: Optional[ReportScheduleConfig] = Field(
        default_factory=ReportScheduleConfig,
        description="Schedule configuration",
    )
    delivery_config: Optional[DeliveryConfig] = Field(
        default_factory=DeliveryConfig,
        description="Email delivery configuration",
    )
    export_config: Optional[ExportConfig] = Field(
        default_factory=ExportConfig,
        description="Export format configuration",
    )


class ReportScheduleCreate(ReportScheduleBase):
    """Schema for creating a report schedule run."""

    report_id: str = Field(..., description="Report to execute")
    triggered_by_id: Optional[str] = Field(
        None,
        description="User who manually triggered this run",
    )


# =============================================================================
# Update Schemas
# =============================================================================


class ReportUpdate(BaseModel):
    """Schema for updating a report."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    format: Optional[ReportFormat] = None
    frequency: Optional[ScheduleFrequency] = None
    cron_expression: Optional[str] = None
    schedule_config: Optional[ReportScheduleConfig] = None
    delivery_config: Optional[DeliveryConfig] = None
    export_config: Optional[ExportConfig] = None
    is_active: Optional[bool] = None
    is_paused: Optional[bool] = None
    max_runs_per_day: Optional[int] = Field(None, ge=1, le=100)
    notify_on_success: Optional[bool] = None
    notify_on_failure: Optional[bool] = None
    notification_email: Optional[str] = None
    retention_days: Optional[int] = Field(None, ge=1, le=365)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron_expression(cls, v: Optional[str]) -> Optional[str]:
        """Validate cron expression format."""
        if v is None:
            return v
        parts = v.split()
        if len(parts) != 5:
            raise ValueError(
                "cron_expression must have 5 parts: minute hour day month weekday"
            )
        return v


class ReportScheduleUpdate(BaseModel):
    """Schema for updating a report schedule run."""

    status: Optional[ReportStatus] = None
    output_path: Optional[str] = None
    output_size_bytes: Optional[int] = Field(None, ge=0)
    error_message: Optional[str] = None
    error_details: Optional[str] = None
    delivery_status: Optional[str] = None
    recipients_count: Optional[int] = Field(None, ge=0)
    duration_seconds: Optional[int] = Field(None, ge=0)
    record_count: Optional[int] = Field(None, ge=0)
    retry_count: Optional[int] = Field(None, ge=0)


# =============================================================================
# Response Schemas
# =============================================================================


class ReportResponse(ReportBase):
    """Schema for report response."""

    id: str
    base_id: str
    dashboard_id: str
    created_by_id: Optional[str]
    schedule_config: dict[str, Any] = Field(default_factory=dict)
    delivery_config: dict[str, Any] = Field(default_factory=dict)
    export_config: dict[str, Any] = Field(default_factory=dict)
    total_runs: int
    successful_runs: int
    failed_runs: int
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    average_duration_seconds: Optional[int]
    last_output_path: Optional[str]
    last_output_size_bytes: Optional[int]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """Schema for listing reports."""

    items: list[ReportResponse]
    total: int
    page: int = 1
    page_size: int = 50
    pages: int


class ReportScheduleResponse(ReportScheduleBase):
    """Schema for report schedule response."""

    id: str
    report_id: str
    triggered_by_id: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    output_path: Optional[str]
    output_size_bytes: Optional[int]
    error_message: Optional[str]
    error_details: Optional[str]
    delivered_at: Optional[datetime]
    delivery_status: Optional[str]
    recipients_count: int
    duration_seconds: Optional[int]
    record_count: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportScheduleListResponse(BaseModel):
    """Schema for listing report schedules."""

    items: list[ReportScheduleResponse]
    total: int
    page: int = 1
    page_size: int = 50
    pages: int


# =============================================================================
# Utility Schemas
# =============================================================================


class ReportGenerateRequest(BaseModel):
    """Request to manually generate a report."""

    report_id: str = Field(..., description="Report to generate")
    send_email: bool = Field(
        default=True,
        description="Send email to configured recipients",
    )
    override_recipients: Optional[list[str]] = Field(
        None,
        description="Override default recipients for this generation",
    )


class ReportExportResponse(BaseModel):
    """Response for report export."""

    report_id: str
    schedule_id: str
    output_path: str
    output_size_bytes: int
    format: ReportFormat
    generated_at: datetime
    record_count: Optional[int]
    download_url: Optional[str] = Field(
        None,
        description="Temporary download URL for the report file",
    )


class ReportStatistics(BaseModel):
    """Report execution statistics."""

    report_id: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float = Field(..., description="Success rate percentage")
    average_duration_seconds: Optional[int]
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    is_active: bool
    is_paused: bool
    is_overdue: bool


class ReportDuplicate(BaseModel):
    """Request to duplicate a report."""

    new_name: str = Field(..., min_length=1, max_length=255)
    copy_schedule: bool = Field(
        default=True,
        description="Copy schedule configuration to new report",
    )
    copy_delivery_config: bool = Field(
        default=True,
        description="Copy delivery settings to new report",
    )
