"""
Multi-modal embedding generation for CAD model similarity search.

Supports:
- Text embeddings via sentence-transformers/CLIP
- Image embeddings via CLIP vision encoder
- Geometry embeddings (placeholder for DGCNN/PointNet)
- Fused embeddings combining multiple modalities
"""

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from pybase.core.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from PIL import Image


class EmbeddingGenerator:
    """
    Generate multi-modal embeddings for CAD retrieval.

    Uses CLIP for text/image cross-modal encoding.
    Geometry encoder placeholder for future PointNet++/DGCNN integration.
    """

    # Embedding dimensions
    TEXT_EMBEDDING_DIM = 512
    IMAGE_EMBEDDING_DIM = 512
    GEOMETRY_EMBEDDING_DIM = 1024
    FUSED_EMBEDDING_DIM = 512

    def __init__(self, device: str = "cpu"):
        """Initialize embedding models."""
        self.device = device
        self._text_encoder = None
        self._image_encoder = None
        self._geometry_encoder = None

    def _ensure_text_encoder(self):
        """Lazy-load text encoder (sentence-transformers CLIP)."""
        if self._text_encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._text_encoder = SentenceTransformer(
                    "clip-ViT-B-32",
                    device=self.device
                )
                logger.info("Loaded sentence-transformers CLIP model")
            except ImportError:
                logger.warning("sentence-transformers not available, using fallback")
                self._text_encoder = "fallback"

    def _ensure_image_encoder(self):
        """Lazy-load image encoder (CLIP)."""
        if self._image_encoder is None:
            try:
                import clip
                import torch
                self._image_encoder = clip
                self._clip_model, self._clip_preprocess = clip.load(
                    "ViT-B/32", device=self.device
                )
                logger.info("Loaded OpenAI CLIP model")
            except ImportError:
                logger.warning("CLIP not available, using fallback")
                self._image_encoder = "fallback"

    def encode_text(self, text: str) -> list[float]:
        """
        Encode text description to embedding vector.

        Args:
            text: Description string

        Returns:
            512-dimensional embedding vector
        """
        if not text or not isinstance(text, str):
            return [0.0] * self.TEXT_EMBEDDING_DIM

        self._ensure_text_encoder()

        if self._text_encoder == "fallback":
            # Fallback: use hash-based pseudo-embedding
            return self._pseudo_embedding_from_text(text, self.TEXT_EMBEDDING_DIM)

        # Encode with sentence-transformers
        embedding = self._text_encoder.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        return embedding.astype(np.float32).tolist()

    def encode_image(self, image_path: str | Path) -> list[float]:
        """
        Encode image to embedding vector using CLIP.

        Args:
            image_path: Path to rendered view image

        Returns:
            512-dimensional embedding vector
        """
        self._ensure_image_encoder()

        if self._image_encoder == "fallback":
            # Fallback: hash-based pseudo-embedding
            return self._pseudo_embedding_from_path(str(image_path), self.IMAGE_EMBEDDING_DIM)

        try:
            from PIL import Image as PILImage

            # Load and preprocess image
            image = PILImage.open(image_path).convert("RGB")
            image_input = self._clip_preprocess(image).unsqueeze(0).to(self.device)

            # Encode with CLIP
            import torch
            import torch.nn.functional as F
            with torch.no_grad():
                image_features = self._clip_model.encode_image(image_input)
                image_features = F.normalize(image_features, dim=-1)

            return image_features.cpu().numpy().flatten().astype(np.float32).tolist()

        except Exception as e:
            logger.warning(f"Image encoding failed: {e}, using fallback")
            return self._pseudo_embedding_from_path(str(image_path), self.IMAGE_EMBEDDING_DIM)

    def encode_geometry(
        self,
        point_cloud: list[list[float]] | np.ndarray | None,
        bbox: dict | None = None
    ) -> list[float]:
        """
        Encode 3D geometry to embedding vector using DeepSDF encoder.

        Uses trained DeepSDF model if available, otherwise falls back
        to statistical embedding.

        Args:
            point_cloud: Nx3 array of 3D points
            bbox: Bounding box {min: [x,y,z], max: [x,y,z]}

        Returns:
            1024-dimensional geometry embedding
        """
        # Try to use trained DeepSDF encoder
        try:
            import torch

            # Lazy load DeepSDF model
            if self._geometry_encoder is None or self._geometry_encoder == "fallback":
                self._ensure_geometry_encoder()

            # If DeepSDF model loaded, use it
            if self._geometry_encoder != "fallback" and point_cloud is not None:
                points = np.array(point_cloud) if isinstance(point_cloud, list) else point_cloud
                if len(points) > 100:  # Minimum points for meaningful encoding
                    return self._encode_with_deepsdf(points)

        except Exception as e:
            logger.debug(f"DeepSDF encoding failed: {e}, using fallback")

        # Fallback: statistical pseudo-embedding
        return self._encode_geometry_fallback(point_cloud, bbox)

    def _ensure_geometry_encoder(self) -> None:
        """Lazy-load DeepSDF encoder if trained model exists."""
        try:
            import torch
            from pathlib import Path

            # Check for trained model
            model_path = Path("models/deepsdf/inference.pt")

            if model_path.exists():
                from pybase.services.deepsdf_trainer import DeepSDFTrainer

                self._deepsdf_decoder, self._deepsdf_encoder = DeepSDFTrainer.load_for_inference(
                    str(model_path),
                    device=self.device,
                )
                self._geometry_encoder = "deepsdf"
                logger.info("Loaded DeepSDF model for geometry encoding")
            else:
                self._geometry_encoder = "fallback"

        except Exception as e:
            logger.warning(f"Failed to load DeepSDF model: {e}")
            self._geometry_encoder = "fallback"

    def _encode_with_deepsdf(self, points: np.ndarray) -> list[float]:
        """
        Encode point cloud using DeepSDF encoder.

        Args:
            points: (N, 3) point cloud

        Returns:
            256-dim latent vector from DeepSDF encoder, padded to 1024
        """
        import torch

        # Normalize point cloud to unit sphere
        centroid = points.mean(axis=0)
        points_centered = points - centroid
        scale = np.max(np.linalg.norm(points_centered, axis=1))
        if scale > 0:
            points_normalized = points_centered / scale
        else:
            points_normalized = points_centered

        # Resample to fixed size if needed
        target_size = 2048
        if len(points_normalized) > target_size:
            indices = np.random.choice(len(points_normalized), target_size, replace=False)
            points_resampled = points_normalized[indices]
        elif len(points_normalized) < target_size:
            # Upsample with jitter
            shortage = target_size - len(points_normalized)
            indices = np.random.choice(len(points_normalized), shortage, replace=True)
            jitter = np.random.normal(0, 0.01, (shortage, 3))
            points_resampled = np.vstack([points_normalized, points_normalized[indices] + jitter])
        else:
            points_resampled = points_normalized

        # Convert to tensor and encode
        points_tensor = torch.from_numpy(points_resampled).float().unsqueeze(0)

        with torch.no_grad():
            latent_z = self._deepsdf_encoder(points_tensor.to(self.device))

        # DeepSDF latent is 256-dim, pad to 1024
        latent_np = latent_z.cpu().numpy().flatten()

        # Pad to target dimension
        embedding = np.zeros(self.GEOMETRY_EMBEDDING_DIM)
        n_copy = min(len(latent_np), self.GEOMETRY_EMBEDDING_DIM)
        embedding[:n_copy] = latent_np[:n_copy]

        # If latent is smaller, repeat to fill
        if len(latent_np) < self.GEOMETRY_EMBEDDING_DIM:
            for i in range(len(latent_np), self.GEOMETRY_EMBEDDING_DIM):
                embedding[i] = latent_np[i % len(latent_np)]

        return embedding.astype(np.float32).tolist()

    def _encode_geometry_fallback(
        self,
        point_cloud: list[list[float]] | np.ndarray | None,
        bbox: dict | None = None
    ) -> list[float]:
        """
        Fallback geometry encoding using statistical features.

        Args:
            point_cloud: Nx3 array of 3D points
            bbox: Bounding box {min: [x,y,z], max: [x,y,z]}

        Returns:
            1024-dimensional statistical embedding
        """
        if point_cloud is not None:
            points = np.array(point_cloud) if isinstance(point_cloud, list) else point_cloud
            if len(points) > 0:
                # Use statistics as embedding features
                centroid = points.mean(axis=0)
                std = points.std(axis=0)
                # Add higher moments for more discriminative power
                skewness = self._compute_skewness(points)
                kurtosis = self._compute_kurtosis(points)
                features = np.concatenate([
                    centroid,   # 3
                    std,        # 3
                    skewness,   # 3
                    kurtosis,   # 3
                    [len(points)],  # 1
                ])
            else:
                features = np.zeros(13)
        elif bbox is not None:
            # Use bbox dimensions
            min_pt = np.array(bbox.get("min", [0, 0, 0]))
            max_pt = np.array(bbox.get("max", [0, 0, 0]))
            dimensions = max_pt - min_pt
            center = (min_pt + max_pt) / 2
            features = np.concatenate([min_pt, max_pt, dimensions, center])
        else:
            features = np.zeros(13)

        # Pad/truncate to target dimension
        embedding = np.zeros(self.GEOMETRY_EMBEDDING_DIM)
        n_features = min(len(features), self.GEOMETRY_EMBEDDING_DIM)
        embedding[:n_features] = features[:n_features]

        return embedding.astype(np.float32).tolist()

    @staticmethod
    def _compute_skewness(points: np.ndarray) -> np.ndarray:
        """Compute skewness of point cloud per dimension."""
        mean = points.mean(axis=0)
        std = points.std(axis=0) + 1e-8
        centered = points - mean
        return np.mean((centered / std) ** 3, axis=0)

    @staticmethod
    def _compute_kurtosis(points: np.ndarray) -> np.ndarray:
        """Compute kurtosis of point cloud per dimension."""
        mean = points.mean(axis=0)
        std = points.std(axis=0) + 1e-8
        centered = points - mean
        return np.mean((centered / std) ** 4, axis=0) - 3

    def fuse_embeddings(
        self,
        text_embedding: list[float] | None = None,
        image_embedding: list[float] | None = None,
        geometry_embedding: list[float] | None = None,
        weights: dict[str, float] | None = None
    ) -> list[float]:
        """
        Fuse multiple modality embeddings into single vector.

        Args:
            text_embedding: Optional text embedding
            image_embedding: Optional image embedding
            geometry_embedding: Optional geometry embedding
            weights: Optional weights per modality (default: equal)

        Returns:
            512-dimensional fused embedding
        """
        embeddings = []
        valid_weights = []

        default_weights = {"text": 1.0, "image": 1.0, "geometry": 1.0}
        if weights is None:
            weights = default_weights
        else:
            weights = {**default_weights, **weights}

        if text_embedding and len(text_embedding) > 0:
            embeddings.append(np.array(text_embedding))
            valid_weights.append(weights["text"])

        if image_embedding and len(image_embedding) > 0:
            embeddings.append(np.array(image_embedding))
            valid_weights.append(weights["image"])

        if geometry_embedding and len(geometry_embedding) > 0:
            # Resize geometry embedding to match other dimensions
            geom = np.array(geometry_embedding)
            if len(geom) != self.TEXT_EMBEDDING_DIM:
                # Simple pooling to match dimension
                geom = self._resize_embedding(geom, self.TEXT_EMBEDDING_DIM)
            embeddings.append(geom)
            valid_weights.append(weights["geometry"])

        if not embeddings:
            return [0.0] * self.FUSED_EMBEDDING_DIM

        # Weighted average
        weights_array = np.array(valid_weights)
        weights_array = weights_array / weights_array.sum()

        stacked = np.stack(embeddings)
        fused = np.average(stacked, axis=0, weights=weights_array)

        # Normalize
        fused = fused / (np.linalg.norm(fused) + 1e-8)

        return fused.astype(np.float32).tolist()

    def compute_lsh_buckets(
        self,
        embedding: list[float] | np.ndarray,
        num_buckets: int = 4
    ) -> list[int]:
        """
        Compute LSH bucket indices for coarse filtering.

        Uses deterministic random hyperplanes for consistent bucket assignment.

        Args:
            embedding: Embedding vector
            num_buckets: Number of LSH buckets to compute

        Returns:
            List of bucket indices (0 or 1 for each bucket)
        """
        if isinstance(embedding, list):
            embedding = np.array(embedding)

        # Deterministic random hyperplanes (fixed seed for consistency)
        np.random.seed(42)
        hyperplanes = np.random.randn(num_buckets, len(embedding))

        buckets = []
        for hp in hyperplanes:
            bucket = int(np.dot(embedding, hp) > 0)
            buckets.append(bucket)

        return buckets

    def _pseudo_embedding_from_text(self, text: str, dim: int) -> list[float]:
        """Generate pseudo-embedding from text using hash (fallback)."""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # Expand hash to desired dimension
        embedding = []
        for i in range(dim):
            idx = i % len(hash_bytes)
            # Convert byte to float in [-1, 1]
            val = (hash_bytes[idx] / 127.5) - 1.0
            embedding.append(val)
        # Normalize
        embedding = np.array(embedding)
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        return embedding.astype(np.float32).tolist()

    def _pseudo_embedding_from_path(self, path: str, dim: int) -> list[float]:
        """Generate pseudo-embedding from file path using hash (fallback)."""
        return self._pseudo_embedding_from_text(path, dim)

    @staticmethod
    def _resize_embedding(embedding: np.ndarray, target_dim: int) -> np.ndarray:
        """Resize embedding to target dimension via pooling/interpolation."""
        current_dim = len(embedding)
        if current_dim == target_dim:
            return embedding

        if current_dim < target_dim:
            # Pad with zeros
            result = np.zeros(target_dim)
            result[:current_dim] = embedding
            return result
        else:
            # Average pool to reduce dimension
            pool_size = current_dim // target_dim
            if pool_size <= 1:
                return embedding[:target_dim]
            reshaped = embedding[: pool_size * target_dim].reshape(target_dim, pool_size)
            return reshaped.mean(axis=1)


# Singleton instance for reuse
_default_generator: EmbeddingGenerator | None = None


def get_embedding_generator(device: str = "cpu") -> EmbeddingGenerator:
    """Get or create singleton embedding generator."""
    global _default_generator
    if _default_generator is None:
        _default_generator = EmbeddingGenerator(device=device)
    return _default_generator
