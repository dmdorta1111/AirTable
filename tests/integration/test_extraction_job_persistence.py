"""
Integration tests for extraction job persistence.

Tests verify that extraction jobs are correctly persisted to the database
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
async def test_job_persists_to_database_before_worker_starts(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """
    Test that extraction job persists to database before worker starts.

    This test verifies:
    1. Job is created via API endpoint
    2. Job record exists in database
    3. Job has correct status (pending)
    4. Job has correct format and user_id
    """
    # Create a simple PDF file for testing
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    # Create file-like object
    files = {
        "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    # Form data
    data = {
        "format": "pdf",
    }

    # Submit job creation request
    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/jobs",
        headers=auth_headers,
        files=files,
        data=data,
    )

    # Verify API response
    assert response.status_code == 202
    result = response.json()

    # Verify response structure
    assert "id" in result
    assert "status" in result
    assert result["status"] == "pending"
    assert "format" in result
    assert result["format"] == "pdf"
    assert "retry_count" in result
    assert result["retry_count"] == 0
    assert "created_at" in result

    job_id = result["id"]

    # Query database directly to verify job persistence
    # This simulates the manual verification step:
    # SELECT * FROM pybase.extraction_jobs WHERE id = ...
    stmt = select(ExtractionJob).where(ExtractionJob.id == job_id)
    job_result = await db_session.execute(stmt)
    job_model = job_result.scalar_one_or_none()

    # Verify job exists in database
    assert job_model is not None, "Job not found in database"

    # Verify job fields
    assert job_model.id == job_id
    assert job_model.status == ExtractionJobStatus.PENDING
    assert job_model.extraction_format == "pdf"
    assert job_model.retry_count == 0
    assert job_model.max_retries == 3
    assert job_model.progress == 0
    assert job_model.created_at is not None
    assert job_model.started_at is None  # Not started yet
    assert job_model.completed_at is None  # Not completed yet
    assert job_model.celery_task_id is None  # Worker hasn't picked it up yet
    assert job_model.error_message is None

    # Verify file_path is set
    assert job_model.file_path is not None
    assert job_model.file_path.endswith(".pdf") or job_model.file_path.endswith(".tmp")

    # Verify options is a valid JSON/dict
    options = job_model.get_options()
    assert isinstance(options, dict)


@pytest.mark.asyncio
async def test_job_persistence_with_dxf_format(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """Test job persistence with DXF format."""
    # Create a simple DXF file for testing
    dxf_content = b"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n"

    files = {
        "file": ("test.dxf", io.BytesIO(dxf_content), "application/dxf")
    }

    data = {
        "format": "dxf",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/jobs",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 202
    result = response.json()
    job_id = result["id"]

    # Query database
    stmt = select(ExtractionJob).where(ExtractionJob.id == job_id)
    job_result = await db_session.execute(stmt)
    job_model = job_result.scalar_one_or_none()

    assert job_model is not None
    assert job_model.status == ExtractionJobStatus.PENDING
    assert job_model.extraction_format == "dxf"


@pytest.mark.asyncio
async def test_job_persistence_with_ifc_format(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """Test job persistence with IFC format."""
    # Create a simple IFC file for testing
    ifc_content = b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"

    files = {
        "file": ("test.ifc", io.BytesIO(ifc_content), "application/ifc")
    }

    data = {
        "format": "ifc",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/jobs",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 202
    result = response.json()
    job_id = result["id"]

    # Query database
    stmt = select(ExtractionJob).where(ExtractionJob.id == job_id)
    job_result = await db_session.execute(stmt)
    job_model = job_result.scalar_one_or_none()

    assert job_model is not None
    assert job_model.status == ExtractionJobStatus.PENDING
    assert job_model.extraction_format == "ifc"


@pytest.mark.asyncio
async def test_job_persistence_with_step_format(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """Test job persistence with STEP format."""
    # Create a simple STEP file for testing
    step_content = b"ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"

    files = {
        "file": ("test.step", io.BytesIO(step_content), "application/step")
    }

    data = {
        "format": "step",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/jobs",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 202
    result = response.json()
    job_id = result["id"]

    # Query database
    stmt = select(ExtractionJob).where(ExtractionJob.id == job_id)
    job_result = await db_session.execute(stmt)
    job_model = job_result.scalar_one_or_none()

    assert job_model is not None
    assert job_model.status == ExtractionJobStatus.PENDING
    assert job_model.extraction_format == "step"
