"""
Extraction API endpoints.

Handles file upload and extraction for PDF, DXF, IFC, STEP formats,
and Werk24 API integration for engineering drawings.
"""

import json
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePath
from typing import Annotated, Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.api.deps import CurrentSuperuser, CurrentUser, DbSession
from pybase.models.extraction_job import ExtractionJob as ExtractionJobModel
from pybase.services.extraction import ExtractionService
from pybase.schemas.extraction import (
    BOMExtractionOptions,
    BOMExtractionResponse,
    BOMFlatteningStrategy,
    BOMHierarchyMode,
    BulkExtractionRequest,
    BulkExtractionResponse,
    BulkImportPreview,
    BulkImportRequest,
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
    FileExtractionStatus,
    GeometrySummarySchema,
    IFCExtractionOptions,
    ImportPreview,
    ImportRequest,
    ImportResponse,
    JobCleanupResponse,
    JobStatsResponse,
    JobStatus,
    PDFExtractionOptions,
    PDFExtractionResponse,
    STEPExtractionOptions,
    Werk24ExtractionOptions,
    Werk24ExtractionResponse,
)

router = APIRouter()

# =============================================================================
# Dependencies
# =============================================================================


def get_extraction_service() -> ExtractionService:
    """Get extraction service instance."""
    return ExtractionService()


