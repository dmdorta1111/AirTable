"""Realtime WebSocket API endpoints.

Provides:
- WebSocket endpoint for real-time collaboration
- REST endpoints for connection stats and presence
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.security import verify_token
from pybase.realtime import get_connection_manager, get_presence_service
from pybase.schemas.realtime import EventType, UserPresence

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================


class ConnectionStats(BaseModel):
    """WebSocket connection statistics."""

    total_connections: int = Field(..., description="Total active WebSocket connections")
    total_users: int = Field(..., description="Total unique users connected")
    channels: dict[str, int] = Field(
        default_factory=dict, description="Channel -> subscriber count mapping"
    )


class PresenceResponse(BaseModel):
    """Presence information for a channel."""

    channel: str = Field(..., description="Channel name")
    users: list[UserPresence] = Field(default_factory=list, description="Users in channel")
    count: int = Field(..., description="Number of users")


class CellFocusInfo(BaseModel):
    """Cell focus information."""

    cell_key: str = Field(..., description="Cell key (record_id:field_id)")
    user_id: str = Field(..., description="User ID with focus")


class ChannelFocusResponse(BaseModel):
    """All cell focus in a channel."""

    channel: str = Field(..., description="Channel name")
    focus: list[CellFocusInfo] = Field(default_factory=list, description="Cell focus entries")


# =============================================================================
# WebSocket Endpoint
# =============================================================================


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket endpoint for real-time collaboration.

    Connect with: ws://host/api/v1/realtime/ws?token=<jwt_token>

    ## Message Protocol

    All messages are JSON with format:
    ```json
    {"type": "event_type", "payload": {...}, "request_id": "optional"}
    ```

    ## Client -> Server Messages

    - **ping**: Keepalive ping
      ```json
      {"type": "ping"}
      ```

    - **subscribe**: Subscribe to channel
      ```json
      {"type": "subscribe", "payload": {"channel": "table:uuid"}}
      ```

    - **unsubscribe**: Unsubscribe from channel
      ```json
      {"type": "unsubscribe", "payload": {"channel": "table:uuid"}}
      ```

    - **presence_update**: Update presence
      ```json
      {"type": "presence.update", "payload": {"current_view_id": "uuid"}}
      ```

    - **cell_focus**: Focus on a cell
      ```json
      {"type": "cell.focus", "payload": {"table_id": "...", "view_id": "...", "record_id": "...", "field_id": "..."}}
      ```

    - **cell_blur**: Blur from a cell
      ```json
      {"type": "cell.blur", "payload": {"table_id": "...", "view_id": "...", "record_id": "...", "field_id": "..."}}
      ```

    - **cursor_move**: Move cursor
      ```json
      {"type": "cursor.move", "payload": {"table_id": "...", "view_id": "...", "position": {...}}}
      ```

    - **selection_change**: Change selection
      ```json
      {"type": "selection.change", "payload": {"table_id": "...", "view_id": "...", "selection": {...}}}
      ```

    ## Server -> Client Messages

    - **connect**: Connection established
    - **pong**: Response to ping
    - **subscribed**: Subscription confirmed
    - **unsubscribed**: Unsubscription confirmed
    - **error**: Error occurred
    - **presence.join**: User joined channel
    - **presence.leave**: User left channel
    - **presence.state**: Full presence state
    - **presence.update**: User presence updated
    - **cell.focus**: User focused on cell
    - **cell.blur**: User blurred from cell
    - **cursor.move**: User moved cursor
    - **selection.change**: User changed selection
    - **record.created/updated/deleted**: Record changes
    - **field.created/updated/deleted**: Field changes
    - **view.created/updated/deleted**: View changes
    - **dashboard.created/updated/deleted**: Dashboard changes
    """
    manager = get_connection_manager()
    presence = get_presence_service()

    # Authenticate via token
    payload = await verify_token(token, token_type="access")
    if payload is None:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user_id = str(payload.sub)
    user_name = payload.name or f"User {user_id[:8]}"

    # Accept connection
    connection = await manager.connect(websocket, user_id, user_name)
    connection_id = connection.connection_id

    try:
        while True:
            # Receive message
            try:
                data = await websocket.receive_json()
            except json.JSONDecodeError:
                await manager.send_error(
                    connection_id,
                    code="invalid_json",
                    message="Invalid JSON message",
                )
                continue

            # Parse message
            msg_type = data.get("type", "")
            payload_data = data.get("payload", {})
            request_id = data.get("request_id")

            # Handle message types
            try:
                await _handle_message(
                    manager,
                    presence,
                    connection_id,
                    msg_type,
                    payload_data,
                    request_id,
                )
            except Exception as e:
                logger.exception(f"Error handling message: {e}")
                await manager.send_error(
                    connection_id,
                    code="internal_error",
                    message=str(e),
                    request_id=request_id,
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
    finally:
        # Clean up subscriptions and notify presence
        for channel in list(connection.subscriptions):
            await presence.handle_leave(connection_id, channel)
        await manager.disconnect(connection_id)


async def _handle_message(
    manager: Any,
    presence: Any,
    connection_id: str,
    msg_type: str,
    payload: dict[str, Any],
    request_id: str | None,
) -> None:
    """Handle incoming WebSocket message."""

    # Ping
    if msg_type == EventType.PING.value:
        await manager.handle_ping(connection_id)
        return

    # Subscribe
    if msg_type == EventType.SUBSCRIBE.value:
        channel = payload.get("channel")
        if not channel:
            await manager.send_error(
                connection_id,
                code="missing_channel",
                message="Channel is required for subscribe",
                request_id=request_id,
            )
            return

        # Validate channel format
        if not _validate_channel(channel):
            await manager.send_error(
                connection_id,
                code="invalid_channel",
                message=f"Invalid channel format: {channel}",
                request_id=request_id,
            )
            return

        await manager.subscribe(connection_id, channel)
        await presence.handle_join(connection_id, channel)
        return

    # Unsubscribe
    if msg_type == EventType.UNSUBSCRIBE.value:
        channel = payload.get("channel")
        if not channel:
            await manager.send_error(
                connection_id,
                code="missing_channel",
                message="Channel is required for unsubscribe",
                request_id=request_id,
            )
            return

        await presence.handle_leave(connection_id, channel)
        await manager.unsubscribe(connection_id, channel)
        return

    # Presence update
    if msg_type == EventType.PRESENCE_UPDATE.value:
        await presence.update_presence(
            connection_id,
            current_view_id=payload.get("current_view_id"),
            current_record_id=payload.get("current_record_id"),
            cursor_position=payload.get("cursor_position"),
        )
        return

    # Cell focus
    if msg_type == EventType.CELL_FOCUS.value:
        required = ["table_id", "view_id", "record_id", "field_id"]
        if not all(k in payload for k in required):
            await manager.send_error(
                connection_id,
                code="missing_fields",
                message=f"Required fields: {required}",
                request_id=request_id,
            )
            return

        await presence.handle_cell_focus(
            connection_id,
            payload["table_id"],
            payload["view_id"],
            payload["record_id"],
            payload["field_id"],
        )
        return

    # Cell blur
    if msg_type == EventType.CELL_BLUR.value:
        required = ["table_id", "view_id", "record_id", "field_id"]
        if not all(k in payload for k in required):
            await manager.send_error(
                connection_id,
                code="missing_fields",
                message=f"Required fields: {required}",
                request_id=request_id,
            )
            return

        await presence.handle_cell_blur(
            connection_id,
            payload["table_id"],
            payload["view_id"],
            payload["record_id"],
            payload["field_id"],
        )
        return

    # Cursor move
    if msg_type == EventType.CURSOR_MOVE.value:
        required = ["table_id", "view_id", "position"]
        if not all(k in payload for k in required):
            await manager.send_error(
                connection_id,
                code="missing_fields",
                message=f"Required fields: {required}",
                request_id=request_id,
            )
            return

        await presence.handle_cursor_move(
            connection_id,
            payload["table_id"],
            payload["view_id"],
            payload["position"],
        )
        return

    # Selection change
    if msg_type == EventType.SELECTION_CHANGE.value:
        required = ["table_id", "view_id", "selection"]
        if not all(k in payload for k in required):
            await manager.send_error(
                connection_id,
                code="missing_fields",
                message=f"Required fields: {required}",
                request_id=request_id,
            )
            return

        await presence.handle_selection_change(
            connection_id,
            payload["table_id"],
            payload["view_id"],
            payload["selection"],
        )
        return

    # Unknown message type
    await manager.send_error(
        connection_id,
        code="unknown_message_type",
        message=f"Unknown message type: {msg_type}",
        request_id=request_id,
    )


def _validate_channel(channel: str) -> bool:
    """Validate channel format."""
    valid_prefixes = ["workspace:", "base:", "table:", "view:", "record:", "user:"]
    return any(channel.startswith(prefix) for prefix in valid_prefixes)


# =============================================================================
# REST Endpoints
# =============================================================================


@router.get("/stats", response_model=ConnectionStats)
async def get_connection_stats(
    current_user: CurrentUser,
) -> ConnectionStats:
    """
    Get WebSocket connection statistics.

    Returns total connections, users, and channel subscriber counts.
    Requires authentication.
    """
    manager = get_connection_manager()
    stats = manager.get_stats()

    return ConnectionStats(
        total_connections=stats["total_connections"],
        total_users=stats["total_users"],
        channels=stats["channels"],
    )


@router.get("/presence/{channel:path}", response_model=PresenceResponse)
async def get_channel_presence(
    channel: str,
    current_user: CurrentUser,
) -> PresenceResponse:
    """
    Get presence information for a channel.

    Returns list of users currently in the channel.

    Args:
        channel: Channel name (e.g., "table:uuid")
    """
    if not _validate_channel(channel):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel format: {channel}",
        )

    presence = get_presence_service()
    users = presence.get_users_in_channel(channel)

    return PresenceResponse(
        channel=channel,
        users=users,
        count=len(users),
    )


