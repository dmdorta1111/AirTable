"""
CAD search API endpoints for multi-modal retrieval.

Provides endpoints for text, image, geometry, and similar model search.
"""

import tempfile
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.logging import get_logger
from pybase.schemas.cad_search import (
    BBoxFilter,
    CADSearchResponse,
    GeometrySearchRequest,
    ImageSearchRequest,
    ModalityScores,
    MultiModalSearchRequest,
    QueryComplexity,
    SearchAnalytics,
    SearchFilters,
    SearchHistoryEntry,
    SearchMetadata,
    SimilarModelRequest,
    TextSearchRequest,
)
from pybase.services.coscad_retriever import (
    CosCADRetriever,
    RetrievalQuery,
    RetrievalResult,
    find_similar_models,
    text_search,
)
from pybase.services.retrieval_helpers import (
    MetricsCollector,
    QueryPreprocessor,
    ResultPostprocessor,
    get_metrics_collector,
)

logger = get_logger(__name__)

router = APIRouter()

# In-memory history storage (replace with DB in production)
_search_history: list[dict[str, Any]] = []


# =============================================================================
# Helper Functions
# =============================================================================


def retrieval_result_to_schema(result: RetrievalResult) -> dict[str, Any]:
    """Convert RetrievalResult to API response format."""
    scores_dict = None
    if result.modality_scores:
        scores_dict = ModalityScores(
            text_similarity=result.modality_scores.get("text_similarity"),
            image_similarity=result.modality_scores.get("image_similarity"),
            geometry_similarity=result.modality_scores.get("geometry_similarity"),
            fused_similarity=result.modality_scores.get("fused_similarity"),
            shape_similarity=result.modality_scores.get("shape_similarity"),
            topology_similarity=result.modality_scores.get("topology_similarity"),
        )

    return {
        "model_id": str(result.model_id),
        "file_name": result.file_name,
        "file_type": result.file_type,
        "similarity_score": result.similarity_score,
        "rank": result.rank,
        "category_label": result.metadata.get("category_label"),
        "tags": result.metadata.get("tags", []),
        "material": result.metadata.get("material"),
        "mass_kg": result.metadata.get("mass_kg"),
        "volume_cm3": result.metadata.get("volume_cm3"),
        "bounding_box": result.metadata.get("bounding_box"),
        "has_rendered_views": result.metadata.get("has_rendered_views", False),
        "preview_url": result.metadata.get("preview_url"),
        "scores": scores_dict,
    }


async def enrich_results_with_model_data(
    db: AsyncSession,
    results: list[RetrievalResult],
) -> list[RetrievalResult]:
    """Enrich results with full model data from database."""
    from sqlalchemy import select
    from pybase.models.cad_model import CADModel

    model_ids = [r.model_id for r in results if r.model_id]
    if not model_ids:
        return results

    stmt = select(CADModel).where(CADModel.id.in_(model_ids))
    db_result = await db.execute(stmt)
    models = {m.id: m for m in result.scalars()}

    for result in results:
        if result.model_id in models:
            model = models[result.model_id]
            result.metadata.update({
                "file_name": model.file_name,
                "file_type": model.file_type,
                "category_label": model.category_label,
                "tags": model.tags or [],
                "material": model.material,
                "mass_kg": model.mass_kg,
                "volume_cm3": model.volume_cm3,
                "bounding_box": model.bounding_box,
                "has_rendered_views": len(model.rendered_views) > 0 if model.rendered_views else False,
            })

    return results


def record_search_history(
    user_id: str | uuid.UUID,
    query_type: str,
    query_summary: str,
    results_count: int,
    execution_time_ms: float,
) -> None:
    """Record search in history."""
    entry = {
        "search_id": uuid.uuid4(),
        "user_id": user_id,
        "query_type": query_type,
        "query_summary": query_summary,
        "results_count": results_count,
        "execution_time_ms": execution_time_ms,
        "created_at": datetime.now(timezone.utc),
    }
    _search_history.append(entry)
    # Keep only last 1000 entries
    if len(_search_history) > 1000:
        _search_history.pop(0)


