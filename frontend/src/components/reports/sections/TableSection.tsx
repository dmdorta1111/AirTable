import React, { useMemo } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Table as TableIcon,
  AlertCircle,
  Settings,
  MoreVertical,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Table column definition
export interface TableColumn {
  id: string;
  label: string;
  type: 'text' | 'number' | 'date' | 'boolean';
  width?: number;
  align?: 'left' | 'center' | 'right';
  format?: (value: unknown) => string;
}

// Table row data
export type TableRowData = Record<string, unknown>;

// Table section configuration
export interface TableSectionConfig {
  title?: string;
  description?: string;
  columns: TableColumn[];
  data: TableRowData[];
  showHeader?: boolean;
  striped?: boolean;
  hoverable?: boolean;
  bordered?: boolean;
  compact?: boolean;
  pageSize?: number;
  onRowClick?: (row: TableRowData) => void;
  onConfigure?: () => void;
}

interface TableSectionProps {
  config: TableSectionConfig;
  className?: string;
  isLoading?: boolean;
  error?: string;
}

// Default formatters for different column types
const defaultFormatters = {
  text: (value: unknown) => (value !== null && value !== undefined ? String(value) : '-'),
  number: (value: unknown) => (value !== null && value !== undefined ? Number(value).toLocaleString() : '-'),
  date: (value: unknown) => {
    if (value === null || value === undefined) return '-';
    try {
      return new Date(value as string).toLocaleDateString();
    } catch {
      return String(value);
    }
  },
  boolean: (value: unknown) => {
    if (value === null || value === undefined) return '-';
    return value === true ? '✓' : '✗';
  },
};

export const TableSection: React.FC<TableSectionProps> = ({
  config,
  className,
  isLoading = false,
  error,
}) => {
  const {
    title,
    description,
    columns,
    data,
    showHeader = true,
    striped = true,
    hoverable = true,
    bordered = false,
    compact = false,
    onRowClick,
    onConfigure,
  } = config;

  // Format cell value based on column type
  const formatCellValue = (column: TableColumn, value: unknown): string => {
    if (column.format) {
      return column.format(value);
    }
    return defaultFormatters[column.type](value);
  };

  // Get text alignment class
  const getAlignClass = (align?: 'left' | 'center' | 'right') => {
    switch (align) {
      case 'center':
        return 'text-center';
      case 'right':
        return 'text-right';
      default:
        return 'text-left';
    }
  };

  // Render loading state
  if (isLoading) {
    return (
      <Card className={cn('h-full', className)}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <CardTitle className="text-base font-medium flex items-center gap-2">
                  <TableIcon className="h-5 w-5" />
                  {title}
                </CardTitle>
              )}
              {description && <CardDescription>{description}</CardDescription>}
            </div>
            {onConfigure && (
              <button
                onClick={onConfigure}
                className="p-2 hover:bg-accent rounded-md transition-colors"
              >
                <Settings className="h-4 w-4" />
              </button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-4 bg-muted animate-pulse rounded w-full" />
            <div className="h-4 bg-muted animate-pulse rounded w-full" />
            <div className="h-4 bg-muted animate-pulse rounded w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render error state
  if (error) {
    return (
      <Card className={cn('h-full border-destructive', className)}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <CardTitle className="text-base font-medium flex items-center gap-2">
                  <TableIcon className="h-5 w-5" />
                  {title}
                </CardTitle>
              )}
            </div>
            {onConfigure && (
              <button
                onClick={onConfigure}
                className="p-2 hover:bg-accent rounded-md transition-colors"
              >
                <Settings className="h-4 w-4" />
              </button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center text-destructive">
            <div className="text-center space-y-2">
              <AlertCircle className="h-8 w-8 mx-auto" />
              <p className="text-sm font-medium">Table Error</p>
              <p className="text-xs text-muted-foreground">{error}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render empty state
  if (!data || data.length === 0) {
    return (
      <Card className={cn('h-full', className)}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              {title && (
                <CardTitle className="text-base font-medium flex items-center gap-2">
                  <TableIcon className="h-5 w-5" />
                  {title}
                </CardTitle>
              )}
              {description && <CardDescription>{description}</CardDescription>}
            </div>
            {onConfigure && (
              <button
                onClick={onConfigure}
                className="p-2 hover:bg-accent rounded-md transition-colors"
              >
                <Settings className="h-4 w-4" />
              </button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <TableIcon className="h-12 w-12 mx-auto mb-2" />
              <p className="text-sm">No data available</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('h-full flex flex-col', className, bordered && 'border-2')}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex-1">
            {title && (
              <CardTitle className="text-base font-medium flex items-center gap-2">
                <TableIcon className="h-5 w-5" />
                {title}
              </CardTitle>
            )}
            {description && <CardDescription>{description}</CardDescription>}
          </div>
          {onConfigure && (
            <button
              onClick={onConfigure}
              className="p-2 hover:bg-accent rounded-md transition-colors"
            >
              <Settings className="h-4 w-4" />
            </button>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-auto">
        <Table>
          {showHeader && (
            <TableHeader>
              <TableRow>
                {columns.map((column) => (
                  <TableHead
                    key={column.id}
                    className={cn(
                      getAlignClass(column.align),
                      column.width && `w-[${column.width}px]`
                    )}
                  >
                    {column.label}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
          )}
          <TableBody>
            {data.map((row, rowIndex) => (
              <TableRow
                key={rowIndex}
                className={cn(
                  striped && rowIndex % 2 === 0 && 'bg-muted/50',
                  hoverable && onRowClick && 'cursor-pointer hover:bg-muted/80',
                  compact && 'h-10'
                )}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((column) => (
                  <TableCell
                    key={column.id}
                    className={cn(getAlignClass(column.align))}
                  >
                    {formatCellValue(column, row[column.id])}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

export default TableSection;