@router.get("/presence/{channel:path}/focus", response_model=ChannelFocusResponse)
async def get_channel_cell_focus(
    channel: str,
    current_user: CurrentUser,
) -> ChannelFocusResponse:
    """
    Get all cell focus for a channel.

    Returns which cells are being edited by which users.

    Args:
        channel: Channel name (e.g., "table:uuid")
    """
    if not _validate_channel(channel):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel format: {channel}",
        )

    presence = get_presence_service()
    focus_data = presence.get_channel_cell_focus(channel)

    focus_list = [
        CellFocusInfo(cell_key=cell_key, user_id=user_id)
        for cell_key, user_id in focus_data.items()
    ]

    return ChannelFocusResponse(
        channel=channel,
        focus=focus_list,
    )


@router.post("/broadcast/{channel:path}")
async def broadcast_to_channel(
    channel: str,
    message: dict[str, Any],
    current_user: CurrentUser,
) -> dict[str, int]:
    """
    Broadcast a message to all subscribers of a channel.

    This is primarily for server-to-client notifications.
    Clients should use WebSocket messages for collaboration events.

    Args:
        channel: Channel name
        message: Message payload to broadcast

    Returns:
        Number of connections message was sent to
    """
    if not _validate_channel(channel):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel format: {channel}",
        )

    # Import here to avoid circular imports
    from pybase.schemas.realtime import ActivityEvent, EventType

    manager = get_connection_manager()

    # Create activity event
    event = ActivityEvent(
        activity_type=message.get("type", "custom"),
        entity_type=message.get("entity_type", "unknown"),
        entity_id=message.get("entity_id", ""),
        entity_name=message.get("entity_name"),
        user_id=str(current_user.id),
        user_name=current_user.display_name or current_user.email,
        description=message.get("description", ""),
        metadata=message.get("metadata"),
    )

    sent_count = await manager.broadcast_to_channel(channel, event)

    return {"sent_to": sent_count}


# =============================================================================
# Background Cleanup Task
# =============================================================================


async def cleanup_dead_connections_task() -> None:
    """Background task to clean up dead connections periodically."""
    manager = get_connection_manager()

    while True:
        try:
            cleaned = await manager.cleanup_dead_connections()
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} dead WebSocket connections")
        except Exception as e:
            logger.error(f"Error cleaning up connections: {e}")

        # Run every 30 seconds
        await asyncio.sleep(30)


def start_cleanup_task() -> asyncio.Task:
    """Start the background cleanup task."""
    return asyncio.create_task(cleanup_dead_connections_task())
