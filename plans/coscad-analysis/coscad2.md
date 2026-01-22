I'll continue with the 3D geometry encoder, view rendering pipeline, and deeper integration with your Pro/TOOLKIT extraction system.

```python
# cad_retrieval/geometry_encoder.py
"""
3D Geometry Encoder for CAD models.
Trained with contrastive loss to align with CLIP embeddings.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple
import numpy as np


class PointNetEncoder(nn.Module):
    """
    PointNet++ inspired encoder for CAD geometry.
    Maps point clouds to 512-dim embeddings aligned with CLIP space.
    """
    
    def __init__(self, output_dim: int = 512):
        super().__init__()
        
        # Point-wise MLP (shared weights across points)
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
        Args:
            x: Point cloud tensor of shape (B, N, 3)
            
        Returns:
            Embedding tensor of shape (B, output_dim)
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
        
        # L2 normalize for cosine similarity
        x = F.normalize(x, p=2, dim=1)
        
        return x


class DGCNNEncoder(nn.Module):
    """
    Dynamic Graph CNN encoder for CAD geometry.
    Better at capturing local geometric structures than PointNet.
    """
    
    def __init__(self, output_dim: int = 512, k: int = 20):
        super().__init__()
        self.k = k
        
        # EdgeConv layers
        self.conv1 = nn.Sequential(
            nn.Conv2d(6, 64, 1, bias=False),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.2)
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(128, 64, 1, bias=False),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.2)
        )
        self.conv3 = nn.Sequential(
            nn.Conv2d(128, 128, 1, bias=False),
            nn.BatchNorm2d(128),
            nn.LeakyReLU(0.2)
        )
        self.conv4 = nn.Sequential(
            nn.Conv2d(256, 256, 1, bias=False),
            nn.BatchNorm2d(256),
            nn.LeakyReLU(0.2)
        )
        
        # Global feature
        self.conv5 = nn.Sequential(
            nn.Conv1d(512, 1024, 1, bias=False),
            nn.BatchNorm1d(1024),
            nn.LeakyReLU(0.2)
        )
        
        # Output projection
        self.fc = nn.Sequential(
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.5),
            nn.Linear(512, output_dim)
        )
        
    def knn(self, x: torch.Tensor) -> torch.Tensor:
        """Compute k-nearest neighbors."""
        inner = -2 * torch.matmul(x.transpose(2, 1), x)
        xx = torch.sum(x ** 2, dim=1, keepdim=True)
        pairwise_distance = -xx - inner - xx.transpose(2, 1)
        idx = pairwise_distance.topk(k=self.k, dim=-1)[1]
        return idx
    
    def get_graph_feature(self, x: torch.Tensor, idx: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Get edge features for graph convolution."""
        batch_size, num_dims, num_points = x.size()
        
        if idx is None:
            idx = self.knn(x)
            
        idx_base = torch.arange(0, batch_size, device=x.device).view(-1, 1, 1) * num_points
        idx = idx + idx_base
        idx = idx.view(-1)
        
        x = x.transpose(2, 1).contiguous()
        feature = x.view(batch_size * num_points, -1)[idx, :]
        feature = feature.view(batch_size, num_points, self.k, num_dims)
        x = x.view(batch_size, num_points, 1, num_dims).repeat(1, 1, self.k, 1)
        feature = torch.cat((feature - x, x), dim=3).permute(0, 3, 1, 2).contiguous()
        
        return feature
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Point cloud tensor of shape (B, N, 3)
            
        Returns:
            Embedding tensor of shape (B, output_dim)
        """
        x = x.transpose(1, 2)  # (B, 3, N)
        batch_size = x.size(0)
        
        # EdgeConv layers with dynamic graph
        x1 = self.conv1(self.get_graph_feature(x))
        x1 = x1.max(dim=-1)[0]
        
        x2 = self.conv2(self.get_graph_feature(x1))
        x2 = x2.max(dim=-1)[0]
        
        x3 = self.conv3(self.get_graph_feature(x2))
        x3 = x3.max(dim=-1)[0]
        
        x4 = self.conv4(self.get_graph_feature(x3))
        x4 = x4.max(dim=-1)[0]
        
        # Concatenate multi-scale features
        x = torch.cat((x1, x2, x3, x4), dim=1)
        x = self.conv5(x)
        
        # Global pooling
        x = x.max(dim=-1)[0]
        
        # Output projection
        x = self.fc(x)
        x = F.normalize(x, p=2, dim=1)
        
        return x


# ============================================================================
# CONTRASTIVE TRAINING FOR CROSS-MODAL ALIGNMENT
# ============================================================================

class CrossModalContrastiveLoss(nn.Module):
    """
    CLIP-style contrastive loss for aligning 3D geometry with text/image embeddings.
    """
    
    def __init__(self, temperature: float = 0.07):
        super().__init__()
        self.temperature = temperature
        self.logit_scale = nn.Parameter(torch.ones([]) * np.log(1 / temperature))
        
    def forward(
        self,
        geometry_features: torch.Tensor,
        text_features: torch.Tensor,
        image_features: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, dict]:
        """
        Compute contrastive loss between modalities.
        
        Args:
            geometry_features: (B, D) 3D geometry embeddings
            text_features: (B, D) text embeddings (from CLIP)
            image_features: (B, D) image embeddings (from CLIP), optional
            
        Returns:
            loss: Scalar loss value
            metrics: Dictionary of loss components
        """
        logit_scale = self.logit_scale.exp()
        
        # Geometry-Text contrastive
        logits_geom_text = logit_scale * geometry_features @ text_features.t()
        logits_text_geom = logits_geom_text.t()
        
        labels = torch.arange(len(geometry_features), device=geometry_features.device)
        
        loss_geom_text = F.cross_entropy(logits_geom_text, labels)
        loss_text_geom = F.cross_entropy(logits_text_geom, labels)
        
        total_loss = (loss_geom_text + loss_text_geom) / 2
        
        metrics = {
            'loss_geom_text': loss_geom_text.item(),
            'loss_text_geom': loss_text_geom.item()
        }
        
        # Geometry-Image contrastive (if provided)
        if image_features is not None:
            logits_geom_image = logit_scale * geometry_features @ image_features.t()
            logits_image_geom = logits_geom_image.t()
            
            loss_geom_image = F.cross_entropy(logits_geom_image, labels)
            loss_image_geom = F.cross_entropy(logits_image_geom, labels)
            
            total_loss = total_loss + (loss_geom_image + loss_image_geom) / 2
            
            metrics['loss_geom_image'] = loss_geom_image.item()
            metrics['loss_image_geom'] = loss_image_geom.item()
        
        return total_loss, metrics


class GeometryEncoderTrainer:
    """
    Trainer for aligning 3D geometry encoder with CLIP embeddings.
    """
    
    def __init__(
        self,
        geometry_encoder: nn.Module,
        clip_model,
        learning_rate: float = 1e-4,
        device: str = "cuda"
    ):
        self.geometry_encoder = geometry_encoder.to(device)
        self.clip_model = clip_model.to(device)
        self.device = device
        
        # Freeze CLIP - we only train geometry encoder
        for param in self.clip_model.parameters():
            param.requires_grad = False
            
        self.optimizer = torch.optim.AdamW(
            self.geometry_encoder.parameters(),
            lr=learning_rate,
            weight_decay=0.01
        )
        
        self.loss_fn = CrossModalContrastiveLoss()
        self.loss_fn.to(device)
        
    def train_step(
        self,
        point_clouds: torch.Tensor,
        texts: list,
        images: Optional[torch.Tensor] = None
    ) -> dict:
        """
        Single training step.
        
        Args:
            point_clouds: (B, N, 3) point cloud batch
            texts: List of B text descriptions
            images: (B, 3, H, W) rendered view batch, optional
        """
        self.geometry_encoder.train()
        self.optimizer.zero_grad()
        
        # Encode geometry
        geometry_features = self.geometry_encoder(point_clouds.to(self.device))
        
        # Encode text with frozen CLIP
        import clip
        text_tokens = clip.tokenize(texts, truncate=True).to(self.device)
        with torch.no_grad():
            text_features = self.clip_model.encode_text(text_tokens)
            text_features = F.normalize(text_features.float(), dim=-1)
        
        # Encode images with frozen CLIP (if provided)
        image_features = None
        if images is not None:
            with torch.no_grad():
                image_features = self.clip_model.encode_image(images.to(self.device))
                image_features = F.normalize(image_features.float(), dim=-1)
        
        # Compute loss
        loss, metrics = self.loss_fn(geometry_features, text_features, image_features)
        
        # Backward
        loss.backward()
        self.optimizer.step()
        
        metrics['total_loss'] = loss.item()
        return metrics
```

