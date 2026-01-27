# CosCAD Extraction Setup Guide

> gRPC-based CAD extraction for aerospace and automotive engineering files

## Overview

PyBase integrates with CosCAD extraction service via gRPC to provide specialized CAD data extraction for aerospace and automotive industries. CosCAD is a proprietary CAD format widely used in these industries for complex engineering designs.

### What is CosCAD?

CosCAD is a CAD format and extraction service used primarily in:
- **Aerospace industry**: Aircraft components, structural parts, assemblies
- **Automotive industry**: Engine components, chassis parts, transmission systems
- **Industrial machinery**: Complex mechanical systems and precision parts

The CosCAD gRPC service extracts:
- **Geometry metadata**: Faces, edges, vertices, surfaces, solids
- **Dimensions**: Linear, angular, radial, diameter with tolerances and units
- **GD&T symbols**: Geometric dimensioning and tolerancing callouts
- **Annotations**: Text labels, notes, leaders, callouts
- **Title blocks**: Drawing numbers, revisions, authors, approval dates
- **Material specifications**: Material designations and properties
- **File metadata**: Author, organization, creation dates, custom properties

### Key Benefits

- **Aerospace/Automotive Support**: Access to industry-specific CAD format
- **Comprehensive Extraction**: Geometry, dimensions, annotations, and metadata
- **Unit Conversion**: Automatic handling of CosCAD units (mm, inch, um, cm, m)
- **Tolerance Support**: Symmetric and asymmetric tolerances with proper parsing
- **Error Resilience**: Graceful handling of corrupted files and version mismatches
- **gRPC Performance**: Efficient binary protocol for fast data transfer

---

## Quick Start

### Prerequisites

1. **CosCAD gRPC Service**: Running CosCAD extraction service instance
2. **gRPC Dependencies**: Python gRPC libraries installed
3. **Network Access**: Ability to connect to CosCAD service host and port
4. **PyBase**: Running PyBase instance with database migrations applied

### Installation

```bash
# Install gRPC dependencies
pip install grpcio>=1.60.0

# Or install PyBase with all dependencies
pip install -e ".[all]"
```

### Configuration

Add CosCAD service configuration to the `.env` file:

```env
# CosCAD gRPC Service Configuration
COSCAD_SERVICE_HOST=localhost
COSCAD_SERVICE_PORT=50051
```

**Optional: Custom Timeout**

```env
# Timeout for CosCAD extraction requests (in seconds)
COSCAD_TIMEOUT=300
```

The service host and port are automatically loaded from environment variables. You can also override these programmatically when creating a client.

---

## Usage

### Basic Extraction

#### Using the CosCAD Extractor

```python
from pybase.extraction.cad import CosCADExtractor

# Initialize extractor (uses env vars by default)
extractor = CosCADExtractor()

# Parse a CosCAD file
result = extractor.parse("model.coscad")

# Access extraction results
print(f"Success: {result.success}")
print(f"Source: {result.source_file}")

# Access geometry summary
if result.geometry_summary:
    print(f"Solids: {result.geometry_summary.solids}")
    print(f"Total entities: {result.geometry_summary.total_entities}")

# Access dimensions
for dim in result.dimensions:
    print(f"{dim.dimension_type}: {dim.value} ±{dim.tolerance_plus}/{dim.tolerance_minus} {dim.unit}")

# Access annotations
for annotation in result.annotations:
    print(f"Text: {annotation.text}")
    print(f"Position: {annotation.bbox}")

# Access title block
if result.title_block:
    print(f"Drawing: {result.title_block.drawing_number}")
    print(f"Revision: {result.title_block.revision}")
```

#### Using the gRPC Client Directly

