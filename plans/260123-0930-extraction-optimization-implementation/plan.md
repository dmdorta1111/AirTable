# Extraction Process Optimization - Implementation Plan

**Date:** 2026-01-23
**Status:** In Progress
**Priority:** High
**Complexity:** High (multi-VM deployment)

---

## Overview

Implement job coordination system and optimize extraction pipeline for 5 VMs (2 Ubuntu, 3 Windows) processing 500K-1M files. Goal: Better data quality with reliability-critical tolerance.

**Key Enhancement:** Job coordination with claiming, heartbeats, and auto-retry eliminates duplicate processing, improves throughput 20-30%.

**Reference:** `plans/reports/brainstormer-260123-0853-extraction-redo-optimization.md`

---

## Phase Summary

| Phase | Duration | VM | Description | Status |
|-------|----------|-----|-------------|--------|
| 00 | 30 min | All | Pre-deployment verification & setup | **In Progress** |
| 01 | 2 hours | VM1 | Database migration verification + Phase A execution | Pending |
| 02 | 8 hours | VM2, VM3 | Phase B parallel extraction (PDF/DXF) | Pending |
| 03 | 12 hours | VM4, VM5 | Phase D parallel CAD extraction (Creo gRPC) | Pending |
| 04 | 1 hour | VM5 | Phase C search API deployment | Pending |
| 05 | 2 hours | All | Post-deployment validation & reporting | Pending |

**Total Estimated Time:** 25.5 hours

---

## Phase 00: Pre-Deployment Verification & Setup

**Duration:** 30 minutes
**VMs:** All 5 VMs
**Dependencies:** None

### Objectives
- Verify database migration complete
- Deploy code to all VMs
- Install dependencies
- Create job coordination tables

### Tasks

#### Task 00.1: Database Migration Verification (15 min)
**File:** `unified-doc-intelligence-deploy/scripts/verify-migration.py` (CREATE)

**Steps:**
1. Create verification script
2. Run on VM1 (Ubuntu)
3. Verify 14 tables exist
4. Verify pgvector extension enabled
5. Verify HNSW indexes created
6. **Exit criteria:** All checks pass

**Validation:**
```sql
-- Should return 14
SELECT COUNT(DISTINCT table_name)
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
  'document_groups', 'document_group_members',
  'extraction_jobs', 'extracted_metadata',
  'extracted_dimensions', 'extracted_parameters',
  'extracted_materials', 'extracted_bom_items',
  'cad_models', 'cad_model_embeddings',
  'cad_assembly_relations', 'cad_manufacturing_features',
  'cad_rendered_views'
);
```

**Risk:** Migration incomplete
**Mitigation:** Run `alembic upgrade head` if tables missing

---

#### Task 00.2: Create Job Coordination Columns (10 min)
**File:** `unified-doc-intelligence-deploy/scripts/add-job-coordination.sql` (CREATE)

**Steps:**
1. Create SQL migration script
2. Add columns to `extraction_jobs`:
   - `claimed_by VARCHAR(100)`
   - `claimed_at TIMESTAMP`
   - `heartbeat TIMESTAMP`
   - `retry_count INT DEFAULT 0`
   - `last_error TEXT`
3. Create index on `claimed_by`
4. Run migration on VM1

**SQL:**
```sql
ALTER TABLE extraction_jobs ADD COLUMN IF NOT EXISTS claimed_by VARCHAR(100);
ALTER TABLE extraction_jobs ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP;
ALTER TABLE extraction_jobs ADD COLUMN IF NOT EXISTS heartbeat TIMESTAMP;
ALTER TABLE extraction_jobs ADD COLUMN IF NOT EXISTS retry_count INT DEFAULT 0;
ALTER TABLE extraction_jobs ADD COLUMN IF NOT EXISTS last_error TEXT;

CREATE INDEX IF NOT EXISTS idx_jobs_claimed
ON extraction_jobs(claimed_by)
WHERE claimed_by IS NOT NULL;
```

**Exit criteria:** Columns and index created successfully

---

#### Task 00.3: Deploy Code to All VMs (5 min)
**Steps:**
1. Copy `unified-doc-intelligence-deploy/` to all 5 VMs
2. Verify `config.txt` synchronized (same DB_URL, B2 credentials)
3. Create output/logs directories

