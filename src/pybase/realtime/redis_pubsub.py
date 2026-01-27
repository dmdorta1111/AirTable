"""Redis pub/sub manager for cross-instance WebSocket message broadcasting.

Enables multiple backend instances to coordinate real-time updates through Redis.
When a message is published to a channel, all subscribed instances receive it
and can broadcast to their local WebSocket connections.

Supported channel patterns:
- realtime:* - All realtime WebSocket messages
- presence:* - Presence updates across instances
- table:{table_id} - Table-specific updates
- view:{view_id} - View-specific updates
- dashboard:{dashboard_id} - Dashboard-specific updates
"""

import asyncio
import json
import logging
from typing import Any, Callable, Optional

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from pybase.core.config import settings
from pybase.core.logging import get_logger

logger = get_logger(__name__)


class RedisPubSubManager:
    """Manages Redis pub/sub for cross-instance WebSocket coordination.

    This manager handles:
    - Publishing messages to Redis channels
    - Subscribing to channels and receiving messages
    - Message callback registration
    - Connection lifecycle management
    """

    # Channel prefixes
    REALTIME_CHANNEL_PREFIX = "realtime"
    PRESENCE_CHANNEL_PREFIX = "presence"

    def __init__(self) -> None:
        """Initialize Redis pub/sub manager."""
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._message_handlers: dict[str, list[Callable]] = {}
        self._is_listening = False
        self._lock = asyncio.Lock()

    async def get_redis(self) -> Optional[redis.Redis]:
        """Get or create Redis connection.

        Returns:
            Redis client instance or None if connection fails
        """
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    settings.redis_url,
                    max_connections=settings.redis_max_connections,
                    decode_responses=True,
                )
                # Test connection
                await self._redis.ping()
                logger.info(f"Redis pub/sub connected: {settings.redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis for pub/sub: {e}")
                self._redis = None
        return self._redis

    async def get_pubsub(self) -> Optional[redis.client.PubSub]:
        """Get or create PubSub instance.

        Returns:
            PubSub instance or None if Redis is not available
        """
        if self._pubsub is None:
            redis_client = await self.get_redis()
            if not redis_client:
                return None
            self._pubsub = redis_client.pubsub()
        return self._pubsub

    async def publish(
        self,
        channel: str,
        message: dict[str, Any],
    ) -> bool:
        """Publish a message to a Redis channel.

        Args:
            channel: Channel name to publish to
            message: Message data to publish (will be JSON serialized)

        Returns:
            True if published successfully, False otherwise
        """
        try:
            redis_client = await self.get_redis()
            if not redis_client:
                return False

            # Serialize message
            message_json = json.dumps(message)

            # Publish to channel
            result = await redis_client.publish(channel, message_json)

            if result > 0:
                logger.debug(f"Published to {channel}: {message.get('event', 'unknown')}")
            else:
                logger.debug(f"Published to {channel} but no subscribers")

            return True

        except Exception as e:
            logger.warning(f"Failed to publish to {channel}: {e}")
            return False

    async def subscribe(self, channel: str) -> bool:
        """Subscribe to a Redis channel.

        Args:
            channel: Channel name to subscribe to

        Returns:
            True if subscribed successfully, False otherwise
        """
        try:
            pubsub = await self.get_pubsub()
            if not pubsub:
                return False

            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to Redis channel: {channel}")
            return True

        except Exception as e:
            logger.warning(f"Failed to subscribe to {channel}: {e}")
            return False

    async def unsubscribe(self, channel: str) -> bool:
        """Unsubscribe from a Redis channel.

        Args:
            channel: Channel name to unsubscribe from

        Returns:
            True if unsubscribed successfully, False otherwise
        """
        try:
            pubsub = await self.get_pubsub()
            if not pubsub:
                return False

            await pubsub.unsubscribe(channel)
            logger.info(f"Unsubscribed from Redis channel: {channel}")
            return True

        except Exception as e:
            logger.warning(f"Failed to unsubscribe from {channel}: {e}")
            return False

    async def subscribe_pattern(self, pattern: str) -> bool:
        """Subscribe to a channel pattern.

        Args:
            pattern: Channel pattern (e.g., "realtime:*")

        Returns:
            True if subscribed successfully, False otherwise
        """
        try:
            pubsub = await self.get_pubsub()
            if not pubsub:
                return False

            await pubsub.psubscribe(pattern)
            logger.info(f"Subscribed to Redis pattern: {pattern}")
            return True

        except Exception as e:
            logger.warning(f"Failed to subscribe to pattern {pattern}: {e}")
            return False

    async def unsubscribe_pattern(self, pattern: str) -> bool:
        """Unsubscribe from a channel pattern.

        Args:
            pattern: Channel pattern to unsubscribe from

        Returns:
            True if unsubscribed successfully, False otherwise
        """
        try:
            pubsub = await self.get_pubsub()
            if not pubsub:
                return False

            await pubsub.punsubscribe(pattern)
            logger.info(f"Unsubscribed from Redis pattern: {pattern}")
            return True

        except Exception as e:
            logger.warning(f"Failed to unsubscribe from pattern {pattern}: {e}")
            return False

    def on_message(self, channel: str, handler: Callable) -> None:
        """Register a message handler for a channel.

        Args:
            channel: Channel name (or pattern)
            handler: Async callback function(message: dict)
        """
        if channel not in self._message_handlers:
            self._message_handlers[channel] = []
        self._message_handlers[channel].append(handler)
        logger.debug(f"Registered handler for channel: {channel}")

    def off_message(self, channel: str, handler: Optional[Callable] = None) -> None:
        """Unregister a message handler for a channel.

        Args:
            channel: Channel name (or pattern)
            handler: Specific handler to remove, or None to remove all handlers for channel
        """
        if channel not in self._message_handlers:
            return

        if handler is None:
            # Remove all handlers for this channel
            del self._message_handlers[channel]
            logger.debug(f"Removed all handlers for channel: {channel}")
        else:
            # Remove specific handler
            try:
                self._message_handlers[channel].remove(handler)
                logger.debug(f"Removed handler for channel: {channel}")
                # Clean up empty handler lists
                if not self._message_handlers[channel]:
                    del self._message_handlers[channel]
            except ValueError:
                pass  # Handler not in list

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Handle an incoming Redis pub/sub message.

        Args:
            message: Redis message dict with 'channel', 'type', and 'data'
        """
        try:
            # Ignore non-message types
            if message.get("type") not in ("message", "pmessage"):
                return

            # Extract channel and data
            channel = message.get("channel", "")
            if message.get("type") == "pmessage":
                # For pattern subscriptions, use the pattern matched
                channel = message.get("pattern", channel)

            data_str = message.get("data")
            if not data_str:
                return

            # Parse JSON data
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse message from {channel}: {data_str}")
                return

            # Find and call handlers
            # Check for exact channel match first
            handlers = self._message_handlers.get(channel, [])

            # Also check for pattern matches
            for pattern, pattern_handlers in self._message_handlers.items():
                if "*" in pattern:
                    # Simple pattern matching (convert to glob-like pattern)
                    # Redis pattern syntax: * matches any characters
                    import fnmatch

                    if fnmatch.fnmatch(channel, pattern):
                        handlers.extend(pattern_handlers)

            # Call all handlers
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Handler error for {channel}: {e}")

        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")

    async def _listener(self) -> None:
        """Listener task for processing pub/sub messages.

        Runs in a background task and processes incoming messages.
        """
        logger.info("Redis pub/sub listener started")
        self._is_listening = True

        try:
            pubsub = await self.get_pubsub()
            if not pubsub:
                logger.warning("Cannot start listener: PubSub not available")
                return

            async for message in pubsub.listen():
                if not self._is_listening:
                    break
                await self._handle_message(message)

        except asyncio.CancelledError:
            logger.info("Redis pub/sub listener cancelled")
        except Exception as e:
            logger.error(f"Redis pub/sub listener error: {e}")
        finally:
            self._is_listening = False
            logger.info("Redis pub/sub listener stopped")

    async def start_listener(self) -> bool:
        """Start the background listener task.

        Returns:
            True if listener started successfully, False otherwise
        """
        async with self._lock:
            if self._listener_task is not None and not self._listener_task.done():
                logger.warning("Redis pub/sub listener already running")
                return True

            try:
                self._listener_task = asyncio.create_task(self._listener())
                logger.info("Started Redis pub/sub listener task")
                return True
            except Exception as e:
                logger.error(f"Failed to start Redis pub/sub listener: {e}")
                return False

    async def stop_listener(self) -> None:
        """Stop the background listener task."""
        async with self._lock:
            if self._listener_task is None:
                return

            self._is_listening = False
            self._listener_task.cancel()

            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

            self._listener_task = None
            logger.info("Stopped Redis pub/sub listener task")

    async def close(self) -> None:
        """Close Redis connections and cleanup.

        Should be called on application shutdown.
        """
        async with self._lock:
            # Stop listener
            await self.stop_listener()

            # Unsubscribe from all channels
            if self._pubsub:
                try:
                    await self._pubsub.close()
                except Exception as e:
                    logger.warning(f"Error closing pubsub: {e}")
                self._pubsub = None

            # Close Redis connection
            if self._redis:
                try:
                    await self._redis.close()
                except Exception as e:
                    logger.warning(f"Error closing Redis connection: {e}")
                self._redis = None

            # Clear handlers
            self._message_handlers.clear()
            logger.info("Redis pub/sub manager closed")

    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._redis is not None

    @property
    def is_listening(self) -> bool:
        """Check if listener is running."""
        return self._is_listening


# Global pub/sub manager instance
pubsub_manager = RedisPubSubManager()


def get_pubsub_manager() -> RedisPubSubManager:
    """Get the global pub/sub manager instance.

    Returns:
        Global RedisPubSubManager instance
    """
    return pubsub_manager