```python
from pybase.extraction.cad.coscad_client import CosCADClient

# Initialize client
client = CosCADClient(
    host="localhost",
    port=50051,
    timeout=300
)

# Extract all information
result = await client.extract_async("model.coscad")

# Access extracted data
for geom in result.geometry:
    print(f"Type: {geom.geometry_type}, Entities: {geom.entity_count}")

for dim in result.dimensions:
    print(f"Value: {dim.nominal_value} {dim.unit}")
    print(f"Tolerance: +{dim.upper_deviation}/-{dim.lower_deviation}")

# Check for errors
if result.errors:
    for error in result.errors:
        print(f"Error: {error}")
```

### Selective Extraction

Control which information to extract using extraction flags:

```python
from pybase.extraction.cad import CosCADExtractor

# Extract only dimensions and metadata
extractor = CosCADExtractor(
    service_host="localhost",
    service_port=50051,
    timeout=300,
    extract_geometry=False,      # Skip geometry extraction
    extract_dimensions=True,     # Extract dimensions
    extract_annotations=False,   # Skip annotations
    extract_metadata=True        # Extract metadata
)

result = extractor.parse("model.coscad")

# Result will have dimensions and metadata only
print(f"Dimensions: {len(result.dimensions)}")
print(f"Title block: {result.title_block}")
```

**Benefits of Selective Extraction:**
- Faster processing time
- Reduced network traffic
- Lower memory usage
- Focused results for specific use cases

---

## Data Mapping

PyBase automatically converts CosCAD extraction results to standard extraction types used throughout the codebase.

### Geometry Mapping

**CosCAD Format:**
```python
{
    "geometry_type": "solid",
    "entity_count": 150,
    "bounding_box": {
        "min": {"x": 0, "y": 0, "z": 0},
        "max": {"x": 100, "y": 50, "z": 25}
    },
    "properties": {
        "volume": 125000.0,
        "surface_area": 8500.0
    }
}
```

**PyBase Layer Organization:**
```python
ExtractedLayer(
    name="Solids",
    entities=[
        {"type": "solid", "count": 150}
    ],
    visible=True
)
```

### Dimension Mapping

**CosCAD Format:**
```python
{
    "nominal_value": 10.5,
    "unit": "mm",
    "upper_deviation": 0.1,
    "lower_deviation": -0.05,
    "dimension_type": "linear",
    "label": "LENGTH",
    "tolerance_type": "symmetric"
}
```

**PyBase Dimension Field:**
```python
ExtractedDimension(
    value=10.5,
    unit="mm",
    tolerance_plus=0.1,
    tolerance_minus=0.05,  # Converted to positive
    dimension_type="linear",
    label="LENGTH",
    bbox=[...]
)
```

**Supported Dimension Types:**
- `linear`: Linear dimensions (length, width, height)
- `angular`: Angular dimensions (degrees, radians)
- `radial`: Radius dimensions
- `diameter`: Diameter dimensions
- `ordinate`: Ordinate dimensions
- `chamfer`: Chamfer dimensions

### Unit Conversion

CosCAD supports multiple units that are automatically converted to standard units:

| CosCAD Unit | Converted Unit | Conversion Factor |
|-------------|----------------|-------------------|
| `mm` | `mm` | 1.0 |
| `inch` | `inch` | 1.0 |
| `um` (micrometer) | `mm` | 0.001 |
| `cm` | `mm` | 10.0 |
| `m` | `mm` | 1000.0 |
| `rad` (radian) | `degree` | 57.2958 |

```python
# CosCAD unit conversion example
# Input: 1000 um → Output: 1.0 mm
# Input: 2.54 inch → Output: 2.54 inch
# Input: 0.5 rad → Output: 28.65 degree
```

### Annotation Mapping

**CosCAD Format:**
```python
{
    "text": "NOTE: ALL DIMENSIONS IN MM",
    "annotation_type": "note",
    "position": {"x": 50, "y": 100, "z": 0},
    "font_size": 3.5,
    "bounding_box": {
        "min": {"x": 50, "y": 100, "z": 0},
        "max": {"x": 150, "y": 110, "z": 0}
    }
}
```

