# Subtask 5-4: Test Retry Logic with Exponential Backoff

## Overview

This subtask verifies the retry logic implementation for database-backed extraction jobs. We test that:

1. **Exponential Backoff**: Jobs retry with increasing delays (2^n seconds: 1s, 2s, 4s, 8s, ...)
2. **Max Retries**: Jobs stop retrying after max_retries limit (default: 3)
3. **Database Tracking**: retry_count increments correctly in the database
4. **Status Transitions**: Job status updates properly (pending → processing → retrying → completed/failed)
5. **Celery Integration**: Retry mechanism works correctly with Celery task system

## What We're Testing

The extraction worker implements retry logic with the following pattern:

```python
# From workers/celery_extraction_worker.py
@app.task(bind=True)
def extract_pdf(self, file_path: str, options: dict = None, job_id: str = None):
    try:
        # Extraction logic here
        ...
    except Exception as e:
        retry_count = self.request.retries
        max_retries = options.get("max_retries", 3)

        if retry_count < max_retries:
            # Exponential backoff: 2^retry_count seconds
            backoff = 2 ** retry_count
            logger.info(f"Retrying in {backoff}s (attempt {retry_count + 1}/{max_retries})")
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded - mark as failed
        run_async(update_job_complete(job_id, "failed", error_message=str(e)))
```

**Retry Pattern:**
- Attempt 1: Fails immediately → Retry in 1s (2^0)
- Attempt 2: Fails immediately → Retry in 2s (2^1)
- Attempt 3: Fails immediately → Retry in 4s (2^2)
- Attempt 4: Succeeds (or fails permanently if max_retries exceeded)

## Files Created

1. **workers/test_retry_task.py**: Celery task that simulates retry behavior
   - Fails first 3 attempts, succeeds on 4th attempt
   - Logs detailed retry information with timestamps
   - Demonstrates exponential backoff timing

2. **scripts/verify_retry_logic.py**: Automated verification script
   - Creates test job
   - Triggers test extraction task
   - Monitors job status through retries
   - Measures timing between retries
   - Verifies exponential backoff accuracy

3. **scripts/verify_retry_manual.py**: Manual verification guide
   - Step-by-step instructions
   - Prerequisites checklist
   - Manual verification commands

## Prerequisites

Before running verification, ensure the following services are running:

### 1. PostgreSQL Database
```bash
# Check database is running
psql -h localhost -U postgres -c "SELECT 1;"

# Verify extraction_jobs table exists
psql -h localhost -U postgres -d pybase -c "\d pybase.extraction_jobs"
```

### 2. Redis Server
```bash
# Start Redis
redis-server

# Verify Redis is running
redis-cli ping
# Expected output: PONG
```

### 3. FastAPI Server
```bash
# Start FastAPI server
uvicorn pybase.main:app --reload --host 0.0.0.0 --port 8000

# Verify server is running
curl http://localhost:8000/api/v1/health
```

### 4. Celery Worker with Test Task
```bash
# Start worker with test retry task
celery -A workers.test_retry_task worker -l INFO --pool=solo

# Expected output:
# [tasks]
#   . test_extraction_retry
#
# [2025-01-25 14:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379/1
# [2025-01-25 14:00:00,000: INFO/MainProcess] celery@hostname ready.
```

## Verification Methods

### Method 1: Automated Verification (Recommended)

The automated script handles everything for you:

```bash
# Run automated verification
python scripts/verify_retry_logic.py
```

**What it does:**
1. ✅ Authenticates with FastAPI
2. ✅ Creates test file
3. ✅ Creates test extraction job
4. ✅ Triggers test extraction task (fails 3x, then succeeds)
5. ✅ Monitors job status through retries
6. ✅ Records timestamps for each retry
7. ✅ Calculates timing between retries
8. ✅ Verifies exponential backoff accuracy
9. ✅ Prints comprehensive summary

