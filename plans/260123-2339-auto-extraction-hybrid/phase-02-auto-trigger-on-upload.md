# Phase 02: Auto-Trigger Extraction on Upload

**Date**: 2026-01-23 | **Updated**: 2026-01-24
**Priority**: P1
**Status**: pending
**Estimated Effort**: 4h

---

## Context Links

- ExtractionJob model: `src/pybase/models/extraction_job.py` (from Phase 01)
- Existing extraction API: `src/pybase/api/v1/extraction.py`
- In-memory jobs: Line 1465 `_jobs: dict[str, Any] = {}`

## Overview

Implement auto-extraction on file upload using FastAPI BackgroundTasks. Create service layer for ExtractionJob CRUD and background extraction task.

## Key Clarification

> **No CloudFile changes needed**. ExtractionJob tracks file via `file_url`.
> Background task creates new DB session (required for async background tasks).

## Architecture

```
POST /extraction/upload
         │
         v
┌─────────────────────────────────┐
│ 1. Validate file type           │
│ 2. Save to S3/B2                │
│ 3. Create ExtractionJob (DB)   │
│ 4. Add BackgroundTask           │
│ 5. Return 202 + job_id          │
└─────────────────────────────────┘
         │
         v (background, after response)
┌─────────────────────────────────┐
│ BackgroundTask:                 │
│ 1. Create new DB session        │
│ 2. Update job -> processing     │
│ 3. Detect format, run extractor │
│ 4. Update job -> completed/fail │
└─────────────────────────────────┘
```

## Files to Create

### 1. ExtractionJobService (`src/pybase/services/extraction_job_service.py`)

```python
"""Service for ExtractionJob CRUD operations."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus


class ExtractionJobService:
    """Service for managing extraction jobs."""
    
    @staticmethod
    async def create_job(
        db: AsyncSession,
        filename: str,
        file_url: str,
        file_size: int,
        format: str,
        options: dict | None = None,
        record_id: str | None = None,
        field_id: str | None = None,
        attachment_id: str | None = None,
    ) -> ExtractionJob:
        """Create new extraction job."""
        job = ExtractionJob(
            filename=filename,
            file_url=file_url,
            file_size=file_size,
            format=format,
            record_id=record_id,
            field_id=field_id,
            attachment_id=attachment_id,
        )
        if options:
            job.set_options(options)
        
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job
    
    @staticmethod
    async def get_job(db: AsyncSession, job_id: str | UUID) -> ExtractionJob | None:
        """Get job by ID."""
        result = await db.execute(
            select(ExtractionJob).where(ExtractionJob.id == str(job_id))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_job_by_file_url(db: AsyncSession, file_url: str) -> ExtractionJob | None:
        """Get most recent job for file URL."""
        result = await db.execute(
            select(ExtractionJob)
            .where(ExtractionJob.file_url == file_url)
            .order_by(ExtractionJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_status(
        db: AsyncSession,
        job_id: str | UUID,
        status: ExtractionJobStatus,
        result: dict | None = None,
        error_message: str | None = None,
    ) -> ExtractionJob | None:
        """Update job status and optionally result/error."""
        job = await ExtractionJobService.get_job(db, job_id)
        if not job:
            return None
        
        job.status = status.value
        
        if status == ExtractionJobStatus.PROCESSING:
            job.started_at = datetime.now(timezone.utc)
        elif status in (ExtractionJobStatus.COMPLETED, ExtractionJobStatus.FAILED):
            job.completed_at = datetime.now(timezone.utc)
        
        if result is not None:
            job.set_result(result)
        if error_message is not None:
            job.error_message = error_message
        
        await db.commit()
        await db.refresh(job)
        return job
    
    @staticmethod
    async def list_jobs(
        db: AsyncSession,
        status: ExtractionJobStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ExtractionJob]:
        """List jobs with optional status filter."""
        query = select(ExtractionJob).order_by(ExtractionJob.created_at.desc())
        if status:
            query = query.where(ExtractionJob.status == status.value)
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_retryable_jobs(db: AsyncSession) -> list[ExtractionJob]:
        """Get jobs ready for retry (failed + next_retry_at < now)."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(ExtractionJob)
            .where(
                ExtractionJob.status == ExtractionJobStatus.PENDING.value,
                ExtractionJob.retry_count > 0,
                ExtractionJob.next_retry_at <= now,
            )
            .order_by(ExtractionJob.next_retry_at)
        )
        return list(result.scalars().all())
```

### 2. Background Extraction (`src/pybase/services/extraction/background.py`)

