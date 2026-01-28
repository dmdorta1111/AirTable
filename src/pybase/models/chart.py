"""
Chart model - visual representations of data for analytics dashboards.

Charts display data from tables in various visual formats like line, bar, pie, etc.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import SoftDeleteModel, utc_now

if TYPE_CHECKING:
    from pybase.models.dashboard import Dashboard
    from pybase.models.table import Table
    from pybase.models.user import User


class ChartType(str, Enum):
    """Supported chart types."""

    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    GAUGE = "gauge"
    DONUT = "donut"
    HEATMAP = "heatmap"
    HISTOGRAM = "histogram"


class AggregationType(str, Enum):
    """Data aggregation types for chart calculations."""

    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    DISTINCT_COUNT = "distinct_count"


class Chart(SoftDeleteModel):
    """
    Chart model - a visual representation of table data.

    Each chart has:
    - Type (line, bar, pie, scatter, gauge, etc.)
    - Data source configuration (table, fields, aggregation)
    - Visual configuration (colors, legend, axes)
    - Position in dashboard layout
    """

    __tablename__: str = "charts"  # type: ignore[assignment]

    # Foreign keys
    dashboard_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    table_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Table to query data from",
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
    chart_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ChartType.BAR.value,
    )

    # Position in dashboard
    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Order in dashboard layout",
    )

    # Widget dimensions (for dashboard grid layout)
    width: Mapped[int] = mapped_column(
        Integer,
        default=6,
        nullable=False,
        doc="Width in grid columns (1-12)",
    )
    height: Mapped[int] = mapped_column(
        Integer,
        default=4,
        nullable=False,
        doc="Height in grid rows",
    )

    # Data configuration (JSON stored as text)
    # Stores: x_field, y_field, group_by_field, aggregation_type, date_range
    # Format: {
    #   "x_field_id": "field-uuid",
    #   "y_field_id": "field-uuid",
    #   "group_by_field_id": "field-uuid",
    #   "aggregation": "sum",
    #   "date_range": "last_30_days",
    #   "limit": 10
    # }
    data_config: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    # Filtering configuration (JSON stored as text)
    # Stores: filter conditions applied to chart data
    # Format: [
    #   {"field_id": "field-uuid", "operator": "equals", "value": "Active"},
    #   {"field_id": "field-uuid", "operator": "greater_than", "value": 100}
    # ]
    filters: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="[]",
    )

    # Sorting configuration (JSON stored as text)
    # Stores: how to sort chart data
    # Format: [
    #   {"field": "value", "direction": "desc"}
    # ]
    sorts: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="[]",
    )

    # Visual configuration (JSON stored as text)
    # Chart-type specific visual settings
    # Grid/Bar/Line: show_legend, show_grid, show_values, stacked
    # Pie/Donut: show_labels, show_percentages, donut_width
    # Gauge: min_value, max_value, thresholds (green/yellow/red)
    # Format: {
    #   "show_legend": true,
    #   "show_grid": true,
    #   "show_values": false,
    #   "stacked": false,
    #   "colors": ["#FF6384", "#36A2EB", "#FFCE56"],
    #   "legend_position": "bottom"
    # }
    visual_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Axis configuration for charts that support axes (JSON stored as text)
    # Format: {
    #   "x_axis": {"label": "Date", "show": true},
    #   "y_axis": {"label": "Revenue", "show": true, "format": "currency"}
    # }
    axis_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Color/theme
    color_scheme: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Color scheme preset (default, blue, green, etc.)",
    )

    # Drill-down configuration (JSON stored as text)
    # Allows clicking chart elements to see underlying records
    # Format: {
    #   "enabled": true,
    #   "target_view_id": "view-uuid"
    # }
    drilldown_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Refresh settings
    auto_refresh: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Auto-refresh chart data on interval",
    )
    refresh_interval: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Refresh interval in seconds (if auto_refresh enabled)",
    )

    # Cache settings
    cache_duration: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Cache duration in seconds (null = no cache)",
    )

    # Last data refresh tracking
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Last time chart data was refreshed",
    )

    # Relationships
    dashboard: Mapped["Dashboard"] = relationship(
        "Dashboard",
        backref="charts",
    )
    table: Mapped["Table"] = relationship(
        "Table",
        backref="charts",
    )
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )

    # Indexes
    __table_args__ = (
        Index("ix_charts_dashboard_position", "dashboard_id", "position"),
        Index("ix_charts_table", "table_id"),
        Index("ix_charts_type", "chart_type"),
        Index("ix_charts_dashboard_type", "dashboard_id", "chart_type"),
    )

    def __repr__(self) -> str:
        return f"<Chart {self.name} ({self.chart_type})>"

    @property
    def type_enum(self) -> ChartType:
        """Get chart type as enum."""
        return ChartType(self.chart_type)

    def get_data_config_dict(self) -> dict:
        """Parse data_config JSON."""
        import json

        try:
            return json.loads(self.data_config or "{}")
        except json.JSONDecodeError:
            return {}

    def get_filters_list(self) -> list:
        """Parse filters JSON."""
        import json

        try:
            return json.loads(self.filters or "[]")
        except json.JSONDecodeError:
            return []

    def get_sorts_list(self) -> list:
        """Parse sorts JSON."""
        import json

        try:
            return json.loads(self.sorts or "[]")
        except json.JSONDecodeError:
            return []

    def get_visual_config_dict(self) -> dict:
        """Parse visual_config JSON."""
        import json

        try:
            return json.loads(self.visual_config or "{}")
        except json.JSONDecodeError:
            return {}

    def get_axis_config_dict(self) -> dict:
        """Parse axis_config JSON."""
        import json

        try:
            return json.loads(self.axis_config or "{}")
        except json.JSONDecodeError:
            return {}

    def get_drilldown_config_dict(self) -> dict:
        """Parse drilldown_config JSON."""
        import json

        try:
            return json.loads(self.drilldown_config or "{}")
        except json.JSONDecodeError:
            return {}

    def update_last_refreshed(self) -> None:
        """Update last refreshed timestamp."""
        self.last_refreshed_at = utc_now()

    @property
    def is_cached(self) -> bool:
        """Check if chart has caching enabled."""
        return self.cache_duration is not None and self.cache_duration > 0

    @property
    def supports_drilldown(self) -> bool:
        """Check if chart has drill-down configured."""
        config = self.get_drilldown_config_dict()
        return config.get("enabled", False) is True

    @property
    def needs_refresh(self) -> bool:
        """Check if chart data needs refresh based on cache settings."""
        if not self.is_cached or self.last_refreshed_at is None:
            return True

        from datetime import timedelta

        cache_expiry = self.last_refreshed_at + timedelta(seconds=self.cache_duration)
        return utc_now() > cache_expiry
