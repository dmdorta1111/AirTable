"""Realtime event schemas for WebSocket communication."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Event Types
# =============================================================================


class EventType(str, Enum):
    """Types of realtime events."""

    # Connection events
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"

    # Subscription events
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"

    # Presence events
    PRESENCE_JOIN = "presence.join"
    PRESENCE_LEAVE = "presence.leave"
    PRESENCE_UPDATE = "presence.update"
    PRESENCE_STATE = "presence.state"

    # Record events
    RECORD_CREATED = "record.created"
    RECORD_UPDATED = "record.updated"
    RECORD_DELETED = "record.deleted"
    RECORD_BATCH_CREATED = "record.batch_created"
    RECORD_BATCH_UPDATED = "record.batch_updated"
    RECORD_BATCH_DELETED = "record.batch_deleted"

    # Field events
    FIELD_CREATED = "field.created"
    FIELD_UPDATED = "field.updated"
    FIELD_DELETED = "field.deleted"
    FIELD_REORDERED = "field.reordered"

    # View events
    VIEW_CREATED = "view.created"
    VIEW_UPDATED = "view.updated"
    VIEW_DELETED = "view.deleted"

    # Table events
    TABLE_CREATED = "table.created"
    TABLE_UPDATED = "table.updated"
    TABLE_DELETED = "table.deleted"

    # Dashboard events
    DASHBOARD_CREATED = "dashboard.created"
    DASHBOARD_UPDATED = "dashboard.updated"
    DASHBOARD_DELETED = "dashboard.deleted"

    # Chart events
    CHART_UPDATED = "chart.updated"
    CHART_DATA_CHANGED = "chart.data_changed"

    # Collaboration events
    CELL_FOCUS = "cell.focus"
    CELL_BLUR = "cell.blur"
    CURSOR_MOVE = "cursor.move"
    SELECTION_CHANGE = "selection.change"

    # Activity events
    ACTIVITY = "activity"

    # Undo/Redo events
    OPERATION_UNDONE = "operation.undone"
    OPERATION_REDONE = "operation.redone"


class ChannelType(str, Enum):
    """Types of channels to subscribe to."""

    WORKSPACE = "workspace"  # workspace:{workspace_id}
    BASE = "base"  # base:{base_id}
    TABLE = "table"  # table:{table_id}
    VIEW = "view"  # view:{view_id}
    RECORD = "record"  # record:{record_id}
    DASHBOARD = "dashboard"  # dashboard:{dashboard_id}
    USER = "user"  # user:{user_id} - personal notifications


# =============================================================================
# Base Event Schema
# =============================================================================


class BaseEvent(BaseModel):
    """Base schema for all realtime events."""

    event: EventType = Field(..., description="Event type")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    request_id: Optional[str] = Field(None, description="Client request ID for correlation")


# =============================================================================
# Connection Events
# =============================================================================


class ConnectEvent(BaseEvent):
    """Event sent when connection is established."""

    event: EventType = EventType.CONNECT
    connection_id: str = Field(..., description="Unique connection identifier")
    user_id: str = Field(..., description="Authenticated user ID")


class DisconnectEvent(BaseEvent):
    """Event sent when connection is closed."""

    event: EventType = EventType.DISCONNECT
    reason: Optional[str] = Field(None, description="Disconnect reason")


class PingEvent(BaseEvent):
    """Ping event for connection keepalive."""

    event: EventType = EventType.PING


class PongEvent(BaseEvent):
    """Pong response to ping."""

    event: EventType = EventType.PONG


class ErrorEvent(BaseEvent):
    """Error event."""

    event: EventType = EventType.ERROR
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional error details")


# =============================================================================
# Subscription Events
# =============================================================================


class SubscribeRequest(BaseEvent):
    """Request to subscribe to a channel."""

    event: EventType = EventType.SUBSCRIBE
    channel: str = Field(..., description="Channel to subscribe to (e.g., 'table:uuid')")


class UnsubscribeRequest(BaseEvent):
    """Request to unsubscribe from a channel."""

    event: EventType = EventType.UNSUBSCRIBE
    channel: str = Field(..., description="Channel to unsubscribe from")


class SubscribedEvent(BaseEvent):
    """Confirmation of successful subscription."""

    event: EventType = EventType.SUBSCRIBED
    channel: str = Field(..., description="Channel subscribed to")
    presence_count: int = Field(default=0, description="Number of users in channel")


class UnsubscribedEvent(BaseEvent):
    """Confirmation of successful unsubscription."""

    event: EventType = EventType.UNSUBSCRIBED
    channel: str = Field(..., description="Channel unsubscribed from")


# =============================================================================
# Presence Events
# =============================================================================


class UserPresence(BaseModel):
    """User presence information."""

    user_id: str = Field(..., description="User ID")
    name: str = Field(..., description="User display name")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")
    color: str = Field(..., description="User color for UI (hex)")
    online_at: datetime = Field(..., description="When user came online")
    last_seen_at: datetime = Field(..., description="Last activity timestamp")
    current_view_id: Optional[str] = Field(None, description="View user is currently viewing")
    current_record_id: Optional[str] = Field(None, description="Record user is currently editing")
    cursor_position: Optional[dict[str, Any]] = Field(None, description="Cursor/selection position")


class PresenceJoinEvent(BaseEvent):
    """Event when a user joins a channel."""

    event: EventType = EventType.PRESENCE_JOIN
    channel: str = Field(..., description="Channel joined")
    user: UserPresence = Field(..., description="User who joined")


class PresenceLeaveEvent(BaseEvent):
    """Event when a user leaves a channel."""

    event: EventType = EventType.PRESENCE_LEAVE
    channel: str = Field(..., description="Channel left")
    user_id: str = Field(..., description="User who left")


class PresenceUpdateEvent(BaseEvent):
    """Event when a user's presence info changes."""

    event: EventType = EventType.PRESENCE_UPDATE
    channel: str = Field(..., description="Channel")
    user: UserPresence = Field(..., description="Updated user presence")


