# Phase 00: Pre-Deployment Verification & Setup

**Duration:** 30 minutes
**VMs:** All 5 VMs
**Dependencies:** None
**Status:** Pending

---

## Overview

Prepare all 5 VMs for extraction pipeline deployment. Verify database migration, deploy code, install dependencies, create job coordination tables.

**VM Inventory:**
- VM1: Ubuntu Basic (Phase A coordinator)
- VM2: Ubuntu Basic (Phase B primary - PDF)
- VM3: Windows High (Phase B secondary - DXF)
- VM4: Windows High (Phase D primary - Creo)
- VM5: Windows High (Phase D secondary + Phase C)

---

## Task 00.1: Database Migration Verification

**Duration:** 15 minutes
**VM:** VM1 (Ubuntu)
**Priority:** Critical

### Objectives
- Verify all 14 tables exist
- Verify pgvector extension enabled
- Verify HNSW indexes created
- Verify foreign key constraints

### Steps

#### Step 1: Create Verification Script
**File:** `unified-doc-intelligence-deploy/scripts/verify-migration.py` (CREATE)

```python
#!/usr/bin/env python3
"""
Verify database migration before extraction.
Exits with error if any check fails.
"""

import sys
import psycopg2
from pathlib import Path

# Expected tables
EXPECTED_TABLES = [
    'document_groups', 'document_group_members',
    'extraction_jobs', 'extracted_metadata',
    'extracted_dimensions', 'extracted_parameters',
    'extracted_materials', 'extracted_bom_items',
    'cad_models', 'cad_model_embeddings',
    'cad_assembly_relations', 'cad_manufacturing_features',
    'cad_rendered_views'
]

def load_config():
    """Load config.txt"""
    config_file = Path(__file__).parent.parent / "config.txt"
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        sys.exit(1)

    config = {}
    with open(config_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config

def verify_migration(db_url):
    """Run all verification checks."""
    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # Check 1: Tables exist
        print("🔍 Checking tables...")
        cur.execute("""
            SELECT COUNT(DISTINCT table_name)
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN %s
        """, (tuple(EXPECTED_TABLES),))
        table_count = cur.fetchone()[0]

        if table_count < len(EXPECTED_TABLES):
            print(f"❌ Only {table_count}/{len(EXPECTED_TABLES)} tables found")
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN %s
                ORDER BY table_name
            """, (tuple(EXPECTED_TABLES),))
            existing = [r[0] for r in cur.fetchall()]
            missing = set(EXPECTED_TABLES) - set(existing)
            print(f"   Missing tables: {', '.join(missing)}")
            return False
        print(f"✅ All {table_count} tables found")

        # Check 2: pgvector extension
        print("🔍 Checking pgvector extension...")
        cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        if not cur.fetchone():
            print("❌ pgvector extension not found")
            print("   Run: CREATE EXTENSION IF NOT EXISTS vector;")
            return False
        print("✅ pgvector extension enabled")

        # Check 3: PostGIS extension
        print("🔍 Checking PostGIS extension...")
        cur.execute("SELECT extname FROM pg_extension WHERE extname = 'postgis'")
        if not cur.fetchone():
            print("⚠️  PostGIS extension not found (optional for CAD)")
        else:
            print("✅ PostGIS extension enabled")

        # Check 4: CAD table structure
        print("🔍 Checking cad_models table structure...")
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'cad_models'
            AND column_name IN ('brep_genome', 'deepsdf_latent', 'point_cloud')
            ORDER BY ordinal_position
        """)
        cad_columns = cur.fetchall()
        if len(cad_columns) < 3:
            print(f"⚠️  Only {len(cad_columns)}/3 CAD dual-representation columns found")
        else:
            print("✅ CAD dual-representation columns present")

        # Check 5: HNSW indexes
        print("🔍 Checking HNSW indexes...")
        cur.execute("""
            SELECT COUNT(*) FROM pg_indexes
            WHERE tablename = 'cad_model_embeddings'
            AND indexdef LIKE '%USING hnsw%'
        """)
        index_count = cur.fetchone()[0]
        if index_count < 6:
            print(f"⚠️  Only {index_count}/6 HNSW indexes found")
        else:
            print(f"✅ All {index_count} HNSW indexes present")

        # Check 6: Document groups table
        print("🔍 Checking document_groups table...")
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'document_groups'
        """)
        if cur.fetchone()[0] == 0:
            print("❌ document_groups table not found")
            return False
        print("✅ document_groups table present")

        conn.close()
        print("\n✅ Migration verified successfully")
        return True

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        print("❌ NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    print("=" * 70)
    print("DATABASE MIGRATION VERIFICATION")
    print("=" * 70)

    success = verify_migration(db_url)
    sys.exit(0 if success else 1)
```

