/**
 * API client for custom reports endpoints.
 */

import { get, post, patch, del } from "@/lib/api"

// =============================================================================
// Type Definitions
// =============================================================================

/** Report format options */
export type ReportFormat = "pdf" | "html" | "csv" | "xlsx"

/** Report section types */
export type ReportSectionType = "table" | "chart" | "text" | "image"

/** Report status */
export type ReportStatus = "pending" | "generating" | "completed" | "failed"

/** Schedule frequency */
export type ScheduleFrequency =
  | "manual"
  | "daily"
  | "weekly"
  | "monthly"
  | "quarterly"
  | "yearly"
  | "custom"

/** Join types for data sources */
export type JoinType = "inner" | "left" | "right" | "full"

/** Aggregate function types */
export type AggregateType =
  | "none"
  | "sum"
  | "avg"
  | "count"
  | "min"
  | "max"

/** Filter operators */
export type FilterOperator =
  | "equals"
  | "not_equals"
  | "contains"
  | "not_contains"
  | "starts_with"
  | "ends_with"
  | "greater_than"
  | "less_than"
  | "greater_equal"
  | "less_equal"
  | "is_null"
  | "is_not_null"
  | "in"
  | "not_in"

/** Sort direction */
export type SortDirection = "asc" | "desc"

/** Logic operator for filters */
export type LogicOperator = "and" | "or"

// =============================================================================
// Configuration Types
// =============================================================================

/** Schedule configuration */
export interface CustomReportScheduleConfig {
  time_of_day?: string
  day_of_week?: string
  day_of_month?: number
  timezone?: string
}

/** Email delivery configuration */
export interface CustomReportDeliveryConfig {
  recipients?: string[]
  cc?: string[]
  bcc?: string[]
  subject?: string
  message?: string
  reply_to?: string
}

/** Layout configuration */
export interface LayoutConfig {
  page_size?: string
  orientation?: "portrait" | "landscape"
  margins?: {
    top?: number
    bottom?: number
    left?: number
    right?: number
  }
}

/** Style configuration */
export interface StyleConfig {
  font_family?: string
  font_size?: number
  colors?: {
    primary?: string
    secondary?: string
    background?: string
  }
  header_style?: "centered" | "left" | "right"
  show_page_numbers?: boolean
  logo_url?: string
}

/** Join definition for multi-table queries */
export interface JoinDefinition {
  left_table: string
  left_field: string
  right_table: string
  right_field: string
}

/** Table join configuration */
export interface TableJoinConfig {
  table_id: string
  join_type: JoinType
  joins: JoinDefinition[]
  alias?: string
}

/** Tables configuration with primary and joined tables */
export interface TablesConfig {
  primary_table: string
  joined_tables?: TableJoinConfig[]
}

/** Field configuration for data sources */
export interface FieldConfig {
  field_id: string
  table_id?: string
  alias?: string
  aggregate?: AggregateType
  visible?: boolean
}

/** Filter configuration */
export interface FilterConfig {
  field_id: string
  operator: FilterOperator
  value?: string | number | boolean | string[] | number[]
  logic?: LogicOperator
}

/** Sort configuration */
export interface SortConfig {
  field_id: string
  direction: SortDirection
}

/** Combined sort, group, limit, offset configuration */
export interface SortGroupConfig {
  sort_by?: SortConfig[]
  group_by?: string[]
  limit?: number
  offset?: number
}

// =============================================================================
// Report Section Types
// =============================================================================

/** Report section configuration */
export interface ReportSectionBase {
  title: string
  section_type: ReportSectionType
  section_config?: Record<string, unknown>
  display_order?: number
}

/** Report section create request */
export interface ReportSectionCreate extends ReportSectionBase {
  data_source_id?: string
}

/** Report section update request */
export interface ReportSectionUpdate {
  title?: string
  section_config?: Record<string, unknown>
  display_order?: number
}

/** Report section response */
export interface ReportSectionResponse extends ReportSectionBase {
  id: string
  report_id: string
  data_source_id?: string
  created_at: string
  updated_at: string
}

