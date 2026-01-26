"""
Retry service for failed extraction jobs.

Implements exponential backoff retry logic for extraction jobs,
with configurable delays and maximum retry attempts.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from pybase.db.session import get_db_context
from pybase.models.extraction_job import ExtractionJobStatus
from pybase.services.extraction_job_service import ExtractionJobService
from pybase.services.extraction.background import run_extraction_background

logger = logging.getLogger(__name__)


# Default retry configuration
DEFAULT_BASE_DELAY_SECONDS = 60  # 1 minute
DEFAULT_MAX_DELAY_SECONDS = 3600  # 1 hour
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_MULTIPLIER = 2.0


def calculate_retry_delay(
    retry_count: int,
    base_delay: int = DEFAULT_BASE_DELAY_SECONDS,
    max_delay: int = DEFAULT_MAX_DELAY_SECONDS,
    multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
) -> int:
    """
    Calculate retry delay using exponential backoff.

    Args:
        retry_count: Current retry attempt (1-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap in seconds
        multiplier: Backoff multiplier

    Returns:
        Delay in seconds
    """
    delay = base_delay * (multiplier ** (retry_count - 1))
    return min(int(delay), max_delay)


async def process_retryable_jobs(
    batch_size: int = 10,
    base_delay: int = DEFAULT_BASE_DELAY_SECONDS,
) -> int:
    """
    Process all jobs eligible for retry.

    Finds failed jobs where:
    - retry_count < max_retries
    - next_retry_at is in the past or NULL

    Args:
        batch_size: Maximum jobs to process in one batch
        base_delay: Base delay for exponential backoff

    Returns:
        Number of jobs queued for retry
    """
    async with get_db_context() as db:
        service = ExtractionJobService(db)
        retryable_jobs = await service.list_retryable_jobs(limit=batch_size)

        if not retryable_jobs:
            logger.debug("No retryable jobs found")
            return 0

        queued_count = 0
        for job in retryable_jobs:
            try:
                # Reset job for retry
                await service.reset_for_retry(job.id)
                queued_count += 1
                logger.info(
                    f"Queued job {job.id} for retry "
                    f"(attempt {job.retry_count + 1}/{job.max_retries})"
                )
            except Exception as e:
                logger.error(f"Failed to queue job {job.id} for retry: {e}")

        return queued_count


async def retry_single_job(job_id: str) -> bool:
    """
    Manually retry a specific failed job.

    Args:
        job_id: Job UUID to retry

    Returns:
        True if job was queued for retry, False otherwise
    """
    async with get_db_context() as db:
        service = ExtractionJobService(db)

        try:
            job = await service.get_job(job_id)
        except Exception:
            logger.error(f"Job {job_id} not found")
            return False

        # Check if job can be retried
        if job.status != ExtractionJobStatus.FAILED.value:
            logger.warning(f"Job {job_id} is not in failed state (status: {job.status})")
            return False

        if job.retry_count >= job.max_retries:
            logger.warning(
                f"Job {job_id} has exhausted retries ({job.retry_count}/{job.max_retries})"
            )
            return False

        # Reset and trigger background task
        await service.reset_for_retry(job_id)
        logger.info(f"Manually retrying job {job_id}")

        # Run extraction in background
        asyncio.create_task(run_extraction_background(job_id))
        return True


async def run_retry_worker(
    interval_seconds: int = 60,
    batch_size: int = 10,
    stop_event: asyncio.Event | None = None,
) -> None:
    """
    Background worker that periodically processes retryable jobs.

    Args:
        interval_seconds: Seconds between retry checks
        batch_size: Maximum jobs to process per interval
        stop_event: Event to signal worker shutdown
    """
    logger.info(f"Starting retry worker (interval: {interval_seconds}s)")

    while True:
        if stop_event and stop_event.is_set():
            logger.info("Retry worker stopping")
            break

        try:
            queued = await process_retryable_jobs(batch_size=batch_size)
            if queued > 0:
                logger.info(f"Queued {queued} jobs for retry")

                # Process the queued jobs
                async with get_db_context() as db:
                    service = ExtractionJobService(db)
                    pending_jobs = await service.list_pending_jobs(limit=batch_size)

                    for job in pending_jobs:
                        asyncio.create_task(run_extraction_background(job.id))

        except Exception as e:
            logger.exception(f"Error in retry worker: {e}")

        # Wait for next interval
        try:
            if stop_event:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=interval_seconds,
                )
                break
            else:
                await asyncio.sleep(interval_seconds)
        except asyncio.TimeoutError:
            continue


async def get_retry_stats() -> dict[str, int]:
    """
    Get statistics about retryable jobs.

    Returns:
        Dict with retry statistics
    """
    async with get_db_context() as db:
        service = ExtractionJobService(db)

        # Get job stats by status
        stats = await service.get_job_stats()

        # Count retryable jobs
        retryable = await service.list_retryable_jobs(limit=1000)

        return {
            "pending": stats.get("pending", 0),
            "processing": stats.get("processing", 0),
            "completed": stats.get("completed", 0),
            "failed": stats.get("failed", 0),
            "cancelled": stats.get("cancelled", 0),
            "retryable": len(retryable),
        }
