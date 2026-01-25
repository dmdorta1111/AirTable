import { useState } from "react"
import { useParams } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { get, patch, post } from "@/lib/api" // Assuming patch/post exist or I need to check api.ts
import type { Table, Field } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { LayoutGrid, List, Calendar as CalendarIcon, FileText, Upload, X } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

import { GridView } from "@/components/views/GridView"
import { VirtualizedGridView } from "@/components/views/VirtualizedGridView"
import { KanbanView } from "@/components/views/KanbanView"
import { CalendarView } from "@/components/views/CalendarView"
import { FormView } from "@/components/views/FormView"
import { useWebSocket } from "@/hooks/useWebSocket"
import { useAuthStore } from "@/features/auth/stores/authStore"
import { FileUploadDropzone } from "@/features/extraction/components/FileUploadDropzone"
import { ExtractionPreview } from "@/features/extraction/components/ExtractionPreview"
import { FieldMappingDialog } from "@/features/extraction/components/FieldMappingDialog"
import type { ImportPreview, ExtractionFormat } from "@/features/extraction/types"
import {
  createExtractionJob,
  getExtractionJob,
  previewImport,
  importExtractedData,
} from "@/features/extraction/api/extractionApi"

export default function TableViewPage() {
  const { tableId } = useParams<{ tableId: string }>()
  const queryClient = useQueryClient()
  const { token } = useAuthStore()
  const [currentView, setCurrentView] = useState<'grid' | 'virtual-grid' | 'kanban' | 'calendar' | 'form'>('grid')

  // -- Extraction State --
  const [showExtractionDialog, setShowExtractionDialog] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [extractionPreview, setExtractionPreview] = useState<ImportPreview | null>(null)
  const [selectedRows, setSelectedRows] = useState<number[]>([])
  const [showMappingDialog, setShowMappingDialog] = useState(false)
  const [fieldMapping, setFieldMapping] = useState<Record<string, string>>({})

  // -- WebSocket --
  const { status, send } = useWebSocket({
    url: 'ws://localhost:8000/api/v1/realtime/ws', // Adjust if needed
    token: token || undefined,
    onMessage: (msg) => {
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

  // -- Extraction Handlers --
  const [extractionJobId, setExtractionJobId] = useState<string | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);

  const handleFileSelect = async (files: File[]) => {
    if (files.length > 0 && !isExtracting) {
      const file = files[0];
      const extension = file.name.split('.').pop()?.toLowerCase();

      try {
        setIsExtracting(true);

        // Create extraction job for the file
        const format: ExtractionFormat = extension === 'pdf' ? 'pdf'
          : extension === 'dxf' ? 'dxf'
          : extension === 'ifc' ? 'ifc'
          : 'step';

        if (!tableId) {
          throw new Error('Table ID is required for extraction');
        }

        const job = await createExtractionJob(file, format, tableId);
        setExtractionJobId(job.id);

        // Poll for job completion
        let completedJob = await getExtractionJob(job.id);
        const isJobRunning = (status: string) =>
          status === 'processing' ||
          status === 'pending' ||
          status === 'queued';

        while (isJobRunning(completedJob.status)) {
          await new Promise(resolve => setTimeout(resolve, 1000)); // Poll every second
          completedJob = await getExtractionJob(job.id);
        }

        if (completedJob.status === 'completed' && completedJob.result) {
          // Get preview data
          const preview = await previewImport(job.id, tableId);
          setExtractionPreview(preview);
          setShowPreview(true);
        } else if (completedJob.status === 'failed') {
          throw new Error(completedJob.error_message || 'Extraction failed');
        } else {
          throw new Error(`Unexpected job status: ${completedJob.status}`);
        }
      } catch (error) {
        console.error('Extraction error:', error);
        alert(`Error extracting data: ${error instanceof Error ? error.message : 'Unknown error'}`);
      } finally {
        setIsExtracting(false);
      }
    }
  };

  const handleSelectionChange = (indices: number[]) => {
    setSelectedRows(indices);
  };

  const handleMappingConfirm = (mapping: Record<string, string>) => {
    setFieldMapping(mapping);
    setShowMappingDialog(false);
  };

  const handleImportClick = () => {
    setShowExtractionDialog(true);
  };

  const handleCloseExtraction = () => {
    setShowExtractionDialog(false);
    setShowPreview(false);
    setExtractionPreview(null);
    setSelectedRows([]);
    setFieldMapping({});
    setExtractionJobId(null);
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
                variant={currentView === 'virtual-grid' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setCurrentView('virtual-grid')}
                className="h-7 px-2"
            >
                <LayoutGrid className="w-4 h-4 mr-1" /> Virtual Grid
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
          </div>
        </div>
        <div className="flex items-center gap-2">
            <Button onClick={handleImportClick} size="sm" variant="outline">
              <Upload className="w-4 h-4 mr-2" />
              Import from CAD/PDF
            </Button>
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
                {currentView === 'virtual-grid' && (
                    <VirtualizedGridView
                        data={formattedRecords}
                        fields={fields}
                        onCellUpdate={handleCellUpdate}
                        onRowAdd={handleRowAdd}
                    />
                )}
                {currentView === 'kanban' && (
                    <KanbanView tableId={tableId!} fields={fields} />
                )}
                {currentView === 'calendar' && (
                    <CalendarView data={formattedRecords} fields={fields} />
                )}
                {currentView === 'form' && (
                    <FormView fields={fields} onSubmit={(data) => createRecordMutation.mutate(data)} />
                )}
            </>
        )}
      </div>

      {/* Extraction Dialog */}
      <Dialog open={showExtractionDialog} onOpenChange={setShowExtractionDialog}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <div>
                <DialogTitle>Import from CAD/PDF</DialogTitle>
                <DialogDescription>
                  Upload engineering files to extract and import data into this table
                </DialogDescription>
              </div>
              <Button variant="ghost" size="icon" onClick={handleCloseExtraction}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </DialogHeader>

          <div className="space-y-6 mt-4">
            {/* File Upload */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Step 1: Upload Files</CardTitle>
              </CardHeader>
              <CardContent>
                <FileUploadDropzone onFileSelect={handleFileSelect} maxFiles={5} />
              </CardContent>
            </Card>

            {/* Preview */}
            {showPreview && extractionPreview && (
              <>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Step 2: Review Extracted Data</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ExtractionPreview
                      preview={extractionPreview}
                      onSelectionChange={handleSelectionChange}
                    />
                  </CardContent>
                </Card>

                {/* Action Buttons */}
                <div className="flex justify-between items-center">
                  <Button variant="outline" onClick={() => setShowMappingDialog(true)}>
                    Configure Field Mapping
                  </Button>
                  <div className="flex gap-2">
                    <Button variant="outline" onClick={handleCloseExtraction}>
                      Cancel
                    </Button>
                    <Button
                      disabled={selectedRows.length === 0}
                      onClick={async () => {
                        if (selectedRows.length === 0 || !extractionPreview || !tableId) return;

                        try {
                          // Create import request with selected rows and field mapping
                          const importRequest = {
                            job_id: extractionJobId || 'mock-job-id',
                            table_id: tableId!,
                            field_mapping: fieldMapping,
                            row_indices: selectedRows,
                          };

                          const result = await importExtractedData(importRequest);

                          // Invalidate queries to refresh table data
                          queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] });

                          // Close dialog and show success
                          handleCloseExtraction();
                          alert(`Successfully imported ${result.records_imported} rows!`);
                        } catch (error) {
                          console.error('Import error:', error);
                          alert(`Error importing data: ${error instanceof Error ? error.message : 'Unknown error'}`);
                        }
                      }}
                    >
                      Import {selectedRows.length} Selected Rows
                    </Button>
                  </div>
                </div>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Field Mapping Dialog */}
      {extractionPreview && (
        <FieldMappingDialog
          open={showMappingDialog}
          onOpenChange={setShowMappingDialog}
          preview={extractionPreview}
          onConfirm={handleMappingConfirm}
        />
      )}
    </div>
  )
}