class PresenceStateEvent(BaseEvent):
    """Full presence state for a channel."""

    event: EventType = EventType.PRESENCE_STATE
    channel: str = Field(..., description="Channel")
    users: list[UserPresence] = Field(default_factory=list, description="All users in channel")


# =============================================================================
# Data Change Events
# =============================================================================


class RecordChangeEvent(BaseEvent):
    """Event for record changes."""

    event: EventType  # RECORD_CREATED, RECORD_UPDATED, RECORD_DELETED
    table_id: str = Field(..., description="Table ID")
    record_id: str = Field(..., description="Record ID")
    data: Optional[dict[str, Any]] = Field(None, description="Record data (for create/update)")
    changed_fields: Optional[list[str]] = Field(
        None, description="Fields that changed (for update)"
    )
    changed_by: str = Field(..., description="User ID who made the change")


class RecordBatchChangeEvent(BaseEvent):
    """Event for batch record changes."""

    event: EventType  # RECORD_BATCH_CREATED, RECORD_BATCH_UPDATED, RECORD_BATCH_DELETED
    table_id: str = Field(..., description="Table ID")
    record_ids: list[str] = Field(..., description="Record IDs affected")
    count: int = Field(..., description="Number of records affected")
    changed_by: str = Field(..., description="User ID who made the change")


class FieldChangeEvent(BaseEvent):
    """Event for field changes."""

    event: EventType  # FIELD_CREATED, FIELD_UPDATED, FIELD_DELETED
    table_id: str = Field(..., description="Table ID")
    field_id: str = Field(..., description="Field ID")
    data: Optional[dict[str, Any]] = Field(None, description="Field data")
    changed_by: str = Field(..., description="User ID who made the change")


class FieldReorderedEvent(BaseEvent):
    """Event for field reordering."""

    event: EventType = EventType.FIELD_REORDERED
    table_id: str = Field(..., description="Table ID")
    field_order: list[str] = Field(..., description="New field order (field IDs)")
    changed_by: str = Field(..., description="User ID who made the change")


class ViewChangeEvent(BaseEvent):
    """Event for view changes."""

    event: EventType  # VIEW_CREATED, VIEW_UPDATED, VIEW_DELETED
    table_id: str = Field(..., description="Table ID")
    view_id: str = Field(..., description="View ID")
    data: Optional[dict[str, Any]] = Field(None, description="View data")
    changed_by: str = Field(..., description="User ID who made the change")


class TableChangeEvent(BaseEvent):
    """Event for table changes."""

    event: EventType  # TABLE_CREATED, TABLE_UPDATED, TABLE_DELETED
    base_id: str = Field(..., description="Base ID")
    table_id: str = Field(..., description="Table ID")
    data: Optional[dict[str, Any]] = Field(None, description="Table data")
    changed_by: str = Field(..., description="User ID who made the change")


class DashboardChangeEvent(BaseEvent):
    """Event for dashboard changes."""

    event: EventType  # DASHBOARD_CREATED, DASHBOARD_UPDATED, DASHBOARD_DELETED
    base_id: str = Field(..., description="Base ID")
    dashboard_id: str = Field(..., description="Dashboard ID")
    data: Optional[dict[str, Any]] = Field(None, description="Dashboard data")
    changed_by: str = Field(..., description="User ID who made the change")


class ChartDataChangeEvent(BaseEvent):
    """Event for chart data changes (when underlying records change)."""

    event: EventType = EventType.CHART_DATA_CHANGED
    table_id: str = Field(..., description="Table ID whose records changed")
    chart_ids: list[str] = Field(default_factory=list, description="Affected chart IDs")
    changed_by: str = Field(..., description="User ID who made the change")


