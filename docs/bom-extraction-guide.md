# BOM Extraction and Validation Guide

> Automated Bill of Materials extraction from CAD assemblies with hierarchy parsing, quantity rollup, and database validation

## Overview

PyBase provides specialized **BOM (Bill of Materials) extraction** capabilities from engineering CAD files, addressing a critical gap in manufacturing workflows. This feature eliminates manual data entry, reduces transcription errors, and accelerates procurement processes.

### What is BOM Extraction?

BOM extraction automatically identifies and extracts:
- **Part lists** from DXF blocks, IFC assemblies, and STEP files
- **Parent-child relationships** in hierarchical assemblies
- **Quantity information** with automatic rollup calculations
- **Material specifications** and properties
- **Metadata** including part numbers, descriptions, and custom attributes

### Key Benefits

- **Automation**: Extract hundreds of parts in seconds instead of hours
- **Accuracy**: Eliminate transcription errors from manual data entry
- **Validation**: Cross-reference against existing parts database
- **Flexibility**: Maintain hierarchy or flatten with quantity rollup
- **Integration**: Direct import to PyBase tables with field mapping

### Supported Formats

| Format | Extension | Hierarchy Support | Quantity Rollup |
|--------|-----------|-------------------|-----------------|
| DXF    | .dxf      | ✅ Blocks/Attributes | ✅ |
| IFC    | .ifc      | ✅ Assembly relationships | ✅ |
| STEP   | .step, .stp | ✅ Assembly structure | ✅ |

---

## Quick Start

### Prerequisites

1. **PyBase Installation**: Running PyBase instance with database migrations applied
2. **CAD Files**: DXF, IFC, or STEP files containing BOM information
3. **Table Setup**: Target table with appropriate field schema

### Basic Extraction Workflow

```bash
# 1. Extract BOM from a CAD file
curl -X POST "http://localhost:8000/api/v1/extraction/bom/extract" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@assembly.step" \
  -F "format=step" \
  -F "flatten=true" \
  -F "include_quantities=true"

# 2. Validate against existing parts database
curl -X POST "http://localhost:8000/api/v1/extraction/bom/validate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"part_number": "PART-001", "quantity": 10, "description": "Bracket"}
    ],
    "table_id": "table-uuid",
    "field_mapping": {
      "part_number": "field-uuid-1",
      "quantity": "field-uuid-2",
      "description": "field-uuid-3"
    }
  }'

# 3. Import validated BOM to table
curl -X POST "http://localhost:8000/api/v1/extraction/bom/import" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "table_id": "table-uuid",
    "bom_data": {
      "items": [...],
      "field_mapping": {...}
    }
  }'
```

---

## Extraction Options

### Hierarchy Modes

PyBase supports three BOM hierarchy modes:

#### 1. Hierarchical Mode
Maintains full parent-child relationships without flattening.

```python
{
  "hierarchy_mode": "hierarchical",
  "preserve_parent_child": true,
  "add_level_info": true,
  "add_path_info": false
}
```

**Use when:** You need to maintain assembly structure for manufacturing or configuration management.

#### 2. Flattened Mode
Collapses hierarchy into a single-level list with quantity rollup.

```python
{
  "hierarchy_mode": "flattened",
  "flattening_strategy": "path",
  "path_separator": " > "
}
```

**Use when:** You need a simple parts list for purchasing or inventory management.

#### 3. Inducted Mode
Flattens with explicit parent reference columns.

```python
{
  "hierarchy_mode": "inducted",
  "flattening_strategy": "parent_reference",
  "include_parent_ref": true
}
```

**Use when:** You need both flat list and ability to reconstruct hierarchy.

### Flattening Strategies

When flattening hierarchical BOMs, choose from these strategies:

| Strategy | Description | Example Output |
|----------|-------------|----------------|
| `path` | Concatenated path string | "Assembly > Subassembly > Part" |
| `inducted` | Level-based indentation | "└── Subassembly<br> └── Part" |
| `level_prefix` | Numeric level prefix | "1.2.3 Part" |
| `parent_reference` | Explicit parent ID column | Part with `parent_id: "sub-123"` |

### Quantity Rollup

PyBase automatically calculates total quantities by multiplying quantities up the hierarchy tree.

**Example:**
```
Assembly (Qty: 1)
└── Subassembly A (Qty: 2)
    └── Bolt (Qty: 4 each) → Total: 1 × 2 × 4 = 8 bolts
```

