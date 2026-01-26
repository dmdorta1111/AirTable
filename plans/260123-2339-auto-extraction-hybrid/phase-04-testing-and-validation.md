# Phase 04: Testing and Validation

**Date**: 2026-01-23 | **Updated**: 2026-01-24
**Priority**: P2
**Status**: pending
**Estimated Effort**: 3h

---

## Context Links

- Existing test patterns: `tests/conftest.py`
- Extraction services: `src/pybase/services/extraction/*.py`
- Extraction API: `src/pybase/api/v1/extraction.py`

## Overview

Comprehensive testing for auto-extraction system. Unit tests for model/service/retry, integration tests for API endpoints, mocked extractors for fast execution.

## Test Structure

```
tests/
├── conftest.py                      # Existing, add extraction fixtures
└── extraction/
    ├── __init__.py
    ├── conftest.py                  # Extraction-specific fixtures
    ├── test_extraction_job_model.py # Model CRUD, status transitions
    ├── test_extraction_job_service.py # Service layer tests
    ├── test_retry_logic.py          # Backoff calculation, retry decisions
    ├── test_background.py           # Background task (mocked extractors)
    └── test_upload_api.py           # API integration tests
```

## Files to Create

### 1. Test Package Init (`tests/extraction/__init__.py`)

```python
"""Extraction tests package."""
```

### 2. Test Fixtures (`tests/extraction/conftest.py`)

```python
"""Extraction test fixtures."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus


@pytest.fixture
def sample_extraction_job_data():
    """Sample data for creating ExtractionJob."""
    return {
        "filename": "test_drawing.pdf",
        "file_url": "s3://bucket/test_drawing.pdf",
        "file_size": 1024000,
        "format": "pdf",
    }


@pytest_asyncio.fixture
async def extraction_job(db_session: AsyncSession, sample_extraction_job_data):
    """Create and return an ExtractionJob instance."""
    job = ExtractionJob(**sample_extraction_job_data)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def completed_extraction_job(db_session: AsyncSession, sample_extraction_job_data):
    """Create completed ExtractionJob."""
    job = ExtractionJob(
        **sample_extraction_job_data,
        status=ExtractionJobStatus.COMPLETED.value,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    job.set_result({"tables": [], "text": "extracted content"})
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def failed_extraction_job(db_session: AsyncSession, sample_extraction_job_data):
    """Create failed ExtractionJob."""
    job = ExtractionJob(
        **sample_extraction_job_data,
        status=ExtractionJobStatus.FAILED.value,
        error_message="Test error",
        retry_count=3,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest.fixture
def mock_pdf_extractor():
    """Mock PDFExtractor."""
    extractor = MagicMock()
    extractor.extract = AsyncMock(return_value={
        "tables": [{"headers": ["A", "B"], "rows": [["1", "2"]]}],
        "text_blocks": [{"text": "Sample text"}],
    })
    return extractor


@pytest.fixture
def mock_storage():
    """Mock S3/B2 storage."""
    storage = MagicMock()
    storage.upload = AsyncMock(return_value="s3://bucket/uploaded_file.pdf")
    storage.download = AsyncMock(return_value=b"file content")
    return storage
```

### 3. Model Tests (`tests/extraction/test_extraction_job_model.py`)

