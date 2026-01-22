"""
Extraction API endpoints.

Handles file upload and extraction for PDF, DXF, IFC, STEP formats,
and Werk24 API integration for engineering drawings.
"""

import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePath
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from pybase.schemas.extraction import (
    CADExtractionResponse,
    DXFExtractionOptions,
    ExtractedBlockSchema,
    ExtractedBOMSchema,
    ExtractedDimensionSchema,
    ExtractedLayerSchema,
    ExtractedTableSchema,
    ExtractedTextSchema,
    ExtractedTitleBlockSchema,
    ExtractionFormat,
    ExtractionJobCreate,
    ExtractionJobListResponse,
    ExtractionJobResponse,
    GeometrySummarySchema,
    IFCExtractionOptions,
    ImportPreview,
    ImportRequest,
    ImportResponse,
    JobStatus,
    PDFExtractionOptions,
    PDFExtractionResponse,
    STEPExtractionOptions,
    Werk24ExtractionOptions,
    Werk24ExtractionResponse,
)
from pybase.services.import_service import ImportService

router = APIRouter()

# =============================================================================
# Constants
# =============================================================================

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
ALLOWED_EXTENSIONS = {
    ExtractionFormat.PDF: {".pdf"},
    ExtractionFormat.DXF: {".dxf", ".dwg"},
    ExtractionFormat.IFC: {".ifc"},
    ExtractionFormat.STEP: {".stp", ".step"},
    ExtractionFormat.WERK24: {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"},
}


# =============================================================================
# Dependencies
# =============================================================================


def get_import_service() -> ImportService:
    """Get import service instance."""
    return ImportService()


# =============================================================================
# Helper Functions
# =============================================================================


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.

    Strips directory components, special characters, and limits length.
    """
    # Remove any path components, keep only filename
    clean = PurePath(filename).name

    # Remove special characters, keep alphanumeric, dots, hyphens, underscores
    clean = re.sub(r"[^\w\-.]", "_", clean)

    # Limit length to 255 characters
    clean = clean[:255]

    # Ensure we have a valid filename
    if not clean or clean.startswith("."):
        clean = f"file_{uuid.uuid4().hex[:8]}"

    return clean


def validate_file(file: UploadFile, format: ExtractionFormat) -> None:
    """Validate uploaded file."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    ext = Path(sanitize_filename(file.filename)).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS.get(format, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension for {format.value}. Allowed: {ALLOWED_EXTENSIONS[format]}",
        )


async def save_upload_file(file: UploadFile) -> Path:
    """Save uploaded file to temp directory and return path."""
    safe_filename = sanitize_filename(file.filename or "upload")
    suffix = Path(safe_filename).suffix
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        return Path(temp_file.name)
    except Exception as e:
        Path(temp_file.name).unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}",
        )


def result_to_response(result: Any, source_type: str, filename: str) -> dict[str, Any]:
    """Convert extraction result dataclass to response dict."""
    if hasattr(result, "to_dict"):
        # Type ignore since to_dict() method may not have proper return type
        return result.to_dict()  # type: ignore[no-any-return]
    return {
        "source_file": filename,
        "source_type": source_type,
        "success": True,
        "errors": [],
    }


# =============================================================================
# PDF Extraction
# =============================================================================


