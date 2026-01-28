/**
 * Search API client for PyBase backend.
 *
 * Provides functions for full-text search with faceted navigation support.
 */

import type {
  DateRangeFilter,
  FacetConfig,
  FieldFilter,
  IndexCreate,
  IndexResponse,
  IndexStats,
  IndexUpdate,
  NumericRangeFilter,
  ReindexRequest,
  SearchFilters,
  SearchRequest,
  SearchResponse,
  SortConfig,
} from "@/types/search"
import { get, post, put, del } from "../api"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"

/**
 * Execute a search within a specific base.
 *
 * @param baseId - The base/workspace ID to search within
 * @param request - Search request parameters
 * @returns Promise<SearchResponse> with results and facets
 *
 * @example
 * ```ts
 * const results = await searchInBase("base-123", {
 *   query: "dimension",
 *   limit: 20,
 *   highlight_results: true,
 * })
 * ```
 */
export async function searchInBase(
  baseId: string,
  request: SearchRequest
): Promise<SearchResponse> {
  const url = `/api/v1/bases/${baseId}/search`
  return post<SearchResponse>(url, request)
}

/**
 * Execute a global search across all accessible bases.
 *
 * @param request - Search request parameters
 * @returns Promise<SearchResponse> with results and facets
 *
 * @example
 * ```ts
 * const results = await globalSearch({
 *   query: "part name",
 *   limit: 20,
 * })
 * ```
 */
export async function globalSearch(request: SearchRequest): Promise<SearchResponse> {
  const url = "/api/v1/search"
  return post<SearchResponse>(url, request)
}

/**
 * Create a search index for a base.
 *
 * @param baseId - The base/workspace ID
 * @param indexData - Index configuration
 * @returns Promise<IndexResponse> with operation result
 *
 * @example
 * ```ts
 * const result = await createBaseIndex("base-123", {
 *   primary_key: "id",
 * })
 * ```
 */
export async function createBaseIndex(
  baseId: string,
  indexData: IndexCreate
): Promise<IndexResponse> {
  const url = `/api/v1/indexes/base/${baseId}`
  return post<IndexResponse>(url, indexData)
}

/**
 * Get statistics for a base's search index.
 *
 * @param baseId - The base/workspace ID
 * @returns Promise<IndexStats> with document count and field distribution
 *
 * @example
 * ```ts
 * const stats = await getBaseIndexStats("base-123")
 * console.log(`${stats.number_of_documents} documents indexed`)
 * ```
 */
export async function getBaseIndexStats(baseId: string): Promise<IndexStats> {
  const url = `/api/v1/indexes/base/${baseId}`
  return get<IndexStats>(url)
}

/**
 * Update settings for a base's search index.
 *
 * @param baseId - The base/workspace ID
 * @param indexData - Index settings to update
 * @returns Promise<IndexResponse> with operation result
 *
 * @example
 * ```ts
 * const result = await updateBaseIndex("base-123", {
 *   searchable_attributes: ["name", "description"],
 *   filterable_attributes: ["status", "category"],
 * })
 * ```
 */
export async function updateBaseIndex(
  baseId: string,
  indexData: IndexUpdate
): Promise<IndexResponse> {
  const url = `/api/v1/indexes/base/${baseId}`
  return put<IndexResponse>(url, indexData)
}

/**
 * Delete a base's search index.
 *
 * @param baseId - The base/workspace ID
 * @returns Promise<void>
 *
 * @example
 * ```ts
 * await deleteBaseIndex("base-123")
 * ```
 */
export async function deleteBaseIndex(baseId: string): Promise<void> {
  const url = `/api/v1/indexes/base/${baseId}`
  return del<void>(url)
}

/**
 * Reindex all records in a base.
 *
 * Triggers asynchronous reindexing of all tables and records.
 *
 * @param baseId - The base/workspace ID
 * @param reindexData - Reindex configuration options
 * @returns Promise<IndexResponse> with operation result
 *
 * @example
 * ```ts
 * const result = await reindexBase("base-123", {
 *   batch_size: 1000,
 * })
 * console.log(result.message)
 * ```
 */
