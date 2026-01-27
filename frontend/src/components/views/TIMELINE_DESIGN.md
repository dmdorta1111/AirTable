# Timeline View - Horizontal Layout Design

## Overview
The Timeline View has been redesigned with a horizontal timeline layout inspired by the GanttView pattern, displaying records as points on a horizontal time axis.

## Layout Structure

### 1. Time Header (Top)
- **Zoom-based scale**: Supports 5 zoom levels
  - `day`: Shows individual days with month/quarter labels
  - `week`: Shows days with abbreviated weekday names
  - `month`: Shows months with quarter labels
  - `quarter`: Shows quarters with year labels
  - `year`: Shows years only
- **Two-row header**:
  - Top row: Larger time units (months/quarters/years)
  - Bottom row: Current zoom level units
- **Visual indicators**:
  - Today highlighted with primary color
  - Weekends shaded (in day/week mode)

### 2. Horizontal Scrollable Container
- **Split pane layout**:
  - Left panel (300px): Groups list
  - Right panel (flex-1): Timeline with horizontal scroll
- **Grid background**: Vertical lines marking time units
- **Sticky positioning**: Time header stays visible on scroll

### 3. Rows Grouped by Field
- **Configurable grouping**: Users can select any select/multi-select field for grouping
- **Default grouping**: Auto-detects status field for grouping
- **Collapsible groups**: Each group can be expanded/collapsed
- **Group header shows**:
  - Group value/name
  - Record count badge
  - Expand/collapse chevron

### 4. Records as Points
- **Positioned by date**: Each record displayed as a circular point on the timeline
- **Color coding**: Based on status field
  - Done/Completed: Green
  - In Progress: Blue
  - Blocked: Red
  - To Do: Slate
  - Default: Primary color
- **Hover effects**: Points scale up (150%) and show shadow on hover
- **Tooltips**: Show record details on hover (title, date, status)
- **Click interaction**: Click to open detail modal

### 5. Click-to-Expand Details
- **Modal overlay**: Backdrop blur with centered card
- **Shows all fields**: Displays all record fields and values
- **Formatted display**:
  - Dates formatted with date-fns (PPP p format)
  - Objects displayed as JSON
  - Other values as strings
- **Actions**: Close and Edit buttons (Edit placeholder)

## Preserved Features

### Search
- **Real-time filtering**: Filters records by title field
- **Dedicated search box**: In toolbar with search icon

### Zoom
- **5 zoom levels**: Day, Week, Month, Quarter, Year
- **Zoom buttons**: Toggle buttons in toolbar
- **Dynamic column width**: Adjusts based on zoom level (40-100px)

### Grouping
- **Group by selector**: Dropdown to select grouping field
- **Multiple grouping options**: Any select/multi-select field
- **Expand/collapse all**: Groups start expanded

### Color Coding
- **Status-based colors**: Automatic color mapping from status field values
- **Consistent with GanttView**: Uses same color scheme as Gantt view

### Navigation
- **Date navigation**: Previous/Next buttons with Today button
- **Context-aware**: Navigation step size adapts to zoom level
- **Current date indicator**: Shows currently focused date range

## Technical Implementation

### State Management
- `zoomLevel`: Current zoom level
- `currentDate`: Center date for viewport
- `columnWidth`: Width per time unit (pixels)
- `searchQuery`: Current search filter
- `selectedRecord`: Record displayed in modal (if any)
- `expandedGroups`: Set of expanded group keys
- Field mapping state (dateFieldId, titleFieldId, etc.)

### Helper Functions
- `safeParseDate`: Safe date parsing with validation
- `getPositionForDate`: Calculate horizontal position for a date
- `getPointColor`: Determine color based on status
- `renderTimeHeader`: Generate header based on zoom level
- `renderGridBackground`: Generate vertical grid lines

### Data Processing
- `filteredData`: Search-filtered and validated records
- `groupedRows`: Records grouped by selected field
- `timeUnits`: Array of time units in current view range
- `startDate`/`endDate`: View boundaries

## CSS Classes Used
- `flex`, `flex-col`: Layout structure
- `sticky`: Header positioning
- `overflow-auto`: Scrollable containers
- `transition-all`: Smooth animations
- `hover:*`: Interactive states
- `bg-background/50`: Semi-transparent backgrounds
- `shadow-sm`, `shadow-md`: Depth effects

## File Size
The component is approximately 550 lines, following the pattern from GanttView.tsx.

## Next Steps
Future enhancements could include:
- Drag-to-move records on timeline
- Record dependencies with connecting lines
- Custom color schemes
- Export timeline as image
- Print-friendly layout