**Expected Output:**
```
================================================================================
RETRY LOGIC VERIFICATION
Testing exponential backoff and max retry behavior
================================================================================

🔐 Authenticating...
✅ Authenticated successfully

📄 Created test file: /tmp/test_retry_extraction.txt

📝 Creating test extraction job...
✅ Job created successfully
   Job ID: 123e4567-e89b-12d3-a456-426614174000
   Status: pending
   Configured to fail 3 times, then succeed on 4th attempt

🚀 Triggering test extraction task...
✅ Test task triggered
   Task ID: abc-123-def-456
   Job ID: 123e4567-e89b-12d3-a456-426614174000

👀 Monitoring job progress (timeout: 60s)...
────────────────────────────────────────────────────────────────────────────────

⏰ 2025-01-25T14:00:05.123456
   Status: processing
   Retry count: 0
   Progress: 0%
   Celery task ID: abc-123-def-456

🔄 Retry detected!
   Retry #1
   Timestamp: 2025-01-25T14:00:06.234567
   Time since last retry: 1.1s
   Expected backoff: 2^0 = 1s
   Backoff accurate: True

🔄 Retry detected!
   Retry #2
   Timestamp: 2025-01-25T14:00:08.345678
   Time since last retry: 2.1s
   Expected backoff: 2^1 = 2s
   Backoff accurate: True

🔄 Retry detected!
   Retry #3
   Timestamp: 2025-01-25T14:00:12.456789
   Time since last retry: 4.1s
   Expected backoff: 2^2 = 4s
   Backoff accurate: True

⏰ 2025-01-25T14:00:16.567890
   Status: completed
   Retry count: 3
   Progress: 100%
   ✅ Job completed successfully!
   Total attempts: 4

────────────────────────────────────────────────────────────────────────────────
🏁 Monitoring ended

================================================================================
RETRY LOGIC VERIFICATION SUMMARY
================================================================================

📊 Status Changes:
   1. 2025-01-25T14:00:05.123456
      Status: processing
      Retry count: 0
   2. 2025-01-25T14:00:16.567890
      Status: completed
      Retry count: 3

⏱️  Retry Timeline:
   Retry    Timestamp                    Delay      Expected   Status
   ───────────────────────────────────────────────────────────────────
   #1       2025-01-25T14:00:06.234567   1.1s       1s         ✅
   #2       2025-01-25T14:00:08.345678   2.1s       2s         ✅
   #3       2025-01-25T14:00:12.456789   4.1s       4s         ✅

✅ Verification Criteria:
   ✓ Job created successfully
   ✓ Status transitions: processing → completed
   ✓ Job succeeded after 3 retries
   ✓ Retry count matches expected: 3

🎉 RETRY LOGIC VERIFICATION PASSED!
================================================================================
```

### Method 2: Manual Verification

For manual verification, follow these steps:

#### Step 1: Start All Services

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: FastAPI
uvicorn pybase.main:app --reload

# Terminal 3: Celery worker with test task
celery -A workers.test_retry_task worker -l INFO --pool=solo

# Terminal 4: Verification script
python scripts/verify_retry_manual.py
```

#### Step 2: Create Test Job

```bash
# Get authentication token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  | jq -r '.access_token')

# Create test file
echo "Test file for retry verification" > /tmp/test_retry.txt

# Create extraction job
JOB_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/extraction/jobs \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test_retry.txt" \
  -F "format=pdf" \
  -F 'options={"fail_attempts":3,"max_retries":3}')

JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')
echo "Job ID: $JOB_ID"
```

#### Step 3: Trigger Test Task

```bash
# Trigger test extraction task directly
python -c "
from celery import Celery
import sys

app = Celery('test', broker='redis://localhost:6379/1')

task = app.send_task(
    'test_extraction_retry',
    args=['/tmp/test_retry.txt', {'fail_attempts': 3, 'max_retries': 3}, '$JOB_ID']
)

