"""Chart schemas for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


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


class AggregationType(str, Enum):
    """Data aggregation types for chart calculations."""

    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    DISTINCT_COUNT = "distinct_count"


class DateRangeType(str, Enum):
    """Date range types for time-based charts."""

    ALL_TIME = "all_time"
    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    THIS_WEEK = "this_week"
    THIS_MONTH = "this_month"
    THIS_QUARTER = "this_quarter"
    THIS_YEAR = "this_year"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    LAST_QUARTER = "last_quarter"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"


class FilterOperator(str, Enum):
    """Filter operators for chart data."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN_OR_EQUAL = "lte"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"


class SortDirection(str, Enum):
    """Sort direction."""

    ASC = "asc"
    DESC = "desc"


class LegendPosition(str, Enum):
    """Legend position options."""

    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    NONE = "none"


class AxisFormat(str, Enum):
    """Axis value formatting options."""

    NUMBER = "number"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    DURATION = "duration"
    DATE = "date"
    DATETIME = "datetime"
    CUSTOM = "custom"


# =============================================================================
# Chart Configuration Schemas
# =============================================================================


class FilterCondition(BaseModel):
    """A single filter condition for chart data."""

    field_id: UUID = Field(..., description="Field to filter on")
    operator: FilterOperator = Field(..., description="Filter operator")
    value: Any = Field(None, description="Value to compare against")


class SortRule(BaseModel):
    """A single sort rule for chart data."""

    field: str = Field(..., description="Field to sort by (value, label, etc.)")
    direction: SortDirection = Field(default=SortDirection.ASC, description="Sort direction")


class DataConfig(BaseModel):
    """Chart data configuration."""

    x_field_id: Optional[UUID] = Field(None, description="X-axis field (for x/y charts)")
    y_field_id: Optional[UUID] = Field(None, description="Y-axis field (for x/y charts)")
    group_by_field_id: Optional[UUID] = Field(None, description="Field to group data by")
    aggregation: AggregationType = Field(
        default=AggregationType.COUNT, description="Aggregation type"
    )
    date_range: Optional[DateRangeType] = Field(None, description="Date range filter")
    custom_date_start: Optional[datetime] = Field(None, description="Custom date range start")
    custom_date_end: Optional[datetime] = Field(None, description="Custom date range end")
    limit: Optional[int] = Field(None, ge=1, le=1000, description="Maximum number of data points")
    series: Optional[list[dict[str, Any]]] = Field(
        None, description="Multiple series configuration for multi-line/bar charts"
    )


class AxisConfig(BaseModel):
    """Chart axis configuration."""

    x_axis: Optional[dict[str, Any]] = Field(
        None,
        description="X-axis config: {label: str, show: bool, format: str, min: float, max: float}",
    )
    y_axis: Optional[dict[str, Any]] = Field(
        None,
        description="Y-axis config: {label: str, show: bool, format: str, min: float, max: float}",
    )


class VisualConfig(BaseModel):
    """Chart visual configuration - common settings."""

    show_legend: bool = Field(default=True, description="Show legend")
    legend_position: LegendPosition = Field(
        default=LegendPosition.BOTTOM, description="Legend position"
    )
    show_grid: bool = Field(default=True, description="Show grid lines")
    show_values: bool = Field(default=False, description="Show values on data points")
    colors: Optional[list[str]] = Field(None, description="Custom color palette (hex colors)")
    opacity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Chart opacity")
    animation_enabled: bool = Field(default=True, description="Enable animations")


class LineChartConfig(VisualConfig):
    """Line chart specific configuration."""

    line_style: str = Field(default="solid", description="Line style: solid, dashed, dotted")
    line_width: int = Field(default=2, ge=1, le=10, description="Line width in pixels")
    show_points: bool = Field(default=True, description="Show data points")
    point_radius: int = Field(default=3, ge=1, le=10, description="Point radius in pixels")
    fill_area: bool = Field(default=False, description="Fill area under line")
    smooth_curve: bool = Field(default=False, description="Smooth line curve")


class BarChartConfig(VisualConfig):
    """Bar chart specific configuration."""

    orientation: str = Field(default="vertical", description="Orientation: vertical, horizontal")
    stacked: bool = Field(default=False, description="Stack bars")
    bar_width: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Bar width as ratio (0.5 = half spacing)"
    )
    show_data_labels: bool = Field(default=False, description="Show value labels on bars")


