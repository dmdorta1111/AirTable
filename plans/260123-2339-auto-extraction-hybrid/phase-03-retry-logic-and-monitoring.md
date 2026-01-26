# Phase 03: Retry Logic and Monitoring

**Date**: 2026-01-23 | **Updated**: 2026-01-24
**Priority**: P2
**Status**: pending
**Estimated Effort**: 3h

---

## Context Links

- ExtractionJob model: `src/pybase/models/extraction_job.py`
- Job service: `src/pybase/services/extraction_job_service.py`
- Background extraction: `src/pybase/services/extraction/background.py`

## Overview

Implement exponential backoff retry for failed extractions and monitoring endpoints for job tracking.

## Retry Strategy

```
Backoff Formula: delay = base * (multiplier ^ retry_count)
- Base: 30 seconds
- Multiplier: 4
- Max retries: 3

Retry 1: 30s wait  (after 1st failure)
Retry 2: 120s wait (after 2nd failure)  
Retry 3: 480s wait (after 3rd failure)
Total:   ~11 minutes max wait

After 3 failures -> permanently FAILED
```

## Retryable vs Permanent Errors

```python
RETRYABLE_ERRORS = [
    "ConnectionError",
    "TimeoutError", 
    "ServiceUnavailable",
    "RateLimitExceeded",
    "TemporaryFailure",
    "S3ConnectionError",
]

PERMANENT_ERRORS = [
    "UnsupportedFormat",
    "CorruptedFile",
    "InvalidFileType",
    "AuthenticationFailed",
    "PermissionDenied",
]
```

## Files to Create

### Retry Logic (`src/pybase/services/extraction/retry.py`)

```python
"""Retry logic for extraction jobs."""

import random
from datetime import datetime, timedelta, timezone

from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus


# Retry configuration
BASE_DELAY_SECONDS = 30
DELAY_MULTIPLIER = 4
MAX_RETRIES = 3

# Error classification
RETRYABLE_ERRORS = {
    "ConnectionError",
    "TimeoutError",
    "ServiceUnavailable", 
    "RateLimitExceeded",
    "TemporaryFailure",
    "S3ConnectionError",
    "Werk24Timeout",
}

PERMANENT_ERRORS = {
    "UnsupportedFormat",
    "CorruptedFile",
    "InvalidFileType",
    "AuthenticationFailed",
    "PermissionDenied",
    "FileTooLarge",
}


def is_retryable_error(error: Exception | str) -> bool:
    """Check if error is retryable."""
    error_type = type(error).__name__ if isinstance(error, Exception) else str(error)
    
    # Check if explicitly retryable
    for retryable in RETRYABLE_ERRORS:
        if retryable.lower() in error_type.lower():
            return True
    
    # Check if explicitly permanent
    for permanent in PERMANENT_ERRORS:
        if permanent.lower() in error_type.lower():
            return False
    
    # Default: retry unknown errors
    return True


def calculate_next_retry(retry_count: int, jitter: bool = True) -> datetime:
    """
    Calculate next retry time with exponential backoff.
    
    Args:
        retry_count: Current retry count (0-based)
        jitter: Add random jitter to prevent thundering herd
    
    Returns:
        datetime when job should be retried
    """
    delay_seconds = BASE_DELAY_SECONDS * (DELAY_MULTIPLIER ** retry_count)
    
    if jitter:
        # Add 0-25% random jitter
        jitter_seconds = random.uniform(0, delay_seconds * 0.25)
        delay_seconds += jitter_seconds
    
    return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)


def should_retry(job: ExtractionJob) -> bool:
    """Check if job should be retried."""
    return job.retry_count < job.max_retries


def prepare_for_retry(job: ExtractionJob, error: Exception | str) -> ExtractionJob:
    """
    Prepare job for retry.
    
    Updates retry_count, next_retry_at, and resets status to pending.
    Does NOT commit to DB - caller must commit.
    """
    if not is_retryable_error(error):
        # Mark as permanently failed
        job.status = ExtractionJobStatus.FAILED.value
        job.error_message = f"Permanent error: {error}"
        return job
    
    if not should_retry(job):
        # Max retries exceeded
        job.status = ExtractionJobStatus.FAILED.value
        job.error_message = f"Max retries ({job.max_retries}) exceeded. Last error: {error}"
        return job
    
    # Schedule retry
    job.retry_count += 1
    job.next_retry_at = calculate_next_retry(job.retry_count - 1)
    job.status = ExtractionJobStatus.PENDING.value
    job.error_message = f"Retry {job.retry_count}/{job.max_retries}: {error}"
    
    return job


def mark_permanently_failed(job: ExtractionJob, error: str) -> ExtractionJob:
    """Mark job as permanently failed (no more retries)."""
    job.status = ExtractionJobStatus.FAILED.value
    job.error_message = error
    job.completed_at = datetime.now(timezone.utc)
    return job
```

