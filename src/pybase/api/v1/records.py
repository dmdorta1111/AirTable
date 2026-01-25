"""
Record endpoints.

Handles record CRUD operations.
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.models.record import Record
from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from pybase.schemas.record import (
    RecordCreate,
    RecordListResponse,
    RecordResponse,
    RecordUpdate,
)
from pybase.services.record import RecordService

router = APIRouter()

# =============================================================================
# Dependencies
# =============================================================================


def get_record_service() -> RecordService:
    """Get record service instance."""
    return RecordService()


def record_to_response(record: Record, table_id: str) -> RecordResponse:
    """Convert Record model to RecordResponse schema."""
    from uuid import UUID

    # Parse JSON data
    try:
        data = json.loads(record.data) if isinstance(record.data, str) else record.data
    except (json.JSONDecodeError, TypeError):
        data = {}

    return RecordResponse(
        id=str(record.id),
        table_id=table_id if table_id else str(record.table_id),
        data=data,
        row_height=record.row_height or 32,
        created_by_id=str(record.created_by_id) if record.created_by_id else None,
        last_modified_by_id=str(record.last_modified_by_id) if record.last_modified_by_id else None,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


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
    # Validate table_id UUID format
    try:
        from uuid import UUID

        UUID(record_data.table_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table ID format",
        )

    try:
        record = await record_service.create_record(
            db=db,
            user_id=str(current_user.id),
            record_data=record_data,
        )
    except ValidationError as e:
        # Convert ValidationError to HTTP 400 response
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e
    except ConflictError as e:
        # Convert ConflictError to HTTP 409 response
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except NotFoundError as e:
        # Convert NotFoundError to HTTP 404 response
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except PermissionDeniedError as e:
        # Convert PermissionDeniedError to HTTP 403 response
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e

    return record_to_response(record, record_data.table_id)


@router.get("", response_model=RecordListResponse)
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
) -> RecordListResponse:
    """
    List records accessible to current user.

    Returns paginated list of records.
    Can filter by table_id.
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

    return RecordListResponse(
        items=[record_to_response(r, str(r.table_id)) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{record_id}", response_model=RecordResponse)
async def get_record(
    record_id: str,
    db: DbSession,
    current_user: CurrentUser,
    record_service: Annotated[RecordService, Depends(get_record_service)],
) -> RecordResponse:
    """
    Get a record by ID.

    Returns record details.
    Requires user to have access to record's table workspace.
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

    return record_to_response(record, str(record.table_id))


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

    # Validate that at least one field is being updated
    if record_data.data is None and record_data.row_height is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field (data or row_height) must be provided for update",
        )

    # Validate that data is not empty if provided
    if record_data.data is not None and len(record_data.data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data field cannot be empty. Provide field values to update",
        )

    try:
        updated_record = await record_service.update_record(
            db=db,
            record_id=record_id,  # Keep as string
            user_id=str(current_user.id),
            record_data=record_data,
        )
    except ValidationError as e:
        # Convert ValidationError to HTTP 400 response
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e
    except ConflictError as e:
        # Convert ConflictError to HTTP 409 response
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    except NotFoundError as e:
        # Convert NotFoundError to HTTP 404 response
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except PermissionDeniedError as e:
        # Convert PermissionDeniedError to HTTP 403 response
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e

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