# =============================================================================
# Unified Semantic Search
# =============================================================================


@router.post(
    "/search/semantic",
    response_model=CADSearchResponse,
    summary="Unified semantic search",
    description="Search CAD models using text, image, geometry, or combined modalities.",
    tags=["CAD Search"],
)
async def semantic_search(
    request: MultiModalSearchRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> CADSearchResponse:
    """
    Unified multi-modal semantic search for CAD models.

    **Supported Modalities:**
    - **Text**: Natural language description (e.g., "steel bracket m10")
    - **Image**: Base64 encoded image or URL
    - **Geometry**: Point cloud as Nx3 array
    - **Reference**: Find models similar to existing model_id

    **Query Examples:**

    *Text search:*
    ```json
    {
        "text_query": "mounting bracket with m10 hole",
        "top_k": 10,
        "filters": {"material": "steel"}
    }
    ```

    *Image search:*
    ```json
    {
        "image_data": "data:image/png;base64,iVBORw0KG...",
        "top_k": 10
    }
    ```

    *Combined search:*
    ```json
    {
        "text_query": "bracket",
        "image_data": "https://example.com/bracket.png",
        "modality_weights": {"text": 1.0, "image": 1.5}
    }
    ```

    **Response:**
    - Results ranked by similarity score (0-1)
    - Per-modality similarity scores
    - Model metadata (material, mass, category, etc.)

    Args:
        request: Multi-modal search request

    Returns:
        Search results with metadata
    """
    retriever = CosCADRetriever(session=db)

    # Build query
    query = RetrievalQuery(
        text=request.text_query,
        image_data=request.image_data,
        point_cloud=request.point_cloud,
        reference_model_id=request.reference_model_id,
        filters=request.filters,
        modality_weights=request.modality_weights,
    )

    # Execute search
    results, metadata = await retriever.retrieve(
        query=query,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
        use_cache=request.use_cache,
    )

    # Enrich with model data
    results = await enrich_results_with_model_data(db, results)

    # Record history
    record_search_history(
        user_id=current_user.id,
        query_type=metadata["modalities_used"][0] if metadata["modalities_used"] else "semantic",
        query_summary=f"multi_modal: {request.text_query or '<image>' or '<geometry>'}",
        results_count=len(results),
        execution_time_ms=metadata["execution_time_ms"],
    )

    # Convert to response format
    return CADSearchResponse(
        results=[retrieval_result_to_schema(r) for r in results],
        total_results=len(results),
        metadata=SearchMetadata(**metadata),
    )


# =============================================================================
# Text-to-CAD Search
# =============================================================================


@router.post(
    "/search/text",
    response_model=CADSearchResponse,
    summary="Text-to-CAD search",
    description="Find CAD models using natural language description.",
    tags=["CAD Search"],
)
async def text_search_endpoint(
    request: TextSearchRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> CADSearchResponse:
    """
    Search CAD models by text description.

    Uses CLIP text embeddings for cross-modal retrieval.

    **Example Request:**
    ```json
    {
        "query": "steel L-bracket with 10mm mounting holes",
        "filters": {
            "material": "steel",
            "mass_min": 0.01,
            "mass_max": 1.0
        },
        "top_k": 10,
        "min_similarity": 0.6
    }
    ```

    **Supported Filters:**
    - `material`: Material type
    - `category_label`: Category (bracket, fastener, etc.)
    - `tags`: List of tags
    - `mass_min/max`: Mass range in kg
    - `volume_min/max`: Volume range in cm3
    - `bbox`: Bounding box filter
    - `feature_types`: Manufacturing features

    Args:
        request: Text search request

    Returns:
        Search results with similarity scores
    """
    retriever = CosCADRetriever(session=db)

    query = RetrievalQuery(
        text=request.query,
        filters=request.filters,
    )

    results, metadata = await retriever.retrieve(
        query=query,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
        use_cache=request.use_cache,
    )

    results = await enrich_results_with_model_data(db, results)

    record_search_history(
        user_id=current_user.id,
        query_type="text",
        query_summary=request.query[:100],
        results_count=len(results),
        execution_time_ms=metadata["execution_time_ms"],
    )

    return CADSearchResponse(
        results=[retrieval_result_to_schema(r) for r in results],
        total_results=len(results),
        metadata=SearchMetadata(**metadata),
    )


# =============================================================================
# Image-to-CAD Search
# =============================================================================


@router.post(
    "/search/image",
    response_model=CADSearchResponse,
    summary="Image-to-CAD search",
    description="Find CAD models similar to a reference image.",
    tags=["CAD Search"],
)
async def image_search_endpoint(
    request: ImageSearchRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> CADSearchResponse:
    """
    Search CAD models using a reference image.

    Supports base64 encoded images or image URLs.

    **Example Request (Base64):**
    ```json
    {
        "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...",
        "top_k": 10,
        "min_similarity": 0.6
    }
    ```

    **Example Request (URL):**
    ```json
    {
        "image_data": "https://example.com/bracket.png",
        "top_k": 10
    }
    ```

    **Multi-part Form Alternative:**
    Upload image directly via `/api/v1/cad/search/image/upload`

    Args:
        request: Image search request

    Returns:
        Similar CAD models with similarity scores
    """
    retriever = CosCADRetriever(session=db)

    query = RetrievalQuery(
        image_data=request.image_data,
        filters=request.filters,
    )

    results, metadata = await retriever.retrieve(
        query=query,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
        use_cache=request.use_cache,
    )

    results = await enrich_results_with_model_data(db, results)

    record_search_history(
        user_id=current_user.id,
        query_type="image",
        query_summary="<image>",
        results_count=len(results),
        execution_time_ms=metadata["execution_time_ms"],
    )

    return CADSearchResponse(
        results=[retrieval_result_to_schema(r) for r in results],
        total_results=len(results),
        metadata=SearchMetadata(**metadata),
    )


@router.post(
    "/search/image/upload",
    response_model=CADSearchResponse,
    summary="Image-to-CAD search (file upload)",
    description="Upload an image file to find similar CAD models.",
    tags=["CAD Search"],
)
async def image_search_upload(
    file: Annotated[
        UploadFile,
        File(description="Image file (PNG, JPG, etc.)")
    ],
    current_user: CurrentUser,
    db: DbSession,
    filters: Annotated[
        str | None,
        Form(description="JSON-encoded filters (optional)")
    ] = None,
    top_k: Annotated[
        int,
        Form(ge=1, le=100),
    ] = 10,
    min_similarity: Annotated[
        float,
        Form(ge=0.0, le=1.0),
    ] = 0.5,
) -> CADSearchResponse:
    """
    Upload an image file to find similar CAD models.

    **Usage:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/cad/search/image/upload" \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -F "file=@bracket.png" \\
      -F "top_k=10"
    ```

    Args:
        file: Uploaded image file
        filters: Optional JSON-encoded filters
        top_k: Number of results
        min_similarity: Minimum similarity threshold

    Returns:
        Similar CAD models
    """
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Check file size (5MB limit)
    MAX_SIZE = 5 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {MAX_SIZE // 1024 // 1024}MB)",
        )

    # Encode to base64
    import base64
    import io
    from PIL import Image

    try:
        # Validate and optimize image
        img = Image.open(io.BytesIO(content))
        img = img.convert("RGB")

        # Resize if too large
        max_dim = 1024
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim))

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        image_data = f"data:image/png;base64,{image_base64}"

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image file: {str(e)}",
        )

    # Parse filters
    parsed_filters = None
    if filters:
        try:
            import json
            parsed_filters = json.loads(filters)
        except json.JSONDecodeError:
            pass

    # Create and execute query
    retriever = CosCADRetriever(session=db)
    query = RetrievalQuery(image_data=image_data, filters=parsed_filters)

    results, metadata = await retriever.retrieve(
        query=query,
        top_k=top_k,
        min_similarity=min_similarity,
    )

    results = await enrich_results_with_model_data(db, results)

    return CADSearchResponse(
        results=[retrieval_result_to_schema(r) for r in results],
        total_results=len(results),
        metadata=SearchMetadata(**metadata),
    )


