# Plan Review & Refinement Report

**Date**: 2026-01-24
**Reviewer**: Planning Agent
**Plan**: Auto-Extraction Hybrid System

---

## Executive Summary

The current plan has a **CRITICAL FLAW**: it references a non-existent `CloudFile` model. After analyzing the codebase, I've identified the correct architecture and provide a refined implementation plan with specific file paths, agent assignments, and success criteria.

---

## Issue #1: CloudFile Confusion (RESOLVED)

### Problem
Plan mentions `CloudFile` model repeatedly, but **it doesn't exist**. The plan incorrectly assumes:
- Files are stored in a separate CloudFile table
- Extraction status should go on CloudFile

### Reality
Attachments in PyBase are stored as **JSON in Record.data field**:
```python
# Record.data structure (attachment field value)
{
    "field_id_123": [  # attachment field
        {
            "id": "uuid",
            "filename": "drawing.pdf",
            "url": "https://s3.../...",
            "size": 1024000,
            "mime_type": "application/pdf",
            "thumbnails": {...}
        }
    ]
}
```

### Solution
**ExtractionJob is self-sufficient** - it tracks everything:
- File reference via `file_url` (S3/B2 path) + `filename`
- Optional `record_id` + `field_id` + `attachment_id` for linking back
- Status, results, retries all on ExtractionJob

**NO changes to Record model needed.** The ExtractionJob tracks the extraction, and results can be queried by file URL or attachment ID.

---

## Issue #2: Where Does extraction_status Go? (RESOLVED)

### Answer: **NOWHERE on existing models**

The plan's idea to add `extraction_status` to CloudFile was misguided. Instead:

1. **ExtractionJob IS the status** - query by file_url or attachment_id
2. **Result storage** - `ExtractionJob.result` JSONB field holds extracted data
3. **Optional enhancement** - Add `extraction_job_id` to attachment object in Record.data (Phase 2)

---

## Refined Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     AUTO-EXTRACTION HYBRID SYSTEM                        │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Upload Flow:                                                            │
│  ┌──────────┐    ┌─────────────┐    ┌──────────────────┐                │
│  │ POST     │───>│ Save file   │───>│ Create           │                │
│  │ /upload  │    │ to S3/B2    │    │ ExtractionJob    │                │
│  └──────────┘    └─────────────┘    │ (pending)        │                │
│                                      └────────┬─────────┘                │
│                                               │                          │
│                                               v BackgroundTask           │
│                                      ┌──────────────────┐                │
│                                      │ Extract & Update │                │
│                                      │ ExtractionJob    │                │
│                                      │ (completed/fail) │                │
│                                      └──────────────────┘                │
│                                                                          │
│  ExtractionJob Model:                                                    │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ id, status, format, filename, file_url, file_size                │   │
│  │ record_id?, field_id?, attachment_id? (optional linking)         │   │
│  │ options (JSONB), result (JSONB), error_message                   │   │
│  │ retry_count, max_retries, next_retry_at                          │   │
│  │ created_at, started_at, completed_at, updated_at                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  Query Patterns:                                                         │
│  - By job_id: Direct lookup                                              │
│  - By file_url: Find extraction for specific file                        │
│  - By attachment_id: Find extraction for attachment in record            │
│  - By status: Find pending/failed jobs for retry                         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Refined Phase Breakdown

### Phase 01: ExtractionJob Database Model (2h)
**Priority**: P1 | **Complexity**: Low

#### Files to CREATE:
| File | Description |
|------|-------------|
| `src/pybase/models/extraction_job.py` | ORM model (use AutomationRun as template) |

#### Files to MODIFY:
| File | Changes |
|------|---------|
| `src/pybase/models/__init__.py` | Export ExtractionJob, ExtractionJobStatus |

#### Migration:
```bash
alembic revision --autogenerate -m "add_extraction_job_model"
```

#### Model Design (refined):
```python
class ExtractionJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ExtractionJob(BaseModel):
    __tablename__ = "extraction_jobs"
    
    # File identification
    filename: Mapped[str]                    # Original filename
    file_url: Mapped[str]                    # S3/B2 URL (unique identifier)
    file_size: Mapped[int]
    format: Mapped[str]                      # pdf, dxf, ifc, step, werk24
    
    # Optional linking to Record.data attachment
    record_id: Mapped[str | None]            # FK nullable
    field_id: Mapped[str | None]             # attachment field ID
    attachment_id: Mapped[str | None]        # attachment object ID in array
    
    # Job tracking
    status: Mapped[str] = "pending"
    options: Mapped[str | None]              # JSONB extraction options
    result: Mapped[str | None]               # JSONB extraction result
    error_message: Mapped[str | None]
    
    # Retry logic
    retry_count: Mapped[int] = 0
    max_retries: Mapped[int] = 3
    next_retry_at: Mapped[datetime | None]
    
    # Timing
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    
    # Indexes
    __table_args__ = (
        Index("ix_extraction_jobs_status", "status"),
        Index("ix_extraction_jobs_status_retry", "status", "next_retry_at"),
        Index("ix_extraction_jobs_file_url", "file_url"),
        Index("ix_extraction_jobs_attachment", "record_id", "attachment_id"),
    )
```

