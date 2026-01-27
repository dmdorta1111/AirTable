"""Pydantic schemas for custom reports with drag-and-drop sections."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from pybase.models.custom_report import (
    ReportFormat,
    ReportSectionType,
    ReportStatus,
    ScheduleFrequency,
)


# =============================================================================
# Schedule Config Schemas
# =============================================================================


class CustomReportScheduleConfig(BaseModel):
    """Schedule configuration for custom report generation."""

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


class CustomReportDeliveryConfig(BaseModel):
    """Email delivery configuration for custom reports."""

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
        default="Custom Report",
        description="Email subject line",
    )
    message: str = Field(
        default="Please find the attached custom report.",
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


# =============================================================================
# Layout and Style Config Schemas
# =============================================================================


class LayoutConfig(BaseModel):
    """Report layout configuration."""

    page_size: str = Field(
        default="A4",
        description="Page size (A4, Letter, Legal, etc.)",
    )
    orientation: str = Field(
        default="portrait",
        description="Page orientation (portrait/landscape)",
    )
    margins: dict[str, int] = Field(
        default_factory=lambda: {"top": 20, "bottom": 20, "left": 15, "right": 15},
        description="Page margins in points",
    )

    @field_validator("orientation")
    @classmethod
    def validate_orientation(cls, v: str) -> str:
        """Validate orientation value."""
        if v.lower() not in ["portrait", "landscape"]:
            raise ValueError("orientation must be 'portrait' or 'landscape'")
        return v.lower()


class StyleConfig(BaseModel):
    """Visual styling configuration."""

    font_family: str = Field(
        default="Arial",
        description="Font family",
    )
    font_size: int = Field(
        default=10,
        ge=6,
        le=72,
        description="Base font size",
    )
    colors: dict[str, str] = Field(
        default_factory=lambda: {
            "primary": "#0066cc",
            "secondary": "#6c757d",
            "background": "#ffffff",
        },
        description="Color scheme",
    )
    header_style: str = Field(
        default="centered",
        description="Header alignment (centered, left, right)",
    )
    show_page_numbers: bool = Field(
        default=True,
        description="Show page numbers in footer",
    )
    logo_url: Optional[str] = Field(
        None,
        description="URL to logo image",
    )


# =============================================================================
# Base Schemas
# =============================================================================


class CustomReportBase(BaseModel):
    """Base schema for CustomReport."""

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
    is_published: bool = Field(
        default=False,
        description="Published reports are visible to other users",
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


class ReportSectionBase(BaseModel):
    """Base schema for ReportSection."""

    section_type: ReportSectionType = Field(
        ...,
        description="Type of section (table, chart, text, image, etc.)",
    )
    order: int = Field(
        default=0,
        ge=0,
        description="Order of this section in the report",
    )
    title: Optional[str] = Field(
        None,
        max_length=255,
        description="Section title",
    )
    is_visible: bool = Field(
        default=True,
        description="Whether this section is visible in the report",
    )


class ReportDataSourceBase(BaseModel):
    """Base schema for ReportDataSource."""

    name: str = Field(..., min_length=1, max_length=255, description="Data source name")
    description: Optional[str] = Field(None, description="Data source description")


class ReportTemplateBase(BaseModel):
    """Base schema for ReportTemplate."""

    name: str = Field(..., min_length=1, max_length=255, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    category: Optional[str] = Field(
        None,
        max_length=100,
        description="Template category (e.g., 'BOM', 'Quality')",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for searchability",
    )
    is_system: bool = Field(
        default=False,
        description="System templates are built-in",
    )
    is_active: bool = Field(
        default=True,
        description="Active templates are shown in gallery",
    )


class CustomReportScheduleBase(BaseModel):
    """Base schema for CustomReportSchedule."""

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


class CustomReportCreate(CustomReportBase):
    """Schema for creating a new custom report."""

    template_id: Optional[str] = Field(
        None,
        description="Template this report was created from",
    )
    layout_config: Optional[LayoutConfig] = Field(
        default_factory=LayoutConfig,
        description="Layout configuration",
    )
    style_config: Optional[StyleConfig] = Field(
        default_factory=StyleConfig,
        description="Visual styling configuration",
    )
    schedule_config: Optional[CustomReportScheduleConfig] = Field(
        default_factory=CustomReportScheduleConfig,
        description="Schedule configuration",
    )
    delivery_config: Optional[CustomReportDeliveryConfig] = Field(
        default_factory=CustomReportDeliveryConfig,
        description="Email delivery configuration",
    )
    export_config: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Export format configuration",
    )
    parameters_config: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Configurable parameters",
    )


class ReportSectionCreate(ReportSectionBase):
    """Schema for creating a report section."""

    section_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Section-specific configuration",
    )
    style_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Section-specific styling",
    )


class ReportDataSourceCreate(ReportDataSourceBase):
    """Schema for creating a data source."""

    tables_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Tables and join configuration",
    )
    fields_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Fields to include in query",
    )
    filters_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Filter configuration",
    )
    sort_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Sorting and grouping configuration",
    )
    parameters_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameter binding configuration",
    )


class ReportTemplateCreate(ReportTemplateBase):
    """Schema for creating a report template."""

    template_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Complete template configuration",
    )


class CustomReportScheduleCreate(CustomReportScheduleBase):
    """Schema for creating a custom report schedule run."""

    report_id: str = Field(..., description="Report to execute")
    triggered_by_id: Optional[str] = Field(
        None,
        description="User who manually triggered this run",
    )
    parameters_used: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameter values for this run",
    )


# =============================================================================
# Update Schemas
# =============================================================================


class CustomReportUpdate(BaseModel):
    """Schema for updating a custom report."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    format: Optional[ReportFormat] = None
    frequency: Optional[ScheduleFrequency] = None
    cron_expression: Optional[str] = None
    template_id: Optional[str] = None
    layout_config: Optional[LayoutConfig] = None
    style_config: Optional[StyleConfig] = None
    schedule_config: Optional[CustomReportScheduleConfig] = None
    delivery_config: Optional[CustomReportDeliveryConfig] = None
    export_config: Optional[dict[str, Any]] = None
    parameters_config: Optional[dict[str, Any]] = None
    is_published: Optional[bool] = None
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


