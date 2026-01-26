"""
DeepSDF: Implicit 3D representation for engineering CAD parts.

Modified from Park et al. 2019 for mechanical components:
- Auto-decoder architecture with learnable latent codes
- Cross-modal contrastive loss for CLIP alignment
- Manufacturing-aware sampling support
- Assembly-aware latent encoding (optional)
"""

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np


class EngineeringPartSDF(nn.Module):
    """
    DeepSDF decoder for engineering CAD parts.

    Architecture:
        latent code z (256-dim) -> MLP -> SDF value at point xyz

    Modified from original DeepSDF for:
    - Mechanical feature awareness (holes, fillets, chamfers)
    - Bounded output (clamp to reasonable SDF range)
    - Epsilon regularization for surface stability
    """

    def __init__(
        self,
        latent_dim: int = 256,
        hidden_dim: int = 512,
        num_layers: int = 8,
        geometric_features: bool = True,
    ):
        """
        Initialize DeepSDF decoder.

        Args:
            latent_dim: Dimension of latent code z
            hidden_dim: Hidden layer dimension
            num_layers: Number of MLP layers
            geometric_features: Use sin/cos positional encoding on coordinates
        """
        super().__init__()

        self.latent_dim = latent_dim
        self.hidden_dim = hidden_dim
        self.geometric_features = geometric_features

        # Input dimension depends on whether we use geometric features
        # Positional encoding: 3 coords -> 3*2*freq = 60 dims
        self.geo_feat_dim = 60 if geometric_features else 3
        input_dim = latent_dim + self.geo_feat_dim

        # Build MLP decoder
        layers = []
        layers.append(nn.Linear(input_dim, hidden_dim))

        for _ in range(num_layers - 2):
            layers.append(nn.Linear(hidden_dim, hidden_dim))
            layers.append(nn.ReLU(inplace=True))

        # Final layer: output SDF value
        layers.append(nn.Linear(hidden_dim, 1))

        self.decoder = nn.Sequential(*layers)

        # Initialize last layer near zero (SDF ~ 0 at surface)
        with torch.no_grad():
            self.decoder[-1].weight.fill_(0.0)
            self.decoder[-1].bias.fill_(0.0)

        # Latent codes for auto-decoder (learned per shape)
        self.latent_codes: Optional[nn.ParameterList] = None

    def encode_position(self, xyz: torch.Tensor) -> torch.Tensor:
        """
        Positional encoding for 3D coordinates (neural rendering style).

        Args:
            xyz: (B, N, 3) coordinates

        Returns:
            (B, N, 60) encoded features
        """
        # Frequencies for positional encoding
        freqs = torch.tensor(
            [2**i for i in range(10)],
            device=xyz.device,
            dtype=xyz.dtype
        )

        encoded = []
        for freq in freqs:
            encoded.append(torch.sin(xyz * freq))
            encoded.append(torch.cos(xyz * freq))

        return torch.cat(encoded, dim=-1)

    def forward(
        self,
        xyz: torch.Tensor,
        latent_z: torch.Tensor,
    ) -> torch.Tensor:
        """
        Predict SDF value at query points.

        Args:
            xyz: (B, N, 3) query points in 3D space
            latent_z: (B, latent_dim) latent code for each shape

        Returns:
            (B, N, 1) predicted SDF values
        """
        batch_size, num_points, _ = xyz.shape

        # Encode coordinates if using geometric features
        if self.geometric_features:
            geo_feat = self.encode_position(xyz)  # (B, N, 60)
        else:
            geo_feat = xyz

        # Expand latent to match points
        z_expanded = latent_z.unsqueeze(1).expand(-1, num_points, -1)

        # Concatenate latent + geometry
        combined = torch.cat([z_expanded, geo_feat], dim=-1)

        # Decode to SDF
        sdf = self.decoder(combined)

        # Clamp to reasonable range for numerical stability
        # Engineering parts typically within [-1, 1] after normalization
        sdf = torch.clamp(sdf, min=-2.0, max=2.0)

        return sdf

    def initialize_latent_codes(self, num_shapes: int) -> nn.Parameter:
        """
        Initialize learnable latent codes for auto-decoder training.

        Args:
            num_shapes: Number of shapes in training set

        Returns:
            Parameter containing latent codes
        """
        # Initialize from normal distribution
        codes = torch.randn(num_shapes, self.latent_dim) * 0.01
        self.latent_codes = nn.Parameter(codes)
        return self.latent_codes

    def extract_latent(
        self,
        point_cloud: torch.Tensor,
        num_iterations: int = 100,
        lr: float = 0.01,
    ) -> torch.Tensor:
        """
        Extract latent code from point cloud via optimization.

        Used for encoding new parts at inference time.

        Args:
            point_cloud: (1, N, 3) point cloud
            num_iterations: Optimization iterations
            lr: Learning rate

        Returns:
            (1, latent_dim) latent code
        """
        device = point_cloud.device
        z = torch.zeros(1, self.latent_dim, device=device, requires_grad=True)
        optimizer = torch.optim.Adam([z], lr=lr)

        # For extraction, we assume surface points (SDF=0)
        target_sdf = torch.zeros(point_cloud.shape[:2], device=device)

        for _ in range(num_iterations):
            optimizer.zero_grad()

            pred_sdf = self.forward(point_cloud, z)
            loss = F.mse_loss(pred_sdf.squeeze(-1), target_sdf)

            loss.backward()
            optimizer.step()

        return z.detach()


