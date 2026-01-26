"""Report service for scheduled report generation and delivery."""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from pybase.db.base import utc_now
from pybase.models.base import Base
from pybase.models.dashboard import Dashboard
from pybase.models.report import Report, ReportFormat, ReportSchedule, ReportStatus, ScheduleFrequency
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.report import (
    DeliveryConfig,
    ExportConfig,
    ReportCreate,
    ReportDuplicate,
    ReportGenerateRequest,
    ReportScheduleConfig,
    ReportUpdate,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Report Service
# =============================================================================


class ReportService:
    """Service for report operations."""

    def __init__(self):
        """Initialize report service."""
        self.output_dir = Path("./reports")
        self.output_dir.mkdir(exist_ok=True)

    # -------------------------------------------------------------------------
    # CRUD Operations
    # -------------------------------------------------------------------------

    async def create_report(
        self,
        db: AsyncSession,
        user_id: str,
        report_data: ReportCreate,
    ) -> Report:
        """Create a new report for a dashboard.

        Args:
            db: Database session
            user_id: User ID creating the report
            report_data: Report creation data

        Returns:
            Created report

        Raises:
            NotFoundError: If dashboard not found
            PermissionDeniedError: If user doesn't have access

        """
        # Check if dashboard exists and user has access
        dashboard = await self._get_dashboard_with_access(
            db, str(report_data.dashboard_id), user_id
        )

        # Serialize configurations to JSON
        schedule_config = "{}"
        if report_data.schedule_config:
            schedule_config = json.dumps(report_data.schedule_config.model_dump(mode="json"))

        delivery_config = "{}"
        if report_data.delivery_config:
            delivery_config = json.dumps(report_data.delivery_config.model_dump(mode="json"))

        export_config = "{}"
        if report_data.export_config:
            export_config = json.dumps(report_data.export_config.model_dump(mode="json"))

        # Create report
        report = Report(
            id=str(uuid4()),
            base_id=dashboard.base_id,
            dashboard_id=str(report_data.dashboard_id),
            created_by_id=user_id,
            name=report_data.name,
            description=report_data.description,
            format=report_data.format.value,
            frequency=report_data.frequency.value,
            cron_expression=report_data.cron_expression,
            schedule_config=schedule_config,
            delivery_config=delivery_config,
            export_config=export_config,
            is_active=report_data.is_active,
            is_paused=report_data.is_paused,
            max_runs_per_day=report_data.max_runs_per_day,
            notify_on_success=report_data.notify_on_success,
            notify_on_failure=report_data.notify_on_failure,
            notification_email=report_data.notification_email,
            retention_days=report_data.retention_days,
        )

        # Calculate next run if scheduled
        if report.is_scheduled:
            report.next_run_at = report.calculate_next_run()

        db.add(report)
        await db.commit()
        await db.refresh(report)

        return report

    async def get_report_by_id(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
    ) -> Report:
        """Get a report by ID, checking user access.

        Args:
            db: Database session
            report_id: Report ID
            user_id: User ID requesting access

        Returns:
            Report

        Raises:
            NotFoundError: If report not found
            PermissionDeniedError: If user doesn't have access

        """
        report = await db.get(Report, report_id)
        if not report or report.is_deleted:
            raise NotFoundError("Report not found")

        # Check user access to base
        await self._get_base_with_access(db, report.base_id, user_id)

        return report

    async def list_reports(
        self,
        db: AsyncSession,
        base_id: UUID,
        user_id: str,
        dashboard_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        frequency: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Report], int]:
        """List reports for a base.

        Args:
            db: Database session
            base_id: Base ID
            user_id: User ID
            dashboard_id: Optional dashboard ID filter
            is_active: Optional active status filter
            frequency: Optional frequency filter
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (reports, total count)

        """
        # Check user access to base
        await self._get_base_with_access(db, str(base_id), user_id)

        offset = (page - 1) * page_size

        # Base conditions
        conditions = [
            Report.base_id == str(base_id),
            Report.deleted_at.is_(None),
        ]

        if dashboard_id:
            conditions.append(Report.dashboard_id == str(dashboard_id))

        if is_active is not None:
            conditions.append(Report.is_active == is_active)

        if frequency:
            conditions.append(Report.frequency == frequency)

        # Count query
        count_query = select(func.count()).select_from(Report).where(*conditions)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query - order by next run, then name
        query = (
            select(Report)
            .where(*conditions)
            .order_by(Report.next_run_at.desc(), Report.name)
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        reports = result.scalars().all()

        return list(reports), total

    async def update_report(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
        update_data: ReportUpdate,
    ) -> Report:
        """Update a report.

        Args:
            db: Database session
            report_id: Report ID
            user_id: User ID performing update
            update_data: Update data

        Returns:
            Updated report

        Raises:
            NotFoundError: If report not found
            PermissionDeniedError: If user doesn't have edit access

        """
        report = await self.get_report_by_id(db, report_id, user_id)

        # Update fields if provided
        if update_data.name is not None:
            report.name = update_data.name

        if update_data.description is not None:
            report.description = update_data.description

        if update_data.format is not None:
            report.format = update_data.format.value

        if update_data.frequency is not None:
            report.frequency = update_data.frequency.value
            # Recalculate next run when frequency changes
            if report.is_scheduled:
                report.next_run_at = report.calculate_next_run()

        if update_data.cron_expression is not None:
            report.cron_expression = update_data.cron_expression

        if update_data.schedule_config is not None:
            report.schedule_config = json.dumps(
                update_data.schedule_config.model_dump(mode="json")
            )
            # Recalculate next run when schedule changes
            if report.is_scheduled:
                report.next_run_at = report.calculate_next_run()

        if update_data.delivery_config is not None:
            report.delivery_config = json.dumps(
                update_data.delivery_config.model_dump(mode="json")
            )

        if update_data.export_config is not None:
            report.export_config = json.dumps(
                update_data.export_config.model_dump(mode="json")
            )

        if update_data.is_active is not None:
            report.is_active = update_data.is_active
            # Recalculate next run when activation changes
            if report.is_scheduled:
                report.next_run_at = report.calculate_next_run()
            elif not report.is_active:
                report.next_run_at = None

        if update_data.is_paused is not None:
            report.is_paused = update_data.is_paused
            # Clear next run when paused
            if report.is_paused:
                report.next_run_at = None
            elif report.is_scheduled:
                report.next_run_at = report.calculate_next_run()

        if update_data.max_runs_per_day is not None:
            report.max_runs_per_day = update_data.max_runs_per_day

        if update_data.notify_on_success is not None:
            report.notify_on_success = update_data.notify_on_success

        if update_data.notify_on_failure is not None:
            report.notify_on_failure = update_data.notify_on_failure

        if update_data.notification_email is not None:
            report.notification_email = update_data.notification_email

        if update_data.retention_days is not None:
            report.retention_days = update_data.retention_days

        await db.commit()
        await db.refresh(report)

        return report

    async def delete_report(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
    ) -> None:
        """Delete a report (soft delete).

        Args:
            db: Database session
            report_id: Report ID
            user_id: User ID performing deletion

        Raises:
            NotFoundError: If report not found
            PermissionDeniedError: If user doesn't have delete access

        """
        report = await self.get_report_by_id(db, report_id, user_id)

        report.soft_delete()
        await db.commit()

    async def duplicate_report(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
        duplicate_data: ReportDuplicate,
    ) -> Report:
        """Duplicate a report with a new name.

        Args:
            db: Database session
            report_id: Report ID to duplicate
            user_id: User ID performing duplication
            duplicate_data: Duplication settings

        Returns:
            Duplicated report

        Raises:
            NotFoundError: If report not found
            PermissionDeniedError: If user doesn't have access

        """
        original = await self.get_report_by_id(db, report_id, user_id)

        # Create duplicate
        duplicate = Report(
            id=str(uuid4()),
            base_id=original.base_id,
            dashboard_id=original.dashboard_id,
            created_by_id=user_id,
            name=duplicate_data.new_name,
            description=original.description,
            format=original.format,
            frequency=original.frequency if duplicate_data.copy_schedule else ScheduleFrequency.MANUAL.value,
            cron_expression=original.cron_expression if duplicate_data.copy_schedule else None,
            schedule_config=original.schedule_config if duplicate_data.copy_schedule else "{}",
            delivery_config=original.delivery_config if duplicate_data.copy_delivery_config else "{}",
            export_config=original.export_config,
            is_active=False,  # New reports start inactive
            is_paused=False,
            max_runs_per_day=original.max_runs_per_day,
            notify_on_success=original.notify_on_success,
            notify_on_failure=original.notify_on_failure,
            notification_email=original.notification_email,
            retention_days=original.retention_days,
        )

        db.add(duplicate)
        await db.commit()
        await db.refresh(duplicate)

        return duplicate

    # -------------------------------------------------------------------------
    # Report Generation
    # -------------------------------------------------------------------------

    async def generate_report(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
        send_email: bool = True,
        override_recipients: Optional[list[str]] = None,
    ) -> ReportSchedule:
        """Generate a report immediately.

        Args:
            db: Database session
            report_id: Report ID to generate
            user_id: User ID triggering generation
            send_email: Whether to send email
            override_recipients: Override email recipients

        Returns:
            Report schedule (run record)

        Raises:
            NotFoundError: If report not found
            PermissionDeniedError: If user doesn't have access
            ValidationError: If rate limit exceeded

        """
        report = await self.get_report_by_id(db, report_id, user_id)

        # Check rate limit
        await self._check_rate_limit(db, report)

        # Create schedule run
        schedule = ReportSchedule(
            id=str(uuid4()),
            report_id=report.id,
            triggered_by_id=user_id,
            scheduled_at=utc_now(),
            status=ReportStatus.PENDING.value,
        )
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)

        # Start generation
        try:
            schedule.start()
            await db.commit()

            # Generate report based on format
            output_path, output_size, record_count = await self._generate_report_file(
                db, report, schedule
            )

            # Mark as completed
            schedule.complete(
                output_path=output_path,
                output_size_bytes=output_size,
                record_count=record_count,
            )

            # Update report stats
            duration = schedule.duration_seconds or 0
            report.update_stats(success=True, duration_seconds=duration)
            report.last_output_path = output_path
            report.last_output_size_bytes = output_size

            await db.commit()

            # Send email if requested
            if send_email:
                recipients = override_recipients or report.get_delivery_config_dict().get("recipients", [])
                if recipients:
                    await self._send_email(db, report, schedule, recipients)

        except Exception as e:
            logger.exception(f"Report generation failed: {e}")
            schedule.fail(str(e), error_details=repr(e))
            report.update_stats(success=False)
            await db.commit()
            raise

        return schedule

    async def _generate_report_file(
        self,
        db: AsyncSession,
        report: Report,
        schedule: ReportSchedule,
    ) -> tuple[str, int, int]:
        """Generate the actual report file.

        Args:
            db: Database session
            report: Report configuration
            schedule: Schedule run record

        Returns:
            Tuple of (output_path, output_size_bytes, record_count)

        """
        # Get dashboard data
        dashboard = await db.get(Dashboard, report.dashboard_id)
        if not dashboard:
            raise NotFoundError("Dashboard not found")

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report.name.replace(' ', '_')}_{timestamp}.{report.format}"
        output_path = str(self.output_dir / filename)

        # Generate based on format
        if report.format == ReportFormat.PDF.value:
            output_size, record_count = await self._generate_pdf(
                db, report, dashboard, output_path
            )
        elif report.format == ReportFormat.EXCEL.value:
            output_size, record_count = await self._generate_excel(
                db, report, dashboard, output_path
            )
        elif report.format == ReportFormat.CSV.value:
            output_size, record_count = await self._generate_csv(
                db, report, dashboard, output_path
            )
        elif report.format == ReportFormat.HTML.value:
            output_size, record_count = await self._generate_html(
                db, report, dashboard, output_path
            )
        elif report.format == ReportFormat.JSON.value:
            output_size, record_count = await self._generate_json(
                db, report, dashboard, output_path
            )
        else:
            raise ValidationError(f"Unsupported format: {report.format}")

        return output_path, output_size, record_count

    async def _generate_pdf(
        self,
        db: AsyncSession,
        report: Report,
        dashboard: Dashboard,
        output_path: str,
    ) -> tuple[int, int]:
        """Generate PDF report.

        Args:
            db: Database session
            report: Report configuration
            dashboard: Dashboard to export
            output_path: Output file path

        Returns:
            Tuple of (file_size_bytes, record_count)

        """
        # PDF generation logic would go here
        # For now, create a placeholder file with basic info
        export_config = report.get_export_config_dict()
        pdf_config = export_config.get("pdf", {})

        content = f"""PDF Report: {report.name}
Dashboard: {dashboard.name}
Generated: {utc_now().isoformat()}
Page Size: {pdf_config.get('page_size', 'A4')}
Orientation: {pdf_config.get('orientation', 'portrait')}

This is a placeholder PDF report.
In production, this would include:
- Dashboard charts and widgets
- Data tables
- Filters and configuration
- Summary statistics
"""

        # Write content
        with open(output_path, "w") as f:
            f.write(content)

        # Get file size
        file_size = os.path.getsize(output_path)
        record_count = 0  # Would be calculated from actual data

        return file_size, record_count

    async def _generate_excel(
        self,
        db: AsyncSession,
        report: Report,
        dashboard: Dashboard,
        output_path: str,
    ) -> tuple[int, int]:
        """Generate Excel report.

        Args:
            db: Database session
            report: Report configuration
            dashboard: Dashboard to export
            output_path: Output file path

        Returns:
            Tuple of (file_size_bytes, record_count)

        """
        # Excel generation logic placeholder
        with open(output_path, "w") as f:
            f.write(f"Excel Report: {report.name}\nDashboard: {dashboard.name}\n")

        file_size = os.path.getsize(output_path)
        return file_size, 0

    async def _generate_csv(
        self,
        db: AsyncSession,
        report: Report,
        dashboard: Dashboard,
        output_path: str,
    ) -> tuple[int, int]:
        """Generate CSV report.

        Args:
            db: Database session
            report: Report configuration
            dashboard: Dashboard to export
            output_path: Output file path

        Returns:
            Tuple of (file_size_bytes, record_count)

        """
        # CSV generation logic placeholder
        export_config = report.get_export_config_dict()
        csv_config = export_config.get("csv", {})
        delimiter = csv_config.get("delimiter", ",")

        with open(output_path, "w") as f:
            f.write(f"Report{delimiter}{report.name}\n")
            f.write(f"Dashboard{delimiter}{dashboard.name}\n")

        file_size = os.path.getsize(output_path)
        return file_size, 0

    async def _generate_html(
        self,
        db: AsyncSession,
        report: Report,
        dashboard: Dashboard,
        output_path: str,
    ) -> tuple[int, int]:
        """Generate HTML report.

        Args:
            db: Database session
            report: Report configuration
            dashboard: Dashboard to export
            output_path: Output file path

        Returns:
            Tuple of (file_size_bytes, record_count)

        """
        # HTML generation logic placeholder
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{report.name}</title>
</head>
<body>
    <h1>{report.name}</h1>
    <p>Dashboard: {dashboard.name}</p>
    <p>Generated: {utc_now().isoformat()}</p>
