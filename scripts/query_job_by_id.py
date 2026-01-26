#!/usr/bin/env python3
"""
Quick database query script to verify a job exists in the database.

Usage:
    python scripts/query_job_by_id.py <job_id>

This simulates the manual verification step:
    SELECT * FROM pybase.extraction_jobs WHERE id = <job_id>
"""

import os
import sys
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pybase.models.extraction_job import ExtractionJob


def query_job(job_id: str):
    """Query job from database and display results."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("Error: DATABASE_URL environment variable is required")
        sys.exit(1)

    # Convert postgresql+asyncpg to postgresql for synchronous query
    sync_db_url = database_url.replace("+asyncpg", "")

    print(f"Connecting to database...")
    print(f"Query: SELECT * FROM pybase.extraction_jobs WHERE id = '{job_id}'")
    print()

    # Create synchronous engine
    engine = create_engine(sync_db_url)
    Session = sessionmaker(bind=engine)

    try:
        with Session() as session:
            # Query job by ID
            stmt = select(ExtractionJob).where(ExtractionJob.id == UUID(job_id))
            result = session.execute(stmt)
            job = result.scalar_one_or_none()

            if job is None:
                print(f"No job found with ID: {job_id}")
                return

            # Display job details
            print("=" * 70)
            print("EXTRACTION JOB FOUND")
            print("=" * 70)
            print(f"ID:              {job.id}")
            print(f"Status:          {job.status}")
            print(f"Format:          {job.extraction_format}")
            print(f"User ID:         {job.user_id}")
            print(f"File Path:       {job.file_path}")
            print(f"Progress:        {job.progress}%")
            print(f"Retry Count:     {job.retry_count} / {job.max_retries}")
            print(f"Created At:      {job.created_at}")
            print(f"Started At:      {job.started_at}")
            print(f"Completed At:    {job.completed_at}")
            print(f"Duration (ms):   {job.duration_ms}")
            print(f"Celery Task ID:  {job.celery_task_id}")
            print(f"Error Message:   {job.error_message}")
            print(f"Options:         {job.get_options()}")
            print(f"Results:         {job.get_results()}")
            print("=" * 70)

    except Exception as e:
        print(f"Error querying database: {e}")
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/query_job_by_id.py <job_id>")
        sys.exit(1)

    job_id = sys.argv[1]
    query_job(job_id)
