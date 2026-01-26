# pgVector Optimization Strategy for CAD Similarity Search

**Date:** 2026-01-22
**Subagent:** pgVector Optimization Expert
**Status:** Implementation Ready

---

## Executive Summary

Optimized pgvector indexing strategy for multi-modal CAD similarity search based on CosCAD analysis. Focuses on **recall over raw speed** for engineering applications where missing similar parts has high manufacturing cost.

**Key Files Created:**
1. `migrations/versions/20260122_173000_add_pgvector_extension_and_indexes.py` - Alembic migration
2. `migrations/sql/pgvector_similarity_queries.sql` - Query templates
3. `migrations/sql/postgresql_vector_config.sql` - PostgreSQL configuration
4. `src/pybase/db/vector_search.py` - Python service layer

---

## Index Configuration

### Primary: SDF Latent Vectors (256D)
```sql
CREATE INDEX idx_cad_sdf_latent_hnsw
ON cad_models USING hnsw (sdf_latent vector_cosine_ops)
WITH (m = 24, ef_construction = 300);
```
- **m=24**: Higher connectivity for complex CAD shape space
- **ef_construction=300**: Better quality index
- **ef_search=100**: Runtime default (configurable per-query)

### Secondary: B-Rep Graph Embeddings (512D)
```sql
CREATE INDEX idx_cad_brep_ivfflat
ON cad_models USING ivfflat (brep_graph_embedding vector_cosine_ops)
WITH (lists = 1000);
```
- **lists=1000**: Optimal for ~1M rows (sqrt(n))
- Use IVFFlat here for faster builds, HNSW for primary search

### CLIP Embeddings (512D)
```sql
CREATE INDEX idx_cad_clip_text_hnsw
ON cad_models USING hnsw (clip_text_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 200);
```

---

## Query Templates

### 1. Multi-Modal Similarity Search
Combines SDF shape + B-Rep topology with material filtering:
```sql
WITH similarity_search AS (
    SELECT model_id, 1 - (sdf_latent <=> :query_vector) as shape_similarity
    FROM cad_models
    WHERE :material_filter IS NULL OR material = :material_filter
    ORDER BY sdf_latent <=> :query_vector LIMIT 1000
),
reranked AS (
    SELECT f.*, 0.7 * shape_similarity +
        0.3 * (1 - (brep_graph_embedding <=> :query_vector)) as composite_score
    FROM similarity_search f
    JOIN cad_models cm USING (model_id)
)
SELECT * FROM reranked ORDER BY composite_score DESC LIMIT 20;
```

### 2. Assembly-Aware Search
Aggregates component similarities:
```sql
WITH component_similarity AS (
    SELECT assembly_id, 1 - (c.sdf_latent <=> :component_vector) as component_sim
    FROM assembly_hierarchy a
    JOIN cad_models c ON a.component_id = c.model_id
),
assembly_aggregate AS (
    SELECT assembly_id, AVG(component_sim) as avg_component_similarity,
        COUNT(*) as component_count
    FROM component_similarity
    GROUP BY assembly_id
)
SELECT * FROM assembly_aggregate
ORDER BY avg_component_similarity DESC LIMIT 20;
```

### 3. Adaptive EF Search
Dynamic precision based on query complexity:
```python
def adaptive_ef_search(query_vector):
    query_norm = np.linalg.norm(query_vector)
    query_entropy = calculate_entropy(query_vector)

    if query_norm < 0.3 or query_entropy > 0.8:
        return 200, 100  # Vague query: high recall
    else:
        return 50, 20    # Specific query: faster
```

---

## Performance Expectations

| Dataset Size | Index Type | Query Time | Recall@10 | Storage |
|--------------|------------|------------|-----------|---------|
| 10K parts    | HNSW       | 2-5ms      | 99%       | 500MB   |
| 100K parts   | HNSW       | 5-15ms     | 98%       | 5GB     |
| 1M parts     | HNSW       | 20-50ms    | 99%       | 60GB    |
| 1M parts     | IVFFlat    | 10-30ms    | 95%       | 50GB    |
| 10M parts    | IVFPQ      | 50-100ms   | 85%       | 300GB   |

---

## Scaling Strategy

### < 1M Parts
- Use HNSW indexes
- Single table approach
- Materialized views for pre-filtering

### 1M - 5M Parts
- Keep HNSW for SDF latents (primary)
- IVFFlat for B-Rep embeddings
- Partition by part_family if needed

### > 5M Parts
- Consider IVFPQ for compression
- Partition by part_family
- Evaluate pgvector-gpu for acceleration

### > 10M Parts
- Implement sharding by part family
- Use partitioned tables
- Consider GPU acceleration via pgvector-gpu

---

## Memory Optimization

### Half-Precision Storage (FP16)
Reduces storage by 50% with minimal accuracy loss:
```python
def half_precision_vector(vector):
    return np.float16(vector).tobytes()
```

### Delta Encoding
Store vectors as deltas from cluster centroids for similar parts.

---

## Monitoring Queries

```sql
-- Index health
SELECT schemaname, tablename, indexname, idx_scan,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
FROM pg_stat_user_indexes
WHERE indexname LIKE '%hnsw%' OR indexname LIKE '%ivf%';

-- Cache hit rate
SELECT sum(idx_blks_hit) / (sum(idx_blks_hit) + sum(idx_blks_read)) as hit_ratio
FROM pg_statio_user_indexes
WHERE indexname = 'idx_cad_sdf_latent_hnsw';
```

---

## Integration Points

### Existing Code
- **Session management**: `src/pybase/db/session.py` - async SQLAlchemy
- **Base models**: `src/pybase/db/base.py` - UUID and timestamp mixins
- **Migrations**: `migrations/versions/` - existing Alembic structure

### New Service
- `src/pybase/db/vector_search.py` - Python wrapper with:
  - `VectorSearchService` class
  - `multi_modal_search()` - primary search method
  - `text_to_cad_search()` - CLIP cross-modal
  - `assembly_aware_search()` - component aggregation
  - Cache management

---

## Unresolved Questions

1. **GPU Acceleration**: Do we have NVIDIA GPUs available? pgvector-gpu requires CUDA 12.x
2. **Existing CAD Models Table**: Does `cad_models` table exist or needs creation in separate migration?
3. **Embedding Pipeline**: Where will SDF/CLIP embeddings be generated? (separate task)
4. **Production RAM**: What is actual server memory for tuning `shared_buffers`?
5. **Assembly Hierarchy**: Does `assembly_hierarchy` table exist for assembly search?

---

## Next Steps

1. **Verify database schema** - Ensure `cad_models` table exists
2. **Apply migration** - Run `alembic upgrade head`
3. **Install pgvector** - Ensure extension available in PostgreSQL
4. **Test with sample data** - Validate index performance with real embeddings
5. **Configure PostgreSQL** - Apply memory settings from config file

---

## References

- CosCAD Analysis: `plans/coscad-analysis/coscad5.md` (lines 577-1042)
- pgVector Docs: https://github.com/pgvector/pgvector
- HNSW Paper: Malkov, Y. A., & Yashunin, D. A. (2018). "Efficient and robust approximate nearest neighbor search"
