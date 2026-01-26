"""
Sketch Similarity Service for processing existing serialized sketch data.

Processes sketches JSONB from serialized_models table to enable:
- "Find similar sketches" functionality
- Sketch pattern indexing and retrieval

Integrates with existing CosCAD retrieval system without modifying
master_serialize_and_index.py extraction.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np

from pybase.core.logging import get_logger

logger = get_logger(__name__)

# Target embedding dimension
SKETCH_EMBEDDING_DIM = 256


@dataclass
class SketchFeatures:
    """Extracted features from a single sketch."""
    entity_counts: dict[str, int]  # line, arc, circle, spline counts
    bounding_box: dict[str, float]  # {min_x, max_x, min_y, max_y}
    total_length: float
    centroid: tuple[float, float]
    aspect_ratio: float
    complexity_score: float


@dataclass
class SketchSimilarityResult:
    """Result of sketch similarity search."""
    sketch_id: str
    feature_id: int
    similarity: float
    metadata: dict[str, Any]


class SketchSimilarityService:
    """
    Process sketches from serialized_models.sketches for similarity search.

    Reads from serialized_models.sketches JSONB:
    - entities: List of sketch entities (lines, arcs, circles, etc.)
    - constraints: Geometric constraints
    - dimensions: Dimension values

    Generates searchable embeddings for "find similar sketches".
    """

    def __init__(self, embedding_dim: int = SKETCH_EMBEDDING_DIM):
        self.embedding_dim = embedding_dim

    def extract_sketch_features(
        self,
        sketches: list[dict[str, Any]] | None,
    ) -> dict[int, SketchFeatures]:
        """
        Extract features from all sketches in a model.

        Args:
            sketches: JSONB data from serialized_models.sketches

        Returns:
            Dict mapping feature_id to SketchFeatures
        """
        if not sketches:
            return {}

        features_by_feature = {}

        for sketch in sketches:
            feature_id = sketch.get("feature_id")
            if feature_id is None:
                continue

            try:
                feats = self._extract_single_sketch_features(sketch)
                features_by_feature[feature_id] = feats
            except Exception as e:
                logger.warning(f"Failed to extract features for sketch {feature_id}: {e}")

        return features_by_feature

    def encode_sketch(self, sketch: dict[str, Any]) -> list[float] | None:
        """
        Encode a single sketch to embedding vector.

        Args:
            sketch: Single sketch dict from serialized_models.sketches

        Returns:
            256-dimensional embedding vector
        """
        try:
            feats = self._extract_single_sketch_features(sketch)
            return self._features_to_embedding(feats)
        except Exception as e:
            logger.warning(f"Sketch encoding failed: {e}")
            return None

    def encode_all_sketches(
        self,
        sketches: list[dict[str, Any]] | None,
    ) -> dict[int, list[float]]:
        """
        Encode all sketches in a model.

        Returns:
            Dict mapping feature_id to embedding
        """
        if not sketches:
            return {}

        embeddings = {}

        for sketch in sketches:
            feature_id = sketch.get("feature_id")
            if feature_id is None:
                continue

            emb = self.encode_sketch(sketch)
            if emb:
                embeddings[feature_id] = emb

        return embeddings

    def compute_sketch_similarity(
        self,
        sketch_embedding: list[float],
        sketch_db: dict[int, list[float]],
        top_k: int = 10,
    ) -> list[SketchSimilarityResult]:
        """
        Find similar sketches by embedding similarity.

        Args:
            sketch_embedding: Query sketch embedding
            sketch_db: Database of sketch embeddings {feature_id: embedding}
            top_k: Number of results to return

        Returns:
            List of SketchSimilarityResult sorted by similarity
        """
        if not sketch_db:
            return []

        query_vec = np.array(sketch_embedding)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0:
            return []

        similarities = []

        for feat_id, emb in sketch_db.items():
            emb_vec = np.array(emb)
            emb_norm = np.linalg.norm(emb_vec)

            if emb_norm == 0:
                continue

            # Cosine similarity
            sim = np.dot(query_vec, emb_vec) / (query_norm * emb_norm)

            similarities.append(SketchSimilarityResult(
                sketch_id=str(feat_id),
                feature_id=feat_id,
                similarity=float(sim),
                metadata={"embedding_dim": len(emb)},
            ))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x.similarity, reverse=True)

        return similarities[:top_k]

    def _extract_single_sketch_features(self, sketch: dict[str, Any]) -> SketchFeatures:
        """Extract features from a single sketch."""
        entities = sketch.get("entities", [])
        constraints = sketch.get("constraints", [])

        # Count entity types
        entity_counts = defaultdict(int)
        total_length = 0.0
        all_points = []

        for entity in entities:
            etype = entity.get("type", "unknown")
            entity_counts[etype] += 1

            # Accumulate length and points
            if etype == "line":
                start = entity.get("start", [])
                end = entity.get("end", [])
                if len(start) >= 2 and len(end) >= 2:
                    dx, dy = end[0] - start[0], end[1] - start[1]
                    total_length += np.sqrt(dx**2 + dy**2)
                    all_points.extend([start[:2], end[:2]])

            elif etype in ("arc", "circle"):
                radius = entity.get("radius", 0)
                if radius > 0:
                    # Approximate arc length (2*pi*r for full circle)
                    angle = entity.get("angle", 2 * np.pi)
                    total_length += abs(angle) * radius

                center = entity.get("center", [])
                if len(center) >= 2:
                    all_points.append(center[:2])

            elif etype == "spline":
                points = entity.get("points", [])
                all_points.extend([p[:2] for p in points if len(p) >= 2])
                # Approximate spline length
                for i in range(len(points) - 1):
                    if len(points[i]) >= 2 and len(points[i+1]) >= 2:
                        dx = points[i+1][0] - points[i][0]
                        dy = points[i+1][1] - points[i][1]
                        total_length += np.sqrt(dx**2 + dy**2)

        # Compute bounding box
        if all_points:
            points_arr = np.array(all_points)
            min_x, min_y = points_arr.min(axis=0)
            max_x, max_y = points_arr.max(axis=0)
            centroid = (float((min_x + max_x) / 2), float((min_y + max_y) / 2))
        else:
            min_x = min_y = max_x = max_y = 0.0
            centroid = (0.0, 0.0)

        bbox = {
            "min_x": float(min_x),
            "max_x": float(max_x),
            "min_y": float(min_y),
            "max_y": float(max_y),
        }

        # Aspect ratio
        width = max(max_x - min_x, 1e-6)
        height = max(max_y - min_y, 1e-6)
        aspect_ratio = width / height

        # Complexity score (weighted sum of entities)
        complexity = (
            entity_counts.get("line", 0) * 1.0 +
            entity_counts.get("arc", 0) * 1.5 +
            entity_counts.get("circle", 0) * 1.2 +
            entity_counts.get("spline", 0) * 2.0 +
            len(constraints) * 0.5
        )

        return SketchFeatures(
            entity_counts=dict(entity_counts),
            bounding_box=bbox,
            total_length=total_length,
            centroid=centroid,
            aspect_ratio=aspect_ratio,
            complexity_score=complexity,
        )

    def _features_to_embedding(self, feats: SketchFeatures) -> list[float]:
        """Convert sketch features to embedding vector."""
        # Entity type one-hot features
        entity_types = ["line", "arc", "circle", "spline", "point", "ellipse"]
        entity_features = [
            feats.entity_counts.get(t, 0)
            for t in entity_types
        ]

        # Normalize entity counts by log
        entity_features = [
            np.log1p(x) for x in entity_features
        ]

        # Bounding box features
        bbox = feats.bounding_box
        width = max(bbox["max_x"] - bbox["min_x"], 1e-6)
        height = max(bbox["max_y"] - bbox["min_y"], 1e-6)
        bbox_features = [
            width,
            height,
            feats.aspect_ratio,
            feats.total_length,
        ]

        # Normalized bbox features
        bbox_norm = [
            np.log1p(width),
            np.log1p(height),
            np.log1p(feats.aspect_ratio),
            np.log1p(feats.total_length),
        ]

        # Centroid (normalized to unit square)
        centroid_features = list(feats.centroid)

        # Complexity features
        complexity_features = [
            feats.complexity_score,
            sum(feats.entity_counts.values()),
        ]

        # Combine all features
        all_features = (
            entity_features +   # 6 dims
            bbox_norm +         # 4 dims
            centroid_features + # 2 dims
            complexity_features # 2 dims
        )

        feature_vec = np.array(all_features, dtype=np.float32)

        # Pad to target dimension
        if len(feature_vec) < self.embedding_dim:
            padded = np.zeros(self.embedding_dim)
            padded[:len(feature_vec)] = feature_vec
            feature_vec = padded
        elif len(feature_vec) > self.embedding_dim:
            feature_vec = feature_vec[:self.embedding_dim]

        # L2 normalize
        norm = np.linalg.norm(feature_vec)
        if norm > 0:
            feature_vec = feature_vec / norm

        return feature_vec.tolist()

    def aggregate_model_sketch_embedding(
        self,
        sketch_embeddings: dict[int, list[float]],
    ) -> list[float] | None:
        """
        Aggregate all sketch embeddings in a model to single vector.

        Useful for storing model-level sketch pattern in cad_model_embeddings.
        """
        if not sketch_embeddings:
            return None

        # Average all sketch embeddings
        embeddings = [np.array(emb) for emb in sketch_embeddings.values()]
        avg_emb = np.mean(embeddings, axis=0)

        # Normalize
        norm = np.linalg.norm(avg_emb)
        if norm > 0:
            avg_emb = avg_emb / norm

        return avg_emb.astype(np.float32).tolist()


# Convenience functions
def encode_sketches_from_serialized(
    sketches: list[dict[str, Any]] | None,
) -> dict[int, list[float]]:
    """Quick encode all sketches from serialized_models.sketches."""
    service = SketchSimilarityService()
    return service.encode_all_sketches(sketches)


def find_similar_sketches(
    query_sketch: dict[str, Any],
    sketch_db: dict[int, list[float]],
    top_k: int = 10,
) -> list[SketchSimilarityResult]:
    """Find sketches similar to a query sketch."""
    service = SketchSimilarityService()
    query_emb = service.encode_sketch(query_sketch)

    if not query_emb:
        return []

    return service.compute_sketch_similarity(query_emb, sketch_db, top_k)
