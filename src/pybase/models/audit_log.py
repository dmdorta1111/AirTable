"""
Audit Log model for tracking all system changes.

Provides tamper-evident audit trail for compliance with SOC2, ISO27001, and ITAR.
Logs all CRUD operations, authentication events, and API access.
"""

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import BaseModel

if TYPE_CHECKING:
    from pybase.models.user import User


class AuditAction(str, Enum):
    """Types of auditable actions."""

    # Record operations
    RECORD_CREATE = "record.create"
    RECORD_UPDATE = "record.update"
    RECORD_DELETE = "record.delete"
    RECORD_BULK_CREATE = "record.bulk_create"
    RECORD_BULK_UPDATE = "record.bulk_update"
    RECORD_BULK_DELETE = "record.bulk_delete"

    # Table operations
    TABLE_CREATE = "table.create"
    TABLE_UPDATE = "table.update"
    TABLE_DELETE = "table.delete"

    # Field operations
    FIELD_CREATE = "field.create"
    FIELD_UPDATE = "field.update"
    FIELD_DELETE = "field.delete"

    # View operations
    VIEW_CREATE = "view.create"
    VIEW_UPDATE = "view.update"
    VIEW_DELETE = "view.delete"

    # Authentication events
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_LOGIN_FAILED = "user.login_failed"
    USER_PASSWORD_RESET = "user.password_reset"
    USER_PASSWORD_CHANGED = "user.password_changed"

    # Workspace operations
    WORKSPACE_CREATE = "workspace.create"
    WORKSPACE_UPDATE = "workspace.update"
    WORKSPACE_DELETE = "workspace.delete"
    WORKSPACE_MEMBER_ADD = "workspace.member_add"
    WORKSPACE_MEMBER_REMOVE = "workspace.member_remove"
    WORKSPACE_MEMBER_UPDATE = "workspace.member_update"

    # API key operations
    API_KEY_CREATE = "api_key.create"
    API_KEY_DELETE = "api_key.delete"
    API_KEY_USE = "api_key.use"

    # Automation operations
    AUTOMATION_CREATE = "automation.create"
    AUTOMATION_UPDATE = "automation.update"
    AUTOMATION_DELETE = "automation.delete"
    AUTOMATION_RUN = "automation.run"
    AUTOMATION_RUN_FAILED = "automation.run_failed"

    # Export operations
    EXPORT_CREATE = "export.create"
    EXPORT_DOWNLOAD = "export.download"

    # System operations
    SYSTEM_SETTINGS_UPDATE = "system.settings_update"
    AUDIT_LOG_EXPORT = "audit.export"
    AUDIT_LOG_QUERY = "audit.query"


class AuditLog(BaseModel):
    """
    Audit log entry for tracking system changes.

    Provides tamper-evident storage through hash chaining.
    Once written, audit logs should never be modified or deleted
    (except through retention policy cleanup).
    """

    # Actor information
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )  # Denormalized for historical accuracy

    # Action details
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # e.g., "record", "table", "workspace"
    resource_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        index=True,
    )  # ID of affected resource

    # Table context (for record operations)
    table_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        index=True,
    )

    # Data changes (JSON stored as text)
    old_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # Previous state (for updates/deletes)
    new_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # New state (for creates/updates)

    # Request context
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    request_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )  # For request correlation

    # Tamper-evident storage (hash chain)
    # Each log entry contains a hash of the previous entry
    # This creates a chain where any modification is detectable
    integrity_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )  # SHA-256 hash of this entry
    previous_log_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )  # Hash of the previous log entry

    # Additional context (JSON)
    meta: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_table_action", "table_id", "action"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_integrity", "integrity_hash"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} on {self.resource_type} by {self.user_email}>"

    def to_dict(self) -> dict:
        """Convert audit log to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "table_id": self.table_id,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "integrity_hash": self.integrity_hash,
            "previous_log_hash": self.previous_log_hash,
            "meta": self.meta,
        }
