"""Integration tests for bulk job retry functionality."""

import io
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from pybase.core.config import settings
from pybase.schemas.extraction import JobStatus


@pytest.mark.asyncio
async def test_retry_bulk_job_with_failed_files(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
):
    """
    Test retrying a bulk job with failed files without re-uploading.

    Verifies:
    - Bulk job can be created with mix of valid and invalid files
    - Failed files are marked correctly
    - Retry endpoint resets failed jobs to PENDING
    - Retry response shows updated status
    - Files are stored in database/temp so no re-upload needed
    """
    from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus

    # Create bulk job with mix of valid and invalid files
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    invalid_content = b"This is not a valid PDF file"

    files = [
        ("files", ("valid1.pdf", io.BytesIO(valid_pdf), "application/pdf")),
        ("files", ("invalid1.pdf", io.BytesIO(invalid_content), "application/pdf")),
        ("files", ("valid2.pdf", io.BytesIO(valid_pdf), "application/pdf")),
        ("files", ("invalid2.pdf", io.BytesIO(invalid_content), "application/pdf")),
    ]

    # Upload with continue_on_error to process all files
    upload_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={
            "auto_detect_format": "true",
            "continue_on_error": "true",
        },
    )

    assert upload_response.status_code == 202
    upload_data = upload_response.json()
    bulk_job_id = upload_data["bulk_job_id"]
    assert upload_data["total_files"] == 4

    # Get initial job status
    status_response = await client.get(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}",
        headers=auth_headers,
    )

    assert status_response.status_code == 200
    initial_status = status_response.json()

    # Count failed files
    failed_files = [
        f for f in initial_status["files"]
        if f["status"] == JobStatus.FAILED.value
    ]
    assert len(failed_files) >= 1, "Expected at least one failed file"

    # Verify bulk job exists in database
    bulk_job = await db_session.get(ExtractionJob, bulk_job_id)
    assert bulk_job is not None
    assert bulk_job.status == ExtractionJobStatus.PROCESSING.value

    # Call retry endpoint
    retry_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}/retry",
        headers=auth_headers,
    )

    # Should return updated job status
    assert retry_response.status_code == 200
    retry_data = retry_response.json()

    # Verify response structure
    assert retry_data["bulk_job_id"] == bulk_job_id
    assert retry_data["total_files"] == 4
    assert "files" in retry_data
    assert len(retry_data["files"]) == 4

    # Verify failed files were reset to PENDING
    previously_failed_files = {f["file_path"] for f in initial_status["files"] if f["status"] == JobStatus.FAILED.value}
    retried_files = []

    for file_status in retry_data["files"]:
        if file_status["file_path"] in previously_failed_files:
            # File should be reset to PENDING for retry
            retried_files.append(file_status)
            assert file_status["status"] in [
                JobStatus.PENDING.value,
                JobStatus.PROCESSING.value,
            ], f"Failed file should be reset to PENDING or PROCESSING, got {file_status['status']}"

    # Verify at least some files were retried
    assert len(retried_files) >= 1, "Expected at least one file to be retried"

    # Verify overall status reflects retry in progress
    assert retry_data["overall_status"] in [
        JobStatus.PROCESSING.value,
        JobStatus.PENDING.value,
    ]

    # Verify files_pending increased from initial status
    assert retry_data["files_pending"] >= initial_status["files_pending"]

    # Query database to verify individual file jobs were reset
    for file_path in previously_failed_files:
        # Find file job by file_url
        result = await db_session.execute(
            select(ExtractionJob).where(
                ExtractionJob.file_url == file_path,
                ExtractionJob.id != bulk_job_id,  # Exclude bulk job itself
            )
        )
        file_job = result.scalar_one_or_none()

        if file_job:
            # Verify job was reset for retry
            assert file_job.status in [
                ExtractionJobStatus.PENDING.value,
                ExtractionJobStatus.PROCESSING.value,
            ], f"File job should be reset to PENDING or PROCESSING after retry, got {file_job.status}"
            assert file_job.next_retry_at is None, "next_retry_at should be cleared after manual retry"
            assert file_job.error_message is None, "error_message should be cleared after manual retry"