#### Success Criteria:
- [ ] Migration runs without errors
- [ ] `ExtractionJob` importable from `pybase.models`
- [ ] All indexes created
- [ ] JSON getter/setter methods work

#### Agent Assignment:
| Category | Skills | Rationale |
|----------|--------|-----------|
| `fullstack-developer` | `backend-development`, `databases` | DB model creation, SQLAlchemy patterns |

---

### Phase 02: Auto-Trigger on Upload (4h)
**Priority**: P1 | **Complexity**: Medium

#### Files to CREATE:
| File | Description |
|------|-------------|
| `src/pybase/services/extraction_job_service.py` | CRUD operations for ExtractionJob |
| `src/pybase/services/extraction/background.py` | Background task for extraction |

#### Files to MODIFY:
| File | Changes |
|------|---------|
| `src/pybase/api/v1/extraction.py` | Add upload endpoint, replace `_jobs` dict usage |
| `src/pybase/schemas/extraction.py` | Add upload schemas if needed |

#### Key Implementation Details:

**1. ExtractionJobService** (`src/pybase/services/extraction_job_service.py`):
```python
class ExtractionJobService:
    async def create_job(db, file_url, filename, ...) -> ExtractionJob
    async def get_job(db, job_id) -> ExtractionJob | None
    async def get_job_by_file_url(db, file_url) -> ExtractionJob | None
    async def update_status(db, job_id, status, result?, error?) -> ExtractionJob
    async def get_pending_jobs(db) -> list[ExtractionJob]
    async def get_retryable_jobs(db) -> list[ExtractionJob]  # next_retry_at < now
```

**2. Background Extraction** (`src/pybase/services/extraction/background.py`):
```python
async def extract_file_background(job_id: str, db_url: str):
    """Background task - runs after response sent."""
    # 1. Create new DB session (background tasks need own session)
    # 2. Update job -> processing
    # 3. Detect format from extension
    # 4. Call appropriate extractor
    # 5. Update job -> completed + result OR failed + error
```

**3. Upload Endpoint** (`src/pybase/api/v1/extraction.py`):
```python
@router.post("/upload", status_code=202)
async def upload_and_extract(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
    current_user: User,
):
    # 1. Save file to S3/B2
    # 2. Create ExtractionJob (pending)
    # 3. Add background task
    # 4. Return 202 with job_id
```

**4. Replace `_jobs` dict**:
- Replace in-memory `_jobs` and `_bulk_jobs` usage with DB queries
- Keep API response schemas unchanged

#### Success Criteria:
- [ ] `POST /extraction/upload` returns 202 + job_id
- [ ] ExtractionJob created in DB with status=pending
- [ ] Background task starts extraction
- [ ] Job status updates to completed/failed
- [ ] Result stored in ExtractionJob.result

#### Agent Assignment:
| Category | Skills | Rationale |
|----------|--------|-----------|
| `fullstack-developer` | `backend-development`, `databases` | Service layer, FastAPI BackgroundTasks |

---

### Phase 03: Retry Logic & Monitoring (3h)
**Priority**: P2 | **Complexity**: Medium

#### Files to CREATE:
| File | Description |
|------|-------------|
| `src/pybase/services/extraction/retry.py` | Retry logic with exponential backoff |

#### Files to MODIFY:
| File | Changes |
|------|---------|
| `src/pybase/services/extraction/background.py` | Add retry on failure |
| `src/pybase/api/v1/extraction.py` | Add monitoring endpoints |

#### Retry Logic:
```python
# Exponential backoff: 30s, 2m, 8m (base=30, multiplier=4)
def calculate_next_retry(retry_count: int) -> datetime:
    delay_seconds = 30 * (4 ** retry_count)  # 30, 120, 480
    return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)

RETRYABLE_ERRORS = [
    "ConnectionError", "Timeout", "ServiceUnavailable",
    "RateLimitExceeded", "TemporaryFailure"
]
```

#### Monitoring Endpoints:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/extraction/jobs/{job_id}` | GET | Get job status & result |
| `/extraction/jobs` | GET | List jobs (filter by status) |
| `/extraction/jobs/{job_id}` | DELETE | Cancel pending job |
| `/extraction/jobs/{job_id}/retry` | POST | Manual retry |

#### Success Criteria:
- [ ] Failed jobs auto-retry with backoff
- [ ] Max 3 retries then permanent failure
- [ ] All monitoring endpoints work
- [ ] Users can only see/cancel their own jobs

