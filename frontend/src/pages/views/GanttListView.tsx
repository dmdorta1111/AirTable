import { useState, useCallback, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  List as ListIcon,
  LayoutGrid,
  Calendar,
  MoreVertical,
  X,
  Clock,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Field, Record as RecordType } from '@/types'

export interface GanttTask {
  id: string
  title: string
  start: string
  end: string
  progress?: number
  color?: string
}

export interface ListItemData {
  id: string
  record: RecordType
  titleField: string
  titleValue: string
  fields: Array<{ key: string; value: unknown; name: string }>
}

export interface GanttListViewProps {
  tableId: string
  fields: Field[]
  viewMode: 'gantt' | 'list'
}

export default function GanttListView({ tableId, fields, viewMode }: GanttListViewProps) {
  const queryClient = useQueryClient()
  const [viewMode, setViewModeInternal] = useState<'gantt' | 'list'>(viewMode)

  // Get title and date fields
  const titleFields = fields.filter(f => f.type === 'text' || f.type === 'long_text')
  const titleField = titleFields[0]
  const dateFields = fields.filter(f => f.type === 'date' || f.type === 'datetime')
  const dateField = dateFields[0]

  // Fetch records
  const { data: records, isLoading } = useQuery({
    queryKey: ['records', tableId],
    queryFn: async () => {
      const response = await api.get<{ items: RecordType[] }>(`/records?table_id=${tableId}`)
      return response.data.items
    },
    enabled: !!tableId,
  })

  // Update record mutation
  const updateRecord = useMutation({
    mutationFn: async ({ recordId, fieldId, value }: { recordId: string; fieldId: string; value: unknown }) => {
      return api.patch<RecordType>(`/records/${recordId}`, {
        fields: { [fieldId]: value }
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', tableId] })
    },
  })

  // Delete record mutation
  const deleteRecord = useMutation({
    mutationFn: async (recordId: string) => {
      return api.delete(`/records/${recordId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', tableId] })
    },
  })

  // Create task mutation
  const createTask = useMutation({
    mutationFn: async (data: { title: string; startDate: string; endDate: string }) => {
      return api.post<RecordType>('/records', {
        table_id: tableId,
        fields: {
          ...(titleField && { [titleField.id]: data.title }),
          ...(dateField && { [dateField.id]: data.startDate }),
        }
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', tableId] })
    },
  })

  // Gantt tasks from records
  const ganttTasks = useMemo((): GanttTask[] => {
    if (!records || !dateField || !titleField) return []

    return records
      .map(record => {
        const recordDate = record.fields[dateField.id]
        const startDate = typeof recordDate === 'string' && recordDate.split(',').length > 0
          ? recordDate.split(',')[0]
          : String(recordDate || '')

        const endDate = typeof recordDate === 'string' && recordDate.split(',').length > 1
          ? recordDate.split(',')[1]
          : startDate

        const title = String(record.fields[titleField.id] || 'Untitled')

        return {
          id: record.id,
          title,
          start: startDate,
          end: endDate,
          color: getTaskColor(record.id),
        }
      })
      .filter(task => task.start && task.end)
  }, [records, dateField, titleField])

  // List items from records
  const listItems = useMemo((): ListItemData[] => {
    if (!records) return []

    return records.map(record => {
      const titleValue = titleField ? String(record.fields[titleField.id] || 'Untitled') : 'Untitled'

      return {
        id: record.id,
        record,
        titleField: titleField?.id || '',
        titleValue,
        fields: Object.entries(record.fields)
          .map(([key, value]) => {
            const field = fields.find(f => f.id === key)
            return {
              key,
              value,
              name: field?.name || key,
            }
          })
          .filter(f => f.name), // Filter out empty or unknown fields
      }
    })
  }, [records, fields, titleField])

  // Get color for task
  const getTaskColor = useCallback((taskId: string): string => {
    const colors = [
      'bg-blue-500',
      'bg-green-500',
      'bg-yellow-500',
      'bg-purple-500',
      'bg-pink-500',
      'bg-indigo-500',
    ]
    const index = parseInt(taskId.replace(/[^0-9]/g, ''), 10) % colors.length
    return colors[index]
  }, [])

  // Format date for display
  const formatDate = (dateStr: string) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString()
  }

  // Calculate task duration in days
  const getTaskDuration = (startDate: string, endDate: string): number => {
    const start = new Date(startDate)
    const end = new Date(endDate)
    const diffTime = Math.abs(end.getTime() - start.getTime())
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1
  }

  // Handle delete
  const handleDelete = useCallback((taskId: string) => {
    if (confirm('Delete this task?')) {
      deleteRecord.mutate(taskId)
    }
  }, [deleteRecord])

  // Handle edit task
  const [editingTask, setEditingTask] = useState<GanttTask | null>(null)
  const handleEditTask = useCallback((task: GanttTask) => {
    setEditingTask(task)
  }, [])

  // Save task edit
  const handleSaveTask = useCallback(() => {
    if (!editingTask) return

    updateRecord.mutate({
      recordId: editingTask.id,
      fieldId: dateField.id,
      value: `${editingTask.start},${editingTask.end}`,
    })

    setEditingTask(null)
  }, [editingTask, updateRecord, dateField])

  const today = new Date()
  const ganttDays = Array.from({ length: 30 }, (_, i) => {
    const date = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 15 + i)
    return date
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary border-t-transparent"></div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-card">
        <h2 className="text-xl font-semibold">
          {viewMode === 'gantt' ? 'Gantt' : 'List'} View
        </h2>
        <div className="flex items-center gap-2">
          <Button
            variant={viewMode === 'gantt' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewModeInternal('gantt')}
          >
            <Calendar className="h-4 w-4 mr-1" />
            Gantt
          </Button>
          <Button
            variant={viewMode === 'list' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setViewModeInternal('list')}
          >
            <ListIcon className="h-4 w-4 mr-1" />
            List
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {viewMode === 'gantt' ? (
          <div className="p-4">
            {!dateField ? (
              <div className="text-center py-8 text-muted-foreground">
                Add a date field to use Gantt view
              </div>
            ) : (
              <>
                {/* Gantt Grid */}
                <div className="overflow-x-auto">
                  <div className="min-w-full">
                    {/* Date header */}
                    <div className="flex border-b">
                      <div className="w-64 flex-shrink-0 p-2 font-semibold text-sm bg-muted/50 sticky left-0 z-10">
                        Task
                      </div>
                      {ganttDays.map(day => (
                        <div
                          key={day.toISOString()}
                          className="w-20 flex-shrink-0 p-2 text-center text-xs font-medium border-l"
                        >
                          {day.getDate()}
                          <div className="text-xs text-muted-foreground">
                            {day.toLocaleDateString('en', { weekday: 'short' })}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Tasks */}
                    {ganttTasks.map(task => (
                      <div
                        key={task.id}
                        className={cn(
                          "flex border-b group hover:bg-muted/30",
                          editingTask?.id === task.id && "ring-2 ring-primary"
                        )}
                      >
                        {/* Task name */}
                        <div
                          className={cn(
                            "w-64 flex-shrink-0 p-2 text-sm font-medium bg-background sticky left-0 z-10",
                            task.color
                          )}
                          onClick={() => handleEditTask(task)}
                        >
                          {task.title}
                          <div className="text-xs text-muted-foreground/70 mt-1">
                            {getTaskDuration(task.start, task.end)}d
                          </div>
                        </div>

                        {/* Gantt bars */}
                        {ganttDays.map(day => {
                          const taskStart = new Date(task.start)
                          const taskEnd = new Date(task.end)
                          const cellDate = day

                          const isTaskDay = cellDate >= taskStart && cellDate <= taskEnd
                          const isStartDay = cellDate.toDateString() === taskStart.toDateString()
                          const isEndDay = cellDate.toDateString() === taskEnd.toDateString()

                          return (
                            <div
                              key={day.toISOString()}
                              className={cn(
                                "w-20 h-12 border-l flex-shrink-0 p-0.5",
                                isTaskDay && task.color && "bg-primary/10"
                              )}
                            >
                              {isTaskDay && (
                                <div
                                  className={cn(
                                    "h-full rounded",
                                    task.color
                                  )}
                                >
                                  {isStartDay && (
                                    <div className="flex items-center justify-center h-full text-xs text-white font-medium">
                                      {formatDate(task.start)}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        ) : (
          /* List View */
          <div className="p-4">
            {listItems.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No records yet. Add a record to get started.
              </div>
            ) : (
              <div className="space-y-2">
                {listItems.map(item => (
                  <div
                    key={item.id}
                    className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    {/* Header */}
                    <div className="flex items-start justify-between mb-3">
                      <h3 className="font-semibold text-lg">{item.titleValue}</h3>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(item.id)}
                      >
                        <X className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>

                    {/* Date info */}
                    <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
                      <Clock className="h-4 w-4" />
                      {dateField ? formatDate(String(item.record.fields[dateField.id] || '')) : 'No date'}
                    </div>

                    {/* Additional fields */}
                    <div className="space-y-2">
                      {item.fields.map((field, idx) => (
                        <div key={`${field.key}-${idx}`} className="flex">
                          <label className="w-32 flex-shrink-0 text-sm font-medium text-muted-foreground">
                            {field.name}
                          </label>
                          <div className="flex-1 min-w-0 text-sm">
                            {String(field.value || '-')}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