---

## API Endpoints

### Extract BOM

Extract BOM from CAD file with hierarchy parsing.

```bash
POST /api/v1/extraction/bom/extract
```

**Request Parameters:**
- `file`: CAD file (multipart/form-data)
- `format`: File format (`dxf`, `ifc`, `step`)
- `options`: JSON string of extraction options

**Extraction Options:**
```json
{
  "extract_bom": true,
  "hierarchy_mode": "flattened",
  "flattening_strategy": "path",
  "max_depth": null,
  "include_quantities": true,
  "include_materials": true,
  "include_properties": true,
  "preserve_parent_child": true,
  "add_level_info": false,
  "add_path_info": true,
  "path_separator": " > ",
  "include_parent_ref": false
}
```

**Response:**
```json
{
  "success": true,
  "format": "step",
  "bom": {
    "items": [
      {
        "part_number": "BRACKET-001",
        "description": "Mounting Bracket",
        "quantity": 8,
        "material": "AL-6061-T6",
        "path": "Assembly > Subassembly A > Bracket",
        "level": 3,
        "parent_id": "sub-123"
      }
    ],
    "is_flat": false,
    "total_items": 150,
    "hierarchy_depth": 5,
    "metadata": {
      "extraction_time": 2.45,
      "source_file": "assembly.step"
    }
  }
}
```

### Validate BOM

Validate extracted BOM against existing parts database.

```bash
POST /api/v1/extraction/bom/validate
```

**Request Body:**
```json
{
  "items": [
    {
      "part_number": "BRACKET-001",
      "quantity": 8,
      "description": "Mounting Bracket",
      "material": "AL-6061-T6"
    }
  ],
  "table_id": "uuid-of-target-table",
  "field_mapping": {
    "part_number": "field-uuid-for-part-number",
    "quantity": "field-uuid-for-quantity",
    "description": "field-uuid-for-description",
    "material": "field-uuid-for-material"
  },
  "validation_config": {
    "require_part_number": true,
    "require_quantity": true,
    "require_description": true,
    "check_duplicates": true,
    "validate_against_database": true,
    "part_number_pattern": "^[A-Z0-9-]+$",
    "min_quantity": 1,
    "allow_fractional_quantity": false
  }
}
```

**Response:**
```json
{
  "is_valid": true,
  "total_items": 50,
  "valid_items": 45,
  "invalid_items": 5,
  "warning_count": 8,
  "error_count": 0,
  "errors": [],
  "warnings": [
    {
      "row_index": 12,
      "field_name": "part_number",
      "error_code": "DUPLICATE_PART",
      "message": "Duplicate part number 'BRACKET-001' found in BOM",
      "severity": "warning",
      "suggestion": "This part also appears at row 3"
    }
  ],
  "new_parts": [
    {
      "part_number": "BRACKET-NEW",
      "quantity": 10,
      "description": "New Bracket Design"
    }
  ],
  "existing_parts": [
    {
      "part_number": "BRACKET-001",
      "quantity": 8,
      "_existing_record": {
        "id": "record-uuid",
        "data": {...}
      }
    }
  ],
  "duplicate_parts": [],
  "validation_time": 0.152,
  "validated_at": "2026-01-27T12:00:00Z"
}
```

### Import BOM

Import validated BOM to a table.

```bash
POST /api/v1/extraction/bom/import
```

**Request Body:**
```json
{
  "table_id": "uuid-of-target-table",
  "bom_data": {
    "items": [
      {
        "part_number": "BRACKET-001",
        "quantity": 8,
        "description": "Mounting Bracket",
        "material": "AL-6061-T6"
      }
    ]
  },
  "field_mapping": {
    "part_number": "field-uuid-for-part-number",
    "quantity": "field-uuid-for-quantity",
    "description": "field-uuid-for-description",
    "material": "field-uuid-for-material"
  },
  "import_options": {
    "skip_duplicates": true,
    "update_existing": false,
    "create_missing_fields": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "imported_count": 45,
  "skipped_count": 5,
  "updated_count": 0,
  "failed_count": 0,
  "errors": [],
  "import_time": 0.856
}
```

### Cross-Reference Parts

Compare BOM items against existing database without importing.

```bash
POST /api/v1/extraction/bom/cross-reference
```

**Request Body:**
```json
{
  "items": [...],
  "table_id": "uuid-of-target-table",
  "field_mapping": {...}
}
```