**Commands (from local machine):**
```bash
# Ubuntu VMs
scp -r unified-doc-intelligence-deploy user@vm1-ubuntu:/path/to/
scp -r unified-doc-intelligence-deploy user@vm2-ubuntu:/path/to/

# Windows VMs (use WinSCP or rsync)
scp -r unified-doc-intelligence-deploy user@vm3-windows:/path/to/
scp -r unified-doc-intelligence-deploy user@vm4-windows:/path/to/
scp -r unified-doc-intelligence-deploy user@vm5-windows:/path/to/
```

**Exit criteria:** Code deployed on all 5 VMs

---

## Phase 01: Database Verification + Phase A Execution

**Duration:** 2 hours
**VM:** VM1 (Ubuntu Basic)
**Dependencies:** Phase 00 complete

### Objectives
- Run final database verification
- Execute Phase A (auto-linking)
- Validate document groups created
- Trigger Phase B start

### Tasks

#### Task 01.1: Final Database Verification (15 min)
**Steps:**
1. Run `verify-migration.py`
2. Check database connection pool settings
3. Verify B2 bucket access
4. **Exit criteria:** All systems go

**Commands:**
```bash
cd unified-doc-intelligence-deploy
python scripts/verify-migration.py
```

---

#### Task 01.2: Execute Phase A - Auto-Linking (1 hour 30 min)
**File:** `unified-doc-intelligence-deploy/run-pipeline.py`

**Steps:**
1. Run Phase A scripts sequentially
2. Monitor progress via logs
3. Verify document_groups created

**Commands:**
```bash
python run-pipeline.py --phase a
```

**Scripts executed:**
- A1: Schema Migration
- A2: Link by Basename
- A3: Link by Folder
- A4: Extract Project Codes
- A5: Flag Review Queue
- A6: Generate Link Report

**Exit criteria:** A6 completes successfully

---

#### Task 01.3: Validate Phase A Results (15 min)
**Validation queries:**
```sql
-- Check document groups created
SELECT COUNT(*) AS doc_groups FROM document_groups;
-- Expected: > 0

-- Check group members
SELECT COUNT(*) AS group_members FROM document_group_members;
-- Expected: > 0

-- Check for errors
SELECT COUNT(*) AS flagged FROM document_groups WHERE needs_review = true;
-- Expected: Low count (< 5% of total)
```

**Exit criteria:**
- Document groups > 0
- No critical errors

**Risk:** Linking fails
**Mitigation:** Check logs, fix data issues, retry

---

## Phase 02: Phase B - Parallel PDF/DXF Extraction

**Duration:** 8 hours
**VMs:** VM2 (Ubuntu), VM3 (Windows)
**Dependencies:** Phase 01 complete

### Objectives
- Create extraction tables
- Queue extraction jobs
- Parallel PDF + DXF extraction
- Index extracted data

### VM2 Tasks (Ubuntu - Phase B Primary)

#### Task 02.1: Create Extraction Tables + Queue Jobs (15 min)
**Steps:**
1. Run B1 (create tables)
2. Run B2 (queue jobs)
3. Verify job queue populated

**Commands:**
```bash
cd unified-doc-intelligence-deploy
python scripts/phase-b-extraction/B1-create-extraction-tables.py
python scripts/phase-b-extraction/B2-queue-extraction-jobs.py
```

**Exit criteria:** Jobs queued (COUNT(*) from extraction_jobs > 0)

---

#### Task 02.2: Start PDF Worker + Text Indexer (7 hours 30 min)
**File:** `unified-doc-intelligence-deploy/scripts/phase-b-extraction/B3-pdf-extraction-worker.py` (MODIFY)

**Modifications needed:**
1. Add job claiming logic
2. Add heartbeat updates
3. Add retry mechanism

