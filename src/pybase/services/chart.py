"""Chart service for business logic."""

import json
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from pybase.db.base import utc_now
from pybase.models.base import Base
from pybase.models.chart import Chart, ChartType
from pybase.models.dashboard import Dashboard
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.chart import (
    ChartCreate,
    ChartDataRequest,
    ChartDataResponse,
    ChartDuplicate,
    ChartUpdate,
    ChartDataPoint,
    ChartSeries,
    AggregationType,
)
from pybase.services.analytics import AnalyticsService


class ChartService:
    """Service for chart operations."""

    def __init__(self):
        """Initialize chart service with analytics service."""
        self.analytics_service = AnalyticsService()

    async def create_chart(
        self,
        db: AsyncSession,
        user_id: str,
        chart_data: ChartCreate,
    ) -> Chart:
        """Create a new chart for a dashboard.

        Args:
            db: Database session
            user_id: User ID creating the chart
            chart_data: Chart creation data

        Returns:
            Created chart

        Raises:
            NotFoundError: If dashboard or table not found
            PermissionDeniedError: If user doesn't have access

        """
        # Check if dashboard exists and user has access
        dashboard = await self._get_dashboard_with_access(db, str(chart_data.dashboard_id), user_id)

        # Check if table exists and user has access
        table = await self._get_table_with_access(db, str(chart_data.table_id), user_id)

        # Determine position (append to end)
        max_position_query = select(func.max(Chart.position)).where(
            Chart.dashboard_id == str(chart_data.dashboard_id),
            Chart.deleted_at.is_(None),
        )
        result = await db.execute(max_position_query)
        max_position = result.scalar() or 0

        # Serialize configurations to JSON
        data_config = json.dumps(chart_data.data_config.model_dump(mode="json"))
        filters = json.dumps([f.model_dump(mode="json") for f in chart_data.filters])
        sorts = json.dumps([s.model_dump(mode="json") for s in chart_data.sorts])

        visual_config = None
        if chart_data.visual_config:
            visual_config = json.dumps(chart_data.visual_config)

        axis_config = None
        if chart_data.axis_config:
            axis_config = json.dumps(chart_data.axis_config.model_dump(mode="json"))

        drilldown_config = None
        if chart_data.drilldown_config:
            drilldown_config = json.dumps(chart_data.drilldown_config.model_dump(mode="json"))

        # Create chart
        chart = Chart(
            dashboard_id=str(chart_data.dashboard_id),
            table_id=str(chart_data.table_id),
            created_by_id=user_id,
            name=chart_data.name,
            description=chart_data.description,
            chart_type=chart_data.chart_type.value,
            position=chart_data.position if chart_data.position is not None else max_position + 1,
            width=chart_data.width,
            height=chart_data.height,
            data_config=data_config,
            filters=filters,
            sorts=sorts,
            visual_config=visual_config or "{}",
            axis_config=axis_config or "{}",
            drilldown_config=drilldown_config or "{}",
            color_scheme=chart_data.color_scheme,
            auto_refresh=chart_data.auto_refresh,
            refresh_interval=chart_data.refresh_interval,
            cache_duration=chart_data.cache_duration,
        )
        db.add(chart)
        await db.commit()
        await db.refresh(chart)

        return chart

    async def get_chart_by_id(
        self,
        db: AsyncSession,
        chart_id: str,
        user_id: str,
    ) -> Chart:
        """Get a chart by ID, checking user access.

        Args:
            db: Database session
            chart_id: Chart ID
            user_id: User ID requesting access

        Returns:
            Chart

        Raises:
            NotFoundError: If chart not found
            PermissionDeniedError: If user doesn't have access

        """
        chart = await db.get(Chart, chart_id)
        if not chart or chart.is_deleted:
            raise NotFoundError("Chart not found")

        # Check user access to dashboard
        await self._get_dashboard_with_access(db, chart.dashboard_id, user_id)

        return chart

    async def list_charts(
        self,
        db: AsyncSession,
        dashboard_id: UUID,
        user_id: str,
        chart_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Chart], int]:
        """List charts for a dashboard.

        Args:
            db: Database session
            dashboard_id: Dashboard ID
            user_id: User ID
            chart_type: Optional chart type filter
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (charts, total count)

        """
        # Check user access to dashboard
        await self._get_dashboard_with_access(db, str(dashboard_id), user_id)

        offset = (page - 1) * page_size

        # Base conditions
        conditions = [
            Chart.dashboard_id == str(dashboard_id),
            Chart.deleted_at.is_(None),
        ]

        if chart_type:
            conditions.append(Chart.chart_type == chart_type)

        # Count query
        count_query = select(func.count()).select_from(Chart).where(*conditions)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query
        query = (
            select(Chart).where(*conditions).order_by(Chart.position).offset(offset).limit(page_size)
        )
        result = await db.execute(query)
        charts = result.scalars().all()

        return list(charts), total

    async def update_chart(
        self,
        db: AsyncSession,
        chart_id: str,
        user_id: str,
        chart_data: ChartUpdate,
    ) -> Chart:
        """Update a chart.

        Args:
            db: Database session
            chart_id: Chart ID to update
            user_id: User ID making the update
            chart_data: Updated chart data

        Returns:
            Updated chart

        Raises:
            NotFoundError: If chart not found
            PermissionDeniedError: If user doesn't have edit access

        """
        # Get chart and check access
        chart = await self.get_chart_by_id(db, chart_id, user_id)

        # Check edit permission
        await self._check_dashboard_edit_permission(db, chart.dashboard_id, user_id)

        # Update basic fields
        if chart_data.name is not None:
            chart.name = chart_data.name
        if chart_data.description is not None:
            chart.description = chart_data.description
        if chart_data.chart_type is not None:
            chart.chart_type = chart_data.chart_type.value
        if chart_data.position is not None:
            chart.position = chart_data.position
        if chart_data.width is not None:
            chart.width = chart_data.width
        if chart_data.height is not None:
            chart.height = chart_data.height
        if chart_data.color_scheme is not None:
            chart.color_scheme = chart_data.color_scheme

        # Update configuration fields
        if chart_data.data_config is not None:
            chart.data_config = json.dumps(chart_data.data_config.model_dump(mode="json"))
        if chart_data.filters is not None:
            chart.filters = json.dumps([f.model_dump(mode="json") for f in chart_data.filters])
        if chart_data.sorts is not None:
            chart.sorts = json.dumps([s.model_dump(mode="json") for s in chart_data.sorts])
        if chart_data.visual_config is not None:
            chart.visual_config = json.dumps(chart_data.visual_config)
        if chart_data.axis_config is not None:
            chart.axis_config = json.dumps(chart_data.axis_config.model_dump(mode="json"))
        if chart_data.drilldown_config is not None:
            chart.drilldown_config = json.dumps(chart_data.drilldown_config.model_dump(mode="json"))

        # Update refresh settings
        if chart_data.auto_refresh is not None:
            chart.auto_refresh = chart_data.auto_refresh
        if chart_data.refresh_interval is not None:
            chart.refresh_interval = chart_data.refresh_interval
        if chart_data.cache_duration is not None:
            chart.cache_duration = chart_data.cache_duration

        await db.commit()
        await db.refresh(chart)

        return chart

    async def delete_chart(
        self,
        db: AsyncSession,
        chart_id: str,
        user_id: str,
    ) -> None:
        """Delete a chart (soft delete).

        Args:
            db: Database session
            chart_id: Chart ID to delete
            user_id: User ID making the deletion

        Raises:
            NotFoundError: If chart not found
            PermissionDeniedError: If user doesn't have edit access

        """
        # Get chart and check access
        chart = await self.get_chart_by_id(db, chart_id, user_id)

        # Check edit permission
        await self._check_dashboard_edit_permission(db, chart.dashboard_id, user_id)

        # Soft delete
        chart.soft_delete()
        await db.commit()

    async def duplicate_chart(
        self,
        db: AsyncSession,
        chart_id: str,
        user_id: str,
        duplicate_data: ChartDuplicate,
    ) -> Chart:
        """Duplicate a chart.

        Args:
            db: Database session
            chart_id: Chart ID to duplicate
            user_id: User ID making the duplication
            duplicate_data: Duplication configuration

        Returns:
            New duplicated chart

        Raises:
            NotFoundError: If chart not found
            PermissionDeniedError: If user doesn't have access

        """
        # Get original chart
        original = await self.get_chart_by_id(db, chart_id, user_id)

        # If target dashboard specified, check access
        target_dashboard_id = (
            str(duplicate_data.dashboard_id) if duplicate_data.dashboard_id else original.dashboard_id
        )
        await self._get_dashboard_with_access(db, target_dashboard_id, user_id)

        # Determine position in target dashboard
        max_position_query = select(func.max(Chart.position)).where(
            Chart.dashboard_id == target_dashboard_id,
            Chart.deleted_at.is_(None),
        )
        result = await db.execute(max_position_query)
        max_position = result.scalar() or 0

        # Create duplicate
        duplicate = Chart(
            dashboard_id=target_dashboard_id,
            table_id=original.table_id,
            created_by_id=user_id,
            name=duplicate_data.name,
            description=original.description,
            chart_type=original.chart_type,
            position=max_position + 1,
            width=original.width,
            height=original.height,
            data_config=original.data_config if duplicate_data.include_data_config else "{}",
            filters=original.filters if duplicate_data.include_filters else "[]",
            sorts=original.sorts if duplicate_data.include_filters else "[]",
            visual_config=original.visual_config if duplicate_data.include_visual_config else "{}",
            axis_config=original.axis_config if duplicate_data.include_visual_config else "{}",
            drilldown_config=original.drilldown_config if duplicate_data.include_drilldown else "{}",
            color_scheme=original.color_scheme if duplicate_data.include_visual_config else None,
            auto_refresh=original.auto_refresh,
            refresh_interval=original.refresh_interval,
            cache_duration=original.cache_duration,
        )
        db.add(duplicate)
        await db.commit()
        await db.refresh(duplicate)

        return duplicate

    async def get_chart_data(
        self,
        db: AsyncSession,
        chart_id: str,
        user_id: str,
        data_request: Optional[ChartDataRequest] = None,
    ) -> ChartDataResponse:
        """Generate chart data from table records.

        Args:
            db: Database session
            chart_id: Chart ID to generate data for
            user_id: User ID requesting data
            data_request: Optional overrides for filters/date range

        Returns:
            Chart data response with computed data points

        Raises:
            NotFoundError: If chart not found
            PermissionDeniedError: If user doesn't have access
            ValidationError: If chart configuration is invalid

        """
        # Get chart and check access
        chart = await self.get_chart_by_id(db, chart_id, user_id)

        # Check cache
        if not (data_request and data_request.bypass_cache) and not chart.needs_refresh:
            # TODO: Implement Redis cache lookup
            pass

        # Parse chart configuration
        data_config = chart.get_data_config_dict()
        filters = chart.get_filters_list()
        sorts = chart.get_sorts_list()

        # Apply request overrides
        if data_request:
            if data_request.filters:
                filters = [f.model_dump(mode="json") for f in data_request.filters]
            if data_request.date_range:
                data_config["date_range"] = data_request.date_range.value
            if data_request.custom_date_start:
                data_config["custom_date_start"] = data_request.custom_date_start.isoformat()
            if data_request.custom_date_end:
                data_config["custom_date_end"] = data_request.custom_date_end.isoformat()
            if data_request.limit:
                data_config["limit"] = data_request.limit

        # Generate chart data based on configuration
        chart_data = await self._compute_chart_data(
            db=db,
            user_id=user_id,
            table_id=chart.table_id,
            chart_type=chart.chart_type,
            data_config=data_config,
            filters=filters,
            sorts=sorts,
        )

        # Update last refreshed timestamp
        chart.update_last_refreshed()
        await db.commit()

        # Build response
        response = ChartDataResponse(
            chart_id=UUID(chart_id),
            chart_type=ChartType(chart.chart_type),
            data=chart_data.get("data", []),
            series=chart_data.get("series"),
            labels=chart_data.get("labels", []),
            metadata={
                "total_records": chart_data.get("total_records", 0),
                "aggregation_type": data_config.get("aggregation", "count"),
                "chart_type": chart.chart_type,
            },
            generated_at=utc_now(),
            cached=False,
        )

        # TODO: Cache response in Redis
        return response

    async def _compute_chart_data(
        self,
        db: AsyncSession,
        user_id: str,
        table_id: str,
        chart_type: str,
        data_config: dict[str, Any],
        filters: list[dict[str, Any]],
        sorts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compute chart data based on configuration.

        Args:
            db: Database session
            user_id: User ID
            table_id: Table to query
            chart_type: Type of chart
            data_config: Data configuration
            filters: Filter conditions
            sorts: Sort rules

        Returns:
            Dictionary with chart data points and metadata

        """
        x_field_id = data_config.get("x_field_id")
        y_field_id = data_config.get("y_field_id")
        group_by_field_id = data_config.get("group_by_field_id")
        aggregation = data_config.get("aggregation", "count")
        limit = data_config.get("limit", 100)

        # Handle series configuration for multi-series charts
        series_config = data_config.get("series")

        if series_config:
            # Multi-series chart
            series_list = []
            for series in series_config:
                series_data = await self.analytics_service.compute_chart_data(
                    db=db,
                    user_id=user_id,
                    table_id=table_id,
                    x_field_id=str(x_field_id) if x_field_id else None,
                    y_field_id=str(series.get("y_field_id")),
                    group_by_field_id=str(group_by_field_id) if group_by_field_id else None,
                    aggregation_type=series.get("aggregation", aggregation),
                    filters=filters,
                    limit=limit,
                )
                series_list.append(
                    ChartSeries(
                        name=series.get("name", f"Series {len(series_list) + 1}"),
                        data=[
                            ChartDataPoint(label=point["label"], value=point["value"])
                            for point in series_data.get("data", [])
                        ],
                        color=series.get("color"),
                    )
                )

            # Extract all unique labels
            all_labels = []
            for series in series_list:
                all_labels.extend([dp.label for dp in series.data])
            unique_labels = list(dict.fromkeys(all_labels))  # Preserve order

            return {
                "data": [],
                "series": series_list,
                "labels": unique_labels,
                "total_records": sum(len(s.data) for s in series_list),
            }
        else:
            # Single series chart
            result = await self.analytics_service.compute_chart_data(
                db=db,
                user_id=user_id,
                table_id=table_id,
                x_field_id=str(x_field_id) if x_field_id else None,
                y_field_id=str(y_field_id) if y_field_id else None,
                group_by_field_id=str(group_by_field_id) if group_by_field_id else None,
                aggregation_type=aggregation,
                filters=filters,
                limit=limit,
            )

            data_points = [
                ChartDataPoint(label=point["label"], value=point["value"])
                for point in result.get("data", [])
            ]

            return {
                "data": data_points,
                "series": None,
                "labels": [dp.label for dp in data_points],
                "total_records": result.get("total_records", 0),
            }

    # =============================================================================
    # Helper Methods
    # =============================================================================

    async def _get_dashboard_with_access(
        self,
        db: AsyncSession,
        dashboard_id: str,
        user_id: str,
    ) -> Dashboard:
        """Get dashboard and verify user has access.

        Args:
            db: Database session
            dashboard_id: Dashboard ID
            user_id: User ID

        Returns:
            Dashboard

        Raises:
            NotFoundError: If dashboard not found
            PermissionDeniedError: If user doesn't have access

        """
        dashboard = await db.get(Dashboard, dashboard_id)
        if not dashboard or dashboard.is_deleted:
            raise NotFoundError("Dashboard not found")

        # Check if user has access to dashboard's base
        base = await self._get_base_with_access(db, dashboard.base_id, user_id)

        # Check if dashboard is personal and belongs to another user
        if dashboard.is_personal and dashboard.created_by_id != user_id:
            raise PermissionDeniedError("This is a personal dashboard")

        return dashboard

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
        await self._check_workspace_access(db, table.base.workspace_id, user_id)

        return table

    async def _get_base_with_access(
        self,
        db: AsyncSession,
        base_id: str,
        user_id: str,
    ) -> Base:
        """Get base and verify user has access.

        Args:
            db: Database session
            base_id: Base ID
            user_id: User ID

        Returns:
            Base

        Raises:
            NotFoundError: If base not found
            PermissionDeniedError: If user doesn't have access

        """
        base = await db.get(Base, base_id)
        if not base or base.is_deleted:
            raise NotFoundError("Base not found")

        # Check workspace access
        await self._check_workspace_access(db, base.workspace_id, user_id)

        return base

    async def _check_workspace_access(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
    ) -> WorkspaceMember:
        """Check if user has access to workspace.

        Args:
            db: Database session
            workspace_id: Workspace ID
            user_id: User ID

        Returns:
            WorkspaceMember

        Raises:
            PermissionDeniedError: If user doesn't have access

        """
        query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.deleted_at.is_(None),
        )
        result = await db.execute(query)
        member = result.scalar_one_or_none()

        if not member:
            raise PermissionDeniedError("You don't have access to this workspace")

        return member

    async def _check_dashboard_edit_permission(
        self,
        db: AsyncSession,
        dashboard_id: str,
        user_id: str,
    ) -> None:
        """Check if user has edit permission for dashboard.

        Args:
            db: Database session
            dashboard_id: Dashboard ID
            user_id: User ID

        Raises:
            PermissionDeniedError: If user doesn't have edit access

        """
        dashboard = await db.get(Dashboard, dashboard_id)
        if not dashboard or dashboard.is_deleted:
            raise NotFoundError("Dashboard not found")

        # Dashboard owner can always edit
        if dashboard.created_by_id == user_id:
            return

        # Check if dashboard is locked
        if dashboard.is_locked:
            raise PermissionDeniedError("Dashboard is locked")

        # Check workspace role
        base = await db.get(Base, dashboard.base_id)
        member = await self._check_workspace_access(db, base.workspace_id, user_id)

        # Viewers cannot edit
        if member.role == WorkspaceRole.VIEWER:
            raise PermissionDeniedError("You don't have permission to edit this dashboard")
