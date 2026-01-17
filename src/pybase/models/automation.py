"""
Automation models for trigger-based workflows.

Automations consist of:
- Triggers: Events that start the automation
- Actions: Operations performed when triggered
- Runs: Execution history and status
"""

import json
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import BaseModel, SoftDeleteModel

if TYPE_CHECKING:
    from pybase.models.base import Base
    from pybase.models.table import Table
    from pybase.models.user import User


# =============================================================================
# Enums
# =============================================================================


class TriggerType(str, Enum):
    """Types of automation triggers."""

    # Record triggers
    RECORD_CREATED = "record_created"
    RECORD_UPDATED = "record_updated"
    RECORD_DELETED = "record_deleted"
    RECORD_MATCHES_CONDITIONS = "record_matches_conditions"

    # Field triggers
    FIELD_CHANGED = "field_changed"

    # Form triggers
    FORM_SUBMITTED = "form_submitted"

    # Time triggers
    SCHEDULED = "scheduled"  # Cron-based
    AT_SCHEDULED_TIME = "at_scheduled_time"  # One-time

    # External triggers
    WEBHOOK_RECEIVED = "webhook_received"

    # Manual triggers
    BUTTON_CLICKED = "button_clicked"


class ActionType(str, Enum):
    """Types of automation actions."""

    # Record actions
    CREATE_RECORD = "create_record"
    UPDATE_RECORD = "update_record"
    DELETE_RECORD = "delete_record"

    # Notification actions
    SEND_EMAIL = "send_email"
    SEND_SLACK_MESSAGE = "send_slack_message"
    SEND_WEBHOOK = "send_webhook"

    # Linked record actions
    LINK_RECORDS = "link_records"
    UNLINK_RECORDS = "unlink_records"

    # Script actions
    RUN_SCRIPT = "run_script"  # Sandboxed Python/JS

    # Control flow
    CONDITIONAL = "conditional"  # If/else logic
    LOOP = "loop"  # Iterate over records
    DELAY = "delay"  # Wait before continuing

    # Integration actions
    CALL_API = "call_api"