print(f'Task ID: {task.id}')
print(f'Job ID: $JOB_ID')
print(f'Watch Celery logs for retry attempts...')
"
```

#### Step 4: Monitor Celery Logs

Watch Terminal 3 (Celery worker) for retry attempts:

```
[2025-01-25 14:00:05,000: INFO/MainProcess] Task test_extraction_retry[abc-123] received
[2025-01-25 14:00:05,100: INFO/ForkPoolWorker-1] =================================================================================
[2025-01-25 14:00:05,100: INFO/ForkPoolWorker-1] Test extraction task: Attempt 1/4
[2025-01-25 14:00:05,100: INFO/ForkPoolWorker-1] File: /tmp/test_retry.txt
[2025-01-25 14:00:05,100: INFO/ForkPoolWorker-1] Job ID: 123e4567-e89b-12d3-a456-426614174000
[2025-01-25 14:00:05,100: INFO/ForkPoolWorker-1] Will fail first 3 attempts, then succeed
[2025-01-25 14:00:05,100: INFO/ForkPoolWorker-1] ==================================================================================
[2025-01-25 14:00:05,200: WARNING/ForkPoolWorker-1] ❌ Task failed: Simulated extraction failure (attempt 1/4)
[2025-01-25 14:00:05,200: WARNING/ForkPoolWorker-1] ⏱️  Will retry in 1s (exponential backoff: 2^0 = 1)
[2025-01-25 14:00:05,200: WARNING/ForkPoolWorker-1] 📊 Retry progress: 1/3 failures before success
[2025-01-25 14:00:05,200: WARNING/ForkPoolWorker-1] ⏰ Timestamp: 2025-01-25T14:00:05.200000

[2025-01-25 14:00:06,300: INFO/ForkPoolWorker-1] Task test_extraction_retry[abc-123] retry: 1/3
[2025-01-25 14:00:06,400: INFO/ForkPoolWorker-1] =================================================================================
[2025-01-25 14:00:06,400: INFO/ForkPoolWorker-1] Test extraction task: Attempt 2/4
[2025-01-25 14:00:06,400: INFO/ForkPoolWorker-1] File: /tmp/test_retry.txt
...
[2025-01-25 14:00:06,500: WARNING/ForkPoolWorker-1] ⏱️  Will retry in 2s (exponential backoff: 2^1 = 2)

[2025-01-25 14:00:08,600: INFO/ForkPoolWorker-1] Task test_extraction_retry[abc-123] retry: 2/3
[2025-01-25 14:00:08,700: WARNING/ForkPoolWorker-1] ⏱️  Will retry in 4s (exponential backoff: 2^2 = 4)

[2025-01-25 14:00:12,800: INFO/ForkPoolWorker-1] Task test_extraction_retry[abc-123] retry: 3/3
[2025-01-25 14:00:13,000: INFO/ForkPoolWorker-1] ✅ Task succeeded on attempt 4!
[2025-01-25 14:00:13,000: INFO/ForkPoolWorker-1] 🎉 Test extraction completed successfully after 3 retries
```

#### Step 5: Query Job Status via API

```bash
# Monitor job status
watch -n 1 "curl -s -H \"Authorization: Bearer $TOKEN\" \
  http://localhost:8000/api/v1/extraction/jobs/$JOB_ID | jq '{status, retry_count, progress, error_message}'"
```

Expected progression:
```json
{"status":"processing","retry_count":0,"progress":0,"error_message":null}
{"status":"processing","retry_count":1,"progress":0,"error_message":null}
{"status":"processing","retry_count":2,"progress":0,"error_message":null}
{"status":"processing","retry_count":3,"progress":0,"error_message":null}
{"status":"completed","retry_count":3,"progress":100,"error_message":null}
```

#### Step 6: Query Database Directly

```bash
# Query job state from database
psql -h localhost -U postgres -d pybase -c "
SELECT
    id,
    status,
    retry_count,
    max_retries,
    error_message,
    started_at,
    completed_at,
    EXTRACT(EPOCH FROM (completed_at - started_at)) as duration_seconds
