import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Loader2 } from 'lucide-react'
import { api } from '@/lib/api'
import type { Record as RecordType, Field } from '@/types'

interface RecordDetailModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  record: RecordType | null
  fields: Field[]
  tableId: string
}

export default function RecordDetailModal({ open, onOpenChange, record, fields, tableId }: RecordDetailModalProps) {
  const queryClient = useQueryClient()

  const [localValues, setLocalValues] = useState<Record<string, unknown>>(() => {
    if (!record) return {}
    return { ...record.fields }
  })

  const updateRecord = useMutation({
    mutationFn: async (updated: Record<string, unknown>) => {
      if (!record) throw new Error('No record')
      const response = await api.patch(`/records/${record.id}`, { fields: updated })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', tableId] })
      onOpenChange(false)
    },
  })

  const handleChange = (fieldId: string, value: unknown) => {
    setLocalValues(prev => ({ ...prev, [fieldId]: value }))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateRecord.mutate(localValues)
  }

  if (!record) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Record Details</DialogTitle>
          <DialogDescription>Edit fields for this record.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {fields.map(field => (
            <div key={field.id} className="space-y-1">
              <Label htmlFor={field.id}>{field.name}</Label>
              <Input
                id={field.id}
                value={String(localValues[field.id] ?? '')}
                onChange={e => handleChange(field.id, e.target.value)}
                disabled={updateRecord.isPending}
              />
            </div>
          ))}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={updateRecord.isPending}>Cancel</Button>
            <Button type="submit" disabled={updateRecord.isPending}>
              {updateRecord.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