**Response:**
```json
{
  "new_parts": [...],
  "existing_parts": [...],
  "summary": {
    "total_items": 50,
    "new_count": 12,
    "existing_count": 38
  }
}
```

### Highlight Differences

Show field-by-field differences between BOM and database records.

```bash
POST /api/v1/extraction/bom/highlight-differences
```

**Request Body:**
```json
{
  "items": [...],
  "table_id": "uuid-of-target-table",
  "field_mapping": {...}
}
```

**Response:**
```json
{
  "matched_with_differences": [
    {
      "bom_item": {
        "part_number": "BRACKET-001",
        "quantity": 8,
        "description": "Mounting Bracket v2"
      },
      "existing_record": {
        "id": "record-uuid",
        "data": {
          "description": "Mounting Bracket v1"
        }
      },
      "differences": [
        {
          "field": "description",
          "bom_value": "Mounting Bracket v2",
          "record_value": "Mounting Bracket v1"
        }
      ]
    }
  ],
  "exact_matches": [...],
  "new_items": [...],
  "summary": {
    "total_items": 50,
    "differences_count": 5,
    "exact_match_count": 33,
    "new_count": 12
  }
}
```

---

## Usage Examples

### Example 1: Extract and Import DXF BOM

Extract BOM from AutoCAD DXF file with block attributes.

```python
import requests

# Extract BOM from DXF
response = requests.post(
    "http://localhost:8000/api/v1/extraction/bom/extract",
    headers={"Authorization": f"Bearer {token}"},
    files={"file": open("assembly.dxf", "rb")},
    data={
        "format": "dxf",
        "options": json.dumps({
            "hierarchy_mode": "flattened",
            "flattening_strategy": "path",
            "extract_attributes": True,
            "include_quantities": True,
            "path_separator": " > "
        })
    }
)

bom_data = response.json()["bom"]
print(f"Extracted {bom_data['total_items']} parts")
```

### Example 2: Extract IFC Assembly BOM

Extract BOM from IFC building model with material information.

```python
response = requests.post(
    "http://localhost:8000/api/v1/extraction/bom/extract",
    headers={"Authorization": f"Bearer {token}"},
    files={"file": open("building.ifc", "rb")},
    data={
        "format": "ifc",
        "options": json.dumps({
            "hierarchy_mode": "hierarchical",
            "include_materials": True,
            "include_properties": True,
            "element_types": ["IfcBuildingElementPart", "IfcDistributionElement"]
        })
    }
)

bom_data = response.json()["bom"]

# Print hierarchy
for item in bom_data["items"]:
    indent = "  " * item.get("level", 0)
    print(f"{indent}{item['part_number']}: {item['quantity']}x {item['description']}")
```

### Example 3: Extract STEP Assembly BOM

Extract BOM from STEP CAD file with assembly structure.

```python
response = requests.post(
    "http://localhost:8000/api/v1/extraction/bom/extract",
    headers={"Authorization": f"Bearer {token}"},
    files={"file": open("mechanical-assembly.step", "rb")},
    data={
        "format": "step",
        "options": json.dumps({
            "hierarchy_mode": "flattened",
            "flattening_strategy": "level_prefix",
            "include_quantities": True,
            "calculate_volumes": True,
            "level_prefix_separator": "."
        })
    }
)

bom_data = response.json()["bom"]

# Show quantity rollup
for item in bom_data["items"][:5]:
    print(f"{item['part_number']}: {item['quantity']}x - {item['description']}")
    if item.get("volume_cm3"):
        print(f"  Volume: {item['volume_cm3']} cm³")
```

### Example 4: Validate and Import Workflow

Complete workflow: extract → validate → import.

