# Export Testing Guide

This guide explains how to test the large dataset export functionality to ensure it handles 100K+ records without timeout.

## Overview

The export testing verifies that:
- Export starts immediately (returns HTTP 202)
- Download completes without timeout
- Exported file contains all records
- Data integrity is maintained
- Streaming works efficiently

## Test File

`frontend/e2e/large-dataset-export.spec.ts` contains 4 test cases:

1. **CSV Export Test** - Verifies CSV export with 100K records
2. **JSON Export Test** - Verifies JSON export with 100K records
3. **Immediate Start Test** - Verifies HTTP 202 and quick response
4. **Streaming Test** - Verifies streaming and progress tracking

## Prerequisites

### 1. Database Seeding

Seed your database with 100K test records:

```bash
python scripts/seed_large_dataset.py --table YOUR_TABLE_ID --count 100000
```

### 2. Backend Server

Ensure the backend server is running:

```bash
# Terminal 1: Start backend
uvicorn src.pybase.main:app --reload
```

### 3. Auth Token

Get a valid authentication token:

```bash
# Option 1: Login via API and extract token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpassword"}' \
  | jq -r '.access_token'

# Option 2: Use browser DevTools
# 1. Login to the app
# 2. Open DevTools > Application > Local Storage
# 3. Copy the 'token' value
```

### 4. Environment Variables

Set the required environment variables:

```bash
export TABLE_ID="your-table-uuid"
export AUTH_TOKEN="your-auth-token"
export API_BASE_URL="http://localhost:8000"  # Optional, defaults to this
```

## Running Tests

### Quick Start (Automated Script)

Use the provided helper script:

```bash
./scripts/run_export_test.sh
```

This script:
- Checks all prerequisites
- Verifies environment variables
- Runs the Playwright tests
- Reports results with color-coded output

### Manual Execution

Run tests directly with Playwright:

```bash
cd frontend

# Set environment variables
export TABLE_ID="your-table-uuid"
export AUTH_TOKEN="your-auth-token"
export API_BASE_URL="http://localhost:8000"

# Run all export tests
npx playwright test large-dataset-export.spec.ts

# Run specific test
npx playwright test large-dataset-export.spec.ts -g "CSV Export"

# Run with debug output
DEBUG=pw:api npx playwright test large-dataset-export.spec.ts

# Run with UI mode
npx playwright test large-dataset-export.spec.ts --ui
```

## Test Details

### Test 1: CSV Export

**What it tests:**
- Export endpoint returns valid CSV
- CSV contains header row
- All 100K records are exported
- Data rows have correct format

**Expected results:**
- Response status: 200-299
- Content-Type: text/csv
- Content-Disposition includes .csv filename
- Header row present
- 100K+ data rows

**Verification:**
```bash
npx playwright test large-dataset-export.spec.ts -g "CSV Export"
```

### Test 2: JSON Export

**What it tests:**
- Export endpoint returns valid JSON
- JSON is an array of objects
- All 100K records are exported
- Each record has correct structure

**Expected results:**
- Response status: 200-299
- Content-Type: application/json
- JSON array with 100K+ objects
- Each object has field keys

**Verification:**
```bash
npx playwright test large-dataset-export.spec.ts -g "JSON Export"
```

### Test 3: Immediate Start

**What it tests:**
- Export request starts immediately
- HTTP 202 status returned
- Time to first byte < 5 seconds

**Expected results:**
- Response status: 202
- Time to first byte < 5000ms

**Verification:**
```bash
npx playwright test large-dataset-export.spec.ts -g "immediately"
```

### Test 4: Streaming and Progress

**What it tests:**
- Streaming response (multiple chunks)
- Download progress tracking
- Reasonable download speed
- No timeout during download

**Expected results:**
- Multiple chunks received (> 1)
- Download speed > 0.1 MB/s
- Duration < 120 seconds
- Total file size appropriate for 100K records

**Verification:**
```bash
npx playwright test large-dataset-export.spec.ts -g "streaming"
```

## Expected Performance

For a table with 100K records and ~10 fields:

| Metric | Target | Acceptable |
|--------|--------|------------|
| Time to first byte | < 1s | < 5s |
| Total export time (CSV) | < 30s | < 60s |
| Total export time (JSON) | < 45s | < 90s |
| Download speed | > 5 MB/s | > 0.1 MB/s |
| File size (CSV) | ~20-50 MB | - |
| File size (JSON) | ~30-80 MB | - |

## Troubleshooting

### Test Fails: "TABLE_ID environment variable is required"

**Solution:** Set the TABLE_ID environment variable:
```bash
export TABLE_ID="your-table-uuid"
```

### Test Fails: "AUTH_TOKEN environment variable is required"

**Solution:** Set the AUTH_TOKEN environment variable:
```bash
export AUTH_TOKEN="your-auth-token"
```

### Test Fails: "ECONNREFUSED" or "Network error"

**Solution:** Ensure backend server is running:
```bash
# Check if backend is running
curl http://localhost:8000/api/v1/health

# Start backend if not running
uvicorn src.pybase.main:app --reload
```

### Test Fails: "401 Unauthorized"

**Solution:** Verify your AUTH_TOKEN is valid:
```bash
# Test token with API
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  http://localhost:8000/api/v1/me
```

### Test Fails: "404 Not Found" or "Table not found"

**Solution:** Verify TABLE_ID exists:
```bash
# Check if table exists (requires valid auth)
curl -H "Authorization: Bearer $AUTH_TOKEN" \
  http://localhost:8000/api/v1/tables/$TABLE_ID
```

### Test Fails: "Timeout exceeded"

**Possible causes:**
1. Database not optimized (missing indexes)
2. Backend server overloaded
3. Network issues

**Solutions:**
```bash
# Check database has required indexes
psql $DATABASE_URL -c "\d records" | grep table_id_created_at

# Restart backend server
# Increase Playwright timeout in test file
```

### Test Fails: "Exported records count less than expected"

**Solution:** Verify database has 100K records:
```bash
psql $DATABASE_URL -c \
  "SELECT COUNT(*) FROM records WHERE table_id = '$TABLE_ID' AND deleted_at IS NULL;"
```

## Manual Testing

You can also test export manually via browser:

1. Open browser DevTools
2. Set auth token in localStorage:
   ```javascript
   localStorage.setItem('token', 'your-auth-token')
   ```
3. Navigate to your table view
4. Open Network tab in DevTools
5. Trigger export (via UI or console):
   ```javascript
   fetch('http://localhost:8000/api/v1/records/export?table_id=YOUR_TABLE_ID&format=csv', {
     method: 'POST',
     headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
   })
   .then(resp => resp.text())
   .then(data => console.log(data.split('\n').length + ' lines'))
   ```
6. Verify in Network tab:
   - Status: 202
   - Response contains CSV data
   - Download completes successfully

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Export E2E Tests

on: [push, pull_request]

jobs:
  export-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[all]"

      - name: Seed test data
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
          TABLE_ID: ${{ secrets.TEST_TABLE_ID }}
        run: |
          python scripts/seed_large_dataset.py --table $TABLE_ID --count 100000

      - name: Start backend
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
        run: |
          uvicorn src.pybase.main:app &
          sleep 10

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install Playwright
        run: |
          cd frontend
          npm install
          npx playwright install --with-deps

      - name: Run export tests
        env:
          TABLE_ID: ${{ secrets.TEST_TABLE_ID }}
          AUTH_TOKEN: ${{ secrets.TEST_AUTH_TOKEN }}
          API_BASE_URL: http://localhost:8000
        run: |
          cd frontend
          npx playwright test large-dataset-export.spec.ts

      - name: Upload test results
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

## Next Steps

After export testing passes:
1. Test with different dataset sizes (10K, 50K, 100K, 500K)
2. Test with different field types
3. Test with filtered data
4. Load test with concurrent exports
5. Verify memory usage during export

## Related Files

- Test file: `frontend/e2e/large-dataset-export.spec.ts`
- Test script: `scripts/run_export_test.sh`
- Backend service: `src/pybase/services/export_service.py`
- Frontend utils: `frontend/src/utils/exportUtils.ts`
- Seed script: `scripts/seed_large_dataset.py`