**PyBase Text Field:**
```python
ExtractedText(
    text="NOTE: ALL DIMENSIONS IN MM",
    bbox=[50, 100, 150, 110],
    font_size=3.5,
    rotation=0
)
```

**Supported Annotation Types:**
- `text_label`: Text labels and callouts
- `note`: General notes and comments
- `leader`: Leader lines with text
- `surface_finish`: Surface finish symbols
- `welding_symbol`: Welding symbols
- `callout`: Special callouts and markers

### Title Block Mapping

**CosCAD Format:**
```python
{
    "drawing_number": "DWG-2024-001",
    "title": "Main Assembly",
    "revision": "A",
    "date": "2024-01-15",
    "author": "John Doe",
    "organization": "Acme Aerospace",
    "scale": "1:10",
    "sheet": "1 of 5",
    "material": "ALUMINUM 6061-T6",
    "finish": "ANODIZE"
}
```

**PyBase Title Block:**
```python
ExtractedTitleBlock(
    drawing_number="DWG-2024-001",
    title="Main Assembly",
    revision="A",
    date="2024-01-15",
    author="John Doe",
    company="Acme Aerospace",
    scale="1:10",
    sheet="1 of 5",
    material="ALUMINUM 6061-T6",
    finish="ANODIZE"
)
```

---

## Error Handling

### Exception Hierarchy

PyBase provides a comprehensive exception hierarchy for CosCAD extraction errors:

```python
from pybase.extraction.cad.coscad_client import (
    CosCADExtractionError,            # Base exception
    CosCADServiceUnavailableError,    # Service not running
    CosCADConnectionError,            # Connection failed
    CosCADTimeoutError,               # Request timeout
    CosCADFileCorruptedError,         # File is corrupted
    CosCADUnsupportedVersionError,    # Unsupported file version
    CosCADParseError,                 # Parse error
    CosCADExtractionFailureError,     # Extraction failed
    CosCADInternalError               # Internal service error
)
```

### Error Handling Examples

#### Service Not Available

```python
from pybase.extraction.cad.coscad_client import (
    CosCADClient,
    CosCADServiceUnavailableError
)

client = CosCADClient()

try:
    result = await client.extract_async("model.coscad")
except CosCADServiceUnavailableError as e:
    print(f"CosCAD service is not available: {e}")
    # Fallback: Use alternative extraction or manual entry
except CosCADConnectionError as e:
    print(f"Failed to connect to CosCAD service: {e}")
    # Check network connection and service status
except CosCADTimeoutError as e:
    print(f"Extraction timed out: {e}")
    # Consider increasing timeout or processing smaller files
```

#### File Corruption

```python
from pybase.extraction.cad import CosCADExtractor
from pybase.extraction.cad.coscad_client import CosCADFileCorruptedError

extractor = CosCADExtractor()

try:
    result = extractor.parse("corrupted.coscad")
except CosCADFileCorruptedError as e:
    print(f"File is corrupted: {e}")
    # Attempt file recovery or notify user
except CosCADUnsupportedVersionError as e:
    print(f"Unsupported CosCAD version: {e}")
    # Suggest converting to supported version
except CosCADParseError as e:
    print(f"Parse error: {e}")
    # Log error and use partial results if available
```

#### Graceful Degradation

```python
from pybase.extraction.cad import CosCADExtractor

extractor = CosCADExtractor()
result = extractor.parse("model.coscad")

# Check result success
if not result.success:
    print(f"Extraction partially failed")
    for error in result.errors:
        print(f"Error: {error}")

    # Use available data
    if result.dimensions:
        print(f"Extracted {len(result.dimensions)} dimensions despite errors")
else:
    print(f"Extraction succeeded")
```

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `CosCADServiceUnavailableError` | Service not running | Start CosCAD gRPC service |
| `CosCADConnectionError` | Network/connection issue | Check host/port, firewall settings |
| `CosCADTimeoutError` | Processing too long | Increase timeout, check file size |
| `CosCADFileCorruptedError` | File is corrupted | Recover file or use backup |
| `CosCADUnsupportedVersionError` | File version not supported | Convert to supported version |
| `CosCADParseError` | Invalid file format | Verify file is valid CosCAD format |

