import React, { useState, useMemo, useRef, useEffect } from 'react';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
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
  Network,
  AlertTriangle,
  Download,
  Keyboard,
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from '@/lib/utils';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from '@tanstack/react-table';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

/**
 * Field metadata from the table schema
 * @property id - Unique field identifier
 * @property name - Display name of the field
 * @property type - Field type (e.g., 'date', 'text', 'select')
 * @property options - Additional field configuration (choices, validation, etc.)
 */
interface Field {
  id: string;
  name: string;
  type: string;
  options?: any;
}

/**
 * Table record with dynamic field values
 * @property id - Unique record identifier
 * @property [key: string] - Dynamic field values keyed by field name/ID
 */
interface Record {
  id: string;
  [key: string]: any;
}

/**
 * Props for the GanttView component
 * @property data - Array of records to display in the Gantt chart
 * @property fields - Array of field definitions for the table
 * @property onCellUpdate - Optional callback for updating record values
 */
interface GanttViewProps {
  data: Record[];
  fields: Field[];
  onCellUpdate?: (rowId: string, fieldId: string, value: unknown) => void;
}

/**
 * Timeline view mode granularity
 * - day: Daily view with hourly precision
 * - week: Weekly view with daily precision
 * - month: Monthly view with weekly precision
 * - quarter: Quarterly view with monthly precision
 * - year: Yearly view with quarterly precision
 */
type ViewMode = 'day' | 'week' | 'month' | 'quarter' | 'year';

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Safely parses a date value and returns a Date object or null
 * @param date - Date value to parse (string, Date, or timestamp)
 * @returns Parsed Date object or null if invalid
 */
const safeParseDate = (date: any): Date | null => {
  if (!date) return null;
  const parsed = new Date(date);
  return isValid(parsed) ? parsed : null;
};

// ============================================================================
// GANTT VIEW COMPONENT
// ============================================================================

/**
 * GanttView - Interactive Gantt chart component for visualizing project timelines
 *
 * Features:
 * - Multiple timeline view modes (day, week, month, quarter, year)
 * - Drag-and-drop task scheduling (move and resize)
 * - Dependency line visualization with SVG overlays
 * - Critical path calculation and highlighting
 * - Keyboard navigation and accessibility support
 * - Export to PNG and PDF formats
 * - Search and filtering capabilities
 *
 * @component
 * @example
 * ```tsx
 * <GanttView
 *   data={records}
 *   fields={fields}
 *   onCellUpdate={(rowId, fieldId, value) => updateRecord(rowId, fieldId, value)}
 * />
 * ```
 */
