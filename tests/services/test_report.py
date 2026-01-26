"""
Unit tests for ReportService business logic.
"""

import json
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from pybase.db.base import utc_now
from pybase.models.base import Base
from pybase.models.dashboard import Dashboard
from pybase.models.report import Report, ReportFormat, ReportSchedule, ReportStatus, ScheduleFrequency
from pybase.models.user import User
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.report import (
    DeliveryConfig,
    ExportConfig,
    PDFExportConfig,
    ReportCreate,
    ReportDuplicate,
    ReportScheduleConfig,
    ReportUpdate,
)
from pybase.services.report import ReportService


@pytest.fixture
def report_service():
    """Create an instance of ReportService."""
    return ReportService()


@pytest_asyncio.fixture
async def test_workspace(db_session: AsyncSession, test_user: User) -> Workspace:
    """Create a test workspace with user as owner."""
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add owner as workspace member
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    return workspace


@pytest_asyncio.fixture
async def test_base(db_session: AsyncSession, test_workspace: Workspace) -> Base:
    """Create a test base."""
    base = Base(
        workspace_id=test_workspace.id,
        name="Test Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def test_dashboard(
    db_session: AsyncSession,
    test_base: Base,
    test_user: User,
) -> Dashboard:
    """Create a test dashboard."""
    dashboard = Dashboard(
        base_id=test_base.id,
        created_by_id=test_user.id,
        name="Test Dashboard",
        description="Test Description",
        is_default=False,
        is_personal=False,
        is_public=False,
        is_locked=False,
        layout_config="{}",
        settings="{}",
        global_filters="[]",
    )
    db_session.add(dashboard)
    await db_session.commit()
    await db_session.refresh(dashboard)
    return dashboard


@pytest_asyncio.fixture
async def test_report(
    db_session: AsyncSession,
    test_base: Base,
    test_dashboard: Dashboard,
    test_user: User,
) -> Report:
    """Create a test report."""
    report = Report(
        id=str(uuid4()),
        base_id=test_base.id,
        dashboard_id=test_dashboard.id,
        created_by_id=test_user.id,
        name="Test Report",
        description="Test report description",
        format=ReportFormat.PDF.value,
        frequency=ScheduleFrequency.MANUAL.value,
        schedule_config="{}",
        delivery_config="{}",
        export_config="{}",
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)
    return report