@router.post(
    "/pdf",
    response_model=PDFExtractionResponse,
    summary="Extract data from PDF",
    description="Upload a PDF file and extract tables, text, and dimensions.",
)
async def extract_pdf(
    file: Annotated[UploadFile, File(description="PDF file to extract from")],
    current_user: CurrentUser,
    extract_tables: Annotated[bool, Form(description="Extract tables")] = True,
    extract_text: Annotated[bool, Form(description="Extract text blocks")] = True,
    extract_dimensions: Annotated[
        bool, Form(description="Extract dimensions (requires OCR)")
    ] = False,
    use_ocr: Annotated[bool, Form(description="Use OCR for scanned documents")] = False,
    ocr_language: Annotated[str, Form(description="OCR language code")] = "eng",
    pages: Annotated[str | None, Form(description="Comma-separated page numbers")] = None,
) -> PDFExtractionResponse:
    """
    Extract data from a PDF file.

    Supports:
    - Table extraction (BOM, parts lists, etc.)
    - Text block extraction
    - Dimension extraction (with OCR)
    - Title block detection
    """
    validate_file(file, ExtractionFormat.PDF)

    temp_path = await save_upload_file(file)
    try:
        # Parse pages parameter
        page_list: list[int] | None = None
        if pages:
            try:
                page_list = [int(p.strip()) for p in pages.split(",")]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid pages format. Use comma-separated integers.",
                )

        # Import extractor (lazy import to handle missing dependencies)
        try:
            from pybase.extraction import PDFExtractor
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"PDF extraction not available. Install pdf dependencies: {e}",
            )

        # Create options
        options = PDFExtractionOptions(
            extract_tables=extract_tables,
            extract_text=extract_text,
            extract_dimensions=extract_dimensions,
            use_ocr=use_ocr,
            ocr_language=ocr_language,
            pages=page_list,
        )

        # Extract - PDFExtractor extract method signature matches options
        extractor = PDFExtractor()
        result = extractor.extract(
            str(temp_path),
            extract_tables=options.extract_tables,
            extract_text=options.extract_text,
            extract_dimensions=options.extract_dimensions,
            extract_title_block=False,  # Title block extraction not currently implemented
            pages=options.pages,
        )
        # OCR currently not implemented in PDFExtractor - needs Phase 3 work

        # Convert to response - convert dataclass objects to Pydantic schema objects
        return PDFExtractionResponse(
            source_file=file.filename or "unknown.pdf",
            source_type="pdf",
            success=result.success,
            tables=[
                ExtractedTableSchema(
                    headers=t.headers,
                    rows=t.rows,
                    page=t.page,
                    confidence=t.confidence,
                    bbox=t.bbox,
                    num_rows=t.num_rows,
                    num_columns=t.num_columns,
                )
                for t in result.tables
            ],
            dimensions=[
                ExtractedDimensionSchema(
                    value=d.value,
                    unit=d.unit,
                    tolerance_plus=d.tolerance_plus,
                    tolerance_minus=d.tolerance_minus,
                    dimension_type=d.dimension_type,
                    label=d.label,
                    page=d.page,
                    confidence=d.confidence,
                    bbox=d.bbox,
                )
                for d in result.dimensions
            ],
            text_blocks=[
                ExtractedTextSchema(
                    text=t.text,
                    page=t.page,
                    confidence=t.confidence,
                    bbox=t.bbox,
                    font_size=t.font_size,
                    is_title=t.is_title,
                )
                for t in result.text_blocks
            ],
            title_block=(
                ExtractedTitleBlockSchema(
                    drawing_number=result.title_block.drawing_number,
                    title=result.title_block.title,
                    revision=result.title_block.revision,
                    date=result.title_block.date,
                    author=result.title_block.author,
                    company=result.title_block.company,
                    scale=result.title_block.scale,
                    sheet=result.title_block.sheet,
                    material=result.title_block.material,
                    finish=result.title_block.finish,
                    custom_fields=result.title_block.custom_fields,
                    confidence=result.title_block.confidence,
                )
                if result.title_block
                else None
            ),
            bom=(
                ExtractedBOMSchema(
                    items=result.bom.items,
                    headers=result.bom.headers,
                    total_items=result.bom.total_items or len(result.bom.items),
                    confidence=result.bom.confidence,
                )
                if result.bom
                else None
            ),
            metadata=result.metadata,
            errors=result.errors,
            warnings=result.warnings,
        )
    finally:
        temp_path.unlink(missing_ok=True)


# =============================================================================
# DXF Extraction
# =============================================================================


