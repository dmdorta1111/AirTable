"""Automation service for managing and executing automations."""

import json
import logging
import re
import secrets
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pybase.models.automation import (
    ActionType,
    Automation,
    AutomationAction,
    AutomationRun,
    AutomationRunStatus,
    TriggerType,
    Webhook,
)
from pybase.schemas.automation import (
    AutomationCreate,
    AutomationUpdate,
    WebhookCreate,
    WebhookUpdate,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Template Engine
# =============================================================================


class TemplateEngine:
    """Simple template engine for automation variables."""

    PATTERN = re.compile(r"\{\{([^}]+)\}\}")

    @classmethod
    def render(cls, template: Any, context: dict[str, Any]) -> Any:
        """Render a template with context variables.

        Supports:
        - {{trigger.record.field_name}}
        - {{trigger.record.id}}
        - {{previous_action.result}}
        - {{now}}
        - {{user.id}}
        """
        if isinstance(template, str):
            return cls._render_string(template, context)
        elif isinstance(template, dict):
            return {k: cls.render(v, context) for k, v in template.items()}
        elif isinstance(template, list):
            return [cls.render(item, context) for item in template]
        return template

    @classmethod
    def _render_string(cls, template: str, context: dict[str, Any]) -> Any:
        """Render a string template."""
        # Check if entire string is a single variable
        match = cls.PATTERN.fullmatch(template.strip())
        if match:
            value = cls._get_value(match.group(1).strip(), context)
            return value  # Return actual type, not string

        # Replace all variables in string
        def replace(m: re.Match) -> str:
            value = cls._get_value(m.group(1).strip(), context)
            return str(value) if value is not None else ""

        return cls.PATTERN.sub(replace, template)

    @classmethod
    def _get_value(cls, path: str, context: dict[str, Any]) -> Any:
        """Get value from context using dot notation."""
        parts = path.split(".")
        value = context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None

            if value is None:
                return None

        return value


# =============================================================================
# Automation Service
# =============================================================================


class AutomationService:
    """Service for managing automations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # CRUD Operations
    # -------------------------------------------------------------------------

    async def create_automation(
        self,
        data: AutomationCreate,
        created_by_id: str,
    ) -> Automation:
        """Create a new automation with actions."""
        automation = Automation(
            id=str(uuid4()),
            base_id=data.base_id,
            table_id=data.table_id,
            created_by_id=created_by_id,
            name=data.name,
            description=data.description,
            trigger_type=data.trigger_type.value,
            trigger_config=json.dumps(data.trigger_config),
            is_active=data.is_active,
            max_runs_per_hour=data.max_runs_per_hour,
            error_notification_email=data.error_notification_email,
        )

        self.db.add(automation)

        # Create actions
        for i, action_data in enumerate(data.actions):
            action = AutomationAction(
                id=str(uuid4()),
                automation_id=automation.id,
                action_type=action_data.action_type.value,
                name=action_data.name,
                action_config=json.dumps(action_data.action_config),
                position=action_data.position if action_data.position else i,
                is_enabled=action_data.is_enabled,
                continue_on_error=action_data.continue_on_error,
                retry_count=action_data.retry_count,
                retry_delay_seconds=action_data.retry_delay_seconds,
            )
            self.db.add(action)

        await self.db.commit()
        await self.db.refresh(automation)

        return automation

    async def get_automation(
        self,
        automation_id: str,
        include_actions: bool = True,
    ) -> Optional[Automation]:
        """Get an automation by ID."""
        query = select(Automation).where(
            Automation.id == automation_id,
            Automation.deleted_at.is_(None),
        )

        if include_actions:
            query = query.options(selectinload(Automation.actions))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_automations(
        self,
        base_id: str,
        table_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Automation], int]:
        """List automations with filtering."""
        query = select(Automation).where(
            Automation.base_id == base_id,
            Automation.deleted_at.is_(None),
        )

        if table_id:
            query = query.where(Automation.table_id == table_id)

        if is_active is not None:
            query = query.where(Automation.is_active == is_active)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch page
        query = (
            query.options(selectinload(Automation.actions))
            .order_by(Automation.position, Automation.created_at)
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        automations = list(result.scalars().all())

        return automations, total

    async def update_automation(
        self,
        automation_id: str,
        data: AutomationUpdate,
    ) -> Optional[Automation]:
        """Update an automation."""
        automation = await self.get_automation(automation_id, include_actions=False)
        if not automation:
            return None

        if data.name is not None:
            automation.name = data.name
        if data.description is not None:
            automation.description = data.description
        if data.trigger_type is not None:
            automation.trigger_type = data.trigger_type.value
        if data.trigger_config is not None:
            automation.trigger_config = json.dumps(data.trigger_config)
        if data.is_active is not None:
            automation.is_active = data.is_active
        if data.is_paused is not None:
            automation.is_paused = data.is_paused
        if data.max_runs_per_hour is not None:
            automation.max_runs_per_hour = data.max_runs_per_hour
        if data.error_notification_email is not None:
            automation.error_notification_email = data.error_notification_email

        await self.db.commit()
        await self.db.refresh(automation)

        return automation

    async def delete_automation(self, automation_id: str) -> bool:
        """Soft delete an automation."""
        automation = await self.get_automation(automation_id, include_actions=False)
        if not automation:
            return False

        automation.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()

        return True

    # -------------------------------------------------------------------------
    # Action Management
    # -------------------------------------------------------------------------

    async def add_action(
        self,
        automation_id: str,
        action_type: ActionType,
        action_config: dict[str, Any],
        name: Optional[str] = None,
        position: Optional[int] = None,
    ) -> Optional[AutomationAction]:
        """Add an action to an automation."""
        automation = await self.get_automation(automation_id, include_actions=True)
        if not automation:
            return None

        # Determine position
        if position is None:
            position = len(automation.actions)

        action = AutomationAction(
            id=str(uuid4()),
            automation_id=automation_id,
            action_type=action_type.value,
            name=name,
            action_config=json.dumps(action_config),
            position=position,
        )

        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(action)

        return action

    async def update_action(
        self,
        action_id: str,
        action_type: Optional[ActionType] = None,
        action_config: Optional[dict[str, Any]] = None,
        name: Optional[str] = None,
        position: Optional[int] = None,
        is_enabled: Optional[bool] = None,
    ) -> Optional[AutomationAction]:
        """Update an action."""
        result = await self.db.execute(
            select(AutomationAction).where(AutomationAction.id == action_id)
        )
        action = result.scalar_one_or_none()
        if not action:
            return None

        if action_type is not None:
            action.action_type = action_type.value
        if action_config is not None:
            action.action_config = json.dumps(action_config)
        if name is not None:
            action.name = name
        if position is not None:
            action.position = position
        if is_enabled is not None:
            action.is_enabled = is_enabled

        await self.db.commit()
        await self.db.refresh(action)

        return action

    async def delete_action(self, action_id: str) -> bool:
        """Delete an action."""
        result = await self.db.execute(
            select(AutomationAction).where(AutomationAction.id == action_id)
        )
        action = result.scalar_one_or_none()
        if not action:
            return False

        await self.db.delete(action)
        await self.db.commit()

        return True

    async def reorder_actions(
        self,
        automation_id: str,
        action_ids: list[str],
    ) -> bool:
        """Reorder actions within an automation."""
        for i, action_id in enumerate(action_ids):
            result = await self.db.execute(
                select(AutomationAction).where(
                    AutomationAction.id == action_id,
                    AutomationAction.automation_id == automation_id,
                )
            )
            action = result.scalar_one_or_none()
            if action:
                action.position = i

        await self.db.commit()
        return True

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    async def trigger_automation(
        self,
        automation_id: str,
        trigger_data: dict[str, Any],
        triggered_by_id: Optional[str] = None,
    ) -> AutomationRun:
        """Trigger an automation execution."""
        automation = await self.get_automation(automation_id, include_actions=True)
        if not automation:
            raise ValueError(f"Automation not found: {automation_id}")

        if not automation.is_active or automation.is_paused:
            raise ValueError("Automation is not active")

        # Create run record
        run = AutomationRun(
            id=str(uuid4()),
            automation_id=automation_id,
            triggered_by_id=triggered_by_id,
            status=AutomationRunStatus.PENDING.value,
            trigger_data=json.dumps(trigger_data),
        )

        self.db.add(run)
        await self.db.commit()

        # Execute asynchronously (in production, use Celery)
        try:
            await self._execute_automation(automation, run, trigger_data)
        except Exception as e:
            logger.exception(f"Automation execution failed: {e}")
            run.status = AutomationRunStatus.FAILED.value
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            await self.db.commit()

        return run

    async def _execute_automation(
        self,
        automation: Automation,
        run: AutomationRun,
        trigger_data: dict[str, Any],
    ) -> None:
        """Execute an automation."""
        run.status = AutomationRunStatus.RUNNING.value
        run.started_at = datetime.now(timezone.utc)
        await self.db.commit()

        context = {
            "trigger": trigger_data,
            "automation": {
                "id": automation.id,
                "name": automation.name,
            },
            "now": datetime.now(timezone.utc).isoformat(),
            "results": {},
        }

        results = {}

        try:
            # Execute actions in order
            for i, action in enumerate(sorted(automation.actions, key=lambda a: a.position)):
                if not action.is_enabled:
                    continue

                try:
                    result = await self._execute_action(action, context)
                    results[f"action_{i}"] = result
                    context["results"][f"action_{i}"] = result
                    context["previous_action"] = result
                except Exception as e:
                    logger.error(f"Action {action.id} failed: {e}")
                    if not action.continue_on_error:
                        raise
                    results[f"action_{i}"] = {"error": str(e)}

            # Update run as completed
            run.status = AutomationRunStatus.COMPLETED.value
            run.results = json.dumps(results)
            run.completed_at = datetime.now(timezone.utc)
            run.duration_ms = int((run.completed_at - run.started_at).total_seconds() * 1000)

            # Update automation stats
            automation.total_runs += 1
            automation.successful_runs += 1
            automation.last_run_at = run.completed_at
            automation.last_error = None

        except Exception as e:
            run.status = AutomationRunStatus.FAILED.value
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            run.duration_ms = int((run.completed_at - run.started_at).total_seconds() * 1000)

            automation.total_runs += 1
            automation.failed_runs += 1
            automation.last_run_at = run.completed_at
            automation.last_error = str(e)

            raise

        finally:
            await self.db.commit()

    async def _execute_action(
        self,
        action: AutomationAction,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a single action."""
        action_type = ActionType(action.action_type)
        config = action.get_action_config()

        # Render templates in config
        config = TemplateEngine.render(config, context)

        handlers = {
            ActionType.CREATE_RECORD: self._action_create_record,
            ActionType.UPDATE_RECORD: self._action_update_record,
            ActionType.DELETE_RECORD: self._action_delete_record,
            ActionType.SEND_EMAIL: self._action_send_email,
            ActionType.SEND_WEBHOOK: self._action_send_webhook,
            ActionType.DELAY: self._action_delay,
        }

        handler = handlers.get(action_type)
        if handler:
            return await handler(config, context)

        # Default: return config as result
        return {"action": action_type.value, "config": config}

    async def _action_create_record(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute create record action."""
        # In production, import and use RecordService
        logger.info(f"Create record: {config}")
        return {
            "action": "create_record",
            "table_id": config.get("table_id"),
            "fields": config.get("fields"),
            # Would include created record ID
        }

    async def _action_update_record(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute update record action."""
        logger.info(f"Update record: {config}")
        return {
            "action": "update_record",
            "record_id": config.get("record_id"),
            "fields": config.get("fields"),
        }

    async def _action_delete_record(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute delete record action."""
        logger.info(f"Delete record: {config}")
        return {
            "action": "delete_record",
            "record_id": config.get("record_id"),
        }

    async def _action_send_email(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute send email action."""
        # In production, use email service
        logger.info(f"Send email: {config}")
        return {
            "action": "send_email",
            "to": config.get("to"),
            "subject": config.get("subject"),
        }

    async def _action_send_webhook(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute send webhook action."""
        import httpx

        url = config.get("url")
        method = config.get("method", "POST")
        headers = config.get("headers", {})
        body = config.get("body", {})

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=body,
                timeout=30,
            )

        return {
            "action": "send_webhook",
            "url": url,
            "status_code": response.status_code,
            "response": response.text[:1000],  # Truncate
        }

    async def _action_delay(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute delay action."""
        import asyncio

        seconds = config.get("seconds", 0)
        if seconds > 0:
            await asyncio.sleep(seconds)

        return {
            "action": "delay",
            "seconds": seconds,
        }

    # -------------------------------------------------------------------------
    # Run History
    # -------------------------------------------------------------------------

    async def list_runs(
        self,
        automation_id: str,
        status: Optional[AutomationRunStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AutomationRun], int]:
        """List automation runs."""
        query = select(AutomationRun).where(AutomationRun.automation_id == automation_id)

        if status:
            query = query.where(AutomationRun.status == status.value)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch
        query = query.order_by(AutomationRun.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        runs = list(result.scalars().all())

        return runs, total

    async def get_run(self, run_id: str) -> Optional[AutomationRun]:
        """Get a run by ID."""
        result = await self.db.execute(select(AutomationRun).where(AutomationRun.id == run_id))
        return result.scalar_one_or_none()


# =============================================================================
# Webhook Service
# =============================================================================


class WebhookService:
    """Service for managing webhooks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_webhook(
        self,
        data: WebhookCreate,
        created_by_id: str,
    ) -> Webhook:
        """Create a new webhook."""
        webhook = Webhook(
            id=str(uuid4()),
            base_id=data.base_id,
            table_id=data.table_id,
            created_by_id=created_by_id,
            name=data.name,
            description=data.description,
            is_incoming=data.is_incoming,
            is_active=data.is_active,
        )

        if data.is_incoming:
            # Generate unique URL token for incoming webhooks
            webhook.webhook_url_token = secrets.token_urlsafe(32)
            webhook.allowed_ips = data.allowed_ips
            webhook.secret_key = data.secret_key or secrets.token_urlsafe(32)
        else:
            # Outgoing webhook config
            webhook.target_url = data.target_url
            webhook.http_method = data.http_method
            webhook.headers = json.dumps(data.headers)
            webhook.trigger_on_create = data.trigger_on_create
            webhook.trigger_on_update = data.trigger_on_update
            webhook.trigger_on_delete = data.trigger_on_delete

        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)

        return webhook

    async def get_webhook(self, webhook_id: str) -> Optional[Webhook]:
        """Get a webhook by ID."""
        result = await self.db.execute(
            select(Webhook).where(
                Webhook.id == webhook_id,
                Webhook.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_webhook_by_token(self, token: str) -> Optional[Webhook]:
        """Get an incoming webhook by URL token."""
        result = await self.db.execute(
            select(Webhook).where(
                Webhook.webhook_url_token == token,
                Webhook.is_incoming == True,
                Webhook.is_active == True,
                Webhook.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_webhooks(
        self,
        base_id: str,
        table_id: Optional[str] = None,
        is_incoming: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Webhook], int]:
        """List webhooks with filtering."""
        query = select(Webhook).where(
            Webhook.base_id == base_id,
            Webhook.deleted_at.is_(None),
        )

        if table_id:
            query = query.where(Webhook.table_id == table_id)

        if is_incoming is not None:
            query = query.where(Webhook.is_incoming == is_incoming)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Fetch
        query = query.order_by(Webhook.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        webhooks = list(result.scalars().all())

        return webhooks, total

    async def update_webhook(
        self,
        webhook_id: str,
        data: WebhookUpdate,
    ) -> Optional[Webhook]:
        """Update a webhook."""
        webhook = await self.get_webhook(webhook_id)
        if not webhook:
            return None

        if data.name is not None:
            webhook.name = data.name
        if data.description is not None:
            webhook.description = data.description
        if data.is_active is not None:
            webhook.is_active = data.is_active

        if webhook.is_incoming:
            if data.allowed_ips is not None:
                webhook.allowed_ips = data.allowed_ips
            if data.secret_key is not None:
                webhook.secret_key = data.secret_key
        else:
            if data.target_url is not None:
                webhook.target_url = data.target_url
            if data.http_method is not None:
                webhook.http_method = data.http_method
            if data.headers is not None:
                webhook.headers = json.dumps(data.headers)
            if data.trigger_on_create is not None:
                webhook.trigger_on_create = data.trigger_on_create
            if data.trigger_on_update is not None:
                webhook.trigger_on_update = data.trigger_on_update
            if data.trigger_on_delete is not None:
                webhook.trigger_on_delete = data.trigger_on_delete

        await self.db.commit()
        await self.db.refresh(webhook)

        return webhook

    async def delete_webhook(self, webhook_id: str) -> bool:
        """Soft delete a webhook."""
        webhook = await self.get_webhook(webhook_id)
        if not webhook:
            return False

        webhook.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()

        return True

    async def handle_incoming_webhook(
        self,
        token: str,
        payload: dict[str, Any],
        source_ip: Optional[str] = None,
    ) -> dict[str, Any]:
        """Handle an incoming webhook call."""
        webhook = await self.get_webhook_by_token(token)
        if not webhook:
            raise ValueError("Webhook not found")

        # Validate IP if allowed_ips is set
        if webhook.allowed_ips and source_ip:
            allowed = webhook.get_allowed_ips_list()
            if allowed and source_ip not in allowed:
                raise ValueError("IP not allowed")

        # Update stats
        webhook.total_calls += 1
        webhook.last_called_at = datetime.now(timezone.utc)

        try:
            # Trigger any automations that use this webhook
            # In production, this would find automations with webhook_received trigger
            webhook.successful_calls += 1
            await self.db.commit()

            return {
                "success": True,
                "webhook_id": webhook.id,
                "message": "Webhook received",
            }

        except Exception as e:
            webhook.failed_calls += 1
            webhook.last_error = str(e)
            await self.db.commit()
            raise

    async def test_outgoing_webhook(
        self,
        webhook_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Test an outgoing webhook."""
        import httpx
        import time

        webhook = await self.get_webhook(webhook_id)
        if not webhook or webhook.is_incoming:
            raise ValueError("Outgoing webhook not found")

        start_time = time.time()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=webhook.http_method,
                    url=webhook.target_url,
                    headers=webhook.get_headers(),
                    json=payload,
                    timeout=30,
                )

            duration_ms = int((time.time() - start_time) * 1000)

            return {
                "success": response.is_success,
                "status_code": response.status_code,
                "response_body": response.text[:5000],
                "duration_ms": duration_ms,
            }

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": str(e),
                "duration_ms": duration_ms,
            }


# =============================================================================
# Dependency Injection
# =============================================================================


def get_automation_service(db: AsyncSession) -> AutomationService:
    """Get automation service instance."""
    return AutomationService(db)


def get_webhook_service(db: AsyncSession) -> WebhookService:
    """Get webhook service instance."""
    return WebhookService(db)
