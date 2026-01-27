"""
Record endpoints.

Handles record CRUD operations.
"""

import json
import logging
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from pybase.api.deps import CurrentUser, DbSession
from pybase.models.record import Record
from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from pybase.realtime import get_connection_manager
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
from pybase.schemas.cursor import CursorPage, CursorResponse
from pybase.schemas.realtime import EventType, RecordChangeEvent, RecordBatchChangeEvent
from pybase.services.record import RecordService
from pybase.services.export_service import ExportService

router = APIRouter()
logger = logging.getLogger(__name__)

# =============================================================================
# Dependencies
# =============================================================================


def get_record_service() -> RecordService:
    """Get record service instance."""
    return RecordService()


def get_export_service() -> ExportService:
    """Get export service instance."""
    return ExportService()


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

    # Emit WebSocket event for record creation
    await _emit_record_event(
        event_type=EventType.RECORD_CREATED,
        table_id=record_data.table_id,
        record_id=str(record.id),
        record=record,
        user_id=str(current_user.id),
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

    # Emit WebSocket event for record update
    await _emit_record_event(
        event_type=EventType.RECORD_UPDATED,
        table_id=str(updated_record.table_id),
        record_id=record_id,
        record=updated_record,
        user_id=str(current_user.id),
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

    # Get table_id before deleting for WebSocket event
    record = await record_service.get_record_by_id(
        db=db,
        record_id=record_id,
        user_id=str(current_user.id),
    )
    table_id = str(record.table_id)

    await record_service.delete_record(
        db=db,
        record_id=record_id,  # Keep as string
        user_id=str(current_user.id),
    )

    # Emit WebSocket event for record deletion
    await _emit_record_event(
        event_type=EventType.RECORD_DELETED,
        table_id=table_id,
        record_id=record_id,
        record=None,  # No record data for deleted events
        user_id=str(current_user.id),
    )


@router.post("/export", status_code=status.HTTP_202_ACCEPTED)
async def export_records(
    db: DbSession,
    current_user: CurrentUser,
    export_service: Annotated[ExportService, Depends(get_export_service)],
    table_id: Annotated[
        str,
        Query(
            description="Table ID to export records from",
        ),
    ],
    format: Annotated[
        str,
        Query(
            description="Export format (csv or json)",
        ),
    ] = "csv",
    batch_size: Annotated[
        int,
        Query(
            ge=100,
            le=10000,
            description="Number of records per batch (100-10000)",
        ),
    ] = 1000,
):
    """
    Export records from a table.

    Streams export data for large datasets efficiently.
    Supports CSV and JSON formats.
    Returns 202 to indicate async processing has started.
    """
    from uuid import UUID

    # Validate table_id
    try:
        table_uuid = UUID(table_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table ID format",
        )

    # Validate format
    format = format.lower()
    if format not in ["csv", "json"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format. Must be 'csv' or 'json'",
        )

    # Create streaming generator
    async def generate_export():
        async for chunk in export_service.export_records(
            db=db,
            table_id=table_uuid,
            user_id=str(current_user.id),
            format=format,
            batch_size=batch_size,
        ):
            yield chunk

    # Determine media type
    media_type = "text/csv" if format == "csv" else "application/json"
    filename = f"export_{table_id}.{format}"

    # Return streaming response
    return StreamingResponse(
        generate_export(),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
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

        # Emit WebSocket event for batch record creation
        await _emit_batch_record_event(
            event_type=EventType.RECORD_BATCH_CREATED,
            table_id=table_id_str,
            record_ids=[str(record.id) for record in created_records],
            user_id=str(current_user.id),
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

        # Emit WebSocket event for batch record update
        await _emit_batch_record_event(
            event_type=EventType.RECORD_BATCH_UPDATED,
            table_id=table_id,
            record_ids=[str(record.id) for record in updated_records],
            user_id=str(current_user.id),
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

        # Emit WebSocket event for batch record deletion
        await _emit_batch_record_event(
            event_type=EventType.RECORD_BATCH_DELETED,
            table_id=table_id,
            record_ids=[str(record.id) for record in deleted_records],
            user_id=str(current_user.id),
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

# =============================================================================
# WebSocket Event Emission Helpers
# =============================================================================


async def _emit_record_event(
    event_type: EventType,
    table_id: str,
    record_id: str,
    record: Optional[Record],
    user_id: str,
) -> None:
    """Emit a WebSocket event for record changes.

    Args:
        event_type: Type of event (RECORD_CREATED, RECORD_UPDATED, RECORD_DELETED)
        table_id: Table ID
        record_id: Record ID
        record: Record model (None for deleted events)
        user_id: User ID who made the change

    """
    try:
        manager = get_connection_manager()

        # Prepare record data (exclude for deleted events)
        record_data = None
        if record is not None:
            try:
                data = json.loads(record.data) if isinstance(record.data, str) else record.data
            except (json.JSONDecodeError, TypeError):
                data = {}

            record_data = {
                "id": str(record.id),
                "table_id": str(record.table_id),
                "data": data,
                "row_height": record.row_height or 32,
                "created_by_id": str(record.created_by_id) if record.created_by_id else None,
                "last_modified_by_id": str(record.last_modified_by_id) if record.last_modified_by_id else None,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            }

        # Create event
        event = RecordChangeEvent(
            event=event_type,
            table_id=table_id,
            record_id=record_id,
            data=record_data,
            changed_by=user_id,
        )

        # Broadcast to table channel (all users viewing the table)
        table_channel = f"table:{table_id}"
        await manager.broadcast_to_channel(table_channel, event)

        logger.debug(
            f"Emitted {event_type.value} event for record {record_id} to channel: {table_channel}"
        )

    except Exception as e:
        # Don't fail the operation if WebSocket broadcast fails
        logger.error(f"Failed to emit record event: {e}", exc_info=True)


async def _emit_batch_record_event(
    event_type: EventType,
    table_id: str,
    record_ids: list[str],
    user_id: str,
) -> None:
    """Emit a WebSocket event for batch record changes.

    Args:
        event_type: Type of event (RECORD_BATCH_CREATED, RECORD_BATCH_UPDATED, RECORD_BATCH_DELETED)
        table_id: Table ID
        record_ids: List of record IDs affected
        user_id: User ID who made the change

    """
    try:
        manager = get_connection_manager()

        # Create event
        event = RecordBatchChangeEvent(
            event=event_type,
            table_id=table_id,
            record_ids=record_ids,
            count=len(record_ids),
            changed_by=user_id,
        )

        # Broadcast to table channel (all users viewing the table)
        table_channel = f"table:{table_id}"
        await manager.broadcast_to_channel(table_channel, event)

        logger.debug(
            f"Emitted {event_type.value} event for {len(record_ids)} records to channel: {table_channel}"
        )

    except Exception as e:
        # Don't fail the operation if WebSocket broadcast fails
        logger.error(f"Failed to emit batch record event: {e}", exc_info=True)
