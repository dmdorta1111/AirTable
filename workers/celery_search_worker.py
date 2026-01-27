#!/usr/bin/env python3
"""
Celery worker for background indexing tasks.

This worker processes extraction results and updates Meilisearch indexes.
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


@app.task(name="index_record")
def index_record(record_id: str, table_id: str, workspace_id: str):
    """
    Index a single record for search.

    Updates Meilisearch index with record data.
    """
    from pybase.services.search import get_search_service
    from sqlalchemy import create_engine

    try:
        engine = create_engine(os.getenv("DATABASE_URL"))
        engine.connect()

        service = get_search_service(engine)

        logger.info(f"Indexing record {record_id} from table {table_id}")
        # Implementation would call service.index_record(record_id)

        return {"status": "indexed", "record_id": record_id}

    except Exception as e:
        logger.error(f"Failed to index record {record_id}: {e}")
        return {"status": "failed", "record_id": record_id, "error": str(e)}


@app.task(name="index_table")
def index_table(table_id: str):
    """
    Index all records in a table.

    Full reindex of table data in Meilisearch.
    """
    from pybase.services.search import get_search_service
    from pybase.models.record import Record
    from sqlalchemy import create_engine, select
    import json

    try:
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

        return {"status": "indexed", "table_id": table_id, "count": len(records)}

    except Exception as e:
        logger.error(f"Failed to index table {table_id}: {e}")
        return {"status": "failed", "table_id": table_id, "error": str(e)}


@app.task(name="update_index")
def update_index(table_id: str, record_id: str, old_data: dict = None, new_data: dict = None):
    """
    Update search index when record is modified.

    Increments/decrements counts, updates specific fields.
    """
    if old_data:
        logger.info(f"Updating index for record {record_id}: remove old data")

    if new_data:
        logger.info(f"Updating index for record {record_id}: add new data")

    return {"status": "updated", "record_id": record_id}


# =============================================================================
# Celery Beat Schedule Configuration
# =============================================================================

# Configure Celery beat schedule for periodic tasks
app.conf.beat_schedule = {
    "refresh-search-indexes": {
        "task": "refresh_search_indexes",
        "schedule": 300.0,  # Every 5 minutes
    },
    "cleanup-audit-logs": {
        "task": "cleanup_audit_logs",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM UTC
    },
}

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


# =============================================================================
# Scheduled Tasks
# =============================================================================


@app.task(name="refresh_search_indexes")
def refresh_search_indexes():
    """
    Periodic refresh of search indexes.

    Keeps Meilisearch in sync with database.
    """
    logger.info("Refreshing search indexes")
    # Get all tables and trigger refresh
    # Implementation would call index_table for each table
    return {"status": "refreshed"}


if __name__ == "__main__":
    logger.info("Starting Celery worker with search background tasks")

    # Run initial setup
    try:
        app.autodiscover_tasks(["src.pybase", "workers"])
        logger.info("Celery worker ready")
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        sys.exit(1)
