import { useState, useEffect } from 'react'
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Loader2 } from 'lucide-react'
import type { Field, FieldType, FieldOptions, SelectOption } from '@/types'

const fieldEditorSchema = zod.object({
  name: zod.string().min(1, 'Name is required').max(100, 'Name too long'),
  type: zod.enum([
    'text', 'long_text', 'rich_text', 'number', 'currency', 'percent',
    'checkbox', 'date', 'datetime', 'duration', 'single_select',
    'multi_select', 'status', 'linked_record', 'lookup', 'rollup',
    'count', 'attachment', 'url', 'email', 'phone', 'user',
    'created_by', 'modified_by', 'created_time', 'modified_time',
    'formula', 'autonumber', 'barcode', 'rating', 'dimension',
    'gdt', 'thread', 'surface_finish', 'material'
  ]),
  description: zod.string().max(500).optional(),
})

interface FieldEditorModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  field?: Field | null
  tableId?: string
}

export default function FieldEditorModal({ open, onOpenChange, field, tableId }: FieldEditorModalProps) {
  const queryClient = useQueryClient()
  const [choices, setChoices] = useState<SelectOption[]>([])
  
  const form = useForm<zod.infer<typeof fieldEditorSchema>>({
    resolver: zodResolver(fieldEditorSchema),
    defaultValues: {
      name: field?.name ?? '',
      type: field?.type ?? 'text',
      description: '',
    },
  })

  useEffect(() => {
    if (field?.options.choices) {
      setChoices(field.options.choices)
    }
  }, [field])

  const createField = useMutation({
    mutationFn: async (data: zod.infer<typeof fieldEditorSchema>) => {
      const response = await api.post('/fields', {
        table_id: tableId,
        name: data.name,
        type: data.type,
        options: buildOptions(data.type),
        order: 0,
        is_primary: false,
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fields', tableId] })
      form.reset()
      setChoices([])
      onOpenChange(false)
    },
  })

  const updateField = useMutation({
    mutationFn: async (data: zod.infer<typeof fieldEditorSchema>) => {
      if (!field) throw new Error('Field not found')
      const response = await api.patch(`/fields/${field.id}`, {
        name: data.name,
        type: data.type,
        options: buildOptions(data.type),
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fields', tableId] })
      form.reset()
      setChoices([])
      onOpenChange(false)
    },
  })

  const isEdit = !!field

  const buildOptions = (type: FieldType): FieldOptions => {
    const options: FieldOptions = {}
    
    switch (type) {
      case 'single_select':
      case 'multi_select':
      case 'status':
        options.choices = choices
        break
      
      case 'number':
        options.precision = 2
        options.allow_negative = true
        break
      
      case 'currency':
        options.currency_symbol = '$'
        options.precision = 2
        break
      
      case 'percent':
        options.precision = 0
        break
      
      case 'date':
        options.date_format = 'YYYY-MM-DD'
        break
      
      case 'datetime':
        options.date_format = 'YYYY-MM-DD'
        options.time_format = 'HH:mm'
        break
      
      case 'rating':
        options.max = 5
        options.icon = '★'
        break
      
      case 'dimension':
        options.unit = 'mm'
        break
    }
    
    return options
  }

  const addChoice = () => {
    const newChoice: SelectOption = {
      id: crypto.randomUUID(),
      name: '',
      color: 'default',
    }
    setChoices([...choices, newChoice])
  }

  const updateChoice = (choiceId: string, name: string) => {
    setChoices(choices.map(c => c.id === choiceId ? { ...c, name } : c))
  }

  const removeChoice = (choiceId: string) => {
    setChoices(choices.filter(c => c.id !== choiceId))
  }

  const onSubmit = form.handleSubmit((data) => {
    if (isEdit) {
      updateField.mutate(data)
    } else {
      createField.mutate(data)
    }
  })

  const fieldType = form.watch('type')
  const isPending = createField.isPending || updateField.isPending

  const showChoices = fieldType === 'single_select' || fieldType === 'multi_select' || fieldType === 'status'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Field' : 'Create Field'}</DialogTitle>
          <DialogDescription>
            Configure your field settings. Field type determines what kind of data can be stored.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-6">
          <div className="space-y-3">
            <div>
              <Label htmlFor="name">Field Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Task Name, Email, Due Date"
                {...form.register('name')}
                disabled={isPending}
              />
              {form.formState.errors.name && (
                <p className="text-sm text-destructive mt-1">
                  {form.formState.errors.name.message}
                </p>
              )}
            </div>

            <div>
              <Label htmlFor="type">Field Type *</Label>
              <Select
                value={fieldType}
                onValueChange={(value) => form.setValue('type', value as FieldType)}
                disabled={isPending || isEdit}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {fieldEditorSchema.shape.type.options.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type.replace(/_/g, ' ').replace(/\b\w/g, word => word.charAt(0).toUpperCase() + word.slice(1))}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {showChoices && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Choices</Label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addChoice}
                    disabled={isPending}
                  >
                    Add Choice
                  </Button>
                </div>
                {choices.map((choice) => (
                  <div key={choice.id} className="flex gap-2">
                    <Input
                      placeholder="Choice name"
                      value={choice.name}
                      onChange={(e) => updateChoice(choice.id, e.target.value)}
                      disabled={isPending}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => removeChoice(choice.id)}
                      disabled={isPending}
                      className="text-destructive"
                    >
                      ×
                    </Button>
                  </div>
                ))}
                {choices.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    Add at least one choice option
                  </p>
                )}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isPending || (showChoices && choices.length === 0)}>
              {isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                isEdit ? 'Save Changes' : 'Create Field'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
