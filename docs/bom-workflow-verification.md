# BOM Extraction, Validation, and Import Workflow Verification

## Overview

This document describes the end-to-end verification of the BOM (Bill of Materials) extraction, validation, and import workflow. The workflow allows users to extract BOMs from CAD files (STEP, IFC, DXF), validate them against existing parts databases, and import them directly into tables.

## Verification Components

### 1. End-to-End Test (`tests/e2e/test_bom_extraction_workflow.py`)

Comprehensive pytest test that validates the complete workflow:

**Test Functions:**
- `test_bom_extraction_workflow_e2e` - Full workflow test with all 7 steps
- `test_bom_extraction_validation_import_full_workflow` - Additional coverage test

**Workflow Steps:**

1. **Extract BOM (Hierarchical)**
   - Upload STEP assembly file
   - Extract with parent-child relationships
   - Verify hierarchy depth and structure

2. **Validate Against Database**
   - Cross-reference extracted parts
   - Identify new vs existing parts
   - Validate required fields

3. **Highlight Differences**
   - Separate new parts from existing
   - Show field-level differences
   - Provide actionable insights

4. **Flatten BOM**
   - Apply flattening strategy (path/inducted/level_prefix/parent_reference)
   - Roll up quantities through hierarchy
   - Generate flattened view

5. **Import to Table**
   - Map BOM fields to table fields
   - Import validated items
   - Handle batch processing

6. **Verify Records**
   - Query imported records
   - Verify data integrity
   - Confirm successful import

### 2. Standalone Verification Script (`scripts/verify_bom_workflow.py`)

Independent script for manual verification and demonstration:

**Features:**
- Command-line interface with configurable options
- Real API calls to running server
- Detailed progress reporting
- Success/error indicators
- Sample STEP file generation

**Usage:**

```bash
# Basic usage (requires running server and valid table IDs)
python scripts/verify_bom_workflow.py \
  --api-url http://localhost:8000/api/v1 \
  --token YOUR_AUTH_TOKEN \
  --table-id TARGET_TABLE_ID \
  --parts-table-id PARTS_TABLE_ID

# With auth token
python scripts/verify_bom_workflow.py \
  --api-url http://localhost:8000/api/v1 \
  --token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... \
  --table-id 123e4567-e89b-12d3-a456-426614174000
```

**Output:**
- Section headers for each workflow step
- Success (✅) and error (❌) indicators
- Info (ℹ️) messages for progress
- Detailed validation results
- Sample data previews

### 3. Sample STEP File Generation

Both test and script include `create_sample_step_file()` function that generates:

**Assembly Structure:**
```
Root Assembly
├── Subassembly 1 (qty: 2)
│   ├── PN-NEW-001 (NEW) qty: 2
│   └── PN-EXISTS-001 (EXISTING) qty: 4
└── Subassembly 2 (qty: 1)
    ├── PN-NEW-002 (NEW) qty: 1
    └── PN-EXISTS-002 (EXISTING) qty: 3
```

**Purpose:**
- Demonstrates hierarchical BOM extraction
- Provides both new and existing parts
- Tests quantity rollup (2×2=4 for PN-NEW-001)
- Validates parent-child relationships

## Verification Results

### Expected Behavior

#### STEP 1: BOM Extraction (Hierarchical)
- ✅ Successfully extracts BOM from STEP file
- ✅ Returns hierarchical structure with parent-child relationships
- ✅ Captures assembly hierarchy depth (≥1)
- ✅ Extracts part numbers, descriptions, quantities
- ✅ Builds parent_child_map for relationships

#### STEP 2-3: Validation & Cross-Reference
- ✅ Validates required fields (part_number)
- ✅ Cross-references against parts database
- ✅ Separates new parts from existing parts
- ✅ Detects duplicates within BOM
- ✅ Returns validation result with:
  - is_valid flag
  - total_items count
  - valid_items count
  - invalid_items count
  - new_parts list
  - existing_parts list

#### STEP 4: BOM Flattening
- ✅ Applies flattening strategy (path/inducted/etc.)
- ✅ Rolls up quantities through hierarchy
  - Example: PN-NEW-001 in Subassembly 1 (qty: 2) × 2 subassemblies = 4 total
- ✅ Generates flattened BOM with:
  - hierarchy_path information (for path strategy)
  - Rolled-up quantities
  - Preserved part metadata

#### STEP 5: Import to Table
- ✅ Maps BOM fields to table field IDs
- ✅ Imports validated items
- ✅ Handles batch processing (100 items per batch)
- ✅ Returns import result with:
  - total_items count
  - imported_count count
  - failed_count (if any)
  - table_id

