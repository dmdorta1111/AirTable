# Timeline View Pattern Analysis

## Overview
This document analyzes the horizontal timeline patterns from GanttView.tsx to guide TimelineView implementation.

## Key Pattern Areas

### 1. Date Range Calculation (Lines 149-164)

**Pattern:**
```typescript
const { startDate, endDate, days } = useMemo(() => {
  let start, end;
  if (viewMode === 'day') {
    start = subDays(currentDate, 10);
    end = addDays(currentDate, 20);
  } else if (viewMode === 'week') {
    start = startOfWeek(subDays(currentDate, 30));
    end = endOfWeek(addDays(currentDate, 60));
  } else { // month
    start = startOfMonth(subMonths(currentDate, 2));
    end = endOfMonth(addMonths(currentDate, 4));
  }

  const dayList = eachDayOfInterval({ start, end });
  return { startDate: start, endDate: end, days: dayList };
}, [currentDate, viewMode]);
```

**Key Points:**
- Uses `useMemo` for performance optimization (recalculates only when currentDate or viewMode changes)
- Date-fns utilities: `subDays`, `addDays`, `startOfWeek`, `endOfWeek`, `eachDayOfInterval`, `startOfMonth`, `endOfMonth`, `subMonths`, `addMonths`
- Returns tuple: `{ startDate, endDate, days }` where `days` is an array of all dates in range
- Different view modes have different date spans:
  - Day: ±10-20 days from currentDate
  - Week: ±30-60 days from currentDate, aligned to week boundaries
  - Month: ±2-4 months from currentDate, aligned to month boundaries

**For TimelineView:**
- Use similar pattern but adjust date ranges for timeline needs
- Consider startDate field from data rather than currentDate
- May need longer ranges for historical views

---

### 2. Position Calculation (Lines 227-270)

**Pattern 1: Date to Position Conversion**
```typescript
const getPositionForDate = (date: Date) => {
  const diff = differenceInDays(date, startDate);
  return diff * columnWidth;
};
```

**Key Points:**
- Simple linear calculation: `daysFromStart * columnWidth`
- Uses `differenceInDays` from date-fns
- `columnWidth` state variable controls zoom level (e.g., 50px per day)

**Pattern 2: Record Styling (Position + Width + Colors)**
```typescript
const getRecordStyle = (record: Record) => {
  const start = safeParseDate(record[startDateFieldId]);
  const end = safeParseDate(record[endDateFieldId]) || (start ? addDays(start, 1) : null);

  if (!start || !end) return { display: 'none' };

  // Clip to view range
  if (end < startDate || start > endDate) return { display: 'none' };

  const left = getPositionForDate(start);
  const width = Math.max(columnWidth, differenceInDays(end, start) * columnWidth);

  // Status colors
  let bgColor = 'bg-primary';
  if (statusFieldId) {
    const status = record[statusFieldId];
    if (status === 'Done' || status === 'Complete') bgColor = 'bg-green-500';
    else if (status === 'In Progress') bgColor = 'bg-blue-500';
    else if (status === 'Blocked') bgColor = 'bg-red-500';
    else if (status === 'To Do') bgColor = 'bg-slate-400';
  }

  return {
    left: `${left}px`,
    width: `${width}px`,
    backgroundColor: `var(--${bgColor}-color, ${bgColor})`,
    className: bgColor
  };
};
```

**Key Points:**
- `safeParseDate` wrapper handles invalid dates (returns null)
- Clips records outside visible range: `display: 'none'`
- Calculates left position using `getPositionForDate`
- Width calculation: `differenceInDays(end, start) * columnWidth`
- Minimum width of `columnWidth` to prevent tiny bars
- Conditional styling based on status field
- Returns object with inline styles (`left`, `width`) and CSS class (`className`)

**For TimelineView:**
- Similar positioning logic needed for timeline events
- May need vertical positioning instead of horizontal stacking
- Consider different color schemes for event types

---

### 3. Header Rendering (Lines 349-400)

**Pattern: Two-Level Time Header**

