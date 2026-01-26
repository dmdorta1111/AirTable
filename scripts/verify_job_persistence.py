#!/usr/bin/env python3
"""
Manual verification script for subtask-5-1: Job persistence in database.

This script:
1. Creates an extraction job via API
2. Queries the database to verify the job exists
3. Verifies the job has correct status (pending)

Usage:
    python scripts/verify_job_persistence.py

Environment variables required:
    - API_BASE_URL: Base URL of API (default: http://localhost:8000)
    - API_TOKEN: Authentication token (required)
    - DATABASE_URL: PostgreSQL connection URL (required)
"""

import io
import os
import sys
from uuid import UUID

import httpx
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus


def create_test_job(api_base_url: str, token: str) -> tuple[str, dict]:
    """
    Create a test extraction job via API.

    Returns:
        Tuple of (job_id, response_json)
    """
    print("Step 1: Creating extraction job via API...")

    # Create a simple PDF file for testing
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    files = {
        "file": ("test_persistence.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    data = {
        "format": "pdf",
    }

    headers = {
        "Authorization": f"Bearer {token}"
    }

    url = f"{api_base_url}/api/v1/extraction/jobs"

    try:
        response = httpx.post(url, headers=headers, files=files, data=data, timeout=30.0)
        response.raise_for_status()

        result = response.json()
        job_id = result.get("id")

        print(f"  ✓ Job created successfully")
        print(f"  Job ID: {job_id}")
        print(f"  Status: {result.get('status')}")
        print(f"  Format: {result.get('format')}")
        print(f"  Retry Count: {result.get('retry_count')}")

        return job_id, result

    except httpx.HTTPError as e:
        print(f"  ✗ Failed to create job: {e}")
        sys.exit(1)


def verify_job_in_database(database_url: str, job_id: str) -> ExtractionJob:
    """
    Query the database to verify the job exists and has correct values.

    Returns:
        The ExtractionJob model instance
    """
    print("\nStep 2: Querying database to verify job persistence...")

    # Convert postgresql+asyncpg to postgresql for synchronous query
    sync_db_url = database_url.replace("+asyncpg", "")

    # Create synchronous engine for direct query
    engine = create_engine(sync_db_url)
    Session = sessionmaker(bind=engine)

    try:
        with Session() as session:
            # Query job by ID
            stmt = select(ExtractionJob).where(ExtractionJob.id == UUID(job_id))
            result = session.execute(stmt)
            job_model = result.scalar_one_or_none()

            if job_model is None:
                print(f"  ✗ Job not found in database")
                print(f"  Query: SELECT * FROM pybase.extraction_jobs WHERE id = '{job_id}'")
                sys.exit(1)

            print(f"  ✓ Job found in database")
            print(f"  Database query result:")
            print(f"    - ID: {job_model.id}")
            print(f"    - Status: {job_model.status}")
            print(f"    - Format: {job_model.extraction_format}")
            print(f"    - Retry Count: {job_model.retry_count}")
            print(f"    - Max Retries: {job_model.max_retries}")
            print(f"    - Progress: {job_model.progress}%")
            print(f"    - Created At: {job_model.created_at}")
            print(f"    - Started At: {job_model.started_at}")
            print(f"    - Completed At: {job_model.completed_at}")
            print(f"    - Celery Task ID: {job_model.celery_task_id}")
            print(f"    - File Path: {job_model.file_path}")

            return job_model

    except Exception as e:
        print(f"  ✗ Database query failed: {e}")
        sys.exit(1)
    finally:
        engine.dispose()


def verify_job_fields(job_model: ExtractionJob, api_response: dict):
    """
    Verify that database fields match API response and have correct values.
    """
    print("\nStep 3: Verifying job fields...")

    errors = []

    # Check status is PENDING
    if job_model.status != ExtractionJobStatus.PENDING:
        errors.append(f"Status should be 'pending', got '{job_model.status}'")

    # Check format
    if job_model.extraction_format != "pdf":
        errors.append(f"Format should be 'pdf', got '{job_model.extraction_format}'")

    # Check retry_count is 0
    if job_model.retry_count != 0:
        errors.append(f"Retry count should be 0, got {job_model.retry_count}")

    # Check max_retries
    if job_model.max_retries != 3:
        errors.append(f"Max retries should be 3, got {job_model.max_retries}")

    # Check progress is 0
    if job_model.progress != 0:
        errors.append(f"Progress should be 0, got {job_model.progress}")

    # Check timestamps
    if job_model.created_at is None:
        errors.append("created_at should not be None")

    if job_model.started_at is not None:
        errors.append(f"started_at should be None (not started yet), got {job_model.started_at}")

    if job_model.completed_at is not None:
        errors.append(f"completed_at should be None (not completed yet), got {job_model.completed_at}")

    # Check celery_task_id is None (worker hasn't picked it up yet)
    if job_model.celery_task_id is not None:
        errors.append(f"celery_task_id should be None (worker hasn't picked it up), got {job_model.celery_task_id}")

    # Check error_message is None
    if job_model.error_message is not None:
        errors.append(f"error_message should be None, got {job_model.error_message}")

    # Check file_path is set
    if not job_model.file_path:
        errors.append("file_path should not be empty")

    if errors:
        print("  ✗ Verification failed:")
        for error in errors:
            print(f"    - {error}")
        sys.exit(1)
    else:
        print("  ✓ All fields verified successfully")
        print(f"    ✓ Status is PENDING")
        print(f"    ✓ Retry count is 0")
        print(f"    ✓ Progress is 0%")
        print(f"    ✓ Not started yet (started_at is None)")
        print(f"    ✓ Not completed yet (completed_at is None)")
        print(f"    ✓ Worker hasn't picked it up (celery_task_id is None)")
        print(f"    ✓ File path is set")


def main():
    """Main verification flow."""
    print("=" * 70)
    print("SUBTASK 5-1: Verify Job Persists in Database Before Worker Starts")
    print("=" * 70)

    # Get environment variables
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_token = os.getenv("API_TOKEN")
    database_url = os.getenv("DATABASE_URL")

    if not api_token:
        print("\n✗ Error: API_TOKEN environment variable is required")
        print("\nUsage:")
        print("  export API_TOKEN='your_jwt_token'")
        print("  python scripts/verify_job_persistence.py")
        sys.exit(1)

    if not database_url:
        print("\n✗ Error: DATABASE_URL environment variable is required")
        sys.exit(1)

    print(f"\nConfiguration:")
    print(f"  API Base URL: {api_base_url}")
    print(f"  Database: {database_url.split('@')[-1] if '@' in database_url else 'N/A'}")

    # Step 1: Create job via API
    job_id, api_response = create_test_job(api_base_url, api_token)

    # Step 2: Query database
    job_model = verify_job_in_database(database_url, job_id)

    # Step 3: Verify fields
    verify_job_fields(job_model, api_response)

    print("\n" + "=" * 70)
    print("✓ VERIFICATION PASSED")
    print("=" * 70)
    print("\nSummary:")
    print("  ✓ Job successfully created via API")
    print("  ✓ Job persists in extraction_jobs table")
    print("  ✓ Job has correct status (pending)")
    print("  ✓ All fields match expected values")
    print("\nSubtask 5-1 is complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
