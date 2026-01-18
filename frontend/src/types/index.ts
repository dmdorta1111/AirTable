/**
 * Shared TypeScript types for PyBase frontend.
 */

export interface Id {
  id: string
}

export interface CreatedAt {
  created_at: string
}

export interface UpdatedAt {
  updated_at: string
}

export interface User extends Id, CreatedAt, UpdatedAt {
  email: string
  name?: string
  username?: string
}

export interface Workspace extends Id, CreatedAt, UpdatedAt {
  name: string
  description?: string
  created_by_id: string
}

export interface Base extends Id, CreatedAt, UpdatedAt {
  workspace_id: string
  name: string
  description?: string
  created_by_id: string
}

export interface Table extends Id, CreatedAt, UpdatedAt {
  base_id: string
  name: string
  description?: string
  created_by_id: string
  icon?: string
}

/** Options for select-type fields */
export interface SelectFieldOptions {
  choices?: Array<{ id: string; name: string; color?: string }>
}

/** Options for number/currency fields */
export interface NumberFieldOptions {
  precision?: number
  format?: string
  currency?: string
}

/** Options for date fields */
export interface DateFieldOptions {
  dateFormat?: string
  timeFormat?: string
  includeTime?: boolean
}

/** Options for linked record fields */
export interface LinkedRecordFieldOptions {
  linkedTableId?: string
  viewIdForRecordSelection?: string
  isReversed?: boolean
}

/** Options for formula fields */
export interface FormulaFieldOptions {
  formula?: string
  resultType?: "text" | "number" | "date" | "boolean"
}

/** Options for lookup/rollup fields */
export interface LookupFieldOptions {
  recordLinkFieldId?: string
  fieldIdInLinkedTable?: string
  rollupFunction?: string
}

/** Union of all field options */
export type FieldOptions =
  | SelectFieldOptions
  | NumberFieldOptions
  | DateFieldOptions
  | LinkedRecordFieldOptions
  | FormulaFieldOptions
  | LookupFieldOptions
  | Record<string, unknown>

export interface Field extends Id, CreatedAt, UpdatedAt {
  table_id: string
  name: string
  type: FieldType
  options?: FieldOptions
  description?: string
  required?: boolean
}

export type FieldType =
  | "text"
  | "long_text"
  | "number"
  | "checkbox"
  | "single_select"
  | "multi_select"
  | "date"
  | "datetime"
  | "duration"
  | "linked_record"
  | "lookup"
  | "rollup"
  | "formula"
  | "autonumber"
  | "attachment"
  | "url"
  | "email"
  | "phone"
  | "currency"
  | "percent"
  | "rating"
  | "status"

export interface Record extends Id, CreatedAt, UpdatedAt {
  table_id: string
  values: Record<string, unknown>
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface RegisterRequest {
  email: string
  password: string
  name?: string
}

export interface RegisterResponse {
  user: User
  access_token: string
}

export interface ViewType {
  type: "grid" | "kanban" | "calendar" | "gallery" | "form" | "gantt" | "timeline"
}

export interface View extends Id, CreatedAt, UpdatedAt {
  table_id: string
  name: string
  view_type: string
  is_default?: boolean
  type_config?: Record<string, unknown>
}