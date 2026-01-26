"""
DeepSDF training data generator for engineering CAD parts.

Interfaces with Subagent 3's CreoGenomeExtractor to generate
multi-resolution SDF samples for training.

Sampling strategy:
1. Surface points (stratified sampling on mesh)
2. Near-surface (Gaussian distribution around surface)
3. Uniform volume (grid-based)
4. Manufacturing-aware (feature density weighting)
"""

import hashlib
import json
import pickle
import zlib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch

from pybase.core.logging import get_logger
from pybase.services.creo_genome_extractor import (
    DeepSDFTrainingData,
    SDFSample,
)

logger = get_logger(__name__)


class SamplingStrategy(Enum):
    """SDF sampling strategies."""
    SURFACE = "surface"  # Points on mesh surface
    NEAR_SURFACE = "near_surface"  # Gaussian band around surface
    VOLUME = "volume"  # Uniform in bounding box
    MANUFACTURING = "manufacturing"  # Feature-aware sampling


@dataclass
class SamplingConfig:
    """Configuration for SDF sampling."""

    # Number of samples per type
    num_surface: int = 10000
    num_near_surface: int = 50000
    num_volume: int = 100000
    num_manufacturing: int = 20000

    # Near-surface parameters
    near_surface_std: float = 0.02  # Gaussian std relative to bbox
    near_surface_band: float = 0.1  # Max distance from surface

    # Manufacturing-aware parameters
    feature_radius: float = 0.05  # Radius around features (holes, edges)
    feature_density_weight: float = 2.0  # Oversample features

    # Caching
    cache_dir: str = "cache/deepsdf_samples"
    use_cache: bool = True

    # Normalization
    normalize_to_unit_sphere: bool = True


@dataclass
class TrainingSample:
    """Single training sample with points and SDF values."""
    shape_id: str
    points: np.ndarray  # (N, 3)
    sdf_values: np.ndarray  # (N,)
    normals: np.ndarray | None = None  # (N, 3) optional
    metadata: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.points)

    def to_dict(self) -> dict:
        return {
            "shape_id": self.shape_id,
            "points": self.points.tolist(),
            "sdf_values": self.sdf_values.tolist(),
            "normals": self.normals.tolist() if self.normals is not None else None,
            "metadata": self.metadata,
        }