```python
"""Tests for ExtractionJob model."""

import json
import pytest
import pytest_asyncio
from datetime import datetime, timezone

from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus


class TestExtractionJobModel:
    """Test ExtractionJob ORM model."""
    
    @pytest_asyncio.fixture
    async def job(self, db_session, sample_extraction_job_data):
        """Create job for testing."""
        job = ExtractionJob(**sample_extraction_job_data)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        return job
    
    async def test_create_job(self, db_session, sample_extraction_job_data):
        """Test job creation with default values."""
        job = ExtractionJob(**sample_extraction_job_data)
        db_session.add(job)
        await db_session.commit()
        
        assert job.id is not None
        assert job.status == ExtractionJobStatus.PENDING.value
        assert job.retry_count == 0
        assert job.max_retries == 3
        assert job.created_at is not None
    
    async def test_status_enum_property(self, job):
        """Test status_enum property."""
        assert job.status_enum == ExtractionJobStatus.PENDING
        
        job.status = ExtractionJobStatus.PROCESSING.value
        assert job.status_enum == ExtractionJobStatus.PROCESSING
    
    async def test_options_json(self, job, db_session):
        """Test options getter/setter."""
        options = {"extract_tables": True, "use_ocr": False}
        job.set_options(options)
        await db_session.commit()
        
        assert job.get_options() == options
    
    async def test_result_json(self, job, db_session):
        """Test result getter/setter."""
        result = {"tables": [{"headers": ["A"]}], "success": True}
        job.set_result(result)
        await db_session.commit()
        
        assert job.get_result() == result
    
    async def test_status_transitions(self, job, db_session):
        """Test valid status transitions."""
        # pending -> processing
        job.status = ExtractionJobStatus.PROCESSING.value
        job.started_at = datetime.now(timezone.utc)
        await db_session.commit()
        
        assert job.status == "processing"
        assert job.started_at is not None
        
        # processing -> completed
        job.status = ExtractionJobStatus.COMPLETED.value
        job.completed_at = datetime.now(timezone.utc)
        await db_session.commit()
        
        assert job.status == "completed"
        assert job.completed_at is not None
    
    async def test_optional_record_linking(self, db_session, sample_extraction_job_data):
        """Test optional record_id, field_id, attachment_id."""
        data = {
            **sample_extraction_job_data,
            "record_id": "550e8400-e29b-41d4-a716-446655440000",
            "field_id": "660e8400-e29b-41d4-a716-446655440000",
            "attachment_id": "770e8400-e29b-41d4-a716-446655440000",
        }
        job = ExtractionJob(**data)
        db_session.add(job)
        await db_session.commit()
        
        assert job.record_id == data["record_id"]
        assert job.field_id == data["field_id"]
        assert job.attachment_id == data["attachment_id"]
```

### 4. Service Tests (`tests/extraction/test_extraction_job_service.py`)

```python
"""Tests for ExtractionJobService."""

import pytest
import pytest_asyncio
from datetime import datetime, timezone

from pybase.models.extraction_job import ExtractionJobStatus
from pybase.services.extraction_job_service import ExtractionJobService


class TestExtractionJobService:
    """Test ExtractionJobService methods."""
    
    async def test_create_job(self, db_session, sample_extraction_job_data):
        """Test job creation via service."""
        job = await ExtractionJobService.create_job(
            db_session,
            **sample_extraction_job_data,
            options={"extract_tables": True},
        )
        
        assert job.id is not None
        assert job.filename == sample_extraction_job_data["filename"]
        assert job.get_options() == {"extract_tables": True}
    
    async def test_get_job(self, db_session, extraction_job):
        """Test get job by ID."""
        found = await ExtractionJobService.get_job(db_session, extraction_job.id)
        assert found is not None
        assert found.id == extraction_job.id
    
    async def test_get_job_not_found(self, db_session):
        """Test get non-existent job."""
        found = await ExtractionJobService.get_job(
            db_session, "00000000-0000-0000-0000-000000000000"
        )
        assert found is None
    
    async def test_get_job_by_file_url(self, db_session, extraction_job):
        """Test get job by file URL."""
        found = await ExtractionJobService.get_job_by_file_url(
            db_session, extraction_job.file_url
        )
        assert found is not None
        assert found.id == extraction_job.id
    
    async def test_update_status_to_processing(self, db_session, extraction_job):
        """Test status update to processing."""
        updated = await ExtractionJobService.update_status(
            db_session,
            extraction_job.id,
            ExtractionJobStatus.PROCESSING,
        )
        
        assert updated.status == ExtractionJobStatus.PROCESSING.value
        assert updated.started_at is not None
    
    async def test_update_status_to_completed(self, db_session, extraction_job):
        """Test status update to completed with result."""
        result = {"tables": [], "success": True}
        updated = await ExtractionJobService.update_status(
            db_session,
            extraction_job.id,
            ExtractionJobStatus.COMPLETED,
            result=result,
        )
        
        assert updated.status == ExtractionJobStatus.COMPLETED.value
        assert updated.completed_at is not None
        assert updated.get_result() == result
    
    async def test_update_status_to_failed(self, db_session, extraction_job):
        """Test status update to failed with error."""
        updated = await ExtractionJobService.update_status(
            db_session,
            extraction_job.id,
            ExtractionJobStatus.FAILED,
            error_message="Test error occurred",
        )
        
        assert updated.status == ExtractionJobStatus.FAILED.value
        assert updated.error_message == "Test error occurred"
    
    async def test_list_jobs_no_filter(self, db_session, extraction_job, completed_extraction_job):
        """Test listing jobs without filter."""
        jobs = await ExtractionJobService.list_jobs(db_session)
        assert len(jobs) >= 2
    
    async def test_list_jobs_with_status_filter(self, db_session, extraction_job, completed_extraction_job):
        """Test listing jobs with status filter."""
        pending_jobs = await ExtractionJobService.list_jobs(
            db_session, status=ExtractionJobStatus.PENDING
        )
        
        assert all(j.status == "pending" for j in pending_jobs)
```