/** Report section list response */
export interface ReportSectionListResponse {
  items: ReportSectionResponse[]
  total: number
  page: number
  page_size: number
  pages: number
}

// =============================================================================
// Data Source Types
// =============================================================================

/** Report data source base */
export interface ReportDataSourceBase {
  name: string
  description?: string
  tables_config: TablesConfig
  fields_config?: FieldConfig[]
  filters_config?: FilterConfig[]
  sort_group_config?: SortGroupConfig
  parameter_bindings?: Record<string, string>
}

/** Report data source create request */
export interface ReportDataSourceCreate extends ReportDataSourceBase {}

/** Report data source update request */
export interface ReportDataSourceUpdate {
  name?: string
  description?: string
  tables_config?: TablesConfig
  fields_config?: FieldConfig[]
  filters_config?: FilterConfig[]
  sort_group_config?: SortGroupConfig
  parameter_bindings?: Record<string, string>
}

/** Report data source response */
export interface ReportDataSourceResponse extends ReportDataSourceBase {
  id: string
  report_id: string
  created_at: string
  updated_at: string
}

/** Report data source list response */
export interface ReportDataSourceListResponse {
  items: ReportDataSourceResponse[]
  total: number
  page: number
  page_size: number
  pages: number
}

// =============================================================================
// Custom Report Types
// =============================================================================

/** Custom report base */
export interface CustomReportBase {
  name: string
  description?: string
  format?: ReportFormat
  frequency?: ScheduleFrequency
  cron_expression?: string
  is_published?: boolean
  is_active?: boolean
  is_paused?: boolean
  template_id?: string
  layout_config?: LayoutConfig
  style_config?: StyleConfig
  schedule_config?: CustomReportScheduleConfig
  delivery_config?: CustomReportDeliveryConfig
}

/** Custom report create request */
export interface CustomReportCreate extends CustomReportBase {}

/** Custom report update request */
export interface CustomReportUpdate {
  name?: string
  description?: string
  format?: ReportFormat
  frequency?: ScheduleFrequency
  cron_expression?: string
  is_published?: boolean
  is_active?: boolean
  is_paused?: boolean
  template_id?: string
  layout_config?: LayoutConfig
  style_config?: StyleConfig
  schedule_config?: CustomReportScheduleConfig
  delivery_config?: CustomReportDeliveryConfig
}

/** Custom report response */
export interface CustomReportResponse extends CustomReportBase {
  id: string
  base_id: string
  created_by_id: string
  status: ReportStatus
  generated_count: number
  last_generated_at?: string
  next_run_at?: string
  created_at: string
  updated_at: string
}

/** Custom report list response */
export interface CustomReportListResponse {
  items: CustomReportResponse[]
  total: number
  page: number
  page_size: number
  pages: number
}

/** Duplicate report request */
export interface CustomReportDuplicate {
  new_name?: string
  new_description?: string
  include_sections?: boolean
  include_data_sources?: boolean
}

/** Generate report request */
export interface CustomReportGenerateRequest {
  format?: ReportFormat
  parameter_values?: Record<string, string | number | boolean>
}

/** Export report response */
export interface CustomReportExportResponse {
  export_id: string
  format: ReportFormat
  status: ReportStatus
  file_url?: string
  expires_at?: string
}

// =============================================================================
// Schedule Types
// =============================================================================

/** Report schedule response */
export interface CustomReportScheduleResponse {
  id: string
  report_id: string
  status: ReportStatus
  started_at: string
  completed_at?: string
  error_message?: string
  file_url?: string
  expires_at?: string
  created_at: string
}

/** Report schedule list response */
export interface CustomReportScheduleListResponse {
  items: CustomReportScheduleResponse[]
  total: number
  page: number
  page_size: number
  pages: number
}

// =============================================================================
// Template Types
// =============================================================================

/** Report template base */
export interface ReportTemplateBase {
  name: string
  description?: string
  category?: string
  is_system?: boolean
  is_active?: boolean
  template_config?: Record<string, unknown>
  icon?: string
  tags?: string[]
}