class ReportSectionUpdate(BaseModel):
    """Schema for updating a report section."""

    section_type: Optional[ReportSectionType] = None
    order: Optional[int] = Field(None, ge=0)
    title: Optional[str] = Field(None, max_length=255)
    is_visible: Optional[bool] = None
    section_config: Optional[dict[str, Any]] = None
    style_config: Optional[dict[str, Any]] = None


class ReportDataSourceUpdate(BaseModel):
    """Schema for updating a data source."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tables_config: Optional[dict[str, Any]] = None
    fields_config: Optional[dict[str, Any]] = None
    filters_config: Optional[dict[str, Any]] = None
    sort_config: Optional[dict[str, Any]] = None
    parameters_config: Optional[dict[str, Any]] = None


class ReportTemplateUpdate(BaseModel):
    """Schema for updating a report template."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[list[str]] = None
    template_config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class CustomReportScheduleUpdate(BaseModel):
    """Schema for updating a custom report schedule run."""

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
    parameters_used: Optional[dict[str, Any]] = None


# =============================================================================
# Response Schemas
# =============================================================================


class CustomReportResponse(CustomReportBase):
    """Schema for custom report response."""

    id: str
    base_id: str
    created_by_id: Optional[str]
    template_id: Optional[str]
    layout_config: dict[str, Any] = Field(default_factory=dict)
    style_config: dict[str, Any] = Field(default_factory=dict)
    schedule_config: dict[str, Any] = Field(default_factory=dict)
    delivery_config: dict[str, Any] = Field(default_factory=dict)
    export_config: dict[str, Any] = Field(default_factory=dict)
    parameters_config: dict[str, Any] = Field(default_factory=dict)
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


