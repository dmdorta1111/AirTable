import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as zod from 'zod'
import { api } from '@/lib/api'
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogDescription, 
  DialogFooter 
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Loader2, Plus, Trash2 } from 'lucide-react'
import type { FieldType, Field } from '@/types'

const createTableSchema = zod.object({
  name: zod.string().min(1, 'Name is required').max(100, 'Name too long'),
  description: zod.string().max(500, 'Description too long').optional(),
})

interface CreateTableModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  baseId: string
}

export default function CreateTableModal({ open, onOpenChange, baseId }: CreateTableModalProps) {
  const queryClient = useQueryClient()
  
  const form = useForm<zod.infer<typeof createTableSchema>>({
    resolver: zodResolver(createTableSchema),
    defaultValues: {
      name: '',
      description: '',
    },
  })

  const [fields, setFields] = useState<Partial<Field>[]>([
    { id: crypto.randomUUID(), name: 'Name', type: 'text', order: 0, is_primary: true, options: {} },
  ])

  const createTable = useMutation({
    mutationFn: async (data: zod.infer<typeof createTableSchema>) => {
      const response = await api.post('/tables', {
        base_id: baseId,
        ...data,
        fields: fields
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tables', baseId] })
      queryClient.invalidateQueries({ queryKey: ['bases'] })
      form.reset()
      setFields([])
      onOpenChange(false)
    },
  })

  const addField = () => {
    const newField: Partial<Field> = {
      id: crypto.randomUUID(),
      name: '',
      type: 'text',
      order: fields.length,
      is_primary: false,
      options: {}
    }
    setFields([...fields, newField])
  }

  const removeField = (fieldId: string) => {
    setFields(fields.filter(f => f.id !== fieldId))
  }

  const updateField = (fieldId: string, updates: Partial<Field>) => {
    setFields(fields.map(f => f.id === fieldId ? { ...f, ...updates } : f))
  }

  const onSubmit = form.handleSubmit((data) => {
    createTable.mutate(data)
  })

  const fieldTypeOptions: { label: string; value: FieldType }[] = [
    { label: 'Text', value: 'text' },
    { label: 'Long Text', value: 'long_text' },
    { label: 'Number', value: 'number' },
    { label: 'Currency', value: 'currency' },
    { label: 'Percent', value: 'percent' },
    { label: 'Checkbox', value: 'checkbox' },
    { label: 'Date', value: 'date' },
    { label: 'Date & Time', value: 'datetime' },
    { label: 'Single Select', value: 'single_select' },
    { label: 'Multi Select', value: 'multi_select' },
    { label: 'Attachment', value: 'attachment' },
    { label: 'URL', value: 'url' },
    { label: 'Email', value: 'email' },
    { label: 'Phone', value: 'phone' },
  ]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Table</DialogTitle>
          <DialogDescription>
            Define your table structure with fields. The first field becomes the primary field.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-6">
          {/* Table info */}
          <div className="space-y-2">
            <div>
              <Label htmlFor="name">Table Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Tasks, Contacts, Orders"
                {...form.register('name')}
                disabled={createTable.isPending}
              />
              {form.formState.errors.name && (
                <p className="text-sm text-destructive">
                  {form.formState.errors.name.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="description">Description</Label>
              <textarea
                id="description"
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="What is this table for?..."
                {...form.register('description')}
                disabled={createTable.isPending}
              />
            </div>
          </div>

          {/* Fields */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium">Fields</h3>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addField}
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Field
              </Button>
            </div>

            <div className="space-y-2">
              {fields.map((field) => (
                <div key={field.id} className="flex gap-2 items-start">
                  <div className="flex-1 grid grid-cols-[auto_1fr_auto] gap-2">
                    <Input
                      placeholder="Field name"
                      value={field.name}
                      onChange={(e) => updateField(field.id!, { name: e.target.value })}
                      disabled={createTable.isPending || field.is_primary}
                    />
                    <select
                      className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      value={field.type}
                      onChange={(e) => updateField(field.id!, { type: e.target.value as FieldType })}
                      disabled={createTable.isPending}
                    >
                      {fieldTypeOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    {!field.is_primary && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => removeField(field.id!)}
                        disabled={createTable.isPending}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createTable.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createTable.isPending}>
              {createTable.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Table'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
