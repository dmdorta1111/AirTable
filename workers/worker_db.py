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
