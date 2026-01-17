"""Pydantic schemas for automations and webhooks."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from pybase.models.automation import ActionType, AutomationRunStatus, TriggerType


# =============================================================================
# Trigger Config Schemas
# =============================================================================


class RecordTriggerConfig(BaseModel):
    """Config for record-based triggers."""

    watch_fields: list[str] = Field(
        default_factory=list,
        description="Field IDs to watch (empty = all fields)",
    )
    previous_value_required: bool = Field(
        default=False,
        description="Include previous values in trigger data",
    )


class ConditionsTriggerConfig(BaseModel):
    """Config for conditions-based triggers."""

    conditions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Filter conditions",
    )
    check_on_create: bool = True
    check_on_update: bool = True


class FieldChangedTriggerConfig(BaseModel):
    """Config for field change triggers."""

    field_id: str = Field(..., description="Field to watch")
    from_value: Optional[Any] = Field(None, description="Trigger only from this value")
    to_value: Optional[Any] = Field(None, description="Trigger only to this value")


class ScheduledTriggerConfig(BaseModel):
    """Config for scheduled triggers."""

    cron_expression: str = Field(..., description="Cron expression")
    timezone: str = Field(default="UTC", description="Timezone")


class DateFieldTriggerConfig(BaseModel):
    """Config for date field-based triggers."""

    date_field_id: str = Field(..., description="Date field to watch")
    offset_minutes: int = Field(
        default=0,
        description="Minutes before/after to trigger",
    )


class FormSubmittedTriggerConfig(BaseModel):
    """Config for form submission triggers."""

    view_id: str = Field(..., description="Form view ID")


class ButtonClickedTriggerConfig(BaseModel):
    """Config for button click triggers."""

    button_field_id: str = Field(..., description="Button field ID")


# =============================================================================
# Action Config Schemas
# =============================================================================


class CreateRecordActionConfig(BaseModel):
    """Config for create record action."""

    table_id: str = Field(..., description="Target table ID")
    fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Field values (supports templates)",
    )


class UpdateRecordActionConfig(BaseModel):
    """Config for update record action."""

    record_id: str = Field(
        default="{{trigger.record.id}}",
        description="Record ID to update (supports templates)",
    )
    fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Field values to update",
    )


class DeleteRecordActionConfig(BaseModel):
    """Config for delete record action."""

    record_id: str = Field(
        default="{{trigger.record.id}}",
        description="Record ID to delete",
    )


class SendEmailActionConfig(BaseModel):
    """Config for send email action."""

    to: list[str] = Field(..., description="Recipient email addresses")
    cc: list[str] = Field(default_factory=list)
    bcc: list[str] = Field(default_factory=list)
    subject: str = Field(..., description="Email subject (supports templates)")
    body: str = Field(..., description="Email body HTML (supports templates)")
    from_name: str = Field(default="PyBase", description="Sender display name")


class SendWebhookActionConfig(BaseModel):
    """Config for send webhook action."""

    url: str = Field(..., description="Webhook URL")
    method: str = Field(default="POST", description="HTTP method")
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, Any] = Field(
        default_factory=dict,
        description="Request body (supports templates)",
    )


class SendSlackMessageActionConfig(BaseModel):
    """Config for Slack message action."""

    webhook_url: str = Field(..., description="Slack webhook URL")
    channel: Optional[str] = Field(None, description="Channel override")
    message: str = Field(..., description="Message text (supports templates)")
    blocks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Slack Block Kit blocks",
    )


class RunScriptActionConfig(BaseModel):
    """Config for run script action."""

    language: str = Field(default="python", description="Script language")
    code: str = Field(..., description="Script code")
    timeout_seconds: int = Field(default=30, description="Execution timeout")


class ConditionalActionConfig(BaseModel):
    """Config for conditional logic action."""

    condition: dict[str, Any] = Field(..., description="Condition to evaluate")
    if_actions: list[int] = Field(
        default_factory=list,
        description="Action indices if true",
    )
    else_actions: list[int] = Field(
        default_factory=list,
        description="Action indices if false",
    )


class LoopActionConfig(BaseModel):
    """Config for loop action."""

    source: str = Field(..., description="Data source (template or lookup)")
    actions: list[int] = Field(..., description="Action indices to run")
    max_iterations: int = Field(default=100, description="Max iterations")


class DelayActionConfig(BaseModel):
    """Config for delay action."""

    seconds: Optional[int] = Field(None, description="Delay in seconds")
    until_datetime: Optional[str] = Field(
        None,
        description="Wait until datetime (template)",
    )


class CallApiActionConfig(BaseModel):
    """Config for API call action."""

    url: str = Field(..., description="API URL")
    method: str = Field(default="GET", description="HTTP method")
    headers: dict[str, str] = Field(default_factory=dict)
    body: Optional[dict[str, Any]] = Field(None, description="Request body")
    extract_response: dict[str, str] = Field(
        default_factory=dict,
        description="JSONPath extractions",
    )


# =============================================================================
# Automation Schemas
# =============================================================================


class AutomationActionBase(BaseModel):
    """Base schema for automation actions."""

    action_type: ActionType
    name: Optional[str] = None
    action_config: dict[str, Any] = Field(default_factory=dict)
    position: int = 0
    is_enabled: bool = True
    continue_on_error: bool = False
    retry_count: int = 0
    retry_delay_seconds: int = 60


class AutomationActionCreate(AutomationActionBase):
    """Schema for creating an automation action."""

    pass


class AutomationActionUpdate(BaseModel):
    """Schema for updating an automation action."""

    action_type: Optional[ActionType] = None
    name: Optional[str] = None
    action_config: Optional[dict[str, Any]] = None
    position: Optional[int] = None
    is_enabled: Optional[bool] = None
    continue_on_error: Optional[bool] = None
    retry_count: Optional[int] = None
    retry_delay_seconds: Optional[int] = None


class AutomationActionResponse(AutomationActionBase):
    """Schema for automation action response."""

    id: str
    automation_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AutomationBase(BaseModel):
    """Base schema for automations."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_type: TriggerType
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    max_runs_per_hour: int = Field(default=100, ge=1, le=10000)
    error_notification_email: Optional[str] = None