def get_extraction_job_service() -> "ExtractionJobService":
    """Get extraction job service instance."""
    from pybase.services.extraction_job import ExtractionJobService

    return ExtractionJobService()


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
    summary="Extract data from PDF documents",
    description="Upload a PDF file and extract tables, text blocks, dimensions, and title blocks.",
    tags=["PDF Extraction"],
    responses={
        200: {
            "description": "Extraction successful",
            "content": {
                "application/json": {
                    "example": {
                        "source_file": "parts_list.pdf",
                        "source_type": "pdf",
                        "success": True,
                        "tables": [
                            {
                                "headers": ["Part Number", "Description", "Qty"],
                                "rows": [["A-001", "Bracket", "10"], ["B-002", "Bolt M10", "20"]],
                                "page": 1,
                                "confidence": 0.98,
                                "num_rows": 2,
                                "num_columns": 3,
                            }
                        ],
                        "dimensions": [],
                        "text_blocks": [],
                        "title_block": None,
                        "bom": None,
                        "metadata": {},
                        "errors": [],
                        "warnings": [],
                    }
                }
            },
        }
    },
)
async def extract_pdf(
    file: Annotated[UploadFile, File(description="PDF file to extract data from")],
    current_user: CurrentUser,
    extract_tables: Annotated[
        bool, Form(description="Extract tables (BOMs, parts lists, etc.)")
    ] = True,
    extract_text: Annotated[bool, Form(description="Extract text blocks with positions")] = True,
    extract_dimensions: Annotated[
        bool, Form(description="Extract dimensions (requires OCR, experimental)")
    ] = False,
    use_ocr: Annotated[bool, Form(description="Use OCR for scanned PDFs (slower)")] = False,
    ocr_language: Annotated[
        str, Form(description="OCR language code (e.g., 'eng', 'deu', 'fra')")
    ] = "eng",
    pages: Annotated[
        str | None,
        Form(
            description="Comma-separated page numbers to process (e.g., '1,3,5' or leave empty for all)"
        ),
    ] = None,
) -> PDFExtractionResponse:
    """
    Extract data from a PDF document.

    Supports extracting tables, text blocks, dimensions, and title blocks from PDF files.
    Ideal for processing technical documents, BOMs, parts lists, and specifications.

    **Usage Examples:**

    **cURL - Extract tables from BOM:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/extraction/pdf" \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -F "file=@bom.pdf" \\
      -F "extract_tables=true" \\
      -F "extract_text=false"
    ```

    **cURL - Extract from specific pages:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/extraction/pdf" \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -F "file=@document.pdf" \\
      -F "pages=1,2,5"
    ```

    **Python:**
    ```python
    import requests

    url = "http://localhost:8000/api/v1/extraction/pdf"
    headers = {"Authorization": "Bearer YOUR_TOKEN"}
    files = {"file": open("parts_list.pdf", "rb")}
    data = {
        "extract_tables": True,
        "extract_text": True,
        "pages": "1,2"  # Process only pages 1 and 2
    }

    response = requests.post(url, headers=headers, files=files, data=data)
    result = response.json()

    # Access extracted tables
    for table in result["tables"]:
        print(f"Table on page {table['page']}:")
        print(f"Headers: {table['headers']}")
        for row in table["rows"]:
            print(f"  {row}")
    ```

    Args:
        file: PDF file to extract from
        extract_tables: Extract tables from the PDF (default: True)
        extract_text: Extract text blocks with positions (default: True)
        extract_dimensions: Extract dimensions using OCR (default: False, experimental)
        use_ocr: Enable OCR for scanned PDFs (default: False)
        ocr_language: OCR language code for text recognition (default: "eng")
        pages: Comma-separated page numbers to process, or None for all pages

    Returns:
        PDFExtractionResponse with extracted data
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

        # Extract - Initialize PDFExtractor with OCR parameters
        extractor = PDFExtractor(
            enable_ocr=use_ocr,
            ocr_language=ocr_language,
        )
        result = extractor.extract(
            str(temp_path),
            extract_tables=options.extract_tables,
            extract_text=options.extract_text,
            extract_dimensions=options.extract_dimensions,
            extract_title_block=False,  # Title block extraction not currently implemented
            pages=options.pages,
            use_ocr=use_ocr,
        )

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
    summary="Extract data from DXF/DWG CAD files",
    description="Upload a DXF or DWG file and extract layers, blocks, dimensions, text, and geometry.",
    tags=["CAD Extraction"],
    responses={
        200: {
            "description": "Extraction successful",
            "content": {
                "application/json": {
                    "example": {
                        "source_file": "mechanical_part.dxf",
                        "source_type": "dxf",
                        "success": True,
                        "layers": [
                            {
                                "name": "DIMENSIONS",
                                "color": 7,
                                "linetype": "Continuous",
                                "is_on": True,
                                "entity_count": 45,
                            }
                        ],
                        "blocks": [],
                        "dimensions": [],
                        "text_blocks": [],
                        "title_block": None,
                        "geometry_summary": {
                            "lines": 120,
                            "circles": 8,
                            "arcs": 15,
                            "total_entities": 143,
                        },
                        "entities": [],
                        "metadata": {},
                        "errors": [],
                        "warnings": [],
                    }
                }
            },
        }
    },
)
async def extract_dxf(
    file: Annotated[UploadFile, File(description="DXF or DWG CAD file to extract from")],
    current_user: CurrentUser,
    extract_layers: Annotated[
        bool, Form(description="Extract layer information with properties")
    ] = True,
    extract_blocks: Annotated[
        bool, Form(description="Extract block definitions and attributes")
    ] = True,
    extract_dimensions: Annotated[
        bool, Form(description="Extract dimension entities (linear, angular, radial)")
    ] = True,
    extract_text: Annotated[bool, Form(description="Extract TEXT and MTEXT entities")] = True,
    extract_title_block: Annotated[
        bool, Form(description="Detect and extract title block information")
    ] = True,
    extract_geometry: Annotated[
        bool, Form(description="Calculate geometry summary (entity counts)")
    ] = False,
) -> CADExtractionResponse:
    """
    Extract data from a DXF/DWG CAD file.

    Parses AutoCAD DXF and DWG files to extract structured engineering data including
    layers, blocks, dimensions, text, and geometry information.

    **Usage Examples:**

    **cURL - Extract layers and dimensions:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/extraction/dxf" \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -F "file=@drawing.dxf" \\
      -F "extract_layers=true" \\
      -F "extract_dimensions=true" \\
      -F "extract_geometry=true"
    ```

    **Python:**
    ```python
    import requests

    url = "http://localhost:8000/api/v1/extraction/dxf"
    headers = {"Authorization": "Bearer YOUR_TOKEN"}
    files = {"file": open("mechanical_part.dxf", "rb")}
    data = {
        "extract_layers": True,
        "extract_blocks": True,
        "extract_dimensions": True,
        "extract_text": True,
        "extract_title_block": True,
        "extract_geometry": True
    }

    response = requests.post(url, headers=headers, files=files, data=data)
    result = response.json()

    # Access extracted data
    print(f"Found {len(result['layers'])} layers")
    print(f"Found {len(result['dimensions'])} dimensions")
    if result['geometry_summary']:
        print(f"Total entities: {result['geometry_summary']['total_entities']}")
    ```

    **Extracted Data:**
    - **Layers**: Name, color, linetype, state (on/off/frozen), entity count
    - **Blocks**: Block definitions, insert counts, attributes
    - **Dimensions**: Linear, angular, radial, diameter dimensions with values
    - **Text**: TEXT and MTEXT entities with content and positions
    - **Title Block**: Drawing number, revision, date, company (auto-detected)
    - **Geometry Summary**: Counts of lines, circles, arcs, polylines, etc.

    Args:
        file: DXF or DWG file to extract from
        extract_layers: Extract layer information (default: True)
        extract_blocks: Extract block definitions (default: True)
        extract_dimensions: Extract dimensions (default: True)
        extract_text: Extract text entities (default: True)
        extract_title_block: Extract title block (default: True)
        extract_geometry: Calculate geometry summary (default: False)

    Returns:
        CADExtractionResponse with extracted CAD data
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
    summary="Extract engineering data via Werk24 AI",
    description="Upload an engineering drawing (PDF/image) and extract dimensions, GD&T, threads, materials, and more using AI-powered Werk24 API.",
    tags=["Werk24", "AI Extraction"],
    responses={
        200: {
            "description": "Extraction successful",
            "content": {
                "application/json": {
                    "example": {
                        "source_file": "bracket_drawing.pdf",
                        "source_type": "werk24",
                        "success": True,
                        "dimensions": [
                            {
                                "value": 50.0,
                                "unit": "mm",
                                "tolerance_plus": 0.1,
                                "tolerance_minus": 0.1,
                                "dimension_type": "linear",
                                "label": "Length",
                                "page": 1,
                                "confidence": 0.95,
                                "bbox": [100, 200, 150, 220],
                            }
                        ],
                        "gdt_annotations": [
                            {
                                "characteristic_type": "flatness",
                                "tolerance_value": 0.05,
                                "unit": "mm",
                                "datum_references": ["A"],
                                "material_condition": "RFS",
                                "confidence": 0.92,
                            }
                        ],
                        "threads": [
                            {
                                "designation": "M10x1.5",
                                "standard": "ISO",
                                "thread_type": "internal",
                                "confidence": 0.88,
                            }
                        ],
                        "materials": ["Steel AISI 1045"],
                        "title_block": {
                            "drawing_number": "DRW-2024-001",
                            "title": "Mounting Bracket",
                            "revision": "C",
                            "company": "ACME Corp",
                            "confidence": 0.97,
                        },
                        "metadata": {"processing_time_ms": 1250},
                        "errors": [],
                        "warnings": [],
                    }
                }
            },
        },
        503: {
            "description": "Werk24 API key not configured",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Werk24 API key not configured. Set WERK24_API_KEY environment variable."
                    }
                }
            },
        },
    },
)
async def extract_werk24(
    file: Annotated[
        UploadFile,
        File(
            description="Engineering drawing file to extract from. Supported formats: PDF, PNG, JPG, JPEG, TIF, TIFF"
        ),
    ],
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
    extract_dimensions: Annotated[
        bool, Form(description="Extract dimensional information with tolerances")
    ] = True,
    extract_gdt: Annotated[
        bool, Form(description="Extract GD&T (Geometric Dimensioning and Tolerancing) annotations")
    ] = True,
    extract_threads: Annotated[
        bool, Form(description="Extract thread specifications (M, UNC, etc.)")
    ] = True,
    extract_surface_finish: Annotated[
        bool, Form(description="Extract surface finish requirements (Ra, Rz values)")
    ] = True,
    extract_materials: Annotated[bool, Form(description="Extract material specifications")] = True,
    extract_title_block: Annotated[
        bool, Form(description="Extract title block information (drawing number, revision, etc.)")
    ] = True,
    confidence_threshold: Annotated[
        float,
        Form(
            ge=0.0,
            le=1.0,
            description="Minimum confidence threshold (0.0-1.0) for filtering results. Default: 0.7",
        ),
    ] = 0.7,
    workspace_id: Annotated[
        str | None,
        Form(description="Optional workspace ID for usage tracking and quota management"),
    ] = None,
) -> Werk24ExtractionResponse:
    """
    Extract engineering data from drawings using Werk24 AI API.

    This endpoint uses the Werk24 AI service to automatically extract engineering
    information from technical drawings. It supports various image formats and PDFs.

    **Prerequisites:**
    - Set `WERK24_API_KEY` environment variable with your Werk24 API key
    - Supported file formats: PDF, PNG, JPG, JPEG, TIF, TIFF
    - Maximum file size: 100 MB

    **Extracted Data Types:**
    - **Dimensions**: Linear, angular, radial dimensions with tolerances
    - **GD&T**: Geometric tolerances (flatness, perpendicularity, position, etc.)
    - **Threads**: Thread callouts (metric, UNC, UNF, etc.)
    - **Surface Finish**: Ra, Rz, and other surface roughness values
    - **Materials**: Material specifications from title block or notes
    - **Title Block**: Drawing number, revision, date, author, company, scale

    **Usage Examples:**

    **cURL:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/extraction/werk24" \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -F "file=@drawing.pdf" \\
      -F "extract_dimensions=true" \\
      -F "extract_gdt=true" \\
      -F "extract_threads=true" \\
      -F "confidence_threshold=0.8"
    ```

    **Python (requests):**
    ```python
    import requests

    url = "http://localhost:8000/api/v1/extraction/werk24"
    headers = {"Authorization": "Bearer YOUR_TOKEN"}
    files = {"file": open("drawing.pdf", "rb")}
    data = {
        "extract_dimensions": True,
        "extract_gdt": True,
        "extract_threads": True,
        "extract_surface_finish": True,
        "extract_materials": True,
        "extract_title_block": True,
        "confidence_threshold": 0.8
    }

    response = requests.post(url, headers=headers, files=files, data=data)
    result = response.json()

    print(f"Extracted {len(result['dimensions'])} dimensions")
    print(f"Extracted {len(result['gdt_annotations'])} GD&T annotations")
    ```

    **Python (httpx - async):**
    ```python
    import httpx

    async with httpx.AsyncClient() as client:
        files = {"file": ("drawing.pdf", open("drawing.pdf", "rb"), "application/pdf")}
        data = {"extract_dimensions": True, "confidence_threshold": 0.75}
        response = await client.post(
            "http://localhost:8000/api/v1/extraction/werk24",
            headers={"Authorization": "Bearer YOUR_TOKEN"},
            files=files,
            data=data
        )
        result = response.json()
    ```

    **Selective Extraction (faster, lower cost):**
    ```bash
    # Extract only dimensions and title block
    curl -X POST "http://localhost:8000/api/v1/extraction/werk24" \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -F "file=@drawing.pdf" \\
      -F "extract_dimensions=true" \\
      -F "extract_gdt=false" \\
      -F "extract_threads=false" \\
      -F "extract_surface_finish=false" \\
      -F "extract_materials=false" \\
      -F "extract_title_block=true"
    ```

    **Response Structure:**
    ```json
    {
      "source_file": "drawing.pdf",
      "source_type": "werk24",
      "success": true,
      "dimensions": [...],        # Array of ExtractedDimension objects
      "gdt_annotations": [...],   # Array of GDT annotation objects
      "threads": [...],           # Array of thread specification objects
      "surface_finishes": [...],  # Array of surface finish objects
      "materials": [...],         # Array of material strings
      "title_block": {...},       # Title block object or null
      "metadata": {
        "processing_time_ms": 1250,
        "api_version": "2.0"
      },
      "errors": [],               # Array of error messages
      "warnings": []              # Array of warning messages
    }
    ```

    **Best Practices:**
    1. Use selective extraction to reduce API costs and improve response time
    2. Set appropriate confidence_threshold (0.7-0.9) based on drawing quality
    3. High-quality scans (300+ DPI) yield better extraction results
    4. For batch processing, consider using the async job endpoint instead
    5. Check the `warnings` array for extraction issues

    **Error Handling:**
    - Returns 200 with `success: false` if extraction fails (check `errors` array)
    - Returns 503 if WERK24_API_KEY is not configured
    - Returns 400 for invalid file formats
    - Returns 500 for server errors

    **Rate Limits:**
    - Werk24 API has usage quotas - check your plan limits
    - Usage is tracked in the database for quota monitoring
    - Use `/api/v1/werk24/usage` endpoint to check consumption

    Args:
        file: Engineering drawing file (PDF, PNG, JPG, JPEG, TIF, TIFF)
        extract_dimensions: Extract dimensions with tolerances (default: True)
        extract_gdt: Extract GD&T annotations (default: True)
        extract_threads: Extract thread specifications (default: True)
        extract_surface_finish: Extract surface finish requirements (default: True)
        extract_materials: Extract material specifications (default: True)
        extract_title_block: Extract title block information (default: True)
        confidence_threshold: Minimum confidence for results (0.0-1.0, default: 0.7)

    Returns:
        Werk24ExtractionResponse with extracted engineering data

    Raises:
        HTTPException 503: If Werk24 API key is not configured
        HTTPException 400: If file format is invalid
        HTTPException 500: If extraction fails
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

        # Get tracking metadata
        file_size = file.size if file.size else 0
        file_type = Path(file.filename or "").suffix.lower() if file.filename else None
        request_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", None)

        # Extract - use extract_async since we're in an async function
        client = Werk24Client()
        result = await client.extract_async(
            str(temp_path),
            ask_types=ask_types,
            db=db,
            user_id=str(current_user.id),
            workspace_id=workspace_id,
            file_size=file_size,
            file_type=file_type,
            request_ip=request_ip,
            user_agent=user_agent,
        )

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
# BOM Extraction
# =============================================================================


