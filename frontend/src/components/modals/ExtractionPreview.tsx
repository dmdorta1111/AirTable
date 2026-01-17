import { useState, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  File,
  X,
  Download,
  Eye,
  Search,
  AlertCircle,
  CheckCircle,
  Clock,
  RefreshCw,
  ArrowRight,
  FileText,
  Table,
  Image as ImageIcon,
  Layers,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Record as RecordType, Field } from '@/types'

export interface ExtractionResult {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  type: 'pdf' | 'dxf' | 'ifc' | 'step'
  fileUrl?: string
  progress?: number
  results?: {
    tables?: Array<{
      headers: string[]
      rows: Array<string[]>
    }>
    dimensions?: Array<{
      value: string
      tolerance?: string
      unit?: string
    }>
    metadata?: {
      title?: string
      author?: string
      created?: string
      modified?: string
    }
  }
  error?: string
  createdAt: string
  updatedAt: string
}

export interface ExtractionPreviewProps {
  tableId: string
  recordId: string
  attachmentField?: Field
  onClose: () => void
}

export default function ExtractionPreview({ tableId, recordId, attachmentField, onClose }: ExtractionPreviewProps) {
  const queryClient = useQueryClient()

  const [activeTab, setActiveTab] = useState<'preview' | 'tables' | 'dimensions' | 'metadata'>('preview')
  const [isPolling, setIsPolling] = useState(false)

  // Fetch record
  const { data: record } = useQuery({
    queryKey: ['record', recordId],
    queryFn: async () => {
      const response = await api.get<RecordType>(`/records/${recordId}`)
      return response.data
    },
    enabled: !!recordId,
  })

  // Trigger extraction mutation
  const triggerExtraction = useMutation({
    mutationFn: async () => {
      if (!attachmentField) {
        throw new Error('No attachment field found')
      }

      const fileUrl = record?.fields[attachmentField.id] as string
      if (!fileUrl) {
        throw new Error('No file found')
      }

      return api.post<ExtractionResult>('/extraction', {
        file_url: fileUrl,
        record_id: recordId,
        extract_tables: true,
        extract_dimensions: true,
      })
    },
    onSuccess: () => {
      setIsPolling(true)
      // Poll for results
      setTimeout(() => pollExtractionResults(), 5000)
    },
  })

  // Fetch extraction results
  const { data: extractions, isLoading } = useQuery({
    queryKey: ['extractions', recordId],
    queryFn: async () => {
      const response = await api.get<{ items: ExtractionResult[] }>(`/extractions?record_id=${recordId}`)
      return response.data.items
    },
    enabled: !!recordId,
    refetchInterval: isPolling ? 3000 : false,
  })

  // Stop polling when completed
  useEffect(() => {
    if (isPolling && extractions && extractions.length > 0) {
      const latest = extractions[0]
      if (latest.status === 'completed' || latest.status === 'failed') {
        setIsPolling(false)
      }
    }
  }, [isPolling, extractions])

  const pollExtractionResults = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['extractions', recordId] })
  }, [queryClient, recordId])

  const latestExtraction = extractions?.[0]

  if (!record) {
    return null
  }

  const fileUrl = attachmentField ? record.fields[attachmentField.id] as string : null
  const fileExtension = fileUrl ? fileUrl.split('.').pop()?.toLowerCase() : ''

  const getFileIcon = () => {
    if (!fileExtension) return <File className="h-8 w-8" />

    const icons: Record<string, any> = {
      pdf: <FileText className="h-8 w-8 text-red-500" />,
      dxf: <Layers className="h-8 w-8 text-blue-500" />,
      ifc: <Table className="h-8 w-8 text-green-500" />,
      step: <Layers className="h-8 w-8 text-purple-500" />,
    }

    return icons[fileExtension] || <File className="h-8 w-8" />
  }

  const renderStatusBadge = (status: ExtractionResult['status']) => {
    switch (status) {
      case 'pending':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
            <Clock className="h-3 w-3 mr-1" />
            Pending
          </span>
        )
      case 'processing':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
            <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
            Processing
          </span>
        )
      case 'completed':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
            <CheckCircle className="h-3 w-3 mr-1" />
            Completed
          </span>
        )
      case 'failed':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
            <AlertCircle className="h-3 w-3 mr-1" />
            Failed
          </span>
        )
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
            Unknown
          </span>
        )
    }

  const renderPreview = () => {
    if (!fileUrl) return null

    return (
      <div className="flex flex-col items-center justify-center py-8 border-2 border-dashed rounded-lg">
        {fileExtension === 'pdf' ? (
          <iframe
            src={fileUrl}
            className="w-full h-96 border-0"
            title="PDF Preview"
          />
        ) : fileExtension === 'dxf' ? (
          <div className="text-center">
            <Layers className="h-24 w-24 text-blue-500 mb-4" />
            <p className="text-muted-foreground">
              DXF preview coming soon
            </p>
          </div>
        ) : fileExtension === 'ifc' ? (
          <div className="text-center">
            <Table className="h-24 w-24 text-green-500 mb-4" />
            <p className="text-muted-foreground">
              IFC preview coming soon
            </p>
          </div>
        ) : (
          <div className="text-center">
            <File className="h-24 w-24 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              Preview not available for this file type
            </p>
          </div>
        )}
      </div>
    )
  }

  const renderTables = () => {
    if (!latestExtraction?.results?.tables || latestExtraction.results.tables.length === 0) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          No tables extracted yet
        </div>
      )
    }

    return (
      <div className="space-y-4">
        {latestExtraction.results.tables.map((table, index) => (
          <Card key={index}>
            <CardHeader>
              <CardTitle>Table {index + 1}</CardTitle>
              <Button
                variant="outline"
                size="icon"
                onClick={() => {
                  const headers = table.headers.join('\t')
                  const csv = [headers, ...table.rows].map(row => row.join('\t'))].map(row => row.join(',')).join('\n')
                  const blob = new Blob([csv], { type: 'text/csv' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = `table-${index + 1}.csv`
                  a.click()
                }}
              >
                <Download className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="bg-muted/50">
                      {table.headers.map(header => (
                        <th
                          key={header}
                          className="px-2 py-1 text-left font-medium text-foreground border-b"
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {table.rows.slice(0, 10).map((row, rowIndex) => (
                      <tr key={rowIndex}>
                        {row.map((cell, cellIndex) => (
                          <td
                            key={cellIndex}
                            className="px-2 py-1 border-b"
                          >
                            {cell || '-'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const renderDimensions = () => {
    if (!latestExtraction?.results?.dimensions || latestExtraction.results.dimensions.length === 0) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          No dimensions extracted yet
        </div>
      )
    }

    return (
      <div className="space-y-4">
        {latestExtraction.results.dimensions.map((dim, index) => (
          <Card key={index}>
            <CardContent className="flex items-center justify-between">
              <div>
                <h4 className="text-lg font-semibold">
                  {dim.value}
                  {dim.tolerance && ` ±${dim.tolerance}`}
                  {dim.unit && ` ${dim.unit}`}
                </h4>
                <p className="text-sm text-muted-foreground mt-1">
                  Dimension #{index + 1}
                </p>
              </div>
              <Button
                variant="outline"
                size="icon"
                onClick={() => {
                  if (record && attachmentField) {
                    // Update record with extracted dimension
                    const fieldId = Object.keys(record.fields).find(key =>
                      fields?.some(f => f.id === key && f.type === 'dimension')
                    ) || ''

                    if (fieldId) {
                      api.patch(`/records/${record.id}`, {
                        fields: {
                          [fieldId]: {
                            value: parseFloat(dim.value),
                            tolerance: dim.tolerance ? parseFloat(dim.tolerance) : undefined,
                            unit: dim.unit,
                          }
                        }
                      }
                    })
                  }
                }}
              >
                <ArrowRight className="h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const renderMetadata = () => {
    if (!latestExtraction?.results?.metadata) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          No metadata extracted
        </div>
      )
    }

    const meta = latestExtraction.results.metadata

    return (
      <div className="space-y-4">
        {meta.title && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Document Title
              </CardTitle>
            </CardHeader>
            <CardContent>
              {meta.title}
            </CardContent>
          </Card>
        )}
        {meta.author && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Author
              </CardTitle>
            </CardHeader>
            <CardContent>
              {meta.author}
            </CardContent>
          </Card>
        )}
        {meta.created && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Created
              </CardTitle>
            </CardHeader>
            <CardContent>
              {new Date(meta.created).toLocaleString()}
            </CardContent>
          </Card>
        )}
        {meta.modified && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Modified
              </CardTitle>
            </CardHeader>
            <CardContent>
              {new Date(meta.modified).toLocaleString()}
            </CardContent>
          </Card>
        )}
      </div>
    )
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-5xl max-h-[90vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {getFileIcon()}
              <DialogTitle>
                Extraction Preview
              </DialogTitle>
              {latestExtraction && renderStatusBadge(latestExtraction.status)}
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>
          </DialogHeader>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-shrink-0">
          <TabsList className="w-full">
            <TabsTrigger value="preview">Preview</TabsTrigger>
            <TabsTrigger value="tables">Tables ({latestExtraction?.results?.tables?.length || 0})</TabsTrigger>
            <TabsTrigger value="dimensions">Dimensions ({latestExtraction?.results?.dimensions?.length || 0})</TabsTrigger>
            <TabsTrigger value="metadata">Metadata</TabsTrigger>
          </TabsList>

          {/* Preview Tab */}
          <TabsContent value="preview" className="mt-4 flex-1 overflow-auto">
            <div className="h-full flex flex-col">
              {latestExtraction && latestExtraction.status === 'pending' && (
                <div className="flex-1 flex-col items-center justify-center text-center py-8">
                  <Search className="h-16 w-16 text-muted-foreground mb-4" />
                  <h3 className="text-lg font-semibold">Waiting for Extraction</h3>
                  <p className="text-sm text-muted-foreground">
                    Click below to start extracting data from the file
                  </p>
                </div>
              )}
              {latestExtraction?.error && (
                <div className="flex-1 flex-col items-center justify-center text-center py-8">
                  <AlertCircle className="h-16 w-16 text-red-500 mb-4" />
                  <h3 className="text-lg font-semibold text-red-500">Extraction Failed</h3>
                  <p className="text-sm text-muted-foreground mt-2">
                    {latestExtraction.error}
                  </p>
                  <Button variant="outline" onClick={() => triggerExtraction.mutate()}>
                    Retry
                  </Button>
                </div>
              )}
              {(latestExtraction?.status === 'pending' || latestExtraction?.error) && (
                <div className="flex-1 flex items-center justify-center py-8">
                  <Button
                    onClick={() => triggerExtraction.mutate()}
                    disabled={!fileUrl || !attachmentField}
                    size="lg"
                  >
                    <Search className="h-4 w-4 mr-2" />
                    Extract Data
                  </Button>
                </div>
              )}
              {latestExtraction?.status === 'processing' && (
                <div className="flex-1 flex-col items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary border-t-transparent"></div>
                  <p className="text-sm text-muted-foreground mt-4">
                    Extracting data from file...
                  </p>
                </div>
              )}
              {latestExtraction?.status === 'completed' && (
                renderPreview()
              )}
            </div>
          </TabsContent>

          {/* Tables Tab */}
          <TabsContent value="tables" className="mt-4 flex-1 overflow-auto">
            {renderTables()}
          </TabsContent>

          {/* Dimensions Tab */}
          <TabsContent value="dimensions" className="mt-4 flex-1 overflow-auto">
            {renderDimensions()}
          </TabsContent>

          {/* Metadata Tab */}
          <TabsContent value="metadata" className="mt-4 flex-1 overflow-auto">
            {renderMetadata()}
          </TabsContent>
        </Tabs>

        {/* Footer */}
        <DialogFooter className="flex-shrink-0">
          {latestExtraction?.status === 'completed' && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => triggerExtraction.mutate()}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Re-Extract
              </Button>
              <Button onClick={onClose}>
                Close
              </Button>
            </div>
          )}
          {latestExtraction?.status !== 'completed' && (
            <div className="ml-auto">
              <Button variant="ghost" onClick={onClose}>
                Close
              </Button>
            </div>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
