-- Create audit_logs table for comprehensive audit logging
-- This script creates the table directly without using Alembic

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS pybase.audit_logs (
    id VARCHAR PRIMARY KEY,
    -- Actor information
    user_id VARCHAR REFERENCES pybase.users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),
    -- Action details
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR,
    -- Table context
    table_id VARCHAR,
    -- Data changes
    old_value TEXT,
    new_value TEXT,
    -- Request context
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    request_id VARCHAR(255),
    -- Tamper-evident storage
    integrity_hash VARCHAR(64) NOT NULL,
    previous_log_hash VARCHAR(64),
    -- Additional context
    meta TEXT DEFAULT '{}',
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON pybase.audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_email ON pybase.audit_logs(user_email);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON pybase.audit_logs(action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_type ON pybase.audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_id ON pybase.audit_logs(resource_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_table_id ON pybase.audit_logs(table_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_request_id ON pybase.audit_logs(request_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_integrity_hash ON pybase.audit_logs(integrity_hash);

-- Create composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_action ON pybase.audit_logs(user_id, action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_table_action ON pybase.audit_logs(table_id, action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_resource ON pybase.audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON pybase.audit_logs(created_at);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON pybase.audit_logs TO current_user;
GRANT USAGE, SELECT ON SEQUENCE pybase.audit_logs_id_seq TO current_user;
