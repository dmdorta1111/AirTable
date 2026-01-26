"""
Comment endpoints.

Handles comment CRUD operations on records.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.models.comment import Comment
from pybase.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
)
from pybase.schemas.comment import (
    CommentCreate,
    CommentListResponse,
    CommentResponse,
    CommentUpdate,
)
from pybase.services.comment import CommentService

router = APIRouter()

# =============================================================================
# Dependencies
# =============================================================================


def get_comment_service() -> CommentService:
    """Get comment service instance."""
    return CommentService()


def validate_comment_id(comment_id: Annotated[str, Path(description="Comment UUID")]) -> str:
    """Validate comment_id is a valid UUID format.

    Args:
        comment_id: The comment ID from the path parameter.

    Returns:
        The validated comment ID string.

    Raises:
        HTTPException: If the comment ID is not a valid UUID format.
    """
    try:
        UUID(comment_id)
        return comment_id
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid comment ID format",
        )


def comment_to_response(comment: Comment) -> CommentResponse:
    """Convert Comment model to CommentResponse schema."""
    return CommentResponse(
        id=str(comment.id),
        record_id=str(comment.record_id),
        user_id=str(comment.user_id),
        content=comment.content,
        is_edited=comment.is_edited,
        edited_at=comment.edited_at,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


# =============================================================================
# Comment CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    comment_data: CommentCreate,
    db: DbSession,
    current_user: CurrentUser,
    comment_service: Annotated[CommentService, Depends(get_comment_service)],
) -> CommentResponse:
    """
    Create a new comment on a record.

    Creates a new comment on specified record.
    User must have access to record's workspace.
    """
    try:
        comment = await comment_service.create_comment(
            db=db,
            user_id=str(current_user.id),
            comment_data=comment_data,
        )
        return comment_to_response(comment)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get("", response_model=CommentListResponse)
async def list_comments(
    db: DbSession,
    current_user: CurrentUser,
    comment_service: Annotated[CommentService, Depends(get_comment_service)],
    record_id: Annotated[
        str | None,
        Query(
            description="Record ID to filter comments by (optional)",
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
) -> CommentListResponse:
    """
    List comments accessible to current user.

    Returns paginated list of comments.
    Can filter by record_id.
    """
    from uuid import UUID

    record_uuid: UUID | None = None
    if record_id:
        try:
            record_uuid = UUID(record_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid record ID format",
            )

    comments, total = await comment_service.list_comments(
        db=db,
        record_id=record_uuid,
        user_id=str(current_user.id),
        page=page,
        page_size=page_size,
    )

    return CommentListResponse(
        items=[comment_to_response(c) for c in comments],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{comment_id}", response_model=CommentResponse)
async def get_comment(
    comment_id: Annotated[str, Depends(validate_comment_id)],
    db: DbSession,
    current_user: CurrentUser,
    comment_service: Annotated[CommentService, Depends(get_comment_service)],
) -> CommentResponse:
    """
    Get a comment by ID.

    Returns comment details.
    Requires user to have access to comment's record workspace.
    """
    try:
        comment = await comment_service.get_comment_by_id(
            db=db,
            comment_id=comment_id,
            user_id=str(current_user.id),
        )
        return comment_to_response(comment)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.patch("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: Annotated[str, Depends(validate_comment_id)],
    comment_data: CommentUpdate,
    db: DbSession,
    current_user: CurrentUser,
    comment_service: Annotated[CommentService, Depends(get_comment_service)],
) -> CommentResponse:
    """
    Update a comment.

    Updates comment content.
    Requires user to be comment author or workspace admin/owner.
    """
    try:
        comment = await comment_service.update_comment(
            db=db,
            comment_id=comment_id,
            user_id=str(current_user.id),
            comment_data=comment_data,
        )
        return comment_to_response(comment)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: Annotated[str, Depends(validate_comment_id)],
    db: DbSession,
    current_user: CurrentUser,
    comment_service: Annotated[CommentService, Depends(get_comment_service)],
) -> None:
    """
    Delete a comment (soft delete).

    Soft deletes the comment.
    Requires user to be comment author or workspace admin/owner.
    """
    try:
        await comment_service.delete_comment(
            db=db,
            comment_id=comment_id,
            user_id=str(current_user.id),
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
