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
import { Loader2 } from 'lucide-react'

const createBaseSchema = zod.object({
  name: zod.string().min(1, 'Name is required').max(100, 'Name too long'),
  description: zod.string().max(500, 'Description too long').optional(),
})

interface CreateBaseModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  workspaceId?: string
}

export default function CreateBaseModal({ open, onOpenChange, workspaceId }: CreateBaseModalProps) {
  const queryClient = useQueryClient()
  
  const form = useForm<zod.infer<typeof createBaseSchema>>({
    resolver: zodResolver(createBaseSchema),
    defaultValues: {
      name: '',
      description: '',
    },
  })

  const createBase = useMutation({
    mutationFn: async (data: zod.infer<typeof createBaseSchema>) => {
      const response = await api.post('/bases', {
        workspace_id: workspaceId,
        ...data
      })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bases'] })
      form.reset()
      onOpenChange(false)
    },
  })

  const onSubmit = form.handleSubmit((data) => {
    createBase.mutate(data)
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Base</DialogTitle>
          <DialogDescription>
            A base contains tables and records. Give it a descriptive name.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <div>
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                placeholder="e.g., Project Tracker, CRM, Inventory"
                {...form.register('name')}
                disabled={createBase.isPending}
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
                placeholder="Optional description for your base..."
                {...form.register('description')}
                disabled={createBase.isPending}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createBase.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createBase.isPending}>
              {createBase.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Base'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