class CreoTrainingDataGenerator:
    """
    Generate DeepSDF training data from Creo extraction results.

    Processes CreoGenomeExtractor output into training samples
    with multi-resolution SDF sampling.
    """

    def __init__(
        self,
        config: SamplingConfig | None = None,
    ):
        """
        Initialize data generator.

        Args:
            config: Sampling configuration
        """
        self.config = config or SamplingConfig()
        self._cache_dir = Path(self.config.cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def generate_from_extraction(
        self,
        extraction_data: DeepSDFTrainingData,
        shape_id: str,
        strategies: list[SamplingStrategy] | None = None,
    ) -> TrainingSample:
        """
        Generate training samples from Creo extraction result.

        Args:
            extraction_data: SDF training data from CreoGenomeExtractor
            shape_id: Unique identifier for this shape
            strategies: Which sampling strategies to use

        Returns:
            TrainingSample with combined SDF samples
        """
        if strategies is None:
            strategies = [
                SamplingStrategy.SURFACE,
                SamplingStrategy.NEAR_SURFACE,
                SamplingStrategy.VOLUME,
            ]

        # Check cache
        cache_key = self._get_cache_key(shape_id, strategies)
        if self.config.use_cache:
            cached = self._load_from_cache(cache_key)
            if cached is not None:
                return cached

        all_points = []
        all_sdf = []
        all_normals = []

        bbox = extraction_data.bounding_box

        # Generate samples for each strategy
        for strategy in strategies:
            if strategy == SamplingStrategy.SURFACE:
                points, sdf, normals = self._sample_surface(
                    extraction_data.surface_samples
                )
            elif strategy == SamplingStrategy.NEAR_SURFACE:
                points, sdf = self._sample_near_surface(
                    extraction_data,
                    bbox,
                )
                normals = None
            elif strategy == SamplingStrategy.VOLUME:
                points, sdf = self._sample_volume(
                    extraction_data,
                    bbox,
                )
                normals = None
            elif strategy == SamplingStrategy.MANUFACTURING:
                points, sdf = self._sample_manufacturing_aware(
                    extraction_data,
                    bbox,
                )
                normals = None
            else:
                continue

            all_points.append(points)
            all_sdf.append(sdf)
            if normals is not None:
                all_normals.append(normals)

        # Combine all samples
        combined_points = np.vstack(all_points)
        combined_sdf = np.concatenate(all_sdf)
        combined_normals = np.vstack(all_normals) if all_normals else None

        # Normalize to unit sphere if enabled
        if self.config.normalize_to_unit_sphere:
            combined_points, combined_sdf = self._normalize_to_unit_sphere(
                combined_points,
                combined_sdf,
                bbox,
            )

        sample = TrainingSample(
            shape_id=shape_id,
            points=combined_points,
            sdf_values=combined_sdf,
            normals=combined_normals,
            metadata={
                "bbox": bbox,
                "num_points": len(combined_points),
                "strategies": [s.value for s in strategies],
            },
        )

        # Cache result
        if self.config.use_cache:
            self._save_to_cache(cache_key, sample)

        return sample

    def _sample_surface(
        self,
        surface_samples: list[SDFSample],
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Extract surface samples from extraction data.

        Args:
            surface_samples: List of SDFSample with sdf_value ~ 0

        Returns:
            (points, sdf, normals) arrays
        """
        if not surface_samples:
            return (
                np.zeros((0, 3), dtype=np.float32),
                np.zeros(0, dtype=np.float32),
                np.zeros((0, 3), dtype=np.float32),
            )

        points = np.array([s.position for s in surface_samples], dtype=np.float32)
        sdf = np.array([s.sdf_value for s in surface_samples], dtype=np.float32)

        normals = None
        if surface_samples[0].normal is not None:
            normals = np.array(
                [s.normal for s in surface_samples],
                dtype=np.float32
            )

        return points, sdf, normals

    def _sample_near_surface(
        self,
        extraction_data: DeepSDFTrainingData,
        bbox: dict,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Generate near-surface samples via Gaussian distribution.

        Args:
            extraction_data: Training data with surface samples
            bbox: Bounding box

        Returns:
            (points, sdf) arrays
        """
        if not extraction_data.near_surface_samples:
            return self._generate_near_surface_fallback(
                extraction_data,
                bbox,
                self.config.num_near_surface,
            )

        points = np.array(
            [s.position for s in extraction_data.near_surface_samples],
            dtype=np.float32,
        )
        sdf = np.array(
            [s.sdf_value for s in extraction_data.near_surface_samples],
            dtype=np.float32,
        )

        return points, sdf

    def _generate_near_surface_fallback(
        self,
        extraction_data: DeepSDFTrainingData,
        bbox: dict,
        num_samples: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Generate near-surface samples when not in extraction data.

        Uses surface samples and offsets along normals.
        """
        if not extraction_data.surface_samples:
            return np.zeros((0, 3)), np.zeros(0)

        surface_points = np.array(
            [s.position for s in extraction_data.surface_samples],
            dtype=np.float32,
        )

        # Sample surface points
        n_surface = len(surface_points)
        indices = np.random.choice(n_surface, size=min(num_samples, n_surface * 10), replace=True)
        base_points = surface_points[indices]

        # Get normals if available
        if extraction_data.surface_samples[0].normal:
            normals = np.array(
                [s.normal for s in extraction_data.surface_samples],
                dtype=np.float32,
            )[indices]
        else:
            # Random normals
            normals = np.random.randn(len(base_points), 3).astype(np.float32)
            normals /= np.linalg.norm(normals, axis=1, keepdims=True)

        # Offset along normals with Gaussian
        bbox_min = np.array(bbox["min"])
        bbox_max = np.array(bbox["max"])
        bbox_scale = (bbox_max - bbox_min).max()

        offsets = np.random.randn(len(base_points), 1).astype(np.float32)
        offsets *= self.config.near_surface_std * bbox_scale

        near_points = base_points + normals * offsets

        # Estimate SDF (sign of offset)
        near_sdf = offsets.squeeze(-1)

        return near_points, near_sdf

    def _sample_volume(
        self,
        extraction_data: DeepSDFTrainingData,
        bbox: dict,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Generate uniform volume samples in bounding box.

        Args:
            extraction_data: Training data
            bbox: Bounding box

        Returns:
            (points, sdf) arrays
        """
        if extraction_data.volume_samples:
            points = np.array(
                [s.position for s in extraction_data.volume_samples],
                dtype=np.float32,
            )
            sdf = np.array(
                [s.sdf_value for s in extraction_data.volume_samples],
                dtype=np.float32,
            )
            return points, sdf

        # Generate uniform random samples in bbox
        num_samples = self.config.num_volume
        bbox_min = np.array(bbox["min"])
        bbox_max = np.array(bbox["max"])

        points = np.random.rand(num_samples, 3).astype(np.float32)
        points = points * (bbox_max - bbox_min) + bbox_min

        # For volume samples without SDF, use heuristic:
        # - Points near surface: use distance
        # - Points far: use sign based on proximity to center
        sdf = self._estimate_volume_sdf(points, extraction_data)

        return points, sdf

    def _estimate_volume_sdf(
        self,
        points: np.ndarray,
        extraction_data: DeepSDFTrainingData,
    ) -> np.ndarray:
        """
        Estimate SDF for volume samples using surface proxy.

        Simple heuristic: use distance to nearest surface sample.
        """
        if not extraction_data.surface_samples:
            return np.zeros(len(points), dtype=np.float32)

        surface_points = np.array(
            [s.position for s in extraction_data.surface_samples],
            dtype=np.float32,
        )

        # For efficiency, use random subset of surface points
        max_surface = 1000
        if len(surface_points) > max_surface:
            idx = np.random.choice(len(surface_points), max_surface, replace=False)
            surface_points = surface_points[idx]

        # Compute distance to nearest surface point
        # Vectorized brute force (acceptable for moderate sizes)
        sdf = np.full(len(points), -1.0, dtype=np.float32)  # Default: inside

        # Simple heuristic: if point is "outside" bbox centroid, mark positive
        bbox_min = np.array(extraction_data.bounding_box["min"])
        bbox_max = np.array(extraction_data.bounding_box["max"])
        centroid = (bbox_min + bbox_max) / 2

        for i, pt in enumerate(points):
            dist_to_surface = np.linalg.norm(surface_points - pt, axis=1).min()

            # Determine sign: points farther from centroid than surface likely outside
            dist_to_centroid = np.linalg.norm(pt - centroid)
            avg_surface_radius = np.linalg.norm(surface_points - centroid, axis=1).mean()

            if dist_to_centroid > avg_surface_radius:
                sdf[i] = dist_to_surface  # Outside
            else:
                sdf[i] = -dist_to_surface  # Inside

        return sdf

    def _sample_manufacturing_aware(
        self,
        extraction_data: DeepSDFTrainingData,
        bbox: dict,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Generate manufacturing-aware samples near features.

        Focuses sampling on:
        - Edges (sharp changes in normal)
        - Small features (holes, fillets)
        - High-curvature regions

        Args:
            extraction_data: Training data
            bbox: Bounding box

        Returns:
            (points, sdf) arrays
        """
        num_samples = self.config.num_manufacturing
        bbox_min = np.array(bbox["min"])
        bbox_max = np.array(bbox["max"])
        bbox_scale = (bbox_max - bbox_min).max()

        # Use surface samples as base
        if not extraction_data.surface_samples:
            return np.zeros((0, 3)), np.zeros(0)

        surface_points = np.array(
            [s.position for s in extraction_data.surface_samples],
            dtype=np.float32,
        )

        # Stratified sampling: oversample regions with high normal variance
        # (indicator of edges/features)

        if extraction_data.surface_samples[0].normal:
            normals = np.array(
                [s.normal for s in extraction_data.surface_samples],
                dtype=np.float32,
            )

            # Compute normal variance (local)
            # Simplified: random subset for efficiency
            n_features = min(len(surface_points), 5000)
            indices = np.random.choice(len(surface_points), n_features, replace=False)
            feature_points = surface_points[indices]
            feature_normals = normals[indices]

            # Sample around feature points
            points = []
            sdf = []

            for i in range(num_samples):
                # Pick random feature point
                idx = np.random.randint(0, len(feature_points))
                base_pt = feature_points[idx]
                base_sdf = 0.0  # On surface

                # Add noise
                noise = np.random.randn(3).astype(np.float32)
                noise *= self.config.feature_radius * bbox_scale

                pt = base_pt + noise
                sdf_val = base_sdf + np.random.randn() * self.config.near_surface_std * bbox_scale

                points.append(pt)
                sdf.append(sdf_val)

            return np.array(points), np.array(sdf)
        else:
            # Fallback: uniform sampling
            return self._sample_volume(extraction_data, bbox)

    def _normalize_to_unit_sphere(
        self,
        points: np.ndarray,
        sdf: np.ndarray,
        bbox: dict,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Normalize points to unit sphere and scale SDF accordingly.

        Args:
            points: (N, 3) points
            sdf: (N,) SDF values
            bbox: Original bounding box

        Returns:
            Normalized (points, sdf)
        """
        if len(points) == 0:
            return points, sdf

        bbox_min = np.array(bbox["min"])
        bbox_max = np.array(bbox["max"])

        # Center at origin
        center = (bbox_min + bbox_max) / 2
        points_centered = points - center

        # Scale to unit sphere
        scale = (bbox_max - bbox_min).max() / 2
        if scale > 0:
            points_normalized = points_centered / scale
            sdf_normalized = sdf / scale
        else:
            points_normalized = points_centered
            sdf_normalized = sdf

        return points_normalized.astype(np.float32), sdf_normalized.astype(np.float32)

    def _get_cache_key(
        self,
        shape_id: str,
        strategies: list[SamplingStrategy],
    ) -> str:
        """Generate cache key for samples."""
        key = f"{shape_id}_{'_'.join(s.value for s in strategies)}_{self.config.num_surface}"
        return hashlib.md5(key.encode()).hexdigest()

    def _load_from_cache(self, cache_key: str) -> Optional[TrainingSample]:
        """Load samples from cache."""
        cache_path = self._cache_dir / f"{cache_key}.pkl"

        if cache_path.exists():
            try:
                with open(cache_path, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass

        return None

    def _save_to_cache(self, cache_key: str, sample: TrainingSample) -> None:
        """Save samples to cache."""
        cache_path = self._cache_dir / f"{cache_key}.pkl"

        try:
            with open(cache_path, "wb") as f:
                pickle.dump(sample, f)
        except Exception as e:
            logger.warning(f"Failed to cache samples: {e}")

    def create_torch_dataset(
        self,
        samples: list[TrainingSample],
        clip_features: dict[str, list[np.ndarray]] | None = None,
    ) -> "DeepSDFDataset":
        """
        Create PyTorch dataset from training samples.

        Must import locally to avoid circular dependency.

        Args:
            samples: List of TrainingSample
            clip_features: Optional CLIP embeddings

        Returns:
            DeepSDFDataset instance
        """
        from pybase.services.deepsdf_trainer import DeepSDFDataset

        points_list = [s.points for s in samples]
        sdf_list = [s.sdf_values for s in samples]

        return DeepSDFDataset(
            samples=points_list,
            sdf_values=sdf_list,
            clip_features=clip_features,
        )

    def generate_from_json_files(
        self,
        json_paths: list[str | Path],
    ) -> list[TrainingSample]:
        """
        Generate training samples from Creo extraction JSON files.

        Args:
            json_paths: List of paths to extraction JSON files

        Returns:
            List of TrainingSample
        """
        from pybase.services.creo_genome_extractor import CreoGenomeExtractor

        samples = []

        for path in json_paths:
            path = Path(path)

            # Load extraction data
            extractor = CreoGenomeExtractor()
            result = extractor.extract_from_json(str(path))

            if result.deepsdf_data:
                shape_id = path.stem
                sample = self.generate_from_extraction(
                    result.deepsdf_data,
                    shape_id,
                )
                samples.append(sample)
            else:
                logger.warning(f"No DeepSDF data in {path}")

        return samples

    def export_dataset(
        self,
        samples: list[TrainingSample],
        output_path: str | Path,
        format: str = "json",
    ) -> None:
        """
        Export dataset to file.

        Args:
            samples: List of TrainingSample
            output_path: Output file path
            format: Export format ("json", "npz", "hdf5")
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            data = {
                "samples": [s.to_dict() for s in samples],
                "num_shapes": len(samples),
                "total_points": sum(len(s) for s in samples),
            }
            with open(output_path, "w") as f:
                json.dump(data, f)

        elif format == "npz":
            # Compressed numpy format
            points_dict = {
                f"shape_{i}": s.points
                for i, s in enumerate(samples)
            }
            sdf_dict = {
                f"shape_{i}": s.sdf_values
                for i, s in enumerate(samples)
            }

            np.savez_compressed(
                output_path,
                **points_dict,
                **sdf_dict,
                shape_ids=[s.shape_id for s in samples],
            )

        elif format == "hdf5":
            try:
                import h5py

                with h5py.File(output_path, "w") as f:
                    for i, s in enumerate(samples):
                        group = f.create_group(s.shape_id)
                        group.create_dataset("points", data=s.points)
                        group.create_dataset("sdf", data=s.sdf_values)
                        if s.normals is not None:
                            group.create_dataset("normals", data=s.normals)

                        # Metadata as attributes
                        for key, value in s.metadata.items():
                            group.attrs[key] = json.dumps(value)
            except ImportError:
                logger.warning("h5py not installed, falling back to npz")
                self.export_dataset(samples, output_path.with_suffix(".npz"), "npz")

        logger.info(f"Exported {len(samples)} samples to {output_path}")


def create_training_batch(
    samples: list[TrainingSample],
    batch_size: int = 64,
    samples_per_shape: int = 16384,
) -> list[dict[str, torch.Tensor]]:
    """
    Create training batches from samples.

    Args:
        samples: List of TrainingSample
        batch_size: Batch size
        samples_per_shape: Target samples per shape (resample if needed)

    Returns:
        List of batch dictionaries
    """
    batches = []

    for i in range(0, len(samples), batch_size):
        batch_samples = samples[i:i + batch_size]

        batch_points = []
        batch_sdf = []
        batch_shape_idx = []

        for shape_idx, sample in enumerate(batch_samples):
            # Resample to target size
            n = len(sample)
            if n >= samples_per_shape:
                indices = np.random.choice(n, samples_per_shape, replace=False)
                points = sample.points[indices]
                sdf = sample.sdf_values[indices]
            else:
                # Upsample with replacement
                indices = np.random.choice(n, samples_per_shape, replace=True)
                points = sample.points[indices]
                sdf = sample.sdf_values[indices]

            batch_points.append(torch.from_numpy(points))
            batch_sdf.append(torch.from_numpy(sdf))
            batch_shape_idx.append(shape_idx)

        # Pad to same size (collate_fn will handle)
        batches.append({
            "points": batch_points,
            "sdf": batch_sdf,
            "shape_idx": torch.tensor(batch_shape_idx),
        })

    return batches
