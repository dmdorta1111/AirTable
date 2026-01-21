import React, { useState, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  ColumnDef,
} from '@tanstack/react-table';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import type { ImportPreview } from '../types';

interface ExtractionPreviewProps {
  preview: ImportPreview;
  onSelectionChange?: (selectedRowIndices: number[]) => void;
}

/**
 * Validation status for a cell value based on expected field type
 */
interface ValidationStatus {
  isValid: boolean;
  message?: string;
}

/**
 * Validates a value against a field type
 */
const validateValue = (value: any, fieldType: string): ValidationStatus => {
  if (value === null || value === undefined || value === '') {
    return { isValid: true, message: 'Empty' };
  }

  switch (fieldType) {
    case 'number':
      const isNumber = !isNaN(Number(value));
      return {
        isValid: isNumber,
        message: isNumber ? undefined : 'Invalid number',
      };
    case 'date':
      const isDate = !isNaN(Date.parse(String(value)));
      return {
        isValid: isDate,
        message: isDate ? undefined : 'Invalid date',
      };
    case 'checkbox':
      const isBoolean = typeof value === 'boolean' || value === 'true' || value === 'false';
      return {
        isValid: isBoolean,
        message: isBoolean ? undefined : 'Invalid boolean',
      };
    case 'email':
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      const isEmail = emailRegex.test(String(value));
      return {
        isValid: isEmail,
        message: isEmail ? undefined : 'Invalid email',
      };
    case 'url':
      try {
        new URL(String(value));
        return { isValid: true };
      } catch {
        return { isValid: false, message: 'Invalid URL' };
      }
    default:
      return { isValid: true };
  }
};

/**
 * Renders validation status icon for a cell
 */
const ValidationIndicator: React.FC<{ status: ValidationStatus }> = ({ status }) => {
  if (status.isValid) {
    return <CheckCircle2 className="h-4 w-4 text-green-500" />;
  }
  return (
    <div className="flex items-center gap-1" title={status.message}>
      <XCircle className="h-4 w-4 text-destructive" />
    </div>
  );
};

/**
 * Renders cell content with validation
 */
const PreviewCell: React.FC<{
  value: any;
  fieldType: string;
  showValidation?: boolean;
}> = ({ value, fieldType, showValidation = true }) => {
  const validation = validateValue(value, fieldType);

  if (value === null || value === undefined || value === '') {
    return <span className="text-muted-foreground text-xs italic">Empty</span>;
  }

  return (
    <div className="flex items-center justify-between gap-2">
      <span className="truncate flex-1">{String(value)}</span>
      {showValidation && <ValidationIndicator status={validation} />}
    </div>
  );
};

/**
 * ExtractionPreview displays extracted data in a table format with:
 * - Row selection checkboxes for choosing which rows to import
 * - Data type badges for each column
 * - Validation status indicators for each cell
 * - Summary metadata about the extraction
 */
