# Performance Testing Guide

This guide provides instructions for performing comprehensive performance testing on all 7 view types with large datasets (10K+ records).

## Prerequisites

1. **Backend Running**: FastAPI server must be running on `http://localhost:8000`
2. **Frontend Running**: Vite dev server must be running on `http://localhost:5173`
3. **Database**: PostgreSQL database must be accessible
4. **Test Data**: 10K+ records dataset must be generated

## Setup

### 1. Generate Test Data

Generate 10,000 test records:

```bash
# From project root
python tests/performance/generate_test_data.py --count 10000
```

For more comprehensive testing, generate 15,000 records:

```bash
python tests/performance/generate_test_data.py --count 15000
```

To start fresh (clean database):

```bash
python tests/performance/generate_test_data.py --count 10000 --clean
```

### 2. Start Services

Ensure both backend and frontend are running:

```bash
# Terminal 1 - Backend
cd src
uvicorn pybase.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### 3. Open Browser with DevTools

1. Open Chrome or Edge browser
2. Open DevTools (F12)
3. Go to Performance tab
4. Enable "Screenshots" and "Memory" options
5. Navigate to the test table URL (displayed after data generation)

## Performance Test Procedures

### Test 1: Initial Render Performance

**Objective**: Verify initial view render time < 2 seconds

**Steps**:
1. Clear browser cache (Ctrl+Shift+Del)
2. Open DevTools Performance tab
3. Click "Record" button
4. Navigate to table URL: `http://localhost:5173/tables/{table_id}`
5. Wait for Grid view to fully render
6. Stop recording
7. Measure time from navigation start to DOM content loaded

**Expected Results**:
- Initial Grid view render: < 2 seconds
- All records visible (virtualized scrolling)
- No visible lag or jank

**Metrics to Record**:
- Time to First Paint (FP)
- Time to First Contentful Paint (FCP)
- Time to Interactive (TTI)
- Total Blocking Time (TBT)

### Test 2: View Switching Performance

**Objective**: Verify view switch time < 500ms

**Steps**:
1. Start from Grid view (already loaded)
2. Open DevTools Performance tab
3. Click "Record" button
4. Click each view button in sequence:
   - Kanban
   - Calendar
   - Form
   - Gallery
   - Gantt
   - Timeline
5. Stop recording after all views tested
6. Measure time between click and view fully rendered for each

**Expected Results**:
- Each view switch: < 500ms
- Smooth transition (no flash of unstyled content)
- Data renders correctly in each view

**Metrics to Record** (for each view):
- Click to render time
- Layout shift (CLS)
- Frame rate during transition

### Test 3: Scrolling Performance

**Objective**: Verify smooth scrolling (60fps) in all views

**Steps**:
For each view type:
1. Load the view
2. Open DevTools Performance tab
3. Enable "Enable advanced paint instrumentation"
4. Start recording
5. Scroll smoothly from top to bottom (5 seconds)
6. Stop recording
7. Check frame rate in timeline

**Expected Results**:
- Consistent 60fps during scrolling
- No dropped frames (< 5% frame drops acceptable)
- Virtualized rendering working (only visible records in DOM)

**Views to Test**:
- ✓ Grid view (vertical scroll)
- ✓ Kanban view (horizontal scroll)
- ✓ Calendar view (scroll through months)
- ✓ Gallery view (grid scroll)
- ✓ Gantt view (horizontal timeline scroll)
- ✓ Timeline view (vertical date groups scroll)
- ✓ Form view (scroll through fields)

### Test 4: Memory Leak Detection

**Objective**: Verify no memory leaks during extended use

**Steps**:
1. Open DevTools Memory tab
2. Take heap snapshot (baseline)
3. Perform the following cycle 5 times:
   - Switch to each of 7 views
   - Scroll through data
   - Return to Grid view
4. Force garbage collection (DevTools -> Memory -> 🗑️ icon)
5. Take another heap snapshot
6. Compare snapshots

**Expected Results**:
- Memory increase < 50MB after 5 cycles
- No detached DOM nodes accumulating
- Event listeners properly cleaned up

