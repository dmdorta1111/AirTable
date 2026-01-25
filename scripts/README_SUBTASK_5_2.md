# Subtask 5-2: Verify Worker Picks Up Jobs

This subtask verifies that the Celery worker picks up jobs and updates the database status correctly.

## Prerequisites

1. **PostgreSQL** running with database migrations applied:
   ```bash
   alembic upgrade head
   ```

2. **Redis** running (for Celery broker/backend):
   ```bash
   # Windows
   redis-server

   # Linux/macOS
   redis-server
   ```

3. **Environment variables** configured in `.env`:
   ```bash
   DATABASE_URL=postgresql+asyncpg://user:pass@localhost/pybase
   CELERY_BROKER_URL=redis://localhost:6379/1
   CELERY_RESULT_BACKEND=redis://localhost:6379/2
   ```

## Verification Steps

### Option 1: Automated Verification Script (Recommended)

1. **Start the Celery worker** (in a separate terminal):
   ```bash
   celery -A workers.celery_extraction_worker worker -l INFO
   ```

   Expected output:
   ```
   -------------- celery@your-host v5.x.x
   ---- **** -----
   --- * ***  * -- Linux/macOS
   -- * - **** ---
   - ** ---------- [config]
   - ** ---------- .> app:         workers:celery_extraction_worker
   - ** ---------- .> transport:   redis://localhost:6379/1
   - ** ---------- .> results:     redis://localhost:6379/2
   - *** --- * --- .> concurrency: 8 (prefork)
   -- ******* ---- .> task events: OFF
   --- ***** ----- --------------- [queues]
                .> celery           exchange=celery(direct) key=celery

   [tasks]
     . extract_dxf
     . extract_ifc
     . extract_pdf
     . extract_step
     . extract_werk24
     . extract_bulk
     . extract_file_auto

   [2025-01-25 12:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379/1
   [2025-01-25 12:00:00,000: INFO/MainProcess] celery ready.
   ```

2. **Run the verification script** (in another terminal):
   ```bash
   python scripts/verify_worker_pickup.py
   ```

   Expected output:
   ```
   ============================================================
   Celery Worker Pickup Verification
   ============================================================

   [Step 1] Verifying database...
   ✓ Database connection OK
   ✓ extraction_jobs table exists

   [Step 2] Creating test job...
   ✓ Created test job: 12345678-1234-1234-1234-123456789abc
     Initial status: pending
     celery_task_id: None

   [Step 3] Triggering Celery task...
   ✓ Sent task to Celery: abc-def-123
     Job ID: 12345678-1234-1234-1234-123456789abc

   [Step 4] Monitoring job status...
     Make sure Celery worker is running:
       celery -A workers.celery_extraction_worker worker -l INFO

   ------------------------------------------------------------
   Monitoring job 12345678-1234-1234-1234-123456789abc (timeout: 60s)...
   ------------------------------------------------------------
   [0.5s] Status: None → processing
   [0.5s] celery_task_id assigned: abc-def-123

   ✓ Job reached terminal state: FAILED
     Final status: failed
     celery_task_id: abc-def-123
     Progress: 0%
     Started at: 2025-01-25 12:00:01.000000
     Completed at: 2025-01-25 12:00:02.000000
     Error: PDF extraction dependencies missing... (expected, since /tmp/test.pdf doesn't exist)

   [Step 5] Verification Results
   ------------------------------------------------------------
   ✓ Worker successfully picked up job
   ✓ Status transitioned to: FAILED
   ✓ celery_task_id populated: abc-def-123
   ✓ started_at timestamp set
   ✓ completed_at timestamp set

   ✅ VERIFICATION PASSED: Worker successfully picks up jobs
   ✓ Cleaned up test job: 12345678-1234-1234-1234-123456789abc
   ```

3. **Check worker logs** (in the worker terminal):
   ```
   [2025-01-25 12:00:01,000: INFO/ForkPoolWorker-1] Task extract_pdf[abc-def-123] received
   [2025-01-25 12:00:01,100: INFO/ForkPoolWorker-1] Starting PDF extraction for /tmp/test.pdf (attempt 1)
   [2025-01-25 12:00:02,000: ERROR/ForkPoolWorker-1] PDF extraction failed for /tmp/test.pdf (attempt 1): File not found
   [2025-01-25 12:00:02,100: INFO/ForkPoolWorker-1] Task extract_pdf[abc-def-123] received
   ```

