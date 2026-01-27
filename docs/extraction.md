# Extraction System

> Comprehensive CAD/PDF data extraction for engineering teams

PyBase provides powerful extraction capabilities for engineering data from CAD files, PDFs, and technical drawings. Extract tables, dimensions, annotations, GD&T symbols, materials, and metadata automatically.

## Overview

The extraction system supports multiple file formats and extraction methods, each optimized for specific use cases:

### Supported Formats

| Format | Type | Extraction Capabilities | Documentation |
|--------|------|------------------------|---------------|
| **PDF** | Technical drawings, tables | Tables, text, dimensions, title blocks, Werk24 AI | [PDF Extraction](#pdf-extraction) |
| **DXF/DWG** | AutoCAD drawings | Layers, blocks, dimensions, attributes, title blocks | [CAD Extraction](#cad-extraction) |
| **IFC** | BIM/Revit models | Building elements, properties, quantities, materials | [CAD Extraction](#cad-extraction) |
| **STEP/STP** | 3D CAD models | Geometry, assemblies, manufacturing data, metadata | [CAD Extraction](#cad-extraction) |
| **CosCAD** | Aerospace/automotive CAD | Geometry, dimensions, GD&T, annotations, metadata | [CosCAD Setup](./coscad_extraction_setup.md) |
| **Images** | Scanned drawings | OCR text extraction, Werk24 AI analysis | [Werk24 Integration](./werk24-integration.md) |

### Extraction Methods

- **PDFPlumber**: Python library for PDF table and text extraction
- **Tabula**: Java-based PDF table extraction for complex layouts
- **PyMuPDF (fitz)**: High-performance PDF text and metadata extraction
- **ezdxf**: AutoCAD DXF file parsing with geometry and attributes
- **IfcOpenShell**: IFC/BIM file processing for building data
- **CadQuery/PythonOCC**: STEP file 3D geometry and topology extraction
- **Werk24 AI**: AI-powered engineering drawing analysis (dimensions, GD&T, threads, materials)
- **CosCAD gRPC**: Proprietary CAD format extraction for aerospace/automotive
- **OCR (Tesseract)**: Optical character recognition for scanned drawings
- **YOLOv11 + Donut**: Custom ML models for drawing understanding (fallback)

---

## Quick Start

### Basic Extraction

```python
from pybase.extraction.cad import DXFParser, IFCParser, STEPParser, CosCADExtractor
from pybase.extraction.pdf.extractor import PDFExtractor

# PDF extraction
pdf_extractor = PDFExtractor()
pdf_result = pdf_extractor.extract_tables("drawing.pdf")
for table in pdf_result.tables:
    print(f"Table: {table.rows} x {table.columns}")

# DXF extraction
dxf_parser = DXFParser()
dxf_result = dxf_parser.parse("drawing.dxf")
print(f"Layers: {len(dxf_result.layers)}")
print(f"Dimensions: {len(dxf_result.dimensions)}")

# CosCAD extraction
coscad_extractor = CosCADExtractor()
coscad_result = coscad_extractor.parse("model.coscad")
print(f"Solids: {coscad_result.geometry_summary.solids}")
print(f"Dimensions: {len(coscad_result.dimensions)}")
```

### API Endpoint

```bash
# Extract from PDF
curl -X POST "http://localhost:8000/api/v1/extraction/pdf" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@drawing.pdf" \
  -F "extract_tables=true" \
  -F "extract_dimensions=true"

# Extract from CAD file
curl -X POST "http://localhost:8000/api/v1/extraction/cad" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@drawing.dxf" \
  -F "extract_geometry=true" \
  -F "extract_dimensions=true"
```

---

## PDF Extraction

### Capabilities

PDF extraction supports technical drawings, tables, and text documents:

- **Tables**: Extract table structure with row/column data, merged cells, headers
- **Text blocks**: Extract text with positions, fonts, sizes, rotation
- **Dimensions**: Recognize dimension text and values (with Werk24 AI)
- **Title blocks**: Extract drawing metadata (number, revision, date, author)
- **GD&T symbols**: Extract geometric tolerancing (with Werk24 AI)
- **Materials**: Identify material callouts and specifications (with Werk24 AI)

### Usage

```python
from pybase.extraction.pdf.extractor import PDFExtractor

extractor = PDFExtractor()

# Extract all tables
result = extractor.extract_tables("drawing.pdf")
for table in result.tables:
    print(f"Table on page {table.page}")
    for row in table.rows:
        print(row)

# Extract text with positions
result = extractor.extract_text("drawing.pdf")
for text_block in result.text_blocks:
    print(f"Text: {text_block.text}")
    print(f"Position: {text_block.bbox}")

# Extract with Werk24 AI (requires API key)
from pybase.extraction.werk24.client import Werk24Client
client = Werk24Client()
result = await client.extract_async("drawing.pdf")

for dim in result.dimensions:
    print(f"Dimension: {dim.nominal_value} ±{dim.upper_deviation}/{dim.lower_deviation}")

for gdt in result.gdts:
    print(f"GD&T: {gdt.characteristic_type} {gdt.tolerance_value}")
```

### Dependencies

```bash
# Core PDF extraction
pip install pdfplumber pymupdf

# Optional: Advanced table extraction
pip install tabula-py

# Optional: OCR for scanned PDFs
pip install pytesseract

# Optional: AI-powered extraction
pip install werk24
```

---

## CAD Extraction

### DXF/DWG Extraction

**AutoCAD drawing extraction** using ezdxf library:

```python
from pybase.extraction.cad import DXFParser

parser = DXFParser()
result = parser.parse("drawing.dxf")

# Access layers
for layer in result.layers:
    print(f"Layer: {layer.name}")
    print(f"Entities: {len(layer.entities)}")

# Access dimensions
for dim in result.dimensions:
    print(f"Dimension: {dim.value} {dim.unit}")
    print(f"Tolerance: ±{dim.tolerance_plus}/{dim.tolerance_minus}")

# Access title block
if result.title_block:
    print(f"Drawing: {result.title_block.drawing_number}")
    print(f"Revision: {result.title_block.revision}")
```

**Supported Features:**
- Layer parsing with entity counts
- Dimension extraction (linear, angular, radial, diameter)
- Text and attribute extraction
- Block definitions and inserts
- Title block metadata
- Units and tolerance handling

### IFC/BIM Extraction

**Building information modeling** extraction using IfcOpenShell:

```python
from pybase.extraction.cad import IFCParser

parser = IFCParser()
result = parser.parse("building.ifc")

# Access building elements
for element in result.elements:
    print(f"Element: {element.type}")
    print(f"Name: {element.name}")
    print(f"Properties: {element.properties}")

# Access quantities
for quantity in result.quantities:
    print(f"Quantity: {quantity.name} = {quantity.value} {quantity.unit}")
```

**Supported Features:**
- IfcBuildingElement parsing (walls, slabs, doors, windows)
- Property sets and quantities
- Material information
- Classification systems
- Spatial structure (building, floors, spaces)

### STEP/STP Extraction

**3D CAD model** extraction using CadQuery:

```python
from pybase.extraction.cad import STEPParser

parser = STEPParser()
result = parser.parse("assembly.step")

# Access geometry summary
print(f"Solids: {result.geometry_summary.solids}")
print(f"Total entities: {result.geometry_summary.total_entities}")

# Access metadata
if result.metadata:
    print(f"Author: {result.metadata.get('author')}")
    print(f"Application: {result.metadata.get('application')}")
```

**Supported Features:**
- Solid topology extraction
- Geometry metadata (faces, edges, vertices)
- Assembly structure
- Manufacturing properties
- File metadata (author, application, date)

---

## CosCAD Extraction

> **Aerospace and automotive CAD format support via gRPC**

CosCAD is a proprietary CAD format widely used in aerospace and automotive industries. PyBase integrates with CosCAD extraction service via gRPC to provide specialized data extraction.

### Capabilities

- **Geometry metadata**: Faces, edges, vertices, surfaces, solids, bounding boxes
- **Dimensions**: Linear, angular, radial, diameter with tolerances and units
- **GD&T symbols**: Geometric dimensioning and tolerancing callouts
- **Annotations**: Text labels, notes, leaders, callouts, surface finish symbols
- **Title blocks**: Drawing numbers, revisions, authors, approval dates
- **Material specifications**: Material designations and properties
- **File metadata**: Author, organization, creation dates, custom properties

### Quick Start

```python
from pybase.extraction.cad import CosCADExtractor

# Initialize extractor (uses env vars by default)
extractor = CosCADExtractor()

# Parse a CosCAD file
result = extractor.parse("model.coscad")

# Access results
print(f"Success: {result.success}")
print(f"Solids: {result.geometry_summary.solids}")
print(f"Dimensions: {len(result.dimensions)}")

for dim in result.dimensions:
    print(f"{dim.dimension_type}: {dim.value} ±{dim.tolerance_plus}/{dim.tolerance_minus} {dim.unit}")
```

### Setup

1. **Install dependencies:**
   ```bash
   pip install grpcio>=1.60.0
   ```

2. **Configure environment variables:**
   ```env
   COSCAD_SERVICE_HOST=localhost
   COSCAD_SERVICE_PORT=50051
   ```

3. **Start extracting:**
   ```python
   from pybase.extraction.cad import CosCADExtractor

   extractor = CosCADExtractor()
   result = extractor.parse("model.coscad")
   ```

### Documentation

For comprehensive documentation on CosCAD extraction, including:
- Configuration and setup
- Selective extraction (geometry only, dimensions only, etc.)
- Data mapping and unit conversion
- Error handling and troubleshooting
- Best practices and optimization

**See:** [CosCAD Extraction Setup Guide](./coscad_extraction_setup.md)

---

## Werk24 AI Integration

> **AI-powered engineering drawing analysis**

[Werk24](https://werk24.io) provides AI-powered extraction of engineering information from technical drawings. This is a **unique capability** that sets PyBase apart from traditional database tools.

### Capabilities

- **Dimensions** with tolerances (e.g., 10.5 ±0.1 mm)
- **GD&T** (Geometric Dimensioning and Tolerancing) symbols
- **Thread specifications** (e.g., M8x1.25)
- **Material callouts** (e.g., AISI 304)
- **Surface finish requirements** (e.g., Ra 1.6)
- **Title block information** (drawing number, revision, author)
- **Overall dimensions** (length, width, height)

### Quick Start

```python
from pybase.extraction.werk24.client import Werk24Client

client = Werk24Client()
result = await client.extract_async("drawing.pdf")

for dim in result.dimensions:
    print(f"Dimension: {dim.nominal_value} ±{dim.upper_deviation}/{dim.lower_deviation}")

for gdt in result.gdts:
    print(f"GD&T: {gdt.characteristic_type} {gdt.tolerance_value} {gdt.material_condition}")
```

### Setup

1. **Get API key:** Sign up at [werk24.io](https://werk24.io)
2. **Install SDK:** `pip install werk24`
3. **Configure:** Add `WERK24_API_KEY` to `.env`

### Documentation

**See:** [Werk24 AI Integration Guide](./werk24-integration.md)

---

## Data Mapping

Extracted data is automatically mapped to PyBase engineering field types:

### Field Type Mappings

| Extracted Data | Field Type | Handler |
|---------------|------------|---------|
| Dimensions with tolerances | Dimension | `DimensionFieldHandler` |
| GD&T symbols | GD&T | `GDTFieldHandler` |
| Thread specifications | Thread | `ThreadFieldHandler` |
| Material callouts | Material | `MaterialFieldHandler` |
| Surface finish | Surface Finish | `SurfaceFinishFieldHandler` |
| Text blocks | Text | `TextFieldHandler` |
| Title blocks | Title Block | Custom fields |
| Table data | Lookup/Select | Auto-detected |

### Mapping Service

```python
from pybase.services.extraction_mapper import ExtractionMapperService

mapper = ExtractionMapperService()

# Map Werk24 results
mapped_data = mapper.map_werk24_result(werk24_result.to_dict())

# Map individual items
dimension_field = mapper.map_dimension(werk24_dimension)
gdt_field = mapper.map_gdt(werk24_gdt)
thread_field = mapper.map_thread(werk24_thread)

# Validate mapped data
is_valid, error = mapper.validate_mapped_data(dimension_field, "dimension")
```

---

## API Reference

### Extraction Endpoints

#### Extract from PDF

```http
POST /api/v1/extraction/pdf
Content-Type: multipart/form-data

{
  "file": <binary>,
  "extract_tables": true,
  "extract_text": true,
  "extract_dimensions": true,
  "use_werk24": false
}
```

#### Extract from CAD

```http
POST /api/v1/extraction/cad
Content-Type: multipart/form-data

{
  "file": <binary>,
  "extract_geometry": true,
  "extract_dimensions": true,
  "extract_annotations": true,
  "extract_metadata": true
}
```

#### Extract with Werk24 AI

```http
POST /api/v1/extraction/werk24
Content-Type: multipart/form-data

{
  "file": <binary>,
  "extract_dimensions": true,
  "extract_gdts": true,
  "extract_title_block": true,
  "extract_materials": true,
  "extract_threads": true,
  "extract_surface_finish": true
}
```

#### Get Extraction Status

```http
GET /api/v1/extraction/{job_id}

Response:
{
  "job_id": "uuid",
  "status": "completed",
  "progress": 100,
  "result": {
    "success": true,
    "source_file": "drawing.pdf",
    "tables": [...],
    "dimensions": [...],
    "metadata": {...}
  }
}
```

---

## Best Practices

### 1. Choose the Right Extractor

| Use Case | Recommended Extractor |
|----------|---------------------|
| Technical drawings with dimensions | Werk24 AI or DXFParser |
| Data tables in PDFs | PDFExtractor with pdfplumber |
| Complex table layouts | PDFExtractor with tabula |
| 3D CAD models | STEPParser |
| BIM/Revit data | IFCParser |
| Aerospace/automotive CAD | CosCADExtractor |
| Scanned drawings | OCR or Werk24 AI |

### 2. Selective Extraction

Only extract the data you need to improve performance:

```python
# ❌ Avoid: Extract everything
extractor = CosCADExtractor()

# ✅ Better: Extract only what you need
extractor = CosCADExtractor(
    extract_geometry=False,
    extract_dimensions=True,
    extract_annotations=False,
    extract_metadata=True
)
```

### 3. Validate Extracted Data

Always validate extracted data before using it:

```python
for dim in result.dimensions:
    if dim.value <= 0:
        print(f"Warning: Invalid dimension value: {dim.value}")
    if dim.tolerance_plus < 0 or dim.tolerance_minus < 0:
        print(f"Warning: Negative tolerance for {dim.label}")
```

### 4. Handle Errors Gracefully

```python
try:
    result = await client.extract_async("model.coscad")
except CosCADExtractionError as e:
    logger.error(f"Extraction failed: {e}")
    # Fallback to manual entry or alternative extraction
else:
    # Process result
    pass
```

### 5. Cache Results

Avoid re-processing the same file:

```python
import hashlib

file_hash = hashlib.sha256(file_content).hexdigest()
cached_result = cache.get(file_hash)

if cached_result:
    return cached_result
else:
    result = extractor.parse(file_path)
    cache.set(file_hash, result, timeout=3600)
    return result
```

---

## Performance

### File Size Guidelines

| File Type | Recommended Size | Maximum Size | Notes |
|-----------|------------------|--------------|-------|
| PDF | < 5 MB | 10 MB | Larger files may timeout |
| DXF | < 10 MB | 50 MB | Complex drawings take longer |
| IFC | < 20 MB | 100 MB | BIM models can be large |
| STEP | < 15 MB | 50 MB | 3D geometry processing |
| CosCAD | < 50 MB | 200 MB | Use selective extraction |

### Processing Time Estimates

| Format | Small File (<1 MB) | Medium File (1-10 MB) | Large File (>10 MB) |
|--------|--------------------|-----------------------|---------------------|
| PDF (tables) | 1-3 seconds | 3-10 seconds | 10-30 seconds |
| DXF | 1-2 seconds | 2-5 seconds | 5-15 seconds |
| IFC | 2-5 seconds | 5-15 seconds | 15-60 seconds |
| STEP | 3-8 seconds | 8-20 seconds | 20-60 seconds |
| CosCAD (metadata) | 1-2 seconds | 2-5 seconds | 5-10 seconds |
| CosCAD (all) | 10-20 seconds | 30-60 seconds | 60-120 seconds |
| Werk24 AI | 2-5 seconds | 5-15 seconds | 15-30 seconds |

---

## Troubleshooting

### Common Issues

#### Issue: PDF extraction returns empty tables

**Possible causes:**
- PDF is image-based (scanned) without text layer
- Tables are complex with merged cells
- PDF is corrupted or password-protected

**Solutions:**
1. Check if PDF is text-based or image-based
2. For image-based PDFs, use OCR or Werk24 AI
3. Try alternative extraction method (tabula instead of pdfplumber)

#### Issue: CosCAD service unavailable

**Error:** `CosCADServiceUnavailableError`

**Solutions:**
1. Check if CosCAD gRPC service is running
2. Verify `COSCAD_SERVICE_HOST` and `COSCAD_SERVICE_PORT` environment variables
3. Test network connectivity: `telnet localhost 50051`

See [CosCAD Setup Guide](./coscad_extraction_setup.md#troubleshooting) for detailed troubleshooting.

#### Issue: Werk24 API quota exceeded

**Solutions:**
1. Check quota remaining in usage statistics
2. Upgrade Werk24 API plan
3. Implement caching to avoid duplicate calls
4. Use selective extraction to reduce API calls

See [Werk24 Integration Guide](./werk24-integration.md#troubleshooting) for more details.

---

## Related Documentation

- [Field Types Reference](./fields.md) - Engineering field types and validation
- [API Reference](./api.md) - Complete API endpoint documentation
- [Werk24 AI Integration](./werk24-integration.md) - AI-powered drawing extraction
- [CosCAD Extraction Setup](./coscad_extraction_setup.md) - Aerospace/automotive CAD extraction
- [System Architecture](./system-architecture.md) - Extraction system architecture
- [Development Guide](./code-standards.md) - Code patterns for extractors

---

## External Resources

### Libraries and Tools

- [pdfplumber](https://github.com/jsvine/pdfplumber) - PDF table extraction
- [ezdxf](https://ezdxf.readthedocs.io/) - DXF file parsing
- [IfcOpenShell](https://ifcopenshell.org/) - IFC/BIM processing
- [CadQuery](https://cadquery.readthedocs.io/) - STEP file processing
- [Werk24](https://werk24.io) - AI engineering drawing extraction

### Standards

- [ASME Y14.5](https://www.asme.org/codes-standards/find-codes-standards/y14-5-dimensioning-tolerancing) - GD&T standard
- [ISO 1101](https://www.iso.org/standard/66777.html) - Geometric tolerancing

---

## Support

For extraction issues:
1. Check the relevant troubleshooting section above
2. Review format-specific documentation (CosCAD, Werk24)
3. Check [PyBase TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
4. File issues at [GitHub Issues](https://github.com/pybase/pybase/issues)

---

**Last Updated:** 2026-01-27
**Extraction System Version:** 1.0.0
