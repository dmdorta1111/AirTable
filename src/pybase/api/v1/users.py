"""
User management endpoints.

Handles user profile updates, API key management, etc.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from pybase.api.deps import CurrentUser, CurrentSuperuser, DbSession
from pybase.core.security import generate_api_key, hash_api_key
from pybase.models.user import APIKey, User

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class UpdateProfileRequest(BaseModel):
    """Update user profile request."""

    name: str | None = Field(None, min_length=1, max_length=255)
    avatar_url: str | None = None


class UserResponse(BaseModel):
    """User information response."""

    id: str
    email: str
    name: str
    avatar_url: str | None
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    last_login_at: datetime | None

    class Config:
        from_attributes = True


class CreateAPIKeyRequest(BaseModel):
    """Create API key request."""

    name: str = Field(..., min_length=1, max_length=255)
    expires_at: datetime | None = None
    scopes: list[str] | None = None


class APIKeyResponse(BaseModel):
    """API key response (without full key)."""

    id: str
    name: str
    key_prefix: str
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyCreatedResponse(APIKeyResponse):
    """API key response with full key (only shown once)."""

    key: str  # Full API key, only shown on creation


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: CurrentUser,
) -> User:
    """
    Get current user's profile.
    """
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    request: UpdateProfileRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> User:
    """
    Update current user's profile.
    """
    if request.name is not None:
        current_user.name = request.name

    if request.avatar_url is not None:
        current_user.avatar_url = request.avatar_url

    await db.commit()
    await db.refresh(current_user)

    return current_user


# =============================================================================
# API Key Management
# =============================================================================


@router.get("/me/api-keys", response_model=list[APIKeyResponse])
async def list_my_api_keys(
    current_user: CurrentUser,
    db: DbSession,
) -> list[APIKey]:
    """
    List current user's API keys.
    """
    result = await db.execute(
        select(APIKey)
        .where(
            APIKey.user_id == current_user.id,
        )
        .order_by(APIKey.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/me/api-keys", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED
)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Create a new API key.

    The full API key is only shown once in the response.
    Store it securely - it cannot be retrieved again.
    """
    # Generate new API key
    full_key = generate_api_key()
    key_prefix = full_key[:12]  # Store prefix for identification

    # Create API key record
    api_key = APIKey(
        user_id=current_user.id,
        name=request.name,
        key_prefix=key_prefix,
        hashed_key=hash_api_key(full_key),
        expires_at=request.expires_at,
        scopes=str(request.scopes) if request.scopes else "[]",
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    # Return with full key (only time it's shown)
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key_prefix": api_key.key_prefix,
        "key": full_key,  # Only shown once!
        "is_active": api_key.is_active,
        "expires_at": api_key.expires_at,
        "last_used_at": api_key.last_used_at,
        "created_at": api_key.created_at,
    }


@router.delete("/me/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """
    Delete an API key.
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await db.delete(api_key)
    await db.commit()


@router.patch("/me/api-keys/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    current_user: CurrentUser,
    db: DbSession,
    name: str | None = None,
    is_active: bool | None = None,
) -> APIKey:
    """
    Update an API key (name or active status).
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    if name is not None:
        api_key.name = name

    if is_active is not None:
        api_key.is_active = is_active

    await db.commit()
    await db.refresh(api_key)

    return api_key


# =============================================================================
# Admin Endpoints (Superuser only)
# =============================================================================


@router.get("/", response_model=list[UserResponse])
async def list_users(
    current_user: CurrentSuperuser,
    db: DbSession,
    skip: int = 0,
    limit: int = 100,
) -> list[User]:
    """
    List all users (superuser only).
    """
    result = await db.execute(
        select(User)
        .where(User.deleted_at == None)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> User:
    """
    Get a specific user (superuser only).
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at == None,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.patch("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: str,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> User:
    """
    Deactivate a user (superuser only).
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at == None,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = False
    await db.commit()
    await db.refresh(user)

    return user


@router.patch("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: str,
    current_user: CurrentSuperuser,
    db: DbSession,
) -> User:
    """
    Activate a user (superuser only).
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.deleted_at == None,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = True
    await db.commit()
    await db.refresh(user)

    return user
