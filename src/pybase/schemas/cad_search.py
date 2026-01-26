"""
CAD search schemas for multi-modal retrieval.

Defines request/response schemas for CAD similarity search via text, image, and geometry.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class SearchModality(str, Enum):
    """Search modality types."""

    TEXT = "text"
    IMAGE = "image"
    GEOMETRY = "geometry"
    FUSED = "fused"
    SIMILAR_MODEL = "similar_model"


class QueryComplexity(str, Enum):
    """Query complexity for adaptive ef_search."""

    LOW = "low"  # Specific, well-defined query
    MEDIUM = "medium"
    HIGH = "high"  # Vague, exploratory query


# =============================================================================
# Request Schemas
# =============================================================================


class BBoxFilter(BaseModel):
    """Bounding box filter for spatial queries."""

    min_x: float = Field(..., description="Minimum X coordinate")
    min_y: float = Field(..., description="Minimum Y coordinate")
    min_z: float = Field(..., description="Minimum Z coordinate")
    max_x: float = Field(..., description="Maximum X coordinate")
    max_y: float = Field(..., description="Maximum Y coordinate")
    max_z: float = Field(..., description="Maximum Z coordinate")


class SearchFilters(BaseModel):
    """Filters for CAD search."""

    material: Optional[str] = Field(None, description="Material filter (e.g., 'steel', 'aluminum')")
    category_label: Optional[str] = Field(None, description="Category label filter")
    tags: Optional[list[str]] = Field(None, description="Tags to filter by")
    mass_min: Optional[float] = Field(None, ge=0, description="Minimum mass in kg")
    mass_max: Optional[float] = Field(None, ge=0, description="Maximum mass in kg")
    volume_min: Optional[float] = Field(None, ge=0, description="Minimum volume in cm3")
    volume_max: Optional[float] = Field(None, ge=0, description="Maximum volume in cm3")
    bbox: Optional[BBoxFilter] = Field(None, description="Bounding box filter")
    feature_types: Optional[list[str]] = Field(
        None, description="Manufacturing feature types (e.g., 'hole', 'fillet')"
    )
    file_type: Optional[str] = Field(None, description="File type filter (step, iges, etc.)")


class TextSearchRequest(BaseModel):
    """Request for text-to-CAD search."""

    query: str = Field(..., min_length=1, max_length=1000, description="Text description query")
    filters: Optional[SearchFilters] = Field(None, description="Optional search filters")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    min_similarity: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity threshold")
    use_cache: bool = Field(True, description="Use cached results if available")


class ImageSearchRequest(BaseModel):
    """Request for image-to-CAD search."""

    image_data: str = Field(
        ...,
        description="Base64 encoded image data or image URL",
    )
    filters: Optional[SearchFilters] = Field(None, description="Optional search filters")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    min_similarity: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity threshold")
    use_cache: bool = Field(True, description="Use cached results if available")


class GeometrySearchRequest(BaseModel):
    """Request for geometry (point cloud) to CAD search."""

    point_cloud: list[list[float]] = Field(
        ...,
        min_length=1,
        description="Nx3 point cloud array [[x,y,z], ...]",
    )
    filters: Optional[SearchFilters] = Field(None, description="Optional search filters")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    min_similarity: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity threshold")
    use_cache: bool = Field(True, description="Use cached results if available")


class SimilarModelRequest(BaseModel):
    """Request to find models similar to an existing model."""

    model_id: UUID = Field(..., description="Reference model ID")
    filters: Optional[SearchFilters] = Field(None, description="Optional search filters")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    min_similarity: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity threshold")
    exclude_self: bool = Field(True, description="Exclude the reference model from results")


class MultiModalSearchRequest(BaseModel):
    """Unified multi-modal search request."""

    text_query: Optional[str] = Field(None, description="Text description query")
    image_data: Optional[str] = Field(None, description="Base64 encoded image or URL")
    point_cloud: Optional[list[list[float]]] = Field(None, description="Nx3 point cloud")
    reference_model_id: Optional[UUID] = Field(None, description="Reference model ID")
    filters: Optional[SearchFilters] = Field(None, description="Optional search filters")
    top_k: int = Field(10, ge=1, le=100, description="Number of results to return")
    min_similarity: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity threshold")
    modality_weights: Optional[dict[str, float]] = Field(
        None,
        description="Weights for modalities (default: text=1.0, image=1.2, geometry=1.5)",
    )
    use_cache: bool = Field(True, description="Use cached results if available")


# =============================================================================
# Response Schemas
# =============================================================================


class ModalityScores(BaseModel):
    """Per-modality similarity scores."""

    text_similarity: Optional[float] = Field(None, description="Text embedding similarity")
    image_similarity: Optional[float] = Field(None, description="Image embedding similarity")
    geometry_similarity: Optional[float] = Field(None, description="Geometry embedding similarity")
    fused_similarity: Optional[float] = Field(None, description="Fused embedding similarity")
    shape_similarity: Optional[float] = Field(None, description="SDF latent shape similarity")
    topology_similarity: Optional[float] = Field(None, description="B-Rep graph topology similarity")


class CADSearchResult(BaseModel):
    """Single CAD model search result."""

    model_id: UUID = Field(..., description="CAD model ID")
    file_name: str = Field(..., description="File name")
    file_type: str = Field(..., description="File type (step, iges, etc.)")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Overall similarity score")
    rank: int = Field(..., ge=1, description="Result rank")

    # Metadata
    category_label: Optional[str] = Field(None, description="Category label")
    tags: list[str] = Field(default_factory=list, description="Tags")
    material: Optional[str] = Field(None, description="Material")
    mass_kg: Optional[float] = Field(None, description="Mass in kg")
    volume_cm3: Optional[float] = Field(None, description="Volume in cm3")
    bounding_box: Optional[dict[str, Any]] = Field(None, description="Bounding box")

    # Modality scores
    scores: Optional[ModalityScores] = Field(None, description="Per-modality similarity scores")

    # Rendering info
    has_rendered_views: bool = Field(default=False, description="Has pre-rendered views")
    preview_url: Optional[str] = Field(None, description="Preview image URL")


class SearchMetadata(BaseModel):
    """Search operation metadata."""

    query_complexity: QueryComplexity = Field(..., description="Detected query complexity")
    ef_search_used: int = Field(..., description="HNSW ef_search parameter used")
    candidates_retrieved: int = Field(..., description="Number of candidates retrieved")
    candidates_filtered: int = Field(..., description="Number filtered out")
    cache_hit: bool = Field(default=False, description="Results from cache")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    modalities_used: list[SearchModality] = Field(
        default_factory=list, description="Modalities used in search"
    )


class CADSearchResponse(BaseModel):
    """CAD search response."""

    results: list[CADSearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results (before pagination)")
    metadata: SearchMetadata = Field(..., description="Search metadata")


# =============================================================================
# History/Analytics Schemas
# =============================================================================


class SearchHistoryEntry(BaseModel):
    """Search history entry."""

    search_id: UUID = Field(..., description="Unique search ID")
    user_id: UUID = Field(..., description="User who performed search")
    query_type: SearchModality = Field(..., description="Type of search performed")
    query_summary: str = Field(..., description="Summary of query")
    results_count: int = Field(..., description="Number of results returned")
    execution_time_ms: float = Field(..., description="Execution time")
    created_at: datetime = Field(..., description="Search timestamp")


class SearchAnalytics(BaseModel):
    """Search analytics summary."""

    total_searches: int = Field(..., description="Total searches in period")
    searches_by_type: dict[str, int] = Field(
        default_factory=dict, description="Searches grouped by type"
    )
    avg_execution_time_ms: float = Field(..., description="Average execution time")
    cache_hit_rate: float = Field(..., ge=0.0, le=1.0, description="Cache hit rate")
    top_queries: list[dict[str, Any]] = Field(
        default_factory=list, description="Most common queries"
    )
    unique_users: int = Field(..., description="Number of unique users")
    period_start: datetime = Field(..., description="Analytics period start")
    period_end: datetime = Field(..., description="Analytics period end")
