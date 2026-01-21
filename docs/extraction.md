# PyBase Extraction System Documentation

> **Engineering-First Data Extraction**
> Extract tables, dimensions, GD&T, and metadata from CAD files and technical drawings

## Overview

PyBase provides a comprehensive extraction system for engineering documents and CAD files. The system automatically extracts structured data from PDFs, DXF, IFC, STEP files, and engineering drawings, enabling teams to transform static documents into queryable databases.

### Key Features

- **Multi-Format Support**: PDF, DXF, IFC, STEP, and images
- **Engineering Intelligence**: Dimension extraction, GD&T parsing, thread specifications
- **AI-Powered Analysis**: Werk24 API integration for engineering drawings
- **Table Detection**: Automatic BOM and parts list extraction
- **Title Block Recognition**: Metadata extraction from drawing borders
- **Async Processing**: Background job queue for large files
- **Import Workflow**: Direct integration with PyBase tables

### Architecture

```
File Upload → Validation → Extraction → Normalization → Import to Table
                                ↓
                    [PDF | DXF | IFC | STEP | Werk24]
                                ↓
                    [Tables | Dimensions | Text | Metadata]
```

---

## Supported File Formats

| Format | Extensions | Extractors | Engineering Data |
|--------|-----------|------------|------------------|
| **PDF** | `.pdf` | pdfplumber, pypdf, OCR | Tables, dimensions, title blocks, BOM |
| **DXF/DWG** | `.dxf`, `.dwg` | ezdxf | Layers, blocks, dimensions, text, title blocks |
| **IFC/BIM** | `.ifc` | ifcopenshell | Elements, properties, quantities, materials |
| **STEP** | `.stp`, `.step` | OCP/build123d | Assembly, parts, volumes, surface areas |
| **Images** | `.png`, `.jpg`, `.tif` | pytesseract (OCR) | Text extraction |
| **Werk24** | `.pdf`, images | Werk24 AI API | Dimensions, GD&T, threads, surface finish |

---

## API Endpoints

Base path: `/api/v1/extraction`

### PDF Extraction

**Endpoint:** `POST /extraction/pdf`

Extract tables, text, dimensions, and metadata from PDF documents.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/extraction/pdf" \
  -H "Authorization: Bearer <token>" \
  -F "file=@drawing.pdf" \
  -F "extract_tables=true" \
  -F "extract_text=true" \
  -F "extract_dimensions=true" \
  -F "use_ocr=false" \
  -F "pages=1,2,3"
```

**Form Parameters:**
- `file` (required): PDF file
- `extract_tables` (boolean): Extract tables (default: true)
- `extract_text` (boolean): Extract text blocks (default: true)
- `extract_dimensions` (boolean): Extract dimension callouts (default: false)
- `use_ocr` (boolean): Use OCR for scanned documents (default: false)
- `ocr_language` (string): OCR language code (default: "eng")
- `pages` (string): Comma-separated page numbers (default: all pages)

**Response:**
```json
{
  "source_file": "drawing.pdf",
  "source_type": "pdf",
  "success": true,
  "tables": [
    {
      "headers": ["Part Number", "Description", "Qty", "Material"],
      "rows": [
        ["BRG-001", "Ball Bearing", 2, "Steel"],
        ["SFT-001", "Drive Shaft", 1, "AISI 4140"]
      ],
      "page": 1,
      "confidence": 0.95,
      "bbox": [50, 200, 550, 400],
      "num_rows": 2,
      "num_columns": 4
    }
  ],
  "dimensions": [
    {
      "value": 50.0,
      "unit": "mm",
      "tolerance_plus": 0.1,
      "tolerance_minus": 0.1,
      "dimension_type": "linear",
      "page": 1,
      "confidence": 0.88
    }
  ],
  "text_blocks": [
    {
      "text": "ASSEMBLY DRAWING",
      "page": 1,
      "confidence": 1.0,
      "font_size": 12.0,
      "is_title": true
    }
  ],
  "title_block": {
    "drawing_number": "DWG-001-A",
    "title": "Main Assembly",
    "revision": "C",
    "material": "AISI 304",
    "scale": "1:2"
  },
  "bom": {
    "items": [...],
    "headers": ["Item", "Part No", "Description"],
    "total_items": 15
  },
  "metadata": {
    "page_count": 3,
    "pdf_version": "1.4"
  },
  "errors": [],
  "warnings": []
}
```

---

### DXF/DWG Extraction

**Endpoint:** `POST /extraction/dxf`

Extract layers, blocks, dimensions, and text from AutoCAD files.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/extraction/dxf" \
  -H "Authorization: Bearer <token>" \
  -F "file=@mechanical_part.dxf" \
  -F "extract_layers=true" \
  -F "extract_blocks=true" \
  -F "extract_dimensions=true" \
  -F "extract_text=true" \
  -F "extract_title_block=true"
```

