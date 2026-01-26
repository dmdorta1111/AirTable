# CAD Dual-Representation Schema Implementation Report

**Date:** 2026-01-22
**Subagent:** Database Schema Designer
**Status:** Complete

## Summary

Implemented PostgreSQL schema for dual-representation CAD storage (B-Rep + DeepSDF) based on CosCAD architecture. Uses pgvector for similarity search and supports assembly hierarchies.

## Files Created

### Migrations
1. `migrations/versions/20260122_173000_cad_models_dual_representation.py`
   - Main schema: `cad_models`, `cad_model_embeddings`, `cad_assembly_relations`, `cad_manufacturing_features`, `cad_rendered_views`
   - PostGIS spatial columns for bounding boxes
   - Materialized view `cad_model_search_index`
   - Standard btree/gin indexes

2. `migrations/versions/20260122_173010_cad_models_hnsw_indexes.py`
   - HNSW indexes for all embedding types
   - CosCAD-optimized parameters: m=16, ef_construction=100

### ORM Models
3. `src/pybase/models/cad_model.py`
   - `CADModel` - Main model with dual representation
   - `CADModelEmbedding` - Multimodal embeddings (B-Rep, CLIP, geometry, fused)
   - `CADAssemblyRelation` - Parent-child hierarchy with transforms
   - `CADManufacturingFeature` - Feature metadata
   - `CADRenderedView` - Pre-rendered views for image search

### Updated
4. `src/pybase/models/__init__.py` - Added CAD model exports

## Schema Design

### Dual Representation Storage

| Representation | Purpose | Storage Format |
|----------------|---------|----------------|
| B-Rep Genome | Parametric editing | JSONB + compressed BYTEA |
| DeepSDF Latent | Similarity search | FLOAT ARRAY(256) |
| Point Cloud | Rendering/analysis | JSONB + compressed BYTEA |

### Embedding Dimensions (aligned with CosCAD)

| Embedding | Dimensions | Index | Use Case |
|-----------|------------|-------|----------|
| B-Rep graph (UV-Net) | 512 | HNSW | Geometry similarity |
| CLIP text | 512 | HNSW | Text-to-CAD |
| CLIP image | 512 | HNSW | Image-to-CAD |
| Point cloud (PointNet++) | 1024 | HNSW | Shape similarity |
| Fused | 512 | HNSW | General queries |
| DeepSDF latent | 256 | HNSW | Implicit similarity |
| Rendered view | 512 | HNSW | Sketch-to-CAD |

### Key Features

1. **LSH Buckets**: 4 buckets for coarse filtering (Tri-Index optimization)
2. **PQ Codes**: Product quantization for compressed features
3. **PostGIS**: 3D bounding box and centroid for spatial queries
4. **Materialized View**: Pre-joined search index for fast queries
5. **Soft Delete**: Inherited from `SoftDeleteModel`

## Integration Points

### Existing Codebase

| Location | Purpose |
|----------|---------|
| `src/pybase/extraction/cad/` | Extract B-Rep from DXF/IFC/STEP |
| `src/pybase/models/workspace.py` | Workspace ownership |
| `src/pybase/models/user.py` | User ownership |
| `migrations/env.py` | Alembic configuration |

### Dependencies Required

```python
# Already in project
sqlalchemy[asyncio]
alembic

# Need to add
pgvector  # PostgreSQL vector extension
psycopg2-binary  # PostGIS support
```

## Migration Execution

```bash
# Apply schema
alembic upgrade head

# After populating embeddings, apply HNSW indexes
alembic upgrade +1
```

## Example Queries

### Text-to-CAD Search
```sql
SELECT cm.file_name, emb.clip_text_embedding <-> query_embedding AS distance
FROM pybase.cad_model_search_index cm
ORDER BY distance
LIMIT 10;
```

### Shape Similarity
```sql
SELECT cm.file_name, emb.brep_graph_embedding <-> query_embedding AS distance
FROM pybase.cad_models cm
JOIN pybase.cad_model_embeddings emb ON cm.id = emb.cad_model_id
WHERE cm.category_label = 'fastener'
ORDER BY distance
LIMIT 10;
```

### Assembly Hierarchy
```sql
WITH RECURSIVE assembly_tree AS (
    SELECT id, file_name, 0 AS level
    FROM pybase.cad_models
    WHERE id = $1
    UNION ALL
    SELECT cm.id, cm.file_name, at.level + 1
    FROM pybase.cad_models cm
    JOIN pybase.cad_assembly_relations ar ON ar.child_model_id = cm.id
    JOIN assembly_tree at ON ar.parent_model_id = at.id
)
SELECT * FROM assembly_tree;
```

## Unresolved Questions

1. **DeepSDF Training Pipeline**: Not implemented. Need to define:
   - Training data preparation
   - Model architecture (256-dim latent)
   - Export to numpy/pgvector format

2. **B-Rep Genome Format**: Need to standardize JSON schema for:
   - Feature tree structure
   - Face/edge topology
   - Parametric constraints

3. **Embedding Generation**: Not implemented. Need:
   - UV-Net or BC-NET for B-Rep graphs
   - CLIP integration for text/image
   - PointNet++ for point clouds

4. **LSH Bucket Assignment**: Algorithm not defined. Need:
   - Hash function selection
   - Bucket count configuration

5. **Storage Integration**: Backblaze B2/S3 configuration for rendered views

## Next Steps

1. Implement DeepSDF encoder service
2. Create B-Rep genome extraction from existing CAD parsers
3. Implement embedding generation pipeline
4. Add API endpoints for similarity search
5. Create frontend for CAD model browser
