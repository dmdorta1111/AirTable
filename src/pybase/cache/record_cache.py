"""Redis caching for record queries."""

import json
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from pybase.core.config import settings
from pybase.core.logging import get_logger

logger = get_logger(__name__)


class RecordCache:
    """Redis cache for record queries.

    Provides caching for record list queries to improve performance
    for large datasets. Cache keys are based on table_id, user_id,
    cursor, and page_size to ensure proper cache isolation.

    Cache TTL: 5 minutes (300 seconds) by default
    """

    # Cache TTL in seconds
    DEFAULT_TTL = 300
    LIST_CACHE_PREFIX = "record:list"

    def __init__(self) -> None:
        """Initialize Redis cache client."""
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
                logger.info(f"Redis cache connected: {settings.redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self._redis = None
        return self._redis

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def generate_cache_key(
        self,
        table_id: Optional[str],
        user_id: str,
        cursor: Optional[str] = None,
        page_size: int = 20,
    ) -> str:
        """Generate cache key for record list query.

        Args:
            table_id: Optional table ID
            user_id: User ID
            cursor: Optional pagination cursor
            page_size: Page size

        Returns:
            Cache key string

        """
        table_part = table_id if table_id else "all"
        cursor_part = cursor if cursor else "none"
        return f"{self.LIST_CACHE_PREFIX}:{user_id}:{table_part}:{page_size}:{cursor_part}"

    async def get_cached_records(
        self,
        table_id: Optional[str],
        user_id: str,
        cursor: Optional[str] = None,
        page_size: int = 20,
    ) -> Optional[dict[str, Any]]:
        """Get cached records for a query.

        Args:
            table_id: Optional table ID
            user_id: User ID
            cursor: Optional pagination cursor
            page_size: Page size

        Returns:
            Cached data dict with records, next_cursor, has_more, or None if not cached

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                return None

            cache_key = self.generate_cache_key(table_id, user_id, cursor, page_size)
            cached_data = await redis_client.get(cache_key)

            if cached_data:
                logger.debug(f"Cache hit: {cache_key}")
                return json.loads(cached_data)
            else:
                logger.debug(f"Cache miss: {cache_key}")
                return None

        except Exception as e:
            logger.warning(f"Error getting cached records: {e}")
            return None

    async def set_cached_records(
        self,
        table_id: Optional[str],
        user_id: str,
        data: dict[str, Any],
        cursor: Optional[str] = None,
        page_size: int = 20,
        ttl: int = DEFAULT_TTL,
    ) -> bool:
        """Cache records for a query.

        Args:
            table_id: Optional table ID
            user_id: User ID
            data: Data to cache (records, next_cursor, has_more)
            cursor: Optional pagination cursor
            page_size: Page size
            ttl: Time to live in seconds

        Returns:
            True if cached successfully, False otherwise

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                return False

            cache_key = self.generate_cache_key(table_id, user_id, cursor, page_size)

            # Serialize records for caching
            cache_data = {
                "records": [
                    {
                        "id": str(r.id),
                        "table_id": str(r.table_id),
                        "data": r.data,
                        "created_at": r.created_at.isoformat(),
                        "updated_at": r.updated_at.isoformat(),
                        "row_height": r.row_height,
                    }
                    for r in data.get("records", [])
                ],
                "next_cursor": data.get("next_cursor"),
                "has_more": data.get("has_more", False),
            }

            await redis_client.setex(cache_key, ttl, json.dumps(cache_data))
            logger.debug(f"Cached data: {cache_key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.warning(f"Error setting cached records: {e}")
            return False

    async def invalidate_table_cache(self, table_id: str) -> None:
        """Invalidate all cache entries for a table.

        Called when records in a table are created, updated, or deleted.

        Args:
            table_id: Table ID to invalidate cache for

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                return

            pattern = f"{self.LIST_CACHE_PREFIX}:*:{table_id}:*"
            keys = []

            async for key in redis_client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries for table {table_id}")

        except Exception as e:
            logger.warning(f"Error invalidating table cache: {e}")

    async def invalidate_user_cache(self, user_id: str) -> None:
        """Invalidate all cache entries for a user.

        Called when user permissions change.

        Args:
            user_id: User ID to invalidate cache for

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                return

            pattern = f"{self.LIST_CACHE_PREFIX}:{user_id}:*"
            keys = []

            async for key in redis_client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries for user {user_id}")

        except Exception as e:
            logger.warning(f"Error invalidating user cache: {e}")
