"""Presence service for tracking user activity and location.

Handles:
- User presence tracking (online/away/offline)
- Current location tracking (what view/record user is looking at)
- Cursor/selection tracking for collaborative editing
- Activity feed generation
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from pybase.realtime.manager import Connection, ConnectionManager, get_connection_manager
from pybase.schemas.realtime import (
    CellBlurEvent,
    CellFocusEvent,
    CursorMoveEvent,
    PresenceJoinEvent,
    PresenceLeaveEvent,
    PresenceStateEvent,
    PresenceUpdateEvent,
    SelectionChangeEvent,
    UserPresence,
)

logger = logging.getLogger(__name__)


class PresenceService:
    """Service for tracking and broadcasting user presence."""

    def __init__(self, manager: Optional[ConnectionManager] = None):
        self._manager = manager or get_connection_manager()
        # Track cell focus: channel -> {cell_key: user_id}
        # cell_key = f"{record_id}:{field_id}"
        self._cell_focus: dict[str, dict[str, str]] = {}

    def _connection_to_presence(self, connection: Connection) -> UserPresence:
        """Convert a Connection to UserPresence."""
        return UserPresence(
            user_id=connection.user_id,
            name=connection.user_name,
            avatar_url=connection.metadata.get("avatar_url"),
            color=connection.user_color,
            online_at=connection.connected_at,
            last_seen_at=connection.last_ping,
            current_view_id=connection.metadata.get("current_view_id"),
            current_record_id=connection.metadata.get("current_record_id"),
            cursor_position=connection.metadata.get("cursor_position"),
        )

    async def handle_join(self, connection_id: str, channel: str) -> None:
        """Handle a user joining a channel - broadcast presence.

        Args:
            connection_id: Connection that joined
            channel: Channel joined
        """
        connection = self._manager.get_connection(connection_id)
        if not connection:
            return

        presence = self._connection_to_presence(connection)

        # Broadcast join to other subscribers
        await self._manager.broadcast_to_channel(
            channel,
            PresenceJoinEvent(
                channel=channel,
                user=presence,
            ),
            exclude_connection=connection_id,
        )

        # Send current presence state to the new subscriber
        await self.send_presence_state(connection_id, channel)

    async def handle_leave(self, connection_id: str, channel: str) -> None:
        """Handle a user leaving a channel - broadcast departure.

        Args:
            connection_id: Connection that left
            channel: Channel left
        """
        connection = self._manager.get_connection(connection_id)
        if not connection:
            return

        # Clear any cell focus for this user in this channel
        await self._clear_user_cell_focus(channel, connection.user_id)

        # Broadcast leave to remaining subscribers
        await self._manager.broadcast_to_channel(
            channel,
            PresenceLeaveEvent(
                channel=channel,
                user_id=connection.user_id,
            ),
            exclude_connection=connection_id,
        )

    async def send_presence_state(self, connection_id: str, channel: str) -> None:
        """Send the current presence state of a channel to a connection.

        Args:
            connection_id: Connection to send to
            channel: Channel to get presence for
        """
        connections = self._manager.get_channel_connections(channel)

        # Build unique users (avoid duplicates from multiple tabs)
        users_seen: set[str] = set()
        users: list[UserPresence] = []

        for conn in connections:
            if conn.user_id not in users_seen:
                users_seen.add(conn.user_id)
                users.append(self._connection_to_presence(conn))

        await self._manager.send_to_connection(
            connection_id,
            PresenceStateEvent(
                channel=channel,
                users=users,
            ),
        )

    async def update_presence(
        self,
        connection_id: str,
        current_view_id: Optional[str] = None,
        current_record_id: Optional[str] = None,
        cursor_position: Optional[dict[str, Any]] = None,
    ) -> None:
        """Update a user's presence information.

        Args:
            connection_id: Connection to update
            current_view_id: View user is currently in
            current_record_id: Record user is currently editing
            cursor_position: Cursor position data
        """
        connection = self._manager.get_connection(connection_id)
        if not connection:
            return

        # Update metadata
        if current_view_id is not None:
            connection.metadata["current_view_id"] = current_view_id
        if current_record_id is not None:
            connection.metadata["current_record_id"] = current_record_id
        if cursor_position is not None:
            connection.metadata["cursor_position"] = cursor_position

        connection.last_ping = datetime.now(timezone.utc)

        # Broadcast update to all subscribed channels
        presence = self._connection_to_presence(connection)
        for channel in connection.subscriptions:
            await self._manager.broadcast_to_channel(
                channel,
                PresenceUpdateEvent(
                    channel=channel,
                    user=presence,
                ),
                exclude_connection=connection_id,
            )

    async def handle_cell_focus(
        self,
        connection_id: str,
        table_id: str,
        view_id: str,
        record_id: str,
        field_id: str,
    ) -> None:
        """Handle a user focusing on a cell.

        Args:
            connection_id: Connection that focused
            table_id: Table ID
            view_id: View ID
            record_id: Record ID
            field_id: Field ID
        """
        connection = self._manager.get_connection(connection_id)
        if not connection:
            return

        channel = f"table:{table_id}"
        cell_key = f"{record_id}:{field_id}"

        # Track the focus
        if channel not in self._cell_focus:
            self._cell_focus[channel] = {}

        # Clear previous focus for this user
        await self._clear_user_cell_focus(channel, connection.user_id)

        # Set new focus
        self._cell_focus[channel][cell_key] = connection.user_id

        # Update presence metadata
        connection.metadata["current_record_id"] = record_id

        # Broadcast focus event
        await self._manager.broadcast_to_channel(
            channel,
            CellFocusEvent(
                table_id=table_id,
                view_id=view_id,
                record_id=record_id,
                field_id=field_id,
                user_id=connection.user_id,
                user_color=connection.user_color,
            ),
            exclude_connection=connection_id,
        )

    async def handle_cell_blur(
        self,
        connection_id: str,
        table_id: str,
        view_id: str,
        record_id: str,
        field_id: str,
    ) -> None:
        """Handle a user blurring from a cell.

        Args:
            connection_id: Connection that blurred
            table_id: Table ID
            view_id: View ID
            record_id: Record ID
            field_id: Field ID
        """
        connection = self._manager.get_connection(connection_id)
        if not connection:
            return

        channel = f"table:{table_id}"
        cell_key = f"{record_id}:{field_id}"

        # Clear the focus
        if channel in self._cell_focus:
            self._cell_focus[channel].pop(cell_key, None)

        # Update presence metadata
        connection.metadata.pop("current_record_id", None)

        # Broadcast blur event
        await self._manager.broadcast_to_channel(
            channel,
            CellBlurEvent(
                table_id=table_id,
                view_id=view_id,
                record_id=record_id,
                field_id=field_id,
                user_id=connection.user_id,
            ),
            exclude_connection=connection_id,
        )

    async def handle_cursor_move(
        self,
        connection_id: str,
        table_id: str,
        view_id: str,
        position: dict[str, Any],
    ) -> None:
        """Handle cursor movement for collaborative editing.

        Args:
            connection_id: Connection that moved cursor
            table_id: Table ID
            view_id: View ID
            position: Cursor position data
        """
        connection = self._manager.get_connection(connection_id)
        if not connection:
            return

        channel = f"table:{table_id}"

        # Update presence metadata
        connection.metadata["cursor_position"] = position

        # Broadcast cursor move
        await self._manager.broadcast_to_channel(
            channel,
            CursorMoveEvent(
                table_id=table_id,
                view_id=view_id,
                user_id=connection.user_id,
                user_color=connection.user_color,
                position=position,
            ),
            exclude_connection=connection_id,
        )

    async def handle_selection_change(
        self,
        connection_id: str,
        table_id: str,
        view_id: str,
        selection: dict[str, Any],
    ) -> None:
        """Handle selection changes (rows, cells, ranges).

        Args:
            connection_id: Connection that changed selection
            table_id: Table ID
            view_id: View ID
            selection: Selection data (rows, cells, range)
        """
        connection = self._manager.get_connection(connection_id)
        if not connection:
            return

        channel = f"table:{table_id}"

        # Broadcast selection change
        await self._manager.broadcast_to_channel(
            channel,
            SelectionChangeEvent(
                table_id=table_id,
                view_id=view_id,
                user_id=connection.user_id,
                user_color=connection.user_color,
                selection=selection,
            ),
            exclude_connection=connection_id,
        )

    async def _clear_user_cell_focus(self, channel: str, user_id: str) -> None:
        """Clear all cell focus for a user in a channel."""
        if channel not in self._cell_focus:
            return

        # Find and remove all focus entries for this user
        keys_to_remove = [key for key, uid in self._cell_focus[channel].items() if uid == user_id]
        for key in keys_to_remove:
            del self._cell_focus[channel][key]

    def get_cell_focus(self, channel: str, record_id: str, field_id: str) -> Optional[str]:
        """Get user ID that has focus on a cell, if any.

        Args:
            channel: Channel (table:uuid)
            record_id: Record ID
            field_id: Field ID

        Returns:
            User ID or None
        """
        cell_key = f"{record_id}:{field_id}"
        return self._cell_focus.get(channel, {}).get(cell_key)

    def get_channel_cell_focus(self, channel: str) -> dict[str, str]:
        """Get all cell focus for a channel.

        Args:
            channel: Channel (table:uuid)

        Returns:
            Dict of cell_key -> user_id
        """
        return self._cell_focus.get(channel, {}).copy()

    def get_users_in_channel(self, channel: str) -> list[UserPresence]:
        """Get all unique users in a channel.

        Args:
            channel: Channel name

        Returns:
            List of user presence data
        """
        connections = self._manager.get_channel_connections(channel)

        users_seen: set[str] = set()
        users: list[UserPresence] = []

        for conn in connections:
            if conn.user_id not in users_seen:
                users_seen.add(conn.user_id)
                users.append(self._connection_to_presence(conn))

        return users

    def is_user_in_channel(self, channel: str, user_id: str) -> bool:
        """Check if a user is in a channel.

        Args:
            channel: Channel name
            user_id: User ID to check

        Returns:
            True if user is in channel
        """
        user_ids = self._manager.get_channel_user_ids(channel)
        return user_id in user_ids


# Global presence service instance
_presence_service: Optional[PresenceService] = None


def get_presence_service() -> PresenceService:
    """Get the global presence service instance."""
    global _presence_service
    if _presence_service is None:
        _presence_service = PresenceService()
    return _presence_service
