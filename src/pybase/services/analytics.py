"""Analytics service for data aggregation and chart computations."""

import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from pybase.models.base import Base
from pybase.models.field import Field
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


class AnalyticsService:
    """Service for analytics operations and data aggregation."""

    async def aggregate_field(
        self,
        db: AsyncSession,
        user_id: str,
        table_id: str,
        field_id: str,
        aggregation_type: str,
        filters: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Aggregate data for a specific field.

        Args:
            db: Database session
            user_id: User ID making request
            table_id: Table ID to query
            field_id: Field ID to aggregate
            aggregation_type: Type of aggregation (sum, avg, count, min, max)
            filters: Optional filter conditions

        Returns:
            Dictionary with aggregation result

        Raises:
            NotFoundError: If table or field not found
            PermissionDeniedError: If user doesn't have access
            ValidationError: If aggregation type is invalid

        """
        # Check table access
        table = await self._get_table_with_access(db, table_id, user_id)

        # Validate field exists
        field = await self._get_field(db, field_id, table_id)

        # Validate aggregation type
        valid_aggregations = ["sum", "avg", "count", "min", "max", "median", "distinct_count"]
        if aggregation_type not in valid_aggregations:
            raise ValidationError(
                f"Invalid aggregation type. Must be one of: {', '.join(valid_aggregations)}"
            )

        # Get records
        records = await self._get_filtered_records(db, table_id, filters)

        # Perform aggregation
        result = await self._perform_aggregation(
            records, field.name, aggregation_type
        )

        return {
            "table_id": table_id,
            "field_id": field_id,
            "field_name": field.name,
            "aggregation_type": aggregation_type,
            "value": result,
            "record_count": len(records),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def group_by(
        self,
        db: AsyncSession,
        user_id: str,
        table_id: str,
        group_field_id: str,
        value_field_id: Optional[str] = None,
        aggregation_type: str = "count",
        filters: Optional[list[dict[str, Any]]] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Group records by a field and aggregate values.

        Args:
            db: Database session
            user_id: User ID making request
            table_id: Table ID to query
            group_field_id: Field ID to group by
            value_field_id: Field ID to aggregate (required for non-count aggregations)
            aggregation_type: Type of aggregation (sum, avg, count, min, max)
            filters: Optional filter conditions
            limit: Maximum number of groups to return

        Returns:
            Dictionary with grouped data

        Raises:
            NotFoundError: If table or fields not found
            PermissionDeniedError: If user doesn't have access
            ValidationError: If aggregation type is invalid

        """
        # Check table access
        table = await self._get_table_with_access(db, table_id, user_id)

        # Validate fields
        group_field = await self._get_field(db, group_field_id, table_id)
        value_field = None
        if value_field_id:
            value_field = await self._get_field(db, value_field_id, table_id)
        elif aggregation_type != "count":
            raise ValidationError(
                f"value_field_id is required for {aggregation_type} aggregation"
            )

        # Get records
        records = await self._get_filtered_records(db, table_id, filters)

        # Group and aggregate
        groups = await self._group_and_aggregate(
            records,
            group_field.name,
            value_field.name if value_field else None,
            aggregation_type,
            limit,
        )

        return {
            "table_id": table_id,
            "group_field": {
                "id": group_field_id,
                "name": group_field.name,
            },
            "value_field": {
                "id": value_field_id,
                "name": value_field.name,
            } if value_field else None,
            "aggregation_type": aggregation_type,
            "groups": groups,
            "total_groups": len(groups),
            "record_count": len(records),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def pivot_table(
        self,
        db: AsyncSession,
        user_id: str,
        table_id: str,
        row_field_id: str,
        column_field_id: Optional[str] = None,
        value_field_id: Optional[str] = None,
        aggregation_type: str = "count",
        filters: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Create a pivot table from records.

        Args:
            db: Database session
            user_id: User ID making request
            table_id: Table ID to query
            row_field_id: Field ID for pivot rows
            column_field_id: Optional field ID for pivot columns
            value_field_id: Field ID to aggregate
            aggregation_type: Type of aggregation (sum, avg, count, min, max)
            filters: Optional filter conditions

        Returns:
            Dictionary with pivot table data

        Raises:
            NotFoundError: If table or fields not found
            PermissionDeniedError: If user doesn't have access
            ValidationError: If configuration is invalid

        """
        # Check table access
        table = await self._get_table_with_access(db, table_id, user_id)

        # Validate fields
        row_field = await self._get_field(db, row_field_id, table_id)
        column_field = None
        if column_field_id:
            column_field = await self._get_field(db, column_field_id, table_id)

        value_field = None
        if value_field_id:
            value_field = await self._get_field(db, value_field_id, table_id)
        elif aggregation_type != "count":
            raise ValidationError(
                f"value_field_id is required for {aggregation_type} aggregation"
            )

        # Get records
        records = await self._get_filtered_records(db, table_id, filters)

        # Create pivot table
        pivot_data = await self._create_pivot(
            records,
            row_field.name,
            column_field.name if column_field else None,
            value_field.name if value_field else None,
            aggregation_type,
        )

        return {
            "table_id": table_id,
            "row_field": {
                "id": row_field_id,
                "name": row_field.name,
            },
            "column_field": {
                "id": column_field_id,
                "name": column_field.name,
            } if column_field else None,
            "value_field": {
                "id": value_field_id,
                "name": value_field.name,
            } if value_field else None,
            "aggregation_type": aggregation_type,
            "data": pivot_data,
            "record_count": len(records),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def compute_chart_data(
        self,
        db: AsyncSession,
        user_id: str,
        table_id: str,
        x_field_id: str,
        y_field_id: Optional[str] = None,
        group_field_id: Optional[str] = None,
        aggregation_type: str = "count",
        filters: Optional[list[dict[str, Any]]] = None,
        sorts: Optional[list[dict[str, str]]] = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Compute data for chart visualization.

        Args:
            db: Database session
            user_id: User ID making request
            table_id: Table ID to query
            x_field_id: Field ID for x-axis
            y_field_id: Field ID for y-axis values
            group_field_id: Optional field ID for grouping/series
            aggregation_type: Type of aggregation (sum, avg, count, min, max)
            filters: Optional filter conditions
            sorts: Optional sort configuration
            limit: Maximum number of data points

        Returns:
            Dictionary with chart data

        Raises:
            NotFoundError: If table or fields not found
            PermissionDeniedError: If user doesn't have access

        """
        # Check table access
        table = await self._get_table_with_access(db, table_id, user_id)

        # Validate fields
        x_field = await self._get_field(db, x_field_id, table_id)
        y_field = None
        if y_field_id:
            y_field = await self._get_field(db, y_field_id, table_id)
        elif aggregation_type != "count":
            raise ValidationError(
                f"y_field_id is required for {aggregation_type} aggregation"
            )

        group_field = None
        if group_field_id:
            group_field = await self._get_field(db, group_field_id, table_id)

        # Get records
        records = await self._get_filtered_records(db, table_id, filters)

        # Compute chart data
        chart_data = await self._compute_chart_series(
            records,
            x_field.name,
            y_field.name if y_field else None,
            group_field.name if group_field else None,
            aggregation_type,
            sorts,
            limit,
        )

        return {
            "table_id": table_id,
            "x_field": {
                "id": x_field_id,
                "name": x_field.name,
            },
            "y_field": {
                "id": y_field_id,
                "name": y_field.name,
            } if y_field else None,
            "group_field": {
                "id": group_field_id,
                "name": group_field.name,
            } if group_field else None,
            "aggregation_type": aggregation_type,
            "data": chart_data,
            "record_count": len(records),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def get_statistics(
        self,
        db: AsyncSession,
        user_id: str,
        table_id: str,
        field_ids: list[str],
        filters: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Get statistical summary for multiple fields.

        Args:
            db: Database session
            user_id: User ID making request
            table_id: Table ID to query
            field_ids: List of field IDs to analyze
            filters: Optional filter conditions

        Returns:
            Dictionary with statistics for each field

        Raises:
            NotFoundError: If table or fields not found
            PermissionDeniedError: If user doesn't have access

        """
        # Check table access
        table = await self._get_table_with_access(db, table_id, user_id)

        # Get records
        records = await self._get_filtered_records(db, table_id, filters)

        # Compute statistics for each field
        stats = {}
        for field_id in field_ids:
            field = await self._get_field(db, field_id, table_id)
            field_stats = await self._compute_field_statistics(
                records, field.name, field.field_type
            )
            stats[field_id] = {
                "field_name": field.name,
                "field_type": field.field_type,
                "statistics": field_stats,
            }

        return {
            "table_id": table_id,
            "fields": stats,
            "record_count": len(records),
            "timestamp": datetime.utcnow().isoformat(),
        }

    # Helper methods

    async def _get_table_with_access(
        self,
        db: AsyncSession,
        table_id: str,
        user_id: str,
    ) -> Table:
        """Get table and verify user has access.

        Args:
            db: Database session
            table_id: Table ID
            user_id: User ID

        Returns:
            Table

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access

        """
        table = await db.get(Table, table_id)
        if not table or table.is_deleted:
            raise NotFoundError("Table not found")

        # Check workspace access
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this table")

        return table

    async def _get_base(
        self,
        db: AsyncSession,
        base_id: str,
    ) -> Base:
        """Get base by ID.

        Args:
            db: Database session
            base_id: Base ID

        Returns:
            Base

        Raises:
            NotFoundError: If base not found

        """
        base = await db.get(Base, base_id)
        if not base or base.is_deleted:
            raise NotFoundError("Base not found")
        return base

    async def _get_workspace(
        self,
        db: AsyncSession,
        workspace_id: str,
    ) -> Workspace:
        """Get workspace by ID.

        Args:
            db: Database session
            workspace_id: Workspace ID

        Returns:
            Workspace

        Raises:
            NotFoundError: If workspace not found

        """
        workspace = await db.get(Workspace, workspace_id)
        if not workspace or workspace.is_deleted:
            raise NotFoundError("Workspace not found")
        return workspace

    async def _get_workspace_member(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
    ) -> Optional[WorkspaceMember]:
        """Get workspace member.

        Args:
            db: Database session
            workspace_id: Workspace ID
            user_id: User ID

        Returns:
            WorkspaceMember or None

        """
        query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _get_field(
        self,
        db: AsyncSession,
        field_id: str,
        table_id: str,
    ) -> Field:
        """Get field and verify it belongs to table.

        Args:
            db: Database session
            field_id: Field ID
            table_id: Table ID

        Returns:
            Field

        Raises:
            NotFoundError: If field not found or doesn't belong to table

        """
        field = await db.get(Field, field_id)
        if not field or field.is_deleted:
            raise NotFoundError("Field not found")

        if str(field.table_id) != str(table_id):
            raise NotFoundError("Field does not belong to this table")

        return field

    async def _get_filtered_records(
        self,
        db: AsyncSession,
        table_id: str,
        filters: Optional[list[dict[str, Any]]] = None,
    ) -> list[Record]:
        """Get records with optional filters applied.

        Args:
            db: Database session
            table_id: Table ID
            filters: Optional filter conditions

        Returns:
            List of records

        """
        query = select(Record).where(
            Record.table_id == table_id,
            Record.deleted_at.is_(None),
        )

        # Apply filters if provided
        # Note: Basic implementation - full filter logic would be more complex
        if filters:
            # Filters will be applied in memory for now
            # Production implementation should use database-level filtering
            pass

        result = await db.execute(query)
        records = list(result.scalars().all())

        # Apply in-memory filters if provided
        if filters:
            records = self._apply_filters_in_memory(records, filters)

        return records

    def _apply_filters_in_memory(
        self,
        records: list[Record],
        filters: list[dict[str, Any]],
    ) -> list[Record]:
        """Apply filters to records in memory.

        Args:
            records: List of records
            filters: Filter conditions

        Returns:
            Filtered list of records

        """
        filtered_records = []
        for record in records:
            data = record.get_all_values()
            matches = True

            for filter_condition in filters:
                field_id = filter_condition.get("field_id")
                operator = filter_condition.get("operator", "equals")
                value = filter_condition.get("value")

                record_value = data.get(field_id)

                # Apply operator logic
                if operator == "equals" and record_value != value:
                    matches = False
                    break
                elif operator == "not_equals" and record_value == value:
                    matches = False
                    break
                elif operator == "contains" and value not in str(record_value):
                    matches = False
                    break
                elif operator == "greater_than":
                    try:
                        if float(record_value) <= float(value):
                            matches = False
                            break
                    except (ValueError, TypeError):
                        matches = False
                        break
                elif operator == "less_than":
                    try:
                        if float(record_value) >= float(value):
                            matches = False
                            break
                    except (ValueError, TypeError):
                        matches = False
                        break

            if matches:
                filtered_records.append(record)

        return filtered_records

    async def _perform_aggregation(
        self,
        records: list[Record],
        field_name: str,
        aggregation_type: str,
    ) -> Any:
        """Perform aggregation on field values.

        Args:
            records: List of records
            field_name: Name of field to aggregate
            aggregation_type: Type of aggregation

        Returns:
            Aggregated value

        """
        values = []
        for record in records:
            data = record.get_all_values()
            value = data.get(field_name)
            if value is not None:
                values.append(value)

        if not values:
            return None

        if aggregation_type == "count":
            return len(records)
        elif aggregation_type == "distinct_count":
            return len(set(values))
        elif aggregation_type == "sum":
            return sum(float(v) for v in values if self._is_numeric(v))
        elif aggregation_type == "avg":
            numeric_values = [float(v) for v in values if self._is_numeric(v)]
            return sum(numeric_values) / len(numeric_values) if numeric_values else 0
        elif aggregation_type == "min":
            numeric_values = [float(v) for v in values if self._is_numeric(v)]
            return min(numeric_values) if numeric_values else None
        elif aggregation_type == "max":
            numeric_values = [float(v) for v in values if self._is_numeric(v)]
            return max(numeric_values) if numeric_values else None
        elif aggregation_type == "median":
            numeric_values = sorted([float(v) for v in values if self._is_numeric(v)])
            if not numeric_values:
                return None
            n = len(numeric_values)
            if n % 2 == 0:
                return (numeric_values[n // 2 - 1] + numeric_values[n // 2]) / 2
            else:
                return numeric_values[n // 2]

        return None

    async def _group_and_aggregate(
        self,
        records: list[Record],
        group_field_name: str,
        value_field_name: Optional[str],
        aggregation_type: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Group records and aggregate values.

        Args:
            records: List of records
            group_field_name: Field name to group by
            value_field_name: Field name to aggregate
            aggregation_type: Type of aggregation
            limit: Maximum number of groups

        Returns:
            List of grouped data

        """
        groups = {}
        for record in records:
            data = record.get_all_values()
            group_value = data.get(group_field_name)
            if group_value is None:
                group_value = "(empty)"

            if group_value not in groups:
                groups[group_value] = []
            groups[group_value].append(record)

        # Aggregate each group
        result = []
        for group_value, group_records in groups.items():
            if aggregation_type == "count":
                aggregated_value = len(group_records)
            else:
                aggregated_value = await self._perform_aggregation(
                    group_records, value_field_name, aggregation_type
                )

            result.append({
                "group": group_value,
                "value": aggregated_value,
                "count": len(group_records),
            })

        # Sort by value descending
        result.sort(key=lambda x: x["value"] if x["value"] is not None else 0, reverse=True)

        return result[:limit]

    async def _create_pivot(
        self,
        records: list[Record],
        row_field_name: str,
        column_field_name: Optional[str],
        value_field_name: Optional[str],
        aggregation_type: str,
    ) -> dict[str, Any]:
        """Create pivot table data structure.

        Args:
            records: List of records
            row_field_name: Field name for rows
            column_field_name: Field name for columns
            value_field_name: Field name to aggregate
            aggregation_type: Type of aggregation

        Returns:
            Pivot table data structure

        """
        if not column_field_name:
            # Simple one-dimensional pivot (just rows)
            groups = await self._group_and_aggregate(
                records, row_field_name, value_field_name, aggregation_type, 1000
            )
            return {
                "rows": [g["group"] for g in groups],
                "columns": ["value"],
                "values": [[g["value"]] for g in groups],
            }

        # Two-dimensional pivot
        pivot = {}
        columns = set()

        for record in records:
            data = record.get_all_values()
            row_value = data.get(row_field_name, "(empty)")
            col_value = data.get(column_field_name, "(empty)")
            columns.add(col_value)

            if row_value not in pivot:
                pivot[row_value] = {}
            if col_value not in pivot[row_value]:
                pivot[row_value][col_value] = []
            pivot[row_value][col_value].append(record)

        # Aggregate cells
        rows = list(pivot.keys())
        columns = sorted(list(columns))
        values = []

        for row_value in rows:
            row_values = []
            for col_value in columns:
                cell_records = pivot[row_value].get(col_value, [])
                if cell_records:
                    if aggregation_type == "count":
                        cell_value = len(cell_records)
                    else:
                        cell_value = await self._perform_aggregation(
                            cell_records, value_field_name, aggregation_type
                        )
                else:
                    cell_value = 0
                row_values.append(cell_value)
            values.append(row_values)

        return {
            "rows": rows,
            "columns": columns,
            "values": values,
        }

    async def _compute_chart_series(
        self,
        records: list[Record],
        x_field_name: str,
        y_field_name: Optional[str],
        group_field_name: Optional[str],
        aggregation_type: str,
        sorts: Optional[list[dict[str, str]]],
        limit: int,
    ) -> dict[str, Any]:
        """Compute chart data series.

        Args:
            records: List of records
            x_field_name: X-axis field name
            y_field_name: Y-axis field name
            group_field_name: Grouping field name
            aggregation_type: Type of aggregation
            sorts: Sort configuration
            limit: Maximum data points

        Returns:
            Chart data with series

        """
        if not group_field_name:
            # Single series
            groups = await self._group_and_aggregate(
                records, x_field_name, y_field_name, aggregation_type, limit
            )
            return {
                "labels": [g["group"] for g in groups],
                "series": [{
                    "name": "Value",
                    "data": [g["value"] for g in groups],
                }],
            }

        # Multiple series (grouped)
        series_data = {}
        labels = set()

        for record in records:
            data = record.get_all_values()
            x_value = data.get(x_field_name, "(empty)")
            group_value = data.get(group_field_name, "(empty)")
            labels.add(x_value)

            if group_value not in series_data:
                series_data[group_value] = {}
            if x_value not in series_data[group_value]:
                series_data[group_value][x_value] = []
            series_data[group_value][x_value].append(record)

        # Aggregate series
        labels = sorted(list(labels))[:limit]
        series = []

        for group_value, group_data in series_data.items():
            series_values = []
            for x_value in labels:
                cell_records = group_data.get(x_value, [])
                if cell_records:
                    if aggregation_type == "count":
                        value = len(cell_records)
                    else:
                        value = await self._perform_aggregation(
                            cell_records, y_field_name, aggregation_type
                        )
                else:
                    value = 0
                series_values.append(value)

            series.append({
                "name": str(group_value),
                "data": series_values,
            })

        return {
            "labels": labels,
            "series": series,
        }

    async def _compute_field_statistics(
        self,
        records: list[Record],
        field_name: str,
        field_type: str,
    ) -> dict[str, Any]:
        """Compute statistical summary for a field.

        Args:
            records: List of records
            field_name: Field name
            field_type: Field type

        Returns:
            Dictionary of statistics

        """
        values = []
        for record in records:
            data = record.get_all_values()
            value = data.get(field_name)
            if value is not None:
                values.append(value)

        stats = {
            "count": len(values),
            "null_count": len(records) - len(values),
        }

        if not values:
            return stats

        # Numeric statistics
        numeric_values = [float(v) for v in values if self._is_numeric(v)]
        if numeric_values:
            stats.update({
                "sum": sum(numeric_values),
                "avg": sum(numeric_values) / len(numeric_values),
                "min": min(numeric_values),
                "max": max(numeric_values),
                "median": self._calculate_median(numeric_values),
            })

        # Distinct values
        stats["distinct_count"] = len(set(str(v) for v in values))

        # Most common values (top 5)
        value_counts = {}
        for v in values:
            v_str = str(v)
            value_counts[v_str] = value_counts.get(v_str, 0) + 1

        most_common = sorted(
            value_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        stats["most_common"] = [
            {"value": v, "count": c} for v, c in most_common
        ]

        return stats

    def _is_numeric(self, value: Any) -> bool:
        """Check if value is numeric.

        Args:
            value: Value to check

        Returns:
            True if numeric, False otherwise

        """
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def _calculate_median(self, values: list[float]) -> float:
        """Calculate median of numeric values.

        Args:
            values: List of numeric values

        Returns:
            Median value

        """
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        else:
            return sorted_values[n // 2]
