#!/usr/bin/env python3
"""
Celery worker for background indexing tasks.

This worker processes search indexing operations and updates Meilisearch indexes.
"""

import sys
import os
from datetime import datetime, timezone
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

# Setup logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Create Celery app
app = Celery(
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
    include=["workers.celery_search_worker"],
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
    # Celery Beat schedule for periodic tasks
    beat_schedule={
        "refresh-search-indexes": {
            "task": "refresh_search_indexes",
            "schedule": 300.0,  # Run every 5 minutes
        },
    },
)

# ==============================================================================
# Background Tasks
# ==============================================================================


@app.task(bind=True, name="index_record")
def index_record(
    self,
    record_id: str,
    table_id: str,
    workspace_id: str,
    options: dict = None,
    job_id: str = None,
):
    """
    Index a single record for search.

    Updates Meilisearch index with record data.

    Args:
        self: Celery task instance (for retry support)
        record_id: Record ID to index
        table_id: Table ID containing the record
        workspace_id: Workspace ID containing the table
        options: Indexing options (max_retries, etc.)
        job_id: Optional job ID for database tracking

    Returns:
        Dictionary with indexing results
    """
    options = options or {}

    try:
        from pybase.services.search import get_search_service
        from pybase.db.session import get_db_session
        import asyncio

        logger.info(
            f"Starting index for record {record_id} from table {table_id} (attempt {self.request.retries + 1})"
        )

        # Run indexing in thread to avoid blocking
        def run_indexing():
            with get_db_session() as db:
                service = get_search_service(db)
                return service.index_record(record_id)

        result = asyncio.run(run_indexing())

        logger.info(f"Record indexing completed for {record_id}")

        return {
            "status": "indexed",
            "record_id": record_id,
            "table_id": table_id,
            "workspace_id": workspace_id,
            "result": result,
        }

    except ImportError as e:
        logger.error(f"Search indexing dependencies missing for record {record_id}: {e}")
        # Don't retry ImportError - it's a configuration issue
        error_msg = f"Search indexing not available. Install search dependencies: {e}"
        return {
            "status": "failed",
            "record_id": record_id,
            "table_id": table_id,
            "error": error_msg,
        }
    except Exception as e:
        retry_count = self.request.retries
        max_retries = options.get("max_retries", 3)

        logger.error(f"Record indexing failed for {record_id} (attempt {retry_count + 1}): {e}")

        if retry_count < max_retries:
            # Exponential backoff: 2^retry_count seconds (1, 2, 4, 8, ...)
            backoff = 2 ** retry_count
            logger.info(
                f"Retrying record indexing for {record_id} in {backoff}s (attempt {retry_count + 1}/{max_retries})"
            )
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(
            f"Record indexing failed permanently for {record_id} after {retry_count} attempts"
        )
        return {
            "status": "failed",
            "record_id": record_id,
            "table_id": table_id,
            "error": str(e),
        }


@app.task(bind=True, name="index_table")
def index_table(self, table_id: str, options: dict = None, job_id: str = None):
    """
    Index all records in a table.

    Full reindex of table data in Meilisearch.

    Args:
        self: Celery task instance (for retry support)
        table_id: Table ID to index
        options: Indexing options (max_retries, batch_size, etc.)
        job_id: Optional job ID for database tracking

    Returns:
        Dictionary with indexing results
    """
    options = options or {}

    try:
        from pybase.services.search import get_search_service
        from pybase.models.record import Record
        from pybase.db.session import get_db_session
        from sqlalchemy import select
        import asyncio

        logger.info(
            f"Starting table index for {table_id} (attempt {self.request.retries + 1})"
        )

        # Run indexing in thread to avoid blocking
        def run_indexing():
            with get_db_session() as db:
                service = get_search_service(db)

                # Fetch all records for table
                result = db.execute(
                    select(Record).where(
                        Record.table_id == table_id, Record.deleted_at.is_(None)
                    )
                )
                records = result.scalars().all()
                logger.info(f"Found {len(records)} records to index for table {table_id}")

                # Index each record
                indexed_count = 0
                for record in records:
                    try:
                        service.index_record(str(record.id))
                        indexed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to index record {record.id}: {e}")

                return {"indexed_count": indexed_count, "total_count": len(records)}

        result = asyncio.run(run_indexing())

        logger.info(f"Table indexing completed for {table_id}: {result['indexed_count']} records")

        return {
            "status": "indexed",
            "table_id": table_id,
            "indexed_count": result["indexed_count"],
            "total_count": result["total_count"],
        }

    except ImportError as e:
        logger.error(f"Search indexing dependencies missing for table {table_id}: {e}")
        error_msg = f"Search indexing not available. Install search dependencies: {e}"
        return {
            "status": "failed",
            "table_id": table_id,
            "error": error_msg,
        }
    except Exception as e:
        retry_count = self.request.retries
        max_retries = options.get("max_retries", 3)

        logger.error(f"Table indexing failed for {table_id} (attempt {retry_count + 1}): {e}")

        if retry_count < max_retries:
            backoff = 2 ** retry_count
            logger.info(
                f"Retrying table indexing for {table_id} in {backoff}s (attempt {retry_count + 1}/{max_retries})"
            )
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        logger.error(
            f"Table indexing failed permanently for {table_id} after {retry_count} attempts"
        )
        return {
            "status": "failed",
            "table_id": table_id,
            "error": str(e),
        }


