#!/usr/bin/env python3
"""Check Alembic version."""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DB_URL = os.getenv("DATABASE_URL", "postgresql://pybase:pybase@localhost:5432/pybase")
if "+asyncpg" in DB_URL:
    DB_URL = DB_URL.replace("+asyncpg", "")

engine = create_engine(DB_URL)

with engine.connect() as conn:
    # Check alembic_version table in pybase schema
    print("=== Checking alembic_version ===")
    try:
        result = conn.execute(text("""
            SELECT version_num FROM pybase.alembic_version
        """))
        versions = [row[0] for row in result]
        if versions:
            print(f"  Current version(s): {versions}")
        else:
            print("  No version found - database appears un-migrated!")
    except Exception as e:
        print(f"  Error: {e}")

    # Check if users table exists
    print("\n=== Checking for users table ===")
    try:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'pybase'
                AND table_name = 'users'
            )
        """))
        exists = result.scalar()
        print(f"  pybase.users exists: {exists}")
    except Exception as e:
        print(f"  Error: {e}")
