import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import {
  Image as ImageIcon,
  LayoutGrid,
  List as ListIcon,
  Search,
  X,
  MoreVertical,
  ZoomIn,
  ZoomOut,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Field, Record as RecordType } from '@/types'

interface GalleryItem {
  id: string
  record: RecordType
  imageField?: string
  imageValue?: string
  titleField?: string
  titleValue?: string
}

export interface GalleryViewProps {
  tableId: string
  fields: Field[]
}

export default function GalleryView({ tableId, fields }: GalleryViewProps) {
  const queryClient = useQueryClient()

  // State
  const [layoutMode, setLayoutMode] = useState<'grid' | 'list'>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedItem, setSelectedItem] = useState<GalleryItem | null>(null)
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [gridSize, setGridSize] = useState<'sm' | 'md' | 'lg'>('md')

  // Get image fields
  const imageFields = fields.filter(f => f.type === 'attachment')
  const imageField = imageFields[0]

  // Get title fields
  const titleFields = fields.filter(f => f.type === 'text' || f.type === 'long_text')
  const titleField = titleFields[0]

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

  // Create gallery items from records
  const galleryItems = useCallback((): GalleryItem[] => {
    if (!records) return []

    return records.map(record => ({
      id: record.id,
      record,
      imageField: imageField?.id,
      imageValue: imageField ? record.fields[imageField.id] as string : undefined,
      titleField: titleField?.id,
      titleValue: titleField ? record.fields[titleField.id] as string : undefined,
    }))
  }, [records, imageField, titleField])

  // Filter items based on search
  const filteredItems = useCallback((): GalleryItem[] => {
    const items = galleryItems()

    if (!searchQuery.trim()) {
      return items
    }

    const query = searchQuery.toLowerCase()

    return items.filter(item =>
      item.titleValue?.toLowerCase().includes(query) ||
      Object.values(item.record.fields).some(v =>
        String(v || '').toLowerCase().includes(query)
      )
    )
  }, [galleryItems, searchQuery])

  // Toggle selection
  const toggleSelection = useCallback((itemId: string) => {
    setSelectedItems(prev => {
      const next = new Set(prev)
      if (next.has(itemId)) {
        next.delete(itemId)
      } else {
        next.add(itemId)
      }
      return next
    })
  }, [])

  // Clear selection
  const clearSelection = useCallback(() => {
    setSelectedItems(new Set())
  }, [])

  // Toggle select all
  const toggleSelectAll = useCallback(() => {
    const items = filteredItems()
    if (selectedItems.size === items.length) {
      clearSelection()
    } else {
      setSelectedItems(new Set(items.map(i => i.id)))
    }
  }, [filteredItems, selectedItems.size, clearSelection])

  // Handle delete
  const handleDelete = useCallback((item: GalleryItem) => {
    if (confirm('Delete this record?')) {
      deleteRecord.mutate(item.id)
    }
  }, [deleteRecord])

  // Handle bulk delete
  const handleBulkDelete = useCallback(() => {
    if (confirm(`Delete ${selectedItems.size} selected item${selectedItems.size > 1 ? 's' : ''}?`)) {
      selectedItems.forEach(id => {
        deleteRecord.mutate(id)
      })
      clearSelection()
    }
  }, [selectedItems, deleteRecord, clearSelection])

  // Handle grid resize
  const handleGridResize = useCallback((delta: number) => {
    const sizes = ['sm', 'md', 'lg'] as const
    const currentIndex = sizes.indexOf(gridSize)
    const newIndex = Math.max(0, Math.min(sizes.length - 1, currentIndex + delta))
    setGridSize(sizes[newIndex])
  }, [gridSize])

  const gridSizes = {
    sm: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5',
    md: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6',
    lg: 'grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4',
  }

  const items = filteredItems()

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
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-semibold">Gallery</h2>

          {/* Layout Toggle */}
          <div className="flex border rounded-md">
            <Button
              variant={layoutMode === 'grid' ? 'default' : 'ghost'}
              size="icon"
              className="rounded-none rounded-l-md"
              onClick={() => setLayoutMode('grid')}
            >
              <LayoutGrid className="h-4 w-4" />
            </Button>
            <Button
              variant={layoutMode === 'list' ? 'default' : 'ghost'}
              size="icon"
              className="rounded-none rounded-r-md"
              onClick={() => setLayoutMode('list')}
            >
              <ListIcon className="h-4 w-4" />
            </Button>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4 py-1.5 border rounded-md text-sm w-64 focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Selection Actions */}
          {selectedItems.size > 0 && (
            <>
              <span className="text-sm text-muted-foreground">
                {selectedItems.size} selected
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={clearSelection}
              >
                Clear
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleBulkDelete}
              >
                Delete
              </Button>
            </>
          )}

          {/* Grid Size Controls */}
          {layoutMode === 'grid' && (
            <div className="flex items-center gap-1 border rounded-md px-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handleGridResize(-1)}
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => handleGridResize(1)}
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Gallery Content */}
      <div className="flex-1 overflow-auto p-4">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <ImageIcon className="h-16 w-16 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Records</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              {searchQuery
                ? 'No records match your search'
                : 'Add records to see them in the gallery view'}
            </p>
          </div>
        ) : layoutMode === 'grid' ? (
          <div className={cn("grid gap-4", gridSizes[gridSize])}>
            {items.map(item => (
              <div
                key={item.id}
                className={cn(
                  "relative group cursor-pointer rounded-lg overflow-hidden border-2",
                  selectedItems.has(item.id) ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                )}
                onClick={() => setSelectedItem(item)}
                onDoubleClick={() => setShowPreviewModal(true)}
              >
                {/* Image/Thumbnail */}
                {item.imageValue ? (
                  <div className="aspect-square bg-muted">
                    <img
                      src={String(item.imageValue)}
                      alt={item.titleValue || 'Untitled'}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  </div>
                ) : (
                  <div className="aspect-square bg-muted/30 flex items-center justify-center">
                    <ImageIcon className="h-16 w-16 text-muted-foreground/50" />
                  </div>
                )}

                {/* Selection Checkbox */}
                <div
                  className={cn(
                    "absolute top-2 left-2 p-1 rounded bg-background/80 backdrop-blur-sm transition-opacity opacity-0 group-hover:opacity-100",
                    selectedItems.has(item.id) && "opacity-100"
                  )}
                  onClick={(e) => {
                    e.stopPropagation()
                    toggleSelection(item.id)
                  }}
                >
                  <div className={cn(
                    "w-4 h-4 border rounded flex items-center justify-center text-xs",
                    selectedItems.has(item.id) ? "bg-primary border-primary text-white" : "border-border"
                  )}>
                    {selectedItems.has(item.id) && '✓'}
                  </div>
                </div>

                {/* Title Overlay */}
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-3">
                  <h3 className="text-white text-sm font-medium truncate">
                    {item.titleValue || 'Untitled'}
                  </h3>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {items.map(item => (
              <div
                key={item.id}
                className={cn(
                  "relative group flex items-center gap-4 p-4 border rounded-lg cursor-pointer",
                  selectedItems.has(item.id) ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
                )}
                onClick={() => setSelectedItem(item)}
              >
                {/* Image/Thumbnail */}
                {item.imageValue ? (
                  <div className="w-16 h-16 rounded bg-muted overflow-hidden flex-shrink-0">
                    <img
                      src={String(item.imageValue)}
                      alt={item.titleValue || 'Untitled'}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  </div>
                ) : (
                  <div className="w-16 h-16 rounded bg-muted/30 flex items-center justify-center flex-shrink-0">
                    <ImageIcon className="h-8 w-8 text-muted-foreground/50" />
                  </div>
                )}

                {/* Title */}
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-sm truncate">
                    {item.titleValue || 'Untitled'}
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    {Object.keys(item.record.fields).length} fields
                  </p>
                </div>

                {/* Actions */}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDelete(item)
                  }}
                >
                  <X className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Select All Button */}
      {items.length > 0 && selectedItems.size === 0 && (
        <Button
          variant="outline"
          size="sm"
          onClick={toggleSelectAll}
          className="fixed bottom-4 right-4"
        >
          Select All ({items.length})
        </Button>
      )}

      {/* Preview Modal */}
      {showPreviewModal && selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card rounded-lg shadow-lg max-w-4xl w-full mx-4 max-h-[90vh] flex flex-col">
            {/* Header */}
            <div className="flex items-start justify-between p-4 border-b">
              <h3 className="text-lg font-semibold">{selectedItem.titleValue || 'Untitled'}</h3>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  setShowPreviewModal(false)
                  setSelectedItem(null)
                }}
              >
                <X className="h-5 w-5" />
              </Button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-6">
              {selectedItem.imageValue && (
                <div className="mb-6">
                  <img
                    src={String(selectedItem.imageValue)}
                    alt={selectedItem.titleValue || 'Untitled'}
                    className="w-full rounded-lg"
                  />
                </div>
              )}

              <div className="space-y-4">
                {Object.entries(selectedItem.record.fields).map(([key, value]) => {
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
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