/** Report template create request */
export interface ReportTemplateCreate extends ReportTemplateBase {}

/** Report template update request */
export interface ReportTemplateUpdate {
  name?: string
  description?: string
  category?: string
  is_active?: boolean
  template_config?: Record<string, unknown>
  icon?: string
  tags?: string[]
}

/** Report template response */
export interface ReportTemplateResponse extends ReportTemplateBase {
  id: string
  usage_count: number
  created_at: string
  updated_at: string
}

/** Report template list response */
export interface ReportTemplateListResponse {
  items: ReportTemplateResponse[]
  total: number
  page: number
  page_size: number
  pages: number
}

/** Duplicate template request */
export interface ReportTemplateDuplicate {
  new_name?: string
  new_description?: string
  new_category?: string
}

// =============================================================================
// Custom Report API Functions
// =============================================================================

/**
 * Create a new custom report.
 */
export async function createCustomReport(
  baseId: string,
  data: CustomReportCreate
): Promise<CustomReportResponse> {
  return post<CustomReportResponse>(`/api/v1/custom-reports?base_id=${baseId}`, data)
}

/**
 * List custom reports for a base.
 */
export async function listCustomReports(
  baseId: string,
  params?: {
    is_published?: boolean
    is_active?: boolean
    template_id?: string
    frequency?: ScheduleFrequency
    page?: number
    page_size?: number
  }
): Promise<CustomReportListResponse> {
  const searchParams = new URLSearchParams({ base_id: baseId })

  if (params?.is_published !== undefined) {
    searchParams.append("is_published", String(params.is_published))
  }
  if (params?.is_active !== undefined) {
    searchParams.append("is_active", String(params.is_active))
  }
  if (params?.template_id) {
    searchParams.append("template_id", params.template_id)
  }
  if (params?.frequency) {
    searchParams.append("frequency", params.frequency)
  }
  if (params?.page) {
    searchParams.append("page", String(params.page))
  }
  if (params?.page_size) {
    searchParams.append("page_size", String(params.page_size))
  }

  return get<CustomReportListResponse>(`/api/v1/custom-reports?${searchParams.toString()}`)
}

/**
 * Get a custom report by ID.
 */
export async function getCustomReport(reportId: string): Promise<CustomReportResponse> {
  return get<CustomReportResponse>(`/api/v1/custom-reports/${reportId}`)
}

/**
 * Update a custom report.
 */
export async function updateCustomReport(
  reportId: string,
  data: CustomReportUpdate
): Promise<CustomReportResponse> {
  return patch<CustomReportResponse>(`/api/v1/custom-reports/${reportId}`, data)
}

/**
 * Delete a custom report (soft delete).
 */
export async function deleteCustomReport(reportId: string): Promise<void> {
  return del<void>(`/api/v1/custom-reports/${reportId}`)
}

/**
 * Duplicate a custom report.
 */
export async function duplicateCustomReport(
  reportId: string,
  data: CustomReportDuplicate
): Promise<CustomReportResponse> {
  return post<CustomReportResponse>(`/api/v1/custom-reports/${reportId}/duplicate`, data)
}

/**
 * Generate a report immediately.
 */
export async function generateCustomReport(
  reportId: string,
  data: CustomReportGenerateRequest
): Promise<CustomReportScheduleResponse> {
  return post<CustomReportScheduleResponse>(
    `/api/v1/custom-reports/${reportId}/generate`,
    data
  )
}

/**
 * Export a report to configured format.
 */
export async function exportCustomReport(
  reportId: string,
  format?: ReportFormat
): Promise<CustomReportExportResponse> {
  const params = format ? `?format=${format}` : ""
  return post<CustomReportExportResponse>(
    `/api/v1/custom-reports/${reportId}/export${params}`
  )
}

/**
 * Export a report to PDF (returns blob).
 */