Now the view rendering pipeline for generating training data and indexing:

```python
# cad_retrieval/view_renderer.py
"""
Automated view rendering for CAD models.
Generates canonical views for image-based retrieval indexing.
"""

import asyncio
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
import tempfile
import subprocess


@dataclass
class ViewConfig:
    """Configuration for a rendered view."""
    name: str
    azimuth: float  # Degrees
    elevation: float  # Degrees
    distance_factor: float = 2.5  # Multiple of bounding box diagonal
    resolution: Tuple[int, int] = (512, 512)
    background: str = "white"
    render_edges: bool = True
    render_surfaces: bool = True


# Standard view configurations (like CosCAD's canonical views)
CANONICAL_VIEWS = [
    ViewConfig("front", azimuth=0, elevation=0),
    ViewConfig("back", azimuth=180, elevation=0),
    ViewConfig("left", azimuth=90, elevation=0),
    ViewConfig("right", azimuth=-90, elevation=0),
    ViewConfig("top", azimuth=0, elevation=90),
    ViewConfig("bottom", azimuth=0, elevation=-90),
    ViewConfig("iso_front_right", azimuth=-45, elevation=30),
    ViewConfig("iso_front_left", azimuth=45, elevation=30),
    ViewConfig("iso_back_right", azimuth=-135, elevation=30),
    ViewConfig("iso_back_left", azimuth=135, elevation=30),
]


class CreoViewRenderer:
    """
    Render views from Creo models using Pro/TOOLKIT or Creo View API.
    Integrates with your existing gRPC service.
    """
    
    def __init__(self, creo_client, output_dir: Path):
        """
        Args:
            creo_client: Your existing gRPC client to Creo
            output_dir: Directory to save rendered images
        """
        self.creo = creo_client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def render_canonical_views(
        self,
        model_path: str,
        genome_id: str,
        views: List[ViewConfig] = CANONICAL_VIEWS
    ) -> List[dict]:
        """
        Render all canonical views of a model.
        
        Returns:
            List of dicts with view metadata and paths
        """
        results = []
        
        # Open model in Creo
        model = await self.creo.open_model(model_path)
        
        # Get bounding box for camera positioning
        bbox = await self.creo.get_bounding_box(model)
        diagonal = np.linalg.norm(
            np.array(bbox['max']) - np.array(bbox['min'])
        )
        
        for view in views:
            output_path = self.output_dir / genome_id / f"{view.name}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Calculate camera position
            camera_distance = diagonal * view.distance_factor
            camera_pos = self._spherical_to_cartesian(
                camera_distance,
                np.radians(view.azimuth),
                np.radians(view.elevation)
            )
            
            # Render via Creo
            await self.creo.set_view_orientation(
                model,
                camera_position=camera_pos,
                look_at=[0, 0, 0],
                up_vector=[0, 0, 1]
            )
            
            await self.creo.render_to_image(
                model,
                str(output_path),
                width=view.resolution[0],
                height=view.resolution[1],
                background=view.background,
                show_edges=view.render_edges,
                show_surfaces=view.render_surfaces
            )
            
            results.append({
                'view_name': view.name,
                'path': str(output_path),
                'azimuth': view.azimuth,
                'elevation': view.elevation,
                'resolution': view.resolution
            })
            
        return results
    
    def _spherical_to_cartesian(
        self,
        r: float,
        azimuth: float,
        elevation: float
    ) -> List[float]:
        """Convert spherical coordinates to Cartesian."""
        x = r * np.cos(elevation) * np.cos(azimuth)
        y = r * np.cos(elevation) * np.sin(azimuth)
        z = r * np.sin(elevation)
        return [x, y, z]


class OfflineViewRenderer:
    """
    Render views using Open3D or PyVista for offline processing.
    Useful when Creo is not available.
    """
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def render_from_mesh(
        self,
        mesh_path: str,
        genome_id: str,
        views: List[ViewConfig] = CANONICAL_VIEWS
    ) -> List[dict]:
        """Render views from STL/OBJ mesh file."""
        import pyvista as pv
        
        # Load mesh
        mesh = pv.read(mesh_path)
        
        # Center and normalize
        mesh.points -= mesh.center
        scale = np.max(np.abs(mesh.points))
        mesh.points /= scale
        
        results = []
        
        for view in views:
            output_path = self.output_dir / genome_id / f"{view.name}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create plotter
            plotter = pv.Plotter(off_screen=True)
            plotter.add_mesh(
                mesh,
                color='lightgray',
                show_edges=view.render_edges,
                edge_color='black',
                line_width=0.5
            )
            
            # Set camera position
            camera_distance = view.distance_factor
            camera_pos = self._spherical_to_cartesian(
                camera_distance,
                np.radians(view.azimuth),
                np.radians(view.elevation)
            )
            
            plotter.camera_position = [
                camera_pos,
                [0, 0, 0],
                [0, 0, 1]
            ]
            
            plotter.set_background(view.background)
            plotter.window_size = view.resolution
            
            # Render
            plotter.screenshot(str(output_path))
            plotter.close()
            
            results.append({
                'view_name': view.name,
                'path': str(output_path),
                'azimuth': view.azimuth,
                'elevation': view.elevation,
                'resolution': view.resolution
            })
            
        return results
    
    def _spherical_to_cartesian(self, r, azimuth, elevation):
        x = r * np.cos(elevation) * np.cos(azimuth)
        y = r * np.cos(elevation) * np.sin(azimuth)
        z = r * np.sin(elevation)
        return [x, y, z]


class PointCloudExtractor:
    """
    Extract point clouds from CAD models for geometry encoding.
    """
    
    def __init__(self, num_points: int = 2048):
        self.num_points = num_points
        
    def from_mesh(self, mesh_path: str) -> np.ndarray:
        """Sample point cloud from mesh surface."""
        import trimesh
        
        mesh = trimesh.load(mesh_path)
        
        # Sample points uniformly on surface
        points, _ = trimesh.sample.sample_surface(mesh, self.num_points)
        
        # Normalize to unit sphere
        centroid = points.mean(axis=0)
        points -= centroid
        scale = np.max(np.linalg.norm(points, axis=1))
        points /= scale
        
        return points.astype(np.float32)
    
    def from_creo_tessellation(self, tessellation_data: bytes) -> np.ndarray:
        """
        Extract point cloud from Creo tessellation data.
        Assumes your gRPC service can export tessellation.
        """
        # Parse tessellation format (STL binary or custom format)
        # This depends on how you're exporting from Pro/TOOLKIT
        
        # Example for STL binary format
        import struct
        import io
        
        buffer = io.BytesIO(tessellation_data)
        
        # Skip header
        buffer.read(80)
        
        # Read number of triangles
        num_triangles = struct.unpack('<I', buffer.read(4))[0]
        
        # Read vertices
        vertices = []
        for _ in range(num_triangles):
            buffer.read(12)  # Skip normal
            for _ in range(3):
                v = struct.unpack('<fff', buffer.read(12))
                vertices.append(v)
            buffer.read(2)  # Skip attribute
        
        points = np.array(vertices, dtype=np.float32)
        
        # Remove duplicates and sample
        points = np.unique(points, axis=0)
        
        if len(points) > self.num_points:
            indices = np.random.choice(len(points), self.num_points, replace=False)
            points = points[indices]
        elif len(points) < self.num_points:
            # Upsample by adding jittered points
            shortage = self.num_points - len(points)
            indices = np.random.choice(len(points), shortage, replace=True)
            jitter = np.random.normal(0, 0.01, (shortage, 3))
            extra_points = points[indices] + jitter
            points = np.vstack([points, extra_points])
        
        # Normalize
        centroid = points.mean(axis=0)
        points -= centroid
        scale = np.max(np.linalg.norm(points, axis=1))
        points /= scale
        
        return points
```

