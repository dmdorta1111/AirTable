"""
Database helper for Celery workers.

Provides async database access for background tasks.
"""

import asyncio
from typing import Optional


async def update_job_start(job_id: str, celery_task_id: str) -> Optional["ExtractionJob"]:
    """
    Update job when Celery task starts.

    Sets celery_task_id and status to PROCESSING.

    Args:
        job_id: Extraction job ID
        celery_task_id: Celery task ID

    Returns:
        Updated job or None if job not found
    """
    if not job_id:
        return None

    async with AsyncSessionLocal() as db:
        try:
            service = ExtractionJobService()
            # Set Celery task ID
            job = await service.set_celery_task_id(db, job_id, celery_task_id)
            # Update status to PROCESSING
            job = await service.update_job_status(db, job_id, ExtractionJobStatus.PROCESSING)
            return job
        except Exception as e:
            print(f"Error updating job start: {e}")
            return None


async def update_job_complete(
    job_id: str,
    status: str,  # ExtractionJobStatus value
    result: Optional[dict] = None,
    error_message: Optional[str] = None,
    error_stack_trace: Optional[str] = None,
) -> Optional["ExtractionJob"]:
    """
    Update job when Celery task completes.

    Sets status to COMPLETED or FAILED and stores results.

    Args:
        job_id: Extraction job ID
        status: Final job status (COMPLETED or FAILED)
        result: Extraction results (if successful)
        error_message: Error message (if failed)
        error_stack_trace: Error stack trace (if failed)

    Returns:
        Updated job or None if job not found
    """
    if not job_id:
        return None

    # Lazy imports to avoid circular dependency with FastAPI
    from pybase.db.session import AsyncSessionLocal
    from pybase.models.extraction_job import ExtractionJobStatus
    from pybase.services.extraction_job import ExtractionJobService

    async with AsyncSessionLocal() as db:
        try:
            service = ExtractionJobService()

            # Update status
            job = await service.update_job_status(
                db,
                job_id,
                status,
                error_message=error_message,
                error_stack_trace=error_stack_trace,
            )

            # Store results if successful
            if status == ExtractionJobStatus.COMPLETED and result:
                import json

                await service.update_job_results(db, job_id, result)

            return job
        except Exception as e:
            print(f"Error updating job complete: {e}")
            return None


async def update_job_progress(
    job_id: str,
    progress: int,
    processed_items: Optional[int] = None,
    failed_items: Optional[int] = None,
) -> Optional["ExtractionJob"]:
    """
    Update job progress.

    Args:
        job_id: Extraction job ID
        progress: Progress percentage (0-100)
        processed_items: Number of successfully processed items
        failed_items: Number of failed items

    Returns:
        Updated job or None if job not found
    """
    if not job_id:
        return None

    # Lazy imports to avoid circular dependency with FastAPI
    from pybase.db.session import AsyncSessionLocal
    from pybase.services.extraction_job import ExtractionJobService

    async with AsyncSessionLocal() as db:
        try:
            service = ExtractionJobService()
            job = await service.update_job_progress(
                db,
                job_id,
                progress,
                processed_items=processed_items,
                failed_items=failed_items,
            )
            return job
        except Exception as e:
            print(f"Error updating job progress: {e}")
            return None


async def update_export_job_start(job_id: str, celery_task_id: str, total_records: int = None) -> Optional["ExportJob"]:
    """
    Update export job when Celery task starts.

    Sets celery_task_id and status to PROCESSING.

    Args:
        job_id: Export job ID
        celery_task_id: Celery task ID
        total_records: Total records to export (optional)

    Returns:
        Updated job or None if job not found
    """
    if not job_id:
        return None

    from pybase.db.session import AsyncSessionLocal
    from pybase.models.export_job import ExportJob
    from datetime import datetime, timezone

    async with AsyncSessionLocal() as db:
        try:
            job = await db.get(ExportJob, str(job_id))
            if not job:
                return None

            job.celery_task_id = celery_task_id
            job.status = "processing"
            job.started_at = datetime.now(timezone.utc)
            if total_records is not None:
                job.total_records = total_records

            await db.commit()
            await db.refresh(job)
            return job
        except Exception as e:
            print(f"Error updating export job start: {e}")
            return None


async def update_export_job_complete(
    job_id: str,
    status: str,
    file_path: str = None,
    download_url: str = None,
    file_size: int = None,
    record_count: int = None,
    error_message: str = None,
    error_stack_trace: str = None,
) -> Optional["ExportJob"]:
    """
    Update export job when Celery task completes.

    Sets status to COMPLETED or FAILED and stores results.

    Args:
        job_id: Export job ID
        status: Final job status (completed or failed)
        file_path: Path to exported file (if successful)
        download_url: Download URL for exported file (if successful)
        file_size: Size of exported file in bytes (if successful)
        record_count: Number of records exported (if successful)
        error_message: Error message (if failed)
        error_stack_trace: Error stack trace (if failed)

    Returns:
        Updated job or None if job not found
    """
    if not job_id:
        return None

    from pybase.db.session import AsyncSessionLocal
    from pybase.models.export_job import ExportJob
    from datetime import datetime, timezone, timedelta

    async with AsyncSessionLocal() as db:
        try:
            job = await db.get(ExportJob, str(job_id))
            if not job:
                return None

            job.status = status
            job.completed_at = datetime.now(timezone.utc)

            # Calculate duration
            if job.started_at:
                duration = job.completed_at - job.started_at
                job.duration_ms = int(duration.total_seconds() * 1000)

            # Set results for successful exports
            if status == "completed":
                if file_path:
                    job.file_path = file_path
                if download_url:
                    job.download_url = download_url
                if file_size is not None:
                    job.results = f'{{"file_size": {file_size}}}'
                if record_count is not None:
                    job.processed_records = record_count
                    job.progress = 100

                # Set expiry to 7 days from now
                job.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
            else:
                # Set error information for failed exports
                if error_message:
                    job.error_message = error_message
                if error_stack_trace:
                    job.error_stack_trace = error_stack_trace

            await db.commit()
            await db.refresh(job)
            return job
        except Exception as e:
            print(f"Error updating export job complete: {e}")
            return None


async def update_export_job_progress(
    job_id: str,
    progress: int,
    processed_records: int = None,
) -> Optional["ExportJob"]:
    """
    Update export job progress.

    Args:
        job_id: Export job ID
        progress: Progress percentage (0-100)
        processed_records: Number of records processed so far

    Returns:
        Updated job or None if job not found
    """
    if not job_id:
        return None

    from pybase.db.session import AsyncSessionLocal
    from pybase.models.export_job import ExportJob

    async with AsyncSessionLocal() as db:
        try:
            job = await db.get(ExportJob, str(job_id))
            if not job:
                return None

            job.progress = progress
            if processed_records is not None:
                job.processed_records = processed_records

            await db.commit()
            await db.refresh(job)
            return job
        except Exception as e:
            print(f"Error updating export job progress: {e}")
            return None


def run_async(coro):
    """
    Run async function from sync context.

    Args:
        coro: Async function to run

    Returns:
        Result of async function
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)