export async function exportCustomReportPDF(
  reportId: string
): Promise<Blob> {
  const response = await fetch(
    `/api/v1/custom-reports/${reportId}/export/pdf`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to export PDF: ${response.statusText}`)
  }

  return response.blob()
}

// =============================================================================
// Report Sections API Functions
// =============================================================================

/**
 * Create a report section.
 */
export async function createReportSection(
  reportId: string,
  data: ReportSectionCreate
): Promise<ReportSectionResponse> {
  return post<ReportSectionResponse>(
    `/api/v1/custom-reports/${reportId}/sections`,
    data
  )
}

/**
 * List report sections.
 */
export async function listReportSections(
  reportId: string,
  params?: {
    page?: number
    page_size?: number
  }
): Promise<ReportSectionListResponse> {
  const searchParams = new URLSearchParams()

  if (params?.page) {
    searchParams.append("page", String(params.page))
  }
  if (params?.page_size) {
    searchParams.append("page_size", String(params.page_size))
  }

  const queryString = searchParams.toString()
  return get<ReportSectionListResponse>(
    `/api/v1/custom-reports/${reportId}/sections${queryString ? `?${queryString}` : ""}`
  )
}

/**
 * Get a report section by ID.
 */
export async function getReportSection(
  reportId: string,
  sectionId: string
): Promise<ReportSectionResponse> {
  return get<ReportSectionResponse>(
    `/api/v1/custom-reports/${reportId}/sections/${sectionId}`
  )
}

/**
 * Update a report section.
 */
export async function updateReportSection(
  reportId: string,
  sectionId: string,
  data: ReportSectionUpdate
): Promise<ReportSectionResponse> {
  return patch<ReportSectionResponse>(
    `/api/v1/custom-reports/${reportId}/sections/${sectionId}`,
    data
  )
}

/**
 * Delete a report section.
 */
export async function deleteReportSection(
  reportId: string,
  sectionId: string
): Promise<void> {
  return del<void>(`/api/v1/custom-reports/${reportId}/sections/${sectionId}`)
}

/**
 * Reorder report sections.
 */
export async function reorderReportSections(
  reportId: string,
  sectionIds: string[]
): Promise<ReportSectionResponse[]> {
  return post<ReportSectionResponse[]>(
    `/api/v1/custom-reports/${reportId}/sections/reorder`,
    { section_ids: sectionIds }
  )
}

// =============================================================================
// Data Source API Functions
// =============================================================================

/**
 * Create a data source.
 */
export async function createDataSource(
  reportId: string,
  data: ReportDataSourceCreate
): Promise<ReportDataSourceResponse> {
  return post<ReportDataSourceResponse>(
    `/api/v1/custom-reports/${reportId}/datasources`,
    data
  )
}

/**
 * List data sources.
 */
export async function listDataSources(
  reportId: string,
  params?: {
    page?: number
    page_size?: number
  }
): Promise<ReportDataSourceListResponse> {
  const searchParams = new URLSearchParams()

  if (params?.page) {
    searchParams.append("page", String(params.page))
  }
  if (params?.page_size) {
    searchParams.append("page_size", String(params.page_size))
  }

  const queryString = searchParams.toString()
  return get<ReportDataSourceListResponse>(
    `/api/v1/custom-reports/${reportId}/datasources${queryString ? `?${queryString}` : ""}`
  )
}

/**
 * Get a data source by ID.
 */
export async function getDataSource(
  reportId: string,
  dataSourceId: string
): Promise<ReportDataSourceResponse> {
  return get<ReportDataSourceResponse>(
    `/api/v1/custom-reports/${reportId}/datasources/${dataSourceId}`
  )
}

/**
 * Update a data source.
 */
export async function updateDataSource(
  reportId: string,
  dataSourceId: string,
  data: ReportDataSourceUpdate
): Promise<ReportDataSourceResponse> {
  return patch<ReportDataSourceResponse>(
    `/api/v1/custom-reports/${reportId}/datasources/${dataSourceId}`,
    data
  )
}

/**
 * Delete a data source.
 */
export async function deleteDataSource(
  reportId: string,
  dataSourceId: string
): Promise<void> {
  return del<void>(`/api/v1/custom-reports/${reportId}/datasources/${dataSourceId}`)
}

// =============================================================================
// Schedule API Functions
// =============================================================================

/**
 * List schedule runs for a report.
 */
export async function listReportSchedules(
  reportId: string,
  params?: {
    status?: ReportStatus
    page?: number
    page_size?: number
  }
): Promise<CustomReportScheduleListResponse> {
  const searchParams = new URLSearchParams()

  if (params?.status) {
    searchParams.append("status", params.status)
  }
  if (params?.page) {
    searchParams.append("page", String(params.page))
  }
  if (params?.page_size) {
    searchParams.append("page_size", String(params.page_size))
  }

  const queryString = searchParams.toString()
  return get<CustomReportScheduleListResponse>(
    `/api/v1/custom-reports/${reportId}/schedules${queryString ? `?${queryString}` : ""}`
  )
}

/**
 * Get a schedule run by ID.
 */
export async function getReportSchedule(
  reportId: string,
  scheduleId: string
): Promise<CustomReportScheduleResponse> {
  return get<CustomReportScheduleResponse>(
    `/api/v1/custom-reports/${reportId}/schedules/${scheduleId}`
  )
}

/**
 * Cancel a schedule run.
 */
export async function cancelReportSchedule(
  reportId: string,
  scheduleId: string
): Promise<CustomReportScheduleResponse> {
  return post<CustomReportScheduleResponse>(
    `/api/v1/custom-reports/${reportId}/schedules/${scheduleId}/cancel`,
    {}
  )
}

/**
 * Retry a failed schedule run.
 */
export async function retryReportSchedule(
  reportId: string,
  scheduleId: string
): Promise<CustomReportScheduleResponse> {
  return post<CustomReportScheduleResponse>(
    `/api/v1/custom-reports/${reportId}/schedules/${scheduleId}/retry`,
    {}
  )
}

// =============================================================================
// Report Template API Functions
// =============================================================================

/**
 * Create a report template.
 */
export async function createReportTemplate(
  data: ReportTemplateCreate
): Promise<ReportTemplateResponse> {
  return post<ReportTemplateResponse>("/api/v1/report-templates", data)
}

/**
 * List report templates.
 */
export async function listReportTemplates(params?: {
  category?: string
  is_system?: boolean
  is_active?: boolean
  page?: number
  page_size?: number
}): Promise<ReportTemplateListResponse> {
  const searchParams = new URLSearchParams()

  if (params?.category) {
    searchParams.append("category", params.category)
  }
  if (params?.is_system !== undefined) {
    searchParams.append("is_system", String(params.is_system))
  }
  if (params?.is_active !== undefined) {
    searchParams.append("is_active", String(params.is_active))
  }
  if (params?.page) {
    searchParams.append("page", String(params.page))
  }
  if (params?.page_size) {
    searchParams.append("page_size", String(params.page_size))
  }

  const queryString = searchParams.toString()
  return get<ReportTemplateListResponse>(
    `/api/v1/report-templates${queryString ? `?${queryString}` : ""}`
  )
}

/**
 * Get a report template by ID.
 */
export async function getReportTemplate(
  templateId: string
): Promise<ReportTemplateResponse> {
  return get<ReportTemplateResponse>(`/api/v1/report-templates/${templateId}`)
}

/**
 * Update a report template.
 */
export async function updateReportTemplate(
  templateId: string,
  data: ReportTemplateUpdate
): Promise<ReportTemplateResponse> {
  return patch<ReportTemplateResponse>(
    `/api/v1/report-templates/${templateId}`,
    data
  )
}

/**
 * Delete a report template.
 */
export async function deleteReportTemplate(templateId: string): Promise<void> {
  return del<void>(`/api/v1/report-templates/${templateId}`)
}

/**
 * Duplicate a report template.
 */
export async function duplicateReportTemplate(
  templateId: string,
  data: ReportTemplateDuplicate
): Promise<ReportTemplateResponse> {
  return post<ReportTemplateResponse>(
    `/api/v1/report-templates/${templateId}/duplicate`,
    data
  )
}