---

## Best Practices

### 1. Use Selective Extraction

Only extract the data you need to improve performance:

```python
# ❌ Avoid: Extract everything
extractor = CosCADExtractor()  # All flags True by default

# ✅ Better: Extract only what you need
extractor = CosCADExtractor(
    extract_geometry=False,
    extract_dimensions=True,
    extract_annotations=False,
    extract_metadata=True
)
```

### 2. Set Appropriate Timeouts

Large CosCAD files may take longer to process:

```python
# For small files (<1 MB)
client = CosCADClient(timeout=60)

# For large files (>10 MB)
client = CosCADClient(timeout=600)
```

### 3. Validate Extracted Data

Always validate extracted data before using it:

```python
result = extractor.parse("model.coscad")

# Validate dimensions
for dim in result.dimensions:
    if dim.value <= 0:
        print(f"Warning: Invalid dimension value: {dim.value}")
    if dim.tolerance_plus < 0 or dim.tolerance_minus < 0:
        print(f"Warning: Negative tolerance for {dim.label}")

# Validate title block
if result.title_block:
    if not result.title_block.drawing_number:
        print(f"Warning: Missing drawing number")
```

### 4. Handle Errors Gracefully

Never let CosCAD extraction errors crash your application:

```python
try:
    result = await client.extract_async("model.coscad")
except CosCADExtractionError as e:
    logger.error(f"CosCAD extraction failed: {e}")
    # Fallback to manual entry or alternative extraction
    return None
else:
    # Process successful result
    return result
```

### 5. Cache Results

Avoid re-processing the same CosCAD file:

```python
import hashlib

def get_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file."""
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

# Check cache
file_hash = get_file_hash("model.coscad")
cached_result = cache.get(file_hash)

if cached_result:
    return cached_result
else:
    result = extractor.parse("model.coscad")
    cache.set(file_hash, result, timeout=3600)
    return result
```

### 6. Log Extraction Details

Track extraction operations for debugging and monitoring:

```python
import logging

logger = logging.getLogger(__name__)

result = extractor.parse("model.coscad")

logger.info(f"CosCAD extraction: {result.source_file}")
logger.info(f"  Success: {result.success}")
logger.info(f"  Geometry: {len(result.layers)} layers")
logger.info(f"  Dimensions: {len(result.dimensions)}")
logger.info(f"  Annotations: {len(result.annotations)}")
logger.info(f"  Processing time: {result.metadata.get('processing_time_ms')}ms")

if result.errors:
    logger.warning(f"  Errors: {len(result.errors)}")
    for error in result.errors:
        logger.warning(f"    - {error}")
```

---

## API Reference

### CosCADExtractor

```python
class CosCADExtractor:
    def __init__(
        self,
        service_host: str | None = None,
        service_port: int | None = None,
        timeout: int = 300,
        extract_geometry: bool = True,
        extract_dimensions: bool = True,
        extract_annotations: bool = True,
        extract_metadata: bool = True,
    ):
        """Initialize the CosCAD extractor.

        Args:
            service_host: CosCAD service host (default: from COSCAD_SERVICE_HOST env var or localhost).
            service_port: CosCAD service port (default: from COSCAD_SERVICE_PORT env var or 50051).
            timeout: Request timeout in seconds (default: 300).
            extract_geometry: Whether to extract geometry information.
            extract_dimensions: Whether to extract dimension entities.
            extract_annotations: Whether to extract text annotations.
            extract_metadata: Whether to extract file metadata.
        """

    def parse(
        self,
        source: str | Path,
        extract_geometry: bool | None = None,
        extract_dimensions: bool | None = None,
        extract_annotations: bool | None = None,
        extract_metadata: bool | None = None,
    ) -> CADExtractionResult:
        """Parse a CosCAD file and extract data.

        Args:
            source: Path to CosCAD file.
            extract_geometry: Override geometry extraction flag.
            extract_dimensions: Override dimensions extraction flag.
            extract_annotations: Override annotations extraction flag.
            extract_metadata: Override metadata extraction flag.

        Returns:
            CADExtractionResult with extracted data. Check result.success
            and result.errors for partial failures.
        """
```

