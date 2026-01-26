# Extraction Process Redo - Optimization Analysis

**Date:** 2026-01-23
**Agent:** Brainstormer
**Status:** Complete

---

## Problem Statement

Need to redo extraction process for 500K-1M files across 5 VMs (2 Ubuntu basic, 3 Windows high-performance). Goals: **Better data quality** via new extraction tech (enhanced Creo, CAD indexing, embeddings) with **reliability-critical** tolerance.

---

## Current Architecture Analysis

### Pipeline Structure
```
Phase A: Auto-Linking (6 scripts)
  ├─ A1: Schema Migration
  ├─ A2-A5: Linking & grouping logic
  └─ A6: Generate link report

Phase B: PDF/DXF Extraction (10 scripts)
  ├─ B1: Create extraction tables
  ├─ B2: Queue extraction jobs
  ├─ B3-B4: Workers (PDF/DXF) - NEW: B8-B9 for text/blocks
  ├─ B5-B7: Indexing & reporting

Phase C: Search API (6 scripts)
  ├─ C1-C5: Search tests
  └─ C6: Start API server

Phase D: CAD Extraction (6 scripts)
  ├─ D1: Queue CAD jobs
  ├─ D2: Creo worker (ENHANCED)
  ├─ D3: JSON importer
  ├─ D4: Link CAD to documents
  ├─ D5: Index CAD parameters
  └─ D6: CAD extraction report
```

### Database Schema Status
**Migrated Tables:**
- ✅ `cad_models` (dual-representation: B-Rep + DeepSDF)
- ✅ `cad_model_embeddings` (7 embedding types with HNSW)
- ✅ `cad_assembly_relations` (hierarchy)
- ✅ `cad_manufacturing_features`
- ✅ `cad_rendered_views`

**Legacy Tables (need verification):**
- ❓ `document_groups`, `document_group_members`
- ❓ `extraction_jobs`, `extracted_metadata`
- ❓ `extracted_dimensions`, `extracted_parameters`
- ❓ `extracted_materials`, `extracted_bom_items`

### New Extraction Technologies Available
1. **Enhanced Creo Extraction** (`D2-creo-extraction-enhanced.py`)
   - B-Rep graph extraction (face adjacency, UV grids)
   - Point cloud generation (2048-point normalized)
   - DeepSDF training data (infrastructure ready)
   - Modes: gRPC (live), JSON (pre-extracted), auto

2. **CAD Indexing Pipeline** (`src/pybase/services/cad_indexing_pipeline.py`)
   - Multi-modal embeddings (B-Rep, CLIP text/image, geometry, fused)
   - Integration with pgvector/HNSW indexes
   - Assembly hierarchy support

3. **Bulk Extraction Services** (`src/pybase/services/`)
   - `bulk_extraction.py` - Parallel processing
   - `extraction.py` - Core extraction logic
   - `embedding_generator.py` - Vector generation

---

## Bottleneck Analysis

### Current Pipeline Issues

1. **Sequential Phase Dependencies**
   - Phase B workers run indefinitely (no completion signal)
   - No parallel execution between phases
   - Workers don't coordinate across VMs

2. **No Job Coordination**
   - Each worker polls database independently
   - Potential duplicate processing
   - No progress tracking between VMs

3. **Limited Retry Logic**
   - Single failure point per file
   - No exponential backoff
   - Failed jobs not requeued automatically

4. **Resource Underutilization**
   - 5 VMs but only 4 phases
   - No phase B parallelization (PDF vs DXF workers)
   - Ubuntu VMs underutilized (CAD extraction is Windows-only)

---

## Optimization Approaches Evaluated

### Approach 1: Single Pipeline per Phase (Status Quo)
**Distribution:**
- VM1 (Ubuntu): Phase A
- VM2 (Ubuntu): Phase B (PDF worker)
- VM3 (Windows): Phase B (DXF worker)
- VM4 (Windows): Phase D (Creo extraction)
- VM5 (Windows): Phase C (API)

