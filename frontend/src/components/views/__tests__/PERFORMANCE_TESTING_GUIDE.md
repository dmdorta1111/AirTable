# Gantt View Performance Testing Guide

This guide provides comprehensive instructions for testing the performance of the Gantt view component with large datasets.

## Overview

The Gantt view performance testing suite includes:
- **Test Data Generators**: Create realistic project datasets with 25-200+ tasks
- **Performance Monitoring**: Measure rendering, calculations, and export times
- **Automated Benchmarks**: Run standardized performance tests

## Quick Start

### 1. Run Performance Tests in Development Mode

```bash
cd frontend
npm run dev
```

Navigate to a table with Gantt view in your application.

### 2. Use Test Data Generators

Import the test data generator in your browser console or test file:

```javascript
import { getTestData, testPresets } from './gantt-test-data-generator';

// Get 100 tasks (standard test)
const testData = getTestData('large');

// Get 200 tasks (stress test)
const stressData = getTestData('xlarge');

// Get realistic software project
const softwareProject = getTestData('software');
```

### 3. Monitor Performance

Import the performance monitor:

```javascript
import { performanceMonitor } from './gantt-performance-monitor';

// Start monitoring
performanceMonitor.startMark('initialRender');

// ... render component ...

// Stop monitoring
const renderTime = performanceMonitor.endMark('initialRender');
console.log(`Render time: ${renderTime}ms`);
```

## Test Scenarios

### Scenario 1: Small Dataset (25 Tasks)

**Purpose**: Verify baseline performance
**Expected**: All operations < 500ms

```javascript
const data = getTestData('small');
// Test rendering
// Test interactions
// Test exports
```

### Scenario 2: Medium Dataset (50 Tasks)

**Purpose**: Verify scalability
**Expected**: Rendering < 1000ms, exports < 3000ms

```javascript
const data = getTestData('medium');
// Test with dependencies visible
// Test with critical path enabled
// Test drag operations
```

### Scenario 3: Large Dataset (100 Tasks) - Standard Test

**Purpose**: Verify performance with realistic project size
**Expected**: Rendering < 2000ms, exports < 5000ms

```javascript
const data = getTestData('large');

// 1. Test initial render
performanceMonitor.startMark('initialRender');
// Mount component with data
const renderTime = performanceMonitor.endMark('initialRender');

// 2. Test critical path calculation
performanceMonitor.startMark('criticalPathCalculation');
// Toggle critical path
const criticalPathTime = performanceMonitor.endMark('criticalPathCalculation');

// 3. Test dependency rendering
performanceMonitor.startMark('dependencyRender');
// Toggle dependencies
const dependencyTime = performanceMonitor.endMark('dependencyRender');

// 4. Test drag operation
performanceMonitor.startMark('dragOperation');
// Drag a task
const dragTime = performanceMonitor.endMark('dragOperation');

// 5. Test PNG export
performanceMonitor.startMark('pngExport');
// Export as PNG
const pngTime = performanceMonitor.endMark('pngExport');

// 6. Test PDF export
performanceMonitor.startMark('pdfExport');
// Export as PDF
const pdfTime = performanceMonitor.endMark('pdfExport');

// Generate report
const report = performanceMonitor.generateReport(100);
performanceMonitor.printReport(report);
```

### Scenario 4: Extra Large Dataset (200 Tasks) - Stress Test

**Purpose**: Identify performance limits
**Expected**: Rendering < 4000ms, exports < 10000ms

```javascript
const data = getTestData('xlarge');
// Run all tests from Scenario 3
// Monitor memory usage
// Check for frame rate drops
```

### Scenario 5: Realistic Software Project

**Purpose**: Test with realistic project structure
**Expected**: Similar to large dataset

```javascript
const data = getTestData('software');
// Test with realistic dependencies
// Test with phase-based structure
// Verify critical path identifies correctly
```

### Scenario 6: Maximum Complexity

**Purpose**: Test with dense dependency network
**Expected**: Critical path calculation is bottleneck

```javascript
const data = getTestData('maxComplexity');
// Focus on critical path performance
// Test with all dependencies visible
```

## Performance Benchmarks

### Thresholds by Dataset Size

| Metric | 25 Tasks | 50 Tasks | 100 Tasks | 200 Tasks |
|--------|----------|----------|-----------|-----------|
| Initial Render | < 500ms | < 1000ms | < 2000ms | < 4000ms |
| Critical Path Calc | < 100ms | < 200ms | < 500ms | < 1000ms |
| Dependency Calc | < 50ms | < 100ms | < 200ms | < 400ms |
| Drag Operation | < 100ms | < 150ms | < 200ms | < 300ms |
| PNG Export | < 2000ms | < 3000ms | < 5000ms | < 10000ms |
| PDF Export | < 2000ms | < 3000ms | < 5000ms | < 10000ms |
| Frame Rate | > 60 FPS | > 60 FPS | > 30 FPS | > 30 FPS |

## Manual Testing Checklist

### Initial Load Performance

- [ ] Dataset loads without blocking UI
- [ ] Spinner shows during load
- [ ] No console errors during load
- [ ] Memory usage is reasonable (< 100MB for 100 tasks)

### Rendering Performance

