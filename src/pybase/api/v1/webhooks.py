"""Webhook API endpoints."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from pybase.api.deps import CurrentUser, DbSession
from pybase.schemas.automation import (
    IncomingWebhookPayload,
    WebhookCreate,
    WebhookListResponse,
    WebhookResponse,
    WebhookTestRequest,
    WebhookTestResponse,
    WebhookUpdate,
)
from pybase.services.automation import get_webhook_service

router = APIRouter()


# =============================================================================
# Webhook CRUD
# =============================================================================


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    data: WebhookCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> WebhookResponse:
    """
    Create a new webhook.

    Webhooks can be:
    - **Incoming**: Receive data from external systems
    - **Outgoing**: Send data to external systems when events occur
    """
    service = get_webhook_service(db)
    webhook = await service.create_webhook(data, str(current_user.id))

    response = WebhookResponse.model_validate(webhook)

    # Add computed webhook URL for incoming webhooks
    if webhook.is_incoming and webhook.webhook_url_token:
        response.webhook_url = f"/api/v1/webhooks/incoming/{webhook.webhook_url_token}"

    return response


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(
    base_id: str = Query(..., description="Base ID to list webhooks for"),
    table_id: Optional[str] = Query(None, description="Filter by table ID"),
    is_incoming: Optional[bool] = Query(None, description="Filter by type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: DbSession = Depends(),
    current_user: CurrentUser = Depends(),
) -> WebhookListResponse:
    """List webhooks for a base."""
    service = get_webhook_service(db)
    webhooks, total = await service.list_webhooks(
        base_id=base_id,
        table_id=table_id,
        is_incoming=is_incoming,
        limit=limit,
        offset=offset,
    )

    items = []
    for webhook in webhooks:
        response = WebhookResponse.model_validate(webhook)
        if webhook.is_incoming and webhook.webhook_url_token:
            response.webhook_url = f"/api/v1/webhooks/incoming/{webhook.webhook_url_token}"
        items.append(response)

    return WebhookListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> WebhookResponse:
    """Get a webhook by ID."""
    service = get_webhook_service(db)
    webhook = await service.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    response = WebhookResponse.model_validate(webhook)
    if webhook.is_incoming and webhook.webhook_url_token:
        response.webhook_url = f"/api/v1/webhooks/incoming/{webhook.webhook_url_token}"

    return response


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    data: WebhookUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> WebhookResponse:
    """Update a webhook."""
    service = get_webhook_service(db)
    webhook = await service.update_webhook(webhook_id, data)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    response = WebhookResponse.model_validate(webhook)
    if webhook.is_incoming and webhook.webhook_url_token:
        response.webhook_url = f"/api/v1/webhooks/incoming/{webhook.webhook_url_token}"

    return response


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete a webhook."""
    service = get_webhook_service(db)
    deleted = await service.delete_webhook(webhook_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )


# =============================================================================
# Webhook Testing
# =============================================================================


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: str,
    data: WebhookTestRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> WebhookTestResponse:
    """
    Test an outgoing webhook.

    Sends a test payload to the configured URL and returns the response.
    """
    service = get_webhook_service(db)

    try:
        result = await service.test_outgoing_webhook(webhook_id, data.payload)
        return WebhookTestResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{webhook_id}/regenerate-token", response_model=WebhookResponse)
async def regenerate_webhook_token(
    webhook_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> WebhookResponse:
    """
    Regenerate the URL token for an incoming webhook.

    This invalidates the old URL and generates a new one.
    """
    import secrets

    service = get_webhook_service(db)
    webhook = await service.get_webhook(webhook_id)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    if not webhook.is_incoming:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only regenerate token for incoming webhooks",
        )

    # Generate new token
    webhook.webhook_url_token = secrets.token_urlsafe(32)
    await db.commit()
    await db.refresh(webhook)

    response = WebhookResponse.model_validate(webhook)
    response.webhook_url = f"/api/v1/webhooks/incoming/{webhook.webhook_url_token}"

    return response


# =============================================================================
# Incoming Webhook Handler
# =============================================================================


@router.post("/incoming/{token}")
async def handle_incoming_webhook(
    token: str,
    payload: IncomingWebhookPayload,
    request: Request,
    db: DbSession,
) -> dict[str, Any]:
    """
    Handle an incoming webhook call.

    This endpoint is called by external systems to trigger automations
    or import data.

    No authentication required - the token in the URL is the authentication.
    """
    service = get_webhook_service(db)

    # Get client IP for validation
    client_ip = request.client.host if request.client else None

    try:
        result = await service.handle_incoming_webhook(
            token=token,
            payload=payload.data,
            source_ip=client_ip,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/incoming/{token}")
async def incoming_webhook_info(
    token: str,
    db: DbSession,
) -> dict[str, Any]:
    """
    Get info about an incoming webhook (for verification).

    This can be used by external systems to verify the webhook is valid
    before sending data.
    """
    service = get_webhook_service(db)
    webhook = await service.get_webhook_by_token(token)

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    return {
        "name": webhook.name,
        "description": webhook.description,
        "is_active": webhook.is_active,
        "accepts_data": True,
    }
