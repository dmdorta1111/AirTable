import type {
  ExtractionJob,
  ExtractionJobListResponse,
  ExtractionFormat,
  ImportPreview,
  ImportRequest,
  ImportResponse,
  PDFExtractionResponse,
  CADExtractionResponse,
  Werk24ExtractionResponse,
  PDFExtractionOptions,
  DXFExtractionOptions,
  IFCExtractionOptions,
  STEPExtractionOptions,
  Werk24ExtractionOptions,
} from "../types"
import { get, post, del } from "@/lib/api"

/**
 * Upload a PDF file and extract data.
 */
export async function extractPDF(
  file: File,
  options: PDFExtractionOptions = {}
): Promise<PDFExtractionResponse> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("extract_tables", String(options.extract_tables ?? true))
  formData.append("extract_text", String(options.extract_text ?? true))
  formData.append("extract_dimensions", String(options.extract_dimensions ?? false))
  formData.append("use_ocr", String(options.use_ocr ?? false))
  formData.append("ocr_language", options.ocr_language ?? "eng")

  if (options.pages) {
    formData.append("pages", options.pages.join(","))
  }

  return post<PDFExtractionResponse>("/api/v1/extraction/pdf", formData)
}

/**
 * Upload a DXF file and extract data.
 */
export async function extractDXF(
  file: File,
  options: DXFExtractionOptions = {}
): Promise<CADExtractionResponse> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("extract_layers", String(options.extract_layers ?? true))
  formData.append("extract_blocks", String(options.extract_blocks ?? true))
  formData.append("extract_dimensions", String(options.extract_dimensions ?? true))
  formData.append("extract_text", String(options.extract_text ?? true))
  formData.append("extract_title_block", String(options.extract_title_block ?? true))
  formData.append("extract_geometry", String(options.extract_geometry ?? false))

  return post<CADExtractionResponse>("/api/v1/extraction/dxf", formData)
}

/**
 * Upload an IFC file and extract data.
 */
export async function extractIFC(
  file: File,
  options: IFCExtractionOptions = {}
): Promise<CADExtractionResponse> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("extract_properties", String(options.extract_properties ?? true))
  formData.append("extract_quantities", String(options.extract_quantities ?? true))
  formData.append("extract_materials", String(options.extract_materials ?? true))
  formData.append("extract_spatial", String(options.extract_spatial ?? true))

  if (options.element_types) {
    formData.append("element_types", options.element_types.join(","))
  }

  return post<CADExtractionResponse>("/api/v1/extraction/ifc", formData)
}

/**
 * Upload a STEP file and extract data.
 */
export async function extractSTEP(
  file: File,
  options: STEPExtractionOptions = {}
): Promise<CADExtractionResponse> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("extract_assembly", String(options.extract_assembly ?? true))
  formData.append("extract_parts", String(options.extract_parts ?? true))
  formData.append("calculate_volumes", String(options.calculate_volumes ?? true))
  formData.append("calculate_areas", String(options.calculate_areas ?? true))
  formData.append("count_shapes", String(options.count_shapes ?? true))

  return post<CADExtractionResponse>("/api/v1/extraction/step", formData)
}

/**
 * Upload a file and extract via Werk24 AI API.
 */
export async function extractWerk24(
  file: File,
  options: Werk24ExtractionOptions = {}
): Promise<Werk24ExtractionResponse> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("extract_dimensions", String(options.extract_dimensions ?? true))
  formData.append("extract_gdt", String(options.extract_gdt ?? true))
  formData.append("extract_threads", String(options.extract_threads ?? true))
  formData.append("extract_surface_finish", String(options.extract_surface_finish ?? true))
  formData.append("extract_materials", String(options.extract_materials ?? true))
  formData.append("extract_title_block", String(options.extract_title_block ?? true))
  formData.append("confidence_threshold", String(options.confidence_threshold ?? 0.7))

  return post<Werk24ExtractionResponse>("/api/v1/extraction/werk24", formData)
}

/**
 * Create an async extraction job for large files.
 */
export async function createExtractionJob(
  file: File,
  format: ExtractionFormat,
  targetTableId?: string
): Promise<ExtractionJob> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("format", format)

  if (targetTableId) {
    formData.append("target_table_id", targetTableId)
  }

  return post<ExtractionJob>("/api/v1/extraction/jobs", formData)
}

/**
 * Get extraction job status and result.
 */
export async function getExtractionJob(jobId: string): Promise<ExtractionJob> {
  return get<ExtractionJob>(`/api/v1/extraction/jobs/${jobId}`)
}

/**
 * List extraction jobs with optional status filter.
 */
export async function listExtractionJobs(
  status?: string,
  page: number = 1,
  pageSize: number = 20
): Promise<ExtractionJobListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  })

  if (status) {
    params.append("status", status)
  }

  return get<ExtractionJobListResponse>(`/api/v1/extraction/jobs?${params.toString()}`)
}

/**
 * Cancel or delete an extraction job.
 */
export async function deleteExtractionJob(jobId: string): Promise<void> {
  return del<void>(`/api/v1/extraction/jobs/${jobId}`)
}

/**
 * Preview how extracted data will map to table fields.
 * Returns suggested field mappings and sample data.
 */
export async function previewImport(
  jobId: string,
  tableId: string
): Promise<ImportPreview> {
  return post<ImportPreview>(
    `/api/v1/extraction/jobs/${jobId}/preview?table_id=${tableId}`
  )
}

/**
 * Import extracted data into a table with field mapping.
 */
export async function importExtractedData(
  request: ImportRequest
): Promise<ImportResponse> {
  return post<ImportResponse>("/api/v1/extraction/import", request)
}
