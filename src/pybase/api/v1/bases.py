"""
Base endpoints.

Handles base CRUD operations.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
)
from pybase.schemas.base import (
    BaseCreate,
    BaseListResponse,
    BaseResponse,
    BaseUpdate,
)
from pybase.services.base import BaseService

router = APIRouter()

# =============================================================================
# Dependencies
# =============================================================================


def get_base_service() -> BaseService:
    """Get base service instance."""
    return BaseService()


# =============================================================================
# Base CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=BaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_base(
    base_data: BaseCreate,
    db: DbSession,
    current_user: CurrentUser,
    base_service: Annotated[BaseService, Depends(get_base_service)],
) -> BaseResponse:
    """
    Create a new base in a workspace.

    Creates a new base owned by the specified workspace.
    User must have access to workspace.
    """
    base = await base_service.create_base(
        db=db,
        user_id=current_user.id,
        base_data=base_data,
    )

    return base


@router.get("", response_model=BaseListResponse)
async def list_bases(
    db: DbSession,
    current_user: CurrentUser,
    base_service: Annotated[BaseService, Depends(get_base_service)],
    workspace_id: Annotated[
        str | None,
        Query(
            description="Workspace ID to filter bases by (optional)",
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
) -> BaseListResponse:
    """
    List bases accessible to current user.

    Returns paginated list of bases.
    Can filter by workspace_id.
    """
    bases, total = await base_service.list_bases(
        db=db,
        workspace_id=workspace_id,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )

    return BaseListResponse(
        items=bases,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{base_id}", response_model=BaseResponse)
async def get_base(
    base_id: str,
    db: DbSession,
    current_user: CurrentUser,
    base_service: Annotated[BaseService, Depends(get_base_service)],
) -> BaseResponse:
    """
    Get a base by ID.

    Returns base details.
    Requires user to have access to base's workspace.
    """
    from uuid import UUID

    try:
        base_uuid = UUID(base_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base ID format",
        )

    base = await base_service.get_base_by_id(
        db=db,
        base_id=base_uuid,
        user_id=current_user.id,
    )

    return base


@router.patch("/{base_id}", response_model=BaseResponse)
async def update_base(
    base_id: str,
    base_data: BaseUpdate,
    db: DbSession,
    current_user: CurrentUser,
    base_service: Annotated[BaseService, Depends(get_base_service)],
) -> BaseResponse:
    """
    Update a base.

    Updates base name, description, and/or icon.
    Requires workspace owner or admin role.
    """
    from uuid import UUID

    try:
        base_uuid = UUID(base_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base ID format",
        )

    updated_base = await base_service.update_base(
        db=db,
        base_id=base_uuid,
        user_id=current_user.id,
        base_data=base_data,
    )

    return updated_base


@router.delete("/{base_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_base(
    base_id: str,
    db: DbSession,
    current_user: CurrentUser,
    base_service: Annotated[BaseService, Depends(get_base_service)],
) -> None:
    """
    Delete a base.

    Soft deletes the base (marks as deleted).
    Only workspace owner can delete bases.
    """
    from uuid import UUID

    try:
        base_uuid = UUID(base_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base ID format",
        )

    await base_service.delete_base(
        db=db,
        base_id=base_uuid,
        user_id=current_user.id,
    )


# =============================================================================