@router.post(
    "/bom/extract",
    response_model=BOMExtractionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Extract Bill of Materials from CAD files",
    description="Upload a CAD file (DXF, IFC, or STEP) and extract hierarchical or flattened BOM with quantities and parent-child relationships.",
    tags=["BOM Extraction"],
    responses={
        201: {
            "description": "BOM extraction successful",
            "content": {
                "application/json": {
                    "example": {
                        "source_file": "assembly.step",
                        "source_type": "step",
                        "success": True,
                        "bom": {
                            "items": [
                                {
                                    "item_id": "1",
                                    "parent_id": None,
                                    "name": "Assembly",
                                    "part_number": "ASM-001",
                                    "quantity": 1,
                                    "material": "N/A",
                                    "description": "Main assembly",
                                }
                            ],
                            "headers": [
                                "item_id",
                                "parent_id",
                                "name",
                                "part_number",
                                "quantity",
                                "material",
                                "description",
                            ],
                            "total_items": 1,
                        },
                        "hierarchy_mode": "hierarchical",
                        "flattening_strategy": None,
                        "flattened": False,
                        "flattened_items": [],
                        "total_unique_items": 1,
                        "hierarchy_depth": 3,
                        "quantity_rolled_up": False,
                        "metadata": {},
                        "errors": [],
                        "warnings": [],
                    }
                }
            },
        },
        400: {"description": "Invalid file format or extraction options"},
        500: {"description": "Extraction failed"},
    },
)
async def extract_bom(
    file: Annotated[UploadFile, File(description="CAD file (DXF, IFC, or STEP) to extract BOM from")],
    current_user: CurrentUser,
    format: Annotated[
        ExtractionFormat,
        Form(description="File format (auto-detected if not specified)"),
    ] = ExtractionFormat.STEP,
    extract_bom: Annotated[
        bool, Form(description="Extract bill of materials")
    ] = True,
    hierarchy_mode: Annotated[
        BOMHierarchyMode,
        Form(description="How to handle hierarchical BOM data (hierarchical, flattened, inducted)"),
    ] = BOMHierarchyMode.HIERARCHICAL,
    flattening_strategy: Annotated[
        BOMFlatteningStrategy,
        Form(description="Strategy for flattening hierarchical BOMs (path, inducted, level_prefix, parent_reference)"),
    ] = BOMFlatteningStrategy.PATH,
    max_depth: Annotated[
        int | None,
        Form(description="Maximum hierarchy depth to extract (None = unlimited)"),
    ] = None,
    include_quantities: Annotated[
        bool, Form(description="Extract item quantities")
    ] = True,
    include_materials: Annotated[
        bool, Form(description="Extract material information")
    ] = True,
    include_properties: Annotated[
        bool, Form(description="Extract item properties")
    ] = True,
    include_metadata: Annotated[
        bool, Form(description="Extract BOM metadata")
    ] = True,
    preserve_parent_child: Annotated[
        bool, Form(description="Preserve parent-child relationships")
    ] = True,
    add_level_info: Annotated[
        bool, Form(description="Add hierarchy level information")
    ] = False,
    add_path_info: Annotated[
        bool, Form(description="Add item path information")
    ] = False,
    path_separator: Annotated[
        str, Form(description="Separator for path strings")
    ] = " > ",
    level_prefix_separator: Annotated[
        str, Form(description="Separator for level prefixes")
    ] = ".",
    include_parent_ref: Annotated[
        bool, Form(description="Include parent reference in flattened view")
    ] = False,
) -> BOMExtractionResponse:
    """
    Extract Bill of Materials from CAD assembly files.

    Supports hierarchical and flattened BOM extraction from DXF, IFC, and STEP files
    with automatic quantity rollup, parent-child relationship tracking, and material
    information extraction.

    **Supported Formats:**
    - **DXF**: Extracts BOM from blocks and attributes
    - **IFC**: Extracts BOM from IFC assembly relationships and elements
    - **STEP**: Extracts BOM from STEP assembly structure (AP214/AP242)

    **Hierarchy Modes:**
    - **hierarchical**: Preserve full assembly hierarchy with parent-child relationships
    - **flattened**: Flatten hierarchy with quantity rollup
    - **inducted**: Show only leaf-level items with rolled-up quantities

    **Flattening Strategies (when hierarchy_mode=flattened):**
    - **path**: Include hierarchy path (e.g., "Assembly > Subassembly > Part")
    - **inducted**: Only leaf items with rolled-up quantities
    - **level_prefix**: Add level prefix (e.g., "1. ", "1.1. ")
    - **parent_reference**: Include parent references in flattened view

    **Usage Examples:**

    **cURL - Extract hierarchical BOM:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/extraction/bom/extract" \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -F "file=@assembly.step" \\
      -F "format=step" \\
      -F "hierarchy_mode=hierarchical"
    ```

    **cURL - Extract flattened BOM with quantity rollup:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/extraction/bom/extract" \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -F "file=@assembly.dxf" \\
      -F "format=dxf" \\
      -F "hierarchy_mode=flattened" \\
      -F "flattening_strategy=path"
    ```

    **Python - Extract BOM with custom options:**
    ```python
    import requests

    with open("assembly.ifc", "rb") as f:
        response = requests.post(
            "http://localhost:8000/api/v1/extraction/bom/extract",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": f},
            data={
                "format": "ifc",
                "hierarchy_mode": "flattened",
                "flattening_strategy": "inducted",
                "include_materials": True,
                "max_depth": 5,
            }
        )
    bom_data = response.json()
    ```

    **Response Fields:**
    - **bom**: Extracted BOM with items and hierarchy
    - **flattened**: Whether BOM was flattened
    - **flattened_items**: Flattened BOM items (if flattened=True)
    - **total_unique_items**: Count of unique part numbers
    - **hierarchy_depth**: Maximum hierarchy depth
    - **quantity_rolled_up**: Whether quantities were rolled up from children

    **Notes:**
    - Parent-child relationships are preserved by default in hierarchical mode
    - Quantities are automatically rolled up in flattened mode
    - Material information is extracted when available
    - Supports multi-level assemblies with complex nesting
    """
    # Validate file
    try:
        validate_file(file, format)
    except HTTPException:
        # Try to auto-detect format from file extension
        if file.filename:
            ext = Path(sanitize_filename(file.filename)).suffix.lower()
            for fmt, extensions in ALLOWED_EXTENSIONS.items():
                if ext in extensions:
                    format = fmt
                    break
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file format: {ext}. Supported: DXF, IFC, STEP",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File format must be specified or auto-detected from filename",
            )

    # Save uploaded file
    temp_path: Path | None = None
    try:
        temp_path = await save_upload_file(file)

        # Get extraction service
        extraction_service = get_extraction_service()

        # Build BOM extraction options
        bom_options = BOMExtractionOptions(
            extract_bom=extract_bom,
            hierarchy_mode=hierarchy_mode,
            flattening_strategy=flattening_strategy,
            max_depth=max_depth,
            include_quantities=include_quantities,
            include_materials=include_materials,
            include_properties=include_properties,
            include_metadata=include_metadata,
            preserve_parent_child=preserve_parent_child,
            add_level_info=add_level_info,
            add_path_info=add_path_info,
            path_separator=path_separator,
            level_prefix_separator=level_prefix_separator,
            include_parent_ref=include_parent_ref,
        )

        # Extract BOM based on format
        result_bom = None
        errors: list[str] = []
        warnings: list[str] = []
        metadata: dict[str, Any] = {}

        if format == ExtractionFormat.DXF:
            # Extract BOM from DXF file
            from pybase.extraction.cad.dxf import DXFParser

            parser = DXFParser()
            result_bom = parser.extract_bom(
                source=temp_path,
                include_quantities=include_quantities,
                include_materials=include_materials,
            )
            metadata["parser"] = "dxf"

        elif format == ExtractionFormat.IFC:
            # Extract BOM from IFC file
            from pybase.extraction.cad.ifc import IFCParser

            parser = IFCParser()
            result_bom = parser.extract_bom(
                source=temp_path,
                include_quantities=include_quantities,
                include_materials=include_materials,
            )
            metadata["parser"] = "ifc"

        elif format == ExtractionFormat.STEP:
            # Extract BOM from STEP file
            from pybase.extraction.cad.step import STEPParser

            parser = STEPParser()
            result_bom = parser.extract_bom(
                source=temp_path,
                include_geometry=False,
            )
            metadata["parser"] = "step"

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"BOM extraction not supported for format: {format.value}",
            )

        # Apply flattening if requested
        flattened = False
        flattened_items: list[dict[str, Any]] = []
        hierarchy_depth = 0
        quantity_rolled_up = False
        total_unique_items = 0

        if result_bom:
            # Build BOM schema from result
            bom_schema = ExtractedBOMSchema(
                items=[
                    {
                        "item_id": item.item_id,
                        "parent_id": item.parent_id,
                        "name": item.name,
                        "part_number": item.part_number,
                        "quantity": item.quantity,
                        "unit": item.unit,
                        "material": item.material,
                        "description": item.description,
                    }
                    for item in result_bom.items
                ],
                headers=result_bom.headers,
                total_items=result_bom.total_items or len(result_bom.items),
                confidence=result_bom.confidence,
            )

            # Calculate hierarchy depth
            if result_bom.parent_child_map:
                hierarchy_depth = result_bom.hierarchy_level or 0

            # Count unique items
            unique_part_numbers = {
                item.part_number for item in result_bom.items if item.part_number
            }
            total_unique_items = len(unique_part_numbers)

            # Apply flattening if requested
            if hierarchy_mode in (BOMHierarchyMode.FLATTENED, BOMHierarchyMode.INDUCTED):
                from pybase.services.bom_flattener import BOMFlattenerService

                flattener = BOMFlattenerService()

                # Convert BOM items to dict format for flattener
                bom_dict = {
                    "items": [
                        {
                            "item_id": item.item_id,
                            "parent_id": item.parent_id,
                            "name": item.name,
                            "part_number": item.part_number,
                            "quantity": item.quantity,
                            "unit": item.unit,
                            "material": item.material,
                            "description": item.description,
                        }
                        for item in result_bom.items
                    ],
                    "headers": result_bom.headers,
                }

                # Flatten BOM
                flattened_result = flattener.flatten_bom(
                    bom_data=bom_dict,
                    strategy=flattening_strategy,
                    merge_duplicates=True,
                )

                flattened = True
                flattened_items = flattened_result.get("items", [])
                quantity_rolled_up = flattened_result.get("quantities_rolled_up", False)

                # Update metadata with flattening info
                metadata["flattening"] = {
                    "strategy": flattening_strategy.value,
                    "original_items": len(result_bom.items),
                    "flattened_items": len(flattened_items),
                    "quantities_rolled_up": quantity_rolled_up,
                }

            # Build response
            return BOMExtractionResponse(
                source_file=sanitize_filename(file.filename or "upload"),
                source_type=format.value,
                success=True,
                bom=bom_schema,
                hierarchy_mode=hierarchy_mode,
                flattening_strategy=flattening_strategy if flattened else None,
                flattened=flattened,
                flattened_items=flattened_items,
                total_unique_items=total_unique_items,
                hierarchy_depth=hierarchy_depth,
                quantity_rolled_up=quantity_rolled_up,
                metadata=metadata,
                errors=errors,
                warnings=warnings,
            )

        else:
            # No BOM extracted
            return BOMExtractionResponse(
                source_file=sanitize_filename(file.filename or "upload"),
                source_type=format.value,
                success=False,
                bom=None,
                hierarchy_mode=hierarchy_mode,
                flattening_strategy=None,
                flattened=False,
                flattened_items=[],
                total_unique_items=0,
                hierarchy_depth=0,
                quantity_rolled_up=False,
                metadata=metadata,
                errors=["No BOM data found in file"],
                warnings=warnings,
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle unexpected errors
        return BOMExtractionResponse(
            source_file=sanitize_filename(file.filename or "upload"),
            source_type=format.value,
            success=False,
            bom=None,
            hierarchy_mode=hierarchy_mode,
            flattening_strategy=None,
            flattened=False,
            flattened_items=[],
            total_unique_items=0,
            hierarchy_depth=0,
            quantity_rolled_up=False,
            metadata={},
            errors=[f"Extraction failed: {str(e)}"],
            warnings=[],
        )
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)


