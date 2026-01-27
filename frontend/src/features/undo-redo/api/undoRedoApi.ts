/**
 * API client for undo/redo operations.
 */

import { get, post } from "@/lib/api"

// =============================================================================
// Types
// =============================================================================

export interface OperationLogResponse {
  id: string
  user_id: string
  operation_type: string
  entity_type: string
  entity_id: string
  before_data: Record<string, unknown> | null
  after_data: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface OperationLogListResponse {
  items: OperationLogResponse[]
  total: number
  page: number
  page_size: number
}

export interface UndoRequest {
  operation_id: string
}

export interface RedoRequest {
  operation_id: string
}

export interface GetOperationsParams {
  page?: number
  page_size?: number
  operation_type?: string
  entity_type?: string
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Get operations for the current user.
 *
 * @param params - Query parameters for filtering and pagination
 * @returns Promise<OperationLogListResponse> with paginated operations
 *
 * @example
 * ```ts
 * // Get first page of operations
 * const ops1 = await getOperations({ page: 1, page_size: 20 })
 *
 * // Get operations filtered by type
 * const ops2 = await getOperations({ operation_type: "update", entity_type: "record" })
 * ```
 */
export async function getOperations(
  params?: GetOperationsParams
): Promise<OperationLogListResponse> {
  const queryParams = new URLSearchParams()

  if (params?.page) {
    queryParams.append("page", params.page.toString())
  }

  if (params?.page_size) {
    queryParams.append("page_size", params.page_size.toString())
  }

  if (params?.operation_type) {
    queryParams.append("operation_type", params.operation_type)
  }

  if (params?.entity_type) {
    queryParams.append("entity_type", params.entity_type)
  }

  const queryString = queryParams.toString()
  const url = `/api/v1/undo-redo/operations${queryString ? `?${queryString}` : ""}`

  return get<OperationLogListResponse>(url)
}

/**
 * Undo an operation.
 *
 * Reverts the specified operation to its before state.
 * User must own the operation to undo it.
 *
 * @param request - Request containing the operation_id to undo
 * @returns Promise<OperationLogResponse> with the undone operation details
 *
 * @example
 * ```ts
 * const undone = await undoOperation({ operation_id: "op-123" })
 * console.log(`Undone operation: ${undone.operation_type}`)
 * ```
 */
export async function undoOperation(
  request: UndoRequest
): Promise<OperationLogResponse> {
  return post<OperationLogResponse>("/api/v1/undo-redo/undo", request)
}

/**
 * Redo an operation.
 *
 * Re-applies the specified operation using its after state.
 * User must own the operation to redo it.
 *
 * @param request - Request containing the operation_id to redo
 * @returns Promise<OperationLogResponse> with the redone operation details
 *
 * @example
 * ```ts
 * const redone = await redoOperation({ operation_id: "op-123" })
 * console.log(`Redone operation: ${redone.operation_type}`)
 * ```
 */
export async function redoOperation(
  request: RedoRequest
): Promise<OperationLogResponse> {
  return post<OperationLogResponse>("/api/v1/undo-redo/redo", request)
}
