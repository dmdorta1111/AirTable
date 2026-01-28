import type {
  BatchOperationResponse,
  RestoreResponse,
  TrashListResponse,
} from "@/types"
import { get, post } from "@/lib/api"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem("token")

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
    "Content-Type": "application/json",
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  return await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
  })
}

export async function listTrash(params?: {
  table_id?: string
  page?: number
  page_size?: number
}): Promise<TrashListResponse> {
  const searchParams = new URLSearchParams()

  if (params?.table_id) {
    searchParams.append("table_id", params.table_id)
  }
  if (params?.page) {
    searchParams.append("page", params.page.toString())
  }
  if (params?.page_size) {
    searchParams.append("page_size", params.page_size.toString())
  }

  const queryString = searchParams.toString()
  const url = queryString ? `/api/v1/trash?${queryString}` : "/api/v1/trash"

  return get<TrashListResponse>(url)
}

export async function restoreRecord(recordId: string): Promise<RestoreResponse> {
  return post<RestoreResponse>(`/api/v1/trash/${recordId}/restore`, {})
}

export async function batchRestoreRecords(
  recordIds: string[]
): Promise<BatchOperationResponse> {
  return post<BatchOperationResponse>("/api/v1/trash/batch/restore", {
    record_ids: recordIds,
  })
}

export async function permanentDeleteRecord(recordId: string): Promise<void> {
  const response = await fetchWithAuth(`/api/v1/trash/${recordId}/permanent`, {
    method: "DELETE",
  })

  if (!response.ok) {
    throw new Error(`Failed to permanently delete record: ${response.statusText}`)
  }
}

export async function batchPermanentDeleteRecords(
  recordIds: string[]
): Promise<BatchOperationResponse> {
  const response = await fetchWithAuth("/api/v1/trash/batch/permanent", {
    method: "DELETE",
    body: JSON.stringify({ record_ids: recordIds }),
  })

  if (!response.ok) {
    throw new Error(`Failed to batch permanently delete records: ${response.statusText}`)
  }

  return response.json()
}
