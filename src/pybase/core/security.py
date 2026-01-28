"""
Security utilities for PyBase.

Provides JWT token handling, password hashing, and API key generation.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from pybase.core.config import settings
from pybase.core.session_store import RedisSessionStore


# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"


class TokenPayload(BaseModel):
    """JWT token payload model."""

    sub: str  # Subject (user ID)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at time
    type: str  # Token type: "access" or "refresh"
    jti: str | None = None  # JWT ID (for token revocation)


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until access token expires


# =============================================================================
# Password Hashing
# =============================================================================


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to check against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password meets strength requirements.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors: list[str] = []

    if len(password) < settings.password_min_length:
        errors.append(f"Password must be at least {settings.password_min_length} characters")

    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")

    return len(errors) == 0, errors


# =============================================================================
# JWT Token Handling
# =============================================================================


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: Token subject (usually user ID)
        expires_delta: Custom expiration time
        extra_claims: Additional claims to include

    Returns:
        Encoded JWT token
    """
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "access",
        "jti": secrets.token_urlsafe(16),
    }

    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: Token subject (usually user ID)
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT token
    """
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.refresh_token_expire_days)

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
    }

    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def create_token_pair(subject: str) -> TokenPair:
    """
    Create an access and refresh token pair.

    Args:
        subject: Token subject (usually user ID)

    Returns:
        TokenPair with both tokens
    """
    return TokenPair(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
        expires_in=settings.access_token_expire_minutes * 60,
    )


def decode_token(token: str) -> TokenPayload | None:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token to decode

    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return TokenPayload(
            sub=payload["sub"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
            type=payload.get("type", "access"),
            jti=payload.get("jti"),
        )
    except JWTError:
        return None


async def verify_token(token: str, token_type: str = "access") -> TokenPayload | None:
    """
    Verify a JWT token is valid and of the expected type.

    Checks:
    - Token signature and expiration
    - Token type matches expected type
    - Token is not blacklisted in Redis session store

    Args:
        token: JWT token to verify
        token_type: Expected token type ("access" or "refresh")

    Returns:
        TokenPayload if valid, None otherwise
    """
    payload = decode_token(token)

    if payload is None:
        return None

    # Check token type
    if payload.type != token_type:
        return None

    # Check expiration
    if payload.exp < datetime.now(timezone.utc):
        return None

    # Check if token is blacklisted
    if payload.jti:
        session_store = RedisSessionStore()
        try:
            is_blacklisted = await session_store.is_token_blacklisted(payload.jti)
            if is_blacklisted:
                return None
        except Exception:
            # If Redis check fails, allow token (fail open)
            # This prevents authentication issues during Redis unavailability
            pass

    return payload


# =============================================================================
# API Key Generation
# =============================================================================


def generate_api_key() -> str:
    """
    Generate a new API key.

    API keys are prefixed for easy identification and use URL-safe characters.

    Returns:
        Generated API key
    """
    key = secrets.token_urlsafe(32)
    return f"{settings.api_key_prefix}{key}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage.

    Args:
        api_key: API key to hash

    Returns:
        Hashed API key
    """
    return pwd_context.hash(api_key)


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash.

    Args:
        api_key: API key to verify
        hashed_key: Hashed key to check against

    Returns:
        True if key matches, False otherwise
    """
    return pwd_context.verify(api_key, hashed_key)


# =============================================================================
# Utility Functions
# =============================================================================


def generate_random_string(length: int = 32) -> str:
    """
    Generate a random URL-safe string.

    Args:
        length: Approximate length of the string

    Returns:
        Random string
    """
    return secrets.token_urlsafe(length)


def generate_verification_token() -> str:
    """
    Generate a token for email verification or password reset.

    Returns:
        Verification token
    """
    return secrets.token_urlsafe(32)
