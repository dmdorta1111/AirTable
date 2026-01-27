"""
Authentication endpoints.

Handles user registration, login, token refresh, and password reset.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.config import settings
from pybase.core.security import (
    create_token_pair,
    hash_password,
    validate_password_strength,
    verify_password,
    verify_token,
)
from pybase.models.user import User

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Authentication token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class UserResponse(BaseModel):
    """User information response."""

    id: str
    email: str
    name: str | None
    avatar_url: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Auth response with user and tokens (for register/login)."""

    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    current_password: str
    new_password: str = Field(..., min_length=8)


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: DbSession,
) -> AuthResponse:
    """
    Register a new user and return auth tokens.

    Creates a new user account with the provided email and password,
    then automatically logs them in.
    """
    # Check if registration is enabled
    if not settings.enable_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User registration is disabled",
        )

    # Check SSO-only mode enforcement
    if settings.sso_only_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSO-only mode is enabled. Please use single sign-on to login.",
        )

    # Validate password strength
    is_valid, errors = validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password too weak", "errors": errors},
        )

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email.lower()))
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create new user
    user = User(
        email=request.email.lower(),
        hashed_password=hash_password(request.password),
        name=request.name or request.email.split("@")[0],  # Default name from email
        is_active=True,
        is_verified=False,  # Require email verification in production
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate tokens (auto-login)
    token_pair = create_token_pair(user.id)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    db: DbSession,
) -> AuthResponse:
    """
    Authenticate user and return tokens with user info.

    Validates email/password and returns access and refresh tokens.
    """
    # Check SSO-only mode enforcement
    if settings.sso_only_mode:
        # Check if this is the admin recovery account
        admin_recovery_email = settings.sso_admin_recovery_email
        is_admin_recovery = (
            admin_recovery_email
            and request.email.lower() == admin_recovery_email.lower()
        )

        # If not admin recovery, deny local login
        if not is_admin_recovery:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SSO-only mode is enabled. Please use single sign-on to login.",
            )

    # Find user by email
    result = await db.execute(
        select(User).where(
            User.email == request.email.lower(),
            User.deleted_at == None,
        )
    )
    user = result.scalar_one_or_none()

    # Verify user exists and password is correct
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )

    # Update last login
    user.update_last_login()
    await db.commit()

    # Generate tokens
    token_pair = create_token_pair(user.id)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: DbSession,
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Validates the refresh token and returns new token pair.
    """
    # Verify refresh token
    payload = verify_token(request.refresh_token, token_type="refresh")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Verify user still exists and is active
    result = await db.execute(
        select(User).where(
            User.id == payload.sub,
            User.is_active == True,
            User.deleted_at == None,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Generate new tokens
    token_pair = create_token_pair(user.id)

    return TokenResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: CurrentUser,
) -> User:
    """
    Get current authenticated user's information.
    """
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """
    Change current user's password.

    Requires current password for verification.
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password strength
    is_valid, errors = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "New password too weak", "errors": errors},
        )

    # Update password
    current_user.hashed_password = hash_password(request.new_password)
    await db.commit()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: CurrentUser,
) -> None:
    """
    Logout current user.

    Note: JWT tokens are stateless, so this endpoint is primarily
    for client-side token cleanup. For true token invalidation,
    implement a token blacklist using Redis.
    """
    # In a production system, you would:
    # 1. Add the token to a blacklist in Redis
    # 2. Set TTL to token expiration time
    # For now, this is a no-op; client should discard tokens
    pass
