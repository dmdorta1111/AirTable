# Memory Leak Testing Guide

This guide explains how to perform manual memory leak testing using React DevTools Profiler to ensure the virtualized grid view maintains constant memory usage regardless of dataset size.

## Overview

Memory leak testing verifies that:
- Memory usage remains constant (~50-100MB) regardless of dataset size
- No memory leaks occur during scrolling through large datasets
- React components properly unmount when scrolling away
- Event listeners and subscriptions are properly cleaned up
- Virtual scrolling doesn't accumulate detached DOM nodes

## Why Manual Testing?

While automated E2E tests (in `virtual-scrolling-performance.spec.ts`) check basic memory metrics, manual testing with React DevTools Profiler provides deeper insights:
- Component mount/unmount patterns
- React render count and duration
- Component state and props changes
- Identifies which components cause memory retention
- Detects memory leaks from closures, event listeners, etc.

## Prerequisites

### 1. Database Seeding

Seed your database with test records (various sizes):

```bash
# Test with 10K records (baseline)
python scripts/seed_large_dataset.py --table YOUR_TABLE_ID --count 10000

# Test with 100K records (target)
python scripts/seed_large_dataset.py --table YOUR_TABLE_ID --count 100000

# Optional: Test with 1M records (stress test)
python scripts/seed_large_dataset.py --table YOUR_TABLE_ID --count 1000000
```

### 2. Install React DevTools

