/**
 * Export utilities for streaming large dataset downloads.
 *
 * Handles streaming exports from the backend API with progress tracking
 * and proper error handling for large datasets.
 */

const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000"

/** Supported export formats */
export type ExportFormat = "csv" | "json"

/** Export progress information */
export interface ExportProgress {
  /** Number of bytes received so far */
  loaded: number
  /** Total file size in bytes (null if unknown) */
  total: number | null
  /** Progress percentage (0-100, null if total unknown) */
  percentage: number | null
}

/** Export options */
export interface ExportOptions {
  /** Export format (csv or json) */
  format?: ExportFormat
  /** Number of records per batch (100-10000) */
  batchSize?: number
  /** Optional progress callback */
  onProgress?: (progress: ExportProgress) => void
  /** Optional abort signal for cancellation */
  signal?: AbortSignal
}

/**
 * Stream export records from a table.
 *
 * Initiates a streaming download of table records in CSV or JSON format.
 * Progress callbacks provide download progress information.
 * Handles large datasets efficiently without browser timeout.
 *
 * @param tableId - Table ID to export records from
 * @param options - Export options including format, batch size, and progress callback
 * @returns Promise<Blob> containing the exported data
 *
 * @example
 * ```ts
 * // Basic CSV export
 * const blob = await exportTableRecords("tbl-123")
 * downloadBlob(blob, "export.csv")
 *
 * // Export with progress tracking
 * const blob = await exportTableRecords("tbl-123", {
 *   format: "csv",
 *   onProgress: (progress) => {
 *     if (progress.percentage) {
 *       console.log(`Download: ${progress.percentage}%`)
 *     }
 *   }
 * })
 *
 * // JSON export with cancellation
 * const controller = new AbortController()
 * const blob = await exportTableRecords("tbl-123", {
 *   format: "json",
 *   signal: controller.signal
 * })
 * ```
 *
 * @throws {Error} If export fails or request is aborted
 */
export async function exportTableRecords(
  tableId: string,
  options: ExportOptions = {}
): Promise<Blob> {
  const {
    format = "csv",
    batchSize = 1000,
    onProgress,
    signal,
  } = options

  // Validate format
  if (format !== "csv" && format !== "json") {
    throw new Error(`Invalid export format: ${format}. Must be 'csv' or 'json'`)
  }

  // Validate batch size
  if (batchSize < 100 || batchSize > 10000) {
    throw new Error("Batch size must be between 100 and 10000")
  }

  // Build query parameters
  const params = new URLSearchParams({
    table_id: tableId,
    format: format,
    batch_size: batchSize.toString(),
  })

  const url = `${API_BASE_URL}/api/v1/records/export?${params.toString()}`

  // Get auth token
  const token = localStorage.getItem("token")

  // Prepare headers
  const headers: Record<string, string> = {}
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  try {
    const response = await fetch(url, {
      method: "POST",
      headers,
      signal,
    })

    if (!response.ok) {
      let errorData
      try {
        errorData = await response.json()
      } catch {
        errorData = null
      }
      throw new Error(
        `Export failed: ${response.status} ${response.statusText}${
          errorData ? ` - ${JSON.stringify(errorData)}` : ""
        }`
      )
    }

    // Get content length for progress tracking
    const contentLength = response.headers.get("Content-Length")
    const total = contentLength ? parseInt(contentLength, 10) : null

    // Stream the response and track progress
    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error("Response body is not readable")
    }

    const chunks: Uint8Array[] = []
    let loaded = 0

    while (true) {
      const { done, value } = await reader.read()

      if (done) {
        break
      }

      chunks.push(value)
      loaded += value.length

      // Report progress if callback provided
      if (onProgress) {
        const percentage = total !== null ? Math.round((loaded / total) * 100) : null
        onProgress({ loaded, total, percentage })
      }
    }

    // Combine chunks into a single Blob
    const blob = new Blob(chunks as BlobPart[], {
      type: format === "csv" ? "text/csv" : "application/json",
    })

    return blob
  } catch (error) {
    // Re-throw abort errors as-is
    if (error instanceof Error && error.name === "AbortError") {
      throw error
    }

    // Wrap other errors
    if (error instanceof Error) {
      throw new Error(`Export failed: ${error.message}`)
    }

    throw new Error("Export failed: Unknown error")
  }
}

/**
 * Download a Blob as a file in the browser.
 *
 * Creates a temporary download link and triggers the browser's download
 * functionality for the given Blob.
 *
 * @param blob - The Blob data to download
 * @param filename - The filename to save as (default: "export.csv")
 *
 * @example
 * ```ts
 * const blob = await exportTableRecords("tbl-123", { format: "csv" })
 * downloadBlob(blob, "my-table-export.csv")
 * ```
 */
export function downloadBlob(blob: Blob, filename: string = "export.csv"): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Export and download table records in one step.
 *
 * Convenience function that combines exportTableRecords and downloadBlob.
 * Shows optional progress during download.
 *
 * @param tableId - Table ID to export
 * @param filename - Filename for download (default: auto-generated)
 * @param options - Export options
 * @returns Promise that resolves when download starts
 *
 * @example
 * ```ts
 * // Simple export
 * await exportTableRecordsDownload("tbl-123")
 *
 * // With progress and custom filename
 * await exportTableRecordsDownload("tbl-123", "parts.csv", {
 *   format: "csv",
 *   onProgress: (p) => console.log(`${p.percentage}%`)
 * })
 * ```
 */
export async function exportTableRecordsDownload(
  tableId: string,
  filename?: string,
  options: ExportOptions = {}
): Promise<void> {
  const format = options.format || "csv"
  const defaultFilename = `export_${tableId}.${format}`

  const blob = await exportTableRecords(tableId, options)
  downloadBlob(blob, filename || defaultFilename)
}
