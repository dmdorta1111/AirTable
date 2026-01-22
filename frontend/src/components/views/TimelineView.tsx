import React, { useState, useMemo } from 'react';
import { format, isValid, getYear, getQuarter, startOfMonth, startOfQuarter, startOfYear } from 'date-fns';
import { Search, Filter, Calendar as CalendarIcon, ChevronRight, X, Clock, AlertCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/components/ui/button'; // Importing cn from button as per codebase pattern

interface TimelineViewProps {
  data: any[];
  fields: any[];
}

type ZoomLevel = 'month' | 'quarter' | 'year';

interface GroupedData {
  title: string;
  date: Date;
  records: any[];
}

export const TimelineView: React.FC<TimelineViewProps> = ({ data, fields }) => {
  const [zoomLevel, setZoomLevel] = useState<ZoomLevel>('month');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRecord, setSelectedRecord] = useState<any | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  // Identify key fields
  const dateField = useMemo(() => fields.find(f => f.type === 'date'), [fields]);
  const titleField = useMemo(() => fields.find(f => f.type === 'text' || f.name === 'Name' || f.name === 'Title') || fields[0], [fields]);
  const statusField = useMemo(() => fields.find(f => f.type === 'select' || f.name === 'Status'), [fields]);
  const tagsField = useMemo(() => fields.find(f => f.type === 'multi_select' || f.name === 'Tags'), [fields]);

  // Filter and Sort Data
  const processedData = useMemo(() => {
    if (!dateField) return [];

    let filtered = data.filter(item => {
      const dateVal = item[dateField.name];
      if (!dateVal) return false;
      const date = new Date(dateVal);
      if (!isValid(date)) return false;

      if (searchQuery) {
        const searchLower = searchQuery.toLowerCase();
        const titleMatch = String(item[titleField?.name] || '').toLowerCase().includes(searchLower);
        // Can add more fields to search here
        return titleMatch;
      }
      return true;
    });

    // Sort chronologically
    return filtered.sort((a, b) => {
      const dateA = new Date(a[dateField.name]);
      const dateB = new Date(b[dateField.name]);
      return dateA.getTime() - dateB.getTime();
    });
  }, [data, dateField, searchQuery, titleField]);

  // Group Data based on Zoom Level
  const groupedData = useMemo(() => {
    if (!dateField) return [];

    const groups: Map<string, GroupedData> = new Map();

    processedData.forEach(item => {
      const date = new Date(item[dateField.name]);
      let groupKey = '';
      let groupTitle = '';
      let groupDate: Date;

      if (zoomLevel === 'month') {
        groupKey = format(date, 'yyyy-MM');
        groupTitle = format(date, 'MMMM yyyy');
        groupDate = startOfMonth(date);
      } else if (zoomLevel === 'quarter') {
        const q = getQuarter(date);
        const y = getYear(date);
        groupKey = `${y}-Q${q}`;
        groupTitle = `Q${q} ${y}`;
        groupDate = startOfQuarter(date);
      } else { // year
        const y = getYear(date);
        groupKey = `${y}`;
        groupTitle = `${y}`;
        groupDate = startOfYear(date);
      }

      if (!groups.has(groupKey)) {
        groups.set(groupKey, { title: groupTitle, date: groupDate, records: [] });
      }
      groups.get(groupKey)?.records.push(item);
    });

    return Array.from(groups.values()).sort((a, b) => a.date.getTime() - b.date.getTime());
  }, [processedData, zoomLevel, dateField]);

  // Toggle group expansion
  const toggleGroup = (title: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(title)) {
      newExpanded.delete(title);
    } else {
      newExpanded.add(title);
    }
    setExpandedGroups(newExpanded);
  };

  // Initialize all groups as expanded on load
  React.useEffect(() => {
    if (groupedData.length > 0 && expandedGroups.size === 0) {
      setExpandedGroups(new Set(groupedData.map(g => g.title)));
    }
  }, [groupedData.length]);


  if (!dateField) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-muted-foreground bg-muted/10 rounded-lg border-2 border-dashed border-muted m-4">
        <AlertCircle className="w-12 h-12 mb-4 opacity-50" />
        <h3 className="text-lg font-semibold">No Date Field Found</h3>
        <p>Please add a Date field to your table to use the Timeline View.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-background/50 relative">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-4 p-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-20">
        <div className="flex-1 relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input 
            placeholder="Search timeline..." 
            className="pl-8" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        
        <div className="flex gap-2">
           <Select value={zoomLevel} onValueChange={(v: ZoomLevel) => setZoomLevel(v)}>
            <SelectTrigger className="w-[140px]">
              <CalendarIcon className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Zoom" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="month">Month</SelectItem>
              <SelectItem value="quarter">Quarter</SelectItem>
              <SelectItem value="year">Year</SelectItem>
            </SelectContent>
          </Select>
          
          <Button variant="outline" size="icon">
            <Filter className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Timeline Container */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-8 relative">
        {/* Main Vertical Line */}
        <div className="absolute left-[27px] sm:left-[118px] top-0 bottom-0 w-px bg-border z-0" />

        {groupedData.length === 0 ? (
           <div className="text-center py-20 text-muted-foreground">
             No records found within this range.
           </div>
        ) : (
          <div className="space-y-8 relative z-10">
            {groupedData.map((group) => (
              <div key={group.title} className="group-section">
                {/* Group Header */}
                <div 
                  className="flex items-center gap-4 mb-6 cursor-pointer hover:opacity-80 transition-opacity sticky top-0 z-10 py-2 bg-background/95"
                  onClick={() => toggleGroup(group.title)}
                >
                  <div className="w-[16px] sm:w-[100px] flex justify-end">
                     <div className={cn(
                       "flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary transition-transform duration-200",
                       expandedGroups.has(group.title) ? "rotate-90" : ""
                     )}>
                        <ChevronRight className="w-4 h-4" />
                     </div>
                  </div>
                  <h3 className="text-lg font-bold text-foreground tracking-tight">{group.title}</h3>
                  <Badge variant="secondary" className="text-xs font-normal">
                    {group.records.length}
                  </Badge>
                </div>

                {/* Records in Group */}
                {expandedGroups.has(group.title) && (
                  <div className="space-y-6">
                    {group.records.map((record, idx) => {
                      const recordDate = new Date(record[dateField.name]);
                      const dateStr = format(recordDate, 'MMM d');
                      const dayStr = format(recordDate, 'EEE');
                      const status = statusField ? record[statusField.name] : null;
                      
                      return (
                        <div key={idx} className="flex gap-4 sm:gap-8 group record-item animate-in fade-in slide-in-from-bottom-4 duration-500 fill-mode-both" style={{ animationDelay: `${idx * 50}ms` }}>
                          
                          {/* Date Label (Left Axis) */}
                          <div className="hidden sm:flex flex-col items-end w-[100px] pt-4 text-right">
                            <span className="text-sm font-bold text-foreground">{dateStr}</span>
                            <span className="text-xs text-muted-foreground uppercase tracking-wider">{dayStr}</span>
                          </div>

                          {/* Timeline Node */}
                          <div className="relative flex flex-col items-center">
                             <div className={cn(
                               "w-3.5 h-3.5 rounded-full border-2 border-background z-10 mt-5 transition-all duration-300 group-hover:scale-125 group-hover:shadow-[0_0_10px_rgba(var(--primary),0.5)]",
                               status === 'Done' || status === 'Completed' ? "bg-green-500" : 
                               status === 'In Progress' ? "bg-blue-500" : 
                               "bg-primary"
                             )} />
                          </div>

                          {/* Card Content */}
                          <div className="flex-1 pb-2 min-w-0">
                            <Card 
                              className="hover:shadow-lg transition-all duration-300 cursor-pointer border-muted-foreground/10 hover:border-primary/30 group-hover:-translate-y-1"
                              onClick={() => setSelectedRecord(record)}
                            >
                              <CardContent className="p-4 flex items-start justify-between gap-4">
                                <div className="space-y-1 min-w-0">
                                   {/* Mobile Date */}
                                   <div className="sm:hidden flex items-center gap-2 text-xs text-muted-foreground mb-1">
                                      <Clock className="w-3 h-3" />
                                      <span>{dateStr}, {dayStr}</span>
                                   </div>
                                   
                                   <h4 className="font-semibold text-base leading-none truncate">
                                     {record[titleField?.name] || 'Untitled Record'}
                                   </h4>
                                   
                                   {/* Tags/Badges */}
                                   {(tagsField && record[tagsField.name]) && (
                                     <div className="flex flex-wrap gap-1 pt-2">
                                       {Array.isArray(record[tagsField.name]) ? record[tagsField.name].map((tag: any, i: number) => (
                                          <Badge key={i} variant="outline" className="text-[10px] h-5 px-1.5 bg-secondary/50 border-transparent">
                                            {typeof tag === 'object' ? tag.name : tag}
                                          </Badge>
                                       )) : (
                                          <Badge variant="outline" className="text-[10px] h-5 px-1.5 bg-secondary/50 border-transparent">
                                            {String(record[tagsField.name])}
                                          </Badge>
                                       )}
                                     </div>
                                   )}
                                </div>

                                {status && (
                                  <Badge className={cn(
                                    "shrink-0",
                                    status === 'Done' ? "bg-green-500/15 text-green-700 dark:text-green-400 hover:bg-green-500/25" :
                                    status === 'In Progress' ? "bg-blue-500/15 text-blue-700 dark:text-blue-400 hover:bg-blue-500/25" :
                                    "bg-secondary text-secondary-foreground"
                                  )}>
                                    {typeof status === 'object' ? status.name : status}
                                  </Badge>
                                )}
                              </CardContent>
                            </Card>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Details Overlay (Simple Modal) */}
      {selectedRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-lg bg-card border rounded-xl shadow-2xl animate-in zoom-in-95 duration-200 overflow-hidden flex flex-col max-h-[90vh]">
            <div className="flex items-center justify-between p-6 border-b">
              <h2 className="text-xl font-bold truncate pr-8">
                {selectedRecord[titleField?.name] || 'Record Details'}
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
    </div>
  );
};
