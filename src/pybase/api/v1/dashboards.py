"""
Dashboard endpoints.

Handles dashboard CRUD operations, sharing, and permissions.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.schemas.dashboard import (
    DashboardCreate,
    DashboardDuplicate,
    DashboardListResponse,
    DashboardMemberResponse,
    DashboardPermissionUpdate,
    DashboardResponse,
    DashboardShareRequest,
    DashboardUnshareRequest,
    DashboardUpdate,
)
from pybase.services.dashboard import DashboardService

router = APIRouter()


# =============================================================================
# Dependencies
# =============================================================================


def get_dashboard_service() -> DashboardService:
    """Get dashboard service instance."""
    return DashboardService()


def _dashboard_to_response(dashboard: Any) -> DashboardResponse:
    """Convert Dashboard model to DashboardResponse schema."""
    return DashboardResponse(
        id=UUID(dashboard.id),
        base_id=UUID(dashboard.base_id),
        created_by_id=UUID(dashboard.created_by_id) if dashboard.created_by_id else None,
        name=dashboard.name,
        description=dashboard.description,
        is_default=dashboard.is_default,
        is_personal=dashboard.is_personal,
        is_public=dashboard.is_public,
        is_locked=dashboard.is_locked,
        is_shared=dashboard.is_shared,
        color=dashboard.color,
        icon=dashboard.icon,
        template_id=dashboard.template_id,
        share_token=dashboard.share_token,
        last_viewed_at=dashboard.last_viewed_at,
        layout_config=dashboard.get_layout_config_dict()
        if hasattr(dashboard, "get_layout_config_dict")
        else None,
        settings=dashboard.get_settings_dict() if hasattr(dashboard, "get_settings_dict") else None,
        global_filters=dashboard.get_global_filters_list()
        if hasattr(dashboard, "get_global_filters_list")
        else [],
        created_at=dashboard.created_at,
        updated_at=dashboard.updated_at,
        deleted_at=dashboard.deleted_at,
    )


# =============================================================================
# Dashboard CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=DashboardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new dashboard",
)
async def create_dashboard(
    dashboard_data: DashboardCreate,
    db: DbSession,
    current_user: CurrentUser,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardResponse:
    """
    Create a new dashboard for a base.

    A dashboard is a custom analytics view with:
    - **Layout configuration**: Define widget positions and sizes
    - **Dashboard settings**: Customize refresh interval, theme, etc.
    - **Global filters**: Apply filters across all widgets
    - **Sharing options**: Control visibility and permissions
    """
    dashboard = await dashboard_service.create_dashboard(
        db=db,
        user_id=str(current_user.id),
        dashboard_data=dashboard_data,
    )
    return _dashboard_to_response(dashboard)


@router.get(
    "",
    response_model=DashboardListResponse,
    summary="List dashboards",
)
async def list_dashboards(
    db: DbSession,
    current_user: CurrentUser,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
    base_id: Annotated[
        str,
        Query(description="Base ID to list dashboards for"),
    ],
    include_personal: Annotated[
        bool,
        Query(description="Include personal dashboards (only your own)"),
    ] = True,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Number of items per page (max 100)"),
    ] = 50,
) -> DashboardListResponse:
    """
    List dashboards for a base.

    Returns paginated list of dashboards.
    Personal dashboards are only returned for the creator.
    """
    try:
        base_uuid = UUID(base_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base ID format",
        )

    dashboards, total = await dashboard_service.list_dashboards(
        db=db,
        base_id=base_uuid,
        user_id=str(current_user.id),
        include_personal=include_personal,
        page=page,
        page_size=page_size,
    )

    return DashboardListResponse(
        items=[_dashboard_to_response(d) for d in dashboards],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/default",
    response_model=DashboardResponse,
    summary="Get default dashboard",
)
async def get_default_dashboard(
    db: DbSession,
    current_user: CurrentUser,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
    base_id: Annotated[str, Query(description="Base ID")],
) -> DashboardResponse:
    """
    Get the default dashboard for a base.

    If no default is set, returns the first dashboard by name.
    """
    try:
        UUID(base_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base ID format",
        )

    dashboards, _ = await dashboard_service.list_dashboards(
        db=db,
        base_id=UUID(base_id),
        user_id=str(current_user.id),
        include_personal=True,
        page=1,
        page_size=1,
    )

    if not dashboards:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No dashboards found for this base",
        )

    return _dashboard_to_response(dashboards[0])


@router.get(
    "/{dashboard_id}",
    response_model=DashboardResponse,
    summary="Get a dashboard",
)
async def get_dashboard(
    dashboard_id: str,
    db: DbSession,
    current_user: CurrentUser,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardResponse:
    """
    Get a dashboard by ID.

    Returns complete dashboard configuration including:
    - Layout and widget positions
    - Dashboard settings
    - Global filters
    - Sharing information
    """
    try:
        UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format",
        )

    dashboard = await dashboard_service.get_dashboard_by_id(
        db=db,
        dashboard_id=dashboard_id,
        user_id=str(current_user.id),
    )
    return _dashboard_to_response(dashboard)


@router.patch(
    "/{dashboard_id}",
    response_model=DashboardResponse,
    summary="Update a dashboard",
)
async def update_dashboard(
    dashboard_id: str,
    dashboard_data: DashboardUpdate,
    db: DbSession,
    current_user: CurrentUser,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardResponse:
    """
    Update a dashboard.

    Only the dashboard creator or users with edit permission can update.
    Locked dashboards cannot be updated by non-creators.
    """
    try:
        UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format",
        )

    dashboard = await dashboard_service.update_dashboard(
        db=db,
        dashboard_id=dashboard_id,
        user_id=str(current_user.id),
        dashboard_data=dashboard_data,
    )
    return _dashboard_to_response(dashboard)


@router.delete(
    "/{dashboard_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a dashboard",
)
async def delete_dashboard(
    dashboard_id: str,
    db: DbSession,
    current_user: CurrentUser,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> None:
    """
    Delete a dashboard (soft delete).

    Only the dashboard creator or workspace owner can delete.
    """
    try:
        UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format",
        )

    await dashboard_service.delete_dashboard(
        db=db,
        dashboard_id=dashboard_id,
        user_id=str(current_user.id),
    )


# =============================================================================
# Dashboard Duplication
# =============================================================================


@router.post(
    "/{dashboard_id}/duplicate",
    response_model=DashboardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate a dashboard",
)
async def duplicate_dashboard(
    dashboard_id: str,
    duplicate_data: DashboardDuplicate,
    db: DbSession,
    current_user: CurrentUser,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardResponse:
    """
    Duplicate an existing dashboard.

    Creates a copy of the dashboard with options to:
    - Copy layout configuration
    - Copy dashboard settings
    - Copy global filters
    - Copy all charts/widgets

    The duplicated dashboard is always created as a personal dashboard.
    """
    try:
        UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format",
        )

    dashboard = await dashboard_service.duplicate_dashboard(
        db=db,
        dashboard_id=dashboard_id,
        user_id=str(current_user.id),
        duplicate_data=duplicate_data,
    )
    return _dashboard_to_response(dashboard)


# =============================================================================
# Dashboard Sharing Endpoints
# =============================================================================


@router.post(
    "/{dashboard_id}/share",
    response_model=list[DashboardMemberResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Share a dashboard with users",
)
async def share_dashboard(
    dashboard_id: str,
    share_request: DashboardShareRequest,
    db: DbSession,
    current_user: CurrentUser,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> list[DashboardMemberResponse]:
    """
    Share a dashboard with users.

    Only the dashboard creator can share.
    Cannot share personal dashboards.

    Permission levels:
    - **owner**: Full control including deletion
    - **edit**: Can modify dashboard and widgets
    - **view**: Read-only access
    """
    try:
        UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format",
        )

    members = await dashboard_service.share_dashboard(
        db=db,
        dashboard_id=dashboard_id,
        user_id=str(current_user.id),
        share_request=share_request,
    )
    return [
        DashboardMemberResponse(
            id=UUID(m.id),
            dashboard_id=UUID(m.dashboard_id),
            user_id=UUID(m.user_id),
            permission=m.permission_enum,
            shared_by_id=UUID(m.shared_by_id) if m.shared_by_id else None,
            shared_at=m.shared_at,
            created_at=m.created_at,
        )
        for m in members
    ]


@router.post(
    "/{dashboard_id}/unshare",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove dashboard access from users",
)
async def unshare_dashboard(
    dashboard_id: str,
    unshare_request: DashboardUnshareRequest,
    db: DbSession,
    current_user: CurrentUser,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> None:
    """
    Remove dashboard access from users.

    Only the dashboard creator can unshare.
    """
    try:
        UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format",
        )

    await dashboard_service.unshare_dashboard(
        db=db,
        dashboard_id=dashboard_id,
        user_id=str(current_user.id),
        unshare_request=unshare_request,
    )


@router.get(
    "/{dashboard_id}/members",
    response_model=list[DashboardMemberResponse],
    summary="List dashboard members",
)
async def get_dashboard_members(
    dashboard_id: str,
    db: DbSession,
    current_user: CurrentUser,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> list[DashboardMemberResponse]:
    """
    Get all members with access to a dashboard.

    Returns list of users and their permission levels.
    """
    try:
        UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format",
        )

    members = await dashboard_service.get_dashboard_members(
        db=db,
        dashboard_id=dashboard_id,
        user_id=str(current_user.id),
    )
    return [
        DashboardMemberResponse(
            id=UUID(m.id),
            dashboard_id=UUID(m.dashboard_id),
            user_id=UUID(m.user_id),
            permission=m.permission_enum,
            shared_by_id=UUID(m.shared_by_id) if m.shared_by_id else None,
            shared_at=m.shared_at,
            created_at=m.created_at,
        )
        for m in members
    ]


@router.patch(
    "/{dashboard_id}/permissions",
    response_model=DashboardMemberResponse,
    summary="Update dashboard member permissions",
)
async def update_member_permission(
    dashboard_id: str,
    permission_update: DashboardPermissionUpdate,
    db: DbSession,
    current_user: CurrentUser,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardMemberResponse:
    """
    Update a dashboard member's permission level.

    Only the dashboard creator can update permissions.
    """
    try:
        UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format",
        )

    member = await dashboard_service.update_member_permission(
        db=db,
        dashboard_id=dashboard_id,
        user_id=str(current_user.id),
        permission_update=permission_update,
    )
    return DashboardMemberResponse(
        id=UUID(member.id),
        dashboard_id=UUID(member.dashboard_id),
        user_id=UUID(member.user_id),
        permission=member.permission_enum,
        shared_by_id=UUID(member.shared_by_id) if member.shared_by_id else None,
        shared_at=member.shared_at,
        created_at=member.created_at,
    )


# =============================================================================
# Public Sharing Endpoints
# =============================================================================


@router.post(
    "/{dashboard_id}/share-token",
    response_model=dict[str, str],
    status_code=status.HTTP_201_CREATED,
    summary="Generate public share token",
)
async def generate_share_token(
    dashboard_id: str,
    db: DbSession,
    current_user: CurrentUser,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> dict[str, str]:
    """
    Generate a public share token for a dashboard.

    Only the dashboard creator can generate a share token.
    The token allows anyone with the link to view the dashboard.
    """
    try:
        UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format",
        )

    token = await dashboard_service.generate_share_token(
        db=db,
        dashboard_id=dashboard_id,
        user_id=str(current_user.id),
    )
    return {"share_token": token}


@router.delete(
    "/{dashboard_id}/share-token",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke public share token",
)
async def revoke_share_token(
    dashboard_id: str,
    db: DbSession,
    current_user: CurrentUser,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> None:
    """
    Revoke a dashboard's public share token.

    Only the dashboard creator can revoke a share token.
    """
    try:
        UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format",
        )

    await dashboard_service.revoke_share_token(
        db=db,
        dashboard_id=dashboard_id,
        user_id=str(current_user.id),
    )


@router.get(
    "/shared/{share_token}",
    response_model=DashboardResponse,
    summary="Get dashboard by share token",
)
async def get_dashboard_by_share_token(
    share_token: str,
    db: DbSession,
    dashboard_service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardResponse:
    """
    Get a dashboard using its public share token.

    No authentication required.
    Works only if the dashboard has a valid share token.
    """
    dashboard = await dashboard_service.get_dashboard_by_share_token(
        db=db,
        share_token=share_token,
    )
    return _dashboard_to_response(dashboard)
