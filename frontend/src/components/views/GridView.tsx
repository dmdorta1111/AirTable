import React, { useState, useEffect } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  ColumnDef,
  CellContext,
  SortingState,
} from '@tanstack/react-table';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'; // Assuming shadcn table exists, otherwise I'll use standard HTML
import type { RecordFieldValue, Field } from '@/types';

import { TextCellEditor } from '../fields/TextCellEditor';
import { NumberCellEditor } from '../fields/NumberCellEditor';
import { DateCellEditor } from '../fields/DateCellEditor';
import { SelectCellEditor } from '../fields/SelectCellEditor';
import { CheckboxCellEditor } from '../fields/CheckboxCellEditor';
import { LinkCellEditor } from '../fields/LinkCellEditor';
import { AttachmentCellEditor } from '../fields/AttachmentCellEditor';
import { Plus, ArrowUp, ArrowDown, ArrowUpDown } from 'lucide-react';
import { getEmptyStateMessage, getEmptyStateClasses } from '@/utils/emptyStateHelpers';

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

interface GridViewProps {
  data: RecordData[];
  fields: Field[];
  onCellUpdate: (rowId: string, fieldId: string, value: unknown) => void;
  onRowAdd?: () => void;
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

  // Cancel handler: reverts to original value and exits edit mode
  const onCancel = () => {
    setValue(initialValue);
    setIsEditing(false);
  };

  const fieldType = (column.columnDef.meta as any)?.type || 'text';
  const fieldOptions = (column.columnDef.meta as any)?.options || {};

  if (isEditing) {
    switch (fieldType) {
      case 'number':
        return <NumberCellEditor value={value as number} onChange={setValue} onBlur={onBlur} onCancel={onCancel} />;
      case 'date':
        return <DateCellEditor value={value as string} onChange={setValue} onBlur={onBlur} onCancel={onCancel} />;
      case 'select':
        return <SelectCellEditor value={value as string} options={fieldOptions.choices} onChange={setValue} onBlur={onBlur} onCancel={onCancel} />;
      case 'checkbox':
        return <CheckboxCellEditor value={value as boolean} onChange={setValue} onBlur={onBlur} onCancel={onCancel} />;
      case 'link':
        return <LinkCellEditor value={value} onChange={setValue} onBlur={onBlur} onCancel={onCancel} />;
      case 'attachment':
        return <AttachmentCellEditor value={value as any[]} onChange={setValue} onBlur={onBlur} onCancel={onCancel} />;
      case 'text':
      default:
        return <TextCellEditor value={value as string} onChange={setValue} onBlur={onBlur} onCancel={onCancel} />;
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
    if (value === null || value === undefined) {
        return <span className={getEmptyStateClasses(type as any)}>{getEmptyStateMessage(type as any)}</span>;
    }

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

export const GridView: React.FC<GridViewProps> = ({ data, fields, onCellUpdate, onRowAdd }) => {
  // Sorting state for multi-column sorting support
  const [sorting, setSorting] = useState<SortingState>([]);

  // Generate columns from fields
  const columns = React.useMemo<ColumnDef<any>[]>(() => {
    return fields.map((field) => ({
      // Use accessorFn to correctly access nested data in row.data
      accessorFn: (row: RecordData) => row.data[field.name],
      id: field.id || field.name,
      header: ({ column }) => {
        const isSorted = column.getIsSorted();
        const SortIcon = isSorted === 'asc' ? ArrowUp : isSorted === 'desc' ? ArrowDown : ArrowUpDown;

        return (
          <button
            type="button"
            className="flex items-center gap-2 cursor-pointer select-none hover:text-primary transition-colors bg-transparent border-none p-0 font-inherit text-inherit"
            onClick={(e) => {
              // Toggle sorting with shift+click support for multi-column
              column.getToggleSortingHandler()?.(e);
            }}
          >
            <span>{field.name}</span>
            <SortIcon className={`w-4 h-4 ${isSorted ? 'text-primary' : 'text-muted-foreground'}`} />
          </button>
        );
      },
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
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    enableSorting: true,
    enableMultiSort: true,
    meta: {
      updateData: (rowId: string, columnId: string, value: any) => {
        onCellUpdate(rowId, columnId, value);
      },
    },
  });

  return (
    <div className="w-full border rounded-md overflow-hidden bg-background shadow-sm">
      <div className="overflow-x-auto">
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
            <TableBody>
            {table.getRowModel().rows.map((row, index) => (
                <TableRow key={row.id} className="group">
                    <TableCell className="text-center text-muted-foreground text-xs bg-muted/20">{index + 1}</TableCell>
                    {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id} className="p-0 border-l h-10 relative">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </TableCell>
                    ))}
                </TableRow>
            ))}
            </TableBody>
        </Table>
      </div>
      {onRowAdd && (
        <div 
            className="border-t p-2 cursor-pointer hover:bg-muted/50 flex items-center gap-2 text-muted-foreground text-sm"
            onClick={onRowAdd}
        >
            <Plus className="w-4 h-4" />
            Add row
        </div>
      )}
    </div>
  );
};
