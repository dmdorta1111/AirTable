# Unified Engineering Document Intelligence Platform
# Implementation Execution Guide

## Status: **READY FOR EXECUTION**

## Prerequisites

### 1. Configuration Setup

**REQUIRED:** Edit `config.txt` with your actual credentials:

```bash
cd plans/260119-1400-unified-doc-intelligence
notepad config.txt  # or use your preferred editor
```

Replace placeholder values with actual credentials:

```
# Neon Database Configuration
NEON_DATABASE_URL=postgresql://username:password@ep-xxxx.region.aws.neon.tech/dbname?sslmode=require

# Backblaze B2 Configuration
B2_APPLICATION_KEY_ID=your_actual_key_id
B2_APPLICATION_KEY=your_actual_application_key
B2_BUCKET_NAME=EmjacDB
```

### 2. Install Dependencies

```bash
cd plans/260119-1400-unified-doc-intelligence
pip install -r requirements.txt
```

Required packages:
- psycopg2-binary (PostgreSQL driver)
- python-dotenv (Environment variables)
- tqdm (Progress bars)
- tabulate (Table formatting)
- PyMuPDF (PDF extraction)
- ezdxf (DXF parsing)
- b2sdk (Backblaze B2 storage)
- fastapi (Search API)
- uvicorn (ASGI server)
- pydantic (Data validation)

---

## Phase A: Auto-Linking (2-3 hours)

### A1: Schema Migration
```bash
python phase-a-linking/A1-migrate-schema.py
```

**Creates:** 8 new tables + 6 enum types + indexes + views
- document_groups
- document_group_members
- extracted_metadata
- extraction_jobs
- extracted_dimensions
- extracted_parameters
- extracted_materials
- extracted_bom_items

**Output:** `output/A1-migration.log` (success), `output/B1-table-status.json` (table verification)

### A2: Link by Basename (Confidence: 0.95)
```bash
python phase-a-linking/A2-link-by-basename.py
```

Groups files with same basename (e.g., `88617-001.pdf`, `88617-001.dxf`, `88617-001.prt`)

**Output:** `output/A2-basename-linking.json` (statistics report)

### A3: Link by Folder (Confidence: 0.80)
```bash
python phase-a-linking/A3-link-by-folder.py
```

Groups files co-located in same project directory

**Output:** `output/A3-folder-linking.json` (statistics report)

### A4: Extract Project Codes (Confidence: 0.70)
```bash
python phase-a-linking/A4-extract-project-codes.py
```

Regex extraction of project/job codes from filenames (e.g., `PRJ-2024-001`, `JOB-88617`)

**Output:** `output/A4-project-codes.json` (extracted codes report)

### A5: Flag Review Queue
```bash
python phase-a-linking/A5-flag-review-queue.py
```

Flags low-confidence or conflicted groups for human review

**Output:** `output/A5-review-queue.json` (groups requiring review)

### A6: Generate Linking Report
```bash
python phase-a-linking/A6-generate-link-report.py
```

Comprehensive summary of all linking operations

**Output:** `output/A6-linking-report.md` (formatted report with statistics)

---

## Phase B: PDF/DXF Extraction (6-8 hours)

### B1: Verify Extraction Tables
```bash
python phase-b-extraction/B1-create-extraction-tables.py
```

Verifies all extraction tables exist and creates missing indexes

**Output:** `output/B1-table-status.json` (table/index verification report)

### B2: Queue Extraction Jobs
```bash
python phase-b-extraction/B2-queue-extraction-jobs.py
```

Creates extraction jobs for all PDF and DXF files (~191K PDFs)

**Output:** `output/B2-jobs-queued.json` (jobs created summary)

### B3: PDF Extraction Worker (Parallel)
```bash
python phase-b-extraction/B3-pdf-extraction-worker.py
```

Extracts tables, dimensions, text, materials from PDFs using PyMuPDF
Uses 50 parallel workers for high throughput

**Output:** `output/B3-pdf-extraction.log` (extraction progress)

### B4: DXF Extraction Worker (Parallel)
```bash
python phase-b-extraction/B4-dxf-extraction-worker.py
```

Extracts layers, blocks, entities, dimensional metadata from DXFs using ezdxf
Uses 50 parallel workers for high throughput

**Output:** `output/B4-dxf-extraction.log` (extraction progress)

### B5: Index Dimensions
```bash
python phase-b-extraction/B5-index-dimensions.py
```

Populates `extracted_dimensions` table from extracted PDF/DXF metadata

**Output:** `output/B5-dimensions-indexed.json` (indexing statistics)

### B6: Index Materials
```bash
python phase-b-extraction/B6-index-materials.py
```

Populates `extracted_materials` table from extracted PDF/DXF data

**Output:** `output/B6-materials-indexed.json` (indexing statistics)

### B7: Extraction Summary Report
```bash
python phase-b-extraction/B7-extraction-report.py
```

Comprehensive summary of extraction operations and data quality

**Output:** `output/B7-extraction-summary.md` (formatted report)

---

## Phase C: Search API (4-6 hours)

### C1: Dimensions Search
```bash
python phase-c-search/C1-search-dimensions.py --value 10.5 --tolerance 0.1 --unit mm
```

Search by value, tolerance, unit, label, dimension type

**Output:** Console results with grouped DocumentGroups

