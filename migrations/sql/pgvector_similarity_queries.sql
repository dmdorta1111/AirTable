-- pgVector Similarity Search Queries for PyBase CAD Models
-- Based on CosCAD optimization recommendations
-- Execute: psql -d pybase -f migrations/sql/pgvector_similarity_queries.sql

-- ============================================================================
-- QUERY TEMPLATES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Template 1: Multi-Modal Similarity Search with Filtering
-- ----------------------------------------------------------------------------
-- Primary search using SDF latents with material/feature pre-filtering
-- Parameters: :query_vector (VECTOR), :min_similarity (FLOAT), :material (TEXT)
-- ----------------------------------------------------------------------------
\prompt 'Enter query vector as array [e.g., "{0.1,0.2,...}"]: ' query_vector
\prompt 'Enter minimum similarity (0-1, default 0.7): ' min_similarity
\prompt 'Enter material filter (optional, press Enter to skip): ' material_filter

WITH similarity_search AS (
    SELECT
        model_id,
        1 - (sdf_latent <=> :'query_vector'::vector) as shape_similarity,
        ROW_NUMBER() OVER (ORDER BY sdf_latent <=> :'query_vector'::vector) as shape_rank
    FROM cad_models
    WHERE :'material_filter' IS NULL OR material = :'material_filter'::text
    ORDER BY sdf_latent <=> :'query_vector'::vector
    LIMIT 1000
),
filtered AS (
    SELECT *
    FROM similarity_search
    WHERE shape_similarity > COALESCE(:'min_similarity'::float, 0.7)
),
reranked AS (
    SELECT
        f.*,
        cm.part_family,
        cm.material,
        cm.mass_kg,
        0.7 * shape_similarity +
        0.3 * COALESCE((1 - (cm.brep_graph_embedding <=> :'query_vector'::vector)), 0.5) as composite_score
    FROM filtered f
    JOIN cad_models cm USING (model_id)
)
SELECT
    model_id,
    part_family,
    material,
    mass_kg,
    shape_similarity,
    composite_score,
    shape_rank
FROM reranked
ORDER BY composite_score DESC
LIMIT 20;


-- ----------------------------------------------------------------------------
-- Template 2: Assembly-Aware Similarity Search
-- ----------------------------------------------------------------------------
-- Find similar assemblies considering component relationships
-- ----------------------------------------------------------------------------
WITH component_similarity AS (
    SELECT
        a.assembly_id,
        c.model_id as component_id,
        1 - (c.sdf_latent <=> $1::vector) as component_sim
    FROM assembly_hierarchy a
    JOIN cad_models c ON a.component_id = c.model_id
    WHERE c.sdf_latent IS NOT NULL
),
assembly_aggregate AS (
    SELECT
        assembly_id,
        AVG(component_sim) as avg_component_similarity,
        COUNT(*) as component_count,
        SUM(CASE WHEN component_sim > 0.8 THEN 1 ELSE 0 END) as high_sim_count
    FROM component_similarity
    GROUP BY assembly_id
    HAVING COUNT(*) BETWEEN $2 AND $3  -- min_components, max_components
),
topology_match AS (
    SELECT
        a.*,
        CASE
            WHEN cm.brep_graph_embedding IS NOT NULL
            THEN 1 - (cm.brep_graph_embedding <=> $4::vector)
            ELSE 0.5
        END as topology_similarity
    FROM assembly_aggregate a
    JOIN cad_models cm ON a.assembly_id = cm.model_id
)
SELECT
    *,
    0.4 * avg_component_similarity +
    0.4 * topology_similarity +
    0.2 * (high_sim_count::float / component_count) as assembly_score
FROM topology_match
ORDER BY assembly_score DESC
LIMIT 20;
-- Parameters: $1=component_vector, $2=min_components, $3=max_components, $4=topology_vector


