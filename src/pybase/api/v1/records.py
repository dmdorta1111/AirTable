"""
Record endpoints.

Handles record CRUD operations.
"""

import json
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.models.record import Record
from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.schemas.record import (
    RecordCreate,
    RecordListResponse,
    RecordResponse,
    RecordUpdate,
)
from pybase.schemas.cursor import CursorPage, CursorResponse
from pybase.services.record import RecordService

router = APIRouter()

# =============================================================================
# Dependencies
# =============================================================================


def get_record_service() -> RecordService:
    """Get record service instance."""
    return RecordService()


def record_to_response(record: Record, table_id: str, fields: Optional[list[str]] = None) -> RecordResponse | dict[str, Any]:
    """Convert Record model to RecordResponse schema.

    Args:
        record: Record model instance
        table_id: Table ID string
        fields: Optional list of field names to include in response.
                If None or empty, returns all fields. If provided, returns only specified fields.

    Returns:
        RecordResponse if fields is None or empty, otherwise dict with only requested fields.
    """
    from uuid import UUID

    # Parse JSON data
    try:
        data = json.loads(record.data) if isinstance(record.data, str) else record.data
    except (json.JSONDecodeError, TypeError):
        data = {}

    # Build full response
    full_response = {
        "id": str(record.id),
        "table_id": table_id if table_id else str(record.table_id),
        "data": data,
        "row_height": record.row_height or 32,
        "created_by_id": str(record.created_by_id) if record.created_by_id else None,
        "last_modified_by_id": str(record.last_modified_by_id) if record.last_modified_by_id else None,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }

    # Return full response if no fields specified or empty list
    if fields is None or len(fields) == 0:
        return RecordResponse(**full_response)

    # Filter to only requested fields
    filtered_response = {}
    for field in fields:
        if field in full_response:
            filtered_response[field] = full_response[field]

    return filtered_response


# =============================================================================
# Record CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=RecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_record(
    record_data: RecordCreate,
    db: DbSession,
    current_user: CurrentUser,
    record_service: Annotated[RecordService, Depends(get_record_service)],
) -> RecordResponse:
    """
    Create a new record in a table.

    Creates a new record in specified table.
    User must have access to table's workspace.
    """
    record = await record_service.create_record(
        db=db,
        user_id=str(current_user.id),
        record_data=record_data,
    )

    return record_to_response(record, record_data.table_id)


