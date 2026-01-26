"""
Helper utilities for CAD retrieval operations.

Provides query preprocessing, result postprocessing, caching, and metrics.
"""

import hashlib
import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import numpy as np

from pybase.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Query Preprocessor
# =============================================================================


class QueryPreprocessor:
    """
    Preprocess search queries for optimal retrieval.

    Normalizes queries, detects complexity, and prepares parameters.
    """

    # Complexity thresholds
    LOW_COMPLEXITY_THRESHOLD = 0.7  # Specific queries
    HIGH_COMPLEXITY_THRESHOLD = 0.3  # Vague queries

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text query for embedding."""
        if not text:
            return ""
        # Basic normalization
        text = text.strip().lower()
        # Remove extra whitespace
        import re
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def compute_query_complexity(
        text: str | None = None,
        vector: list[float] | np.ndarray | None = None,
    ) -> str:
        """
        Detect query complexity for adaptive ef_search.

        Returns: 'low', 'medium', or 'high'
        """
        complexity = "medium"

        if text:
            # Text-based complexity
            word_count = len(text.split())
            unique_ratio = len(set(text.lower().split())) / max(word_count, 1)

            # Short, specific queries = low complexity
            if word_count <= 5 and unique_ratio > 0.8:
                complexity = "low"
            # Long, vague queries = high complexity
            elif word_count > 15 or unique_ratio < 0.5:
                complexity = "high"

        elif vector is not None:
            # Vector-based complexity using norm and entropy
            if isinstance(vector, list):
                vector = np.array(vector)

            norm = np.linalg.norm(vector)
            entropy = -sum(p * np.log(p + 1e-10)
                          for p in np.abs(vector) / (np.sum(np.abs(vector)) + 1e-10))

            if norm > QueryPreprocessor.LOW_COMPLEXITY_THRESHOLD:
                complexity = "low"
            elif norm < QueryPreprocessor.HIGH_COMPLEXITY_THRESHOLD or entropy > 0.8:
                complexity = "high"

        return complexity

    @staticmethod
    def compute_query_hash(
        text: str | None = None,
        vector: list[float] | np.ndarray | None = None,
        filters: dict[str, Any] | None = None,
    ) -> str:
        """Compute hash for query caching."""
        components = []

        if text:
            components.append(f"text:{text}")

        if vector is not None:
            if isinstance(vector, np.ndarray):
                vector = vector.flatten().tolist()
            # Use first 10 and last 10 values for hash (trade precision for speed)
            if len(vector) > 20:
                vec_str = str(vector[:10] + vector[-10:])
            else:
                vec_str = str(vector)
            components.append(f"vec:{vec_str}")

        if filters:
            components.append(f"filters:{json.dumps(sorted(filters.items()), sort_keys=True)}")

        combined = "|".join(components)
        return hashlib.sha256(combined.encode()).hexdigest()

    @staticmethod
    def prepare_bbox_filter(bbox: dict[str, Any] | None) -> dict[str, float] | None:
        """Validate and normalize bounding box filter."""
        if not bbox:
            return None

        # Support both flat dict and nested min/max formats
        if "min" in bbox and "max" in bbox:
            min_pt = bbox["min"]
            max_pt = bbox["max"]
            return {
                "min_x": float(min_pt[0]),
                "min_y": float(min_pt[1]),
                "min_z": float(min_pt[2]),
                "max_x": float(max_pt[0]),
                "max_y": float(max_pt[1]),
                "max_z": float(max_pt[2]),
            }
        else:
            # Flat format
            return {
                "min_x": float(bbox.get("min_x", bbox.get("min_x", 0))),
                "min_y": float(bbox.get("min_y", bbox.get("min_y", 0))),
                "min_z": float(bbox.get("min_z", bbox.get("min_z", 0))),
                "max_x": float(bbox.get("max_x", bbox.get("max_x", 1000))),
                "max_y": float(bbox.get("max_y", bbox.get("max_y", 1000))),
                "max_z": float(bbox.get("max_z", bbox.get("max_z", 1000))),
            }

    @staticmethod
    def validate_point_cloud(point_cloud: list[list[float]]) -> bool:
        """Validate point cloud format."""
        if not point_cloud or not isinstance(point_cloud, list):
            return False
        for point in point_cloud:
            if not isinstance(point, list) or len(point) != 3:
                return False
            if not all(isinstance(c, (int, float)) for c in point):
                return False
        return True


# =============================================================================
# Result Postprocessor
# =============================================================================


class ResultPostprocessor:
    """
    Postprocess search results for API responses.

    Formats results, adds metadata, and handles pagination.
    """

    @staticmethod
    def format_result(
        model_id: str,
        file_name: str,
        file_type: str,
        similarity: float,
        rank: int,
        metadata: dict[str, Any] | None = None,
        modality_scores: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Format a single search result."""
        result = {
            "model_id": model_id,
            "file_name": file_name,
            "file_type": file_type,
            "similarity_score": float(similarity),
            "rank": rank,
            "category_label": metadata.get("category_label") if metadata else None,
            "tags": metadata.get("tags", []) if metadata else [],
            "material": metadata.get("material") if metadata else None,
            "mass_kg": metadata.get("mass_kg") if metadata else None,
            "volume_cm3": metadata.get("volume_cm3") if metadata else None,
            "bounding_box": metadata.get("bounding_box") if metadata else None,
            "has_rendered_views": metadata.get("has_rendered_views", False) if metadata else False,
            "preview_url": metadata.get("preview_url") if metadata else None,
        }

        if modality_scores:
            result["scores"] = {
                "text_similarity": modality_scores.get("text_similarity"),
                "image_similarity": modality_scores.get("image_similarity"),
                "geometry_similarity": modality_scores.get("geometry_similarity"),
                "fused_similarity": modality_scores.get("fused_similarity"),
                "shape_similarity": modality_scores.get("shape_similarity"),
                "topology_similarity": modality_scores.get("topology_similarity"),
            }

        return result

    @staticmethod
    def deduplicate_results(
        results: list[dict[str, Any]],
        key: str = "model_id",
    ) -> list[dict[str, Any]]:
        """Remove duplicate results by key, keeping highest similarity."""
        seen: dict[str, dict[str, Any]] = {}

        for result in results:
            result_key = result.get(key)
            if not result_key:
                continue

            if result_key not in seen:
                seen[result_key] = result
            else:
                # Keep higher similarity
                if result.get("similarity_score", 0) > seen[result_key].get("similarity_score", 0):
                    seen[result_key] = result

        # Sort by similarity and return
        return sorted(seen.values(), key=lambda x: x.get("similarity_score", 0), reverse=True)

    @staticmethod
    def apply_min_similarity(
        results: list[dict[str, Any]],
        min_similarity: float,
    ) -> list[dict[str, Any]]:
        """Filter results by minimum similarity."""
        return [r for r in results if r.get("similarity_score", 0) >= min_similarity]

    @staticmethod
    def re_rank_by_modality(
        results: list[dict[str, Any]],
        weights: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Re-rank results using weighted modality scores.

        Weights: {"text": 1.0, "image": 1.2, "geometry": 1.5}
        """
        if not weights:
            weights = {"text": 1.0, "image": 1.2, "geometry": 1.5}

        for result in results:
            scores = result.get("scores", {})
            combined_scores = []
            weight_values = []

            for modality, weight in weights.items():
                similarity_key = f"{modality}_similarity"
                if similarity_key in scores and scores[similarity_key] is not None:
                    combined_scores.append(scores[similarity_key])
                    weight_values.append(weight)

            if combined_scores and weight_values:
                # Weighted average
                weighted_sum = sum(s * w for s, w in zip(combined_scores, weight_values))
                total_weight = sum(weight_values)
                result["similarity_score"] = weighted_sum / total_weight if total_weight > 0 else 0

        # Re-sort by new scores
        return sorted(results, key=lambda x: x.get("similarity_score", 0), reverse=True)


# =============================================================================
# Search Cache (In-Memory)
# =============================================================================


class SearchCache:
    """
    In-memory cache for search results.

    Caches frequent queries to improve response time.
    Replace with Redis in production for distributed caching.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self._cache: dict[str, dict[str, Any]] = {}
        self._access_count: dict[str, int] = defaultdict(int)
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds

    def get(self, query_hash: str) -> list[dict[str, Any]] | None:
        """Get cached results if fresh."""
        if query_hash not in self._cache:
            return None

        entry = self._cache[query_hash]
        created_at = entry.get("created_at")

        # Check TTL
        if created_at:
            age = (datetime.now(timezone.utc) - created_at).total_seconds()
            if age > self._ttl_seconds:
                # Expired
                del self._cache[query_hash]
                return None

        self._access_count[query_hash] += 1
        return entry.get("results")

    def set(self, query_hash: str, results: list[dict[str, Any]]) -> None:
        """Cache results."""
        # Evict if at capacity
        if len(self._cache) >= self._max_size:
            # Remove least recently used
            lru_key = min(self._access_count, key=self._access_count.get)
            del self._cache[lru_key]
            del self._access_count[lru_key]

        self._cache[query_hash] = {
            "results": results,
            "created_at": datetime.now(timezone.utc),
        }
        self._access_count[query_hash] = 0

    def invalidate(self, query_hash: str | None = None) -> None:
        """Invalidate cache entry or all cache."""
        if query_hash:
            self._cache.pop(query_hash, None)
            self._access_count.pop(query_hash, None)
        else:
            self._cache.clear()
            self._access_count.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl_seconds,
            "total_accesses": sum(self._access_count.values()),
        }