```typescript
const renderTimeHeader = () => {
  // Month row
  const months = [];
  let mDate = startDate;
  while (mDate <= endDate) {
    const nextMonth = startOfMonth(addMonths(mDate, 1));
    const limitDate = nextMonth > endDate ? endDate : nextMonth;
    const firstDayOfSegment = mDate < startDate ? startDate : mDate;
    const width = (differenceInDays(limitDate, firstDayOfSegment)) * columnWidth;

    if (width > 0) {
      months.push(
        <div
          key={`month-${mDate.toISOString()}`}
          className="h-8 border-b border-r flex items-center px-2 text-sm font-semibold sticky top-0 bg-background/95 backdrop-blur z-20 text-muted-foreground"
          style={{ width: `${width}px` }}
        >
          {format(mDate, 'MMMM yyyy')}
        </div>
      );
    }
    mDate = nextMonth;
  }

  // Days/Weeks row
  const dayCells = days.map((day) => {
    const isWeekend = day.getDay() === 0 || day.getDay() === 6;
    const isToday = isSameDay(day, new Date());

    return (
      <div
        key={day.toISOString()}
        className={cn(
          "h-8 border-r flex items-center justify-center text-xs flex-shrink-0 select-none",
          isWeekend ? "bg-muted/30" : "bg-background",
          isToday ? "bg-primary/5 font-bold text-primary" : "text-muted-foreground"
        )}
        style={{ width: `${columnWidth}px` }}
      >
        {viewMode === 'month' ? format(day, 'd') : format(day, 'EEE d')}
      </div>
    );
  });

  return (
    <div className="flex flex-col min-w-max">
      <div className="flex flex-row">{months}</div>
      <div className="flex flex-row border-b">{dayCells}</div>
    </div>
  );
};
```

**Key Points:**
- Two rows: months (top), days (bottom)
- Month row spans multiple day columns
- Days are individual cells with fixed `columnWidth`
- `sticky top-0` keeps header visible while scrolling
- `min-w-max` ensures header doesn't shrink
- Weekend highlighting: `bg-muted/30`
- Today highlighting: `bg-primary/5 font-bold text-primary`
- Date formatting with `format()` from date-fns
- `flex-shrink-0` on day cells prevents squishing

**For TimelineView:**
- Similar two-level header needed
- May need years/quarters instead of months
- Consider scale adaptation (years for long timelines)

---

### 4. Grid Background (Lines 402-422)

**Pattern:**
```typescript
const renderGridBackground = () => {
  return (
    <div className="absolute inset-0 flex pointer-events-none h-full min-w-max">
      {days.map((day) => {
        const isWeekend = day.getDay() === 0 || day.getDay() === 6;
        const isToday = isSameDay(day, new Date());
        return (
          <div
            key={`grid-${day.toISOString()}`}
            className={cn(
              "h-full border-r flex-shrink-0",
              isWeekend ? "bg-muted/10" : "bg-transparent",
              isToday ? "bg-primary/5" : ""
            )}
            style={{ width: `${columnWidth}px` }}
          />
        );
      })}
    </div>
  );
};
```

**Key Points:**
- Absolute positioning: `absolute inset-0` covers entire timeline area
- `pointer-events-none` allows clicks to pass through to records
- Vertical lines: `border-r` on each day column
- Weekend/today highlighting (subtle)
- `min-w-max` ensures grid spans full width

**For TimelineView:**
- Similar vertical grid lines needed
- May need horizontal grid lines for swimlanes
- Consider different visual patterns for time scales

---

### 5. Horizontal Scrolling Architecture (Lines 507-616)

**Pattern: Split-Pane Layout**