```python
"""Background task for file extraction."""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from pybase.core.config import settings
from pybase.models.extraction_job import ExtractionJobStatus
from pybase.services.extraction_job_service import ExtractionJobService

logger = logging.getLogger(__name__)

# Format detection mapping
FORMAT_EXTENSIONS = {
    ".pdf": "pdf",
    ".dxf": "dxf",
    ".dwg": "dxf",  # Treat DWG as DXF
    ".ifc": "ifc",
    ".stp": "step",
    ".step": "step",
}


def detect_format(filename: str) -> str | None:
    """Detect extraction format from filename extension."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return FORMAT_EXTENSIONS.get(ext)


async def extract_file_background(job_id: str, database_url: str) -> None:
    """
    Background task to extract file.
    
    Creates own DB session because BackgroundTasks run after response.
    """
    # Create new session for background task
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # Get job
            job = await ExtractionJobService.get_job(db, job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            
            # Update to processing
            await ExtractionJobService.update_status(
                db, job_id, ExtractionJobStatus.PROCESSING
            )
            
            # Run extraction based on format
            result = await _run_extraction(job)
            
            # Update to completed
            await ExtractionJobService.update_status(
                db, job_id, ExtractionJobStatus.COMPLETED, result=result
            )
            
            logger.info(f"Extraction completed: {job_id}")
            
        except Exception as e:
            logger.error(f"Extraction failed for {job_id}: {e}")
            await ExtractionJobService.update_status(
                db, job_id, ExtractionJobStatus.FAILED, error_message=str(e)
            )
    
    await engine.dispose()


async def _run_extraction(job) -> dict[str, Any]:
    """Run extraction based on job format."""
    from pybase.extraction.pdf import PDFExtractor
    from pybase.extraction.cad.dxf_parser import DXFParser
    from pybase.extraction.cad.ifc_parser import IFCParser
    from pybase.extraction.cad.step_parser import STEPParser
    
    options = job.get_options()
    
    # Download file from S3 to temp location
    # TODO: Implement file download from job.file_url
    temp_path = f"/tmp/{job.filename}"  # Placeholder
    
    if job.format == "pdf":
        extractor = PDFExtractor()
        result = await extractor.extract(temp_path, **options)
    elif job.format == "dxf":
        parser = DXFParser()
        result = parser.parse(temp_path)
    elif job.format == "ifc":
        parser = IFCParser()
        result = parser.parse(temp_path)
    elif job.format == "step":
        parser = STEPParser()
        result = parser.parse(temp_path)
    elif job.format == "werk24":
        # Werk24 API call
        from pybase.extraction.werk24 import Werk24Client
        client = Werk24Client()
        result = await client.extract(temp_path, **options)
    else:
        raise ValueError(f"Unsupported format: {job.format}")
    
    return result if isinstance(result, dict) else result.model_dump()
```

## Files to Modify

### 1. Extraction API (`src/pybase/api/v1/extraction.py`)

Add upload endpoint and migrate from `_jobs` dict:

```python
# Add at top of file
from pybase.services.extraction_job_service import ExtractionJobService
from pybase.services.extraction.background import extract_file_background, detect_format
from pybase.core.config import settings

# Add new endpoint
@router.post(
    "/upload",
    response_model=ExtractionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload file and trigger extraction",
    tags=["Auto-Extraction"],
)
async def upload_and_extract(
    file: Annotated[UploadFile, File(description="File to extract")],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    record_id: Annotated[str | None, Form()] = None,
    field_id: Annotated[str | None, Form()] = None,
    attachment_id: Annotated[str | None, Form()] = None,
    options: Annotated[str | None, Form(description="JSON options")] = None,
) -> ExtractionJobResponse:
    """
    Upload file and automatically trigger extraction.
    
    Returns 202 with job_id. Poll GET /jobs/{job_id} for status.
    """
    # Detect format
    format = detect_format(file.filename)
    if not format:
        raise HTTPException(400, f"Unsupported file type: {file.filename}")
    
    # Save file to S3/B2
    file_content = await file.read()
    file_url = await save_to_storage(file.filename, file_content)  # TODO: implement
    
    # Parse options
    parsed_options = json.loads(options) if options else {}
    
    # Create job
    job = await ExtractionJobService.create_job(
        db=db,
        filename=file.filename,
        file_url=file_url,
        file_size=len(file_content),
        format=format,
        options=parsed_options,
        record_id=record_id,
        field_id=field_id,
        attachment_id=attachment_id,
    )
    
    # Add background task
    background_tasks.add_task(
        extract_file_background,
        job.id,
        str(settings.DATABASE_URL),
    )
    
    return ExtractionJobResponse(
        id=job.id,
        status=JobStatus(job.status),
        format=ExtractionFormat(job.format),
        filename=job.filename,
        file_size=job.file_size,
        options=job.get_options(),
        progress=0,
        created_at=job.created_at,
    )
```

### 2. Migrate Existing Endpoints

Replace `_jobs` dict usage in existing endpoints with `ExtractionJobService` calls:

```python
# Old:
_jobs[job_id] = {...}
job = _jobs.get(job_id)

# New:
job = await ExtractionJobService.create_job(db, ...)
job = await ExtractionJobService.get_job(db, job_id)
```

## Todo Checklist

- [ ] Create `src/pybase/services/extraction_job_service.py`
- [ ] Create `src/pybase/services/extraction/background.py`
- [ ] Add `POST /extraction/upload` endpoint
- [ ] Replace `_jobs` dict with DB queries in existing endpoints
- [ ] Implement `save_to_storage()` helper (or use existing)
- [ ] Test upload -> background extraction flow
- [ ] Verify job status updates correctly

## Success Criteria

- [ ] `POST /extraction/upload` returns 202 with job_id
- [ ] ExtractionJob created in DB with status=pending
- [ ] Background task starts after response sent
- [ ] Job status updates: pending -> processing -> completed/failed
- [ ] Result stored in ExtractionJob.result
- [ ] All 4 formats work (PDF, DXF, IFC, STEP)

## Agent Assignment

| Category | Skills | Rationale |
|----------|--------|-----------|
| `fullstack-developer` | `backend-development`, `databases` | FastAPI, BackgroundTasks, async SQLAlchemy |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Background task silent failure | Medium | High | Wrap in try/except, update job.error_message |
| DB session issues in background | Medium | High | Create new session per background task |
| Duplicate jobs for same file | Low | Medium | Check existing job by file_url before creating |

## Unresolved Questions

1. **Storage integration**: Where's the existing file upload to S3/B2?
2. **File download**: How to download file from S3 for extraction?
3. **Duplicate handling**: Block or allow multiple extractions for same file?

## Next Steps

- Complete Phase 02
- Proceed to [Phase 03: Retry Logic and Monitoring](./phase-03-retry-logic-and-monitoring.md)