**Pros:**
- Simple, no code changes
- Clear separation of concerns
- Easy to debug

**Cons:**
- VM2/VM3 both doing Phase B (redundant setup)
- VM4 sits idle after Phase D completes
- No parallelization within phases
- Estimated time: 12-18 hours sequential

**Verdict:** ❌ Not optimal for VM utilization

---

### Approach 2: Parallel Workers within Phases
**Distribution:**
- VM1 (Ubuntu): Phase A → Phase B PDF worker (20 workers)
- VM2 (Ubuntu): Phase B DXF worker (20 workers)
- VM3 (Windows): Phase D (Creo gRPC, 10 concurrent)
- VM4 (Windows): Phase D (Creo gRPC, 10 concurrent)
- VM5 (Windows): Phase C + monitoring

**Pros:**
- Better utilization (all 5 VMs active)
- Parallel CAD extraction (2x faster)
- Independent worker scaling

**Cons:**
- Requires worker coordination (job partitioning)
- Need to prevent duplicate processing
- Complex setup

**Verdict:** ⚠️ Better but needs job deduplication

---

### Approach 3: Optimized Distribution with Checkpoints (RECOMMENDED)
**Distribution:**
- **VM1 (Ubuntu Basic):** Phase A + Validation
  - Run A1-A6 (linking)
  - Validate document_groups created
  - Trigger Phase B start

- **VM2 (Ubuntu Basic):** Phase B Primary
  - Run B1-B2 (setup + queue jobs)
  - Start B3 PDF worker (30 workers)
  - Start B8 text indexer (15 workers)
  - Monitor queue drain

- **VM3 (Windows High):** Phase B Secondary
  - Run B4 DXF worker (30 workers)
  - Run B9 block indexer (15 workers)
  - B5-B7 indexing when queue empty

- **VM4 (Windows High):** Phase D Primary (Creo)
  - Run D1 (queue CAD jobs)
  - Run D2 enhanced Creo worker (10 concurrent, gRPC mode)
  - D5 parameter indexing
  - D6 reporting

- **VM5 (Windows High):** Phase D Secondary + Coordination
  - Run D2 enhanced Creo worker (10 concurrent, gRPC mode)
  - D3 JSON importer (fallback for gRPC failures)
  - D4 document linking
  - Phase C startup after D completion

**Pros:**
- Optimal VM utilization (Ubuntu for I/O, Windows for compute)
- Parallel CAD extraction (2x Creo workers)
- Checkpoint-based validation between phases
- Fallback mechanism (gRPC → JSON)
- Dedicated coordinator (VM5)

**Cons:**
- Requires checkpoint scripts
- Need coordination mechanism
- More complex deployment

**Verdict:** ✅ **BEST** - Maximizes throughput with reliability

---

## Database Migration Verification

### Pre-Extraction Checklist

```sql
-- 1. Verify all tables exist
SELECT table_name
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
)
ORDER BY table_name;

-- Expected: 14 tables

-- 2. Check CAD table structure (dual-representation)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'cad_models'
AND column_name IN ('brep_genome', 'deepsdf_latent', 'point_cloud')
ORDER BY ordinal_position;

-- Expected: 3 rows (jsonb, array[], jsonb)

-- 3. Verify HNSW indexes exist
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'cad_model_embeddings'
AND indexdef LIKE '%USING hnsw%';

-- Expected: 6 indexes (one per embedding type)

-- 4. Check pgvector extension
SELECT extname FROM pg_extension WHERE extname = 'vector';

-- Expected: 1 row

-- 5. Verify foreign keys
SELECT constraint_name
FROM information_schema.table_constraints
WHERE table_schema = 'pybase'
AND constraint_type = 'FOREIGN KEY';

-- Expected: Multiple FKs linking cad_models to workspaces/users
```

