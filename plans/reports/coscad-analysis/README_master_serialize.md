# Master Model Serialization and Indexing - LLM Guide

## Purpose

This is the **single source of truth** for serializing PTC Creo CAD models (parts `.prt` and assemblies `.asm`). It extracts complete model data from a running Creo session and stores it in a database for later retrieval, analysis, or recreation.

**All other serialization scripts in this project are deprecated in favor of this one.**

---

## What This Script Does

### Core Function
1. **Connects to Creo** via gRPC or HTTP JSON-RPC
2. **Extracts model data** including:
   - Complete feature element trees (the internal Creo representation)
   - Feature hierarchy and relationships
   - Sketch geometry (lines, arcs, circles, splines, points)
   - Parameters and relations (parametric equations)
   - Metadata (units, mass properties, bounding box)
3. **Saves to database** (PostgreSQL) with indexing for retrieval
4. **Optionally saves JSON** files for inspection

### Why This Matters
- **Recreation**: Extracted data enables recreating models programmatically
- **Analysis**: Understanding model structure without opening Creo
- **Search**: Database indexing enables finding similar models/features
- **Documentation**: Captures complete model definition for LLM understanding

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MASTER SERIALIZATION PIPELINE                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Input: Directory of .prt/.asm files                                 │
│         │                                                             │
│         ▼                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │  Find Models    │───▶│ Serialize Model │───▶│ Enhance Data    │  │
│  │  (.prt, .asm)   │    │  (gRPC/HTTP)    │    │  (Add sketches, │  │
│  └─────────────────┘    └─────────────────┘    │   refs, groups)  │  │
│                                                  └─────────────────┘  │
│                                                         │             │
│                                                         ▼             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │  Save JSON      │◀───│  Save to DB     │◀───│  Validate       │  │
│  │  (optional)     │    │  (PostgreSQL)   │    │  Quality        │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Classes

### `MasterSerializationEngine`
The core engine that handles individual model serialization.

**Key Methods:**
- `serialize_model_grpc()` - Serialize via gRPC (preferred, faster)
- `serialize_model_http()` - Serialize via HTTP JSON-RPC (fallback)
- `_enhance_serialization()` - Add sketches, references, groups, metadata
- `save_to_database()` - Store serialized data in PostgreSQL
- `_extract_all_sketches()` - Extract sketch geometry from features

### `MasterSerializationPipeline`
Orchestrates batch processing of multiple models.

**Key Methods:**
- `find_models()` - Scan directory for .prt/.asm files
- `run()` - Execute full serialization pipeline
- `_serialize_sequential()` - Process models one at a time
- `_serialize_parallel()` - Process models concurrently

---

## Extraction Options (Phases & Features)

### Phase 1: Parameter Extraction (`--include-parameters`)
Extracts model-level parameters:
- Parameter names and values
- Parameter types (STRING, DOUBLE, INTEGER, BOOLEAN, NOTE)
- Units for numeric parameters
- Designation (DRIVING/DRIVEN)

### Phase 2: Relations Extraction (`--include-relations`)
Extracts parametric relations:
- Relation text (equations like `d5 = d3 * 2`)
- IF/ELSE/ENDIF block structure
- Variable usage analysis
- Error status for each relation

### Phase 3: Metadata Extraction (`--include-metadata`)
Extracts model metadata:
- Units system (length, mass, time, temperature)
- Mass properties (mass, volume, density, COG, inertia)
- Bounding box (min/max points, dimensions)
- Feature statuses (ACTIVE, SUPPRESSED, HIDDEN)
- Model dates and author

### Option 2B: Group Structure Capture (`--enhanced`)
Uses `ProSolidGroupsCollect` and `ProGroupFeaturesCollect` to get:
- All groups in the model
- Children of each group
- Parent-child relationships

### Option 3A: Feature Reference Extraction (`--enhanced`)
Uses `ProFeatureRefsGet` to capture:
- Reference type (surface, edge, axis, etc.)
- Reference ID and name
- Owner model

### Option 3.0: Complete Sketch Extraction (`--enhanced`)
Extracts sketches from ALL features that use sketches:
- Covers EXTRUDE, SWEEP, FILL, REVOLVE, CUT, PROTRUSION operations
- Captures entities (lines, arcs, circles, splines, points)
- Links sketches to parent features by feature_id
- Sketch plane and orientation information

