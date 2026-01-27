"""
Record endpoints.

Handles record CRUD operations.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Annotated, Any, Optional
from uuid import UUID

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
from pybase.services.record import RecordService
from pybase.services.export_service import ExportService
from pybase.schemas.extraction import (
    ExportJobCreate,
    ExportJobResponse,
    ExportJobStatus,
)
from pybase.services.export_job_service import ExportJobService

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


def get_export_job_service() -> ExportJobService:
    """Get export job service instance."""
    return ExportJobService()


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
            description="Export format (csv, json, xlsx, or xml)",
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
    fields: Annotated[
        str | None,
        Query(
            description="Comma-separated list of field IDs to include in export (e.g., 'field_id1,field_id2')",
        ),
    ] = None,
    view_id: Annotated[
        str | None,
        Query(
            description="View ID to apply filters and sorts from (optional)",
        ),
    ] = None,
    include_attachments: Annotated[
        bool,
        Query(
            description="Include attachment files in export (as ZIP for non-JSON formats)",
        ),
    ] = False,
    flatten_linked_records: Annotated[
        bool,
        Query(
            description="Flatten linked record data into export (embed linked record values)",
        ),
    ] = False,
):
    """
    Export records from a table.

    Streams export data for large datasets efficiently.
    Supports CSV, JSON, Excel (.xlsx), and XML formats.
    Can filter by specific fields, apply view filters/sorts, include attachments,
    and flatten linked record data.
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
    valid_formats = ["csv", "json", "xlsx", "xml"]
    if format not in valid_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}",
        )

    # Parse fields parameter if provided
    field_ids = None
    if fields:
        field_ids = []
        for field_id_str in [f.strip() for f in fields.split(",") if f.strip()]:
            try:
                field_ids.append(UUID(field_id_str))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid field ID format: {field_id_str}",
                )

    # Validate view_id if provided
    view_uuid = None
    if view_id:
        try:
            view_uuid = UUID(view_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid view ID format",
            )

    # Create streaming generator
    async def generate_export():
        async for chunk in export_service.export_records(
            db=db,
            table_id=table_uuid,
            user_id=str(current_user.id),
            format=format,
            batch_size=batch_size,
            field_ids=field_ids,
            view_id=view_uuid,
            include_attachments=include_attachments,
            flatten_linked_records=flatten_linked_records,
        ):
            yield chunk

    # Determine media type and filename
    media_types = {
        "csv": "text/csv",
        "json": "application/json",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xml": "application/xml",
    }
    media_type = media_types.get(format, "application/octet-stream")
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
# Background Export Job Endpoints
# =============================================================================


