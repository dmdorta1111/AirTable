import { useState } from "react"
import { useParams } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { get, patch, post } from "@/lib/api"
import type { Table, Field } from "@/types"
import { Button } from "@/components/ui/button"
import { LayoutGrid, List, Calendar as CalendarIcon, FileText, ImageIcon, GanttChartSquare, Clock } from "lucide-react"

import { GridView } from "@/components/views/GridView"
import { KanbanView } from "@/components/views/KanbanView"
import { CalendarView } from "@/components/views/CalendarView"
import { FormView } from "@/components/views/FormView"
import { GalleryView } from "@/components/views/GalleryView"
import { GanttView } from "@/components/views/GanttView"
import { TimelineView } from "@/components/views/TimelineView"
import { useWebSocket } from "@/hooks/useWebSocket"
import { useAuthStore } from "@/features/auth/stores/authStore"

export default function TableViewPage() {
  const { tableId } = useParams<{ baseId: string; tableId: string }>()
  const queryClient = useQueryClient()
  const { token } = useAuthStore()
  const [currentView, setCurrentView] = useState<'grid' | 'kanban' | 'calendar' | 'form' | 'gallery' | 'gantt' | 'timeline'>('grid')

  // -- WebSocket --
  const { status, send } = useWebSocket({
    url: 'ws://localhost:8000/api/v1/realtime/ws', // Adjust if needed
    token: token || undefined,
    onMessage: (msg) => {
        console.log('WS Msg:', msg);
        if (msg.event_type === 'record.created' || msg.event_type === 'record.updated') {
             queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] });
        }
    }
  });

  // -- Queries --
  const { data: table } = useQuery({
    queryKey: ["tables", tableId],
    queryFn: () => get<Table>(`/tables/${tableId}`),
    enabled: !!tableId,
  })

  const { data: fields } = useQuery({
    queryKey: ["tables", tableId, "fields"],
    queryFn: () => get<Field[]>(`/tables/${tableId}/fields`),
    enabled: !!tableId,
  })

  const { data: records, isLoading: recordsLoading } = useQuery({
    queryKey: ["tables", tableId, "records"],
    queryFn: () => get<any[]>(`/tables/${tableId}/records`), // Use any[] for now as Record type might be complex
    enabled: !!tableId,
  })

  // -- Mutations --
  const updateRecordMutation = useMutation({
    mutationFn: (variables: { recordId: string, data: any }) => 
      patch(`/records/${variables.recordId}`, variables.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] })
    }
  })

  const createRecordMutation = useMutation({
    mutationFn: (data: any) => post(`/tables/${tableId}/records`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] })
    }
  })

  // -- Handlers --
  const handleCellUpdate = (rowId: string, fieldId: string, value: any) => {
    // Optimistic update could go here
    updateRecordMutation.mutate({
        recordId: rowId,
        data: { [fieldId]: value } // Assuming API takes { fieldName: value }
    });
    
    // Notify via WS (optional, if backend doesn't broadcast own updates)
    send('record_update', { tableId, recordId: rowId, fieldId, value });
  };

  const handleRowAdd = () => {
    createRecordMutation.mutate({});
  };

  if (!table || !fields) return <div className="p-8">Loading table...</div>

  // Flatten records for the view if needed.
  // Assuming records come as { id: "...", ...fields } or { id: "...", data: { ... } }
  // I'll assume the API returns flat objects or I need to flatten them.
  // For now, let's assume flat objects matching field names.
  const formattedRecords = records || [];

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] overflow-hidden space-y-4 p-4">
      {/* Header */}
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center justify-center w-10 h-10 rounded bg-primary/10 text-2xl">
            {table.icon || "📊"}
          </div>
          <div>
            <h1 className="text-xl font-bold">{table.name}</h1>
            <p className="text-xs text-muted-foreground">{table.description || "No description"}</p>
          </div>
          <div className="ml-4 flex gap-1 bg-muted p-1 rounded-md">
            <Button 
                variant={currentView === 'grid' ? 'secondary' : 'ghost'} 
                size="sm" 
                onClick={() => setCurrentView('grid')}
                className="h-7 px-2"
            >
                <List className="w-4 h-4 mr-1" /> Grid
            </Button>
            <Button 
                variant={currentView === 'kanban' ? 'secondary' : 'ghost'} 
                size="sm" 
                onClick={() => setCurrentView('kanban')}
                className="h-7 px-2"
            >
                <LayoutGrid className="w-4 h-4 mr-1" /> Kanban
            </Button>
            <Button 
                variant={currentView === 'calendar' ? 'secondary' : 'ghost'} 
                size="sm" 
                onClick={() => setCurrentView('calendar')}
                className="h-7 px-2"
            >
                <CalendarIcon className="w-4 h-4 mr-1" /> Calendar
            </Button>
            <Button
                variant={currentView === 'form' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setCurrentView('form')}
                className="h-7 px-2"
            >
                <FileText className="w-4 h-4 mr-1" /> Form
            </Button>
            <Button
                variant={currentView === 'gallery' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setCurrentView('gallery')}
                className="h-7 px-2"
            >
                <ImageIcon className="w-4 h-4 mr-1" /> Gallery
            </Button>
            <Button
                variant={currentView === 'gantt' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setCurrentView('gantt')}
                className="h-7 px-2"
            >
                <GanttChartSquare className="w-4 h-4 mr-1" /> Gantt
            </Button>
            <Button
                variant={currentView === 'timeline' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setCurrentView('timeline')}
                className="h-7 px-2"
            >
                <Clock className="w-4 h-4 mr-1" /> Timeline
            </Button>
          </div>
        </div>
        <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${status === 'connected' ? 'bg-green-500' : 'bg-red-500'}`} title={`WebSocket: ${status}`} />
            <span className="text-xs text-muted-foreground uppercase">{records?.length || 0} Records</span>
        </div>
      </div>

      {/* View Content */}
      <div className="flex-1 overflow-hidden border rounded-md bg-background shadow-sm">
        {recordsLoading ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">Loading records...</div>
        ) : (
            <>
                {currentView === 'grid' && (
                    <GridView 
                        data={formattedRecords} 
                        fields={fields} 
                        onCellUpdate={handleCellUpdate}
                        onRowAdd={handleRowAdd}
                    />
                )}
                {currentView === 'kanban' && (
                    <KanbanView data={formattedRecords} fields={fields} />
                )}
                {currentView === 'calendar' && (
                    <CalendarView data={formattedRecords} fields={fields} />
                )}
                {currentView === 'form' && (
                    <FormView fields={fields} onSubmit={(data) => createRecordMutation.mutate(data)} />
                )}
                {currentView === 'gallery' && (
                    <GalleryView data={formattedRecords} fields={fields} />
                )}
                {currentView === 'gantt' && (
                    <GanttView data={formattedRecords} fields={fields} />
                )}
                {currentView === 'timeline' && (
                    <TimelineView data={formattedRecords} fields={fields} />
                )}
            </>
        )}
      </div>
    </div>
  )
}
