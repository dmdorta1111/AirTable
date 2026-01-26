import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';
import { Table2, AlertCircle, ChevronRight } from 'lucide-react';

// Pivot cell data structure
export interface PivotCell {
  row: string;
  column?: string;
  value: number;
  count: number;
  records?: Array<{ id: string; [key: string]: unknown }>;
}

// Pivot table data structure
export interface PivotTableData {
  rows: string[]; // Row headers
  columns?: string[]; // Column headers (optional for 1D pivot)
  cells: PivotCell[]; // Cell data with aggregated values
  totals?: {
    rows: Record<string, number>; // Total for each row
    columns?: Record<string, number>; // Total for each column
    grand?: number; // Grand total
  };
}

// Pivot table configuration
export interface PivotTableConfig {
  title?: string;
  description?: string;
  rowLabel?: string; // Label for row header column
  columnLabel?: string; // Label for column header row
  valueLabel?: string; // Label for value (e.g., "Sum", "Count", "Average")
  showTotals?: boolean; // Show row/column totals
  formatValue?: (value: number) => string; // Custom value formatter
  onDrillDown?: (cell: PivotCell) => void; // Drill-down callback
}

interface PivotTableProps {
  data: PivotTableData;
  config: PivotTableConfig;
  className?: string;
  isLoading?: boolean;
  error?: string;
}