**New functions to add:**
```python
def claim_jobs(db_conn, worker_id, job_type, limit=50):
    """Atomically claim unclaimed jobs."""
    with db_conn.cursor() as cur:
        cur.execute("""
            UPDATE extraction_jobs
            SET claimed_by = %s,
                claimed_at = NOW(),
                heartbeat = NOW()
            WHERE id IN (
                SELECT id FROM extraction_jobs
                WHERE status = 'pending'
                AND job_type = %s
                AND claimed_by IS NULL
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id, file_id
        """, (worker_id, job_type, limit))
        return cur.fetchall()

def update_heartbeat(db_conn, worker_id):
    """Update worker heartbeat."""
    with db_conn.cursor() as cur:
        cur.execute("""
            UPDATE extraction_jobs
            SET heartbeat = NOW()
            WHERE claimed_by = %s
        """, (worker_id,))

def requeue_stalled_jobs(db_conn, timeout_sec=300):
    """Requeue stalled jobs."""
    with db_conn.cursor() as cur:
        cur.execute("""
            UPDATE extraction_jobs
            SET claimed_by = NULL,
                claimed_at = NULL,
                heartbeat = NULL,
                retry_count = retry_count + 1,
                last_error = 'Worker timeout'
            WHERE claimed_by IS NOT NULL
            AND heartbeat < NOW() - INTERVAL '%s seconds'
            AND retry_count < 3
        """, (timeout_sec,))
```

**Commands:**
```bash
# Terminal 1: PDF worker (30 workers)
python scripts/phase-b-extraction/B3-pdf-extraction-worker.py --workers 30

# Terminal 2: Text indexer (15 workers)
python scripts/phase-b-extraction/B8-index-text.py --workers 15
```

**Exit criteria:** < 5% pending jobs remain

---

### VM3 Tasks (Windows - Phase B Secondary)

#### Task 02.3: Start DXF Worker + Block Indexer (7 hours 30 min)
**File:** `unified-doc-intelligence-deploy/scripts/phase-b-extraction/B4-dxf-extraction-worker.py` (MODIFY)

**Same modifications as B3:**
1. Add job claiming logic
2. Add heartbeat updates
3. Add retry mechanism

**Commands:**
```bash
# Terminal 1: DXF worker (30 workers)
python scripts\phase-b-extraction\B4-dxf-extraction-worker.py --workers 30

# Terminal 2: Block indexer (15 workers)
python scripts\phase-b-extraction\B9-index-blocks.py --workers 15
```

**Exit criteria:** < 5% pending jobs remain

---

#### Task 02.4: Run Indexing Scripts (Both VMs) (30 min)
**When queue < 5% pending:**

**VM2:**
```bash
python scripts/phase-b-extraction/B5-index-dimensions.py
python scripts/phase-b-extraction/B6-index-materials.py
```

**VM3:**
```bash
python scripts/phase-b-extraction/B7-extraction-report.py
python scripts/phase-b-extraction/B10-update-metadata-fields.py
```

**Exit criteria:** All indexing complete

---

#### Task 02.5: Validate Phase B Results (15 min)
**Validation queries:**
```sql
-- Overall progress
SELECT
  status,
  COUNT(*) AS count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct
FROM extraction_jobs
GROUP BY status
ORDER BY status;

-- Extraction quality
SELECT
  job_type,
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE parameters IS NOT NULL AND jsonb_array_length(parameters) > 0) AS has_params,
  COUNT(*) FILTER (WHERE last_error IS NOT NULL) AS failed
FROM extraction_jobs
GROUP BY job_type;

-- Worker activity
SELECT
  claimed_by,
  COUNT(*) AS jobs_claimed,
  MAX(heartbeat) AS last_heartbeat,
  NOW() - MAX(heartbeat) AS stall_time
FROM extraction_jobs
WHERE claimed_by IS NOT NULL
GROUP BY claimed_by
ORDER BY stall_time DESC;
```

**Exit criteria:**
- > 95% jobs completed
- < 3% failed
- No stalled workers

**Risk:** Extraction failures > 5%
**Mitigation:** Check error logs, fix specific issues, requeue failed jobs

---

## Phase 03: Phase D - Parallel CAD Extraction

**Duration:** 12 hours
**VMs:** VM4 (Windows), VM5 (Windows)
**Dependencies:** Phase 02 complete

### Objectives
- Queue CAD jobs
- Parallel Creo extraction (gRPC mode)
- Fallback to JSON if gRPC fails
- Index CAD parameters

### VM4 Tasks (Windows - Phase D Primary)