# =============================================================================
# Geometry Search
# =============================================================================


@router.post(
    "/search/geometry",
    response_model=CADSearchResponse,
    summary="Geometry-to-CAD search",
    description="Find CAD models similar to a point cloud.",
    tags=["CAD Search"],
)
async def geometry_search_endpoint(
    request: GeometrySearchRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> CADSearchResponse:
    """
    Search CAD models using point cloud geometry.

    **Example Request:**
    ```json
    {
        "point_cloud": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], ...],
        "filters": {"mass_max": 1.0},
        "top_k": 10
    }
    ```

    The point cloud should be normalized to unit space for best results.

    Args:
        request: Geometry search request

    Returns:
        Similar CAD models
    """
    # Validate point cloud
    if not QueryPreprocessor.validate_point_cloud(request.point_cloud):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid point_cloud format. Expected Nx3 array of floats.",
        )

    retriever = CosCADRetriever(session=db)

    query = RetrievalQuery(
        point_cloud=request.point_cloud,
        filters=request.filters,
    )

    results, metadata = await retriever.retrieve(
        query=query,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
        use_cache=request.use_cache,
    )

    results = await enrich_results_with_model_data(db, results)

    record_search_history(
        user_id=current_user.id,
        query_type="geometry",
        query_summary=f"{len(request.point_cloud)} points",
        results_count=len(results),
        execution_time_ms=metadata["execution_time_ms"],
    )

    return CADSearchResponse(
        results=[retrieval_result_to_schema(r) for r in results],
        total_results=len(results),
        metadata=SearchMetadata(**metadata),
    )


