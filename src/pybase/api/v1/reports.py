"""Report API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from pybase.db.session import get_db
from pybase.schemas.report import (
    ReportCreate,
    ReportDuplicate,
    ReportExportResponse,
    ReportGenerateRequest,
    ReportListResponse,
    ReportResponse,
    ReportScheduleListResponse,
    ReportScheduleResponse,
    ReportUpdate,
)
from pybase.services.report import ReportService

router = APIRouter()


def get_report_service() -> ReportService:
    """Get report service instance."""
    return ReportService()


# =============================================================================
# Report CRUD
# =============================================================================


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> ReportResponse:
    """
    Create a new scheduled report.

    Reports can be configured to generate automatically on a schedule
    and deliver results via email.
    """
    service = get_report_service()
    try:
        report = await service.create_report(
            db=db,
            user_id=str(current_user.id),
            report_data=data,
        )
        return ReportResponse.model_validate(report)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get("", response_model=ReportListResponse)
async def list_reports(
    db: DbSession,
    current_user: CurrentUser,
    base_id: UUID = Query(..., description="Base ID to list reports for"),
    dashboard_id: Optional[UUID] = Query(None, description="Filter by dashboard ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    frequency: Optional[str] = Query(None, description="Filter by frequency"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> ReportListResponse:
    """List reports for a base."""
    service = get_report_service()
    try:
        reports, total = await service.list_reports(
            db=db,
            base_id=base_id,
            user_id=str(current_user.id),
            dashboard_id=dashboard_id,
            is_active=is_active,
            frequency=frequency,
            page=page,
            page_size=page_size,
        )

        pages = (total + page_size - 1) // page_size

        return ReportListResponse(
            items=[ReportResponse.model_validate(r) for r in reports],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> ReportResponse:
    """Get a report by ID."""
    service = get_report_service()
    try:
        report = await service.get_report_by_id(
            db=db,
            report_id=report_id,
            user_id=str(current_user.id),
        )
        return ReportResponse.model_validate(report)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.patch("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: str,
    data: ReportUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ReportResponse:
    """Update a report."""
    service = get_report_service()
    try:
        report = await service.update_report(
            db=db,
            report_id=report_id,
            user_id=str(current_user.id),
            update_data=data,
        )
        return ReportResponse.model_validate(report)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete a report."""
    service = get_report_service()
    try:
        await service.delete_report(
            db=db,
            report_id=report_id,
            user_id=str(current_user.id),
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post("/{report_id}/duplicate", response_model=ReportResponse)
async def duplicate_report(
    report_id: str,
    data: ReportDuplicate,
    db: DbSession,
    current_user: CurrentUser,
) -> ReportResponse:
    """Duplicate a report with a new name."""
    service = get_report_service()
    try:
        report = await service.duplicate_report(
            db=db,
            report_id=report_id,
            user_id=str(current_user.id),
            duplicate_data=data,
        )
        return ReportResponse.model_validate(report)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# =============================================================================
# Report Generation & Export
# =============================================================================


@router.post("/{report_id}/generate", response_model=ReportScheduleResponse)
async def generate_report(
    report_id: str,
    db: DbSession,
    current_user: CurrentUser,
    send_email: bool = Query(True, description="Send email to configured recipients"),
    override_recipients: Optional[list[str]] = Query(
        None, description="Override default recipients"
    ),
) -> ReportScheduleResponse:
    """
    Generate a report immediately.

    Creates a schedule run and generates the report file. Optionally sends
    email to configured recipients or override recipients.
    """
    service = get_report_service()
    try:
        schedule = await service.generate_report(
            db=db,
            report_id=report_id,
            user_id=str(current_user.id),
            send_email=send_email,
            override_recipients=override_recipients,
        )
        return ReportScheduleResponse.model_validate(schedule)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{report_id}/export", response_model=ReportExportResponse)
async def export_report(
    report_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> ReportExportResponse:
    """
    Export a report to the configured format.

    Generates the report file and returns download information.
    """
    service = get_report_service()
    try:
        # Generate report without sending email
        schedule = await service.generate_report(
            db=db,
            report_id=report_id,
            user_id=str(current_user.id),
            send_email=False,
        )

        # Get report details
        report = await service.get_report_by_id(
            db=db,
            report_id=report_id,
            user_id=str(current_user.id),
        )

        return ReportExportResponse(
            report_id=report.id,
            schedule_id=schedule.id,
            output_path=schedule.output_path or "",
            output_size_bytes=schedule.output_size_bytes or 0,
            format=report.format,
            generated_at=schedule.completed_at or schedule.created_at,
            record_count=schedule.record_count,
            download_url=None,  # Would be a presigned URL in production
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# =============================================================================
# Schedule Operations
# =============================================================================


@router.get("/{report_id}/schedules", response_model=ReportScheduleListResponse)
async def list_schedules(
    report_id: str,
    db: DbSession,
    current_user: CurrentUser,
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> ReportScheduleListResponse:
    """List schedule runs for a report."""
    service = get_report_service()
    try:
        schedules, total = await service.list_schedules(
            db=db,
            report_id=report_id,
            user_id=str(current_user.id),
            status=status,
            page=page,
            page_size=page_size,
        )

        pages = (total + page_size - 1) // page_size

        return ReportScheduleListResponse(
            items=[ReportScheduleResponse.model_validate(s) for s in schedules],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/{report_id}/schedules/{schedule_id}", response_model=ReportScheduleResponse
)
async def get_schedule(
    report_id: str,
    schedule_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> ReportScheduleResponse:
    """Get a schedule run by ID."""
    service = get_report_service()
    try:
        schedule = await service.get_schedule_by_id(
            db=db,
            schedule_id=schedule_id,
            user_id=str(current_user.id),
        )
        return ReportScheduleResponse.model_validate(schedule)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post(
    "/{report_id}/schedules/{schedule_id}/cancel",
    response_model=ReportScheduleResponse,
)
async def cancel_schedule(
    report_id: str,
    schedule_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> ReportScheduleResponse:
    """Cancel a pending or running schedule."""
    service = get_report_service()
    try:
        schedule = await service.cancel_schedule(
            db=db,
            schedule_id=schedule_id,
            user_id=str(current_user.id),
        )
        return ReportScheduleResponse.model_validate(schedule)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/{report_id}/schedules/{schedule_id}/retry",
    response_model=ReportScheduleResponse,
)
async def retry_schedule(
    report_id: str,
    schedule_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> ReportScheduleResponse:
    """Retry a failed schedule."""
    service = get_report_service()
    try:
        schedule = await service.retry_schedule(
            db=db,
            schedule_id=schedule_id,
            user_id=str(current_user.id),
        )
        return ReportScheduleResponse.model_validate(schedule)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
