"""
Document Intelligence models for unified engineering document extraction.

This module provides models for:
- Auto-linking related files into DocumentGroups
- Tracking extraction jobs for PDF/DXF/CAD files
- Storing extracted dimensions, parameters, materials, and BOMs
- Semantic search across engineering metadata
"""

import json
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pybase.db.base import BaseModel, TimestampMixin, utc_now

if TYPE_CHECKING:
    from pybase.models.cad_model import CADModel


# =============================================================================
# Enums (PostgreSQL ENUM types created in migration)
# =============================================================================


class LinkingMethod(str, Enum):
    """Method used to create document groups."""

    AUTO_FILENAME = "auto_filename"  # Exact basename matching (confidence: 0.95)
    AUTO_FOLDER = "auto_folder"      # Folder siblings (confidence: 0.80)
    AUTO_PROJECT = "auto_project"    # Project code extraction (confidence: 0.70)
    MANUAL = "manual"                # User-defined grouping


class DocumentRole(str, Enum):
    """Role of a file within a document group."""

    SOURCE_CAD = "source_cad"       # Original CAD source file (Creo .prt, .asm)
    DRAWING_PDF = "drawing_pdf"      # PDF drawing export
    DRAWING_DXF = "drawing_dxf"      # DXF drawing export
    UDF = "udf"                     # User Defined Feature file


class ExtractionSourceType(str, Enum):
    """Source type for extracted metadata."""

    PDF = "pdf"
    DXF = "dxf"
    CREO_PART = "creo_part"
    CREO_ASM = "creo_asm"
    AUTOCAD = "autocad"