#### Task 03.1: Queue CAD Jobs (15 min)
**Steps:**
1. Run D1 to queue CAD jobs
2. Verify queue populated

**Commands:**
```bash
cd unified-doc-intelligence-deploy
python scripts\phase-d-cad-extraction\D1-queue-cad-jobs.py
```

**Exit criteria:** CAD jobs queued

---

#### Task 03.2: Start Enhanced Creo Worker (10 hours)
**File:** `unified-doc-intelligence-deploy/scripts/phase-d-cad-extraction/D2-creo-extraction-enhanced.py` (READY)

**Steps:**
1. Verify Creo gRPC service running
2. Start enhanced worker with `mode="grpc"`
3. Monitor for failures

**Commands:**
```bash
# Terminal 1: Enhanced Creo worker (10 concurrent)
python scripts\phase-d-cad-extraction\D2-creo-extraction-enhanced.py --workers 10 --mode grpc
```

**Monitoring queries:**
```sql
-- Creo extraction progress
SELECT
  extraction_mode,
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE brep_genome IS NOT NULL) AS has_brep,
  COUNT(*) FILTER (WHERE point_cloud IS NOT NULL) AS has_pointcloud,
  AVG(face_count) FILTER (WHERE face_count > 0) AS avg_faces
FROM cad_models
GROUP BY extraction_mode;
```

**Exit criteria:** < 5% pending CAD jobs

**Risk:** gRPC failures > 10%
**Mitigation:** Auto-switch to JSON mode (VM5 Task 03.4)

---

#### Task 03.3: Index CAD Parameters (1 hour)
**When queue < 5% pending:**

**Commands:**
```bash
python scripts\phase-d-cad-extraction\D5-index-cad-parameters.py
```

**Exit criteria:** Parameter indexing complete

---

#### Task 03.4: Generate CAD Report (30 min)
**Commands:**
```bash
python scripts\phase-d-cad-extraction\D6-cad-extraction-report.py
```

**Exit criteria:** Report generated

---

### VM5 Tasks (Windows - Phase D Secondary + Coordination)

#### Task 03.5: Start Enhanced Creo Worker (10 hours)
**Same as VM4:**

**Commands:**
```bash
# Terminal 1: Enhanced Creo worker (10 concurrent)
python scripts\phase-d-cad-extraction\D2-creo-extraction-enhanced.py --workers 10 --mode grpc
```

---

#### Task 03.6: JSON Fallback Importer (Ongoing)
**File:** `unified-doc-intelligence-deploy/scripts/phase-d-cad-extraction/D3-creo-json-importer.py`

**Trigger conditions:**
- gRPC failure rate > 10%
- Manual intervention

**Commands:**
```bash
# Terminal 2: JSON fallback (monitor gRPC failures)
python scripts\phase-d-cad-extraction\D3-creo-json-importer.py --auto-fallback
```

**Exit criteria:** All gRPC failures imported via JSON

---

#### Task 03.7: Link CAD to Documents (30 min)
**Commands:**
```bash
python scripts\phase-d-cad-extraction\D4-link-cad-to-documents.py
```

**Exit criteria:** CAD-documents linked

---

#### Task 03.8: Validate Phase D Results (15 min)
**Validation queries:**
```sql
-- CAD extraction quality
SELECT
  COUNT(*) AS total_cad_models,
  COUNT(*) FILTER (WHERE brep_genome IS NOT NULL) AS has_brep,
  COUNT(*) FILTER (WHERE deepsdf_latent IS NOT NULL) AS has_deepsdf,
  COUNT(*) FILTER (WHERE point_cloud IS NOT NULL) AS has_pointcloud,
  AVG(face_count) FILTER (WHERE face_count > 0) AS avg_faces
FROM cad_models;

-- Embedding coverage
SELECT
  embedding_type,
  COUNT(*) AS models_with_embedding,
  COUNT(DISTINCT cad_model_id) AS unique_models
FROM cad_model_embeddings
GROUP BY embedding_type;
```

**Exit criteria:**
- > 80% CAD models have B-Rep genome
- > 70% have point clouds
- No critical failures

**Risk:** Creo extraction fails completely
**Mitigation:** JSON fallback mode processes all jobs

