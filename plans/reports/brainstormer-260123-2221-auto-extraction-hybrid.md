# Auto-Extraction Hybrid Approach - Brainstorm Summary

**Date:** 2026-01-23
**Context:** PyBase document extraction standardization

---

## Problem Statement

User needs a standardized, embedded process for daily document ingestion and intelligence extraction. Currently has two separate systems:
- **PyBase main app:** API endpoints for on-demand extraction
- **Unified deploy package:** Large-scale batch processing (designed for 819K+ files)

Daily volume: **< 100 files/day**

---

## Evaluated Approaches

| Approach | Description | Pros | Cons | Effort |
|----------|-------------|------|------|--------|
| **1. Embed in PyBase** | Auto-extract on file upload | Immediate, single codebase | Requires Celery/Redis infrastructure | Medium (2-3 weeks) |
| **2. Separate Batch Service** | Daily cron of unified deploy | Isolates heavy processing | Delayed results, two systems | Low (1 week) |
| **3. Hybrid** | Light auto-extract + bulk for imports | Best of both, simple start | Two codebases | Low-Med (1-2 weeks) |

---

## Recommended Solution: Approach 3 (Hybrid)

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PyBase Main App                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   File Upload → CloudFile Created                                │
│                      ↓                                            │
│           BackgroundTask Triggered                                │
│                      ↓                                            │
│           ExtractionService.process()                             │
│                      ↓                                            │
│           Extracted Data Saved                                    │
│                      ↓                                            │
│           CloudFile.metadata.updated                              │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                   Unified Deploy (Bulk Only)                     │
│                                                                   │
│   For large imports/migrations → Run full A→B→C→D pipeline       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Components

| Component | Description | Priority |
|-----------|-------------|----------|
| **ExtractionJob Model** | Persistent job tracking in database | P0 |
| **Auto-trigger on upload** | BackgroundTask on CloudFile create | P0 |
| **Extraction status metadata** | Store status in CloudFile | P0 |
| **Simple retry logic** | Handle transient failures | P1 |
| **Progress webhook/event** | Notify UI of extraction progress | P2 |
| **Monitoring endpoint** | Health check for extraction system | P2 |

### Key Design Decisions

1. **No Celery initially** - Use FastAPI BackgroundTasks for simplicity
2. **Store status in CloudFile metadata** - Avoid separate job table initially
3. **Unified deploy remains** - For bulk imports, not daily operations
4. **Scale when needed** - Add Celery/Redis only if volume increases

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Background task dies on restart | Medium | Add recovery on startup |
| Extraction failures silent | High | Add logging + retry |
| Werk24 quota exceeded | Medium | Track usage in Werk24Usage |
| Processing slows down uploads | Low | Run async, non-blocking |

---

## Success Criteria

- ✅ Files auto-extracted on upload (no manual trigger)
- ✅ Extraction results visible in UI
- ✅ Failed extractions logged and retryable
- ✅ < 5 second upload response time (extraction async)
- ✅ Unified deploy still works for bulk imports

---

## Dependencies

- Existing extraction services must be functional
- CloudFile model accessible
- Database migrations for new metadata fields
- Werk24 API credentials configured

---

## Next Steps

1. Create detailed implementation plan (`/plan:fast`)
2. Build ExtractionJob model/service
3. Add upload trigger
4. Test with real files
5. Document usage

---

## Open Questions

- Should extracted data be indexed immediately or deferred?
- What extraction formats are required for auto-processing (all or subset)?
- Should users be able to trigger re-extraction manually?