@pytest_asyncio.fixture
async def second_user(db_session: AsyncSession, test_workspace: Workspace) -> User:
    """Create a second test user with workspace access."""
    user = User(
        email=f"second-user-{uuid4()}@test.com",
        username=f"seconduser-{uuid4()}",
        hashed_password="hashedpass",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Add as workspace member
    member = WorkspaceMember(
        workspace_id=test_workspace.id,
        user_id=user.id,
        role=WorkspaceRole.MEMBER,
    )
    db_session.add(member)
    await db_session.commit()

    return user


class TestCreateReport:
    """Test report creation."""

    @pytest.mark.asyncio
    async def test_create_basic_report(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_dashboard: Dashboard,
        test_user: User,
    ):
        """Test creating a basic report."""
        report_data = ReportCreate(
            dashboard_id=test_dashboard.id,
            name="Weekly Report",
            description="Weekly dashboard report",
            format=ReportFormat.PDF,
            frequency=ScheduleFrequency.MANUAL,
        )

        report = await report_service.create_report(
            db_session,
            test_user.id,
            report_data,
        )

        assert report.id is not None
        assert report.name == "Weekly Report"
        assert report.description == "Weekly dashboard report"
        assert report.format == ReportFormat.PDF.value
        assert report.frequency == ScheduleFrequency.MANUAL.value
        assert report.dashboard_id == test_dashboard.id
        assert report.created_by_id == test_user.id

    @pytest.mark.asyncio
    async def test_create_scheduled_report(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_dashboard: Dashboard,
        test_user: User,
    ):
        """Test creating a scheduled report with schedule config."""
        schedule_config = ReportScheduleConfig(
            time_of_day="09:00",
            day_of_week="monday",
            timezone="UTC",
        )
        delivery_config = DeliveryConfig(
            recipients=["test@example.com"],
            subject="Weekly Report",
            message="Please find the attached report.",
        )

        report_data = ReportCreate(
            dashboard_id=test_dashboard.id,
            name="Weekly Scheduled Report",
            frequency=ScheduleFrequency.WEEKLY,
            schedule_config=schedule_config,
            delivery_config=delivery_config,
            is_active=True,
        )

        report = await report_service.create_report(
            db_session,
            test_user.id,
            report_data,
        )

        assert report.frequency == ScheduleFrequency.WEEKLY.value
        assert report.is_active is True
        assert report.is_scheduled is True
        assert report.next_run_at is not None  # Should be calculated

        # Verify configs stored as JSON
        config = report.get_schedule_config_dict()
        assert config["time_of_day"] == "09:00"
        assert config["day_of_week"] == "monday"

        delivery = report.get_delivery_config_dict()
        assert "test@example.com" in delivery["recipients"]

    @pytest.mark.asyncio
    async def test_create_report_with_export_config(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_dashboard: Dashboard,
        test_user: User,
    ):
        """Test creating a report with export configuration."""
        export_config = ExportConfig(
            pdf=PDFExportConfig(
                page_size="A4",
                orientation="landscape",
                include_filters=True,
                include_timestamp=True,
            )
        )

        report_data = ReportCreate(
            dashboard_id=test_dashboard.id,
            name="PDF Report",
            format=ReportFormat.PDF,
            export_config=export_config,
        )

        report = await report_service.create_report(
            db_session,
            test_user.id,
            report_data,
        )

        config = report.get_export_config_dict()
        assert config["pdf"]["page_size"] == "A4"
        assert config["pdf"]["orientation"] == "landscape"

    @pytest.mark.asyncio
    async def test_create_report_invalid_dashboard(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_user: User,
    ):
        """Test creating report with non-existent dashboard."""
        report_data = ReportCreate(
            dashboard_id=str(uuid4()),
            name="Invalid Report",
        )

        with pytest.raises(NotFoundError):
            await report_service.create_report(
                db_session,
                test_user.id,
                report_data,
            )


class TestGetReport:
    """Test report retrieval."""

    @pytest.mark.asyncio
    async def test_get_report_by_id(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_report: Report,
        test_user: User,
    ):
        """Test getting a report by ID."""
        report = await report_service.get_report_by_id(
            db_session,
            test_report.id,
            test_user.id,
        )

        assert report.id == test_report.id
        assert report.name == test_report.name

    @pytest.mark.asyncio
    async def test_get_report_not_found(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_user: User,
    ):
        """Test getting non-existent report."""
        with pytest.raises(NotFoundError):
            await report_service.get_report_by_id(
                db_session,
                str(uuid4()),
                test_user.id,
            )

    @pytest.mark.asyncio
    async def test_get_report_no_access(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_report: Report,
    ):
        """Test getting report without workspace access."""
        # Create user without workspace access
        other_user = User(
            email=f"other-{uuid4()}@test.com",
            username=f"other-{uuid4()}",
            hashed_password="hashedpass",
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        with pytest.raises(PermissionDeniedError):
            await report_service.get_report_by_id(
                db_session,
                test_report.id,
                other_user.id,
            )


class TestListReports:
    """Test report listing."""

    @pytest.mark.asyncio
    async def test_list_reports(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_base: Base,
        test_report: Report,
        test_user: User,
    ):
        """Test listing reports for a base."""
        reports, total = await report_service.list_reports(
            db_session,
            test_base.id,
            test_user.id,
        )

        assert total >= 1
        assert any(r.id == test_report.id for r in reports)

    @pytest.mark.asyncio
    async def test_list_reports_with_filters(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_base: Base,
        test_dashboard: Dashboard,
        test_user: User,
    ):
        """Test listing reports with filters."""
        # Create multiple reports
        report1 = Report(
            id=str(uuid4()),
            base_id=test_base.id,
            dashboard_id=test_dashboard.id,
            created_by_id=test_user.id,
            name="Active Report",
            format=ReportFormat.PDF.value,
            frequency=ScheduleFrequency.DAILY.value,
            is_active=True,
        )
        report2 = Report(
            id=str(uuid4()),
            base_id=test_base.id,
            dashboard_id=test_dashboard.id,
            created_by_id=test_user.id,
            name="Inactive Report",
            format=ReportFormat.EXCEL.value,
            frequency=ScheduleFrequency.WEEKLY.value,
            is_active=False,
        )
        db_session.add_all([report1, report2])
        await db_session.commit()

        # Filter by active status
        active_reports, total = await report_service.list_reports(
            db_session,
            test_base.id,
            test_user.id,
            is_active=True,
        )
        assert all(r.is_active for r in active_reports)

        # Filter by frequency
        daily_reports, total = await report_service.list_reports(
            db_session,
            test_base.id,
            test_user.id,
            frequency=ScheduleFrequency.DAILY.value,
        )
        assert all(r.frequency == ScheduleFrequency.DAILY.value for r in daily_reports)


class TestUpdateReport:
    """Test report updates."""

    @pytest.mark.asyncio
    async def test_update_report_name(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_report: Report,
        test_user: User,
    ):
        """Test updating report name."""
        update_data = ReportUpdate(name="Updated Report Name")

        updated = await report_service.update_report(
            db_session,
            test_report.id,
            test_user.id,
            update_data,
        )

        assert updated.name == "Updated Report Name"

    @pytest.mark.asyncio
    async def test_update_report_frequency(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_report: Report,
        test_user: User,
    ):
        """Test updating report frequency."""
        update_data = ReportUpdate(
            frequency=ScheduleFrequency.WEEKLY,
            is_active=True,
        )

        updated = await report_service.update_report(
            db_session,
            test_report.id,
            test_user.id,
            update_data,
        )

        assert updated.frequency == ScheduleFrequency.WEEKLY.value
        assert updated.is_active is True
        assert updated.next_run_at is not None  # Should be recalculated

    @pytest.mark.asyncio
    async def test_update_report_pause(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_user: User,
        test_dashboard: Dashboard,
    ):
        """Test pausing an active report."""
        # Create active report
        report_data = ReportCreate(
            dashboard_id=test_dashboard.id,
            name="Active Report",
            frequency=ScheduleFrequency.DAILY,
            is_active=True,
        )
        report = await report_service.create_report(
            db_session,
            test_user.id,
            report_data,
        )

        # Pause it
        update_data = ReportUpdate(is_paused=True)
        updated = await report_service.update_report(
            db_session,
            report.id,
            test_user.id,
            update_data,
        )

        assert updated.is_paused is True
        assert updated.next_run_at is None  # Should clear next run


class TestDeleteReport:
    """Test report deletion."""

    @pytest.mark.asyncio
    async def test_delete_report(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_report: Report,
        test_user: User,
    ):
        """Test soft deleting a report."""
        await report_service.delete_report(
            db_session,
            test_report.id,
            test_user.id,
        )

        # Verify soft deleted
        with pytest.raises(NotFoundError):
            await report_service.get_report_by_id(
                db_session,
                test_report.id,
                test_user.id,
            )


class TestDuplicateReport:
    """Test report duplication."""

    @pytest.mark.asyncio
    async def test_duplicate_report(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_report: Report,
        test_user: User,
    ):
        """Test duplicating a report."""
        duplicate_data = ReportDuplicate(
            new_name="Duplicated Report",
            copy_schedule=True,
            copy_delivery_config=True,
        )

        duplicate = await report_service.duplicate_report(
            db_session,
            test_report.id,
            test_user.id,
            duplicate_data,
        )

        assert duplicate.id != test_report.id
        assert duplicate.name == "Duplicated Report"
        assert duplicate.dashboard_id == test_report.dashboard_id
        assert duplicate.is_active is False  # New reports start inactive

    @pytest.mark.asyncio
    async def test_duplicate_report_without_schedule(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_user: User,
        test_dashboard: Dashboard,
    ):
        """Test duplicating report without copying schedule."""
        # Create scheduled report
        report_data = ReportCreate(
            dashboard_id=test_dashboard.id,
            name="Scheduled Report",
            frequency=ScheduleFrequency.WEEKLY,
            schedule_config=ReportScheduleConfig(
                time_of_day="09:00",
                day_of_week="monday",
            ),
        )
        original = await report_service.create_report(
            db_session,
            test_user.id,
            report_data,
        )

        # Duplicate without schedule
        duplicate_data = ReportDuplicate(
            new_name="Duplicated Without Schedule",
            copy_schedule=False,
        )

        duplicate = await report_service.duplicate_report(
            db_session,
            original.id,
            test_user.id,
            duplicate_data,
        )

        assert duplicate.frequency == ScheduleFrequency.MANUAL.value


class TestGenerateReport:
    """Test report generation."""

    @pytest.mark.asyncio
    async def test_generate_pdf_report(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_report: Report,
        test_user: User,
    ):
        """Test generating a PDF report."""
        schedule = await report_service.generate_report(
            db_session,
            test_report.id,
            test_user.id,
            send_email=False,
        )

        assert schedule.id is not None
        assert schedule.report_id == test_report.id
        assert schedule.status == ReportStatus.COMPLETED.value
        assert schedule.output_path is not None
        assert schedule.output_size_bytes > 0

    @pytest.mark.asyncio
    async def test_generate_report_rate_limit(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_report: Report,
        test_user: User,
    ):
        """Test report generation rate limiting."""
        # Set low rate limit
        test_report.max_runs_per_day = 2
        await db_session.commit()

        # Generate reports up to limit
        await report_service.generate_report(
            db_session,
            test_report.id,
            test_user.id,
            send_email=False,
        )
        await report_service.generate_report(
            db_session,
            test_report.id,
            test_user.id,
            send_email=False,
        )

        # Third attempt should fail
        with pytest.raises(ValidationError, match="Rate limit exceeded"):
            await report_service.generate_report(
                db_session,
                test_report.id,
                test_user.id,
                send_email=False,
            )


class TestScheduleOperations:
    """Test schedule operations."""

    @pytest.mark.asyncio
    async def test_list_schedules(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_report: Report,
        test_user: User,
    ):
        """Test listing schedule runs."""
        # Generate a report to create schedule
        await report_service.generate_report(
            db_session,
            test_report.id,
            test_user.id,
            send_email=False,
        )

        schedules, total = await report_service.list_schedules(
            db_session,
            test_report.id,
            test_user.id,
        )

        assert total >= 1
        assert len(schedules) >= 1

    @pytest.mark.asyncio
    async def test_cancel_schedule(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_report: Report,
        test_user: User,
    ):
        """Test cancelling a schedule."""
        # Create pending schedule
        schedule = ReportSchedule(
            id=str(uuid4()),
            report_id=test_report.id,
            triggered_by_id=test_user.id,
            scheduled_at=utc_now(),
            status=ReportStatus.PENDING.value,
        )
        db_session.add(schedule)
        await db_session.commit()
        await db_session.refresh(schedule)

        # Cancel it
        cancelled = await report_service.cancel_schedule(
            db_session,
            schedule.id,
            test_user.id,
        )

        assert cancelled.status == ReportStatus.CANCELLED.value

    @pytest.mark.asyncio
    async def test_cancel_completed_schedule_fails(
        self,
        db_session: AsyncSession,
        report_service: ReportService,
        test_report: Report,
        test_user: User,
    ):
        """Test that completed schedules cannot be cancelled."""
        # Generate report (creates completed schedule)
        schedule = await report_service.generate_report(
            db_session,
            test_report.id,
            test_user.id,
            send_email=False,
        )

        # Try to cancel
        with pytest.raises(ValidationError, match="Cannot cancel completed"):
            await report_service.cancel_schedule(
                db_session,
                schedule.id,
                test_user.id,
            )
