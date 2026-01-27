#!/usr/bin/env python3
"""Verify operation_logs table exists."""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DB_URL = os.getenv("DATABASE_URL", "postgresql://pybase:pybase@localhost:5432/pybase")
if "+asyncpg" in DB_URL:
    DB_URL = DB_URL.replace("+asyncpg", "")

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
        print("✓ Table pybase.operation_logs exists")

        # Get table structure
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'pybase'
            AND table_name = 'operation_logs'
            ORDER BY ordinal_position
        """))

        print("\n  Columns:")
        for row in result:
            print(f"    - {row[0]}: {row[1]}")

        # Check indexes
        result = conn.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'pybase'
            AND tablename = 'operation_logs'
            ORDER BY indexname
        """))

        print("\n  Indexes:")
        for row in result:
            print(f"    - {row[0]}")

        print("\n✓ Verification complete!")
        exit(0)
    else:
        print("✗ Table pybase.operation_logs does NOT exist")
        exit(1)
