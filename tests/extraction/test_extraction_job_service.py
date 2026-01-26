"""
Tests for ExtractionJobService.

Tests the extraction job service including:
- CRUD operations (create, read, update, delete)
- Status management (start, complete, fail, cancel)
- Retry logic
- Job listing and filtering
- Statistics
"""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import NotFoundError
from pybase.models.extraction_job import (
    ExtractionJob,
    ExtractionJobFormat,
    ExtractionJobStatus,
)
from pybase.services.extraction_job_service import ExtractionJobService


class TestExtractionJobServiceCreate:
    """Tests for job creation."""

    @pytest.mark.asyncio
    async def test_create_job_minimal(
        self,
        extraction_job_service: ExtractionJobService,
    ):
        """Test creating job with minimal required fields."""
        job = await extraction_job_service.create_job(
            filename="test.pdf",
            file_url="s3://bucket/test.pdf",
            file_size=1024,
            format=ExtractionJobFormat.PDF,
        )

        assert job.id is not None
        assert job.filename == "test.pdf"
        assert job.file_url == "s3://bucket/test.pdf"
        assert job.file_size == 1024
        assert job.format == "pdf"
        assert job.status == ExtractionJobStatus.PENDING.value
        assert job.retry_count == 0
        assert job.max_retries == 3

    @pytest.mark.asyncio
    async def test_create_job_with_options(
        self,
        extraction_job_service: ExtractionJobService,
    ):
        """Test creating job with extraction options."""
        options = {
            "extract_tables": True,
            "extract_text": False,
            "pages": [1, 2, 3],
        }

        job = await extraction_job_service.create_job(
            filename="test.pdf",
            file_url="s3://bucket/test.pdf",
            file_size=2048,
            format=ExtractionJobFormat.PDF,
            options=options,
        )

        assert job.get_options() == options

    @pytest.mark.asyncio
    async def test_create_job_with_all_fields(
        self,
        extraction_job_service: ExtractionJobService,
        test_user,
    ):
        """Test creating job with all optional fields."""
        job = await extraction_job_service.create_job(
            filename="drawing.dxf",
            file_url="s3://bucket/drawing.dxf",
            file_size=4096,
            format=ExtractionJobFormat.DXF,
            created_by_id=str(test_user.id),
            record_id="record-uuid",
            field_id="field-uuid",
            attachment_id="attachment-uuid",
            options={"extract_layers": True},
            max_retries=5,
        )

        assert job.created_by_id == str(test_user.id)
        assert job.record_id == "record-uuid"
        assert job.field_id == "field-uuid"
        assert job.attachment_id == "attachment-uuid"
        assert job.max_retries == 5

    @pytest.mark.asyncio
    async def test_create_job_format_string(
        self,
        extraction_job_service: ExtractionJobService,
    ):
        """Test creating job with format as string."""
        job = await extraction_job_service.create_job(
            filename="test.ifc",
            file_url="s3://bucket/test.ifc",
            file_size=1024,
            format="ifc",  # String instead of enum
        )

        assert job.format == "ifc"