@router.post(
    "/exports",
    response_model=ExportJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create background export job",
    description="Create a background export job for large datasets. Returns job ID for tracking.",
    tags=["Export Jobs"],
)
async def create_export_job(
    job_data: ExportJobCreate,
    db: DbSession,
    current_user: CurrentUser,
    export_job_service: Annotated[ExportJobService, Depends(get_export_job_service)],
) -> ExportJobResponse:
    """
    Create a background export job.

    Creates an export job that runs asynchronously in the background.
    Returns job ID that can be used to poll for status and download link.

    **Job Flow:**
    1. Job created in PENDING status
    2. Celery worker picks up job and marks as PROCESSING
    3. Worker exports data and uploads to storage
    4. Job marked COMPLETED with download link
    5. Download link expires after 7 days

    **Supported Formats:**
    - csv: Comma-separated values
    - xlsx: Excel spreadsheet
    - json: JSON array of records
    - xml: XML format with schema

    **Export Options:**
    - field_ids: List of field IDs to include (exports all if not specified)
    - filters: Dict of filter criteria for records
    - sort: List of sort specifications [{field: field_name, direction: asc|desc}]
    - include_attachments: Boolean to include attachment files as ZIP
    - flatten_linked_records: Boolean to embed linked record values

    Returns 201 with job details for status polling.
    """
    # Validate table_id
    try:
        table_uuid = UUID(str(job_data.table_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table ID format",
        )

    # Validate view_id if provided
    view_uuid = None
    if job_data.view_id:
        try:
            view_uuid = UUID(str(job_data.view_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid view ID format",
            )

    # Validate field_ids if provided
    field_ids = None
    if job_data.field_ids:
        field_ids = [str(fid) for fid in job_data.field_ids]

    # Build options dict
    options = job_data.options or {}
    if job_data.filters:
        options["filters"] = job_data.filters
    if job_data.sort:
        options["sort"] = job_data.sort
    if job_data.max_records:
        options["max_records"] = job_data.max_records
    if job_data.offset:
        options["offset"] = job_data.offset
    if job_data.callback_url:
        options["callback_url"] = job_data.callback_url

    # Create export job in database
    job_model = await export_job_service.create_job(
        db=db,
        table_id=str(table_uuid),
        export_format=job_data.format,
        user_id=str(current_user.id),
        view_id=str(view_uuid) if view_uuid else None,
        field_ids=field_ids,
        options=options,
        max_retries=3,
    )

    # Trigger Celery export task
    try:
        from celery import Celery
        import os

        # Create Celery app to send task
        celery_app = Celery(
            broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
            backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
        )

        # Send export task to Celery with job_id for database tracking
        celery_app.send_task(
            "export_data_background",
            args=[
                str(table_uuid),
                job_data.format.value,
                options,
                str(job_model.id),  # job_id for database tracking
            ],
        )

    except Exception as e:
        # Log error but don't fail - job is created and will be picked up by worker
        logger.error(f"Failed to send Celery task for export job {job_model.id}: {e}")

    # Get table name for response
    from pybase.models.table import Table
    from sqlalchemy import select

    table_query = select(Table).where(Table.id == table_uuid)
    table_result = await db.execute(table_query)
    table_model = table_result.scalar_one_or_none()
    table_name = table_model.name if table_model else "Unknown"

    # Get view name if applicable
    view_name = None
    if view_uuid:
        from pybase.models.view import View

        view_query = select(View).where(View.id == view_uuid)
        view_result = await db.execute(view_query)
        view_model = view_result.scalar_one_or_none()
        view_name = view_model.name if view_model else None

    # Set download expiration to 7 days from now
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    return ExportJobResponse(
        id=job_model.id,
        status=ExportJobStatus(job_model.status_enum.value),
        format=job_data.format,
        table_id=table_uuid,
        table_name=table_name,
        view_id=view_uuid,
        view_name=view_name,
        filters=job_data.filters or {},
        field_ids=job_data.field_ids,
        options=options,
        progress=0,
        records_processed=0,
        total_records=0,
        file_url=None,
        file_size=None,
        file_path=None,
        expires_at=expires_at,
        error_message=None,
        retry_count=0,
        celery_task_id=job_model.celery_task_id,
        created_at=job_model.created_at,
        started_at=None,
        completed_at=None,
    )


@router.get(
    "/exports/{job_id}",
    response_model=ExportJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get export job status",
    description="Get the status and details of a background export job by job ID.",
    tags=["Export Jobs"],
)
async def get_export_job(
    job_id: str,
    db: DbSession,
    current_user: CurrentUser,
    export_job_service: Annotated[ExportJobService, Depends(get_export_job_service)],
) -> ExportJobResponse:
    """
    Get export job status by ID.

    Returns current status of export job including:
    - Status (PENDING, PROCESSING, COMPLETED, FAILED)
    - Progress percentage
    - Number of records processed
    - Download URL (when completed)
    - Error details (if failed)

    Returns 404 if job not found.
    Returns 403 if user doesn't have access to the job.
    """
    # Validate job_id format
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    # Get job from service
    try:
        job_model = await export_job_service.get_job(
            db=db,
            job_id=str(job_uuid),
        )
    except NotFoundError as e:
        # Convert NotFoundError to HTTP 404 response
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e

    # Import necessary modules
    from sqlalchemy import select
    from pybase.models.base import Base
    from pybase.models.table import Table
    from pybase.models.view import View
    from pybase.models.workspace import WorkspaceMember
    from pybase.schemas.extraction import ExportFormat

    # Get table for permission check and response
    table_query = select(Table).where(Table.id == UUID(str(job_model.table_id)))
    table_result = await db.execute(table_query)
    table_model = table_result.scalar_one_or_none()

    if not table_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found",
        )

    # Check permission: user must be the job owner or have access to the table
    if job_model.user_id != str(current_user.id):
        # Get base to find workspace
        base_query = select(Base).where(Base.id == table_model.base_id)
        base_result = await db.execute(base_query)
        base_model = base_result.scalar_one_or_none()

        if not base_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Base not found",
            )

        # Check if user is a workspace member
        member_query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == base_model.workspace_id,
            WorkspaceMember.user_id == str(current_user.id),
        )
        member_result = await db.execute(member_query)
        member = member_result.scalar_one_or_none()

        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this export job",
            )

    table_name = table_model.name

    # Get view name if applicable
    view_name = None
    view_uuid = None
    if job_model.view_id:
        try:
            view_uuid = UUID(str(job_model.view_id))
            view_query = select(View).where(View.id == view_uuid)
            view_result = await db.execute(view_query)
            view_model = view_result.scalar_one_or_none()
            view_name = view_model.name if view_model else None
        except ValueError:
            pass  # Invalid view UUID, ignore

    # Build response from job model
    return ExportJobResponse(
        id=job_model.id,
        status=ExportJobStatus(job_model.status_enum.value),
        format=ExportFormat(job_model.export_format),
        table_id=UUID(str(job_model.table_id)),
        table_name=table_name,
        view_id=view_uuid,
        view_name=view_name,
        filters=job_model.filters if job_model.filters else {},
        field_ids=job_model.field_ids if job_model.field_ids else None,
        options=job_model.options if job_model.options else {},
        progress=job_model.progress or 0,
        records_processed=job_model.records_processed or 0,
        total_records=job_model.total_records or 0,
        file_url=job_model.file_url,
        file_size=job_model.file_size,
        file_path=job_model.file_path,
        expires_at=job_model.expires_at,
        error_message=job_model.error_message,
        retry_count=job_model.retry_count or 0,
        celery_task_id=job_model.celery_task_id,
        created_at=job_model.created_at,
        started_at=job_model.started_at,
        completed_at=job_model.completed_at,
    )