#### Agent Assignment:
| Category | Skills | Rationale |
|----------|--------|-----------|
| `fullstack-developer` | `backend-development` | Error handling, API endpoints |

---

### Phase 04: Testing & Validation (3h)
**Priority**: P2 | **Complexity**: Medium

#### Files to CREATE:
| File | Description |
|------|-------------|
| `tests/extraction/__init__.py` | Test package |
| `tests/extraction/test_extraction_job_model.py` | Model tests |
| `tests/extraction/test_extraction_job_service.py` | Service tests |
| `tests/extraction/test_background.py` | Background task tests |
| `tests/extraction/test_retry.py` | Retry logic tests |
| `tests/extraction/test_upload_api.py` | API integration tests |
| `tests/extraction/conftest.py` | Test fixtures |

#### Files to MODIFY:
| File | Changes |
|------|---------|
| `tests/conftest.py` | Add extraction fixtures if needed |

#### Test Strategy:
```
Unit Tests (fast, mocked):
├── test_extraction_job_model.py - CRUD, status transitions
├── test_extraction_job_service.py - Service layer logic
└── test_retry.py - Backoff calculation, retry decisions

Integration Tests (slower, real DB):
├── test_background.py - Mock extractors, real DB
└── test_upload_api.py - Full flow with TestClient
```

#### Success Criteria:
- [ ] All tests pass
- [ ] Coverage >80% for new code
- [ ] Existing tests unchanged
- [ ] No regressions in unified deploy

#### Agent Assignment:
| Category | Skills | Rationale |
|----------|--------|-----------|
| `fullstack-developer` | `backend-development`, `Debugging` | pytest async, test fixtures |

---

## Implementation Order

```
Phase 01 ─────────────────────────┐
(ExtractionJob Model)             │
2h                                │
                                  │ Sequential (DB dependency)
                                  v
Phase 02 ─────────────────────────┐
(Upload + BackgroundTasks)        │
4h                                │
                                  │ Sequential (Service dependency)
                                  v
Phase 03 ─────────────────────────┤
(Retry + Monitoring)              │
3h                                │
                                  │ Can parallelize tests
                                  v
Phase 04 ─────────────────────────┘
(Testing & Validation)
3h

Total: 12h (as planned)
```

---

## Database Migration Strategy

### Step 1: Create Model
```python
# src/pybase/models/extraction_job.py
# Full model implementation
```

### Step 2: Generate Migration
```bash
cd src/pybase
alembic revision --autogenerate -m "add_extraction_job_model"
```

### Step 3: Review Migration
- Verify all columns present
- Verify indexes created
- Verify no FK to non-existent CloudFile

### Step 4: Apply Migration
```bash
alembic upgrade head
```

### Step 5: Validate
```python
# Quick validation script
from pybase.models import ExtractionJob
from pybase.db.session import get_db

async with get_db() as db:
    job = ExtractionJob(
        filename="test.pdf",
        file_url="s3://bucket/test.pdf",
        file_size=1024,
        format="pdf"
    )
    db.add(job)
    await db.commit()
    print(f"Created job: {job.id}")
```

---

## Summary of Changes to Original Plan

| Aspect | Original Plan | Refined Plan |
|--------|---------------|--------------|
| CloudFile dependency | FK to CloudFile.id | Removed - use file_url + optional record linking |
| extraction_status field | Add to CloudFile | Not needed - ExtractionJob IS the status |
| File tracking | cloud_file_id FK | file_url (S3 path) + optional record_id/attachment_id |
| Model template | Generic | Use AutomationRun as direct template |
| Indexes | Basic | Added status+retry, file_url, attachment composite |

---

## Unresolved Questions

1. **Retry scheduler**: Should retry be checked on lifespan startup or via cron?
   - *Recommendation*: Start with lifespan task, upgrade to cron if needed

2. **Backfill**: How to handle files uploaded before this feature?
   - *Recommendation*: Add `/extraction/backfill` admin endpoint (Phase 5)

3. **Werk24 testing**: Requires API key - how to test?
   - *Recommendation*: Mock Werk24 client in tests, manual validation in staging

---

## Files Summary

### To CREATE (7 files):
1. `src/pybase/models/extraction_job.py`
2. `src/pybase/services/extraction_job_service.py`
3. `src/pybase/services/extraction/background.py`
4. `src/pybase/services/extraction/retry.py`
5. `tests/extraction/__init__.py`
6. `tests/extraction/conftest.py`
7. `tests/extraction/test_*.py` (5 test files)

### To MODIFY (3 files):
1. `src/pybase/models/__init__.py`
2. `src/pybase/api/v1/extraction.py`
3. `src/pybase/schemas/extraction.py` (minor updates)

### Migration:
1. `migrations/versions/YYYYMMDD_HHMMSS_add_extraction_job_model.py`

---

*Report generated by Planning Agent*
