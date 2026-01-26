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
)
from pybase.schemas.batch import (
    BatchOperationResponse,
    BatchRecordCreate,
    BatchRecordDelete,
    BatchRecordUpdate,
    RecordOperationResult,
    RecordUpdateItem,
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
    record = await record_service.create_record(
        db=db,
        user_id=str(current_user.id),
        record_data=record_data,
    )

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
# Batch Operations Endpoints
# =============================================================================


@router.post(
    "/batch/create",
    response_model=BatchOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Create multiple records in batch",
    description="Create multiple records in a single request. All records must belong to the same table. Max 100 records per batch.",
)
async def batch_create_records(
    batch_data: BatchRecordCreate,
    db: DbSession,
    current_user: CurrentUser,
    record_service: Annotated[RecordService, Depends(get_record_service)],
) -> BatchOperationResponse:
    """
    Create multiple records in a single batch operation.

    All records must belong to the same table.
    Either all records are created successfully, or none are (transactional).
    """
    from uuid import UUID

    # Validate all records have the same table_id
    if not batch_data.records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch must contain at least 1 record",
        )

    table_id_str = batch_data.records[0].table_id
    for idx, record in enumerate(batch_data.records):
        if record.table_id != table_id_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"All records must belong to the same table. Record at index {idx} has different table_id",
            )

    # Validate table_id format
    try:
        table_uuid = UUID(table_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table ID format",
        )

    # Try to create all records in a single transaction
    try:
        created_records = await record_service.batch_create_records(
            db=db,
            user_id=str(current_user.id),
            table_id=table_uuid,
            records_data=batch_data.records,
        )

        # All successful - build response
        results = [
            RecordOperationResult(
                record_id=str(record.id),
                success=True,
                record=record_to_response(record, table_id_str),
                error=None,
                error_code=None,
            )
            for record in created_records
        ]

        return BatchOperationResponse(
            total=len(batch_data.records),
            successful=len(created_records),
            failed=0,
            results=results,
        )

    except NotFoundError as e:
        # Table not found - all records fail
        results = [
            RecordOperationResult(
                record_id=None,
                success=False,
                record=None,
                error=str(e),
                error_code="NOT_FOUND",
            )
            for _ in batch_data.records
        ]
        return BatchOperationResponse(
            total=len(batch_data.records),
            successful=0,
            failed=len(batch_data.records),
            results=results,
        )

    except PermissionDeniedError as e:
        # Permission denied - all records fail
        results = [
            RecordOperationResult(
                record_id=None,
                success=False,
                record=None,
                error=str(e),
                error_code="PERMISSION_DENIED",
            )
            for _ in batch_data.records
        ]
        return BatchOperationResponse(
            total=len(batch_data.records),
            successful=0,
            failed=len(batch_data.records),
            results=results,
        )

    except ConflictError as e:
        # Validation failed - all records fail
        results = [
            RecordOperationResult(
                record_id=None,
                success=False,
                record=None,
                error=str(e),
                error_code="CONFLICT",
            )
            for _ in batch_data.records
        ]
        return BatchOperationResponse(
            total=len(batch_data.records),
            successful=0,
            failed=len(batch_data.records),
            results=results,
        )


