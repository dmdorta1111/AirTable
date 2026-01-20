# Phase D: Creo CAD Extraction

Extract metadata from Creo Parametric CAD files (.prt, .asm) and integrate with the document intelligence platform.

## Overview

Phase D extends the extraction pipeline to handle Creo CAD files:
- **Parts (.prt)**: Individual component models
- **Assemblies (.asm)**: Multi-component assemblies with BOM

## Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| D1-queue-cad-jobs.py | Queue .prt/.asm files for extraction | Ready |
| D2-creo-extraction-worker.py | Worker framework for Creo extraction | **PLACEHOLDER** |
| D3-creo-json-importer.py | Import existing JSON extraction files | Ready |
| D4-link-cad-to-documents.py | Link CAD files to DocumentGroups | Ready |
| D5-index-cad-parameters.py | Index parameters for search | Ready |
| D6-cad-extraction-report.py | Generate extraction statistics | Ready |

## Creo Integration Status

### Current State: PLACEHOLDER

The D2 worker framework is complete but the actual Creo extraction requires:

1. **Creo Parametric Installation** - Running instance with API access
2. **Creo API DLL** - Loaded within Creo's Python environment
3. **Extraction Script** - Python script executed within Creo

### Integration Points

The `extract_with_creo()` function in D2 needs to be replaced with actual Creo API calls:

```python
# PLACEHOLDER - Replace with actual Creo integration
def extract_with_creo(local_file_path: str, job_type: str) -> dict:
    """
    TODO: Implement Creo API integration
    
    Options:
    1. creoson library (if available)
    2. Direct Creo Toolkit API via DLL
    3. External script invocation
    """
    pass
```

### Workaround: JSON Import (D3)

Until Creo integration is complete, use D3 to import existing JSON files:

```bash
# If you have existing Creo extraction JSON files
python D3-creo-json-importer.py --input-dir /path/to/json/files
```

## Usage

### Step 1: Queue CAD Files

```bash
# Find all .prt/.asm files and create extraction jobs
python D1-queue-cad-jobs.py

# Dry run to see what would be queued
python D1-queue-cad-jobs.py --dry-run

# Queue with higher priority
python D1-queue-cad-jobs.py --priority 10
```

### Step 2: Extract (Choose One)

**Option A: Import Existing JSON** (Recommended until Creo integrated)
```bash
python D3-creo-json-importer.py --input-dir /path/to/json/files
```

**Option B: Run Worker** (Placeholder - marks jobs as skipped)
```bash
python D2-creo-extraction-worker.py --workers 1
```

### Step 3: Link to DocumentGroups

```bash
# Link CAD files to existing DocumentGroups by basename matching
python D4-link-cad-to-documents.py

# Dry run
python D4-link-cad-to-documents.py --dry-run
```

### Step 4: Index Parameters

```bash
# Index parameters from raw_data for search
python D5-index-cad-parameters.py

# Reindex all (clears existing)
python D5-index-cad-parameters.py --reindex
```

### Step 5: Generate Report

```bash
# Console report
python D6-cad-extraction-report.py

# Detailed report
python D6-cad-extraction-report.py --detailed

# JSON output
python D6-cad-extraction-report.py --output-format json
```

## Expected JSON Structure

D3 and D5 are designed to handle flexible JSON structures. Common formats:

### Format 1: List of Parameters
```json
{
  "filename": "88617-001.prt",
  "parameters": [
    {"name": "MATERIAL", "value": "304 SS", "designated": true},
    {"name": "WEIGHT", "value": "2.45", "units": "kg"}
  ],
  "bom": null
}
```

### Format 2: Dict of Parameters
```json
{
  "model_name": "88617-001.prt",
  "params": {
    "MATERIAL": "304 SS",
    "WEIGHT": {"value": 2.45, "units": "kg"}
  },
  "mass_properties": {
    "mass": 2.45,
    "volume": 0.00031
  }
}
```

### Format 3: Assembly with BOM
```json
{
  "filename": "ASSEMBLY-001.asm",
  "parameters": [...],
  "bom": [
    {"item": 1, "part_number": "88617-001", "qty": 2},
    {"item": 2, "part_number": "88617-002", "qty": 1}
  ]
}
```

## Database Tables Used

| Table | Purpose |
|-------|---------|
| extraction_jobs | Job queue (job_type: 'creo_part', 'creo_asm') |
| extracted_metadata | Raw JSON storage (source_type: 'creo_part', 'creo_asm') |
| extracted_parameters | Indexed parameters for search |
| document_group_members | CAD-to-DocumentGroup links (role: 'source_cad') |

## Linking Strategy

D4 matches CAD files to DocumentGroups by basename:

```
88617-001.prt.1  ->  basename: "88617-001"  ->  DocumentGroup: "88617-001"
BRACKET_ASSY.asm ->  basename: "BRACKET_ASSY" -> DocumentGroup: "BRACKET_ASSY"
```

Match priority:
1. Exact name match
2. Item number match
3. Case-insensitive match
4. Partial/contains match

## Parameter Categorization

D5 automatically categorizes parameters:

| Category | Example Parameters |
|----------|-------------------|
| material | MATERIAL, MAT, PRO_MP_MATERIAL |
| weight | WEIGHT, MASS, PRO_MP_MASS |
| density | DENSITY, PRO_MP_DENSITY |
| description | DESCRIPTION, DESC |
| part_number | PART_NUMBER, PN |
| revision | REVISION, REV |
| custom | (everything else) |

## Troubleshooting

### No CAD files found
```bash
# Check CloudFiles for CAD extensions
python D1-queue-cad-jobs.py --stats-only
```

### JSON import not matching
```bash
# Check what filenames are being extracted
python D3-creo-json-importer.py --input-dir /path --dry-run
```

### Parameters not indexing
```bash
# Check if raw_data has expected structure
python D5-index-cad-parameters.py --stats-only
```

## Future: Creo Integration

When ready to integrate Creo:

1. Identify Creo API access method (creoson, Toolkit, etc.)
2. Update `extract_with_creo()` in D2
3. Test with single file: `python D2-creo-extraction-worker.py --limit 1`
4. Scale up workers as needed

The worker framework handles:
- Job claiming with row-level locking
- B2 file download
- Result storage
- Error handling
- Graceful shutdown

Only the extraction function needs implementation.

---

*Phase D - Creo CAD Extraction*
*Part of the Unified Engineering Document Intelligence Platform*
