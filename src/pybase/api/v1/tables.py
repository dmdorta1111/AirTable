"""
Table endpoints.

Handles table CRUD operations.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.schemas.table import (
    TableCreate,
    TableListResponse,
    TableResponse,
    TableUpdate,
)
from pybase.services.table import TableService

router = APIRouter()

# =============================================================================
# Dependencies
# =============================================================================


def get_table_service() -> TableService:
    """Get table service instance."""
    return TableService()


# =============================================================================
# Table CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=TableResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_table(
    table_data: TableCreate,
    db: DbSession,
    current_user: CurrentUser,
    table_service: Annotated[TableService, Depends(get_table_service)],
) -> TableResponse:
    """
    Create a new table in a base.

    Creates a new table in the specified base.
    User must have access to the base's workspace.
    """
    table = await table_service.create_table(
        db=db,
        user_id=current_user.id,
        table_data=table_data,
    )

    return table


@router.get("", response_model=TableListResponse)
async def list_tables(
    db: DbSession,
    current_user: CurrentUser,
    table_service: Annotated[TableService, Depends(get_table_service)],
    base_id: Annotated[
        str | None,
        Query(
            description="Base ID to filter tables by (optional)",
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
) -> TableListResponse:
    """
    List tables accessible to current user.

    Returns paginated list of tables.
    Can filter by base_id.
    """
    from uuid import UUID

    base_uuid: UUID | None = None
    if base_id:
        try:
            base_uuid = UUID(base_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base ID format",
            )

    tables, total = await table_service.list_tables(
        db=db,
        base_id=base_uuid,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )

    return TableListResponse(
        items=tables,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{table_id}", response_model=TableResponse)
async def get_table(
    table_id: str,
    db: DbSession,
    current_user: CurrentUser,
    table_service: Annotated[TableService, Depends(get_table_service)],
) -> TableResponse:
    """
    Get a table by ID.

    Returns table details.
    Requires user to have access to table's base workspace.
    """
    from uuid import UUID

    try:
        table_uuid = UUID(table_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table ID format",
        )

    table = await table_service.get_table_by_id(
        db=db,
        table_id=table_uuid,
        user_id=current_user.id,
    )

    return table


@router.patch("/{table_id}", response_model=TableResponse)
async def update_table(
    table_id: str,
    table_data: TableUpdate,
    db: DbSession,
    current_user: CurrentUser,
    table_service: Annotated[TableService, Depends(get_table_service)],
) -> TableResponse:
    """
    Update a table.

    Updates table name, description, and/or primary field.
    Requires workspace owner or admin role.
    """
    from uuid import UUID

    try:
        table_uuid = UUID(table_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table ID format",
        )

    updated_table = await table_service.update_table(
        db=db,
        table_id=table_uuid,
        user_id=current_user.id,
        table_data=table_data,
    )

    return updated_table


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(
    table_id: str,
    db: DbSession,
    current_user: CurrentUser,
    table_service: Annotated[TableService, Depends(get_table_service)],
) -> None:
    """
    Delete a table.

    Soft deletes the table (marks as deleted).
    Only workspace owner can delete tables.
    """
    from uuid import UUID

    try:
        table_uuid = UUID(table_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table ID format",
        )

    await table_service.delete_table(
        db=db,
        table_id=table_uuid,
        user_id=current_user.id,
    )


# =============================================================================
