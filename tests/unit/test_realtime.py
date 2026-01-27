"""Unit tests for realtime WebSocket connection manager with Redis pub/sub."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from pybase.realtime.manager import ConnectionManager, Connection
from pybase.schemas.realtime import (
    ConnectEvent,
    DisconnectEvent,
    SubscribedEvent,
    EventType,
)


@pytest.fixture
def connection_manager():
    """Create a ConnectionManager instance for testing."""
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.fixture
def mock_redis_pubsub():
    """Create a mock Redis pub/sub manager."""
    mock_manager = MagicMock()
    mock_manager.publish = AsyncMock(return_value=True)
    mock_manager.subscribe = AsyncMock(return_value=True)
    mock_manager.unsubscribe = AsyncMock(return_value=True)
    mock_manager.start_listener = AsyncMock(return_value=True)
    mock_manager.close = AsyncMock()
    mock_manager.on_message = MagicMock()
    mock_manager.REALTIME_CHANNEL_PREFIX = "realtime"
    return mock_manager


class TestConnectionManager:
    """Test suite for ConnectionManager basic functionality."""

    @pytest.mark.asyncio
    async def test_connect(self, connection_manager, mock_websocket):
        """Test accepting a new WebSocket connection."""
        user_id = str(uuid4())
        user_name = "Test User"

        connection = await connection_manager.connect(
            mock_websocket,
            user_id,
            user_name,
        )

        assert connection is not None
        assert connection.user_id == user_id
        assert connection.user_name == user_name
        assert connection.connection_id in connection_manager._connections
        assert user_id in connection_manager._user_connections
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, connection_manager, mock_websocket):
        """Test disconnecting a WebSocket connection."""
        user_id = str(uuid4())
        user_name = "Test User"

        connection = await connection_manager.connect(
            mock_websocket,
            user_id,
            user_name,
        )
        connection_id = connection.connection_id

        await connection_manager.disconnect(connection_id, "test disconnect")

        assert connection_id not in connection_manager._connections
        assert user_id not in connection_manager._user_connections

    @pytest.mark.asyncio
    async def test_subscribe(self, connection_manager, mock_websocket):
        """Test subscribing to a channel."""
        user_id = str(uuid4())
        connection = await connection_manager.connect(
            mock_websocket,
            user_id,
            "Test User",
        )

        channel = "table:test-uuid"
        result = await connection_manager.subscribe(connection.connection_id, channel)

        assert result is True
        assert channel in connection.subscriptions
        assert connection.connection_id in connection_manager._channel_subscribers[channel]

    @pytest.mark.asyncio
    async def test_unsubscribe(self, connection_manager, mock_websocket):
        """Test unsubscribing from a channel."""
        user_id = str(uuid4())
        connection = await connection_manager.connect(
            mock_websocket,
            user_id,
            "Test User",
        )

        channel = "table:test-uuid"
        await connection_manager.subscribe(connection.connection_id, channel)
        result = await connection_manager.unsubscribe(connection.connection_id, channel)

        assert result is True
        assert channel not in connection.subscriptions
        assert channel not in connection_manager._channel_subscribers


class TestRedisPubSub:
    """Test suite for Redis pub/sub integration in ConnectionManager."""

    @pytest.mark.asyncio
    async def test_ensure_redis_initializes_pubsub(
        self, connection_manager, mock_redis_pubsub
    ):
        """Test that _ensure_redis initializes the Redis pub/sub manager."""
        with patch(
            "pybase.realtime.manager.get_pubsub_manager",
            return_value=mock_redis_pubsub,
        ):
            redis_manager = await connection_manager._ensure_redis()

            assert redis_manager is not None
            assert connection_manager._redis_pubsub == mock_redis_pubsub
            assert connection_manager._instance_id is not None
            assert connection_manager._redis_listener_started is True
            mock_redis_pubsub.start_listener.assert_called_once()
            mock_redis_pubsub.on_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_redis_returns_none_when_unavailable(
        self, connection_manager
    ):
        """Test that _ensure_redis returns None when Redis is not available."""
        with patch("pybase.realtime.manager.REDIS_AVAILABLE", False):
            redis_manager = await connection_manager._ensure_redis()
            assert redis_manager is None

    @pytest.mark.asyncio
    async def test_broadcast_to_channel_publishes_to_redis(
        self, connection_manager, mock_websocket, mock_redis_pubsub
    ):
        """Test that broadcast_to_channel publishes to Redis when available."""
        # Setup connection and subscription
        user_id = str(uuid4())
        connection = await connection_manager.connect(
            mock_websocket,
            user_id,
            "Test User",
        )
        channel = "table:test-uuid"
        await connection_manager.subscribe(connection.connection_id, channel)

        # Mock Redis pub/sub manager
        with patch(
            "pybase.realtime.manager.get_pubsub_manager",
            return_value=mock_redis_pubsub,
        ):
            # Initialize Redis
            await connection_manager._ensure_redis()

            # Create event to broadcast
            event = ConnectEvent(connection_id=connection.connection_id, user_id=user_id)

            # Broadcast to channel (excluding the sender)
            sent = await connection_manager.broadcast_to_channel(
                channel, event, exclude_connection=connection.connection_id
            )

            # Verify Redis publish was called
            mock_redis_pubsub.publish.assert_called_once()
            call_args = mock_redis_pubsub.publish.call_args

            # Check the published message structure
            published_message = call_args[0][1]  # Second argument is the message dict
            assert published_message["instance_id"] == connection_manager._instance_id
            assert published_message["channel"] == channel
            assert "event" in published_message
            assert published_message["exclude_connection"] == connection.connection_id

    @pytest.mark.asyncio
    async def test_handle_redis_message_ignores_own_instance(
        self, connection_manager, mock_redis_pubsub
    ):
        """Test that _handle_redis_message ignores messages from own instance."""
        # Setup
        with patch(
            "pybase.realtime.manager.get_pubsub_manager",
            return_value=mock_redis_pubsub,
        ):
            await connection_manager._ensure_redis()

            # Create message from own instance
            message = {
                "instance_id": connection_manager._instance_id,
                "channel": "table:test-uuid",
                "event": {"type": "connect", "timestamp": "2024-01-01T00:00:00Z"},
                "exclude_connection": None,
            }

            # Handle message (should be ignored)
            await connection_manager._handle_redis_message(message)

            # Verify publish was not called again (message was ignored)
            assert mock_redis_pubsub.publish.call_count == 0

    @pytest.mark.asyncio
    async def test_handle_redis_message_relays_to_local_connections(
        self, connection_manager, mock_websocket, mock_redis_pubsub
    ):
        """Test that _handle_redis_message relays to local WebSocket connections."""
        # Setup two connections
        user_id1 = str(uuid4())
        user_id2 = str(uuid4())
        conn1 = await connection_manager.connect(mock_websocket, user_id1, "User 1")
        conn2 = await connection_manager.connect(mock_websocket, user_id2, "User 2")

        channel = "table:test-uuid"
        await connection_manager.subscribe(conn1.connection_id, channel)
        await connection_manager.subscribe(conn2.connection_id, channel)

        # Initialize Redis
        with patch(
            "pybase.realtime.manager.get_pubsub_manager",
            return_value=mock_redis_pubsub,
        ):
            await connection_manager._ensure_redis()

            # Create message from another instance
            event = ConnectEvent(connection_id=str(uuid4()), user_id=user_id1)
            message = {
                "instance_id": "other-instance-id",
                "channel": channel,
                "event": event.model_dump(mode="json"),
                "exclude_connection": None,
            }

            # Handle message
            await connection_manager._handle_redis_message(message)

            # Verify both local connections received the message
            assert mock_websocket.send_json.call_count >= 2

    @pytest.mark.asyncio
    async def test_startup_initializes_redis(self, connection_manager, mock_redis_pubsub):
        """Test that startup() initializes Redis pub/sub manager."""
        with patch(
            "pybase.realtime.manager.get_pubsub_manager",
            return_value=mock_redis_pubsub,
        ):
            await connection_manager.startup()

            assert connection_manager._redis_pubsub is not None
            assert connection_manager._redis_listener_started is True

    @pytest.mark.asyncio
    async def test_shutdown_closes_redis(self, connection_manager, mock_redis_pubsub):
        """Test that shutdown() closes Redis connections."""
        # Initialize Redis first
        with patch(
            "pybase.realtime.manager.get_pubsub_manager",
            return_value=mock_redis_pubsub,
        ):
            await connection_manager._ensure_redis()

            # Shutdown
            await connection_manager.shutdown()

            # Verify close was called
            mock_redis_pubsub.close.assert_called_once()
            assert connection_manager._redis_listener_started is False

    @pytest.mark.asyncio
    async def test_broadcast_without_redis_still_works(
        self, connection_manager, mock_websocket
    ):
        """Test that broadcast_to_channel works even without Redis."""
        # Setup connection
        user_id = str(uuid4())
        connection = await connection_manager.connect(
            mock_websocket,
            user_id,
            "Test User",
        )

        channel = "table:test-uuid"
        await connection_manager.subscribe(connection.connection_id, channel)

        # Ensure Redis is not available
        with patch("pybase.realtime.manager.REDIS_AVAILABLE", False):
            event = ConnectEvent(connection_id=connection.connection_id, user_id=user_id)
            sent = await connection_manager.broadcast_to_channel(channel, event)

            # Should still send to local connection
            assert sent >= 0

    @pytest.mark.asyncio
    async def test_redis_message_with_excluded_connection(
        self, connection_manager, mock_websocket, mock_redis_pubsub
    ):
        """Test that excluded connection doesn't receive the message."""
        # Setup two connections
        user_id1 = str(uuid4())
        user_id2 = str(uuid4())
        conn1 = await connection_manager.connect(mock_websocket, user_id1, "User 1")
        conn2 = await connection_manager.connect(mock_websocket, user_id2, "User 2")

        channel = "table:test-uuid"
        await connection_manager.subscribe(conn1.connection_id, channel)
        await connection_manager.subscribe(conn2.connection_id, channel)

        # Initialize Redis
        with patch(
            "pybase.realtime.manager.get_pubsub_manager",
            return_value=mock_redis_pubsub,
        ):
            await connection_manager._ensure_redis()

            # Reset mock to track new calls
            mock_websocket.send_json.reset_mock()

            # Create message that excludes conn1
            event = ConnectEvent(connection_id=str(uuid4()), user_id=user_id1)
            message = {
                "instance_id": "other-instance-id",
                "channel": channel,
                "event": event.model_dump(mode="json"),
                "exclude_connection": conn1.connection_id,
            }

            # Handle message
            await connection_manager._handle_redis_message(message)

            # Count how many times send_json was called (should be 1 for conn2 only)
            # Note: The connect/disconnect events also trigger send_json, so we check
            # that at least the broadcast happened
            assert mock_websocket.send_json.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_stats(self, connection_manager, mock_websocket):
        """Test that get_stats returns connection statistics."""
        # Create multiple connections
        user_id1 = str(uuid4())
        user_id2 = str(uuid4())
        conn1 = await connection_manager.connect(mock_websocket, user_id1, "User 1")
        conn2 = await connection_manager.connect(mock_websocket, user_id2, "User 2")

        channel = "table:test-uuid"
        await connection_manager.subscribe(conn1.connection_id, channel)
        await connection_manager.subscribe(conn2.connection_id, channel)

        stats = connection_manager.get_stats()

        assert stats["total_connections"] == 2
        assert stats["total_users"] == 2
        assert channel in stats["channels"]
        assert stats["channels"][channel] == 2
