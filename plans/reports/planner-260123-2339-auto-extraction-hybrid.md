# Auto-Extraction Hybrid System - Implementation Plan

**Date**: 2026-01-23
**Plan**: `plans/260123-2339-auto-extraction-hybrid/`
**Status**: Pending Implementation

---

## Executive Summary

Create a hybrid auto-extraction system where files are automatically extracted on upload using FastAPI BackgroundTasks (KISS principle for <100 files/day), while keeping the unified deploy package for bulk imports.

**Estimated Effort**: 12 hours
**Priority**: P1 (High)

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐
│   Upload    │────>│   FastAPI   │────>│  ExtractionJob      │
│   File      │     │   Endpoint  │     │  (DB Model)          │
└─────────────┘     └─────────────┘     └─────────────────────┘
                            │
                            v BackgroundTask
                     ┌─────────────┐
                     │ Extraction  │
                     │ Service    │
                     └─────────────┘
                            │
                            v
                     ┌─────────────┐
                     │ CloudFile   │
                     │ metadata    │
                     └─────────────┘
```

## Key Design Decisions

1. **FastAPI BackgroundTasks** - Simpler than Celery for <100 files/day (YAGNI)
2. **ExtractionJob Model** - Persistent job tracking in DB (not in-memory)
3. **Unified Deploy** - Keep existing bulk workers unchanged
4. **Status in CloudFile** - Add `extraction_status` JSONB column
5. **Retry Logic** - Exponential backoff, max 3 retries

## Phases

### Phase 01: ExtractionJob Database Model (2h)
**File**: `phase-01-extraction-job-model.md`

Create persistent database model:
- ExtractionJob ORM with status, retry tracking, result storage
- Migration with indexes on (status, next_retry_at), (cloud_file_id)
- Update extraction schemas

### Phase 02: Auto-Trigger on Upload (4h)
**File**: `phase-02-auto-trigger-on-upload.md`

Implement auto-extraction:
- ExtractionJobService for job management
- Background extraction module
- Upload endpoint with BackgroundTasks integration
- CloudFile extraction_status column

### Phase 03: Retry Logic and Monitoring (3h)
**File**: `phase-03-retry-logic-and-monitoring.md`

Add reliability and observability:
- Exponential backoff (30s, 2m, 8m, 25m)
- Monitoring endpoints (status, list, cancel)
- Distinguish transient vs permanent failures

### Phase 04: Testing and Validation (3h)
**File**: `phase-04-testing-and-validation.md`

Comprehensive testing:
- Unit tests for services
- Integration tests for API
- Retry logic tests
- Sample test files for each format

## Files to Create

```
src/pybase/
├── models/
│   └── extraction_job.py           # NEW: ExtractionJob ORM
├── services/
│   └── extraction/
│       ├── job.py                  # NEW: ExtractionJobService
│       ├── background.py           # NEW: Background extraction
│       └── retry.py                # NEW: Retry logic
└── schemas/
    └── extraction.py               # MODIFY: Add upload/monitoring schemas

tests/
└── extraction/
    ├── test_job_model.py
    ├── test_job_service.py
    ├── test_background.py
    ├── test_retry.py
    └── test_upload_api.py

migrations/versions/
└── YYYYMMDD_HHMMSS_*.py            # ExtractionJob + CloudFile migration
```

## Supported Formats

| Format | Extensions | Extraction Library |
|--------|-----------|-------------------|
| PDF | .pdf | PyMuPDF |
| DXF | .dxf, .dwg | ezdxf |
| IFC | .ifc | ifcopenshell |
| STEP | .stp, .step | cadquery/OCP |

## Success Criteria

- [ ] Files auto-extract on upload
- [ ] Extraction status stored in CloudFile
- [ ] Failed extractions retry automatically
- [ ] Bulk imports still work via unified deploy
- [ ] All tests pass with >80% coverage

## Integration Points

1. **Existing Extraction API** (`src/pybase/api/v1/extraction.py`)
   - Add upload endpoint
   - Add monitoring endpoints
   - Keep existing endpoints unchanged

2. **CloudFile Model**
   - Add `extraction_status` JSONB column
   - Stores: status, job_id, completed_at, error

3. **Unified Deploy** (unchanged)
   - Bulk workers continue to use existing job queue
   - No changes to B3/B4/D2 workers

## Unresolved Questions

1. Should upload be a separate endpoint or integrated into existing attachment upload?
2. How to handle files uploaded before this feature (backfill)?
3. Should retry be triggered by scheduled task or on-demand?
4. How to alert users about permanently failing files?

## Next Steps

1. Review plan with team
2. Start with Phase 01 (database model)
3. Implement phases sequentially
4. Test thoroughly before deploying

---

**Plan Location**: `C:\Users\dmdor\VsCode\AirTable\plans\260123-2339-auto-extraction-hybrid\`
**Active Plan Set**: Yes