**Form Parameters:**
- `file` (required): DXF/DWG file
- `extract_layers` (boolean): Extract layer information (default: true)
- `extract_blocks` (boolean): Extract block definitions (default: true)
- `extract_dimensions` (boolean): Extract dimension entities (default: true)
- `extract_text` (boolean): Extract TEXT/MTEXT entities (default: true)
- `extract_title_block` (boolean): Detect title block from blocks (default: true)
- `extract_geometry` (boolean): Extract geometry summary (default: false)

**Response:**
```json
{
  "source_file": "mechanical_part.dxf",
  "source_type": "dxf",
  "success": true,
  "layers": [
    {
      "name": "DIMENSIONS",
      "color": 3,
      "linetype": "Continuous",
      "is_on": true,
      "entity_count": 47
    }
  ],
  "blocks": [
    {
      "name": "TITLE_BLOCK_A3",
      "description": "Standard title block",
      "attributes": {
        "DRAWING_NO": "DWG-001",
        "REVISION": "B"
      }
    }
  ],
  "dimensions": [
    {
      "value": 25.4,
      "unit": "mm",
      "tolerance_plus": 0.05,
      "tolerance_minus": 0.05,
      "dimension_type": "linear"
    }
  ],
  "text_blocks": [
    {
      "text": "NOTE: ALL DIMENSIONS IN MM",
      "font_size": 3.5
    }
  ],
  "title_block": {
    "drawing_number": "DWG-001",
    "revision": "B",
    "company": "ACME Engineering"
  },
  "metadata": {
    "dxf_version": "AC1027",
    "layer_count": 12,
    "block_count": 5
  }
}
```

---

### IFC/BIM Extraction

**Endpoint:** `POST /extraction/ifc`

Extract building elements, properties, and materials from IFC files.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/extraction/ifc" \
  -H "Authorization: Bearer <token>" \
  -F "file=@building_model.ifc" \
  -F "extract_properties=true" \
  -F "extract_quantities=true" \
  -F "extract_materials=true" \
  -F "extract_spatial=true" \
  -F "element_types=IfcWall,IfcDoor,IfcWindow"
```

**Form Parameters:**
- `file` (required): IFC file
- `extract_properties` (boolean): Extract property sets (default: true)
- `extract_quantities` (boolean): Extract quantity takeoffs (default: true)
- `extract_materials` (boolean): Extract material assignments (default: true)
- `extract_spatial` (boolean): Extract spatial hierarchy (default: true)
- `element_types` (string): Comma-separated IFC types to extract (default: all)

**Response:**
```json
{
  "source_file": "building_model.ifc",
  "source_type": "ifc",
  "success": true,
  "entities": [
    {
      "type": "IfcWall",
      "global_id": "2O2Fr$t4X7Zf8NOew3FLOH",
      "name": "Wall-001",
      "properties": {
        "LoadBearing": true,
        "FireRating": "2HR",
        "ThermalTransmittance": 0.26
      },
      "quantities": {
        "Length": 4.5,
        "Width": 0.2,
        "Height": 3.0,
        "GrossVolume": 2.7
      },
      "material": "Concrete 200mm"
    }
  ],
  "metadata": {
    "schema": "IFC4",
    "project_name": "Office Building",
    "element_counts": {
      "IfcWall": 124,
      "IfcDoor": 38,
      "IfcWindow": 56
    }
  }
}
```

---

### STEP Extraction

**Endpoint:** `POST /extraction/step`

Extract assembly structure and part information from STEP files.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/extraction/step" \
  -H "Authorization: Bearer <token>" \
  -F "file=@assembly.step" \
  -F "extract_assembly=true" \
  -F "extract_parts=true" \
  -F "calculate_volumes=true" \
  -F "calculate_areas=true"
```