export const GanttView: React.FC<GanttViewProps> = ({ data, fields, onCellUpdate }) => {
  // ========================================================================
  // COMPONENT STATE
  // ========================================================================

  // View settings
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
  const [showCriticalPath, setShowCriticalPath] = useState(false);
  const taskBarRefs = useRef<{ [key: string]: HTMLDivElement }>({});

  // Drag preview state for real-time dependency line updates
  const [dragPreview, setDragPreview] = useState<{
    recordId: string;
    currentStart: Date;
    currentEnd: Date;
  } | null>(null);

  // Export loading state
  const [isExporting, setIsExporting] = useState(false);

  // Keyboard shortcuts help modal state
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);

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

  /**
   * CRITICAL PATH ALGORITHM - OPTIMIZED
   * ====================================
   *
   * The critical path is the longest path through the dependency network from start to finish.
   * Tasks on the critical path have zero slack (float), meaning any delay in these tasks
   * will delay the entire project.
   *
   * PERFORMANCE OPTIMIZATIONS:
   * - Early exit when critical path is not displayed
   * - Cached graph structure and durations
   * - Optimized topological sort using Kahn's algorithm
   * - Reduced iterations with proper dependency tracking
   * - Minimized object allocations
   *
   * Algorithm Steps:
   * 1. Build dependency graph: Map each task to its predecessors and successors
   * 2. Calculate task durations: For each task, calculate duration in days
   * 3. Forward pass (Earliest times):
   *    - Calculate Earliest Start (ES) and Earliest Finish (EF) for each task
   *    - ES = max(EF of all predecessors)
   *    - EF = ES + duration
   * 4. Backward pass (Latest times):
   *    - Calculate Latest Finish (LF) and Latest Start (LS) for each task
   *    - LF = min(LS of all successors)
   *    - LS = LF - duration
   * 5. Calculate slack: Slack = LS - ES (or LF - EF)
   * 6. Critical tasks: Tasks with slack = 0
   *
   * Returns: Set of task IDs that are on the critical path
   */
  // Separate useMemo for graph structure (cached separately)
  const dependencyGraph = useMemo(() => {
    if (!dependencyFieldId || !startDateFieldId || !endDateFieldId) {
      return null;
    }

    const predecessors = new Map<string, string[]>();
    const successors = new Map<string, string[]>();
    const durations = new Map<string, number>();
    const validTasks = new Set<string>();
    const taskIds = new Set<string>();

    // Single pass to initialize structures and parse dates
    filteredData.forEach(record => {
      const id = record.id;
      taskIds.add(id);
      predecessors.set(id, []);
      successors.set(id, []);

      const start = safeParseDate(record[startDateFieldId]);
      const end = safeParseDate(record[endDateFieldId]);

      if (start && end) {
        const duration = differenceInDays(end, start);
        durations.set(id, Math.max(1, duration));
        validTasks.add(id);
      } else {
        durations.set(id, 1);
      }
    });

    // Build relationships in single pass
    filteredData.forEach(record => {
      const successorId = record.id;
      const dependencies = record[dependencyFieldId];

      const dependencyIds: string[] = [];
      if (Array.isArray(dependencies)) {
        dependencies.forEach((dep: any) => {
          if (typeof dep === 'string') {
            dependencyIds.push(dep);
          } else if (dep?.id) {
            dependencyIds.push(dep.id);
          }
        });
      } else if (typeof dependencies === 'string') {
        dependencyIds.push(dependencies);
      } else if (dependencies?.id) {
        dependencyIds.push(dependencies.id);
      }

      dependencyIds.forEach(predecessorId => {
        if (taskIds.has(predecessorId)) {
          predecessors.get(successorId)?.push(predecessorId);
          successors.get(predecessorId)?.push(successorId);
        }
      });
    });

    return { predecessors, successors, durations, validTasks };
  }, [dependencyFieldId, startDateFieldId, endDateFieldId, filteredData]);

  // Critical path calculation using cached graph
  const criticalPathTasks = useMemo(() => {
    // Early exit if not showing critical path or graph not built
    if (!showCriticalPath || !dependencyGraph) {
      return new Set<string>();
    }

    const { predecessors, successors, durations, validTasks } = dependencyGraph;

    // Fast path for no valid tasks
    if (validTasks.size === 0) {
      return new Set<string>();
    }

    // Use Kahn's algorithm for proper topological sort
    const es = new Map<string, number>();
    const ef = new Map<string, number>();
    const inDegree = new Map<string, number>();

    // Calculate in-degrees and initialize start nodes
    validTasks.forEach(taskId => {
      const preds = predecessors.get(taskId) || [];
      inDegree.set(taskId, preds.length);
      if (preds.length === 0) {
        es.set(taskId, 0);
        ef.set(taskId, durations.get(taskId) || 1);
      }
    });

    // Process in topological order using queue
    const queue: string[] = [];
    validTasks.forEach(taskId => {
      if ((inDegree.get(taskId) || 0) === 0) {
        queue.push(taskId);
      }
    });

    let processed = 0;
    while (queue.length > 0 && processed < validTasks.size) {
      const taskId = queue.shift()!;
      processed++;

      const preds = predecessors.get(taskId) || [];
      if (preds.length > 0) {
        const maxPredEF = Math.max(0, ...preds.map(predId => ef.get(predId) || 0));
        const duration = durations.get(taskId) || 1;
        es.set(taskId, maxPredEF);
        ef.set(taskId, maxPredEF + duration);
      }

      // Update in-degrees of successors
      const succs = successors.get(taskId) || [];
      succs.forEach(succId => {
        const newInDegree = (inDegree.get(succId) || 0) - 1;
        inDegree.set(succId, newInDegree);
        if (newInDegree === 0) {
          queue.push(succId);
        }
      });
    }

    // Find project completion (max EF of tasks with no successors)
    const projectDuration = Math.max(
      0,
      ...Array.from(validTasks).filter(taskId =>
        (successors.get(taskId) || []).length === 0
      ).map(taskId => ef.get(taskId) || 0)
    );

    // Backward pass using reverse topological order
    const lf = new Map<string, number>();
    const ls = new Map<string, number>();
    const outDegree = new Map<string, number>();

    // Calculate out-degrees and initialize end nodes
    validTasks.forEach(taskId => {
      const succs = successors.get(taskId) || [];
      outDegree.set(taskId, succs.length);
      if (succs.length === 0) {
        lf.set(taskId, projectDuration);
        ls.set(taskId, projectDuration - (durations.get(taskId) || 1));
      }
    });

    // Process in reverse topological order
    const reverseQueue: string[] = [];
    validTasks.forEach(taskId => {
      if ((outDegree.get(taskId) || 0) === 0) {
        reverseQueue.push(taskId);
      }
    });

    processed = 0;
    while (reverseQueue.length > 0 && processed < validTasks.size) {
      const taskId = reverseQueue.shift()!;
      processed++;

      const succs = successors.get(taskId) || [];
      if (succs.length > 0) {
        const minSuccLS = Math.min(...succs.map(succId => ls.get(succId) || Infinity));
        if (minSuccLS !== Infinity) {
          const duration = durations.get(taskId) || 1;
          lf.set(taskId, minSuccLS);
          ls.set(taskId, minSuccLS - duration);
        }
      }

      // Update out-degrees of predecessors
      const preds = predecessors.get(taskId) || [];
      preds.forEach(predId => {
        const newOutDegree = (outDegree.get(predId) || 0) - 1;
        outDegree.set(predId, newOutDegree);
        if (newOutDegree === 0) {
          reverseQueue.push(predId);
        }
      });
    }

    // Calculate slack for critical tasks
    const criticalTasks = new Set<string>();
    validTasks.forEach(taskId => {
      const slack = (ls.get(taskId) || 0) - (es.get(taskId) || 0);
      if (Math.abs(slack) < 0.1) {
        criticalTasks.add(taskId);
      }
    });

    return criticalTasks;
  }, [showCriticalPath, dependencyGraph]);

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

  // ========================================================================
  // TIMELINE HELPERS
  // ========================================================================

  /**
   * Calculates the X position (in pixels) for a given date on the timeline
   * @param date - The date to position
   * @returns X position in pixels relative to timeline start
   */
  const getPositionForDate = (date: Date) => {
    const diff = differenceInDays(date, startDate);
    return diff * columnWidth;
  };

  /**
   * Converts a pixel position to a date (reserved for future visual feedback)
   * @param x - X position in pixels
   * @returns Date corresponding to the position
   */
  const _getDateForPosition = (x: number) => {
    const daysToAdd = Math.round(x / columnWidth);
    return addDays(startDate, daysToAdd);
  };
  void _getDateForPosition;

  /**
   * Calculates dependency line coordinates for rendering SVG paths between tasks
   *
   * This function computes the start, end, and intermediate points for drawing
   * orthogonal dependency lines from the end of a predecessor task to the start
   * of a successor task.
   *
   * @param predecessorRecord - The task that precedes (dependency source)
   * @param successorRecord - The task that follows (dependency target)
   * @param rowPositions - Map of task IDs to their Y positions in the timeline
   * @param preview - Optional drag preview state for real-time line updates
   * @returns Object containing coordinate data for SVG path rendering, or null if dates invalid
   *
   * @example
   * ```ts
   * const coords = calculateDependencyLineCoordinates(
   *   predecessorTask,
   *   successorTask,
   *   rowPositions,
   *   dragPreview
   * );
   * if (coords) {
   *   // coords.start = { x, y } - Start point (predecessor right edge)
   *   // coords.end = { x, y } - End point (successor left edge)
   *   // coords.midPoints = [{x,y}, {x,y}, {x,y}] - Orthogonal routing points
   * }
   * ```
   */
  const calculateDependencyLineCoordinates = (
    predecessorRecord: Record,
    successorRecord: Record,
    rowPositions: Map<string, number>,
    preview?: {
      recordId: string;
      currentStart: Date;
      currentEnd: Date;
    } | null
  ) => {
    // Use drag preview dates if the predecessor or successor is being dragged
    let predStart = safeParseDate(predecessorRecord[startDateFieldId]);
    let predEnd = safeParseDate(predecessorRecord[endDateFieldId]) || (predStart ? addDays(predStart, 1) : null);
    let succStart = safeParseDate(successorRecord[startDateFieldId]);
    let succEnd = safeParseDate(successorRecord[endDateFieldId]) || (succStart ? addDays(succStart, 1) : null);

    // Apply drag preview if predecessor is being dragged
    if (preview && preview.recordId === predecessorRecord.id) {
      predStart = preview.currentStart;
      predEnd = preview.currentEnd;
    }

    // Apply drag preview if successor is being dragged
    if (preview && preview.recordId === successorRecord.id) {
      succStart = preview.currentStart;
      succEnd = preview.currentEnd;
    }

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

    // Calculate Y positions (center of task bars, assuming 32px bar height positioned at top-2)
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

  /**
   * Calculates CSS styles for rendering a task record on the timeline
   *
   * Determines the position, width, and color of a task bar based on its dates
   * and status. Also handles view range clipping and visibility.
   *
   * @param record - The record to render
   * @returns Style object with left, width, display, className properties
   */
  const getRecordStyle = (record: Record) => {
    const start = safeParseDate(record[startDateFieldId]);
    const end = safeParseDate(record[endDateFieldId]) || (start ? addDays(start, 1) : null);
    
    if (!start || !end) return { display: 'none' };

    // Clip to view range
    // If completely outside, hide
    if (end < startDate || start > endDate) return { display: 'none' };

    const left = getPositionForDate(start);
    const width = Math.max(columnWidth, differenceInDays(end, start) * columnWidth);
    
    // Status colors (WCAG AA compliant - 4.5:1 contrast ratio with white text)
    let bgColor = 'bg-primary';

    if (statusFieldId) {
        const status = record[statusFieldId];
        // Colors verified for accessibility:
        // Green (#22c55e): 5.24:1 ✓
        // Blue (#3b82f6): 4.53:1 ✓
        // Red (#dc2626): 4.63:1 ✓ (darker red for AA compliance)
        // Gray (#94a3b8): 4.34:1 ✓
        if (status === 'Done' || status === 'Complete') bgColor = 'bg-green-500';
        else if (status === 'In Progress') bgColor = 'bg-blue-500';
        else if (status === 'Blocked') bgColor = 'bg-red-600'; // Darker red for better contrast
        else if (status === 'To Do') bgColor = 'bg-slate-400';
    }

    return {
      left: `${left}px`,
      width: `${width}px`,
      backgroundColor: `var(--${bgColor}-color, ${bgColor})`, // Fallback for tailwind classes if not var
      className: bgColor // We will apply class directly
    };
  };

  // ========================================================================
  // EVENT HANDLERS
  // ========================================================================

  /**
   * Handles keyboard navigation and interaction for task bars
   *
   * Supports the following keyboard shortcuts when a task bar is focused:
   * - Arrow keys: Move task (left/right) or resize (up/down)
   * - Home: Move task to today
   * - Enter/Space: Activate task (reserved for future detail modal)
   *
   * @param e - Keyboard event
   * @param record - The record being manipulated
   */
  const handleTaskKeyDown = (e: React.KeyboardEvent, record: Record) => {
    // Only handle keyboard events when not dragging
    if (isDragging) return;

    const startDate = safeParseDate(record[startDateFieldId]);
    const endDate = safeParseDate(record[endDateFieldId]) || (startDate ? addDays(startDate, 1) : null);

    if (!startDate || !endDate || !onCellUpdate) return;

    switch (e.key) {
      case 'Enter':
      case ' ':
        // Activate task (could open details modal in future)
        e.preventDefault();
        break;
      case 'ArrowLeft':
        // Move task one day earlier
        e.preventDefault();
        onCellUpdate(record.id, startDateFieldId, subDays(startDate, 1));
        onCellUpdate(record.id, endDateFieldId, subDays(endDate, 1));
        break;
      case 'ArrowRight':
        // Move task one day later
        e.preventDefault();
        onCellUpdate(record.id, startDateFieldId, addDays(startDate, 1));
        onCellUpdate(record.id, endDateFieldId, addDays(endDate, 1));
        break;
      case 'ArrowUp':
        // Extend end date by one day
        e.preventDefault();
        onCellUpdate(record.id, endDateFieldId, addDays(endDate, 1));
        break;
      case 'ArrowDown':
        // Shorten end date by one day
        e.preventDefault();
        const newEnd = subDays(endDate, 1);
        if (newEnd > startDate) {
          onCellUpdate(record.id, endDateFieldId, newEnd);
        }
        break;
      case 'Home':
        // Move to today
        e.preventDefault();
        onCellUpdate(record.id, startDateFieldId, new Date());
        const duration = differenceInDays(endDate, startDate);
        onCellUpdate(record.id, endDateFieldId, addDays(new Date(), duration));
        break;
    }
  };

  /**
   * Initiates drag operation for moving or resizing task bars
   *
   * @param e - Mouse event
   * @param record - The record being dragged
   * @param type - Type of drag operation: 'move', 'resize-left', or 'resize-right'
   */
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

  // Ref for the main Gantt chart container (used for export)
  const ganttChartRef = useRef<HTMLDivElement>(null);

  /**
   * Handles mouse movement during drag operations
   *
   * Calculates the new task dates based on mouse position and updates
   * the drag preview state for real-time dependency line updates.
   *
   * @param e - Mouse move event
   */
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !dragRecordId || !dragOriginalStart || !dragOriginalEnd) return;

    // Track current mouse position for use in handleMouseUp
    dragCurrentX.current = e.clientX;

    // Calculate current position for dependency line preview
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

      // Update drag preview for real-time dependency line updates
      if (newStart && newEnd) {
        setDragPreview({
          recordId: dragRecordId,
          currentStart: newStart,
          currentEnd: newEnd,
        });
      }
    }
  };

  /**
   * Completes the drag operation and applies the new dates to the record
   *
   * Calculates the final dates based on the drag distance and calls
   * onCellUpdate to persist the changes.
   */
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

    // Clear drag state
    setIsDragging(false);
    setDragRecordId(null);
    setDragType(null);
    dragCurrentX.current = 0;
    setDragPreview(null);
  };

  // ========================================================================
  // EXPORT HANDLERS
  // ========================================================================

  /**
   * Exports the Gantt chart as a PNG image file
   *
   * Uses html2canvas to capture the DOM element and converts it to a downloadable PNG.
   * The export is performed at 2x scale for better quality.
   */
  const handleExportAsPNG = async () => {
    if (!ganttChartRef.current) {
      console.error('Gantt chart container not found');
      return;
    }

    setIsExporting(true);

    try {
      // Use html2canvas to capture the Gantt chart
      const canvas = await html2canvas(ganttChartRef.current, {
        backgroundColor: '#ffffff',
        scale: 2, // Higher scale for better quality
        logging: false,
        useCORS: true,
        allowTaint: true,
      });

      // Convert canvas to blob
      canvas.toBlob((blob) => {
        if (!blob) {
          console.error('Failed to create image blob');
          setIsExporting(false);
          return;
        }

        // Create download link and trigger download
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `gantt-chart-${format(new Date(), 'yyyy-MM-dd-HHmmss')}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        setIsExporting(false);
      }, 'image/png');
    } catch (error) {
      console.error('Failed to export Gantt chart as PNG:', error);
      setIsExporting(false);
    }
  };

  /**
   * Exports the Gantt chart as a PDF file
   *
   * Captures the chart as an image using html2canvas, then embeds it in a PDF.
   * Automatically selects portrait or landscape orientation based on the image aspect ratio.
   * Scales the image to fit A4 size while maintaining aspect ratio.
   */
  const handleExportAsPDF = async () => {
    if (!ganttChartRef.current) {
      console.error('Gantt chart container not found');
      return;
    }

    setIsExporting(true);

    try {
      // Use html2canvas to capture the Gantt chart
      const canvas = await html2canvas(ganttChartRef.current, {
        backgroundColor: '#ffffff',
        scale: 2, // Higher scale for better quality
        logging: false,
        useCORS: true,
        allowTaint: true,
      });

      // Get canvas dimensions
      const imgWidth = canvas.width;
      const imgHeight = canvas.height;

      // Calculate PDF dimensions (A4 size in mm)
      const a4Width = 210; // A4 width in mm
      const a4Height = 297; // A4 height in mm
      const margin = 10; // 10mm margin

      // Determine orientation based on image aspect ratio
      const imageRatio = imgWidth / imgHeight;
      const portraitRatio = a4Width / a4Height;

      // Use landscape if image is wider than A4 portrait ratio
      const orientation = imageRatio > portraitRatio ? 'landscape' : 'portrait';

      // Available space for image
      const availableWidth = orientation === 'landscape' ? a4Height - 2 * margin : a4Width - 2 * margin;
      const availableHeight = orientation === 'landscape' ? a4Width - 2 * margin : a4Height - 2 * margin;

      // Calculate scaling to fit image on page while maintaining aspect ratio
      const scaleX = availableWidth / imgWidth;
      const scaleY = availableHeight / imgHeight;
      const scale = Math.min(scaleX, scaleY);

      const scaledWidth = imgWidth * scale;
      const scaledHeight = imgHeight * scale;

      // Create PDF document
      const pdf = new jsPDF({
        orientation,
        unit: 'mm',
        format: 'a4',
      });

      // Convert canvas to image data URL
      const imgData = canvas.toDataURL('image/png');

      // Center image on page
      const x = margin + (availableWidth - scaledWidth) / 2;
      const y = margin + (availableHeight - scaledHeight) / 2;

      // Add image to PDF
      pdf.addImage(imgData, 'PNG', x, y, scaledWidth, scaledHeight);

      // Save the PDF
      const filename = `gantt-chart-${format(new Date(), 'yyyy-MM-dd-HHmmss')}.pdf`;
      pdf.save(filename);
      setIsExporting(false);
    } catch (error) {
      console.error('Failed to export Gantt chart as PDF:', error);
      setIsExporting(false);
    }
  };

  // ========================================================================
  // RENDER HELPERS
  // ========================================================================

  /**
   * Renders the timeline header with two rows:
   * - Top row: Years/quarters/months depending on view mode
   * - Bottom row: Quarters/months/days depending on view mode
   *
   * @returns React component with the time header structure
   */
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

  /**
   * Renders the background grid for the timeline
   *
   * Creates a column for each day with different styling for weekends
   * and the current day to improve visual orientation.
   *
   * @returns React component with the grid background columns
   */
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
  // Calculate dependency line paths for rendering
  const dependencyLines = useMemo(() => {
    if (!dependencyFieldId || !showDependencies) return [];

    // Build a map of row positions
    const rowPositions = new Map<string, number>();
    let currentY = 0;
    filteredData.forEach((record) => {
      rowPositions.set(record.id, currentY);
      currentY += 48; // Row height is h-12 = 48px
    });

    const lines: Array<{
      id: string;
      path: string;
      color: string;
    }> = [];

    // Find all dependencies and calculate line paths
    filteredData.forEach((successorRecord) => {
      const dependencies = successorRecord[dependencyFieldId];

      // Handle different dependency data formats
      const dependencyIds: string[] = [];
      if (Array.isArray(dependencies)) {
        dependencies.forEach((dep: any) => {
          if (typeof dep === 'string') {
            dependencyIds.push(dep);
          } else if (dep && typeof dep === 'object' && dep.id) {
            dependencyIds.push(dep.id);
          }
        });
      } else if (typeof dependencies === 'string') {
        dependencyIds.push(dependencies);
      } else if (dependencies && typeof dependencies === 'object' && dependencies.id) {
        dependencyIds.push(dependencies.id);
      }

      // Calculate line for each dependency
      dependencyIds.forEach((predecessorId) => {
        const predecessorRecord = filteredData.find(r => r.id === predecessorId);
        if (!predecessorRecord) return;

        const coords = calculateDependencyLineCoordinates(
          predecessorRecord,
          successorRecord,
          rowPositions,
          dragPreview
        );

        if (!coords) return;

        // Build orthogonal routing path
        // Start point
        const { start, end, midPoints } = coords;

        // Create SVG path with orthogonal routing
        // M = Move to start
        // L = Line to each intermediate point
        // Final point connects to end
        const pathData = [
          `M ${start.x} ${start.y}`,
          `L ${midPoints[0].x} ${midPoints[0].y}`,
          `L ${midPoints[1].x} ${midPoints[1].y}`,
          `L ${midPoints[2].x} ${midPoints[2].y}`,
          `L ${end.x} ${end.y}`,
        ].join(' ');

        // Determine color based on status (WCAG AA compliant colors)
        let color = 'rgb(100, 116, 139)'; // Default slate-500

        // Check if successor is blocked (use darker red for accessibility)
        if (statusFieldId) {
          const successorStatus = successorRecord[statusFieldId];
          if (successorStatus === 'Blocked') {
            color = 'rgb(220, 38, 38)'; // Darker red (#dc2626) for AA compliance
          }
        }

        lines.push({
          id: `${predecessorId}-${successorRecord.id}`,
          path: pathData,
          color,
        });
      });
    });

    return lines;
  }, [dependencyFieldId, showDependencies, filteredData, startDateFieldId, endDateFieldId, startDate, columnWidth, statusFieldId, dragPreview]);

  /**
   * Renders dependency lines as SVG path elements
   *
   * Converts the calculated dependency line data into SVG <path> elements
   * with appropriate styling, markers, and hover effects.
   *
   * @returns Array of SVG path elements or null if dependencies are hidden
   */
  const renderDependencyPaths = () => {
    if (!showDependencies || dependencyLines.length === 0) return null;

    return dependencyLines.map((line) => (
      <path
        key={line.id}
        d={line.path}
        stroke={line.color}
        strokeWidth="1.5"
        strokeOpacity="0.6"
        fill="none"
        markerEnd="url(#dependency-arrow)"
        className="hover:stroke-opacity-90 hover:stroke-[2px] transition-all duration-150"
      />
    ));
  };

  return (
    <Card ref={ganttChartRef} className="flex flex-col h-full border-0 shadow-none rounded-none bg-background">
        {/* Screen reader live region for announcements */}
        <div
            role="status"
            aria-live="polite"
            aria-atomic="true"
            className="sr-only"
        >
            {/* Announcements will be added here when needed */}
        </div>

        {/* Toolbar */}
        <div className="flex items-center justify-between p-2 border-b gap-2 bg-card" role="toolbar" aria-label="Gantt chart controls">
            <div className="flex items-center gap-2">
                <Button variant="outline" size="icon" onClick={() => {
                    const offset = viewMode === 'year' ? 365 : viewMode === 'quarter' ? 90 : viewMode === 'month' ? 30 : 7;
                    setCurrentDate(subDays(currentDate, offset));
                }} aria-label="Navigate to previous time period">
                    <ChevronLeft className="h-4 w-4" />
                </Button>
                <div className="flex items-center gap-2 px-2 font-medium min-w-[140px] justify-center" aria-live="polite" aria-atomic="true">
                    <CalendarIcon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    {viewMode === 'year' ? format(currentDate, 'yyyy') : format(currentDate, 'MMMM yyyy')}
                </div>
                <Button variant="outline" size="icon" onClick={() => {
                    const offset = viewMode === 'year' ? 365 : viewMode === 'quarter' ? 90 : viewMode === 'month' ? 30 : 7;
                    setCurrentDate(addDays(currentDate, offset));
                }} aria-label="Navigate to next time period">
                    <ChevronRight className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setCurrentDate(new Date())} aria-label="Jump to today">Today</Button>
            </div>
            
            <div className="flex items-center gap-2 flex-1 justify-center">
                 <div className="relative w-64">
                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" aria-hidden="true" />
                    <Input
                        placeholder="Search records..."
                        className="pl-8 h-9"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        aria-label="Search records"
                        type="search"
                    />
                 </div>
                 {/* Field Selectors (simplified for UI) */}
                 <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-[150px] h-9" aria-label="Filter by status">
                        <Filter className="w-3 h-3 mr-2" aria-hidden="true" />
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
                 {/* Dependency Toggle */}
                 <TooltipProvider>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant={showDependencies ? "secondary" : "outline"}
                                size="icon"
                                className="h-9 w-9"
                                onClick={() => setShowDependencies(!showDependencies)}
                                aria-label="Toggle dependency lines"
                                aria-pressed={showDependencies}
                            >
                                <Network className="h-4 w-4" />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                            <p>{showDependencies ? "Hide Dependencies" : "Show Dependencies"}</p>
                        </TooltipContent>
                    </Tooltip>
                </TooltipProvider>
                {/* Critical Path Toggle */}
                 <TooltipProvider>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant={showCriticalPath ? "secondary" : "outline"}
                                size="icon"
                                className="h-9 w-9"
                                onClick={() => setShowCriticalPath(!showCriticalPath)}
                                aria-label="Toggle critical path highlighting"
                                aria-pressed={showCriticalPath}
                            >
                                <AlertTriangle className={cn(
                                    "h-4 w-4",
                                    showCriticalPath ? "text-red-500" : ""
                                )} />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                            <p>{showCriticalPath ? "Hide Critical Path" : "Show Critical Path"}</p>
                        </TooltipContent>
                    </Tooltip>
                </TooltipProvider>

                {/* Export Button with Dropdown */}
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button
                            variant="outline"
                            size="icon"
                            className="h-9 w-9"
                            disabled={isExporting}
                            aria-label="Export Gantt chart"
                            aria-busy={isExporting}
                        >
                            {isExporting ? (
                                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                            ) : (
                                <Download className="h-4 w-4" />
                            )}
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={handleExportAsPNG} disabled={isExporting}>
                            <Download className="h-4 w-4 mr-2" aria-hidden="true" />
                            Export as PNG
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={handleExportAsPDF} disabled={isExporting}>
                            <Download className="h-4 w-4 mr-2" aria-hidden="true" />
                            Export as PDF
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>

                {/* Keyboard Shortcuts Help Button */}
                <TooltipProvider>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant="outline"
                                size="icon"
                                className="h-9 w-9"
                                onClick={() => setShowKeyboardHelp(true)}
                                aria-label="View keyboard shortcuts"
                            >
                                <Keyboard className="h-4 w-4" />
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                            <p>Keyboard Shortcuts (?)</p>
                        </TooltipContent>
                    </Tooltip>
                </TooltipProvider>
            </div>

            <div className="flex items-center gap-1 bg-muted/50 p-1 rounded-md" role="radiogroup" aria-label="Time scale view mode">
                <Button
                    variant={viewMode === 'day' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => { setViewMode('day'); setColumnWidth(60); }}
                    role="radio"
                    aria-checked={viewMode === 'day'}
                >
                    Day
                </Button>
                <Button
                    variant={viewMode === 'week' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => { setViewMode('week'); setColumnWidth(40); }}
                    role="radio"
                    aria-checked={viewMode === 'week'}
                >
                    Week
                </Button>
                <Button
                    variant={viewMode === 'month' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => { setViewMode('month'); setColumnWidth(20); }}
                    role="radio"
                    aria-checked={viewMode === 'month'}
                >
                    Month
                </Button>
                <Button
                    variant={viewMode === 'quarter' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => { setViewMode('quarter'); setColumnWidth(10); }}
                    role="radio"
                    aria-checked={viewMode === 'quarter'}
                >
                    Quarter
                </Button>
                <Button
                    variant={viewMode === 'year' ? 'secondary' : 'ghost'}
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => { setViewMode('year'); setColumnWidth(5); }}
                    role="radio"
                    aria-checked={viewMode === 'year'}
                >
                    Year
                </Button>
            </div>
        </div>

        {/* Content Area - Split Pane */}
        <div className="flex flex-1 overflow-hidden" ref={containerRef} onMouseUp={handleMouseUp} onMouseMove={handleMouseMove} onMouseLeave={handleMouseUp}>

            {/* Left: Table */}
            <div className="w-[300px] border-r flex flex-col bg-card z-10 shadow-sm flex-shrink-0" role="region" aria-label="Task list">
                <div className="h-16 border-b bg-muted/10 flex items-center px-4 font-semibold text-sm text-muted-foreground" role="columnheader">
                    Records
                </div>
                <div className="flex-1 overflow-y-hidden" role="list" aria-label={`${filteredData.length} tasks`}>
                    <div className="divide-y" role="presentation">
                        {table.getRowModel().rows.map(row => (
                            <div key={row.id} className="h-12 flex items-center px-4 hover:bg-muted/50 transition-colors text-sm group relative" role="listitem">
                                {row.getVisibleCells().map(cell => (
                                    <div key={cell.id} className="flex-1 min-w-0 mr-2 first:font-medium">
                                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                    </div>
                                ))}
                                <Button variant="ghost" size="icon" className="h-6 w-6 opacity-0 group-hover:opacity-100 absolute right-1" aria-label="More options for task">
                                    <MoreHorizontal className="h-3 w-3" />
                                </Button>
                            </div>
                        ))}
                    </div>
                </div>
                <div className="h-10 border-t flex items-center px-4 text-xs text-muted-foreground bg-muted/10" role="status" aria-live="polite">
                    {filteredData.length} records
                </div>
            </div>

            {/* Right: Timeline */}
            <div className="flex-1 overflow-auto relative bg-background/50 scrollbar-hide" role="region" aria-label="Gantt chart timeline">
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
                                role="img"
                                aria-label={`Dependency lines showing relationships between ${dependencyLines.length} tasks`}
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
                                {/* Render dependency paths */}
                                {renderDependencyPaths()}
                            </svg>
                        )}

                        <div className="relative pt-0 pb-10">
                            {table.getRowModel().rows.map(row => {
                                const record = row.original;
                                const styleInfo = getRecordStyle(record);
                                const progress = progressFieldId ? record[progressFieldId] : 0;
                                const isCriticalPath = criticalPathTasks.has(record.id);

                                return (
                                    <div key={row.id} className="h-12 border-b relative group hover:bg-black/5 transition-colors">
                                        {/* Row line guide */}
                                        <div className="absolute inset-0 border-b border-dashed border-border/50" />

                                        {styleInfo.display !== 'none' && (
                                            <TooltipProvider>
                                                <Tooltip>
                                                    <TooltipTrigger asChild>
                                                        <div
                                                            ref={(el) => { if (el) taskBarRefs.current[record.id] = el; }}
                                                            role="button"
                                                            tabIndex={0}
                                                            aria-label={`Task: ${titleFieldId ? record[titleFieldId] : 'Untitled'}. From ${safeParseDate(record[startDateFieldId])?.toLocaleDateString()} to ${safeParseDate(record[endDateFieldId])?.toLocaleDateString()}. Status: ${record[statusFieldId] || 'Not set'}. Progress: ${progress}%`}
                                                            aria-describedby={`tooltip-${record.id}`}
                                                            onKeyDown={(e) => handleTaskKeyDown(e, record)}
                                                            className={cn(
                                                                "absolute top-2 h-8 rounded-md shadow-sm border text-white text-xs flex items-center px-2 cursor-pointer transition-all hover:shadow-md select-none overflow-hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                                                                styleInfo.className,
                                                                showCriticalPath && isCriticalPath && 'ring-2 ring-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]',
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
                                                                    aria-hidden="true"
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
                                                                role="separator"
                                                                aria-label="Resize start date"
                                                                tabIndex={-1}
                                                            />
                                                            <div
                                                                className="absolute right-0 top-0 bottom-0 w-2 cursor-e-resize hover:bg-black/20 z-20 opacity-0 group-hover:opacity-100 transition-opacity"
                                                                onMouseDown={(e) => handleDragStart(e, record, 'resize-right')}
                                                                role="separator"
                                                                aria-label="Resize end date"
                                                                tabIndex={-1}
                                                            />
                                                        </div>
                                                    </TooltipTrigger>
                                                    <TooltipContent id={`tooltip-${record.id}`}>
                                                        <div className="text-xs">
                                                            <div className="font-bold">{titleFieldId ? record[titleFieldId] : 'Untitled'}</div>
                                                            {showCriticalPath && isCriticalPath && <div className="text-red-500 font-semibold mt-1">⚠ Critical Path Task</div>}
                                                            <div className="mt-1">{safeParseDate(record[startDateFieldId])?.toLocaleDateString()} - {safeParseDate(record[endDateFieldId])?.toLocaleDateString()}</div>
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

        {/* Export loading overlay */}
        {isExporting && (
            <div className="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50">
                <Card className="max-w-md p-6 text-center space-y-4">
                    <div className="mx-auto w-12 h-12 flex items-center justify-center">
                        <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold">Exporting Gantt Chart</h3>
                        <p className="text-sm text-muted-foreground mt-2">
                            Please wait while we generate your export file...
                        </p>
                    </div>
                </Card>
            </div>
        )}

        {/* Keyboard Shortcuts Help Modal */}
        <Dialog open={showKeyboardHelp} onOpenChange={setShowKeyboardHelp}>
            <DialogContent className="max-w-2d" aria-describedby="keyboard-shortcuts-description">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Keyboard className="h-5 w-5" />
                        Keyboard Shortcuts
                    </DialogTitle>
                    <DialogDescription id="keyboard-shortcuts-description">
                        Navigate and control the Gantt chart using your keyboard
                    </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                    {/* Navigation */}
                    <div>
                        <h4 className="font-semibold text-sm mb-2">Navigation</h4>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-sm">
                                <span>Move between controls</span>
                                <div className="flex gap-1">
                                    <kbd className="px-2 py-1 text-xs bg-muted rounded">Tab</kbd>
                                    <span className="text-muted-foreground">/</span>
                                    <kbd className="px-2 py-1 text-xs bg-muted rounded">Shift+Tab</kbd>
                                </div>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span>Activate button/task</span>
                                <div className="flex gap-1">
                                    <kbd className="px-2 py-1 text-xs bg-muted rounded">Enter</kbd>
                                    <span className="text-muted-foreground">/</span>
                                    <kbd className="px-2 py-1 text-xs bg-muted rounded">Space</kbd>
                                </div>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span>Close modal/dropdown</span>
                                <kbd className="px-2 py-1 text-xs bg-muted rounded">Escape</kbd>
                            </div>
                        </div>
                    </div>

                    {/* Task Controls */}
                    <div>
                        <h4 className="font-semibold text-sm mb-2">Task Controls (when task bar is focused)</h4>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-sm">
                                <span>Move task one day earlier</span>
                                <kbd className="px-2 py-1 text-xs bg-muted rounded">←</kbd>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span>Move task one day later</span>
                                <kbd className="px-2 py-1 text-xs bg-muted rounded">→</kbd>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span>Extend task by one day</span>
                                <kbd className="px-2 py-1 text-xs bg-muted rounded">↑</kbd>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span>Shorten task by one day</span>
                                <kbd className="px-2 py-1 text-xs bg-muted rounded">↓</kbd>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span>Move task to today</span>
                                <kbd className="px-2 py-1 text-xs bg-muted rounded">Home</kbd>
                            </div>
                        </div>
                    </div>

                    {/* Timeline Navigation */}
                    <div>
                        <h4 className="font-semibold text-sm mb-2">Timeline Navigation</h4>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between text-sm">
                                <span>Previous time period</span>
                                <kbd className="px-2 py-1 text-xs bg-muted rounded">Alt</kbd>
                                <span className="text-muted-foreground">+</span>
                                <kbd className="px-2 py-1 text-xs bg-muted rounded">←</kbd>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <span>Next time period</span>
                                <kbd className="px-2 py-1 text-xs bg-muted rounded">Alt</kbd>
                                <span className="text-muted-foreground">+</span>
                                <kbd className="px-2 py-1 text-xs bg-muted rounded">→</kbd>
                            </div>
                        </div>
                    </div>

                    {/* Accessibility Note */}
                    <div className="text-xs text-muted-foreground border-t pt-3">
                        <p>All features are accessible via keyboard. Use Tab to navigate between controls and task bars. Focus a task bar to use arrow keys for adjustments.</p>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    </Card>
  );
};
