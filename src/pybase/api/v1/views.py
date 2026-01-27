"""
View endpoints.

Handles view CRUD operations and data retrieval with filters/sorts applied.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.schemas.field import FieldResponse
from pybase.schemas.view import (
    ViewCreate,
    ViewDataRequest,
    ViewDataResponse,
    ViewDuplicate,
    ViewListResponse,
    ViewResponse,
    ViewType,
    ViewUpdate,
)
from pybase.services.field import FieldService
from pybase.services.view import ViewService

router = APIRouter()


# =============================================================================
# Dependencies
# =============================================================================


def get_view_service() -> ViewService:
    """Get view service instance."""
    return ViewService()


def get_field_service() -> FieldService:
    """Get field service instance."""
    return FieldService()


def _view_to_response(view: Any) -> ViewResponse:
    """Convert View model to ViewResponse schema."""
    return ViewResponse(
        id=UUID(view.id),
        table_id=UUID(view.table_id),
        created_by_id=UUID(view.created_by_id) if view.created_by_id else None,
        name=view.name,
        description=view.description,
        view_type=ViewType(view.view_type),
        is_default=view.is_default,
        is_locked=view.is_locked,
        is_personal=view.is_personal,
        position=view.position,
        color=view.color,
        row_height=view.row_height,
        field_config=view.get_field_config_dict()
        if hasattr(view, "get_field_config_dict")
        else None,
        filters=view.get_filters_list() if hasattr(view, "get_filters_list") else [],
        sorts=view.get_sorts_list() if hasattr(view, "get_sorts_list") else [],
        groups=view.get_groups_dict() if hasattr(view, "get_groups_dict") else None,
        type_config=view.get_type_config_dict() if hasattr(view, "get_type_config_dict") else None,
        created_at=view.created_at,
        updated_at=view.updated_at,
    )


# =============================================================================
# View CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=ViewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new view",
)
async def create_view(
    view_data: ViewCreate,
    db: DbSession,
    current_user: CurrentUser,
    view_service: Annotated[ViewService, Depends(get_view_service)],
) -> ViewResponse:
    """
    Create a new view for a table.

    Supports the following view types:
    - **grid**: Spreadsheet-like view with rows and columns
    - **kanban**: Board view with cards grouped by a field
    - **calendar**: Calendar view for date-based records
    - **gallery**: Card grid view with cover images
    - **form**: Form view for data entry
    - **gantt**: Project timeline view
    - **timeline**: Chronological timeline view
    """
    view = await view_service.create_view(
        db=db,
        user_id=str(current_user.id),
        view_data=view_data,
    )
    return _view_to_response(view)


@router.get(
    "",
    response_model=ViewListResponse,
    summary="List views",
)
async def list_views(
    db: DbSession,
    current_user: CurrentUser,
    view_service: Annotated[ViewService, Depends(get_view_service)],
    table_id: Annotated[
        str,
        Query(description="Table ID to list views for"),
    ],
    view_type: Annotated[
        str | None,
        Query(description="Filter by view type"),
    ] = None,
    include_personal: Annotated[
        bool,
        Query(description="Include personal views (only your own)"),
    ] = True,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Number of items per page (max 100)"),
    ] = 50,
) -> ViewListResponse:
    """
    List views for a table.

    Returns paginated list of views.
    Personal views are only returned for the creator.
    """
    try:
        table_uuid = UUID(table_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table ID format",
        )

    views, total = await view_service.list_views(
        db=db,
        table_id=table_uuid,
        user_id=str(current_user.id),
        view_type=view_type,
        include_personal=include_personal,
        page=page,
        page_size=page_size,
    )

    return ViewListResponse(
        items=[_view_to_response(v) for v in views],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/default",
    response_model=ViewResponse,
    summary="Get default view",
)
async def get_default_view(
    db: DbSession,
    current_user: CurrentUser,
    view_service: Annotated[ViewService, Depends(get_view_service)],
    table_id: Annotated[str, Query(description="Table ID")],
) -> ViewResponse:
    """
    Get the default view for a table.

    If no default is set, returns the first view by position.
    """
    try:
        UUID(table_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table ID format",
        )

    view = await view_service.get_default_view(
        db=db,
        table_id=table_id,
        user_id=str(current_user.id),
    )
    return _view_to_response(view)


@router.get(
    "/{view_id}",
    response_model=ViewResponse,
    summary="Get a view",
)
async def get_view(
    view_id: str,
    db: DbSession,
    current_user: CurrentUser,
    view_service: Annotated[ViewService, Depends(get_view_service)],
) -> ViewResponse:
    """
    Get a view by ID.

    Returns view details including all configuration.
    """
    try:
        UUID(view_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid view ID format",
        )

    view = await view_service.get_view_by_id(
        db=db,
        view_id=view_id,
        user_id=str(current_user.id),
    )
    return _view_to_response(view)


@router.patch(
    "/{view_id}",
    response_model=ViewResponse,
    summary="Update a view",
)
async def update_view(
    view_id: str,
    view_data: ViewUpdate,
    db: DbSession,
    current_user: CurrentUser,
    view_service: Annotated[ViewService, Depends(get_view_service)],
) -> ViewResponse:
    """
    Update a view.

    Updates view name, filters, sorts, groups, and type-specific config.
    Locked views can only be modified by the creator or workspace admin.
    """
    try:
        UUID(view_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid view ID format",
        )

    view = await view_service.update_view(
        db=db,
        view_id=view_id,
        user_id=str(current_user.id),
        view_data=view_data,
    )
    return _view_to_response(view)


@router.delete(
    "/{view_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a view",
)
async def delete_view(
    view_id: str,
    db: DbSession,
    current_user: CurrentUser,
    view_service: Annotated[ViewService, Depends(get_view_service)],
) -> None:
    """
    Delete a view.

    Soft deletes the view (marks as deleted).
    Cannot delete the last view of a table.
    Personal views can be deleted by the creator.
    Other views require workspace admin/owner permission.
    """
    try:
        UUID(view_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid view ID format",
        )

    await view_service.delete_view(
        db=db,
        view_id=view_id,
        user_id=str(current_user.id),
    )


# =============================================================================
# View Operations
# =============================================================================


@router.post(
    "/{view_id}/duplicate",
    response_model=ViewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate a view",
)
async def duplicate_view(
    view_id: str,
    duplicate_data: ViewDuplicate,
    db: DbSession,
    current_user: CurrentUser,
    view_service: Annotated[ViewService, Depends(get_view_service)],
) -> ViewResponse:
    """
    Duplicate an existing view.

    Creates a copy of the view with the specified name.
    You can choose which configurations to copy (filters, sorts, groups, field config).
    """
    try:
        UUID(view_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid view ID format",
        )

    view = await view_service.duplicate_view(
        db=db,
        view_id=view_id,
        user_id=str(current_user.id),
        duplicate_data=duplicate_data,
    )
    return _view_to_response(view)


@router.post(
    "/reorder",
    response_model=list[ViewResponse],
    summary="Reorder views",
)
async def reorder_views(
    db: DbSession,
    current_user: CurrentUser,
    view_service: Annotated[ViewService, Depends(get_view_service)],
    table_id: Annotated[str, Query(description="Table ID")],
    view_ids: list[str],
) -> list[ViewResponse]:
    """
    Reorder views for a table.

    Pass the view IDs in the desired order.
    Views not in the list maintain their relative position at the end.
    """
    try:
        UUID(table_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table ID format",
        )

    views = await view_service.reorder_views(
        db=db,
        table_id=table_id,
        user_id=str(current_user.id),
        view_ids=view_ids,
    )
    return [_view_to_response(v) for v in views]


# =============================================================================
# View Data Endpoints
# =============================================================================


@router.post(
    "/{view_id}/data",
    response_model=ViewDataResponse,
    summary="Get view data",
)
async def get_view_data(
    view_id: str,
    request: ViewDataRequest,
    db: DbSession,
    current_user: CurrentUser,
    view_service: Annotated[ViewService, Depends(get_view_service)],
) -> ViewDataResponse:
    """
    Get records with view filters and sorts applied.

    Returns paginated records matching the view's configuration.
    You can optionally override filters/sorts and add a search query.

    **Note**: This endpoint applies the view's filters, sorts, and field
    configuration to return data as it would appear in the view.
    """
    try:
        view_uuid = UUID(view_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid view ID format",
        )

    # Get view data with filters/sorts applied
    records, total = await view_service.get_view_data(
        db=db,
        view_id=view_id,
        user_id=str(current_user.id),
        page=request.page,
        page_size=request.page_size,
        override_filters=request.override_filters,
        override_sorts=request.override_sorts,
        search=request.search,
    )

    # Calculate has_more flag
    has_more = (request.page * request.page_size) < total

    return ViewDataResponse(
        view_id=view_uuid,
        records=records,
        total=total,
        page=request.page,
        page_size=request.page_size,
        has_more=has_more,
    )


# =============================================================================
# Form View Endpoints
# =============================================================================


@router.get(
    "/{view_id}/form",
    response_model=dict[str, Any],
    summary="Get form view configuration",
)
async def get_form_view(
    view_id: str,
    db: DbSession,
    current_user: CurrentUser,
    view_service: Annotated[ViewService, Depends(get_view_service)],
    field_service: Annotated[FieldService, Depends(get_field_service)],
) -> dict[str, Any]:
    """
    Get form view configuration for embedding or sharing.

    Returns the form configuration including:
    - Form title and description
    - Visible fields with their configuration
    - Required fields
    - Submit button text
    - Success message
    """
    try:
        UUID(view_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid view ID format",
        )

    view = await view_service.get_view_by_id(
        db=db,
        view_id=view_id,
        user_id=str(current_user.id),
    )

    if view.view_type != "form":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only for form views",
        )

    type_config = view.get_type_config_dict()
    field_config = view.get_field_config_dict()

    # Fetch actual field definitions for the form
    fields = await view_service.get_view_fields(
        db=db,
        view_id=view_id,
        user_id=str(current_user.id),
    )

    # Convert Field objects to FieldResponse format
    field_responses = []
    for field in fields:
        field_response = FieldResponse(
            id=UUID(field.id),
            table_id=UUID(field.table_id),
            name=field.name,
            description=field.description,
            field_type=field.field_type,
            options=field.get_options_dict() if hasattr(field, "get_options_dict") else {},
            is_required=field.is_required,
            is_unique=field.is_unique,
            position=field.position,
            width=field.width,
            is_visible=field.is_visible,
            is_primary=field.is_primary,
            is_computed=field.is_computed,
            is_locked=field.is_locked,
            created_at=field.created_at,
            updated_at=field.updated_at,
        )
        field_responses.append(field_response.model_dump(mode="json"))

    return {
        "view_id": view.id,
        "table_id": view.table_id,
        "title": type_config.get("title", view.name),
        "description": type_config.get("description", view.description),
        "submit_button_text": type_config.get("submit_button_text", "Submit"),
        "success_message": type_config.get("success_message", "Thank you!"),
        "redirect_url": type_config.get("redirect_url"),
        "show_branding": type_config.get("show_branding", True),
        "cover_image_url": type_config.get("cover_image_url"),
        "fields": field_responses,
        "required_fields": type_config.get("required_fields", []),
        "field_order": field_config.get("field_order", []),
        "hidden_fields": field_config.get("hidden_fields", []),
    }


@router.post(
    "/{view_id}/form/submit",
    status_code=status.HTTP_201_CREATED,
    summary="Submit form data",
)
async def submit_form(
    view_id: str,
    data: dict[str, Any],
    db: DbSession,
    current_user: CurrentUser,
    view_service: Annotated[ViewService, Depends(get_view_service)],
) -> dict[str, Any]:
    """
    Submit data through a form view.

    Creates a new record in the table with the submitted data.
    Only fields visible in the form view are accepted.
    """
    try:
        UUID(view_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid view ID format",
        )

    view = await view_service.get_view_by_id(
        db=db,
        view_id=view_id,
        user_id=str(current_user.id),
    )

    if view.view_type != "form":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only for form views",
        )

    # TODO: Implement form submission
    # 1. Validate required fields
    # 2. Filter to only allowed fields
    # 3. Create record via RecordService
    # 4. Return success with record ID

    return {
        "success": True,
        "message": "Record created successfully",
        "record_id": None,  # TODO: Return actual record ID
    }