@router.post(
    "/dxf",
    response_model=CADExtractionResponse,
    summary="Extract data from DXF",
    description="Upload a DXF file and extract layers, blocks, dimensions, and text.",
)
async def extract_dxf(
    file: Annotated[UploadFile, File(description="DXF file to extract from")],
    current_user: CurrentUser,
    extract_layers: Annotated[bool, Form(description="Extract layer info")] = True,
    extract_blocks: Annotated[bool, Form(description="Extract block definitions")] = True,
    extract_dimensions: Annotated[bool, Form(description="Extract dimensions")] = True,
    extract_text: Annotated[bool, Form(description="Extract text entities")] = True,
    extract_title_block: Annotated[bool, Form(description="Extract title block")] = True,
    extract_geometry: Annotated[bool, Form(description="Extract geometry summary")] = False,
) -> CADExtractionResponse:
    """
    Extract data from a DXF/DWG file.

    Supports:
    - Layer extraction with properties
    - Block definitions and attributes
    - Dimension extraction (linear, angular, etc.)
    - TEXT/MTEXT extraction
    - Title block detection
    - Geometry summary
    """
    validate_file(file, ExtractionFormat.DXF)

    temp_path = await save_upload_file(file)
    try:
        # Import parser
        try:
            from pybase.extraction import DXFParser
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"DXF extraction not available. Install cad dependencies (ezdxf): {e}",
            )

        # Create options
        options = DXFExtractionOptions(
            extract_layers=extract_layers,
            extract_blocks=extract_blocks,
            extract_dimensions=extract_dimensions,
            extract_text=extract_text,
            extract_title_block=extract_title_block,
            extract_geometry=extract_geometry,
            layer_filter=None,  # Explicitly set optional field for strict type checking
        )

        # Extract
        parser = DXFParser()
        result = parser.parse(
            str(temp_path),
            extract_layers=options.extract_layers,
            extract_blocks=options.extract_blocks,
            extract_dimensions=options.extract_dimensions,
            extract_text=options.extract_text,
            extract_title_block=options.extract_title_block,
            extract_geometry=options.extract_geometry,
        )

        # Convert to response - convert dataclass objects to Pydantic schema objects
        return CADExtractionResponse(
            source_file=file.filename or "unknown.dxf",
            source_type="dxf",
            success=result.success,
            layers=[
                ExtractedLayerSchema(
                    name=l.name,
                    color=l.color,
                    linetype=l.linetype,
                    lineweight=l.lineweight,
                    is_on=l.is_on,
                    is_frozen=l.is_frozen,
                    is_locked=l.is_locked,
                    entity_count=l.entity_count,
                )
                for l in result.layers
            ],
            blocks=[
                ExtractedBlockSchema(
                    name=b.name,
                    insert_count=b.insert_count,
                    base_point=b.base_point,
                    attributes=b.attributes,
                    entity_count=b.entity_count,
                )
                for b in result.blocks
            ],
            dimensions=[
                ExtractedDimensionSchema(
                    value=d.value,
                    unit=d.unit,
                    tolerance_plus=d.tolerance_plus,
                    tolerance_minus=d.tolerance_minus,
                    dimension_type=d.dimension_type,
                    label=d.label,
                    page=d.page,
                    confidence=d.confidence,
                    bbox=d.bbox,
                )
                for d in result.dimensions
            ],
            text_blocks=[
                ExtractedTextSchema(
                    text=t.text,
                    page=t.page,
                    confidence=t.confidence,
                    bbox=t.bbox,
                    font_size=t.font_size,
                    is_title=t.is_title,
                )
                for t in result.text_blocks
            ],
            title_block=(
                ExtractedTitleBlockSchema(
                    drawing_number=result.title_block.drawing_number,
                    title=result.title_block.title,
                    revision=result.title_block.revision,
                    date=result.title_block.date,
                    author=result.title_block.author,
                    company=result.title_block.company,
                    scale=result.title_block.scale,
                    sheet=result.title_block.sheet,
                    material=result.title_block.material,
                    finish=result.title_block.finish,
                    custom_fields=result.title_block.custom_fields,
                    confidence=result.title_block.confidence,
                )
                if result.title_block
                else None
            ),
            geometry_summary=(
                GeometrySummarySchema(
                    lines=result.geometry_summary.lines,
                    circles=result.geometry_summary.circles,
                    arcs=result.geometry_summary.arcs,
                    polylines=result.geometry_summary.polylines,
                    splines=result.geometry_summary.splines,
                    ellipses=result.geometry_summary.ellipses,
                    points=result.geometry_summary.points,
                    hatches=result.geometry_summary.hatches,
                    solids=result.geometry_summary.solids,
                    meshes=result.geometry_summary.meshes,
                    total_entities=result.geometry_summary.total_entities,
                )
                if result.geometry_summary
                else None
            ),
            entities=[e.to_dict() for e in result.entities],
            metadata=result.metadata,
            errors=result.errors,
            warnings=result.warnings,
        )
    finally:
        temp_path.unlink(missing_ok=True)