@router.get(
    "/exports/{job_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download export file",
    description="Download the exported file for a completed export job.",
    tags=["Export Jobs"],
)
async def download_export_file(
    job_id: str,
    db: DbSession,
    current_user: CurrentUser,
    export_job_service: Annotated[ExportJobService, Depends(get_export_job_service)],
):
    """
    Download export file by job ID.

    Streams the exported file to the client if the job is completed.
    Returns 404 if job not found.
    Returns 403 if user doesn't have access to the job.
    Returns 400 if job is not completed or download link has expired.

    **Download Flow:**
    1. Validates job exists and user has permission
    2. Checks job status is COMPLETED
    3. Checks download link hasn't expired
    4. Streams file from storage (local or S3)
    5. Returns appropriate Content-Type and Content-Disposition headers
    """
    import os
    from pathlib import Path

    # Validate job_id format
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    # Get job from service
    try:
        job_model = await export_job_service.get_job(
            db=db,
            job_id=str(job_uuid),
        )
    except NotFoundError as e:
        # Convert NotFoundError to HTTP 404 response
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e

    # Import necessary modules for permission check
    from sqlalchemy import select
    from pybase.models.base import Base
    from pybase.models.table import Table
    from pybase.models.workspace import WorkspaceMember

    # Get table for permission check
    table_query = select(Table).where(Table.id == UUID(str(job_model.table_id)))
    table_result = await db.execute(table_query)
    table_model = table_result.scalar_one_or_none()

    if not table_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found",
        )

    # Check permission: user must be the job owner or have access to the table
    if job_model.user_id != str(current_user.id):
        # Get base to find workspace
        base_query = select(Base).where(Base.id == table_model.base_id)
        base_result = await db.execute(base_query)
        base_model = base_result.scalar_one_or_none()

        if not base_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Base not found",
            )

        # Check if user is a workspace member
        member_query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == base_model.workspace_id,
            WorkspaceMember.user_id == str(current_user.id),
        )
        member_result = await db.execute(member_query)
        member = member_result.scalar_one_or_none()

        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this export job",
            )

    # Check if job is completed
    if job_model.status_enum != ExportJobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export job is not completed. Current status: {job_model.status_enum.value}",
        )

    # Check if download link has expired
    if job_model.expires_at and job_model.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Download link has expired",
        )

    # Determine file path and media type
    file_path = job_model.file_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found",
        )

    # Determine media type based on export format
    media_types = {
        "csv": "text/csv",
        "json": "application/json",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xml": "application/xml",
    }
    media_type = media_types.get(job_model.export_format, "application/octet-stream")

    # Generate filename
    filename = f"export_{table_model.name}_{job_id[:8]}.{job_model.export_format}"

    # Async generator to stream file in chunks
    async def file_generator():
        chunk_size = 8192  # 8KB chunks
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                yield chunk

    # Return streaming response
    return StreamingResponse(
        file_generator(),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(os.path.getsize(file_path)),
        },
    )