### CosCADClient

```python
class CosCADClient:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout: int = 300,
    ):
        """Initialize the CosCAD gRPC client.

        Args:
            host: CosCAD service host (default: from COSCAD_SERVICE_HOST env var).
            port: CosCAD service port (default: from COSCAD_SERVICE_PORT env var).
            timeout: Request timeout in seconds (default: 300).
        """

    async def extract_async(
        self,
        source: str | Path | BinaryIO,
        extraction_types: list[CosCADExtractionType] | None = None,
    ) -> CosCADExtractionResponse:
        """Extract information from a CosCAD file asynchronously.

        Args:
            source: File path or file-like object.
            extraction_types: Types of extraction to perform (default: all).

        Returns:
            CosCADExtractionResponse with extracted data. Check response.errors
            for any errors that occurred during extraction.
        """

    def extract(
        self,
        source: str | Path | BinaryIO,
        extraction_types: list[CosCADExtractionType] | None = None,
    ) -> CosCADExtractionResponse:
        """Extract information from a CosCAD file synchronously.

        Args:
            source: File path or file-like object.
            extraction_types: Types of extraction to perform (default: all).

        Returns:
            CosCADExtractionResponse with extracted data.
        """

    async def extract_geometry_async(
        self,
        source: str | Path | BinaryIO,
    ) -> CosCADExtractionResponse:
        """Extract geometry information from a CosCAD file.

        Args:
            source: File path or file-like object.

        Returns:
            CosCADExtractionResponse with geometry data.
        """

    async def extract_dimensions_async(
        self,
        source: str | Path | BinaryIO,
    ) -> CosCADExtractionResponse:
        """Extract dimension information from a CosCAD file.

        Args:
            source: File path or file-like object.

        Returns:
            CosCADExtractionResponse with dimension data.
        """

    async def extract_annotations_async(
        self,
        source: str | Path | BinaryIO,
    ) -> CosCADExtractionResponse:
        """Extract annotation information from a CosCAD file.

        Args:
            source: File path or file-like object.

        Returns:
            CosCADExtractionResponse with annotation data.
        """

    async def extract_metadata_async(
        self,
        source: str | Path | BinaryIO,
    ) -> CosCADExtractionResponse:
        """Extract metadata from a CosCAD file.

        Args:
            source: File path or file-like object.

        Returns:
            CosCADExtractionResponse with metadata.
        """

    async def check_service_availability(
        self,
        timeout: int = 5,
    ) -> bool:
        """Check if CosCAD service is available.

        Args:
            timeout: Check timeout in seconds (default: 5).

        Returns:
            True if service is available, False otherwise.
        """
```

### Data Classes

#### CosCADExtractionType (Enum)

```python
class CosCADExtractionType(str, Enum):
    """Types of extraction requests."""
    GEOMETRY = "geometry"
    DIMENSIONS = "dimensions"
    ANNOTATIONS = "annotations"
    METADATA = "metadata"
    TITLE_BLOCK = "title_block"
    MATERIALS = "materials"
    GDT = "gdt"
    ALL = "all"
```

#### CosCADUnit (Enum)

```python
class CosCADUnit(str, Enum):
    """Unit systems supported by CosCAD."""
    MILLIMETER = "mm"
    INCH = "inch"
    MICROMETER = "um"
    CENTIMETER = "cm"
    METER = "m"
```

#### CosCADDimensionType (Enum)