class PieChartConfig(VisualConfig):
    """Pie chart specific configuration."""

    show_labels: bool = Field(default=True, description="Show slice labels")
    show_percentages: bool = Field(default=True, description="Show percentage values")
    inner_radius: Optional[float] = Field(
        None, ge=0.0, le=0.9, description="Inner radius ratio (for donut charts)"
    )
    start_angle: int = Field(default=0, ge=0, le=360, description="Start angle in degrees")


class DonutChartConfig(PieChartConfig):
    """Donut chart specific configuration (extends pie chart)."""

    donut_width: int = Field(default=30, ge=10, le=100, description="Donut ring width in pixels")


class ScatterChartConfig(VisualConfig):
    """Scatter chart specific configuration."""

    point_size: int = Field(default=5, ge=1, le=20, description="Point size in pixels")
    show_regression_line: bool = Field(default=False, description="Show regression/trend line")


class GaugeChartConfig(BaseModel):
    """Gauge chart specific configuration."""

    min_value: float = Field(default=0.0, description="Minimum gauge value")
    max_value: float = Field(default=100.0, description="Maximum gauge value")
    target_value: Optional[float] = Field(None, description="Target value marker")
    thresholds: Optional[list[dict[str, Any]]] = Field(
        None,
        description="Threshold ranges: [{value: float, color: str, label: str}]",
    )
    show_value: bool = Field(default=True, description="Show current value")
    show_min_max: bool = Field(default=True, description="Show min/max labels")
    arc_width: int = Field(default=20, ge=5, le=50, description="Arc width in pixels")


class HeatmapChartConfig(VisualConfig):
    """Heatmap chart specific configuration."""

    color_scale: str = Field(
        default="blue-red", description="Color scale: blue-red, green-red, viridis, etc."
    )
    show_values: bool = Field(default=True, description="Show cell values")
    cell_padding: int = Field(default=2, ge=0, le=10, description="Padding between cells")


class DrilldownConfig(BaseModel):
    """Chart drill-down configuration."""

    enabled: bool = Field(default=False, description="Enable drill-down functionality")
    target_view_id: Optional[UUID] = Field(
        None, description="View to navigate to when clicking chart elements"
    )
    pass_filters: bool = Field(
        default=True, description="Pass clicked value as filter to target view"
    )


# =============================================================================
# Main Chart Schemas
# =============================================================================


class ChartBase(BaseModel):
    """Base schema for chart."""

    name: str = Field(..., min_length=1, max_length=255, description="Chart name")
    description: Optional[str] = Field(None, max_length=5000, description="Chart description")
    chart_type: ChartType = Field(default=ChartType.BAR, description="Chart type")


class ChartCreate(ChartBase):
    """Schema for creating a chart."""

    dashboard_id: UUID = Field(..., description="Dashboard ID")
    table_id: UUID = Field(..., description="Table to query data from")
    position: int = Field(default=0, ge=0, description="Position in dashboard layout")
    width: int = Field(default=6, ge=1, le=12, description="Width in grid columns (1-12)")
    height: int = Field(default=4, ge=1, le=24, description="Height in grid rows")

    # Configuration
    data_config: DataConfig = Field(..., description="Data source configuration")
    filters: list[FilterCondition] = Field(default_factory=list, description="Filter conditions")
    sorts: list[SortRule] = Field(default_factory=list, description="Sort rules")
    visual_config: Optional[dict[str, Any]] = Field(None, description="Visual configuration")
    axis_config: Optional[AxisConfig] = Field(None, description="Axis configuration")
    drilldown_config: Optional[DrilldownConfig] = Field(None, description="Drill-down config")

    # Display options
    color_scheme: Optional[str] = Field(
        None, max_length=50, description="Color scheme preset (default, blue, green, etc.)"
    )

    # Refresh settings
    auto_refresh: bool = Field(default=False, description="Auto-refresh chart data")
    refresh_interval: Optional[int] = Field(
        None, ge=5, le=3600, description="Refresh interval in seconds"
    )
    cache_duration: Optional[int] = Field(
        None, ge=0, description="Cache duration in seconds (0 = no cache)"
    )