@router.get("")
async def list_records(
    db: DbSession,
    current_user: CurrentUser,
    record_service: Annotated[RecordService, Depends(get_record_service)],
    table_id: Annotated[
        str | None,
        Query(
            description="Table ID to filter records by (optional)",
        ),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Number of items per page (max 100)",
        ),
    ] = 20,
    fields: Annotated[
        str | None,
        Query(
            description="Comma-separated list of fields to include in response (e.g., 'id,created_at,data')",
        ),
    ] = None,
):
    """
    List records accessible to current user.

    Returns paginated list of records.
    Can filter by table_id.
    Can optionally specify which fields to include in response using the fields parameter.
    """
    from uuid import UUID

    table_uuid: UUID | None = None
    if table_id:
        try:
            table_uuid = UUID(table_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid table ID format",
            )

    records, total = await record_service.list_records(
        db=db,
        table_id=table_uuid,
        user_id=str(current_user.id),
        page=page,
        page_size=page_size,
    )

    # Parse fields parameter if provided
    fields_list = None
    if fields:
        fields_list = [f.strip() for f in fields.split(",") if f.strip()]

    # Convert records to response
    items = [record_to_response(r, str(r.table_id), fields_list) for r in records]

    # Return RecordListResponse if no fields specified, otherwise return dict
    if fields_list is None:
        return RecordListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    else:
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@router.get("/cursor")
async def list_records_cursor(
    db: DbSession,
    current_user: CurrentUser,
    record_service: Annotated[RecordService, Depends(get_record_service)],
    table_id: Annotated[
        str | None,
        Query(
            description="Table ID to filter records by (optional)",
        ),
    ] = None,
    cursor: Annotated[
        str | None,
        Query(
            description="Cursor for pagination (encoded pagination token)",
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=1000,
            description="Number of items per page (max 1000)",
        ),
    ] = 50,
    fields: Annotated[
        str | None,
        Query(
            description="Comma-separated list of fields to include in response (e.g., 'id,created_at,data')",
        ),
    ] = None,
):
    """
    List records using cursor-based pagination.

    Returns paginated list of records using efficient cursor pagination.
    More efficient than offset-based pagination for large datasets.
    Can filter by table_id.
    Can optionally specify which fields to include in response using the fields parameter.
    """
    from uuid import UUID

    table_uuid: UUID | None = None
    if table_id:
        try:
            table_uuid = UUID(table_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid table ID format",
            )

    result = await record_service.list_records_cursor(
        db=db,
        table_id=table_uuid,
        user_id=str(current_user.id),
        cursor=cursor,
        page_size=limit,
    )

    # Parse fields parameter if provided
    fields_list = None
    if fields:
        fields_list = [f.strip() for f in fields.split(",") if f.strip()]

    # Convert records to response
    items = [record_to_response(r, str(r.table_id), fields_list) for r in result["records"]]

    return CursorPage[RecordResponse](
        items=items,
        meta=CursorResponse(
            next_cursor=result.get("next_cursor"),
            prev_cursor=None,  # Previous cursor not implemented yet
            has_next=result.get("has_more", False),
            has_prev=False,  # Previous page not supported yet
            limit=limit,
            total_count=None,  # Total count not provided for performance
        ),
    )


@router.get("/{record_id}")
async def get_record(
    record_id: str,
    db: DbSession,
    current_user: CurrentUser,
    record_service: Annotated[RecordService, Depends(get_record_service)],
    fields: Annotated[
        str | None,
        Query(
            description="Comma-separated list of fields to include in response (e.g., 'id,created_at,data')",
        ),
    ] = None,
):
    """
    Get a record by ID.

    Returns record details.
    Requires user to have access to record's table workspace.
    Can optionally specify which fields to include in response using the fields parameter.
    """
    # Validate UUID format but keep as string
    try:
        from uuid import UUID

        UUID(record_id)  # Just validate format
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid record ID format",
        )

    record = await record_service.get_record_by_id(
        db=db,
        record_id=record_id,  # Keep as string
        user_id=str(current_user.id),
    )

    # Parse fields parameter if provided
    fields_list = None
    if fields:
        fields_list = [f.strip() for f in fields.split(",") if f.strip()]

    return record_to_response(record, str(record.table_id), fields_list)


@router.patch("/{record_id}", response_model=RecordResponse)
async def update_record(
    record_id: str,
    record_data: RecordUpdate,
    db: DbSession,
    current_user: CurrentUser,
    record_service: Annotated[RecordService, Depends(get_record_service)],
) -> RecordResponse:
    """
    Update a record.

    Updates record data and/or display settings.
    Requires workspace owner, admin, or editor role.
    """
    # Validate UUID format but keep as string
    try:
        from uuid import UUID

        UUID(record_id)  # Just validate format
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid record ID format",
        )

    updated_record = await record_service.update_record(
        db=db,
        record_id=record_id,  # Keep as string
        user_id=str(current_user.id),
        record_data=record_data,
    )

    return record_to_response(updated_record, str(updated_record.table_id))


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: str,
    db: DbSession,
    current_user: CurrentUser,
    record_service: Annotated[RecordService, Depends(get_record_service)],
) -> None:
    """
    Delete a record.

    Soft deletes record (marks as deleted).
    Requires workspace owner, admin, or editor role.
    """
    # Validate UUID format but keep as string
    try:
        from uuid import UUID

        UUID(record_id)  # Just validate format
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid record ID format",
        )

    await record_service.delete_record(
        db=db,
        record_id=record_id,  # Keep as string
        user_id=str(current_user.id),
    )


# =============================================================================