-- ----------------------------------------------------------------------------
-- Template 3: Hierarchical Multi-Stage Search (High Recall)
-- ----------------------------------------------------------------------------
-- Stage 1: Approximate search -> Stage 2: Re-rank -> Stage 3: Cross-modal verify
-- ----------------------------------------------------------------------------
WITH stage1 AS (
    -- Fast approximate search on filtered set
    SELECT
        model_id,
        1 - (sdf_latent <=> $1::vector) as similarity
    FROM manufacturing_parts_prefilter
    ORDER BY sdf_latent <=> $1::vector
    LIMIT 1000
),
stage2 AS (
    -- Re-rank with exact distance + metadata boost
    SELECT
        m.*,
        s.similarity *
        CASE WHEN m.material = $2::text THEN 1.2 ELSE 1.0 END *
        CASE WHEN m.mass_kg BETWEEN $3::float AND $4::float THEN 1.1 ELSE 1.0 END as boosted_score
    FROM cad_models m
    JOIN stage1 s ON m.model_id = s.model_id
    WHERE m.bounding_box && ST_3DMakeBox($5::float, $6::float, $7::float,
                                          $8::float, $9::float, $10::float)
),
stage3 AS (
    -- Cross-modal verification
    SELECT *,
        0.7 * boosted_score +
        0.3 * (1 - (brep_graph_embedding <=> $1::vector)) as final_score
    FROM stage2
)
SELECT *
FROM stage3
ORDER BY final_score DESC
LIMIT 20;


-- ----------------------------------------------------------------------------
-- Template 4: Adaptive EF Search (Dynamic precision)
-- ----------------------------------------------------------------------------
-- Adjusts ef_search based on query complexity
-- ----------------------------------------------------------------------------
PREPARE adaptive_search (vector, int, int) AS
SELECT
    model_id,
    1 - (sdf_latent <=> $1) as distance
FROM cad_models
ORDER BY sdf_latent <=> $1
LIMIT $2;

-- Set ef_search dynamically before execution
SET LOCAL hnsw.ef_search = 200;  -- For vague queries, high recall
EXECUTE adaptive_search($1, 100);

SET LOCAL hnsw.ef_search = 50;   -- For specific queries, faster
EXECUTE adaptive_search($1, 20);


-- ----------------------------------------------------------------------------
-- Template 5: Cross-Modal Text-to-CAD Search
-- ----------------------------------------------------------------------------
-- Search CAD models using text description via CLIP embeddings
-- ----------------------------------------------------------------------------
WITH text_search AS (
    SELECT
        model_id,
        1 - (clip_text_embedding <=> $1::vector) as text_similarity
    FROM cad_models
    WHERE clip_text_embedding IS NOT NULL
    ORDER BY clip_text_embedding <=> $1::vector
    LIMIT 500
),
shape_verify AS (
    SELECT
        t.model_id,
        t.text_similarity,
        1 - (cm.sdf_latent <=> COALESCE($2::vector, clip_text_embedding)) as shape_similarity
    FROM text_search t
    JOIN cad_models cm ON t.model_id = cm.model_id
)
SELECT
    model_id,
    text_similarity,
    shape_similarity,
    0.6 * text_similarity + 0.4 * shape_similarity as combined_score
FROM shape_verify
ORDER BY combined_score DESC
LIMIT 20;


-- ----------------------------------------------------------------------------
-- Template 6: Image-to-CAD Search (Sketch/Reference Image)
-- ----------------------------------------------------------------------------
-- Find CAD models similar to a reference image
-- ----------------------------------------------------------------------------
SELECT
    model_id,
    1 - (clip_image_embedding <=> $1::vector) as image_similarity,
    1 - (sdf_latent <=> COALESCE($2::vector, clip_image_embedding)) as shape_similarity,
    part_family,
    material
FROM cad_models
WHERE clip_image_embedding IS NOT NULL
ORDER BY
    0.7 * (1 - (clip_image_embedding <=> $1::vector)) +
    0.3 * (1 - (sdf_latent <=> COALESCE($2::vector, clip_image_embedding))) DESC
LIMIT 20;


