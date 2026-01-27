#!/usr/bin/env python3
"""
Celery worker for background maintenance tasks.

This worker handles periodic maintenance operations including trash purging,
cache cleanup, and other system maintenance tasks.
"""

import sys
import os
from datetime import datetime, timezone
from pathlib import Path
import logging

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
from workers.worker_db import run_async

# Setup logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Create Celery app
app = Celery(
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
    include=["workers.celery_maintenance_worker"],
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
    task_default_max_retries=3,  # Default max retries for all tasks
)

# ==============================================================================
# Background Tasks
# ==============================================================================


@app.task(bind=True, name="purge_old_trash")
def purge_old_trash(self, retention_days: int = None, dry_run: bool = False):
    """
    Permanently delete records that have been in trash longer than retention period.

    This task is typically run on a schedule (e.g., daily) to automatically clean up
    old deleted records and free up storage space.

    Args:
        self: Celery task instance (for retry support)
        retention_days: Optional retention period in days (defaults to config setting)
        dry_run: If True, only report what would be deleted without actually deleting

    Returns:
        Dictionary with purge results including count of deleted records
    """
    from pybase.db.session import AsyncSessionLocal
    from pybase.services.trash import TrashService

    # Get retention days from config or parameter
    if retention_days is None:
        from pybase.core.config import settings
        retention_days = settings.trash_retention_days

    logger.info(f"Starting trash purge (retention: {retention_days} days, dry_run: {dry_run})")

    async def run_purge():
        async with AsyncSessionLocal() as db:
            service = TrashService()

            if dry_run:
                # Count records that would be purged
                from datetime import timedelta
                from sqlalchemy import and_, select, func

                cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
                from pybase.models.record import Record

                count_query = select(func.count()).select_from(Record).where(
                    and_(
                        Record.deleted_at.is_not(None),
                        Record.deleted_at < cutoff_date,
                    )
                )
                result = await db.execute(count_query)
                count = result.scalar() or 0

                logger.info(f"Dry run: {count} records would be purged")
                return {
                    "status": "dry_run",
                    "retention_days": retention_days,
                    "would_purge": count,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            else:
                # Actually purge old records
                purged_count = await service.purge_old_records(db, retention_days=retention_days)

                logger.info(f"Purged {purged_count} records older than {retention_days} days")
                return {
                    "status": "completed",
                    "retention_days": retention_days,
                    "purged_count": purged_count,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

    try:
        result = run_async(run_purge())
        return result

    except Exception as e:
        logger.error(f"Trash purge failed: {e}")

        # Don't retry database errors - they're likely transient
        # Retry logic can be added here if needed
        return {
            "status": "failed",
            "retention_days": retention_days,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@app.task(bind=True, name="cleanup_expired_cache")
def cleanup_expired_cache(self, cache_type: str = "all"):
    """
    Clean up expired cache entries.

    Args:
        self: Celery task instance (for retry support)
        cache_type: Type of cache to clean (record, table, workspace, all)

    Returns:
        Dictionary with cleanup results
    """
    logger.info(f"Starting cache cleanup for type: {cache_type}")

    try:
        # This is a placeholder for future cache cleanup implementation
        # Currently, cache entries are cleaned up on a per-key basis via TTL

        logger.info(f"Cache cleanup completed for type: {cache_type}")
        return {
            "status": "completed",
            "cache_type": cache_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        logger.error(f"Cache cleanup failed for type {cache_type}: {e}")
        return {
            "status": "failed",
            "cache_type": cache_type,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# =============================================================================
# Worker Entry Point
# =============================================================================


if __name__ == "__main__":
    logger.info("Starting Celery worker with maintenance background tasks")

    # Run initial setup
    try:
        app.autodiscover_tasks(["workers"])
        logger.info("Celery maintenance worker ready")
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        sys.exit(1)