```typescript
{/* Content Area - Split Pane */}
<div className="flex flex-1 overflow-hidden" ref={containerRef} onMouseUp={handleMouseUp} onMouseMove={handleMouseMove} onMouseLeave={handleMouseUp}>

  {/* Left: Table */}
  <div className="w-[300px] border-r flex flex-col bg-card z-10 shadow-sm flex-shrink-0">
    {/* Fixed width left panel */}
  </div>

  {/* Right: Timeline */}
  <div className="flex-1 overflow-auto relative bg-background/50 scrollbar-hide">
    <div className="min-w-max">
      {/* Header */}
      {renderTimeHeader()}

      {/* Grid & Rows */}
      <div className="relative min-w-max">
        {renderGridBackground()}

        {/* Records */}
        <div className="relative pt-0 pb-10">
          {table.getRowModel().rows.map(row => {
            const record = row.original;
            const styleInfo = getRecordStyle(record);

            return (
              <div key={row.id} className="h-12 border-b relative group hover:bg-black/5 transition-colors">
                {/* Record bar */}
                <div
                  className="absolute top-2 h-8 rounded-md shadow-sm border..."
                  style={{
                    left: styleInfo.left,
                    width: styleInfo.width,
                  }}
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  </div>
</div>
```

**Key Points:**
- Outer flex container: `flex flex-1 overflow-hidden`
- Left panel: `w-[300px] flex-shrink-0` (fixed, no shrinking)
- Right panel: `flex-1 overflow-auto` (scrolls independently)
- Timeline content: `min-w-max` forces horizontal scroll
- Left panel has higher z-index (`z-10`) for layering
- Grid background: `absolute inset-0` (underneath records)
- Records: absolutely positioned based on calculated styles
- Scrollbar styling: `scrollbar-hide` utility class

**For TimelineView:**
- Similar split-pane needed (legend vs timeline)
- May need vertical scroll if many records
- Consider synchronized scrolling (if any)

---

### 6. Interactive State & Dragging (Lines 96-103, 274-345)

**Pattern: Drag-to-Move/Resize**

```typescript
// State
const [isDragging, setIsDragging] = useState(false);
const [dragRecordId, setDragRecordId] = useState<string | null>(null);
const [dragStartX, setDragStartX] = useState(0);
const [dragOriginalStart, setDragOriginalStart] = useState<Date | null>(null);
const [dragOriginalEnd, setDragOriginalEnd] = useState<Date | null>(null);
const [dragType, setDragType] = useState<'move' | 'resize-left' | 'resize-right' | null>(null);
const dragCurrentX = useRef(0);

// Handler
const handleDragStart = (e: React.MouseEvent, record: Record, type: 'move' | 'resize-left' | 'resize-right') => {
  e.stopPropagation();
  e.preventDefault();
  setIsDragging(true);
  setDragRecordId(record.id);
  setDragStartX(e.clientX);
  dragCurrentX.current = e.clientX;
  setDragType(type);
  setDragOriginalStart(safeParseDate(record[startDateFieldId]));
  setDragOriginalEnd(safeParseDate(record[endDateFieldId]));
};

// Mouse move tracking
const handleMouseMove = (e: React.MouseEvent) => {
  if (!isDragging || !dragRecordId || !dragOriginalStart || !dragOriginalEnd) return;
  dragCurrentX.current = e.clientX;
  // Visual feedback could be added here
};

// Mouse up - commit changes
const handleMouseUp = () => {
  if (isDragging && dragRecordId && dragOriginalStart && dragOriginalEnd && onCellUpdate) {
    const deltaX = dragCurrentX.current - dragStartX;
    const deltaDays = Math.round(deltaX / columnWidth);

    if (deltaDays !== 0) {
      let newStart, newEnd;
      if (dragType === 'move') {
        newStart = addDays(dragOriginalStart, deltaDays);
        newEnd = addDays(dragOriginalEnd, deltaDays);
      } else if (dragType === 'resize-left') {
        newStart = addDays(dragOriginalStart, deltaDays);
        newEnd = dragOriginalEnd;
      } else if (dragType === 'resize-right') {
        newStart = dragOriginalStart;
        newEnd = addDays(dragOriginalEnd, deltaDays);
      }

      // Update via callback
      onCellUpdate(dragRecordId, startDateFieldId, newStart.toISOString());
      onCellUpdate(dragRecordId, endDateFieldId, newEnd.toISOString());
    }
  }
  // Reset drag state
  setIsDragging(false);
  setDragRecordId(null);
  setDragType(null);
};
```

