"""Analytics schemas for request/response validation."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from pybase.schemas.chart import AggregationType, FilterOperator


# =============================================================================
# Filter Schemas
# =============================================================================


class FilterCondition(BaseModel):
    """Filter condition for analytics queries."""

    field_id: str = Field(description="Field ID to filter on")
    operator: FilterOperator = Field(description="Filter operator")
    value: Any = Field(description="Filter value")


# =============================================================================
# Aggregate Field Schemas
# =============================================================================


class AggregateFieldRequest(BaseModel):
    """Request schema for field aggregation."""

    table_id: UUID = Field(description="Table ID to aggregate")
    field_id: UUID = Field(description="Field ID to aggregate")
    aggregation_type: AggregationType = Field(
        description="Type of aggregation (sum, avg, count, min, max, median, distinct_count)"
    )
    filters: Optional[list[FilterCondition]] = Field(
        default=None,
        description="Optional filter conditions",
    )


class AggregateFieldResponse(BaseModel):
    """Response schema for field aggregation."""

    table_id: str = Field(description="Table ID")
    field_id: str = Field(description="Field ID")
    field_name: str = Field(description="Field name")
    aggregation_type: str = Field(description="Aggregation type used")
    value: Any = Field(description="Aggregated value")
    record_count: int = Field(description="Number of records aggregated")
    timestamp: str = Field(description="Timestamp of aggregation")


# =============================================================================
# Group By Schemas
# =============================================================================


class GroupByRequest(BaseModel):
    """Request schema for group by aggregation."""

    table_id: UUID = Field(description="Table ID to query")
    group_field_id: UUID = Field(description="Field ID to group by")
    value_field_id: Optional[UUID] = Field(
        default=None,
        description="Field ID to aggregate (required for non-count aggregations)",
    )
    aggregation_type: AggregationType = Field(
        default=AggregationType.COUNT,
        description="Type of aggregation",
    )
    filters: Optional[list[FilterCondition]] = Field(
        default=None,
        description="Optional filter conditions",
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of groups to return (1-1000)",
    )


class FieldInfo(BaseModel):
    """Field information."""

    id: str = Field(description="Field ID")
    name: str = Field(description="Field name")


class GroupInfo(BaseModel):
    """Grouped data information."""

    group_value: Any = Field(description="Group key value")
    aggregated_value: Any = Field(description="Aggregated value for group")
    record_count: int = Field(description="Number of records in group")


class GroupByResponse(BaseModel):
    """Response schema for group by aggregation."""

    table_id: str = Field(description="Table ID")
    group_field: FieldInfo = Field(description="Field used for grouping")
    value_field: Optional[FieldInfo] = Field(
        default=None,
        description="Field used for aggregation",
    )
    aggregation_type: str = Field(description="Aggregation type used")
    groups: list[GroupInfo] = Field(description="Grouped data")
    total_groups: int = Field(description="Total number of groups")
    record_count: int = Field(description="Total number of records processed")
    timestamp: str = Field(description="Timestamp of aggregation")


# =============================================================================
# Pivot Table Schemas
# =============================================================================


class PivotTableRequest(BaseModel):
    """Request schema for pivot table generation."""

    table_id: UUID = Field(description="Table ID to query")
    row_field_id: UUID = Field(description="Field ID for pivot rows")
    column_field_id: Optional[UUID] = Field(
        default=None,
        description="Optional field ID for pivot columns",
    )
    value_field_id: Optional[UUID] = Field(
        default=None,
        description="Field ID to aggregate",
    )
    aggregation_type: AggregationType = Field(
        default=AggregationType.COUNT,
        description="Type of aggregation",
    )
    filters: Optional[list[FilterCondition]] = Field(
        default=None,
        description="Optional filter conditions",
    )


class PivotCell(BaseModel):
    """Pivot table cell data."""

    row: str = Field(description="Row key")
    column: Optional[str] = Field(default=None, description="Column key (for 2D pivots)")
    value: Any = Field(description="Cell value")
    record_count: int = Field(description="Number of records in cell")


class PivotTableResponse(BaseModel):
    """Response schema for pivot table."""

    table_id: str = Field(description="Table ID")
    row_field: FieldInfo = Field(description="Field used for rows")
    column_field: Optional[FieldInfo] = Field(
        default=None,
        description="Field used for columns",
    )
    value_field: Optional[FieldInfo] = Field(
        default=None,
        description="Field used for values",
    )
    aggregation_type: str = Field(description="Aggregation type used")
    data: dict[str, Any] = Field(description="Pivot table data")
    record_count: int = Field(description="Total number of records processed")
    timestamp: str = Field(description="Timestamp of aggregation")


# =============================================================================
# Statistics Schemas
# =============================================================================


class StatisticsRequest(BaseModel):
    """Request schema for field statistics."""

    table_id: UUID = Field(description="Table ID to analyze")
    field_id: UUID = Field(description="Field ID to get statistics for")
    filters: Optional[list[FilterCondition]] = Field(
        default=None,
        description="Optional filter conditions",
    )


class StatisticsResponse(BaseModel):
    """Response schema for field statistics."""

    table_id: str = Field(description="Table ID")
    field_id: str = Field(description="Field ID")
    field_name: str = Field(description="Field name")
    statistics: dict[str, Any] = Field(
        description="Statistical measures (count, sum, avg, min, max, median, std_dev, etc.)"
    )
    record_count: int = Field(description="Number of records analyzed")
    timestamp: str = Field(description="Timestamp of analysis")