# =============================================================================
# Collaboration Events
# =============================================================================


class CellFocusEvent(BaseEvent):
    """Event when a user focuses on a cell."""

    event: EventType = EventType.CELL_FOCUS
    table_id: str = Field(..., description="Table ID")
    view_id: str = Field(..., description="View ID")
    record_id: str = Field(..., description="Record ID")
    field_id: str = Field(..., description="Field ID")
    user_id: str = Field(..., description="User who focused")
    user_color: str = Field(..., description="User's assigned color")


class CellBlurEvent(BaseEvent):
    """Event when a user blurs from a cell."""

    event: EventType = EventType.CELL_BLUR
    table_id: str = Field(..., description="Table ID")
    view_id: str = Field(..., description="View ID")
    record_id: str = Field(..., description="Record ID")
    field_id: str = Field(..., description="Field ID")
    user_id: str = Field(..., description="User who blurred")


class CursorMoveEvent(BaseEvent):
    """Event for cursor movement (for collaborative editing)."""

    event: EventType = EventType.CURSOR_MOVE
    table_id: str = Field(..., description="Table ID")
    view_id: str = Field(..., description="View ID")
    user_id: str = Field(..., description="User ID")
    user_color: str = Field(..., description="User's assigned color")
    position: dict[str, Any] = Field(..., description="Cursor position data")


class SelectionChangeEvent(BaseEvent):
    """Event for selection changes (rows, cells)."""

    event: EventType = EventType.SELECTION_CHANGE
    table_id: str = Field(..., description="Table ID")
    view_id: str = Field(..., description="View ID")
    user_id: str = Field(..., description="User ID")
    user_color: str = Field(..., description="User's assigned color")
    selection: dict[str, Any] = Field(..., description="Selection data (rows, cells, range)")


# =============================================================================
# Activity Events
# =============================================================================


class ActivityEvent(BaseEvent):
    """General activity event for activity feed."""

    event: EventType = EventType.ACTIVITY
    activity_type: str = Field(..., description="Activity type (e.g., 'record.created')")
    entity_type: str = Field(..., description="Entity type (record, field, view, table)")
    entity_id: str = Field(..., description="Entity ID")
    entity_name: Optional[str] = Field(None, description="Entity name for display")
    user_id: str = Field(..., description="User who performed the action")
    user_name: str = Field(..., description="User display name")
    description: str = Field(..., description="Human-readable activity description")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional activity metadata")


# =============================================================================
# Undo/Redo Events
# =============================================================================


class OperationUndoneEvent(BaseEvent):
    """Event when an operation is undone."""

    event: EventType = EventType.OPERATION_UNDONE
    operation_id: str = Field(..., description="Operation log ID that was undone")
    operation_type: str = Field(..., description="Type of operation (create, update, delete)")
    entity_type: str = Field(..., description="Entity type (record, field, view)")
    entity_id: str = Field(..., description="Entity ID affected")
    table_id: Optional[str] = Field(None, description="Table ID (for record/field/view operations)")
    undone_by: str = Field(..., description="User ID who undid the operation")
    undone_by_name: str = Field(..., description="Display name of user who undid the operation")
    before_data: Optional[dict[str, Any]] = Field(None, description="State before undo (after original op)")
    after_data: Optional[dict[str, Any]] = Field(None, description="State after undo (before original op)")


class OperationRedoneEvent(BaseEvent):
    """Event when an operation is redone."""

    event: EventType = EventType.OPERATION_REDONE
    operation_id: str = Field(..., description="Operation log ID that was redone")
    operation_type: str = Field(..., description="Type of operation (create, update, delete)")
    entity_type: str = Field(..., description="Entity type (record, field, view)")
    entity_id: str = Field(..., description="Entity ID affected")
    table_id: Optional[str] = Field(None, description="Table ID (for record/field/view operations)")
    redone_by: str = Field(..., description="User ID who redid the operation")
    redone_by_name: str = Field(..., description="Display name of user who redid the operation")
    before_data: Optional[dict[str, Any]] = Field(None, description="State before redo (before original op)")
    after_data: Optional[dict[str, Any]] = Field(None, description="State after redo (after original op)")


# =============================================================================
# WebSocket Message Wrapper
# =============================================================================


class WebSocketMessage(BaseModel):
    """Generic WebSocket message wrapper for sending/receiving."""

    type: str = Field(..., description="Message type (event type)")
    payload: dict[str, Any] = Field(..., description="Event payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = Field(None, description="Client request ID")

    @classmethod
    def from_event(cls, event: BaseEvent) -> "WebSocketMessage":
        """Create WebSocket message from an event."""
        return cls(
            type=event.event.value,
            payload=event.model_dump(exclude={"event", "timestamp", "request_id"}),
            timestamp=event.timestamp,
            request_id=event.request_id,
        )