@app.task(bind=True, name="update_index")
def update_index(
    self,
    table_id: str,
    record_id: str,
    old_data: dict = None,
    new_data: dict = None,
    options: dict = None,
    job_id: str = None,
):
    """
    Update search index when record is modified.

    Increments/decrements counts, updates specific fields.

    Args:
        self: Celery task instance (for retry support)
        table_id: Table ID containing the record
        record_id: Record ID to update
        old_data: Previous record data (for removal)
        new_data: New record data (for addition)
        options: Indexing options (max_retries, etc.)
        job_id: Optional job ID for database tracking

    Returns:
        Dictionary with update results
    """
    options = options or {}

    try:
        from pybase.services.search import get_search_service
        from pybase.db.session import get_db_session
        import asyncio

        logger.info(
            f"Starting index update for record {record_id} from table {table_id} (attempt {self.request.retries + 1})"
        )

        # Run update in thread to avoid blocking
        def run_update():
            with get_db_session() as db:
                service = get_search_service(db)

                result = {
                    "removed_old": False,
                    "added_new": False,
                    "old_fields": [],
                    "new_fields": [],
                }

                if old_data:
                    logger.info(f"Removing old data from index for record {record_id}")
                    try:
                        # Remove old field values from index
                        for field_name, field_value in old_data.items():
                            if field_value is not None:
                                service.remove_record_field(record_id, field_name, field_value)
                                result["old_fields"].append(field_name)
                        result["removed_old"] = True
                        logger.info(f"Removed {len(result['old_fields'])} old fields from index for record {record_id}")
                    except AttributeError:
                        # If remove_record_field doesn't exist, fall back to full reindex
                        logger.info(f"remove_record_field not available, reindexing record {record_id}")
                        service.index_record(record_id)
                        result["removed_old"] = True

                if new_data:
                    logger.info(f"Adding new data to index for record {record_id}")
                    try:
                        # Add new field values to index
                        for field_name, field_value in new_data.items():
                            if field_value is not None:
                                service.update_record_field(record_id, field_name, field_value)
                                result["new_fields"].append(field_name)
                        result["added_new"] = True
                        logger.info(f"Added {len(result['new_fields'])} new fields to index for record {record_id}")
                    except AttributeError:
                        # If update_record_field doesn't exist, fall back to full reindex
                        logger.info(f"update_record_field not available, reindexing record {record_id}")
                        service.index_record(record_id)
                        result["added_new"] = True

                return result

        result = asyncio.run(run_update())

        logger.info(f"Index update completed for record {record_id}: old={result['removed_old']}, new={result['added_new']}")

        return {
            "status": "updated",
            "record_id": record_id,
            "table_id": table_id,
            "removed_old": result["removed_old"],
            "added_new": result["added_new"],
            "old_fields_count": len(result.get("old_fields", [])),
            "new_fields_count": len(result.get("new_fields", [])),
        }

    except ImportError as e:
        logger.error(f"Search indexing dependencies missing for record {record_id}: {e}")
        error_msg = f"Search indexing not available. Install search dependencies: {e}"
        return {
            "status": "failed",
            "record_id": record_id,
            "table_id": table_id,
            "error": error_msg,
        }
    except Exception as e:
        retry_count = self.request.retries
        max_retries = options.get("max_retries", 3)

        logger.error(f"Index update failed for record {record_id} (attempt {retry_count + 1}): {e}")

        if retry_count < max_retries:
            # Exponential backoff: 2^retry_count seconds (1, 2, 4, 8, ...)
            backoff = 2 ** retry_count
            logger.info(
                f"Retrying index update for {record_id} in {backoff}s (attempt {retry_count + 1}/{max_retries})"
            )
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(
            f"Index update failed permanently for {record_id} after {retry_count} attempts"
        )
        return {
            "status": "failed",
            "record_id": record_id,
            "table_id": table_id,
            "error": str(e),
        }