---

## Phase 04: Phase C - Search API Deployment

**Duration:** 1 hour
**VM:** VM5 (Windows)
**Dependencies:** Phase 03 complete

### Objectives
- Run search tests
- Deploy API server
- Validate endpoints

### Tasks

#### Task 04.1: Run Search Tests (30 min)
**Steps:**
1. Run C1-C5 search tests
2. Verify all tests pass

**Commands:**
```bash
cd unified-doc-intelligence-deploy

python scripts\phase-c-search\C1-search-dimensions.py
python scripts\phase-c-search\C2-search-parameters.py
python scripts\phase-c-search\C3-search-materials.py
python scripts\phase-c-search\C4-search-projects.py
python scripts\phase-c-search\C5-search-fulltext.py
```

**Exit criteria:** All tests pass

---

#### Task 04.2: Deploy Search API Server (30 min)
**Steps:**
1. Start uvicorn server
2. Verify Swagger UI accessible
3. Test health endpoint

**Commands:**
```bash
# Start API server (background)
uvicorn scripts.phase_c_search.C6_search_api_server:app --host 0.0.0.0 --port 8080 --workers 4
```

**Validation:**
```bash
# Health check
curl http://localhost:8080/

# Swagger UI
# Open browser: http://localhost:8080/docs
```

**Exit criteria:** API server responding

---

## Phase 05: Post-Deployment Validation & Reporting

**Duration:** 2 hours
**VMs:** All 5 VMs
**Dependencies:** Phase 04 complete

### Objectives
- Generate final reports
- Validate data quality
- Document success metrics
- Cleanup temporary resources

### Tasks

#### Task 05.1: Generate Final Reports (30 min)
**VM1:**
```bash
python scripts/phase-a-linking/A6-generate-link-report.py
```

**VM3:**
```bash
python scripts/phase-b-extraction/B7-extraction-report.py
```

**VM4:**
```bash
python scripts/phase-d-cad-extraction/D6-cad-extraction-report.py
```

**Exit criteria:** All reports generated

---

#### Task 05.2: Data Quality Validation (1 hour)
**Validation queries:**

```sql
-- 1. Overall extraction progress
SELECT
  phase,
  COUNT(*) FILTER (WHERE status = 'pending') AS pending,
  COUNT(*) FILTER (WHERE status = 'processing') AS processing,
  COUNT(*) FILTER (WHERE status = 'completed') AS completed,
  COUNT(*) FILTER (WHERE status = 'failed') AS failed,
  ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'completed') / COUNT(*), 1) AS progress_pct
FROM (
  SELECT 'Phase B' AS phase, status FROM extraction_jobs
  UNION ALL
  SELECT 'Phase D', status FROM cad_models
) jobs
GROUP BY phase;

-- 2. Extraction quality metrics
SELECT
  job_type,
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE parameters IS NOT NULL AND jsonb_array_length(parameters) > 0) AS has_params,
  COUNT(*) FILTER (WHERE bom IS NOT NULL AND jsonb_array_length(bom) > 0) AS has_bom,
  COUNT(*) FILTER (WHERE last_error IS NOT NULL) AS failed
FROM extraction_jobs
GROUP BY job_type;

-- 3. CAD genome extraction quality
SELECT
  COUNT(*) AS total_cad_models,
  COUNT(*) FILTER (WHERE brep_genome IS NOT NULL) AS has_brep,
  COUNT(*) FILTER (WHERE deepsdf_latent IS NOT NULL) AS has_deepsdf,
  COUNT(*) FILTER (WHERE point_cloud IS NOT NULL) AS has_pointcloud,
  AVG(face_count) FILTER (WHERE face_count > 0) AS avg_faces
FROM cad_models;

-- 4. Embedding coverage
SELECT
  embedding_type,
  COUNT(*) AS models_with_embedding,
  COUNT(DISTINCT cad_model_id) AS unique_models
FROM cad_model_embeddings
GROUP BY embedding_type;

-- 5. Worker health check
SELECT
  claimed_by,
  COUNT(*) AS jobs_claimed,
  MAX(heartbeat) AS last_heartbeat,
  NOW() - MAX(heartbeat) AS stall_time
FROM extraction_jobs
WHERE claimed_by IS NOT NULL
GROUP BY claimed_by
ORDER BY stall_time DESC;
```