- [ ] All 100+ task bars render
- [ ] Timeline header renders correctly
- [ ] Task names are visible
- [ ] Status colors display properly
- [ ] Progress bars show correctly

### Interaction Performance

- [ ] Dragging tasks is smooth (no lag)
- [ ] Resizing tasks responds quickly
- [ ] Hover tooltips appear instantly
- [ ] Scroll is smooth (60 FPS)
- [ ] Click operations respond immediately

### Feature Toggle Performance

- [ ] Dependency lines toggle is instant
- [ ] Critical path toggle is instant
- [ ] View mode switches are smooth
- [ ] Filter updates are quick

### Export Performance

- [ ] PNG export completes in < 5 seconds (100 tasks)
- [ ] PDF export completes in < 5 seconds (100 tasks)
- [ ] Loading indicator shows during export
- [ ] Export quality is acceptable
- [ ] File downloads correctly

### Critical Path Performance

- [ ] Calculation completes in < 500ms (100 tasks)
- [ ] Toggle is instant after calculation
- [ ] Correct tasks are highlighted
- [ ] Multiple clicks don't slow down

## Browser DevTools Measurements

### Chrome DevTools Performance Profile

1. Open Chrome DevTools (F12)
2. Go to Performance tab
3. Click "Record"
4. Load Gantt view with 100 tasks
5. Stop recording
6. Analyze:
   - Main thread activity
   - Scripting time
   - Rendering time
   - Frame rate

### Memory Profiling

1. Open Chrome DevTools (F12)
2. Go to Memory tab
3. Take heap snapshot before loading
4. Load Gantt view with 100 tasks
5. Take heap snapshot after loading
6. Compare snapshots:
   - Look for memory leaks
   - Check total heap size
   - Verify no detached DOM nodes

### Network Throttling

Test performance on slow connections:

1. Open Chrome DevTools (F12)
2. Go to Network tab
3. Select throttling: "Slow 3G"
4. Load Gantt view
5. Measure time to interactive

## Automated Testing

### Unit Test Performance

Add performance tests to `GanttView.test.tsx`:

```typescript
describe('GanttView Performance', () => {
  it('should render 100 tasks in under 2 seconds', async () => {
    const testData = getTestData('large');

    const startTime = performance.now();
    render(<GanttView data={testData} fields={fields} />);
    await waitFor(() => expect(screen.getAllByRole('row')).toHaveLength(100));

    const endTime = performance.now();
    expect(endTime - startTime).toBeLessThan(2000);
  });

  it('should calculate critical path for 100 tasks in under 500ms', async () => {
    const testData = getTestData('large');

    const startTime = performance.now();
    // Trigger critical path calculation
    const endTime = performance.now();

    expect(endTime - startTime).toBeLessThan(500);
  });
});
```

## Common Performance Issues and Solutions

### Issue: Slow Initial Render

**Symptoms**: Takes > 2 seconds to render 100 tasks
**Solutions**:
- Verify React.memo is used on expensive components
- Check for unnecessary re-renders with React DevTools Profiler
- Consider virtualization for very large datasets

### Issue: Laggy Drag Operations

**Symptoms**: Dragging tasks feels sluggish
**Solutions**:
- Verify onCellUpdate is debounced
- Check for expensive calculations in onMouseMove
- Use requestAnimationFrame for updates

### Issue: Slow Critical Path Calculation

**Symptoms**: Takes > 500ms for 100 tasks
**Solutions**:
- Verify useMemo dependencies are correct
- Check that dependency graph is cached
- Consider web worker for very large projects

### Issue: Export Timeout

**Symptoms**: Export takes > 5 seconds or fails
**Solutions**:
- Reduce canvas scale factor
- Implement progressive rendering
- Add timeout with user notification

## Performance Optimization Tips

### React Optimization

1. **Use React.memo**: Memoize expensive child components
2. **Use useMemo**: Cache expensive calculations
3. **Use useCallback**: Prevent function recreation
4. **Avoid inline objects**: Create objects outside render

### Dependency Line Optimization

1. **Batch updates**: Update all lines in single render
2. **Use SVG efficiently**: Minimize DOM elements
3. **Cache calculations**: Store coordinate calculations

### Critical Path Optimization

1. **Cache dependency graph**: Separate from calculation
2. **Use Kahn's algorithm**: O(V + E) complexity
3. **Early exit**: Skip when not visible

### Export Optimization

1. **Debounce export**: Prevent multiple simultaneous exports
2. **Show loading**: Give user feedback
3. **Optimize canvas**: Use appropriate scale factor

## Reporting Performance Issues

When reporting performance issues, include:

1. **Dataset size**: Number of tasks and dependencies
2. **Browser**: Chrome, Firefox, Safari, Edge version
3. **Metrics**: Actual times from performance monitor
4. **Steps to reproduce**: What actions cause the slowdown
5. **Screenshots**: Performance profile screenshots
6. **Console**: Any errors or warnings

## Continuous Monitoring

For production deployments:

1. **Set up performance monitoring** (e.g., Sentry, LogRocket)
2. **Track metrics over time**
3. **Set up alerts** for performance degradation
4. **A/B test optimizations** before rollout

## Conclusion

Regular performance testing ensures the Gantt view remains responsive as projects grow. Use the tools and guidelines in this document to maintain optimal performance.