# =============================================================================
# Scheduled Export Endpoints
# =============================================================================


@router.post(
    "/scheduled-exports",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create scheduled export",
    description="Create a scheduled export that runs periodically based on a cron schedule.",
    tags=["Scheduled Exports"],
)
async def create_scheduled_export(
    scheduled_export_data: dict,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """
    Create a scheduled export.

    Creates a scheduled export configuration that will run periodically based on
    the provided cron schedule expression. The export will be executed by Celery beat
    and can be configured to upload to external storage (S3, SFTP).

    **Schedule Format:**
    Uses standard cron expression format: "minute hour day month day_of_week"
    Examples:
    - "0 0 * * *" - Daily at midnight
    - "0 0 * * 0" - Weekly on Sunday at midnight
    - "0 0 1 * *" - Monthly on the 1st at midnight
    - "0 */6 * * *" - Every 6 hours

    **Request Body:**
    - table_id: Table ID to export (required)
    - schedule: Cron schedule expression (required)
    - format: Export format - csv, xlsx, json, xml (default: csv)
    - name: Optional name for the scheduled export
    - description: Optional description
    - view_id: Optional view ID for filtering
    - filters: Optional filter criteria
    - sort: Optional sort specification
    - field_ids: Optional list of field IDs to export
    - options: Optional format-specific export options
    - include_attachments: Include attachment files (default: false)
    - flatten_linked_records: Flatten linked record data (default: false)
    - storage_config: Optional storage configuration (S3, SFTP)
    - is_active: Whether the scheduled export is active (default: true)

    Returns 201 with scheduled export details.
    """
    from uuid import UUID, uuid4
    from sqlalchemy import select
    from pybase.models.table import Table
    from pybase.models.view import View

    # Extract and validate table_id
    table_id_str = scheduled_export_data.get("table_id")
    if not table_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="table_id is required",
        )

    try:
        table_uuid = UUID(str(table_id_str))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table ID format",
        )

    # Validate schedule (basic cron validation)
    schedule = scheduled_export_data.get("schedule")
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="schedule is required",
        )

    # Basic cron format validation (5 parts separated by spaces)
    schedule_parts = schedule.strip().split()
    if len(schedule_parts) != 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cron schedule format. Must be 5 parts: minute hour day month day_of_week",
        )

    # Validate export format
    format_str = scheduled_export_data.get("format", "csv")
    valid_formats = ["csv", "xlsx", "json", "xml"]
    if format_str.lower() not in valid_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}",
        )

    # Validate view_id if provided
    view_uuid = None
    view_id_str = scheduled_export_data.get("view_id")
    if view_id_str:
        try:
            view_uuid = UUID(str(view_id_str))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid view ID format",
            )

    # Validate field_ids if provided
    field_ids = None
    field_ids_list = scheduled_export_data.get("field_ids")
    if field_ids_list:
        field_ids = [str(fid) for fid in field_ids_list]

    # Get table for permission check and response
    table_query = select(Table).where(Table.id == table_uuid)
    table_result = await db.execute(table_query)
    table_model = table_result.scalar_one_or_none()

    if not table_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found",
        )

    # Check permission: user must have access to the table
    from pybase.models.base import Base
    from pybase.models.workspace import WorkspaceMember

    base_query = select(Base).where(Base.id == table_model.base_id)
    base_result = await db.execute(base_query)
    base_model = base_result.scalar_one_or_none()

    if not base_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base not found",
        )

    # Check if user is a workspace member
    member_query = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == base_model.workspace_id,
        WorkspaceMember.user_id == str(current_user.id),
    )
    member_result = await db.execute(member_query)
    member = member_result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this table",
        )

    # Get view name if applicable
    view_name = None
    if view_uuid:
        view_query = select(View).where(View.id == view_uuid)
        view_result = await db.execute(view_query)
        view_model = view_result.scalar_one_or_none()
        view_name = view_model.name if view_model else None

    # Build options dict
    options = scheduled_export_data.get("options") or {}
    if scheduled_export_data.get("filters"):
        options["filters"] = scheduled_export_data["filters"]
    if scheduled_export_data.get("sort"):
        options["sort"] = scheduled_export_data["sort"]
    if scheduled_export_data.get("include_attachments"):
        options["include_attachments"] = scheduled_export_data["include_attachments"]
    if scheduled_export_data.get("flatten_linked_records"):
        options["flatten_linked_records"] = scheduled_export_data["flatten_linked_records"]
    if view_uuid:
        options["view_id"] = str(view_uuid)
    if field_ids:
        options["field_ids"] = field_ids

    # Generate unique scheduled export ID and task name
    scheduled_export_id = str(uuid4())
    task_name = f"scheduled_export_{scheduled_export_id}"

    # Register scheduled task with Celery beat
    try:
        from celery import Celery
        import os

        # Create Celery app to register periodic task
        celery_app = Celery(
            broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
            backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
        )

        # Configure Celery beat schedule
        celery_app.conf.beat_schedule = {
            task_name: {
                "task": "export_data_scheduled",
                "schedule": schedule,  # This will be parsed by celery beat
                "args": [
                    str(table_uuid),
                    str(current_user.id),
                    format_str.lower(),
                    schedule,
                    options,
                    scheduled_export_data.get("storage_config"),
                ],
            },
        }

        # Send task to register with beat
        celery_app.send_task(
            "export_data_scheduled",
            args=[
                str(table_uuid),
                str(current_user.id),
                format_str.lower(),
                schedule,
                options,
                scheduled_export_data.get("storage_config"),
            ],
        )

    except Exception as e:
        # Log error but don't fail - registration can be done manually
        logger.error(f"Failed to register Celery beat task for scheduled export {scheduled_export_id}: {e}")

    # Calculate next run time (simple estimation based on cron)
    from datetime import datetime, timezone, timedelta

    # For simplicity, next run is estimated (actual calculation by celery beat)
    next_run_at = datetime.now(timezone.utc) + timedelta(minutes=5)  # Placeholder

    # Return response
    return {
        "id": scheduled_export_id,
        "name": scheduled_export_data.get("name"),
        "description": scheduled_export_data.get("description"),
        "table_id": table_uuid,
        "table_name": table_model.name,
        "schedule": schedule,
        "format": format_str.lower(),
        "view_id": view_uuid,
        "view_name": view_name,
        "filters": scheduled_export_data.get("filters") or {},
        "field_ids": field_ids_list,
        "options": options,
        "include_attachments": scheduled_export_data.get("include_attachments", False),
        "flatten_linked_records": scheduled_export_data.get("flatten_linked_records", False),
        "storage_config": scheduled_export_data.get("storage_config"),
        "is_active": scheduled_export_data.get("is_active", True),
        "user_id": current_user.id,
        "celery_task_name": task_name,
        "last_run_at": None,
        "next_run_at": next_run_at,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
    }


# =============================================================================