class TestExtractionJobServiceRead:
    """Tests for job retrieval."""

    @pytest.mark.asyncio
    async def test_get_job_exists(
        self,
        extraction_job_service: ExtractionJobService,
        sample_extraction_job: ExtractionJob,
    ):
        """Test getting existing job by ID."""
        job = await extraction_job_service.get_job(sample_extraction_job.id)

        assert job.id == sample_extraction_job.id
        assert job.filename == sample_extraction_job.filename

    @pytest.mark.asyncio
    async def test_get_job_not_found(
        self,
        extraction_job_service: ExtractionJobService,
    ):
        """Test getting non-existent job raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await extraction_job_service.get_job("non-existent-uuid")

    @pytest.mark.asyncio
    async def test_get_job_by_file_url(
        self,
        extraction_job_service: ExtractionJobService,
        sample_extraction_job: ExtractionJob,
    ):
        """Test getting job by file URL."""
        job = await extraction_job_service.get_job_by_file_url(sample_extraction_job.file_url)

        assert job is not None
        assert job.id == sample_extraction_job.id

    @pytest.mark.asyncio
    async def test_get_job_by_file_url_not_found(
        self,
        extraction_job_service: ExtractionJobService,
    ):
        """Test getting job by non-existent file URL returns None."""
        job = await extraction_job_service.get_job_by_file_url("s3://bucket/non-existent.pdf")

        assert job is None


class TestExtractionJobServiceList:
    """Tests for job listing."""

    @pytest.mark.asyncio
    async def test_list_jobs_empty(
        self,
        extraction_job_service: ExtractionJobService,
    ):
        """Test listing jobs when none exist."""
        jobs, total = await extraction_job_service.list_jobs()

        assert jobs == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_jobs_with_data(
        self,
        extraction_job_service: ExtractionJobService,
        multiple_extraction_jobs: list[ExtractionJob],
    ):
        """Test listing all jobs."""
        jobs, total = await extraction_job_service.list_jobs()

        assert total == len(multiple_extraction_jobs)
        assert len(jobs) == len(multiple_extraction_jobs)

    @pytest.mark.asyncio
    async def test_list_jobs_filter_by_status(
        self,
        extraction_job_service: ExtractionJobService,
        multiple_extraction_jobs: list[ExtractionJob],
    ):
        """Test filtering jobs by status."""
        jobs, total = await extraction_job_service.list_jobs(status=ExtractionJobStatus.PENDING)

        assert total == 3  # 3 pending jobs in fixture
        for job in jobs:
            assert job.status == ExtractionJobStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_list_jobs_filter_by_format(
        self,
        extraction_job_service: ExtractionJobService,
        multiple_extraction_jobs: list[ExtractionJob],
    ):
        """Test filtering jobs by format."""
        jobs, total = await extraction_job_service.list_jobs(format=ExtractionJobFormat.PDF)

        # 3 pending PDFs + 1 cancelled PDF = 4
        assert total == 4
        for job in jobs:
            assert job.format == ExtractionJobFormat.PDF.value

    @pytest.mark.asyncio
    async def test_list_jobs_pagination(
        self,
        extraction_job_service: ExtractionJobService,
        multiple_extraction_jobs: list[ExtractionJob],
    ):
        """Test job listing pagination."""
        # Get first page
        jobs_page1, total = await extraction_job_service.list_jobs(page=1, page_size=3)

        assert total == len(multiple_extraction_jobs)
        assert len(jobs_page1) == 3

        # Get second page
        jobs_page2, _ = await extraction_job_service.list_jobs(page=2, page_size=3)

        assert len(jobs_page2) == 3

        # Ensure no overlap
        page1_ids = {j.id for j in jobs_page1}
        page2_ids = {j.id for j in jobs_page2}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_list_pending_jobs(
        self,
        extraction_job_service: ExtractionJobService,
        multiple_extraction_jobs: list[ExtractionJob],
    ):
        """Test listing pending jobs."""
        jobs = await extraction_job_service.list_pending_jobs()

        assert len(jobs) == 3
        for job in jobs:
            assert job.status == ExtractionJobStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_list_retryable_jobs(
        self,
        extraction_job_service: ExtractionJobService,
        multiple_extraction_jobs: list[ExtractionJob],
    ):
        """Test listing retryable jobs."""
        jobs = await extraction_job_service.list_retryable_jobs()

        # 1 failed job with retry_count=1, max_retries=3
        assert len(jobs) == 1
        assert jobs[0].status == ExtractionJobStatus.FAILED.value
        assert jobs[0].retry_count < jobs[0].max_retries


class TestExtractionJobServiceStatusUpdates:
    """Tests for status update operations."""

    @pytest.mark.asyncio
    async def test_start_processing(
        self,
        extraction_job_service: ExtractionJobService,
        sample_extraction_job: ExtractionJob,
    ):
        """Test marking job as processing."""
        job = await extraction_job_service.start_processing(sample_extraction_job.id)

        assert job.status == ExtractionJobStatus.PROCESSING.value
        assert job.started_at is not None

    @pytest.mark.asyncio
    async def test_complete_job(
        self,
        extraction_job_service: ExtractionJobService,
        sample_extraction_job: ExtractionJob,
    ):
        """Test marking job as completed."""
        result = {
            "success": True,
            "tables": [{"headers": ["A"], "rows": [["1"]]}],
        }

        job = await extraction_job_service.complete_job(
            sample_extraction_job.id,
            result=result,
        )

        assert job.status == ExtractionJobStatus.COMPLETED.value
        assert job.completed_at is not None
        assert job.get_result() == result

    @pytest.mark.asyncio
    async def test_fail_job_with_retry(
        self,
        extraction_job_service: ExtractionJobService,
        sample_extraction_job: ExtractionJob,
    ):
        """Test failing job with retry scheduled."""
        job = await extraction_job_service.fail_job(
            sample_extraction_job.id,
            error_message="Test error",
            schedule_retry=True,
            retry_delay_seconds=60,
        )

        assert job.status == ExtractionJobStatus.FAILED.value
        assert job.error_message == "Test error"
        assert job.retry_count == 1
        assert job.next_retry_at is not None
        assert job.completed_at is None  # Not completed yet, can retry

    @pytest.mark.asyncio
    async def test_fail_job_no_retry(
        self,
        extraction_job_service: ExtractionJobService,
        sample_extraction_job: ExtractionJob,
    ):
        """Test failing job without retry."""
        job = await extraction_job_service.fail_job(
            sample_extraction_job.id,
            error_message="Permanent error",
            schedule_retry=False,
        )

        assert job.status == ExtractionJobStatus.FAILED.value
        assert job.next_retry_at is None

    @pytest.mark.asyncio
    async def test_fail_job_exhausted_retries(
        self,
        extraction_job_service: ExtractionJobService,
        exhausted_extraction_job: ExtractionJob,
    ):
        """Test failing job that has exhausted retries."""
        # Reset to pending first to allow failing
        exhausted_extraction_job.status = ExtractionJobStatus.PENDING.value
        exhausted_extraction_job.retry_count = 2  # One less than max

        job = await extraction_job_service.fail_job(
            exhausted_extraction_job.id,
            error_message="Final failure",
            schedule_retry=True,
        )

        # retry_count is now 3 (== max_retries), so completed_at should be set
        assert job.retry_count == 3
        assert job.completed_at is not None

    @pytest.mark.asyncio
    async def test_cancel_job(
        self,
        extraction_job_service: ExtractionJobService,
        sample_extraction_job: ExtractionJob,
    ):
        """Test cancelling a pending job."""
        job = await extraction_job_service.cancel_job(sample_extraction_job.id)

        assert job.status == ExtractionJobStatus.CANCELLED.value
        assert job.completed_at is not None

    @pytest.mark.asyncio
    async def test_cancel_completed_job_no_change(
        self,
        extraction_job_service: ExtractionJobService,
        completed_extraction_job: ExtractionJob,
    ):
        """Test cancelling already completed job doesn't change status."""
        job = await extraction_job_service.cancel_job(completed_extraction_job.id)

        assert job.status == ExtractionJobStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_reset_for_retry(
        self,
        extraction_job_service: ExtractionJobService,
        failed_extraction_job: ExtractionJob,
    ):
        """Test resetting failed job for retry."""
        job = await extraction_job_service.reset_for_retry(failed_extraction_job.id)

        assert job.status == ExtractionJobStatus.PENDING.value
        assert job.next_retry_at is None
        assert job.error_message is None

    @pytest.mark.asyncio
    async def test_reset_non_failed_job_no_change(
        self,
        extraction_job_service: ExtractionJobService,
        sample_extraction_job: ExtractionJob,
    ):
        """Test resetting non-failed job doesn't change status."""
        job = await extraction_job_service.reset_for_retry(sample_extraction_job.id)

        assert job.status == ExtractionJobStatus.PENDING.value  # Already pending