**Form Parameters:**
- `file` (required): STEP file
- `extract_assembly` (boolean): Extract assembly structure (default: true)
- `extract_parts` (boolean): Extract part information (default: true)
- `calculate_volumes` (boolean): Calculate part volumes (default: true)
- `calculate_areas` (boolean): Calculate surface areas (default: true)
- `count_shapes` (boolean): Count geometric shapes (default: true)

**Response:**
```json
{
  "source_file": "assembly.step",
  "source_type": "step",
  "success": true,
  "entities": [
    {
      "type": "part",
      "name": "Housing",
      "volume": 125000.0,
      "surface_area": 45000.0,
      "bbox": {
        "min": [0, 0, 0],
        "max": [100, 50, 25]
      }
    }
  ],
  "geometry_summary": {
    "total_parts": 12,
    "total_volume": 750000.0,
    "shape_counts": {
      "solids": 12,
      "shells": 24,
      "faces": 348
    }
  }
}
```

---

### Werk24 AI Extraction

**Endpoint:** `POST /extraction/werk24`

Extract engineering data using Werk24 AI API (requires API key).

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/extraction/werk24" \
  -H "Authorization: Bearer <token>" \
  -F "file=@technical_drawing.pdf" \
  -F "extract_dimensions=true" \
  -F "extract_gdt=true" \
  -F "extract_threads=true" \
  -F "extract_surface_finish=true" \
  -F "confidence_threshold=0.7"
```

**Form Parameters:**
- `file` (required): Drawing file (PDF or image)
- `extract_dimensions` (boolean): Extract dimensions with tolerances (default: true)
- `extract_gdt` (boolean): Extract GD&T annotations (default: true)
- `extract_threads` (boolean): Extract thread specifications (default: true)
- `extract_surface_finish` (boolean): Extract surface finish symbols (default: true)
- `extract_materials` (boolean): Extract material callouts (default: true)
- `extract_title_block` (boolean): Extract title block (default: true)
- `confidence_threshold` (float): Minimum confidence score (0.0-1.0, default: 0.7)

**Response:**
```json
{
  "source_file": "technical_drawing.pdf",
  "source_type": "werk24",
  "success": true,
  "dimensions": [
    {
      "value": 50.0,
      "unit": "mm",
      "tolerance_plus": 0.1,
      "tolerance_minus": 0.05,
      "dimension_type": "linear",
      "confidence": 0.92
    }
  ],
  "gdt_annotations": [
    {
      "symbol": "perpendicularity",
      "tolerance": 0.05,
      "datum": "A",
      "confidence": 0.88
    }
  ],
  "threads": [
    {
      "designation": "M12x1.5",
      "type": "metric",
      "confidence": 0.95
    }
  ],
  "surface_finishes": [
    {
      "symbol": "Ra 3.2",
      "value": 3.2,
      "unit": "μm"
    }
  ],
  "title_block": {
    "drawing_number": "DWG-2024-001",
    "title": "Shaft Assembly",
    "revision": "A"
  }
}
```

---

## Job Management (Async Processing)

For large files or batch processing, use the asynchronous job API.

### Create Extraction Job

**Endpoint:** `POST /extraction/jobs`

```bash
curl -X POST "http://localhost:8000/api/v1/extraction/jobs" \
  -H "Authorization: Bearer <token>" \
  -F "file=@large_assembly.pdf" \
  -F "format=pdf" \
  -F "target_table_id=tbl_abc123"
