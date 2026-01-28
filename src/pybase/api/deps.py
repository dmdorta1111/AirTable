"""
FastAPI dependency injection functions.

Provides reusable dependencies for authentication, database sessions, etc.
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    AuthenticationError,
    InvalidAPIKeyError,
    InvalidTokenError,
    TokenExpiredError,
    UserNotFoundError,
)
from pybase.core.security import verify_api_key, verify_token
from pybase.db.session import get_db
from pybase.models.user import APIKey, User


# HTTP Bearer token security scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        db: Database session
        credentials: HTTP Bearer credentials

    Returns:
        Authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify JWT token
    payload = await verify_token(credentials.credentials, token_type="access")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
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
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User | None:
    """
    Get the current user if authenticated, otherwise None.

    Useful for endpoints that work with or without authentication.
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(db, credentials)
    except HTTPException:
        return None


async def get_current_active_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get the current user if they are a superuser.

    Args:
        current_user: Current authenticated user

    Returns:
        User if superuser

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )
    return current_user


async def get_user_from_api_key(
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> User | None:
    """
    Get user from API key header.

    Args:
        db: Database session
        x_api_key: API key from header

    Returns:
        User if valid API key, None otherwise
    """
    if x_api_key is None:
        return None

    # Extract prefix for lookup
    prefix = x_api_key[:12] if len(x_api_key) > 12 else x_api_key

    # Find API key by prefix
    result = await db.execute(
        select(APIKey).where(
            APIKey.key_prefix == prefix,
            APIKey.is_active == True,
        )
    )
    api_key = result.scalar_one_or_none()

    if api_key is None:
        return None

    # Verify the full key
    if not verify_api_key(x_api_key, api_key.hashed_key):
        return None

    # Check expiration
    if api_key.is_expired:
        return None

    # Get the user
    result = await db.execute(
        select(User).where(
            User.id == api_key.user_id,
            User.is_active == True,
            User.deleted_at == None,
        )
    )
    user = result.scalar_one_or_none()

    if user:
        # Update API key usage
        api_key.update_usage()
        await db.commit()

    return user


async def get_current_user_or_api_key(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    x_api_key: Annotated[str | None, Header()] = None,
) -> User:
    """
    Get current user from either JWT token or API key.

    Tries JWT first, then falls back to API key.

    Args:
        db: Database session
        credentials: HTTP Bearer credentials
        x_api_key: API key from header

    Returns:
        Authenticated user

    Raises:
        HTTPException: If no valid authentication provided
    """
    # Try JWT token first
    if credentials is not None:
        try:
            return await get_current_user(db, credentials)
        except HTTPException:
            pass

    # Try API key
    if x_api_key is not None:
        user = await get_user_from_api_key(db, x_api_key)
        if user is not None:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide Bearer token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]
CurrentSuperuser = Annotated[User, Depends(get_current_active_superuser)]
CurrentUserOrAPIKey = Annotated[User, Depends(get_current_user_or_api_key)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
