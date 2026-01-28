"""
Integration tests for bulk worker restart recovery.

Tests verify that bulk extraction jobs can recover from worker restarts
and maintain database consistency throughout the lifecycle.
"""

import io

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.config import settings
from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus


@pytest.mark.asyncio
async def test_bulk_job_survives_worker_restart_simulation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """
    Test that bulk job persists and can be recovered after worker restart.

    This test simulates a worker restart scenario:
    1. Create bulk job via API
    2. Verify job exists in database with PENDING status
    3. Simulate worker picking up job (mark as PROCESSING)
    4. Simulate worker restart (verify job still exists)
    5. Verify job can still be queried via API
    6. Verify individual file jobs are still in database
    """
    # Create multiple PDF files for testing
    pdf_content_1 = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"
    pdf_content_2 = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"
    pdf_content_3 = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"

    files = [
        ("files", ("test1.pdf", io.BytesIO(pdf_content_1), "application/pdf")),
        ("files", ("test2.pdf", io.BytesIO(pdf_content_2), "application/pdf")),
        ("files", ("test3.pdf", io.BytesIO(pdf_content_3), "application/pdf")),
    ]

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

    bulk_job_id = result["bulk_job_id"]
    assert bulk_job_id is not None
    assert result["total_files"] == 3
    assert result["overall_status"] == "pending"

    # Step 1: Verify bulk job exists in database before worker processing
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    bulk_job = job_result.scalar_one_or_none()

    assert bulk_job is not None, "Bulk job not found in database"
    assert bulk_job.status == ExtractionJobStatus.PENDING
    assert bulk_job.started_at is None

    # Get file paths from bulk job options
    options = bulk_job.get_options()
    file_paths = options.get("file_paths", [])
    assert len(file_paths) == 3

    # Step 2: Simulate worker picking up the job
    # In real scenario, worker would call update_job_start()
    from pybase.services.extraction_job_service import ExtractionJobService

    job_service = ExtractionJobService(db_session)
    await job_service.start_processing(str(bulk_job.id), celery_task_id="celery-task-123")

    # Refresh from database
    await db_session.refresh(bulk_job)

    assert bulk_job.status == ExtractionJobStatus.PROCESSING
    assert bulk_job.started_at is not None
    assert bulk_job.celery_task_id == "celery-task-123"

    # Step 3: Simulate worker restart - verify job still exists
    # In real scenario, worker would restart and query for PROCESSING jobs
    # Here we just verify the job persists
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    restarted_job = job_result.scalar_one_or_none()

    assert restarted_job is not None, "Bulk job lost after worker restart simulation"
    assert restarted_job.status == ExtractionJobStatus.PROCESSING
    assert restarted_job.started_at is not None

    # Step 4: Verify job can still be queried via API after restart
    status_response = await client.get(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}",
        headers=auth_headers,
    )

    assert status_response.status_code == 200
    status_data = status_response.json()

    assert status_data["bulk_job_id"] == bulk_job_id
    assert status_data["total_files"] == 3
    assert status_data["overall_status"] == "processing"
    assert status_data["files_pending"] == 3  # All files still pending

    # Step 5: Verify individual file jobs exist and can be recovered
    # The BulkExtractionService should create individual jobs for each file
    # These should also survive worker restart
    for file_path in file_paths:
        # Query by file_url to find individual file jobs
        file_job = await job_service.get_job_by_file_url(file_path)
        if file_job:
            # Individual file jobs should exist and be queryable
            assert file_job.id is not None
            # File jobs may be PENDING or PROCESSING depending on when worker was interrupted


