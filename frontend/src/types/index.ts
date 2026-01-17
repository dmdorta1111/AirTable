// Common types

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

// Workspace
export interface Workspace {
  id: string
  name: string
  description?: string
  icon?: string
  created_at: string
  updated_at: string
}

// Base
export interface Base {
  id: string
  workspace_id: string
  name: string
  description?: string
  icon?: string
  color?: string
  created_at: string
  updated_at: string
}

// Table
export interface Table {
  id: string
  base_id: string
  name: string
  description?: string
  primary_field_id?: string
  created_at: string
  updated_at: string
  fields?: Field[]
  views?: View[]
}

// Field Types
export type FieldType =
  | 'text'
  | 'long_text'
  | 'rich_text'
  | 'number'
  | 'currency'
  | 'percent'
  | 'checkbox'
  | 'date'
  | 'datetime'
  | 'duration'
  | 'single_select'
  | 'multi_select'
  | 'status'
  | 'linked_record'
  | 'lookup'
  | 'rollup'
  | 'count'
  | 'attachment'
  | 'url'
  | 'email'
  | 'phone'
  | 'user'
  | 'created_by'
  | 'modified_by'
  | 'created_time'
  | 'modified_time'
  | 'formula'
  | 'autonumber'
  | 'barcode'
  | 'rating'
  | 'dimension'
  | 'gdt'
  | 'thread'
  | 'surface_finish'
  | 'material'

export interface SelectOption {
  id: string
  name: string
  color: string
}

export interface FieldOptions {
  // Text
  max_length?: number
  enable_rich_text?: boolean
  
  // Number
  precision?: number
  allow_negative?: boolean
  currency_symbol?: string
  
  // Date
  date_format?: string
  time_format?: string
  include_time?: boolean
  timezone?: string
  
  // Select
  choices?: SelectOption[]
  
  // Linked Record
  linked_table_id?: string
  allow_multiple?: boolean
  
  // Lookup/Rollup
  linked_field_id?: string
  lookup_field_id?: string
  rollup_field_id?: string
  rollup_function?: string
  
  // Formula
  formula?: string
  
  // Rating
  max?: number
  icon?: string
  
  // Attachment
  allowed_types?: string[]
  max_size?: number
  
  // Engineering
  unit?: string
  tolerance_type?: string
  standard?: string
}

export interface Field {
  id: string
  table_id: string
  name: string
  type: FieldType
  options: FieldOptions
  is_primary: boolean
  order: number
  created_at: string
  updated_at: string
}

// View Types
export type ViewType = 'grid' | 'kanban' | 'calendar' | 'gallery' | 'form' | 'gantt' | 'timeline'

export interface ViewFilter {
  field: string
  operator: string
  value: unknown
}

export interface ViewSort {
  field: string
  direction: 'asc' | 'desc'
}

export interface ViewConfig {
  // Grid
  row_height?: 'short' | 'medium' | 'tall'
  frozen_columns?: number
  
  // Kanban
  group_field_id?: string
  stack_field_id?: string
  
  // Calendar
  date_field_id?: string
  end_date_field_id?: string
  
  // Gallery
  cover_field_id?: string
  card_fields?: string[]
  
  // Form
  fields?: string[]
  submit_text?: string
  
  // Gantt
  start_field_id?: string
  end_field_id?: string
  dependency_field_id?: string
  
  // Timeline
  group_field_id?: string
}

export interface View {
  id: string
  table_id: string
  name: string
  type: ViewType
  config: ViewConfig
  filters?: ViewFilter[]
  sorts?: ViewSort[]
  hidden_fields?: string[]
  field_order?: string[]
  is_locked: boolean
  is_personal: boolean
  order: number
  created_at: string
  updated_at: string
}

// Record
export interface Record {
  id: string
  table_id: string
  fields: { [fieldId: string]: unknown }
  created_at: string
  updated_at: string
  created_by?: string
  modified_by?: string
}
