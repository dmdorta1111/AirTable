import React, { useState, useMemo, useRef, useEffect } from 'react';
import {
  format,
  addDays,
  subDays,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  differenceInDays,
  startOfMonth,
  endOfMonth,
  isSameDay,
  addMonths,
  subMonths,
  addYears,
  subYears,
  startOfQuarter,
  endOfQuarter,
  startOfYear,
  endOfYear,
  getQuarter,
  isValid,
} from 'date-fns';
import {
  ChevronLeft,
  ChevronRight,
  Filter,
  Calendar as CalendarIcon,
  MoreHorizontal,
  Search,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from '@/lib/utils';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from '@tanstack/react-table';

// Types based on the context
interface Field {
  id: string;
  name: string;
  type: string;
  options?: any;
}

interface Record {
  id: string;
  [key: string]: any;
}

interface GanttViewProps {
  data: Record[];
  fields: Field[];
  onCellUpdate?: (rowId: string, fieldId: string, value: unknown) => void;
}

type ViewMode = 'day' | 'week' | 'month' | 'quarter' | 'year';

// Helper to safely parse dates
const safeParseDate = (date: any): Date | null => {
  if (!date) return null;
  const parsed = new Date(date);
  return isValid(parsed) ? parsed : null;
};

export const GanttView: React.FC<GanttViewProps> = ({ data, fields, onCellUpdate }) => {
  // --- State ---
  const [viewMode, setViewMode] = useState<ViewMode>('day');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [columnWidth, setColumnWidth] = useState(50); // px per unit
  const [searchQuery, setSearchQuery] = useState('');
  
  // Field mapping state
  const [startDateFieldId, setStartDateFieldId] = useState<string>('');
  const [endDateFieldId, setEndDateFieldId] = useState<string>('');
  const [titleFieldId, setTitleFieldId] = useState<string>('');
  const [statusFieldId, setStatusFieldId] = useState<string>('');
  const [progressFieldId, setProgressFieldId] = useState<string>('');
  const [dependencyFieldId, setDependencyFieldId] = useState<string>('');

  // Filtering state
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Interactive state
  const [isDragging, setIsDragging] = useState(false);
  const [dragRecordId, setDragRecordId] = useState<string | null>(null);
  const [dragStartX, setDragStartX] = useState(0);
  const [dragOriginalStart, setDragOriginalStart] = useState<Date | null>(null);
  const [dragOriginalEnd, setDragOriginalEnd] = useState<Date | null>(null);
  const [dragType, setDragType] = useState<'move' | 'resize-left' | 'resize-right' | null>(null);
  const dragCurrentX = useRef(0);

  // Dependency visualization state
  const [showDependencies, setShowDependencies] = useState(true);
  const taskBarRefs = useRef<{ [key: string]: HTMLDivElement }>({});

  // --- Initialization ---
  useEffect(() => {
    // Auto-detect fields
    if (fields.length > 0) {
      const dateFields = fields.filter(f => f.type === 'date');
      if (dateFields.length > 0) setStartDateFieldId(dateFields[0].name);
      if (dateFields.length > 1) setEndDateFieldId(dateFields[1].name);
      
      const textField = fields.find(f => f.type === 'text' || f.type === 'long_text' || f.name === 'Name' || f.name === 'Title');
      if (textField) setTitleFieldId(textField.name);
      else if (fields[0]) setTitleFieldId(fields[0].name);

      const statusField = fields.find(f => f.type === 'select' || f.type === 'singleSelect' || f.name.toLowerCase().includes('status'));
      if (statusField) setStatusFieldId(statusField.name);

      const progressField = fields.find(f => f.type === 'number' || f.type === 'percent' || f.name.toLowerCase().includes('progress'));
      if (progressField) setProgressFieldId(progressField.name);
      
      const depField = fields.find(f => f.type === 'link' || f.name.toLowerCase().includes('depend'));
      if (depField) setDependencyFieldId(depField.name);
    }
  }, [fields]);

  // --- Derived Data ---
  
  const filteredData = useMemo(() => {
    return data.filter(record => {
      // Search filter
      if (searchQuery) {
        const title = record[titleFieldId]?.toString().toLowerCase() || '';
        if (!title.includes(searchQuery.toLowerCase())) return false;
      }
      
      // Status filter
      if (statusFilter !== 'all' && statusFieldId) {
        const status = record[statusFieldId];
        if (status !== statusFilter) return false;
      }
      
      return true;
    });
  }, [data, searchQuery, statusFilter, titleFieldId, statusFieldId]);

  // Calculate visible date range
  const { startDate, endDate, days } = useMemo(() => {
    let start, end;
    if (viewMode === 'day') {
      start = subDays(currentDate, 10);
      end = addDays(currentDate, 20);
    } else if (viewMode === 'week') {
      start = startOfWeek(subDays(currentDate, 30));
      end = endOfWeek(addDays(currentDate, 60));
    } else if (viewMode === 'month') {
      start = startOfMonth(subMonths(currentDate, 2));
      end = endOfMonth(addMonths(currentDate, 4));
    } else if (viewMode === 'quarter') {
      start = startOfQuarter(subMonths(currentDate, 6));
      end = endOfQuarter(addMonths(currentDate, 12));
    } else { // year
      start = startOfYear(subYears(currentDate, 1));
      end = endOfYear(addYears(currentDate, 2));
    }

    const dayList = eachDayOfInterval({ start, end });
    return { startDate: start, endDate: end, days: dayList };
  }, [currentDate, viewMode]);

  // --- TanStack Table Setup (Left Panel) ---
  const columnHelper = createColumnHelper<Record>();
  
  const columns = useMemo(() => {
    const cols = [];
    
    // Title Column
    if (titleFieldId) {
      cols.push(columnHelper.accessor(row => row[titleFieldId], {
        id: 'title',
        header: 'Name',
        cell: info => <span className="font-medium truncate block max-w-[150px]" title={info.getValue()}>{info.getValue() || 'Untitled'}</span>
      }));
    } else {
        // Fallback if no title field detected yet
         cols.push(columnHelper.accessor('id', {
            id: 'id',
            header: 'Record',
            cell: () => <span className="text-muted-foreground italic">No Title Field</span>
        }));
    }

    // Status Column
    if (statusFieldId) {
      cols.push(columnHelper.accessor(row => row[statusFieldId], {
        id: 'status',
        header: 'Status',
        cell: info => {
          const val = info.getValue();
          return val ? (
            <Badge variant="secondary" className="text-xs px-1 py-0 h-5 font-normal">
              {val}
            </Badge>
          ) : null;
        }
      }));
    }

    // Start Date
    if (startDateFieldId) {
       cols.push(columnHelper.accessor(row => row[startDateFieldId], {
        id: 'start',
        header: 'Start',
        cell: info => {
            const d = safeParseDate(info.getValue());
            return d ? <span className="text-xs text-muted-foreground">{format(d, 'MMM d')}</span> : '-';
        }
      })); 
    }

    return cols;
  }, [titleFieldId, statusFieldId, startDateFieldId]);

  const table = useReactTable({
    data: filteredData,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  // --- Timeline Helpers ---

  const getPositionForDate = (date: Date) => {
    const diff = differenceInDays(date, startDate);
    return diff * columnWidth;
  };

  // Helper for position to date conversion (reserved for future visual feedback)
  const _getDateForPosition = (x: number) => {
    const daysToAdd = Math.round(x / columnWidth);
    return addDays(startDate, daysToAdd);
  };
  void _getDateForPosition;

  // Helper function to calculate dependency line coordinates
  // Returns the start and end points for drawing a dependency line between two tasks
  const calculateDependencyLineCoordinates = (
    predecessorRecord: Record,
    successorRecord: Record,
    rowPositions: Map<string, number>
  ) => {
    const predStart = safeParseDate(predecessorRecord[startDateFieldId]);
    const predEnd = safeParseDate(predecessorRecord[endDateFieldId]) || (predStart ? addDays(predStart, 1) : null);
    const succStart = safeParseDate(successorRecord[startDateFieldId]);
    const succEnd = safeParseDate(successorRecord[endDateFieldId]) || (succStart ? addDays(succStart, 1) : null);

    if (!predStart || !predEnd || !succStart || !succEnd) {
      return null;
    }

    // Get row Y positions
    const predRowY = rowPositions.get(predecessorRecord.id);
    const succRowY = rowPositions.get(successorRecord.id);

    if (predRowY === undefined || succRowY === undefined) {
      return null;
    }

    // Calculate X positions on timeline
    const predEndX = getPositionForDate(predEnd);
    const succStartX = getPositionForDate(succStart);

    // Calculate Y positions (center of task bars, assuming 48px height with 12px row height)
    const rowHeight = 48; // h-12 class = 48px
    const barHeight = 32; // h-8 class = 32px, positioned top-2 = 8px offset
    const barCenterYOffset = 8 + (barHeight / 2); // top-2 + half bar height = 8 + 16 = 24px

    const predCenterY = predRowY + barCenterYOffset;
    const succCenterY = succRowY + barCenterYOffset;

    // Calculate coordinates
    // Start from right edge of predecessor (minus small offset)
    const startX = predEndX - 5;
    const startY = predCenterY;

    // End at left edge of successor (plus small offset)
    const endX = succStartX + 5;
    const endY = succCenterY;

    // Calculate orthogonal routing points
    const midX1 = startX + 10; // 10px right from start
    const midY1 = startY; // Same Y as start
    const midX2 = midX1; // Same X as mid1
    const midY2 = succCenterY; // Y level of successor
    const midX3 = endX; // X position of end point
    const midY3 = succCenterY; // Same Y as successor

    const result = {
      start: { x: startX, y: startY },
      end: { x: endX, y: endY },
      midPoints: [
        { x: midX1, y: midY1 },
        { x: midX2, y: midY2 },
        { x: midX3, y: midY3 },
      ],
      predecessorId: predecessorRecord.id,
      successorId: successorRecord.id,
    };

    return result;
  };

  const getRecordStyle = (record: Record) => {
    const start = safeParseDate(record[startDateFieldId]);
    const end = safeParseDate(record[endDateFieldId]) || (start ? addDays(start, 1) : null);
    
    if (!start || !end) return { display: 'none' };

    // Clip to view range
    // If completely outside, hide
    if (end < startDate || start > endDate) return { display: 'none' };

    const left = getPositionForDate(start);
    const width = Math.max(columnWidth, differenceInDays(end, start) * columnWidth);
    
    // Status colors
    let bgColor = 'bg-primary';
    
    if (statusFieldId) {
        const status = record[statusFieldId];
        // Simple hashing for color variation if we don't have metadata
        if (status === 'Done' || status === 'Complete') bgColor = 'bg-green-500';
        else if (status === 'In Progress') bgColor = 'bg-blue-500';
        else if (status === 'Blocked') bgColor = 'bg-red-500';
        else if (status === 'To Do') bgColor = 'bg-slate-400';
    }

    return {
      left: `${left}px`,
      width: `${width}px`,
      backgroundColor: `var(--${bgColor}-color, ${bgColor})`, // Fallback for tailwind classes if not var
      className: bgColor // We will apply class directly
    };
  };

  // --- Handlers ---

  const handleDragStart = (e: React.MouseEvent, record: Record, type: 'move' | 'resize-left' | 'resize-right') => {
    e.stopPropagation();
    e.preventDefault();
    setIsDragging(true);
    setDragRecordId(record.id);
    setDragStartX(e.clientX);
    dragCurrentX.current = e.clientX;
    setDragType(type);
    setDragOriginalStart(safeParseDate(record[startDateFieldId]));
    setDragOriginalEnd(safeParseDate(record[endDateFieldId]) || addDays(safeParseDate(record[startDateFieldId])!, 1));
  };

  // Global mouse up/move listener would be attached to window/document in a real app or a large overlay
  // For this component, we'll attach to the main container
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !dragRecordId || !dragOriginalStart || !dragOriginalEnd) return;

    // Track current mouse position for use in handleMouseUp
    dragCurrentX.current = e.clientX;

    // Visual feedback could be added here with local state
    // For now, we'll update on mouse up to avoid too many backend calls
  };

  const handleMouseUp = () => {
    if (isDragging && dragRecordId && dragOriginalStart && dragOriginalEnd && onCellUpdate) {
      const deltaX = dragCurrentX.current - dragStartX;
      const deltaDays = Math.round(deltaX / columnWidth);

      if (deltaDays !== 0) {
        let newStart: Date | null = null;
        let newEnd: Date | null = null;

        if (dragType === 'move') {
          // Move both dates by the same amount
          newStart = addDays(dragOriginalStart, deltaDays);
          newEnd = addDays(dragOriginalEnd, deltaDays);
        } else if (dragType === 'resize-left') {
          // Resize from the left (change start date only)
          newStart = addDays(dragOriginalStart, deltaDays);
          newEnd = dragOriginalEnd;
          // Ensure start is before end
          if (newStart >= newEnd) {
            newStart = addDays(newEnd, -1);
          }
        } else if (dragType === 'resize-right') {
          // Resize from the right (change end date only)
          newStart = dragOriginalStart;
          newEnd = addDays(dragOriginalEnd, deltaDays);
          // Ensure end is after start
          if (newEnd <= newStart) {
            newEnd = addDays(newStart, 1);
          }
        }

        // Update the record with new dates
        if (newStart && startDateFieldId) {
          onCellUpdate(dragRecordId, startDateFieldId, newStart.toISOString());
        }
        if (newEnd && endDateFieldId) {
          onCellUpdate(dragRecordId, endDateFieldId, newEnd.toISOString());
        }
      }
    }

    setIsDragging(false);
    setDragRecordId(null);
    setDragType(null);
    dragCurrentX.current = 0;
  };
  
  // --- Render Helpers ---
  
  const renderTimeHeader = () => {
    // Top row (years/quarters/months depending on view mode)
    const topRowCells: React.ReactNode[] = [];

    if (viewMode === 'year') {
      // Year view: Top row shows years
      let yDate = startDate;
      while (yDate <= endDate) {
        const nextYear = startOfYear(addYears(yDate, 1));
        const limitDate = nextYear > endDate ? endDate : nextYear;
        const firstDayOfSegment = yDate < startDate ? startDate : yDate;
        const width = differenceInDays(limitDate, firstDayOfSegment) * columnWidth;

        if (width > 0) {
          topRowCells.push(
            <div
              key={`year-${yDate.toISOString()}`}
              className="h-8 border-b border-r flex items-center px-2 text-sm font-semibold sticky top-0 bg-background/95 backdrop-blur z-20 text-muted-foreground"
              style={{ width: `${width}px` }}
            >
              {format(yDate, 'yyyy')}
            </div>
          );
        }
        yDate = nextYear;
      }
    } else if (viewMode === 'quarter') {
      // Quarter view: Top row shows quarters
      let qDate = startDate;
      while (qDate <= endDate) {
        const nextQuarter = startOfQuarter(addMonths(qDate, 3));
        const limitDate = nextQuarter > endDate ? endDate : nextQuarter;
        const firstDayOfSegment = qDate < startDate ? startDate : qDate;
        const width = differenceInDays(limitDate, firstDayOfSegment) * columnWidth;

        if (width > 0) {
          const quarterNum = getQuarter(qDate);
          topRowCells.push(
            <div
              key={`quarter-${qDate.toISOString()}`}
              className="h-8 border-b border-r flex items-center px-2 text-sm font-semibold sticky top-0 bg-background/95 backdrop-blur z-20 text-muted-foreground"
              style={{ width: `${width}px` }}
            >
              Q{quarterNum} {format(qDate, 'yyyy')}
            </div>
          );
        }
        qDate = nextQuarter;
      }
    } else {
      // Day/Week/Month view: Top row shows months
      let mDate = startDate;
      while (mDate <= endDate) {
        const nextMonth = startOfMonth(addMonths(mDate, 1));
        const limitDate = nextMonth > endDate ? endDate : nextMonth;
        const firstDayOfSegment = mDate < startDate ? startDate : mDate;
        const width = differenceInDays(limitDate, firstDayOfSegment) * columnWidth;

        if (width > 0) {
          topRowCells.push(
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
    }

    // Bottom row (quarters/months/days depending on view mode)
    const bottomRowCells: React.ReactNode[] = [];

    if (viewMode === 'year') {
      // Year view: Bottom row shows quarters
      let qDate = startOfQuarter(startDate);
      while (qDate <= endDate) {
        const nextQuarter = startOfQuarter(addMonths(qDate, 3));
        const limitDate = nextQuarter > endDate ? endDate : nextQuarter;
        const firstDayOfSegment = qDate < startDate ? startDate : qDate;
        const width = differenceInDays(limitDate, firstDayOfSegment) * columnWidth;

        if (width > 0) {
          const quarterNum = getQuarter(qDate);
          bottomRowCells.push(
            <div
              key={`q-${qDate.toISOString()}`}
              className="h-8 border-r flex items-center justify-center text-xs flex-shrink-0 select-none bg-muted/20 text-muted-foreground"
              style={{ width: `${width}px` }}
            >
              Q{quarterNum}
            </div>
          );
        }
        qDate = nextQuarter;
      }
    } else if (viewMode === 'quarter') {
      // Quarter view: Bottom row shows months
      let mDate = startOfMonth(startDate);
      while (mDate <= endDate) {
        const nextMonth = startOfMonth(addMonths(mDate, 1));
        const limitDate = nextMonth > endDate ? endDate : nextMonth;
        const firstDayOfSegment = mDate < startDate ? startDate : mDate;
        const width = differenceInDays(limitDate, firstDayOfSegment) * columnWidth;

        if (width > 0) {
          bottomRowCells.push(
            <div
              key={`m-${mDate.toISOString()}`}
              className="h-8 border-r flex items-center justify-center text-xs flex-shrink-0 select-none bg-muted/20 text-muted-foreground"
              style={{ width: `${width}px` }}
            >
              {format(mDate, 'MMM')}
            </div>
          );
        }
        mDate = nextMonth;
      }
    } else {
      // Day/Week/Month view: Bottom row shows days
      bottomRowCells.push(...days.map((day) => {
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
      }));
    }

    return (
      <div className="flex flex-col min-w-max">
        <div className="flex flex-row">{topRowCells}</div>
        <div className="flex flex-row border-b">{bottomRowCells}</div>
      </div>
    );
  };

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

  /**
   * DEPENDENCY LINE RENDERING APPROACH
   * ==================================
   *
   * Overview:
   * ---------
   * This function renders SVG lines connecting dependent tasks in the Gantt chart.
   * Dependencies flow from the end of a predecessor task to the start of a successor task.
   *
   * Technical Approach:
   * -------------------
   *
   * 1. TASK POSITION DETECTION
   *    - Use React refs to store references to task bar DOM elements
   *    - Each task bar will have a ref attached: taskBarRefs[recordId]
   *    - Calculate coordinates relative to the timeline container using getBoundingClientRect()
   *    - Account for scroll offset by subtracting container's scroll position
   *
   * 2. COORDINATE CALCULATION
   *    - Start point (predecessor):
   *      x = taskBarRightEdge - 5px (slight offset from edge)
   *      y = taskBarCenterY
   *
   *    - End point (successor):
   *      x = taskBarLeftEdge + 5px
   *      y = taskBarCenterY
   *
   * 3. LINE ROUTING STRATEGY (Orthogonal Routing)
   *    - Use orthogonal (horizontal + vertical) routing for clean appearance
   *    - Avoid overlaps by calculating different vertical offsets for multiple dependencies
   *    - Path pattern: Start → Right → Down/Up → Right → End
   *
   *    Path coordinates:
   *    a) Start at predecessor right edge, middle height
   *    b) Extend right by 10px (horizontal segment)
   *    c) Route vertically to successor's Y level (with offset to avoid overlaps)
   *    d) Extend horizontally to successor left edge
   *
   *    Overlap avoidance:
   *    - Calculate number of dependencies between row pairs
   *    - Apply vertical offset based on dependency index: offset = index * 8px
   *    - Limit max offset to prevent lines going too far from rows
   *
   * 4. SVG RENDERING
   *    - Use absolute positioned SVG overlay covering entire timeline area
   *    - SVG properties:
   *      position: absolute
   *      top: 0
   *      left: 0
   *      width: 100%
   *      height: 100%
   *      pointer-events: none (allow clicks to pass through to task bars)
   *      z-index: 5 (above grid, below task bars)
   *
   *    - Each dependency rendered as <path> element with d attribute
   *    - Path data format (M = move to, L = line to):
   *      M startX startY L mid1X mid1Y L mid2X mid2Y L endX endY
   *
   * 5. ARROW MARKERS
   *    - Define SVG <marker> element in <defs> section
   *    - Marker orientation: auto (rotates to match line direction)
   *    - Arrow shape: small triangle or chevron pointing right
   *    - Marker properties:
   *      id: "dependency-arrow"
   *      markerWidth: 10
   *      markerHeight: 10
   *      refX: 9 (arrow tip position)
   *      refY: 3 (vertical center)
   *      orient: auto
   *
   *    - Apply marker to path using marker-end attribute
   *    - Marker color matches dependency line color
   *
   * 6. STYLING
   *    - Default color: #64748b (slate-500)
   *    - Stroke width: 1.5px
   *    - Stroke opacity: 0.6
   *    - Hover effect: Increase opacity to 0.9, stroke width to 2px
   *    - Critical path dependencies: Use accent color (e.g., #f59e0b amber-500)
   *    - Blocked dependencies: Use danger color (e.g., #ef4444 red-500)
   *
   * 7. UPDATE MECHANISMS
   *    - Recalculate on:
   *      a) Component mount (initial render)
   *      b) Task drag end (handleMouseUp)
   *      c) Timeline scroll (useScroll hook on timeline container)
   *      d) Window resize (useEffect with resize listener)
   *      e) Data changes (filteredData changes)
   *
   *    - Throttle scroll/resize updates to avoid performance issues
   *    - Use requestAnimationFrame for smooth updates during drag
   *
   * 8. PERFORMANCE OPTIMIZATIONS
   *    - Memoize dependency calculations using useMemo
   *    - Only recalculate when relevant data changes
   *    - Use virtual rendering for large datasets (>100 dependencies)
   *    - Consider canvas instead of SVG for 500+ dependencies
   *    - Debounce scroll events by 100ms
   *
   * 9. STATE MANAGEMENT
   *    - showDependencies: boolean (default: true) - toggle visibility
   *    - taskBarRefs: useRef<Record<string, HTMLDivElement>> - DOM element refs
   *    - dependencyLines: useMemo<DependencyLine[]> - calculated line data
   *
   * 10. DEPENDENCY DATA STRUCTURE
   *     - Dependency line interface:
    *       interface DependencyLine {
    *         id: string;
    *         fromTaskId: string;
    *         toTaskId: string;
    *         path: string; // SVG path data
    *         color: string;
    *     }
   *
   * Implementation Steps:
   * --------------------
   * 1. Create taskBarRefs ref to store element references
   * 2. Attach ref to each task bar div in the render loop
   * 3. Create calculateDependencyLines() function to compute paths
   * 4. Add SVG overlay element in timeline container
   * 5. Render <path> elements for each dependency
   * 6. Add scroll/resize/drag event listeners to trigger recalculation
   * 7. Add toggle button in toolbar for show/hide
   *
   * Known Limitations:
   * ------------------
   * - Requires 2-pass rendering or useLayoutEffect for accurate positions
   * - May have slight offset on first render (resolves on next frame)
   * - Very complex dependency networks may cause visual clutter
   * - Circular dependencies not handled (will create infinite loops)
   *
   * Future Enhancements:
   * --------------------
   * - Bezier curve routing for smoother appearance
   * - Animated line drawing on load
   * - Dependency type indicators (FS, SS, FF, SF)
   * - Lag/lead time visualization
   * - Dependency line tooltips showing task names
   */
  const _renderDependencies = () => {
      if (!dependencyFieldId) return null;

      // Implementation will follow the approach documented above
      // This will be implemented in subsequent subtasks (2-2 through 2-7)
      return null;
  };
  void _renderDependencies; // Reserved for dependency visualization implementation

  return (
    <Card className="flex flex-col h-full border-0 shadow-none rounded-none bg-background">
        {/* Toolbar */}
        <div className="flex items-center justify-between p-2 border-b gap-2 bg-card">
            <div className="flex items-center gap-2">
                <Button variant="outline" size="icon" onClick={() => {
                    const offset = viewMode === 'year' ? 365 : viewMode === 'quarter' ? 90 : viewMode === 'month' ? 30 : 7;
                    setCurrentDate(subDays(currentDate, offset));
                }}>
                    <ChevronLeft className="h-4 w-4" />
                </Button>
                <div className="flex items-center gap-2 px-2 font-medium min-w-[140px] justify-center">
                    <CalendarIcon className="h-4 w-4 text-muted-foreground" />
                    {viewMode === 'year' ? format(currentDate, 'yyyy') : format(currentDate, 'MMMM yyyy')}
                </div>
                <Button variant="outline" size="icon" onClick={() => {
                    const offset = viewMode === 'year' ? 365 : viewMode === 'quarter' ? 90 : viewMode === 'month' ? 30 : 7;
                    setCurrentDate(addDays(currentDate, offset));
                }}>
                    <ChevronRight className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setCurrentDate(new Date())}>Today</Button>
            </div>
            
            <div className="flex items-center gap-2 flex-1 justify-center">
                 <div className="relative w-64">
                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input 
                        placeholder="Search records..." 
                        className="pl-8 h-9" 
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                 </div>
                 {/* Field Selectors (simplified for UI) */}
                 <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-[150px] h-9">
                        <Filter className="w-3 h-3 mr-2" />
                        <SelectValue placeholder="Filter Status" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">All Statuses</SelectItem>
                         {/* We would dynamically generate these from the status field options */}
                        <SelectItem value="To Do">To Do</SelectItem>
                        <SelectItem value="In Progress">In Progress</SelectItem>
                        <SelectItem value="Done">Done</SelectItem>
                    </SelectContent>
                 </Select>
            </div>

            <div className="flex items-center gap-1 bg-muted/50 p-1 rounded-md">
                <Button
                    variant={viewMode === 'day' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => { setViewMode('day'); setColumnWidth(60); }}
                >
                    Day
                </Button>
                <Button
                    variant={viewMode === 'week' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => { setViewMode('week'); setColumnWidth(40); }}
                >
                    Week
                </Button>
                <Button
                    variant={viewMode === 'month' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => { setViewMode('month'); setColumnWidth(20); }}
                >
                    Month
                </Button>
                <Button
                    variant={viewMode === 'quarter' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => { setViewMode('quarter'); setColumnWidth(10); }}
                >
                    Quarter
                </Button>
                <Button
                    variant={viewMode === 'year' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => { setViewMode('year'); setColumnWidth(5); }}
                >
                    Year
                </Button>
            </div>
        </div>

        {/* Content Area - Split Pane */}
        <div className="flex flex-1 overflow-hidden" ref={containerRef} onMouseUp={handleMouseUp} onMouseMove={handleMouseMove} onMouseLeave={handleMouseUp}>
            
            {/* Left: Table */}
            <div className="w-[300px] border-r flex flex-col bg-card z-10 shadow-sm flex-shrink-0">
                <div className="h-16 border-b bg-muted/10 flex items-center px-4 font-semibold text-sm text-muted-foreground">
                    Records
                </div>
                <div className="flex-1 overflow-y-hidden">
                    <div className="divide-y">
                        {table.getRowModel().rows.map(row => (
                            <div key={row.id} className="h-12 flex items-center px-4 hover:bg-muted/50 transition-colors text-sm group relative">
                                {row.getVisibleCells().map(cell => (
                                    <div key={cell.id} className="flex-1 min-w-0 mr-2 first:font-medium">
                                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                    </div>
                                ))}
                                <Button variant="ghost" size="icon" className="h-6 w-6 opacity-0 group-hover:opacity-100 absolute right-1">
                                    <MoreHorizontal className="h-3 w-3" />
                                </Button>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="h-10 border-t flex items-center px-4 text-xs text-muted-foreground bg-muted/10">
                    {filteredData.length} records
                </div>
            </div>

            {/* Right: Timeline */}
            <div className="flex-1 overflow-auto relative bg-background/50 scrollbar-hide">
                <div className="min-w-max">
                    {/* Header */}
                    {renderTimeHeader()}
                    
                    {/* Grid & Rows */}
                    <div className="relative min-w-max">
                        {renderGridBackground()}

                        {/* SVG Overlay for Dependency Lines */}
                        {showDependencies && (
                            <svg
                                className="absolute inset-0 pointer-events-none z-[5]"
                            >
                                <defs>
                                    {/* Arrow marker definition for dependency lines */}
                                    <marker
                                        id="dependency-arrow"
                                        markerWidth="10"
                                        markerHeight="10"
                                        refX="9"
                                        refY="3"
                                        orient="auto"
                                        markerUnits="strokeWidth"
                                    >
                                        <path
                                            d="M0,0 L0,6 L9,3 z"
                                            fill="rgb(100, 116, 139)"
                                        />
                                    </marker>
                                </defs>
                                {/* Dependency paths will be rendered here in subsequent subtasks */}
                            </svg>
                        )}

                        <div className="relative pt-0 pb-10">
                            {table.getRowModel().rows.map(row => {
                                const record = row.original;
                                const styleInfo = getRecordStyle(record);
                                const progress = progressFieldId ? record[progressFieldId] : 0;
                                
                                return (
                                    <div key={row.id} className="h-12 border-b relative group hover:bg-black/5 transition-colors">
                                        {/* Row line guide */}
                                        <div className="absolute inset-0 border-b border-dashed border-border/50" />
                                        
                                        {styleInfo.display !== 'none' && (
                                            <TooltipProvider>
                                                <Tooltip>
                                                    <TooltipTrigger asChild>
                                                        <div 
                                                            className={cn(
                                                                "absolute top-2 h-8 rounded-md shadow-sm border text-white text-xs flex items-center px-2 cursor-pointer transition-all hover:shadow-md select-none overflow-hidden",
                                                                styleInfo.className,
                                                                isDragging && dragRecordId === record.id ? 'ring-2 ring-ring opacity-80 z-50 cursor-grabbing' : ''
                                                            )}
                                                            style={{
                                                                left: styleInfo.left,
                                                                width: styleInfo.width,
                                                                // If specific color logic was complex, we'd use style here, but we are using tailwind classes mostly
                                                            }}
                                                            onMouseDown={(e) => handleDragStart(e, record, 'move')}
                                                        >
                                                            {/* Progress Bar Background */}
                                                            {progress > 0 && (
                                                                <div 
                                                                    className="absolute left-0 top-0 bottom-0 bg-black/20 pointer-events-none" 
                                                                    style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} 
                                                                />
                                                            )}
                                                            
                                                            {/* Content */}
                                                            <span className="relative z-10 truncate font-medium drop-shadow-sm">
                                                                {titleFieldId ? record[titleFieldId] : 'Untitled'}
                                                            </span>
                                                            
                                                            {/* Resize Handles */}
                                                            <div 
                                                                className="absolute left-0 top-0 bottom-0 w-2 cursor-w-resize hover:bg-black/20 z-20 opacity-0 group-hover:opacity-100 transition-opacity"
                                                                onMouseDown={(e) => handleDragStart(e, record, 'resize-left')}
                                                            />
                                                            <div 
                                                                className="absolute right-0 top-0 bottom-0 w-2 cursor-e-resize hover:bg-black/20 z-20 opacity-0 group-hover:opacity-100 transition-opacity"
                                                                onMouseDown={(e) => handleDragStart(e, record, 'resize-right')}
                                                            />
                                                        </div>
                                                    </TooltipTrigger>
                                                    <TooltipContent>
                                                        <div className="text-xs">
                                                            <div className="font-bold">{titleFieldId ? record[titleFieldId] : 'Untitled'}</div>
                                                            <div>{safeParseDate(record[startDateFieldId])?.toLocaleDateString()} - {safeParseDate(record[endDateFieldId])?.toLocaleDateString()}</div>
                                                            {progress > 0 && <div>Progress: {progress}%</div>}
                                                            {record[statusFieldId] && <div>Status: {record[statusFieldId]}</div>}
                                                        </div>
                                                    </TooltipContent>
                                                </Tooltip>
                                            </TooltipProvider>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        {/* Missing fields warning */}
        {!startDateFieldId && (
            <div className="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50">
                <Card className="max-w-md p-6 text-center space-y-4">
                    <div className="mx-auto w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center text-primary">
                        <CalendarIcon className="w-6 h-6" />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold">Start Date Required</h3>
                        <p className="text-sm text-muted-foreground mt-2">
                            To use the Gantt view, your table must have at least one Date field.
                            Please add a date field to your table structure.
                        </p>
                    </div>
                </Card>
            </div>
        )}
    </Card>
  );
};
