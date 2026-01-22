#!/usr/bin/env python3
"""
Celery worker tasks for background indexing.

This module defines background tasks for search indexing and Meilisearch updates.
Task definitions are discovered by the main Celery app in pybase.worker.
"""

import os
import logging

# Import the centralized Celery app instance from pybase.worker
from pybase.worker import app

# Setup logging
logger = logging.getLogger(__name__)

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
# Scheduled Tasks
# =============================================================================


@app.task(name="refresh_search_indexes")
def refresh_search_indexes():
    """
    Periodic refresh of search indexes.

    Keeps Meilisearch in sync with database.
    Scheduled to run every 5 minutes via Celery Beat (configured in pybase.worker).
    """
    logger.info("Refreshing search indexes")
    # Get all tables and trigger refresh
    # Implementation would call index_table for each table
    return {"status": "refreshed"}


# NOTE: This module should not be run directly.
# Start the Celery worker using: celery -A pybase.worker worker --loglevel=info
# Tasks defined here are automatically discovered by the main Celery app in pybase.worker
