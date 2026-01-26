-- PostgreSQL Configuration for pgVector CAD Similarity Search
-- Add to postgresql.conf or include via ALTER DATABASE
-- Execute: psql -d pybase -f migrations/sql/postgresql_vector_config.sql

-- ============================================================================
-- MEMORY CONFIGURATION
-- ============================================================================

-- For a 16GB RAM server (adjust proportionally for your hardware)
ALTER SYSTEM SET shared_buffers = '4GB';           -- 25% of RAM
ALTER SYSTEM SET effective_cache_size = '12GB';     -- 75% of RAM
ALTER SYSTEM SET work_mem = '64MB';                 -- Per-operation memory
ALTER SYSTEM SET maintenance_work_mem = '2GB';      -- For index builds

-- ============================================================================
-- PARALLEL QUERY CONFIGURATION
-- ============================================================================

ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 8;
ALTER SYSTEM SET parallel_tuple_cost = 0.01;
ALTER SYSTEM SET parallel_setup_cost = 100.0;

-- ============================================================================
-- PGVECTOR-SPECIFIC SETTINGS
-- ============================================================================

-- HNSW index parameters (default session values)
-- Can be overridden per-query using SET LOCAL
ALTER DATABASE pybase SET hnsw.ef_search = 100;

-- IVFFlat index probe count
ALTER DATABASE pybase SET ivfflat.probes = 100;

-- ============================================================================
-- QUERY PLANNER TUNING
-- ============================================================================

-- Favor indexed plans for vector queries
ALTER SYSTEM SET enable_seqscan = on;   -- Keep on, planner decides
ALTER SYSTEM SET enable_bitmapscan = on;
ALTER SYSTEM SET random_page_cost = 1.1;  -- For SSD storage

-- ============================================================================
-- LOGGING AND MONITORING
-- ============================================================================

-- Log slow vector queries for optimization
ALTER SYSTEM SET log_min_duration_statement = 100;  -- Log queries >100ms
ALTER SYSTEM SET log_statement = 'none';  -- Don't log query content (privacy)

-- Enable auto_explain for slow queries
LOAD 'auto_explain';
ALTER SYSTEM SET auto_explain.log_min_duration = 100;
ALTER SYSTEM SET auto_explain.log_analyze = true;
ALTER SYSTEM SET auto_explain.log_buffers = true;
ALTER SYSTEM SET auto_explain.log_timing = true;

-- ============================================================================
-- CONNECTION POOLING (for application-level config)
-- ============================================================================

-- Recommended pgBouncer settings for pgvector workloads:
-- pool_mode = transaction
-- max_client_conn = 1000
-- default_pool_size = 50
-- reserve_pool_size = 10
-- reserve_pool_timeout = 3s

-- ============================================================================
-- VACUUM AND MAINTENANCE
-- ============================================================================

-- Autovacuum tuning for vector tables
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = 0.05;
ALTER SYSTEM SET autovacuum_analyze_scale_factor = 0.02;

-- Custom autovacuum settings for cad_models table
ALTER TABLE cad_models SET (
    autovacuum_vacuum_scale_factor = 0.05,
    autovacuum_analyze_scale_factor = 0.02,
    autovacuum_vacuum_insert_scale_factor = 0.1
);

-- ============================================================================
-- APPLY CHANGES
-- ============================================================================

-- Reload configuration (requires superuser)
SELECT pg_reload_conf();

-- Verify settings
SELECT name, setting, unit, context
FROM pg_settings
WHERE name LIKE '%vector%' OR name LIKE '%work_mem%'
   OR name LIKE '%parallel%' OR name LIKE '%autovacuum%'
ORDER BY category, name;
