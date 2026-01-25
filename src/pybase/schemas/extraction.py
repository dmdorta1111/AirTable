"""Extraction schemas for request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ExtractionFormat(str, Enum):
    """Supported extraction formats."""

    PDF = "pdf"
    DXF = "dxf"
    IFC = "ifc"
    STEP = "step"
    WERK24 = "werk24"


class JobStatus(str, Enum):
    """Extraction job status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# --- Request Schemas ---


class PDFExtractionOptions(BaseModel):
    """Options for PDF extraction."""

    extract_tables: bool = Field(default=True, description="Extract tables from PDF")
    extract_text: bool = Field(default=True, description="Extract text blocks")
    extract_dimensions: bool = Field(default=False, description="Extract dimensions (requires OCR)")
    use_ocr: bool = Field(default=False, description="Use OCR for scanned documents")
    ocr_language: str = Field(default="eng", description="OCR language code")
    pages: Optional[list[int]] = Field(None, description="Specific pages to extract (1-indexed)")
    table_detection_strategy: str = Field(
        default="lines", description="Table detection: lines|text|stream"
    )


class DXFExtractionOptions(BaseModel):
    """Options for DXF extraction."""

    extract_layers: bool = Field(default=True, description="Extract layer information")
    extract_blocks: bool = Field(default=True, description="Extract block definitions")
    extract_dimensions: bool = Field(default=True, description="Extract dimensions")
    extract_text: bool = Field(default=True, description="Extract text/MTEXT entities")
    extract_title_block: bool = Field(default=True, description="Attempt title block extraction")
    extract_geometry: bool = Field(default=False, description="Extract geometry summary")
    include_model_space: bool = Field(default=True, description="Include model space entities")
    include_paper_space: bool = Field(default=True, description="Include paper space entities")
    layer_filter: Optional[list[str]] = Field(None, description="Filter to specific layers")


class IFCExtractionOptions(BaseModel):
    """Options for IFC extraction."""

    extract_properties: bool = Field(default=True, description="Extract element properties")
    extract_quantities: bool = Field(default=True, description="Extract quantities (area, volume)")
    extract_materials: bool = Field(default=True, description="Extract material assignments")
    extract_spatial_structure: bool = Field(
        default=True, description="Extract building/floor structure"
    )
    element_types: Optional[list[str]] = Field(
        None, description="Filter to specific IFC element types (e.g., IfcWall, IfcDoor)"
    )
    include_geometry: bool = Field(default=False, description="Include geometry information")


class STEPExtractionOptions(BaseModel):
    """Options for STEP extraction."""

    extract_assembly: bool = Field(default=True, description="Extract assembly structure")
    extract_parts: bool = Field(default=True, description="Extract part information")
    calculate_volumes: bool = Field(default=True, description="Calculate part volumes")
    calculate_areas: bool = Field(default=True, description="Calculate surface areas")
    calculate_centroids: bool = Field(default=False, description="Calculate part centroids")
    count_shapes: bool = Field(default=True, description="Count geometric shapes")


class Werk24ExtractionOptions(BaseModel):
    """Options for Werk24 API extraction."""

    extract_dimensions: bool = Field(default=True, description="Extract dimensions")
    extract_gdt: bool = Field(default=True, description="Extract GD&T annotations")
    extract_threads: bool = Field(default=True, description="Extract thread specifications")
    extract_surface_finish: bool = Field(default=True, description="Extract surface finish")
    extract_materials: bool = Field(default=True, description="Extract material information")
    extract_title_block: bool = Field(default=True, description="Extract title block")
    confidence_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum confidence threshold"
    )


class ExtractionRequest(BaseModel):
    """Generic extraction request."""

    format: ExtractionFormat = Field(..., description="File format to extract")
    options: Optional[dict[str, Any]] = Field(
        default_factory=dict, description="Format-specific options"
    )
    target_table_id: Optional[UUID] = Field(
        None, description="Table ID to import extracted data into"
    )
    field_mapping: Optional[dict[str, str]] = Field(
        None, description="Mapping of extracted fields to table fields"
    )


class BulkExtractionRequest(BaseModel):
    """Request schema for bulk multi-file extraction."""

    file_paths: list[str] = Field(..., description="List of file paths to extract", min_length=1)
    format: Optional[ExtractionFormat] = Field(None, description="Override format detection")
    options: Optional[dict[str, Any]] = Field(
        default_factory=dict, description="Format-specific extraction options"
    )
    target_table_id: Optional[UUID] = Field(
        None, description="Table ID to import extracted data into"
    )
    field_mapping: Optional[dict[str, str]] = Field(
        None, description="Mapping of extracted fields to table fields"
    )
    auto_detect_format: bool = Field(
        default=True, description="Auto-detect file format from extension"
    )
    continue_on_error: bool = Field(
        default=True, description="Continue processing other files if one fails"
    )
    callback_url: Optional[str] = Field(None, description="Webhook URL for completion notification")


# --- Response Schemas ---


class ExtractedTableSchema(BaseModel):
    """Schema for an extracted table."""

    headers: list[str]
    rows: list[list[Any]]
    page: Optional[int] = None
    confidence: float = 1.0
    bbox: Optional[tuple[float, float, float, float]] = None
    num_rows: int
    num_columns: int


