import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown'
import { Zap, Plus, Play, Pause, Trash2, Edit, MoreVertical } from 'lucide-react'
import { Switch } from '@/components/ui/switch'
import AutomationBuilder, type { Automation } from './AutomationBuilder'

export interface AutomationPanelProps {
  tableId: string
  onClose: () => void
}

export default function AutomationPanel({
  tableId,
  onClose
}: AutomationPanelProps) {
  const queryClient = useQueryClient()
  const [selectedAutomation, setSelectedAutomation] = useState<Automation | null>(null)
  const [showBuilder, setShowBuilder] = useState(false)

  // Fetch automations
  const { data: automations, isLoading } = useQuery({
    queryKey: ['automations', tableId],
    queryFn: async () => {
      const response = await api.get<{ items: Automation[] }>('/automations')
      return response.data.items.filter(a => a.table_id === tableId)
    },
    enabled: !!tableId,
    refetchInterval: 10000, // Refetch every 10 seconds
  })

  // Toggle automation status mutation
  const toggleAutomation = useMutation({
    mutationFn: async ({ id, is_active }: { id: string; is_active: boolean }) => {
      return api.patch<Automation>(`/automations/${id}`, { is_active })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['automations', tableId] })
    },
  })

  // Delete automation mutation
  const deleteAutomation = useMutation({
    mutationFn: async (id: string) => {
      return api.delete(`/automations/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['automations', tableId] })
    },
  })

  const handleToggle = (automation: Automation) => {
    toggleAutomation.mutate({
      id: automation.id,
      is_active: !automation.is_active
    })
  }

  const handleDelete = (automation: Automation) => {
    if (confirm(`Delete automation "${automation.name}"?`)) {
      deleteAutomation.mutate(automation.id)
    }
  }

  const handleEdit = (automation: Automation) => {
    setSelectedAutomation(automation)
    setShowBuilder(true)
  }

  const handleNew = () => {
    setSelectedAutomation(null)
    setShowBuilder(true)
  }

  const closeBuilder = () => {
    setShowBuilder(false)
    setSelectedAutomation(null)
  }

  return (
    <>
      {/* Automation List */}
      <Dialog open onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
          <DialogHeader className="flex-shrink-0">
            <div className="flex items-center justify-between">
              <DialogTitle>
                <div className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-primary" />
                  Automations
                </div>
              </DialogTitle>
              <Button variant="ghost" size="icon" onClick={onClose}>
                <Trash2 className="h-5 w-5" />
              </Button>
            </div>
            <DialogDescription>
              Configure automated workflows for this table
            </DialogDescription>
          </DialogHeader>

          {/* Content */}
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary border-t-transparent"></div>
              </div>
            ) : automations && automations.length > 0 ? (
              <div className="space-y-3">
                {automations.map((automation) => (
                  <div
                    key={automation.id}
                    className={cn(
                      "flex items-start gap-4 border rounded-lg p-4 transition-all",
                      automation.is_active ? "bg-card" : "bg-muted/30"
                    )}
                  >
                    {/* Status Toggle */}
                    <div className="flex-shrink-0">
                      <Switch
                        checked={automation.is_active}
                        onCheckedChange={() => handleToggle(automation)}
                        disabled={toggleAutomation.isPending}
                      />
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <h4 className="font-semibold text-base mb-1">
                        {automation.name}
                      </h4>
                      {automation.description && (
                        <p className="text-sm text-muted-foreground">
                          {automation.description}
                        </p>
                      )}

                      {/* Trigger info */}
                      <div className="flex items-center gap-2 mt-3 text-xs text-muted-foreground">
                        <span className="font-medium">
                          {automation.triggers.length} trigger{automation.triggers.length !== 1 ? 's' : ''}
                        </span>
                        <span>•</span>
                        <span className="font-medium">
                          {automation.actions.length} action{automation.actions.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex-shrink-0">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleEdit(automation)}>
                            <Edit className="h-4 w-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => handleDelete(automation)}
                            className="text-destructive"
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Zap className="h-16 w-16 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No automations yet</h3>
                <p className="text-sm text-muted-foreground max-w-sm mb-6">
                  Automations allow you to automatically trigger actions based on events in your table.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleNew}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Create First Automation
                </Button>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex-shrink-0 border-t px-6 py-4">
            <Button
              variant="outline"
              onClick={handleNew}
              className="w-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              New Automation
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Automation Builder */}
      {showBuilder && (
        <AutomationBuilder
          tableId={tableId}
          fields={[]} // TODO: Fetch fields for this table
          automation={selectedAutomation}
          onClose={closeBuilder}
        />
      )}
    </>
  )
}
