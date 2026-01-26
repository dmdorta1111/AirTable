"""
Vector similarity search utilities for PyBase CAD models.

Provides optimized pgvector queries with adaptive parameters,
multi-modal search, and caching.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import text
from sqlalchemy.exc import DataError
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.logging import get_logger

logger = get_logger(__name__)


class VectorValidationError(Exception):
    """Raised when vector validation fails."""
    pass


@dataclass
class VectorSearchResult:
    """Result from vector similarity search."""
    model_id: UUID
    similarity: float
    part_family: str | None = None
    material: str | None = None
    mass_kg: float | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class VectorSearchParams:
    """Parameters for vector similarity search."""
    query_vector: list[float] | np.ndarray
    min_similarity: float = 0.7
    material_filter: str | None = None
    part_family_filter: str | None = None
    limit: int = 20
    ef_search: int | None = None  # None = use default (100)


class VectorSearchService:
    """
    Service for executing optimized vector similarity searches.

    Uses pgvector HNSW indexes with adaptive ef_search parameters
    for optimal performance/recall tradeoff.
    """

    # Default index parameters from CosCAD optimization
    DEFAULT_EF_SEARCH = 100
    HIGH_RECALL_EF_SEARCH = 200
    FAST_EF_SEARCH = 50

    # Expected embedding dimensions
    DEEPSDF_DIM = 256
    CLIP_DIM = 512
    GEOMETRY_DIM = 1024

    def __init__(self, session: AsyncSession):
        self.session = session

    async def multi_modal_search(
        self,
        params: VectorSearchParams,
    ) -> list[VectorSearchResult]:
        """
        Execute multi-modal similarity search using SDF latents.

        Combines shape similarity with B-Rep topology verification.

        Raises:
            VectorValidationError: If query vector is invalid or empty
        """
        # Validate and normalize query vector
        query_vector = self._validate_and_normalize_vector(
            params.query_vector,
            expected_dim=self.DEEPSDF_DIM,
            allow_empty=False,
        )

        # Set adaptive ef_search if specified
        if params.ef_search:
            await self._set_ef_search(params.ef_search)

        sql = text("""
            WITH similarity_search AS (
                SELECT
                    model_id,
                    1 - (sdf_latent <=> :query_vector) as shape_similarity,
                    ROW_NUMBER() OVER (ORDER BY sdf_latent <=> :query_vector) as shape_rank
                FROM cad_models
                WHERE sdf_latent IS NOT NULL
                  AND (:material_filter IS NULL OR material = :material_filter)
                  AND (:part_family IS NULL OR part_family = :part_family)
                ORDER BY sdf_latent <=> :query_vector
                LIMIT 1000
            ),
            filtered AS (
                SELECT *
                FROM similarity_search
                WHERE shape_similarity > :min_similarity
            ),
            reranked AS (
                SELECT
                    f.*,
                    cm.part_family,
                    cm.material,
                    cm.mass_kg,
                    0.7 * shape_similarity +
                    0.3 * COALESCE(1 - (cm.brep_graph_embedding <=> :query_vector), 0.5) as composite_score
                FROM filtered f
                JOIN cad_models cm USING (model_id)
            )
            SELECT
                model_id,
                part_family,
                material,
                mass_kg,
                shape_similarity,
                composite_score,
                shape_rank
            FROM reranked
            ORDER BY composite_score DESC
            LIMIT :limit
        """)

        try:
            result = await self.session.execute(sql, {
                "query_vector": query_vector,
                "min_similarity": params.min_similarity,
                "material_filter": params.material_filter,
                "part_family": params.part_family_filter,
                "limit": params.limit,
            })
        except DataError as e:
            raise VectorValidationError(f"Invalid query vector: {e}")

        rows = result.fetchall()
        return [
            VectorSearchResult(
                model_id=row.model_id,
                similarity=row.composite_score,
                part_family=row.part_family,
                material=row.material,
                mass_kg=row.mass_kg,
                metadata={"shape_similarity": row.shape_similarity, "rank": row.shape_rank},
            )
            for row in rows
        ]

    async def text_to_cad_search(
        self,
        text_embedding: list[float] | np.ndarray,
        limit: int = 20,
        min_similarity: float = 0.6,
    ) -> list[VectorSearchResult]:
        """
        Search CAD models using CLIP text embeddings.

        Cross-modal search: text description -> similar CAD parts.

        Raises:
            VectorValidationError: If text embedding is invalid or empty
        """
        query_vector = self._validate_and_normalize_vector(
            text_embedding,
            expected_dim=self.CLIP_DIM,
            allow_empty=False,
        )

        sql = text("""
            WITH text_search AS (
                SELECT
                    model_id,
                    1 - (clip_text_embedding <=> :query_vector) as text_similarity
                FROM cad_models
                WHERE clip_text_embedding IS NOT NULL
                ORDER BY clip_text_embedding <=> :query_vector
                LIMIT 500
            ),
            shape_verify AS (
                SELECT
                    t.model_id,
                    t.text_similarity,
                    1 - (cm.sdf_latent <=> cm.clip_text_embedding) as shape_similarity,
                    cm.part_family,
                    cm.material
                FROM text_search t
                JOIN cad_models cm ON t.model_id = cm.model_id
            )
            SELECT
                model_id,
                text_similarity,
                shape_similarity,
                0.6 * text_similarity + 0.4 * shape_similarity as combined_score,
                part_family,
                material
            FROM shape_verify
            WHERE text_similarity > :min_similarity
            ORDER BY combined_score DESC
            LIMIT :limit
        """)

        try:
            result = await self.session.execute(sql, {
                "query_vector": query_vector,
                "min_similarity": min_similarity,
                "limit": limit,
            })
        except DataError as e:
            raise VectorValidationError(f"Invalid text embedding: {e}")

        rows = result.fetchall()
        return [
            VectorSearchResult(
                model_id=row.model_id,
                similarity=row.combined_score,
                part_family=row.part_family,
                material=row.material,
                metadata={"text_similarity": row.text_similarity, "shape_similarity": row.shape_similarity},
            )
            for row in rows
        ]

    async def assembly_aware_search(
        self,
        component_vector: list[float] | np.ndarray,
        topology_vector: list[float] | np.ndarray | None = None,
        min_components: int = 2,
        max_components: int = 20,
        limit: int = 20,
    ) -> list[VectorSearchResult]:
        """
        Find similar assemblies considering component relationships.

        Aggregates component similarities and matches topology.

        Raises:
            VectorValidationError: If vectors are invalid or empty
        """
        comp_vector = self._validate_and_normalize_vector(
            component_vector,
            expected_dim=self.DEEPSDF_DIM,
            allow_empty=False,
        )
        topo_vector = self._validate_and_normalize_vector(
            topology_vector or component_vector,
            expected_dim=self.CLIP_DIM,
            allow_empty=False,
        )

        sql = text("""
            WITH component_similarity AS (
                SELECT
                    a.assembly_id as model_id,
                    1 - (c.sdf_latent <=> :comp_vector) as component_sim
                FROM assembly_hierarchy a
                JOIN cad_models c ON a.component_id = c.model_id
                WHERE c.sdf_latent IS NOT NULL
            ),
            assembly_aggregate AS (
                SELECT
                    model_id,
                    AVG(component_sim) as avg_component_similarity,
                    COUNT(*) as component_count,
                    SUM(CASE WHEN component_sim > 0.8 THEN 1 ELSE 0 END) as high_sim_count
                FROM component_similarity
                GROUP BY model_id
                HAVING COUNT(*) BETWEEN :min_components AND :max_components
            ),
            topology_match AS (
                SELECT
                    a.*,
                    COALESCE(
                        1 - (cm.brep_graph_embedding <=> :topo_vector), 0.5
                    ) as topology_similarity
                FROM assembly_aggregate a
                JOIN cad_models cm ON a.model_id = cm.model_id
            )
            SELECT
                model_id,
                avg_component_similarity,
                topology_similarity,
                high_sim_count,
                component_count,
                0.4 * avg_component_similarity +
                0.4 * topology_similarity +
                0.2 * (high_sim_count::float / component_count) as assembly_score
            FROM topology_match
            ORDER BY assembly_score DESC
            LIMIT :limit
        """)

        try:
            result = await self.session.execute(sql, {
                "comp_vector": comp_vector,
                "topo_vector": topo_vector,
                "min_components": min_components,
                "max_components": max_components,
                "limit": limit,
            })
        except DataError as e:
            raise VectorValidationError(f"Invalid assembly vectors: {e}")

        rows = result.fetchall()
        return [
            VectorSearchResult(
                model_id=row.model_id,
                similarity=row.assembly_score,
                metadata={
                    "component_similarity": row.avg_component_similarity,
                    "topology_similarity": row.topology_similarity,
                    "component_count": row.component_count,
                },
            )
            for row in rows
        ]

    async def hierarchical_search(
        self,
        query_vector: list[float] | np.ndarray,
        material: str | None = None,
        mass_min: float = 0.0,
        mass_max: float = 100.0,
        bbox_min: tuple[float, float, float] = (0, 0, 0),
        bbox_max: tuple[float, float, float] = (1000, 1000, 1000),
        limit: int = 20,
    ) -> list[VectorSearchResult]:
        """
        Multi-stage hierarchical search with spatial and metadata filtering.

        Stage 1: Approximate vector search
        Stage 2: Re-rank with metadata boosts
        Stage 3: Cross-modal verification

        Raises:
            VectorValidationError: If query vector is invalid or empty
        """
        qvec = self._validate_and_normalize_vector(
            query_vector,
            expected_dim=self.DEEPSDF_DIM,
            allow_empty=False,
        )

        sql = text("""
            WITH stage1 AS (
                SELECT model_id, 1 - (sdf_latent <=> :query_vector) as similarity
                FROM manufacturing_parts_prefilter
                ORDER BY sdf_latent <=> :query_vector
                LIMIT 1000
            ),
            stage2 AS (
                SELECT
                    m.model_id,
                    s.similarity *
                    CASE WHEN m.material = :material OR :material IS NULL THEN 1.2 ELSE 1.0 END *
                    CASE WHEN m.mass_kg BETWEEN :mass_min AND :mass_max THEN 1.1 ELSE 1.0 END as boosted_score,
                    m.part_family,
                    m.material,
                    m.mass_kg
                FROM cad_models m
                JOIN stage1 s ON m.model_id = s.model_id
            ),
            stage3 AS (
                SELECT
                    model_id,
                    part_family,
                    material,
                    mass_kg,
                    0.7 * boosted_score +
                    0.3 * COALESCE(1 - (brep_graph_embedding <=> :query_vector), 0.5) as final_score
                FROM stage2
            )
            SELECT model_id, part_family, material, mass_kg, final_score as similarity
            FROM stage3
            ORDER BY final_score DESC
            LIMIT :limit
        """)

        try:
            result = await self.session.execute(sql, {
                "query_vector": qvec,
                "material": material,
                "mass_min": mass_min,
                "mass_max": mass_max,
                "limit": limit,
            })
        except DataError as e:
            raise VectorValidationError(f"Invalid query vector: {e}")

        rows = result.fetchall()
        return [
            VectorSearchResult(
                model_id=row.model_id,
                similarity=row.similarity,
                part_family=row.part_family,
                material=row.material,
                mass_kg=row.mass_kg,
            )
            for row in rows
        ]

    async def check_cache(
        self,
        query_vector: list[float] | np.ndarray,
        limit: int = 20,
    ) -> list[VectorSearchResult] | None:
        """
        Check vector search cache for cached results.

        Returns cached results if found and fresh, None otherwise.

        Raises:
            VectorValidationError: If query vector is invalid
        """
        import hashlib

        # Validate vector before creating hash
        normalized_vector = self._validate_and_normalize_vector(
            query_vector,
            expected_dim=None,  # Any dimension acceptable for cache
            allow_empty=False,
        )

        query_hash = hashlib.sha256(str(normalized_vector).encode()).digest()

        sql = text("""
            SELECT
                result_ids,
                result_distances,
                accessed_at,
                access_count
            FROM vector_search_cache
            WHERE query_hash = :query_hash
            LIMIT 1
        """)

        result = await self.session.execute(sql, {"query_hash": query_hash})
        row = result.first()

        if not row:
            return None

        # Update access tracking
        await self.session.execute(text("""
            UPDATE vector_search_cache
            SET accessed_at = NOW(),
                access_count = access_count + 1
            WHERE query_hash = :query_hash
        """), {"query_hash": query_hash})

        # Parse cached results
        model_ids = row.result_ids or []
        distances = row.result_distances or []

        return [
            VectorSearchResult(
                model_id=model_id,
                similarity=1.0 - (distances[i] if i < len(distances) else 0.0),
            )
            for i, model_id in enumerate(model_ids[:limit])
        ]

    async def cache_results(
        self,
        query_vector: list[float] | np.ndarray,
        results: list[VectorSearchResult],
    ) -> None:
        """Cache search results for future queries.

        Raises:
            VectorValidationError: If query vector is invalid
        """
        import hashlib

        normalized_vector = self._validate_and_normalize_vector(
            query_vector,
            expected_dim=None,
            allow_empty=False,
        )

        query_hash = hashlib.sha256(str(normalized_vector).encode()).digest()

        model_ids = [r.model_id for r in results]
        distances = [1.0 - r.similarity for r in results]

        sql = text("""
            INSERT INTO vector_search_cache
            (query_hash, query_vector, result_ids, result_distances, created_at, accessed_at, access_count)
            VALUES (:query_hash, :query_vector, :result_ids, :result_distances, NOW(), NOW(), 1)
            ON CONFLICT (query_hash) DO UPDATE
            SET accessed_at = NOW(),
                access_count = vector_search_cache.access_count + 1
        """)

        await self.session.execute(sql, {
            "query_hash": query_hash,
            "query_vector": list(normalized_vector),
            "result_ids": model_ids,
            "result_distances": distances,
        })

    async def _set_ef_search(self, ef_search: int) -> None:
        """Set HNSW ef_search parameter for current session."""
        await self.session.execute(
            text(f"SET LOCAL hnsw.ef_search = {ef_search}")
        )

    @staticmethod
    def _validate_and_normalize_vector(
        vector: list[float] | np.ndarray,
        expected_dim: int | None,
        allow_empty: bool = False,
    ) -> list[float]:
        """
        Validate and normalize vector for pgvector queries.

        Args:
            vector: Input vector to validate
            expected_dim: Expected dimension (None = any dimension ok)
            allow_empty: Whether empty vectors are allowed

        Returns:
            Normalized vector as list of floats

        Raises:
            VectorValidationError: If validation fails
        """
        # Convert to list
        if isinstance(vector, np.ndarray):
            vector = vector.flatten().tolist()
        elif not isinstance(vector, list):
            vector = list(vector)

        # Check for empty vector
        if not vector and not allow_empty:
            raise VectorValidationError("Query vector cannot be empty")

        if not vector:
            return []

        # Validate contains only numbers
        try:
            vector = [float(v) for v in vector]
        except (ValueError, TypeError) as e:
            raise VectorValidationError(f"Vector contains non-numeric values: {e}")

        # Check for NaN or Inf
        if any(not np.isfinite(v) for v in vector):
            raise VectorValidationError("Vector contains NaN or Inf values")

        # Validate dimension if expected
        if expected_dim is not None and len(vector) != expected_dim:
            raise VectorValidationError(
                f"Vector dimension mismatch: expected {expected_dim}, got {len(vector)}. "
                "This indicates an embedding generation issue."
            )

        return vector

    @staticmethod
    def calculate_adaptive_ef_search(
        query_vector: list[float] | np.ndarray,
        initial_results: int = 50,
    ) -> tuple[int, int]:
        """
        Calculate adaptive ef_search based on query characteristics.

        Returns (ef_search, k) tuple for optimal performance.
        """
        if isinstance(query_vector, np.ndarray):
            query_vector = query_vector.flatten()

        query_norm = np.linalg.norm(query_vector)
        query_entropy = -sum(p * np.log(p + 1e-10)
                            for p in np.abs(query_vector) / (np.sum(np.abs(query_vector)) + 1e-10))

        # Vague query (low norm or high entropy) -> need more exploration
        if query_norm < 0.3 or query_entropy > 0.8:
            return 200, 100
        # Specific query -> can be precise
        else:
            return 50, 20