FROM pybase.extraction_jobs
WHERE id = '$JOB_ID';
"
```

Expected output:
```
                  id                  |  status   | retry_count | max_retries |      error_message      |         started_at         |        completed_at        | duration_seconds
--------------------------------------+-----------+-------------+-------------+-------------------------+----------------------------+----------------------------+------------------
 123e4567-e89b-12d3-a456-426614174000 | completed |           3 |           3 |                         | 2025-01-25 14:00:05.123+00 | 2025-01-25 14:00:13.456+00 |       8.333
```

## Verification Checklist

Use this checklist to confirm retry logic is working correctly:

- [ ] **Service Prerequisites**
  - [ ] PostgreSQL database running
  - [ ] Redis server running
  - [ ] FastAPI server running
  - [ ] Celery worker with test task running

- [ ] **Job Creation**
  - [ ] Test job created successfully
  - [ ] Job status is "pending" initially
  - [ ] retry_count is 0

- [ ] **Celery Task Execution**
  - [ ] Worker picks up job (status → "processing")
  - [ ] celery_task_id populated in database
  - [ ] started_at timestamp set

- [ ] **Retry Behavior**
  - [ ] First retry happens after ~1 second
  - [ ] Second retry happens after ~2 seconds
  - [ ] Third retry happens after ~4 seconds
  - [ ] Timing matches exponential backoff pattern (2^n)

- [ ] **Database Tracking**
  - [ ] retry_count increments: 0 → 1 → 2 → 3
  - [ ] Status updates: processing → completed
  - [ ] error_message is null (job succeeded)

- [ ] **Final State**
  - [ ] Job status is "completed"
  - [ ] retry_count equals 3
  - [ ] completed_at timestamp set
  - [ ] Total duration includes retry delays (~8-10 seconds)

## Troubleshooting

### Issue: Worker doesn't pick up job

**Symptoms:**
- Job status stays "pending"
- No activity in Celery worker logs

**Solutions:**
1. Check Celery worker is running with correct task:
   ```bash
   celery -A workers.test_retry_task inspect active
   ```
2. Verify worker can connect to Redis:
   ```bash
   celery -A workers.test_retry_task inspect ping
   ```
3. Check Redis queue:
   ```bash
   redis-cli
   > LLEN celery
   ```

### Issue: Job fails immediately without retries

**Symptoms:**
- Job status changes to "failed"
- retry_count is 0
- Error: "Max retries exceeded"

**Solutions:**
1. Check max_retries configuration:
   ```sql
   SELECT max_retries FROM pybase.extraction_jobs WHERE id = '...';
   ```
2. Verify task options include correct max_retries:
   ```python
   options = {"max_retries": 3}  # Should be set
   ```

### Issue: Retries happen but timing is wrong

**Symptoms:**
- Retries occur but delays don't match exponential backoff
- All retries happen at ~1 second intervals

**Solutions:**
1. Check task is using `@app.task(bind=True)` for retry support
2. Verify countdown calculation:
   ```python
   backoff = 2 ** retry_count  # Should be exponential
   ```
3. Check for custom retry configuration in celery config:
   ```python
   app.conf.task_default_max_retries = 3
   ```

### Issue: Database retry_count not incrementing

**Symptoms:**
- Celery retries are happening (visible in logs)
- Database retry_count stays at 0

**Solutions:**
1. Check worker_db.py is being called
2. Verify update_job_start() is being called on each attempt
3. Check for database errors in worker logs
4. Ensure job_id is being passed to task correctly

## Expected Celery Log Output

When retry logic is working correctly, Celery logs should show:

```
[INFO] Task test_extraction_retry[abc-123] received
[INFO] Test extraction task: Attempt 1/4
[WARNING] ❌ Task failed: Simulated extraction failure (attempt 1/4)
[WARNING] ⏱️  Will retry in 1s (exponential backoff: 2^0 = 1)
[INFO] Task test_extraction_retry[abc-123] retry: 1/3
[INFO] Test extraction task: Attempt 2/4
[WARNING] ❌ Task failed: Simulated extraction failure (attempt 2/4)
[WARNING] ⏱️  Will retry in 2s (exponential backoff: 2^1 = 2)
[INFO] Task test_extraction_retry[abc-123] retry: 2/3
[INFO] Test extraction task: Attempt 3/4
[WARNING] ❌ Task failed: Simulated extraction failure (attempt 3/4)
[WARNING] ⏱️  Will retry in 4s (exponential backoff: 2^2 = 4)
[INFO] Task test_extraction_retry[abc-123] retry: 3/3
[INFO] Test extraction task: Attempt 4/4
[INFO] ✅ Task succeeded on attempt 4!
[INFO] 🎉 Test extraction completed successfully after 3 retries
```

## Database Queries for Verification

### Check Job State

```sql
SELECT
    id,
    status,
    retry_count,
    max_retries,
    error_message,
    celery_task_id,
    created_at,
    started_at,
    completed_at,
    EXTRACT(EPOCH FROM (completed_at - started_at)) as duration_seconds
