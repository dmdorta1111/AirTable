"""
CAD Models for dual-representation storage (B-Rep + DeepSDF).

Implements CosCAD-inspired dual storage:
- B-Rep genome for parametric editing
- DeepSDF latent for similarity search
- Multiple embedding types for cross-modal retrieval
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import SoftDeleteModel

if TYPE_CHECKING:
    from pybase.models.user import User
    from pybase.models.workspace import Workspace


class CADModel(SoftDeleteModel):
    """
    CAD Model with dual representation (B-Rep + DeepSDF).

    Stores both parametric B-Rep genome for editing and
    implicit DeepSDF latent for efficient similarity search.
    """

    __tablename__ = "cad_models"

    # Foreign keys
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("pybase.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("pybase.workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # File metadata
    file_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    file_type: Mapped[str] = mapped_column(
        String(50),  # step, iges, dxf, ifc, etc.
        nullable=False,
        index=True,
    )
    file_size_bytes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    file_hash: Mapped[str | None] = mapped_column(
        String(64),  # SHA-256 for deduplication
        nullable=True,
        index=True,
    )
    storage_path: Mapped[str | None] = mapped_column(
        String(1000),  # B2/S3 path
        nullable=True,
    )

    # B-Rep Genome Storage
    brep_genome: Mapped[dict | None] = mapped_column(
        JSONB,  # Feature tree, topology
        nullable=True,
    )
    brep_topology_compressed: Mapped[bytes | None] = mapped_column(
        BYTEA,  # Compressed B-Rep binary
        nullable=True,
    )
    feature_tree: Mapped[dict | None] = mapped_column(
        JSONB,  # Parametric history
        nullable=True,
    )
    face_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    edge_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    vertex_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # DeepSDF Implicit Representation (256-dim latent vector)
    deepsdf_latent: Mapped[list[float] | None] = mapped_column(
        ARRAY(Float, dimensions=1),
        nullable=True,
    )

    # Point cloud for rendering/analysis
    point_cloud: Mapped[dict | None] = mapped_column(
        JSONB,  # {points: [[x,y,z],...], count: N}
        nullable=True,
    )
    point_cloud_compressed: Mapped[bytes | None] = mapped_column(
        BYTEA,
        nullable=True,
    )

    # Bounding box (3D)
    bounding_box: Mapped[dict | None] = mapped_column(
        JSONB,  # {min: [x,y,z], max: [x,y,z]}
        nullable=True,
    )

    # Manufacturing metadata
    material: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    mass_kg: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    volume_cm3: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    surface_area_cm2: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Category/classification
    category_label: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        index=True,
    )
    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )

    # Source info
    source_system: Mapped[str | None] = mapped_column(
        String(100),  # creo, solidworks, autocad, etc.
        nullable=True,
    )
    extraction_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Indexing status
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
    )
    workspace: Mapped["Workspace | None"] = relationship(
        "Workspace",
        foreign_keys=[workspace_id],
    )

    # Child relationships
    embeddings: Mapped["CADModelEmbedding"] = relationship(
        "CADModelEmbedding",
        back_populates="cad_model",
        uselist=False,
        cascade="all, delete-orphan",
    )
    assembly_children: Mapped[list["CADAssemblyRelation"]] = relationship(
        "CADAssemblyRelation",
        foreign_keys="CADAssemblyRelation.parent_model_id",
        back_populates="parent_model",
        cascade="all, delete-orphan",
    )
    assembly_parents: Mapped[list["CADAssemblyRelation"]] = relationship(
        "CADAssemblyRelation",
        foreign_keys="CADAssemblyRelation.child_model_id",
        back_populates="child_model",
        cascade="all, delete-orphan",
    )
    features: Mapped[list["CADManufacturingFeature"]] = relationship(
        "CADManufacturingFeature",
        back_populates="cad_model",
        cascade="all, delete-orphan",
    )
    rendered_views: Mapped[list["CADRenderedView"]] = relationship(
        "CADRenderedView",
        back_populates="cad_model",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_cad_models_user_workspace", "user_id", "workspace_id"),
    )

    def __repr__(self) -> str:
        return f"<CADModel {self.file_name} ({self.file_type})>"


class CADModelEmbedding(SoftDeleteModel):
    """
    Multimodal embeddings for CAD model similarity search.

    Stores embeddings from different modalities for cross-modal retrieval:
    - B-Rep graph (UV-Net, BC-NET)
    - CLIP text/image
    - Point cloud geometry (PointNet++, DGCNN)
    - Fused combined embedding
    """

    __tablename__ = "cad_model_embeddings"

    cad_model_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("pybase.cad_models.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # B-Rep graph embedding (UV-Net, BC-NET, etc.) - 512-dim
    brep_graph_embedding: Mapped[list[float] | None] = mapped_column(
        ARRAY(Float, dimensions=1),
        nullable=True,
    )

    # CLIP embeddings for cross-modal retrieval - 512-dim each
    clip_text_embedding: Mapped[list[float] | None] = mapped_column(
        ARRAY(Float, dimensions=1),
        nullable=True,
    )
    clip_image_embedding: Mapped[list[float] | None] = mapped_column(
        ARRAY(Float, dimensions=1),
        nullable=True,
    )

    # Point cloud geometry embedding (PointNet++, DGCNN) - 1024-dim
    geometry_embedding: Mapped[list[float] | None] = mapped_column(
        ARRAY(Float, dimensions=1),
        nullable=True,
    )

    # Fused/combined embedding for general queries - 512-dim
    fused_embedding: Mapped[list[float] | None] = mapped_column(
        ARRAY(Float, dimensions=1),
        nullable=True,
    )

    # LSH buckets for coarse filtering (Tri-Index optimization)
    lsh_bucket_1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lsh_bucket_2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lsh_bucket_3: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lsh_bucket_4: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Product quantization codes (compressed feature representation)
    pq_codes: Mapped[bytes | None] = mapped_column(
        BYTEA,
        nullable=True,
    )

    # Metadata
    model_version: Mapped[str | None] = mapped_column(
        String(50),  # Encoder version used
        nullable=True,
    )

    # Relationships
    cad_model: Mapped["CADModel"] = relationship(
        "CADModel",
        back_populates="embeddings",
    )

    def __repr__(self) -> str:
        return f"<CADModelEmbedding for model {self.cad_model_id}>"


class CADAssemblyRelation(SoftDeleteModel):
    """
    Assembly hierarchy relationships between CAD models.

    Stores parent-child relationships with transformation matrices
    for subassemblies and component instances.
    """

    __tablename__ = "cad_assembly_relations"

    parent_model_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("pybase.cad_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    child_model_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("pybase.cad_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Transformation matrix (4x4 for position/orientation)
    transform_matrix: Mapped[list[list[float]] | None] = mapped_column(
        ARRAY(Float, dimensions=2),
        nullable=True,
    )

    # Assembly metadata
    instance_name: Mapped[str | None] = mapped_column(
        String(200),  # Instance name in assembly
        nullable=True,
    )
    instance_count: Mapped[int] = mapped_column(
        Integer,  # For repeated parts
        nullable=False,
        default=1,
    )
    relation_type: Mapped[str] = mapped_column(
        String(50),  # component, subassembly, etc.
        nullable=False,
        default="component",
    )
    constraints: Mapped[dict | None] = mapped_column(
        JSONB,  # Mating constraints
        nullable=True,
    )

    # Relationships
    parent_model: Mapped["CADModel"] = relationship(
        "CADModel",
        foreign_keys=[parent_model_id],
        back_populates="assembly_children",
    )
    child_model: Mapped["CADModel"] = relationship(
        "CADModel",
        foreign_keys=[child_model_id],
        back_populates="assembly_parents",
    )

    def __repr__(self) -> str:
        return f"<CADAssemblyRelation {self.parent_model_id} -> {self.child_model_id}>"


class CADManufacturingFeature(SoftDeleteModel):
    """
    Manufacturing features extracted from CAD models.

    Stores feature metadata for manufacturing planning:
    holes, fillets, chamfers, pockets, etc.
    """

    __tablename__ = "cad_manufacturing_features"

    cad_model_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("pybase.cad_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Feature identification
    feature_type: Mapped[str] = mapped_column(
        String(50),  # hole, fillet, chamfer, pocket, etc.
        nullable=False,
        index=True,
    )
    feature_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    feature_identifier: Mapped[str | None] = mapped_column(
        String(200),  # CAD system's internal ID
        nullable=True,
    )

    # Feature parameters
    parameters: Mapped[dict | None] = mapped_column(
        JSONB,  # {diameter: 10, depth: 5, ...}
        nullable=True,
    )
    tolerance: Mapped[dict | None] = mapped_column(
        JSONB,  # GD&T info
        nullable=True,
    )

    # Location/extent
    location: Mapped[dict | None] = mapped_column(
        JSONB,  # Center point or reference location
        nullable=True,
    )
    extent: Mapped[dict | None] = mapped_column(
        JSONB,  # Bounding box of feature
        nullable=True,
    )

    # Classification
    machining_operation: Mapped[str | None] = mapped_column(
        String(100),  # drill, mill, turn, etc.
        nullable=True,
        index=True,
    )
    is_additive: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Relationships
    cad_model: Mapped["CADModel"] = relationship(
        "CADModel",
        back_populates="features",
    )

    def __repr__(self) -> str:
        return f"<CADManufacturingFeature {self.feature_type}>"


class CADRenderedView(SoftDeleteModel):
    """
    Pre-rendered 2D views for image-based retrieval.

    Stores rendered views of CAD models with their embeddings
    for sketch-to-CAD and image-to-CAD similarity search.
    """

    __tablename__ = "cad_rendered_views"

    cad_model_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("pybase.cad_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # View specification
    view_type: Mapped[str] = mapped_column(
        String(50),  # front, top, iso, canonical_0, etc.
        nullable=False,
        index=True,
    )
    view_angle: Mapped[dict | None] = mapped_column(
        JSONB,  # {azimuth: 45, elevation: 30}
        nullable=True,
    )

    # Storage reference
    storage_bucket: Mapped[str | None] = mapped_column(
        String(200),  # B2/S3 bucket
        nullable=True,
    )
    storage_key: Mapped[str | None] = mapped_column(
        String(500),  # File key
        nullable=True,
    )

    # View embedding for retrieval - 512-dim
    view_embedding: Mapped[list[float] | None] = mapped_column(
        ARRAY(Float, dimensions=1),
        nullable=True,
    )

    # Metadata
    resolution: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer),  # [width, height]
        nullable=True,
    )
    render_settings: Mapped[dict | None] = mapped_column(
        JSONB,  # Renderer settings
        nullable=True,
    )

    # Relationships
    cad_model: Mapped["CADModel"] = relationship(
        "CADModel",
        back_populates="rendered_views",
    )

    def __repr__(self) -> str:
        return f"<CADRenderedView {self.view_type} for {self.cad_model_id}>"

    @property
    def storage_path(self) -> str | None:
        """Get full storage path."""
        if self.storage_bucket and self.storage_key:
            return f"{self.storage_bucket}/{self.storage_key}"
        return None