**Success criteria:**
- ✅ 95%+ files processed without errors
- ✅ 90%+ PDFs have extracted text
- ✅ 85%+ DXFs have extracted dimensions
- ✅ 80%+ CAD models have B-Rep genome
- ✅ 70%+ CAD models have point clouds
- ✅ Zero data loss
- ✅ < 3% duplicate processing

**Exit criteria:** All success criteria met

---

#### Task 05.3: Cleanup & Documentation (30 min)
**Steps:**
1. Stop all workers gracefully
2. Clean up temp directories
3. Archive logs
4. Document any issues

**Commands:**
```bash
# On all VMs
# Stop workers (Ctrl+C or kill)
# Clean temp
rm -rf /tmp/extraction-*

# Archive logs
tar -czf logs-$(date +%Y%m%d).tar.gz logs/
```

**Exit criteria:** All workers stopped, logs archived

---

## Success Metrics

### Extraction Quality Targets
- 95%+ files processed without errors
- 90%+ PDFs have extracted text
- 85%+ DXFs have extracted dimensions
- 80%+ CAD models have B-Rep genome
- 70%+ CAD models have point clouds

### Performance Targets
- Phase A: < 2 hours
- Phase B: < 8 hours
- Phase D: < 12 hours
- Phase C: < 1 hour
- Total: < 24 hours

### System Health
- Zero data loss
- < 3% duplicate processing
- Worker heartbeat < 5 min intervals
- Database connection pool < 80% capacity

---

## Risk Assessment & Mitigation

### High Risks

#### Risk 1: Creo gRPC Service Unavailability
**Probability:** Medium
**Impact:** High
**Mitigation:**
- JSON fallback mode (D3 importer)
- 10% failure rate triggers auto-switch
- Pre-test gRPC connectivity before Phase D

**Recovery plan:**
1. Monitor gRPC failure rate
2. At 10% failures, auto-switch to JSON
3. Process remaining jobs via JSON importer

---

#### Risk 2: Database Connection Pool Exhaustion
**Probability:** Medium
**Impact:** High
**Mitigation:**
- Limit workers to 30 per VM (total 150)
- Monitor `pg_stat_activity`
- Configure pool size in connection strings

**Recovery plan:**
1. Detect pool exhaustion via monitoring
2. Reduce worker count by 50%
3. Restart workers with new limits

---

#### Risk 3: B2 Storage Rate Limits
**Probability:** Low
**Impact:** Medium
**Mitigation:**
- Exponential backoff (1s → 60s)
- Monitor HTTP 429/503 errors
- Implement request throttling

**Recovery plan:**
1. Detect rate limit errors
2. Increase backoff intervals
3. Reduce concurrent downloads

---

### Medium Risks

#### Risk 4: Worker Stalls (Creo Timeout)
**Probability:** Medium
**Impact:** Medium
**Mitigation:**
- 5-minute timeout
- Heartbeat monitoring
- Auto-requeue after 3 attempts

**Recovery plan:**
1. Heartbeat monitor detects stall
2. Auto-requeue stalled jobs
3. Limit retry attempts to 3

---

#### Risk 5: Disk Space (Temporary Downloads)
**Probability:** Low
**Impact:** Medium
**Mitigation:**
- Clean up `/tmp` after each file
- Monitor disk usage
- Alert at 80% capacity

**Recovery plan:**
1. Detect low disk space
2. Stop workers
3. Clean temp directories
4. Resume processing

---

### Low Risks

#### Risk 6: Network Partition
**Probability:** Low
**Impact:** Low
**Mitigation:**
- Local checkpoint files
- Resume on reconnect
- Workers requeue jobs on restart

**Recovery plan:**
1. Detect network partition
2. Workers pause with checkpoint
3. On reconnect, resume from checkpoint

---

## Rollback Plan

### Phase 00-01 Rollback
**Trigger:** Database migration fails
**Actions:**
1. Stop all VMs
2. Restore database from backup
3. Fix migration issues
4. Re-run migration