#### Step 2: Run Verification
**Commands:**
```bash
cd unified-doc-intelligence-deploy
python scripts/verify-migration.py
```

**Expected output:**
```
======================================================================
DATABASE MIGRATION VERIFICATION
======================================================================
🔍 Checking tables...
✅ All 14 tables found
🔍 Checking pgvector extension...
✅ pgvector extension enabled
🔍 Checking PostGIS extension...
✅ PostGIS extension enabled
🔍 Checking cad_models table structure...
✅ CAD dual-representation columns present
🔍 Checking HNSW indexes...
✅ All 6 HNSW indexes present
🔍 Checking document_groups table...
✅ document_groups table present

✅ Migration verified successfully
```

#### Step 3: Handle Failures
**If tables missing:**
```bash
# Run migrations
alembic upgrade head
```

**If pgvector missing:**
```sql
-- Connect to database
psql $DATABASE_URL

-- Create extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
```

**If HNSW indexes missing:**
```bash
# Run HNSW index migration
alembic upgrade +1
```

### Exit Criteria
- ✅ All 14 tables present
- ✅ pgvector extension enabled
- ✅ HNSW indexes created
- ✅ No critical errors

---

## Task 00.2: Create Job Coordination Columns

**Duration:** 10 minutes
**VM:** VM1 (Ubuntu)
**Priority:** High

### Objectives
- Add job coordination columns to extraction_jobs
- Create index for worker queries
- Verify schema changes

### Steps

#### Step 1: Create Migration Script
**File:** `unified-doc-intelligence-deploy/scripts/add-job-coordination.sql` (CREATE)

```sql
-- Job Coordination System Migration
-- Adds claiming, heartbeat, and retry logic to extraction_jobs

-- Add coordination columns
ALTER TABLE extraction_jobs
ADD COLUMN IF NOT EXISTS claimed_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS heartbeat TIMESTAMP,
ADD COLUMN IF NOT EXISTS retry_count INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_error TEXT;

-- Create index for worker queries
CREATE INDEX IF NOT EXISTS idx_jobs_claimed
ON extraction_jobs(claimed_by)
WHERE claimed_by IS NOT NULL;

-- Create index for heartbeat monitoring
CREATE INDEX IF NOT EXISTS idx_jobs_heartbeat
ON extraction_jobs(heartbeat)
WHERE claimed_by IS NOT NULL;

-- Create index for retry logic
CREATE INDEX IF NOT EXISTS idx_jobs_retry
ON extraction_jobs(retry_count, status)
WHERE retry_count < 3;

-- Add comment
COMMENT ON COLUMN extraction_jobs.claimed_by IS 'Worker ID that claimed this job';
COMMENT ON COLUMN extraction_jobs.claimed_at IS 'Timestamp when job was claimed';
COMMENT ON COLUMN extraction_jobs.heartbeat IS 'Last heartbeat from worker';
COMMENT ON COLUMN extraction_jobs.retry_count IS 'Number of retry attempts';
COMMENT ON COLUMN extraction_jobs.last_error IS 'Last error message';
```

#### Step 2: Run Migration
**Commands:**
```bash
cd unified-doc-intelligence-deploy

# Option 1: Direct SQL execution
psql $DATABASE_URL -f scripts/add-job-coordination.sql

# Option 2: Via Python
python -c "
import psycopg2
conn = psycopg2.connect('$DATABASE_URL')
cur = conn.cursor()
with open('scripts/add-job-coordination.sql') as f:
    cur.execute(f.read())
conn.commit()
print('✅ Job coordination columns added')
"
```

#### Step 3: Verify Changes
**Query:**
```sql
-- Verify columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'extraction_jobs'
AND column_name IN ('claimed_by', 'claimed_at', 'heartbeat', 'retry_count', 'last_error')
ORDER BY ordinal_position;

-- Expected: 5 rows

-- Verify indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'extraction_jobs'
AND indexname LIKE 'idx_jobs%';

-- Expected: 3 indexes (idx_jobs_claimed, idx_jobs_heartbeat, idx_jobs_retry)
```

### Exit Criteria
- ✅ 5 columns added to extraction_jobs
- ✅ 3 indexes created
- ✅ No SQL errors

---

## Task 00.3: Deploy Code to All VMs

**Duration:** 5 minutes
**VMs:** All 5 VMs
**Priority:** High

### Objectives
- Copy unified-doc-intelligence-deploy to all VMs
- Verify config.txt synchronized
- Create output/logs directories

### Steps