```python
class CosCADDimensionType(str, Enum):
    """Dimension types in CosCAD files."""
    LINEAR = "linear"
    ANGULAR = "angular"
    RADIAL = "radial"
    DIAMETER = "diameter"
    ORDINATE = "ordinate"
    CHAMFER = "chamfer"
```

---

## Troubleshooting

### Issue: Service Not Available

**Symptoms:**
- `CosCADServiceUnavailableError` exception
- "Failed to connect to CosCAD service" error message

**Possible Causes:**
1. CosCAD gRPC service is not running
2. Incorrect service host or port
3. Firewall blocking connection
4. Network connectivity issues

**Solutions:**
1. **Check service status:**
   ```bash
   # Check if CosCAD service is running
   netstat -an | grep 50051

   # Or with service manager
   systemctl status coscad-service
   ```

2. **Verify environment variables:**
   ```bash
   # Check configuration
   echo $COSCAD_SERVICE_HOST
   echo $COSCAD_SERVICE_PORT

   # Should output:
   # localhost
   # 50051
   ```

3. **Test network connectivity:**
   ```bash
   # Test TCP connection
   telnet localhost 50051

   # Or with nc
   nc -zv localhost 50051
   ```

4. **Check firewall rules:**
   ```bash
   # Linux
   sudo ufw status
   sudo ufw allow 50051/tcp

   # Windows
   netsh advfirewall firewall add rule name="CosCAD" dir=in action=allow protocol=TCP localport=50051
   ```

### Issue: Connection Timeout

**Symptoms:**
- `CosCADTimeoutError` exception
- "Extraction timed out" error message

**Possible Causes:**
1. File is too large
2. Complex geometry requiring long processing
3. Insufficient timeout value
4. Service performance issues

**Solutions:**
1. **Increase timeout:**
   ```python
   client = CosCADClient(timeout=600)  # 10 minutes
   ```

2. **Check file size:**
   ```python
   import os

   file_size_mb = os.path.getsize("model.coscad") / (1024 * 1024)
   if file_size_mb > 50:
       print(f"Warning: Large file ({file_size_mb:.1f} MB)")
   ```

3. **Use selective extraction:**
   ```python
   # Extract only what you need
   client.extract_async(
       "model.coscad",
       extraction_types=[
           CosCADExtractionType.DIMENSIONS,
           CosCADExtractionType.METADATA
       ]
   )
   ```

4. **Monitor service performance:**
   ```bash
   # Check service resource usage
   top -p $(pgrep -f coscad-service)

   # Check service logs
   tail -f /var/log/coscad-service.log
   ```

### Issue: File Corruption Errors

**Symptoms:**
- `CosCADFileCorruptedError` exception
- "File is corrupted or invalid" error message

**Possible Causes:**
1. File transfer incomplete
2. Storage media errors
3. File version mismatch
4. Unsupported CosCAD version

**Solutions:**
1. **Verify file integrity:**
   ```bash
   # Check file size
   ls -lh model.coscad

   # Calculate checksum
   sha256sum model.coscad

   # Compare with original/source
   ```

2. **Test with known good file:**
   ```python
   # Try extracting a simple test file
   result = extractor.parse("test.coscad")
   if result.success:
       print("Test file OK - issue may be with specific file")
   ```

3. **Check file version:**
   ```python
   result = await client.extract_metadata_async("model.coscad")
   if result.metadata:
       version = result.metadata.get("version")
       print(f"CosCAD version: {version}")
   ```

4. **Recover file if possible:**
   - Restore from backup
   - Request re-export from original CAD system
   - Use file repair tools if available

### Issue: Parse Errors

**Symptoms:**
- `CosCADParseError` exception
- "Failed to parse CosCAD file" error message
- Partial extraction results

**Possible Causes:**
1. Invalid file format
2. Missing required data structures
3. Encoding issues
4. Custom or non-standard extensions

**Solutions:**
1. **Validate file format:**
   ```bash
   # Check file signature/magic bytes
   hexdump -C model.coscad | head -n 5

   # Should show CosCAD file signature
   ```

