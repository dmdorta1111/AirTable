# Phase 01: ExtractionJob Database Model

**Date**: 2026-01-23 | **Updated**: 2026-01-24
**Priority**: P1
**Status**: pending
**Estimated Effort**: 2h

---

## Context Links

- Template model: `src/pybase/models/automation.py` (AutomationRun)
- Base classes: `src/pybase/db/base.py` (BaseModel, SoftDeleteModel)
- Existing schemas: `src/pybase/schemas/extraction.py`

## Overview

Create persistent ExtractionJob model to replace in-memory `_jobs` dict in extraction.py (line 1465). Model tracks extraction status, retries, and results.

## Key Clarification

> **CloudFile does NOT exist**. The original plan incorrectly referenced it.
> ExtractionJob is self-contained - tracks file via `file_url` (S3 path).
> Optional linking to Record via `record_id` + `attachment_id`.

## Model Design

```python
# src/pybase/models/extraction_job.py

from datetime import datetime
from enum import Enum
from typing import Any
import json

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pybase.db.base import BaseModel


class ExtractionJobStatus(str, Enum):
    """Status of an extraction job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExtractionJob(BaseModel):
    """
    Extraction job for tracking file processing.
    
    Replaces in-memory _jobs dict with persistent DB storage.
    Template: AutomationRun model pattern.
    """
    
    __tablename__: str = "extraction_jobs"
    
    # File identification
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(2048), nullable=False, doc="S3/B2 file URL")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False, doc="pdf|dxf|ifc|step|werk24")
    
    # Optional linking to Record attachment
    record_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("records.id", ondelete="SET NULL"),
        nullable=True,
        doc="Record containing this attachment"
    )
    field_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        doc="Attachment field ID in record"
    )
    attachment_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        doc="Attachment object ID in field array"
    )
    
    # Job tracking
    status: Mapped[str] = mapped_column(
        String(20),
        default=ExtractionJobStatus.PENDING.value,
        nullable=False,
    )
    options: Mapped[str | None] = mapped_column(
        Text, nullable=True, default="{}", doc="Extraction options (JSON)"
    )
    result: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="Extraction result (JSON)"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    
    # Retry logic
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_extraction_jobs_status", "status"),
        Index("ix_extraction_jobs_status_retry", "status", "next_retry_at"),
        Index("ix_extraction_jobs_file_url", "file_url"),
        Index("ix_extraction_jobs_record", "record_id"),
        Index("ix_extraction_jobs_attachment", "record_id", "attachment_id"),
    )
    
    def __repr__(self) -> str:
        return f"<ExtractionJob {self.id} ({self.status})>"
    
    @property
    def status_enum(self) -> ExtractionJobStatus:
        return ExtractionJobStatus(self.status)
    
    def get_options(self) -> dict[str, Any]:
        try:
            return json.loads(self.options or "{}")
        except json.JSONDecodeError:
            return {}
    
    def set_options(self, options: dict[str, Any]) -> None:
        self.options = json.dumps(options)
    
    def get_result(self) -> dict[str, Any]:
        try:
            return json.loads(self.result or "{}")
        except json.JSONDecodeError:
            return {}
    
    def set_result(self, result: dict[str, Any]) -> None:
        self.result = json.dumps(result)
```

## Files to Create

| File | Description |
|------|-------------|
| `src/pybase/models/extraction_job.py` | ORM model (code above) |

## Files to Modify

| File | Changes |
|------|---------|
| `src/pybase/models/__init__.py` | Add: `from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus` |

## Implementation Steps

### 1. Create Model File
Create `src/pybase/models/extraction_job.py` with code above.

### 2. Update Model Exports
```python
# src/pybase/models/__init__.py
from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus

__all__ = [
    # ... existing exports ...
    "ExtractionJob",
    "ExtractionJobStatus",
]
```

### 3. Generate Migration
```bash
cd src/pybase
alembic revision --autogenerate -m "add_extraction_job_model"
```

### 4. Review Migration
Verify:
- All columns present
- All indexes created
- FK to records (nullable, ON DELETE SET NULL)
- No FK to non-existent CloudFile

### 5. Apply Migration
```bash
alembic upgrade head
```

### 6. Validate
```python
# Quick validation
from pybase.models import ExtractionJob, ExtractionJobStatus
from pybase.db.session import get_db

async def test():
    async with get_db() as db:
        job = ExtractionJob(
            filename="test.pdf",
            file_url="s3://bucket/test.pdf",
            file_size=1024,
            format="pdf"
        )
        db.add(job)
        await db.commit()
        print(f"Created: {job.id}, status: {job.status}")
```

## Todo Checklist

- [ ] Create `src/pybase/models/extraction_job.py`
- [ ] Update `src/pybase/models/__init__.py` exports
- [ ] Generate migration with `alembic revision --autogenerate`
- [ ] Review migration for correctness
- [ ] Apply migration with `alembic upgrade head`
- [ ] Validate model creation works

## Success Criteria

- [ ] Migration runs without errors
- [ ] `ExtractionJob` importable from `pybase.models`
- [ ] All 5 indexes created in DB
- [ ] JSON getter/setter methods work
- [ ] Status enum validates correctly

## Agent Assignment

| Category | Skills | Rationale |
|----------|--------|-----------|
| `fullstack-developer` | `backend-development`, `databases` | SQLAlchemy model, Alembic migration |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Migration conflicts | Low | Medium | Review migration before applying |
| Index naming conflicts | Low | Low | Use explicit index names |

## Next Steps

- Complete Phase 01
- Proceed to [Phase 02: Auto-Trigger on Upload](./phase-02-auto-trigger-on-upload.md)
