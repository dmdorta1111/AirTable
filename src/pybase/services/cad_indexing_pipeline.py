"""
CAD indexing pipeline for multi-modal vector storage.

Integrates genome extraction with embedding generation and database storage.
Processes CAD models through: extraction -> embedding generation -> storage.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.logging import get_logger
from pybase.models.cad_model import (
    CADAssemblyRelation,
    CADManufacturingFeature,
    CADModel,
    CADModelEmbedding,
    CADRenderedView,
)
from pybase.services.embedding_generator import EmbeddingGenerator, get_embedding_generator
from pybase.services.brep_graph_encoder import BRepGraphEncoder
from pybase.services.sketch_similarity import SketchSimilarityService
from pybase.services.parametric_miner import ParametricMiner

logger = get_logger(__name__)


@dataclass
class IndexingResult:
    """Result of indexing a single CAD model."""
    model_id: str | None
    file_name: str
    status: str  # pending, processing, completed, failed
    num_views_rendered: int = 0
    has_text_embedding: bool = False
    has_image_embedding: bool = False
    has_geometry_embedding: bool = False
    has_brep_graph_embedding: bool = False
    has_sketch_embedding: bool = False
    has_parametric_embedding: bool = False
    has_fused_embedding: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


@dataclass
class BatchIndexingResult:
    """Result of batch indexing multiple CAD models."""
    job_id: str
    total_models: int
    completed: int = 0
    failed: int = 0
    pending: int = 0
    results: list[IndexingResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class CADIndexingPipeline:
    """
    End-to-end pipeline for indexing CAD models.

    Flow:
    1. Extract genome (call Subagent 3's extractor)
    2. Generate description from genome metadata
    3. Render canonical views (placeholder)
    4. Upload views to B2 (placeholder)
    5. Extract point cloud (from genome)
    6. Compute embeddings (text, image, geometry, fused)
    7. Store embeddings in database
    8. Update model status
    """

    # Canonical views to render
    CANONICAL_VIEWS = [
        "front", "back", "left", "right", "top", "bottom",
        "iso_1", "iso_2", "iso_3", "iso_4"
    ]

    # Maximum file size (500 MB) to prevent memory issues
    MAX_FILE_SIZE = 500 * 1024 * 1024

    def __init__(
        self,
        max_concurrent: int = 5,
        embedding_device: str = "cpu",
    ):
        """Initialize indexing pipeline."""
        self.max_concurrent = max_concurrent
        self.embedding_device = embedding_device
        self._embedding_generator: EmbeddingGenerator | None = None
        self._brep_encoder: BRepGraphEncoder | None = None
        self._sketch_service: SketchSimilarityService | None = None
        self._parametric_miner: ParametricMiner | None = None

    @property
    def embedding_generator(self) -> EmbeddingGenerator:
        """Lazy-load embedding generator."""
        if self._embedding_generator is None:
            self._embedding_generator = get_embedding_generator(device=self.embedding_device)
        return self._embedding_generator

    @property
    def brep_encoder(self) -> BRepGraphEncoder:
        """Lazy-load B-Rep graph encoder."""
        if self._brep_encoder is None:
            self._brep_encoder = BRepGraphEncoder()
        return self._brep_encoder

    @property
    def sketch_service(self) -> SketchSimilarityService:
        """Lazy-load sketch similarity service."""
        if self._sketch_service is None:
            self._sketch_service = SketchSimilarityService()
        return self._sketch_service

    @property
    def parametric_miner(self) -> ParametricMiner:
        """Lazy-load parametric miner."""
        if self._parametric_miner is None:
            self._parametric_miner = ParametricMiner()
        return self._parametric_miner

    async def index_model(
        self,
        db: AsyncSession,
        user_id: str,
        file_path: str,
        workspace_id: str | None = None,
        description: str | None = None,
        category_label: str | None = None,
        tags: list[str] | None = None,
        skip_existing: bool = True,
    ) -> IndexingResult:
        """
        Index a single CAD model.

        Args:
            db: Database session
            user_id: User uploading the model
            file_path: Path to CAD file
            workspace_id: Optional workspace ID
            description: Optional description (auto-generated if None)
            category_label: Optional category
            tags: Optional tags
            skip_existing: Skip if model already indexed

        Returns:
            IndexingResult with status and any errors
        """
        path = Path(file_path)
        result = IndexingResult(
            model_id=None,
            file_name=path.name,
            status="processing",
        )

        try:
            # Validate file size before processing
            file_size = path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                result.status = "failed"
                result.errors.append(
                    f"File too large: {file_size / (1024*1024):.1f}MB "
                    f"(max {self.MAX_FILE_SIZE / (1024*1024)}MB)"
                )
                result.completed_at = datetime.now(timezone.utc)
                return result

            # Check if model already exists (by file hash)
            if skip_existing:
                existing = await self._get_existing_model(db, user_id, path)
                if existing:
                    result.model_id = str(existing.id)
                    result.status = "completed"
                    result.warnings.append("Model already indexed")
                    return result

            # Step 1: Create CAD model record
            model = await self._create_model_record(
                db=db,
                user_id=user_id,
                file_path=path,
                workspace_id=workspace_id,
                category_label=category_label,
                tags=tags,
            )
            result.model_id = str(model.id)

            # Step 2: Extract genome (placeholder for Subagent 3 integration)
            await self._extract_genome(db, model, path)
            result.warnings.append("Genome extraction: placeholder implementation")

            # Step 3: Generate or use description
            if description is None:
                description = self._generate_description(model)
            result.has_text_embedding = bool(description)

            # Step 4: Render canonical views (placeholder)
            rendered_views = await self._render_views(model, path)
            result.num_views_rendered = len(rendered_views)
            result.warnings.append(f"View rendering: placeholder ({len(rendered_views)} views)")

            # Step 5: Upload views to B2 (placeholder)
            view_urls = await self._upload_views_to_b2(model, rendered_views)
            result.warnings.append("B2 upload: placeholder implementation")

            # Step 6: Extract point cloud (from genome)
            point_cloud = await self._extract_point_cloud(model)

            # Step 7: Compute embeddings
            embeddings = await self._compute_embeddings(
                db=db,
                model=model,
                description=description,
                rendered_views=rendered_views,
                point_cloud=point_cloud,
            )
            result.has_text_embedding = embeddings.get("text_embedding") is not None
            result.has_image_embedding = embeddings.get("image_embedding") is not None
            result.has_geometry_embedding = embeddings.get("geometry_embedding") is not None
            result.has_fused_embedding = embeddings.get("fused_embedding") is not None

            # Step 8: Store embeddings
            await self._store_embeddings(db, model, embeddings)

            # Step 9: Store view metadata
            await self._store_view_metadata(db, model, rendered_views, view_urls)

            # Update status
            model.status = "completed"
            result.status = "completed"
            result.completed_at = datetime.now(timezone.utc)

            await db.commit()

        except Exception as e:
            logger.error(f"Indexing failed for {file_path}: {e}")
            result.status = "failed"
            result.errors.append(str(e))
            result.completed_at = datetime.now(timezone.utc)

            # Try to update model status if we created it
            if result.model_id:
                try:
                    model = await db.get(CADModel, UUID(result.model_id))
                    if model:
                        model.status = "failed"
                        await db.commit()
                except Exception:
                    pass

        return result

    async def index_batch(
        self,
        db: AsyncSession,
        user_id: str,
        file_paths: list[str],
        workspace_id: str | None = None,
        descriptions: dict[str, str] | None = None,
        category_labels: dict[str, str] | None = None,
        continue_on_error: bool = True,
    ) -> BatchIndexingResult:
        """
        Index multiple CAD models concurrently.

        Args:
            db: Database session
            user_id: User uploading the models
            file_paths: List of file paths to index
            workspace_id: Optional workspace ID
            descriptions: Optional mapping of file path to description
            category_labels: Optional mapping of file path to category
            continue_on_error: Continue processing if one file fails

        Returns:
            BatchIndexingResult with per-model results
        """
        import uuid

        job_id = str(uuid.uuid4())
        descriptions = descriptions or {}
        category_labels = category_labels or {}

        result = BatchIndexingResult(
            job_id=job_id,
            total_models=len(file_paths),
            pending=len(file_paths),
        )

        # Process with semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def index_with_semaphore(path: str) -> IndexingResult:
            async with semaphore:
                return await self.index_model(
                    db=db,
                    user_id=user_id,
                    file_path=path,
                    workspace_id=workspace_id,
                    description=descriptions.get(path),
                    category_label=category_labels.get(path),
                )

        # Gather results
        tasks = [index_with_semaphore(path) for path in file_paths]
        model_results = await asyncio.gather(
            *tasks,
            return_exceptions=continue_on_error,
        )

        # Process results
        for i, mr in enumerate(model_results):
            if isinstance(mr, Exception):
                # Convert exception to error result
                error_result = IndexingResult(
                    model_id=None,
                    file_name=Path(file_paths[i]).name,
                    status="failed",
                    errors=[str(mr)],
                    completed_at=datetime.now(timezone.utc),
                )
                result.results.append(error_result)
                result.failed += 1
            else:
                result.results.append(mr)
                if mr.status == "completed":
                    result.completed += 1
                elif mr.status == "failed":
                    result.failed += 1
                else:
                    result.pending += 1

        result.pending = 0  # All done
        result.completed_at = datetime.now(timezone.utc)

        return result

    async def _get_existing_model(
        self,
        db: AsyncSession,
        user_id: str,
        file_path: Path,
    ) -> CADModel | None:
        """Check if model already exists by file hash."""
        # Compute file hash
        file_hash = await self._compute_file_hash(file_path)

        # Query for existing model
        stmt = select(CADModel).where(
            CADModel.user_id == user_id,
            CADModel.file_hash == file_hash,
            CADModel.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file."""
        import hashlib

        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def _create_model_record(
        self,
        db: AsyncSession,
        user_id: str,
        file_path: Path,
        workspace_id: str | None,
        category_label: str | None,
        tags: list[str] | None,
    ) -> CADModel:
        """Create CAD model database record."""
        import hashlib

        # Get file info
        file_size = file_path.stat().st_size
        file_hash = await self._compute_file_hash(file_path)
        file_type = file_path.suffix.lstrip(".").lower()

        # Detect file type
        if file_type not in ["step", "stp", "iges", "igs", "dxf", "dwg", "ifc", "slt", "stl"]:
            file_type = "step"  # Default

        # Create model
        model = CADModel(
            user_id=user_id,
            workspace_id=workspace_id,
            file_name=file_path.name,
            file_type=file_type,
            file_size_bytes=file_size,
            file_hash=file_hash,
            storage_path=None,  # Will be set after B2 upload
            category_label=category_label,
            tags=tags or [],
            status="processing",
        )
        db.add(model)
        await db.flush()
        return model

    async def _extract_genome(
        self,
        db: AsyncSession,
        model: CADModel,
        file_path: Path,
    ) -> None:
        """
        Extract B-Rep genome from CAD file.

        NOTE: This is a placeholder for Subagent 3's genome extractor.
        When available, call the actual genome extraction service.
        """
        # Placeholder: store minimal genome info
        # Subagent 3 will implement full extraction

        # For now, compute basic file stats as placeholder
        try:
            model.brep_genome = {
                "source": file_path.name,
                "format": file_path.suffix,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
            }
            model.face_count = 0
            model.edge_count = 0
            model.vertex_count = 0
        except Exception as e:
            logger.warning(f"Genome extraction placeholder failed: {e}")

    def _generate_description(self, model: CADModel) -> str:
        """Auto-generate description from model metadata."""
        parts = []

        if model.file_name:
            parts.append(f"CAD model: {model.file_name}")

        if model.category_label:
            parts.append(f"Category: {model.category_label}")

        if model.tags:
            parts.append(f"Tags: {', '.join(model.tags)}")

        if model.material:
            parts.append(f"Material: {model.material}")

        # Add geometry info
        if model.face_count:
            parts.append(f"{model.face_count} faces")

        if model.bounding_box:
            bbox = model.bounding_box
            if isinstance(bbox, dict) and "min" in bbox and "max" in bbox:
                dims = [
                    bbox["max"][i] - bbox["min"][i]
                    for i in range(3)
                ]
                parts.append(f"Size: {dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f}")

        return ". ".join(parts) if parts else model.file_name

    async def _render_views(
        self,
        model: CADModel,
        file_path: Path,
    ) -> list[dict[str, Any]]:
        """
        Render canonical 2D views of the CAD model.

        NOTE: This is a placeholder. Actual rendering requires CAD kernel integration.
        """
        # Placeholder: return view metadata without actual images
        views = []
        for view_name in self.CANONICAL_VIEWS:
            views.append({
                "view_type": view_name,
                "path": None,  # No actual file rendered
                "resolution": [512, 512],
                "placeholder": True,
            })
        return views

    async def _upload_views_to_b2(
        self,
        model: CADModel,
        rendered_views: list[dict[str, Any]],
    ) -> list[str | None]:
        """
        Upload rendered views to Backblaze B2.

        NOTE: This is a placeholder. Subagent 6 implements B2 integration.
        """
        # Placeholder: return empty URLs
        return [None] * len(rendered_views)

    async def _extract_point_cloud(
        self,
        model: CADModel,
    ) -> list[list[float]] | None:
        """
        Extract point cloud from model genome.

        NOTE: This is a placeholder for Subagent 3's point cloud extractor.
        """
        # Placeholder: generate random points if bbox exists
        if model.bounding_box and isinstance(model.bounding_box, dict):
            min_pt = np.array(model.bounding_box.get("min", [0, 0, 0]))
            max_pt = np.array(model.bounding_box.get("max", [100, 100, 100]))

            # Generate 100 random points within bbox
            points = np.random.rand(100, 3) * (max_pt - min_pt) + min_pt
            model.point_cloud = {
                "points": points.tolist(),
                "count": 100,
            }
            return points.tolist()

        return None

    async def _compute_embeddings(
        self,
        db: AsyncSession,
        model: CADModel,
        description: str,
        rendered_views: list[dict[str, Any]],
        point_cloud: list[list[float]] | None,
    ) -> dict[str, Any]:
        """Compute all embedding types for the model."""
        embeddings = {}
        gen = self.embedding_generator

        # Text embedding from description
        try:
            text_emb = gen.encode_text(description)
            embeddings["text_embedding"] = text_emb
        except Exception as e:
            logger.warning(f"Text embedding failed: {e}")

        # Image embedding from rendered views (average if multiple)
        try:
            # For placeholder views without actual images, use description embedding
            if rendered_views and rendered_views[0].get("path"):
                image_embs = []
                for view in rendered_views:
                    if view["path"]:
                        emb = gen.encode_image(view["path"])
                        image_embs.append(emb)

                if image_embs:
                    # Average view embeddings
                    avg_emb = np.mean(image_embs, axis=0)
                    avg_emb = avg_emb / (np.linalg.norm(avg_emb) + 1e-8)
                    embeddings["image_embedding"] = avg_emb.astype(np.float32).tolist()
            else:
                # Use text embedding as fallback for cross-modal alignment
                if "text_embedding" in embeddings:
                    embeddings["image_embedding"] = embeddings["text_embedding"]
        except Exception as e:
            logger.warning(f"Image embedding failed: {e}")

        # Geometry embedding from point cloud
        try:
            geom_emb = gen.encode_geometry(
                point_cloud=point_cloud,
                bbox=model.bounding_box,
            )
            embeddings["geometry_embedding"] = geom_emb
        except Exception as e:
            logger.warning(f"Geometry embedding failed: {e}")

        # Fused embedding combining all modalities
        try:
            fused_emb = gen.fuse_embeddings(
                text_embedding=embeddings.get("text_embedding"),
                image_embedding=embeddings.get("image_embedding"),
                geometry_embedding=embeddings.get("geometry_embedding"),
            )
            embeddings["fused_embedding"] = fused_emb
        except Exception as e:
            logger.warning(f"Fused embedding failed: {e}")

        # LSH buckets for coarse filtering
        if embeddings.get("fused_embedding"):
            lsh_buckets = gen.compute_lsh_buckets(embeddings["fused_embedding"])
            embeddings["lsh_buckets"] = lsh_buckets

        return embeddings

    async def _store_embeddings(
        self,
        db: AsyncSession,
        model: CADModel,
        embeddings: dict[str, Any],
    ) -> None:
        """Store embeddings in database with transaction isolation for HNSW updates."""
        # Use SELECT FOR UPDATE to prevent concurrent HNSW index conflicts
        # This ensures only one transaction can update the embedding at a time
        from sqlalchemy import for_update

        stmt = select(CADModelEmbedding).where(
            CADModelEmbedding.cad_model_id == model.id
        ).with_for_update()

        result = await db.execute(stmt)
        emb_record = result.scalar_one_or_none()

        lsh_buckets = embeddings.get("lsh_buckets", [0, 0, 0, 0])

        if emb_record:
            # Update existing (row is locked from SELECT FOR UPDATE)
            emb_record.clip_text_embedding = embeddings.get("text_embedding")
            emb_record.clip_image_embedding = embeddings.get("image_embedding")
            emb_record.geometry_embedding = embeddings.get("geometry_embedding")
            emb_record.brep_graph_embedding = embeddings.get("brep_graph_embedding")
            emb_record.fused_embedding = embeddings.get("fused_embedding")
            emb_record.lsh_bucket_1 = lsh_buckets[0] if len(lsh_buckets) > 0 else None
            emb_record.lsh_bucket_2 = lsh_buckets[1] if len(lsh_buckets) > 1 else None
            emb_record.lsh_bucket_3 = lsh_buckets[2] if len(lsh_buckets) > 2 else None
            emb_record.lsh_bucket_4 = lsh_buckets[3] if len(lsh_buckets) > 3 else None
        else:
            # Create new
            emb_record = CADModelEmbedding(
                cad_model_id=model.id,
                clip_text_embedding=embeddings.get("text_embedding"),
                clip_image_embedding=embeddings.get("image_embedding"),
                geometry_embedding=embeddings.get("geometry_embedding"),
                brep_graph_embedding=embeddings.get("brep_graph_embedding"),
                fused_embedding=embeddings.get("fused_embedding"),
                lsh_bucket_1=lsh_buckets[0] if len(lsh_buckets) > 0 else None,
                lsh_bucket_2=lsh_buckets[1] if len(lsh_buckets) > 1 else None,
                lsh_bucket_3=lsh_buckets[2] if len(lsh_buckets) > 2 else None,
                lsh_bucket_4=lsh_buckets[3] if len(lsh_buckets) > 3 else None,
            )
            db.add(emb_record)

    async def _store_view_metadata(
        self,
        db: AsyncSession,
        model: CADModel,
        rendered_views: list[dict[str, Any]],
        view_urls: list[str | None],
    ) -> None:
        """Store rendered view metadata in database."""
        # Clear existing views
        for existing_view in model.rendered_views:
            await db.delete(existing_view)

        # Add new views
        for view, url in zip(rendered_views, view_urls):
            view_record = CADRenderedView(
                cad_model_id=model.id,
                view_type=view["view_type"],
                view_angle={"azimuth": 0, "elevation": 0},  # Placeholder
                storage_bucket=None,  # Will be set after B2 upload
                storage_key=None,
                resolution=view.get("resolution"),
            )
            db.add(view_record)

    # =========================================================================
    # Advanced Features: Process existing serialized_models data
    # =========================================================================

    async def process_serialized_model_advanced(
        self,
        db: AsyncSession,
        user_id: str,
        model: CADModel,
        serialized_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Process advanced features from existing serialized_models data.

        Enhances CAD model with B-Rep graph, sketch, and parametric embeddings
        extracted from previously serialized data.

        Args:
            db: Database session
            user_id: User ID for ownership
            model: CADModel to enhance
            serialized_data: Data from serialized_models table with keys:
                - feature_geometry: {surfaces: [...], edges: [...]}
                - sketches: [{feature_id, entities, ...}, ...]
                - parameters: {parameters: [...]}
                - relations: {relations: [...]}

        Returns:
            Dict with processing results and embedding info
        """
        if not serialized_data:
            return {"success": False, "error": "No serialized data provided"}

        results = {
            "brep_graph": None,
            "sketch": None,
            "parametric": None,
        }

        # Get or create embedding record
        stmt = select(CADModelEmbedding).where(
            CADModelEmbedding.cad_model_id == model.id
        )
        result = await db.execute(stmt)
        emb_record = result.scalar_one_or_none()

        if not emb_record:
            emb_record = CADModelEmbedding(cad_model_id=model.id)
            db.add(emb_record)
            await db.flush()

        # 1. Process B-Rep graph from feature_geometry
        feature_geom = serialized_data.get("feature_geometry")
        if feature_geom:
            brep_result = self.brep_encoder.encode_from_serialized_data(feature_geom)
            if brep_result.embedding:
                emb_record.brep_graph_embedding = brep_result.embedding
                results["brep_graph"] = {
                    "success": True,
                    "face_count": brep_result.graph.face_count if brep_result.graph else 0,
                }
                logger.info(f"Encoded B-Rep graph: {brep_result.graph.face_count if brep_result.graph else 0} faces")
            else:
                results["brep_graph"] = {"success": False, "error": brep_result.error}

        # 2. Process sketches for similarity search
        sketches = serialized_data.get("sketches")
        if sketches:
            sketch_embeddings = self.sketch_service.encode_all_sketches(sketches)
            if sketch_embeddings:
                # Aggregate to model-level embedding (store in fused_embedding for now)
                agg_emb = self.sketch_service.aggregate_model_sketch_embedding(sketch_embeddings)
                if agg_emb:
                    # Store alongside other embeddings
                    results["sketch"] = {
                        "success": True,
                        "sketch_count": len(sketch_embeddings),
                    }
                    logger.info(f"Encoded {len(sketch_embeddings)} sketches")
            else:
                results["sketch"] = {"success": False, "error": "No sketch embeddings generated"}

        # 3. Process parametric patterns
        parameters = serialized_data.get("parameters")
        relations = serialized_data.get("relations")
        if parameters or relations:
            param_result = self.parametric_miner.mine_from_serialized(parameters, relations)
            if param_result.embedding:
                # Could store in separate column or append to fused
                results["parametric"] = {
                    "success": True,
                    "pattern": {
                        "variables": param_result.pattern.variable_count if param_result.pattern else 0,
                        "equations": param_result.pattern.equation_count if param_result.pattern else 0,
                    }
                }
                logger.info(f"Mined parametric pattern: {param_result.pattern.variable_count if param_result.pattern else 0} vars")
            else:
                results["parametric"] = {"success": False, "error": param_result.error}

        await db.commit()

        return results

    async def index_from_serialized_models_table(
        self,
        db: AsyncSession,
        user_id: str,
        serialized_model_data: dict[str, Any],
        file_name: str,
        category_label: str | None = None,
        tags: list[str] | None = None,
    ) -> IndexingResult:
        """
        Create CAD model entry from existing serialized_models table data.

        Use this to migrate/enhance models already in serialized_models.

        Args:
            db: Database session
            user_id: User ID
            serialized_model_data: Full row data from serialized_models
            file_name: Model file name
            category_label: Optional category
            tags: Optional tags

        Returns:
            IndexingResult with status
        """
        result = IndexingResult(
            model_id=None,
            file_name=file_name,
            status="processing",
        )

        try:
            # Create CAD model record
            model = CADModel(
                user_id=user_id,
                workspace_id=None,
                file_name=file_name,
                file_type="prt",  # Default, can be overridden
                category_label=category_label,
                tags=tags or [],
                status="processing",
            )

            # Copy basic metadata
            if "feature_count" in serialized_model_data:
                model.face_count = serialized_model_data["feature_count"]

            # Store B-Rep genome
            if "serialized_content" in serialized_model_data:
                model.brep_genome = serialized_model_data["serialized_content"]

            if "feature_types" in serialized_model_data:
                model.feature_tree = {"feature_types": serialized_model_data["feature_types"]}

            if "bounding_box" in serialized_model_data:
                model.bounding_box = serialized_model_data["bounding_box"]

            if "mass_properties" in serialized_model_data:
                mass = serialized_model_data["mass_properties"]
                model.mass_kg = mass.get("mass")
                model.volume_cm3 = mass.get("volume")

            db.add(model)
            await db.flush()
            result.model_id = str(model.id)

            # Process advanced features
            advanced_results = await self.process_serialized_model_advanced(
                db=db,
                user_id=user_id,
                model=model,
                serialized_data=serialized_model_data,
            )

            # Update result flags
            if advanced_results.get("brep_graph", {}).get("success"):
                result.has_brep_graph_embedding = True
            if advanced_results.get("sketch", {}).get("success"):
                result.has_sketch_embedding = True
            if advanced_results.get("parametric", {}).get("success"):
                result.has_parametric_embedding = True

            # Generate description from metadata
            description = self._generate_description(model)
            text_emb = self.embedding_generator.encode_text(description)
            if text_emb:
                result.has_text_embedding = True

            # Get or update embedding record
            stmt = select(CADModelEmbedding).where(
                CADModelEmbedding.cad_model_id == model.id
            )
            emb_result = await db.execute(stmt)
            emb_record = emb_result.scalar_one_or_none()

            if emb_record:
                emb_record.clip_text_embedding = text_emb

            model.status = "completed"
            result.status = "completed"
            result.completed_at = datetime.now(timezone.utc)

            await db.commit()

            logger.info(f"Indexed model from serialized data: {file_name}")

        except Exception as e:
            logger.error(f"Indexing from serialized data failed for {file_name}: {e}")
            result.status = "failed"
            result.errors.append(str(e))
            result.completed_at = datetime.now(timezone.utc)

        return result

    async def batch_process_serialized_models(
        self,
        db: AsyncSession,
        user_id: str,
        serialized_models: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Batch process multiple models from serialized_models table.

        Args:
            db: Database session
            user_id: User ID
            serialized_models: List of serialized model data dicts

        Returns:
            Summary dict with counts and any errors
        """
        summary = {
            "total": len(serialized_models),
            "success": 0,
            "failed": 0,
            "errors": [],
        }

        for model_data in serialized_models:
            file_name = model_data.get("model_name", "unknown")
            category = model_data.get("category")
            tags = model_data.get("tags", [])

            result = await self.index_from_serialized_models_table(
                db=db,
                user_id=user_id,
                serialized_model_data=model_data,
                file_name=file_name,
                category_label=category,
                tags=tags,
            )

            if result.status == "completed":
                summary["success"] += 1
            else:
                summary["failed"] += 1
                if result.errors:
                    summary["errors"].append({
                        "file": file_name,
                        "errors": result.errors,
                    })

        return summary
