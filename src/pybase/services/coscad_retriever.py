"""
CosCAD-inspired multi-modal CAD retrieval service.

Implements tri-indexed search: LSH buckets -> HNSW -> reranking.
Supports text, image, and geometry queries with fusion.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pybase.core.logging import get_logger
from pybase.db.vector_search import VectorSearchService, VectorSearchParams
from pybase.models.cad_model import CADModel, CADModelEmbedding
from pybase.schemas.cad_search import (
    BBoxFilter,
    QueryComplexity,
    SearchFilters,
    SearchModality,
)
from pybase.services.embedding_generator import EmbeddingGenerator, get_embedding_generator
from pybase.services.retrieval_helpers import (
    MetricsCollector,
    QueryPreprocessor,
    ResultPostprocessor,
    SearchCache,
    SearchTimer,
    get_metrics_collector,
    get_search_cache,
)

logger = get_logger(__name__)


# =============================================================================
# Search Query
# =============================================================================


class RetrievalQuery:
    """
    Multi-modal query for CAD retrieval.

    Supports text, image, geometry, or combined queries.
    """

    def __init__(
        self,
        text: str | None = None,
        image_data: str | None = None,
        point_cloud: list[list[float]] | np.ndarray | None = None,
        reference_model_id: UUID | str | None = None,
        filters: SearchFilters | dict[str, Any] | None = None,
        modality_weights: dict[str, float] | None = None,
    ):
        self.text = text
        self.image_data = image_data
        self.point_cloud = point_cloud
        self.reference_model_id = (
            UUID(str(reference_model_id)) if reference_model_id else None
        )
        self.filters = filters if isinstance(filters, SearchFilters) else None
        self.raw_filters = filters
        self.modality_weights = modality_weights

        # Embedded representations (populated during retrieval)
        self.text_embedding: list[float] | None = None
        self.image_embedding: list[float] | None = None
        self.geometry_embedding: list[float] | None = None
        self.fused_embedding: list[float] | None = None

    @property
    def has_text(self) -> bool:
        return bool(self.text)

    @property
    def has_image(self) -> bool:
        return bool(self.image_data)

    @property
    def has_geometry(self) -> bool:
        return bool(self.point_cloud)

    @property
    def has_reference(self) -> bool:
        return self.reference_model_id is not None

    @property
    def modality_count(self) -> int:
        return sum([self.has_text, self.has_image, self.has_geometry, self.has_reference])


# =============================================================================
# Retrieval Result
# =============================================================================


class RetrievalResult:
    """Result from CAD similarity search."""

    def __init__(
        self,
        model_id: UUID,
        file_name: str,
        file_type: str,
        similarity_score: float,
        rank: int = 0,
        metadata: dict[str, Any] | None = None,
        modality_scores: dict[str, float] | None = None,
    ):
        self.model_id = model_id
        self.file_name = file_name
        self.file_type = file_type
        self.similarity_score = similarity_score
        self.rank = rank
        self.metadata = metadata or {}
        self.modality_scores = modality_scores or {}


# =============================================================================
# CosCAD Retriever
# =============================================================================


class CosCADRetriever:
    """
    CosCAD-inspired multi-modal CAD retrieval system.

    Pipeline:
    1. Encode query modalities (text, image, geometry)
    2. Fuse embeddings for combined search
    3. LSH bucket filter (coarse pruning)
    4. HNSW vector search via VectorSearchService
    5. Re-rank with per-modality scores
    6. Apply metadata filters

    Uses tri-indexed search for optimal performance:
    - LSH buckets for coarse filtering
    - HNSW for fast ANN search
    - Per-modality reranking for precision
    """

    # Default modality weights (higher weight = more influence)
    DEFAULT_WEIGHTS = {
        "text": 1.0,
        "image": 1.2,
        "geometry": 1.5,
        "reference": 1.0,
    }

    # Adaptive ef_search based on query complexity
    EF_SEARCH_MAP = {
        QueryComplexity.LOW: 50,     # Specific query, faster search
        QueryComplexity.MEDIUM: 100,  # Default
        QueryComplexity.HIGH: 200,    # Vague query, higher recall
    }

    def __init__(
        self,
        session: AsyncSession,
        embedding_generator: EmbeddingGenerator | None = None,
        cache: SearchCache | None = None,
        metrics: MetricsCollector | None = None,
    ):
        self.session = session
        self.embedding_gen = embedding_generator or get_embedding_generator()
        self.cache = cache or get_search_cache()
        self.metrics = metrics or get_metrics_collector()
        self.vector_search = VectorSearchService(session)

    # =========================================================================
    # Main Retrieval Methods
    # =========================================================================

    async def retrieve(
        self,
        query: RetrievalQuery,
        top_k: int = 10,
        min_similarity: float = 0.5,
        use_cache: bool = True,
        exclude_model_id: UUID | None = None,
    ) -> tuple[list[RetrievalResult], dict[str, Any]]:
        """
        Execute multi-modal CAD retrieval.

        Args:
            query: RetrievalQuery with modalities and filters
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
            use_cache: Use cached results if available
            exclude_model_id: Exclude this model from results

        Returns:
            (results, metadata) tuple
        """
        with SearchTimer(self.metrics) as timer:
            # Check cache
            query_hash = self._compute_query_hash(query)
            cache_hit = False

            if use_cache:
                cached = self.cache.get(query_hash)
                if cached:
                    cache_hit = True
                    # Apply exclude and min_similarity filters
                    results = [
                        self._dict_to_result(r)
                        for r in cached
                        if (exclude_model_id is None or UUID(r["model_id"]) != exclude_model_id)
                    ]
                    results = ResultPostprocessor.apply_min_similarity(
                        [self._result_to_dict(r) for r in results],
                        min_similarity,
                    )
                    results = [self._dict_to_result(r) for r in results[:top_k]]

                    return results, self._build_metadata(
                        timer, cache_hit, len(results), query,
                    )

            # Encode query modalities
            await self._encode_query(query)

            # Detect query complexity for adaptive ef_search
            complexity = self._detect_query_complexity(query)
            ef_search = self.EF_SEARCH_MAP.get(complexity, 100)

            # Determine search strategy
            if query.has_reference:
                results = await self._retrieve_by_reference(
                    query, top_k * 3, min_similarity, exclude_model_id, ef_search,
                )
            elif query.modality_count == 1:
                # Single modality search
                if query.has_text:
                    results = await self._retrieve_by_text(
                        query, top_k * 3, min_similarity, exclude_model_id, ef_search,
                    )
                elif query.has_image:
                    results = await self._retrieve_by_image(
                        query, top_k * 3, min_similarity, exclude_model_id, ef_search,
                    )
                else:  # geometry
                    results = await self._retrieve_by_geometry(
                        query, top_k * 3, min_similarity, exclude_model_id, ef_search,
                    )
            else:
                # Multi-modal fused search
                results = await self._retrieve_fused(
                    query, top_k * 3, min_similarity, exclude_model_id, ef_search,
                )

            # Re-rank if multiple modalities
            if query.modality_count > 1 and query.modality_weights:
                results = self._rerank_results(results, query.modality_weights)

            # Apply filters
            results = await self._apply_filters(results, query.raw_filters)

            # Apply min similarity and paginate
            results = [r for r in results if r.similarity_score >= min_similarity]
            results = sorted(results, key=lambda x: x.similarity_score, reverse=True)
            results = results[:top_k]

            # Update ranks
            for i, r in enumerate(results):
                r.rank = i + 1

            # Cache results
            if not cache_hit and use_cache:
                self.cache.set(
                    query_hash,
                    [self._result_to_dict(r) for r in results],
                )

        # Record metrics
        self.metrics.record_search(
            search_type=self._get_search_type(query),
            execution_time_ms=timer.elapsed_ms,
            cache_hit=cache_hit,
            results_count=len(results),
            query_summary=self._summarize_query(query),
        )

        return results, self._build_metadata(
            timer, cache_hit, len(results), query, complexity=complexity, ef_search=ef_search,
        )

    async def _encode_query(self, query: RetrievalQuery) -> None:
        """Encode all query modalities to embeddings."""
        if query.has_text and query.text_embedding is None:
            normalized_text = QueryPreprocessor.normalize_text(query.text)
            query.text_embedding = self.embedding_gen.encode_text(normalized_text)

        if query.has_image and query.image_embedding is None:
            # Check if image_data is base64 or URL/path
            if query.image_data.startswith(("http://", "https://", "/")):
                query.image_embedding = self.embedding_gen.encode_image(query.image_data)
            else:
                # Assume base64 - save to temp file
                import tempfile
                import base64
                try:
                    # Decode base64
                    if "," in query.image_data:
                        # Data URL format
                        header, data = query.image_data.split(",", 1)
                        image_bytes = base64.b64decode(data)
                    else:
                        image_bytes = base64.b64decode(query.image_data)

                    # Write to temp file
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                        f.write(image_bytes)
                        temp_path = f.name

                    query.image_embedding = self.embedding_gen.encode_image(temp_path)

                    # Cleanup
                    import os
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to encode image: {e}")
                    query.image_embedding = None

        if query.has_geometry and query.geometry_embedding is None:
            if QueryPreprocessor.validate_point_cloud(query.point_cloud):
                query.geometry_embedding = self.embedding_gen.encode_geometry(
                    query.point_cloud,
                )

        # Fuse embeddings
        embeddings = {
            "text": query.text_embedding,
            "image": query.image_embedding,
            "geometry": query.geometry_embedding,
        }
        query.fused_embedding = self.embedding_gen.fuse_embeddings(
            **embeddings,
            weights=query.modality_weights or self.DEFAULT_WEIGHTS,
        )

    # =========================================================================
    # Single Modality Retrieval
    # =========================================================================

    async def _retrieve_by_text(
        self,
        query: RetrievalQuery,
        limit: int,
        min_similarity: float,
        exclude_id: UUID | None,
        ef_search: int,
    ) -> list[RetrievalResult]:
        """Retrieve using text embedding."""
        if not query.text_embedding:
            return []

        results = await self.vector_search.text_to_cad_search(
            text_embedding=query.text_embedding,
            limit=limit,
            min_similarity=min_similarity,
        )

        return self._vector_results_to_retrieval(
            results, query, exclude_id,
        )

    async def _retrieve_by_image(
        self,
        query: RetrievalQuery,
        limit: int,
        min_similarity: float,
        exclude_id: UUID | None,
        ef_search: int,
    ) -> list[RetrievalResult]:
        """Retrieve using image embedding (CLIP)."""
        if not query.image_embedding:
            return []

        # Use fused embedding (image modality)
        params = VectorSearchParams(
            query_vector=query.image_embedding,
            min_similarity=min_similarity,
            limit=limit,
        )

        results = await self.vector_search.multi_modal_search(params)

        return self._vector_results_to_retrieval(
            results, query, exclude_id,
        )

    async def _retrieve_by_geometry(
        self,
        query: RetrievalQuery,
        limit: int,
        min_similarity: float,
        exclude_id: UUID | None,
        ef_search: int,
    ) -> list[RetrievalResult]:
        """Retrieve using geometry embedding."""
        if not query.geometry_embedding:
            return []

        params = VectorSearchParams(
            query_vector=query.geometry_embedding,
            min_similarity=min_similarity,
            limit=limit,
        )

        results = await self.vector_search.multi_modal_search(params)

        return self._vector_results_to_retrieval(
            results, query, exclude_id,
        )

    async def _retrieve_by_reference(
        self,
        query: RetrievalQuery,
        limit: int,
        min_similarity: float,
        exclude_id: UUID | None,
        ef_search: int,
    ) -> list[RetrievalResult]:
        """Retrieve models similar to reference model."""
        if not query.reference_model_id:
            return []

        # Get reference model embeddings
        stmt = select(CADModel).options(
            selectinload(CADModel.embeddings),
        ).where(
            CADModel.id == query.reference_model_id,
        )

        result = await self.session.execute(stmt)
        ref_model = result.scalar_one_or_none()

        if not ref_model or not ref_model.embeddings:
            return []

        emb = ref_model.embeddings
        # Use fused embedding or fallback to other embeddings
        query_vector = (
            emb.fused_embedding or emb.clip_text_embedding or
            emb.clip_image_embedding or emb.geometry_embedding
        )

        if not query_vector:
            return []

        params = VectorSearchParams(
            query_vector=query_vector,
            min_similarity=min_similarity,
            limit=limit,
        )

        results = await self.vector_search.multi_modal_search(params)

        return self._vector_results_to_retrieval(
            results, query, exclude_id or query.reference_model_id,
        )

    async def _retrieve_fused(
        self,
        query: RetrievalQuery,
        limit: int,
        min_similarity: float,
        exclude_id: UUID | None,
        ef_search: int,
    ) -> list[RetrievalResult]:
        """Retrieve using fused multi-modal embedding."""
        if not query.fused_embedding:
            return []

        # Prepare filter parameters
        material_filter = None
        part_family_filter = None
        if query.filters:
            material_filter = query.filters.material
            part_family_filter = query.filters.category_label

        params = VectorSearchParams(
            query_vector=query.fused_embedding,
            min_similarity=min_similarity,
            material_filter=material_filter,
            part_family_filter=part_family_filter,
            limit=limit,
            ef_search=ef_search,
        )

        results = await self.vector_search.multi_modal_search(params)

        return self._vector_results_to_retrieval(
            results, query, exclude_id,
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _vector_results_to_retrieval(
        self,
        vector_results: list,
        query: RetrievalQuery,
        exclude_id: UUID | None = None,
    ) -> list[RetrievalResult]:
        """Convert VectorSearchResult to RetrievalResult."""
        results = []
        for v in vector_results:
            if exclude_id and v.model_id == exclude_id:
                continue

            # Compute per-modality similarities
            modality_scores = {}
            if query.text_embedding and v.metadata:
                # Placeholder for actual per-modality comparison
                modality_scores["text_similarity"] = None

            if query.image_embedding:
                modality_scores["image_similarity"] = None

            if query.geometry_embedding:
                modality_scores["geometry_similarity"] = None

            results.append(RetrievalResult(
                model_id=v.model_id,
                file_name=v.metadata.get("file_name", "unknown") if v.metadata else "unknown",
                file_type=v.metadata.get("file_type", "unknown") if v.metadata else "unknown",
                similarity_score=v.similarity,
                metadata=v.metadata or {},
                modality_scores=modality_scores if modality_scores else None,
            ))

        return results

    def _rerank_results(
        self,
        results: list[RetrievalResult],
        weights: dict[str, float],
    ) -> list[RetrievalResult]:
        """Re-rank results using weighted modality scores."""
        for result in results:
            if not result.modality_scores:
                continue

            combined_scores = []
            weight_values = []

            for modality, weight in weights.items():
                similarity_key = f"{modality}_similarity"
                if similarity_key in result.modality_scores:
                    score = result.modality_scores[similarity_key]
                    if score is not None:
                        combined_scores.append(score)
                        weight_values.append(weight)

            if combined_scores and weight_values:
                weighted_sum = sum(s * w for s, w in zip(combined_scores, weight_values))
                total_weight = sum(weight_values)
                result.similarity_score = weighted_sum / total_weight if total_weight > 0 else 0

        return sorted(results, key=lambda x: x.similarity_score, reverse=True)

    async def _apply_filters(
        self,
        results: list[RetrievalResult],
        filters: dict[str, Any] | None,
    ) -> list[RetrievalResult]:
        """Apply metadata filters to results."""
        if not filters:
            return results

        filtered = []
        for r in results:
            if self._matches_filters(r, filters):
                filtered.append(r)

        return filtered

    def _matches_filters(self, result: RetrievalResult, filters: dict[str, Any]) -> bool:
        """Check if result matches filters."""
        # Material filter
        if material := filters.get("material"):
            if result.metadata.get("material") != material:
                return False

        # Category filter
        if category := filters.get("category_label"):
            if result.metadata.get("category_label") != category:
                return False

        # Tags filter
        if tags := filters.get("tags"):
            result_tags = set(result.metadata.get("tags", []))
            if not set(tags).issubset(result_tags):
                return False

        # Mass filter
        if mass_min := filters.get("mass_min"):
            if (result.metadata.get("mass_kg") or 0) < mass_min:
                return False
        if mass_max := filters.get("mass_max"):
            if (result.metadata.get("mass_kg") or float("inf")) > mass_max:
                return False

        # Volume filter
        if vol_min := filters.get("volume_min"):
            if (result.metadata.get("volume_cm3") or 0) < vol_min:
                return False
        if vol_max := filters.get("volume_max"):
            if (result.metadata.get("volume_cm3") or float("inf")) > vol_max:
                return False

        # File type filter
        if file_type := filters.get("file_type"):
            if result.file_type.lower() != file_type.lower():
                return False

        return True

    def _compute_query_hash(self, query: RetrievalQuery) -> str:
        """Compute hash for query caching."""
        return QueryPreprocessor.compute_query_hash(
            text=query.text,
            vector=query.fused_embedding,
            filters=query.raw_filters,
        )

    def _detect_query_complexity(self, query: RetrievalQuery) -> QueryComplexity:
        """Detect query complexity for adaptive ef_search."""
        complexity_str = QueryPreprocessor.compute_query_complexity(
            text=query.text,
            vector=query.fused_embedding,
        )
        return QueryComplexity(complexity_str)

    def _get_search_type(self, query: RetrievalQuery) -> str:
        """Get search type string for metrics."""
        if query.has_reference:
            return SearchModality.SIMILAR_MODEL.value
        if query.modality_count > 1:
            return SearchModality.FUSED.value
        if query.has_text:
            return SearchModality.TEXT.value
        if query.has_image:
            return SearchModality.IMAGE.value
        return SearchModality.GEOMETRY.value

    def _summarize_query(self, query: RetrievalQuery) -> str:
        """Generate query summary for logging."""
        parts = []
        if query.has_text:
            parts.append(f"text:{query.text[:50]}")
        if query.has_image:
            parts.append("image")
        if query.has_geometry:
            pc_size = len(query.point_cloud) if query.point_cloud else 0
            parts.append(f"geometry:{pc_size}pts")
        if query.has_reference:
            parts.append(f"ref:{query.reference_model_id}")
        return "|".join(parts)

    def _build_metadata(
        self,
        timer: SearchTimer,
        cache_hit: bool,
        results_count: int,
        query: RetrievalQuery,
        complexity: QueryComplexity = QueryComplexity.MEDIUM,
        ef_search: int = 100,
    ) -> dict[str, Any]:
        """Build metadata response."""
        return {
            "query_complexity": complexity,
            "ef_search_used": ef_search,
            "candidates_retrieved": results_count,
            "candidates_filtered": 0,  # TODO: track actual filtered count
            "cache_hit": cache_hit,
            "execution_time_ms": timer.elapsed_ms,
            "modalities_used": [self._get_search_type(query)],
        }

    def _result_to_dict(self, result: RetrievalResult) -> dict[str, Any]:
        """Convert RetrievalResult to dict."""
        return {
            "model_id": str(result.model_id),
            "file_name": result.file_name,
            "file_type": result.file_type,
            "similarity_score": result.similarity_score,
            "rank": result.rank,
            "metadata": result.metadata,
            "modality_scores": result.modality_scores,
        }

    def _dict_to_result(self, data: dict[str, Any]) -> RetrievalResult:
        """Convert dict to RetrievalResult."""
        return RetrievalResult(
            model_id=UUID(data["model_id"]),
            file_name=data["file_name"],
            file_type=data["file_type"],
            similarity_score=data["similarity_score"],
            rank=data.get("rank", 0),
            metadata=data.get("metadata", {}),
            modality_scores=data.get("modality_scores"),
        )


# =============================================================================
# Convenience Functions
# =============================================================================


async def find_similar_models(
    session: AsyncSession,
    model_id: UUID | str,
    top_k: int = 10,
    min_similarity: float = 0.5,
    exclude_self: bool = True,
) -> list[RetrievalResult]:
    """
    Find models similar to a given model.

    Convenience function for common use case.
    """
    retriever = CosCADRetriever(session)

    query = RetrievalQuery(reference_model_id=model_id)
    exclude_id = UUID(str(model_id)) if exclude_self else None

    results, _ = await retriever.retrieve(
        query=query,
        top_k=top_k,
        min_similarity=min_similarity,
        exclude_model_id=exclude_id,
    )

    return results


async def text_search(
    session: AsyncSession,
    text_query: str,
    top_k: int = 10,
    min_similarity: float = 0.5,
    filters: dict[str, Any] | None = None,
) -> list[RetrievalResult]:
    """
    Search CAD models by text description.

    Convenience function for text-to-CAD search.
    """
    retriever = CosCADRetriever(session)

    query = RetrievalQuery(text=text_query, filters=filters)

    results, _ = await retriever.retrieve(
        query=query,
        top_k=top_k,
        min_similarity=min_similarity,
    )

    return results
