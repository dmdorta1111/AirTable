# Phases 02-05: Execution Summary

**Complete details in main plan.md**

---

## Phase 02: PDF/DXF Extraction (8 hours)

**VMs:** VM2 (Ubuntu PDF), VM3 (Windows DXF)

### VM2 Tasks
1. **B1-B2:** Create tables, queue jobs (15 min)
2. **B3 + B8:** PDF worker (30) + Text indexer (15) - 7.5 hours
3. **B5-B6:** Index dimensions, materials (30 min)

### VM3 Tasks
1. **B4 + B9:** DXF worker (30) + Block indexer (15) - 7.5 hours
2. **B7 + B10:** Extraction report, metadata update (30 min)

### Validation
```sql
-- Progress > 95% completed
-- Failures < 3%
-- No stalled workers
```

---

## Phase 03: CAD Extraction (12 hours)

**VMs:** VM4, VM5 (Windows - Creo)

### VM4 Tasks
1. **D1:** Queue CAD jobs (15 min)
2. **D2:** Enhanced Creo worker (10 concurrent, gRPC) - 10 hours
3. **D5:** Index CAD parameters (1 hour)
4. **D6:** Generate report (30 min)

### VM5 Tasks
1. **D2:** Enhanced Creo worker (10 concurrent, gRPC) - 10 hours
2. **D3:** JSON fallback importer (monitoring)
3. **D4:** Link CAD to documents (30 min)

### Fallback Trigger
- If gRPC failures > 10% → auto-switch to JSON

### Validation
```sql
-- > 80% CAD models have B-Rep genome
-- > 70% have point clouds
-- No critical failures
```

---

## Phase 04: Search API (1 hour)

**VM:** VM5 (Windows)

### Tasks
1. **C1-C5:** Run search tests (30 min)
2. **C6:** Deploy API server (30 min)

**Command:**
```bash
uvicorn scripts.phase_c_search.C6_search_api_server:app --host 0.0.0.0 --port 8080 --workers 4
```

**Validation:**
```bash
curl http://localhost:8080/
# Browser: http://localhost:8080/docs
```

---

## Phase 05: Final Validation (2 hours)

**VMs:** All 5 VMs

### Tasks
1. Generate all reports (30 min)
2. Data quality validation (1 hour)
3. Cleanup & documentation (30 min)

### Success Criteria
- ✅ 95%+ files processed
- ✅ 90%+ PDFs have text
- ✅ 85%+ DXFs have dimensions
- ✅ 80%+ CAD have B-Rep genome
- ✅ Zero data loss
- ✅ < 3% duplicates

---

## Critical Monitoring Queries

```sql
-- 1. Overall progress
SELECT phase, status, COUNT(*), ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct
FROM (SELECT 'Phase B' AS phase, status FROM extraction_jobs
      UNION ALL SELECT 'Phase D', status FROM cad_models) jobs
GROUP BY phase, status;

-- 2. Worker health
SELECT claimed_by, COUNT(*) AS jobs, MAX(heartbeat) AS last_beat, NOW() - MAX(heartbeat) AS stall
FROM extraction_jobs WHERE claimed_by IS NOT NULL
GROUP BY claimed_by ORDER BY stall DESC;

-- 3. Extraction quality
SELECT job_type, COUNT(*) AS total,
  COUNT(*) FILTER (WHERE parameters IS NOT NULL AND jsonb_array_length(parameters) > 0) AS has_params,
  COUNT(*) FILTER (WHERE last_error IS NOT NULL) AS failed
FROM extraction_jobs GROUP BY job_type;

-- 4. CAD quality
SELECT COUNT(*) AS total,
  COUNT(*) FILTER (WHERE brep_genome IS NOT NULL) AS has_brep,
  COUNT(*) FILTER (WHERE point_cloud IS NOT NULL) AS has_cloud,
  AVG(face_count) FILTER (WHERE face_count > 0) AS avg_faces
FROM cad_models;
```

---

## Risk Response Matrix

| Risk | Trigger | Response |
|------|---------|----------|
| gRPC failures > 10% | Monitoring query | Switch to JSON mode |
| Pool exhaustion > 90% | pg_stat_activity | Reduce workers by 50% |
| Extraction failures > 20% | Status query | Stop, analyze, retry |
| Disk usage > 90% | df -h | Stop workers, clean temp |
| Worker stall > 5 min | Heartbeat query | Auto-requeue jobs |

---

## Rollback Procedures

### Phase 02 Rollback
```bash
# Stop workers
pkill -f B3-pdf-extraction-worker
pkill -f B4-dxf-extraction-worker

# Requeue failed jobs
UPDATE extraction_jobs SET claimed_by = NULL, status = 'pending' WHERE last_error IS NOT NULL;
```

### Phase 03 Rollback
```bash
# Stop Creo workers
pkill -f D2-creo-extraction

# Switch to JSON
python scripts/D3-creo-json-importer.py --process-all
```

---

*See main plan.md for complete details*
