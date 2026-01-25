"""ExtractionJob service for database-backed job management."""

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import NotFoundError
from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus, ExtractionFormat


class ExtractionJobService:
    """Service for extraction job CRUD operations and status management."""

    async def create_job(
        self,
        db: AsyncSession,
        user_id: str,
        extraction_format: ExtractionFormat,
        file_path: Optional[str] = None,
        options: Optional[dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> ExtractionJob:
        """
        Create a new extraction job.

        Args:
            db: Database session
            user_id: User ID creating the job
            extraction_format: Format of extraction (pdf, dxf, ifc, step, werk24)
            file_path: Path to input file
            options: Extraction options as dict
            max_retries: Maximum retry attempts

        Returns:
            Created ExtractionJob

        """
        job = ExtractionJob(
            user_id=user_id,
            status=ExtractionJobStatus.PENDING.value,
            extraction_format=extraction_format.value,
            file_path=file_path,
            options=json.dumps(options or {}),
            max_retries=max_retries,
            retry_count=0,
            progress=0,
            processed_items=0,
            failed_items=0,
        )

        db.add(job)
        await db.commit()
        await db.refresh(job)

        return job

    async def get_job_by_id(
        self,
        db: AsyncSession,
        job_id: str,
    ) -> ExtractionJob:
        """
        Get a job by ID.

        Args:
            db: Database session
            job_id: Job ID

        Returns:
            ExtractionJob

        Raises:
            NotFoundError: If job not found

        """
        job = await db.get(ExtractionJob, job_id)
        if not job:
            raise NotFoundError(f"Extraction job {job_id} not found")

        return job

    async def get_job_by_celery_task_id(
        self,
        db: AsyncSession,
        celery_task_id: str,
    ) -> Optional[ExtractionJob]:
        """
        Get a job by Celery task ID.

        Args:
            db: Database session
            celery_task_id: Celery task ID

        Returns:
            ExtractionJob or None

        """
        query = select(ExtractionJob).where(
            ExtractionJob.celery_task_id == celery_task_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_job_status(
        self,
        db: AsyncSession,
        job_id: str,
        status: ExtractionJobStatus,
        error_message: Optional[str] = None,
        error_stack_trace: Optional[str] = None,
    ) -> ExtractionJob:
        """
        Update job status.

        Args:
            db: Database session
            job_id: Job ID
            status: New status
            error_message: Optional error message
            error_stack_trace: Optional error stack trace

        Returns:
            Updated ExtractionJob

        Raises:
            NotFoundError: If job not found

        """
        job = await self.get_job_by_id(db, job_id)

        job.status = status.value

        if error_message:
            job.error_message = error_message
        if error_stack_trace:
            job.error_stack_trace = error_stack_trace

        # Update timestamps based on status
        now = datetime.now(timezone.utc)
        if status == ExtractionJobStatus.PROCESSING and not job.started_at:
            job.started_at = now
        elif status in [
            ExtractionJobStatus.COMPLETED,
            ExtractionJobStatus.FAILED,
            ExtractionJobStatus.CANCELLED,
        ]:
            job.completed_at = now
            # Calculate duration if started_at exists
            if job.started_at:
                duration = now - job.started_at
                job.duration_ms = int(duration.total_seconds() * 1000)

        await db.commit()
        await db.refresh(job)

        return job

    async def update_job_progress(
        self,
        db: AsyncSession,
        job_id: str,
        progress: int,
        processed_items: Optional[int] = None,
        failed_items: Optional[int] = None,
        total_items: Optional[int] = None,
    ) -> ExtractionJob:
        """
        Update job progress.

        Args:
            db: Database session
            job_id: Job ID
            progress: Progress percentage (0-100)
            processed_items: Number of successfully processed items
            failed_items: Number of failed items
            total_items: Total number of items to process

        Returns:
            Updated ExtractionJob

        Raises:
            NotFoundError: If job not found

        """
        job = await self.get_job_by_id(db, job_id)

        job.progress = progress

        if processed_items is not None:
            job.processed_items = processed_items
        if failed_items is not None:
            job.failed_items = failed_items
        if total_items is not None:
            job.total_items = total_items

        await db.commit()
        await db.refresh(job)

        return job

    async def set_celery_task_id(
        self,
        db: AsyncSession,
        job_id: str,
        celery_task_id: str,
    ) -> ExtractionJob:
        """
        Set the Celery task ID for a job.

        Args:
            db: Database session
            job_id: Job ID
            celery_task_id: Celery task ID

        Returns:
            Updated ExtractionJob

        Raises:
            NotFoundError: If job not found

        """
        job = await self.get_job_by_id(db, job_id)
        job.celery_task_id = celery_task_id

        await db.commit()
        await db.refresh(job)

        return job

    async def increment_retry(
        self,
        db: AsyncSession,
        job_id: str,
        error_message: Optional[str] = None,
    ) -> ExtractionJob:
        """
        Increment retry count and update status.

        Args:
            db: Database session
            job_id: Job ID
            error_message: Error message for this retry attempt

        Returns:
            Updated ExtractionJob

        Raises:
            NotFoundError: If job not found

        """
        job = await self.get_job_by_id(db, job_id)

        job.increment_retry()
        job.last_retry_at = datetime.now(timezone.utc)

        if error_message:
            job.error_message = error_message

        # Clear previous completion data
        job.completed_at = None
        job.duration_ms = None

        await db.commit()
        await db.refresh(job)

        return job

    async def can_retry(
        self,
        db: AsyncSession,
        job_id: str,
    ) -> bool:
        """
        Check if a job can be retried.

        Args:
            db: Database session
            job_id: Job ID

        Returns:
            True if job can be retried, False otherwise

        """
        try:
            job = await self.get_job_by_id(db, job_id)
            return job.can_retry()
        except NotFoundError:
            return False

    async def update_job_results(
        self,
        db: AsyncSession,
        job_id: str,
        results: dict[str, Any],
        result_path: Optional[str] = None,
    ) -> ExtractionJob:
        """
        Update job results.

        Args:
            db: Database session
            job_id: Job ID
            results: Results data as dict
            result_path: Optional path to results file

        Returns:
            Updated ExtractionJob

        Raises:
            NotFoundError: If job not found

        """
        job = await self.get_job_by_id(db, job_id)

        job.set_results(results)

        if result_path:
            job.result_path = result_path

        await db.commit()
        await db.refresh(job)

        return job

    async def list_jobs(
        self,
        db: AsyncSession,
        user_id: Optional[str] = None,
        status: Optional[ExtractionJobStatus] = None,
        extraction_format: Optional[ExtractionFormat] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ExtractionJob], int]:
        """
        List extraction jobs with filters and pagination.

        Args:
            db: Database session
            user_id: Optional user ID to filter by
            status: Optional status to filter by
            extraction_format: Optional format to filter by
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (jobs, total count)

        """
        offset = (page - 1) * page_size

        # Build base query
        query = select(ExtractionJob)

        # Apply filters
        if user_id:
            query = query.where(ExtractionJob.user_id == user_id)
        if status:
            query = query.where(ExtractionJob.status == status.value)
        if extraction_format:
            query = query.where(ExtractionJob.extraction_format == extraction_format.value)

        # Get total count
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(ExtractionJob.created_at.desc())
        query = query.offset(offset)
        query = query.limit(page_size)

        result = await db.execute(query)
        jobs = result.scalars().all()

        return list(jobs), total

    async def cancel_job(
        self,
        db: AsyncSession,
        job_id: str,
    ) -> ExtractionJob:
        """
        Cancel a job.

        Args:
            db: Database session
            job_id: Job ID

        Returns:
            Cancelled ExtractionJob

        Raises:
            NotFoundError: If job not found

        """
        job = await self.get_job_by_id(db, job_id)

        # Only cancel pending or processing jobs
        if job.status_enum not in [
            ExtractionJobStatus.PENDING,
            ExtractionJobStatus.PROCESSING,
            ExtractionJobStatus.RETRYING,
        ]:
            return job

        job.status = ExtractionJobStatus.CANCELLED.value
        job.completed_at = datetime.now(timezone.utc)

        if job.started_at:
            duration = job.completed_at - job.started_at
            job.duration_ms = int(duration.total_seconds() * 1000)

        await db.commit()
        await db.refresh(job)

        return job

    async def delete_job(
        self,
        db: AsyncSession,
        job_id: str,
    ) -> None:
        """
        Delete a job permanently.

        Args:
            db: Database session
            job_id: Job ID

        Raises:
            NotFoundError: If job not found

        """
        job = await self.get_job_by_id(db, job_id)
        await db.delete(job)
        await db.commit()

    async def cleanup_old_jobs(
        self,
        db: AsyncSession,
        older_than_days: int = 30,
        status: Optional[ExtractionJobStatus] = None,
        dry_run: bool = False,
    ) -> int:
        """
        Delete old jobs.

        Args:
            db: Database session
            older_than_days: Delete jobs older than this many days
            status: Optional status filter (default: completed, failed, cancelled)
            dry_run: If True, count jobs without deleting

        Returns:
            Number of jobs deleted (or counted if dry_run)

        """
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

        # Default to cleaning up completed/failed/cancelled jobs
        if status is None:
            query = select(ExtractionJob).where(
                ExtractionJob.created_at < cutoff_date,
                ExtractionJob.status.in_(
                    [
                        ExtractionJobStatus.COMPLETED.value,
                        ExtractionJobStatus.FAILED.value,
                        ExtractionJobStatus.CANCELLED.value,
                    ]
                ),
            )
        else:
            query = select(ExtractionJob).where(
                ExtractionJob.created_at < cutoff_date,
                ExtractionJob.status == status.value,
            )

        result = await db.execute(query)
        jobs = result.scalars().all()

        count = len(jobs)

        if not dry_run:
            for job in jobs:
                await db.delete(job)
            await db.commit()

        return count

    async def get_job_statistics(
        self,
        db: AsyncSession,
        user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get job statistics.

        Args:
            db: Database session
            user_id: Optional user ID to filter by

        Returns:
            Dictionary with job statistics

        """
        from sqlalchemy import func

        # Build base query
        query = select(func.count(ExtractionJob.id))

        if user_id:
            query = query.where(ExtractionJob.user_id == user_id)

        # Get counts by status
        stats: dict[str, Any] = {}

        for status in ExtractionJobStatus:
            status_query = query.where(ExtractionJob.status == status.value)
            result = await db.execute(status_query)
            stats[f"{status.value}_count"] = result.scalar() or 0

        # Get total count
        total_result = await db.execute(query)
        stats["total_count"] = total_result.scalar() or 0

        return stats

    async def reset_job_for_retry(
        self,
        db: AsyncSession,
        job_id: str,
    ) -> ExtractionJob:
        """
        Reset a failed job to pending status for manual retry.

        Args:
            db: Database session
            job_id: Job ID

        Returns:
            Reset ExtractionJob

        Raises:
            NotFoundError: If job not found

        """
        job = await self.get_job_by_id(db, job_id)

        # Only reset failed jobs
        if job.status_enum != ExtractionJobStatus.FAILED:
            raise ValueError(
                f"Only failed jobs can be reset for retry. Current status: {job.status}"
            )

        job.status = ExtractionJobStatus.PENDING.value
        job.error_message = None
        job.error_stack_trace = None
        job.started_at = None
        job.completed_at = None
        job.duration_ms = None
        job.celery_task_id = None
        job.progress = 0

        await db.commit()
        await db.refresh(job)

        return job