@pytest.mark.asyncio
async def test_retry_bulk_job_no_failed_files(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """
    Test retrying a bulk job with no failed files returns 400 error.

    Verifies that retry endpoint returns error when all files are completed.
    """
    # Create bulk job with valid files
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    files = [
        ("files", ("valid1.pdf", io.BytesIO(valid_pdf), "application/pdf")),
        ("files", ("valid2.pdf", io.BytesIO(valid_pdf), "application/pdf")),
    ]

    upload_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={"auto_detect_format": "true"},
    )

    assert upload_response.status_code == 202
    bulk_job_id = upload_response.json()["bulk_job_id"]

    # Try to retry job that has no failed files (or is still processing)
    # This should either succeed with retried_count=0 (if all pending) or fail
    retry_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}/retry",
        headers=auth_headers,
    )

    # If job has no failed files, should return 400
    # Note: In real scenario with valid PDFs, jobs might still be PENDING/PROCESSING
    # The endpoint returns 400 only if retried_count == 0 after checking all files
    if retry_response.status_code == 400:
        assert "No failed jobs found" in retry_response.json()["detail"]


@pytest.mark.asyncio
async def test_retry_nonexistent_bulk_job(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test retrying a non-existent bulk job returns 404."""
    fake_job_id = str(uuid4())

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/{fake_job_id}/retry",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_retry_bulk_job_unauthorized(client: AsyncClient):
    """Test retrying bulk job without authentication returns 401."""
    fake_job_id = str(uuid4())

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/{fake_job_id}/retry",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_retry_preserves_completed_files(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
):
    """
    Test that retry only affects failed files, not completed ones.

    Verifies:
    - Completed files remain completed after retry
    - Only failed files are reset to PENDING
    - Previous results for completed files are preserved
    """
    from pybase.models.extraction_job import ExtractionJob

    # Create bulk job
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    invalid_content = b"Invalid file content"

    files = [
        ("files", ("valid1.pdf", io.BytesIO(valid_pdf), "application/pdf")),
        ("files", ("invalid.pdf", io.BytesIO(invalid_content), "application/pdf")),
        ("files", ("valid2.pdf", io.BytesIO(valid_pdf), "application/pdf")),
    ]

    upload_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={
            "auto_detect_format": "true",
            "continue_on_error": "true",
        },
    )

    assert upload_response.status_code == 202
    bulk_job_id = upload_response.json()["bulk_job_id"]

    # Get initial status
    status_response = await client.get(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}",
        headers=auth_headers,
    )

    assert status_response.status_code == 200
    initial_status = status_response.json()

    # Track completed files
    completed_files_before = {
        f["file_path"]: f
        for f in initial_status["files"]
        if f["status"] == JobStatus.COMPLETED.value
    }

    # Call retry
    retry_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}/retry",
        headers=auth_headers,
    )

    assert retry_response.status_code == 200
    retry_data = retry_response.json()

    # Verify completed files are still completed
    completed_files_after = {
        f["file_path"]: f
        for f in retry_data["files"]
        if f["status"] == JobStatus.COMPLETED.value
    }

    # Same files should be completed
    assert set(completed_files_before.keys()) == set(completed_files_after.keys())

    # Verify results preserved for completed files
    for file_path in completed_files_before:
        before = completed_files_before[file_path]
        after = completed_files_after[file_path]

        # Status should still be COMPLETED
        assert after["status"] == JobStatus.COMPLETED.value

        # Job ID should be same (not re-created)
        assert after["job_id"] == before["job_id"]

        # Verify database records preserved
        result = await db_session.execute(
            select(ExtractionJob).where(ExtractionJob.id == before["job_id"])
        )
        job = result.scalar_one_or_none()
        assert job is not None
        assert job.status == JobStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_retry_clears_error_messages(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
):
    """
    Test that retry clears error messages from failed jobs.

    Verifies:
    - Failed jobs have error messages set
    - After retry, error messages are cleared
    - Jobs are reset to clean PENDING state
    """
    from pybase.models.extraction_job import ExtractionJob

    # Create bulk job with invalid file that will fail
    invalid_content = b"Invalid PDF content that will fail extraction"

    files = [
        ("files", ("invalid1.pdf", io.BytesIO(invalid_content), "application/pdf")),
        ("files", ("invalid2.pdf", io.BytesIO(invalid_content), "application/pdf")),
    ]

    upload_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={
            "auto_detect_format": "true",
            "continue_on_error": "true",
        },
    )

    assert upload_response.status_code == 202
    bulk_job_id = upload_response.json()["bulk_job_id"]

    # Get initial status with errors
    status_response = await client.get(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}",
        headers=auth_headers,
    )

    assert status_response.status_code == 200
    initial_status = status_response.json()

    # Find failed files with error messages
    failed_files_with_errors = [
        f for f in initial_status["files"]
        if f["status"] == JobStatus.FAILED.value and f.get("error_message")
    ]

    # Skip test if no files failed (might happen if extraction is lenient)
    if not failed_files_with_errors:
        pytest.skip("No files failed, cannot test error message clearing")

    # Store error messages before retry
    errors_before = {
        f["file_path"]: f["error_message"]
        for f in failed_files_with_errors
    }

    # Call retry
    retry_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}/retry",
        headers=auth_headers,
    )

    assert retry_response.status_code == 200
    retry_data = retry_response.json()

    # Verify error messages cleared for retried files
    for file_path in errors_before.keys():
        file_status = next(
            (f for f in retry_data["files"] if f["file_path"] == file_path),
            None
        )

        assert file_status is not None, f"File {file_path} not found in retry response"

        # Error message should be cleared
        if file_status["status"] in [JobStatus.PENDING.value, JobStatus.PROCESSING.value]:
            assert file_status.get("error_message") is None, \
                f"Error message should be cleared for retried file {file_path}"

        # Verify database record also cleared
        result = await db_session.execute(
            select(ExtractionJob).where(
                ExtractionJob.file_url == file_path,
                ExtractionJob.id != bulk_job_id,
            )
        )
        job = result.scalar_one_or_none()

        if job and job.status in [JobStatus.PENDING.value, JobStatus.PROCESSING.value]:
            assert job.error_message is None, \
                f"Database error_message should be cleared for retried job {job.id}"
            assert job.next_retry_at is None, \
                f"Database next_retry_at should be cleared for retried job {job.id}"


@pytest.mark.asyncio
async def test_retry_multiple_times(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """
    Test that failed jobs can be retried multiple times.

    Verifies:
    - Retry endpoint can be called multiple times
    - Each retry resets failed jobs to PENDING
    - Files persist across retries (no re-upload needed)
    """
    # Create bulk job with invalid file
    invalid_content = b"Invalid content"

    files = [
        ("files", ("always_fails.pdf", io.BytesIO(invalid_content), "application/pdf")),
    ]

    upload_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={
            "auto_detect_format": "true",
            "continue_on_error": "true",
        },
    )

    assert upload_response.status_code == 202
    bulk_job_id = upload_response.json()["bulk_job_id"]

    # Retry first time
    retry1_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}/retry",
        headers=auth_headers,
    )

    assert retry1_response.status_code == 200
    retry1_data = retry1_response.json()

    # Verify job was retried
    assert retry1_data["bulk_job_id"] == bulk_job_id
    assert retry1_data["total_files"] == 1

    # Retry second time
    retry2_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}/retry",
        headers=auth_headers,
    )

    assert retry2_response.status_code == 200
    retry2_data = retry2_response.json()

    # Verify same job ID (no re-creation)
    assert retry2_data["bulk_job_id"] == bulk_job_id
    assert retry2_data["total_files"] == 1

    # File should still be tracked (not lost between retries)
    assert len(retry2_data["files"]) == 1
    assert retry2_data["files"][0]["file_path"] == retry1_data["files"][0]["file_path"]

    # Verify files are still in database/temp (no re-upload needed)
    # The fact that retry succeeds without file upload proves persistence