### Validation Script
Create `scripts/verify-migration.py`:
```python
#!/usr/bin/env python3
"""
Verify database migration before extraction.
Exits with error if any check fails.
"""
import psycopg2
import sys

def verify_migration(db_url):
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Check tables
    cur.execute("""
        SELECT COUNT(DISTINCT table_name)
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN (%s)
    """, (['document_groups', 'cad_models', 'cad_model_embeddings', ...]))

    table_count = cur.fetchone()[0]
    if table_count < 14:
        print(f"❌ Only {table_count}/14 tables found")
        return False

    # Check pgvector
    cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    if not cur.fetchone():
        print("❌ pgvector extension not found")
        return False

    # Check HNSW indexes
    cur.execute("""
        SELECT COUNT(*) FROM pg_indexes
        WHERE tablename = 'cad_model_embeddings'
        AND indexdef LIKE '%USING hnsw%'
    """)
    index_count = cur.fetchone()[0]
    if index_count < 6:
        print(f"⚠️  Only {index_count}/6 HNSW indexes found")

    print("✅ Migration verified")
    return True
```

---

## ONE Enhancement & Efficiency Improvement

### Enhancement: **Job Coordination with Checkpoint System**

**Problem:** Workers poll independently, no coordination, duplicate processing risk.

**Solution:** Implement a lightweight job coordinator with:
1. **Worker Registry** - Track active workers per job type
2. **Job Claiming** - Atomic UPDATE with worker_id
3. **Heartbeats** - Detect stalled workers
4. **Checkpoints** - Phase completion validation

**Implementation:**

```sql
-- Add to extraction_jobs table
ALTER TABLE extraction_jobs ADD COLUMN claimed_by VARCHAR(100);
ALTER TABLE extraction_jobs ADD COLUMN claimed_at TIMESTAMP;
ALTER TABLE extraction_jobs ADD COLUMN heartbeat TIMESTAMP;
ALTER TABLE extraction_jobs ADD COLUMN retry_count INT DEFAULT 0;
ALTER TABLE extraction_jobs ADD COLUMN last_error TEXT;

CREATE INDEX idx_jobs_claimed ON extraction_jobs(claimed_by) WHERE claimed_by IS NOT NULL;
```

**Worker Pattern:**
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
    """Requeue jobs with stale heartbeats."""
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

**Efficiency Gain:**
- ✅ Eliminates duplicate processing (atomic claiming)
- ✅ Auto-retry stalled jobs (3 attempts)
- ✅ Worker failure detection (heartbeat monitoring)
- ✅ Progress tracking (claimed vs pending)
- **Estimated speedup:** 20-30% (no wasted work)

---

## Recommended VM Distribution (Final)

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE A: LINKING                             │
├─────────────────────────────────────────────────────────────────┤
│ VM1 (Ubuntu)                                                    │
│   ├─ A1: Schema Migration                                      │
│   ├─ A2-A5: Linking logic                                      │
│   └─ A6: Generate report                                       │
│   CHECKPOINT: Verify document_groups > 0                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              PHASE B: PDF/DXF EXTRACTION (Parallel)              │
├─────────────────────────────────────────────────────────────────┤
│ VM2 (Ubuntu)                    VM3 (Windows)                   │
│   ├─ B1: Create tables              └─ B4: DXF worker (30)     │
│   ├─ B2: Queue jobs                    ├─ B9: Block idx (15)   │
│   ├─ B3: PDF worker (30)               └─ B5-B7: Indexing     │
│   └─ B8: Text idx (15)                                          │
│   CHECKPOINT: extraction_jobs status = 'completed' > 95%        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              PHASE D: CAD EXTRACTION (Parallel - gRPC)           │
├─────────────────────────────────────────────────────────────────┤
│ VM4 (Windows)                   VM5 (Windows)                   │
│   ├─ D1: Queue CAD jobs              ├─ D2: Creo worker (10)   │
│   ├─ D2: Creo worker (10)            ├─ D3: JSON fallback      │
│   ├─ D5: Parameter idx               ├─ D4: Document linking   │
│   └─ D6: Reporting                   └─ Phase C prep           │
│   CHECKPOINT: cad_models count matches queued jobs              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE C: SEARCH API                           │
├─────────────────────────────────────────────────────────────────┤
│ VM5 (Windows)                                                    │
│   ├─ C1-C5: Search tests                                       │
│   └─ C6: API server (uvicorn)                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Checklist