## Files to Modify

### 1. Background Extraction (`src/pybase/services/extraction/background.py`)

Add retry handling to the extraction task:

```python
# Add import
from pybase.services.extraction.retry import (
    is_retryable_error,
    prepare_for_retry,
    mark_permanently_failed,
)

# Update extract_file_background()
async def extract_file_background(job_id: str, database_url: str) -> None:
    """Background task with retry handling."""
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            job = await ExtractionJobService.get_job(db, job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            
            # Update to processing
            job.status = ExtractionJobStatus.PROCESSING.value
            job.started_at = datetime.now(timezone.utc)
            await db.commit()
            
            # Run extraction
            result = await _run_extraction(job)
            
            # Success
            job.status = ExtractionJobStatus.COMPLETED.value
            job.completed_at = datetime.now(timezone.utc)
            job.set_result(result)
            await db.commit()
            
            logger.info(f"Extraction completed: {job_id}")
            
        except Exception as e:
            logger.error(f"Extraction failed for {job_id}: {e}")
            
            # Refresh job from DB
            await db.refresh(job)
            
            # Apply retry logic
            prepare_for_retry(job, e)
            await db.commit()
            
            if job.status == ExtractionJobStatus.PENDING.value:
                logger.info(f"Job {job_id} scheduled for retry {job.retry_count} at {job.next_retry_at}")
            else:
                logger.error(f"Job {job_id} permanently failed: {job.error_message}")
    
    await engine.dispose()
```

### 2. Extraction API (`src/pybase/api/v1/extraction.py`)

Add monitoring endpoints:

