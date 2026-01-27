#!/usr/bin/env python3
"""Create operation_logs table directly via SQLAlchemy."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

# Database connection from .env
import os
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DATABASE_URL", "postgresql://pybase:pybase@localhost:5432/pybase")

# Convert asyncpg URL to sync URL if needed
if "+asyncpg" in DB_URL:
    DB_URL = DB_URL.replace("+asyncpg", "")

def create_operation_logs_table():
    """Create operation_logs table if it doesn't exist."""

    engine = create_engine(DB_URL)

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
            return True

        print("Creating operation_logs table...")

        # Create the table
        conn.execute(text("""
            CREATE TABLE pybase.operation_logs (
                id VARCHAR NOT NULL PRIMARY KEY,
                user_id VARCHAR NOT NULL REFERENCES pybase.users(id) ON DELETE CASCADE,
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

        conn.commit()

        print("✓ Successfully created operation_logs table with indexes")
        return True

if __name__ == "__main__":
    try:
        create_operation_logs_table()
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