```python
# Step 1: Extract BOM
extract_response = requests.post(
    "http://localhost:8000/api/v1/extraction/bom/extract",
    headers={"Authorization": f"Bearer {token}"},
    files={"file": open("assembly.step", "rb")},
    data={"format": "step", "flatten": "true"}
)
bom_items = extract_response.json()["bom"]["items"]

# Step 2: Validate against database
validate_response = requests.post(
    "http://localhost:8000/api/v1/extraction/bom/validate",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json={
        "items": bom_items,
        "table_id": parts_table_id,
        "field_mapping": field_mapping,
        "validation_config": {
            "require_part_number": True,
            "require_quantity": True,
            "check_duplicates": True,
            "validate_against_database": True,
            "min_quantity": 1
        }
    }
)

validation_result = validate_response.json()
if not validation_result["is_valid"]:
    print(f"Validation failed: {validation_result['error_count']} errors")
    for error in validation_result["errors"]:
        print(f"  Row {error['row_index']}: {error['message']}")
    exit(1)

print(f"Validation passed: {validation_result['new_count']} new parts, "
      f"{validation_result['existing_count']} existing parts")

# Step 3: Import to table
import_response = requests.post(
    "http://localhost:8000/api/v1/extraction/bom/import",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json={
        "table_id": parts_table_id,
        "bom_data": {"items": bom_items},
        "field_mapping": field_mapping,
        "import_options": {
            "skip_duplicates": True,
            "update_existing": False
        }
    }
)

import_result = import_response.json()
print(f"Import complete: {import_result['imported_count']} records created")
```

### Example 5: Compare BOM Versions

Highlight differences between new BOM and existing database.

```python
# Extract new BOM version
new_response = requests.post(
    "http://localhost:8000/api/v1/extraction/bom/extract",
    headers={"Authorization": f"Bearer {token}"},
    files={"file": open("assembly-v2.step", "rb")},
    data={"format": "step", "flatten": "true"}
)
new_items = new_response.json()["bom"]["items"]

# Compare with database
diff_response = requests.post(
    "http://localhost:8000/api/v1/extraction/bom/highlight-differences",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json={
        "items": new_items,
        "table_id": parts_table_id,
        "field_mapping": field_mapping
    }
)

diff_result = diff_response.json()

# Review differences
print(f"Changes detected:")
for item in diff_result["matched_with_differences"]:
    print(f"\nPart: {item['bom_item']['part_number']}")
    for diff in item["differences"]:
        print(f"  {diff['field']}:")
        print(f"    Old: {diff['record_value']}")
        print(f"    New: {diff['bom_value']}")

print(f"\nNew parts: {diff_result['summary']['new_count']}")
print(f"Unchanged parts: {diff_result['summary']['exact_match_count']}")
```

---

## Validation Rules

PyBase provides comprehensive BOM validation with configurable rules.

### Required Fields

Ensure critical fields are present:

```json
{
  "validation_config": {
    "require_part_number": true,
    "require_quantity": true,
    "require_description": true,
    "require_material": false
  }
}
```

### Format Patterns

Validate field formats using regex patterns:

```json
{
  "validation_config": {
    "part_number_pattern": "^[A-Z]{2}-\\d{4}-[A-Z]$",
    "quantity_pattern": "^\\d+$",
    "material_code_pattern": "^[A-Z]{2}-\\d{3}$"
  }
}
```

**Example part numbers:** `AB-1234-C`, `XY-5678-Z`

### Value Ranges

Enforce numeric constraints:

```json
{
  "validation_config": {
    "min_quantity": 1,
    "max_quantity": 10000,
    "allow_fractional_quantity": false
  }
}
```

### Custom Field Rules

Define validation rules for specific fields:

```python
from pybase.schemas.extraction import (
    BOMValidationSchema,
    BOMValidationRule,
    BOMValidationSeverity
)

validation_config = BOMValidationSchema(
    field_rules=[
        BOMValidationRule(
            field_name="cost",
            rule_type=BOMValidationRule.VALUE_RANGE,
            min_value=0.01,
            max_value=100000,
            severity=BOMValidationSeverity.WARNING
        ),
        BOMValidationRule(
            field_name="supplier_code",
            rule_type=BOMValidationRule.FORMAT_PATTERN,
            pattern="^SUP-[A-Z0-9]{4}$",
            severity=BOMValidationSeverity.ERROR,
            custom_message="Supplier code must match SUP-XXXX format"
        ),
        BOMValidationRule(
            field_name="lead_time_weeks",
            rule_type=BOMValidationRule.ALLOWED_VALUES,
            allowed_values=["1", "2", "4", "8", "12"],
            severity=BOMValidationSeverity.WARNING
        )
    ]
)
```

---

## Python Service API

### BOMValidationService

Direct Python API for BOM validation.