Install React DevTools browser extension:
- **Chrome**: [React Developer Tools](https://chrome.google.com/webstore/detail/react-developer-tools/fmkadmapgofadopljbjfkapdkoienihi)
- **Firefox**: [React Developer Tools](https://addons.mozilla.org/en-US/firefox/addon/react-devtools/)
- **Edge**: Available in Edge Add-ons

### 3. Application Setup

Ensure your application is running:

```bash
# Terminal 1: Start backend
uvicorn src.pybase.main:app --reload

# Terminal 2: Start frontend
cd frontend
npm run dev
```

### 4. Browser Configuration

For accurate memory measurements:
1. Open Chrome/Edge DevTools (F12)
2. Go to **Performance** tab
3. Click the gear icon (⚙️) for settings
4. Enable:
   - ☑️ **Capture screenshots**
   - ☑️ **Memory**
   - ☑️ **Enable advanced paint instrumentation** (optional)

## Testing Procedure

### Step 1: Baseline Memory Measurement

1. Open a new incognito window (to ensure clean state)
2. Navigate to: `http://localhost:5173/tables/YOUR_TABLE_ID?view=virtual-grid`
3. Open DevTools and switch to **Memory** tab
4. Select **Heap snapshot** radio button
5. Click **Take snapshot** button
6. Wait for snapshot to complete
7. Note the **Total memory** value (should be ~30-50MB for empty page)

**Expected Result:** Baseline memory ~30-50MB

### Step 2: Initial Load Memory Check

1. Refresh the page (Cmd+R / Ctrl+R)
2. Wait for initial data to load (first ~50 records)
3. Take another heap snapshot
4. Note the memory increase

**Expected Result:** Memory should increase to ~50-100MB

### Step 3: Scroll Through Dataset

1. Switch to **Profiler** tab in React DevTools
2. Click the **Record** button (⏺️)
3. Slowly scroll through the entire dataset (or at least 1000 records)
4. Click the **Stop** button (⏹️) after scrolling
5. Analyze the recorded profile

**What to Check:**
- **Flamegraph**: Look for components that remain mounted
- **Ranked**: Check which components take most memory
- **Timeline**: Verify render count is reasonable

### Step 4: Memory Leak Detection - Heap Snapshots

1. Switch to **Memory** tab
2. Take a heap snapshot (Snapshot 1)
3. Scroll through ~500 records
4. Take another heap snapshot (Snapshot 2)
5. Scroll through another ~500 records
6. Take a third heap snapshot (Snapshot 3)
7. Select **Snapshot 3** and change view to **Comparison** (vs. Snapshot 2)
8. Look for:
   - **Detached DOM nodes** (indicates unmounted components not garbage collected)
   - **Event listeners** (indicates missing cleanup)
   - **Strings/Objects** accumulating (indicates data retention)

**Expected Result:**
- No detached DOM nodes
- Memory difference between snapshots should be minimal (< 5MB)
- Total memory should remain constant (~50-100MB)

### Step 5: Component Mount/Unmount Verification

1. Switch to **Components** tab in React DevTools
2. Expand the component tree to find virtualized rows
3. Scroll down slowly and observe:
   - Components at top should unmount (disappear from tree)
   - New components at bottom should mount (appear in tree)
   - Total component count should remain ~100-150

**Expected Result:**
- Only visible rows + overscan rows are mounted
- Total components: ~100-150 (not 100K)
- Components unmount properly when scrolling out of view

### Step 6: Force Garbage Collection

Chrome supports manual garbage collection:

1. Open DevTools **Console** tab
2. Run: `performance.memory.usedJSHeapSize` to check current memory
3. Run: `--expose-gc` (Note: Only works if Chrome was launched with `--js-flags="--expose-gc"`)
4. If available, run: `gc()` to force garbage collection
5. Run: `performance.memory.usedJSHeapSize` again
6. Compare memory before/after GC

**Alternative (without --expose-gc flag):**
1. Take heap snapshot
2. Click the garbage collection icon (🗑️) in Memory tab
3. Take another heap snapshot
4. Compare memory usage

**Expected Result:**
- Memory should decrease after GC (if there was garbage)
- Baseline memory should be similar to Step 2

### Step 7: Extended Scroll Stress Test

1. Take initial heap snapshot
2. Rapidly scroll up and down for 2 minutes
3. Take final heap snapshot
4. Compare snapshots

**Expected Result:**
- Memory increase < 20MB
- No significant accumulation of objects
- No detached DOM nodes

## React DevTools Profiler Analysis

### Understanding the Profiler Tabs

#### 1. Flamegraph
Shows component hierarchy and render times:
- **Width**: Render duration
- **Height**: Component depth in tree
- **Color**: Why component rendered (props/state change)

**What to Look For:**
- Components that re-render unnecessarily (wide bars)
- Components that re-render on every scroll (indicates missing memoization)

#### 2. Ranked
Lists components by render time (sorted by impact):

**What to Look For:**
- `VirtualizedGridView` should be at top (expected)
- Individual `VirtualRow` components should have very short render times (< 1ms)
- Total render time for all rows should be < 16ms (60 FPS)

#### 3. Timeline
Shows render performance over time:

**What to Look For:**
- Renders should be sporadic (not continuous during scroll)
- No long tasks (> 50ms) that block main thread
- FPS should remain ~60

#### 4. Interactions
Shows what triggered renders (clicks, scrolls, etc.):

**What to Look For:**
- Scroll events should trigger minimal renders
- State updates should be batched
- No cascading re-renders

## Common Memory Leak Patterns

### Pattern 1: Missing Cleanup in useEffect

**Problem:** Event listeners or subscriptions not removed:

```typescript
// BAD - Memory leak
useEffect(() => {
  window.addEventListener('resize', handleResize);
}, []); // Missing cleanup

// GOOD - Proper cleanup
useEffect(() => {
  window.addEventListener('resize', handleResize);
  return () => window.removeEventListener('resize', handleResize);
}, []);
```

**Detection:**
- Heap snapshot shows increasing number of event listeners
- Components remain mounted after unmounting

### Pattern 2: Closure Retention

**Problem:** Large objects captured in closures:

```typescript
// BAD - Entire dataset captured in closure
useEffect(() => {
  const handler = () => {
    console.log(largeDataset.length); // Closes over largeDataset
  };
  // ...
}, [largeDataset]); // Re-created on every data change
```

**Detection:**
- Heap snapshot shows many copies of same large object
- Memory usage increases over time

### Pattern 3: Detached DOM Nodes

**Problem:** DOM nodes removed from document but not garbage collected:

```typescript
// BAD - Stores DOM node in ref
const rowRef = useRef(null);
useEffect(() => {
  storedRefs.current.push(rowRef.current); // Never cleared
}, []);
```

**Detection:**
- Heap snapshot comparison shows "Detached DOM nodes"
- Memory keeps increasing during scrolling

### Pattern 4: Missing Key Props

**Problem:** React can't track component identity:

```typescript
// BAD - Index as key
{records.map((record, index) => (
  <VirtualRow key={index} ... />
))}

// GOOD - Stable key
{records.map((record) => (
  <VirtualRow key={record.id} ... />
))}
```

**Detection:**
- Profiler shows unnecessary unmount/remount cycles
- Components re-render when scrolling

## Performance Benchmarks

| Metric | Target | Acceptable | Notes |
|--------|--------|------------|-------|
| Initial Load | < 100MB | < 150MB | After 50 records load |
| During Scroll | Constant | ±20MB | Should not increase |
| After 5 min scroll | < 100MB | < 200MB | Extended scrolling |
| GC Recovery | > 80% | > 50% | Memory freed after GC |
| Component Count | ~100 | < 150 | Mounted components |
| Detached DOM Nodes | 0 | 0 | Should be zero |
| Event Listeners | Constant | ±5 | Should not accumulate |

## Troubleshooting

### Issue: Memory keeps increasing during scroll

**Possible causes:**
1. Components not unmounting properly
2. Missing cleanup in useEffect hooks
3. Refs storing DOM nodes
4. Closures capturing large objects

**Solutions:**
1. Check Components tab - verify components unmount
2. Check for missing cleanup functions in useEffect
3. Search code for `.current =` assignments to refs
4. Review closure patterns in event handlers

### Issue: Detached DOM nodes found

**Possible causes:**
1. Missing key prop in lists
2. Improper ref usage
3. Third-party library not cleaning up

**Solutions:**
1. Ensure all `.map()` calls have stable `key` props
2. Clear refs in useEffect cleanup
3. Check third-party library documentation

### Issue: High component count (> 500)

**Possible causes:**
1. Overscan value too high
2. Virtual scrolling not working
3. Regular GridView being used instead

**Solutions:**
1. Check `overscan` prop in useVirtualizer config
2. Verify URL has `?view=virtual-grid`
3. Check browser console for errors

### Issue: Memory not released after GC

**Possible causes:**
1. Global variables holding references
2. Module-level state
3. Cache not cleared

**Solutions:**
1. Check for `window.` or `global.` assignments
2. Review module-level variables
3. Clear caches in useEffect cleanup

## Testing Checklist

Use this checklist to ensure comprehensive testing:

- [ ] Database seeded with test data (100K records)
- [ ] React DevTools installed
- [ ] Baseline memory measured (< 50MB)
- [ ] Initial load memory checked (50-100MB)
- [ ] Scrolled through 1000+ records
- [ ] Heap snapshots taken at multiple points
- [ ] No detached DOM nodes found
- [ ] Component count verified (~100-150)
- [ ] Components properly unmount on scroll
- [ ] Memory remains constant during extended scrolling
- [ ] Force garbage collection tested
- [ ] Stress test completed (5+ minutes of scrolling)
- [ ] No event listener accumulation
- [ ] Profiler shows reasonable render times
- [ ] FPS remains ~60 during scroll
- [ ] Tested with different dataset sizes (10K, 100K)

## CI/CD Integration

While memory leak testing is primarily manual, you can add basic checks to CI/CD:

```yaml
name: Memory Leak Tests

on: [push, pull_request]

jobs:
  memory-test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd frontend
          npm install

      - name: Run basic memory check
        run: |
          cd frontend
          npx playwright test virtual-scrolling-performance.spec.ts -g "memory"

      - name: Check for memory regression
        run: |
          # Parse test results for memory metrics
          # Fail if memory usage increased significantly
```

## Related Documentation

- Performance Testing: `frontend/e2e/README.md`
- Export Testing: `frontend/e2e/EXPORT_TESTING.md`
- Implementation Summary: `frontend/e2e/TESTING_SUMMARY.md`
- Virtualized Component: `frontend/src/components/views/VirtualizedGridView.tsx`
- Hook: `frontend/src/hooks/useVirtualizedRecords.ts`

## Next Steps

After completing memory leak testing:
1. Document any issues found
2. Fix memory leaks if detected
3. Re-test to verify fixes
4. Add automated tests for regression prevention
5. Consider performance monitoring in production
