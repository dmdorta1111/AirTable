import { useState, useMemo } from "react"
import { useParams } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { get, patch, post } from "@/lib/api" // Assuming patch/post exist or I need to check api.ts
import type { Table, Field } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { LayoutGrid, List, Calendar as CalendarIcon, FileText, Upload, X, Search, Image, GanttChartSquare, Clock } from "lucide-react"
import { useDebounce } from "@/hooks/useDebounce"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

import { GridView } from "@/components/views/GridView"
import { VirtualizedGridView } from "@/components/views/VirtualizedGridView"
import { KanbanView } from "@/components/views/KanbanView"
import { CalendarView } from "@/components/views/CalendarView"
import { FormView } from "@/components/views/FormView"
import { GalleryView } from "@/components/views/GalleryView"
import { GanttView } from "@/components/views/GanttView"
import { TimelineView } from "@/components/views/TimelineView"
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
import { useToast } from "@/hooks/use-toast"

export default function TableViewPage() {
  const { tableId } = useParams<{ tableId: string }>()
  const queryClient = useQueryClient()
  const { token } = useAuthStore()
  const { toast } = useToast()
  const [currentView, setCurrentView] = useState<'grid' | 'virtual-grid' | 'kanban' | 'calendar' | 'form' | 'gallery' | 'gantt' | 'timeline'>('grid')

  // -- Search & Filter State --
  const [searchQuery, setSearchQuery] = useState('')
  const debouncedSearchQuery = useDebounce(searchQuery, 300)

  // -- Extraction State --
  const [showExtractionDialog, setShowExtractionDialog] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [extractionPreview, setExtractionPreview] = useState<ImportPreview | null>(null)
  const [selectedRows, setSelectedRows] = useState<number[]>([])
  const [showMappingDialog, setShowMappingDialog] = useState(false)
  const [fieldMapping, setFieldMapping] = useState<Record<string, string>>({})
  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null)
  const [showRecordModal, setShowRecordModal] = useState(false)

  // -- WebSocket --
  const { status, send } = useWebSocket({
    url: 'ws://localhost:8000/api/v1/realtime/ws', // Adjust if needed
    token: token || undefined,
    onMessage: (msg) => {
        if (msg.event_type === 'record.created' || msg.event_type === 'record.updated') {
             queryClient.invalidateQueries({ queryKey: ["views", defaultView?.id, "data"] });
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

  // Fetch the default view for the table
  const { data: defaultView } = useQuery({
    queryKey: ["tables", tableId, "defaultView"],
    queryFn: () => get<any>(`/api/v1/views/default?table_id=${tableId}`),
    enabled: !!tableId,
  })

  // Fetch records through the view data endpoint
  const { data: viewData, isLoading: recordsLoading } = useQuery({
    queryKey: ["views", defaultView?.id, "data"],
    queryFn: () => post<any>(`/api/v1/views/${defaultView?.id}/data`, {
      page: 1,
      page_size: 1000,
    }),
    enabled: !!defaultView?.id,
  })

  // Extract records from view data response
  const records = viewData?.records || []

  // -- Mutations --
  const updateRecordMutation = useMutation({
    mutationFn: (variables: { recordId: string, data: any }) =>
      patch(`/records/${variables.recordId}`, variables.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["views", defaultView?.id, "data"] })
      toast({ title: "Record updated", description: "Changes saved successfully." })
    },
    onError: (error) => {
      toast({ title: "Failed to update record", description: error instanceof Error ? error.message : "Unknown error", variant: "destructive" })
    }
  })

  const createRecordMutation = useMutation({
    mutationFn: (data: any) => post(`/tables/${tableId}/records`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["views", defaultView?.id, "data"] })
      toast({ title: "Record created", description: "New record added successfully." })
    },
    onError: (error) => {
      toast({ title: "Failed to create record", description: error instanceof Error ? error.message : "Unknown error", variant: "destructive" })
    }
  })

  const importDataMutation = useMutation({
    mutationFn: async (variables: {
      jobId: string,
      fieldMapping: Record<string, string>,
      rowIndices: number[]
    }) => {
      const importRequest = {
        job_id: variables.jobId,
        table_id: tableId!,
        field_mapping: variables.fieldMapping,
        row_indices: variables.rowIndices,
      };
      return importExtractedData(importRequest);
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["tables", tableId, "records"] });
      setShowMappingDialog(false);
      handleCloseExtraction();
      toast({ title: "Import successful", description: `Successfully imported ${result.records_imported} rows!` })
    },
    onError: (error) => {
      toast({ title: "Import failed", description: error instanceof Error ? error.message : "Unknown error", variant: "destructive" })
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
          toast({ title: "Extraction complete", description: "Data extracted successfully. Please review and confirm import." })
        } else if (completedJob.status === 'failed') {
          throw new Error(completedJob.error_message || 'Extraction failed');
        } else {
          throw new Error(`Unexpected job status: ${completedJob.status}`);
        }
      } catch (error) {
        console.error('Extraction error:', error);
        toast({ title: "Extraction failed", description: error instanceof Error ? error.message : "Unknown error", variant: "destructive" })
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

    // Trigger import with the confirmed mapping
    if (extractionJobId && selectedRows.length > 0) {
      importDataMutation.mutate({
        jobId: extractionJobId,
        fieldMapping: mapping,
        rowIndices: selectedRows,
      });
    }
  };

  const handleImportClick = () => {
    setShowExtractionDialog(true);
  };

  const handleRecordClick = (recordId: string) => {
    setSelectedRecordId(recordId);
    setShowRecordModal(true);
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

  // Memoized filtered records based on debounced search query
  const filteredRecords = useMemo(() => {
    const recordsData = records || []

    if (!debouncedSearchQuery.trim()) {
      return recordsData
    }

    const query = debouncedSearchQuery.toLowerCase()

    return recordsData.filter((record: any) => {
      // Search across all string fields in the record
      return Object.values(record).some((value) => {
        if (value && typeof value === 'string') {
          return value.toLowerCase().includes(query)
        }
        return false
      })
    })
  }, [records, debouncedSearchQuery])

  // Flatten records for the view if needed.
  // Handle both flat format { id: "...", fieldName: value } and nested format { id: "...", data: { fieldName: value } }
  // Also apply search filtering from filteredRecords
  const formattedRecords = useMemo(() => {
    return (filteredRecords || []).map((record: any) => {
      if (record.data) {
        // Nested format - flatten it
        return {
          ...record,
          ...record.data,
        };
      }
      // Already flat format
      return record;
    });
  }, [filteredRecords]);

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
          <TooltipProvider>
            <div className="ml-4 flex gap-1 bg-muted p-1 rounded-md">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant={currentView === 'grid' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setCurrentView('grid')}
                    className="h-7 px-2"
                  >
                    <List className="w-4 h-4 mr-1" /> Grid
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Grid View (Ctrl+1)</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant={currentView === 'virtual-grid' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setCurrentView('virtual-grid')}
                    className="h-7 px-2"
                  >
                    <LayoutGrid className="w-4 h-4 mr-1" /> Virtual Grid
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Virtual Grid View (Ctrl+2)</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant={currentView === 'kanban' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setCurrentView('kanban')}
                    className="h-7 px-2"
                  >
                    <LayoutGrid className="w-4 h-4 mr-1" /> Kanban
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Kanban View (Ctrl+3)</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant={currentView === 'calendar' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setCurrentView('calendar')}
                    className="h-7 px-2"
                  >
                    <CalendarIcon className="w-4 h-4 mr-1" /> Calendar
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Calendar View (Ctrl+4)</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant={currentView === 'form' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setCurrentView('form')}
                    className="h-7 px-2"
                  >
                    <FileText className="w-4 h-4 mr-1" /> Form
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Form View (Ctrl+5)</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant={currentView === 'gallery' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setCurrentView('gallery')}
                    className="h-7 px-2"
                  >
                    <Image className="w-4 h-4 mr-1" /> Gallery
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Gallery View (Ctrl+6)</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant={currentView === 'gantt' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setCurrentView('gantt')}
                    className="h-7 px-2"
                  >
                    <GanttChartSquare className="w-4 h-4 mr-1" /> Gantt
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Gantt View (Ctrl+7)</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant={currentView === 'timeline' ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setCurrentView('timeline')}
                    className="h-7 px-2"
                  >
                    <Clock className="w-4 h-4 mr-1" /> Timeline
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Timeline View (Ctrl+8)</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </TooltipProvider>
        </div>
        <div className="flex items-center gap-2">
            <Button onClick={handleImportClick} size="sm" variant="outline">
              <Upload className="w-4 h-4 mr-2" />
              Import from CAD/PDF
            </Button>
            <div className={`w-2 h-2 rounded-full ${status === 'connected' ? 'bg-green-500' : 'bg-red-500'}`} title={`WebSocket: ${status}`} />
            <span className="text-xs text-muted-foreground uppercase" data-testid="records-count">
              {searchQuery ? `${filteredRecords.length} of ${records?.length || 0}` : records?.length || 0} Records
            </span>
        </div>
      </div>

      {/* Search Bar */}
      <div className="shrink-0">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search records..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
          {searchQuery && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
              {filteredRecords.length} {filteredRecords.length === 1 ? 'result' : 'results'}
            </div>
          )}
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
                    <KanbanView
                        data={formattedRecords}
                        fields={fields}
                        onRecordUpdate={handleCellUpdate}
                    />
                )}
                {currentView === 'calendar' && (
                    <CalendarView data={formattedRecords} fields={fields} />
                )}
                {currentView === 'form' && (
                    <FormView
                        fields={fields}
                        onSubmit={(data) => createRecordMutation.mutate(data)}
                        isLoading={createRecordMutation.isPending}
                    />
                )}
                {currentView === 'gallery' && (
                    <GalleryView
                        data={formattedRecords}
                        fields={fields}
                        onRowAdd={handleRowAdd}
                        onRecordClick={handleRecordClick}
                        isLoading={recordsLoading}
                    />
                )}
                {currentView === 'gantt' && (
                    <GanttView
                        data={formattedRecords}
                        fields={fields}
                        onCellUpdate={handleCellUpdate}
                    />
                )}
                {currentView === 'timeline' && (
                    <TimelineView data={formattedRecords} fields={fields} />
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
                          queryClient.invalidateQueries({ queryKey: ["views", defaultView?.id, "data"] });

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
          isLoading={importDataMutation.isPending}
        />
      )}

      {/* Record Detail Modal */}
      <Dialog open={showRecordModal} onOpenChange={setShowRecordModal}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center justify-between">
              <div>
                <DialogTitle>Record Details</DialogTitle>
                <DialogDescription>
                  View and edit record information
                </DialogDescription>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setShowRecordModal(false)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </DialogHeader>

          <div className="space-y-4 mt-4">
            {selectedRecordId && (() => {
              const record = formattedRecords.find(r => r.id === selectedRecordId);
              if (!record) return <div className="text-muted-foreground">Record not found</div>;

              return (
                <div className="space-y-6">
                  {fields.map((field) => {
                    const value = record.data?.[field.name] ?? record[field.name];

                    return (
                      <div key={field.id} className="space-y-2">
                        <label className="text-sm font-semibold text-foreground uppercase tracking-wider">
                          {field.name}
                        </label>
                        <div className="p-3 rounded-md border bg-muted/30">
                          {value !== null && value !== undefined && value !== '' ? (
                            (() => {
                              switch (field.type) {
                                case 'checkbox':
                                  return <input type="checkbox" checked={!!value} readOnly className="h-5 w-5" />;
                                case 'attachment':
                                  return (
                                    <div className="space-y-2">
                                      {Array.isArray(value) && value.length > 0 ? (
                                        value.map((file: any, idx: number) => (
                                          <div key={idx} className="flex items-center gap-2 text-sm">
                                            <FileText className="w-4 h-4" />
                                            <span>{file.name || file.url}</span>
                                          </div>
                                        ))
                                      ) : (
                                        <span className="text-muted-foreground">No attachments</span>
                                      )}
                                    </div>
                                  );
                                case 'link':
                                  return <span className="text-blue-500">{Array.isArray(value) ? `${value.length} linked records` : 'Linked'}</span>;
                                case 'select':
                                  return <span className="px-3 py-1 rounded-full bg-secondary text-secondary-foreground font-medium">{String(value)}</span>;
                                default:
                                  return <span className="text-sm">{String(value)}</span>;
                              }
                            })()
                          ) : (
                            <span className="text-muted-foreground italic text-sm">Empty</span>
                          )}
                        </div>
                      </div>
                    );
                  })}

                  <div className="pt-4 border-t">
                    <div className="text-xs text-muted-foreground space-y-1">
                      <div>Created: {new Date(record.created_at).toLocaleString()}</div>
                      <div>Updated: {new Date(record.updated_at).toLocaleString()}</div>
                    </div>
                  </div>
                </div>
              );
            })()}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