### 5. Retry Tests (`tests/extraction/test_retry_logic.py`)

```python
"""Tests for retry logic."""

import pytest
from datetime import datetime, timedelta, timezone

from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus
from pybase.services.extraction.retry import (
    is_retryable_error,
    calculate_next_retry,
    should_retry,
    prepare_for_retry,
    BASE_DELAY_SECONDS,
    DELAY_MULTIPLIER,
)


class TestRetryLogic:
    """Test retry decision and backoff calculation."""
    
    def test_is_retryable_connection_error(self):
        """Test ConnectionError is retryable."""
        assert is_retryable_error("ConnectionError") is True
        assert is_retryable_error(ConnectionError("failed")) is True
    
    def test_is_permanent_corrupted_file(self):
        """Test CorruptedFile is permanent."""
        assert is_retryable_error("CorruptedFile") is False
    
    def test_unknown_error_defaults_retryable(self):
        """Test unknown errors default to retryable."""
        assert is_retryable_error("SomeUnknownError") is True
    
    def test_calculate_backoff_first_retry(self):
        """Test first retry delay (30s)."""
        next_time = calculate_next_retry(0, jitter=False)
        expected = datetime.now(timezone.utc) + timedelta(seconds=BASE_DELAY_SECONDS)
        
        # Allow 1 second tolerance
        assert abs((next_time - expected).total_seconds()) < 1
    
    def test_calculate_backoff_second_retry(self):
        """Test second retry delay (120s)."""
        next_time = calculate_next_retry(1, jitter=False)
        expected_delay = BASE_DELAY_SECONDS * DELAY_MULTIPLIER  # 30 * 4 = 120
        expected = datetime.now(timezone.utc) + timedelta(seconds=expected_delay)
        
        assert abs((next_time - expected).total_seconds()) < 1
    
    def test_calculate_backoff_with_jitter(self):
        """Test jitter adds randomness."""
        times = [calculate_next_retry(0, jitter=True) for _ in range(10)]
        # Not all times should be exactly equal (jitter adds variance)
        unique_times = len(set(t.isoformat() for t in times))
        assert unique_times > 1
    
    def test_should_retry_under_max(self):
        """Test should_retry when under max retries."""
        job = ExtractionJob(
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
            retry_count=1,
            max_retries=3,
        )
        assert should_retry(job) is True
    
    def test_should_retry_at_max(self):
        """Test should_retry when at max retries."""
        job = ExtractionJob(
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
            retry_count=3,
            max_retries=3,
        )
        assert should_retry(job) is False
    
    def test_prepare_for_retry_retryable_error(self):
        """Test prepare_for_retry with retryable error."""
        job = ExtractionJob(
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
            retry_count=0,
            max_retries=3,
        )
        
        prepare_for_retry(job, "ConnectionError")
        
        assert job.retry_count == 1
        assert job.status == ExtractionJobStatus.PENDING.value
        assert job.next_retry_at is not None
    
    def test_prepare_for_retry_permanent_error(self):
        """Test prepare_for_retry with permanent error."""
        job = ExtractionJob(
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
            retry_count=0,
            max_retries=3,
        )
        
        prepare_for_retry(job, "CorruptedFile")
        
        assert job.status == ExtractionJobStatus.FAILED.value
        assert "Permanent error" in job.error_message
    
    def test_prepare_for_retry_max_exceeded(self):
        """Test prepare_for_retry when max retries exceeded."""
        job = ExtractionJob(
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
            retry_count=3,
            max_retries=3,
        )
        
        prepare_for_retry(job, "ConnectionError")
        
        assert job.status == ExtractionJobStatus.FAILED.value
        assert "Max retries" in job.error_message
```

