"""
Authentication endpoints.

Handles user registration, login, token refresh, and password reset.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
from pybase.models.audit_log import AuditAction
from pybase.models.user import User
from pybase.services.audit_service import AuditService

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
    request_obj: RegisterRequest,
    db: DbSession,
    request: Request,
) -> AuthResponse:
    """
    Register a new user and return auth tokens.

    Creates a new user account with the provided email and password,
    then automatically logs them in.
    """
    # Extract request context for audit logging
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    request_id = getattr(request.state, "request_id", None)

    # Check if registration is enabled
    if not settings.enable_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User registration is disabled",
        )

    # Validate password strength
    is_valid, errors = validate_password_strength(request_obj.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password too weak", "errors": errors},
        )

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request_obj.email.lower()))
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create new user
    user = User(
        email=request_obj.email.lower(),
        hashed_password=hash_password(request_obj.password),
        name=request_obj.name or request_obj.email.split("@")[0],  # Default name from email
        is_active=True,
        is_verified=False,  # Require email verification in production
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate tokens (auto-login)
    token_pair = create_token_pair(user.id)

    # Log user registration and auto-login
    audit_service = AuditService()
    await audit_service.log_action(
        db=db,
        action="user.register",
        resource_type="user",
        user_id=user.id,
        user_email=user.email,
        resource_id=str(user.id),
        new_value={"email": user.email, "name": user.name},
        ip_address=client_ip,
        user_agent=user_agent,
        request_id=request_id,
    )

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
        expires_in=token_pair.expires_in,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request_obj: LoginRequest,
    db: DbSession,
    request: Request,
) -> AuthResponse:
    """
    Authenticate user and return tokens with user info.

    Validates email/password and returns access and refresh tokens.
    """
    # Extract request context for audit logging
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    request_id = getattr(request.state, "request_id", None)

    # Find user by email
    result = await db.execute(
        select(User).where(
            User.email == request_obj.email.lower(),
            User.deleted_at == None,
        )
    )
    user = result.scalar_one_or_none()

    # Verify user exists and password is correct
    if user is None or not verify_password(request_obj.password, user.hashed_password):
        # Log failed login attempt
        audit_service = AuditService()
        await audit_service.log_action(
            db=db,
            action=AuditAction.USER_LOGIN_FAILED,
            resource_type="user",
            user_id=user.id if user else None,
            user_email=user.email if user else request_obj.email.lower(),
            ip_address=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            meta={"email": request_obj.email.lower()},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if user is active
    if not user.is_active:
        # Log failed login attempt for inactive account
        audit_service = AuditService()
        await audit_service.log_action(
            db=db,
            action=AuditAction.USER_LOGIN_FAILED,
            resource_type="user",
            user_id=user.id,
            user_email=user.email,
            ip_address=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            meta={"reason": "account_deactivated", "email": user.email},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )

    # Update last login
    user.update_last_login()
    await db.commit()

    # Generate tokens
    token_pair = create_token_pair(user.id)

    # Log successful login
    audit_service = AuditService()
    await audit_service.log_action(
        db=db,
        action=AuditAction.USER_LOGIN,
        resource_type="user",
        user_id=user.id,
        user_email=user.email,
        resource_id=str(user.id),
        ip_address=client_ip,
        user_agent=user_agent,
        request_id=request_id,
        meta={"email": user.email},
    )

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
    request_obj: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DbSession,
    request: Request,
) -> None:
    """
    Change current user's password.

    Requires current password for verification.
    """
    # Extract request context for audit logging
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    request_id = getattr(request.state, "request_id", None)

    # Verify current password
    if not verify_password(request_obj.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password strength
    is_valid, errors = validate_password_strength(request_obj.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "New password too weak", "errors": errors},
        )

    # Update password
    current_user.hashed_password = hash_password(request_obj.new_password)
    await db.commit()

    # Log password change
    audit_service = AuditService()
    await audit_service.log_action(
        db=db,
        action=AuditAction.USER_PASSWORD_CHANGED,
        resource_type="user",
        user_id=current_user.id,
        user_email=current_user.email,
        resource_id=str(current_user.id),
        ip_address=client_ip,
        user_agent=user_agent,
        request_id=request_id,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: CurrentUser,
    request: Request,
    db: DbSession,
) -> None:
    """
    Logout current user.

    Note: JWT tokens are stateless, so this endpoint is primarily
    for client-side token cleanup. For true token invalidation,
    implement a token blacklist using Redis.
    """
    # Extract request context for audit logging
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    request_id = getattr(request.state, "request_id", None)

    # Log logout event
    audit_service = AuditService()
    await audit_service.log_action(
        db=db,
        action=AuditAction.USER_LOGOUT,
        resource_type="user",
        user_id=current_user.id,
        user_email=current_user.email,
        resource_id=str(current_user.id),
        ip_address=client_ip,
        user_agent=user_agent,
        request_id=request_id,
    )

    # In a production system, you would:
    # 1. Add the token to a blacklist in Redis
    # 2. Set TTL to token expiration time
    # For now, this is a no-op; client should discard tokens
    pass
