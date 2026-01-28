"""
Integration tests for bulk job persistence.

Tests verify that bulk extraction jobs are correctly persisted to the database
and can be queried before the worker starts processing them.
"""

import io

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.config import settings
from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus


@pytest.mark.asyncio
async def test_bulk_job_persists_to_database_before_worker_starts(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """
    Test that bulk job persists to database before worker starts.

    This test verifies:
    1. Bulk job is created via API endpoint
    2. Bulk job record exists in database
    3. Job has correct status (pending)
    4. Job has correct options with file_paths
    """
    # Create multiple PDF files for testing
    pdf_content_1 = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"
    pdf_content_2 = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"
    pdf_content_3 = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    # Create file-like objects
    files = [
        ("files", ("test1.pdf", io.BytesIO(pdf_content_1), "application/pdf")),
        ("files", ("test2.pdf", io.BytesIO(pdf_content_2), "application/pdf")),
        ("files", ("test3.pdf", io.BytesIO(pdf_content_3), "application/pdf")),
    ]

    # Form data
    data = {
        "auto_detect_format": "true",
        "continue_on_error": "true",
    }

    # Submit bulk job creation request
    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data=data,
    )

    # Verify API response
    assert response.status_code == 202
    result = response.json()

    # Verify response structure
    assert "bulk_job_id" in result
    assert "total_files" in result
    assert result["total_files"] == 3
    assert "overall_status" in result
    assert result["overall_status"] == "pending"
    assert "progress" in result
    assert result["progress"] == 0
    assert "files_completed" in result
    assert result["files_completed"] == 0
    assert "files_failed" in result
    assert result["files_failed"] == 0
    assert "files_pending" in result
    assert result["files_pending"] == 3
    assert "created_at" in result

    bulk_job_id = result["bulk_job_id"]

    # Query database directly to verify bulk job persistence
    # This simulates the manual verification step:
    # SELECT * FROM pybase.extraction_jobs WHERE id = ...
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    job_model = job_result.scalar_one_or_none()

    # Verify bulk job exists in database
    assert job_model is not None, "Bulk job not found in database"

    # Verify job fields
    assert job_model.id == bulk_job_id
    assert job_model.status == ExtractionJobStatus.PENDING
    assert job_model.retry_count == 0
    assert job_model.max_retries == 3
    assert job_model.progress == 0
    assert job_model.created_at is not None
    assert job_model.started_at is None  # Not started yet
    assert job_model.completed_at is None  # Not completed yet
    assert job_model.celery_task_id is None  # Worker hasn't picked it up yet
    assert job_model.error_message is None

    # Verify options contain bulk job metadata
    options = job_model.get_options()
    assert isinstance(options, dict)
    assert "file_paths" in options
    assert isinstance(options["file_paths"], list)
    assert len(options["file_paths"]) == 3
    assert "auto_detect_format" in options
    assert options["auto_detect_format"] is True
    assert "continue_on_error" in options
    assert options["continue_on_error"] is True


@pytest.mark.asyncio
async def test_bulk_job_persistence_with_format_override(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """Test bulk job persistence with format override."""
    # Create PDF files for testing
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"

    files = [
        ("files", ("test1.pdf", io.BytesIO(pdf_content), "application/pdf")),
        ("files", ("test2.pdf", io.BytesIO(pdf_content), "application/pdf")),
    ]

    data = {
        "format_override": "pdf",
        "auto_detect_format": "false",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 202
    result = response.json()
    bulk_job_id = result["bulk_job_id"]

    # Query database
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    job_model = job_result.scalar_one_or_none()

    assert job_model is not None
    assert job_model.status == ExtractionJobStatus.PENDING

    # Verify format override in options
    options = job_model.get_options()
    assert "format_override" in options
    assert options["format_override"] == "pdf"
    assert "auto_detect_format" in options
    assert options["auto_detect_format"] is False


@pytest.mark.asyncio
async def test_bulk_job_persistence_with_target_table(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """Test bulk job persistence with target table ID."""
    from uuid import uuid4

    # Create PDF files
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"

    files = [
        ("files", ("test1.pdf", io.BytesIO(pdf_content), "application/pdf")),
    ]

    target_table_id = str(uuid4())

    data = {
        "auto_detect_format": "true",
        "target_table_id": target_table_id,
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 202
    result = response.json()
    bulk_job_id = result["bulk_job_id"]

    # Verify response includes target_table_id
    assert result["target_table_id"] == target_table_id

    # Query database
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    job_model = job_result.scalar_one_or_none()

    assert job_model is not None

    # Verify target_table_id in options
    options = job_model.get_options()
    assert "target_table_id" in options
    assert options["target_table_id"] == target_table_id


@pytest.mark.asyncio
async def test_bulk_job_can_be_retrieved_via_api(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """Test that persisted bulk job can be retrieved via GET endpoint."""
    # Create bulk job
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"

    files = [
        ("files", ("test1.pdf", io.BytesIO(pdf_content), "application/pdf")),
        ("files", ("test2.pdf", io.BytesIO(pdf_content), "application/pdf")),
    ]

    create_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={"auto_detect_format": "true"},
    )

    assert create_response.status_code == 202
    create_data = create_response.json()
    bulk_job_id = create_data["bulk_job_id"]

    # Retrieve bulk job status via API
    status_response = await client.get(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}",
        headers=auth_headers,
    )

    assert status_response.status_code == 200
    status_data = status_response.json()

    # Verify retrieved data matches created data
    assert status_data["bulk_job_id"] == bulk_job_id
    assert status_data["total_files"] == 2
    assert status_data["overall_status"] == "pending"
    assert status_data["files_completed"] == 0
    assert status_data["files_pending"] == 2
    assert "created_at" in status_data

    # Verify bulk job still exists in database
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    job_model = job_result.scalar_one_or_none()

    assert job_model is not None
    assert job_model.status == ExtractionJobStatus.PENDING


@pytest.mark.asyncio
async def test_bulk_job_persistence_single_file(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """Test bulk job persistence with single file (edge case)."""
    # Create single PDF file
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"

    files = [
        ("files", ("single.pdf", io.BytesIO(pdf_content), "application/pdf")),
    ]

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={"auto_detect_format": "true"},
    )

    assert response.status_code == 202
    result = response.json()
    bulk_job_id = result["bulk_job_id"]

    # Verify single file is handled correctly
    assert result["total_files"] == 1
    assert result["files_pending"] == 1

    # Query database
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    job_model = job_result.scalar_one_or_none()

    assert job_model is not None
    options = job_model.get_options()
    assert len(options["file_paths"]) == 1


@pytest.mark.asyncio
async def test_bulk_job_persistence_large_file_count(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """Test bulk job persistence with larger file count."""
    # Create 10 PDF files
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"

    files = [
        ("files", (f"test{i}.pdf", io.BytesIO(pdf_content), "application/pdf"))
        for i in range(10)
    ]

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={"auto_detect_format": "true", "continue_on_error": "true"},
    )

    assert response.status_code == 202
    result = response.json()
    bulk_job_id = result["bulk_job_id"]

    # Verify all files are accounted for
    assert result["total_files"] == 10
    assert result["files_pending"] == 10

    # Query database
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    job_model = job_result.scalar_one_or_none()

    assert job_model is not None
    options = job_model.get_options()
    assert len(options["file_paths"]) == 10
    assert options["continue_on_error"] is True