@router.patch(
    "/batch/update",
    response_model=BatchOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update multiple records in batch",
    description="Update multiple records in a single request. All records must belong to the same table. Max 100 records per batch.",
)
async def batch_update_records(
    batch_data: BatchRecordUpdate,
    db: DbSession,
    current_user: CurrentUser,
    record_service: Annotated[RecordService, Depends(get_record_service)],
    table_id: Annotated[
        str,
        Query(description="Table ID that all records belong to"),
    ],
) -> BatchOperationResponse:
    """
    Update multiple records in a single batch operation.

    All records must belong to the specified table.
    Either all records are updated successfully, or none are (transactional).
    Requires workspace owner, admin, or editor role.
    """
    from uuid import UUID

    # Validate table_id format
    try:
        table_uuid = UUID(table_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table ID format",
        )

    # Convert batch data to service format
    updates: list[tuple[str, RecordUpdate]] = []
    for item in batch_data.records:
        update_data = RecordUpdate(
            data=item.data,
            row_height=item.row_height,
        )
        updates.append((item.record_id, update_data))

    # Try to update all records in a single transaction
    try:
        updated_records = await record_service.batch_update_records(
            db=db,
            user_id=str(current_user.id),
            table_id=table_uuid,
            updates=updates,
        )

        # All successful - build response
        results = [
            RecordOperationResult(
                record_id=str(record.id),
                success=True,
                record=record_to_response(record, table_id),
                error=None,
                error_code=None,
            )
            for record in updated_records
        ]

        return BatchOperationResponse(
            total=len(batch_data.records),
            successful=len(updated_records),
            failed=0,
            results=results,
        )

    except NotFoundError as e:
        # Table or record not found - all records fail
        results = [
            RecordOperationResult(
                record_id=item.record_id,
                success=False,
                record=None,
                error=str(e),
                error_code="NOT_FOUND",
            )
            for item in batch_data.records
        ]
        return BatchOperationResponse(
            total=len(batch_data.records),
            successful=0,
            failed=len(batch_data.records),
            results=results,
        )

    except PermissionDeniedError as e:
        # Permission denied - all records fail
        results = [
            RecordOperationResult(
                record_id=item.record_id,
                success=False,
                record=None,
                error=str(e),
                error_code="PERMISSION_DENIED",
            )
            for item in batch_data.records
        ]
        return BatchOperationResponse(
            total=len(batch_data.records),
            successful=0,
            failed=len(batch_data.records),
            results=results,
        )

    except ConflictError as e:
        # Validation failed - all records fail
        results = [
            RecordOperationResult(
                record_id=item.record_id,
                success=False,
                record=None,
                error=str(e),
                error_code="CONFLICT",
            )
            for item in batch_data.records
        ]
        return BatchOperationResponse(
            total=len(batch_data.records),
            successful=0,
            failed=len(batch_data.records),
            results=results,
        )


@router.delete(
    "/batch/delete",
    response_model=BatchOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete multiple records in batch",
    description="Delete multiple records in a single request. All records must belong to the same table. Max 100 records per batch.",
)
async def batch_delete_records(
    batch_data: BatchRecordDelete,
    db: DbSession,
    current_user: CurrentUser,
    record_service: Annotated[RecordService, Depends(get_record_service)],
    table_id: Annotated[
        str,
        Query(description="Table ID that all records belong to"),
    ],
) -> BatchOperationResponse:
    """
    Delete multiple records in a single batch operation.

    All records must belong to the specified table.
    Either all records are deleted successfully, or none are (transactional).
    Requires workspace owner, admin, or editor role.
    """
    from uuid import UUID

    # Validate table_id format
    try:
        table_uuid = UUID(table_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table ID format",
        )

    # Try to delete all records in a single transaction
    try:
        deleted_records = await record_service.batch_delete_records(
            db=db,
            user_id=str(current_user.id),
            table_id=table_uuid,
            record_ids=batch_data.record_ids,
        )

        # All successful - build response
        results = [
            RecordOperationResult(
                record_id=str(record.id),
                success=True,
                record=record_to_response(record, table_id),
                error=None,
                error_code=None,
            )
            for record in deleted_records
        ]

        return BatchOperationResponse(
            total=len(batch_data.record_ids),
            successful=len(deleted_records),
            failed=0,
            results=results,
        )

    except NotFoundError as e:
        # Table or record not found - all records fail
        results = [
            RecordOperationResult(
                record_id=record_id,
                success=False,
                record=None,
                error=str(e),
                error_code="NOT_FOUND",
            )
            for record_id in batch_data.record_ids
        ]
        return BatchOperationResponse(
            total=len(batch_data.record_ids),
            successful=0,
            failed=len(batch_data.record_ids),
            results=results,
        )

    except PermissionDeniedError as e:
        # Permission denied - all records fail
        results = [
            RecordOperationResult(
                record_id=record_id,
                success=False,
                record=None,
                error=str(e),
                error_code="PERMISSION_DENIED",
            )
            for record_id in batch_data.record_ids
        ]
        return BatchOperationResponse(
            total=len(batch_data.record_ids),
            successful=0,
            failed=len(batch_data.record_ids),
            results=results,
        )

    except ConflictError as e:
        # Validation failed - all records fail
        results = [
            RecordOperationResult(
                record_id=record_id,
                success=False,
                record=None,
                error=str(e),
                error_code="CONFLICT",
            )
            for record_id in batch_data.record_ids
        ]
        return BatchOperationResponse(
            total=len(batch_data.record_ids),
            successful=0,
            failed=len(batch_data.record_ids),
            results=results,
        )


# =============================================================================