```

**Response:**
```json
{
  "id": "job_xyz789",
  "status": "pending",
  "format": "pdf",
  "filename": "large_assembly.pdf",
  "file_size": 52428800,
  "progress": 0,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Get Job Status

**Endpoint:** `GET /extraction/jobs/{job_id}`

```bash
curl "http://localhost:8000/api/v1/extraction/jobs/job_xyz789" \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "id": "job_xyz789",
  "status": "completed",
  "format": "pdf",
  "filename": "large_assembly.pdf",
  "progress": 100,
  "result": {
    "tables": [...],
    "dimensions": [...]
  },
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:32:45Z"
}
```

**Job Statuses:**
- `pending`: Queued for processing
- `processing`: Currently extracting
- `completed`: Successfully finished
- `failed`: Extraction failed
- `cancelled`: Job was cancelled

### List Jobs

**Endpoint:** `GET /extraction/jobs`

```bash
curl "http://localhost:8000/api/v1/extraction/jobs?status=completed&page=1&page_size=20" \
  -H "Authorization: Bearer <token>"
```

---

## Import to Table

### Preview Import

**Endpoint:** `POST /extraction/jobs/{job_id}/preview`

Preview how extracted data will map to table fields.

```bash
curl -X POST "http://localhost:8000/api/v1/extraction/jobs/job_xyz789/preview?table_id=tbl_abc123" \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "source_fields": ["Part Number", "Description", "Qty", "Material"],
  "target_fields": [
    {"id": "fld_001", "name": "Part Number", "type": "text"},
    {"id": "fld_002", "name": "Description", "type": "long_text"},
    {"id": "fld_003", "name": "Quantity", "type": "number"},
    {"id": "fld_004", "name": "Material", "type": "material"}
  ],
  "suggested_mapping": {
    "Part Number": "fld_001",
    "Description": "fld_002",
    "Qty": "fld_003",
    "Material": "fld_004"
  },
  "sample_data": [
    {
      "Part Number": "BRG-001",
      "Description": "Ball Bearing",
      "Qty": 2,
      "Material": "Steel"
    }
  ],
  "total_records": 15
}
```

### Execute Import

**Endpoint:** `POST /extraction/import`

Import extracted data into a PyBase table.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/extraction/import" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job_xyz789",
    "table_id": "tbl_abc123",
    "field_mapping": {
      "Part Number": "fld_001",
      "Description": "fld_002"
    },
    "create_missing_fields": true,
    "skip_duplicates": true
  }'
```

**Response:**
```json
{
  "success": true,
  "records_imported": 15,
  "records_failed": 0,
  "errors": [],
  "created_field_ids": ["fld_005", "fld_006"]
}
```

---

## Data Models

### Extracted Table

```python
@dataclass
class ExtractedTable:
    headers: list[str]              # Column headers
    rows: list[list[Any]]           # Table data rows
    page: int | None                # Page number (PDF)
    confidence: float               # 0.0-1.0 confidence score
    bbox: tuple[float, ...]         # Bounding box (x1, y1, x2, y2)
    num_rows: int                   # Number of data rows
    num_columns: int                # Number of columns
```

### Extracted Dimension

```python
@dataclass
class ExtractedDimension:
    value: float                    # Nominal dimension value
    unit: str                       # "mm", "in", "deg", etc.
    tolerance_plus: float | None    # Upper tolerance
    tolerance_minus: float | None   # Lower tolerance
    dimension_type: str             # "linear", "angular", "radius", "diameter"
    label: str | None               # Dimension label/reference
    page: int | None                # Page number
    confidence: float               # Extraction confidence
    bbox: tuple[float, ...]         # Bounding box
```

### Extracted Title Block

```python
@dataclass
class ExtractedTitleBlock:
    drawing_number: str | None
    title: str | None
    revision: str | None
    date: str | None
    author: str | None
    company: str | None
    scale: str | None
    sheet: str | None
    material: str | None
    finish: str | None
    custom_fields: dict[str, str]   # Additional fields
    confidence: float
```

### Extraction Result

```python
@dataclass
class ExtractionResult:
    source_file: str                # Original filename
    source_type: str                # "pdf", "dxf", "ifc", "step"
    success: bool                   # Overall success flag
    tables: list[ExtractedTable]
    dimensions: list[ExtractedDimension]
    text_blocks: list[ExtractedText]
    title_block: ExtractedTitleBlock | None
    bom: ExtractedBOM | None
    metadata: dict[str, Any]        # Format-specific metadata
    errors: list[str]               # Error messages
    warnings: list[str]             # Warning messages
```

---

## Configuration

### Environment Variables

```bash
# Werk24 API (optional)
WERK24_API_KEY=your_api_key_here

# OCR Language (optional)
TESSERACT_LANG=eng

# File Upload Limits
MAX_FILE_SIZE=104857600  # 100 MB in bytes

# Processing Timeouts
EXTRACTION_TIMEOUT=300   # 5 minutes
```

### Dependencies

Install extraction dependencies:

```bash
# Core PDF extraction
pip install pdfplumber pypdf

# CAD extraction
pip install ezdxf ifcopenshell

# STEP extraction (choose one)
pip install build123d  # Recommended
# OR
pip install OCP  # Alternative

# OCR (optional)
pip install pytesseract Pillow
sudo apt-get install tesseract-ocr  # Linux
brew install tesseract  # macOS

