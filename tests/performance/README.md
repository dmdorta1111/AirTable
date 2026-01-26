# Performance Tests

Comprehensive performance testing suite for PyBase views with large datasets.

## Overview

This directory contains tools and documentation for performance testing all 7 view types (Grid, Kanban, Calendar, Form, Gallery, Gantt, Timeline) with 10K+ records.

## Files

### Scripts
- **`generate_test_data.py`** - Generate 10K+ test records for performance testing
- **`test_extraction_speed.py`** - Automated performance tests for PDF extraction

### Documentation
- **`PERFORMANCE_TESTING_GUIDE.md`** - Complete guide for manual performance testing
- **`PERFORMANCE_TEST_REPORT.md`** - Template for documenting test results
- **`QUICK_TEST_CHECKLIST.md`** - Quick reference checklist (30-minute test)
- **`README.md`** - This file

## Quick Start

### 1. Generate Test Data

```bash
# Generate 10,000 test records
python tests/performance/generate_test_data.py --count 10000

# Or with clean database
python tests/performance/generate_test_data.py --count 10000 --clean
```

### 2. Start Services

```bash
# Terminal 1 - Backend
cd src
uvicorn pybase.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### 3. Run Performance Tests

#### Option A: Quick Test (30 minutes)
Follow `QUICK_TEST_CHECKLIST.md` for essential tests

#### Option B: Comprehensive Test (3-4 hours)
Follow `PERFORMANCE_TESTING_GUIDE.md` for full testing

### 4. Run Automated Tests

```bash
# Backend extraction performance tests
pytest tests/performance/test_extraction_speed.py -v -m performance

# All performance tests
pytest tests/performance/ -v -m performance
```

## Performance Targets

All views must meet these criteria with 10K+ records:

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Initial Render | < 2s | < 3s |
| View Switching | < 500ms | < 1s |
| Scrolling FPS | 60fps (< 5% drops) | 45fps |
| Memory Usage | < 50MB increase | < 100MB |
| Memory Leaks | 0 detached nodes | < 50 nodes |
| Interaction Response | < 100ms | < 200ms |
| Drag Operations | 60fps | 45fps |

## Test Data Schema

The generated test data includes realistic engineering data:

### Fields (13 total)
- Part Number (text)
- Description (long_text)
- Status (single_select: Not Started, In Progress, Review, Completed, On Hold)
- Priority (single_select: Low, Medium, High, Critical)
- Department (single_select: Engineering, Manufacturing, Quality, Procurement, Sales)
- Engineer (single_select: 8 engineers)
- Material (single_select: Steel, Aluminum, Brass, Copper, Titanium, Plastic, Composite)
- Quantity (number)
- Dimension (text with tolerances)
- Start Date (date)
- End Date (date)
- Progress (number 0-100)
- Created Date (date)

### Records
- Realistic part numbers (e.g., BRK-234-5678)
- Random but consistent data distribution
- Date ranges spanning 1 year
- Progress values 0-100%

## Troubleshooting

### Data Generation Issues

**Error: Database connection failed**
```bash
# Check PostgreSQL is running
pg_isready

# Check connection string
echo $DATABASE_URL
```

**Error: Permission denied**
```bash
# Grant permissions
psql -d postgres -c "GRANT ALL ON DATABASE pybase TO your_user;"
```

### Performance Issues

**Slow initial render**
- Check database indexes exist on `records` table
- Verify network latency < 100ms
- Check browser DevTools Console for errors

**View switching lag**
- Profile with React DevTools Profiler
- Check for unnecessary re-renders
- Verify component memoization

**Memory leaks**
- Check useEffect cleanup functions
- Verify WebSocket disconnection
- Use Chrome DevTools Memory profiler

**Scrolling jank**
- Confirm virtual scrolling enabled
- Check DOM node count (should be low)
- Profile paint operations in DevTools

## Test Environments

### Development
- Local PostgreSQL database
- Vite dev server (HMR enabled)
- Chrome DevTools

### Staging
- Production-like database
- Built frontend (no HMR)
- Multiple browsers

### Production
- Real production environment
- Real user monitoring (RUM)
- Continuous performance monitoring

## CI/CD Integration

Automated performance tests run on:
- Pull requests (extraction performance)
- Nightly builds (full test suite)
- Release candidates (comprehensive manual testing)

```yaml
# GitHub Actions example
- name: Run Performance Tests
  run: |
    pytest tests/performance/ -v -m performance
```

## Metrics Collection

### Tools
- **Chrome DevTools**: Performance profiling, memory analysis
- **React DevTools Profiler**: Component render analysis
- **Lighthouse**: Automated audits
- **WebPageTest**: Real-world performance testing

### Metrics Tracked
- Core Web Vitals (LCP, FID, CLS)
- Time to Interactive (TTI)
- Total Blocking Time (TBT)
- First Contentful Paint (FCP)
- Memory usage
- Frame rate (FPS)
- Network performance

## Reporting

After testing, create a report using `PERFORMANCE_TEST_REPORT.md`:

1. Fill in test environment details
2. Record all metrics
3. Document issues found
4. Provide recommendations
5. Sign off on results

Store reports in: `tests/performance/reports/YYYY-MM-DD-performance-test.md`

## Best Practices

### Before Testing
- ✓ Close unnecessary browser tabs
- ✓ Disable browser extensions
- ✓ Clear browser cache
- ✓ Use consistent hardware
- ✓ Ensure stable network

### During Testing
- ✓ Follow test procedures exactly
- ✓ Record all metrics
- ✓ Take screenshots of issues
- ✓ Note any anomalies
- ✓ Reproduce issues before reporting

### After Testing
- ✓ Document all results
- ✓ Compare with previous results
- ✓ Identify trends
- ✓ Create action items for issues
- ✓ Archive test data and reports

## Resources

### External Documentation
- [Chrome DevTools Performance](https://developer.chrome.com/docs/devtools/performance/)
- [React Profiler](https://react.dev/reference/react/Profiler)
- [Web Vitals](https://web.dev/vitals/)
- [Lighthouse](https://developer.chrome.com/docs/lighthouse/)

### Internal Documentation
- Project README: `../../README.md`
- Frontend docs: `../../frontend/README.md`
- Backend docs: `../../src/pybase/README.md`

## Contributing

When adding new performance tests:

1. Follow existing patterns in `test_extraction_speed.py`
2. Use pytest markers: `@pytest.mark.performance`
3. Document expected performance in docstrings
4. Add new tests to CI/CD pipeline
5. Update this README

## Support

For questions or issues:
- Check troubleshooting section above
- Review `PERFORMANCE_TESTING_GUIDE.md`
- Search existing test issues
- Create new issue with `performance` label

## License

Same as main project (see root LICENSE file)
