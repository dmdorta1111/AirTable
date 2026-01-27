"""
Audit log endpoints.

Handles audit log querying and export.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from pybase.api.deps import CurrentUser, CurrentSuperuser, DbSession
from pybase.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from pybase.schemas.audit import AuditLogListResponse, AuditLogQuery, AuditLogResponse
from pybase.services.audit_service import AuditService

router = APIRouter()

# =============================================================================
# Dependencies
# =============================================================================


def get_audit_service() -> AuditService:
    """Get audit service instance."""
    return AuditService()


# =============================================================================
# Audit Log Endpoints
# =============================================================================


@router.get("/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    db: DbSession,
    current_user: CurrentSuperuser,
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    user_id: Annotated[
        str | None,
        Query(
            description="Filter by user ID",
        ),
    ] = None,
    action: Annotated[
        str | None,
        Query(
            description="Filter by action type",
        ),
    ] = None,
    resource_type: Annotated[
        str | None,
        Query(
            description="Filter by resource type",
        ),
    ] = None,
    resource_id: Annotated[
        str | None,
        Query(
            description="Filter by resource ID",
        ),
    ] = None,
    table_id: Annotated[
        str | None,
        Query(
            description="Filter by table ID",
        ),
    ] = None,
    request_id: Annotated[
        str | None,
        Query(
            description="Filter by request ID",
        ),
    ] = None,
    start_date: Annotated[
        str | None,
        Query(
            description="Filter by start date (ISO 8601 format, inclusive)",
        ),
    ] = None,
    end_date: Annotated[
        str | None,
        Query(
            description="Filter by end date (ISO 8601 format, inclusive)",
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=1000,
            description="Maximum results to return (max 1000)",
        ),
    ] = 100,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Pagination offset",
        ),
    ] = 0,
):
    """
    List audit logs accessible to current superuser.

    Returns paginated list of audit logs with optional filters.
    Only superusers can access audit logs.

    Filters:
    - user_id: Filter by user ID who performed the action
    - action: Filter by action type (e.g., "record.create", "user.login")
    - resource_type: Filter by resource type (e.g., "record", "table", "user")
    - resource_id: Filter by specific resource ID
    - table_id: Filter by table ID (for record operations)
    - request_id: Filter by request ID for correlation
    - start_date: Filter by start date (ISO 8601 format)
    - end_date: Filter by end date (ISO 8601 format)

    Pagination:
    - limit: Maximum number of results (1-1000, default 100)
    - offset: Number of results to skip (default 0)
    """
    from datetime import datetime

    # Parse date filters if provided
    start_date_parsed = None
    end_date_parsed = None

    if start_date:
        try:
            start_date_parsed = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO 8601 format (e.g., 2024-01-01T00:00:00Z)",
            )

    if end_date:
        try:
            end_date_parsed = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO 8601 format (e.g., 2024-01-01T23:59:59Z)",
            )

    # Query audit logs
    try:
        audit_logs = await audit_service.query_logs(
            db=db,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            table_id=table_id,
            request_id=request_id,
            start_date=start_date_parsed,
            end_date=end_date_parsed,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    # Get total count (note: this is inefficient, should be optimized in production)
    # For now, we'll return the length of the current page
    total = len(audit_logs)

    # Convert audit logs to response format
    items = [
        AuditLogResponse(
            id=str(log.id),
            user_id=log.user_id,
            user_email=log.user_email,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            table_id=log.table_id,
            old_value=log.old_value,
            new_value=log.new_value,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            request_id=log.request_id,
            integrity_hash=log.integrity_hash,
            previous_log_hash=log.previous_log_hash,
            meta=log.meta,
            created_at=log.created_at,
            updated_at=log.updated_at,
        )
        for log in audit_logs
    ]

    return AuditLogListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    db: DbSession,
    current_user: CurrentSuperuser,
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
):
    """
    Get a specific audit log entry by ID.

    Returns detailed audit log information.
    Only superusers can access audit logs.
    """
    try:
        audit_log = await audit_service.get_log_by_id(db=db, log_id=log_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e

    return AuditLogResponse(
        id=str(audit_log.id),
        user_id=audit_log.user_id,
        user_email=audit_log.user_email,
        action=audit_log.action,
        resource_type=audit_log.resource_type,
        resource_id=audit_log.resource_id,
        table_id=audit_log.table_id,
        old_value=audit_log.old_value,
        new_value=audit_log.new_value,
        ip_address=audit_log.ip_address,
        user_agent=audit_log.user_agent,
        request_id=audit_log.request_id,
        integrity_hash=audit_log.integrity_hash,
        previous_log_hash=audit_log.previous_log_hash,
        meta=audit_log.meta,
        created_at=audit_log.created_at,
        updated_at=audit_log.updated_at,
    )


@router.get("/logs/{log_id}/verify")
async def verify_audit_log_integrity(
    log_id: str,
    db: DbSession,
    current_user: CurrentSuperuser,
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
):
    """
    Verify the integrity of an audit log entry.

    Checks that the integrity_hash matches the computed hash
    and that the previous_log_hash matches the previous entry's integrity_hash.
    Returns True if integrity is valid, False otherwise.

    Only superusers can verify audit log integrity.
    """
    try:
        is_valid = await audit_service.verify_integrity(db=db, log_id=log_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e

    return {"log_id": log_id, "integrity_valid": is_valid}
