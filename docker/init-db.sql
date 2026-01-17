-- =============================================================================
-- PostgreSQL Initialization Script for PyBase
-- =============================================================================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search/fuzzy matching

-- Create test database (for running tests)
CREATE DATABASE pybase_test;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE pybase TO pybase;
GRANT ALL PRIVILEGES ON DATABASE pybase_test TO pybase;
