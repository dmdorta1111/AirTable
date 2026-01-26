import React, { useMemo, useState, useEffect, useRef } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  ColumnDef,
} from '@tanstack/react-table';
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Plus, Image as ImageIcon, MoreHorizontal, Settings, Loader2 } from 'lucide-react';

// Types (mirrored from GridView for consistency)
interface RecordData {
  id: string;
  table_id: string;
  data: Record<string, any>; // Relaxed type for flexibility
  row_height: number;
  created_at: string;
  updated_at: string;
  created_by_id: string;
  last_modified_by_id: string;
}

interface Field {
  id: string;
  name: string;
  type: string;
  options?: {
    choices?: string[];
    [key: string]: unknown;
  };
}

interface GalleryViewProps {
  data: RecordData[];
  fields: Field[];
  onRowAdd?: () => void;
  onRecordClick?: (recordId: string) => void;
  isLoading?: boolean;
  onLoadMore?: () => void;
  hasMore?: boolean;
  pageSize?: number;
}

type CardSize = 'small' | 'medium' | 'large';

const CARD_SIZE_CONFIG = {
  small: {
    gridCols: 'grid-cols-1 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6',
    imageHeight: 'h-32',
    minHeight: 'min-h-[160px]'
  },
  medium: {
    gridCols: 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5',
    imageHeight: 'h-48',
    minHeight: 'min-h-[200px]'
  },
  large: {
    gridCols: 'grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4',
    imageHeight: 'h-64',
    minHeight: 'min-h-[240px]'
  }
};

// Helper to render cell content (simplified read-only version)
const renderFieldValue = (value: any, type: string) => {
  if (value === null || value === undefined || value === '') return null;

  switch (type) {
    case 'checkbox':
      return <input type="checkbox" checked={!!value} readOnly className="pointer-events-none h-4 w-4" />;
    case 'attachment':
      return <span className="text-xs text-muted-foreground">{Array.isArray(value) ? `${value.length} files` : '0 files'}</span>;
    case 'link':
      return <span className="text-xs text-blue-500">{Array.isArray(value) ? `${value.length} linked` : 'Linked'}</span>;
    case 'select':
      return <span className="px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground text-xs font-medium">{String(value)}</span>;
    case 'date':
      return <span className="text-xs text-muted-foreground">{String(value)}</span>;
    case 'number':
      return <span className="text-sm font-mono">{String(value)}</span>;
    default:
      return <span className="text-sm line-clamp-2">{String(value)}</span>;
  }
};

