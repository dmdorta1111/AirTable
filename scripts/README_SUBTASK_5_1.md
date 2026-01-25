# Subtask 5-1: Manual Verification Instructions

## Objective
Verify that extraction jobs persist in the database before the Celery worker starts processing them.

## Prerequisites
1. PostgreSQL database running and accessible
2. FastAPI server running (or use the verification script which starts its own HTTP client)
3. Valid authentication token

## Manual Verification Steps

### Step 1: Start the FastAPI Server
```bash
# From project root
uvicorn pybase.main:app --reload
```

### Step 2: Get Authentication Token
```bash
# Login to get token (replace with your credentials)
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "your_password"}'

# Save the access_token from the response
```

### Step 3: Run Verification Script
```bash
# Set environment variables
export API_TOKEN="your_jwt_token_from_step_2"
export DATABASE_URL="postgresql+asyncpg://user:pass@host/dbname"

# Run the verification script
python scripts/verify_job_persistence.py
```

### Expected Output
```
======================================================================
SUBTASK 5-1: Verify Job Persists in Database Before Worker Starts
======================================================================

Configuration:
  API Base URL: http://localhost:8000
  Database: host/dbname

Step 1: Creating extraction job via API...
  ✓ Job created successfully
  Job ID: 123e4567-e89b-12d3-a456-426614174000
  Status: pending
  Format: pdf
  Retry Count: 0

Step 2: Querying database to verify job persistence...
  ✓ Job found in database
  Database query result:
    - ID: 123e4567-e89b-12d3-a456-426614174000
    - Status: pending
    - Format: pdf
    - Retry Count: 0
    - Max Retries: 3
    - Progress: 0%
    - Created At: 2026-01-25 14:30:00.123456
    - Started At: None
    - Completed At: None
    - Celery Task ID: None
    - File Path: /tmp/uploads/test_persistence_XXX.pdf

Step 3: Verifying job fields...
  ✓ All fields verified successfully
    ✓ Status is PENDING
    ✓ Retry count is 0
    ✓ Progress is 0%
    ✓ Not started yet (started_at is None)
    ✓ Not completed yet (completed_at is None)
    ✓ Worker hasn't picked it up (celery_task_id is None)
    ✓ File path is set

======================================================================
✓ VERIFICATION PASSED
======================================================================

Summary:
  ✓ Job successfully created via API
  ✓ Job persists in extraction_jobs table
  ✓ Job has correct status (pending)
  ✓ All fields match expected values

Subtask 5-1 is complete.
======================================================================
```

## Alternative: Manual Database Query

If you want to manually query the database:

### 1. Create Job via API
```bash
curl -X POST "http://localhost:8000/api/v1/extraction/jobs" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.pdf" \
  -F "format=pdf"
```

Save the `id` from the response.

### 2. Query Database Directly
```bash
# Using the query script
python scripts/query_job_by_id.py <job_id_from_step_1>

# Or using psql directly
psql $DATABASE_URL -c "SELECT id, status, extraction_format, retry_count, progress, created_at, started_at, completed_at, celery_task_id FROM pybase.extraction_jobs WHERE id = '<job_id>'"
```

### 3. Verify Results
- ✓ `status` = 'pending'
- ✓ `retry_count` = 0
- ✓ `progress` = 0
- ✓ `created_at` is not NULL
- ✓ `started_at` is NULL (worker hasn't started yet)
- ✓ `completed_at` is NULL
- ✓ `celery_task_id` is NULL (worker hasn't picked it up)

## Test Files Created

1. **tests/integration/test_extraction_job_persistence.py**
   - Automated pytest tests for job persistence
   - Tests PDF, DXF, IFC, and STEP formats
   - Verifies database state after API call

2. **scripts/verify_job_persistence.py**
   - Standalone verification script
   - Creates job via API and queries database
   - Comprehensive field validation

3. **scripts/query_job_by_id.py**
   - Quick database query utility
   - Displays all job fields from database
   - Useful for manual inspection

## Verification Checklist

- [x] Test files created
- [x] Verification script created
- [x] Database query utility created
- [ ] Manual verification passed (run the script and verify output)
- [ ] Integration tests pass (run pytest when infrastructure is ready)

## Troubleshooting

### Database Connection Issues
```
Error: The asyncio extension requires an async driver to be used
```
**Solution:** Ensure DATABASE_URL uses `postgresql+asyncpg://` scheme.

### API Authentication Issues
```
Error: 401 Unauthorized
```
**Solution:** Verify API_TOKEN is valid and not expired.

### Job Not Found in Database
```
Error: Job not found in database
```
**Solution:** Check that the migration has been run:
```bash
alembic upgrade head
```

## Next Steps

After this subtask is verified:
1. Subtask 5-2: Start worker, verify job is picked up and status updates
2. Subtask 5-3: Test job persistence across worker restart
3. Subtask 5-4: Test retry logic with exponential backoff