### C2: Parameters Search
```bash
python phase-c-search/C2-search-parameters.py --name "Weight" --value 25.5
```

Search CAD parameters by name, value, numeric range, category, designated flag

**Output:** Console results with grouped DocumentGroups

### C3: Materials Search
```bash
python phase-c-search/C3-search-materials.py --material "304 Stainless" --spec "ASTM A240"
```

Fuzzy search for materials with similarity matching

**Output:** Console results with grouped DocumentGroups

### C4: Projects Search
```bash
python phase-c-search/C4-search-projects.py --code "PRJ-2024-001" --stats
```

Find all DocumentGroups and files for a project code

**Output:** Console results with file statistics

### C5: Full-text Search
```bash
python phase-c-search/C5-search-fulltext.py --query "dimension | weight" --scope all
```

Full-text search across all extracted data (materials, parameters, dimensions)

**Output:** Console results grouped by scope with relevance scores

### C6: Start Search API Server
```bash
# Development (auto-reload)
uvicorn phase-c-search.C6-search-api-server:app --reload --host 0.0.0.0 --port 8080

# Production (4 workers)
uvicorn phase-c-search.C6-search-api-server:app --host 0.0.0.0 --port 8080 --workers 4
```

**API Endpoints:**
- `GET /` - Health check
- `GET /api/search/dimensions` - Dimensions search
- `GET /api/search/parameters` - Parameters search
- `GET /api/search/materials` - Materials search
- `GET /api/search/projects` - Projects search
- `GET /api/search/fulltext` - Full-text search
- `GET /api/groups/{group_id}` - DocumentGroup details

**Documentation:**
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

---

## Execution Sequence

### Day 1 (AM): Phase A - Auto-Linking
```bash
cd plans/260119-1400-unified-doc-intelligence

# Step 1: Schema migration
python phase-a-linking/A1-migrate-schema.py

# Step 2: Link by basename
python phase-a-linking/A2-link-by-basename.py

# Step 3: Link by folder
python phase-a-linking/A3-link-by-folder.py

# Step 4: Extract project codes
python phase-a-linking/A4-extract-project-codes.py

# Step 5: Flag review queue
python phase-a-linking/A5-flag-review-queue.py

# Step 6: Generate linking report
python phase-a-linking/A6-generate-link-report.py
```

### Day 1 (PM): Phase B - Start Extraction
```bash
# Step 1: Verify tables
python phase-b-extraction/B1-create-extraction-tables.py

# Step 2: Queue jobs
python phase-b-extraction/B2-queue-extraction-jobs.py

# Step 3: Start PDF extraction (will take several hours)
python phase-b-extraction/B3-pdf-extraction-worker.py

# Step 4: Start DXF extraction (will take several hours)
python phase-b-extraction/B4-dxf-extraction-worker.py
```

### Day 2 (AM): Phase B - Complete Extraction
```bash
# Step 5: Index dimensions
python phase-b-extraction/B5-index-dimensions.py

# Step 6: Index materials
python phase-b-extraction/B6-index-materials.py

# Step 7: Generate extraction report
python phase-b-extraction/B7-extraction-report.py
```

### Day 2 (PM): Phase C - Search API
```bash
# Step 1: Test each search endpoint
python phase-c-search/C1-search-dimensions.py --value 10.0 --unit mm
python phase-c-search/C2-search-parameters.py --name "Material"
python phase-c-search/C3-search-materials.py --material "Steel"
python phase-c-search/C4-search-projects.py --code "PRJ-2024-001"
python phase-c-search/C5-search-fulltext.py --query "pressure vessel"

# Step 2: Start API server
uvicorn phase-c-search.C6-search-api-server:app --host 0.0.0.0 --port 8080
```

---

## Troubleshooting

### Database Connection Issues
- Verify NEON_DATABASE_URL format
- Check network connectivity to Neon
- Ensure SSL certificates are valid

### Extraction Worker Failures
- Check Backblaze B2 credentials
- Verify file access permissions
- Monitor worker logs in `output/` directory
- Check disk space for downloaded files

### Performance Issues
- Reduce worker count in extraction scripts (default: 50)
- Increase database connection pool size
- Monitor PostgreSQL resource usage

### API Server Issues
- Verify port 8080 is not in use
- Check firewall settings
- Review server logs for errors

---

## Monitoring Queries

### Check extraction progress
```sql
SELECT extraction_status, COUNT(*) FROM extracted_metadata GROUP BY 1;
```

### Check job queue health
```sql
SELECT * FROM v_extraction_queue_status;
```

### Find stalled jobs
```sql
SELECT *
FROM extraction_jobs
WHERE status = 'processing'
AND started_at < NOW() - INTERVAL '1 hour';
```

### Check document group statistics
```sql
SELECT * FROM v_document_groups_summary;
```

---

## Expected Data Scale

| Metric | Expected Value |
|---------|---------------|
| Total CloudFiles | ~819K files |
| PDF Drawings | ~191K files |
| DXF Drawings | ~Unknown (estimate: 50-100K) |
| DocumentGroups | ~10-50K groups (post-linking) |
| Extracted Dimensions | ~500K-2M entries |
| Extracted Parameters | ~1-5M entries |
| Extracted Materials | ~50-200K entries |

---

*Implementation Guide - Unified Engineering Document Intelligence Platform*
*Generated: 2026-01-19*