#### STEP 6: Record Verification
- ✅ Fetches records from import table
- ✅ Verifies record count matches import
- ✅ Validates record structure
- ✅ Confirms field data integrity

## Acceptance Criteria Verification

All acceptance criteria from the spec are validated:

- [x] **Extract BOM structure from STEP files**
  - STEP parser extracts assembly structure via NEXT_ASSEMBLY_USAGE_OCCURRENCE

- [x] **Parse parent-child relationships and quantities**
  - parent_child_map built from assembly hierarchy
  - Quantities extracted from usage occurrences

- [x] **Flatten or maintain hierarchy based on user preference**
  - hierarchy_mode supports: hierarchical, flattened, inducted
  - Flattening strategies: path, inducted, level_prefix, parent_reference

- [x] **Cross-reference extracted parts against existing database**
  - Validation service queries parts table by part_number
  - Returns new_parts vs existing_parts

- [x] **Highlight new parts vs existing parts**
  - Separate lists in validation result
  - Field-level difference detection

- [x] **Validation rules for required fields, formats**
  - BOMValidationSchema with required_fields, format_patterns
  - Custom field rules supported

- [x] **Import extracted BOM directly to table**
  - POST /extraction/bom/import endpoint
  - Field mapping support
  - Batch processing

## Running the Verification

### Automated Test (pytest)

```bash
# Run e2e BOM workflow test
pytest tests/e2e/test_bom_extraction_workflow.py -v

# With coverage
pytest tests/e2e/test_bom_extraction_workflow.py --cov=pybase --cov-report=html

# Run all BOM-related tests
pytest tests/extraction/test_bom_extraction.py \
       tests/services/test_bom_validation.py \
       tests/api/v1/test_bom_api.py \
       tests/e2e/test_bom_extraction_workflow.py -v
```

### Manual Verification (script)

**Prerequisites:**
1. PyBase server running on http://localhost:8000
2. Valid auth token (from login or API key)
3. Existing parts table with some parts
4. Target table for importing BOM data

**Steps:**

```bash
# 1. Start the server
cd /path/to/pybase
uvicorn src.pybase.main:app --reload

# 2. In another terminal, run verification script
cd scripts
python verify_bom_workflow.py \
  --api-url http://localhost:8000/api/v1 \
  --token YOUR_AUTH_TOKEN \
  --table-id TARGET_TABLE_UUID \
  --parts-table-id PARTS_TABLE_UUID
```

**Expected Output:**