class ExtractionStatus(str, Enum):
    """Status of extraction jobs."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DimensionType(str, Enum):
    """Types of dimensions extracted from drawings."""

    LINEAR = "linear"
    ANGULAR = "angular"
    RADIAL = "radial"
    DIAMETER = "diameter"
    ORDINATE = "ordinate"
    ARC_LENGTH = "arc_length"
    TOLERANCE = "tolerance"


class ToleranceType(str, Enum):
    """Tolerance types for dimensions."""

    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"
    LIMITS = "limits"
    BASIC = "basic"
    REFERENCE = "reference"


# =============================================================================
# Models
# =============================================================================


class DocumentGroup(BaseModel):
    """
    Master record for a logical set of linked engineering files.

    Groups related files (PDFs, DXFs, CAD models) that represent
    the same engineering document or assembly.
    """

    __tablename__: str = "document_groups"  # type: ignore[assignment]
    __table_args__ = {"schema": "pybase"}

    # Identity fields
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Group name (often derived from basename)",
    )
    project_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Extracted project/job code (e.g., PRJ-2024-001)",
    )
    item_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Part/item number from filename",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="User-provided or auto-generated description",
    )

    # Linking metadata
    linking_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=LinkingMethod.AUTO_FILENAME.value,
        doc="How this group was created",
    )
    linking_confidence: Mapped[float] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        default=1.0,
        doc="Confidence score 0.0-1.0",
    )
    needs_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="Flag for groups requiring human verification",
    )

    # Relationships
    members: Mapped[list["DocumentGroupMember"]] = relationship(
        "DocumentGroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_document_groups_name", "name"),
        Index("ix_document_groups_project_code", "project_code"),
        Index("ix_document_groups_item_number", "item_number"),
        Index("ix_document_groups_needs_review", "needs_review"),
        Index("ix_document_groups_created_at", "created_at"),
        {"schema": "pybase"},
    )

    def __repr__(self) -> str:
        return f"<DocumentGroup {self.name} ({self.linking_method})>"


class DocumentGroupMember(BaseModel):
    """
    Junction table linking files to DocumentGroups.

    Supports polymorphic references to CloudFiles (INTEGER ID) and
    cad_models (String/UUID ID). Exactly one foreign key must be non-null.
    """

    __tablename__: str = "document_group_members"  # type: ignore[assignment]
    __table_args__ = {"schema": "pybase"}

    # Parent group reference
    group_id: Mapped[str] = mapped_column(
        ForeignKey("pybase.document_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Polymorphic file references (exactly one must be non-null)
    # CloudFiles.ID is INTEGER in the database
    cloud_file_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="FK to CloudFiles.ID (INTEGER type)",
    )
    # cad_models.id is text/UUID in the database
    cad_model_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("pybase.cad_models.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    udf_definition_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        doc="FK to udf_definitions.id (future table)",
    )

    # Member metadata
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Role of this file in the group",
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Marks the primary/source file in a group",
    )

    # Relationships
    group: Mapped["DocumentGroup"] = relationship(
        "DocumentGroup",
        back_populates="members",
    )

    # Indexes
    __table_args__ = (
        Index("ix_dgm_group_id", "group_id"),
        Index("ix_dgm_cloud_file_id", "cloud_file_id"),
        Index("ix_dgm_cad_model_id", "cad_model_id"),
        Index("ix_dgm_role", "role"),
        Index("ix_dgm_unique_group_cloud", "group_id", "cloud_file_id", unique=True),
        Index("ix_dgm_unique_group_cad", "group_id", "cad_model_id", unique=True),
        {"schema": "pybase"},
    )

    def __repr__(self) -> str:
        return f"<DocumentGroupMember group={self.group_id} role={self.role}>"


class ExtractedMetadata(BaseModel, TimestampMixin):
    """
    Unified extraction tracking with raw JSONB storage.

    Tracks extraction status and results for all document types
    (PDF, DXF, CAD). Stores complete extraction output as JSONB
    for flexible querying.
    """

    __tablename__: str = "extracted_metadata"  # type: ignore[assignment]
    __table_args__ = {"schema": "pybase"}

    # Source references (one or none)
    # CloudFiles.ID is INTEGER
    cloud_file_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="FK to CloudFiles.ID (INTEGER type)",
    )
    # cad_models.id is text/UUID
    cad_model_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("pybase.cad_models.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Source identification
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Type of source file",
    )

    # Extraction tracking
    extraction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="e.g., full, dimensions_only, tables_only",
    )
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        doc="When extraction was performed",
    )
    extraction_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ExtractionStatus.PENDING.value,
        index=True,
        doc="Current extraction status",
    )
    extraction_completeness: Mapped[float | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        doc="Quality score 0.0-1.0 indicating extraction coverage",
    )

    # Raw extracted data
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Complete extraction output as JSONB",
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if extraction failed",
    )
    worker_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="ID of worker that processed this file",
    )

    # Summary flags for quick filtering
    has_dimensions: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="True if dimensions were extracted",
    )
    has_parameters: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="True if parameters were extracted",
    )
    has_bom: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="True if BOM was extracted",
    )
    has_feature_tree: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="True if feature tree was extracted",
    )

    # Summary counts for statistics
    dimension_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of dimensions extracted",
    )
    parameter_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of parameters extracted",
    )
    feature_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of features extracted",
    )

    # Relationships
    dimensions: Mapped[list["ExtractedDimension"]] = relationship(
        "ExtractedDimension",
        back_populates="metadata",
        cascade="all, delete-orphan",
    )
    parameters: Mapped[list["ExtractedParameter"]] = relationship(
        "ExtractedParameter",
        back_populates="metadata",
        cascade="all, delete-orphan",
    )
    materials: Mapped[list["ExtractedMaterial"]] = relationship(
        "ExtractedMaterial",
        back_populates="metadata",
        cascade="all, delete-orphan",
    )
    bom_items: Mapped[list["ExtractedBOMItem"]] = relationship(
        "ExtractedBOMItem",
        back_populates="metadata",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_em_cloud_file_id", "cloud_file_id"),
        Index("ix_em_cad_model_id", "cad_model_id"),
        Index("ix_em_source_type", "source_type"),
        Index("ix_em_extraction_status", "extraction_status"),
        Index("ix_em_extracted_at", "extracted_at"),
        Index("ix_em_has_dimensions", "has_dimensions"),
        Index("ix_em_has_bom", "has_bom"),
        Index("ix_em_raw_data", "raw_data", postgresql_using="gin"),
        {"schema": "pybase"},
    )

    def __repr__(self) -> str:
        return f"<ExtractedMetadata {self.id} ({self.extraction_status})>"

    def get_raw_data(self) -> dict[str, Any]:
        """Parse raw_data JSONB."""
        return self.raw_data or {}

    def set_raw_data(self, data: dict[str, Any]) -> None:
        """Set raw_data from dict."""
        self.raw_data = data


class ExtractedDimension(BaseModel):
    """
    Searchable index of dimensional data from drawings.

    Stores measurements extracted from PDF/DXF drawings with
    tolerance information for precise engineering queries.
    """

    __tablename__: str = "extracted_dimensions"  # type: ignore[assignment]
    __table_args__ = {"schema": "pybase"}

    # Parent references
    metadata_id: Mapped[str] = mapped_column(
        ForeignKey("pybase.extracted_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # CloudFiles.ID is INTEGER
    cloud_file_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="Denormalized FK for faster queries",
    )

    # Dimension value
    value: Mapped[float] = mapped_column(
        Numeric(15, 6),
        nullable=False,
        index=True,
        doc="Numeric value with high precision",
    )
    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="mm",
        doc="Unit of measure",
    )

    # Tolerance data
    tolerance_plus: Mapped[float | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
        doc="Upper tolerance (+)",
    )
    tolerance_minus: Mapped[float | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
        doc="Lower tolerance (-)",
    )
    tolerance_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Type of tolerance",
    )

    # Dimension metadata
    label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Dimension label/callout",
    )
    dimension_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=DimensionType.LINEAR.value,
        doc="Type of dimension",
    )
    layer: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="DXF layer name",
    )
    feature_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Associated CAD feature ID",
    )
    source_page: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Page number in PDF",
    )

    # Position data (optional)
    position_x: Mapped[float | None] = mapped_column(
        Numeric(15, 6),
        nullable=True,
        doc="X coordinate on drawing",
    )
    position_y: Mapped[float | None] = mapped_column(
        Numeric(15, 6),
        nullable=True,
        doc="Y coordinate on drawing",
    )

    # Relationships
    metadata: Mapped["ExtractedMetadata"] = relationship(
        "ExtractedMetadata",
        back_populates="dimensions",
    )

    # Indexes
    __table_args__ = (
        Index("ix_ed_metadata_id", "metadata_id"),
        Index("ix_ed_cloud_file_id", "cloud_file_id"),
        Index("ix_ed_value", "value"),
        Index("ix_ed_value_unit", "value", "unit"),
        Index("ix_ed_label", "label"),
        Index("ix_ed_dimension_type", "dimension_type"),
        Index("ix_ed_layer", "layer"),
        Index("ix_ed_value_range", "value", "tolerance_plus", "tolerance_minus"),
        Index("ix_ed_label_trgm", "label", postgresql_using="gin", postgresql_ops={"label": "gin_trgm_ops"}),
        {"schema": "pybase"},
    )

    def __repr__(self) -> str:
        return f"<ExtractedDimension {self.value}{self.unit}>"


class ExtractedParameter(BaseModel):
    """
    Searchable index of CAD parameters and key-value metadata.

    Stores parameters extracted from CAD models (Creo, etc.)
    including designated parameters and custom properties.
    """

    __tablename__: str = "extracted_parameters"  # type: ignore[assignment]
    __table_args__ = {"schema": "pybase"}

    # Parent references
    metadata_id: Mapped[str] = mapped_column(
        ForeignKey("pybase.extracted_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # cad_models.id is text/UUID
    cad_model_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("pybase.cad_models.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Denormalized FK for faster queries",
    )

    # Parameter identity
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Parameter name",
    )
    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Parameter value as text",
    )
    value_numeric: Mapped[float | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
        index=True,
        doc="Numeric representation if applicable",
    )
    value_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="string",
        doc="string, number, boolean, date",
    )

    # Categorization
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="e.g., material, weight, finish, custom",
    )
    is_designated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="Creo designated parameter flag",
    )
    units: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Units if applicable",
    )

    # Relationships
    metadata: Mapped["ExtractedMetadata"] = relationship(
        "ExtractedMetadata",
        back_populates="parameters",
    )

    # Indexes
    __table_args__ = (
        Index("ix_ep_metadata_id", "metadata_id"),
        Index("ix_ep_cad_model_id", "cad_model_id"),
        Index("ix_ep_name", "name"),
        Index("ix_ep_value", "value"),
        Index("ix_ep_value_numeric", "value_numeric"),
        Index("ix_ep_category", "category"),
        Index("ix_ep_is_designated", "is_designated"),
        Index("ix_ep_name_value", "name", "value"),
        Index("ix_ep_name_trgm", "name", postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),
        Index("ix_ep_value_trgm", "value", postgresql_using="gin", postgresql_ops={"value": "gin_trgm_ops"}),
        {"schema": "pybase"},
    )

    def __repr__(self) -> str:
        return f"<ExtractedParameter {self.name}={self.value}>"


class ExtractedMaterial(BaseModel):
    """
    Material specifications extracted from drawings and CAD.

    Stores material names, specifications, and properties for
    searchability and cross-referencing.
    """

    __tablename__: str = "extracted_materials"  # type: ignore[assignment]
    __table_args__ = {"schema": "pybase"}

    # Parent references
    metadata_id: Mapped[str] = mapped_column(
        ForeignKey("pybase.extracted_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # CloudFiles.ID is INTEGER
    cloud_file_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="Denormalized FK for faster queries",
    )

    # Material identification
    material_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Material name (e.g., 304 Stainless Steel)",
    )
    material_spec: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Specification (e.g., ASTM A240)",
    )

    # Material properties
    finish: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Surface finish specification",
    )
    thickness: Mapped[float | None] = mapped_column(
        Numeric(10, 4),
        nullable=True,
        doc="Material thickness",
    )
    thickness_unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="mm",
        doc="Thickness unit",
    )

    # Additional properties as JSONB
    properties: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Extended properties (density, hardness, etc.)",
    )

    # Relationships
    metadata: Mapped["ExtractedMetadata"] = relationship(
        "ExtractedMetadata",
        back_populates="materials",
    )

    # Indexes
    __table_args__ = (
        Index("ix_emat_metadata_id", "metadata_id"),
        Index("ix_emat_cloud_file_id", "cloud_file_id"),
        Index("ix_emat_material_name", "material_name"),
        Index("ix_emat_material_spec", "material_spec"),
        Index("ix_emat_finish", "finish"),
        Index("ix_emat_properties", "properties", postgresql_using="gin"),
        Index(
            "ix_emat_material_name_trgm",
            "material_name",
            postgresql_using="gin",
            postgresql_ops={"material_name": "gin_trgm_ops"},
        ),
        {"schema": "pybase"},
    )

    def __repr__(self) -> str:
        return f"<ExtractedMaterial {self.material_name}>"

    def get_properties(self) -> dict[str, Any]:
        """Parse properties JSONB."""
        return self.properties or {}

    def set_properties(self, props: dict[str, Any]) -> None:
        """Set properties from dict."""
        self.properties = props


class ExtractedBOMItem(BaseModel):
    """
    Bill of Materials entries extracted from drawings.

    Stores component lists from engineering drawings for
    BOM search and aggregation.
    """

    __tablename__: str = "extracted_bom_items"  # type: ignore[assignment]
    __table_args__ = {"schema": "pybase"}

    # Parent reference
    metadata_id: Mapped[str] = mapped_column(
        ForeignKey("pybase.extracted_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # BOM item data
    item_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        doc="Item/find number in BOM",
    )
    part_number: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Part number",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Part description",
    )
    quantity: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=1.0,
        doc="Quantity required",
    )

    # Additional fields
    material: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Material specification",
    )
    source_table: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Name/ID of source BOM table",
    )

    # Extended properties as JSONB
    properties: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="Additional BOM columns as JSONB",
    )

    # Relationships
    metadata: Mapped["ExtractedMetadata"] = relationship(
        "ExtractedMetadata",
        back_populates="bom_items",
    )

    # Indexes
    __table_args__ = (
        Index("ix_ebom_metadata_id", "metadata_id"),
        Index("ix_ebom_part_number", "part_number"),
        Index("ix_ebom_item_number", "item_number"),
        Index("ix_ebom_material", "material"),
        Index("ix_ebom_properties", "properties", postgresql_using="gin"),
        Index(
            "ix_ebom_part_number_trgm",
            "part_number",
            postgresql_using="gin",
            postgresql_ops={"part_number": "gin_trgm_ops"},
        ),
        {"schema": "pybase"},
    )

    def __repr__(self) -> str:
        return f"<ExtractedBOMItem {self.part_number} (qty:{self.quantity})>"

    def get_properties(self) -> dict[str, Any]:
        """Parse properties JSONB."""
        return self.properties or {}

    def set_properties(self, props: dict[str, Any]) -> None:
        """Set properties from dict."""
        self.properties = props
