# Phase 01: Database Verification + Phase A Execution

**Duration:** 2 hours
**VM:** VM1 (Ubuntu Basic)
**Dependencies:** Phase 00 complete
**Status:** Pending

---

## Overview

Execute Phase A (auto-linking) to create document groups and establish file relationships. Validate results before triggering Phase B start.

---

## Task 01.1: Final Database Verification

**Duration:** 15 minutes
**Priority:** Critical

### Steps

**Run verification:**
```bash
cd unified-doc-intelligence-deploy
python scripts/verify-migration.py
```

**Test B2 connectivity:**
```python
# Quick B2 test
python -c "
from b2sdk.v2 import InMemoryAccountInfo, B2Api
config = {}
with open('config.txt') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            config[k.strip()] = v.strip()

info = InMemoryAccountInfo()
b2 = B2Api(info)
b2.authorize_account('production', config['B2_APPLICATION_KEY_ID'], config['B2_APPLICATION_KEY'])
bucket = b2.get_bucket_by_name(config['B2_BUCKET_NAME'])
print(f'✅ B2 bucket accessible: {bucket.name}')
"
```

**Test database pool:**
```sql
-- Check connection pool settings
SHOW max_connections;
-- Should be >= 200 for Neon

-- Check current connections
SELECT count(*) FROM pg_stat_activity;
-- Should be low (< 10)
```

### Exit Criteria
- ✅ Migration verification passes
- ✅ B2 bucket accessible
- ✅ Database pool OK

---

## Task 01.2: Execute Phase A - Auto-Linking

**Duration:** 1 hour 30 minutes
**Priority:** High

### Scripts to Execute

Sequential execution of A1 through A6:

#### A1: Schema Migration (5 min)
```bash
python scripts/phase-a-linking/A1-migrate-schema.py
```

**Validates:**
- CloudFiles table exists
- document_groups table structure

#### A2: Link by Basename (20 min)
```bash
python scripts/phase-a-linking/A2-link-by-basename.py
```

**Logic:**
- Groups files by basename (filename without extension)
- Links PDF/DXF with same basename
- Example: `drawing.pdf` + `drawing.dxf` → same group

#### A3: Link by Folder (20 min)
```bash
python scripts/phase-a-linking/A3-link-by-folder.py
```

**Logic:**
- Groups files in same folder
- Creates hierarchical relationships
- Example: `/projectX/subY/` files grouped

#### A4: Extract Project Codes (20 min)
```bash
python scripts/phase-a-linking/A4-extract-project-codes.py
```

**Logic:**
- Extracts project codes from file paths
- Pattern matching (e.g., "PROJ-123-*")
- Tags document groups with project metadata

#### A5: Flag Review Queue (10 min)
```bash
python scripts/phase-a-linking/A5-flag-review-queue.py
```

**Logic:**
- Flags ambiguous groups for review
- Criteria: > 10 files, multiple file types, no clear pattern

#### A6: Generate Link Report (15 min)
```bash
python scripts/phase-a-linking/A6-generate-link-report.py
```

**Output:**
- `output/linking-report-YYYYMMDD-HHMMSS.csv`
- Statistics: groups created, files linked, review flags

### Execution Options

**Option 1: Run all via pipeline script**
```bash
python run-pipeline.py --phase a
```

**Option 2: Run individually**
```bash
# Execute each script separately
for script in scripts/phase-a-linking/A*.py; do
    echo "Running $script"
    python "$script"
done
```

**Option 3: Run with monitoring**
```bash
# Run in background with logging
python run-pipeline.py --phase a > logs/phase-a.log 2>&1 &

# Monitor progress
tail -f logs/phase-a.log
```

### Monitoring During Execution

**Check progress:**
```sql
-- Monitor group creation
SELECT
  COUNT(*) AS total_groups,
  SUM(CASE WHEN needs_review THEN 1 ELSE 0 END) AS flagged
FROM document_groups;

-- Monitor file linking
SELECT
  COUNT(*) AS total_members,
  COUNT(DISTINCT group_id) AS total_groups
FROM document_group_members;
```

**Expected output:**
```
total_groups | flagged
--------------+--------
     ~37,000   |   < 5%

total_members | total_groups
--------------+--------------
    ~765,000   |    ~37,000
```

### Exit Criteria
- ✅ A6 completes successfully
- ✅ Report generated in `output/`
- ✅ No critical errors in logs

---

## Task 01.3: Validate Phase A Results

**Duration:** 15 minutes
**Priority:** Critical

### Validation Queries

#### Check 1: Document Groups Created
```sql
SELECT COUNT(*) AS document_groups
FROM document_groups;
-- Expected: > 0 (typically ~37K for 765K files)
```

