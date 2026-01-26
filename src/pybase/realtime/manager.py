"""WebSocket connection manager for realtime functionality.

Handles:
- Connection lifecycle management
- Channel subscriptions (pub/sub)
- Message broadcasting
- Connection heartbeats

Supported channel types:
- workspace:{workspace_id} - Workspace-level updates
- base:{base_id} - Base-level updates (tables, dashboards)
- table:{table_id} - Table-level updates (records, fields, views)
- view:{view_id} - View-specific updates
- dashboard:{dashboard_id} - Dashboard-specific updates
- user:{user_id} - User personal notifications
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect

from pybase.schemas.realtime import (
    BaseEvent,
    ConnectEvent,
    DisconnectEvent,
    ErrorEvent,
    EventType,
    PongEvent,
    SubscribedEvent,
    UnsubscribedEvent,
    WebSocketMessage,
)

logger = logging.getLogger(__name__)


@dataclass
class Connection:
    """Represents a WebSocket connection."""

    connection_id: str
    websocket: WebSocket
    user_id: str
    user_name: str
    user_color: str
    connected_at: datetime
    last_ping: datetime
    subscriptions: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_alive(self) -> bool:
        """Check if connection is still considered alive."""
        now = datetime.now(timezone.utc)
        # Consider dead if no ping in 60 seconds
        return (now - self.last_ping).total_seconds() < 60


# User colors for presence (distinct, accessible colors)
USER_COLORS = [
    "#E53935",  # Red
    "#D81B60",  # Pink
    "#8E24AA",  # Purple
    "#5E35B1",  # Deep Purple
    "#3949AB",  # Indigo
    "#1E88E5",  # Blue
    "#039BE5",  # Light Blue
    "#00ACC1",  # Cyan
    "#00897B",  # Teal
    "#43A047",  # Green
    "#7CB342",  # Light Green
    "#C0CA33",  # Lime
    "#FDD835",  # Yellow
    "#FFB300",  # Amber
    "#FB8C00",  # Orange
    "#F4511E",  # Deep Orange
]


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        # connection_id -> Connection
        self._connections: dict[str, Connection] = {}
        # user_id -> set of connection_ids (user can have multiple tabs)
        self._user_connections: dict[str, set[str]] = {}
        # channel -> set of connection_ids
        self._channel_subscribers: dict[str, set[str]] = {}
        # Event handlers
        self._event_handlers: dict[EventType, list[Callable]] = {}
        # Lock for thread safety
        self._lock = asyncio.Lock()
        # Color assignment counter
        self._color_counter = 0

    def _get_next_color(self) -> str:
        """Get the next user color in rotation."""
        color = USER_COLORS[self._color_counter % len(USER_COLORS)]
        self._color_counter += 1
        return color

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        user_name: str,
    ) -> Connection:
        """Accept a new WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
            user_id: Authenticated user ID
            user_name: User display name

        Returns:
            Connection object
        """
        await websocket.accept()

        connection_id = str(uuid4())
        now = datetime.now(timezone.utc)

        connection = Connection(
            connection_id=connection_id,
            websocket=websocket,
            user_id=user_id,
            user_name=user_name,
            user_color=self._get_next_color(),
            connected_at=now,
            last_ping=now,
        )

        async with self._lock:
            self._connections[connection_id] = connection

            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)

        # Send connect confirmation
        await self.send_to_connection(
            connection_id,
            ConnectEvent(
                connection_id=connection_id,
                user_id=user_id,
            ),
        )

        logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")
        return connection

    async def disconnect(self, connection_id: str, reason: Optional[str] = None) -> None:
        """Handle connection disconnection.

        Args:
            connection_id: Connection to disconnect
            reason: Optional disconnect reason
        """
        async with self._lock:
            connection = self._connections.pop(connection_id, None)
            if not connection:
                return

            # Remove from user connections
            if connection.user_id in self._user_connections:
                self._user_connections[connection.user_id].discard(connection_id)
                if not self._user_connections[connection.user_id]:
                    del self._user_connections[connection.user_id]

            # Unsubscribe from all channels
            for channel in list(connection.subscriptions):
                await self._unsubscribe_internal(connection_id, channel)

        logger.info(f"WebSocket disconnected: {connection_id} (reason: {reason})")

    async def subscribe(self, connection_id: str, channel: str) -> bool:
        """Subscribe a connection to a channel.

        Args:
            connection_id: Connection ID
            channel: Channel name (e.g., "table:uuid")

        Returns:
            True if subscribed, False if connection not found
        """
        async with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return False

            connection.subscriptions.add(channel)

            if channel not in self._channel_subscribers:
                self._channel_subscribers[channel] = set()
            self._channel_subscribers[channel].add(connection_id)

        # Send confirmation
        await self.send_to_connection(
            connection_id,
            SubscribedEvent(
                channel=channel,
                presence_count=len(self._channel_subscribers.get(channel, set())),
            ),
        )

        logger.debug(f"Connection {connection_id} subscribed to {channel}")
        return True

    async def unsubscribe(self, connection_id: str, channel: str) -> bool:
        """Unsubscribe a connection from a channel.

        Args:
            connection_id: Connection ID
            channel: Channel name

        Returns:
            True if unsubscribed, False if connection not found
        """
        async with self._lock:
            result = await self._unsubscribe_internal(connection_id, channel)

        if result:
            await self.send_to_connection(
                connection_id,
                UnsubscribedEvent(channel=channel),
            )

        return result

    async def _unsubscribe_internal(self, connection_id: str, channel: str) -> bool:
        """Internal unsubscribe without sending confirmation."""
        connection = self._connections.get(connection_id)
        if not connection:
            return False

        connection.subscriptions.discard(channel)

        if channel in self._channel_subscribers:
            self._channel_subscribers[channel].discard(connection_id)
            if not self._channel_subscribers[channel]:
                del self._channel_subscribers[channel]

        logger.debug(f"Connection {connection_id} unsubscribed from {channel}")
        return True

    async def send_to_connection(
        self,
        connection_id: str,
        event: BaseEvent,
    ) -> bool:
        """Send an event to a specific connection.

        Args:
            connection_id: Target connection ID
            event: Event to send

        Returns:
            True if sent, False if connection not found
        """
        connection = self._connections.get(connection_id)
        if not connection:
            return False

        try:
            message = WebSocketMessage.from_event(event)
            await connection.websocket.send_json(message.model_dump(mode="json"))
            return True
        except Exception as e:
            logger.error(f"Failed to send to {connection_id}: {e}")
            # Connection may be dead, schedule disconnect
            asyncio.create_task(self.disconnect(connection_id, str(e)))
            return False

    async def send_to_user(self, user_id: str, event: BaseEvent) -> int:
        """Send an event to all connections of a user.

        Args:
            user_id: Target user ID
            event: Event to send

        Returns:
            Number of connections message was sent to
        """
        connection_ids = self._user_connections.get(user_id, set())
        sent = 0
        for conn_id in connection_ids:
            if await self.send_to_connection(conn_id, event):
                sent += 1
        return sent

    async def broadcast_to_channel(
        self,
        channel: str,
        event: BaseEvent,
        exclude_connection: Optional[str] = None,
    ) -> int:
        """Broadcast an event to all subscribers of a channel.

        Args:
            channel: Target channel
            event: Event to broadcast
            exclude_connection: Optional connection ID to exclude (e.g., sender)

        Returns:
            Number of connections message was sent to
        """
        connection_ids = self._channel_subscribers.get(channel, set())
        sent = 0

        for conn_id in connection_ids:
            if conn_id == exclude_connection:
                continue
            if await self.send_to_connection(conn_id, event):
                sent += 1

        return sent

    async def broadcast_to_all(
        self,
        event: BaseEvent,
        exclude_connection: Optional[str] = None,
    ) -> int:
        """Broadcast an event to all connected clients.

        Args:
            event: Event to broadcast
            exclude_connection: Optional connection ID to exclude

        Returns:
            Number of connections message was sent to
        """
        sent = 0
        for conn_id in self._connections:
            if conn_id == exclude_connection:
                continue
            if await self.send_to_connection(conn_id, event):
                sent += 1
        return sent

    async def handle_ping(self, connection_id: str) -> None:
        """Handle ping from client, update last_ping and send pong."""
        connection = self._connections.get(connection_id)
        if connection:
            connection.last_ping = datetime.now(timezone.utc)
            await self.send_to_connection(connection_id, PongEvent())

    async def send_error(
        self,
        connection_id: str,
        code: str,
        message: str,
        details: Optional[dict] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """Send an error event to a connection."""
        await self.send_to_connection(
            connection_id,
            ErrorEvent(
                code=code,
                message=message,
                details=details,
                request_id=request_id,
            ),
        )

    def get_connection(self, connection_id: str) -> Optional[Connection]:
        """Get a connection by ID."""
        return self._connections.get(connection_id)

    def get_user_connections(self, user_id: str) -> list[Connection]:
        """Get all connections for a user."""
        connection_ids = self._user_connections.get(user_id, set())
        return [self._connections[cid] for cid in connection_ids if cid in self._connections]

    def get_channel_connections(self, channel: str) -> list[Connection]:
        """Get all connections subscribed to a channel."""
        connection_ids = self._channel_subscribers.get(channel, set())
        return [self._connections[cid] for cid in connection_ids if cid in self._connections]

    def get_channel_user_ids(self, channel: str) -> set[str]:
        """Get unique user IDs subscribed to a channel."""
        connections = self.get_channel_connections(channel)
        return {conn.user_id for conn in connections}

    @property
    def connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self._connections)

    @property
    def user_count(self) -> int:
        """Get total number of connected users."""
        return len(self._user_connections)

    def get_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": self.connection_count,
            "total_users": self.user_count,
            "channels": {channel: len(subs) for channel, subs in self._channel_subscribers.items()},
        }

    async def cleanup_dead_connections(self) -> int:
        """Remove connections that haven't pinged recently.

        Should be called periodically (e.g., every 30 seconds).

        Returns:
            Number of connections cleaned up
        """
        dead_connections = [
            conn_id for conn_id, conn in self._connections.items() if not conn.is_alive
        ]

        for conn_id in dead_connections:
            await self.disconnect(conn_id, "ping timeout")

        return len(dead_connections)


# Global connection manager instance
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return manager