# =============================================================================
# Similar Model Search
# =============================================================================


@router.post(
    "/search/similar/{model_id}",
    response_model=CADSearchResponse,
    summary="Find similar models",
    description="Find CAD models similar to an existing model.",
    tags=["CAD Search"],
)
async def similar_models_endpoint(
    model_id: str,
    current_user: CurrentUser,
    db: DbSession,
    request: SimilarModelRequest | None = None,
) -> CADSearchResponse:
    """
    Find CAD models similar to a given model.

    Uses the embeddings of the reference model to find similar items.

    **Example Request:**
    ```json
    {
        "filters": {"material": "steel"},
        "top_k": 10,
        "min_similarity": 0.7,
        "exclude_self": true
    }
    ```

    Args:
        model_id: Reference model UUID
        request: Search parameters

    Returns:
        Similar CAD models ranked by similarity
    """
    from uuid import UUID

    try:
        model_uuid = UUID(model_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid model_id format",
        )

    # Use defaults if request not provided
    if request is None:
        request = SimilarModelRequest(model_id=model_uuid)

    retriever = CosCADRetriever(session=db)

    query = RetrievalQuery(
        reference_model_id=model_uuid,
        filters=request.filters,
    )

    exclude_id = model_uuid if request.exclude_self else None

    results, metadata = await retriever.retrieve(
        query=query,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
        exclude_model_id=exclude_id,
    )

    results = await enrich_results_with_model_data(db, results)

    record_search_history(
        user_id=current_user.id,
        query_type="similar_model",
        query_summary=f"model:{model_id}",
        results_count=len(results),
        execution_time_ms=metadata["execution_time_ms"],
    )

    return CADSearchResponse(
        results=[retrieval_result_to_schema(r) for r in results],
        total_results=len(results),
        metadata=SearchMetadata(**metadata),
    )


# =============================================================================
# Search History & Analytics
# =============================================================================


