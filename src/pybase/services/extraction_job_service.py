"""
Extraction job service for managing CAD/PDF extraction jobs.

Provides CRUD operations and status management for ExtractionJob model,
replacing the in-memory _jobs dict with persistent database storage.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import NotFoundError
from pybase.models.extraction_job import (
    ExtractionJob,
    ExtractionJobFormat,
    ExtractionJobStatus,
)

logger = logging.getLogger(__name__)


class ExtractionJobService:
    """Service for managing extraction jobs in the database."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db

    # -------------------------------------------------------------------------
    # Create Operations
    # -------------------------------------------------------------------------

    async def create_job(
        self,
        *,
        filename: str,
        file_url: str,
        file_size: int,
        format: ExtractionJobFormat | str,
        created_by_id: str | None = None,
        record_id: str | None = None,
        field_id: str | None = None,
        attachment_id: str | None = None,
        options: dict[str, Any] | None = None,
        max_retries: int = 3,
        skip_duplicate_check: bool = False,
    ) -> ExtractionJob:
        """
        Create a new extraction job.

        Args:
            filename: Original filename
            file_url: S3/B2 URL (unique identifier)
            file_size: File size in bytes
            format: Extraction format (pdf, dxf, ifc, step, werk24)
            created_by_id: User ID who created the job
            record_id: Optional FK to records.id
            field_id: Optional attachment field ID
            attachment_id: Optional attachment object ID
            options: Extraction options dict
            max_retries: Maximum retry attempts (default 3)
            skip_duplicate_check: Skip duplicate detection (default False)

        Returns:
            Created ExtractionJob instance

        Raises:
            ValueError: If a duplicate job already exists
        """
        # Check for duplicate job if not explicitly skipped
        if not skip_duplicate_check:
            existing = await self._find_existing_job(
                file_url=file_url,
                record_id=record_id,
                attachment_id=attachment_id,
            )
            if existing:
                # Return existing job instead of creating duplicate
                logger.info(f"Returning existing job {existing.id} for {filename}")
                return existing

        format_value = format.value if isinstance(format, ExtractionJobFormat) else format

        job = ExtractionJob(
            id=str(uuid4()),
            filename=filename,
            file_url=file_url,
            file_size=file_size,
            format=format_value,
            status=ExtractionJobStatus.PENDING.value,
            created_by_id=created_by_id,
            record_id=record_id,
            field_id=field_id,
            attachment_id=attachment_id,
            max_retries=max_retries,
        )

        if options:
            job.set_options(options)

        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"Created extraction job {job.id} for {filename}")
        return job

    async def _find_existing_job(
        self,
        *,
        file_url: str | None = None,
        record_id: str | None = None,
        attachment_id: str | None = None,
        lookback_hours: int = 24,
    ) -> ExtractionJob | None:
        """
        Find an existing recent job to prevent duplicates.

        Args:
            file_url: S3/B2 URL to match
            record_id: Record ID to match
            attachment_id: Attachment ID to match
            lookback_hours: Only find jobs created within this many hours

        Returns:
            Existing ExtractionJob or None
        """
        from sqlalchemy import and_

        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        conditions = [
            ExtractionJob.created_at >= cutoff,
            ExtractionJob.status.in_(
                [
                    ExtractionJobStatus.PENDING.value,
                    ExtractionJobStatus.PROCESSING.value,
                    ExtractionJobStatus.COMPLETED.value,
                ]
            ),
        ]

        if file_url:
            conditions.append(ExtractionJob.file_url == file_url)
        if record_id:
            conditions.append(ExtractionJob.record_id == record_id)
        if attachment_id:
            conditions.append(ExtractionJob.attachment_id == attachment_id)

        # At least one specific condition is required
        if not (file_url or record_id or attachment_id):
            return None

        query = select(ExtractionJob).where(and_(*conditions))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # -------------------------------------------------------------------------
    # Read Operations
    # -------------------------------------------------------------------------

    async def get_job(self, job_id: str) -> ExtractionJob:
        """
        Get extraction job by ID.

        Args:
            job_id: Job UUID

        Returns:
            ExtractionJob instance

        Raises:
            NotFoundError: If job not found
        """
        job = await self.db.get(ExtractionJob, job_id)
        if not job:
            raise NotFoundError(f"Extraction job {job_id} not found")
        return job

    async def get_job_by_file_url(self, file_url: str) -> ExtractionJob | None:
        """
        Get extraction job by file URL.

        Args:
            file_url: S3/B2 URL

        Returns:
            ExtractionJob or None if not found
        """
        query = select(ExtractionJob).where(ExtractionJob.file_url == file_url)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_job_by_attachment(
        self,
        record_id: str,
        attachment_id: str,
    ) -> ExtractionJob | None:
        """
        Get extraction job by record and attachment ID.

        Args:
            record_id: Record UUID
            attachment_id: Attachment object ID

        Returns:
            ExtractionJob or None if not found
        """
        query = select(ExtractionJob).where(
            ExtractionJob.record_id == record_id,
            ExtractionJob.attachment_id == attachment_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        *,
        user_id: str | None = None,
        status: ExtractionJobStatus | str | None = None,
        format: ExtractionJobFormat | str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ExtractionJob], int]:
        """
        List extraction jobs with filtering and pagination.

        Args:
            user_id: Filter by creator (optional)
            status: Filter by status (optional)
            format: Filter by format (optional)
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (jobs list, total count)
        """
        offset = (page - 1) * page_size

        # Build base query
        base_query = select(ExtractionJob)

        # Apply filters
        if user_id:
            base_query = base_query.where(ExtractionJob.created_by_id == user_id)
        if status:
            status_value = status.value if isinstance(status, ExtractionJobStatus) else status
            base_query = base_query.where(ExtractionJob.status == status_value)
        if format:
            format_value = format.value if isinstance(format, ExtractionJobFormat) else format
            base_query = base_query.where(ExtractionJob.format == format_value)

        # Count query
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query with ordering and pagination
        data_query = (
            base_query.order_by(ExtractionJob.created_at.desc()).offset(offset).limit(page_size)
        )
        result = await self.db.execute(data_query)
        jobs = list(result.scalars().all())

        return jobs, total

    async def list_pending_jobs(
        self,
        limit: int = 100,
    ) -> list[ExtractionJob]:
        """
        List pending jobs ready for processing.

        Args:
            limit: Maximum jobs to return

        Returns:
            List of pending ExtractionJob instances
        """
        query = (
            select(ExtractionJob)
            .where(ExtractionJob.status == ExtractionJobStatus.PENDING.value)
            .order_by(ExtractionJob.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_retryable_jobs(
        self,
        limit: int = 100,
    ) -> list[ExtractionJob]:
        """
        List failed jobs eligible for retry.

        Jobs are retryable if:
        - Status is FAILED
        - retry_count < max_retries
        - next_retry_at is in the past (or NULL)

        Args:
            limit: Maximum jobs to return

        Returns:
            List of retryable ExtractionJob instances
        """
        now = datetime.now(timezone.utc)
        query = (
            select(ExtractionJob)
            .where(
                ExtractionJob.status == ExtractionJobStatus.FAILED.value,
                ExtractionJob.retry_count < ExtractionJob.max_retries,
                (ExtractionJob.next_retry_at.is_(None)) | (ExtractionJob.next_retry_at <= now),
            )
            .order_by(ExtractionJob.next_retry_at.asc().nullsfirst())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Update Operations
    # -------------------------------------------------------------------------

    async def start_processing(self, job_id: str) -> ExtractionJob:
        """
        Mark job as processing.

        Args:
            job_id: Job UUID

        Returns:
            Updated ExtractionJob

        Raises:
            NotFoundError: If job not found
        """
        job = await self.get_job(job_id)
        job.status = ExtractionJobStatus.PROCESSING.value
        job.started_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"Started processing job {job_id}")
        return job

    async def complete_job(
        self,
        job_id: str,
        result: dict[str, Any],
    ) -> ExtractionJob:
        """
        Mark job as completed with result.

        Args:
            job_id: Job UUID
            result: Extraction result dict

        Returns:
            Updated ExtractionJob

        Raises:
            NotFoundError: If job not found
        """
        job = await self.get_job(job_id)
        job.status = ExtractionJobStatus.COMPLETED.value
        job.completed_at = datetime.now(timezone.utc)
        job.set_result(result)

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"Completed job {job_id}")
        return job

    async def fail_job(
        self,
        job_id: str,
        error_message: str,
        *,
        schedule_retry: bool = True,
        retry_delay_seconds: int = 60,
    ) -> ExtractionJob:
        """
        Mark job as failed with error message.

        Args:
            job_id: Job UUID
            error_message: Error description
            schedule_retry: Whether to schedule a retry (if retries remaining)
            retry_delay_seconds: Base delay for exponential backoff

        Returns:
            Updated ExtractionJob

        Raises:
            NotFoundError: If job not found
        """
        job = await self.get_job(job_id)
        job.status = ExtractionJobStatus.FAILED.value
        job.error_message = error_message
        job.retry_count += 1

        # Schedule retry with exponential backoff if eligible
        if schedule_retry and job.retry_count < job.max_retries:
            delay = retry_delay_seconds * (2 ** (job.retry_count - 1))
            job.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            logger.info(
                f"Job {job_id} failed, retry {job.retry_count}/{job.max_retries} scheduled in {delay}s"
            )
        else:
            job.completed_at = datetime.now(timezone.utc)
            logger.warning(f"Job {job_id} failed permanently: {error_message}")

        await self.db.commit()
        await self.db.refresh(job)

        return job

    async def cancel_job(self, job_id: str) -> ExtractionJob:
        """
        Cancel a pending or processing job.

        Args:
            job_id: Job UUID

        Returns:
            Updated ExtractionJob

        Raises:
            NotFoundError: If job not found
        """
        job = await self.get_job(job_id)

        if job.status in (ExtractionJobStatus.COMPLETED.value, ExtractionJobStatus.CANCELLED.value):
            logger.warning(f"Cannot cancel job {job_id} with status {job.status}")
            return job

        job.status = ExtractionJobStatus.CANCELLED.value
        job.completed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"Cancelled job {job_id}")
        return job

    async def reset_for_retry(self, job_id: str) -> ExtractionJob:
        """
        Reset a failed job for immediate retry.

        Args:
            job_id: Job UUID

        Returns:
            Updated ExtractionJob

        Raises:
            NotFoundError: If job not found
        """
        job = await self.get_job(job_id)

        if job.status != ExtractionJobStatus.FAILED.value:
            logger.warning(f"Cannot retry job {job_id} with status {job.status}")
            return job

        job.status = ExtractionJobStatus.PENDING.value
        job.next_retry_at = None
        job.error_message = None

        await self.db.commit()
        await self.db.refresh(job)

        logger.info(f"Reset job {job_id} for retry")
        return job

    # -------------------------------------------------------------------------
    # Delete Operations
    # -------------------------------------------------------------------------

    async def delete_job(self, job_id: str) -> None:
        """
        Delete an extraction job.

        Args:
            job_id: Job UUID

        Raises:
            NotFoundError: If job not found
        """
        job = await self.get_job(job_id)
        await self.db.delete(job)
        await self.db.commit()

        logger.info(f"Deleted job {job_id}")

    async def delete_completed_jobs(
        self,
        older_than_days: int = 30,
    ) -> int:
        """
        Delete completed jobs older than specified days.

        Args:
            older_than_days: Delete jobs older than this many days

        Returns:
            Number of deleted jobs
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)

        query = select(ExtractionJob).where(
            ExtractionJob.status.in_(
                [
                    ExtractionJobStatus.COMPLETED.value,
                    ExtractionJobStatus.CANCELLED.value,
                ]
            ),
            ExtractionJob.completed_at < cutoff,
        )
        result = await self.db.execute(query)
        jobs = result.scalars().all()

        count = 0
        for job in jobs:
            await self.db.delete(job)
            count += 1

        await self.db.commit()
        logger.info(f"Deleted {count} old completed jobs")
        return count

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    async def get_job_stats(self) -> dict[str, int]:
        """
        Get job statistics by status.

        Returns:
            Dict with counts per status
        """
        stats = {}
        for status in ExtractionJobStatus:
            query = (
                select(func.count())
                .select_from(ExtractionJob)
                .where(ExtractionJob.status == status.value)
            )
            result = await self.db.execute(query)
            stats[status.value] = result.scalar() or 0

        return stats

    # -------------------------------------------------------------------------
    # Timeout Recovery
    # -------------------------------------------------------------------------

    async def find_stuck_jobs(
        self,
        timeout_minutes: int = 30,
    ) -> list[ExtractionJob]:
        """
        Find jobs stuck in PROCESSING status longer than timeout.

        Args:
            timeout_minutes: Minutes before a processing job is considered stuck

        Returns:
            List of stuck ExtractionJob instances
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

        query = select(ExtractionJob).where(
            ExtractionJob.status == ExtractionJobStatus.PROCESSING.value,
            ExtractionJob.started_at < cutoff,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def recover_stuck_job(
        self,
        job_id: str,
        timeout_minutes: int = 30,
    ) -> ExtractionJob:
        """
        Recover a stuck job by marking it for retry.

        Args:
            job_id: Job UUID
            timeout_minutes: Minutes threshold for considering job stuck

        Returns:
            Updated ExtractionJob

        Raises:
            NotFoundError: If job not found
            ValueError: If job is not stuck
        """
        job = await self.get_job(job_id)

        if job.status != ExtractionJobStatus.PROCESSING.value:
            raise ValueError(f"Job {job_id} is not in PROCESSING status")

        if job.started_at is None:
            raise ValueError(f"Job {job_id} has no started_at timestamp")

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        if job.started_at >= cutoff:
            raise ValueError(f"Job {job_id} is not stuck yet")

        # Mark as failed with retry scheduled
        job.status = ExtractionJobStatus.FAILED.value
        job.error_message = f"Job timed out after {timeout_minutes}+ minutes"
        job.retry_count += 1

        if job.retry_count < job.max_retries:
            # Schedule for retry
            delay = 60 * (2 ** (job.retry_count - 1))
            job.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            logger.info(f"Recovering stuck job {job_id}, retry scheduled in {delay}s")
        else:
            job.completed_at = datetime.now(timezone.utc)
            logger.warning(f"Stuck job {job_id} exceeded max retries")

        await self.db.commit()
        await self.db.refresh(job)

        return job

    async def cleanup_orphaned_jobs(
        self,
        failed_older_than_days: int = 7,
        pending_older_than_days: int = 1,
    ) -> dict[str, int]:
        """
        Cleanup orphaned/abandoned jobs.

        - Failed jobs older than N days: mark as cancelled
        - Pending jobs older than N days: mark as failed (stuck)

        Args:
            failed_older_than_days: Days before failed jobs are cleaned up
            pending_older_than_days: Days before pending jobs are considered stuck

        Returns:
            Dict with counts of cleaned up jobs
        """
        failed_cutoff = datetime.now(timezone.utc) - timedelta(days=failed_older_than_days)
        pending_cutoff = datetime.now(timezone.utc) - timedelta(days=pending_older_than_days)

        result = {"failed_cleaned": 0, "pending_cleaned": 0, "total_cleaned": 0}

        # Clean up old failed jobs
        failed_query = select(ExtractionJob).where(
            ExtractionJob.status == ExtractionJobStatus.FAILED.value,
            ExtractionJob.created_at < failed_cutoff,
            ExtractionJob.retry_count >= ExtractionJob.max_retries,
        )
        failed_result = await self.db.execute(failed_query)
        failed_jobs = list(failed_result.scalars().all())

        for job in failed_jobs:
            job.status = ExtractionJobStatus.CANCELLED.value
            job.completed_at = datetime.now(timezone.utc)
            result["failed_cleaned"] += 1

        # Clean up stuck pending jobs
        stuck_query = select(ExtractionJob).where(
            ExtractionJob.status == ExtractionJobStatus.PENDING.value,
            ExtractionJob.created_at < pending_cutoff,
        )
        stuck_result = await self.db.execute(stuck_query)
        stuck_jobs = list(stuck_result.scalars().all())

        for job in stuck_jobs:
            job.status = ExtractionJobStatus.FAILED.value
            job.error_message = "Job stuck in PENDING status - orphaned"
            job.completed_at = datetime.now(timezone.utc)
            result["pending_cleaned"] += 1

        if failed_jobs or stuck_jobs:
            await self.db.commit()
            result["total_cleaned"] = result["failed_cleaned"] + result["pending_cleaned"]
            logger.info(
                f"Cleanup complete: {result['failed_cleaned']} failed, "
                f"{result['pending_cleaned']} stuck pending jobs"
            )

        return result