-- ============================================================================
-- PARTITION FAMILY SEARCH (For scalability >500K parts)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Query routing function for family-specific searches
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION search_across_families(
    query_vector VECTOR(256),
    families TEXT[] DEFAULT NULL,
    result_limit INTEGER DEFAULT 100
) RETURNS TABLE(model_id UUID, similarity FLOAT) AS $$
DECLARE
    family TEXT;
    combined_results TEXT;
BEGIN
    IF families IS NULL THEN
        -- Search all families in parallel (requires family tables exist)
        RETURN QUERY EXECUTE '
            SELECT model_id, 1 - (sdf_latent <=> $1) as similarity
            FROM cad_models
            WHERE sdf_latent IS NOT NULL
            ORDER BY sdf_latent <=> $1
            LIMIT $2'
        USING query_vector, result_limit;
    ELSE
        -- Search specific families
        FOREACH family IN ARRAY families LOOP
            RETURN QUERY EXECUTE format(
                'SELECT model_id, 1 - (sdf_latent <=> $1) as similarity
                 FROM cad_models
                 WHERE part_family = %L AND sdf_latent IS NOT NULL
                 ORDER BY sdf_latent <=> $1
                 LIMIT %s',
                family, result_limit / array_length(families, 1)
            ) USING query_vector;
        END LOOP;
    END IF;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- MONITORING QUERIES
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Index health monitoring
-- ----------------------------------------------------------------------------
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_stat_user_indexes
WHERE indexname LIKE '%hnsw%' OR indexname LIKE '%ivf%'
ORDER BY idx_scan DESC;

-- Cache hit rate analysis
SELECT
    schemaname,
    indexname,
    sum(idx_blks_hit) as hits,
    sum(idx_blks_read) as reads,
    CASE
        WHEN sum(idx_blks_hit + idx_blks_read) = 0 THEN 0
        ELSE round(100.0 * sum(idx_blks_hit) / sum(idx_blks_hit + idx_blks_read), 2)
    END as hit_ratio_percent
FROM pg_statio_user_indexes
WHERE indexname LIKE '%hnsw%' OR indexname LIKE '%ivf%'
GROUP BY schemaname, indexname
ORDER BY hit_ratio_percent DESC NULLS LAST;

-- Query performance summary
SELECT
    query_type,
    AVG(execution_time_ms) as avg_time_ms,
    AVG(result_count) as avg_results,
    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::float / COUNT(*) as cache_hit_rate,
    COUNT(*) as total_queries
FROM vector_query_log
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY query_type
ORDER BY avg_time_ms DESC;


-- ============================================================================
-- MAINTENANCE COMMANDS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Refresh materialized view (run after new CAD models added)
-- ----------------------------------------------------------------------------
REFRESH MATERIALIZED VIEW CONCURRENTLY manufacturing_parts_prefilter;

-- ----------------------------------------------------------------------------
-- Reindex vector indexes (run during maintenance window)
-- ----------------------------------------------------------------------------
REINDEX INDEX CONCURRENTLY idx_cad_sdf_latent_hnsw;
REINDEX INDEX CONCURRENTLY idx_cad_brep_ivfflat;

-- ----------------------------------------------------------------------------
-- Update table statistics for query planner
-- ----------------------------------------------------------------------------
ANALYZE cad_models;

-- ----------------------------------------------------------------------------
-- Clean old cache entries (older than 30 days, low access count)
-- ----------------------------------------------------------------------------
DELETE FROM vector_search_cache
WHERE accessed_at < NOW() - INTERVAL '30 days'
   AND access_count < 5;


-- ============================================================================
-- EMERGENCY PERFORMANCE TUNING
-- ============================================================================
-- Uncomment and run these if queries slow down unexpectedly:

-- SET effective_cache_size = '12GB';
-- SET max_parallel_workers_per_gather = 4;
-- SET enable_seqscan = off;
-- SET enable_bitmapscan = off;
-- SET hnsw.ef_search = 200;  -- Increase for better recall