@router.get(
    "/search/history",
    response_model=dict[str, Any],
    summary="Get search history",
    description="Get recent searches for the current user.",
    tags=["CAD Search"],
)
async def get_search_history(
    current_user: CurrentUser,
    limit: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
) -> dict[str, Any]:
    """
    Get search history for the current user.

    Returns recent searches with metadata.

    Args:
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        List of search history entries
    """
    # Filter by user
    user_history = [
        h for h in _search_history
        if str(h["user_id"]) == str(current_user.id)
    ]

    # Sort by created_at descending
    user_history = sorted(user_history, key=lambda x: x["created_at"], reverse=True)

    # Paginate
    total = len(user_history)
    paginated = user_history[offset:offset + limit]

    entries = [
        SearchHistoryEntry(
            search_id=h["search_id"],
            user_id=h["user_id"],
            query_type=h["query_type"],
            query_summary=h["query_summary"],
            results_count=h["results_count"],
            execution_time_ms=h["execution_time_ms"],
            created_at=h["created_at"],
        )
        for h in paginated
    ]

    return {
        "items": entries,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/search/analytics",
    response_model=SearchAnalytics,
    summary="Get search analytics",
    description="Get search usage analytics and statistics.",
    tags=["CAD Search"],
)
async def get_search_analytics(
    current_user: CurrentUser,
    period_days: Annotated[
        int,
        Query(ge=1, le=90),
    ] = 7,
) -> SearchAnalytics:
    """
    Get search analytics for the current user.

    Returns statistics including:
    - Total searches
    - Searches by type
    - Average execution time
    - Cache hit rate
    - Most common queries

    Args:
        period_days: Number of days to analyze (1-90)

    Returns:
        Search analytics summary
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

    # Filter user's searches in period
    user_searches = [
        h for h in _search_history
        if str(h["user_id"]) == str(current_user.id) and h["created_at"] >= cutoff
    ]

    # Get metrics from collector
    metrics = get_metrics_collector()
    stats = metrics.get_stats()

    # Calculate user-specific stats
    total_searches = len(user_searches)
    searches_by_type: dict[str, int] = {}
    total_execution_time = 0.0

    for s in user_searches:
        searches_by_type[s["query_type"]] = searches_by_type.get(s["query_type"], 0) + 1
        total_execution_time += s["execution_time_ms"]

    # Top queries for this user
    query_counts: dict[str, int] = {}
    for s in user_searches:
        query_counts[s["query_summary"]] = query_counts.get(s["query_summary"], 0) + 1
    top_queries = [
        {"query": k, "count": v}
        for k, v in sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    return SearchAnalytics(
        total_searches=total_searches,
        searches_by_type=searches_by_type,
        avg_execution_time_ms=total_execution_time / total_searches if total_searches > 0 else 0,
        cache_hit_rate=stats["cache_hit_rate"],
        top_queries=top_queries,
        unique_users=1,  # Always 1 for user-specific endpoint
        period_start=cutoff,
        period_end=datetime.now(timezone.utc),
    )


# =============================================================================
# Cache Management
# =============================================================================


@router.post(
    "/search/cache/clear",
    response_model=dict[str, Any],
    summary="Clear search cache",
    description="Clear the search result cache.",
    tags=["CAD Search"],
)
async def clear_search_cache(
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Clear the search cache.

    Returns cache statistics before clearing.

    Returns:
        Cache statistics
    """
    from pybase.services.retrieval_helpers import get_search_cache

    cache = get_search_cache()
    stats = cache.get_stats()

    cache.invalidate()

    return {
        "message": "Cache cleared",
        "previous_stats": stats,
    }


@router.get(
    "/search/cache/stats",
    response_model=dict[str, Any],
    summary="Get cache statistics",
    description="Get search cache statistics.",
    tags=["CAD Search"],
)
async def get_cache_stats(
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Get search cache statistics.

    Returns:
        Cache statistics including size, hit rate, etc.
    """
    from pybase.services.retrieval_helpers import get_search_cache

    cache = get_search_cache()
    return cache.get_stats()
