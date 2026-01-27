/**
 * Audit log API client for PyBase frontend.
 * Provides tamper-evident audit trail for compliance with SOC2, ISO27001, and ITAR.
 */

import type {
  AuditLog,
  AuditLogQuery,
  AuditLogListResponse,
  AuditExportFormat,
} from "@/types"
import { get } from "@/lib/api"

/**
 * Query audit logs with comprehensive filtering options.
 *
 * @param query - Audit log query parameters with filters and pagination
 * @returns Promise<AuditLogListResponse> with paginated audit logs
 *
 * @example
 * ```ts
 * // Get all audit logs
 * const logs = await listAuditLogs({})
 *
 * // Filter by user and action
 * const userLogs = await listAuditLogs({
 *   user_id: "user-123",
 *   action: "record.create"
 * })
 *
 * // Filter by date range
 * const recentLogs = await listAuditLogs({
 *   start_date: "2026-01-01T00:00:00Z",
 *   end_date: "2026-01-31T23:59:59Z",
 *   limit: 100
 * })
 * ```
 */
export async function listAuditLogs(
  query: AuditLogQuery = {}
): Promise<AuditLogListResponse> {
  const params = new URLSearchParams()

  // Add filters to query params
  if (query.user_id) {
    params.append("user_id", query.user_id)
  }

  if (query.user_email) {
    params.append("user_email", query.user_email)
  }

  if (query.action) {
    params.append("action", query.action)
  }

  if (query.resource_type) {
    params.append("resource_type", query.resource_type)
  }

  if (query.resource_id) {
    params.append("resource_id", query.resource_id)
  }

  if (query.table_id) {
    params.append("table_id", query.table_id)
  }

  if (query.request_id) {
    params.append("request_id", query.request_id)
  }

  if (query.start_date) {
    params.append("start_date", query.start_date)
  }

  if (query.end_date) {
    params.append("end_date", query.end_date)
  }

  // Add pagination params (with defaults)
  params.append("limit", String(query.limit ?? 100))
  params.append("offset", String(query.offset ?? 0))

  const queryString = params.toString()
  const url = `/api/v1/audit/logs${queryString ? `?${queryString}` : ""}`

  return get<AuditLogListResponse>(url)
}

/**
 * Get a specific audit log entry by ID.
 *
 * @param logId - The audit log entry ID
 * @returns Promise<AuditLog> with full audit log details
 *
 * @example
 * ```ts
 * const log = await getAuditLog("audit-123")
 * console.log(log.action, log.user_email, log.created_at)
 * ```
 */
export async function getAuditLog(logId: string): Promise<AuditLog> {
  return get<AuditLog>(`/api/v1/audit/logs/${logId}`)
}

/**
 * Verify the integrity of an audit log entry using tamper-evident hash chain.
 *
 * This function checks if the audit log has been tampered with by verifying
 * the hash chain. Any modification to the log entry will be detected.
 *
 * @param logId - The audit log entry ID to verify
 * @returns Promise<{valid: boolean, message: string}> with verification result
 *
 * @example
 * ```ts
 * const verification = await verifyAuditLogIntegrity("audit-123")
 * if (verification.valid) {
 *   console.log("Audit log integrity verified")
 * } else {
 *   console.error("Audit log tampering detected:", verification.message)
 * }
 * ```
 */
export async function verifyAuditLogIntegrity(logId: string): Promise<{
  valid: boolean
  message: string
}> {
  return get<{
    valid: boolean
    message: string
  }>(`/api/v1/audit/logs/${logId}/verify`)
}

/**
 * Export audit logs as a downloadable file (CSV or JSON).
 *
 * This function initiates an export of audit logs with the specified filters.
 * The export is returned as a streaming download.
 *
 * @param format - Export format (csv or json)
 * @param query - Optional audit log query parameters for filtering
 * @returns Promise<Blob> with the exported audit log file
 *
 * @example
 * ```ts
 * // Export all logs as CSV
 * const csvBlob = await exportAuditLogs("csv")
 * downloadFile(csvBlob, "audit_logs.csv")
 *
 * // Export filtered logs as JSON
 * const jsonBlob = await exportAuditLogs("json", {
 *   user_id: "user-123",
 *   start_date: "2026-01-01T00:00:00Z"
 * })
 * downloadFile(jsonBlob, "audit_logs.json")
 * ```
 */
export async function exportAuditLogs(
  format: AuditExportFormat = "csv",
  query: Omit<AuditLogQuery, "limit" | "offset"> = {}
): Promise<Blob> {
  const params = new URLSearchParams()
  params.append("format", format)

  // Add filters to query params
  if (query.user_id) {
    params.append("user_id", query.user_id)
  }

  if (query.user_email) {
    params.append("user_email", query.user_email)
  }

  if (query.action) {
    params.append("action", query.action)
  }

  if (query.resource_type) {
    params.append("resource_type", query.resource_type)
  }

  if (query.resource_id) {
    params.append("resource_id", query.resource_id)
  }

  if (query.table_id) {
    params.append("table_id", query.table_id)
  }

  if (query.request_id) {
    params.append("request_id", query.request_id)
  }

  if (query.start_date) {
    params.append("start_date", query.start_date)
  }

  if (query.end_date) {
    params.append("end_date", query.end_date)
  }

  const queryString = params.toString()
  const url = `/api/v1/audit/logs/export?${queryString}`

  // For export, we need to use fetch directly to get the blob
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
  const token = localStorage.getItem("token")

  const response = await fetch(`${API_BASE_URL}${url}`, {
    method: "GET",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new Error(`Failed to export audit logs: ${response.statusText} ${JSON.stringify(errorData)}`)
  }

  return response.blob()
}