class ReportSectionResponse(ReportSectionBase):
    """Schema for report section response."""

    id: str
    report_id: str
    section_config: dict[str, Any] = Field(default_factory=dict)
    style_config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportDataSourceResponse(ReportDataSourceBase):
    """Schema for data source response."""

    id: str
    report_id: str
    tables_config: dict[str, Any] = Field(default_factory=dict)
    fields_config: dict[str, Any] = Field(default_factory=dict)
    filters_config: dict[str, Any] = Field(default_factory=dict)
    sort_config: dict[str, Any] = Field(default_factory=dict)
    parameters_config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportTemplateResponse(ReportTemplateBase):
    """Schema for report template response."""

    id: str
    base_id: str
    created_by_id: Optional[str]
    template_config: dict[str, Any] = Field(default_factory=dict)
    usage_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CustomReportScheduleResponse(CustomReportScheduleBase):
    """Schema for custom report schedule response."""

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
    parameters_used: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# List Response Schemas
# =============================================================================


class CustomReportListResponse(BaseModel):
    """Schema for listing custom reports."""

    items: list[CustomReportResponse]
    total: int
    page: int = 1
    page_size: int = 50
    pages: int


class ReportSectionListResponse(BaseModel):
    """Schema for listing report sections."""

    items: list[ReportSectionResponse]
    total: int
    page: int = 1
    page_size: int = 50
    pages: int


class ReportDataSourceListResponse(BaseModel):
    """Schema for listing data sources."""

    items: list[ReportDataSourceResponse]
    total: int
    page: int = 1
    page_size: int = 50
    pages: int


class ReportTemplateListResponse(BaseModel):
    """Schema for listing report templates."""

    items: list[ReportTemplateResponse]
    total: int
    page: int = 1
    page_size: int = 50
    pages: int


class CustomReportScheduleListResponse(BaseModel):
    """Schema for listing custom report schedules."""

    items: list[CustomReportScheduleResponse]
    total: int
    page: int = 1
    page_size: int = 50
    pages: int


# =============================================================================
# Utility Schemas
# =============================================================================


class CustomReportGenerateRequest(BaseModel):
    """Request to manually generate a custom report."""

    report_id: str = Field(..., description="Report to generate")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameter values for this generation",
    )
    send_email: bool = Field(
        default=True,
        description="Send email to configured recipients",
    )
    override_recipients: Optional[list[str]] = Field(
        None,
        description="Override default recipients for this generation",
    )


class CustomReportExportResponse(BaseModel):
    """Response for custom report export."""

    report_id: str
    schedule_id: str
    output_path: str
    output_size_bytes: int
    format: ReportFormat
    generated_at: datetime
    record_count: Optional[int]
    parameters_used: dict[str, Any] = Field(default_factory=dict)
    download_url: Optional[str] = Field(
        None,
        description="Temporary download URL for the report file",
    )


class CustomReportStatistics(BaseModel):
    """Custom report execution statistics."""

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
    is_published: bool
    is_overdue: bool


class CustomReportDuplicate(BaseModel):
    """Request to duplicate a custom report."""

    new_name: str = Field(..., min_length=1, max_length=255)
    copy_sections: bool = Field(
        default=True,
        description="Copy sections to new report",
    )
    copy_data_sources: bool = Field(
        default=True,
        description="Copy data sources to new report",
    )
    copy_schedule: bool = Field(
        default=True,
        description="Copy schedule configuration to new report",
    )
    copy_delivery_config: bool = Field(
        default=True,
        description="Copy delivery settings to new report",
    )


class ReportTemplateUse(BaseModel):
    """Request to create a report from a template."""

    template_id: str = Field(..., description="Template to use")
    report_name: str = Field(..., min_length=1, max_length=255, description="Name for new report")
    customize_sections: bool = Field(
        default=True,
        description="Allow customization of template sections",
    )