### 6. API Tests (`tests/extraction/test_upload_api.py`)

```python
"""Tests for extraction upload API."""

import pytest
from io import BytesIO
from unittest.mock import patch, AsyncMock

from fastapi import status
from httpx import AsyncClient


class TestUploadAPI:
    """Test extraction upload endpoint."""
    
    @pytest.fixture
    def pdf_file(self):
        """Create fake PDF file."""
        content = b"%PDF-1.4 fake pdf content"
        return ("test.pdf", BytesIO(content), "application/pdf")
    
    @pytest.mark.asyncio
    async def test_upload_returns_202(self, client: AsyncClient, pdf_file, auth_headers):
        """Test upload returns 202 Accepted."""
        with patch("pybase.api.v1.extraction.save_to_storage", new_callable=AsyncMock) as mock_storage:
            mock_storage.return_value = "s3://bucket/test.pdf"
            
            response = await client.post(
                "/api/v1/extraction/upload",
                files={"file": pdf_file},
                headers=auth_headers,
            )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
        assert data["filename"] == "test.pdf"
    
    @pytest.mark.asyncio
    async def test_upload_unsupported_format(self, client: AsyncClient, auth_headers):
        """Test upload rejects unsupported format."""
        file = ("test.txt", BytesIO(b"text content"), "text/plain")
        
        response = await client.post(
            "/api/v1/extraction/upload",
            files={"file": file},
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported file type" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_upload_requires_auth(self, client: AsyncClient, pdf_file):
        """Test upload requires authentication."""
        response = await client.post(
            "/api/v1/extraction/upload",
            files={"file": pdf_file},
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestJobStatusAPI:
    """Test job status endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_job_status(self, client: AsyncClient, extraction_job, auth_headers):
        """Test getting job status."""
        response = await client.get(
            f"/api/v1/extraction/jobs/{extraction_job.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == extraction_job.id
        assert data["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_get_job_not_found(self, client: AsyncClient, auth_headers):
        """Test 404 for non-existent job."""
        response = await client.get(
            "/api/v1/extraction/jobs/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCancelJobAPI:
    """Test job cancellation endpoint."""
    
    @pytest.mark.asyncio
    async def test_cancel_pending_job(self, client: AsyncClient, extraction_job, auth_headers, db_session):
        """Test cancelling pending job."""
        response = await client.delete(
            f"/api/v1/extraction/jobs/{extraction_job.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify job is cancelled
        await db_session.refresh(extraction_job)
        assert extraction_job.status == "cancelled"
    
    @pytest.mark.asyncio
    async def test_cancel_completed_job_fails(self, client: AsyncClient, completed_extraction_job, auth_headers):
        """Test cannot cancel completed job."""
        response = await client.delete(
            f"/api/v1/extraction/jobs/{completed_extraction_job.id}",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
```

## Todo Checklist

- [ ] Create `tests/extraction/__init__.py`
- [ ] Create `tests/extraction/conftest.py`
- [ ] Create `tests/extraction/test_extraction_job_model.py`
- [ ] Create `tests/extraction/test_extraction_job_service.py`
- [ ] Create `tests/extraction/test_retry_logic.py`
- [ ] Create `tests/extraction/test_upload_api.py`
- [ ] Run test suite: `pytest tests/extraction/ -v`
- [ ] Verify coverage: `pytest tests/extraction/ --cov=pybase.services.extraction --cov=pybase.models.extraction_job`
- [ ] Fix any failing tests
- [ ] Verify existing tests still pass

## Success Criteria

- [ ] All tests pass
- [ ] Coverage >80% for new code
- [ ] Test execution <2 minutes
- [ ] No regressions in existing tests

## Agent Assignment

| Category | Skills | Rationale |
|----------|--------|-----------|
| `fullstack-developer` | `backend-development`, `Debugging` | pytest async, mocking, FastAPI TestClient |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Async test complexity | Medium | Medium | Use pytest-asyncio patterns |
| Mock leakage | Low | Low | Proper fixture scoping |
| Slow tests | Low | Medium | Mock heavy operations |

## Next Steps

- Complete Phase 04
- All phases complete
- Deploy to staging for validation
- Monitor first extractions in production
