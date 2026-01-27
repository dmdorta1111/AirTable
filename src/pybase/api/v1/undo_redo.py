"""
Undo/Redo endpoints.

Handles undo/redo operations for records, fields, and views.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.schemas.operation_log import (
    OperationLogListResponse,
    OperationLogResponse,
    RedoRequest,
    UndoRequest,
)
from pybase.services.undo_redo import UndoRedoService

router = APIRouter()

# =============================================================================
# Dependencies
# =============================================================================


def get_undo_redo_service() -> UndoRedoService:
    """Get undo/redo service instance."""
    return UndoRedoService()


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
