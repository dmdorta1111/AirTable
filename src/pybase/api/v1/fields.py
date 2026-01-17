"""
Field endpoints.

Handles field CRUD operations.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.schemas.field import (
    FieldCreate,
    FieldListResponse,
    FieldResponse,
    FieldUpdate,
)
from pybase.services.field import FieldService

router = APIRouter()

# =============================================================================
# Dependencies
# =============================================================================


def get_field_service() -> FieldService:
    """Get field service instance."""
    return FieldService()


# =============================================================================
# Field CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=FieldResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_field(
    field_data: FieldCreate,
    db: DbSession,
    current_user: CurrentUser,
    field_service: Annotated[FieldService, Depends(get_field_service)],
) -> FieldResponse:
    """
    Create a new field in a table.

    Creates a new field in specified table.
    User must have access to table's workspace.
    """
    field = await field_service.create_field(
        db=db,
        user_id=current_user.id,
        field_data=field_data,
    )

    return field


@router.get("", response_model=FieldListResponse)
async def list_fields(
    db: DbSession,
    current_user: CurrentUser,
    field_service: Annotated[FieldService, Depends(get_field_service)],
    table_id: Annotated[
        str | None,
        Query(
            description="Table ID to filter fields by (optional)",
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
) -> FieldListResponse:
    """
    List fields accessible to current user.

    Returns paginated list of fields.
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

    fields, total = await field_service.list_fields(
        db=db,
        table_id=table_uuid,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )

    return FieldListResponse(
        items=fields,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{field_id}", response_model=FieldResponse)
async def get_field(
    field_id: str,
    db: DbSession,
    current_user: CurrentUser,
    field_service: Annotated[FieldService, Depends(get_field_service)],
) -> FieldResponse:
    """
    Get a field by ID.

    Returns field details.
    Requires user to have access to field's table workspace.
    """
    from uuid import UUID

    try:
        field_uuid = UUID(field_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid field ID format",
        )

    field = await field_service.get_field_by_id(
        db=db,
        field_id=field_uuid,
        user_id=current_user.id,
    )

    return field


@router.patch("/{field_id}", response_model=FieldResponse)
async def update_field(
    field_id: str,
    field_data: FieldUpdate,
    db: DbSession,
    current_user: CurrentUser,
    field_service: Annotated[FieldService, Depends(get_field_service)],
) -> FieldResponse:
    """
    Update a field.

    Updates field name, description, options, and/or display settings.
    Requires workspace owner or admin role.
    """
    from uuid import UUID

    try:
        field_uuid = UUID(field_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid field ID format",
        )

    updated_field = await field_service.update_field(
        db=db,
        field_id=field_uuid,
        user_id=current_user.id,
        field_data=field_data,
    )

    return updated_field


@router.delete("/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_field(
    field_id: str,
    db: DbSession,
    current_user: CurrentUser,
    field_service: Annotated[FieldService, Depends(get_field_service)],
) -> None:
    """
    Delete a field.

    Soft deletes field (marks as deleted).
    Only workspace owner can delete fields.
    """
    from uuid import UUID

    try:
        field_uuid = UUID(field_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid field ID format",
        )

    await field_service.delete_field(
        db=db,
        field_id=field_uuid,
        user_id=current_user.id,
    )


# =============================================================================