#### Check 2: Group Members Linked
```sql
SELECT COUNT(*) AS group_members
FROM document_group_members;
-- Expected: > 0 (should match CloudFiles count minus orphans)
```

#### Check 3: Review Queue Health
```sql
SELECT
  COUNT(*) FILTER (WHERE needs_review = TRUE) AS flagged_count,
  COUNT(*) AS total_count,
  ROUND(100.0 * COUNT(*) FILTER (WHERE needs_review = TRUE) / COUNT(*), 2) AS flag_pct
FROM document_groups;
-- Expected: flag_pct < 5%
```

#### Check 4: Project Codes Extracted
```sql
SELECT
  COUNT(DISTINCT project_code) AS unique_projects,
  COUNT(*) AS groups_with_projects
FROM document_groups
WHERE project_code IS NOT NULL;
-- Expected: Both > 0
```

#### Check 5: Linking Report Statistics
**File:** `output/linking-report-*.csv`

**Check contents:**
- Total groups created
- Total files linked
- Flagged for review count
- Orphaned files (unlinked)

### Acceptable Ranges

| Metric | Minimum | Target | Maximum |
|--------|---------|--------|---------|
| Document groups | 30,000 | 37,000 | 50,000 |
| Group members | 700,000 | 765,000 | 800,000 |
| Flagged % | 0% | 2% | 5% |
| Orphans | 0 | < 1% | < 3% |

### Troubleshooting

#### Issue: Zero groups created
**Diagnosis:**
```sql
-- Check if CloudFiles table has data
SELECT COUNT(*) FROM cloud_files;
-- Expected: > 0
```

**Solution:**
- Verify CloudFiles populated
- Check A1 schema migration
- Review linking logic

#### Issue: Flagged % > 10%
**Diagnosis:**
```sql
-- Check why groups flagged
SELECT
  flag_reason,
  COUNT(*) AS count
FROM document_groups
WHERE needs_review = TRUE
GROUP BY flag_reason
ORDER BY count DESC;
```

**Solution:**
- Review top flag reasons
- Adjust linking criteria
- Re-run A5 with updated thresholds

#### Issue: High orphan count (> 5%)
**Diagnosis:**
```sql
-- Check orphan characteristics
SELECT
  file_extension,
  COUNT(*) AS orphan_count
FROM cloud_files cf
LEFT JOIN document_group_members dgm ON cf.id = dgm.file_id
WHERE dgm.id IS NULL
GROUP BY file_extension
ORDER BY orphan_count DESC;
```

**Solution:**
- Identify problematic file types
- Add extension-specific linking rules
- Re-run A2/A3

### Exit Criteria

**Must meet:**
- ✅ Document groups > 30,000
- ✅ Group members > 700,000
- ✅ Flagged % < 5%
- ✅ Orphans < 3%
- ✅ Linking report generated

**If criteria not met:**
1. Analyze failure patterns
2. Fix specific issues
3. Re-run affected scripts
4. Re-validate

---

## Task 01.4: Trigger Phase B Start

**Duration:** 5 minutes
**Priority:** High

### Options

**Option 1: Manual trigger**
```bash
# Notify team to start Phase B on VM2/VM3
echo "Phase A complete. Ready to start Phase B on VM2/VM3"
```

**Option 2: Database flag**
```sql
-- Set flag in database
CREATE TABLE IF NOT EXISTS pipeline_status (
  phase VARCHAR(10) PRIMARY KEY,
  status VARCHAR(50),
  started_at TIMESTAMP,
  completed_at TIMESTAMP
);

INSERT INTO pipeline_status (phase, status, started_at, completed_at)
VALUES ('A', 'completed', NOW(), NOW());
```

**Option 3: File-based signal**
```bash
# Create signal file
touch /tmp/phase-a-complete

# Other VMs poll for this file
while [ ! -f /tmp/phase-a-complete ]; do sleep 10; done
```

### Validation Before Triggering

**Final checks:**
```sql
-- All Phase A validation queries
-- (from Task 01.3)
```

**Only trigger Phase B if:**
- ✅ All validation queries pass
- ✅ No critical errors in logs
- ✅ Linking report reviewed
- ✅ Team notified

---

## Success Criteria

- ✅ Phase A scripts (A1-A6) executed successfully
- ✅ Document groups created (> 30K)
- ✅ Files linked (> 700K)
- ✅ Flagged % < 5%
- ✅ Linking report generated
- ✅ Phase B ready to start

---

## Handoff to Phase 02

**Deliverables:**
1. Document groups populated
2. Linking report in `output/`
3. Database flag set (if using Option 2)
4. Team notified

**Next phase:** VM2/VM3 begin Phase B (PDF/DXF extraction)

---

*End of Phase 01 documentation.*