export const GalleryView: React.FC<GalleryViewProps> = ({
  data,
  fields,
  onRowAdd,
  onRecordClick,
  isLoading = false,
  onLoadMore,
  hasMore = false,
  pageSize = 20
}) => {
  // State for progressive loading
  const [visibleCount, setVisibleCount] = useState(pageSize);
  const loadTriggerRef = useRef<HTMLDivElement>(null);

  // Settings state
  const [selectedCoverFieldId, setSelectedCoverFieldId] = useState<string | null>(null);
  const [cardSize, setCardSize] = useState<CardSize>('medium');
  const [settingsOpen, setSettingsOpen] = useState(false);

  // Identify the first attachment field to use as the cover image (default)
  const defaultCoverField = useMemo(() => fields.find(f => f.type === 'attachment'), [fields]);

  // Use selected cover field or default
  const coverField = useMemo(() => {
    if (selectedCoverFieldId) {
      return fields.find(f => f.id === selectedCoverFieldId) || defaultCoverField;
    }
    return defaultCoverField;
  }, [selectedCoverFieldId, fields, defaultCoverField]);

  // Identify the primary field (usually the first one) for the card title
  const primaryField = fields[0];

  // Other fields to display in the body (limit to 4 to prevent overcrowding)
  const displayFields = useMemo(() =>
    fields.filter(f => f.id !== coverField?.id && f.id !== primaryField?.id).slice(0, 4),
    [fields, coverField, primaryField]);

  // Get card size configuration
  const sizeConfig = CARD_SIZE_CONFIG[cardSize];

  const columns = useMemo<ColumnDef<RecordData>[]>(() => {
    return fields.map((field) => ({
      accessorKey: field.name,
      id: field.id || field.name,
      header: field.name,
    }));
  }, [fields]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  // Reset visible count when data changes
  useEffect(() => {
    setVisibleCount(pageSize);
  }, [data.length, pageSize]);

  // Intersection Observer for infinite scroll
  useEffect(() => {
    const loadTrigger = loadTriggerRef.current;
    if (!loadTrigger || !onLoadMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting && hasMore && !isLoading) {
          onLoadMore();
        }
      },
      {
        root: null,
        rootMargin: '200px',
        threshold: 0.1,
      }
    );

    observer.observe(loadTrigger);

    return () => {
      observer.unobserve(loadTrigger);
    };
  }, [onLoadMore, hasMore, isLoading]);

  // Get visible rows for rendering
  const visibleRows = useMemo(() => {
    return table.getRowModel().rows.slice(0, visibleCount);
  }, [table, visibleCount]);

  if (isLoading && data.length === 0) {
    return (
      <div className={`grid ${sizeConfig.gridCols} gap-6 p-4`}>
        {[...Array(8)].map((_, i) => (
          <div key={i} className="rounded-lg border bg-card text-card-foreground shadow-sm h-64 animate-pulse flex flex-col">
            <div className={`${sizeConfig.imageHeight} bg-muted w-full rounded-t-lg`} />
            <div className="p-4 space-y-3">
              <div className="h-4 bg-muted w-3/4 rounded" />
              <div className="h-3 bg-muted w-1/2 rounded" />
              <div className="h-3 bg-muted w-full rounded" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!isLoading && data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] text-muted-foreground space-y-4">
        <div className="p-4 bg-muted/30 rounded-full">
            <ImageIcon className="w-12 h-12 opacity-20" />
        </div>
        <p>No records found</p>
        {onRowAdd && (
          <Button variant="outline" onClick={onRowAdd} className="gap-2">
            <Plus className="w-4 h-4" />
            Create Record
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col">
      {/* Settings Bar */}
      <div className="flex items-center justify-end p-2 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <Popover open={settingsOpen} onOpenChange={setSettingsOpen}>
          <PopoverTrigger asChild>
            <Button variant="ghost" size="sm" className="gap-2">
              <Settings className="w-4 h-4" />
              View Settings
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-80" align="end">
            <div className="space-y-4">
              <div className="space-y-2">
                <h4 className="font-medium leading-none">Gallery Settings</h4>
                <p className="text-sm text-muted-foreground">
                  Customize how cards are displayed
                </p>
              </div>

              {/* Cover Field Selection */}
              <div className="space-y-2">
                <Label htmlFor="cover-field">Cover Field</Label>
                <Select
                  value={selectedCoverFieldId || 'auto'}
                  onValueChange={(value) => setSelectedCoverFieldId(value === 'auto' ? null : value)}
                >
                  <SelectTrigger id="cover-field">
                    <SelectValue placeholder="Select cover field" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">Auto (First Attachment)</SelectItem>
                    {fields
                      .filter(f => f.type === 'attachment')
                      .map(field => (
                        <SelectItem key={field.id} value={field.id}>
                          {field.name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Choose which attachment field to display as card cover
                </p>
              </div>

              {/* Card Size Selection */}
              <div className="space-y-3">
                <Label>Card Size</Label>
                <RadioGroup value={cardSize} onValueChange={(value: string) => setCardSize(value as CardSize)}>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="small" id="size-small" />
                    <Label htmlFor="size-small" className="font-normal cursor-pointer">
                      Small
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="medium" id="size-medium" />
                    <Label htmlFor="size-medium" className="font-normal cursor-pointer">
                      Medium
                    </Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="large" id="size-large" />
                    <Label htmlFor="size-large" className="font-normal cursor-pointer">
                      Large
                    </Label>
                  </div>
                </RadioGroup>
              </div>
            </div>
          </PopoverContent>
        </Popover>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className={`grid ${sizeConfig.gridCols} gap-6`}>
          {/* Add New Card */}
          {onRowAdd && (
            <div
              onClick={onRowAdd}
              className={`group relative flex flex-col items-center justify-center ${sizeConfig.minHeight} rounded-xl border-2 border-dashed border-muted bg-muted/10 hover:bg-muted/30 hover:border-primary/50 transition-all cursor-pointer`}
            >
             <div className="p-3 rounded-full bg-background group-hover:scale-110 transition-transform shadow-sm">
                <Plus className="w-6 h-6 text-muted-foreground group-hover:text-primary" />
             </div>
              <span className="mt-3 text-sm font-medium text-muted-foreground group-hover:text-primary">Add New Record</span>
            </div>
          )}

        {visibleRows.map((row) => {
          const record = row.original;
          
          // Extract cover image logic
          let coverImageUrl = null;
          if (coverField) {
            const attachmentValue = record.data[coverField.name]; // Accessing by name as per GridView pattern
            if (Array.isArray(attachmentValue) && attachmentValue.length > 0) {
               // Assuming the object has a url property based on AttachmentCellEditor
               coverImageUrl = attachmentValue[0].url; 
            }
          }

          // Get primary title
          const titleValue = primaryField ? record.data[primaryField.name] : 'Untitled';

          return (
            <Card 
              key={row.id} 
              className="group overflow-hidden hover:shadow-lg hover:border-primary/20 transition-all duration-300 cursor-pointer flex flex-col h-full"
              onClick={() => onRecordClick?.(record.id)}
            >
              {/* Cover Image Area */}
              <div className={`relative ${sizeConfig.imageHeight} bg-muted/30 border-b overflow-hidden`}>
                {coverImageUrl ? (
                  <img
                    src={coverImageUrl}
                    alt={String(titleValue)}
                    loading="lazy"
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-muted-foreground/20 bg-muted/10">
                    <ImageIcon className="w-16 h-16" />
                  </div>
                )}

                {/* Hover overlay/actions could go here */}
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/5 transition-colors" />
              </div>

              <CardHeader className="p-4 pb-2">
                <CardTitle className="text-lg font-semibold leading-tight truncate" title={String(titleValue)}>
                  {renderFieldValue(titleValue, 'text') || <span className="text-muted-foreground italic">Untitled</span>}
                </CardTitle>
              </CardHeader>

              <CardContent className="p-4 pt-2 flex-grow space-y-3">
                {displayFields.map((field) => {
                   const value = record.data[field.name];
                   if (value === null || value === undefined || value === '') return null;
                   
                   return (
                     <div key={field.id} className="flex flex-col gap-1">
                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
                            {field.name}
                        </span>
                        <div className="text-sm">
                            {renderFieldValue(value, field.type)}
                        </div>
                     </div>
                   );
                })}
              </CardContent>
              
              <CardFooter className="p-3 border-t bg-muted/5 flex justify-between items-center text-xs text-muted-foreground">
                 <span>Updated {new Date(record.updated_at).toLocaleDateString()}</span>
                 <Button variant="ghost" size="icon" className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity">
                    <MoreHorizontal className="w-4 h-4" />
                 </Button>
              </CardFooter>
            </Card>
          );
        })}

        {/* Loading trigger sentinel for infinite scroll */}
        <div ref={loadTriggerRef} className="contents" />

        {/* Loading indicator */}
        {hasMore && isLoading && (
          <div className="col-span-full flex justify-center items-center py-8">
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span className="text-sm text-muted-foreground">Loading more records...</span>
            </div>
          </div>
        )}

        {/* End of records indicator */}
        {!hasMore && visibleRows.length > 0 && visibleRows.length >= data.length && (
          <div className="col-span-full text-center py-4">
            <p className="text-sm text-muted-foreground">
              Showing all {data.length} records
            </p>
          </div>
        )}
        </div>
      </div>
    </div>
  );
};