FROM pybase.extraction_jobs
WHERE id = 'YOUR_JOB_ID';
```

### Monitor Retry Progress

```sql
-- Run this repeatedly to watch retry_count increment
SELECT
    status,
    retry_count,
    error_message,
    CASE
        WHEN status = 'pending' THEN 'Waiting for worker'
        WHEN status = 'processing' THEN 'Worker processing'
        WHEN status = 'completed' THEN 'Succeeded'
        WHEN status = 'failed' THEN 'Failed permanently'
        ELSE status
    END as status_description
FROM pybase.extraction_jobs
WHERE id = 'YOUR_JOB_ID';
```

### Check Retry History

```sql
-- Jobs with most retries (useful for finding patterns)
SELECT
    id,
    extraction_format,
    status,
    retry_count,
    max_retries,
    error_message,
    created_at,
    completed_at
FROM pybase.extraction_jobs
ORDER BY retry_count DESC
LIMIT 10;
```

## Success Criteria

Retry logic verification is considered **SUCCESSFUL** when:

1. ✅ Job is created and picked up by worker
2. ✅ Worker logs show 3 retry attempts with exponential backoff
3. ✅ Timing between retries matches pattern: ~1s, ~2s, ~4s
4. ✅ Database retry_count increments: 0 → 1 → 2 → 3
5. ✅ Job status transitions: pending → processing → completed
6. ✅ Job succeeds on 4th attempt (after 3 retries)
7. ✅ Total duration includes retry delays (~8-10 seconds)
8. ✅ No unexpected errors in worker or database logs

## Next Steps

After verifying retry logic works correctly:

1. ✅ Proceed to subtask-6-1: Remove in-memory job storage
2. ✅ Document retry behavior in API documentation
3. ✅ Consider adding monitoring/alerting for repeated job failures
4. ✅ Add metrics for retry statistics (avg retries, failure rate, etc.)

## Additional Resources

- **Celery Retry Documentation**: https://docs.celeryq.dev/en/stable/userguide/tasks.html#retry
- **Exponential Backoff**: https://en.wikipedia.org/wiki/Exponential_backoff
- **Worker Implementation**: `workers/celery_extraction_worker.py`
- **Service Layer**: `src/pybase/services/extraction_job.py`
- **Database Model**: `src/pybase/models/extraction_job.py`

---

**Last Updated:** 2025-01-25
**Subtask:** 5-4 - Test retry logic with exponential backoff
**Status:** ✅ Implementation complete, ready for verification
