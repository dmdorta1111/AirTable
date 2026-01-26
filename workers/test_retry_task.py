#!/usr/bin/env python3
"""
Test Celery task for simulating retry behavior with exponential backoff.

This task is designed to fail the first N attempts and succeed on the N+1 attempt,
allowing verification of retry logic, exponential backoff, and max retry behavior.

Usage:
    # Start a Celery worker with this test task
    celery -A workers.test_retry_task worker -l INFO

    # In another terminal, submit the test job
    python scripts/verify_retry_logic.py
"""

import os
import sys
import logging
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    print("WARNING: Celery not available. Install: pip install celery")
    sys.exit(1)

# Import worker database helper
from workers.worker_db import run_async, update_job_complete, update_job_start

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Celery app
app = Celery(
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
    include=["workers.test_retry_task"],
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_default_max_retries=3,  # Default max retries
)


@app.task(bind=True, name="test_extraction_retry")
def test_extraction_retry(self, file_path: str, options: dict = None, job_id: str = None):
    """
    Test extraction task that simulates retry behavior.

    This task will fail the first 3 attempts and succeed on the 4th attempt,
    allowing verification of:
    - Exponential backoff timing (1s, 2s, 4s, 8s, ...)
    - Max retry enforcement
    - Database retry tracking
    - Status transitions (PROCESSING → RETRYING → COMPLETED)

    Args:
        self: Celery task instance (for retry support)
        file_path: Path to test file
        options: Extraction options
            - fail_attempts: Number of times to fail before succeeding (default: 3)
            - max_retries: Maximum retry attempts (default: 3)
        job_id: Optional ExtractionJob ID for database tracking

    Returns:
        Dictionary with extraction results

    Retry Behavior:
        - Attempt 1: Fail immediately, retry in 1s (2^0)
        - Attempt 2: Fail immediately, retry in 2s (2^1)
        - Attempt 3: Fail immediately, retry in 4s (2^2)
        - Attempt 4: Succeed (if fail_attempts=3)
    """
    options = options or {}
    fail_attempts = options.get("fail_attempts", 3)
    max_retries = options.get("max_retries", 3)

    # Get current retry count from Celery
    retry_count = self.request.retries

    # Update job start in database
    run_async(update_job_start(job_id, self.request.id))

    logger.info(f"=" * 80)
    logger.info(f"Test extraction task: Attempt {retry_count + 1}/{max_retries + 1}")
    logger.info(f"File: {file_path}")
    logger.info(f"Job ID: {job_id}")
    logger.info(f"Will fail first {fail_attempts} attempts, then succeed")
    logger.info(f"=" * 80)

    # Simulate extraction failure for first N attempts
    if retry_count < fail_attempts:
        # Calculate exponential backoff
        backoff = 2 ** retry_count

        error_msg = f"Simulated extraction failure (attempt {retry_count + 1}/{fail_attempts + 1})"

        logger.warning(f"❌ Task failed: {error_msg}")
        logger.warning(f"⏱️  Will retry in {backoff}s (exponential backoff: 2^{retry_count} = {backoff})")
        logger.warning(f"📊 Retry progress: {retry_count + 1}/{fail_attempts} failures before success")

        # Log timestamp for timing verification
        logger.warning(f"⏰ Timestamp: {datetime.now(timezone.utc).isoformat()}")

        if retry_count < max_retries:
            # Trigger retry with exponential backoff
            raise self.retry(
                exc=Exception(error_msg),
                countdown=backoff,
                max_retries=max_retries
            )
        else:
            # Max retries exceeded - mark as failed
            logger.error(f"💀 Max retries ({max_retries}) exceeded. Marking job as failed.")
            run_async(update_job_complete(job_id, "failed", error_message=error_msg))
            return {
                "status": "failed",
                "file_path": file_path,
                "error": error_msg,
                "retry_count": retry_count,
                "max_retries_exceeded": True
            }

    # Success on attempt N+1
    logger.info(f"✅ Task succeeded on attempt {retry_count + 1}!")
    logger.info(f"⏰ Timestamp: {datetime.now(timezone.utc).isoformat()}")

    # Simulate successful extraction result
    result = {
        "source_file": os.path.basename(file_path),
        "source_type": "test_retry",
        "success": True,
        "retry_count": retry_count,
        "attempts_before_success": retry_count + 1,
        "test_timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "test_mode": "retry_simulation",
            "fail_attempts_configured": fail_attempts,
            "actual_attempts": retry_count + 1
        }
    }

    # Update job complete in database
    run_async(update_job_complete(job_id, "completed", result=result))

    logger.info(f"🎉 Test extraction completed successfully after {retry_count} retries")
    logger.info(f"📊 Total attempts: {retry_count + 1}")

    return {
        "status": "completed",
        "file_path": file_path,
        "result": result
    }


if __name__ == "__main__":
    logger.info("Starting Celery worker with test retry task")
    logger.info("=" * 80)
    logger.info("This worker provides a test task that simulates retry behavior.")
    logger.info("Task will fail first 3 attempts, then succeed on 4th attempt.")
    logger.info("Use this to verify:")
    logger.info("  ✓ Exponential backoff (1s, 2s, 4s, 8s, ...)")
    logger.info("  ✓ Max retry enforcement (max_retries=3)")
    logger.info("  ✓ Database retry tracking")
    logger.info("  ✓ Status transitions")
    logger.info("=" * 80)

    try:
        app.autodiscover_tasks(["workers"])
        logger.info("Celery test retry worker ready")
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        sys.exit(1)