class ChartUpdate(BaseModel):
    """Schema for updating a chart."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Chart name")
    description: Optional[str] = Field(None, max_length=5000, description="Chart description")
    chart_type: Optional[ChartType] = Field(None, description="Chart type")
    position: Optional[int] = Field(None, ge=0, description="Position in dashboard")
    width: Optional[int] = Field(None, ge=1, le=12, description="Width in grid columns")
    height: Optional[int] = Field(None, ge=1, le=24, description="Height in grid rows")

    # Configuration updates
    data_config: Optional[DataConfig] = Field(None, description="Data configuration")
    filters: Optional[list[FilterCondition]] = Field(None, description="Filter conditions")
    sorts: Optional[list[SortRule]] = Field(None, description="Sort rules")
    visual_config: Optional[dict[str, Any]] = Field(None, description="Visual configuration")
    axis_config: Optional[AxisConfig] = Field(None, description="Axis configuration")
    drilldown_config: Optional[DrilldownConfig] = Field(None, description="Drill-down config")

    # Display options
    color_scheme: Optional[str] = Field(None, max_length=50, description="Color scheme")

    # Refresh settings
    auto_refresh: Optional[bool] = Field(None, description="Auto-refresh chart data")
    refresh_interval: Optional[int] = Field(None, ge=5, le=3600, description="Refresh interval")
    cache_duration: Optional[int] = Field(None, ge=0, description="Cache duration")


class ChartResponse(ChartBase):
    """Schema for chart response."""

    id: UUID
    dashboard_id: UUID
    table_id: UUID
    created_by_id: Optional[UUID]
    position: int
    width: int
    height: int

    # Parsed configuration
    data_config: dict[str, Any]
    filters: list[dict[str, Any]] = Field(default_factory=list)
    sorts: list[dict[str, Any]] = Field(default_factory=list)
    visual_config: Optional[dict[str, Any]] = None
    axis_config: Optional[dict[str, Any]] = None
    drilldown_config: Optional[dict[str, Any]] = None

    # Display options
    color_scheme: Optional[str]

    # Refresh settings
    auto_refresh: bool
    refresh_interval: Optional[int]
    cache_duration: Optional[int]
    last_refreshed_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChartListResponse(BaseModel):
    """Schema for chart list response."""

    items: list[ChartResponse]
    total: int
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)


# =============================================================================
# Chart Data Response Schemas
# =============================================================================


class ChartDataPoint(BaseModel):
    """A single data point in chart data."""

    label: str = Field(..., description="Data point label (x-axis value)")
    value: float = Field(..., description="Data point value (y-axis value)")
    color: Optional[str] = Field(None, description="Custom color for this data point")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")


class ChartSeries(BaseModel):
    """A data series for multi-series charts."""

    name: str = Field(..., description="Series name")
    data: list[ChartDataPoint] = Field(..., description="Data points in this series")
    color: Optional[str] = Field(None, description="Series color")


class ChartDataResponse(BaseModel):
    """Schema for computed chart data response."""

    chart_id: UUID = Field(..., description="Chart ID")
    chart_type: ChartType = Field(..., description="Chart type")
    data: list[ChartDataPoint] = Field(default_factory=list, description="Chart data points")
    series: Optional[list[ChartSeries]] = Field(None, description="Multiple series (if applicable)")
    labels: list[str] = Field(default_factory=list, description="All unique labels")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (total_records, aggregation_type, etc.)",
    )
    generated_at: datetime = Field(..., description="When this data was generated")
    cached: bool = Field(default=False, description="Whether this data was cached")


class ChartDataRequest(BaseModel):
    """Schema for requesting chart data with optional overrides."""

    filters: Optional[list[FilterCondition]] = Field(
        None, description="Override chart filters temporarily"
    )
    date_range: Optional[DateRangeType] = Field(None, description="Override date range")
    custom_date_start: Optional[datetime] = Field(None, description="Custom date range start")
    custom_date_end: Optional[datetime] = Field(None, description="Custom date range end")
    limit: Optional[int] = Field(None, ge=1, le=1000, description="Limit number of data points")
    bypass_cache: bool = Field(
        default=False, description="Bypass cache and fetch fresh data"
    )


# =============================================================================
# Chart Duplication Schema
# =============================================================================


class ChartDuplicate(BaseModel):
    """Schema for duplicating a chart."""

    name: str = Field(..., min_length=1, max_length=255, description="Name for the duplicate")
    dashboard_id: Optional[UUID] = Field(
        None, description="Dashboard to copy to (defaults to same dashboard)"
    )
    include_data_config: bool = Field(default=True, description="Copy data configuration")
    include_visual_config: bool = Field(default=True, description="Copy visual configuration")
    include_filters: bool = Field(default=True, description="Copy filters")
    include_drilldown: bool = Field(default=True, description="Copy drill-down configuration")
