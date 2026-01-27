"""Redis session storage for JWT blacklists and user sessions."""

import json
from datetime import datetime, timedelta
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from pybase.core.config import settings
from pybase.core.logging import get_logger

logger = get_logger(__name__)


class RedisSessionStore:
    """Redis-based session store for JWT blacklists and user sessions.

    Enables stateless API instances by storing session data in Redis,
    supporting horizontal scaling with multiple API instances behind a load balancer.

    Features:
    - JWT token blacklist for logout and token invalidation
    - User session tracking with metadata
    - Automatic TTL-based expiration
    - Cross-instance session consistency

    Default TTLs:
    - Blacklisted tokens: Token expiration time (typically 30 minutes)
    - User sessions: 24 hours
    """

    # Redis key prefixes
    BLACKLIST_PREFIX = "session:blacklist"
    SESSION_PREFIX = "session:user"

    # Default TTLs in seconds
    DEFAULT_SESSION_TTL = 86400  # 24 hours

    def __init__(self) -> None:
        """Initialize Redis session store client."""
        self._redis: Optional[Redis] = None

    async def get_redis(self) -> Redis:
        """Get or create Redis connection.

        Returns:
            Redis client instance

        """
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    settings.redis_url,
                    max_connections=settings.redis_max_connections,
                    decode_responses=True,
                )
                logger.info(f"Redis session store connected: {settings.redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis session store: {e}")
                self._redis = None
        return self._redis

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def generate_blacklist_key(self, token_jti: str) -> str:
        """Generate Redis key for blacklisted token.

        Args:
            token_jti: JWT ID (jti claim) of the token

        Returns:
            Redis key string

        """
        return f"{self.BLACKLIST_PREFIX}:{token_jti}"

    def generate_session_key(self, user_id: str, session_id: str) -> str:
        """Generate Redis key for user session.

        Args:
            user_id: User ID
            session_id: Session ID (typically UUID)

        Returns:
            Redis key string

        """
        return f"{self.SESSION_PREFIX}:{user_id}:{session_id}"

    async def is_token_blacklisted(self, token_jti: str) -> bool:
        """Check if a JWT token is blacklisted.

        Args:
            token_jti: JWT ID (jti claim) of the token

        Returns:
            True if token is blacklisted, False otherwise

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                # If Redis is unavailable, allow token (fail open)
                logger.warning("Redis unavailable, allowing token (fail open)")
                return False

            blacklist_key = self.generate_blacklist_key(token_jti)
            blacklisted = await redis_client.exists(blacklist_key)

            if blacklisted:
                logger.debug(f"Token {token_jti} is blacklisted")

            return bool(blacklisted)

        except Exception as e:
            logger.warning(f"Error checking token blacklist: {e}")
            # If Redis is unavailable, allow token (fail open)
            return False

    async def blacklist_token(
        self,
        token_jti: str,
        expires_at: datetime,
        user_id: Optional[str] = None,
        reason: str = "logout",
    ) -> bool:
        """Add a JWT token to the blacklist.

        Args:
            token_jti: JWT ID (jti claim) of the token
            expires_at: Token expiration datetime
            user_id: Optional user ID for logging
            reason: Reason for blacklisting (logout, refresh, password_change, etc.)

        Returns:
            True if blacklisted successfully, False otherwise

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                logger.warning("Redis unavailable, cannot blacklist token")
                return False

            blacklist_key = self.generate_blacklist_key(token_jti)

            # Calculate TTL until token expiration
            now = datetime.utcnow()
            ttl_seconds = max(0, int((expires_at - now).total_seconds()))

            # Store blacklist entry with metadata
            blacklist_data = {
                "jti": token_jti,
                "user_id": user_id,
                "blacklisted_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "reason": reason,
            }

            await redis_client.setex(
                blacklist_key,
                ttl_seconds,
                json.dumps(blacklist_data),
            )

            logger.info(
                f"Token {token_jti} blacklisted for user {user_id} "
                f"(reason: {reason}, TTL: {ttl_seconds}s)"
            )
            return True

        except Exception as e:
            logger.warning(f"Error blacklisting token: {e}")
            return False

    async def create_session(
        self,
        user_id: str,
        session_id: str,
        metadata: Optional[dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """Create a user session.

        Args:
            user_id: User ID
            session_id: Session ID (typically UUID)
            metadata: Optional session metadata (ip_address, user_agent, etc.)
            ttl: Time to live in seconds (defaults to DEFAULT_SESSION_TTL)

        Returns:
            True if session created successfully, False otherwise

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                logger.warning("Redis unavailable, cannot create session")
                return False

            session_key = self.generate_session_key(user_id, session_id)

            # Prepare session data
            session_data = {
                "user_id": user_id,
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }

            # Use provided TTL or default
            session_ttl = ttl if ttl is not None else self.DEFAULT_SESSION_TTL

            await redis_client.setex(
                session_key,
                session_ttl,
                json.dumps(session_data),
            )

            logger.debug(
                f"Session created for user {user_id}: {session_id} (TTL: {session_ttl}s)"
            )
            return True

        except Exception as e:
            logger.warning(f"Error creating session: {e}")
            return False

    async def get_session(
        self,
        user_id: str,
        session_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get a user session.

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            Session data dict or None if not found

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                return None

            session_key = self.generate_session_key(user_id, session_id)
            session_data = await redis_client.get(session_key)

            if session_data:
                return json.loads(session_data)
            else:
                return None

        except Exception as e:
            logger.warning(f"Error getting session: {e}")
            return None

    async def update_session(
        self,
        user_id: str,
        session_id: str,
        metadata: Optional[dict[str, Any]] = None,
        extend_ttl: bool = True,
    ) -> bool:
        """Update a user session.

        Args:
            user_id: User ID
            session_id: Session ID
            metadata: Optional metadata to update
            extend_ttl: Whether to extend the TTL (default: True)

        Returns:
            True if session updated successfully, False otherwise

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                return False

            session_key = self.generate_session_key(user_id, session_id)
            session_data = await redis_client.get(session_key)

            if not session_data:
                logger.debug(f"Session not found for update: {session_id}")
                return False

            # Parse existing session
            session = json.loads(session_data)

            # Update metadata
            if metadata:
                session["metadata"].update(metadata)

            # Update timestamp
            session["updated_at"] = datetime.utcnow().isoformat()

            # Save with extended TTL
            session_ttl = self.DEFAULT_SESSION_TTL if extend_ttl else None
            if session_ttl:
                await redis_client.setex(
                    session_key,
                    session_ttl,
                    json.dumps(session),
                )
            else:
                await redis_client.set(session_key, json.dumps(session))

            logger.debug(f"Session updated for user {user_id}: {session_id}")
            return True

        except Exception as e:
            logger.warning(f"Error updating session: {e}")
            return False

    async def delete_session(self, user_id: str, session_id: str) -> bool:
        """Delete a user session.

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            True if session deleted successfully, False otherwise

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                return False

            session_key = self.generate_session_key(user_id, session_id)
            result = await redis_client.delete(session_key)

            if result:
                logger.debug(f"Session deleted for user {user_id}: {session_id}")
                return True
            else:
                logger.debug(f"Session not found for deletion: {session_id}")
                return False

        except Exception as e:
            logger.warning(f"Error deleting session: {e}")
            return False

    async def delete_user_sessions(self, user_id: str) -> int:
        """Delete all sessions for a user.

        Called when user logs out from all devices or changes password.

        Args:
            user_id: User ID

        Returns:
            Number of sessions deleted

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                return 0

            pattern = f"{self.SESSION_PREFIX}:{user_id}:*"
            keys = []

            async for key in redis_client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await redis_client.delete(*keys)
                logger.info(f"Deleted {len(keys)} sessions for user {user_id}")
                return len(keys)
            else:
                logger.debug(f"No sessions found for user {user_id}")
                return 0

        except Exception as e:
            logger.warning(f"Error deleting user sessions: {e}")
            return 0

    async def get_user_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """Get all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            List of session data dicts

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                return []

            pattern = f"{self.SESSION_PREFIX}:{user_id}:*"
            sessions = []

            async for key in redis_client.scan_iter(match=pattern):
                session_data = await redis_client.get(key)
                if session_data:
                    sessions.append(json.loads(session_data))

            return sessions

        except Exception as e:
            logger.warning(f"Error getting user sessions: {e}")
            return []

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (handled automatically by Redis TTL).

        This is a no-op function since Redis automatically expires keys with TTL.
        Kept for API compatibility and potential future batch cleanup operations.

        Returns:
            Always returns 0 (Redis handles expiration automatically)

        """
        # Redis automatically handles TTL expiration
        # This method exists for API compatibility and potential future use
        return 0
