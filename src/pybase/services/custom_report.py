"""Custom Report service for user-defined reports with drag-and-drop sections."""

import json
import logging
from datetime import timedelta
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
from pybase.models.custom_report import (
    CustomReport,
    CustomReportSchedule,
    ReportDataSource,
    ReportSection,
    ReportStatus,
    ReportTemplate,
    ScheduleFrequency,
)
from pybase.models.workspace import WorkspaceMember
from pybase.schemas.custom_report import (
    CustomReportCreate,
    CustomReportDuplicate,
    CustomReportScheduleConfig,
    CustomReportUpdate,
    CustomReportGenerateRequest,
    LayoutConfig,
    ReportDataSourceCreate,
    ReportDataSourceUpdate,
    ReportSectionCreate,
    ReportSectionUpdate,
    ReportTemplateCreate,
    ReportTemplateUpdate,
    StyleConfig,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Report Service
# =============================================================================


class CustomReportService:
    """Service for custom report operations."""

    def __init__(self):
        """Initialize custom report service."""
        self.output_dir = Path("./custom_reports")
        self.output_dir.mkdir(exist_ok=True)

    # -------------------------------------------------------------------------
    # CustomReport CRUD Operations
    # -------------------------------------------------------------------------

    async def create_custom_report(
        self,
        db: AsyncSession,
        base_id: str,
        user_id: str,
        report_data: CustomReportCreate,
    ) -> CustomReport:
        """Create a new custom report.

        Args:
            db: Database session
            base_id: Base ID to create report in
            user_id: User ID creating the report
            report_data: Report creation data

        Returns:
            Created report

        Raises:
            NotFoundError: If base not found
            PermissionDeniedError: If user doesn't have access

        """
        # Check if base exists and user has access
        base = await self._get_base_with_access(db, base_id, user_id)

        # Serialize configurations to JSON
        layout_config = "{}"
        if report_data.layout_config:
            layout_config = json.dumps(report_data.layout_config.model_dump(mode="json"))

        style_config = "{}"
        if report_data.style_config:
            style_config = json.dumps(report_data.style_config.model_dump(mode="json"))

        schedule_config = "{}"
        if report_data.schedule_config:
            schedule_config = json.dumps(report_data.schedule_config.model_dump(mode="json"))

        delivery_config = "{}"
        if report_data.delivery_config:
            delivery_config = json.dumps(report_data.delivery_config.model_dump(mode="json"))

        export_config = "{}"
        if report_data.export_config:
            export_config = json.dumps(report_data.export_config)

        parameters_config = "{}"
        if report_data.parameters_config:
            parameters_config = json.dumps(report_data.parameters_config)

        # Create report
        report = CustomReport(
            id=str(uuid4()),
            base_id=base_id,
            created_by_id=user_id,
            template_id=report_data.template_id,
            name=report_data.name,
            description=report_data.description,
            format=report_data.format.value,
            frequency=report_data.frequency.value,
            cron_expression=report_data.cron_expression,
            layout_config=layout_config,
            style_config=style_config,
            schedule_config=schedule_config,
            delivery_config=delivery_config,
            export_config=export_config,
            parameters_config=parameters_config,
            is_published=report_data.is_published,
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

        # Update template usage if created from template
        if report.template_id:
            template = await db.get(ReportTemplate, report.template_id)
            if template:
                template.increment_usage()

        db.add(report)
        await db.commit()
        await db.refresh(report)

        return report

    async def get_custom_report_by_id(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
    ) -> CustomReport:
        """Get a custom report by ID, checking user access.

        Args:
            db: Database session
            report_id: Report ID
            user_id: User ID requesting access

        Returns:
            CustomReport

        Raises:
            NotFoundError: If report not found
            PermissionDeniedError: If user doesn't have access

        """
        report = await db.get(CustomReport, report_id)
        if not report or report.is_deleted:
            raise NotFoundError("Custom report not found")

        # Check user access to base
        await self._get_base_with_access(db, report.base_id, user_id)

        return report

    async def list_custom_reports(
        self,
        db: AsyncSession,
        base_id: str,
        user_id: str,
        is_published: Optional[bool] = None,
        is_active: Optional[bool] = None,
        template_id: Optional[str] = None,
        frequency: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[CustomReport], int]:
        """List custom reports for a base.

        Args:
            db: Database session
            base_id: Base ID
            user_id: User ID
            is_published: Optional published status filter
            is_active: Optional active status filter
            template_id: Optional template ID filter
            frequency: Optional frequency filter
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (reports, total count)

        """
        # Check user access to base
        await self._get_base_with_access(db, base_id, user_id)

        offset = (page - 1) * page_size

        # Base conditions
        conditions = [
            CustomReport.base_id == base_id,
            CustomReport.deleted_at.is_(None),
        ]

        if is_published is not None:
            conditions.append(CustomReport.is_published == is_published)

        if is_active is not None:
            conditions.append(CustomReport.is_active == is_active)

        if template_id:
            conditions.append(CustomReport.template_id == template_id)

        if frequency:
            conditions.append(CustomReport.frequency == frequency)

        # Count query
        count_query = select(func.count()).select_from(CustomReport).where(*conditions)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query - order by last run, then name
        query = (
            select(CustomReport)
            .where(*conditions)
            .order_by(CustomReport.last_run_at.desc(), CustomReport.name)
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        reports = result.scalars().all()

        return list(reports), total

    async def update_custom_report(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
        update_data: CustomReportUpdate,
    ) -> CustomReport:
        """Update a custom report.

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
        report = await self.get_custom_report_by_id(db, report_id, user_id)

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

        if update_data.template_id is not None:
            report.template_id = update_data.template_id

        if update_data.layout_config is not None:
            report.layout_config = json.dumps(update_data.layout_config.model_dump(mode="json"))

        if update_data.style_config is not None:
            report.style_config = json.dumps(update_data.style_config.model_dump(mode="json"))

        if update_data.schedule_config is not None:
            report.schedule_config = json.dumps(update_data.schedule_config.model_dump(mode="json"))
            # Recalculate next run when schedule changes
            if report.is_scheduled:
                report.next_run_at = report.calculate_next_run()

        if update_data.delivery_config is not None:
            report.delivery_config = json.dumps(update_data.delivery_config.model_dump(mode="json"))

        if update_data.export_config is not None:
            report.export_config = json.dumps(update_data.export_config)

        if update_data.parameters_config is not None:
            report.parameters_config = json.dumps(update_data.parameters_config)

        if update_data.is_published is not None:
            report.is_published = update_data.is_published

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

    async def delete_custom_report(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
    ) -> None:
        """Delete a custom report (soft delete).

        Args:
            db: Database session
            report_id: Report ID
            user_id: User ID performing deletion

        Raises:
            NotFoundError: If report not found
            PermissionDeniedError: If user doesn't have delete access

        """
        report = await self.get_custom_report_by_id(db, report_id, user_id)

        report.soft_delete()
        await db.commit()

    async def duplicate_custom_report(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
        duplicate_data: CustomReportDuplicate,
    ) -> CustomReport:
        """Duplicate a custom report with a new name.

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
        original = await self.get_custom_report_by_id(db, report_id, user_id)

        # Create duplicate
        duplicate = CustomReport(
            id=str(uuid4()),
            base_id=original.base_id,
            created_by_id=user_id,
            name=duplicate_data.new_name,
            description=original.description,
            format=original.format,
            frequency=original.frequency if duplicate_data.copy_schedule else ScheduleFrequency.MANUAL.value,
            cron_expression=original.cron_expression if duplicate_data.copy_schedule else None,
            layout_config=original.layout_config,
            style_config=original.style_config,
            schedule_config=original.schedule_config if duplicate_data.copy_schedule else "{}",
            delivery_config=original.delivery_config if duplicate_data.copy_delivery_config else "{}",
            export_config=original.export_config,
            parameters_config=original.parameters_config,
            is_published=False,  # New reports start unpublished
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

        # Duplicate sections if requested
        if duplicate_data.copy_sections:
            for section in original.sections:
                new_section = ReportSection(
                    id=str(uuid4()),
                    report_id=duplicate.id,
                    section_type=section.section_type,
                    order=section.order,
                    title=section.title,
                    is_visible=section.is_visible,
                    section_config=section.section_config,
                    style_config=section.style_config,
                )
                db.add(new_section)

        # Duplicate data sources if requested
        if duplicate_data.copy_data_sources:
            for data_source in original.data_sources:
                new_data_source = ReportDataSource(
                    id=str(uuid4()),
                    report_id=duplicate.id,
                    name=data_source.name,
                    description=data_source.description,
                    tables_config=data_source.tables_config,
                    fields_config=data_source.fields_config,
                    filters_config=data_source.filters_config,
                    sort_config=data_source.sort_config,
                    parameters_config=data_source.parameters_config,
                )
                db.add(new_data_source)

        await db.commit()
        await db.refresh(duplicate)

        return duplicate

    # -------------------------------------------------------------------------
    # ReportSection CRUD Operations
    # -------------------------------------------------------------------------

    async def create_section(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
        section_data: ReportSectionCreate,
    ) -> ReportSection:
        """Create a new report section.

        Args:
            db: Database session
            report_id: Report ID
            user_id: User ID creating the section
            section_data: Section creation data

        Returns:
            Created section

        Raises:
            NotFoundError: If report not found
            PermissionDeniedError: If user doesn't have access

        """
        # Verify access to report
        await self.get_custom_report_by_id(db, report_id, user_id)

        # Serialize configurations
        section_config = json.dumps(section_data.section_config)
        style_config = json.dumps(section_data.style_config)

        section = ReportSection(
            id=str(uuid4()),
            report_id=report_id,
            section_type=section_data.section_type.value,
            order=section_data.order,
            title=section_data.title,
            is_visible=section_data.is_visible,
            section_config=section_config,
            style_config=style_config,
        )

        db.add(section)
        await db.commit()
        await db.refresh(section)

        return section

    async def get_section_by_id(
        self,
        db: AsyncSession,
        section_id: str,
        user_id: str,
    ) -> ReportSection:
        """Get a report section by ID, checking user access.

        Args:
            db: Database session
            section_id: Section ID
            user_id: User ID requesting access

        Returns:
            ReportSection

        Raises:
            NotFoundError: If section not found
            PermissionDeniedError: If user doesn't have access

        """
        section = await db.get(ReportSection, section_id)
        if not section:
            raise NotFoundError("Report section not found")

        # Verify access to report
        await self.get_custom_report_by_id(db, section.report_id, user_id)

        return section

    async def list_sections(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
        section_type: Optional[str] = None,
        is_visible: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ReportSection], int]:
        """List sections for a report.

        Args:
            db: Database session
            report_id: Report ID
            user_id: User ID
            section_type: Optional section type filter
            is_visible: Optional visibility filter
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (sections, total count)

        """
        # Verify access to report
        await self.get_custom_report_by_id(db, report_id, user_id)

        offset = (page - 1) * page_size

        # Base conditions
        conditions = [ReportSection.report_id == report_id]

        if section_type:
            conditions.append(ReportSection.section_type == section_type)

        if is_visible is not None:
            conditions.append(ReportSection.is_visible == is_visible)

        # Count query
        count_query = select(func.count()).select_from(ReportSection).where(*conditions)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query - order by order field
        query = (
            select(ReportSection)
            .where(*conditions)
            .order_by(ReportSection.order)
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        sections = result.scalars().all()

        return list(sections), total

    async def update_section(
        self,
        db: AsyncSession,
        section_id: str,
        user_id: str,
        update_data: ReportSectionUpdate,
    ) -> ReportSection:
        """Update a report section.

        Args:
            db: Database session
            section_id: Section ID
            user_id: User ID performing update
            update_data: Update data

        Returns:
            Updated section

        Raises:
            NotFoundError: If section not found
            PermissionDeniedError: If user doesn't have access

        """
        section = await self.get_section_by_id(db, section_id, user_id)

        if update_data.section_type is not None:
            section.section_type = update_data.section_type.value

        if update_data.order is not None:
            section.order = update_data.order

        if update_data.title is not None:
            section.title = update_data.title

        if update_data.is_visible is not None:
            section.is_visible = update_data.is_visible

        if update_data.section_config is not None:
            section.section_config = json.dumps(update_data.section_config)

        if update_data.style_config is not None:
            section.style_config = json.dumps(update_data.style_config)

        await db.commit()
        await db.refresh(section)

        return section

    async def delete_section(
        self,
        db: AsyncSession,
        section_id: str,
        user_id: str,
    ) -> None:
        """Delete a report section.

        Args:
            db: Database session
            section_id: Section ID
            user_id: User ID performing deletion

        Raises:
            NotFoundError: If section not found
            PermissionDeniedError: If user doesn't have access

        """
        section = await self.get_section_by_id(db, section_id, user_id)

        await db.delete(section)
        await db.commit()

    async def reorder_sections(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
        section_orders: dict[str, int],
    ) -> list[ReportSection]:
        """Reorder sections in a report.

        Args:
            db: Database session
            report_id: Report ID
            user_id: User ID performing reorder
            section_orders: Dict mapping section_id to new order

        Returns:
            Updated sections

        Raises:
            NotFoundError: If report not found
            PermissionDeniedError: If user doesn't have access

        """
        # Verify access to report
        await self.get_custom_report_by_id(db, report_id, user_id)

        # Update each section's order
        for section_id, new_order in section_orders.items():
            section = await db.get(ReportSection, section_id)
            if section and section.report_id == report_id:
                section.order = new_order

        await db.commit()

        # Return all sections in new order
        sections, _ = await self.list_sections(db, report_id, user_id, page_size=1000)

        return sections

    # -------------------------------------------------------------------------
    # ReportDataSource CRUD Operations
    # -------------------------------------------------------------------------

    async def create_data_source(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
        source_data: ReportDataSourceCreate,
    ) -> ReportDataSource:
        """Create a new data source for a report.

        Args:
            db: Database session
            report_id: Report ID
            user_id: User ID creating the data source
            source_data: Data source creation data

        Returns:
            Created data source

        Raises:
            NotFoundError: If report not found
            PermissionDeniedError: If user doesn't have access

        """
        # Verify access to report
        await self.get_custom_report_by_id(db, report_id, user_id)

        # Serialize configurations
        tables_config = json.dumps(source_data.tables_config.model_dump(mode="json"))
        fields_config = json.dumps(source_data.fields_config)
        filters_config = json.dumps(source_data.filters_config)
        sort_config = json.dumps(source_data.sort_config.model_dump(mode="json"))
        parameters_config = json.dumps(source_data.parameters_config)

        data_source = ReportDataSource(
            id=str(uuid4()),
            report_id=report_id,
            name=source_data.name,
            description=source_data.description,
            tables_config=tables_config,
            fields_config=fields_config,
            filters_config=filters_config,
            sort_config=sort_config,
            parameters_config=parameters_config,
        )

        db.add(data_source)
        await db.commit()
        await db.refresh(data_source)

        return data_source

    async def get_data_source_by_id(
        self,
        db: AsyncSession,
        source_id: str,
        user_id: str,
    ) -> ReportDataSource:
        """Get a data source by ID, checking user access.

        Args:
            db: Database session
            source_id: Data source ID
            user_id: User ID requesting access

        Returns:
            ReportDataSource

        Raises:
            NotFoundError: If data source not found
            PermissionDeniedError: If user doesn't have access

        """
        data_source = await db.get(ReportDataSource, source_id)
        if not data_source:
            raise NotFoundError("Data source not found")

        # Verify access to report
        await self.get_custom_report_by_id(db, data_source.report_id, user_id)

        return data_source

    async def list_data_sources(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ReportDataSource], int]:
        """List data sources for a report.

        Args:
            db: Database session
            report_id: Report ID
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (data_sources, total count)

        """
        # Verify access to report
        await self.get_custom_report_by_id(db, report_id, user_id)

        offset = (page - 1) * page_size

        # Base conditions
        conditions = [ReportDataSource.report_id == report_id]

        # Count query
        count_query = select(func.count()).select_from(ReportDataSource).where(*conditions)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query - order by name
        query = (
            select(ReportDataSource)
            .where(*conditions)
            .order_by(ReportDataSource.name)
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        data_sources = result.scalars().all()

        return list(data_sources), total

    async def update_data_source(
        self,
        db: AsyncSession,
        source_id: str,
        user_id: str,
        update_data: ReportDataSourceUpdate,
    ) -> ReportDataSource:
        """Update a data source.

        Args:
            db: Database session
            source_id: Data source ID
            user_id: User ID performing update
            update_data: Update data

        Returns:
            Updated data source

        Raises:
            NotFoundError: If data source not found
            PermissionDeniedError: If user doesn't have access

        """
        data_source = await self.get_data_source_by_id(db, source_id, user_id)

        if update_data.name is not None:
            data_source.name = update_data.name

        if update_data.description is not None:
            data_source.description = update_data.description

        if update_data.tables_config is not None:
            data_source.tables_config = json.dumps(update_data.tables_config.model_dump(mode="json"))

        if update_data.fields_config is not None:
            data_source.fields_config = json.dumps(update_data.fields_config)

        if update_data.filters_config is not None:
            data_source.filters_config = json.dumps(update_data.filters_config)

        if update_data.sort_config is not None:
            data_source.sort_config = json.dumps(update_data.sort_config.model_dump(mode="json"))

        if update_data.parameters_config is not None:
            data_source.parameters_config = json.dumps(update_data.parameters_config)

        await db.commit()
        await db.refresh(data_source)

        return data_source

    async def delete_data_source(
        self,
        db: AsyncSession,
        source_id: str,
        user_id: str,
    ) -> None:
        """Delete a data source.

        Args:
            db: Database session
            source_id: Data source ID
            user_id: User ID performing deletion

        Raises:
            NotFoundError: If data source not found
            PermissionDeniedError: If user doesn't have access

        """
        data_source = await self.get_data_source_by_id(db, source_id, user_id)

        await db.delete(data_source)
        await db.commit()

    # -------------------------------------------------------------------------
    # ReportTemplate CRUD Operations
    # -------------------------------------------------------------------------

    async def create_template(
        self,
        db: AsyncSession,
        base_id: str,
        user_id: str,
        template_data: ReportTemplateCreate,
    ) -> ReportTemplate:
        """Create a new report template.

        Args:
            db: Database session
            base_id: Base ID to create template in
            user_id: User ID creating the template
            template_data: Template creation data

        Returns:
            Created template

        Raises:
            NotFoundError: If base not found
            PermissionDeniedError: If user doesn't have access

        """
        # Check if base exists and user has access
        base = await self._get_base_with_access(db, base_id, user_id)

        # Serialize configurations
        template_config = json.dumps(template_data.template_config)
        tags = json.dumps(template_data.tags)

        template = ReportTemplate(
            id=str(uuid4()),
            base_id=base_id,
            created_by_id=user_id,
            name=template_data.name,
            description=template_data.description,
            category=template_data.category,
            tags=tags,
            template_config=template_config,
            is_system=template_data.is_system,
            is_active=template_data.is_active,
        )

        db.add(template)
        await db.commit()
        await db.refresh(template)

        return template

    async def get_template_by_id(
        self,
        db: AsyncSession,
        template_id: str,
        user_id: str,
    ) -> ReportTemplate:
        """Get a template by ID, checking user access.

        Args:
            db: Database session
            template_id: Template ID
            user_id: User ID requesting access

        Returns:
            ReportTemplate

        Raises:
            NotFoundError: If template not found
            PermissionDeniedError: If user doesn't have access

        """
        template = await db.get(ReportTemplate, template_id)
        if not template:
            raise NotFoundError("Report template not found")

        # Check user access to base
        await self._get_base_with_access(db, template.base_id, user_id)

        return template

    async def list_templates(
        self,
        db: AsyncSession,
        base_id: str,
        user_id: str,
        category: Optional[str] = None,
        is_system: Optional[bool] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ReportTemplate], int]:
        """List templates for a base.

        Args:
            db: Database session
            base_id: Base ID
            user_id: User ID
            category: Optional category filter
            is_system: Optional system template filter
            is_active: Optional active status filter
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (templates, total count)

        """
        # Check user access to base
        await self._get_base_with_access(db, base_id, user_id)

        offset = (page - 1) * page_size

        # Base conditions
        conditions = [
            ReportTemplate.base_id == base_id,
        ]

        if category:
            conditions.append(ReportTemplate.category == category)

        if is_system is not None:
            conditions.append(ReportTemplate.is_system == is_system)

        if is_active is not None:
            conditions.append(ReportTemplate.is_active == is_active)

        # Count query
        count_query = select(func.count()).select_from(ReportTemplate).where(*conditions)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query - order by usage count, then name
        query = (
            select(ReportTemplate)
            .where(*conditions)
            .order_by(ReportTemplate.usage_count.desc(), ReportTemplate.name)
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        templates = result.scalars().all()

        return list(templates), total

    async def update_template(
        self,
        db: AsyncSession,
        template_id: str,
        user_id: str,
        update_data: ReportTemplateUpdate,
    ) -> ReportTemplate:
        """Update a template.

        Args:
            db: Database session
            template_id: Template ID
            user_id: User ID performing update
            update_data: Update data

        Returns:
            Updated template

        Raises:
            NotFoundError: If template not found
            PermissionDeniedError: If user doesn't have access
            ValidationError: If trying to modify system template

        """
        template = await self.get_template_by_id(db, template_id, user_id)

        # Prevent modification of system templates
        if template.is_system:
            raise ValidationError("Cannot modify system templates")

        if update_data.name is not None:
            template.name = update_data.name

        if update_data.description is not None:
            template.description = update_data.description

        if update_data.category is not None:
            template.category = update_data.category

        if update_data.tags is not None:
            template.tags = json.dumps(update_data.tags)

        if update_data.template_config is not None:
            template.template_config = json.dumps(update_data.template_config)

        if update_data.is_active is not None:
            template.is_active = update_data.is_active

        await db.commit()
        await db.refresh(template)

        return template

    async def delete_template(
        self,
        db: AsyncSession,
        template_id: str,
        user_id: str,
    ) -> None:
        """Delete a template.

        Args:
            db: Database session
            template_id: Template ID
            user_id: User ID performing deletion

        Raises:
            NotFoundError: If template not found
            PermissionDeniedError: If user doesn't have access
            ValidationError: If trying to delete system template

        """
        template = await self.get_template_by_id(db, template_id, user_id)

        # Prevent deletion of system templates
        if template.is_system:
            raise ValidationError("Cannot delete system templates")

        await db.delete(template)
        await db.commit()

    # -------------------------------------------------------------------------
    # CustomReport Schedule Operations
    # -------------------------------------------------------------------------

    async def generate_custom_report(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
        generate_request: CustomReportGenerateRequest,
    ) -> CustomReportSchedule:
        """Generate a custom report immediately.

        Args:
            db: Database session
            report_id: Report ID to generate
            user_id: User ID triggering generation
            generate_request: Generation request parameters

        Returns:
            CustomReportSchedule (run record)

        Raises:
            NotFoundError: If report not found
            PermissionDeniedError: If user doesn't have access
            ValidationError: If rate limit exceeded

        """
        report = await self.get_custom_report_by_id(db, report_id, user_id)

        # Check rate limit
        await self._check_rate_limit(db, report)

        # Create schedule run
        schedule = CustomReportSchedule(
            id=str(uuid4()),
            report_id=report.id,
            triggered_by_id=user_id,
            scheduled_at=utc_now(),
            status=ReportStatus.PENDING.value,
            parameters_used=json.dumps(generate_request.parameters),
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
                db, report, schedule, generate_request.parameters
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
            if generate_request.send_email:
                recipients = generate_request.override_recipients or report.get_delivery_config_dict().get("recipients", [])
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
        report: CustomReport,
        schedule: CustomReportSchedule,
        parameters: dict[str, Any],
    ) -> tuple[str, int, int]:
        """Generate the actual report file.

        Args:
            db: Database session
            report: Report configuration
            schedule: Schedule run record
            parameters: Parameter values for generation

        Returns:
            Tuple of (output_path, output_size_bytes, record_count)

        """
        # Generate filename
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report.name.replace(' ', '_')}_{timestamp}.{report.format}"
        output_path = str(self.output_dir / filename)

        # Placeholder - actual PDF generation will be implemented in Phase 4
        # For now, create a placeholder file with basic info
        layout_config = report.get_layout_config_dict()
        style_config = report.get_style_config_dict()

        content = f"""Custom Report: {report.name}
Description: {report.description or 'N/A'}
Format: {report.format}
Generated: {utc_now().isoformat()}
Parameters: {parameters}
Layout Config: {layout_config}
Style Config: {style_config}

This is a placeholder custom report.
In production, this will include:
- Report sections (tables, charts, text, images)
- Data from configured data sources
- Professional formatting and styling
- Multi-page layout with headers/footers
"""

        # Write content
        with open(output_path, "w") as f:
            f.write(content)

        # Get file size
        import os

        file_size = os.path.getsize(output_path)
        record_count = 0  # Will be calculated from actual data sources

        return output_path, file_size, record_count

    async def _send_email(
        self,
        db: AsyncSession,
        report: CustomReport,
        schedule: CustomReportSchedule,
        recipients: list[str],
    ) -> None:
        """Send report via email.

        Args:
            db: Database session
            report: Report configuration
            schedule: Schedule run record
            recipients: Email recipients

        """
        # Email sending logic will be implemented in Phase 5
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
        report: CustomReport,
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
        count_query = select(func.count()).select_from(CustomReportSchedule).where(
            CustomReportSchedule.report_id == report.id,
            CustomReportSchedule.scheduled_at >= yesterday,
        )
        result = await db.execute(count_query)
        runs_today = result.scalar() or 0

        if runs_today >= report.max_runs_per_day:
            raise ValidationError(
                f"Rate limit exceeded: {runs_today}/{report.max_runs_per_day} runs per day"
            )

    async def list_schedules(
        self,
        db: AsyncSession,
        report_id: str,
        user_id: str,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[CustomReportSchedule], int]:
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
        await self.get_custom_report_by_id(db, report_id, user_id)

        offset = (page - 1) * page_size

        # Base conditions
        conditions = [CustomReportSchedule.report_id == report_id]

        if status:
            conditions.append(CustomReportSchedule.status == status)

        # Count query
        count_query = select(func.count()).select_from(CustomReportSchedule).where(*conditions)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query
        query = (
            select(CustomReportSchedule)
            .where(*conditions)
            .order_by(CustomReportSchedule.scheduled_at.desc())
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
    ) -> CustomReportSchedule:
        """Get a schedule run by ID.

        Args:
            db: Database session
            schedule_id: Schedule ID
            user_id: User ID requesting access

        Returns:
            CustomReportSchedule

        Raises:
            NotFoundError: If schedule not found
            PermissionDeniedError: If user doesn't have access

        """
        schedule = await db.get(CustomReportSchedule, schedule_id)
        if not schedule:
            raise NotFoundError("Report schedule not found")

        # Verify access to report
        await self.get_custom_report_by_id(db, schedule.report_id, user_id)

        return schedule

    async def cancel_schedule(
        self,
        db: AsyncSession,
        schedule_id: str,
        user_id: str,
    ) -> CustomReportSchedule:
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
    ) -> CustomReportSchedule:
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
        new_schedule = CustomReportSchedule(
            id=str(uuid4()),
            report_id=old_schedule.report_id,
            triggered_by_id=user_id,
            scheduled_at=utc_now(),
            status=ReportStatus.PENDING.value,
            retry_count=old_schedule.retry_count + 1,
            max_retries=old_schedule.max_retries,
            parameters_used=old_schedule.parameters_used,
        )
        db.add(new_schedule)
        await db.commit()
        await db.refresh(new_schedule)

        # Trigger generation
        report = await self.get_custom_report_by_id(db, old_schedule.report_id, user_id)
        parameters = old_schedule.get_parameters_used_dict()

        try:
            new_schedule.start()
            await db.commit()

            output_path, output_size, record_count = await self._generate_report_file(
                db, report, new_schedule, parameters
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
