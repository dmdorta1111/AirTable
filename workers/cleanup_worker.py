#!/usr/bin/env python3
"""
Celery worker for audit log cleanup tasks.

This worker handles scheduled cleanup of old audit logs based on retention policies.
"""

import sys
import os
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from celery import Celery
    from celery.schedules import crontab

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    print("WARNING: Celery not available. Install: pip install celery")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Create Celery app
app = Celery(
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
    include=["src.pybase.t"],
)

# ==============================================================================
# Background Tasks
# ==============================================================================


@app.task(name="cleanup_audit_logs")
def cleanup_audit_logs(retention_days: int = None):
    """
    Cleanup old audit logs based on retention policy.

    Deletes audit logs older than the specified retention period.
    The cleanup action itself is logged for compliance.

    Args:
        retention_days: Number of days to retain logs (default from settings)

    Returns:
        dict with status and count of deleted logs
    """
    from pybase.db.session import AsyncSessionLocal
    from pybase.services.audit_service import AuditService
    from pybase.core.config import settings

    try:
        # Use retention days from settings if not provided
        if retention_days is None:
            retention_days = settings.audit_retention_days

        logger.info(f"Starting audit log cleanup: retaining logs for {retention_days} days")

        # Run the async cleanup function
        async def perform_cleanup():
            async with AsyncSessionLocal() as db:
                service = AuditService()

                # Get count of logs to be deleted before cleanup
                from pybase.models.audit_log import AuditLog
                from sqlalchemy import select
                from datetime import timedelta

                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
                count_query = (
                    select(AuditLog)
                    .where(AuditLog.created_at < cutoff_date)
                )
                result = await db.execute(count_query)
                logs_to_delete = result.scalars().all()
                count_before = len(logs_to_delete)

                # Perform cleanup
                deleted_count = await service.delete_old_logs(db, retention_days)
                await db.commit()

                logger.info(f"Deleted {deleted_count} audit logs older than {retention_days} days")

                return {
                    "status": "completed",
                    "retention_days": retention_days,
                    "deleted_count": deleted_count,
                    "count_before": count_before
                }

        # Import run_async helper from worker_db
        from worker_db import run_async

        result = run_async(perform_cleanup())
        return result

    except Exception as e:
        logger.error(f"Failed to cleanup audit logs: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "retention_days": retention_days
        }


@app.task(name="cleanup_old_audit_logs_by_date")
def cleanup_old_audit_logs_by_date(cutoff_date_str: str):
    """
    Cleanup audit logs older than a specific date.

    Useful for manual cleanup or ad-hoc operations.

    Args:
        cutoff_date_str: Cutoff date in ISO format (YYYY-MM-DD)

    Returns:
        dict with status and count of deleted logs
    """
    from pybase.db.session import AsyncSessionLocal
    from pybase.services.audit_service import AuditService
    from datetime import datetime

    try:
        cutoff_date = datetime.fromisoformat(cutoff_date_str)
        retention_days = (datetime.utcnow() - cutoff_date).days

        logger.info(f"Starting audit log cleanup: deleting logs before {cutoff_date_str}")

        async def perform_cleanup():
            async with AsyncSessionLocal() as db:
                service = AuditService()
                deleted_count = await service.delete_old_logs(db, retention_days)
                await db.commit()

                logger.info(f"Deleted {deleted_count} audit logs before {cutoff_date_str}")

                return {
                    "status": "completed",
                    "cutoff_date": cutoff_date_str,
                    "deleted_count": deleted_count
                }

        from worker_db import run_async
        result = run_async(perform_cleanup())
        return result

    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        return {
            "status": "failed",
            "error": f"Invalid date format: {e}",
            "cutoff_date": cutoff_date_str
        }
    except Exception as e:
        logger.error(f"Failed to cleanup audit logs: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "cutoff_date": cutoff_date_str
        }


# =============================================================================
# Scheduled Tasks
# =============================================================================


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Setup periodic tasks after Celery app configuration.

    Schedules audit log cleanup to run daily at 2 AM UTC.
    """
    from celery.schedules import crontab

    # Run cleanup daily at 2 AM UTC
    sender.add_periodic_task(
        crontab(hour=2, minute=0),  # Daily at 2 AM
        cleanup_audit_logs.s(),
        name='Daily audit log cleanup'
    )

    logger.info("Scheduled periodic audit log cleanup task (daily at 2 AM UTC)")


if __name__ == "__main__":
    logger.info("Starting Celery worker with audit log cleanup background tasks")

    # Configure Celery
    app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
    )

    # Run initial setup
    try:
        logger.info("Celery worker ready for audit log cleanup tasks")
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        sys.exit(1)