### Pre-Run (All VMs)
- [ ] Copy `unified-doc-intelligence-deploy/` to all 5 VMs
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Sync `config.txt` (same DB_URL, B2 credentials on all VMs)
- [ ] Run `verify-migration.py` on VM1
- [ ] Create `extraction_jobs` table columns (claimed_by, heartbeat, etc.)

### Phase A - VM1 Only
- [ ] Run: `python run-pipeline.py --phase a`
- [ ] Verify: `SELECT COUNT(*) FROM document_groups` > 0
- [ ] Trigger Phase B start (manual signal or database flag)

### Phase B - VM2 + VM3 (Parallel)
- [ ] VM2: Start PDF worker + text indexer
- [ ] VM3: Start DXF worker + block indexer
- [ ] Monitor: `SELECT status, COUNT(*) FROM extraction_jobs GROUP BY 1`
- [ ] Wait for < 5% pending jobs
- [ ] Run B5-B7 indexing on both VMs

### Phase D - VM4 + VM5 (Parallel)
- [ ] Verify Creo gRPC service running on both Windows VMs
- [ ] Run D1 to queue CAD jobs
- [ ] Start D2 workers with `mode="grpc"` on both VMs
- [ ] Monitor: `SELECT COUNT(*) FROM cad_models WHERE extraction_mode = 'grpc'`
- [ ] VM4: Run D5 parameter indexing
- [ ] VM5: Run D3 JSON importer (fallback), D4 linking
- [ ] VM5: Run D6 reporting

### Phase C - VM5 Only
- [ ] Run C1-C5 search tests
- [ ] Start C6 API server: `uvicorn scripts.C6_search_api_server:app`
- [ ] Verify: `curl http://localhost:8080/docs`

---

## Monitoring & Validation Checkpoints

### Real-Time Monitoring Queries

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

-- 2. Worker activity
SELECT
  claimed_by,
  COUNT(*) AS jobs_claimed,
  MAX(heartbeat) AS last_heartbeat,
  NOW() - MAX(heartbeat) AS stall_time
FROM extraction_jobs
WHERE claimed_by IS NOT NULL
GROUP BY claimed_by
ORDER BY stall_time DESC;

-- 3. Extraction quality metrics
SELECT
  job_type,
  COUNT(*) AS total,
  COUNT(*) FILTER (parameters IS NOT NULL AND jsonb_array_length(parameters) > 0) AS has_params,
  COUNT(*) FILTER (bom IS NOT NULL AND jsonb_array_length(bom) > 0) AS has_bom,
  COUNT(*) FILTER (last_error IS NOT NULL) AS failed
FROM extraction_jobs
GROUP BY job_type;

-- 4. CAD genome extraction quality
SELECT
  COUNT(*) AS total_cad_models,
  COUNT(*) FILTER (brep_genome IS NOT NULL) AS has_brep,
  COUNT(*) FILTER (deepsdf_latent IS NOT NULL) AS has_deepsdf,
  COUNT(*) FILTER (point_cloud IS NOT NULL) AS has_pointcloud,
  AVG(face_count) FILTER (WHERE face_count > 0) AS avg_faces
FROM cad_models;

-- 5. Embedding coverage
SELECT
  embedding_type,
  COUNT(*) AS models_with_embedding,
  COUNT(DISTINCT cad_model_id) AS unique_models