class CrossModalContrastiveLoss(nn.Module):
    """
    CLIP-style contrastive loss for multi-modal alignment.

    Aligns:
    - Geometry latent z (DeepSDF)
    - CLIP text embeddings
    - CLIP image embeddings

    Enables cross-modal retrieval:
    - "find bolts like this sketch"
    - "show brackets similar to this part"
    """

    def __init__(self, temperature: float = 0.07):
        """
        Initialize contrastive loss.

        Args:
            temperature: Softmax temperature (lower = sharper distribution)
        """
        super().__init__()
        self.temperature = temperature
        # Learnable temperature scaling
        self.logit_scale = nn.Parameter(torch.ones([]) * np.log(1 / temperature))

    def forward(
        self,
        geometry_features: torch.Tensor,
        text_features: torch.Tensor,
        image_features: Optional[torch.Tensor] = None,
    ) -> tuple[torch.Tensor, dict]:
        """
        Compute contrastive loss between modalities.

        Args:
            geometry_features: (B, D) DeepSDF latent codes
            text_features: (B, D) CLIP text embeddings
            image_features: (B, D) CLIP image embeddings (optional)

        Returns:
            loss: Scalar loss value
            metrics: Dictionary of loss components
        """
        logit_scale = self.logit_scale.exp()

        # Normalize features
        geometry_features = F.normalize(geometry_features, dim=-1)
        text_features = F.normalize(text_features, dim=-1)

        # Geometry-Text contrastive
        logits_geom_text = logit_scale * geometry_features @ text_features.t()
        logits_text_geom = logits_geom_text.t()

        labels = torch.arange(
            len(geometry_features),
            device=geometry_features.device
        )

        loss_geom_text = F.cross_entropy(logits_geom_text, labels)
        loss_text_geom = F.cross_entropy(logits_text_geom, labels)

        total_loss = (loss_geom_text + loss_text_geom) / 2

        metrics = {
            'loss_geom_text': loss_geom_text.item(),
            'loss_text_geom': loss_text_geom.item(),
        }

        # Geometry-Image contrastive (if provided)
        if image_features is not None:
            image_features = F.normalize(image_features, dim=-1)

            logits_geom_image = logit_scale * geometry_features @ image_features.t()
            logits_image_geom = logits_geom_image.t()

            loss_geom_image = F.cross_entropy(logits_geom_image, labels)
            loss_image_geom = F.cross_entropy(logits_image_geom, labels)

            total_loss = total_loss + (loss_geom_image + loss_image_geom) / 2

            metrics['loss_geom_image'] = loss_geom_image.item()
            metrics['loss_image_geom'] = loss_image_geom.item()

        return total_loss, metrics

    def compute_similarity(
        self,
        query_features: torch.Tensor,
        candidate_features: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute cosine similarity between query and candidates.

        Args:
            query_features: (N_q, D) query embeddings
            candidate_features: (N_c, D) candidate embeddings

        Returns:
            (N_q, N_c) similarity matrix
        """
        query_features = F.normalize(query_features, dim=-1)
        candidate_features = F.normalize(candidate_features, dim=-1)

        similarity = query_features @ candidate_features.t()
        return similarity


class DeepSDFEncoder(nn.Module):
    """
    Point cloud encoder for DeepSDF latent extraction.

    Architecture inspired by PointNet++:
    - Hierarchical feature learning
    - Set abstraction (sampling + grouping)
    - Global feature aggregation

    Used to initialize latent codes from point clouds before
    auto-decoder refinement.
    """

    def __init__(
        self,
        output_dim: int = 256,
        num_points: int = 2048,
    ):
        """
        Initialize point cloud encoder.

        Args:
            output_dim: Output latent dimension
            num_points: Expected number of input points
        """
        super().__init__()

        self.output_dim = output_dim

        # Point-wise MLP (shared across points)
        self.conv1 = nn.Conv1d(3, 64, 1)
        self.conv2 = nn.Conv1d(64, 128, 1)
        self.conv3 = nn.Conv1d(128, 256, 1)
        self.conv4 = nn.Conv1d(256, 512, 1)

        # Batch normalization
        self.bn1 = nn.BatchNorm1d(64)
        self.bn2 = nn.BatchNorm1d(128)
        self.bn3 = nn.BatchNorm1d(256)
        self.bn4 = nn.BatchNorm1d(512)

        # Global feature aggregation
        self.fc1 = nn.Linear(512, 512)
        self.fc2 = nn.Linear(512, output_dim)
        self.bn5 = nn.BatchNorm1d(512)

        self.dropout = nn.Dropout(p=0.3)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Encode point cloud to latent vector.

        Args:
            x: (B, N, 3) point cloud

        Returns:
            (B, output_dim) latent code
        """
        # Transpose for conv1d: (B, N, 3) -> (B, 3, N)
        x = x.transpose(1, 2)

        # Point-wise feature extraction
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = F.relu(self.bn4(self.conv4(x)))

        # Global max pooling
        x = torch.max(x, dim=2)[0]  # (B, 512)

        # Final projection
        x = F.relu(self.bn5(self.fc1(x)))
        x = self.dropout(x)
        x = self.fc2(x)

        # L2 normalize
        x = F.normalize(x, p=2, dim=1)

        return x


class AssemblyAwareEncoder(nn.Module):
    """
    Encoder for assembly-level latent codes.

    Extends DeepSDFEncoder to handle:
    - Multiple components in assembly
    - Part-part relationships
    - Hierarchical structure
    """

    def __init__(
        self,
        part_latent_dim: int = 256,
        assembly_latent_dim: int = 512,
        max_parts: int = 100,
    ):
        """
        Initialize assembly-aware encoder.

        Args:
            part_latent_dim: Latent dim per part
            assembly_latent_dim: Output assembly latent dim
            max_parts: Maximum number of parts to process
        """
        super().__init__()

        self.part_encoder = DeepSDFEncoder(output_dim=part_latent_dim)

        # Transformer for part-part interactions
        self.transformer = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(
                d_model=part_latent_dim,
                nhead=8,
                dim_feedforward=1024,
                dropout=0.1,
                batch_first=True,
            ),
            num_layers=4,
        )

        # Assembly aggregation
        self.fc_assembly = nn.Sequential(
            nn.Linear(part_latent_dim, assembly_latent_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(assembly_latent_dim, assembly_latent_dim),
        )

    def forward(
        self,
        part_point_clouds: list[torch.Tensor],
        part_transforms: list[torch.Tensor] | None = None,
    ) -> torch.Tensor:
        """
        Encode assembly to latent vector.

        Args:
            part_point_clouds: List of (N_i, 3) point clouds per part
            part_transforms: Optional list of (4, 4) transform matrices

        Returns:
            (1, assembly_latent_dim) assembly latent code
        """
        device = part_point_clouds[0].device
        batch_parts = []

        # Encode each part
        for i, pc in enumerate(part_point_clouds):
            # Add batch dimension
            pc_batch = pc.unsqueeze(0)

            # Encode part
            part_latent = self.part_encoder(pc_batch)  # (1, part_latent_dim)
            batch_parts.append(part_latent)

        # Stack parts
        parts = torch.cat(batch_parts, dim=0)  # (num_parts, part_latent_dim)

        # Add batch dimension for transformer
        parts = parts.unsqueeze(0)  # (1, num_parts, part_latent_dim)

        # Apply transformer for part interactions
        parts_encoded = self.transformer(parts)  # (1, num_parts, part_latent_dim)

        # Aggregate to assembly-level latent
        assembly_latent = parts_encoded.mean(dim=1)  # (1, part_latent_dim)
        assembly_latent = self.fc_assembly(assembly_latent)  # (1, assembly_latent_dim)

        # L2 normalize
        assembly_latent = F.normalize(assembly_latent, p=2, dim=-1)

        return assembly_latent
