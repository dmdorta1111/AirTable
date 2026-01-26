"""
Analytics endpoints.

Handles data aggregation operations including pivot tables, group by, and field statistics.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from pybase.schemas.analytics import (
    AggregateFieldRequest,
    AggregateFieldResponse,
    GroupByRequest,
    GroupByResponse,
    PivotTableRequest,
    PivotTableResponse,
    StatisticsRequest,
    StatisticsResponse,
    FieldInfo,
    GroupInfo,
)
from pybase.services.analytics import AnalyticsService

router = APIRouter()


# =============================================================================
# Dependencies
# =============================================================================


def get_analytics_service() -> AnalyticsService:
    """Get analytics service instance."""
    return AnalyticsService()


# =============================================================================
# Analytics Endpoints
# =============================================================================


@router.post(
    "/aggregate",
    response_model=AggregateFieldResponse,
    summary="Aggregate a field",
    status_code=status.HTTP_200_OK,
)
async def aggregate_field(
    request: AggregateFieldRequest,
    db: DbSession,
    current_user: CurrentUser,
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> AggregateFieldResponse:
    """
    Aggregate data for a specific field.

    Supports the following aggregation types:
    - **count**: Count of records
    - **sum**: Sum of numeric values
    - **average**: Average of numeric values
    - **min**: Minimum value
    - **max**: Maximum value
    - **median**: Median value
    - **distinct_count**: Count of distinct values

    Optionally apply filters to limit the records included in the aggregation.
    """
    try:
        # Convert filter conditions to dict format
        filters = None
        if request.filters:
            filters = [
                {
                    "field_id": str(f.field_id),
                    "operator": f.operator.value,
                    "value": f.value,
                }
                for f in request.filters
            ]

        result = await analytics_service.aggregate_field(
            db=db,
            user_id=str(current_user.id),
            table_id=str(request.table_id),
            field_id=str(request.field_id),
            aggregation_type=request.aggregation_type.value,
            filters=filters,
        )

        return AggregateFieldResponse(**result)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/group-by",
    response_model=GroupByResponse,
    summary="Group by field and aggregate",
    status_code=status.HTTP_200_OK,
)
async def group_by(
    request: GroupByRequest,
    db: DbSession,
    current_user: CurrentUser,
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> GroupByResponse:
    """
    Group records by a field and aggregate values.

    This endpoint groups records by a specified field and computes aggregate
    statistics for each group. Useful for generating summary tables and reports.

    Examples:
    - Group by status field and count records in each status
    - Group by category and sum costs for each category
    - Group by assigned user and average completion time
    """
    try:
        # Convert filter conditions to dict format
        filters = None
        if request.filters:
            filters = [
                {
                    "field_id": str(f.field_id),
                    "operator": f.operator.value,
                    "value": f.value,
                }
                for f in request.filters
            ]

        result = await analytics_service.group_by(
            db=db,
            user_id=str(current_user.id),
            table_id=str(request.table_id),
            group_field_id=str(request.group_field_id),
            value_field_id=str(request.value_field_id) if request.value_field_id else None,
            aggregation_type=request.aggregation_type.value,
            filters=filters,
            limit=request.limit,
        )

        # Convert result to response format
        return GroupByResponse(
            table_id=result["table_id"],
            group_field=FieldInfo(**result["group_field"]),
            value_field=FieldInfo(**result["value_field"]) if result.get("value_field") else None,
            aggregation_type=result["aggregation_type"],
            groups=[
                GroupInfo(
                    group_value=g["group_value"],
                    aggregated_value=g["aggregated_value"],
                    record_count=g["record_count"],
                )
                for g in result["groups"]
            ],
            total_groups=result["total_groups"],
            record_count=result["record_count"],
            timestamp=result["timestamp"],
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/pivot",
    response_model=PivotTableResponse,
    summary="Create pivot table",
    status_code=status.HTTP_200_OK,
)
async def pivot_table(
    request: PivotTableRequest,
    db: DbSession,
    current_user: CurrentUser,
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> PivotTableResponse:
    """
    Create a pivot table from records.

    Pivot tables allow you to cross-tabulate data by two dimensions:
    - **Row field**: Primary grouping dimension (required)
    - **Column field**: Secondary grouping dimension (optional, for 2D pivots)
    - **Value field**: Field to aggregate in each cell
    - **Aggregation**: How to aggregate values (count, sum, avg, etc.)

    Examples:
    - 1D pivot: Count records by status
    - 2D pivot: Sum costs by (status, priority)
    - 2D pivot: Average completion time by (assignee, month)
    """
    try:
        # Convert filter conditions to dict format
        filters = None
        if request.filters:
            filters = [
                {
                    "field_id": str(f.field_id),
                    "operator": f.operator.value,
                    "value": f.value,
                }
                for f in request.filters
            ]

        result = await analytics_service.pivot_table(
            db=db,
            user_id=str(current_user.id),
            table_id=str(request.table_id),
            row_field_id=str(request.row_field_id),
            column_field_id=str(request.column_field_id) if request.column_field_id else None,
            value_field_id=str(request.value_field_id) if request.value_field_id else None,
            aggregation_type=request.aggregation_type.value,
            filters=filters,
        )

        # Convert result to response format
        return PivotTableResponse(
            table_id=result["table_id"],
            row_field=FieldInfo(**result["row_field"]),
            column_field=FieldInfo(**result["column_field"]) if result.get("column_field") else None,
            value_field=FieldInfo(**result["value_field"]) if result.get("value_field") else None,
            aggregation_type=result["aggregation_type"],
            data=result["data"],
            record_count=result["record_count"],
            timestamp=result["timestamp"],
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/statistics",
    response_model=StatisticsResponse,
    summary="Get field statistics",
    status_code=status.HTTP_200_OK,
)
async def get_statistics(
    request: StatisticsRequest,
    db: DbSession,
    current_user: CurrentUser,
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> StatisticsResponse:
    """
    Get comprehensive statistics for a field.

    Computes multiple statistical measures in a single request:
    - Count of records
    - Sum of values (numeric fields)
    - Average, min, max (numeric fields)
    - Median and standard deviation (numeric fields)
    - Distinct value count
    - Null/empty count

    Optionally apply filters to analyze a subset of records.
    """
    try:
        # Convert filter conditions to dict format
        filters = None
        if request.filters:
            filters = [
                {
                    "field_id": str(f.field_id),
                    "operator": f.operator.value,
                    "value": f.value,
                }
                for f in request.filters
            ]

        result = await analytics_service.get_statistics(
            db=db,
            user_id=str(current_user.id),
            table_id=str(request.table_id),
            field_id=str(request.field_id),
            filters=filters,
        )

        return StatisticsResponse(**result)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