# Werk24 API (optional)
pip install werk24
```

**Full installation:**
```bash
pip install "pybase[extraction]"
```

---

## Usage Examples

### Extract BOM from PDF

```python
from pybase.extraction import PDFExtractor

extractor = PDFExtractor()
result = extractor.extract(
    "assembly_drawing.pdf",
    extract_tables=True,
    extract_text=False
)

# Find BOM table
for table in result.tables:
    if "part" in str(table.headers).lower():
        records = table.to_records()
        for record in records:
            print(f"{record['Part Number']}: {record['Description']}")
```

### Extract Dimensions from DXF

```python
from pybase.extraction import DXFParser

parser = DXFParser()
result = parser.parse(
    "mechanical_part.dxf",
    extract_dimensions=True,
    extract_title_block=True
)

print(f"Drawing: {result.title_block.drawing_number}")
print(f"Found {len(result.dimensions)} dimensions")

for dim in result.dimensions:
    print(dim.format_display())  # e.g., "50.0 ±0.1 mm"
```

### Extract IFC Properties

```python
from pybase.extraction import IFCParser

parser = IFCParser()
result = parser.parse(
    "building_model.ifc",
    extract_properties=True,
    element_types=["IfcWall", "IfcDoor"]
)

for entity in result.entities:
    if entity.type == "IfcWall":
        print(f"{entity.name}: {entity.properties.get('LoadBearing')}")
```

### Async Job Processing

```python
import httpx
import asyncio