export async function reindexBase(
  baseId: string,
  reindexData: ReindexRequest = {}
): Promise<IndexResponse> {
  const url = `/api/v1/indexes/base/${baseId}/reindex`
  return post<IndexResponse>(url, reindexData)
}

// =============================================================================
// Helper Types for Building Search Requests
// =============================================================================

/**
 * Builder class for constructing search requests with type safety.
 *
 * @example
 * ```ts
 * const request = new SearchRequestBuilder()
 *   .withQuery("dimension")
 *   .withTableFilter("tbl-123")
 *   .withFieldFilter("status", "eq", "active")
 *   .withFacet("category", "string", 10)
 *   .withLimit(20)
 *   .build()
 *
 * const results = await searchInBase("base-123", request)
 * ```
 */
export class SearchRequestBuilder {
  private request: SearchRequest = {
    query: "",
    highlight_results: true,
    limit: 20,
    offset: 0,
  }

  withQuery(query: string): SearchRequestBuilder {
    this.request.query = query
    return this
  }

  withTableFilter(tableId: string): SearchRequestBuilder {
    this.request.table_id = tableId
    return this
  }

  withFieldFilter(
    fieldId: string,
    operator: FieldFilter["operator"],
    value: unknown
  ): SearchRequestBuilder {
    if (!this.request.filters) {
      this.request.filters = {}
    }
    if (!this.request.filters.field_filters) {
      this.request.filters.field_filters = []
    }
    this.request.filters.field_filters.push({
      field_id: fieldId,
      operator,
      value,
    })
    return this
  }

  withNumericRange(
    fieldId: string,
    min?: number,
    max?: number
  ): SearchRequestBuilder {
    if (!this.request.filters) {
      this.request.filters = {}
    }
    if (!this.request.filters.numeric_ranges) {
      this.request.filters.numeric_ranges = []
    }
    this.request.filters.numeric_ranges.push({
      field_id: fieldId,
      min_value: min,
      max_value: max,
    })
    return this
  }

  withDateRange(
    fieldId: string,
    startDate?: string,
    endDate?: string
  ): SearchRequestBuilder {
    if (!this.request.filters) {
      this.request.filters = {}
    }
    if (!this.request.filters.date_ranges) {
      this.request.filters.date_ranges = []
    }
    this.request.filters.date_ranges.push({
      field_id: fieldId,
      start_date: startDate,
      end_date: endDate,
    })
    return this
  }

  withTagFilter(tags: string[]): SearchRequestBuilder {
    if (!this.request.filters) {
      this.request.filters = {}
    }
    this.request.filters.tags = tags
    return this
  }

  withCreatorFilter(userId: string): SearchRequestBuilder {
    if (!this.request.filters) {
      this.request.filters = {}
    }
    this.request.filters.created_by = userId
    return this
  }

  withFacet(
    fieldId: string,
    facetType: FacetConfig["facet_type"],
    maxValues: number = 10
  ): SearchRequestBuilder {
    if (!this.request.facets) {
      this.request.facets = []
    }
    this.request.facets.push({
      field_id: fieldId,
      facet_type: facetType,
      max_values: maxValues,
    })
    return this
  }

  withSort(fieldId: string, order: SortConfig["order"] = "asc"): SearchRequestBuilder {
    if (!this.request.sort) {
      this.request.sort = []
    }
    this.request.sort.push({
      field_id: fieldId,
      order,
    })
    return this
  }

  withLimit(limit: number): SearchRequestBuilder {
    this.request.limit = limit
    return this
  }

  withOffset(offset: number): SearchRequestBuilder {
    this.request.offset = offset
    return this
  }

  withMinScore(score: number): SearchRequestBuilder {
    this.request.min_score = score
    return this
  }

  withHighlighting(enabled: boolean): SearchRequestBuilder {
    this.request.highlight_results = enabled
    return this
  }

  build(): SearchRequest {
    // Validate required fields
    if (!this.request.query) {
      throw new Error("Search query is required")
    }
    return { ...this.request }
  }
}