class ExtractedDimensionSchema(BaseModel):
    """Schema for an extracted dimension."""

    value: float
    unit: str = "mm"
    tolerance_plus: Optional[float] = None
    tolerance_minus: Optional[float] = None
    dimension_type: str = "linear"
    label: Optional[str] = None
    page: Optional[int] = None
    confidence: float = 1.0
    bbox: Optional[tuple[float, float, float, float]] = None


class ExtractedTextSchema(BaseModel):
    """Schema for extracted text."""

    text: str
    page: Optional[int] = None
    confidence: float = 1.0
    bbox: Optional[tuple[float, float, float, float]] = None
    font_size: Optional[float] = None
    is_title: bool = False


class ExtractedTitleBlockSchema(BaseModel):
    """Schema for extracted title block."""

    drawing_number: Optional[str] = None
    title: Optional[str] = None
    revision: Optional[str] = None
    date: Optional[str] = None
    author: Optional[str] = None
    company: Optional[str] = None
    scale: Optional[str] = None
    sheet: Optional[str] = None
    material: Optional[str] = None
    finish: Optional[str] = None
    custom_fields: dict[str, str] = Field(default_factory=dict)
    confidence: float = 1.0


class ExtractedLayerSchema(BaseModel):
    """Schema for an extracted CAD layer."""

    name: str
    color: Optional[int | str] = None
    linetype: Optional[str] = None
    lineweight: Optional[float] = None
    is_on: bool = True
    is_frozen: bool = False
    is_locked: bool = False
    entity_count: int = 0


class ExtractedBlockSchema(BaseModel):
    """Schema for an extracted CAD block."""

    name: str
    insert_count: int = 0
    base_point: Optional[tuple[float, float, float]] = None
    attributes: list[dict[str, Any]] = Field(default_factory=list)
    entity_count: int = 0


class GeometrySummarySchema(BaseModel):
    """Schema for geometry summary."""

    lines: int = 0
    circles: int = 0
    arcs: int = 0
    polylines: int = 0
    splines: int = 0
    ellipses: int = 0
    points: int = 0
    hatches: int = 0
    solids: int = 0
    meshes: int = 0
    total_entities: int = 0


class ExtractedBOMSchema(BaseModel):
    """Schema for extracted Bill of Materials."""

    items: list[dict[str, Any]]
    headers: Optional[list[str]] = None
    total_items: int = 0
    confidence: float = 1.0


class PDFExtractionResponse(BaseModel):
    """Response schema for PDF extraction."""

    source_file: str
    source_type: str = "pdf"
    success: bool
    tables: list[ExtractedTableSchema] = Field(default_factory=list)
    dimensions: list[ExtractedDimensionSchema] = Field(default_factory=list)
    text_blocks: list[ExtractedTextSchema] = Field(default_factory=list)
    title_block: Optional[ExtractedTitleBlockSchema] = None
    bom: Optional[ExtractedBOMSchema] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CADExtractionResponse(BaseModel):
    """Response schema for CAD file extraction."""

    source_file: str
    source_type: str  # dxf, ifc, step
    success: bool
    layers: list[ExtractedLayerSchema] = Field(default_factory=list)
    blocks: list[ExtractedBlockSchema] = Field(default_factory=list)
    dimensions: list[ExtractedDimensionSchema] = Field(default_factory=list)
    text_blocks: list[ExtractedTextSchema] = Field(default_factory=list)
    title_block: Optional[ExtractedTitleBlockSchema] = None
    geometry_summary: Optional[GeometrySummarySchema] = None
    entities: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Werk24ExtractionResponse(BaseModel):
    """Response schema for Werk24 extraction."""

    source_file: str
    source_type: str = "werk24"
    success: bool
    dimensions: list[ExtractedDimensionSchema] = Field(default_factory=list)
    gdt_annotations: list[dict[str, Any]] = Field(default_factory=list)
    threads: list[dict[str, Any]] = Field(default_factory=list)
    surface_finishes: list[dict[str, Any]] = Field(default_factory=list)
    materials: list[dict[str, Any]] = Field(default_factory=list)
    title_block: Optional[ExtractedTitleBlockSchema] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FileExtractionStatus(BaseModel):
    """Status of a single file in bulk extraction."""

    file_path: str = Field(description="Path to the file")
    filename: str = Field(description="Filename")
    format: ExtractionFormat = Field(description="Detected file format")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Extraction status")
    job_id: Optional[UUID] = Field(None, description="Individual extraction job ID")
    progress: int = Field(default=0, ge=0, le=100, description="Progress percentage")
    result: Optional[dict[str, Any]] = Field(None, description="Extraction result")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class BulkExtractionResponse(BaseModel):
    """Response schema for bulk extraction operation."""

    bulk_job_id: UUID = Field(description="Bulk extraction job ID")
    total_files: int = Field(description="Total number of files to process")
    files: list[FileExtractionStatus] = Field(description="Status of each file")
    overall_status: JobStatus = Field(description="Overall bulk job status")
    progress: int = Field(default=0, ge=0, le=100, description="Overall progress percentage")
    files_completed: int = Field(default=0, description="Number of completed files")
    files_failed: int = Field(default=0, description="Number of failed files")
    files_pending: int = Field(default=0, description="Number of pending files")
    created_at: datetime = Field(description="Bulk job creation time")
    started_at: Optional[datetime] = Field(None, description="Bulk job start time")
    completed_at: Optional[datetime] = Field(None, description="Bulk job completion time")
    target_table_id: Optional[UUID] = Field(None, description="Target table ID for import")