async def process_large_file():
    async with httpx.AsyncClient() as client:
        # Upload and create job
        files = {"file": open("large_drawing.pdf", "rb")}
        data = {"format": "pdf"}
        response = await client.post(
            "http://localhost:8000/api/v1/extraction/jobs",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {token}"}
        )
        job_id = response.json()["id"]

        # Poll for completion
        while True:
            status_response = await client.get(
                f"http://localhost:8000/api/v1/extraction/jobs/{job_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            job = status_response.json()

            if job["status"] == "completed":
                return job["result"]
            elif job["status"] == "failed":
                raise Exception(f"Job failed: {job['error_message']}")

            await asyncio.sleep(2)

result = asyncio.run(process_large_file())
```

---

## Best Practices

### File Validation

Always validate files before extraction:

```python
def validate_pdf(file_path: str) -> bool:
    """Check if file is valid PDF."""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(5)
            return header == b'%PDF-'
    except:
        return False
```

### Error Handling

```python
result = extractor.extract("drawing.pdf")

if not result.success:
    print(f"Extraction failed: {result.errors}")
    return

if result.warnings:
    print(f"Warnings: {result.warnings}")

# Check confidence scores
for table in result.tables:
    if table.confidence < 0.8:
        print(f"Low confidence table on page {table.page}")
```

### Performance Optimization

1. **Extract specific pages only**:
   ```python
   result = extractor.extract("large.pdf", pages=[1, 2, 3])
   ```

2. **Disable unnecessary extraction**:
   ```python
   result = extractor.extract(
       "drawing.pdf",
       extract_tables=True,
       extract_text=False,      # Skip if not needed
       extract_dimensions=False # Skip if not needed
   )
   ```

3. **Use async jobs for large files** (> 10 MB)

4. **Batch processing**:
   ```python
   files = ["file1.pdf", "file2.pdf", "file3.pdf"]
   jobs = [create_job(f) for f in files]
   results = await asyncio.gather(*[poll_job(j) for j in jobs])
   ```

### Security

1. **Validate file size**:
   ```python
   MAX_SIZE = 100 * 1024 * 1024  # 100 MB
   if file.size > MAX_SIZE:
       raise ValueError("File too large")
   ```

2. **Sanitize filenames**:
   ```python
   import re
   safe_name = re.sub(r'[^\w\-.]', '_', filename)
   ```

3. **Limit extraction time**:
   ```python
   import signal

   signal.alarm(300)  # 5 minute timeout
   result = extractor.extract(file_path)
   signal.alarm(0)
   ```

---

## Troubleshooting

### Common Issues

#### PDF Tables Not Detected

**Problem**: `result.tables` is empty for PDF with tables

**Solutions**:
- Ensure tables have clear borders
- Try different extraction methods (pdfplumber vs tabula)
- Check if PDF is image-based (use OCR)
- Increase table detection sensitivity

```python
# Enable OCR for scanned PDFs
result = extractor.extract("scanned.pdf", use_ocr=True)
```

#### Low Confidence Scores

**Problem**: Extracted data has confidence < 0.7

**Solutions**:
- Improve source document quality
- Use Werk24 API for engineering drawings
- Manually review and correct low-confidence extractions
- Adjust confidence threshold

#### DXF Title Block Not Found

**Problem**: `result.title_block` is None for DXF with title block

**Solutions**:
- Title block must be a BLOCK with attributes
- Check attribute tag names match expected patterns
- Add custom field mappings

#### IFC Elements Missing

**Problem**: Expected IFC elements not extracted

**Solutions**:
- Specify element types explicitly
- Check IFC schema version compatibility
- Verify elements exist in source file

```python
result = parser.parse(
    "model.ifc",
    element_types=["IfcWall", "IfcWallStandardCase"]  # Include subtypes
)
```

#### Werk24 API Errors

**Problem**: 503 Service Unavailable

**Solutions**:
- Verify `WERK24_API_KEY` is set
- Check API quota/limits
- Ensure file format is supported
- Review API documentation for rate limits

### Debug Mode

Enable detailed logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('pybase.extraction')

result = extractor.extract("drawing.pdf")
```

### Performance Issues

**Problem**: Extraction takes too long

**Diagnostics**:
```python
import time

start = time.time()
result = extractor.extract("large.pdf")
print(f"Extraction took {time.time() - start:.2f}s")
```

**Solutions**:
- Use async jobs for files > 10 MB
- Extract specific pages only
- Disable unnecessary extraction features
- Increase server resources (CPU/RAM)

---

## Integration Patterns

### Webhook Notifications

Receive extraction completion notifications:

```python
# Configure webhook in automation
automation = {
    "trigger": "extraction_completed",
    "actions": [
        {
            "type": "send_webhook",
            "url": "https://your-app.com/extraction-webhook",
            "payload": {
                "job_id": "{{job.id}}",
                "status": "{{job.status}}",
                "filename": "{{job.filename}}"
            }
        }
    ]
}
```

### Auto-Import Workflow

Automatically import extracted data:

```python
# 1. Upload and extract
job = create_extraction_job("drawing.pdf", format="pdf")

# 2. Wait for completion
result = await poll_job_completion(job.id)

# 3. Auto-import to table
import_response = await import_to_table(
    job_id=job.id,
    table_id="tbl_parts",
    create_missing_fields=True
)
```

### Batch Processing Pipeline

```python
async def process_folder(folder_path: str, table_id: str):
    """Process all PDFs in folder and import to table."""
    pdf_files = Path(folder_path).glob("*.pdf")

    for pdf_file in pdf_files:
        # Create job
        job = await create_extraction_job(str(pdf_file))

        # Wait for completion
        result = await poll_job_completion(job.id)

        # Import if successful
        if result.success:
            await import_to_table(job.id, table_id)
        else:
            logger.error(f"Failed to extract {pdf_file}: {result.errors}")
```

---

## API Reference Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/extraction/pdf` | POST | Extract from PDF |
| `/extraction/dxf` | POST | Extract from DXF/DWG |
| `/extraction/ifc` | POST | Extract from IFC |
| `/extraction/step` | POST | Extract from STEP |
| `/extraction/werk24` | POST | Extract via Werk24 API |
| `/extraction/jobs` | POST | Create extraction job |
| `/extraction/jobs/{id}` | GET | Get job status |
| `/extraction/jobs` | GET | List jobs |
| `/extraction/jobs/{id}` | DELETE | Cancel/delete job |
| `/extraction/jobs/{id}/preview` | POST | Preview import mapping |
| `/extraction/import` | POST | Import to table |

---

## Version History

- **v1.0.0** (2024-01): Initial release with PDF, DXF, IFC support
- **v1.1.0** (2024-02): Added STEP extraction
- **v1.2.0** (2024-03): Werk24 API integration
- **v1.3.0** (2024-04): Async job processing

---

## Additional Resources

- [PyBase API Reference](./api.md)
- [Field Types Documentation](./field-types.md)
- [Engineering Field Types](./engineering-fields.md)
- [Automation Guide](./automation.md)
- [Phase 3 Implementation Plan](./master-plan-phase-3-extraction.md)

**Support**: For issues or questions, contact engineering@pybase.io
