/**
 * Search types for PyBase frontend.
 *
 * Matches backend search schemas in src/pybase/schemas/search.py
 */

// =============================================================================
// Enums
// =============================================================================

export type FacetType = "string" | "integer" | "float" | "boolean" | "date" | "array"

export type SortOrder = "asc" | "desc" | "relevance"

// =============================================================================
// Request Types
// =============================================================================

export interface FieldFilter {
  field_id: string
  operator: "eq" | "ne" | "gt" | "lt" | "gte" | "lte" | "in" | "contains"
  value: unknown
}

export interface NumericRangeFilter {
  field_id: string
  min_value?: number
  max_value?: number
}

export interface DateRangeFilter {
  field_id: string
  start_date?: string
  end_date?: string
}

export interface SearchFilters {
  field_filters?: FieldFilter[]
  numeric_ranges?: NumericRangeFilter[]
  date_ranges?: DateRangeFilter[]
  tags?: string[]
  created_by?: string
}

export interface FacetConfig {
  field_id: string
  facet_type: FacetType
  max_values?: number
  sort_by?: string
  sort_order?: SortOrder
}

export interface SortConfig {
  field_id: string
  order: SortOrder
}

export interface SearchRequest {
  query: string
  table_id?: string
  field_id?: string
  filters?: SearchFilters
  facets?: FacetConfig[]
  sort?: SortConfig[]
  limit?: number
  offset?: number
  min_score?: number
  highlight_results?: boolean
}

// =============================================================================
// Response Types
// =============================================================================

export interface FacetValue {
  value: string
  count: number
  is_selected?: boolean
}

export interface NumericFacetStats {
  min: number
  max: number
  avg: number
  count: number
}

export interface FacetResult {
  field_id: string
  field_name: string
  facet_type: FacetType
  values: FacetValue[]
  stats?: NumericFacetStats
  total_values: number
}

export interface SearchResult {
  record_id: string
  table_id: string
  base_id: string
  table_name: string
  fields: Record<string, unknown>
  score: number
  rank: number
  highlights?: Record<string, string[]>
  created_at?: string
  updated_at?: string
}

export interface SearchMetadata {
  query: string
  total_results: number
  total_results_filtered: number
  facets_computed: number
  execution_time_ms: number
  index_used?: string
  filters_applied?: boolean
  cache_hit?: boolean
}

export interface SearchResponse {
  results: SearchResult[]
  facets: FacetResult[]
  metadata: SearchMetadata
  limit: number
  offset: number
}

// =============================================================================
// Index Management Types
// =============================================================================

export interface IndexCreate {
  primary_key?: string
}

export interface IndexUpdate {
  searchable_attributes?: string[]
  filterable_attributes?: string[]
  sortable_attributes?: string[]
  ranking_rules?: string[]
  typo_tolerance?: Record<string, unknown>
  faceting?: Record<string, unknown>
  pagination?: Record<string, unknown>
}

export interface IndexStats {
  number_of_documents: number
  is_indexing: boolean
  field_distribution: Record<string, number>
}

export interface IndexResponse {
  success: boolean
  message: string
  index_name?: string
}

export interface ReindexRequest {
  batch_size?: number
}

// =============================================================================
// History/Analytics Types
// =============================================================================

export interface SearchHistoryEntry {
  search_id: string
  user_id: string
  query: string
  table_id?: string
  results_count: number
  filters_used?: boolean
  facets_used?: number
  execution_time_ms: number
  created_at: string
}

export interface SearchAnalytics {
  total_searches: number
  unique_users: number
  avg_execution_time_ms: number
  avg_results_per_search: number
  top_queries: Array<Record<string, unknown>>
  top_tables: Array<Record<string, number>>
  filter_usage_rate: number
  facet_usage_rate: number
  cache_hit_rate: number
  period_start: string
  period_end: string
}