**Metrics to Record**:
- Initial heap size
- Final heap size (after GC)
- Detached DOM nodes count
- Event listeners count

### Test 5: Interaction Performance

**Objective**: Verify interactive features remain responsive

**Steps for each applicable view**:

#### Grid View
1. Select multiple rows (Shift+Click)
2. Edit cell inline
3. Sort by different columns
4. Filter records
5. Add new record

#### Kanban View
1. Drag card between columns (5 times)
2. Measure drag response time
3. Verify update persistence

#### Gantt View
1. Drag task bar to new date (5 times)
2. Resize task duration (5 times)
3. Measure drag response time

#### Gallery View
1. Open settings panel
2. Change card size (small/medium/large)
3. Select different cover field
4. Click cards to open details

**Expected Results**:
- All interactions respond within 100ms
- Drag operations smooth (60fps)
- UI remains responsive during updates

### Test 6: Network Performance

**Objective**: Verify efficient data fetching and caching

**Steps**:
1. Open DevTools Network tab
2. Clear network log
3. Load Grid view
4. Switch to other views
5. Return to Grid view (should use cache)

**Expected Results**:
- Initial data fetch: < 1 second
- Subsequent same-view loads: cached (0 network requests)
- WebSocket connection stable
- No redundant API calls

**Metrics to Record**:
- Initial data fetch time
- Data transfer size
- Number of API calls per view
- WebSocket message frequency

## Performance Metrics Summary

Create a summary table of all metrics:

| View | Initial Render | View Switch | Scroll FPS | Memory Usage | Interactions |
|------|---------------|-------------|------------|--------------|--------------|
| Grid | XXXms | XXXms | XXfps | XXmb | XXms |
| Kanban | - | XXXms | XXfps | XXmb | XXms |
| Calendar | - | XXXms | XXfps | XXmb | XXms |
| Form | - | XXXms | XXfps | XXmb | XXms |
| Gallery | - | XXXms | XXfps | XXmb | XXms |
| Gantt | - | XXXms | XXfps | XXmb | XXms |
| Timeline | - | XXXms | XXfps | XXmb | XXms |

## Acceptance Criteria

All tests must meet these criteria:

- ✓ Initial render < 2 seconds
- ✓ View switching < 500ms
- ✓ Scrolling at 60fps (< 5% drops)
- ✓ Memory increase < 50MB after extended use
- ✓ No memory leaks (detached nodes)
- ✓ Interactions respond within 100ms
- ✓ Drag operations smooth (60fps)

## Troubleshooting

### Slow Initial Render
- Check database query performance
- Verify indexes on records table
- Check network latency
- Verify virtualization enabled

### View Switching Lag
- Check component mount/unmount logic
- Verify data transformation efficiency
- Check for unnecessary re-renders
- Profile with React DevTools Profiler

### Scrolling Jank
- Verify virtual scrolling enabled
- Check for expensive render operations
- Look for layout thrashing
- Optimize CSS animations

### Memory Leaks
- Check WebSocket cleanup
- Verify event listener removal
- Check React useEffect cleanup functions
- Look for closure memory retention

## Tools

### Chrome DevTools
- **Performance**: Record runtime performance
- **Memory**: Heap snapshots and allocation timeline
- **Network**: Monitor API calls and data transfer
- **Coverage**: Identify unused code

### React DevTools Profiler
- Component render times
- Render frequency
- Props/state changes causing re-renders

### Lighthouse
- Run Lighthouse performance audit
- Target score: > 90

## Automated Performance Tests

Run automated performance tests:

```bash
# Backend performance tests
pytest tests/performance/ -v -m performance

# Frontend performance tests (if available)
cd frontend
npm run test:performance
```

## Reporting

Document all results in `PERFORMANCE_TEST_REPORT.md`:
- Test environment details
- All metrics recorded
- Screenshots of DevTools
- Issues discovered
- Recommendations

## Notes

- Perform tests on a clean browser profile
- Disable browser extensions during testing
- Use consistent hardware for reproducible results
- Test on multiple browsers if possible (Chrome, Firefox, Safari)
- Consider testing on different network conditions (throttling)
