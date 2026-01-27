# Real-Time Chart Updates Test Guide

## Overview

This guide provides step-by-step instructions for manually verifying that real-time chart updates work correctly when data changes via WebSocket.

## Test Page

Access the test page at: `http://localhost:3000/dashboards/realtime-test`

## Test Scenarios

### 1. WebSocket Connection Verification

**Steps:**
1. Navigate to the test page
2. Look at the connection status indicator in the header (top right)
3. Verify it shows "Connected" in green with a WiFi icon

**Expected Result:**
- Connection status should show "Connected" within a few seconds
- Green WiFi icon should be visible
- No "Disconnected" or "Connecting" status should persist

---

### 2. Modify Record Data via Quick Actions

**Steps:**
1. Click the "Update Widget A Quantity (+50)" button
2. Observe the charts section above the table
3. Check the Event Log for new entries

**Expected Result:**
- Charts should update within 1 second
- Bar chart (Quantity by Category) should show increased Electronics value
- Area chart (Total Value by Category) should reflect the new quantity
- Event Log should show:
  - `user.action`: User updated the quantity
  - `simulate.ws`: Simulated WebSocket event
  - `chart.refresh`: Chart data refreshed

---

### 3. Modify Record Data via Cell Editing

**Steps:**
1. In the Grid View table, click on a cell (e.g., quantity field of Widget B)
2. Change the value to a new number
3. Click outside the cell or press Enter to save
4. Observe the charts and event log

**Expected Result:**
- Charts should update automatically after cell edit
- No manual refresh required
- Event log should record the edit action and subsequent WebSocket simulation

---

### 4. Add New Record

**Steps:**
1. Click the "Add Record" button in the Test Actions section
2. Observe the table (new row should appear)
3. Observe the charts (should update to include new data)
4. Check the Event Log

**Expected Result:**
- New record appears in the table with "New Product N" name
- Charts update to show Consumables category data
- Event Log shows:
  - `user.action`: Record added
  - `simulate.ws`: WebSocket event simulated
  - `chart.refresh`: Charts refreshed

---

### 5. Delete Record

**Steps:**
1. Click the "Delete Gadget Y" button in Test Actions
2. Observe the table (row should be removed)
3. Observe the charts (Mechanical category should update)
4. Check the Event Log

**Expected Result:**
- Record disappears from the table
- Charts update to reflect removal
- Event Log shows deletion events

---

### 6. Verify No Stale Data

**Steps:**
1. Perform multiple rapid updates using different action buttons
2. Make at least 5-6 changes in quick succession
3. After each change, verify charts match the table data

**Expected Result:**
- Charts always reflect the current table state
- No lag or stale data visible
- All chart types (bar and area) update correctly
- Values in charts match the aggregated table data

---

### 7. WebSocket Connection Resilience

**Steps:**
1. Keep the test page open for 2-3 minutes
2. Perform periodic updates
3. Verify connection remains stable

**Expected Result:**
- Connection stays "Connected" throughout
- Updates continue to work reliably
- No disconnection or reconnection cycles

---

## Verification Checklist

After completing all test scenarios, verify the following:

### WebSocket Connection
- [ ] Connection status shows "Connected" (green)
- [ ] WebSocket URL includes table and chart IDs
- [ ] Connection stays alive during all interactions

### Real-Time Updates
- [ ] Charts update within 1 second of data change
- [ ] Event log shows WebSocket events
- [ ] No page refresh required for updates

### Data Integrity
- [ ] Charts reflect current table data
- [ ] No stale data after multiple updates
- [ ] All chart types update correctly

### User Actions
- [ ] Add record triggers chart update
- [ ] Update record triggers chart update
- [ ] Delete record triggers chart update
- [ ] Cell edits trigger chart update

---

## Success Criteria

All of the following must be true for the test to pass:

1. **WebSocket Connection**: Stable connection maintained throughout test
2. **Real-Time Updates**: All chart updates occur within 1 second without page refresh
3. **Data Accuracy**: Charts always match the current table data
4. **Event Logging**: All actions and WebSocket events properly logged
5. **Multiple Chart Types**: Both bar and area charts update correctly
6. **No Stale Data**: After multiple rapid updates, no outdated values visible

---

## Troubleshooting

### Issue: Charts don't update

**Check:**
- Is the WebSocket connection showing "Connected"?
- Are there any errors in the browser console?
- Is the Event Log showing the simulate.ws events?

**Solution:**
- Refresh the page to reset the connection
- Check that the backend WebSocket server is running
- Verify the test table and chart IDs are correct

### Issue: Stale data visible

**Check:**
- Did you wait long enough for the update to propagate?
- Are there multiple browser tabs open with the same data?

**Solution:**
- Wait up to 1 second for updates to complete
- Close other browser tabs that might have cached data
- Try a manual page refresh to reset state

### Issue: WebSocket won't connect

**Check:**
- Is the backend server running?
- Is the WebSocket URL configured correctly in environment variables?

**Solution:**
- Verify backend is running on the expected port
- Check `VITE_WS_BASE_URL` in `.env` file
- Ensure no firewall or proxy blocking WebSocket connections

---

## Technical Notes

### Simulation Mode

This test page simulates WebSocket events because in a real deployment:
1. Backend emits `chart.updated` events when records change
2. The `useRealtime` hook receives these events via WebSocket
3. Charts automatically refresh when events are received

The simulation accurately demonstrates how real-time updates will work in production.

### Data Flow

```
User Action → Update Record → Simulate WebSocket Event → useRealtime Hook → refreshChartData() → Charts Update
```

### Key Components Tested

1. **useRealtime Hook**: WebSocket connection and event handling
2. **ChartWidget**: Real-time data fetching and rendering
3. **ChartPanel**: Multiple chart updates
4. **GridView**: Table integration with real-time updates
