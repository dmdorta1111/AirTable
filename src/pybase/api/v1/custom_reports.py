"""Custom Report API endpoints."""

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
from pybase.schemas.custom_report import (
    CustomReportCreate,
    CustomReportDuplicate,
    CustomReportExportResponse,
    CustomReportGenerateRequest,
    CustomReportListResponse,
    CustomReportResponse,
    CustomReportScheduleListResponse,
    CustomReportScheduleResponse,
    CustomReportUpdate,
)
from pybase.services.custom_report import CustomReportService

router = APIRouter()


def get_custom_report_service() -> CustomReportService:
    """Get custom report service instance."""
    return CustomReportService()


# =============================================================================
# Custom Report CRUD
# =============================================================================


@router.post("", response_model=CustomReportResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_report(
    data: CustomReportCreate,
    db: DbSession,
    current_user: CurrentUser,
    base_id: UUID = Query(..., description="Base ID to create report in"),
) -> CustomReportResponse:
    """
    Create a new custom report.

    Custom reports can be configured with multiple sections,
    data sources, and output formats.
    """
    service = get_custom_report_service()
    try:
        report = await service.create_custom_report(
            db=db,
            base_id=str(base_id),
            user_id=str(current_user.id),
            report_data=data,
        )
        return CustomReportResponse.model_validate(report)
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


@router.get("", response_model=CustomReportListResponse)
async def list_custom_reports(
    db: DbSession,
    current_user: CurrentUser,
    base_id: UUID = Query(..., description="Base ID to list reports for"),
    is_published: Optional[bool] = Query(None, description="Filter by published status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    template_id: Optional[str] = Query(None, description="Filter by template ID"),
    frequency: Optional[str] = Query(None, description="Filter by frequency"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> CustomReportListResponse:
    """List custom reports for a base."""
    service = get_custom_report_service()
    try:
        reports, total = await service.list_custom_reports(
            db=db,
            base_id=str(base_id),
            user_id=str(current_user.id),
            is_published=is_published,
            is_active=is_active,
            template_id=template_id,
            frequency=frequency,
            page=page,
            page_size=page_size,
        )

        pages = (total + page_size - 1) // page_size

        return CustomReportListResponse(
            items=[CustomReportResponse.model_validate(r) for r in reports],
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


@router.get("/{report_id}", response_model=CustomReportResponse)
async def get_custom_report(
    report_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> CustomReportResponse:
    """Get a custom report by ID."""
    service = get_custom_report_service()
    try:
        report = await service.get_custom_report_by_id(
            db=db,
            report_id=report_id,
            user_id=str(current_user.id),
        )
        return CustomReportResponse.model_validate(report)
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


@router.patch("/{report_id}", response_model=CustomReportResponse)
async def update_custom_report(
    report_id: str,
    data: CustomReportUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> CustomReportResponse:
    """Update a custom report."""
    service = get_custom_report_service()
    try:
        report = await service.update_custom_report(
            db=db,
            report_id=report_id,
            user_id=str(current_user.id),
            update_data=data,
        )
        return CustomReportResponse.model_validate(report)
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
async def delete_custom_report(
    report_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    """Delete a custom report."""
    service = get_custom_report_service()
    try:
        await service.delete_custom_report(
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


@router.post("/{report_id}/duplicate", response_model=CustomReportResponse)
async def duplicate_custom_report(
    report_id: str,
    data: CustomReportDuplicate,
    db: DbSession,
    current_user: CurrentUser,
) -> CustomReportResponse:
    """Duplicate a custom report with a new name."""
    service = get_custom_report_service()
    try:
        report = await service.duplicate_custom_report(
            db=db,
            report_id=report_id,
            user_id=str(current_user.id),
            duplicate_data=data,
        )
        return CustomReportResponse.model_validate(report)
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


@router.post("/{report_id}/generate", response_model=CustomReportScheduleResponse)
async def generate_custom_report(
    report_id: str,
    db: DbSession,
    current_user: CurrentUser,
    parameters: dict = Query({}, description="Parameter values for generation"),
    send_email: bool = Query(True, description="Send email to configured recipients"),
    override_recipients: Optional[list[str]] = Query(
        None, description="Override default recipients"
    ),
) -> CustomReportScheduleResponse:
    """
    Generate a custom report immediately.

    Creates a schedule run and generates the report file. Optionally sends
    email to configured recipients or override recipients.
    """
    service = get_custom_report_service()
    try:
        generate_request = CustomReportGenerateRequest(
            report_id=report_id,
            parameters=parameters,
            send_email=send_email,
            override_recipients=override_recipients,
        )

        schedule = await service.generate_custom_report(
            db=db,
            report_id=report_id,
            user_id=str(current_user.id),
            generate_request=generate_request,
        )
        return CustomReportScheduleResponse.model_validate(schedule)
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


@router.post("/{report_id}/export", response_model=CustomReportExportResponse)
async def export_custom_report(
    report_id: str,
    db: DbSession,
    current_user: CurrentUser,
    parameters: dict = Query({}, description="Parameter values for generation"),
) -> CustomReportExportResponse:
    """
    Export a custom report to the configured format.

    Generates the report file and returns download information.
    """
    service = get_custom_report_service()
    try:
        # Generate report without sending email
        generate_request = CustomReportGenerateRequest(
            report_id=report_id,
            parameters=parameters,
            send_email=False,
        )

        schedule = await service.generate_custom_report(
            db=db,
            report_id=report_id,
            user_id=str(current_user.id),
            generate_request=generate_request,
        )

        # Get report details
        report = await service.get_custom_report_by_id(
            db=db,
            report_id=report_id,
            user_id=str(current_user.id),
        )

        from pybase.models.custom_report import ReportFormat

        return CustomReportExportResponse(
            report_id=report.id,
            schedule_id=schedule.id,
            output_path=schedule.output_path or "",
            output_size_bytes=schedule.output_size_bytes or 0,
            format=ReportFormat(report.format),
            generated_at=schedule.completed_at or schedule.created_at,
            record_count=schedule.record_count,
            parameters_used=schedule.get_parameters_used_dict(),
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


@router.get("/{report_id}/schedules", response_model=CustomReportScheduleListResponse)
async def list_custom_report_schedules(
    report_id: str,
    db: DbSession,
    current_user: CurrentUser,
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> CustomReportScheduleListResponse:
    """List schedule runs for a custom report."""
    service = get_custom_report_service()
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

        return CustomReportScheduleListResponse(
            items=[CustomReportScheduleResponse.model_validate(s) for s in schedules],
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
    "/{report_id}/schedules/{schedule_id}", response_model=CustomReportScheduleResponse
)
async def get_custom_report_schedule(
    report_id: str,
    schedule_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> CustomReportScheduleResponse:
    """Get a schedule run by ID."""
    service = get_custom_report_service()
    try:
        schedule = await service.get_schedule_by_id(
            db=db,
            schedule_id=schedule_id,
            user_id=str(current_user.id),
        )
        return CustomReportScheduleResponse.model_validate(schedule)
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
    response_model=CustomReportScheduleResponse,
)
async def cancel_custom_report_schedule(
    report_id: str,
    schedule_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> CustomReportScheduleResponse:
    """Cancel a pending or running schedule."""
    service = get_custom_report_service()
    try:
        schedule = await service.cancel_schedule(
            db=db,
            schedule_id=schedule_id,
            user_id=str(current_user.id),
        )
        return CustomReportScheduleResponse.model_validate(schedule)
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
    response_model=CustomReportScheduleResponse,
)
async def retry_custom_report_schedule(
    report_id: str,
    schedule_id: str,
    db: DbSession,
    current_user: CurrentUser,
) -> CustomReportScheduleResponse:
    """Retry a failed schedule."""
    service = get_custom_report_service()
    try:
        schedule = await service.retry_schedule(
            db=db,
            schedule_id=schedule_id,
            user_id=str(current_user.id),
        )
        return CustomReportScheduleResponse.model_validate(schedule)
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