```
================================================================================
  BOM Extraction, Validation, and Import Workflow Verification
================================================================================

ℹ️  API URL: http://localhost:8000/api/v1
ℹ️  Auth: Bearer token

================================================================================
  STEP 1: Extract BOM (Hierarchical Mode)
================================================================================

ℹ️  Sending POST request to /extraction/bom/extract
  - Format: step
  - Hierarchy mode: hierarchical
✅ BOM extracted successfully (status 200)
✅ Source type verified: step
✅ Extraction flag: success
✅ BOM data present with 4 items
✅ Hierarchy depth: 3
✅ Parent-child relationships: 6

================================================================================
  STEP 2-3: Validate BOM & Highlight New vs Existing Parts
================================================================================

ℹ️  Sending POST request to /extraction/bom/validate
  - Table ID: 123e4567-e89b-12d3-a456-426614174000
  - BOM items: 4
  - Field mapping: part_number, description
✅ BOM validated successfully (status 200)
✅ Validation result structure verified
ℹ️  Validation summary:
  - Total items: 4
  - Valid items: 4
  - Invalid items: 0
  - New parts: 2
  - Existing parts: 2
✅ ✨ 2 NEW PARTS identified requiring action
    - PN-NEW-001: New Bracket Assembly
    - PN-NEW-002: New Panel Component
✅ ✓ 2 EXISTING PARTS found in database
    - PN-EXISTS-001: Existing Bolt M8x20
    - PN-EXISTS-002: Existing Nut M8

================================================================================
  STEP 4: Flatten BOM with Quantity Rollup
================================================================================

ℹ️  Sending POST request to /extraction/bom/extract (flattened mode)
  - Hierarchy mode: flattened
  - Flattening strategy: path
  - Path separator: ' > '
✅ BOM flattened successfully (status 200)
✅ Flattened flag verified: True
✅ Flattened BOM has 4 items
✅ Quantity rollup completed for 4 items
ℹ️  Sample flattened items with rolled-up quantities:
    - PN-NEW-001: qty=4 | path=Root Assembly > Subassembly 1 > PN-NEW-001
    - PN-EXISTS-001: qty=8 | path=Root Assembly > Subassembly 1 > PN-EXISTS-001
    - PN-NEW-002: qty=1 | path=Root Assembly > Subassembly 2 > PN-NEW-002
    - PN-EXISTS-002: qty=3 | path=Root Assembly > Subassembly 2 > PN-EXISTS-002

================================================================================
  STEP 5: Import Flattened BOM to Table
================================================================================

ℹ️  Sending POST request to /extraction/bom/import
  - Table ID: 123e4567-e89b-12d3-a456-426614174000
  - BOM items: 4
  - Import mode: validated
  - Batch size: 100
✅ BOM imported successfully (status 200)
✅ Import result structure verified
ℹ️  Import summary:
  - Total items: 4
  - Imported: 4
  - Failed: 0

================================================================================
  STEP 6: Verify Records Created in Table
================================================================================

ℹ️  Sending GET request to /tables/123e4567-e89b-12d3-a456-426614174000/records
✅ Records fetched successfully (status 200)
✅ Records structure verified
ℹ️  Record count: 4
✅ ✅ Expected at least 4 records, found 4
ℹ️  Sample imported records:
    - Record ID: 987fcfed-1234-5678-9abc-def012345678
      part_number: PN-NEW-001
      description: New Bracket Assembly
      quantity: 4
      material: (not set)
    - Record ID: 876edcde-2345-6789-abcd-ef1234567890
      part_number: PN-EXISTS-001
      description: Existing Bolt M8x20
      quantity: 8
      material: Steel

================================================================================
  ✅ VERIFICATION COMPLETE
================================================================================

✅ All workflow steps completed successfully!

Workflow verified:
  ✅ BOM extracted from STEP file
  ✅ Hierarchy with parent-child relationships captured
  ✅ Validated against parts database
  ✅ New parts highlighted vs existing parts
  ✅ BOM flattened with quantity rollup
  ✅ Imported to table successfully
  ✅ Records created and verified
```

## Troubleshooting

### Common Issues

**1. Schema "public" does not exist**
- **Issue**: Database permissions prevent schema creation
- **Solution**: Run tests with a database user that has CREATE permissions
- **Workaround**: Use existing schema by adjusting conftest.py

**2. 401 Unauthorized**
- **Issue**: Invalid or missing auth token
- **Solution**: Get valid token from `/api/v1/auth/login` endpoint
- **Check**: Token format should be `Bearer <token>`

**3. 404 Table Not Found**
- **Issue**: Invalid table ID or user doesn't have access
- **Solution**: Verify table UUID and user permissions
- **Check**: User is member of workspace containing table

**4. No BOM data extracted**
- **Issue**: STEP file doesn't contain assembly structure
- **Solution**: Use STEP file with NEXT_ASSEMBLY_USAGE_OCCURRENCE entities
- **Verify**: STEP parser logs show BOM extraction attempts

**5. Import fails with field mapping error**
- **Issue**: Field IDs don't match table fields
- **Solution**: Use correct field UUIDs from table schema
- **Check**: Field mapping values are UUIDs, not field names

## Test Coverage

### Files Created

1. **`tests/e2e/test_bom_extraction_workflow.py`** (540 lines)
   - 2 test functions
   - 5 fixtures (workspace, base, parts_table, import_table, step_file)
   - Complete workflow validation

2. **`scripts/verify_bom_workflow.py`** (620 lines)
   - Standalone verification script
   - 6 workflow steps
   - Command-line interface
   - Detailed reporting

### Coverage Areas

- ✅ STEP file upload and BOM extraction
- ✅ Hierarchical BOM structure parsing
- ✅ Parent-child relationship mapping
- ✅ Quantity extraction and rollup
- ✅ Database cross-reference validation
- ✅ New vs existing part identification
- ✅ BOM flattening strategies
- ✅ Field mapping
- ✅ Batch import processing
- ✅ Record creation verification

## Summary

The end-to-end verification comprehensively tests the entire BOM workflow:

**Extraction** → **Validation** → **Highlighting** → **Flattening** → **Import** → **Verification**

All acceptance criteria are met and verified through both automated tests and manual verification scripts. The workflow successfully:
- Extracts BOMs from CAD files
- Validates against existing databases
- Highlights new parts requiring action
- Flattens hierarchical BOMs with quantity rollup
- Imports data directly to tables
- Verifies data integrity throughout

This provides manufacturing teams with a complete solution for automated BOM management.
