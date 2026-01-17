import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
  DragOverEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Plus, MoreHorizontal, GripVertical, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Table, Field, Record as RecordType, SelectOption } from '@/types'

interface KanbanViewProps {
  tableId: string
  groupFieldId?: string
}

export default function KanbanView({ tableId, groupFieldId: propGroupFieldId }: KanbanViewProps) {
  const queryClient = useQueryClient()
  const [activeCard, setActiveCard] = useState<RecordType | null>(null)

  // Queries
  const { data: table } = useQuery({
    queryKey: ['table', tableId],
    queryFn: async () => {
      const response = await api.get<Table>(`/tables/${tableId}`)
      return response.data
    },
    enabled: !!tableId,
  })

  const { data: fields, isLoading: fieldsLoading } = useQuery({
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

  // Find the grouping field (single_select type)
  const groupField = useMemo(() => {
    if (!fields) return null
    
    // Use provided groupFieldId or find first single_select field
    if (propGroupFieldId) {
      return fields.find(f => f.id === propGroupFieldId && f.type === 'single_select')
    }
    
    return fields.find(f => f.type === 'single_select' || f.type === 'status')
  }, [fields, propGroupFieldId])

  // Get columns from field options
  const columns = useMemo(() => {
    if (!groupField?.options.choices) {
      return [{ id: '__uncategorized__', name: 'Uncategorized', color: 'gray' }]
    }
    
    const choices = groupField.options.choices
    return [
      ...choices,
      { id: '__uncategorized__', name: 'Uncategorized', color: 'gray' }
    ]
  }, [groupField])

  // Group records by column
  const recordsByColumn = useMemo(() => {
    const grouped: { [columnId: string]: RecordType[] } = {}
    
    // Initialize all columns with empty arrays
    columns.forEach(col => {
      grouped[col.id] = []
    })
    
    if (!records || !groupField) return grouped
    
    records.forEach(record => {
      const value = record.fields[groupField.id]
      const columnId = value ? String(value) : '__uncategorized__'
      
      // Find matching column by name (since value is the name, not id)
      const column = columns.find(c => c.name === columnId || c.id === columnId)
      const targetColumnId = column?.id ?? '__uncategorized__'
      
      if (!grouped[targetColumnId]) {
        grouped[targetColumnId] = []
      }
      grouped[targetColumnId].push(record)
    })
    
    return grouped
  }, [records, columns, groupField])

  // Get primary field for card title
  const primaryField = useMemo(() => {
    if (!fields || !table?.primary_field_id) {
      return fields?.[0]
    }
    return fields.find(f => f.id === table.primary_field_id) ?? fields[0]
  }, [fields, table])

  // Get display fields for card body (first 2-3 non-primary fields)
  const displayFields = useMemo(() => {
    if (!fields || !primaryField) return []
    return fields
      .filter(f => f.id !== primaryField.id && f.id !== groupField?.id)
      .slice(0, 3)
  }, [fields, primaryField, groupField])

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
    mutationFn: async (columnId: string) => {
      const column = columns.find(c => c.id === columnId)
      const fields: { [key: string]: unknown } = {}
      
      if (groupField && column && column.id !== '__uncategorized__') {
        fields[groupField.id] = column.name
      }
      
      const response = await api.post<RecordType>(`/records`, {
        table_id: tableId,
        fields
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', tableId] })
    },
  })

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // DnD handlers
  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event
    const record = records?.find(r => r.id === active.id)
    if (record) {
      setActiveCard(record)
    }
  }

  const handleDragOver = (event: DragOverEvent) => {
    // Handle drag over logic if needed for visual feedback
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    setActiveCard(null)

    if (!over || !groupField) return

    const activeRecord = records?.find(r => r.id === active.id)
    if (!activeRecord) return

    // Determine target column
    let targetColumnId = String(over.id)
    
    // If dropped on another card, find its column
    if (records?.some(r => r.id === over.id)) {
      const overRecord = records.find(r => r.id === over.id)
      if (overRecord) {
        const overValue = overRecord.fields[groupField.id]
        targetColumnId = overValue ? String(overValue) : '__uncategorized__'
        // Find the column by name
        const targetColumn = columns.find(c => c.name === targetColumnId || c.id === targetColumnId)
        targetColumnId = targetColumn?.id ?? '__uncategorized__'
      }
    }

    // Find the target column
    const targetColumn = columns.find(c => c.id === targetColumnId)
    if (!targetColumn) return

    // Get current value
    const currentValue = activeRecord.fields[groupField.id]
    const currentColumnId = currentValue ? String(currentValue) : '__uncategorized__'
    const currentColumn = columns.find(c => c.name === currentColumnId || c.id === currentColumnId)

    // If moved to a different column, update the record
    if (currentColumn?.id !== targetColumn.id) {
      const newValue = targetColumn.id === '__uncategorized__' ? null : targetColumn.name
      updateRecord.mutate({
        recordId: activeRecord.id,
        fieldId: groupField.id,
        value: newValue
      })
    }
  }

  const isLoading = fieldsLoading || recordsLoading

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!groupField) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <h3 className="text-lg font-medium mb-2">No grouping field found</h3>
          <p className="text-muted-foreground mb-4">
            Add a Single Select or Status field to enable Kanban view.
          </p>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Add Field
          </Button>
        </div>
      </div>
    )
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 p-4 h-full overflow-x-auto">
        {columns.map((column) => (
          <KanbanColumn
            key={column.id}
            column={column}
            records={recordsByColumn[column.id] ?? []}
            primaryField={primaryField}
            displayFields={displayFields}
            onAddCard={() => createRecord.mutate(column.id)}
          />
        ))}
      </div>

      <DragOverlay>
        {activeCard && primaryField ? (
          <KanbanCard
            record={activeCard}
            primaryField={primaryField}
            displayFields={displayFields}
            isDragging
          />
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}

// Kanban Column Component
interface KanbanColumnProps {
  column: SelectOption | { id: string; name: string; color: string }
  records: RecordType[]
  primaryField?: Field
  displayFields: Field[]
  onAddCard: () => void
}

function KanbanColumn({ column, records, primaryField, displayFields, onAddCard }: KanbanColumnProps) {
  const recordIds = records.map(r => r.id)

  const getColumnColor = (color: string) => {
    const colors: { [key: string]: string } = {
      gray: 'bg-gray-100 text-gray-700',
      red: 'bg-red-100 text-red-700',
      orange: 'bg-orange-100 text-orange-700',
      yellow: 'bg-yellow-100 text-yellow-700',
      green: 'bg-green-100 text-green-700',
      blue: 'bg-blue-100 text-blue-700',
      purple: 'bg-purple-100 text-purple-700',
      pink: 'bg-pink-100 text-pink-700',
      cyan: 'bg-cyan-100 text-cyan-700',
    }
    return colors[color] ?? colors.gray
  }

  return (
    <div className="flex flex-col w-[300px] min-w-[300px] bg-muted/30 rounded-lg">
      {/* Column Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center gap-2">
          <span className={cn(
            "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
            getColumnColor(column.color)
          )}>
            {column.name}
          </span>
          <span className="text-sm text-muted-foreground">
            {records.length}
          </span>
        </div>
        <Button variant="ghost" size="icon" className="h-6 w-6">
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </div>

      {/* Column Body */}
      <div className="flex-1 p-2 overflow-y-auto">
        <SortableContext items={recordIds} strategy={verticalListSortingStrategy}>
          <div className="flex flex-col gap-2">
            {records.map((record) => (
              <SortableCard
                key={record.id}
                record={record}
                primaryField={primaryField}
                displayFields={displayFields}
              />
            ))}
          </div>
        </SortableContext>
      </div>

      {/* Add Card Button */}
      <div className="p-2 border-t">
        <Button
          variant="ghost"
          className="w-full justify-start text-muted-foreground"
          onClick={onAddCard}
        >
          <Plus className="h-4 w-4 mr-2" />
          Add card
        </Button>
      </div>
    </div>
  )
}

// Sortable Card Wrapper
interface SortableCardProps {
  record: RecordType
  primaryField?: Field
  displayFields: Field[]
}

function SortableCard({ record, primaryField, displayFields }: SortableCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: record.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div ref={setNodeRef} style={style}>
      <KanbanCard
        record={record}
        primaryField={primaryField}
        displayFields={displayFields}
        dragHandleProps={{ ...attributes, ...listeners }}
      />
    </div>
  )
}

