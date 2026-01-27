"""
Trash endpoints.

Handles trash bin operations: list, restore, and permanent delete.
"""

import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.schemas.batch import (
    BatchOperationResponse,
    BatchRecordDelete,
    RecordOperationResult,
)
from pybase.schemas.trash import (
    RestoreResponse,
    TrashItem,
    TrashListResponse,
)
from pybase.services.trash import TrashService

router = APIRouter()

# =============================================================================
# Dependencies
# =============================================================================


def get_trash_service() -> TrashService:
    """Get trash service instance."""
    return TrashService()


def record_to_trash_item(record) -> TrashItem:
    """Convert Record model to TrashItem schema.

    Args:
        record: Record model instance

    Returns:
        TrashItem schema
    """
    # Parse JSON data
    try:
        data = json.loads(record.data) if isinstance(record.data, str) else record.data
    except (json.JSONDecodeError, TypeError):
        data = {}

    return TrashItem(
        id=str(record.id),
        table_id=str(record.table_id),
        data=data,
        deleted_at=record.deleted_at,
        deleted_by_id=str(record.deleted_by_id) if record.deleted_by_id else None,
        created_at=record.created_at,
        updated_at=record.updated_at,
        row_height=record.row_height or 32,
    )


# =============================================================================
# Trash List Endpoints
# =============================================================================


@router.get("", response_model=TrashListResponse)
async def list_trash(
    db: DbSession,
    current_user: CurrentUser,
    trash_service: Annotated[TrashService, Depends(get_trash_service)],
    table_id: Annotated[
        str | None,
        Query(
            description="Table ID to filter trash by (optional)",
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
):
    """
    List deleted records in trash accessible to current user.

    Returns paginated list of deleted records.
    Can filter by table_id.
    Shows deletion timestamp and who deleted each record.
    """
    table_uuid: UUID | None = None
    if table_id:
        try:
            table_uuid = UUID(table_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid table ID format",
            )

    try:
        records, total = await trash_service.list_trash(
            db=db,
            user_id=str(current_user.id),
            table_id=table_uuid,
            page=page,
            page_size=page_size,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e

    # Convert records to trash items
    items = [record_to_trash_item(record) for record in records]

    return TrashListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Trash Restore Endpoints
# =============================================================================


@router.post("/{record_id}/restore", response_model=RestoreResponse)
async def restore_record(
    record_id: str,
    db: DbSession,
    current_user: CurrentUser,
    trash_service: Annotated[TrashService, Depends(get_trash_service)],
) -> RestoreResponse:
    """
    Restore a deleted record from trash.

    Restores a single record from trash back to active records.
    Requires user to have access to record's table workspace.
    """
    # Validate UUID format but keep as string
    try:
        UUID(record_id)  # Just validate format
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid record ID format",
        )

    try:
        restored_record = await trash_service.restore_record(
            db=db,
            record_id=record_id,
            user_id=str(current_user.id),
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e

    return RestoreResponse(
        id=str(restored_record.id),
        message="Record restored successfully",
    )


@router.post(
    "/batch/restore",
    response_model=BatchOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Restore multiple records from trash in batch",
    description="Restore multiple deleted records in a single request. Max 100 records per batch.",
)
async def batch_restore_records(
    batch_data: BatchRecordDelete,
    db: DbSession,
    current_user: CurrentUser,
    trash_service: Annotated[TrashService, Depends(get_trash_service)],
) -> BatchOperationResponse:
    """
    Restore multiple deleted records from trash in a single batch operation.

    All records must be accessible to the user.
    Either all records are restored successfully, or none are (transactional).
    """
    try:
        restored_records = await trash_service.batch_restore_records(
            db=db,
            user_id=str(current_user.id),
            record_ids=batch_data.record_ids,
        )

        # All successful - build response
        results = [
            RecordOperationResult(
                record_id=str(record.id),
                success=True,
                record=None,  # Don't include full record in restore response
                error=None,
                error_code=None,
            )
            for record in restored_records
        ]

        return BatchOperationResponse(
            total=len(batch_data.record_ids),
            successful=len(restored_records),
            failed=0,
            results=results,
        )

    except NotFoundError as e:
        # Record not found - all records fail
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


# =============================================================================
# Trash Permanent Delete Endpoints
# =============================================================================


@router.delete("/{record_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def permanent_delete_record(
    record_id: str,
    db: DbSession,
    current_user: CurrentUser,
    trash_service: Annotated[TrashService, Depends(get_trash_service)],
) -> None:
    """
    Permanently delete a record from trash.

    This action cannot be undone.
    Requires workspace owner or admin role.
    """
    # Validate UUID format but keep as string
    try:
        UUID(record_id)  # Just validate format
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid record ID format",
        )

    try:
        await trash_service.permanent_delete_record(
            db=db,
            record_id=record_id,
            user_id=str(current_user.id),
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        ) from e


@router.delete(
    "/batch/permanent",
    response_model=BatchOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Permanently delete multiple records from trash in batch",
    description="Permanently delete multiple records in a single request. This action cannot be undone. Max 100 records per batch.",
)
async def batch_permanent_delete_records(
    batch_data: BatchRecordDelete,
    db: DbSession,
    current_user: CurrentUser,
    trash_service: Annotated[TrashService, Depends(get_trash_service)],
) -> BatchOperationResponse:
    """
    Permanently delete multiple records from trash in a single batch operation.

    This action cannot be undone.
    Requires workspace owner or admin role.
    Either all records are deleted successfully, or none are (transactional).
    """
    try:
        deleted_count = await trash_service.batch_permanent_delete_records(
            db=db,
            user_id=str(current_user.id),
            record_ids=batch_data.record_ids,
        )

        # All successful - build response
        results = [
            RecordOperationResult(
                record_id=record_id,
                success=True,
                record=None,
                error=None,
                error_code=None,
            )
            for record_id in batch_data.record_ids
        ]

        return BatchOperationResponse(
            total=len(batch_data.record_ids),
            successful=deleted_count,
            failed=0,
            results=results,
        )

    except NotFoundError as e:
        # Record not found - all records fail
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