### Phase 02 Rollback
**Trigger:** Extraction failures > 20%
**Actions:**
1. Stop workers on VM2/VM3
2. Analyze failure patterns
3. Fix specific issues
4. Requeue failed jobs

### Phase 03 Rollback
**Trigger:** Creo gRPC complete failure
**Actions:**
1. Stop gRPC workers
2. Switch to JSON mode on VM5
3. Process all jobs via JSON importer
4. Document gRPC issues

### Phase 04 Rollback
**Trigger:** API deployment fails
**Actions:**
1. Stop API server
2. Fix deployment issues
3. Re-run search tests
4. Restart API server

---

## Monitoring & Alerting

### Real-Time Monitoring Queries

See Phase 05 Task 05.2 for complete validation queries.

### Log Files to Monitor

**VM1:**
- `logs/A1-*.log` through `logs/A6-*.log`

**VM2:**
- `logs/B3-pdf-worker.log`
- `logs/B8-text-indexer.log`
- `logs/B5-index-dimensions.log`
- `logs/B6-index-materials.log`

**VM3:**
- `logs/B4-dxf-worker.log`
- `logs/B9-block-indexer.log`
- `logs/B7-extraction-report.log`
- `logs/B10-update-metadata.log`

**VM4:**
- `logs/D2-creo-worker-1.log`
- `logs/D5-index-parameters.log`
- `logs/D6-cad-report.log`

**VM5:**
- `logs/D2-creo-worker-2.log`
- `logs/D3-json-importer.log`
- `logs/D4-link-cad-docs.log`
- `logs/C1-C5-tests.log`
- `logs/C6-api-server.log`

### Alerting Thresholds

**Critical alerts (immediate action):**
- Extraction failure rate > 20%
- Database connection pool > 90%
- Disk usage > 90%
- Creo gRPC service down

**Warning alerts (monitor closely):**
- Extraction failure rate > 10%
- Worker heartbeat stall > 5 min
- Disk usage > 80%
- B2 rate limit errors

---

## Unresolved Questions

1. **Creo gRPC Service Stability**
   - What's the historical uptime?
   - Known bottlenecks with 10 concurrent connections?
   - **Decision point:** Pre-test in Phase 00

2. **DeepSDF Latent Encoding**
   - Is DeepSDF model trained?
   - Should we postpone deepsdf_latent extraction?
   - **Decision point:** Phase 03 planning

3. **B2 Storage Performance**
   - Actual download speeds from EmjacDB?
   - Throttling during high concurrency?
   - **Decision point:** Phase 02 monitoring

4. **Fallback Trigger Threshold**
   - At what failure rate switch gRPC → JSON? (5%? 10%?)
   - **Decision point:** Phase 03 monitoring

---

## Next Steps

1. **Complete Phase 00** - Pre-deployment setup
2. **Execute Phase 01** - Database verification + Phase A
3. **Monitor Phase 02** - PDF/DXF extraction
4. **Execute Phase 03** - CAD extraction with fallback
5. **Deploy Phase 04** - Search API
6. **Validate Phase 05** - Final reporting

---

## Appendix: File Modifications Summary

### Files to Create
1. `scripts/verify-migration.py` - Database verification script
2. `scripts/add-job-coordination.sql` - Job coordination migration
3. `scripts/monitoring-dashboard.sql` - Real-time monitoring queries

### Files to Modify
1. `scripts/phase-b-extraction/B3-pdf-extraction-worker.py`
   - Add `claim_jobs()` function
   - Add `update_heartbeat()` function
   - Add `requeue_stalled_jobs()` function
   - Integrate into worker loop

2. `scripts/phase-b-extraction/B4-dxf-extraction-worker.py`
   - Same modifications as B3

3. `scripts/phase-d-cad-extraction/D2-creo-extraction-worker.py`
   - Replace placeholder with enhanced extraction
   - Import from `D2-creo-extraction-enhanced.py`

### Files Ready to Use
1. `scripts/phase-d-cad-extraction/D2-creo-extraction-enhanced.py`
2. `scripts/phase-d-cad-extraction/D3-creo-json-importer.py`
3. All Phase A, C scripts
4. All indexing scripts (B5-B10, D5-D6)

---

*End of implementation plan. Ready for execution.*
