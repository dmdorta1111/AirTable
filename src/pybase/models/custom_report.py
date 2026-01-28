"""
Custom Report models - user-defined reports with drag-and-drop sections.

Custom reports allow users to:
- Build formatted reports combining multiple tables, charts, and text sections
- Pull data from multiple tables with joins
- Apply filters and parameters
- Export to PDF with professional formatting
- Schedule reports for automatic generation
- Use templates for common patterns (BOM, inspection, etc.)
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


class ReportSectionType(str, Enum):
    """Types of sections that can be added to a report."""

    TABLE = "table"
    CHART = "chart"
    TEXT = "text"
    IMAGE = "image"
    PAGE_BREAK = "page_break"
    HEADER = "header"
    FOOTER = "footer"


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


class CustomReport(SoftDeleteModel):
    """
    Custom Report model - user-defined reports with drag-and-drop sections.

    Each custom report has:
    - Multiple sections (tables, charts, text, images)
    - Data sources with multi-table joins
    - Professional styling and formatting
    - Schedule configuration for automatic generation
    - Template reference for common patterns
    - Export and delivery settings
    """

    __tablename__: str = "custom_reports"  # type: ignore[assignment]

    # Foreign keys
    base_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    template_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("report_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Template this report was created from (if any)",
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

    # Format configuration
    format: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ReportFormat.PDF.value,
        doc="Default export format",
    )

    # Layout configuration (JSON stored as text)
    # Stores section order, positioning, sizing
    # Format: {
    #   "sections": [
    #     {
    #       "id": "section-uuid",
    #       "type": "table|chart|text|image",
    #       "order": 0,
    #       "height": "auto|400px|50%",
    #       "visible": true
    #     }
    #   ],
    #   "page_size": "A4|Letter",
    #   "orientation": "portrait|landscape",
    #   "margins": { "top": 20, "bottom": 20, "left": 15, "right": 15 }
    # }
    layout_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
        doc="Report layout and section configuration",
    )

    # Style configuration (JSON stored as text)
    # Stores fonts, colors, branding
    # Format: {
    #   "font_family": "Arial",
    #   "font_size": 10,
    #   "colors": {
    #     "primary": "#0066cc",
    #     "secondary": "#6c757d",
    #     "background": "#ffffff"
    #   },
    #   "header_style": "centered|left|right",
    #   "show_page_numbers": true,
    #   "logo_url": "https://..."
    # }
    style_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
        doc="Visual styling configuration",
    )

    # Schedule configuration
    frequency: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ScheduleFrequency.MANUAL.value,
        doc="How often to generate report",
    )

    # Cron expression for CUSTOM frequency
    cron_expression: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Cron expression for custom scheduling",
    )

    # Schedule settings (JSON stored as text)
    # Stores: time_of_day, day_of_week, day_of_month, timezone
    # Format: {
    #   "time_of_day": "09:00",
    #   "day_of_week": "monday",
    #   "day_of_month": 1,
    #   "timezone": "America/New_York"
    # }
    schedule_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Delivery configuration (JSON stored as text)
    # Stores: recipients, subject, message
    # Format: {
    #   "recipients": ["email@example.com"],
    #   "subject": "Monthly Quality Report",
    #   "message": "Please find attached the monthly report.",
    #   "cc": [],
    #   "bcc": []
    # }
    delivery_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Export settings (JSON stored as text)
    # Stores format-specific options
    # Format: {
    #   "include_filters": true,
    #   "include_timestamp": true,
    #   "include_summary": true,
    #   "compression": "none|zip"
    # }
    export_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Status flags
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Published reports are visible to other users with permissions",
    )
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

    # Parameters configuration (JSON stored as text)
    # Stores configurable parameters for the report
    # Format: {
    #   "parameters": [
    #     {
    #       "name": "start_date",
    #       "type": "date",
    #       "default": "2024-01-01",
    #       "required": true
    #     },
    #     {
    #       "name": "department",
    #       "type": "select",
    #       "options": ["Engineering", "Quality", "Manufacturing"],
    #       "required": false
    #     }
    #   ]
    # }
    parameters_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
        doc="Configurable parameters for report generation",
    )

    # Relationships
    base: Mapped["Base"] = relationship(
        "Base",
        back_populates="custom_reports",
    )
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    template: Mapped["ReportTemplate | None"] = relationship(
        "ReportTemplate",
        back_populates="reports",
        foreign_keys=[template_id],
    )
    sections: Mapped[list["ReportSection"]] = relationship(
        "ReportSection",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportSection.order",
    )
    data_sources: Mapped[list["ReportDataSource"]] = relationship(
        "ReportDataSource",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    schedules: Mapped[list["CustomReportSchedule"]] = relationship(
        "CustomReportSchedule",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="CustomReportSchedule.scheduled_at.desc()",
    )

    # Indexes
    __table_args__ = (
        Index("ix_custom_reports_base", "base_id"),
        Index("ix_custom_reports_created_by", "created_by_id"),
        Index("ix_custom_reports_template", "template_id"),
        Index("ix_custom_reports_frequency", "frequency"),
        Index("ix_custom_reports_active", "is_active", "is_paused", "is_published"),
        Index("ix_custom_reports_next_run", "next_run_at"),
        Index("ix_custom_reports_last_run", "last_run_at"),
    )

    def __repr__(self) -> str:
        return f"<CustomReport {self.name} ({self.format})>"

    @property
    def format_enum(self) -> ReportFormat:
        """Get report format as enum."""
        return ReportFormat(self.format)

    @property
    def frequency_enum(self) -> ScheduleFrequency:
        """Get schedule frequency as enum."""
        return ScheduleFrequency(self.frequency)

    def get_layout_config_dict(self) -> dict:
        """Parse layout_config JSON."""
        import json

        try:
            return json.loads(self.layout_config or "{}")
        except json.JSONDecodeError:
            return {}

    def get_style_config_dict(self) -> dict:
        """Parse style_config JSON."""
        import json

        try:
            return json.loads(self.style_config or "{}")
        except json.JSONDecodeError:
            return {}

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

    def get_parameters_config_dict(self) -> dict:
        """Parse parameters_config JSON."""
        import json

        try:
            return json.loads(self.parameters_config or "{}")
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


class ReportSection(BaseModel):
    """
    Report Section model - individual sections within a custom report.

    Each section can be:
    - Table: Display data from a data source
    - Chart: Visualize data with charts
    - Text: Rich text content with formatting
    - Image: Embedded images or logos
    - Page Break: Force page break in PDF
    - Header/Footer: Repeating headers/footers
    """

    __tablename__: str = "report_sections"  # type: ignore[assignment]

    # Foreign key
    report_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("custom_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Section identification
    section_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Type of section (table, chart, text, image, etc.)",
    )

    # Ordering and visibility
    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Order of this section in the report (0 = first)",
    )
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Section title (optional)",
    )
    is_visible: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this section is visible in the report",
    )

    # Section configuration (JSON stored as text)
    # Stores type-specific configuration
    # For TABLE: {
    #   "data_source_id": "uuid",
    #   "show_headers": true,
    #   "stripe_rows": true,
    #   "column_widths": {"col1": 100, "col2": 150}
    # }
    # For CHART: {
    #   "chart_type": "bar|line|pie",
    #   "data_source_id": "uuid",
    #   "x_axis": "field_name",
    #   "y_axis": "field_name",
    #   "group_by": "field_name"
    # }
    # For TEXT: {
    #   "content": "Rich text HTML or Markdown",
    #   "format": "html|markdown"
    # }
    # For IMAGE: {
    #   "url": "https://...",
    #   "width": 600,
    #   "height": 400,
    #   "alignment": "center"
    # }
    section_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
        doc="Section-specific configuration",
    )

    # Styling (JSON stored as text)
    # Format: {
    #   "background_color": "#ffffff",
    #   "border": "1px solid #ccc",
    #   "padding": 10,
    #   "margin_top": 20,
    #   "margin_bottom": 20
    # }
    style_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
        doc="Section-specific styling",
    )

    # Relationships
    report: Mapped["CustomReport"] = relationship(
        "CustomReport",
        back_populates="sections",
    )

    # Indexes
    __table_args__ = (
        Index("ix_report_sections_report", "report_id"),
        Index("ix_report_sections_order", "report_id", "order"),
        Index("ix_report_sections_type", "report_id", "section_type"),
    )

    def __repr__(self) -> str:
        return f"<ReportSection {self.section_type} (order={self.order})>"

    @property
    def section_type_enum(self) -> ReportSectionType:
        """Get section type as enum."""
        return ReportSectionType(self.section_type)

    def get_section_config_dict(self) -> dict:
        """Parse section_config JSON."""
        import json

        try:
            return json.loads(self.section_config or "{}")
        except json.JSONDecodeError:
            return {}

    def get_style_config_dict(self) -> dict:
        """Parse style_config JSON."""
        import json

        try:
            return json.loads(self.style_config or "{}")
        except json.JSONDecodeError:
            return {}


class ReportDataSource(BaseModel):
    """
    Report Data Source model - data sources for custom reports.

    Each data source defines:
    - Which tables to query
    - How to join multiple tables
    - Filters to apply
    - Sorting and grouping
    - Fields to include
    """

    __tablename__: str = "report_data_sources"  # type: ignore[assignment]

    # Foreign key
    report_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("custom_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Basic info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Human-readable name for this data source",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Tables and joins (JSON stored as text)
    # Format: {
    #   "primary_table": "table_id",
    #   "tables": [
    #     {
    #       "table_id": "uuid",
    #       "alias": "t1",
    #       "join_type": "inner|left|right",
    #       "join_on": {
    #         "left_table": "table_id",
    #         "left_field": "field_id",
    #         "right_table": "table_id",
    #         "right_field": "field_id"
    #       }
    #     }
    #   ]
    # }
    tables_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
        doc="Tables and join configuration",
    )

    # Fields to include (JSON stored as text)
    # Format: {
    #   "fields": [
    #     {
    #       "table_id": "uuid",
    #       "field_id": "uuid",
    #       "alias": "display_name",
    #       "aggregate": "none|sum|avg|count|min|max",
    #       "visible": true
    #     }
    #   ]
    # }
    fields_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
        doc="Fields to include in query",
    )

    # Filters (JSON stored as text)
    # Format: {
    #   "filters": [
    #     {
    #       "field_id": "uuid",
    #       "operator": "equals|contains|greater_than|between",
    #       "value": "value",
    #       "logic": "and|or"
    #     }
    #   ]
    # }
    filters_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
        doc="Filter configuration",
    )

    # Sorting and grouping (JSON stored as text)
    # Format: {
    #   "sort_by": [
    #     {"field_id": "uuid", "direction": "asc|desc"}
    #   ],
    #   "group_by": ["field_id", "field_id"],
    #   "limit": 1000,
    #   "offset": 0
    # }
    sort_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
        doc="Sorting and grouping configuration",
    )

    # Parameter bindings (JSON stored as text)
    # Maps query filters to report parameters
    # Format: {
    #   "parameter_bindings": [
    #     {
    #       "filter_id": "uuid",
    #       "parameter_name": "start_date",
    #       "default_value": "2024-01-01"
    #     }
    #   ]
    # }
    parameters_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
        doc="Parameter binding configuration",
    )

    # Relationships
    report: Mapped["CustomReport"] = relationship(
        "CustomReport",
        back_populates="data_sources",
    )

    # Indexes
    __table_args__ = (
        Index("ix_report_data_sources_report", "report_id"),
        Index("ix_report_data_sources_name", "report_id", "name"),
    )

    def __repr__(self) -> str:
        return f"<ReportDataSource {self.name}>"

    def get_tables_config_dict(self) -> dict:
        """Parse tables_config JSON."""
        import json

        try:
            return json.loads(self.tables_config or "{}")
        except json.JSONDecodeError:
            return {}

    def get_fields_config_dict(self) -> dict:
        """Parse fields_config JSON."""
        import json

        try:
            return json.loads(self.fields_config or "{}")
        except json.JSONDecodeError:
            return {}

    def get_filters_config_dict(self) -> dict:
        """Parse filters_config JSON."""
        import json

        try:
            return json.loads(self.filters_config or "{}")
        except json.JSONDecodeError:
            return {}

    def get_sort_config_dict(self) -> dict:
        """Parse sort_config JSON."""
        import json

        try:
            return json.loads(self.sort_config or "{}")
        except json.JSONDecodeError:
            return {}

    def get_parameters_config_dict(self) -> dict:
        """Parse parameters_config JSON."""
        import json

        try:
            return json.loads(self.parameters_config or "{}")
        except json.JSONDecodeError:
            return {}


class ReportTemplate(BaseModel):
    """
    Report Template model - predefined templates for common report patterns.

    Templates provide:
    - Pre-built layouts for common report types
    - BOM reports, inspection reports, quality reports, etc.
    - Starting point that users can customize
    """

    __tablename__: str = "report_templates"  # type: ignore[assignment]

    # Foreign key
    base_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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

    # Template categorization
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Template category (e.g., 'BOM', 'Quality', 'Project')",
    )
    tags: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="[]",
        doc="JSON array of tags for searchability",
    )

    # Template structure (JSON stored as text)
    # Stores the complete template configuration
    # Format: {
    #   "sections": [...],  // Same structure as CustomReport.layout_config
    #   "style_config": {...},  // Default styling
    #   "data_sources": [...],  // Example data sources
    #   "parameters": [...],  // Available parameters
    #   "preview_image": "https://..."
    # }
    template_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
        doc="Complete template configuration",
    )

    # Usage tracking
    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of times this template has been used",
    )

    # Status
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="System templates are built-in and cannot be deleted",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Active templates are shown in template gallery",
    )

    # Relationships
    base: Mapped["Base"] = relationship(
        "Base",
        back_populates="report_templates",
    )
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    reports: Mapped[list["CustomReport"]] = relationship(
        "CustomReport",
        back_populates="template",
        foreign_keys="CustomReport.template_id",
    )

    # Indexes
    __table_args__ = (
        Index("ix_report_templates_base", "base_id"),
        Index("ix_report_templates_category", "category"),
        Index("ix_report_templates_active", "is_active", "is_system"),
    )

    def __repr__(self) -> str:
        return f"<ReportTemplate {self.name} ({self.category})>"

    def get_template_config_dict(self) -> dict:
        """Parse template_config JSON."""
        import json

        try:
            return json.loads(self.template_config or "{}")
        except json.JSONDecodeError:
            return {}

    def get_tags_list(self) -> list:
        """Parse tags JSON array."""
        import json

        try:
            return json.loads(self.tags or "[]")
        except json.JSONDecodeError:
            return []

    def increment_usage(self) -> None:
        """Increment usage counter."""
        self.usage_count += 1


class CustomReportSchedule(BaseModel):
    """
    Custom Report Schedule run - tracks individual report generation executions.

    Each run records:
    - When it was scheduled and executed
    - Status and result
    - Output file location
    - Error information if failed
    """

    __tablename__: str = "custom_report_schedules"  # type: ignore[assignment]

    # Foreign key
    report_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("custom_reports.id", ondelete="CASCADE"),
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

    # Parameters used (JSON stored as text)
    # Stores the parameter values used for this run
    # Format: {
    #   "start_date": "2024-01-01",
    #   "end_date": "2024-01-31",
    #   "department": "Engineering"
    # }
    parameters_used: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
        doc="Parameter values used for this run",
    )

    # Relationships
    report: Mapped["CustomReport"] = relationship(
        "CustomReport",
        back_populates="schedules",
    )
    triggered_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[triggered_by_id],
    )

    # Indexes
    __table_args__ = (
        Index("ix_custom_report_schedules_report", "report_id"),
        Index("ix_custom_report_schedules_status", "status"),
        Index("ix_custom_report_schedules_scheduled_at", "scheduled_at"),
        Index("ix_custom_report_schedules_report_status", "report_id", "status"),
        Index(
            "ix_custom_report_schedules_report_scheduled",
            "report_id",
            "scheduled_at",
        ),
    )

    def __repr__(self) -> str:
        return f"<CustomReportSchedule report={self.report_id} status={self.status}>"

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

    def get_parameters_used_dict(self) -> dict:
        """Parse parameters_used JSON."""
        import json

        try:
            return json.loads(self.parameters_used or "{}")
        except json.JSONDecodeError:
            return {}

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
