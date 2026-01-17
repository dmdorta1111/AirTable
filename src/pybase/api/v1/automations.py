"""Automation API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.models.automation import ActionType, AutomationRunStatus
from pybase.schemas.automation import (
    AutomationActionCreate,
    AutomationActionResponse,
    AutomationActionUpdate,
    AutomationCreate,
    AutomationListResponse,
    AutomationResponse,
    AutomationRunListResponse,
    AutomationRunResponse,
    AutomationUpdate,
    TriggerAutomationRequest,
)
from pybase.services.automation import get_automation_service

router = APIRouter()


# =============================================================================
# Automation CRUD
# =============================================================================


@router.post("", response_model=AutomationResponse, status_code=status.HTTP_201_CREATED)
async def create_automation(
    data: AutomationCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> AutomationResponse:
    """
    Create a new automation.

    Automations are trigger-based workflows that execute actions
    when specific events occur.
    """
    service = get_automation_service(db)
    automation = await service.create_automation(data, str(current_user.id))
    return AutomationResponse.model_validate(automation)


@router.get("", response_model=AutomationListResponse)
async def list_automations(
    base_id: str = Query(..., description="Base ID to list automations for"),
    table_id: Optional[str] = Query(None, description="Filter by table ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: DbSession = Depends(),
    current_user: CurrentUser = Depends(),
) -> AutomationListResponse:
    """List automations for a base."""
    service = get_automation_service(db)
    automations, total = await service.list_automations(
        base_id=base_id,
        table_id=table_id,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )

    return AutomationListResponse(
        items=[AutomationResponse.model_validate(a) for a in automations],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{automation_id}", response_model=AutomationResponse)
async def get_automation(
    automation_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> AutomationResponse:
    """Get an automation by ID."""
    service = get_automation_service(db)
    automation = await service.get_automation(automation_id)

    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation not found",
        )

    return AutomationResponse.model_validate(automation)


@router.patch("/{automation_id}", response_model=AutomationResponse)
async def update_automation(
    automation_id: str,
    data: AutomationUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> AutomationResponse:
    """Update an automation."""
    service = get_automation_service(db)
    automation = await service.update_automation(automation_id, data)

    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation not found",
        )

    return AutomationResponse.model_validate(automation)


@router.delete("/{automation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automation(
    automation_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete an automation."""
    service = get_automation_service(db)
    deleted = await service.delete_automation(automation_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation not found",
        )


# =============================================================================
# Automation Actions
# =============================================================================


@router.post(
    "/{automation_id}/actions",
    response_model=AutomationActionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_action(
    automation_id: str,
    data: AutomationActionCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> AutomationActionResponse:
    """Add an action to an automation."""
    service = get_automation_service(db)
    action = await service.add_action(
        automation_id=automation_id,
        action_type=data.action_type,
        action_config=data.action_config,
        name=data.name,
        position=data.position,
    )

    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation not found",
        )

    return AutomationActionResponse.model_validate(action)


@router.patch(
    "/{automation_id}/actions/{action_id}",
    response_model=AutomationActionResponse,
)
async def update_action(
    automation_id: str,
    action_id: str,
    data: AutomationActionUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> AutomationActionResponse:
    """Update an action."""
    service = get_automation_service(db)
    action = await service.update_action(
        action_id=action_id,
        action_type=data.action_type,
        action_config=data.action_config,
        name=data.name,
        position=data.position,
        is_enabled=data.is_enabled,
    )

    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )

    return AutomationActionResponse.model_validate(action)


@router.delete(
    "/{automation_id}/actions/{action_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_action(
    automation_id: str,
    action_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete an action from an automation."""
    service = get_automation_service(db)
    deleted = await service.delete_action(action_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )


@router.post(
    "/{automation_id}/actions/reorder",
    response_model=AutomationResponse,
)
async def reorder_actions(
    automation_id: str,
    action_ids: list[str],
    db: DbSession,
    current_user: CurrentUser,
) -> AutomationResponse:
    """Reorder actions within an automation."""
    service = get_automation_service(db)
    await service.reorder_actions(automation_id, action_ids)

    automation = await service.get_automation(automation_id)
    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation not found",
        )

    return AutomationResponse.model_validate(automation)


# =============================================================================
# Automation Execution
# =============================================================================


@router.post("/{automation_id}/trigger", response_model=AutomationRunResponse)
async def trigger_automation(
    automation_id: str,
    data: TriggerAutomationRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> AutomationRunResponse:
    """
    Manually trigger an automation.

    This creates a new run and executes the automation with the provided
    trigger data.
    """
    service = get_automation_service(db)

    try:
        run = await service.trigger_automation(
            automation_id=automation_id,
            trigger_data=data.trigger_data,
            triggered_by_id=str(current_user.id),
        )
        return AutomationRunResponse.model_validate(run)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{automation_id}/pause", response_model=AutomationResponse)
async def pause_automation(
    automation_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> AutomationResponse:
    """Pause an automation."""
    service = get_automation_service(db)
    automation = await service.update_automation(
        automation_id,
        AutomationUpdate(is_paused=True),
    )

    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation not found",
        )

    return AutomationResponse.model_validate(automation)


@router.post("/{automation_id}/resume", response_model=AutomationResponse)
async def resume_automation(
    automation_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> AutomationResponse:
    """Resume a paused automation."""
    service = get_automation_service(db)
    automation = await service.update_automation(
        automation_id,
        AutomationUpdate(is_paused=False),
    )

    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automation not found",
        )

    return AutomationResponse.model_validate(automation)


# =============================================================================
# Automation Runs (History)
# =============================================================================


@router.get("/{automation_id}/runs", response_model=AutomationRunListResponse)
async def list_runs(
    automation_id: str,
    status_filter: Optional[AutomationRunStatus] = Query(
        None,
        alias="status",
        description="Filter by run status",
    ),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: DbSession = Depends(),
    current_user: CurrentUser = Depends(),
) -> AutomationRunListResponse:
    """List runs for an automation."""
    service = get_automation_service(db)
    runs, total = await service.list_runs(
        automation_id=automation_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    return AutomationRunListResponse(
        items=[AutomationRunResponse.model_validate(r) for r in runs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{automation_id}/runs/{run_id}", response_model=AutomationRunResponse)
async def get_run(
    automation_id: str,
    run_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> AutomationRunResponse:
    """Get a specific automation run."""
    service = get_automation_service(db)
    run = await service.get_run(run_id)

    if not run or run.automation_id != automation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    return AutomationRunResponse.model_validate(run)