# =============================================================================
# IFC Extraction
# =============================================================================


@router.post(
    "/ifc",
    response_model=CADExtractionResponse,
    summary="Extract data from IFC",
    description="Upload an IFC/BIM file and extract building elements and properties.",
)
async def extract_ifc(
    file: Annotated[UploadFile, File(description="IFC file to extract from")],
    current_user: CurrentUser,
    extract_properties: Annotated[bool, Form(description="Extract element properties")] = True,
    extract_quantities: Annotated[bool, Form(description="Extract quantities")] = True,
    extract_materials: Annotated[bool, Form(description="Extract materials")] = True,
    extract_spatial: Annotated[bool, Form(description="Extract spatial structure")] = True,
    element_types: Annotated[
        str | None, Form(description="Comma-separated IFC types filter")
    ] = None,
) -> CADExtractionResponse:
    """
    Extract data from an IFC (BIM) file.

    Supports:
    - Building element extraction (walls, doors, windows, etc.)
    - Property sets and quantities
    - Material assignments
    - Spatial structure (building, floors, spaces)
    """
    validate_file(file, ExtractionFormat.IFC)

    temp_path = await save_upload_file(file)
    try:
        # Import parser
        try:
            from pybase.extraction import IFCParser
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"IFC extraction not available. Install cad dependencies (ifcopenshell): {e}",
            )

        # Parse element types
        type_list: list[str] | None = None
        if element_types:
            type_list = [t.strip() for t in element_types.split(",")]

        # Create options
        options = IFCExtractionOptions(
            extract_properties=extract_properties,
            extract_quantities=extract_quantities,
            extract_materials=extract_materials,
            extract_spatial_structure=extract_spatial,
            element_types=type_list,
        )

        # Extract - Initialize parser with options
        parser = IFCParser(
            extract_properties=options.extract_properties,
            extract_quantities=options.extract_quantities,
            extract_materials=options.extract_materials,
        )
        result = parser.parse(str(temp_path))

        # Convert to response
        return CADExtractionResponse(
            source_file=file.filename or "unknown.ifc",
            source_type="ifc",
            success=result.success,
            layers=[],  # IFC doesn't have layers in the traditional sense
            blocks=[],
            dimensions=[],
            text_blocks=[],
            title_block=None,
            geometry_summary=None,
            entities=[e.to_dict() for e in result.entities],
            metadata=result.metadata,
            errors=result.errors,
            warnings=result.warnings,
        )
    finally:
        temp_path.unlink(missing_ok=True)


# =============================================================================
# STEP Extraction
# =============================================================================