Now let's integrate everything into your existing pipeline:

```python
# cad_retrieval/indexing_pipeline.py
"""
Complete indexing pipeline for CAD models.
Integrates with your Creo genome extraction system.
"""

import asyncio
from pathlib import Path
from typing import Optional, List
import asyncpg
import numpy as np
from dataclasses import dataclass

from .coscad_retriever import CosCADRetriever
from .view_renderer import (
    CreoViewRenderer, 
    OfflineViewRenderer, 
    PointCloudExtractor,
    CANONICAL_VIEWS
)
from .geometry_encoder import DGCNNEncoder


@dataclass
class IndexingResult:
    genome_id: str
    model_name: str
    num_views_rendered: int
    has_geometry_embedding: bool
    has_text_embedding: bool
    has_image_embedding: bool
    errors: List[str]


class CADIndexingPipeline:
    """
    End-to-end pipeline for indexing CAD models into the retrieval system.
    
    Flow:
    1. Extract genome from Creo model (your existing code)
    2. Generate description for text embedding
    3. Render canonical views for image embedding
    4. Extract point cloud for geometry embedding
    5. Compute and store all embeddings
    6. Upload rendered views to Backblaze B2
    """
    
    def __init__(
        self,
        database_url: str,
        creo_client,  # Your existing gRPC client
        b2_client,    # Your Backblaze B2 client
        render_output_dir: Path,
        device: str = "cuda"
    ):
        self.database_url = database_url
        self.creo = creo_client
        self.b2 = b2_client
        self.render_dir = Path(render_output_dir)
        self.device = device
        
        # Initialize components
        self.retriever = CosCADRetriever(database_url, device=device)
        self.creo_renderer = CreoViewRenderer(creo_client, render_output_dir)
        self.offline_renderer = OfflineViewRenderer(render_output_dir)
        self.point_cloud_extractor = PointCloudExtractor(num_points=2048)
        
        # Load geometry encoder (pre-trained)
        self.geometry_encoder = DGCNNEncoder(output_dim=512)
        self._load_geometry_encoder_weights()
        
        self.pool: Optional[asyncpg.Pool] = None
        
    def _load_geometry_encoder_weights(self):
        """Load pre-trained geometry encoder weights."""
        import torch
        
        weights_path = Path(__file__).parent / "weights" / "dgcnn_clip_aligned.pt"
        if weights_path.exists():
            self.geometry_encoder.load_state_dict(
                torch.load(weights_path, map_location=self.device)
            )
        self.geometry_encoder.to(self.device)
        self.geometry_encoder.eval()
        
    async def initialize(self):
        """Initialize all connections."""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=5,
            max_size=20
        )
        await self.retriever.initialize()
        
    async def close(self):
        """Clean up connections."""
        if self.pool:
            await self.pool.close()
        await self.retriever.close()
        
    async def index_model(
        self,
        model_path: str,
        genome_id: Optional[str] = None,
        description: Optional[str] = None,
        use_creo_rendering: bool = True
    ) -> IndexingResult:
        """
        Index a single CAD model.
        
        Args:
            model_path: Path to .prt or .asm file
            genome_id: Existing genome ID, or None to extract new
            description: Text description, or None to auto-generate
            use_creo_rendering: Use Creo for rendering (vs offline mesh rendering)
        """
        errors = []
        
        # Step 1: Extract or load genome
        if genome_id is None:
            try:
                genome_result = await self._extract_genome(model_path)
                genome_id = genome_result['genome_id']
                model_name = genome_result['model_name']
            except Exception as e:
                return IndexingResult(
                    genome_id="",
                    model_name=Path(model_path).stem,
                    num_views_rendered=0,
                    has_geometry_embedding=False,
                    has_text_embedding=False,
                    has_image_embedding=False,
                    errors=[f"Genome extraction failed: {e}"]
                )
        else:
            model_name = await self._get_model_name(genome_id)
        
        # Step 2: Generate description if not provided
        if description is None:
            try:
                description = await self._generate_description(genome_id)
            except Exception as e:
                errors.append(f"Description generation failed: {e}")
                description = model_name  # Fallback to model name
        
        # Step 3: Render views
        rendered_views = []
        try:
            if use_creo_rendering:
                rendered_views = await self.creo_renderer.render_canonical_views(
                    model_path, genome_id
                )
            else:
                # Export mesh first, then render offline
                mesh_path = await self._export_mesh(model_path, genome_id)
                rendered_views = self.offline_renderer.render_from_mesh(
                    mesh_path, genome_id
                )
        except Exception as e:
            errors.append(f"View rendering failed: {e}")
        
        # Step 4: Upload views to B2
        view_urls = []
        for view in rendered_views:
            try:
                url = await self._upload_to_b2(
                    view['path'],
                    f"cad-views/{genome_id}/{view['view_name']}.png"
                )
                view_urls.append(url)
            except Exception as e:
                errors.append(f"B2 upload failed for {view['view_name']}: {e}")
        
        # Step 5: Extract point cloud
        point_cloud = None
        try:
            tessellation = await self.creo.get_tessellation(model_path)
            point_cloud = self.point_cloud_extractor.from_creo_tessellation(
                tessellation
            )
        except Exception as e:
            errors.append(f"Point cloud extraction failed: {e}")
        
        # Step 6: Compute and store embeddings
        try:
            await self.retriever.index_model(
                genome_id=genome_id,
                description=description,
                rendered_views=[v['path'] for v in rendered_views] if rendered_views else None,
                point_cloud=point_cloud
            )
        except Exception as e:
            errors.append(f"Embedding indexing failed: {e}")
        
        # Step 7: Store view metadata
        if rendered_views:
            await self._store_view_metadata(genome_id, rendered_views, view_urls)
        
        return IndexingResult(
            genome_id=genome_id,
            model_name=model_name,
            num_views_rendered=len(rendered_views),
            has_geometry_embedding=point_cloud is not None,
            has_text_embedding=description is not None,
            has_image_embedding=len(rendered_views) > 0,
            errors=errors
        )
    
    async def index_batch(
        self,
        model_paths: List[str],
        concurrency: int = 4
    ) -> List[IndexingResult]:
        """Index multiple models concurrently."""
        semaphore = asyncio.Semaphore(concurrency)
        
        async def index_with_semaphore(path):
            async with semaphore:
                return await self.index_model(path)
        
        tasks = [index_with_semaphore(path) for path in model_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for path, result in zip(model_paths, results):
            if isinstance(result, Exception):
                final_results.append(IndexingResult(
                    genome_id="",
                    model_name=Path(path).stem,
                    num_views_rendered=0,
                    has_geometry_embedding=False,
                    has_text_embedding=False,
                    has_image_embedding=False,
                    errors=[str(result)]
                ))
            else:
                final_results.append(result)
                
        return final_results
    
    async def _extract_genome(self, model_path: str) -> dict:
        """Extract genome using your existing pipeline."""
        # This calls your existing genome extraction code
        result = await self.creo.extract_genome(model_path)
        return {
            'genome_id': result.genome_id,
            'model_name': result.model_name
        }
    
    async def _get_model_name(self, genome_id: str) -> str:
        """Get model name from database."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT model_name FROM model_genomes WHERE genome_id = $1",
                genome_id
            )
            return row['model_name'] if row else ""
    
    async def _generate_description(self, genome_id: str) -> str:
        """
        Auto-generate description from genome data.
        Uses feature types, parameters, and category.
        """
        async with self.pool.acquire() as conn:
            # Get model info
            model = await conn.fetchrow("""
                SELECT model_name, category, tags, description
                FROM model_genomes WHERE genome_id = $1
            """, genome_id)
            
            # Get feature summary
            features = await conn.fetch("""
                SELECT feature_type, feature_subtype, COUNT(*) as count
                FROM feature_genomes
                WHERE model_genome_id = $1
                GROUP BY feature_type, feature_subtype
                ORDER BY count DESC
                LIMIT 10
            """, genome_id)
            
            # Get key parameters
            params = await conn.fetch("""
                SELECT param_name, param_value
                FROM model_parameters
                WHERE model_genome_id = $1
                AND is_designated = true
                LIMIT 10
            """, genome_id)
        
        # Build description
        parts = []
        
        if model['description']:
            parts.append(model['description'])
        else:
            parts.append(f"CAD model: {model['model_name']}")
            
        if model['category']:
            parts.append(f"Category: {model['category']}")
            
        if model['tags']:
            parts.append(f"Tags: {', '.join(model['tags'])}")
            
        if features:
            feature_desc = ", ".join([
                f"{f['count']} {f['feature_subtype'] or f['feature_type']}"
                for f in features[:5]
            ])
            parts.append(f"Features: {feature_desc}")
            
        if params:
            param_desc = ", ".join([
                f"{p['param_name']}={p['param_value']}"
                for p in params[:5]
            ])
            parts.append(f"Parameters: {param_desc}")
        
        return ". ".join(parts)
    
    async def _export_mesh(self, model_path: str, genome_id: str) -> str:
        """Export model to STL for offline processing."""
        output_path = self.render_dir / genome_id / "mesh.stl"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        await self.creo.export_stl(model_path, str(output_path))
        return str(output_path)
    
    async def _upload_to_b2(self, local_path: str, b2_key: str) -> str:
        """Upload file to Backblaze B2."""
        # Use your existing B2 client
        with open(local_path, 'rb') as f:
            result = await self.b2.upload_file(
                bucket_name="cad-views",
                file_name=b2_key,
                file_data=f.read(),
                content_type="image/png"
            )
        return result['url']
    
    async def _store_view_metadata(
        self,
        genome_id: str,
        rendered_views: List[dict],
        view_urls: List[str]
    ):
        """Store view metadata in database."""
        async with self.pool.acquire() as conn:
            for view, url in zip(rendered_views, view_urls):
                # Compute view embedding
                view_embedding = self.retriever.encode_image(view['path'])
                
                await conn.execute("""
                    INSERT INTO model_rendered_views (
                        model_genome_id, view_type, view_angle,
                        b2_bucket, b2_key, view_embedding, resolution
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (model_genome_id, view_type) 
                    DO UPDATE SET
                        view_angle = EXCLUDED.view_angle,
                        b2_key = EXCLUDED.b2_key,
                        view_embedding = EXCLUDED.view_embedding
                """,
                    genome_id,
                    view['view_name'],
                    {'azimuth': view['azimuth'], 'elevation': view['elevation']},
                    "cad-views",
                    url.split('/')[-1],
                    view_embedding.tolist(),
                    list(view['resolution'])
                )
```

