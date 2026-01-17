"""Realtime module for WebSocket-based collaboration.

Provides:
- ConnectionManager: Handles WebSocket connections, subscriptions, broadcasting
- PresenceService: Tracks user presence, cell focus, cursor positions
"""

from pybase.realtime.manager import Connection, ConnectionManager, get_connection_manager
from pybase.realtime.presence import PresenceService, get_presence_service

__all__ = [
    "Connection",
    "ConnectionManager",
    "get_connection_manager",
    "PresenceService",
    "get_presence_service",
]
