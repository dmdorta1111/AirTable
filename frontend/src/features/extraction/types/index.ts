/**
 * Types for CAD/PDF extraction features.
 * Matches backend schemas in src/pybase/schemas/extraction.py
 */

export type ExtractionFormat = "pdf" | "dxf" | "ifc" | "step" | "werk24"

export type JobStatus = "pending" | "processing" | "completed" | "failed" | "cancelled"

// --- Extracted Data Schemas ---

export interface ExtractedTable {
  headers: string[]
  rows: any[][]
  page?: number
  confidence: number
  bbox?: [number, number, number, number]
  num_rows: number
  num_columns: number
}

export interface ExtractedDimension {
  value: number
  unit: string
  tolerance_plus?: number
  tolerance_minus?: number
  dimension_type: string
  label?: string
  page?: number
  confidence: number
  bbox?: [number, number, number, number]
}

export interface ExtractedText {
  text: string
  page?: number
  confidence: number
  bbox?: [number, number, number, number]
  font_size?: number
  is_title: boolean
}

export interface ExtractedTitleBlock {
  drawing_number?: string
  title?: string
  revision?: string
  date?: string
  author?: string
  company?: string
  scale?: string
  sheet?: string
  material?: string
  finish?: string
  custom_fields: Record<string, string>
  confidence: number
}

export interface ExtractedLayer {
  name: string
  color?: number | string
  linetype?: string
  lineweight?: number
  is_on: boolean
  is_frozen: boolean
  is_locked: boolean
  entity_count: number
}

export interface ExtractedBlock {
  name: string
  insert_count: number
  base_point?: [number, number, number]
  attributes: Record<string, any>[]
  entity_count: number
}

export interface GeometrySummary {
  lines: number
  circles: number
  arcs: number
  polylines: number
  splines: number
  ellipses: number
  points: number
  hatches: number
  solids: number
  meshes: number
  total_entities: number
}

export interface ExtractedBOM {
  items: Record<string, any>[]
  headers?: string[]
  total_items: number
  confidence: number
}

// --- Response Schemas ---

export interface PDFExtractionResponse {
  source_file: string
  source_type: string
  success: boolean
  tables: ExtractedTable[]
  dimensions: ExtractedDimension[]
  text_blocks: ExtractedText[]
  title_block?: ExtractedTitleBlock
  bom?: ExtractedBOM
  metadata: Record<string, any>
  errors: string[]
  warnings: string[]
}

export interface CADExtractionResponse {
  source_file: string
  source_type: string
  success: boolean
  layers: ExtractedLayer[]
  blocks: ExtractedBlock[]
  dimensions: ExtractedDimension[]
  text_blocks: ExtractedText[]
  title_block?: ExtractedTitleBlock
  geometry_summary?: GeometrySummary
  entities: Record<string, any>[]
  metadata: Record<string, any>
  errors: string[]
  warnings: string[]
}

export interface Werk24ExtractionResponse {
  source_file: string
  source_type: string
  success: boolean
  dimensions: ExtractedDimension[]
  gdt_annotations: Record<string, any>[]
  threads: Record<string, any>[]
  surface_finishes: Record<string, any>[]
  materials: Record<string, any>[]
  title_block?: ExtractedTitleBlock
  metadata: Record<string, any>
  errors: string[]
  warnings: string[]
}

export type ExtractionResponse = PDFExtractionResponse | CADExtractionResponse | Werk24ExtractionResponse

// --- Job Schemas ---

export interface ExtractionJob {
  id: string
  status: JobStatus
  format: ExtractionFormat
  filename: string
  file_size: number
  options: Record<string, any>
  target_table_id?: string
  progress: number
  result?: ExtractionResponse
  error_message?: string
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface ExtractionJobListResponse {
  items: ExtractionJob[]
  total: number
  page: number
  page_size: number
}

// --- Import Schemas ---

export interface ImportPreview {
  source_fields: string[]
  target_fields: Array<{
    id: string
    name: string
    type: string
    [key: string]: any
  }>
  suggested_mapping: Record<string, string>
  sample_data: Record<string, any>[]
  total_records: number
}

export interface ImportRequest {
  job_id: string
  table_id: string
  field_mapping: Record<string, string>
  create_missing_fields?: boolean
  skip_errors?: boolean
}

export interface ImportResponse {
  success: boolean
  records_imported: number
  records_failed: number
  errors: Array<{
    row?: number
    field?: string
    message: string
    [key: string]: any
  }>
  created_field_ids: string[]
}

// --- Upload Options ---

export interface PDFExtractionOptions {
  extract_tables?: boolean
  extract_text?: boolean
  extract_dimensions?: boolean
  use_ocr?: boolean
  ocr_language?: string
  pages?: number[]
}

export interface DXFExtractionOptions {
  extract_layers?: boolean
  extract_blocks?: boolean
  extract_dimensions?: boolean
  extract_text?: boolean
  extract_title_block?: boolean
  extract_geometry?: boolean
}

export interface IFCExtractionOptions {
  extract_properties?: boolean
  extract_quantities?: boolean
  extract_materials?: boolean
  extract_spatial?: boolean
  element_types?: string[]
}

export interface STEPExtractionOptions {
  extract_assembly?: boolean
  extract_parts?: boolean
  calculate_volumes?: boolean
  calculate_areas?: boolean
  count_shapes?: boolean
}

export interface Werk24ExtractionOptions {
  extract_dimensions?: boolean
  extract_gdt?: boolean
  extract_threads?: boolean
  extract_surface_finish?: boolean
  extract_materials?: boolean
  extract_title_block?: boolean
  confidence_threshold?: number
}

export type ExtractionOptions =
  | PDFExtractionOptions
  | DXFExtractionOptions
  | IFCExtractionOptions
  | STEPExtractionOptions
  | Werk24ExtractionOptions
