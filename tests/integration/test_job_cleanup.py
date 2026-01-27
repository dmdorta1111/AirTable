"""
Tests for job cleanup respecting retention policy.

Tests the cleanup functionality including:
- Old completed jobs are deleted
- Old cancelled jobs are deleted
- Recent jobs are preserved
- Pending/processing/failed jobs are preserved
- Custom retention periods work correctly
"""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import NotFoundError
from pybase.models.extraction_job import (
    ExtractionJob,
    ExtractionFormat,
    ExtractionJobStatus,
)
from pybase.services.extraction_job_service import ExtractionJobService
from uuid import uuid4

# Alias for backwards compatibility
ExtractionJobFormat = ExtractionFormat


class TestJobCleanupRetentionPolicy:
    """Tests for job cleanup respecting retention policy."""

    @pytest.mark.asyncio
    async def test_delete_old_completed_jobs(
        self,
        extraction_job_service: ExtractionJobService,
        db_session: AsyncSession,
    ):
        """Test that completed jobs older than retention period are deleted."""
        # Create an old completed job (60 days old)
        old_job = ExtractionJob(
            id=str(uuid4()),
            filename="old_completed.pdf",
            file_url="s3://bucket/old_completed.pdf",
            file_size=1024,
            format=ExtractionJobFormat.PDF.value,
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
            await extraction_job_service.get_job(old_job.id)

    @pytest.mark.asyncio
    async def test_preserve_recent_completed_jobs(
        self,
        extraction_job_service: ExtractionJobService,
        db_session: AsyncSession,
    ):
        """Test that completed jobs newer than retention period are preserved."""
        # Create a recent completed job (10 days old)
        recent_job = ExtractionJob(
            id=str(uuid4()),
            filename="recent_completed.pdf",
            file_url="s3://bucket/recent_completed.pdf",
            file_size=2048,
            format=ExtractionJobFormat.PDF.value,
            status=ExtractionJobStatus.COMPLETED.value,
        )
        recent_job.completed_at = datetime.now(timezone.utc) - timedelta(days=10)
        db_session.add(recent_job)
        await db_session.commit()

        # Delete jobs older than 30 days
        deleted_count = await extraction_job_service.delete_completed_jobs(older_than_days=30)

        assert deleted_count == 0

        # Verify job still exists
        job = await extraction_job_service.get_job(recent_job.id)
        assert job.id == recent_job.id

    @pytest.mark.asyncio
    async def test_delete_old_cancelled_jobs(
        self,
        extraction_job_service: ExtractionJobService,
        db_session: AsyncSession,
    ):
        """Test that cancelled jobs older than retention period are deleted."""
        # Create an old cancelled job (45 days old)
        old_cancelled = ExtractionJob(
            id=str(uuid4()),
            filename="old_cancelled.dxf",
            file_url="s3://bucket/old_cancelled.dxf",
            file_size=3072,
            format=ExtractionJobFormat.DXF.value,
            status=ExtractionJobStatus.CANCELLED.value,
        )
        old_cancelled.completed_at = datetime.now(timezone.utc) - timedelta(days=45)
        db_session.add(old_cancelled)
        await db_session.commit()

        # Delete jobs older than 30 days
        deleted_count = await extraction_job_service.delete_completed_jobs(older_than_days=30)

        assert deleted_count == 1

        # Verify job is deleted
        with pytest.raises(NotFoundError):
            await extraction_job_service.get_job(old_cancelled.id)

    @pytest.mark.asyncio
    async def test_preserve_pending_jobs(
        self,
        extraction_job_service: ExtractionJobService,
        db_session: AsyncSession,
    ):
        """Test that pending jobs are preserved regardless of age."""
        # Create an old pending job (100 days old, but still pending)
        old_pending = ExtractionJob(
            id=str(uuid4()),
            filename="old_pending.ifc",
            file_url="s3://bucket/old_pending.ifc",
            file_size=4096,
            format=ExtractionJobFormat.IFC.value,
            status=ExtractionJobStatus.PENDING.value,
        )
        old_pending.created_at = datetime.now(timezone.utc) - timedelta(days=100)
        db_session.add(old_pending)
        await db_session.commit()

        # Delete jobs older than 30 days
        deleted_count = await extraction_job_service.delete_completed_jobs(older_than_days=30)

        assert deleted_count == 0

        # Verify pending job still exists
        job = await extraction_job_service.get_job(old_pending.id)
        assert job.status == ExtractionJobStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_preserve_processing_jobs(
        self,
        extraction_job_service: ExtractionJobService,
        db_session: AsyncSession,
    ):
        """Test that processing jobs are preserved regardless of age."""
        # Create an old processing job (50 days old, still processing)
        old_processing = ExtractionJob(
            id=str(uuid4()),
            filename="old_processing.step",
            file_url="s3://bucket/old_processing.step",
            file_size=5120,
            format=ExtractionJobFormat.STEP.value,
            status=ExtractionJobStatus.PROCESSING.value,
        )
        old_processing.started_at = datetime.now(timezone.utc) - timedelta(days=50)
        db_session.add(old_processing)
        await db_session.commit()

        # Delete jobs older than 30 days
        deleted_count = await extraction_job_service.delete_completed_jobs(older_than_days=30)

        assert deleted_count == 0

        # Verify processing job still exists
        job = await extraction_job_service.get_job(old_processing.id)
        assert job.status == ExtractionJobStatus.PROCESSING.value

    @pytest.mark.asyncio
    async def test_preserve_failed_jobs(
        self,
        extraction_job_service: ExtractionJobService,
        db_session: AsyncSession,
    ):
        """Test that failed jobs are preserved regardless of age."""
        # Create an old failed job (80 days old)
        old_failed = ExtractionJob(
            id=str(uuid4()),
            filename="old_failed.pdf",
            file_url="s3://bucket/old_failed.pdf",
            file_size=6144,
            format=ExtractionJobFormat.PDF.value,
            status=ExtractionJobStatus.FAILED.value,
            error_message="Old failure",
        )
        old_failed.started_at = datetime.now(timezone.utc) - timedelta(days=80)
        db_session.add(old_failed)
        await db_session.commit()

        # Delete jobs older than 30 days
        deleted_count = await extraction_job_service.delete_completed_jobs(older_than_days=30)

        assert deleted_count == 0

        # Verify failed job still exists
        job = await extraction_job_service.get_job(old_failed.id)
        assert job.status == ExtractionJobStatus.FAILED.value

    @pytest.mark.asyncio
    async def test_custom_retention_period(
        self,
        extraction_job_service: ExtractionJobService,
        db_session: AsyncSession,
    ):
        """Test cleanup with custom retention period (90 days)."""
        # Create completed jobs at different ages
        job_100_days = ExtractionJob(
            id=str(uuid4()),
            filename="job_100_days.pdf",
            file_url="s3://bucket/job_100_days.pdf",
            file_size=1024,
            format=ExtractionJobFormat.PDF.value,
            status=ExtractionJobStatus.COMPLETED.value,
        )
        job_100_days.completed_at = datetime.now(timezone.utc) - timedelta(days=100)

        job_80_days = ExtractionJob(
            id=str(uuid4()),
            filename="job_80_days.pdf",
            file_url="s3://bucket/job_80_days.pdf",
            file_size=2048,
            format=ExtractionJobFormat.PDF.value,
            status=ExtractionJobStatus.COMPLETED.value,
        )
        job_80_days.completed_at = datetime.now(timezone.utc) - timedelta(days=80)

        job_50_days = ExtractionJob(
            id=str(uuid4()),
            filename="job_50_days.pdf",
            file_url="s3://bucket/job_50_days.pdf",
            file_size=3072,
            format=ExtractionJobFormat.PDF.value,
            status=ExtractionJobStatus.COMPLETED.value,
        )
        job_50_days.completed_at = datetime.now(timezone.utc) - timedelta(days=50)

        db_session.add_all([job_100_days, job_80_days, job_50_days])
        await db_session.commit()

        # Delete jobs older than 90 days (only job_100_days should be deleted)
        deleted_count = await extraction_job_service.delete_completed_jobs(older_than_days=90)

        assert deleted_count == 1

        # Verify only 100-day job is deleted
        with pytest.raises(NotFoundError):
            await extraction_job_service.get_job(job_100_days.id)

        # Other jobs should still exist
        job_80 = await extraction_job_service.get_job(job_80_days.id)
        assert job_80.id == job_80_days.id

        job_50 = await extraction_job_service.get_job(job_50_days.id)
        assert job_50.id == job_50_days.id

    @pytest.mark.asyncio
    async def test_completed_job_without_completed_at_preserved(
        self,
        extraction_job_service: ExtractionJobService,
        db_session: AsyncSession,
    ):
        """Test that completed jobs without completed_at are preserved."""
        # Create a completed job without completed_at (edge case)
        job_no_completed_at = ExtractionJob(
            id=str(uuid4()),
            filename="no_completed_at.pdf",
            file_url="s3://bucket/no_completed_at.pdf",
            file_size=1024,
            format=ExtractionJobFormat.PDF.value,
            status=ExtractionJobStatus.COMPLETED.value,
        )
        # Note: completed_at is None
        db_session.add(job_no_completed_at)
        await db_session.commit()

        # Delete jobs older than 30 days
        deleted_count = await extraction_job_service.delete_completed_jobs(older_than_days=30)

        # Job should NOT be deleted (no completed_at to compare)
        assert deleted_count == 0

        # Verify job still exists
        job = await extraction_job_service.get_job(job_no_completed_at.id)
        assert job.id == job_no_completed_at.id

    @pytest.mark.asyncio
    async def test_mixed_age_and_status_cleanup(
        self,
        extraction_job_service: ExtractionJobService,
        db_session: AsyncSession,
    ):
        """Test cleanup with mixed job ages and statuses."""
        jobs = []

        # Old completed (should be deleted)
        old_completed = ExtractionJob(
            id=str(uuid4()),
            filename="old_completed.pdf",
            file_url="s3://bucket/old_completed.pdf",
            file_size=1024,
            format=ExtractionJobFormat.PDF.value,
            status=ExtractionJobStatus.COMPLETED.value,
        )
        old_completed.completed_at = datetime.now(timezone.utc) - timedelta(days=60)
        jobs.append(old_completed)

        # Old cancelled (should be deleted)
        old_cancelled = ExtractionJob(
            id=str(uuid4()),
            filename="old_cancelled.dxf",
            file_url="s3://bucket/old_cancelled.dxf",
            file_size=2048,
            format=ExtractionJobFormat.DXF.value,
            status=ExtractionJobStatus.CANCELLED.value,
        )
        old_cancelled.completed_at = datetime.now(timezone.utc) - timedelta(days=45)
        jobs.append(old_cancelled)

        # Recent completed (should be preserved)
        recent_completed = ExtractionJob(
            id=str(uuid4()),
            filename="recent_completed.ifc",
            file_url="s3://bucket/recent_completed.ifc",
            file_size=3072,
            format=ExtractionJobFormat.IFC.value,
            status=ExtractionJobStatus.COMPLETED.value,
        )
        recent_completed.completed_at = datetime.now(timezone.utc) - timedelta(days=10)
        jobs.append(recent_completed)

        # Old pending (should be preserved - not completed)
        old_pending = ExtractionJob(
            id=str(uuid4()),
            filename="old_pending.step",
            file_url="s3://bucket/old_pending.step",
            file_size=4096,
            format=ExtractionJobFormat.STEP.value,
            status=ExtractionJobStatus.PENDING.value,
        )
        old_pending.created_at = datetime.now(timezone.utc) - timedelta(days=90)
        jobs.append(old_pending)

        # Old failed (should be preserved - not completed/cancelled)
        old_failed = ExtractionJob(
            id=str(uuid4()),
            filename="old_failed.pdf",
            file_url="s3://bucket/old_failed.pdf",
            file_size=5120,
            format=ExtractionJobFormat.PDF.value,
            status=ExtractionJobStatus.FAILED.value,
        )
        old_failed.started_at = datetime.now(timezone.utc) - timedelta(days=70)
        jobs.append(old_failed)

        # Old processing (should be preserved - not completed/cancelled)
        old_processing = ExtractionJob(
            id=str(uuid4()),
            filename="old_processing.dxf",
            file_url="s3://bucket/old_processing.dxf",
            file_size=6144,
            format=ExtractionJobFormat.DXF.value,
            status=ExtractionJobStatus.PROCESSING.value,
        )
        old_processing.started_at = datetime.now(timezone.utc) - timedelta(days=50)
        jobs.append(old_processing)

        db_session.add_all(jobs)
        await db_session.commit()

        # Delete jobs older than 30 days
        deleted_count = await extraction_job_service.delete_completed_jobs(older_than_days=30)

        # Should delete only old_completed and old_cancelled
        assert deleted_count == 2

        # Verify deletions
        with pytest.raises(NotFoundError):
            await extraction_job_service.get_job(old_completed.id)

        with pytest.raises(NotFoundError):
            await extraction_job_service.get_job(old_cancelled.id)

        # Verify preserved jobs
        preserved_ids = [
            recent_completed.id,
            old_pending.id,
            old_failed.id,
            old_processing.id,
        ]
        for job_id in preserved_ids:
            job = await extraction_job_service.get_job(job_id)
            assert job.id == job_id

    @pytest.mark.asyncio
    async def test_default_retention_30_days(
        self,
        extraction_job_service: ExtractionJobService,
        db_session: AsyncSession,
    ):
        """Test that default retention period is 30 days."""
        # Create a 35-day old completed job
        job_35_days = ExtractionJob(
            id=str(uuid4()),
            filename="job_35_days.pdf",
            file_url="s3://bucket/job_35_days.pdf",
            file_size=1024,
            format=ExtractionJobFormat.PDF.value,
            status=ExtractionJobStatus.COMPLETED.value,
        )
        job_35_days.completed_at = datetime.now(timezone.utc) - timedelta(days=35)

        # Create a 25-day old completed job
        job_25_days = ExtractionJob(
            id=str(uuid4()),
            filename="job_25_days.pdf",
            file_url="s3://bucket/job_25_days.pdf",
            file_size=2048,
            format=ExtractionJobFormat.PDF.value,
            status=ExtractionJobStatus.COMPLETED.value,
        )
        job_25_days.completed_at = datetime.now(timezone.utc) - timedelta(days=25)

        db_session.add_all([job_35_days, job_25_days])
        await db_session.commit()

        # Call with default retention (should be 30 days)
        deleted_count = await extraction_job_service.delete_completed_jobs()

        # Should delete only 35-day job
        assert deleted_count == 1

        # Verify 35-day job is deleted
        with pytest.raises(NotFoundError):
            await extraction_job_service.get_job(job_35_days.id)

        # Verify 25-day job is preserved
        job = await extraction_job_service.get_job(job_25_days.id)
        assert job.id == job_25_days.id

    @pytest.mark.asyncio
    async def test_cleanup_multiple_jobs_same_age(
        self,
        extraction_job_service: ExtractionJobService,
        db_session: AsyncSession,
    ):
        """Test cleanup deletes multiple jobs of same age."""
        # Create 5 old completed jobs (all 60 days old)
        old_jobs = []
        for i in range(5):
            job = ExtractionJob(
                id=str(uuid4()),
                filename=f"old_job_{i}.pdf",
                file_url=f"s3://bucket/old_job_{i}.pdf",
                file_size=1024 * (i + 1),
                format=ExtractionJobFormat.PDF.value,
                status=ExtractionJobStatus.COMPLETED.value,
            )
            job.completed_at = datetime.now(timezone.utc) - timedelta(days=60)
            old_jobs.append(job)

        db_session.add_all(old_jobs)
        await db_session.commit()

        # Delete jobs older than 30 days
        deleted_count = await extraction_job_service.delete_completed_jobs(older_than_days=30)

        # Should delete all 5 jobs
        assert deleted_count == 5

        # Verify all jobs are deleted
        for job in old_jobs:
            with pytest.raises(NotFoundError):
                await extraction_job_service.get_job(job.id)

    @pytest.mark.asyncio
    async def test_cleanup_boundary_case_exactly_retention_days(
        self,
        extraction_job_service: ExtractionJobService,
        db_session: AsyncSession,
    ):
        """Test cleanup behavior when job age equals retention period."""
        # Create a job exactly 30 days old (boundary case)
        job_boundary = ExtractionJob(
            id=str(uuid4()),
            filename="boundary_job.pdf",
            file_url="s3://bucket/boundary_job.pdf",
            file_size=1024,
            format=ExtractionJobFormat.PDF.value,
            status=ExtractionJobStatus.COMPLETED.value,
        )
        job_boundary.completed_at = datetime.now(timezone.utc) - timedelta(days=30)

        db_session.add(job_boundary)
        await db_session.commit()

        # Delete jobs older than 30 days
        deleted_count = await extraction_job_service.delete_completed_jobs(older_than_days=30)

        # Boundary job should NOT be deleted (not older than 30 days)
        assert deleted_count == 0

        # Verify job still exists
        job = await extraction_job_service.get_job(job_boundary.id)
        assert job.id == job_boundary.id