@router.post(
    "/step",
    response_model=CADExtractionResponse,
    summary="Extract data from STEP",
    description="Upload a STEP file and extract assembly structure and part information.",
)
async def extract_step(
    file: Annotated[UploadFile, File(description="STEP file to extract from")],
    current_user: CurrentUser,
    extract_assembly: Annotated[bool, Form(description="Extract assembly structure")] = True,
    extract_parts: Annotated[bool, Form(description="Extract part information")] = True,
    calculate_volumes: Annotated[bool, Form(description="Calculate volumes")] = True,
    calculate_areas: Annotated[bool, Form(description="Calculate surface areas")] = True,
    count_shapes: Annotated[bool, Form(description="Count geometric shapes")] = True,
) -> CADExtractionResponse:
    """
    Extract data from a STEP file.

    Supports:
    - Assembly structure extraction
    - Part information with bounding boxes
    - Volume and surface area calculation
    - Geometric shape counting
    """
    validate_file(file, ExtractionFormat.STEP)

    temp_path = await save_upload_file(file)
    try:
        # Import parser
        try:
            from pybase.extraction import STEPParser
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"STEP extraction not available. Install cad dependencies (OCP/build123d): {e}",
            )

        # Create options
        options = STEPExtractionOptions(
            extract_assembly=extract_assembly,
            extract_parts=extract_parts,
            calculate_volumes=calculate_volumes,
            calculate_areas=calculate_areas,
            count_shapes=count_shapes,
        )

        # Extract - STEPParser only accepts compute_mass_properties in __init__
        # Mass properties include volumes and surface areas
        parser = STEPParser(
            compute_mass_properties=(options.calculate_volumes or options.calculate_areas)
        )
        result = parser.parse(str(temp_path))

        # Convert to response - convert dataclass objects to Pydantic schema objects
        return CADExtractionResponse(
            source_file=file.filename or "unknown.step",
            source_type="step",
            success=result.success,
            layers=[],
            blocks=[],
            dimensions=[],
            text_blocks=[],
            title_block=None,
            geometry_summary=(
                GeometrySummarySchema(
                    lines=result.geometry_summary.lines,
                    circles=result.geometry_summary.circles,
                    arcs=result.geometry_summary.arcs,
                    polylines=result.geometry_summary.polylines,
                    splines=result.geometry_summary.splines,
                    ellipses=result.geometry_summary.ellipses,
                    points=result.geometry_summary.points,
                    hatches=result.geometry_summary.hatches,
                    solids=result.geometry_summary.solids,
                    meshes=result.geometry_summary.meshes,
                    total_entities=result.geometry_summary.total_entities,
                )
                if result.geometry_summary
                else None
            ),
            entities=[e.to_dict() for e in result.entities],
            metadata=result.metadata,
            errors=result.errors,
            warnings=result.warnings,
        )
    finally:
        temp_path.unlink(missing_ok=True)


# =============================================================================
# Werk24 API Extraction
# =============================================================================