```python
from pybase.services.bom_validation import BOMValidationService
from pybase.schemas.extraction import BOMValidationSchema
from sqlalchemy.ext.asyncio import AsyncSession

async def validate_bom_items(db: AsyncSession, user_id: str, items: list):
    service = BOMValidationService()

    validation_config = BOMValidationSchema(
        require_part_number=True,
        require_quantity=True,
        check_duplicates=True,
        validate_against_database=True,
        min_quantity=1,
        allow_fractional_quantity=False
    )

    result = await service.validate_bom(
        db=db,
        user_id=user_id,
        bom_items=items,
        validation_config=validation_config,
        table_id="table-uuid",
        field_mapping={
            "part_number": "field-uuid-1",
            "quantity": "field-uuid-2"
        }
    )

    return result
```

### BOMFlattenerService

Flatten hierarchical BOMs with quantity rollup.

```python
from pybase.services.bom_flattener import BOMFlattenerService
from pybase.schemas.extraction import (
    BOMExtractionOptions,
    BOMFlatteningStrategy,
    BOMHierarchyMode
)

async def flatten_hierarchical_bom(db: AsyncSession, bom_data: dict):
    service = BOMFlattenerService()

    options = BOMExtractionOptions(
        hierarchy_mode=BOMHierarchyMode.FLATTENED,
        flattening_strategy=BOMFlatteningStrategy.PATH,
        path_separator=" > ",
        preserve_parent_child=False
    )

    flattened = await service.flatten_bom(
        db=db,
        bom_data=bom_data,
        flattening_options=options
    )

    return flattened["flattened_items"]
```

### BOMComparisonService

Compare BOM items with database records.

```python
from pybase.services.bom_comparison import BOMComparisonService

async def compare_with_database(
    db: AsyncSession,
    user_id: str,
    bom_items: list,
    table_id: str,
    field_mapping: dict
):
    service = BOMComparisonService()

    differences = await service.highlight_differences(
        db=db,
        user_id=user_id,
        bom_items=bom_items,
        table_id=table_id,
        field_mapping=field_mapping
    )

    return differences
```

---

## Best Practices

### 1. Field Mapping

Create a consistent field mapping strategy:

```python
# Define mapping once and reuse
FIELD_MAPPING = {
    "part_number": "fld_part_number",
    "quantity": "fld_quantity",
    "description": "fld_description",
    "material": "fld_material_spec",
    "cost": "fld_unit_cost",
    "supplier": "fld_supplier_code"
}
```

### 2. Validation Strategy

Start strict, then relax rules incrementally:

```python
# Development: Strict validation
dev_config = BOMValidationSchema(
    require_part_number=True,
    require_quantity=True,
    require_description=True,
    require_material=True,
    check_duplicates=True,
    min_quantity=1
)

# Production: Business-configurable
prod_config = BOMValidationSchema(
    require_part_number=True,
    require_quantity=True,
    require_description=False,  # Optional in production
    require_material=False,      # Optional in production
    check_duplicates=True,
    min_quantity=1
)
```

### 3. Hierarchy vs Flat

Choose the right mode for your use case:

| Use Case | Recommended Mode | Strategy |
|----------|------------------|----------|
| Purchasing | Flattened | Path or parent_reference |
| Manufacturing | Hierarchical | Preserve parent-child |
| Configuration Mgmt | Inducted | Level prefix or inducted |
| Inventory | Flattened | Path with quantity rollup |
| Costing | Flattened | Path with cost aggregation |

### 4. Error Handling

Implement robust error handling:

```python
try:
    result = await validation_service.validate_bom(
        db=db,
        user_id=user_id,
        bom_items=items,
        validation_config=config,
        table_id=table_id,
        field_mapping=field_mapping
    )

    if not result.is_valid:
        # Log errors for review
        for error in result.errors:
            logger.error(f"BOM validation error: {error.message}")

        # Return detailed error response
        return {
            "success": False,
            "errors": [e.dict() for e in result.errors]
        }

    # Proceed with import
    return await import_bom(db, items, table_id, field_mapping)

except Exception as e:
    logger.error(f"BOM validation failed: {str(e)}")
    raise
```

### 5. Performance

Optimize for large BOMs:

```python
# Batch validation for large BOMs
async def validate_large_bom(db, items, batch_size=100):
    service = BOMValidationService()

    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        result = await service.validate_bom(
            db=db,
            user_id=user_id,
            bom_items=batch,
            validation_config=config,
            table_id=table_id,
            field_mapping=field_mapping
        )
        results.append(result)

    # Merge results
    return merge_validation_results(results)
```

---

