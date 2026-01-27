#!/usr/bin/env python3
"""Create operation_logs table without foreign key constraints.

The Neon database doesn't have users table yet, so we'll create the table
without the FK constraint and it can be added later after users table exists.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DB_URL = os.getenv("DATABASE_URL", "postgresql://pybase:pybase@localhost:5432/pybase")
if "+asyncpg" in DB_URL:
    DB_URL = DB_URL.replace("+asyncpg", "")

engine = create_engine(DB_URL)

def create_operation_logs_table():
    """Create operation_logs table."""

    with engine.connect() as conn:
        # Check if table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_tables
                WHERE schemaname = 'pybase'
                AND tablename = 'operation_logs'
            )
        """))
        exists = result.scalar()

        if exists:
            print("✓ Table operation_logs already exists")
            # Verify structure
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'pybase'
                AND table_name = 'operation_logs'
                ORDER BY ordinal_position
            """))
            print("\n  Current structure:")
            for row in result:
                print(f"    - {row[0]}: {row[1]} (nullable: {row[2]})")
            return True

        print("Creating operation_logs table...")

        # Create the table WITHOUT user FK for now (will be added when users table exists)
        conn.execute(text("""
            CREATE TABLE pybase.operation_logs (
                id VARCHAR NOT NULL PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                operation_type VARCHAR(50) NOT NULL,
                entity_type VARCHAR(50) NOT NULL,
                entity_id VARCHAR(255) NOT NULL,
                before_data TEXT,
                after_data TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
            )
        """))

        # Create indexes
        conn.execute(text("""
            CREATE INDEX ix_operation_logs_user ON pybase.operation_logs(user_id)
        """))
        conn.execute(text("""
            CREATE INDEX ix_operation_logs_user_created ON pybase.operation_logs(user_id, created_at)
        """))
        conn.execute(text("""
            CREATE INDEX ix_operation_logs_operation ON pybase.operation_logs(operation_type)
        """))
        conn.execute(text("""
            CREATE INDEX ix_operation_logs_entity ON pybase.operation_logs(entity_type, entity_id)
        """))

        # Add comment
        conn.execute(text("""
            COMMENT ON TABLE pybase.operation_logs IS 'Stores operation history for undo/redo functionality. Tracks operations for 24 hours.'
        """))

        conn.commit()

        print("✓ Successfully created operation_logs table with indexes")
        print("\n  Note: Foreign key to users table not created (users table doesn't exist yet)")
        print("        Run: ALTER TABLE pybase.operation_logs ADD CONSTRAINT fk_operation_logs_user")
        print("               FOREIGN KEY (user_id) REFERENCES pybase.users(id) ON DELETE CASCADE;")
        print("        after users table is created")
        return True

if __name__ == "__main__":
    try:
        create_operation_logs_table()
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
