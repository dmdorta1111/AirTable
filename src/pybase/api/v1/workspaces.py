"""
Workspace endpoints.

Handles workspace CRUD operations and member management.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.models.workspace import WorkspaceRole
from pybase.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceDetailResponse,
    WorkspaceListResponse,
    WorkspaceMemberCreate,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from pybase.services.workspace import WorkspaceService

router = APIRouter()

# =============================================================================
# Dependencies
# =============================================================================


def get_workspace_service() -> WorkspaceService:
    """Get workspace service instance."""
    return WorkspaceService()


# =============================================================================
# Workspace CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    db: DbSession,
    current_user: CurrentUser,
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceResponse:
    """
    Create a new workspace.

    Creates a new workspace owned by the current user.
    The user is automatically added as an owner member.
    """
    workspace = await workspace_service.create_workspace(
        db=db,
        owner_id=current_user.id,
        workspace_data=workspace_data,
    )

    return workspace


@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(
    db: DbSession,
    current_user: CurrentUser,
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Number of items per page (max 100)",
        ),
    ] = 20,
) -> WorkspaceListResponse:
    """
    List workspaces accessible to the current user.

    Returns paginated list of workspaces where the user is a member.
    """
    workspaces, total = await workspace_service.list_workspaces(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )

    return WorkspaceListResponse(
        items=workspaces,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{workspace_id}", response_model=WorkspaceDetailResponse)
async def get_workspace(
    workspace_id: str,
    db: DbSession,
    current_user: CurrentUser,
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceDetailResponse:
    """
    Get a workspace by ID.

    Returns workspace details including members.
    Requires the user to be a member of the workspace.
    """
    from uuid import UUID

    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format",
        )

    workspace = await workspace_service.get_workspace_by_id(
        db=db,
        workspace_id=workspace_uuid,
        user_id=current_user.id,
    )

    # Get workspace members
    members = await workspace_service.list_workspace_members(
        db=db,
        workspace_id=workspace_uuid,
        user_id=current_user.id,
    )

    # Count members
    members_count = len(members)

    return WorkspaceDetailResponse(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        owner_id=workspace.owner_id,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        members_count=members_count,
        members=members,
    )


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    workspace_data: WorkspaceUpdate,
    db: DbSession,
    current_user: CurrentUser,
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceResponse:
    """
    Update a workspace.

    Updates workspace name and/or description.
    Requires owner or admin role.
    """
    from uuid import UUID

    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format",
        )

    updated_workspace = await workspace_service.update_workspace(
        db=db,
        workspace_id=workspace_uuid,
        user_id=current_user.id,
        workspace_data=workspace_data,
    )

    return updated_workspace


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    db: DbSession,
    current_user: CurrentUser,
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> None:
    """
    Delete a workspace.

    Soft deletes the workspace (marks as deleted).
    Only the workspace owner can delete it.
    """
    from uuid import UUID

    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format",
        )

    await workspace_service.delete_workspace(
        db=db,
        workspace_id=workspace_uuid,
        user_id=current_user.id,
    )


# =============================================================================
# Workspace Member Management Endpoints
# =============================================================================


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_workspace_member(
    workspace_id: str,
    member_data: WorkspaceMemberCreate,
    db: DbSession,
    current_user: CurrentUser,
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceMemberResponse:
    """
    Add a member to a workspace.

    Adds an existing user as a workspace member.
    Requires owner or admin role.
    """
    from uuid import UUID

    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format",
        )

    member = await workspace_service.add_member(
        db=db,
        workspace_id=workspace_uuid,
        owner_id=current_user.id,
        user_id=member_data.user_id,
        role=member_data.role,
    )

    return member


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberResponse])
async def list_workspace_members(
    workspace_id: str,
    db: DbSession,
    current_user: CurrentUser,
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> list[WorkspaceMemberResponse]:
    """
    List members of a workspace.

    Returns all members of the workspace.
    Requires the user to be a member of the workspace.
    """
    from uuid import UUID

    try:
        workspace_uuid = UUID(workspace_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workspace ID format",
        )

    members = await workspace_service.list_workspace_members(
        db=db,
        workspace_id=workspace_uuid,
        user_id=current_user.id,
    )

    return members


@router.patch("/{workspace_id}/members/{member_id}", response_model=WorkspaceMemberResponse)
async def update_workspace_member_role(
    workspace_id: str,
    member_id: str,
    member_data: WorkspaceMemberUpdate,
    db: DbSession,
    current_user: CurrentUser,
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceMemberResponse:
    """
    Update a member's role.

    Changes the role of a workspace member.
    Only the workspace owner can change roles.
    """
    from uuid import UUID

    try:
        workspace_uuid = UUID(workspace_id)
        member_uuid = UUID(member_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    updated_member = await workspace_service.update_member_role(
        db=db,
        workspace_id=workspace_uuid,
        requester_id=current_user.id,
        member_id=member_uuid,
        role=member_data.role,
    )

    return updated_member


@router.delete("/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: str,
    member_id: str,
    db: DbSession,
    current_user: CurrentUser,
    workspace_service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> None:
    """
    Remove a member from a workspace.

    Removes a user from the workspace.
    Only the workspace owner can remove members.
    The owner cannot remove themselves.
    """
    from uuid import UUID

    try:
        workspace_uuid = UUID(workspace_id)
        member_uuid = UUID(member_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    await workspace_service.remove_member(
        db=db,
        workspace_id=workspace_uuid,
        requester_id=current_user.id,
        member_id=member_uuid,
    )


# =============================================================================