## Troubleshooting

### Issue: Empty BOM Extraction

**Symptom:** BOM extraction returns no items.

**Possible Causes:**
1. CAD file doesn't contain BOM information
2. Wrong extraction format specified
3. Block/attribute names don't match expected patterns

**Solutions:**
```python
# Try different formats
for format_type in ["dxf", "ifc", "step"]:
    response = requests.post(
        "/api/v1/extraction/bom/extract",
        files={"file": open("assembly.dxf", "rb")},
        data={"format": format_type}
    )
    if response.json()["bom"]["total_items"] > 0:
        print(f"Found {format_type} format")
        break
```

### Issue: Validation Fails for All Items

**Symptom:** All BOM items marked as invalid.

**Possible Causes:**
1. Field mapping is incorrect
2. Validation rules too strict
3. Required fields missing from BOM

**Solutions:**
```python
# Relax validation rules gradually
config = BOMValidationSchema(
    require_part_number=True,      # Keep this
    require_quantity=False,        # Relax this
    require_description=False,     # Relax this
    check_duplicates=True,
    min_quantity=0                 # Allow zero
)
```

### Issue: Quantity Rollup Incorrect

**Symptom:** Flattened quantities don't match expected totals.

**Possible Causes:**
1. Hierarchy relationships not detected
2. Missing quantity data in intermediate levels
3. Circular references in BOM

**Solutions:**
```python
# Check hierarchy before flattening
response = requests.post(
    "/api/v1/extraction/bom/extract",
    data={"format": "step", "hierarchy_mode": "hierarchical"}
)

bom = response.json()["bom"]
print(f"Hierarchy depth: {bom['hierarchy_depth']}")
print(f"Items: {bom['total_items']}")

# Verify parent-child map exists
if not bom.get("parent_child_map"):
    print("Warning: No hierarchy detected, BOM may be flat")
```

---

## Advanced Topics

### Custom BOM Extractors

Extend BOM extraction for proprietary formats:

```python
from pybase.extraction.base import ExtractedBOM
from abc import ABC, abstractmethod

class CustomBOMExtractor(ABC):
    """Base class for custom BOM extractors."""

    @abstractmethod
    async def extract_bom(self, file_path: str) -> ExtractedBOM:
        """Extract BOM from custom format."""
        pass

    @abstractmethod
    def parse_hierarchy(self, raw_data: dict) -> dict:
        """Parse parent-child relationships."""
        pass
```

### Batch BOM Processing

Process multiple CAD files in parallel:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def extract_bom_batch(file_paths: list[str]):
    """Extract BOMs from multiple files concurrently."""

    async def extract_one(file_path: str):
        response = requests.post(
            "/api/v1/extraction/bom/extract",
            files={"file": open(file_path, "rb")},
            data={"format": "step", "flatten": "true"}
        )
        return response.json()

    # Process up to 5 files concurrently
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(executor, extract_one, fp)
            for fp in file_paths
        ]
        results = await asyncio.gather(*tasks)

    return results
```

### BOM Version Control

Track BOM changes over time:

```python
from datetime import datetime

def save_bom_version(bom_data: dict, version: str):
    """Save BOM snapshot with version tracking."""

    snapshot = {
        "version": version,
        "timestamp": datetime.utcnow().isoformat(),
        "total_items": len(bom_data["items"]),
        "items": bom_data["items"],
        "checksum": calculate_bom_checksum(bom_data)
    }

    # Store in database or file system
    return snapshot

def compare_bom_versions(version_a: dict, version_b: dict):
    """Compare two BOM versions for changes."""

    added = set(item["part_number"] for item in version_b["items"]) - \
            set(item["part_number"] for item in version_a["items"])

    removed = set(item["part_number"] for item in version_a["items"]) - \
              set(item["part_number"] for item in version_b["items"])

    return {"added": list(added), "removed": list(removed)}
```

---

## Summary

PyBase BOM extraction provides:

✅ **Automated extraction** from DXF, IFC, STEP files
✅ **Hierarchy preservation** or flattening with quantity rollup
✅ **Database validation** against existing parts
✅ **Difference highlighting** for version comparison
✅ **Direct import** to PyBase tables with field mapping
✅ **Flexible validation** rules and format patterns
✅ **RESTful API** and Python service interfaces

This feature significantly reduces manual data entry effort, improves accuracy, and accelerates manufacturing workflows.
