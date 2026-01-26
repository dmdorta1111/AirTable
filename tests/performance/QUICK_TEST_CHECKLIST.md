# Quick Performance Test Checklist

Quick reference for performing essential performance tests on all 7 views.

## Setup (5 minutes)

```bash
# Generate test data
python tests/performance/generate_test_data.py --count 10000

# Start backend
cd src && uvicorn pybase.main:app --reload --port 8000

# Start frontend (new terminal)
cd frontend && npm run dev

# Login: perf@test.com / testpass
```

## Quick Tests (30 minutes)

### ☐ Test 1: Initial Render (5 min)
- [ ] Open DevTools Performance tab
- [ ] Navigate to table URL
- [ ] Measure: Time to Interactive < 2s
- [ ] Check: No console errors

### ☐ Test 2: View Switching (10 min)
Test each view switch < 500ms:
- [ ] Grid → Kanban
- [ ] Kanban → Calendar
- [ ] Calendar → Form
- [ ] Form → Gallery
- [ ] Gallery → Gantt
- [ ] Gantt → Timeline
- [ ] Timeline → Grid

### ☐ Test 3: Scrolling (5 min)
Test smooth scrolling (60fps):
- [ ] Grid view
- [ ] Gallery view
- [ ] Timeline view
- [ ] Gantt view (horizontal)

### ☐ Test 4: Memory Check (5 min)
- [ ] Take baseline heap snapshot
- [ ] Switch through all views 3x
- [ ] Force GC
- [ ] Take final snapshot
- [ ] Check: Memory increase < 50MB

### ☐ Test 5: Interactions (5 min)
Quick interaction tests:
- [ ] Grid: Edit cell, sort column
- [ ] Kanban: Drag card between columns
- [ ] Gantt: Drag task bar
- [ ] Gallery: Change card size

## Quick Pass/Fail Criteria

| Test | Pass Criteria | Result |
|------|--------------|--------|
| Initial Render | < 2s | ☐ |
| View Switch | < 500ms each | ☐ |
| Scrolling | 60fps, smooth | ☐ |
| Memory | < 50MB increase | ☐ |
| Interactions | Responsive, no lag | ☐ |

## Red Flags 🚩

Stop and investigate if you see:
- ❌ Initial render > 3s
- ❌ View switch > 1s
- ❌ Visible lag/jank during scrolling
- ❌ Memory increase > 100MB
- ❌ Browser tab freezes or crashes
- ❌ Console errors or warnings
- ❌ Drag operations stuttering

## Quick Fix Common Issues

**Slow initial render:**
```bash
# Check database indexes
psql -d pybase -c "\d records"
```

**View switching lag:**
- Check React DevTools Profiler for expensive renders
- Verify component memoization

**Memory leaks:**
- Check useEffect cleanup functions
- Verify WebSocket disconnection

**Scrolling jank:**
- Confirm virtual scrolling enabled
- Check for layout thrashing in Performance tab

## Report Results

After testing, fill out key sections in `PERFORMANCE_TEST_REPORT.md`:
1. Acceptance Criteria Check (page 1)
2. Issues Discovered (if any)
3. Pass/Fail determination
4. Sign-off

## Time Estimates

- **Quick Test**: 30 minutes (this checklist)
- **Full Test**: 2-3 hours (complete guide)
- **Report**: 30 minutes (documentation)

**Total**: ~1 hour for quick validation, ~4 hours for comprehensive testing
