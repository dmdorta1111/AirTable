import React, { useState, useEffect, useRef } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  ColumnDef,
  CellContext,
} from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { RecordFieldValue, Field } from '@/types';

import { TextCellEditor } from '../fields/TextCellEditor';
import { NumberCellEditor } from '../fields/NumberCellEditor';
import { DateCellEditor } from '../fields/DateCellEditor';
import { SelectCellEditor } from '../fields/SelectCellEditor';
import { CheckboxCellEditor } from '../fields/CheckboxCellEditor';
import { LinkCellEditor } from '../fields/LinkCellEditor';
import { AttachmentCellEditor } from '../fields/AttachmentCellEditor';
import { Plus } from 'lucide-react';

// Proper types based on backend schemas
interface RecordData {
  id: string;
  table_id: string;
  data: Record<string, RecordFieldValue>;
  row_height: number;
  created_at: string;
  updated_at: string;
  created_by_id: string;
  last_modified_by_id: string;
}

interface VirtualizedGridViewProps {
  data: RecordData[];
  fields: Field[];
  onCellUpdate: (rowId: string, fieldId: string, value: unknown) => void;
  onRowAdd?: () => void;
  estimatedRowHeight?: number;
  overscan?: number;
}

// Cell component to handle edit mode
const EditableCell = ({
  getValue,
  row,
  column,
}: CellContext<any, any>) => {
  const initialValue = getValue();
  const [value, setValue] = useState(initialValue);
  const [isEditing, setIsEditing] = useState(false);

  // Update internal state when prop changes
  useEffect(() => {
    setValue(initialValue);
  }, [initialValue]);

  const onBlur = () => {
    setIsEditing(false);
    // Update cell value using custom meta method we've added to options
    const columnMeta = column.columnDef.meta as Record<string, unknown> | undefined;
    if (columnMeta && typeof columnMeta.updateData === 'function') {
      columnMeta.updateData(row.original.id, column.id, value);
    }
  };

  const fieldType = (column.columnDef.meta as any)?.type || 'text';
  const fieldOptions = (column.columnDef.meta as any)?.options || {};

  if (isEditing) {
    switch (fieldType) {
      case 'number':
        return <NumberCellEditor value={value as number} onChange={setValue} onBlur={onBlur} />;
      case 'date':
        return <DateCellEditor value={value as string} onChange={setValue} onBlur={onBlur} />;
      case 'select':
        return <SelectCellEditor value={value as string} options={fieldOptions.choices} onChange={setValue} onBlur={onBlur} />;
      case 'checkbox':
        return <CheckboxCellEditor value={value as boolean} onChange={setValue} onBlur={onBlur} />;
      case 'link':
        return <LinkCellEditor value={value} onChange={setValue} onBlur={onBlur} />;
      case 'attachment':
        return <AttachmentCellEditor value={value as any[]} onChange={setValue} onBlur={onBlur} />;
      case 'text':
      default:
        return <TextCellEditor value={value as string} onChange={setValue} onBlur={onBlur} />;
    }
  }

  // Render Display Mode
  return (
    <div
      className="h-full w-full min-h-[32px] flex items-center px-2 cursor-pointer hover:bg-muted/50 truncate"
      onClick={() => setIsEditing(true)}
    >
        {renderCellContent(value, fieldType)}
    </div>
  );
};

const renderCellContent = (value: any, type: string) => {
    if (value === null || value === undefined) return <span className="text-muted-foreground text-xs">Empty</span>;

    switch (type) {
        case 'checkbox':
            return <input type="checkbox" checked={!!value} readOnly className="pointer-events-none" />;
        case 'attachment':
            return Array.isArray(value) ? `${value.length} files` : '0 files';
        case 'link':
            return Array.isArray(value) ? `${value.length} linked` : 'Linked';
        case 'select':
            return <span className="px-2 py-0.5 rounded-md bg-secondary text-secondary-foreground text-xs">{String(value)}</span>;
        default:
            return String(value);
    }
};

const ROW_HEIGHT = 40; // Fixed height for each row in pixels
const DEFAULT_OVERSCAN = 5;

export const VirtualizedGridView: React.FC<VirtualizedGridViewProps> = ({
  data,
  fields,
  onCellUpdate,
  onRowAdd,
  estimatedRowHeight = ROW_HEIGHT,
  overscan = DEFAULT_OVERSCAN,
}) => {
  const tableContainerRef = useRef<HTMLDivElement>(null);

  // Generate columns from fields
  const columns = React.useMemo<ColumnDef<any>[]>(() => {
    return fields.map((field) => ({
      accessorKey: field.name,
      id: field.id || field.name,
      header: field.name,
      cell: EditableCell,
      meta: {
        type: field.type,
        options: field.options,
      },
    }));
  }, [fields]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    meta: {
      updateData: (rowId: string, columnId: string, value: any) => {
        onCellUpdate(rowId, columnId, value);
      },
    },
  });

  const { rows } = table.getRowModel();

  // Create virtualizer instance
  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => tableContainerRef.current,
    estimateSize: () => estimatedRowHeight,
    overscan,
  });

  const virtualRows = rowVirtualizer.getVirtualItems();
  const totalHeight = rowVirtualizer.getTotalSize();

  return (
    <div className="w-full border rounded-md overflow-hidden bg-background shadow-sm flex flex-col h-full">
      {/* Header Table - always visible */}
      <div className="overflow-x-auto flex-shrink-0">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                <TableHead className="w-[50px] text-center bg-muted/50">#</TableHead>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id} className="min-w-[150px] border-l bg-muted/50 font-semibold text-foreground">
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
        </Table>
      </div>

      {/* Virtualized Body */}
      <div
        ref={tableContainerRef}
        className="overflow-auto flex-1"
        style={{
          height: 'calc(100vh - 300px)',
          minHeight: '400px',
        }}
      >
        <div
          style={{
            height: `${totalHeight}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          <Table style={{ border: 'none' }}>
            <TableBody>
              {virtualRows.map((virtualRow) => {
                const row = rows[virtualRow.index];
                return (
                  <TableRow
                    key={row.id}
                    className="group absolute w-full"
                    style={{
                      transform: `translateY(${virtualRow.start}px)`,
                      height: `${estimatedRowHeight}px`,
                    }}
                  >
                    <TableCell className="text-center text-muted-foreground text-xs bg-muted/20 w-[50px]">
                      {virtualRow.index + 1}
                    </TableCell>
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id} className="p-0 border-l h-full relative">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Add Row Button */}
      {onRowAdd && (
        <div
          className="border-t p-2 cursor-pointer hover:bg-muted/50 flex items-center gap-2 text-muted-foreground text-sm flex-shrink-0"
          onClick={onRowAdd}
        >
          <Plus className="w-4 h-4" />
          Add row
        </div>
      )}
    </div>
  );
};
