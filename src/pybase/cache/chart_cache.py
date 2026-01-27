"""Redis caching for chart data queries."""

import json
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from pybase.core.config import settings
from pybase.core.logging import get_logger

logger = get_logger(__name__)


class ChartCache:
    """Redis cache for chart data queries.

    Provides caching for chart data generation to improve performance
    for expensive analytics computations. Cache keys are based on chart_id
    and data_request parameters to ensure proper cache isolation.

    Cache TTL: Configurable per chart (default 5 minutes / 300 seconds)
    """

    # Default cache TTL in seconds
    DEFAULT_TTL = 300
    DATA_CACHE_PREFIX = "chart:data"

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
        chart_id: str,
        data_request_hash: str,
    ) -> str:
        """Generate cache key for chart data query.

        Args:
            chart_id: Chart ID
            data_request_hash: Hash of data request parameters

        Returns:
            Cache key string

        """
        return f"{self.DATA_CACHE_PREFIX}:{chart_id}:{data_request_hash}"

    def _hash_data_request(self, data_request: Optional[dict[str, Any]]) -> str:
        """Generate hash from data request parameters.

        Args:
            data_request: Optional data request parameters

        Returns:
            Hash string for cache key

        """
        if not data_request:
            return "default"

        # Create a deterministic hash from request parameters
        request_str = json.dumps(data_request, sort_keys=True)
        return str(hash(request_str))

    async def get_cached_chart_data(
        self,
        chart_id: str,
        data_request: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Get cached chart data.

        Args:
            chart_id: Chart ID
            data_request: Optional data request parameters

        Returns:
            Cached chart data dict or None if not cached

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                return None

            data_request_hash = self._hash_data_request(data_request)
            cache_key = self.generate_cache_key(chart_id, data_request_hash)
            cached_data = await redis_client.get(cache_key)

            if cached_data:
                logger.debug(f"Cache hit: {cache_key}")
                return json.loads(cached_data)
            else:
                logger.debug(f"Cache miss: {cache_key}")
                return None

        except Exception as e:
            logger.warning(f"Error getting cached chart data: {e}")
            return None

    async def set_cached_chart_data(
        self,
        chart_id: str,
        data: dict[str, Any],
        data_request: Optional[dict[str, Any]] = None,
        ttl: int = DEFAULT_TTL,
    ) -> bool:
        """Cache chart data.

        Args:
            chart_id: Chart ID
            data: Chart data to cache
            data_request: Optional data request parameters
            ttl: Time to live in seconds

        Returns:
            True if cached successfully, False otherwise

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                return False

            data_request_hash = self._hash_data_request(data_request)
            cache_key = self.generate_cache_key(chart_id, data_request_hash)

            # Serialize chart data for caching
            cache_data = {
                "chart_id": chart_id,
                "chart_type": data.get("chart_type"),
                "data": data.get("data", []),
                "series": [
                    {
                        "name": s.get("name"),
                        "data": [{"label": dp.get("label"), "value": dp.get("value")} for dp in s.get("data", [])],
                        "color": s.get("color"),
                    }
                    for s in (data.get("series") or [])
                ],
                "labels": data.get("labels", []),
                "metadata": data.get("metadata", {}),
                "generated_at": data.get("generated_at"),
            }

            await redis_client.setex(cache_key, ttl, json.dumps(cache_data))
            logger.debug(f"Cached chart data: {cache_key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.warning(f"Error setting cached chart data: {e}")
            return False

    async def invalidate_chart_cache(self, chart_id: str) -> None:
        """Invalidate all cache entries for a chart.

        Called when chart configuration or source data changes.

        Args:
            chart_id: Chart ID to invalidate cache for

        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                return

            pattern = f"{self.DATA_CACHE_PREFIX}:{chart_id}:*"
            keys = []

            async for key in redis_client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries for chart {chart_id}")

        except Exception as e:
            logger.warning(f"Error invalidating chart cache: {e}")

    async def invalidate_table_cache(self, table_id: str) -> None:
        """Invalidate all cache entries for charts using a table.

        Called when table data changes.

        Note: This requires tracking which charts use which tables.
        Currently, this is a placeholder for future implementation.

        Args:
            table_id: Table ID to invalidate cache for

        """
        # TODO: Implement table-to-chart mapping for cache invalidation
        # This would require maintaining a reverse index of charts -> tables
        logger.debug(f"Table cache invalidation requested for table {table_id} (not yet implemented)")
