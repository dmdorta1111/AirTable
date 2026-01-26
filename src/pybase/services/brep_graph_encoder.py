"""
B-Rep Graph Encoder for processing existing serialized model data.

Processes feature_geometry JSONB from serialized_models table to generate:
- Face adjacency graph
- 512-dim B-Rep graph embedding

Integrates with existing CosCAD retrieval system without modifying
master_serialize_and_index.py extraction.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np

from pybase.core.logging import get_logger

logger = get_logger(__name__)

# Target embedding dimension (matches schema)
BREP_EMBEDDING_DIM = 512


@dataclass
class BRepGraph:
    """Face adjacency graph from feature geometry."""
    faces: list[dict]  # Face nodes with attributes
    edges: list[dict]  # Edge connections between faces
    adjacency: dict[int, list[int]]  # Face ID -> adjacent face IDs
    face_count: int
    edge_count: int


@dataclass
class EncodingResult:
    """Result of B-Rep graph encoding."""
    embedding: list[float] | None
    graph: BRepGraph | None
    error: str | None = None
    features_used: int = 0


class BRepGraphEncoder:
    """
    Encode B-Rep topology from existing serialized feature_geometry.

    Reads from serialized_models.feature_geometry JSONB:
    - surfaces: List of surface definitions
    - edges: List of edge definitions with adjacency info

    Generates 512-dim embedding via simple graph neural encoding.
    """

    def __init__(self, embedding_dim: int = BREP_EMBEDDING_DIM):
        self.embedding_dim = embedding_dim

    def encode_from_serialized_data(
        self,
        feature_geometry: dict[str, Any] | None,
    ) -> EncodingResult:
        """
        Encode B-Rep graph from existing serialized feature_geometry.

        Args:
            feature_geometry: JSONB data from serialized_models.feature_geometry
                             Contains {surfaces: [...], edges: [...]}

        Returns:
            EncodingResult with 512-dim embedding
        """
        if not feature_geometry:
            return EncodingResult(
                embedding=None,
                graph=None,
                error="No feature_geometry data available",
            )

        try:
            # Build graph from surfaces/edges
            graph = self._build_graph(feature_geometry)

            if graph.face_count == 0:
                return EncodingResult(
                    embedding=None,
                    graph=None,
                    error="No faces found in feature_geometry",
                )

            # Generate embedding from graph
            embedding = self._encode_graph(graph)

            return EncodingResult(
                embedding=embedding,
                graph=graph,
                features_used=graph.face_count,
            )

        except Exception as e:
            logger.error(f"B-Rep encoding failed: {e}")
            return EncodingResult(
                embedding=None,
                graph=None,
                error=str(e),
            )

    def _build_graph(self, feature_geometry: dict[str, Any]) -> BRepGraph:
        """Build face adjacency graph from surfaces and edges."""
        surfaces = feature_geometry.get("surfaces", [])
        edges = feature_geometry.get("edges", [])

        # Extract faces from surfaces
        faces = []
        face_id_map = {}  # Track face IDs

        for i, surf in enumerate(surfaces):
            face_id = surf.get("id", i)
            face_id_map[face_id] = len(faces)

            faces.append({
                "id": face_id,
                "type": surf.get("type", "unknown"),
                "area": surf.get("area", 0.0),
                "normal": surf.get("normal", [0, 0, 1]),
                "centroid": surf.get("centroid", [0, 0, 0]),
            })

        # Build adjacency from edges
        adjacency = defaultdict(list)
        graph_edges = []

        for edge in edges:
            # Edge typically connects two faces
            face_ids = edge.get("adjacent_faces", [])
            if len(face_ids) >= 2:
                f1, f2 = face_ids[0], face_ids[1]

                if f1 in face_id_map and f2 in face_id_map:
                    idx1, idx2 = face_id_map[f1], face_id_map[f2]
                    adjacency[idx1].append(idx2)
                    adjacency[idx2].append(idx1)

                    graph_edges.append({
                        "face1": f1,
                        "face2": f2,
                        "convexity": edge.get("convexity", 0),
                        "length": edge.get("length", 0.0),
                    })

        return BRepGraph(
            faces=faces,
            edges=graph_edges,
            adjacency=dict(adjacency),
            face_count=len(faces),
            edge_count=len(graph_edges),
        )

    def _encode_graph(self, graph: BRepGraph) -> list[float]:
        """
        Generate 512-dim embedding from B-Rep graph.

        Uses simplified graph encoding:
        1. Face feature aggregation (type one-hot, geometric stats)
        2. Graph structure encoding (adjacency histogram)
        3. Concatenate and normalize
        """
        # Face type distribution
        face_types = defaultdict(int)
        face_areas = []
        normals = []

        for face in graph.faces:
            ftype = face["type"]
            face_types[ftype] += 1
            face_areas.append(face["area"])
            normals.extend(face["normal"][:3])

        # Normalize face type counts
        type_features = []
        common_types = ["plane", "cylinder", "cone", "sphere", "torus", "spline"]
        for t in common_types:
            type_features.append(face_types.get(t, 0) / max(graph.face_count, 1))

        # Add other types count
        other_count = sum(
            v for k, v in face_types.items()
            if k not in common_types
        )
        type_features.append(other_count / max(graph.face_count, 1))

        # Geometric statistics
        area_stats = self._compute_array_stats(face_areas)
        normal_stats = self._compute_array_stats(normals)

        # Graph structure features
        degree_sequence = [
            len(neighbors) for neighbors in graph.adjacency.values()
        ]
        graph_stats = self._compute_array_stats(degree_sequence) if degree_sequence else [0] * 5

        # Edge convexity distribution
        convexities = [e.get("convexity", 0) for e in graph.edges]
        convex_stats = self._compute_array_stats(convexities) if convexities else [0] * 5

        # Concatenate all features
        all_features = (
            type_features +      # 7 dims
            area_stats +         # 5 dims
            normal_stats +       # 5 dims
            graph_stats +        # 5 dims
            convex_stats +       # 5 dims
            [graph.face_count, graph.edge_count]  # 2 dims
        )

        # Pad/truncate to target dimension
        feature_vec = np.array(all_features, dtype=np.float32)

        if len(feature_vec) < self.embedding_dim:
            # Pad with zeros
            padded = np.zeros(self.embedding_dim)
            padded[:len(feature_vec)] = feature_vec
            feature_vec = padded
        elif len(feature_vec) > self.embedding_dim:
            # Truncate
            feature_vec = feature_vec[:self.embedding_dim]

        # L2 normalize
        norm = np.linalg.norm(feature_vec)
        if norm > 0:
            feature_vec = feature_vec / norm

        return feature_vec.tolist()

    @staticmethod
    def _compute_array_stats(arr: list[float]) -> list[float]:
        """Compute [mean, std, min, max, median] for array."""
        if not arr:
            return [0.0, 0.0, 0.0, 0.0, 0.0]

        a = np.array(arr)
        return [
            float(np.mean(a)),
            float(np.std(a)) if len(a) > 1 else 0.0,
            float(np.min(a)),
            float(np.max(a)),
            float(np.median(a)),
        ]


# Convenience function for standalone use
def encode_brep_from_feature_geometry(
    feature_geometry: dict[str, Any] | None,
) -> tuple[list[float] | None, dict[str, Any] | None]:
    """
    Quick encode B-Rep graph from feature_geometry.

    Returns:
        (embedding, metadata) tuple
    """
    encoder = BRepGraphEncoder()
    result = encoder.encode_from_serialized_data(feature_geometry)

    metadata = None
    if result.graph:
        metadata = {
            "face_count": result.graph.face_count,
            "edge_count": result.graph.edge_count,
            "features_used": result.features_used,
        }

    return result.embedding, metadata