export const ExtractionPreview: React.FC<ExtractionPreviewProps> = ({
  preview,
  onSelectionChange,
}) => {
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const [selectAll, setSelectAll] = useState(false);

  // Create a map of source field to target field for easy lookup
  const fieldTypeMap = useMemo(() => {
    const map: Record<string, { type: string; name: string; id: string }> = {};
    preview.target_fields.forEach((field) => {
      // Find the source field that maps to this target field
      const sourceField = Object.entries(preview.suggested_mapping).find(
        ([_source, target]) => target === field.id
      )?.[0];
      if (sourceField) {
        map[sourceField] = {
          type: field.type,
          name: field.name,
          id: field.id,
        };
      }
    });
    return map;
  }, [preview.target_fields, preview.suggested_mapping]);

  // Generate columns from source fields
  const columns = useMemo<ColumnDef<Record<string, any>>[]>(() => {
    return preview.source_fields.map((sourceField) => {
      const targetField = fieldTypeMap[sourceField];
      return {
        accessorKey: sourceField,
        id: sourceField,
        header: () => (
          <div className="flex flex-col gap-1">
            <span className="font-semibold">{sourceField}</span>
            {targetField && (
              <div className="flex gap-1 items-center">
                <Badge variant="secondary" className="text-xs">
                  {targetField.type}
                </Badge>
                {targetField.name !== sourceField && (
                  <span className="text-xs text-muted-foreground">
                    → {targetField.name}
                  </span>
                )}
              </div>
            )}
          </div>
        ),
        cell: ({ getValue }) => {
          const value = getValue();
          const fieldType = targetField?.type || 'text';
          return <PreviewCell value={value} fieldType={fieldType} />;
        },
      };
    });
  }, [preview.source_fields, fieldTypeMap]);

  // Add selection column at the start
  const columnsWithSelection = useMemo<ColumnDef<Record<string, any>>[]>(() => {
    return [
      {
        id: 'select',
        header: () => (
          <div className="flex items-center justify-center">
            <Checkbox
              checked={selectAll}
              onCheckedChange={(checked) => {
                const newSelectAll = checked === true;
                setSelectAll(newSelectAll);
                if (newSelectAll) {
                  const allIndices = new Set(preview.sample_data.map((_, idx) => idx));
                  setSelectedRows(allIndices);
                  onSelectionChange?.(Array.from(allIndices));
                } else {
                  setSelectedRows(new Set());
                  onSelectionChange?.([]);
                }
              }}
            />
          </div>
        ),
        cell: ({ row }) => (
          <div className="flex items-center justify-center">
            <Checkbox
              checked={selectedRows.has(row.index)}
              onCheckedChange={(checked) => {
                const newSelectedRows = new Set(selectedRows);
                if (checked) {
                  newSelectedRows.add(row.index);
                } else {
                  newSelectedRows.delete(row.index);
                }
                setSelectedRows(newSelectedRows);
                setSelectAll(newSelectedRows.size === preview.sample_data.length);
                onSelectionChange?.(Array.from(newSelectedRows));
              }}
            />
          </div>
        ),
        size: 50,
      },
      ...columns,
    ];
  }, [columns, selectAll, selectedRows, preview.sample_data.length, onSelectionChange]);

  const table = useReactTable({
    data: preview.sample_data,
    columns: columnsWithSelection,
    getCoreRowModel: getCoreRowModel(),
  });

  // Calculate validation statistics
  const validationStats = useMemo(() => {
    let totalCells = 0;
    let validCells = 0;
    let invalidCells = 0;
    let emptyCells = 0;

    preview.sample_data.forEach((row) => {
      preview.source_fields.forEach((field) => {
        const value = row[field];
        const targetField = fieldTypeMap[field];
        const fieldType = targetField?.type || 'text';
        const validation = validateValue(value, fieldType);

        totalCells++;
        if (value === null || value === undefined || value === '') {
          emptyCells++;
        } else if (validation.isValid) {
          validCells++;
        } else {
          invalidCells++;
        }
      });
    });

    return { totalCells, validCells, invalidCells, emptyCells };
  }, [preview.sample_data, preview.source_fields, fieldTypeMap]);

  return (
    <div className="space-y-4">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Records
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{preview.total_records}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Showing {preview.sample_data.length} preview rows
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Selected Rows
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{selectedRows.size}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {selectedRows.size === preview.sample_data.length ? 'All selected' : 'Partial selection'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Valid Cells
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <div className="text-2xl font-bold text-green-600">
                {validationStats.validCells}
              </div>
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {Math.round((validationStats.validCells / validationStats.totalCells) * 100)}% valid
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Invalid Cells
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <div className="text-2xl font-bold text-destructive">
                {validationStats.invalidCells}
              </div>
              {validationStats.invalidCells > 0 && <AlertCircle className="h-5 w-5 text-destructive" />}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {validationStats.emptyCells} empty cells
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Data Table */}
      <Card>
        <CardHeader>
          <CardTitle>Extracted Data Preview</CardTitle>
          <CardDescription>
            Review the extracted data and select rows to import. Data types and validation
            status are shown for each field.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="w-full border rounded-md overflow-hidden bg-background">
            <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
              <Table>
                <TableHeader className="sticky top-0 bg-muted/50 z-10">
                  {table.getHeaderGroups().map((headerGroup) => (
                    <TableRow key={headerGroup.id}>
                      {headerGroup.headers.map((header) => (
                        <TableHead
                          key={header.id}
                          className={`border-l bg-muted/50 ${
                            header.id === 'select' ? 'w-[50px] text-center' : 'min-w-[200px]'
                          }`}
                        >
                          {header.isPlaceholder
                            ? null
                            : flexRender(header.column.columnDef.header, header.getContext())}
                        </TableHead>
                      ))}
                    </TableRow>
                  ))}
                </TableHeader>
                <TableBody>
                  {table.getRowModel().rows.map((row, index) => (
                    <TableRow
                      key={row.id}
                      className={`group ${selectedRows.has(index) ? 'bg-muted/30' : ''}`}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <TableCell
                          key={cell.id}
                          className={`p-3 border-l ${
                            cell.column.id === 'select' ? 'text-center' : ''
                          }`}
                        >
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