Finally, the gRPC service integration:

```protobuf
// cad_retrieval.proto
// Add to your existing proto definitions

syntax = "proto3";

package cad_retrieval;

service CADRetrievalService {
    // Search for similar models
    rpc FindSimilarModels(SimilarModelsRequest) returns (SimilarModelsResponse);
    
    // Index a new model
    rpc IndexModel(IndexModelRequest) returns (IndexModelResponse);
    
    // Batch index models
    rpc IndexModelBatch(stream IndexModelRequest) returns (stream IndexModelResponse);
    
    // Get model embeddings
    rpc GetModelEmbeddings(GetEmbeddingsRequest) returns (GetEmbeddingsResponse);
}

message SimilarModelsRequest {
    // Query modalities (at least one required)
    optional string text_query = 1;
    optional bytes image_data = 2;  // PNG/JPEG bytes
    optional string image_path = 3;
    optional PointCloud geometry_query = 4;
    
    // Filters
    optional string category_filter = 5;
    optional BoundingBox bbox_filter = 6;
    
    // Options
    int32 top_k = 7;
    bool rerank = 8;
    bool include_embeddings = 9;
}

message PointCloud {
    repeated Point3D points = 1;
}

message Point3D {
    float x = 1;
    float y = 2;
    float z = 3;
}

message BoundingBox {
    Point3D min = 1;
    Point3D max = 2;
}

message SimilarModelsResponse {
    repeated SimilarModel results = 1;
    string query_id = 2;  // For logging/debugging
}

message SimilarModel {
    string genome_id = 1;
    string model_name = 2;
    string category = 3;
    float similarity_score = 4;
    optional float text_similarity = 5;
    optional float image_similarity = 6;
    optional float geometry_similarity = 7;
    optional BoundingBox bounding_box = 8;
    repeated string view_urls = 9;  // Pre-rendered view URLs
}

message IndexModelRequest {
    string model_path = 1;
    optional string genome_id = 2;  // If already extracted
    optional string description = 3;
    bool use_creo_rendering = 4;
}

message IndexModelResponse {
    string genome_id = 1;
    string model_name = 2;
    int32 num_views_rendered = 3;
    bool has_geometry_embedding = 4;
    bool has_text_embedding = 5;
    bool has_image_embedding = 6;
    repeated string errors = 7;
}

message GetEmbeddingsRequest {
    string genome_id = 1;
}

message GetEmbeddingsResponse {
    string genome_id = 1;
    repeated float text_embedding = 2;
    repeated float image_embedding = 3;
    repeated float geometry_embedding = 4;
    repeated float fused_embedding = 5;
}
```

