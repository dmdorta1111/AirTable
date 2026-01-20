-- ============================================================================
-- Unified Engineering Document Intelligence Platform
-- Database Schema Migration
-- 
-- Target: Neon PostgreSQL 15+
-- Project: PyBase Document Intelligence Extension
-- Created: 2026-01-19
-- 
-- This migration creates the document intelligence layer for:
-- - Auto-linking related engineering files into DocumentGroups
-- - Parallel extraction of PDF/DXF metadata
-- - Searchable indexes for dimensions, parameters, materials, and BOMs
-- ============================================================================

BEGIN;

-- ============================================================================
-- EXTENSION REQUIREMENTS
-- ============================================================================
-- Ensure pg_trgm is available for text search indexes
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

-- Linking method used to create document groups
CREATE TYPE linking_method AS ENUM (
    'auto_filename',    -- Exact basename matching (confidence: 0.95)
    'auto_folder',      -- Folder siblings (confidence: 0.80)
    'auto_project',     -- Project code extraction (confidence: 0.70)
    'manual'            -- User-defined grouping
);

-- Role of a file within a document group
CREATE TYPE document_role AS ENUM (
    'source_cad',       -- Original CAD source file (Creo .prt, .asm)
    'drawing_pdf',      -- PDF drawing export
    'drawing_dxf',      -- DXF drawing export
    'udf'               -- User Defined Feature file
);

-- Source type for extracted metadata
CREATE TYPE extraction_source_type AS ENUM (
    'pdf',              -- PDF document
    'dxf',              -- AutoCAD DXF
    'creo_part',        -- Creo Parametric Part
    'creo_asm',         -- Creo Parametric Assembly
    'autocad'           -- AutoCAD DWG (future)
);

-- Status of extraction jobs
CREATE TYPE extraction_status AS ENUM (
    'pending',          -- Queued for processing
    'processing',       -- Currently being extracted
    'completed',        -- Successfully extracted
    'failed',           -- Extraction failed
    'skipped'           -- Skipped (e.g., unsupported format)
);

-- Types of dimensions extracted from drawings
CREATE TYPE dimension_type AS ENUM (
    'linear',           -- Linear measurement
    'angular',          -- Angle measurement
    'radial',           -- Radius
    'diameter',         -- Diameter
    'ordinate',         -- Ordinate dimension
    'arc_length',       -- Arc length
    'tolerance'         -- GD&T tolerance zone
);

-- Tolerance types for dimensions
CREATE TYPE tolerance_type AS ENUM (
    'symmetric',        -- +/- same value
    'asymmetric',       -- Different plus/minus values
    'limits',           -- Upper/lower limits
    'basic',            -- Basic dimension (no tolerance)
    'reference'         -- Reference dimension
);

-- ============================================================================
-- TABLE 1: DocumentGroups
-- Master linking table for related engineering files
-- ============================================================================

