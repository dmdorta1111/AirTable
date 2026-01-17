import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useRef, useState, useCallback, useEffect } from 'react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  ChevronLeft, Plus, Loader2, Grid3X3, Columns,
  GripVertical, Check, X, Users, MessageSquare, Filter, Zap
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Table, Field, Record as RecordType, FieldType } from '@/types'
import { useWebSocket, getPresenceColor } from '@/hooks/use-websocket'
import CommentsPanel from '@/components/modals/CommentsPanel'
import FilterPanel from '@/components/modals/FilterPanel'
import AutomationPanel from '@/components/modals/AutomationPanel'

const ROW_HEIGHT = 36
const MIN_COLUMN_WIDTH = 100
const DEFAULT_COLUMN_WIDTH = 200

interface ColumnWidths {
  [fieldId: string]: number
}

interface EditingCell {
  recordId: string
  fieldId: string
  value: unknown
}

export default function TablePage() {
  const { baseId, tableId } = useParams<{
    baseId: string
    tableId: string
    viewId?: string
  }>()

  const queryClient = useQueryClient()
  const parentRef = useRef<HTMLDivElement>(null)

  // WebSocket for real-time collaboration
  const { isConnected, presence, cellFocus, cursors, focusCell, blurCell, moveCursor } = useWebSocket({
    tableId,
    autoReconnect: true,
  })

  // State
  const [columnWidths, setColumnWidths] = useState<ColumnWidths>({})
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set())
  const [editingCell, setEditingCell] = useState<EditingCell | null>(null)
  const [resizingColumn, setResizingColumn] = useState<string | null>(null)
  const [resizeStartX, setResizeStartX] = useState(0)
  const [resizeStartWidth, setResizeStartWidth] = useState(0)
  const [commentsOpen, setCommentsOpen] = useState(false)
  const [selectedRecordForComments, setSelectedRecordForComments] = useState<RecordType | null>(null)
  const [filterOpen, setFilterOpen] = useState(false)
  const [automationsOpen, setAutomationsOpen] = useState(false)

  // Queries
  const { data: table, isLoading: tableLoading } = useQuery({
    queryKey: ['table', tableId],
    queryFn: async () => {
      const response = await api.get<Table>(`/tables/${tableId}`)
      return response.data
    },
    enabled: !!tableId,
  })

  const { data: fields } = useQuery({
    queryKey: ['fields', tableId],
    queryFn: async () => {
      const response = await api.get<{ items: Field[] }>(`/fields?table_id=${tableId}`)
      return response.data.items
    },
    enabled: !!tableId,
  })

  const { data: records, isLoading: recordsLoading } = useQuery({
    queryKey: ['records', tableId],
    queryFn: async () => {
      const response = await api.get<{ items: RecordType[] }>(`/records?table_id=${tableId}`)
      return response.data.items
    },
    enabled: !!tableId,
  })

  // Mutations
  const updateRecord = useMutation({
    mutationFn: async ({ recordId, fieldId, value }: { recordId: string; fieldId: string; value: unknown }) => {
      const response = await api.patch<RecordType>(`/records/${recordId}`, {
        fields: { [fieldId]: value }
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', tableId] })
    },
  })

  const createRecord = useMutation({
    mutationFn: async () => {
      const response = await api.post<RecordType>(`/records`, {
        table_id: tableId,
        fields: {}
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', tableId] })
    },
  })

  // Virtual scrolling
  const rowVirtualizer = useVirtualizer({
    count: (records?.length ?? 0) + 1, // +1 for add row button
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 10,
  })

  // Column resize handlers
  const handleResizeStart = useCallback((e: React.MouseEvent, fieldId: string) => {
    e.preventDefault()
    setResizingColumn(fieldId)
    setResizeStartX(e.clientX)
    setResizeStartWidth(columnWidths[fieldId] ?? DEFAULT_COLUMN_WIDTH)
  }, [columnWidths])

  useEffect(() => {
    if (!resizingColumn) return

    const handleMouseMove = (e: MouseEvent) => {
      const delta = e.clientX - resizeStartX
      const newWidth = Math.max(MIN_COLUMN_WIDTH, resizeStartWidth + delta)
      setColumnWidths(prev => ({ ...prev, [resizingColumn]: newWidth }))
    }

    const handleMouseUp = () => {
      setResizingColumn(null)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [resizingColumn, resizeStartX, resizeStartWidth])

  // Track mouse position for cursor sharing
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      moveCursor(e.clientX, e.clientY)
    }

    document.addEventListener('mousemove', handleMouseMove)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
    }
  }, [moveCursor])

  // Selection handlers
  const toggleRowSelection = useCallback((recordId: string) => {
    setSelectedRows(prev => {
      const next = new Set(prev)
      if (next.has(recordId)) {
        next.delete(recordId)
      } else {
        next.add(recordId)
      }
      return next
    })
  }, [])

  const toggleAllRows = useCallback(() => {
    if (!records) return
    if (selectedRows.size === records.length) {
      setSelectedRows(new Set())
    } else {
      setSelectedRows(new Set(records.map(r => r.id)))
    }
  }, [records, selectedRows.size])

  // Cell editing handlers
  const startEditing = useCallback((recordId: string, fieldId: string, currentValue: unknown) => {
    setEditingCell({ recordId, fieldId, value: currentValue })
    focusCell(recordId, fieldId)
  }, [focusCell])

  const saveEdit = useCallback(() => {
    if (!editingCell) return
    updateRecord.mutate({
      recordId: editingCell.recordId,
      fieldId: editingCell.fieldId,
      value: editingCell.value
    })
    blurCell()
    setEditingCell(null)
  }, [editingCell, updateRecord, blurCell])

  const cancelEdit = useCallback(() => {
    blurCell()
    setEditingCell(null)
  }, [blurCell])

  const handleEditKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      saveEdit()
    } else if (e.key === 'Escape') {
      cancelEdit()
    }
  }, [saveEdit, cancelEdit])

  const getColumnWidth = (fieldId: string) => columnWidths[fieldId] ?? DEFAULT_COLUMN_WIDTH

  const totalWidth = (fields?.reduce((sum, f) => sum + getColumnWidth(f.id), 0) ?? 0) + 50 + 100 // checkbox + add column

  const isLoading = tableLoading || recordsLoading

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <header className="border-b bg-card shrink-0">
        <div className="px-6 py-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
            <Link to={`/base/${baseId}`} className="hover:text-foreground">
              <ChevronLeft className="h-4 w-4 inline" />
              Back
            </Link>
          </div>
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold">{table?.name || 'Loading...'}</h1>
                {selectedRows.size > 0 && (
                  <span className="text-sm text-muted-foreground">
                    {selectedRows.size} row{selectedRows.size > 1 ? 's' : ''} selected
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {/* Connection status */}
                <div
                  className={cn(
                    "flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium",
                    isConnected ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"
                  )}
                >
                  <div
                    className={cn(
                      "h-2 w-2 rounded-full",
                      isConnected ? "bg-green-500" : "bg-yellow-500"
                    )}
                  />
                  {isConnected ? "Connected" : "Connecting..."}
                </div>

                {/* Presence indicators */}
                {presence.length > 0 && (
                  <div className="flex -space-x-1">
                    {presence.slice(0, 5).map((p, i) => (
                      <div
                        key={p.user_id}
                        className="flex items-center justify-center h-7 w-7 rounded-full border-2 border-background text-xs font-medium"
                        style={{ backgroundColor: p.color }}
                        title={p.user_name}
                      >
                        {p.user_name.charAt(0).toUpperCase()}
                      </div>
                    ))}
                    {presence.length > 5 && (
                      <div
                        className="flex items-center justify-center h-7 w-7 rounded-full bg-muted text-xs font-medium"
                        title={`${presence.length - 5} more users`}
                      >
                        +{presence.length - 5}
                      </div>
                    )}
                  </div>
                )}

                <Button variant="outline" size="sm" onClick={() => setFilterOpen(true)}>
                  <Filter className="h-4 w-4 mr-2" />
                  Filters
                </Button>
                <Button variant="outline" size="sm" onClick={() => setAutomationsOpen(true)}>
                  <Zap className="h-4 w-4 mr-2" />
                  Automations
                </Button>
                <Button variant="outline" size="sm" onClick={() => setCommentsOpen(true)}>
                  <MessageSquare className="h-4 w-4 mr-2" />
                  Comments
                </Button>
                <Button variant="outline" size="sm">
                  <Grid3X3 className="h-4 w-4 mr-2" />
                  Grid View
                </Button>
                <Button variant="outline" size="sm">
                  <Columns className="h-4 w-4 mr-2" />
                  Add Field
                </Button>
                <Button size="sm" onClick={() => createRecord.mutate()}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Record
                </Button>
              </div>
            </div>
        </div>
      </header>

      {/* Grid View with Virtual Scrolling */}
      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {/* Cursor display layer */}
            {cursors.size > 0 && (
              <div className="absolute inset-0 pointer-events-none z-20">
                {Array.from(cursors.values()).map((cursor, i) => (
                  <div
                    key={i}
                    className="absolute"
                    style={{
                      left: cursor.x,
                      top: cursor.y,
                      backgroundColor: cursor.color,
                    }}
                  >
                    <div className="w-0.5 h-4" />
                    <div className="text-xs text-white px-1 py-0.5 rounded-sm ml-1">
                      {cursor.user_name}
                    </div>
                  </div>
                ))}
              </div>
            )}

          <div 
            ref={parentRef} 
            className="h-full overflow-auto"
            style={{ contain: 'strict' }}
          >
            <div style={{ minWidth: totalWidth }}>
              {/* Sticky Header */}
              <div className="flex border-b bg-muted/50 sticky top-0 z-10">
                {/* Checkbox column */}
                <div className="flex items-center justify-center w-[50px] border-r bg-background shrink-0">
                  <Checkbox
                    checked={records?.length ? selectedRows.size === records.length : false}
                    onCheckedChange={toggleAllRows}
                  />
                </div>
                
                {/* Field columns */}
                {fields?.map((field) => (
                  <div
                    key={field.id}
                    className="relative flex items-center px-3 py-2 font-medium text-sm border-r bg-background shrink-0 group"
                    style={{ width: getColumnWidth(field.id) }}
                  >
                    <span className="truncate">{field.name}</span>
                    {/* Resize handle */}
                    <div
                      className={cn(
                        "absolute right-0 top-0 bottom-0 w-1 cursor-col-resize bg-transparent hover:bg-primary/50 transition-colors",
                        resizingColumn === field.id && "bg-primary"
                      )}
                      onMouseDown={(e) => handleResizeStart(e, field.id)}
                    />
                  </div>
                ))}
                
                {/* Add column button */}
                <div className="px-3 py-2 w-[100px] bg-background shrink-0">
                  <Button variant="ghost" size="sm" className="h-6 text-xs">
                    <Plus className="h-3 w-3 mr-1" />
                    Add
                  </Button>
                </div>
              </div>

              {/* Virtualized Rows */}
              <div
                style={{
                  height: `${rowVirtualizer.getTotalSize()}px`,
                  width: '100%',
                  position: 'relative',
                }}
              >
                {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                  const isAddRow = virtualRow.index === (records?.length ?? 0)
                  const record = records?.[virtualRow.index]

                  if (isAddRow) {
                    return (
                      <div
                        key="add-row"
                        className="absolute top-0 left-0 w-full flex border-b"
                        style={{
                          height: `${virtualRow.size}px`,
                          transform: `translateY(${virtualRow.start}px)`,
                        }}
                      >
                        <div className="w-[50px] shrink-0" />
                        <div className="px-3 py-2">
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="h-6 text-xs text-muted-foreground"
                            onClick={() => createRecord.mutate()}
                          >
                            <Plus className="h-3 w-3 mr-1" />
                            Add record
                          </Button>
                        </div>
                      </div>
                    )
                  }

                  if (!record) return null

                  // Check if any user is focused on this record
                  const recordFocuses = Array.from(cellFocus.values()).filter(f => f.record_id === record.id)

                  return (
                    <div
                      key={record.id}
                      className={cn(
                        "absolute top-0 left-0 w-full flex border-b hover:bg-muted/30 transition-colors",
                        selectedRows.has(record.id) && "bg-primary/5",
                        recordFocuses.length > 0 && "relative"
                      )}
                      style={{
                        height: `${virtualRow.size}px`,
                        transform: `translateY(${virtualRow.start}px)`,
                      }}
                    >
                      {/* Checkbox */}
                      <div className="flex items-center justify-center w-[50px] border-r shrink-0">
                        <Checkbox
                          checked={selectedRows.has(record.id)}
                          onCheckedChange={() => toggleRowSelection(record.id)}
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-5 w-5 text-muted-foreground hover:text-primary"
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedRecordForComments(record)
                            setCommentsOpen(true)
                          }}
                        >
                          <MessageSquare className="h-3 w-3" />
                        </Button>
                      </div>

                      {/* Cells */}
                      {fields?.map((field) => {
                        const isEditing = editingCell?.recordId === record.id && editingCell?.fieldId === field.id
                        const cellValue = record.fields[field.id]
                        const cellFocuses = Array.from(cellFocus.values()).filter(f => f.record_id === record.id && f.field_id === field.id)

                        return (
                          <div
                            key={field.id}
                            className={cn(
                              "relative border-r shrink-0",
                              cellFocuses.length > 0 && "bg-blue-50/50"
                            )}
                            style={{ width: getColumnWidth(field.id) }}
                          >
                            {isEditing ? (
                              <EditableCell
                                value={editingCell.value}
                                field={field}
                                onChange={(value) => setEditingCell({ ...editingCell, value })}
                                onKeyDown={handleEditKeyDown}
                                onSave={saveEdit}
                                onCancel={cancelEdit}
                              />
                             ) : (
                              <div
                                className="px-3 py-2 h-full cursor-pointer truncate text-sm relative"
                                onClick={() => startEditing(record.id, field.id, cellValue)}
                                title={String(cellValue ?? '')}
                              >
                                <CellDisplay value={cellValue} field={field} />

                                {/* Cell focus indicators for other users */}
                                {cellFocuses.length > 0 && (
                                  <div className="absolute inset-0 border-2 border-blue-400 rounded pointer-events-none" />
                                )}
          </div>
        )}

        {/* Comments Panel */}
        <CommentsPanel
          tableId={tableId}
          record={selectedRecordForComments}
          fields={fields || []}
          onClose={() => {
            setCommentsOpen(false)
            setSelectedRecordForComments(null)
          }}
        />

        {/* Filter Panel */}
        <FilterPanel
          tableId={tableId}
          fields={fields || []}
          onClose={() => setFilterOpen(false)}
        />

        {/* Automation Panel */}
        <AutomationPanel
          tableId={tableId}
          onClose={() => setAutomationsOpen(false)}
        />
      </div>
    </div>
  )
}

// Editable Cell Component
interface EditableCellProps {
  value: unknown
  field: Field
  onChange: (value: unknown) => void
  onKeyDown: (e: React.KeyboardEvent) => void
  onSave: () => void
  onCancel: () => void
}

function EditableCell({ value, field, onChange, onKeyDown, onSave, onCancel }: EditableCellProps) {
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
    if (inputRef.current && 'select' in inputRef.current) {
      inputRef.current.select()
    }
  }, [])

  const handleBlur = () => {
    onSave()
  }

  // Render different inputs based on field type
  switch (field.type) {
    case 'checkbox':
      return (
        <div className="flex items-center justify-between px-3 py-2 h-full">
          <Checkbox
            checked={!!value}
            onCheckedChange={(checked) => {
              onChange(checked)
              setTimeout(onSave, 0)
            }}
          />
          <Button variant="ghost" size="icon" className="h-5 w-5" onClick={onCancel}>
            <X className="h-3 w-3" />
          </Button>
        </div>
      )

    case 'long_text':
    case 'rich_text':
      return (
        <div className="relative h-full">
          <textarea
            ref={inputRef as React.RefObject<HTMLTextAreaElement>}
            className="w-full h-full px-3 py-2 text-sm bg-background border-2 border-primary resize-none focus:outline-none"
            value={String(value ?? '')}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={onKeyDown}
            onBlur={handleBlur}
          />
        </div>
      )

    case 'number':
    case 'currency':
    case 'percent':
      return (
        <input
          ref={inputRef as React.RefObject<HTMLInputElement>}
          type="number"
          className="w-full h-full px-3 py-2 text-sm bg-background border-2 border-primary focus:outline-none"
          value={value as number ?? ''}
          onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
          onKeyDown={onKeyDown}
          onBlur={handleBlur}
        />
      )

    case 'date':
      return (
        <input
          ref={inputRef as React.RefObject<HTMLInputElement>}
          type="date"
          className="w-full h-full px-3 py-2 text-sm bg-background border-2 border-primary focus:outline-none"
          value={value ? String(value).split('T')[0] : ''}
          onChange={(e) => onChange(e.target.value || null)}
          onKeyDown={onKeyDown}
          onBlur={handleBlur}
        />
      )

    case 'datetime':
      return (
        <input
          ref={inputRef as React.RefObject<HTMLInputElement>}
          type="datetime-local"
          className="w-full h-full px-3 py-2 text-sm bg-background border-2 border-primary focus:outline-none"
          value={value ? String(value).slice(0, 16) : ''}
          onChange={(e) => onChange(e.target.value || null)}
          onKeyDown={onKeyDown}
          onBlur={handleBlur}
        />
      )

    default:
      return (
        <input
          ref={inputRef as React.RefObject<HTMLInputElement>}
          type="text"
          className="w-full h-full px-3 py-2 text-sm bg-background border-2 border-primary focus:outline-none"
          value={String(value ?? '')}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={handleBlur}
        />
      )
  }
}

// Cell Display Component
interface CellDisplayProps {
  value: unknown
  field: Field
}

function CellDisplay({ value, field }: CellDisplayProps) {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground">-</span>
  }

  switch (field.type) {
    case 'checkbox':
      return value ? (
        <Check className="h-4 w-4 text-primary" />
      ) : (
        <span className="text-muted-foreground">-</span>
      )

    case 'date':
      return <span>{new Date(value as string).toLocaleDateString()}</span>

    case 'datetime':
      return <span>{new Date(value as string).toLocaleString()}</span>

    case 'single_select':
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
          {String(value)}
        </span>
      )

    case 'multi_select':
      if (!Array.isArray(value)) return <span>{String(value)}</span>
      return (
        <div className="flex gap-1 flex-wrap">
          {value.map((v, i) => (
            <span
              key={i}
              className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary"
            >
              {String(v)}
            </span>
          ))}
        </div>
      )

    case 'url':
      return (
        <a 
          href={String(value)} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-primary hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {String(value)}
        </a>
      )

    case 'email':
      return (
        <a 
          href={`mailto:${value}`}
          className="text-primary hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {String(value)}
        </a>
      )

    case 'number':
    case 'currency':
    case 'percent':
      const num = Number(value)
      if (field.type === 'currency') {
        return <span>{field.options.currency_symbol ?? '$'}{num.toLocaleString()}</span>
      }
      if (field.type === 'percent') {
        return <span>{num}%</span>
      }
      return <span>{num.toLocaleString()}</span>

    case 'rating':
      const rating = Number(value)
      const max = field.options.max ?? 5
      return (
        <div className="flex gap-0.5">
          {Array.from({ length: max }, (_, i) => (
            <span key={i} className={i < rating ? 'text-yellow-500' : 'text-muted-foreground/30'}>
              {field.options.icon ?? '★'}
            </span>
          ))}
        </div>
      )

    case 'dimension':
      const dim = value as { value: number; tolerance?: number; unit?: string }
      if (typeof dim === 'object' && dim.value !== undefined) {
        return (
          <span>
            {dim.value}
            {dim.tolerance && ` ±${dim.tolerance}`}
            {dim.unit && ` ${dim.unit}`}
          </span>
        )
      }
      return <span>{String(value)}</span>

    default:
      return <span>{String(value)}</span>
  }
}