// Kanban Card Component
interface KanbanCardProps {
  record: RecordType
  primaryField?: Field
  displayFields: Field[]
  isDragging?: boolean
  dragHandleProps?: Record<string, unknown>
}

function KanbanCard({ record, primaryField, displayFields, isDragging, dragHandleProps }: KanbanCardProps) {
  const title = primaryField 
    ? String(record.fields[primaryField.id] ?? 'Untitled')
    : 'Untitled'

  return (
    <Card className={cn(
      "cursor-pointer hover:shadow-md transition-shadow",
      isDragging && "shadow-lg rotate-3"
    )}>
      <CardHeader className="p-3 pb-2">
        <div className="flex items-start gap-2">
          <div 
            className="cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground mt-0.5"
            {...dragHandleProps}
          >
            <GripVertical className="h-4 w-4" />
          </div>
          <CardTitle className="text-sm font-medium line-clamp-2 flex-1">
            {title}
          </CardTitle>
        </div>
      </CardHeader>
      {displayFields.length > 0 && (
        <CardContent className="p-3 pt-0">
          <div className="space-y-1">
            {displayFields.map((field) => {
              const value = record.fields[field.id]
              if (value === null || value === undefined) return null

              return (
                <div key={field.id} className="flex items-center gap-2 text-xs">
                  <span className="text-muted-foreground truncate max-w-[80px]">
                    {field.name}:
                  </span>
                  <span className="truncate">
                    {formatValue(value, field)}
                  </span>
                </div>
              )
            })}
          </div>
        </CardContent>
      )}
    </Card>
  )
}

// Format cell value for display
function formatValue(value: unknown, field: Field): string {
  if (value === null || value === undefined) return ''

  switch (field.type) {
    case 'checkbox':
      return value ? 'Yes' : 'No'
    case 'date':
      return new Date(value as string).toLocaleDateString()
    case 'datetime':
      return new Date(value as string).toLocaleString()
    case 'multi_select':
      if (Array.isArray(value)) return value.join(', ')
      return String(value)
    case 'number':
    case 'currency':
    case 'percent':
      const num = Number(value)
      if (field.type === 'currency') {
        return `${field.options.currency_symbol ?? '$'}${num.toLocaleString()}`
      }
      if (field.type === 'percent') {
        return `${num}%`
      }
      return num.toLocaleString()
    default:
      return String(value)
  }
}