export const PivotTable: React.FC<PivotTableProps> = ({
  data,
  config,
  className,
  isLoading = false,
  error,
}) => {
  const [drillDownCell, setDrillDownCell] = useState<PivotCell | null>(null);

  const {
    title,
    description,
    rowLabel = 'Rows',
    columnLabel = 'Columns',
    valueLabel = 'Value',
    showTotals = true,
    formatValue = (value) => value.toLocaleString(),
    onDrillDown,
  } = config;

  // Helper to find cell value
  const getCellValue = (row: string, column?: string): PivotCell | null => {
    return (
      data.cells.find((cell) => cell.row === row && cell.column === column) ||
      null
    );
  };

  // Handle cell click for drill-down
  const handleCellClick = (cell: PivotCell | null) => {
    if (!cell || cell.count === 0) return;

    setDrillDownCell(cell);
    if (onDrillDown) {
      onDrillDown(cell);
    }
  };

  // Render loading state
  if (isLoading) {
    return (
      <Card className={cn('h-full', className)}>
        <CardHeader>
          {title && (
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <Table2 className="h-5 w-5" />
              {title}
            </CardTitle>
          )}
          {description && <CardDescription>{description}</CardDescription>}
        </CardHeader>
        <CardContent className="h-[calc(100%-5rem)]">
          <div className="h-full flex items-center justify-center">
            <div className="space-y-3 w-full">
              <div className="h-4 bg-muted animate-pulse rounded w-3/4 mx-auto" />
              <div className="h-4 bg-muted animate-pulse rounded w-1/2 mx-auto" />
              <div className="h-32 bg-muted animate-pulse rounded" />
            </div>
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
          {title && (
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <Table2 className="h-5 w-5" />
              {title}
            </CardTitle>
          )}
        </CardHeader>
        <CardContent className="h-[calc(100%-5rem)]">
          <div className="h-full flex items-center justify-center text-destructive">
            <div className="text-center space-y-2">
              <AlertCircle className="h-8 w-8 mx-auto" />
              <p className="text-sm font-medium">Pivot Table Error</p>
              <p className="text-xs text-muted-foreground">{error}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Render empty state
  if (!data || data.rows.length === 0) {
    return (
      <Card className={cn('h-full', className)}>
        <CardHeader>
          {title && (
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <Table2 className="h-5 w-5" />
              {title}
            </CardTitle>
          )}
          {description && <CardDescription>{description}</CardDescription>}
        </CardHeader>
        <CardContent className="h-[calc(100%-5rem)]">
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <Table2 className="h-8 w-8 mx-auto" />
              <p className="mt-2 text-sm">No data available</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Determine if this is a 2D pivot table (has columns)
  const is2D = data.columns && data.columns.length > 0;

  return (
    <>
      <Card className={cn('h-full', className)}>
        <CardHeader>
          {title && (
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <Table2 className="h-5 w-5" />
              {title}
            </CardTitle>
          )}
          {description && <CardDescription>{description}</CardDescription>}
        </CardHeader>
        <CardContent className="h-[calc(100%-5rem)] overflow-auto">
          <div className="border rounded-md">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead className="font-semibold border-r bg-muted">
                    {rowLabel}
                  </TableHead>
                  {is2D ? (
                    <>
                      {data.columns!.map((col) => (
                        <TableHead
                          key={col}
                          className="text-center font-semibold"
                        >
                          {col}
                        </TableHead>
                      ))}
                      {showTotals && (
                        <TableHead className="text-center font-semibold border-l bg-muted/50">
                          Total
                        </TableHead>
                      )}
                    </>
                  ) : (
                    <TableHead className="text-center font-semibold">
                      {valueLabel}
                    </TableHead>
                  )}
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.rows.map((row) => (
                  <TableRow key={row} className="hover:bg-muted/30">
                    <TableCell className="font-medium border-r bg-muted/20">
                      {row}
                    </TableCell>
                    {is2D ? (
                      <>
                        {data.columns!.map((col) => {
                          const cell = getCellValue(row, col);
                          return (
                            <TableCell
                              key={`${row}-${col}`}
                              className={cn(
                                'text-center cursor-pointer hover:bg-accent transition-colors',
                                cell && cell.count > 0 && 'font-medium'
                              )}
                              onClick={() => handleCellClick(cell)}
                            >
                              {cell ? (
                                <div className="flex items-center justify-center gap-1">
                                  {formatValue(cell.value)}
                                  {cell.count > 0 && (
                                    <span className="text-xs text-muted-foreground">
                                      ({cell.count})
                                    </span>
                                  )}
                                </div>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </TableCell>
                          );
                        })}
                        {showTotals && data.totals?.rows && (
                          <TableCell className="text-center font-semibold border-l bg-muted/10">
                            {formatValue(data.totals.rows[row] || 0)}
                          </TableCell>
                        )}
                      </>
                    ) : (
                      <TableCell
                        className="text-center cursor-pointer hover:bg-accent transition-colors font-medium"
                        onClick={() => handleCellClick(getCellValue(row))}
                      >
                        {(() => {
                          const cell = getCellValue(row);
                          return cell ? (
                            <div className="flex items-center justify-center gap-1">
                              {formatValue(cell.value)}
                              {cell.count > 0 && (
                                <span className="text-xs text-muted-foreground">
                                  ({cell.count})
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          );
                        })()}
                      </TableCell>
                    )}
                  </TableRow>
                ))}
                {showTotals && is2D && data.totals?.columns && (
                  <TableRow className="bg-muted/50 font-semibold">
                    <TableCell className="border-r border-t">Total</TableCell>
                    {data.columns!.map((col) => (
                      <TableCell
                        key={col}
                        className="text-center border-t"
                      >
                        {formatValue(data.totals!.columns![col] || 0)}
                      </TableCell>
                    ))}
                    {data.totals.grand !== undefined && (
                      <TableCell className="text-center border-l border-t bg-muted/30">
                        {formatValue(data.totals.grand)}
                      </TableCell>
                    )}
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Drill-down dialog */}
      <Dialog open={!!drillDownCell} onOpenChange={() => setDrillDownCell(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ChevronRight className="h-5 w-5" />
              Drill-Down Details
            </DialogTitle>
            <DialogDescription>
              {drillDownCell && (
                <>
                  {drillDownCell.column ? (
                    <>
                      <strong>{rowLabel}:</strong> {drillDownCell.row} &nbsp;|&nbsp;
                      <strong>{columnLabel}:</strong> {drillDownCell.column}
                    </>
                  ) : (
                    <>
                      <strong>{rowLabel}:</strong> {drillDownCell.row}
                    </>
                  )}
                  &nbsp;|&nbsp;
                  <strong>{valueLabel}:</strong> {formatValue(drillDownCell.value)}
                  &nbsp;|&nbsp;
                  <strong>Count:</strong> {drillDownCell.count} records
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4">
            {drillDownCell?.records && drillDownCell.records.length > 0 ? (
              <div className="border rounded-md overflow-auto max-h-96">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      {Object.keys(drillDownCell.records[0])
                        .filter((key) => key !== 'id')
                        .map((key) => (
                          <TableHead key={key} className="font-semibold">
                            {key}
                          </TableHead>
                        ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {drillDownCell.records.map((record, idx) => (
                      <TableRow key={record.id || idx}>
                        {Object.entries(record)
                          .filter(([key]) => key !== 'id')
                          .map(([key, value]) => (
                            <TableCell key={key}>
                              {String(value ?? '—')}
                            </TableCell>
                          ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <div className="text-center text-muted-foreground py-8">
                <p className="text-sm">No detailed records available</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default PivotTable;