CREATE TABLE document_groups (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,
    
    -- Identity fields
    name VARCHAR(255) NOT NULL,
    project_code VARCHAR(100),          -- Extracted project/job code (e.g., "PRJ-2024-001")
    item_number VARCHAR(100),           -- Part/item number from filename
    description TEXT,                   -- User-provided or auto-generated description
    
    -- Linking metadata
    linking_method linking_method NOT NULL DEFAULT 'auto_filename',
    linking_confidence NUMERIC(3,2) NOT NULL DEFAULT 1.0 
        CHECK (linking_confidence >= 0.0 AND linking_confidence <= 1.0),
    needs_review BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for DocumentGroups
CREATE INDEX idx_document_groups_name ON document_groups(name);
CREATE INDEX idx_document_groups_project_code ON document_groups(project_code) 
    WHERE project_code IS NOT NULL;
CREATE INDEX idx_document_groups_item_number ON document_groups(item_number) 
    WHERE item_number IS NOT NULL;
CREATE INDEX idx_document_groups_needs_review ON document_groups(needs_review) 
    WHERE needs_review = TRUE;
CREATE INDEX idx_document_groups_created_at ON document_groups(created_at);

COMMENT ON TABLE document_groups IS 
    'Master table for logical groupings of related engineering files (PDFs, DXFs, CAD models)';
COMMENT ON COLUMN document_groups.linking_confidence IS 
    'Confidence score 0.0-1.0: auto_filename=0.95, auto_folder=0.80, auto_project=0.70, manual=1.0';
COMMENT ON COLUMN document_groups.needs_review IS 
    'Flag for groups requiring human verification (low confidence or conflicts)';

-- ============================================================================
-- TABLE 2: DocumentGroupMembers
-- Links files to document groups (supports CloudFiles, cad_models, udf_definitions)
-- ============================================================================

CREATE TABLE document_group_members (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,
    
    -- Parent group reference
    group_id BIGINT NOT NULL REFERENCES document_groups(id) ON DELETE CASCADE,
    
    -- Polymorphic file references (exactly one must be non-null)
    cloud_file_id INTEGER,              -- FK to CloudFiles.ID (INTEGER per existing schema)
    cad_model_id BIGINT,                -- FK to cad_models.id (BIGSERIAL)
    udf_definition_id BIGINT,           -- FK to udf_definitions.id (BIGSERIAL)
    
    -- Member metadata
    role document_role NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraint: exactly one FK must be non-null
    CONSTRAINT chk_single_reference CHECK (
        (CASE WHEN cloud_file_id IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN cad_model_id IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN udf_definition_id IS NOT NULL THEN 1 ELSE 0 END) = 1
    )
);

-- Indexes for DocumentGroupMembers
CREATE INDEX idx_dgm_group_id ON document_group_members(group_id);
CREATE INDEX idx_dgm_cloud_file_id ON document_group_members(cloud_file_id) 
    WHERE cloud_file_id IS NOT NULL;
CREATE INDEX idx_dgm_cad_model_id ON document_group_members(cad_model_id) 
    WHERE cad_model_id IS NOT NULL;
CREATE INDEX idx_dgm_udf_definition_id ON document_group_members(udf_definition_id) 
    WHERE udf_definition_id IS NOT NULL;
CREATE INDEX idx_dgm_role ON document_group_members(role);
CREATE UNIQUE INDEX idx_dgm_primary_per_group ON document_group_members(group_id) 
    WHERE is_primary = TRUE;

-- Prevent duplicate file memberships in same group
CREATE UNIQUE INDEX idx_dgm_unique_cloud_file ON document_group_members(group_id, cloud_file_id) 
    WHERE cloud_file_id IS NOT NULL;
CREATE UNIQUE INDEX idx_dgm_unique_cad_model ON document_group_members(group_id, cad_model_id) 
    WHERE cad_model_id IS NOT NULL;
CREATE UNIQUE INDEX idx_dgm_unique_udf ON document_group_members(group_id, udf_definition_id) 
    WHERE udf_definition_id IS NOT NULL;

COMMENT ON TABLE document_group_members IS 
    'Junction table linking CloudFiles, cad_models, or udf_definitions to DocumentGroups';
COMMENT ON COLUMN document_group_members.is_primary IS 
    'Marks the primary/source file in a group (one per group)';

-- ============================================================================
-- TABLE 3: ExtractedMetadata
-- Unified extraction tracking with raw JSONB storage
-- ============================================================================

CREATE TABLE extracted_metadata (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,
    
    -- Source references (one or none - supports both CloudFiles and CAD models)
    cloud_file_id INTEGER,              -- FK to CloudFiles.ID
    cad_model_id BIGINT,                -- FK to cad_models.id
    
    -- Source identification
    source_type extraction_source_type NOT NULL,
    
    -- Extraction tracking
    extraction_type VARCHAR(50) NOT NULL,   -- e.g., 'full', 'dimensions_only', 'tables_only'
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    extraction_status extraction_status NOT NULL DEFAULT 'pending',
    extraction_completeness NUMERIC(3,2)    -- 0.0-1.0 completeness score
        CHECK (extraction_completeness IS NULL OR 
               (extraction_completeness >= 0.0 AND extraction_completeness <= 1.0)),
    
    -- Raw extracted data
    raw_data JSONB,                      -- Full extraction output as JSON
    error TEXT,                          -- Error message if extraction failed
    worker_id VARCHAR(100),              -- ID of worker that processed this file
    
    -- Summary flags for quick filtering
    has_dimensions BOOLEAN DEFAULT FALSE,
    has_parameters BOOLEAN DEFAULT FALSE,
    has_bom BOOLEAN DEFAULT FALSE,
    has_feature_tree BOOLEAN DEFAULT FALSE,
    
    -- Summary counts for statistics
    dimension_count INTEGER DEFAULT 0,
    parameter_count INTEGER DEFAULT 0,
    feature_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraint: at least one FK should be set for actual extractions
    CONSTRAINT chk_metadata_source CHECK (
        cloud_file_id IS NOT NULL OR cad_model_id IS NOT NULL
    )
);

-- Indexes for ExtractedMetadata
CREATE INDEX idx_em_cloud_file_id ON extracted_metadata(cloud_file_id) 
    WHERE cloud_file_id IS NOT NULL;
CREATE INDEX idx_em_cad_model_id ON extracted_metadata(cad_model_id) 
    WHERE cad_model_id IS NOT NULL;
CREATE INDEX idx_em_source_type ON extracted_metadata(source_type);
CREATE INDEX idx_em_extraction_status ON extracted_metadata(extraction_status);
CREATE INDEX idx_em_extracted_at ON extracted_metadata(extracted_at);
CREATE INDEX idx_em_has_dimensions ON extracted_metadata(has_dimensions) 
    WHERE has_dimensions = TRUE;
CREATE INDEX idx_em_has_bom ON extracted_metadata(has_bom) 
    WHERE has_bom = TRUE;

-- JSONB index for raw data queries
CREATE INDEX idx_em_raw_data ON extracted_metadata USING GIN (raw_data jsonb_path_ops);

-- Unique constraint: one metadata record per source file
CREATE UNIQUE INDEX idx_em_unique_cloud_file ON extracted_metadata(cloud_file_id) 
    WHERE cloud_file_id IS NOT NULL;
CREATE UNIQUE INDEX idx_em_unique_cad_model ON extracted_metadata(cad_model_id) 
    WHERE cad_model_id IS NOT NULL;

COMMENT ON TABLE extracted_metadata IS 
    'Unified extraction tracking for all document types with raw JSONB storage';
COMMENT ON COLUMN extracted_metadata.raw_data IS 
    'Complete extraction output stored as JSONB for flexible querying';
COMMENT ON COLUMN extracted_metadata.extraction_completeness IS 
    'Quality score 0.0-1.0 indicating extraction coverage';

-- ============================================================================
-- TABLE 4: ExtractionJobs
-- Job queue for parallel extraction processing
-- ============================================================================

CREATE TABLE extraction_jobs (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,
    
    -- Source references
    cloud_file_id INTEGER,              -- FK to CloudFiles.ID
    cad_model_id BIGINT,                -- FK to cad_models.id
    
    -- Job configuration
    job_type VARCHAR(50) NOT NULL,      -- e.g., 'pdf_full', 'dxf_dimensions', 'cad_params'
    priority INTEGER NOT NULL DEFAULT 0, -- Higher = more urgent
    
    -- Job status
    status extraction_status NOT NULL DEFAULT 'pending',
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    
    -- Worker tracking
    worker_id VARCHAR(100),             -- ID of worker processing this job
    started_at TIMESTAMPTZ,             -- When processing began
    completed_at TIMESTAMPTZ,           -- When processing finished
    
    -- Error handling
    error TEXT,                         -- Error message if failed
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraint: exactly one FK must be non-null
    CONSTRAINT chk_job_source CHECK (
        (CASE WHEN cloud_file_id IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN cad_model_id IS NOT NULL THEN 1 ELSE 0 END) = 1
    )
);

-- Indexes for ExtractionJobs
CREATE INDEX idx_ej_status ON extraction_jobs(status);
CREATE INDEX idx_ej_priority ON extraction_jobs(priority DESC, created_at ASC) 
    WHERE status = 'pending';
CREATE INDEX idx_ej_cloud_file_id ON extraction_jobs(cloud_file_id) 
    WHERE cloud_file_id IS NOT NULL;
CREATE INDEX idx_ej_cad_model_id ON extraction_jobs(cad_model_id) 
    WHERE cad_model_id IS NOT NULL;
CREATE INDEX idx_ej_worker_id ON extraction_jobs(worker_id) 
    WHERE worker_id IS NOT NULL;
CREATE INDEX idx_ej_job_type ON extraction_jobs(job_type);
CREATE INDEX idx_ej_created_at ON extraction_jobs(created_at);

-- Index for finding retriable failed jobs
CREATE INDEX idx_ej_retriable ON extraction_jobs(retry_count, status) 
    WHERE status = 'failed' AND retry_count < max_retries;

COMMENT ON TABLE extraction_jobs IS 
    'Job queue for parallel extraction workers processing PDFs, DXFs, and CAD files';
COMMENT ON COLUMN extraction_jobs.priority IS 
    'Job priority (higher values processed first). Default: 0';

-- ============================================================================
-- TABLE 5: ExtractedDimensions
-- Searchable index of dimensional data from drawings
-- ============================================================================

CREATE TABLE extracted_dimensions (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,
    
    -- Parent references
    metadata_id BIGINT NOT NULL REFERENCES extracted_metadata(id) ON DELETE CASCADE,
    cloud_file_id INTEGER,              -- Denormalized FK for faster queries
    
    -- Dimension value
    value NUMERIC(15,6) NOT NULL,       -- Numeric value with high precision
    unit VARCHAR(20) NOT NULL DEFAULT 'mm',  -- Unit of measure
    
    -- Tolerance data
    tolerance_plus NUMERIC(10,6),       -- Upper tolerance (+)
    tolerance_minus NUMERIC(10,6),      -- Lower tolerance (-)
    tolerance_type tolerance_type,
    
    -- Dimension metadata
    label VARCHAR(255),                 -- Dimension label/callout
    dimension_type dimension_type NOT NULL DEFAULT 'linear',
    layer VARCHAR(100),                 -- DXF layer name
    feature_id VARCHAR(100),            -- Associated CAD feature ID
    source_page INTEGER,                -- Page number in PDF
    
    -- Position data (optional)
    position_x NUMERIC(15,6),
    position_y NUMERIC(15,6),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for ExtractedDimensions
CREATE INDEX idx_ed_metadata_id ON extracted_dimensions(metadata_id);
CREATE INDEX idx_ed_cloud_file_id ON extracted_dimensions(cloud_file_id) 
    WHERE cloud_file_id IS NOT NULL;
CREATE INDEX idx_ed_value ON extracted_dimensions(value);
CREATE INDEX idx_ed_value_unit ON extracted_dimensions(value, unit);
CREATE INDEX idx_ed_label ON extracted_dimensions(label) WHERE label IS NOT NULL;
CREATE INDEX idx_ed_label_trgm ON extracted_dimensions USING GIN (label gin_trgm_ops) 
    WHERE label IS NOT NULL;
CREATE INDEX idx_ed_dimension_type ON extracted_dimensions(dimension_type);
CREATE INDEX idx_ed_layer ON extracted_dimensions(layer) WHERE layer IS NOT NULL;

-- Range queries for dimension searches
CREATE INDEX idx_ed_value_range ON extracted_dimensions(value, tolerance_plus, tolerance_minus);

COMMENT ON TABLE extracted_dimensions IS 
    'Searchable index of dimensions extracted from PDF/DXF drawings';
COMMENT ON COLUMN extracted_dimensions.value IS 
    'Numeric dimension value with 6 decimal precision';
COMMENT ON COLUMN extracted_dimensions.tolerance_type IS 
    'Type of tolerance: symmetric, asymmetric, limits, basic, or reference';

-- ============================================================================
-- TABLE 6: ExtractedParameters
-- Searchable index of CAD parameters and key-value metadata
-- ============================================================================

CREATE TABLE extracted_parameters (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,
    
    -- Parent references
    metadata_id BIGINT NOT NULL REFERENCES extracted_metadata(id) ON DELETE CASCADE,
    cad_model_id BIGINT,                -- Denormalized FK for faster queries
    
    -- Parameter identity
    name VARCHAR(255) NOT NULL,         -- Parameter name
    value TEXT NOT NULL,                -- Parameter value as text
    value_numeric NUMERIC(20,8),        -- Numeric representation if applicable
    value_type VARCHAR(50) NOT NULL DEFAULT 'string',  -- 'string', 'number', 'boolean', 'date'
    
    -- Categorization
    category VARCHAR(100),              -- e.g., 'material', 'weight', 'finish', 'custom'
    is_designated BOOLEAN DEFAULT FALSE, -- Creo "designated" parameter flag
    units VARCHAR(50),                  -- Units if applicable
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for ExtractedParameters
CREATE INDEX idx_ep_metadata_id ON extracted_parameters(metadata_id);
CREATE INDEX idx_ep_cad_model_id ON extracted_parameters(cad_model_id) 
    WHERE cad_model_id IS NOT NULL;
CREATE INDEX idx_ep_name ON extracted_parameters(name);
CREATE INDEX idx_ep_name_lower ON extracted_parameters(LOWER(name));
CREATE INDEX idx_ep_name_trgm ON extracted_parameters USING GIN (name gin_trgm_ops);
CREATE INDEX idx_ep_value ON extracted_parameters(value);
CREATE INDEX idx_ep_value_trgm ON extracted_parameters USING GIN (value gin_trgm_ops);
CREATE INDEX idx_ep_value_numeric ON extracted_parameters(value_numeric) 
    WHERE value_numeric IS NOT NULL;
CREATE INDEX idx_ep_category ON extracted_parameters(category) WHERE category IS NOT NULL;
CREATE INDEX idx_ep_is_designated ON extracted_parameters(is_designated) 
    WHERE is_designated = TRUE;

-- Composite index for common parameter searches
CREATE INDEX idx_ep_name_value ON extracted_parameters(name, value);

COMMENT ON TABLE extracted_parameters IS 
    'Searchable index of CAD parameters and engineering key-value pairs';
COMMENT ON COLUMN extracted_parameters.is_designated IS 
    'Creo designated parameter flag - these are primary model parameters';
COMMENT ON COLUMN extracted_parameters.value_numeric IS 
    'Numeric representation for range queries (NULL for non-numeric values)';

-- ============================================================================
-- TABLE 7: ExtractedMaterials
-- Material specifications extracted from drawings and CAD
-- ============================================================================

CREATE TABLE extracted_materials (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,
    
    -- Parent references
    metadata_id BIGINT NOT NULL REFERENCES extracted_metadata(id) ON DELETE CASCADE,
    cloud_file_id INTEGER,              -- Denormalized FK for faster queries
    
    -- Material identification
    material_name VARCHAR(255) NOT NULL, -- Material name (e.g., "304 Stainless Steel")
    material_spec VARCHAR(255),         -- Specification (e.g., "ASTM A240")
    
    -- Material properties
    finish VARCHAR(100),                -- Surface finish specification
    thickness NUMERIC(10,4),            -- Material thickness
    thickness_unit VARCHAR(20) DEFAULT 'mm',
    
    -- Additional properties (stored as JSONB for flexibility)
    properties JSONB,                   -- Extended properties (density, hardness, etc.)
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for ExtractedMaterials
CREATE INDEX idx_emat_metadata_id ON extracted_materials(metadata_id);
CREATE INDEX idx_emat_cloud_file_id ON extracted_materials(cloud_file_id) 
    WHERE cloud_file_id IS NOT NULL;
CREATE INDEX idx_emat_material_name ON extracted_materials(material_name);
CREATE INDEX idx_emat_material_name_lower ON extracted_materials(LOWER(material_name));
CREATE INDEX idx_emat_material_name_trgm ON extracted_materials USING GIN (material_name gin_trgm_ops);
CREATE INDEX idx_emat_material_spec ON extracted_materials(material_spec) 
    WHERE material_spec IS NOT NULL;
CREATE INDEX idx_emat_finish ON extracted_materials(finish) WHERE finish IS NOT NULL;
CREATE INDEX idx_emat_properties ON extracted_materials USING GIN (properties jsonb_path_ops) 
    WHERE properties IS NOT NULL;

COMMENT ON TABLE extracted_materials IS 
    'Material specifications and properties extracted from engineering documents';
COMMENT ON COLUMN extracted_materials.properties IS 
    'Extended material properties as JSONB (density, hardness, yield strength, etc.)';

-- ============================================================================
-- TABLE 8: ExtractedBOMItems
-- Bill of Materials entries extracted from drawings
-- ============================================================================

CREATE TABLE extracted_bom_items (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,
    
    -- Parent reference
    metadata_id BIGINT NOT NULL REFERENCES extracted_metadata(id) ON DELETE CASCADE,
    
    -- BOM item data
    item_number VARCHAR(50),            -- Item/find number in BOM
    part_number VARCHAR(255) NOT NULL,  -- Part number
    description TEXT,                   -- Part description
    quantity NUMERIC(10,2) DEFAULT 1,   -- Quantity required
    
    -- Additional fields
    material VARCHAR(255),              -- Material specification
    source_table VARCHAR(100),          -- Name/ID of source BOM table
    
    -- Extended properties
    properties JSONB,                   -- Additional BOM columns as JSONB
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for ExtractedBOMItems
CREATE INDEX idx_ebom_metadata_id ON extracted_bom_items(metadata_id);
CREATE INDEX idx_ebom_part_number ON extracted_bom_items(part_number);
CREATE INDEX idx_ebom_part_number_lower ON extracted_bom_items(LOWER(part_number));
CREATE INDEX idx_ebom_part_number_trgm ON extracted_bom_items USING GIN (part_number gin_trgm_ops);
CREATE INDEX idx_ebom_item_number ON extracted_bom_items(item_number) 
    WHERE item_number IS NOT NULL;
CREATE INDEX idx_ebom_material ON extracted_bom_items(material) WHERE material IS NOT NULL;
CREATE INDEX idx_ebom_properties ON extracted_bom_items USING GIN (properties jsonb_path_ops) 
    WHERE properties IS NOT NULL;

COMMENT ON TABLE extracted_bom_items IS 
    'Bill of Materials entries extracted from engineering drawings';
COMMENT ON COLUMN extracted_bom_items.source_table IS 
    'Identifier of the BOM table in source document (for multi-BOM drawings)';

-- ============================================================================
-- ALTER STATEMENTS: Add columns to CloudFiles
-- Extend the existing CloudFiles table with extraction tracking
-- ============================================================================

-- Add extraction status column
ALTER TABLE "CloudFiles" 
ADD COLUMN IF NOT EXISTS extraction_status extraction_status DEFAULT 'pending';

-- Add document group reference
ALTER TABLE "CloudFiles" 
ADD COLUMN IF NOT EXISTS document_group_id BIGINT REFERENCES document_groups(id) ON DELETE SET NULL;

-- Add indexes for the new columns
CREATE INDEX IF NOT EXISTS idx_cloudfiles_extraction_status 
ON "CloudFiles"(extraction_status);

CREATE INDEX IF NOT EXISTS idx_cloudfiles_document_group_id 
ON "CloudFiles"(document_group_id) 
WHERE document_group_id IS NOT NULL;

COMMENT ON COLUMN "CloudFiles".extraction_status IS 
    'Current extraction status for this file';
COMMENT ON COLUMN "CloudFiles".document_group_id IS 
    'Reference to parent DocumentGroup (auto-linked or manually assigned)';

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to update timestamps automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at
CREATE TRIGGER trg_document_groups_updated_at
    BEFORE UPDATE ON document_groups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_extracted_metadata_updated_at
    BEFORE UPDATE ON extracted_metadata
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: Document groups with member counts
CREATE OR REPLACE VIEW v_document_groups_summary AS
SELECT 
    dg.id,
    dg.name,
    dg.project_code,
    dg.item_number,
    dg.linking_method,
    dg.linking_confidence,
    dg.needs_review,
    dg.created_at,
    COUNT(dgm.id) AS member_count,
    SUM(CASE WHEN dgm.role = 'drawing_pdf' THEN 1 ELSE 0 END) AS pdf_count,
    SUM(CASE WHEN dgm.role = 'drawing_dxf' THEN 1 ELSE 0 END) AS dxf_count,
    SUM(CASE WHEN dgm.role = 'source_cad' THEN 1 ELSE 0 END) AS cad_count
FROM document_groups dg
LEFT JOIN document_group_members dgm ON dg.id = dgm.group_id
GROUP BY dg.id;

COMMENT ON VIEW v_document_groups_summary IS 
    'Summary view of document groups with member counts by role';

-- View: Extraction job queue status
CREATE OR REPLACE VIEW v_extraction_queue_status AS
SELECT 
    status,
    job_type,
    COUNT(*) AS job_count,
    MIN(created_at) AS oldest_job,
    MAX(created_at) AS newest_job
FROM extraction_jobs
GROUP BY status, job_type
ORDER BY status, job_type;

COMMENT ON VIEW v_extraction_queue_status IS 
    'Summary of extraction job queue by status and type';

-- View: Extraction statistics by source type
CREATE OR REPLACE VIEW v_extraction_statistics AS
SELECT 
    source_type,
    extraction_status,
    COUNT(*) AS file_count,
    AVG(dimension_count) AS avg_dimensions,
    AVG(parameter_count) AS avg_parameters,
    SUM(CASE WHEN has_bom THEN 1 ELSE 0 END) AS files_with_bom
FROM extracted_metadata
GROUP BY source_type, extraction_status
ORDER BY source_type, extraction_status;

COMMENT ON VIEW v_extraction_statistics IS 
    'Extraction statistics aggregated by source type and status';

-- ============================================================================
-- GRANT STATEMENTS (adjust role names as needed)
-- ============================================================================

-- Grant usage on sequences (commented out - role may not exist)
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO pybase;

-- Grant table permissions (commented out - role may not exist)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pybase;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

COMMIT;

-- ============================================================================
-- POST-MIGRATION NOTES
-- ============================================================================
-- 
-- 1. Foreign Key Constraints:
--    - CloudFiles.ID is assumed to be INTEGER
--    - cad_models.id is assumed to be BIGSERIAL
--    - udf_definitions.id is assumed to be BIGSERIAL
--    
--    If these differ, update the FK column types accordingly.
--
-- 2. Index Maintenance:
--    Run ANALYZE after bulk data loads:
--    ANALYZE document_groups;
--    ANALYZE document_group_members;
--    ANALYZE extracted_metadata;
--    ANALYZE extraction_jobs;
--    ANALYZE extracted_dimensions;
--    ANALYZE extracted_parameters;
--    ANALYZE extracted_materials;
--    ANALYZE extracted_bom_items;
--
-- 3. Partitioning (Optional):
--    For large-scale deployments, consider partitioning:
--    - extracted_dimensions by created_at or cloud_file_id range
--    - extraction_jobs by status (list partitioning)
--
-- 4. Monitoring Queries:
--    -- Check extraction progress
--    SELECT extraction_status, COUNT(*) FROM extracted_metadata GROUP BY 1;
--    
--    -- Check job queue health
--    SELECT * FROM v_extraction_queue_status;
--    
--    -- Find stalled jobs
--    SELECT * FROM extraction_jobs 
--    WHERE status = 'processing' 
--    AND started_at < NOW() - INTERVAL '1 hour';
--
-- ============================================================================