### Option 2: Manual Database Query

If the automated script doesn't work, you can manually verify:

1. **Create a test job via API**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/extraction/jobs \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "file=@tests/fixtures/sample.pdf" \
     -F "format=pdf"
   ```

   Save the `job_id` from the response.

2. **Query the database** (before worker starts):
   ```bash
   python scripts/query_job_by_id.py <job_id>
   ```

   Expected output:
   ```
   Job ID: 12345678-1234-1234-1234-123456789abc
   Status: pending
   celery_task_id: None
   Started at: None
   ```

3. **Start the Celery worker**:
   ```bash
   celery -A workers.celery_extraction_worker worker -l INFO
   ```

4. **Query the database again** (after worker picks up job):
   ```bash
   python scripts/query_job_by_id.py <job_id>
   ```

   Expected output (status changed):
   ```
   Job ID: 12345678-1234-1234-1234-123456789abc
   Status: processing (or completed/failed)
   celery_task_id: abc-def-123
   Started at: 2025-01-25 12:00:01.000000
   ```

## What's Being Verified

1. **Worker starts successfully**:
   - Celery worker loads without errors
   - Tasks are registered (extract_pdf, extract_dxf, etc.)
   - Worker connects to Redis broker

2. **Job transitions from PENDING to PROCESSING**:
   - Initial status: `pending`
   - Worker picks up job
   - Status changes to: `processing`
   - `celery_task_id` is populated

3. **Job reaches terminal state**:
   - Status changes to: `completed` or `failed`
   - `started_at` timestamp is set
   - `completed_at` timestamp is set
   - Results are stored in database

## Troubleshooting

### Worker doesn't start

**Problem**: `ImportError: No module named 'celery'`
```bash
pip install celery
```

**Problem**: `Error: Error connecting to redis`
```bash
# Start Redis
redis-server
```

**Problem**: Worker modules not found
```bash
# Make sure you're in the project root
pwd  # Should show: .../018-bulk-job-database-migration

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Worker starts but doesn't pick up jobs

**Problem**: Jobs stay in `pending` status

**Check 1**: Verify Redis connection
```bash
redis-cli ping
# Expected: PONG
```

**Check 2**: Verify task is in queue
```bash
redis-cli -n 1 LLEN celery
# Should show number of pending tasks
```

**Check 3**: Check worker logs for errors
```bash
# Worker should show: "Task extract_pdf[xxx] received"
```

### Database updates fail

**Problem**: `sqlalchemy.exc.OperationalError: could not connect to server`

**Check 1**: Verify PostgreSQL is running
```bash
psql -U postgres -c "SELECT version();"
```

**Check 2**: Verify DATABASE_URL in `.env`
```bash
cat .env | grep DATABASE_URL
# Should be: postgresql+asyncpg://...
```

**Check 3**: Verify migration applied
```bash
alembic current
# Should show latest revision
```

### Task fails immediately

**Problem**: `FileNotFoundError` or missing dependencies

This is **expected** for the test script since we're using a dummy file path. The important thing is that:
1. The worker picks up the job (status changes to `processing`)
2. The celery_task_id is populated
3. The status changes to `failed` (because the file doesn't exist)

This is the **correct behavior** for a non-existent file.

## Expected Database State

After successful verification, querying the job should show:

```sql
SELECT id, status, celery_task_id, started_at, completed_at
FROM pybase.extraction_jobs
WHERE id = '<job_id>';
```

| Column | Expected Value |
|--------|----------------|
| `status` | `processing`, `completed`, or `failed` |
| `celery_task_id` | UUID string (not NULL) |
| `started_at` | Timestamp (not NULL) |
| `completed_at` | Timestamp if terminal state reached |

## Success Criteria

✅ **Verification passes if:**
1. Worker starts without errors
2. Job status transitions from `pending` to `processing` within 5 seconds
3. `celery_task_id` is populated in database
4. `started_at` timestamp is set
5. Job reaches terminal state (`completed` or `failed`)
6. `completed_at` timestamp is set for terminal state

❌ **Verification fails if:**
1. Worker fails to start
2. Job status stays `pending` (worker not picking up)
3. `celery_task_id` remains NULL
4. Database errors during updates

## Next Steps

After successful verification:
1. Proceed to **subtask-5-3**: Test job persistence across worker restart
2. Then **subtask-5-4**: Test retry logic with exponential backoff
