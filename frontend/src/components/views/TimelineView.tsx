import React, { useState, useMemo, useEffect } from 'react';
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
  startOfQuarter,
  endOfQuarter,
  addQuarters,
  subQuarters,
  startOfYear,
  endOfYear,
  addYears,
  subYears,
  eachMonthOfInterval,
  eachQuarterOfInterval,
  eachYearOfInterval,
  isValid,
} from 'date-fns';
import { Search, Filter, Calendar as CalendarIcon, ChevronLeft, ChevronRight, X, AlertCircle } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from '@/lib/utils';

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

interface TimelineViewProps {
  data: Record[];
  fields: Field[];
  onCellUpdate?: (rowId: string, fieldId: string, value: unknown) => void;
}

type ZoomLevel = 'day' | 'week' | 'month' | 'quarter' | 'year';

interface GroupedRow {
  groupKey: string;
  groupTitle: string;
  records: Record[];
}

// Helper to safely parse dates
const safeParseDate = (date: any): Date | null => {
  if (!date) return null;
  const parsed = new Date(date);
  return isValid(parsed) ? parsed : null;
};

export const TimelineView: React.FC<TimelineViewProps> = ({ data, fields }) => {
  // --- State ---
  const [zoomLevel, setZoomLevel] = useState<ZoomLevel>('month');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [columnWidth, setColumnWidth] = useState(50); // px per time unit
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRecord, setSelectedRecord] = useState<Record | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['all']));

  // Field mapping state
  const [dateFieldId, setDateFieldId] = useState<string>('');
  const [titleFieldId, setTitleFieldId] = useState<string>('');
  const [statusFieldId, setStatusFieldId] = useState<string>('');
  const [groupFieldId, setGroupFieldId] = useState<string>('');

  // --- Initialization ---
  useEffect(() => {
    // Auto-detect fields
    if (fields.length > 0) {
      const dateField = fields.find(f => f.type === 'date');
      if (dateField) setDateFieldId(dateField.name);

      const textField = fields.find(f => f.type === 'text' || f.type === 'long_text' || f.name === 'Name' || f.name === 'Title');
      if (textField) setTitleFieldId(textField.name);
      else if (fields[0]) setTitleFieldId(fields[0].name);

      const statusField = fields.find(f => f.type === 'select' || f.type === 'singleSelect' || f.name.toLowerCase().includes('status'));
      if (statusField) {
        setStatusFieldId(statusField.name);
        // Default to status field for grouping if available
        setGroupFieldId(statusField.name);
      }
    }
  }, [fields]);

  // --- Derived Data ---

  // Filter data based on search and date validity
  const filteredData = useMemo(() => {
    return data.filter(record => {
      // Filter by date field existence and validity
      const dateVal = record[dateFieldId];
      const date = safeParseDate(dateVal);
      if (!date) return false;

      // Search filter
      if (searchQuery) {
        const title = record[titleFieldId]?.toString().toLowerCase() || '';
        if (!title.includes(searchQuery.toLowerCase())) return false;
      }

      return true;
    });
  }, [data, dateFieldId, titleFieldId, searchQuery]);

  // Group data by the configured group field
  const groupedRows = useMemo(() => {
    if (!groupFieldId) {
      return [{ groupKey: 'all', groupTitle: 'All Records', records: filteredData }];
    }

    const groups: Map<string, GroupedRow> = new Map();

    filteredData.forEach(record => {
      const groupValue = record[groupFieldId];
      const groupKey = groupValue?.toString() || 'Uncategorized';
      const groupTitle = groupValue?.toString() || 'Uncategorized';

      if (!groups.has(groupKey)) {
        groups.set(groupKey, { groupKey, groupTitle, records: [] });
      }
      groups.get(groupKey)!.records.push(record);
    });

    return Array.from(groups.values());
  }, [filteredData, groupFieldId]);

  // Calculate visible date range based on zoom level
  const { startDate, endDate, timeUnits } = useMemo(() => {
    let start, end;

    if (zoomLevel === 'day') {
      start = subDays(currentDate, 10);
      end = addDays(currentDate, 20);
    } else if (zoomLevel === 'week') {
      start = startOfWeek(subDays(currentDate, 30));
      end = endOfWeek(addDays(currentDate, 60));
    } else if (zoomLevel === 'month') {
      start = startOfMonth(subMonths(currentDate, 2));
      end = endOfMonth(addMonths(currentDate, 4));
    } else if (zoomLevel === 'quarter') {
      start = startOfQuarter(subQuarters(currentDate, 2));
      end = endOfQuarter(addQuarters(currentDate, 2));
    } else { // year
      start = startOfYear(subYears(currentDate, 2));
      end = endOfYear(addYears(currentDate, 2));
    }

    let units: Date[] = [];
    if (zoomLevel === 'day' || zoomLevel === 'week') {
      units = eachDayOfInterval({ start, end });
    } else if (zoomLevel === 'month') {
      units = eachMonthOfInterval({ start, end });
    } else if (zoomLevel === 'quarter') {
      units = eachQuarterOfInterval({ start, end });
    } else { // year
      units = eachYearOfInterval({ start, end });
    }

    return { startDate: start, endDate: end, timeUnits: units };
  }, [currentDate, zoomLevel]);

  // --- Timeline Helpers ---

  // Calculate horizontal position for a date based on zoom level
  const getPositionForDate = (date: Date): number => {
    if (zoomLevel === 'day' || zoomLevel === 'week') {
      // For day/week zoom: position based on exact day difference
      const daysDiff = differenceInDays(date, startDate);
      return daysDiff * columnWidth;
    } else if (zoomLevel === 'month') {
      // For month zoom: position based on day difference, displayed as months
      const daysDiff = differenceInDays(date, startDate);
      return (daysDiff / 30) * columnWidth;
    } else if (zoomLevel === 'quarter') {
      // For quarter zoom: position based on day difference, displayed as quarters
      const daysDiff = differenceInDays(date, startDate);
      return (daysDiff / 91) * columnWidth;
    } else {
      // For year zoom: position based on day difference, displayed as years
      const daysDiff = differenceInDays(date, startDate);
      return (daysDiff / 365) * columnWidth;
    }
  };

  const getPointColor = (record: Record) => {
    if (!statusFieldId) return 'bg-primary';

    const status = record[statusFieldId];
    if (status === 'Done' || status === 'Completed' || status === 'Complete') return 'bg-green-500';
    if (status === 'In Progress' || status === 'Active') return 'bg-blue-500';
    if (status === 'Blocked' || status === 'On Hold') return 'bg-red-500';
    if (status === 'To Do' || status === 'Todo') return 'bg-slate-400';

    return 'bg-primary';
  };

  const toggleGroup = (groupKey: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(groupKey)) {
      newExpanded.delete(groupKey);
    } else {
      newExpanded.add(groupKey);
    }
    setExpandedGroups(newExpanded);
  };


  // --- Render Helpers ---

  const renderTimeHeader = () => {
    const totalWidth = timeUnits.length * columnWidth;

    if (zoomLevel === 'day' || zoomLevel === 'week') {
      // Month row
      const months = [];
      let mDate = startDate;
      while (mDate <= endDate) {
        const nextMonth = startOfMonth(addMonths(mDate, 1));
        const limitDate = nextMonth > endDate ? endDate : nextMonth;
        const firstDayOfSegment = mDate < startDate ? startDate : mDate;
        const width = differenceInDays(limitDate, firstDayOfSegment) * columnWidth;

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

      // Days row
      const dayCells = timeUnits.map((day) => {
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
            {zoomLevel === 'week' ? format(day, 'EEE d') : format(day, 'd')}
          </div>
        );
      });

      return (
        <div className="flex flex-col" style={{ minWidth: `${totalWidth}px` }}>
          <div className="flex flex-row">{months}</div>
          <div className="flex flex-row border-b">{dayCells}</div>
        </div>
      );
    } else if (zoomLevel === 'month') {
      // Quarter row
      const quarters = [];
      let qDate = startDate;
      while (qDate <= endDate) {
        const nextQuarter = startOfQuarter(addQuarters(qDate, 1));
        const limitDate = nextQuarter > endDate ? endDate : nextQuarter;
        const firstDayOfSegment = qDate < startDate ? startDate : qDate;
        const daysInSegment = differenceInDays(limitDate, firstDayOfSegment);
        const width = (daysInSegment / 30) * columnWidth;

        if (width > 0) {
          const q = Math.floor((qDate.getMonth() + 3) / 3);
          quarters.push(
            <div
              key={`quarter-${qDate.toISOString()}`}
              className="h-8 border-b border-r flex items-center px-2 text-sm font-semibold sticky top-0 bg-background/95 backdrop-blur z-20 text-muted-foreground"
              style={{ width: `${width}px` }}
            >
              Q{q} {format(qDate, 'yyyy')}
            </div>
          );
        }
        qDate = nextQuarter;
      }

      // Months row
      const monthCells = timeUnits.map((month) => {
        const isCurrentMonth = isSameDay(month, startOfMonth(new Date()));

        return (
          <div
            key={month.toISOString()}
            className={cn(
              "h-8 border-r flex items-center justify-center text-xs flex-shrink-0 select-none",
              isCurrentMonth ? "bg-primary/5 font-bold text-primary" : "text-muted-foreground"
            )}
            style={{ width: `${columnWidth}px` }}
          >
            {format(month, 'MMM')}
          </div>
        );
      });

      return (
        <div className="flex flex-col" style={{ minWidth: `${totalWidth}px` }}>
          <div className="flex flex-row">{quarters}</div>
          <div className="flex flex-row border-b">{monthCells}</div>
        </div>
      );
    } else if (zoomLevel === 'quarter') {
      // Year row
      const years = [];
      let yDate = startDate;
      while (yDate <= endDate) {
        const nextYear = startOfYear(addYears(yDate, 1));
        const limitDate = nextYear > endDate ? endDate : nextYear;
        const firstDayOfSegment = yDate < startDate ? startDate : yDate;
        const daysInSegment = differenceInDays(limitDate, firstDayOfSegment);
        const width = (daysInSegment / 91) * columnWidth;

        if (width > 0) {
          years.push(
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

      // Quarters row
      const quarterCells = timeUnits.map((quarter) => {
        const q = Math.floor((quarter.getMonth() + 3) / 3);

        return (
          <div
            key={quarter.toISOString()}
            className="h-8 border-r flex items-center justify-center text-xs flex-shrink-0 select-none text-muted-foreground"
            style={{ width: `${columnWidth}px` }}
          >
            Q{q}
          </div>
        );
      });

      return (
        <div className="flex flex-col" style={{ minWidth: `${totalWidth}px` }}>
          <div className="flex flex-row">{years}</div>
          <div className="flex flex-row border-b">{quarterCells}</div>
        </div>
      );
    } else { // year
      // Years row
      const yearCells = timeUnits.map((year) => {
        const isCurrentYear = isSameDay(year, startOfYear(new Date()));

        return (
          <div
            key={year.toISOString()}
            className={cn(
              "h-8 border-r flex items-center justify-center text-xs flex-shrink-0 select-none",
              isCurrentYear ? "bg-primary/5 font-bold text-primary" : "text-muted-foreground"
            )}
            style={{ width: `${columnWidth}px` }}
          >
            {format(year, 'yyyy')}
          </div>
        );
      });

      return (
        <div className="flex flex-col" style={{ minWidth: `${totalWidth}px` }}>
          <div className="flex flex-row border-b">{yearCells}</div>
        </div>
      );
    }
  };

  const renderGridBackground = () => {
    const totalWidth = timeUnits.length * columnWidth;

    return (
      <div
        className="absolute inset-0 flex pointer-events-none h-full"
        style={{ minWidth: `${totalWidth}px` }}
      >
        {timeUnits.map((unit) => {
          const isWeekend = zoomLevel === 'day' || zoomLevel === 'week' ? (unit.getDay() === 0 || unit.getDay() === 6) : false;
          const isToday = isSameDay(unit, new Date());

          return (
            <div
              key={`grid-${unit.toISOString()}`}
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

  if (!dateFieldId) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-muted-foreground bg-muted/10 rounded-lg border-2 border-dashed border-muted m-4">
        <AlertCircle className="w-12 h-12 mb-4 opacity-50" />
        <h3 className="text-lg font-semibold">No Date Field Found</h3>
        <p>Please add a Date field to your table to use the Timeline View.</p>
      </div>
    );
  }

  return (
    <Card className="flex flex-col h-full border-0 shadow-none rounded-none bg-background">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-2 border-b gap-2 bg-card flex-wrap">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => {
            if (zoomLevel === 'day') setCurrentDate(subDays(currentDate, 7));
            else if (zoomLevel === 'week') setCurrentDate(subDays(currentDate, 30));
            else if (zoomLevel === 'month') setCurrentDate(subMonths(currentDate, 2));
            else if (zoomLevel === 'quarter') setCurrentDate(subQuarters(currentDate, 1));
            else setCurrentDate(subYears(currentDate, 1));
          }}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="flex items-center gap-2 px-2 font-medium min-w-[140px] justify-center">
            <CalendarIcon className="h-4 w-4 text-muted-foreground" />
            {format(currentDate, zoomLevel === 'day' || zoomLevel === 'week' ? 'MMMM yyyy' : 'yyyy')}
          </div>
          <Button variant="outline" size="icon" onClick={() => {
            if (zoomLevel === 'day') setCurrentDate(addDays(currentDate, 7));
            else if (zoomLevel === 'week') setCurrentDate(addDays(currentDate, 30));
            else if (zoomLevel === 'month') setCurrentDate(addMonths(currentDate, 2));
            else if (zoomLevel === 'quarter') setCurrentDate(addQuarters(currentDate, 1));
            else setCurrentDate(addYears(currentDate, 1));
          }}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setCurrentDate(new Date())}>Today</Button>
        </div>

        <div className="flex items-center gap-2 flex-1 justify-center">
          <div className="relative w-64">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search timeline..."
              className="pl-8 h-9"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Group By Selector */}
          {groupFieldId && (
            <Select value={groupFieldId} onValueChange={setGroupFieldId}>
              <SelectTrigger className="w-[150px] h-9">
                <Filter className="w-3 h-3 mr-2" />
                <SelectValue placeholder="Group By" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">No Grouping</SelectItem>
                {fields.filter(f => f.type === 'select' || f.type === 'singleSelect' || f.type === 'multi_select').map(field => (
                  <SelectItem key={field.id} value={field.name}>{field.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>

        <div className="flex items-center gap-1 bg-muted/50 p-1 rounded-md">
          {(['day', 'week', 'month', 'quarter', 'year'] as ZoomLevel[]).map((level) => (
            <Button
              key={level}
              variant={zoomLevel === level ? 'secondary' : 'ghost'}
              size="sm"
              className="h-7 text-xs capitalize"
              onClick={() => {
                setZoomLevel(level);
                if (level === 'day') setColumnWidth(60);
                else if (level === 'week') setColumnWidth(40);
                else if (level === 'month') setColumnWidth(50);
                else if (level === 'quarter') setColumnWidth(80);
                else setColumnWidth(100);
              }}
            >
              {level}
            </Button>
          ))}
        </div>
      </div>

      {/* Content Area - Split Pane */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Group Panel */}
        <div className="w-[300px] border-r flex flex-col bg-card z-10 shadow-sm flex-shrink-0">
          <div className="h-16 border-b bg-muted/10 flex items-center px-4 font-semibold text-sm text-muted-foreground">
            Groups
          </div>
          <div className="flex-1 overflow-y-auto">
            <div className="divide-y">
              {groupedRows.map((group) => (
                <div
                  key={group.groupKey}
                  className="flex items-center px-4 py-3 hover:bg-muted/50 transition-colors text-sm group cursor-pointer"
                  onClick={() => toggleGroup(group.groupKey)}
                >
                  <ChevronRight
                    className={cn(
                      "w-4 h-4 mr-2 transition-transform duration-200 flex-shrink-0",
                      expandedGroups.has(group.groupKey) ? "rotate-90" : ""
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{group.groupTitle}</div>
                    <div className="text-xs text-muted-foreground">{group.records.length} records</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="h-10 border-t flex items-center px-4 text-xs text-muted-foreground bg-muted/10">
            {groupedRows.length} groups
          </div>
        </div>

        {/* Right: Timeline */}
        <div className="flex-1 overflow-x-auto overflow-y-auto relative bg-background/50 scroll-smooth">
          <div className="min-w-max">
            {/* Header */}
            {renderTimeHeader()}

            {/* Grid & Rows */}
            <div className="relative" style={{ minWidth: `${timeUnits.length * columnWidth}px` }}>
              {renderGridBackground()}

              <div className="relative pt-0 pb-10">
                {groupedRows.map((group) => (
                  <div key={group.groupKey}>
                    {/* Group Row Header */}
                    <div
                      className="h-10 border-b bg-muted/30 flex items-center px-4 font-medium text-sm sticky left-0 z-10 cursor-pointer hover:bg-muted/50 transition-colors"
                      onClick={() => toggleGroup(group.groupKey)}
                    >
                      <ChevronRight
                        className={cn(
                          "w-4 h-4 mr-2 transition-transform duration-200 flex-shrink-0",
                          expandedGroups.has(group.groupKey) ? "rotate-90" : ""
                        )}
                      />
                      {group.groupTitle}
                      <Badge variant="secondary" className="ml-2 text-xs">
                        {group.records.length}
                      </Badge>
                    </div>

                    {/* Group Records - Horizontal Swimlane */}
                    {expandedGroups.has(group.groupKey) && (
                      <div className="relative h-20 border-b border-border/50 bg-muted/5 hover:bg-muted/10 transition-colors">
                        {/* Timeline track */}
                        <div className="absolute inset-0 flex items-center">
                          {/* Record markers positioned horizontally */}
                          {group.records.map((record) => {
                            const recordDate = safeParseDate(record[dateFieldId]);
                            if (!recordDate) return null;

                            const position = getPositionForDate(recordDate);
                            const pointColor = getPointColor(record);
                            const isOutsideRange = recordDate < startDate || recordDate > endDate;

                            if (isOutsideRange) return null;

                            return (
                              <TooltipProvider key={record.id}>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <div
                                      className={cn(
                                        "absolute w-4 h-4 rounded-full border-2 border-background shadow-sm cursor-pointer transition-all hover:scale-150 hover:shadow-md z-10",
                                        pointColor
                                      )}
                                      style={{ left: `${position}px` }}
                                      onClick={() => setSelectedRecord(record)}
                                    />
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <div className="text-xs">
                                      <div className="font-bold">{record[titleFieldId] || 'Untitled'}</div>
                                      <div>{format(recordDate, 'PPP')}</div>
                                      {statusFieldId && record[statusFieldId] && (
                                        <div>Status: {record[statusFieldId]}</div>
                                      )}
                                    </div>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Details Overlay */}
      {selectedRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-lg bg-card border rounded-xl shadow-2xl animate-in zoom-in-95 duration-200 overflow-hidden flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="text-xl font-bold truncate pr-8">
                {selectedRecord[titleFieldId] || 'Record Details'}
              </h2>
              <Button
                variant="ghost"
                size="icon"
                className="absolute right-4 top-4 rounded-full"
                onClick={() => setSelectedRecord(null)}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              {fields.map(field => {
                const value = selectedRecord[field.name];
                if (value === null || value === undefined || value === '') return null;

                return (
                  <div key={field.name} className="space-y-1">
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      {field.name}
                    </label>
                    <div className="text-sm p-2 bg-muted/30 rounded-md border border-transparent hover:border-border transition-colors">
                      {field.type === 'date' ? format(new Date(value), 'PPP p') :
                        typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="p-4 border-t bg-muted/10 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setSelectedRecord(null)}>Close</Button>
              <Button onClick={() => { /* Edit logic would go here */ }}>Edit</Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};