### Option 4.0: Semantic Geometry References (`--enhanced`)
Builds geometry lookup for reference resolution:
- Maps original geometry IDs to semantic references
- Stores geometric properties (normal, centroid, area) for matching
- Enables reference resolution during model recreation

---

## Database Schema

Serialized models are stored in the `serialized_models` table:

```sql
CREATE TABLE serialized_models (
    id                      SERIAL PRIMARY KEY,
    model_name              VARCHAR(255) UNIQUE NOT NULL,
    model_type              VARCHAR(50),           -- 'part' or 'assembly'
    feature_count           INTEGER,
    category                VARCHAR(100),
    tags                    TEXT[],
    serialized_content      JSONB,                 -- Full serialized data
    structure_summary       JSONB,                 -- Feature types, counts
    feature_types           TEXT[],                -- List of feature types
    units                   JSONB,                 -- Phase 3: length, mass, etc.
    parameters              JSONB,                 -- Phase 1: model parameters
    relations               JSONB,                 -- Phase 2: parametric equations
    mass_properties         JSONB,                 -- Phase 3: mass, volume, COG
    bounding_box            JSONB,                 -- Phase 3: extents
    feature_statuses        JSONB,                 -- Phase 3: active/suppressed
    model_created_at        TIMESTAMP,
    model_author            VARCHAR(255),
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);
```

---

## Usage Examples

### Basic Usage
```bash
# Serialize a single directory
python master_serialize_and_index.py "C:\CAD\Parts" --tags EMJAC,skeleton,complete

# Serialize with parallel workers
python master_serialize_and_index.py "C:\CAD\Parts" --parallel 4

# Resume from previous run (skips completed models)
python master_serialize_and_index.py "C:\CAD\Parts" --resume
```

### Enhanced Mode (All Features)
```bash
# Enable groups, references, sketches, semantic geometry
python master_serialize_and_index.py "C:\CAD\Parts" --enhanced

# Same as --enhanced plus parameters, relations, metadata
python master_serialize_and_index.py "C:\CAD\Parts" --complete
```

### Phase-Specific Extraction
```bash
# Extract only parameters (Phase 1)
python master_serialize_and_index.py "C:\CAD\Parts" --include-parameters

# Extract parameters + relations (Phase 1 + 2)
python master_serialize_and_index.py "C:\CAD\Parts" --include-parameters --include-relations

# Extract everything including metadata (Phase 1 + 2 + 3)
python master_serialize_and_index.py "C:\CAD\Parts" --include-parameters --include-relations --include-metadata
```

### Protocol Selection
```bash
# Use gRPC only (fails if unavailable)
python master_serialize_and_index.py "C:\CAD\Parts" --protocol grpc

# Use HTTP only
python master_serialize_and_index.py "C:\CAD\Parts" --protocol http

# Auto (default): try gRPC, fall back to HTTP
python master_serialize_and_index.py "C:\CAD\Parts" --protocol auto
```

### Custom Server Addresses
```bash
python master_serialize_and_index.py "C:\CAD\Parts" \
    --grpc 192.168.1.72:50052 \
    --http http://192.168.1.72:8080/api/rpc
```

---

## Command-Line Arguments

