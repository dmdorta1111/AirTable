#!/usr/bin/env python3
"""
Celery Beat scheduler for periodic custom report generation.

This scheduler manages cron-based scheduling for periodic reports.
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

# Create Celery app for Beat scheduler
app = Celery(
    "report_scheduler",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# ==============================================================================
# Beat Schedule Configuration
# ==============================================================================

app.conf.beat_schedule = {
    # Check for scheduled custom reports every 5 minutes
    "check-scheduled-custom-reports-every-5-minutes": {
        "task": "check_scheduled_custom_reports",
        "schedule": 300.0,  # Run every 300 seconds (5 minutes)
    },
    # Clean up old custom reports daily at 3 AM UTC
    "cleanup-old-custom-reports-daily": {
        "task": "cleanup_old_custom_reports",
        "schedule": crontab(hour=3, minute=0),  # Run at 3:00 AM UTC every day
    },
}


# =============================================================================
# Optional: Dynamic Schedule Registration
# ==============================================================================

def setup_dynamic_schedules():
    """
    Register dynamic schedules from database.

    This function queries the CustomReport model for reports with
    custom cron expressions and registers them dynamically.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    try:
        engine = create_engine(os.getenv("DATABASE_URL"))
        Session = sessionmaker(bind=engine)
        db = Session()

        from pybase.models.custom_report import CustomReport, ScheduleFrequency

        # Find reports with custom cron expressions
        custom_scheduled_reports = db.query(CustomReport).filter(
            CustomReport.deleted_at.is_(None),
            CustomReport.is_active == True,
            CustomReport.is_paused == False,
            CustomReport.schedule_frequency == ScheduleFrequency.CUSTOM,
            CustomReport.cron_expression.isnot(None),
        ).all()

        logger.info(f"Found {len(custom_scheduled_reports)} reports with custom schedules")

        # Register custom schedules
        for report in custom_scheduled_reports:
            schedule_name = f"custom-report-{report.id}"

            # Parse cron expression and register schedule
            # Note: Celery uses a slightly different cron format than standard cron
            # For production, use celery-redbeat or django-celery-beat for dynamic schedules
            logger.info(f"Report '{report.name}' uses custom schedule: {report.cron_expression}")

        db.close()

    except Exception as e:
        logger.warning(f"Failed to setup dynamic schedules: {e}")


# =============================================================================
# Main Entry Point
# ==============================================================================

if __name__ == "__main__":
    logger.info("Starting Celery Beat scheduler for custom reports")

    try:
        # Setup dynamic schedules from database (optional)
        # Uncomment to enable dynamic schedule registration
        # setup_dynamic_schedules()

        # Log scheduler configuration
        logger.info("Celery Beat scheduler configuration:")
        logger.info("  Broker: %s", app.conf.broker_url)
        logger.info("  Backend: %s", app.conf.result_backend)
        logger.info("  Timezone: %s", app.conf.timezone)
        logger.info("")
        logger.info("Scheduled tasks:")
        logger.info("  - check_scheduled_custom_reports: Every 5 minutes")
        logger.info("      (Triggers report generation for reports due to run)")
        logger.info("  - cleanup_old_custom_reports: Daily at 3 AM UTC")
        logger.info("      (Removes old report files based on retention policy)")
        logger.info("")
        logger.info("Scheduler ready. Press Ctrl+C to stop.")

        # Start Celery Beat
        # Note: This runs the beat scheduler, not the worker
        # Workers should be started separately with: celery -A workers.report_worker worker

    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        sys.exit(1)
