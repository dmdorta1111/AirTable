"""
DeepSDF training pipeline for engineering CAD parts.

Implements curriculum learning with 4 phases:
1. Coarse: Basic shape recovery
2. Balanced: Surface + near-surface
3. Dense: Fine detail capture
4. Manufacturing: Feature-aware sampling

Uses auto-decoder architecture with contrastive CLIP alignment.
"""

import json
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

from pybase.core.logging import get_logger
from pybase.models.deepsdf import (
    AssemblyAwareEncoder,
    CrossModalContrastiveLoss,
    DeepSDFEncoder,
    EngineeringPartSDF,
)

logger = get_logger(__name__)


class TrainingPhase(Enum):
    """Curriculum learning phases."""
    COARSE = "coarse"  # 50 epochs: Basic shape
    BALANCED = "balanced"  # 100 epochs: Surface + near
    DENSE = "dense"  # 200 epochs: Fine details
    MANUFACTURING = "manufacturing"  # 50 epochs: Feature-aware


@dataclass
class TrainingConfig:
    """Configuration for DeepSDF training."""

    # Model architecture
    latent_dim: int = 256
    hidden_dim: int = 512
    num_layers: int = 8

    # Training hyperparameters
    batch_size: int = 64
    num_samples_per_shape: int = 16384  # SDF samples per part

    # Phase-specific learning rates
    lr_coarse: float = 1e-4
    lr_balanced: float = 5e-5
    lr_dense: float = 1e-5
    lr_manufacturing: float = 1e-6

    # Epochs per phase
    epochs_coarse: int = 50
    epochs_balanced: int = 100
    epochs_dense: int = 200
    epochs_manufacturing: int = 50

    # Contrastive learning
    contrastive_weight: float = 0.1  # Weight for CLIP alignment
    temperature: float = 0.07

    # Regularization
    epsilon: float = 0.01  # Surface stabilization

    # Hardware
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    num_workers: int = 4

    # Checkpointing
    checkpoint_dir: str = "models/deepsdf"
    save_every: int = 10

    def get_lr_for_phase(self, phase: TrainingPhase) -> float:
        """Get learning rate for training phase."""
        return {
            TrainingPhase.COARSE: self.lr_coarse,
            TrainingPhase.BALANCED: self.lr_balanced,
            TrainingPhase.DENSE: self.lr_dense,
            TrainingPhase.MANUFACTURING: self.lr_manufacturing,
        }[phase]

    def get_epochs_for_phase(self, phase: TrainingPhase) -> int:
        """Get epochs for training phase."""
        return {
            TrainingPhase.COARSE: self.epochs_coarse,
            TrainingPhase.BALANCED: self.epochs_balanced,
            TrainingPhase.DENSE: self.epochs_dense,
            TrainingPhase.MANUFACTURING: self.epochs_manufacturing,
        }[phase]

    @property
    def total_epochs(self) -> int:
        """Total training epochs across all phases."""
        return sum(
            self.get_epochs_for_phase(p)
            for p in TrainingPhase
        )


@dataclass
class TrainingMetrics:
    """Metrics collected during training."""
    epoch: int
    phase: str
    loss_sdf: float = 0.0
    loss_contrastive: float = 0.0
    loss_total: float = 0.0
    accuracy_inside: float = 0.0  # % correct inside/outside
    time_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "epoch": self.epoch,
            "phase": self.phase,
            "loss_sdf": self.loss_sdf,
            "loss_contrastive": self.loss_contrastive,
            "loss_total": self.loss_total,
            "accuracy_inside": self.accuracy_inside,
            "time_seconds": self.time_seconds,
        }


