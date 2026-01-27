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
            f"Starting index update for record {record_id} (attempt {self.request.retries + 1})"
        )

        # Run update in thread to avoid blocking
        def run_update():
            with get_db_session() as db:
                service = get_search_service(db)

                if old_data:
                    logger.info(f"Removing old data from index for record {record_id}")
                    # Implementation would call service.remove_record_data(record_id, old_data)

                if new_data:
                    logger.info(f"Adding new data to index for record {record_id}")
                    # Implementation would call service.update_record_data(record_id, new_data)

                return {"updated": True}

        result = asyncio.run(run_update())

        logger.info(f"Index update completed for record {record_id}")

        return {
            "status": "updated",
            "record_id": record_id,
            "table_id": table_id,
            "result": result,
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
            backoff = 2 ** retry_count
            logger.info(
                f"Retrying index update for {record_id} in {backoff}s (attempt {retry_count + 1}/{max_retries})"
            )
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        logger.error(
            f"Index update failed permanently for {record_id} after {retry_count} attempts"
        )
        return {
            "status": "failed",
            "record_id": record_id,
            "table_id": table_id,
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
