import { useState, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { X, Plus, Trash2, Zap, ArrowRight, Play, Clock, Mail, MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Field } from '@/types'

export interface AutomationTrigger {
  id: string
  type: 'record_created' | 'record_updated' | 'record_deleted' | 'field_updated'
  config: {
    field_id?: string
    conditions?: Array<{
      field_id: string
      operator: 'equals' | 'not_equals' | 'contains' | 'greater_than' | 'less_than'
      value: unknown
    }>
  }
}

export interface AutomationAction {
  id: string
  type: 'send_email' | 'send_slack' | 'update_record' | 'create_record' | 'webhook'
  config: {
    email?: string
    slack_webhook_url?: string
    record_id?: string
    update_fields?: { [key: string]: unknown }
    webhook_url?: string
  }
}

export interface Automation {
  id: string
  name: string
  description?: string
  table_id: string
  is_active: boolean
  triggers: AutomationTrigger[]
  actions: AutomationAction[]
  created_at: string
  updated_at: string
}

export interface AutomationBuilderProps {
  tableId: string
  fields: Field[]
  automation?: Automation | null
  onClose: () => void
}

export default function AutomationBuilder({
  tableId,
  fields,
  automation,
  onClose
}: AutomationBuilderProps) {
  const queryClient = useQueryClient()
  const isEditing = !!automation

  const [name, setName] = useState(automation?.name || '')
  const [description, setDescription] = useState(automation?.description || '')
  const [isActive, setIsActive] = useState(automation?.is_active ?? true)
  const [triggers, setTriggers] = useState<AutomationTrigger[]>(automation?.triggers || [])
  const [actions, setActions] = useState<AutomationAction[]>(automation?.actions || [])

  // Create automation mutation
  const createAutomation = useMutation({
    mutationFn: async (data: Omit<Automation, 'id' | 'created_at' | 'updated_at'>) => {
      return api.post<Automation>('/automations', data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['automations', tableId] })
      onClose()
    },
  })

  // Update automation mutation
  const updateAutomation = useMutation({
    mutationFn: async (data: Partial<Automation>) => {
      return api.patch<Automation>(`/automations/${automation!.id}`, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['automations', tableId] })
      onClose()
    },
  })

  // Save automation
  const handleSave = () => {
    const automationData = {
      name: name.trim(),
      description: description.trim(),
      table_id: tableId,
      is_active: isActive,
      triggers,
      actions,
    }

    if (isEditing) {
      updateAutomation.mutate(automationData)
    } else {
      createAutomation.mutate(automationData)
    }
  }

  // Add trigger
  const addTrigger = () => {
    setTriggers([...triggers, {
      id: `trigger-${Date.now()}`,
      type: 'record_created',
      config: {}
    }])
  }

  // Remove trigger
  const removeTrigger = (index: number) => {
    setTriggers(triggers.filter((_, i) => i !== index))
  }

  // Update trigger
  const updateTrigger = (index: number, updates: Partial<AutomationTrigger>) => {
    setTriggers(triggers.map((t, i) =>
      i === index ? { ...t, ...updates } : t
    ))
  }

  // Add action
  const addAction = () => {
    setActions([...actions, {
      id: `action-${Date.now()}`,
      type: 'send_email',
      config: {}
    }])
  }

  // Remove action
  const removeAction = (index: number) => {
    setActions(actions.filter((_, i) => i !== index))
  }

  // Update action
  const updateAction = (index: number, updates: Partial<AutomationAction>) => {
    setActions(actions.map((a, i) =>
      i === index ? { ...a, ...updates } : a
    ))
  }

  const triggerTypes: { label: string; value: AutomationTrigger['type'] }[] = [
    { label: 'When record is created', value: 'record_created' },
    { label: 'When record is updated', value: 'record_updated' },
    { label: 'When record is deleted', value: 'record_deleted' },
    { label: 'When field is updated', value: 'field_updated' },
  ]

  const actionTypes: { label: string; value: AutomationAction['type'] }[] = [
    { label: 'Send Email', value: 'send_email' },
    { label: 'Send Slack Message', value: 'send_slack' },
    { label: 'Update Record', value: 'update_record' },
    { label: 'Create Record', value: 'create_record' },
    { label: 'Webhook', value: 'webhook' },
  ]

  const getTriggerIcon = (type: AutomationTrigger['type']) => {
    switch (type) {
      case 'record_created':
        return <Plus className="h-4 w-4 text-green-500" />
      case 'record_updated':
        return <Play className="h-4 w-4 text-blue-500" />
      case 'record_deleted':
        return <Trash2 className="h-4 w-4 text-red-500" />
      case 'field_updated':
        return <ArrowRight className="h-4 w-4 text-purple-500" />
    }
  }

  const getActionIcon = (type: AutomationAction['type']) => {
    switch (type) {
      case 'send_email':
        return <Mail className="h-4 w-4 text-blue-500" />
      case 'send_slack':
        return <MessageSquare className="h-4 w-4 text-green-500" />
      case 'update_record':
        return <Play className="h-4 w-4 text-purple-500" />
      case 'create_record':
        return <Plus className="h-4 w-4 text-green-500" />
      case 'webhook':
        return <Zap className="h-4 w-4 text-orange-500" />
    }
  }

  const isValid = name.trim() && triggers.length > 0 && actions.length > 0

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <DialogTitle>
              {isEditing ? 'Edit Automation' : 'New Automation'}
            </DialogTitle>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>
        </DialogHeader>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {/* Basic Settings */}
          <div className="space-y-4">
            <div>
              <Label htmlFor="automation-name">Name *</Label>
              <Input
                id="automation-name"
                placeholder="Enter automation name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="automation-description">Description</Label>
              <Textarea
                id="automation-description"
                placeholder="Describe what this automation does"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="automation-active"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="h-4 w-4"
              />
              <Label htmlFor="automation-active" className="cursor-pointer">
                Active
              </Label>
            </div>
          </div>

          {/* Triggers */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Triggers</h3>
              <Button
                variant="outline"
                size="sm"
                onClick={addTrigger}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Trigger
              </Button>
            </div>

            {triggers.map((trigger, index) => (
              <div
                key={trigger.id}
                className="border rounded-lg p-4 space-y-4"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    {getTriggerIcon(trigger.type)}
                    <div className="flex-1">
                      <Select
                        value={trigger.type}
                        onValueChange={(value) => updateTrigger(index, { type: value as AutomationTrigger['type'] })}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select trigger type" />
                        </SelectTrigger>
                        <SelectContent>
                          {triggerTypes.map(t => (
                            <SelectItem key={t.value} value={t.value}>
                              {t.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      {trigger.type === 'field_updated' && (
                        <Select
                          value={trigger.config.field_id || ''}
                          onValueChange={(value) => updateTrigger(index, {
                            config: { ...trigger.config, field_id: value }
                          })}
                        >
                          <SelectTrigger className="w-full mt-2">
                            <SelectValue placeholder="Select field" />
                          </SelectTrigger>
                          <SelectContent>
                            {fields.map(f => (
                              <SelectItem key={f.id} value={f.id}>
                                {f.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeTrigger(index)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </div>
            ))}

            {triggers.length === 0 && (
              <div className="text-center text-muted-foreground py-8 border-2 border-dashed rounded-lg">
                <Zap className="h-8 w-8 mx-auto mb-2 text-muted-foreground/50" />
                <p>No triggers configured yet</p>
                <p className="text-sm">Add at least one trigger to define when this automation runs</p>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Actions</h3>
              <Button
                variant="outline"
                size="sm"
                onClick={addAction}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Action
              </Button>
            </div>

            {actions.map((action, index) => (
              <div
                key={action.id}
                className="border rounded-lg p-4 space-y-4"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    {getActionIcon(action.type)}
                    <div className="flex-1">
                      <Select
                        value={action.type}
                        onValueChange={(value) => updateAction(index, { type: value as AutomationAction['type'] })}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select action type" />
                        </SelectTrigger>
                        <SelectContent>
                          {actionTypes.map(a => (
                            <SelectItem key={a.value} value={a.value}>
                              {a.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      {/* Action config based on type */}
                      {action.type === 'send_email' && (
                        <div className="mt-2">
                          <Label htmlFor={`email-${index}`}>Email Address</Label>
                          <Input
                            id={`email-${index}`}
                            type="email"
                            placeholder="recipient@example.com"
                            value={action.config.email || ''}
                            onChange={(e) => updateAction(index, {
                              config: { ...action.config, email: e.target.value }
                            })}
                          />
                        </div>
                      )}

                      {action.type === 'send_slack' && (
                        <div className="mt-2">
                          <Label htmlFor={`slack-${index}`}>Slack Webhook URL</Label>
                          <Input
                            id={`slack-${index}`}
                            type="url"
                            placeholder="https://hooks.slack.com/services/..."
                            value={action.config.slack_webhook_url || ''}
                            onChange={(e) => updateAction(index, {
                              config: { ...action.config, slack_webhook_url: e.target.value }
                            })}
                          />
                        </div>
                      )}

                      {action.type === 'webhook' && (
                        <div className="mt-2">
                          <Label htmlFor={`webhook-${index}`}>Webhook URL</Label>
                          <Input
                            id={`webhook-${index}`}
                            type="url"
                            placeholder="https://example.com/webhook"
                            value={action.config.webhook_url || ''}
                            onChange={(e) => updateAction(index, {
                              config: { ...action.config, webhook_url: e.target.value }
                            })}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeAction(index)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </div>
            ))}

            {actions.length === 0 && (
              <div className="text-center text-muted-foreground py-8 border-2 border-dashed rounded-lg">
                <Clock className="h-8 w-8 mx-auto mb-2 text-muted-foreground/50" />
                <p>No actions configured yet</p>
                <p className="text-sm">Add at least one action to define what happens</p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <DialogFooter className="flex-shrink-0">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={!isValid || createAutomation.isPending || updateAutomation.isPending}
          >
            {isEditing ? 'Update Automation' : 'Create Automation'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