```python
# cad_retrieval/grpc_service.py
"""
gRPC service implementation for CAD retrieval.
"""

import grpc
from concurrent import futures
import asyncio
import numpy as np

from . import cad_retrieval_pb2 as pb2
from . import cad_retrieval_pb2_grpc as pb2_grpc
from .coscad_retriever import CosCADRetriever, RetrievalQuery
from .indexing_pipeline import CADIndexingPipeline


class CADRetrievalServicer(pb2_grpc.CADRetrievalServiceServicer):
    """gRPC service for CAD retrieval operations."""
    
    def __init__(self, retriever: CosCADRetriever, pipeline: CADIndexingPipeline):
        self.retriever = retriever
        self.pipeline = pipeline
        self._loop = asyncio.new_event_loop()
        
    def FindSimilarModels(self, request, context):
        """Find similar CAD models based on query."""
        # Build query
        query = RetrievalQuery()
        
        if request.HasField('text_query'):
            query.text = request.text_query
            
        if request.HasField('image_path'):
            query.image_path = request.image_path
        elif request.HasField('image_data'):
            # Save to temp file and use
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                f.write(request.image_data)
                query.image_path = f.name
                
        if request.HasField('geometry_query'):
            points = np.array([
                [p.x, p.y, p.z] for p in request.geometry_query.points
            ], dtype=np.float32)
            query.geometry_points = points
            
        if request.HasField('category_filter'):
            query.category_filter = request.category_filter
            
        if request.HasField('bbox_filter'):
            query.bbox_filter = {
                'min': [
                    request.bbox_filter.min.x,
                    request.bbox_filter.min.y,
                    request.bbox_filter.min.z
                ],
                'max': [
                    request.bbox_filter.max.x,
                    request.bbox_filter.max.y,
                    request.bbox_filter.max.z
                ]
            }
        
        # Execute search
        results = self._loop.run_until_complete(
            self.retriever.retrieve(
                query,
                top_k=request.top_k or 10,
                rerank=request.rerank
            )
        )
        
        # Build response
        response = pb2.SimilarModelsResponse()
        
        for r in results:
            model = pb2.SimilarModel(
                genome_id=r.genome_id,
                model_name=r.model_name,
                category=r.category or "",
                similarity_score=r.similarity_score
            )
            
            if r.text_similarity is not None:
                model.text_similarity = r.text_similarity
            if r.image_similarity is not None:
                model.image_similarity = r.image_similarity
            if r.geometry_similarity is not None:
                model.geometry_similarity = r.geometry_similarity
                
            if r.bounding_box:
                model.bounding_box.CopyFrom(pb2.BoundingBox(
                    min=pb2.Point3D(
                        x=r.bounding_box['min'][0],
                        y=r.bounding_box['min'][1],
                        z=r.bounding_box['min'][2]
                    ),
                    max=pb2.Point3D(
                        x=r.bounding_box['max'][0],
                        y=r.bounding_box['max'][1],
                        z=r.bounding_box['max'][2]
                    )
                ))
            
            response.results.append(model)
            
        return response
    
    def IndexModel(self, request, context):
        """Index a CAD model for retrieval."""
        result = self._loop.run_until_complete(
            self.pipeline.index_model(
                model_path=request.model_path,
                genome_id=request.genome_id if request.HasField('genome_id') else None,
                description=request.description if request.HasField('description') else None,
                use_creo_rendering=request.use_creo_rendering
            )
        )
        
        return pb2.IndexModelResponse(
            genome_id=result.genome_id,
            model_name=result.model_name,
            num_views_rendered=result.num_views_rendered,
            has_geometry_embedding=result.has_geometry_embedding,
            has_text_embedding=result.has_text_embedding,
            has_image_embedding=result.has_image_embedding,
            errors=result.errors
        )


def serve(
    database_url: str,
    creo_client,
    b2_client,
    port: int = 50052
):
    """Start the gRPC server."""
    # Initialize components
    retriever = CosCADRetriever(database_url)
    pipeline = CADIndexingPipeline(
        database_url=database_url,
        creo_client=creo_client,
        b2_client=b2_client,
        render_output_dir="/tmp/cad-renders"
    )
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(retriever.initialize())
    loop.run_until_complete(pipeline.initialize())
    
    # Create server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_CADRetrievalServiceServicer_to_server(
        CADRetrievalServicer(retriever, pipeline),
        server
    )
    
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    
    print(f"CAD Retrieval Service running on port {port}")
    server.wait_for_termination()
```

## Summary

I've built a complete CosCAD-inspired retrieval system that integrates with your existing:

1. **Schema extensions** for multimodal embeddings with LSH buckets, HNSW indexes, and PostGIS spatial queries
2. **3D geometry encoder** (PointNet++ and DGCNN) with contrastive training to align with CLIP
3. **View rendering pipeline** using Creo or offline mesh rendering
4. **Indexing pipeline** that extracts genomes, renders views, generates point clouds, and computes embeddings
5. **gRPC service** that plugs into your existing architecture

Would you like me to continue with:
- The geometry encoder training script and dataset preparation?
- Integration with your SmartAssembly workflow for template retrieval?
- A TypeScript client for the retrieval API?
- Benchmark queries and evaluation metrics?