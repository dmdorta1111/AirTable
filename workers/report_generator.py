#!/usr/bin/env python3
"""
Celery worker for scheduled report generation.

This worker processes scheduled reports, generates exports (PDF, Excel, CSV),
and delivers them via email.
"""

import sys
import os
from datetime import datetime
import logging
import json

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
    "report_generator",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
    include=["workers.report_generator"],
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
# Background Tasks
# ==============================================================================


@app.task(name="generate_scheduled_report", bind=True, max_retries=3)
def generate_scheduled_report(self, report_id: str, schedule_id: str = None):
    """
    Generate a scheduled report.

    This is the main task that:
    1. Fetches report configuration
    2. Generates the report in the specified format
    3. Delivers the report via email (if configured)
    4. Updates the report schedule status

    Args:
        report_id: UUID of the report to generate
        schedule_id: UUID of the report schedule run (if scheduled)

    Returns:
        dict: Status and result information
    """
    from pybase.services.report import ReportService
    from pybase.models.report import Report, ReportSchedule, ReportStatus
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    logger.info(f"Starting report generation for report_id={report_id}")

    try:
        # Setup database connection
        engine = create_engine(os.getenv("DATABASE_URL"))
        Session = sessionmaker(bind=engine)
        db = Session()

        # Fetch report configuration
        report = db.query(Report).filter(Report.id == report_id, Report.deleted_at.is_(None)).first()
        if not report:
            logger.error(f"Report not found: {report_id}")
            return {"status": "failed", "error": "Report not found"}

        # Check if report is active
        if not report.is_active or report.is_paused:
            logger.warning(f"Report {report_id} is not active or is paused")
            return {"status": "skipped", "reason": "Report inactive or paused"}

        # Get or create schedule record
        schedule = None
        if schedule_id:
            schedule = db.query(ReportSchedule).filter(ReportSchedule.id == schedule_id).first()
        else:
            # Create a new schedule record for manual generation
            from uuid import uuid4
            from pybase.db.base import utc_now

            schedule = ReportSchedule(
                id=str(uuid4()),
                report_id=report_id,
                scheduled_at=utc_now(),
            )
            db.add(schedule)
            db.commit()
            schedule_id = schedule.id

        # Mark schedule as running
        if schedule:
            schedule.start()
            db.commit()

        logger.info(f"Generating report: {report.name} (format: {report.format})")

        # Generate the report using ReportService
        # Note: This is a synchronous call in the worker context
        service = ReportService()

        # Parse configurations
        export_config = report.get_export_config_dict()
        delivery_config = report.get_delivery_config_dict()

        # Generate report file
        # The actual generation will be implemented in subtask 6-2
        output_path = f"./reports/{report_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{report.format}"

        # Placeholder for actual report generation
        # This will be implemented in future subtasks
        logger.info(f"Report generation placeholder - output would be: {output_path}")

        # Update schedule as completed
        if schedule:
            schedule.complete(
                output_path=output_path,
                output_size_bytes=0,  # Will be actual size after generation
                record_count=0,  # Will be actual count after generation
            )
            db.commit()

        # Update report statistics
        report.update_stats(success=True, duration_seconds=schedule.duration_seconds)
        report.last_output_path = output_path
        report.next_run_at = report.calculate_next_run()
        db.commit()

        logger.info(f"Report generation completed: {report_id}")

        # Cleanup
        db.close()

        return {
            "status": "completed",
            "report_id": report_id,
            "schedule_id": schedule_id,
            "output_path": output_path,
        }

    except Exception as e:
        logger.error(f"Failed to generate report {report_id}: {e}", exc_info=True)

        # Update schedule as failed
        try:
            if schedule:
                schedule.fail(error_message=str(e), error_details=repr(e))
                db.commit()

            # Update report statistics
            if report:
                report.update_stats(success=False)
                db.commit()

            db.close()
        except Exception as db_error:
            logger.error(f"Failed to update database after error: {db_error}")

        # Retry task if within retry limit
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying report generation (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

        return {
            "status": "failed",
            "report_id": report_id,
            "schedule_id": schedule_id,
            "error": str(e),
        }


@app.task(name="generate_report_pdf")
def generate_report_pdf(report_id: str, dashboard_id: str, output_path: str, config: dict = None):
    """
    Generate PDF report from dashboard data.

    This task will be implemented in subtask 6-2.

    Args:
        report_id: Report UUID
        dashboard_id: Dashboard UUID to export
        output_path: Where to save the PDF
        config: PDF generation configuration

    Returns:
        dict: Generation result with file path and size
    """
    logger.info(f"PDF generation placeholder for dashboard {dashboard_id}")

    # This will be implemented in subtask 6-2
    return {
        "status": "pending_implementation",
        "format": "pdf",
        "output_path": output_path,
    }


@app.task(name="deliver_report_email")
def deliver_report_email(report_id: str, schedule_id: str, output_path: str, recipients: list):
    """
    Deliver generated report via email.

    This task will be implemented in subtask 6-3.

    Args:
        report_id: Report UUID
        schedule_id: Schedule UUID
        output_path: Path to generated report file
        recipients: List of email addresses

    Returns:
        dict: Delivery status
    """
    logger.info(f"Email delivery placeholder for report {report_id} to {len(recipients)} recipients")

    # This will be implemented in subtask 6-3
    return {
        "status": "pending_implementation",
        "recipients_count": len(recipients),
        "delivered": False,
    }


@app.task(name="cleanup_old_reports")
def cleanup_old_reports():
    """
    Clean up old report files based on retention policy.

    Runs periodically to remove expired report files.

    Returns:
        dict: Cleanup statistics
    """
    from pybase.models.report import Report, ReportSchedule
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from datetime import datetime, timedelta
    import os

    logger.info("Starting cleanup of old report files")

    try:
        engine = create_engine(os.getenv("DATABASE_URL"))
        Session = sessionmaker(bind=engine)
        db = Session()

        # Get all reports with retention policies
        reports = db.query(Report).filter(Report.deleted_at.is_(None)).all()

        cleaned_count = 0
        total_size_freed = 0

        for report in reports:
            retention_days = report.retention_days or 30
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

            # Find old schedules
            old_schedules = (
                db.query(ReportSchedule)
                .filter(
                    ReportSchedule.report_id == report.id,
                    ReportSchedule.completed_at < cutoff_date,
                    ReportSchedule.output_path.isnot(None),
                )
                .all()
            )

            for schedule in old_schedules:
                if schedule.output_path and os.path.exists(schedule.output_path):
                    try:
                        file_size = os.path.getsize(schedule.output_path)
                        os.remove(schedule.output_path)
                        total_size_freed += file_size
                        cleaned_count += 1
                        logger.info(f"Deleted old report file: {schedule.output_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete file {schedule.output_path}: {e}")

        db.close()

        logger.info(f"Cleanup completed: {cleaned_count} files removed, {total_size_freed / (1024*1024):.2f} MB freed")

        return {
            "status": "completed",
            "files_cleaned": cleaned_count,
            "bytes_freed": total_size_freed,
        }

    except Exception as e:
        logger.error(f"Failed to cleanup old reports: {e}")
        return {
            "status": "failed",
            "error": str(e),
        }


@app.task(name="check_scheduled_reports")
def check_scheduled_reports():
    """
    Check for reports that are due to run and trigger generation.

    This task runs periodically to find reports that need to be generated.

    Returns:
        dict: Number of reports triggered
    """
    from pybase.models.report import Report
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from pybase.db.base import utc_now

    logger.info("Checking for scheduled reports")

    try:
        engine = create_engine(os.getenv("DATABASE_URL"))
        Session = sessionmaker(bind=engine)
        db = Session()

        # Find reports that are due
        now = utc_now()
        due_reports = (
            db.query(Report)
            .filter(
                Report.deleted_at.is_(None),
                Report.is_active == True,
                Report.is_paused == False,
                Report.next_run_at <= now,
            )
            .all()
        )

        triggered_count = 0

        for report in due_reports:
            logger.info(f"Triggering scheduled report: {report.name} (id={report.id})")

            # Create schedule record
            from uuid import uuid4
            from pybase.models.report import ReportSchedule

            schedule = ReportSchedule(
                id=str(uuid4()),
                report_id=report.id,
                scheduled_at=now,
            )
            db.add(schedule)
            db.commit()

            # Trigger async report generation
            generate_scheduled_report.delay(report.id, schedule.id)
            triggered_count += 1

        db.close()

        logger.info(f"Triggered {triggered_count} scheduled reports")

        return {
            "status": "completed",
            "reports_triggered": triggered_count,
        }

    except Exception as e:
        logger.error(f"Failed to check scheduled reports: {e}")
        return {
            "status": "failed",
            "error": str(e),
        }


# ==============================================================================
# Periodic Tasks Setup
# ==============================================================================

app.conf.beat_schedule = {
    # Check for scheduled reports every 5 minutes
    "check-scheduled-reports": {
        "task": "check_scheduled_reports",
        "schedule": 300.0,  # Every 5 minutes
    },
    # Clean up old reports daily at 2 AM
    "cleanup-old-reports": {
        "task": "cleanup_old_reports",
        "schedule": crontab(hour=2, minute=0),
    },
}

# ==============================================================================
# Main Entry Point
# ==============================================================================

if __name__ == "__main__":
    logger.info("Starting Celery worker for report generation")

    # Run initial setup
    try:
        app.autodiscover_tasks(["workers"])
        logger.info("Celery worker ready for report generation")
        logger.info("Available tasks:")
        logger.info("  - generate_scheduled_report: Main report generation task")
        logger.info("  - generate_report_pdf: PDF generation (pending implementation)")
        logger.info("  - deliver_report_email: Email delivery (pending implementation)")
        logger.info("  - cleanup_old_reports: Periodic cleanup task")
        logger.info("  - check_scheduled_reports: Periodic scheduler check")
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        sys.exit(1)
