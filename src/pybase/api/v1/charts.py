"""
Chart endpoints.

Handles chart CRUD operations and chart data generation.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.schemas.chart import (
    ChartCreate,
    ChartDataRequest,
    ChartDataResponse,
    ChartDuplicate,
    ChartListResponse,
    ChartResponse,
    ChartType,
    ChartUpdate,
    PivotTableRequest,
    PivotTableResponse,
)
from pybase.services.chart import ChartService

router = APIRouter()


# =============================================================================
# Dependencies
# =============================================================================


def get_chart_service() -> ChartService:
    """Get chart service instance."""
    return ChartService()


def _chart_to_response(chart: Any) -> ChartResponse:
    """Convert Chart model to ChartResponse schema."""
    return ChartResponse(
        id=UUID(chart.id),
        dashboard_id=UUID(chart.dashboard_id),
        table_id=UUID(chart.table_id),
        created_by_id=UUID(chart.created_by_id) if chart.created_by_id else None,
        name=chart.name,
        description=chart.description,
        chart_type=ChartType(chart.chart_type),
        position=chart.position,
        width=chart.width,
        height=chart.height,
        data_config=chart.get_data_config_dict() if hasattr(chart, "get_data_config_dict") else {},
        filters=chart.get_filters_list() if hasattr(chart, "get_filters_list") else [],
        sorts=chart.get_sorts_list() if hasattr(chart, "get_sorts_list") else [],
        visual_config=chart.get_visual_config_dict() if hasattr(chart, "get_visual_config_dict") else None,
        axis_config=chart.get_axis_config_dict() if hasattr(chart, "get_axis_config_dict") else None,
        drilldown_config=chart.get_drilldown_config_dict() if hasattr(chart, "get_drilldown_config_dict") else None,
        color_scheme=chart.color_scheme,
        auto_refresh=chart.auto_refresh,
        refresh_interval=chart.refresh_interval,
        cache_duration=chart.cache_duration,
        last_refreshed_at=chart.last_refreshed_at,
        created_at=chart.created_at,
        updated_at=chart.updated_at,
        deleted_at=chart.deleted_at,
    )


# =============================================================================
# Chart CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=ChartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chart",
)
async def create_chart(
    chart_data: ChartCreate,
    db: DbSession,
    current_user: CurrentUser,
    chart_service: Annotated[ChartService, Depends(get_chart_service)],
) -> ChartResponse:
    """
    Create a new chart for a dashboard.

    Supports the following chart types:
    - **line**: Line chart for trends over time
    - **bar**: Bar chart for comparisons
    - **pie**: Pie chart for proportions
    - **area**: Area chart for cumulative trends
    - **scatter**: Scatter plot for correlations
    - **gauge**: Gauge chart for single values
    - **donut**: Donut chart (pie with center hole)
    - **heatmap**: Heatmap for matrix data
    - **histogram**: Histogram for frequency distribution
    """
    chart = await chart_service.create_chart(
        db=db,
        user_id=str(current_user.id),
        chart_data=chart_data,
    )
    return _chart_to_response(chart)


@router.get(
    "",
    response_model=ChartListResponse,
    summary="List charts",
)
async def list_charts(
    db: DbSession,
    current_user: CurrentUser,
    chart_service: Annotated[ChartService, Depends(get_chart_service)],
    dashboard_id: Annotated[
        str,
        Query(description="Dashboard ID to list charts for"),
    ],
    chart_type: Annotated[
        str | None,
        Query(description="Filter by chart type"),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Number of items per page (max 100)"),
    ] = 50,
) -> ChartListResponse:
    """
    List charts for a dashboard.

    Returns paginated list of charts ordered by position.
    """
    try:
        dashboard_uuid = UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format",
        )

    charts, total = await chart_service.list_charts(
        db=db,
        dashboard_id=dashboard_uuid,
        user_id=str(current_user.id),
        chart_type=chart_type,
        page=page,
        page_size=page_size,
    )

    return ChartListResponse(
        items=[_chart_to_response(c) for c in charts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{chart_id}",
    response_model=ChartResponse,
    summary="Get a chart",
)
async def get_chart(
    chart_id: str,
    db: DbSession,
    current_user: CurrentUser,
    chart_service: Annotated[ChartService, Depends(get_chart_service)],
) -> ChartResponse:
    """
    Get a chart by ID.

    Returns chart configuration and metadata.
    Use the /charts/{chart_id}/data endpoint to get the computed chart data.
    """
    chart = await chart_service.get_chart_by_id(
        db=db,
        chart_id=chart_id,
        user_id=str(current_user.id),
    )
    return _chart_to_response(chart)


@router.patch(
    "/{chart_id}",
    response_model=ChartResponse,
    summary="Update a chart",
)
async def update_chart(
    chart_id: str,
    chart_data: ChartUpdate,
    db: DbSession,
    current_user: CurrentUser,
    chart_service: Annotated[ChartService, Depends(get_chart_service)],
) -> ChartResponse:
    """
    Update a chart.

    Only provided fields will be updated.
    """
    chart = await chart_service.update_chart(
        db=db,
        chart_id=chart_id,
        user_id=str(current_user.id),
        chart_data=chart_data,
    )
    return _chart_to_response(chart)


@router.delete(
    "/{chart_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chart",
)
async def delete_chart(
    chart_id: str,
    db: DbSession,
    current_user: CurrentUser,
    chart_service: Annotated[ChartService, Depends(get_chart_service)],
) -> None:
    """
    Delete a chart (soft delete).

    The chart will be marked as deleted but not permanently removed.
    """
    await chart_service.delete_chart(
        db=db,
        chart_id=chart_id,
        user_id=str(current_user.id),
    )


@router.post(
    "/{chart_id}/duplicate",
    response_model=ChartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate a chart",
)
async def duplicate_chart(
    chart_id: str,
    duplicate_data: ChartDuplicate,
    db: DbSession,
    current_user: CurrentUser,
    chart_service: Annotated[ChartService, Depends(get_chart_service)],
) -> ChartResponse:
    """
    Duplicate a chart.

    Creates a copy of the chart with optional configuration overrides.
    The duplicate can be created in the same dashboard or a different one.
    """
    chart = await chart_service.duplicate_chart(
        db=db,
        chart_id=chart_id,
        user_id=str(current_user.id),
        duplicate_data=duplicate_data,
    )
    return _chart_to_response(chart)


# =============================================================================
# Chart Data Endpoints
# =============================================================================


@router.get(
    "/{chart_id}/data",
    response_model=ChartDataResponse,
    summary="Get chart data",
)
async def get_chart_data(
    chart_id: str,
    db: DbSession,
    current_user: CurrentUser,
    chart_service: Annotated[ChartService, Depends(get_chart_service)],
    bypass_cache: Annotated[
        bool,
        Query(description="Bypass cache and fetch fresh data"),
    ] = False,
) -> ChartDataResponse:
    """
    Get computed chart data for rendering.

    Returns data points, series, and metadata based on the chart's
    data configuration, filters, and aggregation settings.

    Data is cached by default based on the chart's cache_duration setting.
    Use bypass_cache=true to force fresh data computation.
    """
    # Create data request with cache bypass flag
    data_request = ChartDataRequest(bypass_cache=bypass_cache)

    chart_data = await chart_service.get_chart_data(
        db=db,
        chart_id=chart_id,
        user_id=str(current_user.id),
        data_request=data_request,
    )
    return chart_data


@router.post(
    "/{chart_id}/data",
    response_model=ChartDataResponse,
    summary="Get chart data with overrides",
)
async def get_chart_data_with_overrides(
    chart_id: str,
    data_request: ChartDataRequest,
    db: DbSession,
    current_user: CurrentUser,
    chart_service: Annotated[ChartService, Depends(get_chart_service)],
) -> ChartDataResponse:
    """
    Get chart data with temporary filter/date range overrides.

    This endpoint allows you to preview chart data with different filters
    or date ranges without modifying the chart configuration.

    Useful for:
    - Interactive filtering on dashboards
    - Date range selection controls
    - Drill-down functionality
    - Chart preview during configuration
    """
    chart_data = await chart_service.get_chart_data(
        db=db,
        chart_id=chart_id,
        user_id=str(current_user.id),
        data_request=data_request,
    )
    return chart_data


@router.post(
    "/pivot/data",
    response_model=PivotTableResponse,
    summary="Get pivot table data",
)
async def get_pivot_table_data(
    pivot_request: PivotTableRequest,
    db: DbSession,
    current_user: CurrentUser,
    chart_service: Annotated[ChartService, Depends(get_chart_service)],
) -> PivotTableResponse:
    """
    Generate pivot table data for a table.

    Creates a two-dimensional pivot table with:
    - **Rows**: Grouped by row_field values
    - **Columns**: Grouped by col_field values (if provided)
    - **Values**: Aggregated from value_field using the specified aggregation

    Supported aggregation types:
    - **count**: Count records in each cell
    - **sum**: Sum of value_field in each cell
    - **average**: Average of value_field in each cell
    - **min**: Minimum of value_field in each cell
    - **max**: Maximum of value_field in each cell

    Example request body:
    ```json
    {
        "table_id": "uuid",
        "row_field": "uuid",
        "col_field": "uuid",
        "value_field": "uuid",
        "aggregation": "sum",
        "filters": []
    }
    ```

    Returns a pivot table structure suitable for rendering in a data grid.
    """
    pivot_data = await chart_service.get_pivot_table_data(
        db=db,
        user_id=str(current_user.id),
        pivot_request=pivot_request,
    )
    return pivot_data