class DeepSDFDataset(Dataset):
    """
    Dataset for DeepSDF training.

    Each item contains:
    - SDF samples (points + values)
    - Optional CLIP text/image embeddings
    - Shape index for latent code lookup
    """

    def __init__(
        self,
        samples: list[np.ndarray],
        sdf_values: list[np.ndarray],
        clip_features: dict[str, list[np.ndarray]] | None = None,
    ):
        """
        Initialize dataset.

        Args:
            samples: List of (N_i, 3) point arrays per shape
            sdf_values: List of (N_i,) SDF value arrays per shape
            clip_features: Optional {text: [...], image: [...]} embeddings
        """
        self.samples = samples
        self.sdf_values = sdf_values
        self.clip_features = clip_features or {}
        self.num_shapes = len(samples)

        # Build cumulative indices for batching
        self.cumulative_sizes = np.cumsum([len(s) for s in samples])

    def __len__(self) -> int:
        return self.num_shapes

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        """Get training item for shape idx."""
        points = torch.from_numpy(self.samples[idx]).float()
        sdf = torch.from_numpy(self.sdf_values[idx]).float()

        item = {
            "points": points,
            "sdf": sdf.unsqueeze(-1),
            "shape_idx": idx,
        }

        # Add CLIP features if available
        if "text" in self.clip_features:
            item["text_embed"] = torch.from_numpy(
                self.clip_features["text"][idx]
            ).float()

        if "image" in self.clip_features:
            item["image_embed"] = torch.from_numpy(
                self.clip_features["image"][idx]
            ).float()

        return item

    def get_num_samples(self, idx: int) -> int:
        """Get number of samples for shape idx."""
        return len(self.samples[idx])


def collate_fn(batch: list[dict]) -> dict[str, torch.Tensor]:
    """
    Collate function for variable-sized SDF samples.

    Pads to max samples in batch.
    """
    max_samples = max(item["points"].shape[0] for item in batch)
    batch_size = len(batch)

    # Initialize padded tensors
    points = torch.zeros(batch_size, max_samples, 3)
    sdf = torch.zeros(batch_size, max_samples, 1)
    shape_indices = torch.zeros(batch_size, dtype=torch.long)

    # Optional CLIP features
    has_text = "text_embed" in batch[0]
    has_image = "image_embed" in batch[0]

    text_embeds = torch.zeros(batch_size, 512) if has_text else None
    image_embeds = torch.zeros(batch_size, 512) if has_image else None

    for i, item in enumerate(batch):
        n = item["points"].shape[0]
        points[i, :n] = item["points"]
        sdf[i, :n] = item["sdf"]
        shape_indices[i] = item["shape_idx"]

        if has_text:
            text_embeds[i] = item["text_embed"]

        if has_image:
            image_embeds[i] = item["image_embed"]

    result = {
        "points": points,
        "sdf": sdf,
        "shape_idx": shape_indices,
    }

    if has_text:
        result["text_embed"] = text_embeds

    if has_image:
        result["image_embed"] = image_embeds

    return result


