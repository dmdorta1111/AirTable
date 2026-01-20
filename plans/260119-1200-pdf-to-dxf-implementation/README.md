# PDF to DXF Batch Conversion - Implementation Plan

> **Goal:** Convert ~191K PDF files from Backblaze B2 to DXF format using parallel processing

## Decisions Made

| Question | Decision |
|----------|----------|
| Raster PDFs (~10%) | **Skip & flag in DB** |
| Output Storage | **Same B2 bucket, parallel `dxf/` folder** |
| Processing Priority | **All files in parallel** (fastest) |
| Existing DXFs | **Skip PDFs with corresponding DXF** |

---

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Neon DB       │────▶│  Job Coordinator │────▶│  Backblaze B2   │
│  (CloudFiles)   │     │  (Python Script) │     │   (EmjacDB)     │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌─────────┐  ┌─────────┐  ┌─────────┐
              │Worker 1 │  │Worker 2 │  │Worker N │
              │(Thread) │  │(Thread) │  │(Thread) │
              └─────────┘  └─────────┘  └─────────┘
                    │            │            │
                    └────────────┼────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │  DXF Output: B2/dxf/... │
                    └─────────────────────────┘
```

## Output Structure

**Input:** `Y://JOBS CUSTOM FAB/88000/88617/drawing.pdf`  
**Output:** `dxf/JOBS CUSTOM FAB/88000/88617/drawing.dxf`

---

## Database Schema Updates

```sql
-- Add conversion tracking columns to CloudFiles
ALTER TABLE "CloudFiles" ADD COLUMN IF NOT EXISTS "DxfStatus" VARCHAR(20) DEFAULT 'pending';
-- Values: pending, skipped_raster, skipped_has_dxf, processing, completed, failed

ALTER TABLE "CloudFiles" ADD COLUMN IF NOT EXISTS "DxfCloudKey" TEXT;
ALTER TABLE "CloudFiles" ADD COLUMN IF NOT EXISTS "DxfConvertedAt" TIMESTAMP;
ALTER TABLE "CloudFiles" ADD COLUMN IF NOT EXISTS "DxfEntityCount" INTEGER;
ALTER TABLE "CloudFiles" ADD COLUMN IF NOT EXISTS "DxfError" TEXT;

-- Index for efficient querying
CREATE INDEX IF NOT EXISTS idx_cloudfiles_dxf_status 
ON "CloudFiles"("DxfStatus") WHERE "FileType" = 'pdf';
```

---

## Implementation Phases

### Phase 1: Pre-Processing (30 min)
1. Run schema migration
2. Mark PDFs with existing DXFs as `skipped_has_dxf`
3. Count remaining PDFs to process

### Phase 2: Batch Conversion (4-5 hours)
1. Query pending PDFs in batches of 1000
2. Spawn 50 parallel workers
3. Each worker: download → detect raster → convert → upload → update DB

### Phase 3: Verification (30 min)
1. Generate conversion report
2. List failed files for manual review
3. Verify DXF file counts match

---

## Files to Create

| File | Purpose |
|------|---------|
| `01-migrate-schema.py` | Add DxfStatus columns |
| `02-mark-existing-dxfs.py` | Skip PDFs with DXF siblings |
| `03-batch-converter.py` | Main parallel conversion engine |
| `04-verify-results.py` | Generate completion report |
| `config-template.txt` | Credentials template |
| `requirements.txt` | Python dependencies |

---

## Estimated Timeline

| Phase | Duration | Notes |
|-------|----------|-------|
| Schema migration | 5 min | One-time setup |
| Mark existing DXFs | 10-30 min | ~800K files to check |
| Batch conversion | 4-5 hours | 50 workers, ~100K files |
| Verification | 15 min | Generate report |
| **Total** | **~6 hours** | |

---

## Technical Details

### Raster Detection Logic
```python
def is_raster_pdf(pdf_path):
    """Detect if PDF is raster (scanned) vs vector"""
    doc = fitz.open(pdf_path)
    for page in doc:
        # Check for drawings (vector paths)
        drawings = page.get_drawings()
        if drawings:
            return False  # Has vector content
        
        # Check image-to-text ratio
        images = page.get_images()
        text = page.get_text()
        if images and len(text.strip()) < 50:
            return True  # Mostly images, little text
    
    return True  # Default to raster if uncertain
```

### DXF Sibling Detection
```sql
-- Find PDFs that already have a corresponding DXF in same folder
WITH pdf_files AS (
    SELECT ID, CloudKey, 
           regexp_replace(CloudKey, '\.pdf$', '.dxf', 'i') as expected_dxf
    FROM "CloudFiles" 
    WHERE "FileType" = 'pdf'
),
existing_dxfs AS (
    SELECT CloudKey FROM "CloudFiles" WHERE "FileType" = 'dxf'
)
UPDATE "CloudFiles" 
SET "DxfStatus" = 'skipped_has_dxf'
WHERE ID IN (
    SELECT p.ID FROM pdf_files p
    JOIN existing_dxfs d ON lower(p.expected_dxf) = lower(d.CloudKey)
);
```

### Worker Processing Flow
```
1. Fetch batch of 1000 pending PDFs from DB
2. Mark batch as 'processing'
3. For each PDF in parallel (50 workers):
   a. Download from B2 to temp file
   b. Check if raster → mark 'skipped_raster', continue
   c. Convert PDF → DXF using PyMuPDF + ezdxf
   d. Upload DXF to B2 at dxf/{original_path}.dxf
   e. Update DB: status='completed', DxfCloudKey, entity_count
   f. On error: status='failed', DxfError=message
4. Repeat until no pending PDFs
```

---

## Resource Requirements

| Resource | Requirement |
|----------|-------------|
| CPU | 8+ cores recommended |
| RAM | 16GB+ (50 workers × ~300MB each) |
| Disk | 10GB temp space for downloads |
| Network | High bandwidth to B2 |
| Time | ~6 hours total |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Network failures | Auto-retry with exponential backoff |
| Large PDF timeout | Per-file timeout (5 min), mark failed |
| Memory exhaustion | Process files sequentially if >50MB |
| B2 rate limits | Throttle to 100 req/sec |

---

## Next Steps

1. **Review this plan** - Any concerns or modifications?
2. **Confirm to proceed** - I'll generate all implementation scripts
3. **Run Phase 1** - Schema migration & existing DXF detection
4. **Run Phase 2** - Main batch conversion
5. **Run Phase 3** - Verification & cleanup