# =============================================================================
# Bulk Multi-File Extraction
# =============================================================================


@router.post(
    "/bulk",
    response_model=BulkExtractionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Bulk extract multiple files",
    description="Upload and process multiple CAD/PDF files simultaneously with parallel extraction.",
)
async def bulk_extract(
    files: Annotated[list[UploadFile], File(description="Multiple files to extract from")],
    current_user: CurrentUser,
    db: DbSession,
    format_override: Annotated[
        ExtractionFormat | None, Form(description="Override format detection")
    ] = None,
    auto_detect_format: Annotated[bool, Form(description="Auto-detect file format")] = True,
    continue_on_error: Annotated[bool, Form(description="Continue if one file fails")] = True,
    target_table_id: Annotated[str | None, Form(description="Target table ID")] = None,
) -> BulkExtractionResponse:
    """
    Process multiple files in parallel with bulk extraction.

    Supports:
    - Multiple file upload (all supported formats)
    - Parallel processing with progress tracking
    - Per-file status and results
    - Graceful error handling (continue on partial failures)
    - Combined results for import preview

    **Job Persistence:**
    Jobs are stored in the database and persist across worker restarts.
    Automatic retry with exponential backoff is enabled. Status tracked in database.

    Returns 202 Accepted with bulk_job_id for status polling.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided",
        )

    # Save all uploaded files to temp directory
    temp_paths: list[Path] = []
    try:
        for file in files:
            # Validate file has a name
            if not file.filename:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="All files must have filenames",
                )

            # Save file to temp
            temp_path = await save_upload_file(file)
            temp_paths.append(temp_path)

        # Create job in database with bulk format
        job_service = get_extraction_job_service()

        # Prepare options with file paths and bulk extraction settings
        job_options = {
            "file_paths": [str(path) for path in temp_paths],
            "format_override": format_override.value if format_override else None,
            "auto_detect_format": auto_detect_format,
            "continue_on_error": continue_on_error,
            "target_table_id": target_table_id,
        }

        # Create bulk extraction job in database
        # Use "pdf" as base format but mark as bulk in options
        job_model = await job_service.create_job(
            db=db,
            user_id=str(current_user.id),
            extraction_format=ExtractionFormat.PDF,  # Will be overridden by Celery task
            file_path=None,  # Bulk jobs don't have a single file
            options=job_options,
            max_retries=3,
        )

        # Trigger Celery bulk extraction task
        try:
            from celery import Celery
            import os

            # Create Celery app to send task
            celery_app = Celery(
                broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
                backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
            )

            # Send bulk extraction task to Celery with job_id for database tracking
            celery_app.send_task(
                "extract_bulk",
                args=[
                    [str(path) for path in temp_paths],
                    format_override.value if format_override else None,
                    {},  # Format-specific options
                    str(job_model.id),  # job_id for database tracking
                ],
            )

        except Exception as e:
            # Log error but don't fail - job is created and will be picked up by worker
            pass

        # Return BulkExtractionResponse with job_id
        return BulkExtractionResponse(
            bulk_job_id=job_model.id,
            total_files=len(temp_paths),
            files=[],
            overall_status=JobStatus.PENDING,
            progress=0,
            files_completed=0,
            files_failed=0,
            files_pending=len(temp_paths),
            created_at=job_model.created_at,
            target_table_id=UUID(target_table_id) if target_table_id else None,
        )

    except Exception as e:
        # Cleanup temp files on error
        for temp_path in temp_paths:
            temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bulk extraction job: {str(e)}",
        )


@router.get(
    "/bulk/{job_id}",
    response_model=BulkExtractionResponse,
    summary="Get bulk job status",
    description="Check the status and results of a bulk extraction job.",
)
async def get_bulk_job_status(
    job_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> BulkExtractionResponse:
    """
    Get bulk extraction job status and per-file results.

    Returns:
    - Overall job progress
    - Per-file extraction status
    - Individual file results when complete

    **Job Persistence:**
    Job status is retrieved from the database. Jobs persist across restarts
    with automatic retry and exponential backoff. Status tracked in database.
    """
    # Retrieve job from database
    job_service = get_extraction_job_service()
    try:
        job_model = await job_service.get_job_by_id(db, job_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk job not found",
        )

    # Parse results from database
    results_data = {}
    if job_model.results:
        try:
            results_data = (
                json.loads(job_model.results)
                if isinstance(job_model.results, str)
                else job_model.results
            )
        except Exception:
            results_data = {}

    # Parse options to get total files
    options_data = job_model.get_options()
    total_files = len(options_data.get("file_paths", []))

    # Extract file statuses from results
    files = results_data.get("files", [])

    # Parse target_table_id from options with error handling
    target_table_id = None
    if options_data.get("target_table_id"):
        try:
            target_table_id = UUID(options_data.get("target_table_id"))
        except (ValueError, TypeError):
            target_table_id = None

    # Build BulkExtractionResponse from database model
    return BulkExtractionResponse(
        bulk_job_id=job_model.id,
        total_files=results_data.get("total_files", total_files),
        files=[FileExtractionStatus(**f) if isinstance(f, dict) else f for f in files],
        overall_status=JobStatus(job_model.status),
        progress=job_model.progress,
        files_completed=results_data.get("files_completed", 0),
        files_failed=results_data.get("files_failed", 0),
        files_pending=results_data.get("files_pending", 0),
        created_at=job_model.created_at,
        started_at=job_model.started_at,
        completed_at=job_model.completed_at,
        target_table_id=target_table_id,
    )


@router.post(
    "/bulk/{job_id}/preview",
    response_model=BulkImportPreview,
    summary="Preview bulk import",
    description="Generate combined preview of data from all files in bulk extraction job.",
)
async def preview_bulk_import(
    job_id: str,
    current_user: CurrentUser,
    db: DbSession,
    table_id: Annotated[str | None, Query(description="Target table ID")] = None,
) -> BulkImportPreview:
    """
    Preview how extracted data from multiple files will map to table fields.

    Returns:
    - Combined field list from all files
    - Suggested field mappings
    - Per-file preview breakdowns
    - Sample data across all files

    **Job Persistence:**
    Bulk job data is retrieved from the database. Jobs persist across restarts
    with automatic retry and exponential backoff. Status tracked in database.
    """
    try:
        preview_data = await generate_bulk_preview(
            bulk_job_id=job_id,
            db=db,
            table_id=table_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Convert dict to BulkImportPreview schema
    return BulkImportPreview(**preview_data)


@router.post(
    "/bulk/import",
    response_model=ImportResponse,
    summary="Import bulk extraction data",
    description="Import data from bulk extraction job into a table with field mapping.",
)
async def import_bulk_extraction(
    request: BulkImportRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> ImportResponse:
    """
    Import extracted data from bulk extraction job into a table.

    Processes all successfully completed files in the bulk job,
    creates records with source file metadata, and handles partial failures.

    Returns:
    - Import statistics (success/failure counts)
    - Per-file error details
    - Created field IDs (if create_missing_fields=true)

    **Job Persistence:**
    Bulk job data is retrieved from the database. Jobs persist across restarts
    with automatic retry and exponential backoff. Status tracked in database.
    """
    return await bulk_import_to_table(
        bulk_job_id=request.bulk_job_id,
        table_id=request.table_id,
        field_mapping=request.field_mapping,
        db=db,
        user_id=str(current_user.id),
        file_selection=request.file_selection,
        create_missing_fields=request.create_missing_fields,
        skip_errors=request.skip_errors,
        include_source_file=request.include_source_file,
    )


# =============================================================================
# Job Management (for async/large file processing)
# =============================================================================


@router.post(
    "/jobs",
    response_model=ExtractionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create async extraction job",
    description="Create an asynchronous extraction job for large files or batch processing.",
    tags=["Job Management"],
    responses={
        202: {
            "description": "Job created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "pending",
                        "format": "werk24",
                        "filename": "large_drawing.pdf",
                        "file_size": 15728640,
                        "progress": 0,
                        "created_at": "2024-01-20T10:30:00Z",
                    }
                }
            },
        }
    },
)
async def create_extraction_job(
    file: Annotated[UploadFile, File(description="File to extract from")],
    format: Annotated[
        ExtractionFormat, Form(description="Extraction format (pdf, dxf, ifc, step, werk24)")
    ],
    current_user: CurrentUser,
    db: DbSession,
    target_table_id: Annotated[
        str | None, Form(description="Optional target table ID for automatic import")
    ] = None,
) -> ExtractionJobResponse:
    """
    Create an asynchronous extraction job for large files or batch processing.

    Use this endpoint for:
    - Large files (>10 MB) that may take time to process
    - Batch processing of multiple files
    - Background processing without blocking your application

    **Workflow:**
    1. Submit file and get job ID
    2. Poll `/jobs/{job_id}` to check status
    3. When status is "completed", retrieve results
    4. Optionally import results to a table

    **Job Persistence:**
    Jobs are stored in the database and persist across worker restarts.
    Automatic retry with exponential backoff is enabled. Status tracked in database.

    **Usage Examples:**

    **Python - Submit job and poll status:**
    ```python
    import requests
    import time

    # Submit job
    url = "http://localhost:8000/api/v1/extraction/jobs"
    headers = {"Authorization": "Bearer YOUR_TOKEN"}
    files = {"file": open("large_drawing.pdf", "rb")}
    data = {"format": "werk24"}

    response = requests.post(url, headers=headers, files=files, data=data)
    job = response.json()
    job_id = job["id"]

    # Poll status
    status_url = f"http://localhost:8000/api/v1/extraction/jobs/{job_id}"
    while True:
        status_response = requests.get(status_url, headers=headers)
        job_status = status_response.json()

        print(f"Status: {job_status['status']}, Progress: {job_status['progress']}%")

        if job_status["status"] == "completed":
            print("Extraction complete!")
            result = job_status["result"]
            break
        elif job_status["status"] == "failed":
            print(f"Job failed: {job_status['error_message']}")
            break

        time.sleep(2)  # Poll every 2 seconds
    ```

    Args:
        file: File to extract from
        format: Extraction format (pdf, dxf, ifc, step, werk24)
        db: Database session
        target_table_id: Optional table ID for automatic import after extraction

    Returns:
        ExtractionJobResponse with job ID and initial status (pending)
    """
    validate_file(file, format)

    # Save uploaded file to temp location
    temp_file_path = await save_upload_file(file)

    # Create job in database
    job_service = get_extraction_job_service()
    job_model = await job_service.create_job(
        db=db,
        user_id=str(current_user.id),
        extraction_format=format,
        file_path=str(temp_file_path),
        options={},
        max_retries=3,
    )

    # Trigger Celery task based on format
    try:
        from celery import Celery
        import os

        # Create Celery app to send task
        celery_app = Celery(
            broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
            backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
        )

        # Map format to task name
        task_names = {
            ExtractionFormat.PDF: "extract_pdf",
            ExtractionFormat.DXF: "extract_dxf",
            ExtractionFormat.IFC: "extract_ifc",
            ExtractionFormat.STEP: "extract_step",
            ExtractionFormat.WERK24: "extract_werk24",
        }

        task_name = task_names.get(format)
        if task_name:
            # Send task to Celery with job_id for database tracking
            celery_app.send_task(
                task_name,
                args=[str(temp_file_path), {}, str(job_model.id)],
            )

    except Exception as e:
        # Log error but don't fail - job is created and will be picked up by worker
        pass

    # Convert database model to response schema
    return ExtractionJobResponse(
        id=job_model.id,
        status=JobStatus(job_model.status),
        format=ExtractionFormat(job_model.extraction_format),
        filename=file.filename or "unknown",
        file_size=file.size or 0,
        options={},
        target_table_id=UUID(target_table_id) if target_table_id else None,
        progress=job_model.progress,
        result=None,
        error_message=None,
        retry_count=job_model.retry_count,
        celery_task_id=job_model.celery_task_id,
        created_at=job_model.created_at,
        started_at=job_model.started_at,
        completed_at=job_model.completed_at,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=ExtractionJobResponse,
    summary="Get job status",
    description="Get extraction job status and result from database.",
)
async def get_extraction_job(
    job_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> ExtractionJobResponse:
    """
    Get extraction job status and result.

    Retrieves job information from the database including:
    - Current status (pending, processing, completed, failed, cancelled)
    - Progress percentage
    - Extraction results (when completed)
    - Error messages (when failed)
    - Retry count and Celery task ID

    Jobs persist across worker restarts and support automatic retry.
    """
    from pybase.core.exceptions import NotFoundError

    # Get job from database
    job_service = get_extraction_job_service()
    try:
        job_model = await job_service.get_job_by_id(db=db, job_id=job_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Parse options from JSON string
    from json import loads

    try:
        options = loads(job_model.options) if job_model.options else {}
    except Exception:
        options = {}

    # Convert database model to response schema
    return ExtractionJobResponse(
        id=job_model.id,
        status=JobStatus(job_model.status),
        format=ExtractionFormat(job_model.extraction_format),
        filename=job_model.file_path.split("/")[-1] if job_model.file_path else "unknown",
        file_size=0,  # Not stored in database
        options=options,
        target_table_id=None,  # Not stored in database
        progress=job_model.progress,
        result=job_model.result,
        error_message=job_model.error_message,
        retry_count=job_model.retry_count,
        celery_task_id=job_model.celery_task_id,
        created_at=job_model.created_at,
        started_at=job_model.started_at,
        completed_at=job_model.completed_at,
    )


@router.get(
    "/jobs",
    response_model=ExtractionJobListResponse,
    summary="List extraction jobs",
)
async def list_extraction_jobs(
    current_user: CurrentUser,
    db: DbSession,
    status_filter: Annotated[JobStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ExtractionJobListResponse:
    """
    List extraction jobs with optional status filter.

    Jobs are retrieved from the database with pagination support.

    **Job Persistence:**
    Jobs persist across restarts with automatic retry and exponential backoff.
    Status tracked in database.
    """
    from pybase.models.extraction_job import ExtractionJobStatus

    job_service = get_extraction_job_service()

    # Convert status_filter to ExtractionJobStatus enum
    status_enum = None
    if status_filter:
        try:
            status_enum = ExtractionJobStatus(status_filter.value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter: {status_filter}",
            )

    # Get jobs from database
    jobs, total = await job_service.list_jobs(
        db=db,
        user_id=str(current_user.id),
        status=status_enum,
        page=page,
        page_size=page_size,
    )

    # Convert database models to response schemas
    job_responses = []
    for job in jobs:
        # Parse options from JSON string
        options_data = job.get_options()

        job_response = ExtractionJobResponse(
            id=str(job.id),
            status=JobStatus(job.status),
            format=ExtractionFormat(job.extraction_format),
            filename=Path(job.file_path).name if job.file_path else "unknown",
            file_size=0,  # Not stored in database
            progress=job.progress,
            result=json.loads(job.results) if job.results else None,
            error_message=job.error_message,
            retry_count=job.retry_count,
            celery_task_id=job.celery_task_id,
            target_table_id=options_data.get("target_table_id"),
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
        job_responses.append(job_response)

    return ExtractionJobListResponse(
        items=job_responses,
        total=total,
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
    db: DbSession,
) -> None:
    """
    Cancel a pending job or delete a completed job.

    - Pending/Processing/Retrying jobs: Mark as cancelled
    - Completed/Failed jobs: Delete from database

    **Job Persistence:**
    Jobs persist across restarts with automatic retry and exponential backoff.
    Status tracked in database.
    """
    from pybase.core.exceptions import NotFoundError
    from pybase.models.extraction_job import ExtractionJobStatus

    job_service = get_extraction_job_service()

    try:
        # Get job from database
        job_model = await job_service.get_job_by_id(db=db, job_id=job_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    # Cancel pending/processing/retrying jobs
    if job_model.status_enum in [
        ExtractionJobStatus.PENDING,
        ExtractionJobStatus.PROCESSING,
        ExtractionJobStatus.RETRYING,
    ]:
        await job_service.cancel_job(db=db, job_id=job_id)
    else:
        # Delete completed/failed/cancelled jobs
        await job_service.delete_job(db=db, job_id=job_id)


@router.post(
    "/jobs/cleanup",
    response_model=JobCleanupResponse,
    summary="Cleanup old extraction jobs",
    description="Delete old extraction jobs from the database. Requires superuser access.",
    tags=["Job Management"],
    responses={
        200: {
            "description": "Cleanup completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "deleted_count": 42,
                        "dry_run": False,
                        "older_than_days": 30,
                        "status_filter": None,
                    }
                }
            },
        },
        403: {
            "description": "Forbidden - Superuser access required",
        },
    },
)
async def cleanup_extraction_jobs(
    current_user: CurrentSuperuser,
    db: DbSession,
    older_than_days: Annotated[
        int,
        Query(
            ge=1,
            le=365,
            description="Delete jobs older than this many days (1-365)",
        ),
    ] = 30,
    status: Annotated[
        JobStatus | None,
        Query(
            description="Optional status filter (pending, processing, completed, failed, cancelled, retrying)"
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        Query(description="If True, count jobs without deleting them (useful for preview)"),
    ] = False,
) -> JobCleanupResponse:
    """
    Cleanup old extraction jobs from the database.

    This endpoint allows administrators to delete old jobs that are no longer needed.
    By default, it cleans up completed, failed, and cancelled jobs older than 30 days.

    Args:
        older_than_days: Delete jobs older than this many days (default: 30, range: 1-365)
        status: Optional status filter. If not provided, cleans up completed/failed/cancelled jobs
        dry_run: If True, count jobs without deleting (useful for preview before actual cleanup)
        current_user: Authenticated superuser (injected by dependency)
        db: Database session (injected by dependency)

    Returns:
        JobCleanupResponse with count of deleted/counted jobs

    Raises:
        HTTPException 403: If user is not a superuser

    **Job Persistence:**
    Jobs persist across restarts with automatic retry and exponential backoff.
    Status tracked in database.

    Example:
        # Preview how many jobs would be deleted (older than 90 days)
        POST /api/v1/extraction/jobs/cleanup?older_than_days=90&dry_run=true

        # Delete all failed jobs older than 7 days
        POST /api/v1/extraction/jobs/cleanup?older_than_days=7&status=failed

        # Delete completed/failed/cancelled jobs older than 30 days (default)
        POST /api/v1/extraction/jobs/cleanup
    """
    from pybase.models.extraction_job import ExtractionJobStatus

    job_service = get_extraction_job_service()

    # Convert JobStatus enum to ExtractionJobStatus if provided
    status_filter = None
    if status is not None:
        # Map string status to ExtractionJobStatus enum
        status_mapping = {
            JobStatus.PENDING: ExtractionJobStatus.PENDING,
            JobStatus.PROCESSING: ExtractionJobStatus.PROCESSING,
            JobStatus.COMPLETED: ExtractionJobStatus.COMPLETED,
            JobStatus.FAILED: ExtractionJobStatus.FAILED,
            JobStatus.CANCELLED: ExtractionJobStatus.CANCELLED,
            JobStatus.RETRYING: ExtractionJobStatus.RETRYING,
        }
        status_filter = status_mapping.get(status)
        if status_filter is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter: {status}",
            )

    # Call cleanup service
    deleted_count = await job_service.cleanup_old_jobs(
        db=db,
        older_than_days=older_than_days,
        status=status_filter,
        dry_run=dry_run,
    )

    return JobCleanupResponse(
        deleted_count=deleted_count,
        dry_run=dry_run,
        older_than_days=older_than_days,
        status_filter=status.value if status else None,
    )


@router.get(
    "/jobs/stats",
    response_model=JobStatsResponse,
    summary="Get job queue statistics",
    description="Get statistics about extraction jobs in the queue. Requires superuser access.",
    tags=["Job Management"],
    responses={
        200: {
            "description": "Statistics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "total_count": 150,
                        "pending_count": 10,
                        "processing_count": 3,
                        "completed_count": 120,
                        "failed_count": 15,
                        "cancelled_count": 2,
                        "retrying_count": 0,
                    }
                }
            },
        },
        403: {
            "description": "Forbidden - Superuser access required",
        },
    },
)
async def get_job_stats(
    current_user: CurrentSuperuser,
    db: DbSession,
    user_id: Annotated[
        str | None,
        Query(description="Optional user ID to filter statistics by (admin only)"),
    ] = None,
) -> JobStatsResponse:
    """
    Get extraction job queue statistics.

    This endpoint provides administrators with visibility into the job queue,
    including counts of jobs by status. Optionally filter by user ID to see
    statistics for a specific user.

    Args:
        current_user: Authenticated superuser (injected by dependency)
        db: Database session (injected by dependency)
        user_id: Optional user ID to filter statistics by

    Returns:
        JobStatsResponse with job counts by status

    Raises:
        HTTPException 403: If user is not a superuser

    **Job Persistence:**
    Jobs persist across restarts with automatic retry and exponential backoff.
    Status tracked in database.

    Example:
        # Get global statistics
        GET /api/v1/extraction/jobs/stats

        # Get statistics for specific user
        GET /api/v1/extraction/jobs/stats?user_id=123e4567-e89b-12d3-a456-426614174000
    """
    job_service = get_extraction_job_service()

    # Get statistics from service
    stats_dict = await job_service.get_job_statistics(db=db, user_id=user_id)

    # Convert to response schema
    return JobStatsResponse(
        total_count=stats_dict.get("total_count", 0),
        pending_count=stats_dict.get("pending_count", 0),
        processing_count=stats_dict.get("processing_count", 0),
        completed_count=stats_dict.get("completed_count", 0),
        failed_count=stats_dict.get("failed_count", 0),
        cancelled_count=stats_dict.get("cancelled_count", 0),
        retrying_count=stats_dict.get("retrying_count", 0),
    )


@router.get(
    "/jobs/stuck",
    response_model=dict[str, Any],
    summary="Find stuck processing jobs",
    description="Find jobs stuck in PROCESSING status longer than timeout. Requires superuser access.",
    tags=["Job Management"],
)
async def find_stuck_jobs(
    current_user: CurrentSuperuser,
    db: DbSession,
    timeout_minutes: Annotated[
        int,
        Query(
            ge=5,
            le=1440,
            description="Minutes before a processing job is considered stuck (5-1440)",
        ),
    ] = 30,
) -> dict[str, Any]:
    """
    Find jobs stuck in PROCESSING status.

    Jobs that have been processing longer than the timeout are considered stuck
    and may need manual intervention or recovery.

    Args:
        current_user: Authenticated superuser
        db: Database session
        timeout_minutes: Minutes threshold (default 30)

    Returns:
        Dict with stuck job IDs and count
    """
    from pybase.services.extraction_job_service import ExtractionJobService

    service = ExtractionJobService(db)
    stuck_jobs = await service.find_stuck_jobs(timeout_minutes=timeout_minutes)

    return {
        "stuck_count": len(stuck_jobs),
        "timeout_minutes": timeout_minutes,
        "stuck_job_ids": [job.id for job in stuck_jobs],
    }


@router.post(
    "/jobs/{job_id}/recover",
    response_model=dict[str, Any],
    summary="Recover a stuck job",
    description="Recover a job stuck in PROCESSING status by marking it for retry. Requires superuser access.",
    tags=["Job Management"],
)
async def recover_stuck_job(
    job_id: str,
    current_user: CurrentSuperuser,
    db: DbSession,
    timeout_minutes: Annotated[
        int,
        Query(
            ge=5,
            le=1440,
            description="Minutes threshold for considering job stuck (5-1440)",
        ),
    ] = 30,
) -> dict[str, Any]:
    """
    Recover a stuck job by marking it for retry.

    Args:
        job_id: Job UUID to recover
        current_user: Authenticated superuser
        db: Database session
        timeout_minutes: Minutes threshold for considering job stuck

    Returns:
        Dict with recovery status and updated job info
    """
    from pybase.services.extraction_job_service import ExtractionJobService

    service = ExtractionJobService(db)

    try:
        job = await service.recover_stuck_job(job_id, timeout_minutes=timeout_minutes)
        return {
            "success": True,
            "job_id": job.id,
            "status": job.status,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "next_retry_at": job.next_retry_at.isoformat() if job.next_retry_at else None,
        }
    except Exception as e:
        return {
            "success": False,
            "job_id": job_id,
            "error": str(e),
        }


@router.post(
    "/jobs/cleanup-orphaned",
    response_model=dict[str, Any],
    summary="Cleanup orphaned jobs",
    description="Cleanup old failed jobs and stuck pending jobs. Requires superuser access.",
    tags=["Job Management"],
)
async def cleanup_orphaned_jobs(
    current_user: CurrentSuperuser,
    db: DbSession,
    failed_older_than_days: Annotated[
        int,
        Query(
            ge=1,
            le=365,
            description="Days before failed jobs are cleaned up (1-365)",
        ),
    ] = 7,
    pending_older_than_days: Annotated[
        int,
        Query(
            ge=1,
            le=30,
            description="Days before pending jobs are considered stuck (1-30)",
        ),
    ] = 1,
) -> dict[str, Any]:
    """
    Cleanup orphaned/abandoned jobs.

    - Failed jobs older than N days: mark as cancelled
    - Pending jobs older than N days: mark as failed (stuck)

    Args:
        current_user: Authenticated superuser
        db: Database session
        failed_older_than_days: Days before failed jobs are cleaned up
        pending_older_than_days: Days before pending jobs are considered stuck

    Returns:
        Dict with cleanup statistics
    """
    from pybase.services.extraction_job_service import ExtractionJobService

    service = ExtractionJobService(db)
    result = await service.cleanup_orphaned_jobs(
        failed_older_than_days=failed_older_than_days,
        pending_older_than_days=pending_older_than_days,
    )

    return result


# =============================================================================
# Import to Table
# =============================================================================


async def generate_bulk_preview(
    bulk_job_id: str | UUID,
    db: AsyncSession,
    table_id: str | UUID | None = None,
) -> dict[str, Any]:
    """
    Generate preview for bulk extraction job.

    Aggregates data from all successfully extracted files:
    - Detects common fields across files
    - Suggests unified field mapping
    - Shows per-file sample data
    - Calculates total record counts

    Args:
        bulk_job_id: Bulk extraction job ID
        db: Database session
        table_id: Optional target table ID for field mapping suggestions

    Returns:
        Dictionary containing bulk preview data structure

    Raises:
        ValueError: If job not found or no completed files
    """
    from pybase.core.exceptions import NotFoundError

    job_id_str = str(bulk_job_id)
    job_service = get_extraction_job_service()

    try:
        # Get job from database
        job_model = await job_service.get_job_by_id(db=db, job_id=job_id_str)
    except NotFoundError:
        raise ValueError(f"Bulk job {job_id_str} not found")

    # Parse results from database
    results_data = {}
    if job_model.results:
        try:
            results_data = (
                json.loads(job_model.results)
                if isinstance(job_model.results, str)
                else job_model.results
            )
        except Exception:
            results_data = {}

    # Parse options to get total files
    options_data = job_model.get_options()
    total_files = len(options_data.get("file_paths", []))

    # Extract file statuses from results
    files = results_data.get("files", [])

    # Extract successfully completed files
    completed_files = [
        f for f in files if f.get("status") == JobStatus.COMPLETED and f.get("result")
    ]

    if not completed_files:
        raise ValueError("No completed files with extraction results")

    # Aggregate data across all files
    all_fields: set[str] = set()
    file_previews: list[dict[str, Any]] = []
    combined_sample_data: list[dict[str, Any]] = []
    total_records = 0

    for file_status in completed_files:
        result = file_status["result"]
        filename = file_status["filename"]
        file_format = file_status["format"]

        # Extract fields and data based on format
        file_fields: set[str] = set()
        file_sample_data: list[dict[str, Any]] = []

        # Process based on result structure
        if isinstance(result, dict):
            # Handle different extraction result types
            if "tables" in result and result["tables"]:
                # PDF or CAD with table data
                for table in result["tables"][:3]:  # Take first 3 tables
                    if "data" in table and table["data"]:
                        # Extract headers as fields
                        if "headers" in table:
                            file_fields.update(table["headers"])
                        # Add sample rows
                        for row_data in table["data"][:5]:  # Max 5 rows per table
                            if isinstance(row_data, dict):
                                file_sample_data.append(row_data)
                                file_fields.update(row_data.keys())
                            elif isinstance(row_data, list) and "headers" in table:
                                # Convert list to dict using headers
                                headers = table["headers"]
                                row_dict = {
                                    headers[i]: row_data[i]
                                    for i in range(min(len(headers), len(row_data)))
                                }
                                file_sample_data.append(row_dict)

            if "dimensions" in result and result["dimensions"]:
                # Add dimension fields
                file_fields.add("dimension_value")
                file_fields.add("dimension_text")
                file_fields.add("dimension_type")
                for dim in result["dimensions"][:5]:
                    if isinstance(dim, dict):
                        dim_row = {
                            "dimension_value": dim.get("value"),
                            "dimension_text": dim.get("text"),
                            "dimension_type": dim.get("type", "linear"),
                        }
                        file_sample_data.append(dim_row)

            if "text_blocks" in result and result["text_blocks"]:
                # Add text block fields
                file_fields.add("text_content")
                file_fields.add("text_page")
                for text in result["text_blocks"][:5]:
                    if isinstance(text, dict):
                        text_row = {
                            "text_content": text.get("text", text.get("content")),
                            "text_page": text.get("page", 1),
                        }
                        file_sample_data.append(text_row)

            if "layers" in result and result["layers"]:
                # DXF layer data
                file_fields.add("layer_name")
                file_fields.add("entity_count")
                for layer in result["layers"][:5]:
                    if isinstance(layer, dict):
                        layer_row = {
                            "layer_name": layer.get("name"),
                            "entity_count": layer.get("entity_count", 0),
                        }
                        file_sample_data.append(layer_row)

            # Add source file metadata to all records
            for record in file_sample_data:
                record["source_file"] = filename
                record["source_format"] = file_format

        # Count total records from this file
        file_record_count = len(file_sample_data)
        total_records += file_record_count

        # Add to combined dataset
        all_fields.update(file_fields)
        combined_sample_data.extend(file_sample_data[:5])  # Max 5 per file

        # Create file preview
        file_previews.append(
            {
                "file_path": file_status["file_path"],
                "filename": filename,
                "format": file_format,
                "source_fields": sorted(list(file_fields)),
                "sample_data": file_sample_data[:5],
                "total_records": file_record_count,
            }
        )

    # Generate suggested field mapping (basic heuristic)
    suggested_mapping: dict[str, str] = {}
    for field in all_fields:
        # Simple name-based mapping (can be enhanced with table schema)
        suggested_mapping[field] = field.lower().replace(" ", "_")

    # Build bulk preview response
    preview = {
        "bulk_job_id": UUID(job_id_str),
        "total_files": total_files,
        "total_records": total_records,
        "source_fields": sorted(list(all_fields)),
        "target_fields": [],  # Will be populated if table_id provided
        "suggested_mapping": suggested_mapping,
        "sample_data": combined_sample_data[:20],  # Limit combined sample
        "file_previews": file_previews,
        "files_with_data": len(completed_files),
        "files_failed": results_data.get("files_failed", 0),
    }

    return preview


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
    extraction_service: Annotated[ExtractionService, Depends(get_extraction_service)],
) -> ImportPreview:
    """
    Preview how extracted data will map to table fields.

    Returns suggested field mappings and sample data.

    **Job Persistence:**
    Job data is retrieved from the database. Jobs persist across restarts
    with automatic retry and exponential backoff. Status tracked in database.
    """
    from uuid import UUID
    from pybase.core.exceptions import NotFoundError

    # Validate job_id format
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format",
        )

    # Validate table_id format
    try:
        table_uuid = UUID(table_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid table ID format",
        )

    # Get job from database
    job_service = get_extraction_job_service()
    try:
        job_model = await job_service.get_job_by_id(db=db, job_id=job_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Validate job is completed and has results
    if job_model.status_enum.value != JobStatus.COMPLETED or not job_model.results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job not completed or has no results",
        )

    # Parse results from database
    try:
        extracted_data = (
            json.loads(job_model.results)
            if isinstance(job_model.results, str)
            else job_model.results
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse job results",
        )

    # Call extraction service to analyze data and suggest mappings
    preview_data = await extraction_service.preview_import(
        db=db,
        user_id=str(current_user.id),
        table_id=str(table_uuid),
        extracted_data=extracted_data,
    )

    return ImportPreview(**preview_data)


@router.post(
    "/import",
    response_model=ImportResponse,
    summary="Import extracted data",
)
async def import_extracted_data(
    request: ImportRequest,
    current_user: CurrentUser,
    db: DbSession,
    extraction_service: Annotated[ExtractionService, Depends(get_extraction_service)],
) -> ImportResponse:
    """
    Import extracted data into a table.

    Requires completed extraction job and field mapping.

    **Job Persistence:**
    Job data is retrieved from the database. Jobs persist across restarts
    with automatic retry and exponential backoff. Status tracked in database.
    """
    from pybase.core.exceptions import NotFoundError

    # Get job from database
    job_service = get_extraction_job_service()
    try:
        job_model = await job_service.get_job_by_id(db=db, job_id=str(request.job_id))
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Validate job is completed and has results
    if job_model.status_enum.value != JobStatus.COMPLETED or not job_model.results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job not completed or has no results",
        )

    # Parse results from database
    try:
        extracted_data = (
            json.loads(job_model.results)
            if isinstance(job_model.results, str)
            else job_model.results
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse job results",
        )

    # Call extraction service to import data
    try:
        result = await extraction_service.import_data(
            db=db,
            user_id=str(current_user.id),
            table_id=str(request.table_id),
            extracted_data=extracted_data,
            field_mapping=request.field_mapping,
            create_missing_fields=request.create_missing_fields,
            skip_errors=request.skip_errors,
        )

        return ImportResponse(**result)

    except Exception as e:
        # Re-raise known exceptions
        if isinstance(e, (HTTPException,)):
            raise
        # Handle service exceptions
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        )


async def bulk_import_to_table(
    bulk_job_id: UUID,
    table_id: UUID,
    field_mapping: dict[str, str],
    db: DbSession,
    user_id: str,
    file_selection: list[str] | None = None,
    create_missing_fields: bool = False,
    skip_errors: bool = True,
    include_source_file: bool = True,
) -> ImportResponse:
    """
    Import data from bulk extraction job into a table.

    Iterates through all successfully completed files in bulk job,
    creates records with source file metadata, and tracks per-file results.

    Args:
        bulk_job_id: Bulk extraction job ID
        table_id: Target table ID
        field_mapping: Mapping of source fields to target field IDs
        db: Database session
        user_id: User ID performing import
        file_selection: Optional list of file paths to import (imports all if None)
        create_missing_fields: Create fields that don't exist in target table
        skip_errors: Continue import on row errors
        include_source_file: Add source_file metadata to records

    Returns:
        ImportResponse with statistics and errors

    Raises:
        HTTPException: If bulk job not found or not completed

    **Job Persistence:**
    Job data is retrieved from the database. Jobs persist across restarts
    with automatic retry and exponential backoff. Status tracked in database.
    """
    from pybase.core.exceptions import NotFoundError
    from pybase.models.field import FieldType
    from pybase.schemas.field import FieldCreate
    from pybase.schemas.record import RecordCreate
    from pybase.services.field import FieldService
    from pybase.services.record import RecordService

    # Get bulk job from database
    job_service = get_extraction_job_service()
    try:
        job_model = await job_service.get_job_by_id(db=db, job_id=str(bulk_job_id))
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk job not found",
        )

    # Parse results from database
    results_data = {}
    if job_model.results:
        try:
            results_data = (
                json.loads(job_model.results)
                if isinstance(job_model.results, str)
                else job_model.results
            )
        except Exception:
            results_data = {}

    # Initialize services
    record_service = RecordService()
    field_service = FieldService()

    # Track statistics
    records_imported = 0
    records_failed = 0
    errors: list[dict[str, Any]] = []
    created_field_ids: list[UUID] = []

    # Handle create_missing_fields: create TEXT fields for unmapped source fields
    if create_missing_fields:
        # Get existing fields in the target table
        existing_fields = await field_service.list_fields(db, user_id, table_id)
        existing_field_ids = {str(f.id) for f in existing_fields}

        # Find target field IDs that don't exist
        for source_field, target_field_id in field_mapping.items():
            if target_field_id not in existing_field_ids:
                try:
                    # Create new TEXT field with source field name
                    new_field = await field_service.create_field(
                        db=db,
                        user_id=user_id,
                        field_data=FieldCreate(
                            table_id=table_id,
                            name=source_field,
                            field_type=FieldType.TEXT,
                            description=f"Auto-created from extraction import",
                        ),
                    )
                    created_field_ids.append(new_field.id)
                    # Update field_mapping to use the new field ID
                    field_mapping[source_field] = str(new_field.id)
                except Exception as e:
                    errors.append(
                        {
                            "field": source_field,
                            "error": f"Failed to create field: {str(e)}",
                        }
                    )

    # Get files to import from results
    files_to_import = results_data.get("files", [])

    # Filter by file_selection if provided
    if file_selection:
        files_to_import = [f for f in files_to_import if f.get("file_path") in file_selection]

    # Process each file
    for file_status in files_to_import:
        # Skip files that didn't complete successfully
        if file_status.get("status") != "completed" or not file_status.get("result"):
            continue

        file_path = file_status.get("file_path", "unknown")
        filename = file_status.get("filename", "unknown")
        extraction_format = file_status.get("format", "unknown")
        result = file_status.get("result", {})

        # Extract data rows from result based on format
        data_rows = _extract_data_rows_from_result(
            result=result,
            extraction_format=extraction_format,
        )

        # Create records for this file
        for idx, row_data in enumerate(data_rows):
            try:
                # Apply field mapping
                mapped_data: dict[str, Any] = {}
                for source_field, target_field_id in field_mapping.items():
                    if source_field in row_data:
                        mapped_data[target_field_id] = row_data[source_field]

                # Add source file metadata if requested
                if include_source_file:
                    mapped_data["source_file"] = filename
                    mapped_data["source_format"] = extraction_format
                    mapped_data["extraction_job_id"] = str(bulk_job_id)
                    # Use actual extraction time from file_status, not import time
                    extraction_time = file_status.get("completed_at")
                    if extraction_time:
                        # Handle both datetime objects and ISO strings
                        if isinstance(extraction_time, datetime):
                            mapped_data["extraction_timestamp"] = extraction_time.isoformat()
                        else:
                            mapped_data["extraction_timestamp"] = str(extraction_time)
                    else:
                        mapped_data["extraction_timestamp"] = datetime.now(timezone.utc).isoformat()

                # Create record
                record_create = RecordCreate(
                    table_id=table_id,
                    data=mapped_data,
                )

                await record_service.create_record(
                    db=db,
                    user_id=user_id,
                    record_data=record_create,
                )

                records_imported += 1

            except Exception as e:
                records_failed += 1
                errors.append(
                    {
                        "file": filename,
                        "row": idx,
                        "error": str(e),
                    }
                )

                # Stop if skip_errors is False
                if not skip_errors:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Import failed at file {filename}, row {idx}: {str(e)}",
                    )

    return ImportResponse(
        success=records_failed == 0,
        records_imported=records_imported,
        records_failed=records_failed,
        errors=errors,
        created_field_ids=created_field_ids,
    )


def _extract_data_rows_from_result(
    result: dict[str, Any],
    extraction_format: str,
) -> list[dict[str, Any]]:
    """
    Extract data rows from extraction result based on format.

    Handles different extraction result structures for PDF, DXF, IFC, STEP formats.

    Args:
        result: Extraction result dictionary
        extraction_format: Format type (pdf, dxf, ifc, step, werk24)

    Returns:
        List of data rows ready for import
    """
    data_rows: list[dict[str, Any]] = []

    # Handle PDF format
    if extraction_format == "pdf":
        # Extract from tables
        for table in result.get("tables", []):
            data_rows.extend(table.get("data", []))

        # Extract from text blocks
        for text_block in result.get("text_blocks", []):
            data_rows.append(
                {
                    "text": text_block.get("text", ""),
                    "page": text_block.get("page", 0),
                    "bbox": str(text_block.get("bbox", [])),
                }
            )

        # Extract from dimensions
        for dimension in result.get("dimensions", []):
            data_rows.append(
                {
                    "value": dimension.get("value", ""),
                    "type": dimension.get("type", ""),
                    "page": dimension.get("page", 0),
                }
            )

    # Handle DXF format
    elif extraction_format == "dxf":
        # Extract from layers
        for layer in result.get("layers", []):
            data_rows.append(
                {
                    "layer_name": layer.get("name", ""),
                    "entity_count": layer.get("entity_count", 0),
                    "color": layer.get("color", ""),
                }
            )

        # Extract from text entities
        for text in result.get("text_entities", []):
            data_rows.append(
                {
                    "text": text.get("text", ""),
                    "layer": text.get("layer", ""),
                    "position": str(text.get("position", [])),
                }
            )

        # Extract from dimensions
        for dimension in result.get("dimensions", []):
            data_rows.append(
                {
                    "value": dimension.get("measurement", ""),
                    "type": dimension.get("type", ""),
                    "layer": dimension.get("layer", ""),
                }
            )

    # Handle IFC format
    elif extraction_format == "ifc":
        # Extract from elements
        for element in result.get("elements", []):
            data_rows.append(
                {
                    "ifc_type": element.get("ifc_type", ""),
                    "name": element.get("name", ""),
                    "global_id": element.get("global_id", ""),
                    "properties": str(element.get("properties", {})),
                }
            )

    # Handle STEP format
    elif extraction_format == "step":
        # Extract from assemblies
        for assembly in result.get("assemblies", []):
            data_rows.append(
                {
                    "name": assembly.get("name", ""),
                    "part_count": assembly.get("part_count", 0),
                }
            )

        # Extract from parts
        for part in result.get("parts", []):
            data_rows.append(
                {
                    "name": part.get("name", ""),
                    "material": part.get("material", ""),
                    "volume": part.get("volume", 0),
                }
            )

    # Handle Werk24 format
    elif extraction_format == "werk24":
        # Extract from identified features
        for feature in result.get("features", []):
            data_rows.append(
                {
                    "feature_type": feature.get("type", ""),
                    "value": feature.get("value", ""),
                    "confidence": feature.get("confidence", 0),
                }
            )

    return data_rows
