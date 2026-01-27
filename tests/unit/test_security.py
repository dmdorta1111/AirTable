"""Unit tests for security module with session blacklist checking."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import jwt

from pybase.core.config import settings
from pybase.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from pybase.core.session_store import RedisSessionStore


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def sample_token_payload(sample_user_id):
    """Sample JWT payload for testing."""
    return {
        "sub": sample_user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "jti": "test-jti-123",
    }


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing produces a hash."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert hashed != password
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False


class TestTokenCreation:
    """Tests for JWT token creation."""

    def test_create_access_token(self, sample_user_id):
        """Test access token creation."""
        token = create_access_token(sample_user_id)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token structure
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )
        assert payload["sub"] == sample_user_id
        assert payload["type"] == "access"
        assert "jti" in payload

    def test_create_access_token_custom_expiration(self, sample_user_id):
        """Test access token creation with custom expiration."""
        expires = timedelta(minutes=60)
        token = create_access_token(sample_user_id, expires_delta=expires)

        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )

        # Check expiration is approximately 60 minutes from now
        exp_datetime = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = (exp_datetime - now).total_seconds()

        assert 3500 < time_diff < 3700  # ~60 minutes in seconds

    def test_create_access_token_extra_claims(self, sample_user_id):
        """Test access token creation with extra claims."""
        extra_claims = {"role": "admin", "permissions": ["read", "write"]}
        token = create_access_token(sample_user_id, extra_claims=extra_claims)

        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )

        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]

    def test_create_refresh_token(self, sample_user_id):
        """Test refresh token creation."""
        token = create_refresh_token(sample_user_id)

        assert isinstance(token, str)

        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )
        assert payload["sub"] == sample_user_id
        assert payload["type"] == "refresh"
        assert "jti" in payload


class TestTokenVerification:
    """Tests for JWT token verification with blacklist checking."""

    @pytest.mark.asyncio
    async def test_verify_valid_access_token(self, sample_user_id):
        """Test verification of valid access token."""
        token = create_access_token(sample_user_id)
        payload = await verify_token(token, token_type="access")

        assert payload is not None
        assert payload.sub == sample_user_id
        assert payload.type == "access"

    @pytest.mark.asyncio
    async def test_verify_valid_refresh_token(self, sample_user_id):
        """Test verification of valid refresh token."""
        token = create_refresh_token(sample_user_id)
        payload = await verify_token(token, token_type="refresh")

        assert payload is not None
        assert payload.sub == sample_user_id
        assert payload.type == "refresh"

    @pytest.mark.asyncio
    async def test_verify_token_wrong_type(self, sample_user_id):
        """Test verification fails when token type doesn't match."""
        access_token = create_access_token(sample_user_id)
        payload = await verify_token(access_token, token_type="refresh")

        assert payload is None

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.string"
        payload = await verify_token(invalid_token)

        assert payload is None

    @pytest.mark.asyncio
    async def test_verify_token_blacklisted(self, sample_user_id):
        """Test verification of blacklisted token."""
        token = create_access_token(sample_user_id)

        # Decode to get JTI
        unverified_payload = jwt.get_unverified_claims(token)
        token_jti = unverified_payload["jti"]
        exp_datetime = datetime.fromtimestamp(
            unverified_payload["exp"],
            tz=timezone.utc,
        )

        # Mock RedisSessionStore to return token as blacklisted
        with patch.object(
            RedisSessionStore,
            "is_token_blacklisted",
            return_value=AsyncMock(return_value=True),
        ) as mock_blacklist:
            mock_blacklist.return_value = True

            session_store = RedisSessionStore()
            with patch.object(
                RedisSessionStore,
                "__new__",
                return_value=session_store,
            ):
                payload = await verify_token(token, token_type="access")

                # Should return None because token is blacklisted
                assert payload is None

    @pytest.mark.asyncio
    async def test_verify_token_not_blacklisted(self, sample_user_id):
        """Test verification of non-blacklisted token."""
        token = create_access_token(sample_user_id)

        # Mock RedisSessionStore to return token as not blacklisted
        with patch.object(
            RedisSessionStore,
            "is_token_blacklisted",
            return_value=AsyncMock(return_value=False),
        ) as mock_blacklist:
            mock_blacklist.return_value = False

            session_store = RedisSessionStore()
            with patch.object(
                RedisSessionStore,
                "__new__",
                return_value=session_store,
            ):
                payload = await verify_token(token, token_type="access")

                # Should return valid payload
                assert payload is not None
                assert payload.sub == sample_user_id

    @pytest.mark.asyncio
    async def test_verify_token_redis_unavailable(self, sample_user_id):
        """Test verification fails open when Redis is unavailable."""
        token = create_access_token(sample_user_id)

        # Mock RedisSessionStore to raise exception
        async def mock_error(*args, **kwargs):
            raise Exception("Redis unavailable")

        with patch.object(
            RedisSessionStore,
            "is_token_blacklisted",
            new=mock_error,
        ):
            # Should still allow token (fail open)
            payload = await verify_token(token, token_type="access")

            assert payload is not None
            assert payload.sub == sample_user_id

    @pytest.mark.asyncio
    async def test_verify_token_without_jti(self, sample_user_id):
        """Test verification of token without JTI (old format)."""
        # Create a token manually without JTI
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=30)

        to_encode = {
            "sub": str(sample_user_id),
            "exp": expire,
            "iat": now,
            "type": "access",
        }

        token = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")

        # Should verify successfully (skip blacklist check for tokens without JTI)
        payload = await verify_token(token, token_type="access")

        assert payload is not None
        assert payload.sub == sample_user_id

    @pytest.mark.asyncio
    async def test_verify_token_expired(self, sample_user_id):
        """Test verification of expired token."""
        # Create an expired token
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        expire = now - timedelta(minutes=30)  # Expired 30 minutes ago

        to_encode = {
            "sub": str(sample_user_id),
            "exp": expire,
            "iat": now,
            "type": "access",
            "jti": "test-jti-expired",
        }

        token = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")

        payload = await verify_token(token, token_type="access")

        # Should return None because token is expired
        assert payload is None


class TestTokenBlacklistIntegration:
    """Integration tests for token blacklist with Redis."""

    @pytest.mark.asyncio
    async def test_blacklist_and_verify_token(self, sample_user_id):
        """Test that blacklisted tokens fail verification."""
        token = create_access_token(sample_user_id)

        # Decode to get JTI and expiration
        unverified_payload = jwt.get_unverified_claims(token)
        token_jti = unverified_payload["jti"]
        exp_datetime = datetime.fromtimestamp(
            unverified_payload["exp"],
            tz=timezone.utc,
        )

        # Blacklist the token
        session_store = RedisSessionStore()
        success = await session_store.blacklist_token(
            token_jti=token_jti,
            expires_at=exp_datetime,
            user_id=sample_user_id,
            reason="test",
        )

        assert success is True

        # Verify token is now rejected
        payload = await verify_token(token, token_type="access")
        assert payload is None

        # Clean up
        await session_store.close()
