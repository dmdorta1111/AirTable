"""
Export job service for managing data export jobs.

Provides CRUD operations and status management for ExportJob model.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import NotFoundError
from pybase.models.export_job import ExportJob, ExportFormat, ExportJobStatus

logger = logging.getLogger(__name__)


class ExportJobService:
    """Service for managing export jobs in the database."""

    # -------------------------------------------------------------------------
    # Create Operations
    # -------------------------------------------------------------------------

    async def create_job(
        self,
        db: AsyncSession,
        *,
        table_id: str,
        export_format: ExportFormat | str,
        user_id: str | None = None,
        view_id: str | None = None,
        field_ids: list[str] | None = None,
        options: dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> ExportJob:
        """
        Create a new export job.

        Args:
            db: Database session
            table_id: Table ID to export
            export_format: Export format (csv, xlsx, json, xml)
            user_id: User ID who created the job
            view_id: Optional view ID for filtered/sorted export
            field_ids: Optional list of field IDs to include
            options: Export options dict (filters, sort, flatten_linked_records, etc.)
            max_retries: Maximum retry attempts (default 3)

        Returns:
            Created ExportJob instance
        """
        format_value = export_format.value if isinstance(export_format, ExportFormat) else export_format

        job = ExportJob(
            id=str(uuid4()),
            table_id=table_id,
            export_format=format_value,
            status=ExportJobStatus.PENDING.value,
            user_id=user_id,
            view_id=view_id,
            max_retries=max_retries,
        )

        # Build options dict
        job_options = {}
        if field_ids:
            job_options["field_ids"] = field_ids
        if options:
            job_options.update(options)

        if job_options:
            job.set_options(job_options)

        db.add(job)
        await db.commit()
        await db.refresh(job)

        logger.info(f"Created export job {job.id} for table {table_id}")
        return job

    # -------------------------------------------------------------------------
    # Read Operations
    # -------------------------------------------------------------------------

    async def get_job(self, db: AsyncSession, job_id: str) -> ExportJob:
        """
        Get export job by ID.

        Args:
            db: Database session
            job_id: Job UUID

        Returns:
            ExportJob instance

        Raises:
            NotFoundError: If job not found
        """
        job = await db.get(ExportJob, job_id)
        if not job:
            raise NotFoundError(f"Export job {job_id} not found")
        return job

    async def list_jobs(
        self,
        db: AsyncSession,
        *,
        user_id: str | None = None,
        table_id: str | None = None,
        status: ExportJobStatus | str | None = None,
        format: ExportFormat | str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ExportJob], int]:
        """
        List export jobs with filtering and pagination.

        Args:
            db: Database session
            user_id: Filter by creator (optional)
            table_id: Filter by table (optional)
            status: Filter by status (optional)
            format: Filter by format (optional)
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (jobs list, total count)
        """
        offset = (page - 1) * page_size

        # Build base query
        base_query = select(ExportJob)

        # Apply filters
        if user_id:
            base_query = base_query.where(ExportJob.user_id == user_id)
        if table_id:
            base_query = base_query.where(ExportJob.table_id == table_id)
        if status:
            status_value = status.value if isinstance(status, ExportJobStatus) else status
            base_query = base_query.where(ExportJob.status == status_value)
        if format:
            format_value = format.value if isinstance(format, ExportFormat) else format
            base_query = base_query.where(ExportJob.export_format == format_value)

        # Count query
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query with ordering and pagination
        data_query = (
            base_query.order_by(ExportJob.created_at.desc()).offset(offset).limit(page_size)
        )
        result = await db.execute(data_query)
        jobs = list(result.scalars().all())

        return jobs, total

    async def list_pending_jobs(
        self,
        db: AsyncSession,
        limit: int = 100,
    ) -> list[ExportJob]:
        """
        List pending jobs ready for processing.

        Args:
            db: Database session
            limit: Maximum jobs to return

        Returns:
            List of pending ExportJob instances
        """
        query = (
            select(ExportJob)
            .where(ExportJob.status == ExportJobStatus.PENDING.value)
            .order_by(ExportJob.created_at.asc())
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Update Operations
    # -------------------------------------------------------------------------

    async def start_processing(self, db: AsyncSession, job_id: str) -> ExportJob:
        """
        Mark job as processing.

        Args:
            db: Database session
            job_id: Job UUID

        Returns:
            Updated ExportJob

        Raises:
            NotFoundError: If job not found
        """
        job = await self.get_job(db, job_id)
        job.status = ExportJobStatus.PROCESSING.value
        job.started_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(job)

        logger.info(f"Started processing export job {job_id}")
        return job

    async def update_progress(
        self,
        db: AsyncSession,
        job_id: str,
        processed_records: int,
        total_records: int | None = None,
    ) -> ExportJob:
        """
        Update job progress.

        Args:
            db: Database session
            job_id: Job UUID
            processed_records: Number of records processed
            total_records: Total records to process (optional, updates if provided)

        Returns:
            Updated ExportJob

        Raises:
            NotFoundError: If job not found
        """
        job = await self.get_job(db, job_id)
        job.processed_records = processed_records

        if total_records is not None:
            job.total_records = total_records

        # Calculate progress percentage
        job.progress = job.calculate_progress()

        await db.commit()
        await db.refresh(job)

        return job

    async def complete_job(
        self,
        db: AsyncSession,
        job_id: str,
        file_path: str,
        download_url: str | None = None,
        file_size: int | None = None,
        expires_at: datetime | None = None,
        result: dict[str, Any] | None = None,
    ) -> ExportJob:
        """
        Mark job as completed with file details.

        Args:
            db: Database session
            job_id: Job UUID
            file_path: Path to exported file
            download_url: Optional download URL
            file_size: Optional file size in bytes
            expires_at: Optional expiration time for download
            result: Optional result dict with stats

        Returns:
            Updated ExportJob

        Raises:
            NotFoundError: If job not found
        """
        job = await self.get_job(db, job_id)
        job.status = ExportJobStatus.COMPLETED.value
        job.completed_at = datetime.now(timezone.utc)
        job.file_path = file_path
        job.download_url = download_url
        job.progress = 100

        if file_size is not None:
            result = result or {}
            result["file_size"] = file_size

        if expires_at:
            job.expires_at = expires_at

        if result:
            job.set_results(result)

        await db.commit()
        await db.refresh(job)

        logger.info(f"Completed export job {job_id}")
        return job

    async def fail_job(
        self,
        db: AsyncSession,
        job_id: str,
        error_message: str,
        *,
        schedule_retry: bool = True,
        retry_delay_seconds: int = 60,
    ) -> ExportJob:
        """
        Mark job as failed with error message.

        Args:
            db: Database session
            job_id: Job UUID
            error_message: Error description
            schedule_retry: Whether to schedule a retry (if retries remaining)
            retry_delay_seconds: Base delay for exponential backoff

        Returns:
            Updated ExportJob

        Raises:
            NotFoundError: If job not found
        """
        job = await self.get_job(db, job_id)
        job.status = ExportJobStatus.FAILED.value
        job.error_message = error_message
        job.increment_retry()

        # Schedule retry with exponential backoff if eligible
        if schedule_retry and job.can_retry():
            delay = retry_delay_seconds * (2 ** (job.retry_count - 1))
            # Note: ExportJob doesn't have next_retry_at field, so we'll use completed_at
            # The worker will check retry_count and max_retries
            logger.info(
                f"Export job {job_id} failed, retry {job.retry_count}/{job.max_retries}"
            )
        else:
            job.completed_at = datetime.now(timezone.utc)
            logger.warning(f"Export job {job_id} failed permanently: {error_message}")

        await db.commit()
        await db.refresh(job)

        return job

    async def cancel_job(self, db: AsyncSession, job_id: str) -> ExportJob:
        """
        Cancel a pending or processing job.

        Args:
            db: Database session
            job_id: Job UUID

        Returns:
            Updated ExportJob

        Raises:
            NotFoundError: If job not found
        """
        job = await self.get_job(db, job_id)

        if job.status in (ExportJobStatus.COMPLETED.value, ExportJobStatus.CANCELLED.value):
            logger.warning(f"Cannot cancel export job {job_id} with status {job.status}")
            return job

        job.status = ExportJobStatus.CANCELLED.value
        job.completed_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(job)

        logger.info(f"Cancelled export job {job_id}")
        return job

    # -------------------------------------------------------------------------
    # Delete Operations
    # -------------------------------------------------------------------------

    async def delete_job(self, db: AsyncSession, job_id: str) -> None:
        """
        Delete an export job.

        Args:
            db: Database session
            job_id: Job UUID

        Raises:
            NotFoundError: If job not found
        """
        job = await self.get_job(db, job_id)
        await db.delete(job)
        await db.commit()

        logger.info(f"Deleted export job {job_id}")

    async def delete_completed_jobs(
        self,
        db: AsyncSession,
        older_than_days: int = 30,
    ) -> int:
        """
        Delete completed jobs older than specified days.

        Args:
            db: Database session
            older_than_days: Delete jobs older than this many days

        Returns:
            Number of deleted jobs
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)

        query = select(ExportJob).where(
            ExportJob.status.in_(
                [
                    ExportJobStatus.COMPLETED.value,
                    ExportJobStatus.CANCELLED.value,
                ]
            ),
            ExportJob.completed_at < cutoff,
        )
        result = await db.execute(query)
        jobs = result.scalars().all()

        count = 0
        for job in jobs:
            await db.delete(job)
            count += 1

        await db.commit()
        logger.info(f"Deleted {count} old completed export jobs")
        return count

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    async def get_job_stats(self, db: AsyncSession) -> dict[str, int]:
        """
        Get job statistics by status.

        Args:
            db: Database session

        Returns:
            Dict with counts per status
        """
        stats = {}
        for status in ExportJobStatus:
            query = (
                select(func.count())
                .select_from(ExportJob)
                .where(ExportJob.status == status.value)
            )
            result = await db.execute(query)
            stats[status.value] = result.scalar() or 0

        return stats