class AutomationCreate(AutomationBase):
    """Schema for creating an automation."""

    base_id: str
    table_id: Optional[str] = None
    actions: list[AutomationActionCreate] = Field(default_factory=list)


class AutomationUpdate(BaseModel):
    """Schema for updating an automation."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    trigger_type: Optional[TriggerType] = None
    trigger_config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_paused: Optional[bool] = None
    max_runs_per_hour: Optional[int] = Field(None, ge=1, le=10000)
    error_notification_email: Optional[str] = None


class AutomationResponse(AutomationBase):
    """Schema for automation response."""

    id: str
    base_id: str
    table_id: Optional[str] = None
    created_by_id: Optional[str] = None
    is_paused: bool = False
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    last_run_at: Optional[datetime] = None
    last_error: Optional[str] = None
    position: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    actions: list[AutomationActionResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AutomationListResponse(BaseModel):
    """Paginated list of automations."""

    items: list[AutomationResponse]
    total: int
    limit: int
    offset: int


# =============================================================================
# Automation Run Schemas
# =============================================================================


class AutomationRunResponse(BaseModel):
    """Schema for automation run response."""

    id: str
    automation_id: str
    triggered_by_id: Optional[str] = None
    status: AutomationRunStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    trigger_data: dict[str, Any] = Field(default_factory=dict)
    results: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    error_action_index: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("trigger_data", "results", mode="before")
    @classmethod
    def parse_json_fields(cls, v: Any) -> dict[str, Any]:
        """Parse JSON string fields."""
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v or {}


class AutomationRunListResponse(BaseModel):
    """Paginated list of automation runs."""

    items: list[AutomationRunResponse]
    total: int
    limit: int
    offset: int


class TriggerAutomationRequest(BaseModel):
    """Request to manually trigger an automation."""

    trigger_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom trigger data",
    )


# =============================================================================
# Webhook Schemas
# =============================================================================


class WebhookBase(BaseModel):
    """Base schema for webhooks."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_incoming: bool = True
    is_active: bool = True


class WebhookCreate(WebhookBase):
    """Schema for creating a webhook."""

    base_id: str
    table_id: Optional[str] = None

    # Incoming config
    allowed_ips: Optional[str] = None
    secret_key: Optional[str] = None

    # Outgoing config
    target_url: Optional[str] = None
    http_method: str = "POST"
    headers: dict[str, str] = Field(default_factory=dict)
    trigger_on_create: bool = True
    trigger_on_update: bool = True
    trigger_on_delete: bool = False


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None

    # Incoming config
    allowed_ips: Optional[str] = None
    secret_key: Optional[str] = None

    # Outgoing config
    target_url: Optional[str] = None
    http_method: Optional[str] = None
    headers: Optional[dict[str, str]] = None
    trigger_on_create: Optional[bool] = None
    trigger_on_update: Optional[bool] = None
    trigger_on_delete: Optional[bool] = None


class WebhookResponse(WebhookBase):
    """Schema for webhook response."""

    id: str
    base_id: str
    table_id: Optional[str] = None
    created_by_id: Optional[str] = None

    # Incoming
    webhook_url_token: Optional[str] = None
    webhook_url: Optional[str] = None  # Computed full URL
    allowed_ips: Optional[str] = None

    # Outgoing
    target_url: Optional[str] = None
    http_method: str = "POST"
    headers: dict[str, str] = Field(default_factory=dict)
    trigger_on_create: bool = True
    trigger_on_update: bool = True
    trigger_on_delete: bool = False

    # Stats
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    last_called_at: Optional[datetime] = None
    last_error: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("headers", mode="before")
    @classmethod
    def parse_headers(cls, v: Any) -> dict[str, str]:
        """Parse headers JSON."""
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v or {}


class WebhookListResponse(BaseModel):
    """Paginated list of webhooks."""

    items: list[WebhookResponse]
    total: int
    limit: int
    offset: int


class IncomingWebhookPayload(BaseModel):
    """Schema for incoming webhook payload."""

    data: dict[str, Any] = Field(..., description="Webhook payload data")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class WebhookTestRequest(BaseModel):
    """Request to test a webhook."""

    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Test payload",
    )


class WebhookTestResponse(BaseModel):
    """Response from webhook test."""

    success: bool
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int