# Global cache instance
_default_cache: SearchCache | None = None


def get_search_cache() -> SearchCache:
    """Get global search cache instance."""
    global _default_cache
    if _default_cache is None:
        _default_cache = SearchCache()
    return _default_cache


# =============================================================================
# Metrics Collector
# =============================================================================


class MetricsCollector:
    """
    Collect metrics for search operations.

    Tracks performance, cache hits, and usage patterns.
    """

    def __init__(self):
        self._search_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._execution_times: list[float] = []
        self._searches_by_type: dict[str, int] = defaultdict(int)
        self._queries: list[dict[str, Any]] = []
        self._max_queries = 1000

    def record_search(
        self,
        search_type: str,
        execution_time_ms: float,
        cache_hit: bool,
        results_count: int,
        query_summary: str = "",
    ) -> None:
        """Record a search operation."""
        self._search_count += 1
        self._searches_by_type[search_type] += 1
        self._execution_times.append(execution_time_ms)

        if cache_hit:
            self._cache_hits += 1
        else:
            self._cache_misses += 1

        # Store query for analytics (with limit)
        if len(self._queries) >= self._max_queries:
            self._queries.pop(0)

        self._queries.append({
            "type": search_type,
            "execution_time_ms": execution_time_ms,
            "results_count": results_count,
            "cache_hit": cache_hit,
            "summary": query_summary[:200],  # Limit length
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_stats(self) -> dict[str, Any]:
        """Get collected metrics."""
        total_cache_accesses = self._cache_hits + self._cache_misses
        cache_hit_rate = (
            self._cache_hits / total_cache_accesses
            if total_cache_accesses > 0
            else 0
        )

        avg_execution_time = (
            sum(self._execution_times) / len(self._execution_times)
            if self._execution_times
            else 0
        )

        # Top queries by frequency
        query_counts = defaultdict(int)
        for q in self._queries:
            query_counts[q["summary"]] += 1
        top_queries = [
            {"query": k, "count": v}
            for k, v in sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        return {
            "total_searches": self._search_count,
            "searches_by_type": dict(self._searches_by_type),
            "avg_execution_time_ms": round(avg_execution_time, 2),
            "cache_hit_rate": round(cache_hit_rate, 3),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "top_queries": top_queries,
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self._search_count = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._execution_times.clear()
        self._searches_by_type.clear()
        self._queries.clear()


# Global metrics instance
_default_metrics: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _default_metrics
    if _default_metrics is None:
        _default_metrics = MetricsCollector()
    return _default_metrics


# =============================================================================
# Context Manager for Search Timing
# =============================================================================


class SearchTimer:
    """Context manager for timing search operations."""

    def __init__(self, metrics_collector: MetricsCollector | None = None):
        self.metrics = metrics_collector or get_metrics_collector()
        self.start_time: float | None = None
        self.end_time: float | None = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.perf_counter()
        return (end - self.start_time) * 1000