class AutomationRunStatus(str, Enum):
    """Status of an automation run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


# =============================================================================
# Models
# =============================================================================


class Automation(SoftDeleteModel):
    """
    Automation - a trigger-based workflow.

    Each automation has:
    - A trigger that starts it
    - One or more actions to execute
    - Configuration for both
    """

    __tablename__: str = "automations"  # type: ignore[assignment]

    # Foreign keys
    base_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    table_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Table this automation is scoped to (if applicable)",
    )
    created_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Basic info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Trigger configuration
    trigger_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    # Stores trigger-specific config (JSON)
    # - record triggers: field conditions
    # - scheduled: cron expression
    # - webhook: allowed sources, auth
    trigger_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_paused: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Temporarily paused by user",
    )

    # Execution settings
    max_runs_per_hour: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
        doc="Rate limiting",
    )
    error_notification_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Email to notify on errors",
    )

    # Statistics
    total_runs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    successful_runs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    failed_runs: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Ordering
    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    base: Mapped["Base"] = relationship(
        "Base",
        back_populates="automations",
    )
    table: Mapped["Table | None"] = relationship(
        "Table",
        back_populates="automations",
    )
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    actions: Mapped[list["AutomationAction"]] = relationship(
        "AutomationAction",
        back_populates="automation",
        cascade="all, delete-orphan",
        order_by="AutomationAction.position",
    )
    runs: Mapped[list["AutomationRun"]] = relationship(
        "AutomationRun",
        back_populates="automation",
        cascade="all, delete-orphan",
        order_by="AutomationRun.created_at.desc()",
    )

    # Indexes
    __table_args__ = (
        Index("ix_automations_base_active", "base_id", "is_active"),
        Index("ix_automations_table_active", "table_id", "is_active"),
        Index("ix_automations_trigger_type", "trigger_type"),
    )

    def __repr__(self) -> str:
        return f"<Automation {self.name} ({self.trigger_type})>"

    @property
    def trigger_type_enum(self) -> TriggerType:
        """Get trigger type as enum."""
        return TriggerType(self.trigger_type)

    def get_trigger_config(self) -> dict[str, Any]:
        """Parse trigger_config JSON."""
        try:
            return json.loads(self.trigger_config or "{}")
        except json.JSONDecodeError:
            return {}

    def set_trigger_config(self, config: dict[str, Any]) -> None:
        """Set trigger_config from dict."""
        self.trigger_config = json.dumps(config)


class AutomationAction(BaseModel):
    """
    An action within an automation.

    Actions are executed in order based on position.
    """

    __tablename__: str = "automation_actions"  # type: ignore[assignment]

    # Foreign keys
    automation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("automations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Action configuration
    action_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Optional display name for the action",
    )
    # Stores action-specific config (JSON)
    # - create_record: table_id, field_values
    # - send_email: to, subject, body
    # - send_webhook: url, method, headers, body
    # - conditional: condition, if_actions, else_actions
    action_config: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Execution
    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Error handling
    continue_on_error: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Continue to next action even if this one fails",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of retries on failure",
    )
    retry_delay_seconds: Mapped[int] = mapped_column(
        Integer,
        default=60,
        nullable=False,
        doc="Delay between retries",
    )

    # Relationships
    automation: Mapped["Automation"] = relationship(
        "Automation",
        back_populates="actions",
    )

    # Indexes
    __table_args__ = (
        Index("ix_automation_actions_automation_position", "automation_id", "position"),
    )

    def __repr__(self) -> str:
        return f"<AutomationAction {self.action_type} ({self.position})>"

    @property
    def action_type_enum(self) -> ActionType:
        """Get action type as enum."""
        return ActionType(self.action_type)

    def get_action_config(self) -> dict[str, Any]:
        """Parse action_config JSON."""
        try:
            return json.loads(self.action_config or "{}")
        except json.JSONDecodeError:
            return {}

    def set_action_config(self, config: dict[str, Any]) -> None:
        """Set action_config from dict."""
        self.action_config = json.dumps(config)


class AutomationRun(BaseModel):
    """
    A single execution of an automation.

    Tracks status, timing, and results.
    """

    __tablename__: str = "automation_runs"  # type: ignore[assignment]

    # Foreign keys
    automation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("automations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    triggered_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who triggered (for manual triggers)",
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=AutomationRunStatus.PENDING.value,
        nullable=False,
    )

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Execution duration in milliseconds",
    )

    # Trigger data (JSON)
    # Stores: record data, webhook payload, etc.
    trigger_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Results (JSON)
    # Stores: action results, created records, etc.
    results: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
    )

    # Error info
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    error_action_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Index of action that failed",
    )
    error_stack_trace: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    automation: Mapped["Automation"] = relationship(
        "Automation",
        back_populates="runs",
    )
    triggered_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[triggered_by_id],
    )

    # Indexes
    __table_args__ = (
        Index("ix_automation_runs_automation_status", "automation_id", "status"),
        Index("ix_automation_runs_automation_created", "automation_id", "created_at"),
        Index("ix_automation_runs_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<AutomationRun {self.id} ({self.status})>"

    @property
    def status_enum(self) -> AutomationRunStatus:
        """Get status as enum."""
        return AutomationRunStatus(self.status)

    def get_trigger_data(self) -> dict[str, Any]:
        """Parse trigger_data JSON."""
        try:
            return json.loads(self.trigger_data or "{}")
        except json.JSONDecodeError:
            return {}

    def set_trigger_data(self, data: dict[str, Any]) -> None:
        """Set trigger_data from dict."""
        self.trigger_data = json.dumps(data)

    def get_results(self) -> dict[str, Any]:
        """Parse results JSON."""
        try:
            return json.loads(self.results or "{}")
        except json.JSONDecodeError:
            return {}

    def set_results(self, results: dict[str, Any]) -> None:
        """Set results from dict."""
        self.results = json.dumps(results)


class Webhook(SoftDeleteModel):
    """
    Webhook configuration for external integrations.

    Webhooks can be:
    - Incoming: Receive data from external systems
    - Outgoing: Send data to external systems
    """

    __tablename__: str = "webhooks"  # type: ignore[assignment]

    # Foreign keys
    base_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    table_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Basic info
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Webhook type
    is_incoming: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="True for incoming (receive), False for outgoing (send)",
    )

    # Incoming webhook config
    webhook_url_token: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        doc="Unique token for incoming webhook URL",
    )
    allowed_ips: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Comma-separated list of allowed IP addresses",
    )
    secret_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Secret for signature verification",
    )

    # Outgoing webhook config
    target_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        doc="URL to send webhook to",
    )
    http_method: Mapped[str] = mapped_column(
        String(10),
        default="POST",
        nullable=False,
    )
    headers: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default="{}",
        doc="Custom headers (JSON)",
    )

    # Triggers (for outgoing)
    trigger_on_create: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    trigger_on_update: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    trigger_on_delete: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Statistics
    total_calls: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    successful_calls: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    failed_calls: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_called_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    base: Mapped["Base"] = relationship("Base")
    table: Mapped["Table | None"] = relationship("Table")
    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )

    # Indexes
    __table_args__ = (
        Index("ix_webhooks_base_active", "base_id", "is_active"),
        Index("ix_webhooks_table_active", "table_id", "is_active"),
        Index("ix_webhooks_url_token", "webhook_url_token"),
    )

    def __repr__(self) -> str:
        return f"<Webhook {self.name} ({'incoming' if self.is_incoming else 'outgoing'})>"

    def get_headers(self) -> dict[str, str]:
        """Parse headers JSON."""
        try:
            return json.loads(self.headers or "{}")
        except json.JSONDecodeError:
            return {}

    def set_headers(self, headers: dict[str, str]) -> None:
        """Set headers from dict."""
        self.headers = json.dumps(headers)

    def get_allowed_ips_list(self) -> list[str]:
        """Get allowed IPs as list."""
        if not self.allowed_ips:
            return []
        return [ip.strip() for ip in self.allowed_ips.split(",") if ip.strip()]


# =============================================================================
# Trigger and Action Configuration Types (for documentation)
# =============================================================================

"""
TRIGGER CONFIGURATIONS:

record_created:
{
    "watch_fields": ["field_id_1", ...],  # Optional: only trigger if these fields set
}

record_updated:
{
    "watch_fields": ["field_id_1", ...],  # Optional: only trigger if these fields changed
    "previous_value_required": false
}

record_deleted:
{}

record_matches_conditions:
{
    "conditions": [
        {"field_id": "...", "operator": "eq|neq|gt|lt|contains|...", "value": "..."}
    ],
    "check_on_create": true,
    "check_on_update": true
}

field_changed:
{
    "field_id": "...",
    "from_value": "...",  # Optional
    "to_value": "..."  # Optional
}

form_submitted:
{
    "view_id": "..."  # Form view ID
}

scheduled:
{
    "cron_expression": "0 9 * * 1",  # Every Monday at 9 AM
    "timezone": "America/New_York"
}

at_scheduled_time:
{
    "date_field_id": "...",  # Date field to watch
    "offset_minutes": -30  # Trigger 30 mins before
}

webhook_received:
{}  # Config handled by Webhook model

button_clicked:
{
    "button_field_id": "..."
}


ACTION CONFIGURATIONS:

create_record:
{
    "table_id": "...",
    "fields": {
        "field_id": "static value",
        "field_id_2": "{{trigger.record.field_name}}",  # Dynamic value
        "field_id_3": "{{previous_action.created_record_id}}"
    }
}

update_record:
{
    "record_id": "{{trigger.record.id}}",  # Or specific ID
    "fields": {
        "field_id": "new value"
    }
}

delete_record:
{
    "record_id": "{{trigger.record.id}}"
}

send_email:
{
    "to": ["email@example.com", "{{trigger.record.email_field}}"],
    "cc": [],
    "bcc": [],
    "subject": "Subject with {{trigger.record.name}}",
    "body": "HTML body with {{variables}}",
    "from_name": "PyBase"
}

send_slack_message:
{
    "webhook_url": "https://hooks.slack.com/...",
    "channel": "#channel",
    "message": "Message with {{variables}}",
    "blocks": []  # Slack Block Kit
}

send_webhook:
{
    "url": "https://api.example.com/webhook",
    "method": "POST",
    "headers": {"Authorization": "Bearer ..."},
    "body": {"key": "{{trigger.record.field}}"}
}

link_records:
{
    "source_record_id": "{{trigger.record.id}}",
    "linked_field_id": "...",
    "target_record_ids": ["...", "{{lookup:table_id:conditions}}"]
}

run_script:
{
    "language": "python",  # or "javascript"
    "code": "return {'result': input['record']['name'].upper()}",
    "timeout_seconds": 30
}

conditional:
{
    "condition": {
        "field": "{{trigger.record.status}}",
        "operator": "eq",
        "value": "Approved"
    },
    "if_actions": [0, 1],  # Action indices to run if true
    "else_actions": [2]  # Action indices to run if false
}

loop:
{
    "source": "{{lookup:table_id:conditions}}",  # Or array field
    "actions": [0, 1],  # Action indices to run for each item
    "max_iterations": 100
}

delay:
{
    "seconds": 3600,  # 1 hour delay
    "until_datetime": "{{trigger.record.due_date}}"  # Or specific datetime
}

call_api:
{
    "url": "https://api.example.com/endpoint",
    "method": "GET|POST|PUT|DELETE",
    "headers": {},
    "body": {},
    "extract_response": {
        "result_field": "$.data.id"  # JSONPath to extract
    }
}
"""
