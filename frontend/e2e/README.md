# Performance Testing Guide

This guide explains how to run and verify performance tests for the virtual scrolling feature with 100K records.

## Prerequisites

1. **Database Setup**: Seed the database with 100K test records
   ```bash
   python scripts/seed_large_dataset.py --table <TABLE_ID> --count 100000
   ```

2. **Environment Variables**: Set required environment variables
   ```bash
   export TABLE_ID=<your_test_table_id>
   export BASE_URL=http://localhost:5173  # Optional, defaults to this
   ```

3. **Install Playwright Browsers** (first time only):
   ```bash
   cd frontend
   npx playwright install chromium
   ```

## Running Automated Tests

### Run All Performance Tests
```bash
cd frontend
npm run test:e2e
```

### Run Specific Test File
```bash
cd frontend
npx playwright test virtual-scrolling-performance.spec.ts
```

### Run with UI Mode (Interactive)
```bash
cd frontend
npx playwright test --ui
```

### Run with Debugging
```bash
cd frontend
npx playwright test --debug
```

## Test Descriptions

### Test 1: 60 FPS Scroll Verification
**File**: `virtual-scrolling-performance.spec.ts` → `should maintain 60 FPS when scrolling through 100K records`

**What it tests**:
- Scrolls through 100K records in chunks
- Measures FPS during scrolling
- Verifies average FPS > 55
- Verifies minimum FPS > 30
- Checks memory usage remains constant (< 50MB increase)
- Validates DOM size stays < 150 rows

**Expected Results**:
```
Average FPS: ~58-60
Min FPS: > 30
Max FPS: ~60
Memory increase: < 50MB
DOM size: ~100 rows
```

### Test 2: Virtualization Verification
**File**: `virtual-scrolling-performance.spec.ts` → `should render only visible records with virtual scrolling`

**What it tests**:
- Verifies only ~100 records in DOM (not 100K)
- Confirms DOM size remains constant during scrolling
- Validates virtual scrolling is working

**Expected Results**:
```
Virtualized rows in DOM: ~100
Total records in table: 100000
DOM size after scrolling: ~100 (constant)
```

### Test 3: Responsiveness During Rapid Scrolling
**File**: `virtual-scrolling-performance.spec.ts` → `should maintain responsiveness during rapid scrolling`

**What it tests**:
- Performs 50 rapid scrolls
- Measures total scroll time
- Verifies each scroll completes in < 50ms
- Confirms UI remains interactive

**Expected Results**:
```
Total scroll time: < 2500ms (50ms per scroll average)
UI interactive: true
```

## Manual Verification with Chrome DevTools

### Step 1: Open Chrome DevTools
1. Navigate to `http://localhost:5173/tables/<TABLE_ID>?view=virtual-grid`
2. Press `F12` or `Ctrl+Shift+I` to open DevTools
3. Go to the **Performance** tab

### Step 2: Record Performance
1. Click the **Record** button (circle icon)
2. Scroll continuously through the entire list
3. Click **Stop** after scrolling completes

### Step 3: Verify Metrics
Check the following in the performance profile:

#### FPS (Frames Per Second)
- Look at the **FPS** chart in the timeline
- Verify FPS stays near 60 FPS during scrolling
- Acceptable range: 55-60 FPS

#### Frame Time
- Check **Frame Timing** section
- Each frame should take ~16.6ms (60 FPS)
- No long tasks (> 50ms)

#### Memory
- Go to **Memory** tab
- Take heap snapshot before scrolling
- Scroll through entire list
- Take another heap snapshot
- Compare: Memory increase should be < 50MB

#### DOM Size
- Go to **Elements** tab
- Open Console
- Run: `document.querySelectorAll('[data-testid^="virtual-row-"]').length`
- Should return ~100 (not 100,000)

## Performance Benchmarks

### Target Metrics
| Metric | Target | Acceptable |
|--------|--------|------------|
| Average FPS | 60 | > 55 |
| Min FPS | 60 | > 30 |
| Initial Load | < 500ms | < 1000ms |
| Memory Usage | < 100MB | < 200MB |
| Memory Leak | 0 MB | < 50MB |
| DOM Nodes | ~100 | < 150 |

### Comparison with Alternatives
- **Airtable**: Performance degrades at 50K records
- **Notion**: Performance issues at 10K records
- **PyBase Target**: Smooth performance at 100K+ records

## Troubleshooting

### Test Failures

#### Low FPS Detected
- Check if backend API is responding quickly enough
- Verify database has proper indexes on `(table_id, created_at)`
- Check network tab for slow API requests
- Ensure Redis caching is enabled

#### High Memory Usage
- Check for memory leaks in React components
- Verify proper cleanup in useEffect hooks
- Check if Service Worker is caching too much

#### DOM Size Too Large
- Verify virtual scrolling is enabled (check `?view=virtual-grid`)
- Check if @tanstack/react-virtual is working
- Verify row height is fixed at 40px

### Common Issues

#### "TABLE_ID not set" Error
```bash
export TABLE_ID=<your_table_uuid>
```

#### Connection Refused
Ensure the backend is running:
```bash
python src/pybase/main.py
```

#### Browser Not Found
Install Playwright browsers:
```bash
cd frontend
npx playwright install
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Performance Tests
  run: |
    cd frontend
    npm run test:e2e
  env:
    TABLE_ID: ${{ secrets.TEST_TABLE_ID }}
```

### Performance Regression Detection
- Store baseline metrics in `performance-baseline.json`
- Compare test results against baseline
- Fail build if metrics degrade by > 10%

## Additional Resources

- [Playwright Documentation](https://playwright.dev/)
- [React Virtual Documentation](https://tanstack.com/virtual/latest)
- [Chrome DevTools Performance](https://developer.chrome.com/docs/devtools/performance/)
- [Web Performance Testing](https://web.dev/performance/)