class DeepSDFTrainer:
    """
    Trainer for DeepSDF on engineering CAD parts.

    Features:
    - Curriculum learning across 4 phases
    - Auto-decoder with learnable latent codes
    - CLIP contrastive alignment
    - Checkpoint saving/loading
    - Validation metrics
    """

    def __init__(
        self,
        config: TrainingConfig,
        decoder: EngineeringPartSDF | None = None,
        encoder: DeepSDFEncoder | None = None,
    ):
        """
        Initialize trainer.

        Args:
            config: Training configuration
            decoder: Optional pre-initialized decoder
            encoder: Optional pre-initialized encoder
        """
        self.config = config
        self.device = torch.device(config.device)

        # Initialize model
        if decoder is None:
            self.decoder = EngineeringPartSDF(
                latent_dim=config.latent_dim,
                hidden_dim=config.hidden_dim,
                num_layers=config.num_layers,
            ).to(self.device)
        else:
            self.decoder = decoder.to(self.device)

        # Initialize encoder for latent initialization
        if encoder is None:
            self.encoder = DeepSDFEncoder(
                output_dim=config.latent_dim,
            ).to(self.device)
        else:
            self.encoder = encoder.to(self.device)

        # Loss functions
        self.contrastive_loss = CrossModalContrastiveLoss(
            temperature=config.temperature
        ).to(self.device)

        # Training state
        self.current_epoch = 0
        self.current_phase = TrainingPhase.COARSE
        self.latent_codes: Optional[nn.Parameter] = None

        # Optimizer (set in train_step)
        self.optimizer: Optional[torch.optim.Optimizer] = None

        # Metrics history
        self.metrics_history: list[TrainingMetrics] = []

        # Create checkpoint directory
        Path(config.checkpoint_dir).mkdir(parents=True, exist_ok=True)

    def initialize_for_dataset(
        self,
        dataset: DeepSDFDataset,
    ) -> None:
        """
        Initialize latent codes for dataset.

        Args:
            dataset: Training dataset
        """
        num_shapes = len(dataset)
        self.latent_codes = self.decoder.initialize_latent_codes(num_shapes)
        logger.info(f"Initialized {num_shapes} latent codes")

    def train_step(
        self,
        batch: dict[str, torch.Tensor],
        phase: TrainingPhase,
    ) -> TrainingMetrics:
        """
        Single training step.

        Args:
            batch: Batch dict from DataLoader
            phase: Current training phase

        Returns:
            TrainingMetrics with loss values
        """
        start_time = time.time()

        # Setup optimizer for phase
        lr = self.config.get_lr_for_phase(phase)
        if self.optimizer is None or self.optimizer.param_groups[0]["lr"] != lr:
            params = list(self.decoder.parameters())
            if self.latent_codes is not None:
                params.append(self.latent_codes)
            self.optimizer = torch.optim.AdamW(params, lr=lr)

        # Set to training mode
        self.decoder.train()
        if self.latent_codes is not None:
            self.latent_codes.requires_grad = True

        self.optimizer.zero_grad()

        # Move batch to device
        points = batch["points"].to(self.device)
        sdf_gt = batch["sdf"].to(self.device)
        shape_indices = batch["shape_idx"]

        # Get latent codes for batch
        if self.latent_codes is not None:
            z_batch = self.latent_codes[shape_indices]
        else:
            # Fallback: use encoder to generate latents
            z_batch = self.encoder(points).detach()

        # Forward pass
        sdf_pred = self.decoder(points, z_batch)

        # Mask for padding (where all points are zero)
        valid_mask = (points.abs().sum(dim=-1) > 0).unsqueeze(-1)

        # SDF loss (clamped L1/L2)
        sdf_loss_elem = torch.where(
            sdf_pred.abs() < self.config.epsilon,
            0.5 * sdf_pred ** 2 / self.config.epsilon,
            sdf_pred.abs() - 0.5 * self.config.epsilon,
        )
        sdf_loss = (sdf_loss_elem * valid_mask).sum() / valid_mask.sum()

        # Contrastive loss (if CLIP features available)
        contrastive_loss = torch.tensor(0.0, device=self.device)
        if "text_embed" in batch:
            text_embeds = batch["text_embed"].to(self.device)
            contrastive_loss, _ = self.contrastive_loss(
                z_batch,
                text_embeds,
                batch.get("image_embed").to(self.device)
                if "image_embed" in batch
                else None,
            )

        # Combined loss
        total_loss = sdf_loss + self.config.contrastive_weight * contrastive_loss

        # Backward
        total_loss.backward()

        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(
            list(self.decoder.parameters()) +
            ([self.latent_codes] if self.latent_codes is not None else []),
            max_norm=1.0,
        )

        self.optimizer.step()

        # Compute accuracy
        with torch.no_grad():
            # Binary accuracy: correct sign prediction
            pred_sign = (sdf_pred.squeeze(-1) * valid_mask.squeeze(-1)) > 0
            gt_sign = (sdf_gt.squeeze(-1) * valid_mask.squeeze(-1)) > 0
            accuracy = (pred_sign == gt_sign).float().mean().item()

        elapsed = time.time() - start_time

        return TrainingMetrics(
            epoch=self.current_epoch,
            phase=phase.value,
            loss_sdf=sdf_loss.item(),
            loss_contrastive=contrastive_loss.item(),
            loss_total=total_loss.item(),
            accuracy_inside=accuracy,
            time_seconds=elapsed,
        )

    def validate(
        self,
        val_loader: DataLoader,
    ) -> TrainingMetrics:
        """
        Validate on validation set.

        Args:
            val_loader: Validation data loader

        Returns:
            Validation metrics
        """
        self.decoder.eval()

        total_loss = 0.0
        total_accuracy = 0.0
        num_batches = 0

        with torch.no_grad():
            for batch in val_loader:
                points = batch["points"].to(self.device)
                sdf_gt = batch["sdf"].to(self.device)
                shape_indices = batch["shape_idx"]

                if self.latent_codes is not None:
                    z_batch = self.latent_codes[shape_indices]
                else:
                    z_batch = self.encoder(points).detach()

                sdf_pred = self.decoder(points, z_batch)

                valid_mask = (points.abs().sum(dim=-1) > 0).unsqueeze(-1)

                # L1 loss
                loss = (torch.abs(sdf_pred - sdf_gt) * valid_mask).sum()
                loss = loss / valid_mask.sum()

                # Accuracy
                pred_sign = (sdf_pred.squeeze(-1) * valid_mask.squeeze(-1)) > 0
                gt_sign = (sdf_gt.squeeze(-1) * valid_mask.squeeze(-1)) > 0
                accuracy = (pred_sign == gt_sign).float().mean().item()

                total_loss += loss.item()
                total_accuracy += accuracy
                num_batches += 1

        return TrainingMetrics(
            epoch=self.current_epoch,
            phase=self.current_phase.value,
            loss_sdf=total_loss / num_batches,
            loss_total=total_loss / num_batches,
            accuracy_inside=total_accuracy / num_batches,
            time_seconds=0.0,
        )

    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader | None = None,
    ) -> list[TrainingMetrics]:
        """
        Full training loop across all phases.

        Args:
            train_loader: Training data loader
            val_loader: Optional validation data loader

        Returns:
            List of metrics per epoch
        """
        all_metrics = []
        global_epoch = 0

        for phase in TrainingPhase:
            logger.info(f"Starting phase: {phase.value.upper()}")
            num_epochs = self.config.get_epochs_for_phase(phase)
            lr = self.config.get_lr_for_phase(phase)

            for epoch in range(num_epochs):
                self.current_epoch = global_epoch
                self.current_phase = phase

                epoch_metrics = []

                for batch in train_loader:
                    metrics = self.train_step(batch, phase)
                    epoch_metrics.append(metrics)

                # Average metrics for epoch
                avg_metrics = self._average_metrics(epoch_metrics)
                all_metrics.append(avg_metrics)
                self.metrics_history.append(avg_metrics)

                # Validation
                if val_loader is not None and epoch % 5 == 0:
                    val_metrics = self.validate(val_loader)
                    logger.info(
                        f"Epoch {global_epoch} [{phase.value}] "
                        f"loss={avg_metrics.loss_total:.4f} "
                        f"acc={avg_metrics.accuracy_inside:.3f} "
                        f"val_loss={val_metrics.loss_sdf:.4f} "
                        f"val_acc={val_metrics.accuracy_inside:.3f}"
                    )

                # Checkpoint
                if epoch % self.config.save_every == 0:
                    self.save_checkpoint(f"epoch_{global_epoch}")

                global_epoch += 1

        # Save final model
        self.save_checkpoint("final")
        logger.info("Training complete!")

        return all_metrics

    def _average_metrics(self, metrics: list[TrainingMetrics]) -> TrainingMetrics:
        """Average metrics across steps."""
        return TrainingMetrics(
            epoch=metrics[0].epoch,
            phase=metrics[0].phase,
            loss_sdf=sum(m.loss_sdf for m in metrics) / len(metrics),
            loss_contrastive=sum(m.loss_contrastive for m in metrics) / len(metrics),
            loss_total=sum(m.loss_total for m in metrics) / len(metrics),
            accuracy_inside=sum(m.accuracy_inside for m in metrics) / len(metrics),
            time_seconds=sum(m.time_seconds for m in metrics),
        )

    def save_checkpoint(self, name: str) -> None:
        """
        Save training checkpoint.

        Args:
            name: Checkpoint name (e.g., "epoch_50", "final")
        """
        path = Path(self.config.checkpoint_dir) / f"{name}.pt"

        checkpoint = {
            "epoch": self.current_epoch,
            "phase": self.current_phase.value,
            "decoder_state": self.decoder.state_dict(),
            "encoder_state": self.encoder.state_dict(),
            "config": self.config.__dict__,
            "metrics": [m.to_dict() for m in self.metrics_history],
        }

        if self.latent_codes is not None:
            checkpoint["latent_codes"] = self.latent_codes.data.cpu()

        torch.save(checkpoint, path)
        logger.info(f"Saved checkpoint to {path}")

    def load_checkpoint(self, name: str) -> None:
        """
        Load training checkpoint.

        Args:
            name: Checkpoint name
        """
        path = Path(self.config.checkpoint_dir) / f"{name}.pt"

        if not path.exists():
            logger.warning(f"Checkpoint {path} not found")
            return

        checkpoint = torch.load(path, map_location=self.device)

        self.decoder.load_state_dict(checkpoint["decoder_state"])
        self.encoder.load_state_dict(checkpoint["encoder_state"])
        self.current_epoch = checkpoint["epoch"]
        self.current_phase = TrainingPhase(checkpoint["phase"])

        if "latent_codes" in checkpoint:
            self.latent_codes = nn.Parameter(
                checkpoint["latent_codes"].to(self.device)
            )

        logger.info(f"Loaded checkpoint from {path}")

    def save_for_inference(self, path: str) -> None:
        """
        Save model for inference (no training state).

        Args:
            path: Output path for model
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        torch.save(
            {
                "decoder": self.decoder.state_dict(),
                "encoder": self.encoder.state_dict(),
                "latent_dim": self.config.latent_dim,
            },
            path,
        )
        logger.info(f"Saved inference model to {path}")

    @staticmethod
    def load_for_inference(path: str, device: str = "cpu") -> tuple:
        """
        Load model for inference.

        Args:
            path: Path to saved model
            device: Device to load to

        Returns:
            (decoder, encoder) tuple
        """
        checkpoint = torch.load(path, map_location=device)

        latent_dim = checkpoint.get("latent_dim", 256)

        decoder = EngineeringPartSDF(latent_dim=latent_dim).to(device)
        encoder = DeepSDFEncoder(output_dim=latent_dim).to(device)

        decoder.load_state_dict(checkpoint["decoder"])
        encoder.load_state_dict(checkpoint["encoder"])

        decoder.eval()
        encoder.eval()

        return decoder, encoder

    def export_latents(
        self,
        shape_indices: list[int] | None = None,
        output_path: str | None = None,
    ) -> dict[str, np.ndarray]:
        """
        Export learned latent codes.

        Args:
            shape_indices: Optional subset of indices to export
            output_path: Optional JSON output path

        Returns:
            Dict mapping shape_id to latent vector
        """
        if self.latent_codes is None:
            logger.warning("No latent codes to export")
            return {}

        latents = self.latent_codes.data.cpu().numpy()

        if shape_indices is not None:
            latents = latents[shape_indices]

        result = {
            f"shape_{i}": latents[i].tolist()
            for i in range(len(latents))
        }

        if output_path:
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2)

        return result