| Argument | Description |
|----------|-------------|
| `input_dir` | Directory containing .prt/.asm files (required) |
| `-o, --output` | Output directory for JSON files (default: serialized_models) |
| `-c, --category` | Model category (e.g., EMJAC, SDI, STOCK) |
| `-t, --tags` | Comma-separated tags (e.g., skeleton,complete,EMJAC) |
| `-p, --parallel` | Number of parallel workers (default: 1) |
| `--resume` | Resume from previous run (skips completed models) |
| `--enhanced` | Enable enhanced mode (groups, references, sketches) |
| `--include-parameters` | Extract Phase 1: model parameters |
| `--include-relations` | Extract Phase 2: parametric relations |
| `--include-metadata` | Extract Phase 3: units, mass props, bbox |
| `--complete` | Enable ALL extraction options |
| `--grpc` | gRPC server address (default: localhost:50052) |
| `--http` | HTTP JSON-RPC URL (default: http://127.0.0.1:50051) |
| `--protocol` | Protocol: auto, grpc, or http (default: auto) |

---

## Known Creo Type IDs

The script recognizes these Creo feature type IDs:

| Type ID | Feature Type |
|---------|--------------|
| 916 | DATUM_SURFACE (EXTRUDE, TRIM, etc.) |
| 917 | PROTRUSION |
| 918 | CUT |
| 919 | HOLE |
| 920 | ROUND |
| 921 | CHAMFER |
| 922 | DRAFT |
| 923 | DATUM_PLANE |
| 924 | DATUM_AXIS |
| 925 | DATUM_POINT |
| 926 | DATUM_CURVE |
| 931 | FPNT (fixed point) |
| 942 | SWEEP/FILL/REVOLVE |
| 946 | CURVE |
| 949 | SKETCH |
| 979 | CSYS (coordinate system) |
| 984 | DATUM_SURFACE |
| 989 | COPY_GEOM |
| 1084 | PATTERN |
| 1085 | MEASURE |
| 1104 | GROUP (container only) |
| 1232 | ANALYSIS |
| 1243 | SURFACE |

---

## Dependencies

### Required Modules
- `sketch_extraction` - Unified sketch extraction (`SketchExtractor`)
- `parameter_extractor` - Parameter extraction (`ParameterExtractor`)
- `relation_extractor` - Relations extraction (`RelationExtractor`)
- `metadata_extractor` - Metadata extraction (`MetadataExtractor`)

### External Libraries
- `psycopg2` - PostgreSQL database connection
- `grpc` - gRPC client (optional, falls back to HTTP)
- `requests` - HTTP JSON-RPC client
- `python-dotenv` - Environment variables

### Environment Variables
```bash
# Database (MODEL_DATA_DB_URL takes precedence)
MODEL_DATA_DB_URL=postgresql://user:pass@host:port/db
DATABASE_URL=postgresql://user:pass@host:port/db  # Fallback
```

---

## Output Format

### Serialized Model JSON Structure
```json
{
  "model_name": "PART_NAME",
  "features": [
    {
      "id": 123,
      "name": "HOLE_1",
      "type": "HOLE",
      "type_id": 919,
      "element_tree": {
        "elements": [
          {
            "element_id": 1234,
            "value": "...",
            "value_type": "...",
            "depth": 1
          }
        ],
        "element_count": 42
      },
      "references": [...],
      "feature_geometry": {
        "surfaces": [...],
        "edges": [...]
      }
    }
  ],
  "sketches": [
    {
      "feature_id": 456,
      "feature_name": "PROTRUSION_1",
      "plane": {...},
      "entities": [...],
      "constraints": [...],
      "dimensions": [...]
    }
  ],
  "groups": [...],
  "parameters": {...},
  "relations": {...},
  "metadata": {
    "units": {...},
    "mass_properties": {...},
    "bounding_box": {...},
    "feature_statuses": {...}
  },
  "serialization_quality": {...}
}
```

---

## Quality Metrics

The script tracks serialization quality:

| Metric | Description |
|--------|-------------|
| `total_features` | Total features in model |
| `features_with_elements` | Features with element tree data |
| `element_coverage` | Percentage of meaningful features with elements |
| `group_features` | Number of group features (containers) |
| `analysis_features` | Number of analysis features (non-geometric) |
| `recoverable_unknown` | Unknown features with element data |
| `unrecoverable_unknown` | Unknown features without element data (can't recreate) |

---

## Common Issues

### "gRPC connection failed"
- gRPC server not running or wrong address
- Use `--protocol http` to force HTTP mode
- Check firewall settings

### "Could not get model handle"
- Model not open in Creo
- Creo session not accessible
- Check `--http` URL for remote Creo

### "Database connection failed"
- Check `MODEL_DATA_DB_URL` or `DATABASE_URL` in `.env`
- Ensure PostgreSQL is running
- Verify database credentials

### Low element coverage (< 80%)
- Some features may not extract properly
- Check `unrecoverable_unknown` count
- May need higher `MAX_ELEMENTS_PER_FEATURE`

---

## Version History

### v3.0 - Sketch Extraction
- Complete sketch extraction for ALL sketch-using features
- Covers EXTRUDE, SWEEP, FILL, REVOLVE, CUT, PROTRUSION
- Unified sketch extraction module

### v2.0 - Enhanced Features
- Increased `MAX_ELEMENTS_PER_FEATURE` to 50000 (Option 2A)
- Group structure capture (Option 2B)
- Feature reference extraction (Option 3A)
- Quality metrics and validation reporting

### v1.0 - Initial
- Basic feature element tree extraction
- Database storage with indexing
- JSON file export
- Resume capability