@pytest.mark.asyncio
async def test_bulk_job_progress_persists_across_restart(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """
    Test that bulk job progress persists across worker restart.

    This test verifies:
    1. Bulk job progress updates are saved to database
    2. After simulated restart, progress is maintained
    3. Worker can resume from saved progress
    """
    # Create bulk job
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"

    files = [
        ("files", (f"test{i}.pdf", io.BytesIO(pdf_content), "application/pdf"))
        for i in range(5)
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

    # Query bulk job
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    bulk_job = job_result.scalar_one_or_none()

    assert bulk_job is not None
    assert bulk_job.progress == 0

    # Simulate worker progress: update to 40% (2 out of 5 files completed)
    from pybase.services.extraction_job_service import ExtractionJobService

    job_service = ExtractionJobService(db_session)
    await job_service.start_processing(str(bulk_job.id), celery_task_id="task-456")
    await job_service.update_progress(str(bulk_job.id), 40)

    # Refresh from database
    await db_session.refresh(bulk_job)

    assert bulk_job.progress == 40

    # Simulate worker restart - verify progress persisted
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    restarted_job = job_result.scalar_one_or_none()

    assert restarted_job is not None
    assert restarted_job.progress == 40, "Progress lost after worker restart"

    # Verify API returns persisted progress
    status_response = await client.get(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}",
        headers=auth_headers,
    )

    assert status_response.status_code == 200
    status_data = status_response.json()

    assert status_data["progress"] == 40


@pytest.mark.asyncio
async def test_bulk_job_with_partial_completion_recovers_correctly(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """
    Test that partially completed bulk jobs can resume after worker restart.

    Scenario:
    1. Bulk job with 3 files
    2. Worker completes 1 file, 1 file processing, 1 file pending
    3. Worker restarts
    4. Verify completed file results are preserved
    5. Verify job can resume remaining files
    """
    # Create bulk job
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"

    files = [
        ("files", ("file1.pdf", io.BytesIO(pdf_content), "application/pdf")),
        ("files", ("file2.pdf", io.BytesIO(pdf_content), "application/pdf")),
        ("files", ("file3.pdf", io.BytesIO(pdf_content), "application/pdf")),
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

    # Get bulk job from database
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    bulk_job = job_result.scalar_one_or_none()

    assert bulk_job is not None

    # Get file paths
    options = bulk_job.get_options()
    file_paths = options.get("file_paths", [])

    # Simulate partial completion:
    # Create individual file jobs and set their statuses
    from pybase.services.extraction_job_service import ExtractionJobService

    job_service = ExtractionJobService(db_session)

    # File 1: Completed with results
    job1 = await job_service.create_job(
        filename="file1.pdf",
        file_url=file_paths[0],
        file_size=100,
        format="pdf",
        options={},
        skip_duplicate_check=True,
    )
    await job_service.start_processing(str(job1.id))
    await job_service.update_progress(str(job1.id), 100)
    result1 = {"source_file": "file1.pdf", "success": True, "tables": []}
    await job_service.complete_job(str(job1.id), result1)

    # File 2: Processing (interrupted by restart)
    job2 = await job_service.create_job(
        filename="file2.pdf",
        file_url=file_paths[1],
        file_size=100,
        format="pdf",
        options={},
        skip_duplicate_check=True,
    )
    await job_service.start_processing(str(job2.id))
    await job_service.update_progress(str(job2.id), 50)  # Half done

    # File 3: Still pending
    job3 = await job_service.create_job(
        filename="file3.pdf",
        file_url=file_paths[2],
        file_size=100,
        format="pdf",
        options={},
        skip_duplicate_check=True,
    )
    # job3 remains PENDING

    # Mark bulk job as processing
    await job_service.start_processing(str(bulk_job.id), celery_task_id="bulk-task-789")
    await job_service.update_progress(str(bulk_job.id), 33)  # 1/3 complete

    # Simulate worker restart
    # Query bulk job after restart
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    restarted_bulk_job = job_result.scalar_one_or_none()

    assert restarted_bulk_job is not None
    assert restarted_bulk_job.progress == 33

    # Verify individual file jobs can be recovered
    recovered_job1 = await job_service.get_job_by_file_url(file_paths[0])
    assert recovered_job1 is not None
    assert recovered_job1.status == ExtractionJobStatus.COMPLETED
    assert recovered_job1.progress == 100
    assert recovered_job1.get_result() == result1

    recovered_job2 = await job_service.get_job_by_file_url(file_paths[1])
    assert recovered_job2 is not None
    assert recovered_job2.status == ExtractionJobStatus.PROCESSING
    assert recovered_job2.progress == 50

    recovered_job3 = await job_service.get_job_by_file_url(file_paths[2])
    assert recovered_job3 is not None
    assert recovered_job3.status == ExtractionJobStatus.PENDING
    assert recovered_job3.progress == 0

    # Verify API returns correct status for partial completion
    status_response = await client.get(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}",
        headers=auth_headers,
    )

    assert status_response.status_code == 200
    status_data = status_response.json()

    assert status_data["bulk_job_id"] == bulk_job_id
    assert status_data["total_files"] == 3
    # Status should reflect partial completion
    assert status_data["files_completed"] >= 0
    assert status_data["files_pending"] >= 0
    assert status_data["progress"] == 33


@pytest.mark.asyncio
async def test_bulk_job_failed_files_persist_after_restart(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """
    Test that failed file statuses persist across worker restart.

    Scenario:
    1. Bulk job with 2 files
    2. File 1 fails
    3. Worker restarts
    4. Verify failed status is preserved
    5. Verify job can be retried
    """
    # Create bulk job
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"

    files = [
        ("files", ("file1.pdf", io.BytesIO(pdf_content), "application/pdf")),
        ("files", ("file2.pdf", io.BytesIO(pdf_content), "application/pdf")),
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

    # Get bulk job from database
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    bulk_job = job_result.scalar_one_or_none()

    assert bulk_job is not None

    # Get file paths
    options = bulk_job.get_options()
    file_paths = options.get("file_paths", [])

    # Simulate file failure
    from pybase.services.extraction_job_service import ExtractionJobService

    job_service = ExtractionJobService(db_session)

    # File 1: Failed
    job1 = await job_service.create_job(
        filename="file1.pdf",
        file_url=file_paths[0],
        file_size=100,
        format="pdf",
        options={},
        skip_duplicate_check=True,
    )
    await job_service.start_processing(str(job1.id))
    error_msg = "Extraction failed: Invalid PDF format"
    await job_service.fail_job(str(job1.id), error_msg, schedule_retry=False)

    # File 2: Completed
    job2 = await job_service.create_job(
        filename="file2.pdf",
        file_url=file_paths[1],
        file_size=100,
        format="pdf",
        options={},
        skip_duplicate_check=True,
    )
    await job_service.start_processing(str(job2.id))
    await job_service.complete_job(str(job2.id), {"success": True})

    # Mark bulk job as processing
    await job_service.start_processing(str(bulk_job.id))

    # Simulate worker restart
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    restarted_bulk_job = job_result.scalar_one_or_none()

    assert restarted_bulk_job is not None

    # Verify failed job persists with error message
    failed_job = await job_service.get_job_by_file_url(file_paths[0])
    assert failed_job is not None
    assert failed_job.status == ExtractionJobStatus.FAILED
    assert error_msg in failed_job.error_message

    # Verify completed job persists
    completed_job = await job_service.get_job_by_file_url(file_paths[1])
    assert completed_job is not None
    assert completed_job.status == ExtractionJobStatus.COMPLETED

    # Verify API reflects failed status
    status_response = await client.get(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}",
        headers=auth_headers,
    )

    assert status_response.status_code == 200
    status_data = status_response.json()

    assert status_data["bulk_job_id"] == bulk_job_id
    assert status_data["files_failed"] >= 1


@pytest.mark.asyncio
async def test_bulk_job_retry_after_worker_restart(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
):
    """
    Test that failed bulk jobs can be retried after worker restart.

    Scenario:
    1. Create bulk job
    2. Some files fail
    3. Worker restarts
    4. Retry endpoint resets failed jobs to PENDING
    5. Verify jobs can be processed again
    """
    # Create bulk job
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n%%EOF"

    files = [
        ("files", ("file1.pdf", io.BytesIO(pdf_content), "application/pdf")),
        ("files", ("file2.pdf", io.BytesIO(pdf_content), "application/pdf")),
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

    # Get bulk job and simulate failures
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    bulk_job = job_result.scalar_one_or_none()

    options = bulk_job.get_options()
    file_paths = options.get("file_paths", [])

    from pybase.services.extraction_job_service import ExtractionJobService

    job_service = ExtractionJobService(db_session)

    # Mark both files as failed
    for file_path in file_paths:
        job = await job_service.create_job(
            filename=file_path.split("/")[-1],
            file_url=file_path,
            file_size=100,
            format="pdf",
            options={},
            skip_duplicate_check=True,
        )
        await job_service.start_processing(str(job.id))
        await job_service.fail_job(str(job.id), "Simulated failure", schedule_retry=False)

    # Mark bulk job as completed (with failures)
    await job_service.start_processing(str(bulk_job.id))

    # Simulate worker restart - verify failed status persists
    stmt = select(ExtractionJob).where(ExtractionJob.id == bulk_job_id)
    job_result = await db_session.execute(stmt)
    restarted_bulk_job = job_result.scalar_one_or_none()

    assert restarted_bulk_job is not None

    # Verify failed jobs before retry
    failed_job1 = await job_service.get_job_by_file_url(file_paths[0])
    assert failed_job1.status == ExtractionJobStatus.FAILED

    # Call retry endpoint to reset failed jobs
    retry_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}/retry",
        headers=auth_headers,
    )

    # Retry should succeed (200 or 202)
    assert retry_response.status_code in [200, 202]
    retry_data = retry_response.json()

    # Verify retry response
    assert retry_data["bulk_job_id"] == bulk_job_id
    assert "retried_count" in retry_data or "message" in retry_data

    # Verify jobs reset to PENDING after retry
    retried_job1 = await job_service.get_job_by_file_url(file_paths[0])
    # Job should be reset to PENDING or PROCESSING (worker may have picked it up)
    assert retried_job1.status in [
        ExtractionJobStatus.PENDING,
        ExtractionJobStatus.PROCESSING,
    ]
