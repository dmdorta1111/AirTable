---
title: "Auto-Extraction Hybrid System"
description: "Hybrid auto-extraction system using FastAPI BackgroundTasks with unified deploy for bulk imports"
status: pending
priority: P1
effort: 12h
branch: master
tags: [extraction, background-tasks, hybrid]
created: 2026-01-23
updated: 2026-01-24
---

# Auto-Extraction Hybrid System

## Overview

A hybrid extraction system where files are automatically extracted on upload using FastAPI BackgroundTasks (for low daily volume <100 files), while keeping the unified deploy package for bulk imports.

**Status**: Pending
**Estimated Effort**: 12 hours
**Last Reviewed**: 2026-01-24

## Critical Clarification: No CloudFile Model

> **IMPORTANT**: The original plan referenced a `CloudFile` model that **does not exist**.
> 
> Attachments in PyBase are stored as JSON in `Record.data` field via the attachment field handler.
> The `ExtractionJob` model is **self-sufficient** - it tracks file URL, status, and results.
> No changes to Record model are needed.

See: [Plan Review Report](./reports/260124-plan-review-refinement.md)

## Phases

| Phase | Status | Effort | Description |
|-------|--------|--------|-------------|
| [Phase 01](./phase-01-extraction-job-model.md) | pending | 2h | ExtractionJob database model (use AutomationRun template) |
| [Phase 02](./phase-02-auto-trigger-on-upload.md) | pending | 4h | Auto-trigger with BackgroundTasks |
| [Phase 03](./phase-03-retry-logic-and-monitoring.md) | pending | 3h | Retry logic and monitoring endpoints |
| [Phase 04](./phase-04-testing-and-validation.md) | pending | 3h | Testing and validation |

## Refined Architecture

```
┌─────────────┐     ┌─────────────┐     ┌────────────────────────────────┐
│   Upload    │────>│   FastAPI   │────>│  ExtractionJob (DB Model)      │
│   File      │     │   Endpoint  │     │  - file_url (S3 path)          │
└─────────────┘     └─────────────┘     │  - status, result, retries     │
                            │           │  - optional: record_id, etc.   │
                            v           └────────────────────────────────┘
                     BackgroundTask
                            │
                     ┌──────v──────┐
                     │ Extraction  │
                     │ Service     │
                     └──────┬──────┘
                            │
                     ┌──────v───────────────┐
                     │ Update ExtractionJob │
                     │ (completed/failed)   │
                     └──────────────────────┘
```

## Key Design Decisions

1. **FastAPI BackgroundTasks** - Simpler than Celery for <100 files/day (KISS)
2. **ExtractionJob Model** - Self-contained job tracking (no CloudFile dependency)
3. **File Identification** - Use `file_url` (S3/B2 path) as unique identifier
4. **Optional Record Linking** - `record_id` + `attachment_id` for linking back
5. **Retry Logic** - Exponential backoff (30s, 2m, 8m), max 3 retries
6. **Unified Deploy** - Keep existing bulk workers unchanged

## Files Summary

### To Create
| File | Phase | Description |
|------|-------|-------------|
| `src/pybase/models/extraction_job.py` | 01 | ORM model (template: AutomationRun) |
| `src/pybase/services/extraction_job_service.py` | 02 | CRUD operations |
| `src/pybase/services/extraction/background.py` | 02 | Background task |
| `src/pybase/services/extraction/retry.py` | 03 | Retry logic |
| `tests/extraction/*.py` | 04 | Test suite |

### To Modify
| File | Phase | Changes |
|------|-------|---------|
| `src/pybase/models/__init__.py` | 01 | Export ExtractionJob |
| `src/pybase/api/v1/extraction.py` | 02 | Upload endpoint, replace `_jobs` dict |
| `src/pybase/schemas/extraction.py` | 02 | Upload schemas (if needed) |

### Migration
| File | Phase |
|------|-------|
| `migrations/versions/YYYYMMDD_add_extraction_job.py` | 01 |

## Agent Assignments

| Phase | Category | Skills |
|-------|----------|--------|
| 01 | `fullstack-developer` | `backend-development`, `databases` |
| 02 | `fullstack-developer` | `backend-development`, `databases` |
| 03 | `fullstack-developer` | `backend-development` |
| 04 | `fullstack-developer` | `backend-development`, `Debugging` |

## Success Criteria

- [ ] ExtractionJob model created with proper indexes
- [ ] Files auto-extract on upload via BackgroundTasks
- [ ] Job status queryable by job_id or file_url
- [ ] Failed extractions retry automatically (max 3 times)
- [ ] Monitoring endpoints work (GET/DELETE/retry)
- [ ] Bulk imports still work via unified deploy
- [ ] All tests pass with >80% coverage

## Unresolved Questions

1. **Retry scheduler**: Lifespan task or cron? (Recommend: lifespan)
2. **Backfill**: Admin endpoint for pre-existing files? (Phase 5)
3. **Werk24 testing**: Mock in tests, manual in staging

## References

- [Plan Review Report](./reports/260124-plan-review-refinement.md) - Detailed analysis
- [AutomationRun Model](../src/pybase/models/automation.py) - Template for ExtractionJob
- [Attachment Handler](../src/pybase/fields/types/attachment.py) - How attachments are stored
