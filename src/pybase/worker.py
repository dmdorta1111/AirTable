"""
PyBase Celery Worker Application.

This module creates and configures the Celery application instance for
background task processing, including search indexing and CAD/PDF extraction.
"""

import logging
import os

from celery import Celery

from pybase.core.config import settings
from pybase.core.logging import setup_logging

# Setup logging
setup_logging(
    log_level=settings.log_level,
    json_logs=settings.environment == "production",
)

logger = logging.getLogger(__name__)

# Create Celery app with configuration from settings
app = Celery(
    "pybase",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    # Task modules to include (explicit include for task discovery)
    include=[
        "workers.celery_search_worker",  # Search indexing tasks
        "pybase.services.search",  # Search service tasks (if any)
        "pybase.extraction.cad",  # CAD extraction tasks (if any)
        "pybase.extraction.pdf",  # PDF extraction tasks (if any)
    ],
    # Celery Beat schedule configuration (replaces deprecated @periodic_task)
    beat_schedule={
        "refresh-search-indexes": {
            "task": "refresh_search_indexes",
            "schedule": 300.0,  # Every 5 minutes (in seconds)
            "options": {
                "expires": 180,  # Task expires after 3 minutes if not picked up
            },
        },
    },
)

# Autodiscover tasks from pybase modules
# Tasks will be discovered from these modules automatically
app.autodiscover_tasks(
    [
        "pybase.services",
        "pybase.extraction",
    ],
    force=True,
)

logger.info(
    f"Celery worker initialized for {settings.app_name} "
    f"(Environment: {settings.environment})"
)

# Explicitly import task modules to ensure they're registered
# This is needed because the 'include' parameter only takes effect when worker starts
# By importing here, tasks are available even when just importing the app
import workers.celery_search_worker  # noqa: F401