@router.post(
    "/werk24",
    response_model=Werk24ExtractionResponse,
    summary="Extract via Werk24 API",
    description="Upload a drawing and extract engineering data via Werk24 AI API.",
)
async def extract_werk24(
    file: Annotated[UploadFile, File(description="Drawing file (PDF/image)")],
    current_user: CurrentUser,
    extract_dimensions: Annotated[bool, Form(description="Extract dimensions")] = True,
    extract_gdt: Annotated[bool, Form(description="Extract GD&T annotations")] = True,
    extract_threads: Annotated[bool, Form(description="Extract thread specs")] = True,
    extract_surface_finish: Annotated[bool, Form(description="Extract surface finish")] = True,
    extract_materials: Annotated[bool, Form(description="Extract materials")] = True,
    extract_title_block: Annotated[bool, Form(description="Extract title block")] = True,
    confidence_threshold: Annotated[
        float, Form(ge=0.0, le=1.0, description="Min confidence")
    ] = 0.7,
) -> Werk24ExtractionResponse:
    """
    Extract engineering data from drawings using Werk24 AI API.

    Requires WERK24_API_KEY environment variable.

    Supports:
    - Dimension extraction with tolerances
    - GD&T (Geometric Dimensioning and Tolerancing)
    - Thread specifications
    - Surface finish requirements
    - Material specifications
    - Title block information
    """
    validate_file(file, ExtractionFormat.WERK24)

    temp_path = await save_upload_file(file)
    try:
        # Import client
        try:
            from pybase.extraction import Werk24Client
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Werk24 extraction not available. Install werk24 dependencies: {e}",
            )

        # Check API key
        from pybase.core.config import settings

        if not getattr(settings, "WERK24_API_KEY", None):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Werk24 API key not configured. Set WERK24_API_KEY environment variable.",
            )

        # Create options
        options = Werk24ExtractionOptions(
            extract_dimensions=extract_dimensions,
            extract_gdt=extract_gdt,
            extract_threads=extract_threads,
            extract_surface_finish=extract_surface_finish,
            extract_materials=extract_materials,
            extract_title_block=extract_title_block,
            confidence_threshold=confidence_threshold,
        )

        # Build ask_types list based on extraction options
        from pybase.extraction.werk24.client import Werk24AskType

        ask_types: list[Werk24AskType] = []
        if options.extract_dimensions:
            ask_types.append(Werk24AskType.DIMENSIONS)
        if options.extract_gdt:
            ask_types.append(Werk24AskType.GDTS)
        if options.extract_threads:
            ask_types.append(Werk24AskType.THREADS)
        if options.extract_surface_finish:
            ask_types.append(Werk24AskType.SURFACE_FINISH)
        if options.extract_materials:
            ask_types.append(Werk24AskType.MATERIAL)
        if options.extract_title_block:
            ask_types.append(Werk24AskType.TITLE_BLOCK)

        # Extract - use extract_async since we're in an async function
        client = Werk24Client()
        result = await client.extract_async(str(temp_path), ask_types=ask_types)

        # Filter by confidence and convert to ExtractedDimensionSchema
        filtered_dimensions = [
            d for d in result.dimensions if d.confidence >= options.confidence_threshold
        ]
        dimension_schemas = [
            ExtractedDimensionSchema(
                value=ed.value,
                unit=ed.unit,
                tolerance_plus=ed.tolerance_plus,
                tolerance_minus=ed.tolerance_minus,
                dimension_type=ed.dimension_type,
                label=ed.label,
                page=ed.page,
                confidence=ed.confidence,
                bbox=ed.bbox,
            )
            for d in filtered_dimensions
            for ed in [d.to_extracted_dimension()]
        ]

        # Convert to response
        return Werk24ExtractionResponse(
            source_file=file.filename or "unknown",
            source_type="werk24",
            success=result.success,
            dimensions=dimension_schemas,
            gdt_annotations=[g.to_dict() for g in result.gdts],
            threads=[t.to_dict() for t in result.threads],
            surface_finishes=[s.to_dict() for s in result.surface_finishes],
            materials=result.materials,
            title_block=(
                ExtractedTitleBlockSchema(
                    drawing_number=result.title_block.drawing_number,
                    title=result.title_block.title,
                    revision=result.title_block.revision,
                    date=result.title_block.date,
                    author=result.title_block.author,
                    company=result.title_block.company,
                    scale=result.title_block.scale,
                    sheet=result.title_block.sheet,
                    material=result.title_block.material,
                    finish=result.title_block.finish,
                    custom_fields=result.title_block.custom_fields,
                    confidence=result.title_block.confidence,
                )
                if result.title_block
                else None
            ),
            metadata=result.metadata,
            errors=result.errors,
            warnings=result.warnings,
        )
    finally:
        temp_path.unlink(missing_ok=True)


# =============================================================================
# Job Management (for async/large file processing)
# =============================================================================


# In-memory job storage (replace with Redis/DB in production)
# Type annotation updated to match ExtractionJobResponse schema fields
_jobs: dict[str, Any] = {}


@router.post(
    "/jobs",
    response_model=ExtractionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create extraction job",
    description="Create an async extraction job for large files.",
)
async def create_extraction_job(
    file: Annotated[UploadFile, File(description="File to extract from")],
    format: Annotated[ExtractionFormat, Form(description="Extraction format")],
    current_user: CurrentUser,
    target_table_id: Annotated[str | None, Form(description="Target table ID")] = None,
) -> ExtractionJobResponse:
    """
    Create an asynchronous extraction job.

    Use this for large files that may take time to process.
    Poll the job status endpoint to check progress.
    """
    validate_file(file, format)

    job_id = uuid.uuid4()

    # In production, save file to object storage and queue job
    # For now, just create job record
    job_response = ExtractionJobResponse(
        id=job_id,
        status=JobStatus.PENDING,
        format=format,
        filename=file.filename or "unknown",
        file_size=file.size or 0,
        options={},
        target_table_id=UUID(target_table_id) if target_table_id else None,
        progress=0,
        result=None,
        error_message=None,
        created_at=datetime.now(timezone.utc),
        started_at=None,
        completed_at=None,
    )

    # Store job data for later retrieval (convert to dict for storage)
    _jobs[str(job_id)] = {
        "id": job_id,
        "status": JobStatus.PENDING,
        "format": format,
        "filename": file.filename or "unknown",
        "file_size": file.size or 0,
        "options": {},
        "target_table_id": UUID(target_table_id) if target_table_id else None,
        "progress": 0,
        "result": None,
        "error_message": None,
        "created_at": datetime.now(timezone.utc),
        "started_at": None,
        "completed_at": None,
    }

    return job_response