</body>
</html>"""

        with open(output_path, "w") as f:
            f.write(html)

        file_size = os.path.getsize(output_path)
        return file_size, 0

    async def _generate_json(
        self,
        db: AsyncSession,
        report: Report,
        dashboard: Dashboard,
        output_path: str,
    ) -> tuple[int, int]:
        """Generate JSON report.

        Args:
            db: Database session
            report: Report configuration
            dashboard: Dashboard to export
            output_path: Output file path

        Returns:
            Tuple of (file_size_bytes, record_count)

        """
        # JSON generation logic placeholder
        data = {
            "report": report.name,
            "dashboard": dashboard.name,
            "generated_at": utc_now().isoformat(),
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        file_size = os.path.getsize(output_path)
        return file_size, 0

    async def _send_email(
        self,
        db: AsyncSession,
        report: Report,
        schedule: ReportSchedule,
        recipients: list[str],
    ) -> None:
        """Send report via email.

        Args:
            db: Database session
            report: Report configuration
            schedule: Schedule run record
            recipients: Email recipients

        """
        # Email sending logic would go here
        # For now, just mark as delivered
        logger.info(f"Sending report {report.name} to {len(recipients)} recipients")

        schedule.mark_delivered(
            recipients_count=len(recipients),
            delivery_status="Email sent successfully (placeholder)",
        )
        await db.commit()

    async def _check_rate_limit(
        self,
        db: AsyncSession,
        report: Report,
    ) -> None:
        """Check if report has exceeded rate limit.

        Args:
            db: Database session
            report: Report to check

        Raises:
            ValidationError: If rate limit exceeded

        """
        # Count runs in last 24 hours
        yesterday = utc_now() - timedelta(days=1)
        count_query = select(func.count()).select_from(ReportSchedule).where(
            ReportSchedule.report_id == report.id,
            ReportSchedule.scheduled_at >= yesterday,
        )
        result = await db.execute(count_query)
        runs_today = result.scalar() or 0

        if runs_today >= report.max_runs_per_day:
            raise ValidationError(
                f"Rate limit exceeded: {runs_today}/{report.max_runs_per_day} runs per day"
            )

    # -------------------------------------------------------------------------
    # Schedule Operations
    # -------------------------------------------------------------------------

    async def list_schedules(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ReportSchedule], int]:
        """List schedule runs for a report.

        Args:
            db: Database session
            report_id: Report ID
            user_id: User ID
            status: Optional status filter
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (schedules, total count)

        """
        # Verify access to report
        await self.get_report_by_id(db, report_id, user_id)

        offset = (page - 1) * page_size

        # Base conditions
        conditions = [ReportSchedule.report_id == report_id]

        if status:
            conditions.append(ReportSchedule.status == status)

        # Count query
        count_query = select(func.count()).select_from(ReportSchedule).where(*conditions)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query
        query = (
            select(ReportSchedule)
            .where(*conditions)
            .order_by(ReportSchedule.scheduled_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        schedules = result.scalars().all()

        return list(schedules), total

    async def get_schedule_by_id(
        self,
        db: AsyncSession,
        schedule_id: str,
        user_id: str,
    ) -> ReportSchedule:
        """Get a schedule run by ID.

        Args:
            db: Database session
            schedule_id: Schedule ID
            user_id: User ID requesting access

        Returns:
            ReportSchedule

        Raises:
            NotFoundError: If schedule not found
            PermissionDeniedError: If user doesn't have access

        """
        schedule = await db.get(ReportSchedule, schedule_id)
        if not schedule:
            raise NotFoundError("Report schedule not found")

        # Verify access to report
        await self.get_report_by_id(db, schedule.report_id, user_id)

        return schedule

    async def cancel_schedule(
        self,
        db: AsyncSession,
        schedule_id: str,
        user_id: str,
    ) -> ReportSchedule:
        """Cancel a pending or running schedule.

        Args:
            db: Database session
            schedule_id: Schedule ID
            user_id: User ID performing cancellation

        Returns:
            Cancelled schedule

        Raises:
            NotFoundError: If schedule not found
            ValidationError: If schedule cannot be cancelled

        """
        schedule = await self.get_schedule_by_id(db, schedule_id, user_id)

        if schedule.is_complete:
            raise ValidationError("Cannot cancel completed schedule")

        schedule.cancel()
        await db.commit()
        await db.refresh(schedule)

        return schedule

    async def retry_schedule(
        self,
        db: AsyncSession,
        schedule_id: str,
        user_id: str,
    ) -> ReportSchedule:
        """Retry a failed schedule.

        Args:
            db: Database session
            schedule_id: Schedule ID
            user_id: User ID performing retry

        Returns:
            New schedule run

        Raises:
            NotFoundError: If schedule not found
            ValidationError: If schedule cannot be retried

        """
        old_schedule = await self.get_schedule_by_id(db, schedule_id, user_id)

        if not old_schedule.can_retry:
            raise ValidationError(
                f"Cannot retry: status={old_schedule.status}, "
                f"retries={old_schedule.retry_count}/{old_schedule.max_retries}"
            )

        # Create new schedule with incremented retry count
        new_schedule = ReportSchedule(
            id=str(uuid4()),
            report_id=old_schedule.report_id,
            triggered_by_id=user_id,
            scheduled_at=utc_now(),
            status=ReportStatus.PENDING.value,
            retry_count=old_schedule.retry_count + 1,
            max_retries=old_schedule.max_retries,
        )
        db.add(new_schedule)
        await db.commit()
        await db.refresh(new_schedule)

        # Trigger generation
        report = await self.get_report_by_id(db, old_schedule.report_id, user_id)

        try:
            new_schedule.start()
            await db.commit()

            output_path, output_size, record_count = await self._generate_report_file(
                db, report, new_schedule
            )

            new_schedule.complete(
                output_path=output_path,
                output_size_bytes=output_size,
                record_count=record_count,
            )

            duration = new_schedule.duration_seconds or 0
            report.update_stats(success=True, duration_seconds=duration)
            await db.commit()

        except Exception as e:
            logger.exception(f"Report retry failed: {e}")
            new_schedule.fail(str(e), error_details=repr(e))
            report.update_stats(success=False)
            await db.commit()

        return new_schedule

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    async def _get_base_with_access(
        self,
        db: AsyncSession,
        base_id: str,
        user_id: str,
    ) -> Base:
        """Get base and verify user has access.

        Args:
            db: Database session
            base_id: Base ID
            user_id: User ID

        Returns:
            Base

        Raises:
            NotFoundError: If base not found
            PermissionDeniedError: If user doesn't have access

        """
        base = await db.get(Base, base_id)
        if not base or base.is_deleted:
            raise NotFoundError("Base not found")

        # Check workspace access
        workspace_query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == base.workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.deleted_at.is_(None),
        )
        result = await db.execute(workspace_query)
        membership = result.scalar_one_or_none()

        if not membership:
            raise PermissionDeniedError("No access to this base")

        return base

    async def _get_dashboard_with_access(
        self,
        db: AsyncSession,
        dashboard_id: str,
        user_id: str,
    ) -> Dashboard:
        """Get dashboard and verify user has access.

        Args:
            db: Database session
            dashboard_id: Dashboard ID
            user_id: User ID

        Returns:
            Dashboard

        Raises:
            NotFoundError: If dashboard not found
            PermissionDeniedError: If user doesn't have access

        """
        dashboard = await db.get(Dashboard, dashboard_id)
        if not dashboard or dashboard.is_deleted:
            raise NotFoundError("Dashboard not found")

        # Check access to base
        await self._get_base_with_access(db, dashboard.base_id, user_id)

        # Personal dashboards are only visible to creator
        if dashboard.is_personal and dashboard.created_by_id != user_id:
            raise PermissionDeniedError("This is a personal dashboard")

        return dashboard
