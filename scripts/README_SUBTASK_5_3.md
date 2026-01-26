# Subtask 5-3: Worker Restart Persistence Verification

## Overview

This test verifies that extraction jobs persist across Celery worker restarts. This is a **critical requirement** for the database-backed job queue - jobs must survive worker failures and restarts without losing progress.

## What This Tests

1. **Job Persistence**: Job records remain in database during worker restart
2. **Task Recovery**: New worker instance picks up pending/processing jobs
3. **State Continuity**: Job progress and status are preserved
4. **No Data Loss**: No jobs are lost or duplicated during restart

## Prerequisites

### Required Services

```bash
# 1. PostgreSQL database
# Check DATABASE_URL in .env
psql $DATABASE_URL -c "SELECT 1"

# 2. Redis (Celery broker)
redis-server
# Verify: redis-cli ping

# 3. FastAPI server
uvicorn pybase.main:app --reload

# 4. Celery worker (will be restarted during test)
celery -A workers.celery_extraction_worker worker -l INFO
```

### Database Migration

```bash
# Ensure extraction_jobs table exists
alembic upgrade head

# Verify table
psql $DATABASE_URL -c "\d pybase.extraction_jobs"
```

## Automated Verification

The automated script handles the entire test workflow:

```bash
# Run the verification script
python scripts/verify_worker_restart_persistence.py
```

### What the Script Does

