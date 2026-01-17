import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { X, Plus, Filter, ArrowUpDown, Group } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Field } from '@/types'

export interface FilterCondition {
  field_id: string
  operator: 'equals' | 'not_equals' | 'contains' | 'not_contains' | 'greater_than' | 'less_than' | 'is_empty' | 'is_not_empty'
  value: unknown
}

export interface SortCondition {
  field_id: string
  direction: 'asc' | 'desc'
}

export interface GroupCondition {
  field_id: string
}

export interface FilterPanelProps {
  tableId: string
  fields: Field[]
  onClose: () => void
}

export default function FilterPanel({
  tableId,
  fields,
  onClose
}: FilterPanelProps) {
  const queryClient = useQueryClient()

  const [filters, setFilters] = useState<FilterCondition[]>([])
  const [sorts, setSorts] = useState<SortCondition[]>([])
  const [groups, setGroups] = useState<GroupCondition[]>([])
  const [activeTab, setActiveTab] = useState<'filters' | 'sort' | 'group'>('filters')

  // Get operators based on field type
  const getOperatorsForField = (field: Field): FilterCondition['operator'][] => {
    const baseOperators = [
      'is_empty',
      'is_not_empty'
    ]

    switch (field.type) {
      case 'text':
      case 'long_text':
      case 'email':
      case 'url':
        return [
          'equals',
          'not_equals',
          'contains',
          'not_contains',
          ...baseOperators
        ] as FilterCondition['operator'][]

      case 'number':
      case 'currency':
      case 'percent':
        return [
          'equals',
          'not_equals',
          'greater_than',
          'less_than',
          ...baseOperators
        ] as FilterCondition['operator'][]

      case 'date':
      case 'datetime':
        return [
          'equals',
          'not_equals',
          'greater_than',
          'less_than',
          ...baseOperators
        ] as FilterCondition['operator'][]

      case 'checkbox':
        return [
          'equals',
          ...baseOperators
        ] as FilterCondition['operator'][]

      case 'single_select':
      case 'multi_select':
        return [
          'equals',
          'not_equals',
          ...baseOperators
        ] as FilterCondition['operator'][]

      default:
        return baseOperators
    }
  }

  // Get field by ID
  const getFieldById = (fieldId: string) => fields.find(f => f.id === fieldId)

  // Add new filter
  const addFilter = () => {
    const field = fields[0]
    if (!field) return

    const operators = getOperatorsForField(field)
    setFilters([...filters, {
      field_id: field.id,
      operator: operators[0],
      value: null
    }])
  }

  // Remove filter
  const removeFilter = (index: number) => {
    setFilters(filters.filter((_, i) => i !== index))
  }

  // Update filter
  const updateFilter = (index: number, updates: Partial<FilterCondition>) => {
    setFilters(filters.map((f, i) =>
      i === index ? { ...f, ...updates } : f
    ))
  }

  // Add sort
  const addSort = () => {
    const availableFields = fields.filter(f => !sorts.some(s => s.field_id === f.id))
    if (availableFields.length === 0) return

    setSorts([...sorts, {
      field_id: availableFields[0].id,
      direction: 'asc'
    }])
  }

  // Remove sort
  const removeSort = (index: number) => {
    setSorts(sorts.filter((_, i) => i !== index))
  }

  // Update sort
  const updateSort = (index: number, updates: Partial<SortCondition>) => {
    setSorts(sorts.map((s, i) =>
      i === index ? { ...s, ...updates } : s
    ))
  }

  // Toggle sort direction
  const toggleSortDirection = (index: number) => {
    const sort = sorts[index]
    setSorts(sorts.map((s, i) =>
      i === index ? { ...s, direction: sort.direction === 'asc' ? 'desc' : 'asc' } : s
    ))
  }

  // Add group
  const addGroup = () => {
    const availableFields = fields.filter(f => !groups.some(g => g.field_id === f.id))
    if (availableFields.length === 0) return

    setGroups([...groups, { field_id: availableFields[0].id }])
  }

  // Remove group
  const removeGroup = (index: number) => {
    setGroups(groups.filter((_, i) => i !== index))
  }

  // Update group
  const updateGroup = (index: number, updates: Partial<GroupCondition>) => {
    setGroups(groups.map((g, i) =>
      i === index ? { ...g, ...updates } : g
    ))
  }

  // Apply filters/sorts/groups to view
  const applyViewConfiguration = () => {
    // This would integrate with view system to persist configuration
    console.log('Apply filters:', filters)
    console.log('Apply sorts:', sorts)
    console.log('Apply groups:', groups)

    // Invalidate queries to refetch with new configuration
    queryClient.invalidateQueries({ queryKey: ['records', tableId] })
    onClose()
  }

  // Clear all
  const clearAll = () => {
    setFilters([])
    setSorts([])
    setGroups([])
  }

  const hasConfiguration = filters.length > 0 || sorts.length > 0 || groups.length > 0

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <DialogTitle>View Configuration</DialogTitle>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Tabs */}
          <div className="flex border-b">
            <Button
              variant={activeTab === 'filters' ? 'default' : 'ghost'}
              className={cn(
                "flex items-center gap-2 rounded-none border-b-2 border-transparent",
                activeTab === 'filters' && "border-primary"
              )}
              onClick={() => setActiveTab('filters')}
            >
              <Filter className="h-4 w-4" />
              Filters ({filters.length})
            </Button>
            <Button
              variant={activeTab === 'sort' ? 'default' : 'ghost'}
              className={cn(
                "flex items-center gap-2 rounded-none border-b-2 border-transparent",
                activeTab === 'sort' && "border-primary"
              )}
              onClick={() => setActiveTab('sort')}
            >
              <ArrowUpDown className="h-4 w-4" />
              Sort ({sorts.length})
            </Button>
            <Button
              variant={activeTab === 'group' ? 'default' : 'ghost'}
              className={cn(
                "flex items-center gap-2 rounded-none border-b-2 border-transparent",
                activeTab === 'group' && "border-primary"
              )}
              onClick={() => setActiveTab('group')}
            >
              <Group className="h-4 w-4" />
              Group ({groups.length})
            </Button>
          </div>
        </DialogHeader>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {activeTab === 'filters' && (
            <div className="space-y-4">
              {filters.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  No filters configured. Add a filter to get started.
                </div>
              ) : (
                filters.map((filter, index) => {
                  const field = getFieldById(filter.field_id)
                  const operators = getOperatorsForField(field!)

                  return (
                    <div
                      key={index}
                      className="flex gap-2 items-start"
                    >
                      <Select
                        value={filter.field_id}
                        onValueChange={(value) => updateFilter(index, { field_id: value })}
                      >
                        <SelectTrigger className="w-[200px]">
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

                      <Select
                        value={filter.operator}
                        onValueChange={(value) => updateFilter(index, { operator: value as FilterCondition['operator'] })}
                      >
                        <SelectTrigger className="w-[150px]">
                          <SelectValue placeholder="Operator" />
                        </SelectTrigger>
                        <SelectContent>
                          {operators.map(op => (
                            <SelectItem key={op} value={op}>
                              {op.replace(/_/g, ' ').toUpperCase()}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      {filter.operator !== 'is_empty' && filter.operator !== 'is_not_empty' && (
                        <Input
                          type="text"
                          placeholder="Value"
                          value={String(filter.value ?? '')}
                          onChange={(e) => updateFilter(index, {
                            value: field?.type === 'number' ? Number(e.target.value) : e.target.value
                          })}
                          className="flex-1"
                        />
                      )}

                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeFilter(index)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  )
                })
              )}

              <Button
                variant="outline"
                size="sm"
                onClick={addFilter}
                className="w-full"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Filter
              </Button>
            </div>
          )}

          {activeTab === 'sort' && (
            <div className="space-y-4">
              {sorts.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  No sort configured. Add a sort to order your data.
                </div>
              ) : (
                sorts.map((sort, index) => {
                  const field = getFieldById(sort.field_id)
                  return (
                    <div
                      key={index}
                      className="flex gap-2 items-center"
                    >
                      <span className="text-muted-foreground text-sm">#{index + 1}</span>

                      <Select
                        value={sort.field_id}
                        onValueChange={(value) => updateSort(index, { field_id: value })}
                      >
                        <SelectTrigger className="flex-1">
                          <SelectValue placeholder="Select field" />
                        </SelectTrigger>
                        <SelectContent>
                          {fields.filter(f => !sorts.some(s => s.field_id === f.id)).map(f => (
                            <SelectItem key={f.id} value={f.id}>
                              {f.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => toggleSortDirection(index)}
                      >
                        <ArrowUpDown className={cn(
                          "h-4 w-4",
                          sort.direction === 'desc' && "rotate-180"
                        )} />
                      </Button>

                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeSort(index)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  )
                })
              )}

              <Button
                variant="outline"
                size="sm"
                onClick={addSort}
                className="w-full"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Sort
              </Button>
            </div>
          )}

          {activeTab === 'group' && (
            <div className="space-y-4">
              {groups.length === 0 ? (
                <div className="text-center text-muted-foreground py-8">
                  No groups configured. Add a group to organize your data.
                </div>
              ) : (
                groups.map((group, index) => {
                  const field = getFieldById(group.field_id)
                  return (
                    <div
                      key={index}
                      className="flex gap-2 items-center"
                    >
                      <span className="text-muted-foreground text-sm">#{index + 1}</span>

                      <Select
                        value={group.field_id}
                        onValueChange={(value) => updateGroup(index, { field_id: value })}
                      >
                        <SelectTrigger className="flex-1">
                          <SelectValue placeholder="Select field" />
                        </SelectTrigger>
                        <SelectContent>
                          {fields.filter(f => !groups.some(g => g.field_id === f.id)).map(f => (
                            <SelectItem key={f.id} value={f.id}>
                              {f.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>

                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeGroup(index)}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  )
                })
              )}

              <Button
                variant="outline"
                size="sm"
                onClick={addGroup}
                className="w-full"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Group
              </Button>
            </div>
          )}
        </div>

        {/* Footer */}
        <DialogFooter className="flex-shrink-0">
          {hasConfiguration && (
            <Button variant="ghost" onClick={clearAll}>
              Clear All
            </Button>
          )}
          <Button
            onClick={applyViewConfiguration}
            className="ml-auto"
          >
            Apply Configuration
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