class TestExtractionJobServiceDelete:
    """Tests for job deletion."""

    @pytest.mark.asyncio
    async def test_delete_job(
        self,
        extraction_job_service: ExtractionJobService,
        sample_extraction_job: ExtractionJob,
    ):
        """Test deleting a job."""
        job_id = sample_extraction_job.id

        await extraction_job_service.delete_job(job_id)

        with pytest.raises(NotFoundError):
            await extraction_job_service.get_job(job_id)

    @pytest.mark.asyncio
    async def test_delete_job_not_found(
        self,
        extraction_job_service: ExtractionJobService,
    ):
        """Test deleting non-existent job raises NotFoundError."""
        with pytest.raises(NotFoundError):
            await extraction_job_service.delete_job("non-existent-uuid")

    @pytest.mark.asyncio
    async def test_delete_completed_jobs_older_than(
        self,
        extraction_job_service: ExtractionJobService,
        db_session: AsyncSession,
    ):
        """Test deleting old completed jobs."""
        # Create an old completed job
        old_job = ExtractionJob(
            id="old-job-uuid",
            filename="old.pdf",
            file_url="s3://bucket/old.pdf",
            file_size=1024,
            format="pdf",
            status=ExtractionJobStatus.COMPLETED.value,
        )
        old_job.completed_at = datetime.now(timezone.utc) - timedelta(days=60)
        db_session.add(old_job)
        await db_session.commit()

        # Delete jobs older than 30 days
        deleted_count = await extraction_job_service.delete_completed_jobs(older_than_days=30)

        assert deleted_count == 1

        # Verify job is deleted
        with pytest.raises(NotFoundError):
            await extraction_job_service.get_job("old-job-uuid")


class TestExtractionJobServiceStats:
    """Tests for job statistics."""

    @pytest.mark.asyncio
    async def test_get_job_stats_empty(
        self,
        extraction_job_service: ExtractionJobService,
    ):
        """Test getting stats when no jobs exist."""
        stats = await extraction_job_service.get_job_stats()

        assert stats["pending"] == 0
        assert stats["processing"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0
        assert stats["cancelled"] == 0

    @pytest.mark.asyncio
    async def test_get_job_stats_with_data(
        self,
        extraction_job_service: ExtractionJobService,
        multiple_extraction_jobs: list[ExtractionJob],
    ):
        """Test getting stats with various job statuses."""
        stats = await extraction_job_service.get_job_stats()

        assert stats["pending"] == 3
        assert stats["processing"] == 1
        assert stats["completed"] == 2
        assert stats["failed"] == 1
        assert stats["cancelled"] == 1