FROM cad_model_embeddings
GROUP BY embedding_type;
```

---

## Risk Assessment

### High Risks
1. **Creo gRPC Service Unavailability**
   - **Mitigation:** JSON fallback mode (D3 importer)
   - **Detection:** 10% failure rate triggers auto-switch

2. **Database Connection Pool Exhaustion**
   - **Mitigation:** Limit workers to 30 per VM (total 150 concurrent)
   - **Detection:** Monitor `pg_stat_activity` counts

3. **B2 Storage Rate Limits**
   - **Mitigation:** Implement exponential backoff (1s → 60s)
   - **Detection:** HTTP 429/503 errors

### Medium Risks
4. **Worker Stalls (Creo Timeout)**
   - **Mitigation:** 5-minute timeout + heartbeat monitor
   - **Recovery:** Auto-requeue after 3 failed attempts

5. **Disk Space (Temporary Downloads)**
   - **Mitigation:** Clean up `/tmp` after each file
   - **Detection:** Alert at 80% disk usage

### Low Risks
6. **Network Partition**
   - **Mitigation:** Local checkpoint files, resume on reconnect
   - **Recovery:** Workers requeue jobs on restart

---

## Success Metrics

### Extraction Quality
- ✅ 95%+ files processed without errors
- ✅ 90%+ PDFs have extracted text
- ✅ 85%+ DXFs have extracted dimensions
- ✅ 80%+ CAD models have B-Rep genome
- ✅ 70%+ CAD models have point clouds

### Performance Targets
- ✅ Phase A: < 2 hours (linking)
- ✅ Phase B: < 8 hours (PDF/DXF)
- ✅ Phase D: < 12 hours (Creo)
- ✅ Total pipeline: < 24 hours

### System Health
- ✅ Zero data loss (all files accounted for)
- ✅ < 3% duplicate processing
- ✅ Worker heartbeat < 5 minute intervals
- ✅ Database connection pool < 80% capacity

---

## Unresolved Questions

1. **Creo gRPC Service Stability**
   - What's the historical uptime of the Creo gRPC service?
   - Are there known bottlenecks with 10 concurrent connections?

2. **DeepSDF Latent Encoding**
   - Is the DeepSDF model trained and ready for inference?
   - If not, should we postpone deepsdf_latent extraction?

3. **B2 Storage Performance**
   - What are the actual download speeds from EmjacDB?
   - Any known throttling during high concurrency?

4. **VM Network Topology**
   - Are all VMs in the same region/datacenter?
   - What's the latency between VMs and Neon PostgreSQL?

5. **Fallback Trigger Threshold**
   - At what failure rate should we switch from gRPC to JSON? (5%? 10%?)

---

## Next Steps

1. **Create Implementation Plan**
   - Detailed task breakdown for each VM
   - Script modifications (job coordination)
   - Deployment sequence

2. **Setup Monitoring**
   - Database dashboard (Grafana/Periscope)
   - Worker log aggregation
   - Alerting (PagerDuty/Slack)

3. **Test Run**
   - Process 1K files as dry-run
   - Validate checkpoint logic
   - Measure baseline performance

4. **Full Execution**
   - Start Phase A on VM1
   - Parallel Phases B/D
   - Monitor and adjust

---

## Recommendations Summary

### DO THIS:
1. **Implement job coordination** (claiming, heartbeats, retries)
2. **Distribute as per Approach 3** (optimized VM assignment)
3. **Add checkpoints** between phases
4. **Monitor with real-time queries**
5. **Use gRPC mode** for Creo with JSON fallback

### DON'T DO THIS:
1. ❌ Run all phases sequentially on one VM (wastes resources)
2. ❌ Skip heartbeat monitoring (risk of silent failures)
3. ❌ Assume database migration worked (verify first)
4. ❌ Start extraction without monitoring (blind execution)
5. ❌ Ignore retry logic (reliability-critical requirement)

### CRITICAL SUCCESS FACTORS:
- **Database verification** before starting
- **Job coordination** to prevent duplicates
- **Checkpoint validation** between phases
- **Real-time monitoring** for early failure detection
- **Fallback mechanism** (gRPC → JSON)

---

*End of brainstorming report. Ready for implementation planning.*
