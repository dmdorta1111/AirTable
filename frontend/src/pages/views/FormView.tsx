import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Send, ArrowLeft, Plus, Settings, FileText, ToggleLeft, ToggleRight, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Field, Record as RecordType } from '@/types'

export interface FormFieldConfig {
  id: string
  name: string
  type: Field['type']
  required: boolean
  placeholder?: string
  defaultValue?: unknown
  options?: string[] // For select fields
}

export interface FormViewProps {
  isPublic: boolean
  formId?: string // For public forms
  onBack?: () => void
}

export default function FormView({ isPublic, formId, onBack }: FormViewProps) {
  const { tableId } = useParams<{ tableId: string }>()
  const queryClient = useQueryClient()

  // Form configuration
  const [formName, setFormName] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [allowMultipleSubmissions, setAllowMultipleSubmissions] = useState(false)
  const [collectEmail, setCollectEmail] = useState(false)
  const [isPublished, setIsPublished] = useState(false)
  const [activeFields, setActiveFields] = useState<FormFieldConfig[]>([])
  const [formData, setFormData] = useState<Record<string, unknown>>({})
  const [submitted, setSubmitted] = useState(false)

  // Fetch table and fields
  const { data: table } = useQuery({
    queryKey: ['table', tableId],
    queryFn: async () => {
      const response = await api.get(`/tables/${tableId}`)
      return response.data
    },
    enabled: !!tableId && !isPublic,
  })

  const { data: fields } = useQuery({
    queryKey: ['fields', tableId],
    queryFn: async () => {
      const response = await api.get<{ items: Field[] }>(`/fields?table_id=${tableId}`)
      return response.data.items
    },
    enabled: !!tableId && !isPublic,
  })

  // For public forms, fetch form config
  const { data: formConfig } = useQuery({
    queryKey: ['form-config', formId],
    queryFn: async () => {
      const response = await api.get(`/forms/${formId}`)
      return response.data
    },
    enabled: !!isPublic && !!formId,
  })

  // Initialize form configuration from table fields or form config
  useEffect(() => {
    if (isPublic && formConfig) {
      setFormName(formConfig.name || '')
      setFormDescription(formConfig.description || '')
      setIsPublished(formConfig.is_published || false)
      setAllowMultipleSubmissions(formConfig.allow_multiple_submissions || false)
      setCollectEmail(formConfig.collect_email || false)

      const formFields = formConfig.fields || []
      setActiveFields(formFields.map(f => ({
        id: f.id,
        name: f.name,
        type: f.type,
        required: f.required || false,
        placeholder: `Enter ${f.name.toLowerCase()}`,
        defaultValue: f.default_value,
        options: f.options,
      })))
    } else if (fields && table) {
      // Initialize from table fields (default to all text fields)
      setFormName(table.name)
      setActiveFields(fields
        .filter(f => f.type === 'text' || f.type === 'long_text' || f.type === 'email' || f.type === 'number' || f.type === 'date' || f.type === 'single_select' || f.type === 'checkbox')
        .map(f => ({
          id: f.id,
          name: f.name,
          type: f.type,
          required: false,
          placeholder: `Enter ${f.name.toLowerCase()}`,
          defaultValue: null,
          options: f.options,
        }))
      ))
    }
  }, [isPublic, formConfig, fields, table])

  // Submit form mutation
  const submitForm = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      if (isPublic && formId) {
        return api.post(`/forms/${formId}/submissions`, data)
      } else {
        return api.post('/records', {
          table_id: tableId,
          fields: data,
        })
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', tableId] })
      setSubmitted(true)
      // Reset form after success if not allowing multiple submissions
      if (!allowMultipleSubmissions) {
        setTimeout(() => {
          setFormData({})
          setSubmitted(false)
        }, 2000)
      }
    },
  })

  // Update form field value
  const updateFieldValue = (fieldId: string, value: unknown) => {
    setFormData(prev => ({ ...prev, [fieldId]: value }))
  }

  // Add field to form
  const addField = () => {
    if (fields && fields.length > 0) {
      const availableFields = fields.filter(f =>
        !activeFields.some(af => af.id === f.id)
      )
      if (availableFields.length > 0) {
        const field = availableFields[0]
        setActiveFields([...activeFields, {
          id: field.id,
          name: field.name,
          type: field.type,
          required: false,
          placeholder: `Enter ${field.name.toLowerCase()}`,
          defaultValue: null,
          options: field.options,
        }])
      }
    }
  }

  // Remove field from form
  const removeField = (fieldId: string) => {
    setActiveFields(activeFields.filter(f => f.id !== fieldId))
    setFormData(prev => {
      const next = { ...prev }
      delete next[fieldId]
      return next
    })
  }

  // Move field up
  const moveFieldUp = (index: number) => {
    if (index > 0) {
      const newFields = [...activeFields]
      ;[newFields[index], newFields[index - 1]] = [newFields[index - 1], newFields[index]]
      setActiveFields(newFields)
    }
  }

  // Move field down
  const moveFieldDown = (index: number) => {
    if (index < activeFields.length - 1) {
      const newFields = [...activeFields]
      ;[newFields[index], newFields[index + 1]] = [newFields[index + 1], newFields[index]]
      setActiveFields(newFields)
    }
  }

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Validate required fields
    const missingFields = activeFields
      .filter(f => f.required && !formData[f.id])
      .map(f => f.name)

    if (missingFields.length > 0) {
      alert(`Please fill in required fields: ${missingFields.join(', ')}`)
      return
    }

    submitForm.mutate(formData)
  }

  // Render field based on type
  const renderField = (field: FormFieldConfig) => {
    const value = formData[field.id]

    switch (field.type) {
      case 'text':
      case 'email':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.id}>
              {field.name}
              {field.required && <span className="text-destructive">*</span>}
            </Label>
            <Input
              id={field.id}
              type={field.type}
              placeholder={field.placeholder}
              value={String(value ?? '')}
              onChange={(e) => updateFieldValue(field.id, e.target.value)}
              disabled={submitted}
            />
          </div>
        )

      case 'long_text':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.id}>
              {field.name}
              {field.required && <span className="text-destructive">*</span>}
            </Label>
            <Textarea
              id={field.id}
              placeholder={field.placeholder}
              value={String(value ?? '')}
              onChange={(e) => updateFieldValue(field.id, e.target.value)}
              rows={4}
              disabled={submitted}
            />
          </div>
        )

      case 'number':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.id}>
              {field.name}
              {field.required && <span className="text-destructive">*</span>}
            </Label>
            <Input
              id={field.id}
              type="number"
              placeholder={field.placeholder}
              value={value as number ?? ''}
              onChange={(e) => updateFieldValue(field.id, e.target.value ? Number(e.target.value) : null)}
              disabled={submitted}
            />
          </div>
        )

      case 'date':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.id}>
              {field.name}
              {field.required && <span className="text-destructive">*</span>}
            </Label>
            <Input
              id={field.id}
              type="date"
              value={value ? String(value).split('T')[0] : ''}
              onChange={(e) => updateFieldValue(field.id, e.target.value || null)}
              disabled={submitted}
            />
          </div>
        )

      case 'checkbox':
        return (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Checkbox
                id={field.id}
                checked={!!value}
                onCheckedChange={(checked) => updateFieldValue(field.id, checked)}
                disabled={submitted}
              />
              <Label htmlFor={field.id} className="cursor-pointer">
                {field.name}
                {field.required && <span className="text-destructive">*</span>}
              </Label>
            </div>
          </div>
        )

      case 'single_select':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.id}>
              {field.name}
              {field.required && <span className="text-destructive">*</span>}
            </Label>
            <Select
              value={String(value ?? '')}
              onValueChange={(val) => updateFieldValue(field.id, val)}
              disabled={submitted}
            >
              <SelectTrigger>
                <SelectValue placeholder={field.placeholder} />
              </SelectTrigger>
              <SelectContent>
                {field.options?.map(opt => (
                  <SelectItem key={opt} value={opt}>
                    {opt}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )

      default:
        return null
    }
  }

  if (!tableId && !formId) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Loading form...</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b bg-card">
        <div className="flex items-center gap-4">
          {onBack && (
            <Button variant="outline" size="icon" onClick={onBack}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )}
          <div>
            <h1 className="text-2xl font-bold">
              {formName || table?.name || 'Form'}
            </h1>
            {formDescription && (
              <p className="text-sm text-muted-foreground mt-1">
                {formDescription}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {!isPublic && (
            <Button
              variant="outline"
              size="sm"
              onClick={addField}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Field
            </Button>
          )}
        </div>
      </div>

      {/* Form Configuration (Admin) */}
      {!isPublic && (
        <div className="px-6 py-4 border-b bg-muted/30">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl">
            <div className="space-y-2">
              <Label htmlFor="form-name">Form Name</Label>
              <Input
                id="form-name"
                placeholder="Enter form name"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="form-description">Description</Label>
              <Textarea
                id="form-description"
                placeholder="Describe this form"
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                rows={2}
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Switch
                  id="allow-multiple"
                  checked={allowMultipleSubmissions}
                  onCheckedChange={setAllowMultipleSubmissions}
                />
                <Label htmlFor="allow-multiple" className="cursor-pointer">
                  Allow Multiple Submissions
                </Label>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Switch
                  id="collect-email"
                  checked={collectEmail}
                  onCheckedChange={setCollectEmail}
                />
                <Label htmlFor="collect-email" className="cursor-pointer">
                  Collect Email
                </Label>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Form Fields */}
      <div className="flex-1 overflow-auto p-6">
        {activeFields.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <FileText className="h-16 w-16 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Fields Yet</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              {!isPublic
                ? 'Add fields from your table to create this form'
                : 'No fields configured for this form'}
              }
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            {activeFields.map((field, index) => (
              <div
                key={field.id}
                className={cn(
                  "relative p-4 border rounded-lg",
                  field.required && "border-primary/30"
                )}
              >
                {/* Field controls */}
                {!isPublic && (
                  <div className="absolute top-2 right-2 flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => moveFieldUp(index)}
                      disabled={index === 0}
                      className="h-6 w-6"
                    >
                      <ToggleLeft className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => moveFieldDown(index)}
                      disabled={index === activeFields.length - 1}
                      className="h-6 w-6"
                    >
                      <ToggleRight className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeField(field.id)}
                      className="h-6 w-6 text-destructive"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                )}

                {/* Field content */}
                {renderField(field)}
              </div>
            ))}

            {/* Submit button */}
            <div className="flex items-center justify-center pt-4">
              <Button
                type="submit"
                size="lg"
                disabled={submitted}
                className="w-full max-w-md"
              >
                {submitted ? (
                  <>
                    <span className="mr-2">Submitted!</span>
                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8 0 0 1 8 8 0 0 0 1 18-8 0 0 0 1"></path>
                    </svg>
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Submit
                  </>
                )}
              </Button>
            </div>
          </form>
        )}
      </div>

      {/* Footer */}
      {!isPublic && (
        <div className="px-6 py-4 border-t bg-muted/30">
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              Form configuration is saved automatically
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