@app.task(bind=True, name="refresh_search_indexes")
def refresh_search_indexes(self, options: dict = None, job_id: str = None):
    """
    Periodically refresh search indexes to ensure synchronization.

    This scheduled task checks for stale or missing index entries and updates
    them to keep the search index in sync with the database.

    Args:
        self: Celery task instance (for retry support)
        options: Indexing options (max_retries, batch_size, etc.)
        job_id: Optional job ID for database tracking

    Returns:
        Dictionary with refresh results
    """
    options = options or {}

    try:
        from pybase.services.search import get_search_service
        from pybase.models.table import Table
        from pybase.models.record import Record
        from pybase.db.session import get_db_session
        from sqlalchemy import select
        import asyncio

        logger.info(
            f"Starting search index refresh (attempt {self.request.retries + 1})"
        )

        # Run refresh in thread to avoid blocking
        def run_refresh():
            with get_db_session() as db:
                service = get_search_service(db)

                # Get all active tables
                result = db.execute(
                    select(Table).where(Table.deleted_at.is_(None))
                )
                tables = result.scalars().all()
                logger.info(f"Found {len(tables)} tables for index refresh")

                refresh_results = {
                    "tables_checked": len(tables),
                    "tables_refreshed": 0,
                    "records_indexed": 0,
                    "errors": [],
                }

                # Check each table for records needing refresh
                for table in tables:
                    try:
                        # Get records modified since last refresh or not indexed
                        records_result = db.execute(
                            select(Record).where(
                                Record.table_id == table.id,
                                Record.deleted_at.is_(None)
                            )
                        )
                        records = records_result.scalars().all()

                        # Check and refresh each record
                        table_indexed = 0
                        for record in records:
                            try:
                                # Check if record needs indexing (e.g., modified recently)
                                # or simply reindex to ensure consistency
                                service.index_record(str(record.id))
                                table_indexed += 1
                            except Exception as e:
                                logger.warning(
                                    f"Failed to refresh record {record.id} in table {table.id}: {e}"
                                )
                                refresh_results["errors"].append({
                                    "record_id": str(record.id),
                                    "table_id": str(table.id),
                                    "error": str(e),
                                })

                        if table_indexed > 0:
                            logger.info(
                                f"Refreshed {table_indexed} records for table {table.id}"
                            )
                            refresh_results["tables_refreshed"] += 1
                            refresh_results["records_indexed"] += table_indexed

                    except Exception as e:
                        logger.error(f"Failed to refresh table {table.id}: {e}")
                        refresh_results["errors"].append({
                            "table_id": str(table.id),
                            "error": str(e),
                        })

                return refresh_results

        result = asyncio.run(run_refresh())

        logger.info(
            f"Search index refresh completed: "
            f"{result['tables_refreshed']}/{result['tables_checked']} tables, "
            f"{result['records_indexed']} records indexed"
        )

        if result["errors"]:
            logger.warning(f"Refresh completed with {len(result['errors'])} errors")

        return {
            "status": "refreshed",
            "tables_checked": result["tables_checked"],
            "tables_refreshed": result["tables_refreshed"],
            "records_indexed": result["records_indexed"],
            "errors_count": len(result.get("errors", [])),
        }

    except ImportError as e:
        logger.error(f"Search indexing dependencies missing during refresh: {e}")
        error_msg = f"Search indexing not available. Install search dependencies: {e}"
        return {
            "status": "failed",
            "error": error_msg,
        }
    except Exception as e:
        retry_count = self.request.retries
        max_retries = options.get("max_retries", 3)

        logger.error(f"Search index refresh failed (attempt {retry_count + 1}): {e}")

        if retry_count < max_retries:
            # Exponential backoff: 2^retry_count seconds (1, 2, 4, 8, ...)
            backoff = 2 ** retry_count
            logger.info(
                f"Retrying search index refresh in {backoff}s (attempt {retry_count + 1}/{max_retries})"
            )
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(
            f"Search index refresh failed permanently after {retry_count} attempts"
        )
        return {
            "status": "failed",
            "error": str(e),
        }


# =============================================================================
# Worker Entry Point
# =============================================================================


if __name__ == "__main__":
    logger.info("Starting Celery worker with search background tasks")

    # Run initial setup
    try:
        app.autodiscover_tasks(["workers"])
        logger.info("Celery search worker ready")
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        sys.exit(1)
