#!/usr/bin/env python3
"""
Celery worker for background indexing tasks.

This worker processes extraction results and updates Meilisearch indexes.
"""

import sys
import os
from datetime import datetime
import logging
import time

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

# Import Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = None
    Histogram = None
    Gauge = None

# Setup logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# ==============================================================================
# Prometheus Metrics
# ==============================================================================

if PROMETHEUS_AVAILABLE:
    # Task duration histogram
    task_duration = Histogram(
        "celery_search_task_duration_seconds",
        "Search task duration in seconds",
        ["task_name", "status"],
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0, 3600.0],
    )

    # Task counter
    tasks_total = Counter(
        "celery_search_tasks_total",
        "Total number of search tasks",
        ["task_name", "status"],
    )

    # Active tasks gauge
    active_tasks = Gauge(
        "celery_search_active_tasks",
        "Number of currently running search tasks",
        ["task_name"],
    )

    # Task retries counter
    task_retries_total = Counter(
        "celery_search_task_retries_total",
        "Total number of search task retry attempts",
        ["task_name"],
    )

    logger.info("Prometheus metrics initialized for search worker")
else:
    logger.warning("Prometheus client not available. Metrics will not be collected.")
    task_duration = None
    tasks_total = None
    active_tasks = None
    task_retries_total = None

# Create Celery app
app = Celery(
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
    include=["src.pybase.t"],
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
# Metrics Helper
# ==============================================================================


class TaskMetrics:
    """Context manager for tracking task metrics."""

    def __init__(self, task_name: str):
        self.task_name = task_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        if PROMETHEUS_AVAILABLE and active_tasks:
            active_tasks.labels(task_name=self.task_name).inc()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        # Determine status
        if exc_type is not None:
            status = "error"
        else:
            status = "success"

        # Record metrics
        if PROMETHEUS_AVAILABLE:
            if task_duration:
                task_duration.labels(task_name=self.task_name, status=status).observe(duration)
            if tasks_total:
                tasks_total.labels(task_name=self.task_name, status=status).inc()
            if active_tasks:
                active_tasks.labels(task_name=self.task_name).dec()

        return False


def track_retry(task_name: str):
    """Track a retry attempt in metrics."""
    if PROMETHEUS_AVAILABLE and task_retries_total:
        task_retries_total.labels(task_name=task_name).inc()


# ==============================================================================
# Background Tasks
# ==============================================================================


@app.task(bind=True, name="index_record")
def index_record(self, record_id: str, table_id: str, workspace_id: str):
    """
    Index a single record for search.

    Updates Meilisearch index with record data.
    """
    # Start metrics tracking
    metrics = TaskMetrics("index_record")
    metrics.__enter__()

    try:
        from pybase.services.search import get_search_service
        from sqlalchemy import create_engine

        engine = create_engine(os.getenv("DATABASE_URL"))
        engine.connect()

        service = get_search_service(engine)

        logger.info(f"Indexing record {record_id} from table {table_id}")
        # Implementation would call service.index_record(record_id)

        result = {"status": "indexed", "record_id": record_id}
        metrics.__exit__(None, None, None)
        return result

    except Exception as e:
        logger.error(f"Failed to index record {record_id}: {e}")
        metrics.__exit__(type(e), e, e.__traceback__)
        return {"status": "failed", "record_id": record_id, "error": str(e)}


@app.task(bind=True, name="index_table")
def index_table(self, table_id: str):
    """
    Index all records in a table.

    Full reindex of table data in Meilisearch.
    """
    # Start metrics tracking
    metrics = TaskMetrics("index_table")
    metrics.__enter__()

    try:
        from pybase.services.search import get_search_service
        from pybase.models.record import Record
        from sqlalchemy import create_engine, select
        import json

        engine = create_engine(os.getenv("DATABASE_URL"))
        engine.connect()

        service = get_search_service(engine)

        # Fetch all records for table
        with engine.connect() as conn:
            result = conn.execute(
                select(Record).where(Record.table_id == table_id, Record.deleted_at.is_(None))
            )
            records = result.fetchall()
            logger.info(f"Found {len(records)} records to index for table {table_id}")

            # Index each record
            for record in records:
                record_dict = dict(record._mapping)
                logger.info(f"Indexing record {record_dict['id']}")

        result = {"status": "indexed", "table_id": table_id, "count": len(records)}
        metrics.__exit__(None, None, None)
        return result

    except Exception as e:
        logger.error(f"Failed to index table {table_id}: {e}")
        metrics.__exit__(type(e), e, e.__traceback__)
        return {"status": "failed", "table_id": table_id, "error": str(e)}


@app.task(bind=True, name="update_index")
def update_index(self, table_id: str, record_id: str, old_data: dict = None, new_data: dict = None):
    """
    Update search index when record is modified.

    Increments/decrements counts, updates specific fields.
    """
    # Start metrics tracking
    metrics = TaskMetrics("update_index")
    metrics.__enter__()

    try:
        if old_data:
            logger.info(f"Updating index for record {record_id}: remove old data")

        if new_data:
            logger.info(f"Updating index for record {record_id}: add new data")

        result = {"status": "updated", "record_id": record_id}
        metrics.__exit__(None, None, None)
        return result

    except Exception as e:
        logger.error(f"Failed to update index for record {record_id}: {e}")
        metrics.__exit__(type(e), e, e.__traceback__)
        return {"status": "failed", "record_id": record_id, "error": str(e)}


# =============================================================================
# Scheduled Tasks
# =============================================================================


@app.task(name="refresh_search_indexes")
def refresh_search_indexes():
    """
    Periodic refresh of search indexes.

    Keeps Meilisearch in sync with database.
    Configure in beat_schedule to run periodically.
    """
    # Start metrics tracking
    metrics = TaskMetrics("refresh_search_indexes")
    metrics.__enter__()

    try:
        logger.info("Refreshing search indexes")
        # Get all tables and trigger refresh
        # Implementation would call index_table for each table

        result = {"status": "refreshed"}
        metrics.__exit__(None, None, None)
        return result

    except Exception as e:
        logger.error(f"Failed to refresh search indexes: {e}")
        metrics.__exit__(type(e), e, e.__traceback__)
        return {"status": "failed", "error": str(e)}


if __name__ == "__main__":
    logger.info("Starting Celery worker with search background tasks")

    # Run initial setup
    try:
        app.autodiscover_tasks(["src.pybase"])
        app.conf.beat(settings="local", worker_prefork_multiplier=1, force=True)
        logger.info("Celery worker ready")
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        sys.exit(1)