@router.get(
    "/jobs/{job_id}",
    response_model=ExtractionJobResponse,
    summary="Get job status",
)
async def get_extraction_job(
    job_id: str,
    current_user: CurrentUser,
) -> ExtractionJobResponse:
    """Get extraction job status and result."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    # Type ignore for in-memory storage - will be replaced with DB in production
    return ExtractionJobResponse(**job)


@router.get(
    "/jobs",
    response_model=ExtractionJobListResponse,
    summary="List extraction jobs",
)
async def list_extraction_jobs(
    current_user: CurrentUser,
    status_filter: Annotated[JobStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ExtractionJobListResponse:
    """List extraction jobs with optional status filter."""
    jobs = list(_jobs.values())

    if status_filter:
        jobs = [j for j in jobs if j["status"] == status_filter]

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated = jobs[start:end]

    return ExtractionJobListResponse(
        items=[ExtractionJobResponse(**j) for j in paginated],
        total=len(jobs),
        page=page,
        page_size=page_size,
    )


@router.delete(
    "/jobs/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel/delete job",
)
async def delete_extraction_job(
    job_id: str,
    current_user: CurrentUser,
) -> None:
    """Cancel a pending job or delete a completed job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job["status"] == JobStatus.PROCESSING:
        job["status"] = JobStatus.CANCELLED
    else:
        del _jobs[job_id]


# =============================================================================
# Import to Table
# =============================================================================


@router.post(
    "/jobs/{job_id}/preview",
    response_model=ImportPreview,
    summary="Preview import",
)
async def preview_import(
    job_id: str,
    table_id: Annotated[str, Query(description="Target table ID")],
    current_user: CurrentUser,
    db: DbSession,
) -> ImportPreview:
    """
    Preview how extracted data will map to table fields.

    Returns suggested field mappings and sample data.
    """
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job["status"] != JobStatus.COMPLETED or not job["result"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job not completed or has no results",
        )

    # TODO: Implement actual preview logic
    # - Fetch table schema
    # - Analyze extracted data structure
    # - Suggest field mappings

    return ImportPreview(
        source_fields=["field1", "field2"],  # Placeholder
        target_fields=[],
        suggested_mapping={},
        sample_data=[],
        total_records=0,
    )


@router.post(
    "/import",
    response_model=ImportResponse,
    summary="Import extracted data",
)
async def import_extracted_data(
    request: ImportRequest,
    current_user: CurrentUser,
    db: DbSession,
    import_service: Annotated[ImportService, Depends(get_import_service)],
) -> ImportResponse:
    """
    Import extracted data into a table.

    Requires completed extraction job and field mapping.
    """
    # Validate job exists and is completed
    job = _jobs.get(str(request.job_id))
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job["status"] != JobStatus.COMPLETED or not job["result"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job not completed or has no results",
        )

    # Get extraction result from job
    extraction_result = job["result"]

    # Import records using ImportService
    # Exceptions (NotFoundError, PermissionDeniedError, ValidationError, ConflictError)
    # are automatically converted to appropriate HTTP responses by FastAPI exception handlers
    result = await import_service.import_records(
        db=db,
        user_id=str(current_user.id),
        import_data=request,
        extraction_result=extraction_result,
    )

    return result
