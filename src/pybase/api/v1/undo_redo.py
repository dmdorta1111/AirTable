"""
Undo/Redo endpoints.

Handles undo/redo operations for records, fields, and views.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.models.field import Field
from pybase.models.record import Record
from pybase.models.view import View
from pybase.realtime import get_connection_manager
from pybase.schemas.operation_log import (
    OperationLogListResponse,
    OperationLogResponse,
    RedoRequest,
    UndoRequest,
)
from pybase.schemas.realtime import (
    OperationRedoneEvent,
    OperationUndoneEvent,
)
from pybase.services.undo_redo import UndoRedoService

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# Dependencies
# =============================================================================


def get_undo_redo_service() -> UndoRedoService:
    """Get undo/redo service instance."""
    return UndoRedoService()


# =============================================================================
# WebSocket Broadcasting Helpers
# =============================================================================


async def _broadcast_undo_event(
    db: DbSession,
    operation,
    user_id: str,
    user_name: str,
) -> None:
    """Broadcast undo event to WebSocket subscribers.

    Args:
        db: Database session
        operation: Operation that was undone
        user_id: User ID who undid the operation
        user_name: Display name of user who undid the operation
    """
    manager = get_connection_manager()

    # Extract table_id based on entity type
    table_id = None
    try:
        if operation.entity_type == "record":
            entity = await db.get(Record, operation.entity_id)
            if entity:
                table_id = str(entity.table_id)
        elif operation.entity_type == "field":
            entity = await db.get(Field, operation.entity_id)
            if entity:
                table_id = str(entity.table_id)
        elif operation.entity_type == "view":
            entity = await db.get(View, operation.entity_id)
            if entity:
                table_id = str(entity.table_id)
    except Exception as e:
        logger.error(f"Failed to get entity for broadcasting: {e}")

    # Create and broadcast event
    event = OperationUndoneEvent(
        operation_id=str(operation.id),
        operation_type=operation.operation_type,
        entity_type=operation.entity_type,
        entity_id=str(operation.entity_id),
        table_id=table_id,
        undone_by=user_id,
        undone_by_name=user_name,
        before_data=operation.get_after_data(),  # State before undo (after original op)
        after_data=operation.get_before_data(),  # State after undo (before original op)
    )

    # Broadcast to table channel if we have table_id
    if table_id:
        channel = f"table:{table_id}"
        try:
            sent_count = await manager.broadcast_to_channel(channel, event)
            logger.debug(f"Broadcast undo event to {sent_count} subscribers on {channel}")
        except Exception as e:
            logger.error(f"Failed to broadcast undo event: {e}")


async def _broadcast_redo_event(
    db: DbSession,
    operation,
    user_id: str,
    user_name: str,
) -> None:
    """Broadcast redo event to WebSocket subscribers.

    Args:
        db: Database session
        operation: Operation that was redone
        user_id: User ID who redid the operation
        user_name: Display name of user who redid the operation
    """
    manager = get_connection_manager()

    # Extract table_id based on entity type
    table_id = None
    try:
        if operation.entity_type == "record":
            entity = await db.get(Record, operation.entity_id)
            if entity:
                table_id = str(entity.table_id)
        elif operation.entity_type == "field":
            entity = await db.get(Field, operation.entity_id)
            if entity:
                table_id = str(entity.table_id)
        elif operation.entity_type == "view":
            entity = await db.get(View, operation.entity_id)
            if entity:
                table_id = str(entity.table_id)
    except Exception as e:
        logger.error(f"Failed to get entity for broadcasting: {e}")

    # Create and broadcast event
    event = OperationRedoneEvent(
        operation_id=str(operation.id),
        operation_type=operation.operation_type,
        entity_type=operation.entity_type,
        entity_id=str(operation.entity_id),
        table_id=table_id,
        redone_by=user_id,
        redone_by_name=user_name,
        before_data=operation.get_before_data(),  # State before redo (before original op)
        after_data=operation.get_after_data(),  # State after redo (after original op)
    )

    # Broadcast to table channel if we have table_id
    if table_id:
        channel = f"table:{table_id}"
        try:
            sent_count = await manager.broadcast_to_channel(channel, event)
            logger.debug(f"Broadcast redo event to {sent_count} subscribers on {channel}")
        except Exception as e:
            logger.error(f"Failed to broadcast redo event: {e}")


# =============================================================================
# Undo/Redo Endpoints
# =============================================================================


@router.post(
    "/undo",
    response_model=OperationLogResponse,
    status_code=status.HTTP_200_OK,
)
async def undo_operation(
    request: UndoRequest,
    db: DbSession,
    current_user: CurrentUser,
    undo_redo_service: Annotated[UndoRedoService, Depends(get_undo_redo_service)],
) -> OperationLogResponse:
    """
    Undo an operation.

    Reverts the specified operation to its before state.
    User must own the operation to undo it.
    """
    # Validate operation_id UUID format
    try:
        from uuid import UUID

        UUID(request.operation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid operation ID format",
        )

    try:
        operation = await undo_redo_service.undo_operation(
            db=db,
            user_id=str(current_user.id),
            operation_id=request.operation_id,
        )

        # Broadcast undo event via WebSocket
        user_name = current_user.display_name or current_user.email
        await _broadcast_undo_event(db, operation, str(current_user.id), user_name)
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
    except ConflictError as e:
        # Convert ConflictError to HTTP 409 response
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e

    return OperationLogResponse(
        id=str(operation.id),
        user_id=str(operation.user_id),
        operation_type=operation.operation_type,
        entity_type=operation.entity_type,
        entity_id=str(operation.entity_id),
        before_data=operation.get_before_data(),
        after_data=operation.get_after_data(),
        created_at=operation.created_at,
        updated_at=operation.updated_at,
    )


@router.post(
    "/redo",
    response_model=OperationLogResponse,
    status_code=status.HTTP_200_OK,
)
async def redo_operation(
    request: RedoRequest,
    db: DbSession,
    current_user: CurrentUser,
    undo_redo_service: Annotated[UndoRedoService, Depends(get_undo_redo_service)],
) -> OperationLogResponse:
    """
    Redo an operation.

    Re-applies the specified operation using its after state.
    User must own the operation to redo it.
    """
    # Validate operation_id UUID format
    try:
        from uuid import UUID

        UUID(request.operation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid operation ID format",
        )

    try:
        operation = await undo_redo_service.redo_operation(
            db=db,
            user_id=str(current_user.id),
            operation_id=request.operation_id,
        )

        # Broadcast redo event via WebSocket
        user_name = current_user.display_name or current_user.email
        await _broadcast_redo_event(db, operation, str(current_user.id), user_name)
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
    except ConflictError as e:
        # Convert ConflictError to HTTP 409 response
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e

    return OperationLogResponse(
        id=str(operation.id),
        user_id=str(operation.user_id),
        operation_type=operation.operation_type,
        entity_type=operation.entity_type,
        entity_id=str(operation.entity_id),
        before_data=operation.get_before_data(),
        after_data=operation.get_after_data(),
        created_at=operation.created_at,
        updated_at=operation.updated_at,
    )


@router.get(
    "/operations",
    response_model=OperationLogListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_operations(
    db: DbSession,
    current_user: CurrentUser,
    undo_redo_service: Annotated[UndoRedoService, Depends(get_undo_redo_service)],
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Number of items per page (max 100)",
        ),
    ] = 20,
    operation_type: Annotated[
        str | None,
        Query(
            description="Filter by operation type (create, update, delete)",
        ),
    ] = None,
    entity_type: Annotated[
        str | None,
        Query(
            description="Filter by entity type (record, field, view)",
        ),
    ] = None,
) -> OperationLogListResponse:
    """
    List operations for current user.

    Returns paginated list of operations performed by the current user.
    Can filter by operation_type and entity_type.
    Operations are ordered by most recent first.
    """
    operations, total = await undo_redo_service.get_user_operations(
        db=db,
        user_id=str(current_user.id),
        page=page,
        page_size=page_size,
        operation_type=operation_type,
        entity_type=entity_type,
    )

    # Convert operations to response format
    items = [
        OperationLogResponse(
            id=str(operation.id),
            user_id=str(operation.user_id),
            operation_type=operation.operation_type,
            entity_type=operation.entity_type,
            entity_id=str(operation.entity_id),
            before_data=operation.get_before_data(),
            after_data=operation.get_after_data(),
            created_at=operation.created_at,
            updated_at=operation.updated_at,
        )
        for operation in operations
    ]

    return OperationLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
