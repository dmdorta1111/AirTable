import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import {
  Plus,
  X,
  Trash2,
  MoreVertical,
  Settings,
  Table as TableIcon,
  Eye,
  EyeOff,
  GripVertical,
  Hash,
  Type,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Field, Table as TableType } from '@/types'

export interface TableSettingsProps {
  tableId: string
  onClose: () => void
}

export default function TableSettings({ tableId, onClose }: TableSettingsProps) {
  const queryClient = useQueryClient()

  // Tabs
  const [activeTab, setActiveTab] = useState<'general' | 'fields' | 'permissions'>('general')

  // Table settings state
  const [tableName, setTableName] = useState('')
  const [tableDescription, setTableDescription] = useState('')
  const [icon, setIcon] = useState('database')

  // Fields state
  const [selectedFieldId, setSelectedFieldId] = useState<string | null>(null)

  // Fetch table data
  const { data: table } = useQuery({
    queryKey: ['table', tableId],
    queryFn: async () => {
      const response = await api.get<TableType>(`/tables/${tableId}`)
      return response.data
    },
    enabled: !!tableId,
  })

  // Fetch fields
  const { data: fields } = useQuery({
    queryKey: ['fields', tableId],
    queryFn: async () => {
      const response = await api.get<{ items: Field[] }>(`/fields?table_id=${tableId}`)
      return response.data.items
    },
    enabled: !!tableId && activeTab === 'fields',
  })

  // Initialize table settings
  useEffect(() => {
    if (table) {
      setTableName(table.name || '')
      setTableDescription(table.description || '')
    }
  }, [table])

  // Update table mutation
  const updateTable = useMutation({
    mutationFn: async (data: { name: string; description: string }) => {
      return api.patch<TableType>(`/tables/${tableId}`, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['table', tableId] })
    },
  })

  // Update field mutation
  const updateField = useMutation({
    mutationFn: async ({ fieldId, updates }: { fieldId: string; updates: Partial<Field> }) => {
      return api.patch<Field>(`/fields/${fieldId}`, updates)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fields', tableId] })
      setSelectedFieldId(null)
    },
  })

  // Delete field mutation
  const deleteField = useMutation({
    mutationFn: async (fieldId: string) => {
      return api.delete(`/fields/${fieldId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fields', tableId] })
    },
  })

  // Save table settings
  const handleSaveSettings = () => {
    updateTable.mutate({
      name: tableName.trim(),
      description: tableDescription.trim(),
    })
  }

  const selectedField = fields?.find(f => f.id === selectedFieldId)

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl max-h-[85vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <DialogTitle>
              <div className="flex items-center gap-2">
                <TableIcon className="h-5 w-5 text-primary" />
                Table Settings
              </div>
            </DialogTitle>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>
        </DialogHeader>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-shrink-0">
          <TabsList className="w-full">
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="fields">Fields</TabsTrigger>
            <TabsTrigger value="permissions">Permissions</TabsTrigger>
          </TabsList>

          {/* General Tab */}
          <TabsContent value="general" className="mt-4 space-y-6">
            <div>
              <Label htmlFor="table-name">Table Name</Label>
              <Input
                id="table-name"
                placeholder="Enter table name"
                value={tableName}
                onChange={(e) => setTableName(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="table-description">Description</Label>
              <Textarea
                id="table-description"
                placeholder="Describe this table"
                value={tableDescription}
                onChange={(e) => setTableDescription(e.target.value)}
                rows={4}
              />
            </div>
            <div>
              <Label htmlFor="table-icon">Icon</Label>
              <Input
                id="table-icon"
                placeholder="emoji"
                value={icon}
                onChange={(e) => setIcon(e.target.value)}
                maxLength={2}
              />
            </div>
          </TabsContent>

          {/* Fields Tab */}
          <TabsContent value="fields" className="mt-4">
            <div className="space-y-4">
              {/* Add field button */}
              <div className="flex justify-end mb-4">
                <Button variant="outline" size="sm">
                  <Plus className="h-4 w-4 mr-2" />
                  Add Field
                </Button>
              </div>

              {/* Fields list */}
              {fields && fields.length > 0 ? (
                <div className="space-y-2">
                  {fields.map((field, index) => (
                    <div
                      key={field.id}
                      className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded bg-primary/10 flex items-center justify-center text-lg">
                            {icon || field.type.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <h3 className="font-semibold">{field.name}</h3>
                            <p className="text-sm text-muted-foreground">
                              {field.type.replace(/_/g, ' ').toUpperCase()}
                            </p>
                          </div>
                        </div>

                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => setSelectedFieldId(field.id)}>
                              <Settings className="h-4 w-4 mr-2" />
                              Edit Settings
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => {
                              if (confirm(`Delete field "${field.name}"? This cannot be undone.`)) {
                                deleteField.mutate(field.id)
                              }
                            }} className="text-destructive">
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete Field
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>

                      {/* Field details */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label htmlFor={`field-name-${field.id}`}>Name</Label>
                          <Input
                            id={`field-name-${field.id}`}
                            value={selectedFieldId === field.id ? field.name : ''}
                            onChange={(e) => selectedFieldId === field.id && updateField.mutate({
                              fieldId: field.id,
                              updates: { name: e.target.value }
                            })}
                          />
                        </div>
                        <div>
                          <Label htmlFor={`field-type-${field.id}`}>Type</Label>
                          <Select
                            value={selectedFieldId === field.id ? field.type : ''}
                            onValueChange={(val) => updateField.mutate({
                              fieldId: field.id,
                              updates: { type: val as Field['type'] }
                            })}
                            disabled={selectedFieldId !== field.id}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Select type" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="text">Text</SelectItem>
                              <SelectItem value="long_text">Long Text</SelectItem>
                              <SelectItem value="number">Number</SelectItem>
                              <SelectItem value="currency">Currency</SelectItem>
                              <SelectItem value="percent">Percent</SelectItem>
                              <SelectItem value="date">Date</SelectItem>
                              <SelectItem value="datetime">Date & Time</SelectItem>
                              <SelectItem value="checkbox">Checkbox</SelectItem>
                              <SelectItem value="single_select">Single Select</SelectItem>
                              <SelectItem value="multi_select">Multi Select</SelectItem>
                              <SelectItem value="email">Email</SelectItem>
                              <SelectItem value="phone">Phone</SelectItem>
                              <SelectItem value="url">URL</SelectItem>
                              <SelectItem value="attachment">Attachment</SelectItem>
                              <SelectItem value="link">Link</SelectItem>
                              <SelectItem value="lookup">Lookup</SelectItem>
                              <SelectItem value="formula">Formula</SelectItem>
                              <SelectItem value="dimension">Dimension</SelectItem>
                              <SelectItem value="gdt">GD&T</SelectItem>
                              <SelectItem value="thread">Thread</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      {/* Advanced field options */}
                      {selectedFieldId === field.id && (
                        <div className="mt-4 pt-4 border-t space-y-4">
                          <div>
                            <label className="flex items-center justify-between mb-2">
                              <span className="text-sm font-medium">Required</span>
                              <Switch
                                checked={selectedField.required || false}
                                onCheckedChange={(checked) => updateField.mutate({
                                  fieldId: field.id,
                                  updates: { required: checked }
                                })}
                              />
                            </label>
                          </div>
                          <div>
                            <label htmlFor={`field-desc-${field.id}`} className="block text-sm font-medium mb-1">
                              Description
                            </label>
                            <Textarea
                              id={`field-desc-${field.id}`}
                              placeholder="Enter field description"
                              value={selectedField.description || ''}
                              onChange={(e) => updateField.mutate({
                                fieldId: field.id,
                              updates: { description: e.target.value }
                            })}
                              rows={2}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No fields yet. Add your first field to get started.
                </div>
              )}
            </div>
          </TabsContent>

          {/* Permissions Tab */}
          <TabsContent value="permissions" className="mt-4">
            <div className="text-center py-8 text-muted-foreground">
              <Settings className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-semibold mb-2">Permissions Coming Soon</h3>
              <p className="text-sm max-w-sm">
                Configure who can view, edit, and comment on this table.
              </p>
            </div>
          </TabsContent>
        </Tabs>

        {/* Footer */}
        <DialogFooter className="flex-shrink-0">
          {activeTab === 'general' && (
            <div className="flex-1">
              <Button variant="ghost" onClick={onClose}>
                Cancel
              </Button>
              <Button onClick={handleSaveSettings}>
                Save Changes
              </Button>
            </div>
          )}
          {activeTab !== 'general' && (
            <Button className="ml-auto" onClick={onClose}>
              Close
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
