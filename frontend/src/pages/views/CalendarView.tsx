import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Calendar as CalendarIcon,
  Clock,
  MoreVertical,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Field, Record as RecordType } from '@/types'

interface CalendarEvent {
  id: string
  title: string
  date: string
  fieldId: string
  record: RecordType
  backgroundColor?: string
}

export interface CalendarViewProps {
  tableId: string
  fields: Field[]
}

export default function CalendarView({ tableId, fields }: CalendarViewProps) {
  const queryClient = useQueryClient()

  // State
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [selectedDateField, setSelectedDateField] = useState<string | null>(null)
  const [showEventModal, setShowEventModal] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null)

  // Get date field for calendar
  const dateFields = fields.filter(f =>
    f.type === 'date' || f.type === 'datetime'
  )
  const dateField = selectedDateField || dateFields[0]

  // Fetch records
  const { data: records, isLoading } = useQuery({
    queryKey: ['records', tableId],
    queryFn: async () => {
      const response = await api.get<{ items: RecordType[] }>(`/records?table_id=${tableId}`)
      return response.data.items
    },
    enabled: !!tableId && !!dateField,
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

  // Create record mutation
  const createRecord = useMutation({
    mutationFn: async (date: string) => {
      return api.post<RecordType>('/records', {
        table_id: tableId,
        fields: dateField ? { [dateField.id]: date } : {}
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', tableId] })
      setShowEventModal(false)
    },
  })

  // Navigate months
  const navigateMonth = useCallback((delta: number) => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + delta, 1))
  }, [currentMonth])

  // Go to today
  const goToToday = useCallback(() => {
    setCurrentMonth(new Date())
  }, [])

  // Get calendar days for current month
  const getCalendarDays = useCallback((): (Date | null)[][] => {
    const year = currentMonth.getFullYear()
    const month = currentMonth.getMonth()

    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    const daysInMonth = lastDay.getDate()
    const startingDayOfWeek = firstDay.getDay()

    const days: (Date | null)[][] = []
    let currentDay = 1

    // Previous month days
    for (let i = 0; i < startingDayOfWeek; i++) {
      const date = new Date(year, month, 1 - startingDayOfWeek + i)
      days.push(date)
    }

    // Current month days
    for (let i = 0; i < daysInMonth; i++) {
      days.push(new Date(year, month, currentDay++))
    }

    // Calculate remaining days to complete the grid
    const remainingDays = 42 - days.length // 6 weeks * 7 days
    for (let i = 1; i <= remainingDays; i++) {
      const date = new Date(year, month + 1, i)
      days.push(date)
    }

    // Chunk into weeks
    const weeks: (Date | null)[][] = []
    for (let i = 0; i < days.length; i += 7) {
      weeks.push(days.slice(i, i + 7))
    }

    return weeks
  }, [currentMonth])

  // Get events for a date
  const getEventsForDate = useCallback((date: Date): CalendarEvent[] => {
    if (!dateField || !records) return []

    const dateStr = date.toISOString().split('T')[0]

    return records
      .filter(record => {
        const recordDate = record.fields[dateField.id]
        return recordDate && String(recordDate).startsWith(dateStr)
      })
      .map(record => {
        // Use title field or first text field
        const titleField = fields.find(f => f.type === 'text')
        const title = titleField ? String(record.fields[titleField.id] || 'Untitled') : 'Untitled'

        return {
          id: record.id,
          title,
          date: String(record.fields[dateField.id]),
          fieldId: dateField.id,
          record,
        }
      })
  }, [dateField, records, fields])

  // Handle date click
  const handleDateClick = (date: Date) => {
    if (!date) return

    const events = getEventsForDate(date)

    if (events.length === 0) {
      // Create new record for this date
      const dateStr = date.toISOString().split('T')[0]
      createRecord.mutate(dateStr)
    } else if (events.length === 1) {
      // Open event details
      setSelectedEvent(events[0])
      setShowEventModal(true)
    } else {
      // Show all events for this day (could use a dropdown)
      setSelectedEvent(events[0])
      setShowEventModal(true)
    }
  }

  // Handle event drag to new date
  const handleEventDrop = useCallback((event: CalendarEvent, newDate: Date) => {
    const dateStr = newDate.toISOString().split('T')[0]
    updateRecord.mutate({
      recordId: event.record.id,
      fieldId: event.fieldId,
      value: dateStr,
    })
  }, [updateRecord])

  // Generate colors for events
  const getEventColor = (index: number): string => {
    const colors = [
      'bg-blue-500',
      'bg-green-500',
      'bg-yellow-500',
      'bg-purple-500',
      'bg-pink-500',
      'bg-indigo-500',
    ]
    return colors[index % colors.length]
  }

  const calendarWeeks = getCalendarDays()
  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ]
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

  const isCurrentMonth = (date: Date | null) => {
    if (!date) return false
    return date.getMonth() === currentMonth.getMonth() &&
           date.getFullYear() === currentMonth.getFullYear()
  }

  const isToday = (date: Date | null) => {
    if (!date) return false
    const today = new Date()
    return date.getDate() === today.getDate() &&
           date.getMonth() === today.getMonth() &&
           date.getFullYear() === today.getFullYear()
  }

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
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="icon"
            onClick={() => navigateMonth(-1)}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <div className="flex items-center gap-2">
            <h2 className="text-xl font-semibold">
              {monthNames[currentMonth.getMonth()]} {currentMonth.getFullYear()}
            </h2>
          </div>

          <Button
            variant="outline"
            size="icon"
            onClick={() => navigateMonth(1)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex items-center gap-2">
          {dateFields.length > 1 && (
            <select
              value={selectedDateField || ''}
              onChange={(e) => setSelectedDateField(e.target.value)}
              className="border rounded-md px-3 py-1.5 text-sm"
            >
              <option value="">Select date field</option>
              {dateFields.map(field => (
                <option key={field.id} value={field.id}>
                  {field.name}
                </option>
              ))}
            </select>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={goToToday}
          >
            <Clock className="h-4 w-4 mr-1" />
            Today
          </Button>

          <Button
            size="sm"
            onClick={() => setShowEventModal(true)}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add Record
          </Button>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="flex-1 overflow-auto p-4">
        <div className="grid grid-cols-7 gap-px bg-border rounded-lg overflow-hidden">
          {/* Day Headers */}
          {dayNames.map(day => (
            <div
              key={day}
              className="bg-muted/50 p-2 text-center text-sm font-semibold text-foreground"
            >
              {day}
            </div>
          ))}

          {/* Calendar Days */}
          {calendarWeeks.map((week, weekIndex) => (
            <div key={weekIndex} className="contents">
              {week.map((date, dayIndex) => {
                const events = date ? getEventsForDate(date) : []
                const displayDate = date ? date.getDate() : ''

                return (
                  <div
                    key={`${weekIndex}-${dayIndex}`}
                    className={cn(
                      "min-h-[100px] border-b border-r bg-background p-1 transition-colors cursor-pointer hover:bg-muted/30",
                      !isCurrentMonth(date) && "bg-muted/20",
                      isToday(date) && "bg-primary/10"
                    )}
                    onClick={() => handleDateClick(date!)}
                    onDragOver={(e) => {
                      e.preventDefault()
                      e.dataTransfer.dropEffect = 'move'
                    }}
                    onDrop={(e) => {
                      e.preventDefault()
                      const eventId = e.dataTransfer.getData('text/plain')
                      if (eventId) {
                        const event = records?.find(r => r.id === eventId)
                        if (event && date) {
                          handleEventDrop({
                            id: event.id,
                            title: '',
                            date: String(event.fields[dateField.id]),
                            fieldId: dateField.id,
                            record: event,
                          }, date)
                        }
                      }
                    }}
                  >
                    {/* Date Number */}
                    <div className={cn(
                      "text-sm font-medium",
                      !isCurrentMonth(date) && "text-muted-foreground"
                    )}>
                      {displayDate}
                    </div>

                    {/* Events */}
                    {events.map((event, eventIndex) => (
                      <div
                        key={event.id}
                        className={cn(
                          "mt-1 px-2 py-1 rounded-md text-xs font-medium text-white cursor-grab active:cursor-grabbing hover:opacity-90",
                          getEventColor(eventIndex)
                        )}
                        draggable
                        onDragStart={(e) => {
                          e.dataTransfer.setData('text/plain', event.id)
                        }}
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedEvent(event)
                          setShowEventModal(true)
                        }}
                      >
                        {event.title}
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Event Modal */}
      {showEventModal && selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card rounded-lg shadow-lg max-w-md w-full mx-4 p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold">{selectedEvent.title}</h3>
                <p className="text-sm text-muted-foreground">
                  {new Date(selectedEvent.date).toLocaleDateString()}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  setShowEventModal(false)
                  setSelectedEvent(null)
                }}
              >
                <MoreVertical className="h-5 w-5" />
              </Button>
            </div>

            <div className="space-y-4">
              {Object.entries(selectedEvent.record.fields).map(([key, value]) => {
                const field = fields.find(f => f.id === key)
                if (!field) return null

                return (
                  <div key={key}>
                    <label className="text-sm font-medium text-muted-foreground mb-1 block">
                      {field.name}
                    </label>
                    <div className="text-sm">
                      {String(value || '-')}
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="flex gap-2 mt-6">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setShowEventModal(false)}
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Empty Date Field State */}
      {!dateField && !isLoading && (
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <CalendarIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Date Field</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              Add a date or datetime field to your table to use the calendar view.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
