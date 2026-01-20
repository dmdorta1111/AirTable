# Unified Engineering Document Intelligence Platform

## Executive Summary
The **Unified Engineering Document Intelligence Platform** is a high-performance system designed to extract, link, and provide semantic search across all engineering documentation. By consolidating data from massive file stores into a unified intelligence layer, the platform enables rapid retrieval of critical engineering parameters and cross-document relationships.

- **Primary Goal:** Unified system to extract, link, and search all engineering documents.
- **Database:** Single **Neon PostgreSQL** instance.
- **Data Scale:** 
    - Total Files: **~819K** (tracked in `CloudFiles`)
    - PDF Drawings: **~191K**
- **Core Technologies:**
    - **CAD Extraction:** CreoToolkit (existing integration)
    - **PDF/DXF Extraction:** PyMuPDF + ezdxf
    - **Storage:** Backblaze B2 (via `EmjacDB` bucket)

## Implementation Phases

### Phase A: Auto-Linking
**Goal:** Establish logical connections between related engineering files to form `DocumentGroups`.
- **Duration:** 2-3 hours
- **Linking Strategies:**
    | Strategy | Confidence | Description |
    |----------|------------|-------------|
    | Exact Basename | 0.95 | Files sharing the same root filename (e.g., `.pdf`, `.dxf`, `.prt`) |
    | Folder Siblings | 0.80 | Files co-located in the same project directory |
    | Project Code | 0.70 | Regex extraction of project/job codes from filenames |
- **Execution Scripts:** `A1-migrate-schema.py` through `A6-generate-link-report.py`

### Phase B: PDF/DXF Extraction
**Goal:** Deep inspection and metadata extraction from vectorized engineering drawings.
- **Duration:** 6-8 hours
- **Extraction Scope:**
    - **PDF:** Tables, dimensions, text, material specifications.
    - **DXF:** Layers, blocks, entities, dimensional metadata.
- **Performance:** 50 parallel workers processing ~191K files.
- **Execution Scripts:** `B1-init-jobs.py` through `B7-extraction-summary.py`

### Phase C: Search API
**Goal:** Provide specialized endpoints for querying the unified intelligence layer.
- **Duration:** 4-6 hours
- **Query Types:**
    - Dimensions & Tolerances
    - Engineering Parameters
    - Material Properties
    - Project/Job Associations
    - Bill of Materials (BOM)
    - Full-text Search
- **Response Format:** Returns `DocumentGroups` containing all linked source files and metadata.
- **Execution Scripts:** `C1-api-routes.py` through `C6-load-testing.py`

## Database Schema (NEW TABLES)

To support document intelligence, the following tables are introduced:

| Table | Purpose |
|-------|---------|
| `DocumentGroups` | Master record for a logical set of linked files |
| `DocumentGroupMembers` | Mapping between `CloudFiles` and `DocumentGroups` |
| `ExtractionJobs` | Tracking state of long-running extraction tasks |
| `ExtractedMetadata` | General metadata (author, version, date) |
| `ExtractedDimensions` | Quantitative engineering measurements |
| `ExtractedParameters` | Key-Value pairs (e.g., Weight, Finish, Pressure) |
| `ExtractedMaterials` | Material specifications and standards |
| `ExtractedBOMItems` | Component lists extracted from drawings |

## Integration with CreoToolkit
The platform seamlessly bridges physical CAD data with documentation:
- **Relational Linking:** Connects `DocumentGroups` to existing `cad_models` and `udf_definitions` tables.
- **Unified Indexing:** CAD parameters extracted via CreoToolkit are indexed into `ExtractedParameters` for cross-referenced searching.

## File Structure

The project is organized by implementation phase:

```text
260119-1400-unified-doc-intelligence/
├── phase-a-linking/      # Auto-linking scripts (A1-A6)
├── phase-b-extraction/   # Parallel extraction engine (B1-B7)
├── phase-c-search/       # Search API and endpoints (C1-C6)
├── output/               # Reports, logs, and verification data
└── README.md             # This file
```

## Execution Order

| Timeline | Activity |
|----------|----------|
| **Day 1 (AM)** | Phase A: Auto-Linking & Schema Setup |
| **Day 1 (PM)** | Phase B: Start PDF/DXF Batch Extraction |
| **Day 2 (AM)** | Phase B: Extraction Completion & Verification |
| **Day 2 (PM)** | Phase C: Search API Deployment & Integration |

---
*Unified Engineering Document Intelligence Platform - Implementation Plan v1.0*