**Key Points:**
- Three drag types: `move`, `resize-left`, `resize-right`
- `useRef` for `dragCurrentX` (avoid re-renders)
- Convert pixel delta to day delta: `Math.round(deltaX / columnWidth)`
- Date updates via `onCellUpdate` callback
- Resize handles appear on hover: `opacity-0 group-hover:opacity-100`
- Event propagation stopped: `e.stopPropagation()`

**For TimelineView:**
- Dragging may not be needed for read-only timeline
- If interactive, similar pattern for moving events
- Consider pan/zoom instead of individual dragging

---

### 7. Utilities & Helpers

**Safe Date Parsing (Lines 72-76)**
```typescript
const safeParseDate = (date: any): Date | null => {
  if (!date) return null;
  const parsed = new Date(date);
  return isValid(parsed) ? parsed : null;
};
```

**Key Points:**
- Guards against null/undefined
- Validates with `isValid()` from date-fns
- Returns null for invalid dates

**Conditional Display with `void` (Lines 237, 433)**
```typescript
const _getDateForPosition = (x: number) => { /* ... */ };
void _getDateForPosition; // Prevents unused variable lint errors
```

---

### 8. State Management Patterns

**Field Auto-Detection (Lines 106-126)**
```typescript
useEffect(() => {
  if (fields.length > 0) {
    const dateFields = fields.filter(f => f.type === 'date');
    if (dateFields.length > 0) setStartDateFieldId(dateFields[0].name);
    if (dateFields.length > 1) setEndDateFieldId(dateFields[1].name);

    const textField = fields.find(f =>
      f.type === 'text' || f.type === 'long_text' ||
      f.name === 'Name' || f.name === 'Title'
    );
    if (textField) setTitleFieldId(textField.name);

    // ... more field detection
  }
}, [fields]);
```

**Key Points:**
- Run once when fields change
- Smart defaults based on field types and names
- Fallback to first field if no match found

---

### 9. Styling Patterns

**Conditional Classes with `cn()` utility**
```typescript
className={cn(
  "h-8 border-r flex items-center justify-center text-xs flex-shrink-0 select-none",
  isWeekend ? "bg-muted/30" : "bg-background",
  isToday ? "bg-primary/5 font-bold text-primary" : "text-muted-foreground"
)}
```

**Tooltip Integration (Lines 558-607)**
```typescript
<TooltipProvider>
  <Tooltip>
    <TooltipTrigger asChild>
      <div /* record bar */ />
    </TooltipTrigger>
    <TooltipContent>
      <div className="text-xs">
        <div className="font-bold">{title}</div>
        <div>{start} - {end}</div>
        <div>Progress: {progress}%</div>
      </div>
    </TooltipContent>
  </Tooltip>
</TooltipProvider>
```

---

### 10. Performance Optimizations

**Memoization**
- `useMemo` for filtered data (lines 130-146)
- `useMemo` for date range calculation (lines 149-164)
- `useMemo` for table columns (lines 169-217)

**Event Handlers**
- Single mouse move/up handler on container (not per record)
- `useRef` for frequently updated values to avoid re-renders

---

## Summary: Key Takeaways for TimelineView

1. **Position Calculation**: Use `differenceInDays * columnWidth` formula
2. **Header Structure**: Two-level header (periods + units) with sticky positioning
3. **Scroll Architecture**: Split-pane with fixed left panel, scrollable right timeline
4. **Grid System**: Absolute positioned background with `pointer-events-none`
5. **Date Handling**: Always use `safeParseDate` wrapper
6. **Styling**: Use `cn()` for conditional classes, Tailwind for styling
7. **Performance**: Memoize calculations, use `useRef` for drag tracking
8. **Interactivity**: If dragging needed, follow the three-type pattern (move/resize-left/resize-right)

---

## References

- Date-fns: https://date-fns.org/
- TanStack Table: https://tanstack.com/table/v8
- Lucide React: https://lucide.dev/
- Shadcn/ui: https://ui.shadcn.com/