```python
# GET /extraction/jobs/{job_id}
@router.get(
    "/jobs/{job_id}",
    response_model=ExtractionJobResponse,
    summary="Get job status",
    tags=["Monitoring"],
)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExtractionJobResponse:
    """Get extraction job status and result."""
    job = await ExtractionJobService.get_job(db, str(job_id))
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    
    return ExtractionJobResponse(
        id=job.id,
        status=JobStatus(job.status),
        format=ExtractionFormat(job.format),
        filename=job.filename,
        file_size=job.file_size,
        options=job.get_options(),
        result=job.get_result() if job.status == "completed" else None,
        error_message=job.error_message,
        progress=100 if job.status == "completed" else 50 if job.status == "processing" else 0,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


# GET /extraction/jobs
@router.get(
    "/jobs",
    response_model=ExtractionJobListResponse,
    summary="List jobs",
    tags=["Monitoring"],
)
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: JobStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ExtractionJobListResponse:
    """List extraction jobs with optional status filter."""
    offset = (page - 1) * page_size
    
    status_enum = ExtractionJobStatus(status.value) if status else None
    jobs = await ExtractionJobService.list_jobs(db, status_enum, page_size, offset)
    
    # TODO: Add total count query
    return ExtractionJobListResponse(
        items=[
            ExtractionJobResponse(
                id=j.id,
                status=JobStatus(j.status),
                format=ExtractionFormat(j.format),
                filename=j.filename,
                file_size=j.file_size,
                options=j.get_options(),
                progress=100 if j.status == "completed" else 0,
                created_at=j.created_at,
            )
            for j in jobs
        ],
        total=len(jobs),  # TODO: Real count
        page=page,
        page_size=page_size,
    )


# DELETE /extraction/jobs/{job_id}
@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel job",
    tags=["Monitoring"],
)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Cancel pending extraction job."""
    job = await ExtractionJobService.get_job(db, str(job_id))
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    
    if job.status not in (ExtractionJobStatus.PENDING.value,):
        raise HTTPException(400, f"Cannot cancel job with status: {job.status}")
    
    job.status = ExtractionJobStatus.CANCELLED.value
    await db.commit()


# POST /extraction/jobs/{job_id}/retry
@router.post(
    "/jobs/{job_id}/retry",
    response_model=ExtractionJobResponse,
    summary="Manual retry",
    tags=["Monitoring"],
)
async def retry_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExtractionJobResponse:
    """Manually retry a failed extraction job."""
    job = await ExtractionJobService.get_job(db, str(job_id))
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    
    if job.status != ExtractionJobStatus.FAILED.value:
        raise HTTPException(400, f"Can only retry failed jobs, current: {job.status}")
    
    # Reset for retry
    job.status = ExtractionJobStatus.PENDING.value
    job.retry_count = 0
    job.next_retry_at = None
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    await db.commit()
    
    # Trigger extraction
    background_tasks.add_task(
        extract_file_background,
        job.id,
        str(settings.DATABASE_URL),
    )
    
    return ExtractionJobResponse(
        id=job.id,
        status=JobStatus.PENDING,
        format=ExtractionFormat(job.format),
        filename=job.filename,
        file_size=job.file_size,
        options=job.get_options(),
        progress=0,
        created_at=job.created_at,
    )
```

## Optional: Retry Scheduler

Add lifespan task to check and trigger retries:

```python
# src/pybase/main.py (in lifespan)
from contextlib import asynccontextmanager
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start retry checker task
    retry_task = asyncio.create_task(retry_checker_loop())
    yield
    # Cleanup
    retry_task.cancel()

async def retry_checker_loop():
    """Check for retryable jobs every 30 seconds."""
    while True:
        await asyncio.sleep(30)
        try:
            async with get_db() as db:
                jobs = await ExtractionJobService.get_retryable_jobs(db)
                for job in jobs:
                    # Trigger extraction (simplified - need BackgroundTasks alternative)
                    asyncio.create_task(
                        extract_file_background(job.id, str(settings.DATABASE_URL))
                    )
        except Exception as e:
            logger.error(f"Retry checker error: {e}")
```

## Todo Checklist

- [ ] Create `src/pybase/services/extraction/retry.py`
- [ ] Update `background.py` with retry handling
- [ ] Add `GET /extraction/jobs/{job_id}` endpoint
- [ ] Add `GET /extraction/jobs` list endpoint
- [ ] Add `DELETE /extraction/jobs/{job_id}` cancel endpoint
- [ ] Add `POST /extraction/jobs/{job_id}/retry` manual retry
- [ ] (Optional) Add retry scheduler in lifespan

## Success Criteria

- [ ] Failed jobs auto-retry with exponential backoff
- [ ] Max 3 retries, then permanent failure
- [ ] Retryable vs permanent errors classified correctly
- [ ] All monitoring endpoints return correct data
- [ ] Users can cancel pending jobs
- [ ] Users can manually retry failed jobs

## Agent Assignment

| Category | Skills | Rationale |
|----------|--------|-----------|
| `fullstack-developer` | `backend-development` | Error handling, FastAPI, async patterns |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Retry flood | Low | Medium | Jitter in backoff, max retries cap |
| Infinite retry | Low | High | Mandatory max_retries check |
| Scheduler leak | Medium | Medium | Proper cancellation in lifespan |

## Next Steps

- Complete Phase 03
- Proceed to [Phase 04: Testing and Validation](./phase-04-testing-and-validation.md)