# --- Job Schemas ---


class ExtractionJobCreate(BaseModel):
    """Schema for creating an extraction job."""

    format: ExtractionFormat
    options: Optional[dict[str, Any]] = Field(default_factory=dict)
    target_table_id: Optional[UUID] = None
    field_mapping: Optional[dict[str, str]] = None
    callback_url: Optional[str] = Field(None, description="Webhook URL for job completion")


class ExtractionJobResponse(BaseModel):
    """Schema for extraction job response."""

    id: UUID
    status: JobStatus
    format: ExtractionFormat
    filename: str
    file_size: int
    options: dict[str, Any] = Field(default_factory=dict)
    target_table_id: Optional[UUID] = None
    progress: int = Field(default=0, ge=0, le=100, description="Progress percentage")
    result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")
    celery_task_id: Optional[str] = Field(None, description="Celery task ID for tracking")
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ExtractionJobListResponse(BaseModel):
    """Schema for extraction job list response."""

    items: list[ExtractionJobResponse]
    total: int
    page: int
    page_size: int


class JobCleanupResponse(BaseModel):
    """Schema for job cleanup response."""

    deleted_count: int = Field(description="Number of jobs deleted")
    dry_run: bool = Field(description="Whether this was a dry run (no actual deletion)")
    older_than_days: int = Field(description="Jobs older than this many days were cleaned up")
    status_filter: str | None = Field(default=None, description="Status filter applied (if any)")


# --- Import Schemas ---


class ImportPreview(BaseModel):
    """Preview of data to be imported."""

    source_fields: list[str] = Field(description="Fields available in extracted data")
    target_fields: list[dict[str, Any]] = Field(description="Fields in target table")
    suggested_mapping: dict[str, str] = Field(description="Auto-suggested field mapping")
    sample_data: list[dict[str, Any]] = Field(description="Sample rows to preview")
    total_records: int = Field(description="Total records to import")


class ImportRequest(BaseModel):
    """Request to import extracted data."""

    job_id: UUID = Field(description="Extraction job ID")
    table_id: UUID = Field(description="Target table ID")
    field_mapping: dict[str, str] = Field(
        description="Mapping of source fields to target field IDs"
    )
    create_missing_fields: bool = Field(
        default=False, description="Create fields that don't exist in target table"
    )
    skip_errors: bool = Field(default=True, description="Continue import on row errors")


class ImportResponse(BaseModel):
    """Response after import operation."""

    success: bool
    records_imported: int
    records_failed: int
    errors: list[dict[str, Any]] = Field(default_factory=list)
    created_field_ids: list[UUID] = Field(default_factory=list)


class FileImportPreview(BaseModel):
    """Preview of data to be imported from a single file in bulk operation."""

    file_path: str = Field(description="Source file path")
    filename: str = Field(description="Source filename")
    format: ExtractionFormat = Field(description="File format")
    source_fields: list[str] = Field(description="Fields available in this file")
    sample_data: list[dict[str, Any]] = Field(description="Sample rows from this file")
    total_records: int = Field(description="Total records from this file")


class BulkImportPreview(BaseModel):
    """Preview of data to be imported from multiple files."""

    bulk_job_id: UUID = Field(description="Bulk extraction job ID")
    total_files: int = Field(description="Total number of files")
    total_records: int = Field(description="Total records across all files")
    source_fields: list[str] = Field(description="Combined fields from all files")
    target_fields: list[dict[str, Any]] = Field(description="Fields in target table")
    suggested_mapping: dict[str, str] = Field(description="Auto-suggested field mapping")
    sample_data: list[dict[str, Any]] = Field(
        description="Sample rows from all files combined"
    )
    file_previews: list[FileImportPreview] = Field(
        description="Per-file preview breakdowns"
    )
    files_with_data: int = Field(description="Number of files with extractable data")
    files_failed: int = Field(description="Number of files that failed extraction")


class BulkImportRequest(BaseModel):
    """Request to import data from bulk extraction job."""

    bulk_job_id: UUID = Field(description="Bulk extraction job ID")
    table_id: UUID = Field(description="Target table ID")
    field_mapping: dict[str, str] = Field(
        description="Mapping of source fields to target field IDs"
    )
    file_selection: Optional[list[str]] = Field(
        None, description="Optional list of file paths to import (imports all if not specified)"
    )
    create_missing_fields: bool = Field(
        default=False, description="Create fields that don't exist in target table"
    )
    skip_errors: bool = Field(default=True, description="Continue import on row errors")
    include_source_file: bool = Field(
        default=True, description="Add source_file field to imported records"
    )
