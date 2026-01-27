"""
Search schemas for PyBase.

Defines request/response schemas for full-text search with faceted navigation support.
"""

from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class FacetType(str, Enum):
    """Facet types for different field data types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    ARRAY = "array"


class SortOrder(str, Enum):
    """Sort order for results and facets."""

    ASC = "asc"
    DESC = "desc"
    RELEVANCE = "relevance"


# =============================================================================
# Request Schemas
# =============================================================================


class FieldFilter(BaseModel):
    """Individual field filter for faceted search."""

    field_id: str = Field(..., description="Field identifier to filter on")
    operator: str = Field(
        ...,
        description="Comparison operator (eq, ne, gt, lt, gte, lte, in, contains)",
    )
    value: Any = Field(..., description="Filter value")


class NumericRangeFilter(BaseModel):
    """Numeric range filter for continuous values."""

    field_id: str = Field(..., description="Field identifier to filter on")
    min_value: Optional[float] = Field(None, description="Minimum value (inclusive)")
    max_value: Optional[float] = Field(None, description="Maximum value (inclusive)")


class DateRangeFilter(BaseModel):
    """Date range filter for date fields."""

    field_id: str = Field(..., description="Field identifier to filter on")
    start_date: Optional[str] = Field(None, description="Start date ISO format")
    end_date: Optional[str] = Field(None, description="End date ISO format")


class SearchFilters(BaseModel):
    """Structured filters for search refinement."""

    field_filters: Optional[list[FieldFilter]] = Field(
        None, description="Field-specific filters"
    )
    numeric_ranges: Optional[list[NumericRangeFilter]] = Field(
        None, description="Numeric range filters"
    )
    date_ranges: Optional[list[DateRangeFilter]] = Field(
        None, description="Date range filters"
    )
    tags: Optional[list[str]] = Field(None, description="Tags to filter by")
    created_by: Optional[UUID] = Field(None, description="Filter by creator user ID")


class FacetConfig(BaseModel):
    """Configuration for a single facet."""

    field_id: str = Field(..., description="Field to compute facet on")
    facet_type: FacetType = Field(..., description="Data type of facet field")
    max_values: int = Field(
        10, ge=1, le=100, description="Maximum number of facet values to return"
    )
    sort_by: str = Field("count", description="Sort facet values by: count, alpha, or value")
    sort_order: SortOrder = Field(SortOrder.DESC, description="Sort order")


class SortConfig(BaseModel):
    """Sorting configuration for search results."""

    field_id: str = Field(..., description="Field to sort by")
    order: SortOrder = Field(SortOrder.ASC, description="Sort direction")


class SearchRequest(BaseModel):
    """Search request parameters with faceted search support."""

    query: str = Field(..., min_length=1, max_length=1000, description="Search query string")
    table_id: Optional[str] = Field(None, description="Limit search to specific table")
    field_id: Optional[str] = Field(None, description="Limit search to specific field")
    filters: Optional[SearchFilters] = Field(None, description="Structured search filters")
    facets: Optional[list[FacetConfig]] = Field(
        None, description="Facet configurations for aggregation"
    )
    sort: Optional[list[SortConfig]] = Field(None, description="Result sorting configuration")
    limit: int = Field(20, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum relevance score")
    highlight_results: bool = Field(
        True, description="Enable text highlighting in results"
    )


# =============================================================================
# Response Schemas
# =============================================================================


class FacetValue(BaseModel):
    """Single facet value with count."""

    value: str = Field(..., description="Facet value")
    count: int = Field(..., ge=0, description="Number of matching records")
    is_selected: bool = Field(default=False, description="Whether this value is currently filtered")


class NumericFacetStats(BaseModel):
    """Statistical summary for numeric facets."""

    min: float = Field(..., description="Minimum value in result set")
    max: float = Field(..., description="Maximum value in result set")
    avg: float = Field(..., description="Average value")
    count: int = Field(..., ge=0, description="Number of values")


class FacetResult(BaseModel):
    """Facet aggregation result."""

    field_id: str = Field(..., description="Field identifier")
    field_name: str = Field(..., description="Human-readable field name")
    facet_type: FacetType = Field(..., description="Data type of facet")
    values: list[FacetValue] = Field(
        default_factory=list, description="Top facet values with counts"
    )
    stats: Optional[NumericFacetStats] = Field(
        None, description="Numeric statistics for numeric/date facets"
    )
    total_values: int = Field(..., ge=0, description="Total unique values for this facet")


class SearchResult(BaseModel):
    """Individual search result with enhanced metadata."""

    record_id: str = Field(..., description="Record identifier")
    table_id: str = Field(..., description="Table identifier")
    base_id: str = Field(..., description="Base/workspace identifier")
    table_name: str = Field(..., description="Table name")
    fields: dict[str, Any] = Field(..., description="Record field data")
    score: float = Field(..., ge=0, le=1, description="Relevance score")
    rank: int = Field(..., ge=1, description="Result rank")
    highlights: Optional[dict[str, list[str]]] = Field(
        default=None, description="Matched text segments with highlighting"
    )
    created_at: Optional[str] = Field(None, description="Record creation timestamp")
    updated_at: Optional[str] = Field(None, description="Record update timestamp")


class SearchMetadata(BaseModel):
    """Search operation metadata."""

    query: str = Field(..., description="Search query executed")
    total_results: int = Field(..., description="Total matching records")
    total_results_filtered: int = Field(
        ...,
        description="Total results after applying filters (before pagination)",
    )
    facets_computed: int = Field(..., description="Number of facets computed")
    execution_time_ms: float = Field(..., description="Query execution time in milliseconds")
    index_used: Optional[str] = Field(None, description="Search index used")
    filters_applied: bool = Field(default=False, description="Whether filters were applied")
    cache_hit: bool = Field(default=False, description="Results from cache")


class SearchResponse(BaseModel):
    """Search response with results, facets, and metadata."""

    results: list[SearchResult] = Field(..., description="Search results")
    facets: list[FacetResult] = Field(
        default_factory=list, description="Faceted navigation results"
    )
    metadata: SearchMetadata = Field(..., description="Search operation metadata")
    limit: int = Field(..., description="Page size limit")
    offset: int = Field(..., description="Pagination offset")


# =============================================================================
# History/Analytics Schemas
# =============================================================================


class SearchHistoryEntry(BaseModel):
    """Search history entry for analytics."""

    search_id: UUID = Field(..., description="Unique search ID")
    user_id: UUID = Field(..., description="User who performed search")
    query: str = Field(..., description="Search query")
    table_id: Optional[str] = Field(None, description="Table searched")
    results_count: int = Field(..., description="Number of results returned")
    filters_used: bool = Field(default=False, description="Whether filters were applied")
    facets_used: int = Field(default=0, description="Number of facets used")
    execution_time_ms: float = Field(..., description="Execution time")
    created_at: str = Field(..., description="Search timestamp")


class SearchAnalytics(BaseModel):
    """Search analytics summary."""

    total_searches: int = Field(..., description="Total searches in period")
    unique_users: int = Field(..., description="Number of unique users")
    avg_execution_time_ms: float = Field(..., description="Average execution time")
    avg_results_per_search: float = Field(..., description="Average results returned")
    top_queries: list[dict[str, Any]] = Field(
        default_factory=list, description="Most common queries"
    )
    top_tables: list[dict[str, int]] = Field(
        default_factory=list, description="Most searched tables"
    )
    filter_usage_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of searches using filters",
    )
    facet_usage_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of searches using facets",
    )
    cache_hit_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Cache hit rate",
    )
    period_start: str = Field(..., description="Analytics period start")
    period_end: str = Field(..., description="Analytics period end")


# =============================================================================
# Index Management Schemas
# =============================================================================


class IndexCreate(BaseModel):
    """Request schema for creating a search index."""

    primary_key: str = Field(
        default="id",
        description="Primary key for documents in the index",
    )


class IndexUpdate(BaseModel):
    """Request schema for updating search index settings."""

    searchable_attributes: Optional[list[str]] = Field(
        None,
        description="Fields to search in",
    )
    filterable_attributes: Optional[list[str]] = Field(
        None,
        description="Fields to filter on",
    )
    sortable_attributes: Optional[list[str]] = Field(
        None,
        description="Fields to sort by",
    )
    ranking_rules: Optional[list[str]] = Field(
        None,
        description="Ranking rules for relevance",
    )
    typo_tolerance: Optional[dict[str, Any]] = Field(
        None,
        description="Typo tolerance settings",
    )
    faceting: Optional[dict[str, Any]] = Field(
        None,
        description="Faceting configuration",
    )
    pagination: Optional[dict[str, Any]] = Field(
        None,
        description="Pagination settings",
    )


class IndexStats(BaseModel):
    """Response schema for index statistics."""

    number_of_documents: int = Field(..., description="Number of indexed documents")
    is_indexing: bool = Field(..., description="Whether index is currently building")
    field_distribution: dict[str, int] = Field(
        ...,
        description="Document count per field",
    )


class IndexResponse(BaseModel):
    """Response schema for index operations."""

    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Operation result message")
    index_name: Optional[str] = Field(None, description="Name of the index")


class ReindexRequest(BaseModel):
    """Request schema for reindexing a base."""

    batch_size: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Number of records to index per batch",
    )
