# Werk24 AI Integration Guide

> AI-powered engineering drawing extraction using Werk24 API

## Overview

PyBase integrates with [Werk24](https://werk24.io) to provide AI-powered extraction of engineering information from technical drawings. This is a **unique capability** that sets PyBase apart from traditional database tools - no other database platform offers automated AI analysis of engineering drawings.

### What is Werk24?

Werk24 is an AI service that analyzes engineering drawings (PDF, PNG, JPG) and automatically extracts:
- **Dimensions** with tolerances (e.g., 10.5 ±0.1 mm)
- **GD&T** (Geometric Dimensioning and Tolerancing) symbols
- **Thread specifications** (e.g., M8x1.25)
- **Material callouts** (e.g., AISI 304)
- **Surface finish requirements** (e.g., Ra 1.6)
- **Title block information** (drawing number, revision, author)
- **Overall dimensions** (length, width, height)

### Key Benefits

- **Automation**: Eliminate manual data entry from engineering drawings
- **Accuracy**: AI extraction is more reliable than rule-based parsing
- **Speed**: Process drawings in seconds instead of minutes
- **Integration**: Extracted data maps directly to PyBase engineering field types
- **Tracking**: Built-in usage monitoring and quota management

---

## Quick Start

### Prerequisites

1. **Werk24 API Key**: Sign up at [werk24.io](https://werk24.io) to get an API key
2. **Werk24 Python SDK**: Install with `pip install werk24`
3. **PyBase**: Running PyBase instance with database migrations applied

### Installation

```bash
# Install the Werk24 SDK
pip install werk24

# Or install PyBase with all dependencies
pip install -e ".[all]"
```

### Configuration

Add your Werk24 API key to the `.env` file:

```env
# Werk24 API Configuration
WERK24_API_KEY=your-api-key-here
```

The API key is automatically loaded from the environment variable. You can also pass it programmatically when creating a client.

---

## Usage

### Basic Extraction

#### Using the API Endpoint

```bash
# Extract all information from a drawing
curl -X POST "http://localhost:8000/api/v1/extraction/werk24" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@drawing.pdf" \
  -F "extract_dimensions=true" \
  -F "extract_gdts=true" \
  -F "extract_title_block=true" \
  -F "extract_materials=true"

# Response
{
  "success": true,
  "source_file": "drawing.pdf",
  "dimensions": [
    {
      "value": 10.5,
      "tolerance_plus": 0.2,
      "tolerance_minus": 0.1,
      "unit": "mm"
    }
  ],
  "gdts": [
    {
      "type": "position",
      "tolerance": 0.05,
      "diameter_zone": true,
      "material_condition": "MMC",
      "datums": ["A", "B", "C"]
    }
  ],
  "title_block": {
    "drawing_number": "DWG-001",
    "revision": "A",
    "title": "Main Assembly"
  },
  "materials": [
    {
      "designation": "AISI 304",
      "standard": "ASTM",
      "family": "stainless_steel"
    }
  ]
}
```

#### Using Python Client

```python
from pybase.extraction.werk24.client import Werk24Client

# Initialize client
client = Werk24Client(api_key="your-api-key")

# Extract from file
result = await client.extract_async("drawing.pdf")

# Access extracted data
for dim in result.dimensions:
    print(f"Dimension: {dim.nominal_value} ±{dim.upper_deviation}/{dim.lower_deviation} {dim.unit}")

for gdt in result.gdts:
    print(f"GD&T: {gdt.characteristic_type} {gdt.tolerance_value} {gdt.tolerance_unit}")
```

### Selective Extraction

Control which information to extract using `ask_types`:

```python
from pybase.extraction.werk24.client import Werk24Client, Werk24AskType

client = Werk24Client()

# Extract only dimensions and GD&T
result = await client.extract_async(
    "drawing.pdf",
    ask_types=[
        Werk24AskType.DIMENSIONS,
        Werk24AskType.GDTS,
    ]
)
```

#### Available Ask Types

| Ask Type | Description | Extracts |
|----------|-------------|----------|
| `DIMENSIONS` | Linear, angular, radius, diameter dimensions | Values with tolerances |
| `GDTS` | Geometric tolerancing symbols | Position, flatness, etc. |
| `TITLE_BLOCK` | Title block information | Drawing number, revision, date |
| `MATERIAL` | Material specifications | Designation, standard, type |
| `THREADS` | Thread callouts | Standard, size, pitch, class |
| `SURFACE_FINISH` | Surface roughness | Ra, Rz values with lay |
| `OVERALL_DIMENSIONS` | Part bounding box | Length, width, height |
| `THUMBNAIL` | Drawing preview image | PNG thumbnail |
| `PMI` | Product Manufacturing Information | Comprehensive manufacturing data |

---

## Data Mapping

PyBase automatically maps Werk24 extraction results to engineering field types using the `ExtractionMapperService`.

### Dimension Mapping

**Werk24 Format:**
```python
{
    "nominal_value": 10.5,
    "unit": "mm",
    "upper_deviation": 0.2,
    "lower_deviation": -0.1,
    "tolerance_grade": "h7"
}
```

**PyBase Dimension Field:**
```python
{
    "value": 10.5,
    "tolerance_plus": 0.2,
    "tolerance_minus": 0.1,  # Converted to positive
    "unit": "mm"
}
```

### GD&T Mapping

**Werk24 Format:**
```python
{
    "characteristic_type": "position",
    "tolerance_value": 0.05,
    "material_condition": "MMC",
    "datums": ["A", "B", "C"]
}
```

**PyBase GDT Field:**
```python
{
    "type": "position",
    "tolerance": 0.05,
    "diameter_zone": true,
    "material_condition": "MMC",
    "datums": ["A", "B", "C"]
}
```

**Supported GD&T Types:**
- Form: `straightness`, `flatness`, `circularity`, `cylindricity`
- Orientation: `perpendicularity`, `parallelism`, `angularity`
- Location: `position`, `concentricity`, `symmetry`
- Runout: `circular_runout`, `total_runout`
- Profile: `profile_line`, `profile_surface`

### Thread Mapping

**Werk24 Format:**
```python
{
    "standard": "ISO",
    "designation": "M8x1.25",
    "nominal_diameter": 8,
    "pitch": 1.25,
    "thread_class": "6g",
    "hand": "right",
    "thread_type": "external"
}
```

**PyBase Thread Field:**
```python
{
    "standard": "metric",  # ISO → metric
    "size": 8,
    "pitch": 1.25,
    "class": "6g",
    "internal": false,  # external → false
    "left_hand": false   # right → false
}
```

**Standard Name Mappings:**
- `ISO`, `DIN` → `metric`
- `UN`, `Unified` → `unc`
- `BSP` → `bsp`
- `NPT` → `npt`

### Material Mapping

**Werk24 Format:**
```python
{
    "designation": "AISI 304",
    "standard": "ASTM",
    "material_type": "stainless_steel"
}
```

**PyBase Material Field:**
```python
{
    "designation": "AISI 304",
    "standard": "ASTM",
    "family": "stainless_steel",
    "condition": null,
    "properties": {}
}
```

### Surface Finish Mapping

**Werk24 Format:**
```python
{
    "ra_value": 1.6,
    "unit": "μm",
    "lay_symbol": "⟂",
    "process": "ground"
}
```

**PyBase Surface Finish Field:**
```python
{
    "parameter": "Ra",
    "value": 1.6,
    "unit": "μm",
    "lay": "perpendicular",  # ⟂ → perpendicular
    "process": "ground"
}
```

**Lay Symbol Mappings:**
- `⟂` → `perpendicular`
- `=` → `parallel`
- `X` → `crossed`
- `M` → `multidirectional`
- `C` → `circular`
- `R` → `radial`

### Using the Mapper Service

```python
from pybase.services.extraction_mapper import ExtractionMapperService

mapper = ExtractionMapperService()

# Map individual items
dimension_field = mapper.map_dimension(werk24_dimension)
gdt_field = mapper.map_gdt(werk24_gdt)
thread_field = mapper.map_thread(werk24_thread)
material_field = mapper.map_material(werk24_material)
surface_finish_field = mapper.map_surface_finish(werk24_surface_finish)

# Map complete extraction result
result = client.extract_async("drawing.pdf")
mapped_data = mapper.map_werk24_result(result.to_dict())

# Access mapped data
for dim in mapped_data["dimensions"]:
    # Create dimension field with dim data
    pass

# Validate mapped data
is_valid, error = mapper.validate_mapped_data(dimension_field, "dimension")
if not is_valid:
    print(f"Validation error: {error}")
```

---

## Usage Tracking

PyBase automatically tracks all Werk24 API calls for quota management and monitoring.

### What's Tracked

Each API call records:
- **User and workspace** information
- **Request details**: type, ask types, file info
- **Results**: success/failure, extraction counts
- **Performance**: processing time, status code
- **Resource usage**: tokens, cost units, quota remaining
- **Metadata**: IP address, user agent

### Database Model

```python
# Usage record is automatically created
{
    "id": "uuid",
    "user_id": "user-uuid",
    "workspace_id": "workspace-uuid",
    "request_type": "extract_async",
    "ask_types": ["dimensions", "gdts"],
    "source_file": "drawing.pdf",
    "file_type": "pdf",
    "file_size_bytes": 1048576,
    "success": true,
    "processing_time_ms": 2500,
    "dimensions_extracted": 15,
    "gdts_extracted": 8,
    "materials_extracted": 2,
    "threads_extracted": 4,
    "created_at": "2026-01-22T10:30:00Z",
    "completed_at": "2026-01-22T10:30:02Z"
}
```

### Accessing Usage Data

```python
from pybase.services.werk24 import Werk24Service

service = Werk24Service()

# Get usage statistics
stats = await service.get_usage_statistics(
    db=db,
    user_id=current_user.id,
    days=30
)

print(f"Total requests: {stats['total_requests']}")
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"Total dimensions extracted: {stats['total_extractions']['dimensions']}")
print(f"Quota remaining: {stats['quota']['remaining']}")

# List usage records
records, total = await service.list_usage(
    db=db,
    user_id=current_user.id,
    workspace_id=workspace_id,
    success_only=True,
    page=1,
    page_size=20
)

# Get workspace usage (admin only)
workspace_stats = await service.get_workspace_usage_statistics(
    db=db,
    workspace_id=workspace_id,
    user_id=current_user.id,
    days=30
)
```

### Statistics Response

```json
{
  "period_days": 30,
  "start_date": "2025-12-23T00:00:00Z",
  "end_date": "2026-01-22T14:00:00Z",
  "total_requests": 156,
  "successful_requests": 148,
  "failed_requests": 8,
  "success_rate": 0.949,
  "total_extractions": {
    "dimensions": 2340,
    "gdts": 1245,
    "materials": 312,
    "threads": 678,
    "total": 4575
  },
  "cost": {
    "total_units": 234.5,
    "average_per_request": 1.503
  },
  "performance": {
    "average_processing_time_ms": 2450
  },
  "quota": {
    "remaining": 7650
  },
  "request_types": {
    "extract_async": 156
  }
}
```

---

## Error Handling

### Graceful Degradation

PyBase handles Werk24 errors gracefully and never blocks other operations:

```python
result = await client.extract_async("drawing.pdf")

if result.errors:
    # Extraction failed, but system continues
    print(f"Errors: {result.errors}")
    # Fallback: use manual entry or alternative extraction
else:
    # Success, use extracted data
    for dim in result.dimensions:
        # Process dimensions
        pass
```

### Common Errors

#### No API Key

```python
# Error: "Werk24 API key not configured"
# Solution: Set WERK24_API_KEY environment variable
```

#### SDK Not Installed

```python
# Error: "werk24 SDK not installed. Install with: pip install werk24"
# Solution: pip install werk24
```

#### API Quota Exceeded

```python
# Error: "API quota exceeded"
# Solution: Upgrade Werk24 plan or wait for quota reset
# The system tracks quota_remaining in usage records
```

#### Invalid File Format

```python
# Error: "Unsupported file format"
# Solution: Convert to PDF, PNG, or JPG
# Supported formats: PDF, PNG, JPG, TIFF
```

#### Network Timeout

```python
# Configure timeout
client = Werk24Client(timeout=600.0)  # 10 minutes
```

### Error Logging

All errors are logged with details:

```python
import logging

logger = logging.getLogger("pybase.extraction.werk24")
logger.setLevel(logging.DEBUG)

# Errors are logged but don't crash the system
# Check logs for debugging
```

---

## Best Practices

### 1. Use Selective Extraction

Only request the data you need to minimize API costs and processing time:

```python
# ❌ Avoid: Extract everything
result = await client.extract_async("drawing.pdf")

# ✅ Better: Extract only what you need
result = await client.extract_async(
    "drawing.pdf",
    ask_types=[
        Werk24AskType.DIMENSIONS,
        Werk24AskType.TITLE_BLOCK,
    ]
)
```

### 2. Handle Confidence Scores

Werk24 provides confidence scores for extractions. Use them to filter low-confidence results:

```python
# Filter by confidence threshold
MIN_CONFIDENCE = 0.8

reliable_dimensions = [
    dim for dim in result.dimensions
    if dim.confidence >= MIN_CONFIDENCE
]
```

### 3. Validate Extracted Data

Always validate extracted data before saving to database:

```python
from pybase.services.extraction_mapper import ExtractionMapperService

mapper = ExtractionMapperService()

for dim_data in extracted_dimensions:
    mapped = mapper.map_dimension(dim_data)
    is_valid, error = mapper.validate_mapped_data(mapped, "dimension")

    if is_valid:
        # Save to database
        pass
    else:
        # Log validation error and skip
        logger.warning(f"Invalid dimension: {error}")
```

### 4. Monitor Quota Usage

Regularly check quota statistics to avoid service disruption:

```python
stats = await service.get_usage_statistics(db, user_id, days=7)

if stats['quota']['remaining'] < 100:
    # Send alert to admin
    notify_admin("Low Werk24 quota remaining")
```

### 5. Cache Results

Avoid re-processing the same drawing:

```python
# Check if drawing was already processed
existing_record = await db.get_record_by_file_hash(file_hash)

if existing_record:
    # Use cached results
    return existing_record.extraction_data
else:
    # Process with Werk24
    result = await client.extract_async(file)
    # Cache results
    await db.save_extraction_result(file_hash, result)
```

### 6. Batch Processing

For multiple drawings, process them asynchronously:

```python
import asyncio

async def process_drawings(file_paths):
    client = Werk24Client()
    tasks = [client.extract_async(path) for path in file_paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Extraction failed: {result}")
        else:
            # Process result
            pass
```

---

## API Reference

### Werk24Client

```python
class Werk24Client:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 300.0,
    ):
        """Initialize the Werk24 client.

        Args:
            api_key: Werk24 API key (reads from WERK24_API_KEY env var if None)
            base_url: Base URL for the API (defaults to production)
            timeout: Request timeout in seconds (default: 300)
        """

    async def extract_async(
        self,
        source: str | Path | BinaryIO,
        ask_types: list[Werk24AskType] | None = None,
        db: AsyncSession | None = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
        file_size: int | None = None,
        file_type: str | None = None,
        request_ip: str | None = None,
        user_agent: str | None = None,
    ) -> Werk24ExtractionResult:
        """Extract information from an engineering drawing.

        Args:
            source: File path or file-like object
            ask_types: Types of information to extract (default: all)
            db: Database session for usage tracking
            user_id: User ID for usage tracking
            workspace_id: Workspace ID for usage tracking
            file_size: File size in bytes for tracking
            file_type: File type for tracking
            request_ip: Request IP for tracking
            user_agent: User agent for tracking

        Returns:
            Werk24ExtractionResult with extracted data
        """
```

### ExtractionMapperService

```python
class ExtractionMapperService:
    def map_dimension(self, dimension_data: dict) -> dict | None:
        """Map Werk24Dimension to DimensionFieldHandler format."""

    def map_gdt(self, gdt_data: dict) -> dict | None:
        """Map Werk24GDT to GDTFieldHandler format."""

    def map_thread(self, thread_data: dict) -> dict | None:
        """Map Werk24Thread to ThreadFieldHandler format."""

    def map_material(self, material_data: dict) -> dict | None:
        """Map Werk24Material to MaterialFieldHandler format."""

    def map_surface_finish(self, surface_finish_data: dict) -> dict | None:
        """Map Werk24SurfaceFinish to SurfaceFinishFieldHandler format."""

    def map_werk24_result(self, extraction_result: dict) -> dict:
        """Map complete Werk24ExtractionResult to all field formats."""

    def validate_mapped_data(
        self,
        mapped_data: dict,
        field_type: str
    ) -> tuple[bool, str | None]:
        """Validate mapped data against field type handler."""
```

### Werk24Service

```python
class Werk24Service:
    async def create_usage_record(
        self,
        db: AsyncSession,
        user_id: str,
        request_type: str,
        ask_types: list[str],
        **kwargs
    ) -> Werk24Usage:
        """Create a new usage tracking record."""

    async def update_usage_record(
        self,
        db: AsyncSession,
        usage_id: str,
        user_id: str,
        success: bool,
        **kwargs
    ) -> Werk24Usage:
        """Update usage record with results."""

    async def get_usage_statistics(
        self,
        db: AsyncSession,
        user_id: str,
        workspace_id: str | None = None,
        days: int = 30,
    ) -> dict:
        """Get usage statistics for quota management."""

    async def get_workspace_usage_statistics(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        days: int = 30,
    ) -> dict:
        """Get workspace-wide usage statistics."""
```

---

## Troubleshooting

### Issue: Extraction Returns Empty Results

**Possible Causes:**
- Drawing quality is poor (low resolution, blurry)
- Drawing is hand-drawn or not CAD-generated
- File format is unsupported

**Solutions:**
1. Ensure drawing is high-resolution (300 DPI minimum)
2. Use vector PDF instead of raster image when possible
3. Check Werk24 API logs for specific errors
4. Verify file is a proper engineering drawing with title block

### Issue: GD&T Symbols Not Recognized

**Possible Causes:**
- Symbols are in non-standard format
- Drawing uses custom GD&T notation
- Symbol quality is degraded

**Solutions:**
1. Use standard ASME Y14.5 or ISO 1101 symbols
2. Ensure symbols are clearly visible in the drawing
3. Check symbol confidence scores - filter low confidence items
4. Consider manual entry for non-standard symbols

### Issue: API Quota Errors

**Possible Causes:**
- Monthly quota exceeded
- Rate limiting triggered
- API key is invalid or expired

**Solutions:**
1. Check quota remaining in usage statistics
2. Upgrade Werk24 API plan
3. Implement request caching to avoid duplicate calls
4. Contact Werk24 support for quota increase

### Issue: Slow Processing Times

**Possible Causes:**
- Large file size (>10 MB)
- Requesting too many ask types
- Network latency

**Solutions:**
1. Compress PDF files before uploading
2. Request only needed ask types
3. Increase timeout setting
4. Process files asynchronously in batches

### Issue: Incorrect Dimension Units

**Possible Causes:**
- Drawing doesn't specify units clearly
- Mixed units in single drawing
- Unit conversion errors

**Solutions:**
1. Ensure title block specifies units (mm, inches)
2. Validate extracted units against expected values
3. Manually override incorrect units in mapper
4. Add unit validation in field handlers

---

## Performance Optimization

### File Size Recommendations

| File Type | Recommended Size | Maximum Size |
|-----------|------------------|--------------|
| PDF | < 5 MB | 10 MB |
| PNG | < 2 MB | 5 MB |
| JPG | < 2 MB | 5 MB |

### Processing Time Estimates

| Ask Types | Small File (<1 MB) | Large File (5-10 MB) |
|-----------|--------------------|----------------------|
| 1-2 types | 2-5 seconds | 5-10 seconds |
| 3-5 types | 5-10 seconds | 10-20 seconds |
| All types | 10-15 seconds | 20-30 seconds |

### Cost Optimization

1. **Use confidence thresholds** to filter low-quality extractions
2. **Cache results** to avoid re-processing identical drawings
3. **Request selective ask types** instead of extracting everything
4. **Batch process** during off-peak hours if possible
5. **Monitor quota** to avoid overage charges

---

## Security Considerations

### API Key Management

- **Never commit** API keys to version control
- **Use environment variables** for configuration
- **Rotate keys** periodically (every 90 days)
- **Restrict key permissions** to minimum required

### Data Privacy

- Usage tracking includes file metadata but **not file contents**
- Files are **not stored** by PyBase after extraction
- Werk24 API processes files according to their privacy policy
- Consider on-premise Werk24 deployment for sensitive drawings

### Access Control

- Usage tracking respects workspace permissions
- Only workspace members can access extraction statistics
- Admin users can view workspace-wide usage
- API endpoints require authentication

---

## Related Documentation

- [Field Types Reference](./fields.md) - Details on engineering field types
- [API Reference](./api.md) - Complete API endpoint documentation
- [Extraction Guide](./extraction.md) - General CAD/PDF extraction documentation
- [System Architecture](./system-architecture.md) - PyBase architecture overview

---

## External Resources

- [Werk24 Official Documentation](https://werk24.io/docs)
- [Werk24 Python SDK](https://github.com/werk24/werk24-python)
- [ASME Y14.5 GD&T Standard](https://www.asme.org/codes-standards/find-codes-standards/y14-5-dimensioning-tolerancing)
- [ISO 1101 Geometric Tolerancing](https://www.iso.org/standard/66777.html)

---

## Support

For Werk24 integration issues:
1. Check this guide's [Troubleshooting](#troubleshooting) section
2. Review [PyBase TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
3. Contact Werk24 support at support@werk24.io
4. File PyBase issues at [GitHub Issues](https://github.com/pybase/pybase/issues)

---

**Last Updated:** 2026-01-22
**Integration Version:** 1.0.0
**Werk24 SDK Version:** Latest compatible