2. **Check for partial results:**
   ```python
   result = extractor.parse("model.coscad")

   # Even if parse failed, some data may be available
   if result.dimensions:
       print(f"Extracted {len(result.dimensions)} dimensions despite error")
   ```

3. **Review error details:**
   ```python
   if result.errors:
       for error in result.errors:
           print(f"Error: {error}")
           # Error messages may indicate specific issues
   ```

4. **Contact file provider:**
   - Verify file was exported correctly
   - Check for custom extensions or features
   - Request alternative export format if needed

---

## Performance Optimization

### File Size Guidelines

| File Size | Recommended Timeout | Selective Extraction |
|-----------|---------------------|---------------------|
| < 1 MB | 30-60 seconds | Not necessary |
| 1-10 MB | 60-120 seconds | Recommended for large files |
| 10-50 MB | 120-300 seconds | Highly recommended |
| > 50 MB | 300+ seconds | Use selective extraction only |

### Processing Time Estimates

| Extraction Type | Small File (<1 MB) | Medium File (1-10 MB) | Large File (>10 MB) |
|-----------------|--------------------|-----------------------|---------------------|
| Metadata only | 1-2 seconds | 2-5 seconds | 5-10 seconds |
| Dimensions only | 2-5 seconds | 5-15 seconds | 15-30 seconds |
| Geometry only | 5-10 seconds | 10-30 seconds | 30-60 seconds |
| All types | 10-20 seconds | 30-60 seconds | 60-120 seconds |

### Optimization Strategies

1. **Selective Extraction**: Only extract needed data types
2. **Batch Processing**: Process multiple files asynchronously
3. **Caching**: Cache extraction results to avoid re-processing
4. **Timeout Tuning**: Adjust timeouts based on file size
5. **Service Scaling**: Ensure CosCAD service has adequate resources
6. **Network Optimization**: Use local service when possible to reduce latency

---

## Security Considerations

### Network Security

- **Local Deployment**: Run CosCAD service on localhost when possible
- **Firewall Rules**: Restrict access to CosCAD service port
- **TLS Encryption**: Use TLS for remote CosCAD service connections
- **VPN**: Use VPN for accessing remote CosCAD services

### File Handling

- **File Validation**: Always validate file sizes and types before extraction
- **Sandboxing**: Consider running CosCAD service in isolated environment
- **Resource Limits**: Set memory and CPU limits for service
- **Logging**: Log all extraction attempts for audit trails

### Access Control

- **Authentication**: Implement authentication for CosCAD service if remote
- **Authorization**: Restrict which users can access extraction features
- **Rate Limiting**: Implement rate limiting to prevent abuse
- **Monitoring**: Monitor extraction patterns for anomalies

---

## Related Documentation

- [Field Types Reference](./fields.md) - Details on engineering field types
- [API Reference](./api.md) - Complete API endpoint documentation
- [Werk24 Integration](./werk24-integration.md) - AI-powered drawing extraction
- [System Architecture](./system-architecture.md) - PyBase architecture overview
- [Extraction System](./extraction.md) - General CAD/PDF extraction documentation

---

## External Resources

- [gRPC Python Documentation](https://grpc.io/docs/languages/python/)
- [Protocol Buffers](https://protobuf.dev/)
- [CosCAD Official Documentation](https://coscad.example/docs) - *Placeholder URL*
- [ASME Y14.5 GD&T Standard](https://www.asme.org/codes-standards/find-codes-standards/y14-5-dimensioning-tolerancing)

---

## Support

For CosCAD integration issues:
1. Check this guide's [Troubleshooting](#troubleshooting) section
2. Review [PyBase TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
3. Check CosCAD service logs for specific errors
4. Contact CosCAD service administrator
5. File PyBase issues at [GitHub Issues](https://github.com/pybase/pybase/issues)

---

**Last Updated:** 2026-01-27
**Integration Version:** 1.0.0
**gRPC Version:** 1.60.0+
