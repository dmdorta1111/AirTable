"""
Tests for Extraction API endpoints.

Tests the extraction job API endpoints including:
- POST /jobs - Create extraction job
- GET /jobs/{job_id} - Get job status
- GET /jobs - List jobs
- DELETE /jobs/{job_id} - Cancel/delete job
- POST /jobs/{job_id}/retry - Retry failed job
- GET /jobs/stats - Get job statistics
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.config import settings
from pybase.models.extraction_job import (
    ExtractionJob,
    ExtractionJobFormat,
    ExtractionJobStatus,
)


class TestExtractionJobEndpoints:
    """Tests for extraction job API endpoints."""

    @pytest.mark.asyncio
    async def test_get_job_status(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_extraction_job: ExtractionJob,
    ):
        """Test getting job status."""
        response = await client.get(
            f"{settings.api_v1_prefix}/extraction/jobs/{sample_extraction_job.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_extraction_job.id
        assert data["status"] == "pending"
        assert data["filename"] == sample_extraction_job.filename

    @pytest.mark.asyncio
    async def test_get_job_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test getting non-existent job returns 404."""
        response = await client.get(
            f"{settings.api_v1_prefix}/extraction/jobs/{uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_jobs_empty(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test listing jobs when none exist."""
        response = await client.get(
            f"{settings.api_v1_prefix}/extraction/jobs",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_jobs_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        multiple_extraction_jobs: list[ExtractionJob],
    ):
        """Test listing jobs with data."""
        response = await client.get(
            f"{settings.api_v1_prefix}/extraction/jobs",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == len(multiple_extraction_jobs)

    @pytest.mark.asyncio
    async def test_list_jobs_filter_by_status(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        multiple_extraction_jobs: list[ExtractionJob],
    ):
        """Test filtering jobs by status."""
        response = await client.get(
            f"{settings.api_v1_prefix}/extraction/jobs",
            params={"status": "pending"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3  # 3 pending jobs in fixture
        for item in data["items"]:
            assert item["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_jobs_pagination(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        multiple_extraction_jobs: list[ExtractionJob],
    ):
        """Test job listing pagination."""
        response = await client.get(
            f"{settings.api_v1_prefix}/extraction/jobs",
            params={"page": 1, "page_size": 3},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["page_size"] == 3

    @pytest.mark.asyncio
    async def test_delete_pending_job(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_extraction_job: ExtractionJob,
    ):
        """Test deleting a pending job."""
        response = await client.delete(
            f"{settings.api_v1_prefix}/extraction/jobs/{sample_extraction_job.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify job is deleted
        get_response = await client.get(
            f"{settings.api_v1_prefix}/extraction/jobs/{sample_extraction_job.id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_job_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test deleting non-existent job returns 404."""
        response = await client.delete(
            f"{settings.api_v1_prefix}/extraction/jobs/{uuid4()}",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestRetryEndpoint:
    """Tests for POST /jobs/{job_id}/retry endpoint."""

    @pytest.mark.asyncio
    async def test_retry_failed_job(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        failed_extraction_job: ExtractionJob,
    ):
        """Test retrying a failed job."""
        response = await client.post(
            f"{settings.api_v1_prefix}/extraction/jobs/{failed_extraction_job.id}/retry",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["id"] == failed_extraction_job.id

    @pytest.mark.asyncio
    async def test_retry_non_failed_job(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        sample_extraction_job: ExtractionJob,
    ):
        """Test retrying a non-failed job returns 400."""
        response = await client.post(
            f"{settings.api_v1_prefix}/extraction/jobs/{sample_extraction_job.id}/retry",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "not in failed state" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_retry_exhausted_job(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        exhausted_extraction_job: ExtractionJob,
    ):
        """Test retrying a job that has exhausted retries returns 400."""
        response = await client.post(
            f"{settings.api_v1_prefix}/extraction/jobs/{exhausted_extraction_job.id}/retry",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "exhausted" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_retry_job_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test retrying non-existent job returns 404."""
        response = await client.post(
            f"{settings.api_v1_prefix}/extraction/jobs/{uuid4()}/retry",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestStatsEndpoint:
    """Tests for GET /jobs/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ):
        """Test getting stats when no jobs exist."""
        response = await client.get(
            f"{settings.api_v1_prefix}/extraction/jobs/stats",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pending"] == 0
        assert data["processing"] == 0
        assert data["completed"] == 0
        assert data["failed"] == 0
        assert data["cancelled"] == 0
        assert data["retryable"] == 0
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_data(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        multiple_extraction_jobs: list[ExtractionJob],
    ):
        """Test getting stats with various job statuses."""
        response = await client.get(
            f"{settings.api_v1_prefix}/extraction/jobs/stats",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pending"] == 3
        assert data["processing"] == 1
        assert data["completed"] == 2
        assert data["failed"] == 1
        assert data["cancelled"] == 1
        assert data["retryable"] == 1  # 1 failed job with retries remaining
        assert data["total"] == 8


class TestUnauthorizedAccess:
    """Tests for unauthorized access to endpoints."""

    @pytest.mark.asyncio
    async def test_get_job_unauthorized(
        self,
        client: AsyncClient,
        sample_extraction_job: ExtractionJob,
    ):
        """Test getting job without auth returns 401."""
        response = await client.get(
            f"{settings.api_v1_prefix}/extraction/jobs/{sample_extraction_job.id}",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_jobs_unauthorized(
        self,
        client: AsyncClient,
    ):
        """Test listing jobs without auth returns 401."""
        response = await client.get(
            f"{settings.api_v1_prefix}/extraction/jobs",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_retry_job_unauthorized(
        self,
        client: AsyncClient,
        failed_extraction_job: ExtractionJob,
    ):
        """Test retrying job without auth returns 401."""
        response = await client.post(
            f"{settings.api_v1_prefix}/extraction/jobs/{failed_extraction_job.id}/retry",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_stats_unauthorized(
        self,
        client: AsyncClient,
    ):
        """Test getting stats without auth returns 401."""
        response = await client.get(
            f"{settings.api_v1_prefix}/extraction/jobs/stats",
        )

        assert response.status_code == 401