1. **Creates a bulk job** with 5 dummy PDF files (will fail to extract, but that's OK)
2. **Waits for worker to start processing** (status changes to PROCESSING)
3. **Prompts you to restart the worker** (press Enter when ready)
4. **Monitors job after restart** to verify it continues
5. **Reports results** and cleans up test data

### Expected Output

```
============================================================
Worker Restart Persistence Verification
============================================================

[Step 1] Verifying database...
✓ Database connection OK
✓ extraction_jobs table exists

[Step 2] Creating bulk extraction job...
✓ Created bulk job: <uuid>
  Files: 5 dummy PDFs
  Initial status: pending

[Step 3] Triggering Celery task...
✓ Sent bulk task to Celery: <task-id>

[Step 4] Waiting for worker to pick up job...
Waiting for job to reach PROCESSING status (timeout: 30s)...
✓ Job reached PROCESSING status after 2.3s
  celery_task_id: <task-id>
  Progress: 0%

============================================================
ACTION REQUIRED: Restart the Celery worker now
============================================================

Steps:
  1. In another terminal, find the worker process:
     ps aux | grep celery
  2. Kill the worker:
     pkill -f celery
  3. Start the worker again:
     celery -A workers.celery_extraction_worker worker -l INFO

  After restarting, press Enter to continue...
============================================================

[Step 6] Monitoring job after worker restart...
Initial state after restart:
  Status: processing
  Progress: 0%
  celery_task_id: <task-id>
  retry_count: 0

[2.3s] Status: processing → failed
  Error: [Errno 2] No such file or directory: '/tmp/test_file_0.pdf'

[Step 7] Verification Results
------------------------------------------------------------
✓ Job completed after worker restart
✓ Worker successfully picked up job after restart
✓ Final status: FAILED
✓ Time to complete after restart: 2.3s
✓ started_at timestamp preserved
✓ completed_at timestamp set

✅ VERIFICATION PASSED: Job persists across worker restart
✓ Cleaned up test job: <uuid>
```

**Note**: The job will likely **FAIL** because the test files don't exist. This is **expected and OK** - we're testing persistence, not extraction. What matters is that the job continues after restart and reaches a terminal state.

## Manual Verification

If you prefer to test manually without the script:

### Step 1: Start Services

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery Worker
celery -A workers.celery_extraction_worker worker -l INFO

# Terminal 3: FastAPI
uvicorn pybase.main:app --reload
```

### Step 2: Submit a Long-Running Job

```bash
# Option A: Use API (requires authentication)
curl -X POST http://localhost:8000/api/v1/extraction/bulk \
  -H "Authorization: Bearer <token>" \
  -F "files=@test1.pdf" \
  -F "files=@test2.pdf" \
  -F "files=@test3.pdf" \
  -F "format=pdf"

# Option B: Create job directly in database
python -c "
import asyncio
from pybase.db.session import AsyncSessionLocal
from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus, ExtractionFormat
import json

async def create_job():
    async with AsyncSessionLocal() as db:
        job = ExtractionJob(
            user_id='manual-test',
            status=ExtractionJobStatus.PENDING.value,
            extraction_format=ExtractionFormat.BULK.value,
            file_path=json.dumps(['/tmp/test1.pdf', '/tmp/test2.pdf', '/tmp/test3.pdf']),
            options=json.dumps({'extract_tables': True}),
            max_retries=3,
            retry_count=0,
            progress=0,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        print(f'Job ID: {job.id}')

asyncio.run(create_job())
"
```

### Step 3: Wait for Worker to Start Processing

```bash
# Monitor job status (replace <job-id>)
JOB_ID="<job-id>"

watch -n 1 "psql $DATABASE_URL -c \"
SELECT
    status,
    progress,
    celery_task_id,
    started_at,
    retry_count
FROM pybase.extraction_jobs
WHERE id = '$JOB_ID'
\""
```

Wait until status changes from `pending` to `processing`.

### Step 4: Restart Worker

```bash
# In Terminal 2 (worker terminal):
# Press Ctrl+C to stop worker

# Then start it again:
celery -A workers.celery_extraction_worker worker -l INFO
```

### Step 5: Verify Job Continues

```bash
# Continue monitoring job status
# The job should:
# 1. Remain in database (not lost)
# 2. Continue processing or reach terminal state
# 3. Have started_at timestamp preserved
# 4. Eventually reach completed/failed state
```

### Step 6: Verify Results

```sql
-- Query final job state
SELECT
    id,
    status,
    progress,
    retry_count,
    celery_task_id,
    started_at,
    completed_at,
    EXTRACT(EPOCH FROM (completed_at - started_at)) as duration_seconds
FROM pybase.extraction_jobs
WHERE id = '<job-id>';

-- Expected results:
-- - status: 'completed', 'failed', or 'cancelled' (not stuck in 'pending')
-- - started_at: NOT NULL (timestamp preserved)
-- - completed_at: NOT NULL (job reached terminal state)
-- - celery_task_id: NOT NULL (worker picked it up)
```

## Success Criteria

✅ **Job persists in database** during worker restart
✅ **Worker picks up job** after restart (celery_task_id may change)
✅ **Job continues processing** and reaches terminal state
✅ **Timestamps preserved** (started_at not lost)
✅ **No duplicate jobs** created

## Troubleshooting

### Issue: Worker doesn't pick up job after restart

**Symptoms**: Job stuck in `pending` or `processing` status indefinitely

**Diagnosis**:
```bash
# Check worker logs
# Look for errors like:
# - "Connection refused" (Redis not running)
# - "Task not found" (worker not registered)
# - "Database connection error"

# Check Celery registered tasks
celery -A workers.celery_extraction_worker inspect registered
```

**Solutions**:
1. Verify Redis is running: `redis-cli ping`
2. Check worker can connect to Redis (check CELERY_BROKER_URL)
3. Verify worker can connect to database (check DATABASE_URL)
4. Restart Redis if needed: `redis-server --daemonize yes`

### Issue: Job lost during restart

**Symptoms**: Job not found in database after restart

**Diagnosis**:
```bash
# Check database before restart
psql $DATABASE_URL -c "SELECT id, status FROM pybase.extraction_jobs WHERE id = '<job-id>'"

# Check after restart
psql $DATABASE_URL -c "SELECT id, status FROM pybase.extraction_jobs WHERE id = '<job-id>'"
```

**Solutions**:
1. Verify database is running and accessible
2. Check for database connection errors in worker logs
3. Ensure migration applied: `alembic upgrade head`
4. Check database transaction logs for rollback

### Issue: Multiple workers processing same job

**Symptoms**: Job completes multiple times or progress jumps erratically

**Diagnosis**:
```bash
# Check for multiple worker processes
ps aux | grep celery | grep -v grep

# Check for duplicate celery_task_id
psql $DATABASE_URL -c "SELECT id, celery_task_id FROM pybase.extraction_jobs WHERE id = '<job-id>'"
```

**Solutions**:
1. Kill all workers: `pkill -9 -f celery`
2. Start single worker instance
3. Verify only one worker connects to Celery
4. Check for race conditions in worker_db.py

### Issue: Job fails immediately after restart

**Symptoms**: Job status changes to `failed` right after worker restart

**Diagnosis**:
```bash
# Check error_message in database
psql $DATABASE_URL -c "SELECT error_message FROM pybase.extraction_jobs WHERE id = '<job-id>'"

# Check worker logs for exceptions
tail -f /var/log/celery.log
```

**Solutions**:
1. This may be expected if job was processing during restart
2. Check if file paths exist and are accessible
3. Verify retry logic is working (retry_count should increment)
4. Check error_stack_trace for root cause

## Understanding the Test

### Why Bulk Jobs?

We use **bulk extraction jobs** for this test because:
- They take longer to process (multiple files)
- More likely to be in-progress during restart
- Tests the `extract_bulk` task specifically
- Simulates real-world usage patterns

### Why Dummy Files?

The test uses **non-existent file paths** (`/tmp/test_file_*.pdf`) because:
- We're testing **job persistence**, not extraction functionality
- Extraction failures are **expected and acceptable**
- No need for actual test files
- Faster test execution

### What's Actually Being Tested?

1. **Database persistence**: Job record remains in `pybase.extraction_jobs`
2. **Task state management**: Celery tracks task execution state
3. **Worker recovery**: New worker instance resumes processing
4. **State integrity**: Job fields (status, progress, timestamps) remain consistent

## Database Schema Reference

```sql
-- Key fields for this test
CREATE TABLE pybase.extraction_jobs (
    id UUID PRIMARY KEY,
    user_id UUID,
    status VARCHAR(20),  -- pending, processing, completed, failed, cancelled
    extraction_format VARCHAR(20),
    file_path TEXT,
    options JSONB,
    results JSONB,
    progress INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    celery_task_id VARCHAR(255),  -- Celery task ID (may change after restart)
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_retry_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Next Steps

After verification passes:
1. Proceed to **subtask-5-4**: Test retry logic with exponential backoff
2. Document any edge cases discovered
3. Update deployment procedures for worker restarts

## Questions or Issues?

If you encounter problems not covered here:
1. Check worker logs: `celery -A workers.celery_extraction_worker worker -l DEBUG`
2. Check database: Query `pybase.extraction_jobs` table directly
3. Check Redis: `redis-cli monitor` to see Celery messages
4. Review previous subtasks: `scripts/README_SUBTASK_5_2.md`
