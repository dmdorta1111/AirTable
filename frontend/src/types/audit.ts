/**
 * Audit log types for PyBase frontend.
 * Provides tamper-evident audit trail for compliance with SOC2, ISO27001, and ITAR.
 */

import type { CursorPage } from "./index"

/** Types of auditable actions */
export type AuditAction =
  // Record operations
  | "record.create"
  | "record.update"
  | "record.delete"
  | "record.bulk_create"
  | "record.bulk_update"
  | "record.bulk_delete"
  // Table operations
  | "table.create"
  | "table.update"
  | "table.delete"
  // Field operations
  | "field.create"
  | "field.update"
  | "field.delete"
  // View operations
  | "view.create"
  | "view.update"
  | "view.delete"
  // Authentication events
  | "user.login"
  | "user.logout"
  | "user.login_failed"
  | "user.password_reset"
  | "user.password_changed"
  // Workspace operations
  | "workspace.create"
  | "workspace.update"
  | "workspace.delete"
  | "workspace.member_add"
  | "workspace.member_remove"
  | "workspace.member_update"
  // API key operations
  | "api_key.create"
  | "api_key.delete"
  | "api_key.use"
  // Automation operations
  | "automation.create"
  | "automation.update"
  | "automation.delete"
  | "automation.run"
  | "automation.run_failed"
  // Export operations
  | "export.create"
  | "export.download"
  // System operations
  | "system.settings_update"
  | "audit.export"
  | "audit.query"

/** Audit log entry */
export interface AuditLog {
  id: string
  user_id: string | null
  user_email: string | null
  action: AuditAction
  resource_type: string
  resource_id: string | null
  table_id: string | null
  old_value: string | null
  new_value: string | null
  ip_address: string | null
  user_agent: string | null
  request_id: string | null
  integrity_hash: string
  previous_log_hash: string | null
  meta: string | null
  created_at: string
  updated_at: string
}

/** Audit log query parameters */
export interface AuditLogQuery {
  user_id?: string
  user_email?: string
  action?: AuditAction
  resource_type?: string
  resource_id?: string
  table_id?: string
  request_id?: string
  start_date?: string
  end_date?: string
  limit?: number
  offset?: number
}

/** Audit log list response */
export interface AuditLogListResponse {
  items: AuditLog[]
  total: number
  limit: number
  offset: number
}

/** Cursor paginated audit log response */
export type AuditLogCursorPage = CursorPage<AuditLog>

/** Export format options */
export type AuditExportFormat = "csv" | "json"

/** Audit log export request */
export interface AuditLogExportRequest {
  start_date?: string
  end_date?: string
  user_id?: string
  action?: AuditAction
  resource_type?: string
  format: AuditExportFormat
}

/** Audit log export response */
export interface AuditLogExportResponse {
  export_id: string
  status: "pending" | "processing" | "completed" | "failed"
  file_url: string | null
  created_at: string
  completed_at: string | null
}