#### Step 1: Prepare Deployment Package
**On local machine:**
```bash
# Create tarball
cd /path/to/AirTable
tar -czf unified-doc-intelligence-deploy.tar.gz unified-doc-intelligence-deploy/

# Verify contents
tar -tzf unified-doc-intelligence-deploy.tar.gz | head -20
```

#### Step 2: Deploy to Ubuntu VMs
**VM1 (Ubuntu):**
```bash
scp unified-doc-intelligence-deploy.tar.gz user@vm1-ubuntu:/path/to/
ssh user@vm1-ubuntu
cd /path/to/
tar -xzf unified-doc-intelligence-deploy.tar.gz
cd unified-doc-intelligence-deploy
mkdir -p output logs
```

**VM2 (Ubuntu):**
```bash
scp unified-doc-intelligence-deploy.tar.gz user@vm2-ubuntu:/path/to/
ssh user@vm2-ubuntu
cd /path/to/
tar -xzf unified-doc-intelligence-deploy.tar.gz
cd unified-doc-intelligence-deploy
mkdir -p output logs
```

#### Step 3: Deploy to Windows VMs
**Options:**
- **WinSCP:** GUI file transfer
- **rsync on Windows:** If Git Bash available
- **Network share:** Copy to shared folder

**VM3, VM4, VM5 (Windows):**
```powershell
# Using PowerShell (if WinSCP not available)
# First, copy tarball to VM (use WinSCP or network share)

# Extract on Windows VM (requires Git Bash or WSL)
cd C:\path\to
tar -xzf unified-doc-intelligence-deploy.tar.gz

cd unified-doc-intelligence-deploy
mkdir output logs
```

#### Step 4: Verify config.txt Synchronization
**On all VMs, verify:**
```bash
# Ubuntu
cat config.txt | grep NEON_DATABASE_URL
cat config.txt | grep B2_APPLICATION_KEY_ID

# Windows
type config.txt | findstr NEON_DATABASE_URL
type config.txt | findstr B2_APPLICATION_KEY_ID
```

**All VMs should have:**
- Same NEON_DATABASE_URL
- Same B2_APPLICATION_KEY_ID
- Same B2_APPLICATION_KEY
- Same B2_BUCKET_NAME

#### Step 5: Create Directories
**On all VMs:**
```bash
# Ubuntu
mkdir -p output logs

# Windows
mkdir output logs
```

### Exit Criteria
- ✅ Code deployed to all 5 VMs
- ✅ config.txt synchronized
- ✅ output/logs directories created

---

## Validation Checklist

Run this checklist on all VMs before proceeding to Phase 01:

### VM1 (Ubuntu)
- [ ] `verify-migration.py` passes all checks
- [ ] Job coordination columns added
- [ ] Code deployed
- [ ] config.txt correct
- [ ] output/logs directories exist

### VM2 (Ubuntu)
- [ ] Code deployed
- [ ] config.txt synchronized
- [ ] output/logs directories exist
- [ ] Can connect to database

### VM3 (Windows)
- [ ] Code deployed
- [ ] config.txt synchronized
- [ ] output/logs directories exist
- [ ] Can connect to database

### VM4 (Windows)
- [ ] Code deployed
- [ ] config.txt synchronized
- [ ] output/logs directories exist
- [ ] Can connect to database
- [ ] Creo gRPC service accessible

### VM5 (Windows)
- [ ] Code deployed
- [ ] config.txt synchronized
- [ ] output/logs directories exist
- [ ] Can connect to database
- [ ] Creo gRPC service accessible

---

## Troubleshooting

### Issue: Database connection fails
**Symptoms:** `psycopg2.OperationalError: could not connect`

**Solutions:**
1. Verify DATABASE_URL format: `postgresql://user:pass@host:port/db?sslmode=require`
2. Check network connectivity
3. Verify SSL certificates
4. Test with `psql` command line

### Issue: Tables missing
**Symptoms:** `Only X/14 tables found`

**Solutions:**
1. Run `alembic upgrade head`
2. Check Alembic configuration
3. Review migration logs

### Issue: Permission denied on VMs
**Symptoms:** `scp: Permission denied`

**Solutions:**
1. Verify SSH keys configured
2. Check user permissions on VMs
3. Use correct username/host

### Issue: config.txt out of sync
**Symptoms:** Different DATABASE_URL on VMs

**Solutions:**
1. Copy config.txt from VM1 to all other VMs
2. Verify file integrity (MD5 checksum)

---

## Success Criteria

- ✅ All 5 VMs have code deployed
- ✅ Database migration verified
- ✅ Job coordination system installed
- ✅ All VMs can connect to database
- ✅ config.txt synchronized across VMs
- ✅ Ready to proceed to Phase 01

---

*End of Phase 00 documentation.*
