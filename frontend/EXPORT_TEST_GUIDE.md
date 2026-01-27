# Chart Export Functionality - Test Guide

## Purpose
This guide provides instructions for manually testing the export functionality for all 8 chart types (line, bar, area, pie, donut, scatter, histogram, gauge) to PNG and SVG formats.

## Test Page Location
Navigate to: `http://localhost:3000/dashboards/export-test`

## Test Procedure

### 1. Start the Application
```bash
cd frontend
npm run dev
```

### 2. Open the Export Test Page
Open your browser and navigate to: `http://localhost:3000/dashboards/export-test`

### 3. Test Each Chart Type

For each of the 8 charts displayed:

#### Line Chart
1. Click the download button (first icon) to export as PNG
2. Verify:
   - File downloads with name: `Monthly_Revenue_Trend_chart.png`
   - File opens in image viewer
   - Visual quality is crisp and clear
   - Colors, labels, and data match the displayed chart
3. Click the "SVG" button to export as SVG
4. Verify:
   - File downloads with name: `Monthly_Revenue_Trend_chart.svg`
   - File opens in browser or vector editor (e.g., Inkscape, Illustrator)
   - SVG is scalable without quality loss
   - All elements (axes, grid, line, labels) are present

#### Bar Chart
1. Export as PNG and SVG
2. Verify file names: `Monthly_Revenue_chart.png/svg`
3. Verify all bars are rendered with correct colors

#### Area Chart
1. Export as PNG and SVG
2. Verify file names: `Revenue_Area_Chart_chart.png/svg`
3. Verify area fill opacity is correct

#### Pie Chart
1. Export as PNG and SVG
2. Verify file names: `Category_Distribution_chart.png/svg`
3. Verify all slices with correct colors

#### Donut Chart
1. Export as PNG and SVG
2. Verify file names: `Category_Distribution_Donut_chart.png/svg`
3. Verify donut hole is present

#### Scatter Chart
1. Export as PNG and SVG
2. Verify file names: `Correlation_Analysis_chart.png/svg`
3. Verify all data points are visible

#### Histogram
1. Export as PNG and SVG
2. Verify file names: `Revenue_Distribution_chart.png/svg`
3. Verify bins and labels are correct

#### Gauge
1. Export as PNG and SVG
2. Verify file names: `Performance_Gauge_chart.png/svg`
3. Verify gauge needle/value and color thresholds

### 4. Mark Verification Checkboxes
For each chart, check the boxes:
- ☑ PNG exports and opens
- ☑ SVG exports and opens

### 5. Verify Completion
At the top of the page, you'll see progress:
- X / 8 PNG exports
- X / 8 SVG exports

When all checkboxes are marked, you'll see:
- Green border around all chart cards
- "All exports complete!" message
- Success summary at bottom

## Success Criteria

### Must Pass
✅ All 8 chart types export to PNG
✅ All 8 chart types export to SVG
✅ Downloaded files have valid formats
✅ File names are descriptive and valid

### Should Pass
✅ PNG images are crisp (2x scale for high resolution)
✅ SVG files are valid and scalable
✅ Visual output matches chart display
✅ No console errors during export

### May Pass
⚠️ File sizes are reasonable (PNG < 1MB, SVG < 100KB)
⚠️ Export completes within 2 seconds per chart

## Known Limitations

### Gauge Chart SVG Export
The gauge chart uses HTML/CSS for value display, which may not be captured in SVG export. The gauge arc itself should export correctly.

### Browser Compatibility
Export functionality tested on:
- Chrome/Edge (Chromium): Full support
- Firefox: Full support
- Safari: Full support

## Troubleshooting

### Export Button Not Working
1. Check browser console for errors
2. Verify html2canvas is installed: `npm list html2canvas`
3. Ensure no popup blockers are preventing download

### PNG File is Blank
1. Check if chart has finished rendering
2. Try refreshing the page
3. Check browser console for canvas-related errors

### SVG File is Corrupted
1. Ensure SVG element is present in DOM (use browser inspector)
2. Verify chart has data
3. Try different browser

## Automated Testing

For automated testing, see:
- `frontend/src/components/analytics/__tests__/ChartWidget.test.tsx`
- Run tests: `npm test -- ChartWidget`

## Related Files

- Test page: `frontend/src/pages/ChartExportTestPage.tsx`
- Export utilities: `frontend/src/components/analytics/ChartWidget.tsx`
- Router config: `frontend/src/lib/router.tsx`

## Notes

- PNG export uses `html2canvas` library with 2x scale for high resolution
- SVG export uses native `XMLSerializer` API
- Export handlers support both default and custom implementations
- File names are auto-generated from chart title with special characters replaced
