/**
 * API client for PyBase backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: any
  ) {
    super(`API Error: ${status} ${statusText}`)
    this.name = "ApiError"
  }
}

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem("token")

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  // Don't set Content-Type for FormData - browser will set it with boundary
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json"
  }

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let errorData
    try {
      errorData = await response.json()
    } catch {
      errorData = null
    }
    throw new ApiError(response.status, response.statusText, errorData)
  }

  return response
}

export async function get<T>(url: string): Promise<T> {
  const response = await fetchWithAuth(url, { method: "GET" })
  return response.json()
}

export async function post<T>(url: string, data?: any): Promise<T> {
  const body = data instanceof FormData ? data : JSON.stringify(data)

  const response = await fetchWithAuth(url, {
    method: "POST",
    body,
  })

  // Handle 204 No Content responses
  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

export async function patch<T>(url: string, data?: any): Promise<T> {
  const body = data instanceof FormData ? data : JSON.stringify(data)

  const response = await fetchWithAuth(url, {
    method: "PATCH",
    body,
  })

  return response.json()
}

export async function del<T>(url: string): Promise<T> {
  const response = await fetchWithAuth(url, { method: "DELETE" })

  // Handle 204 No Content responses
  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

export { ApiError }
