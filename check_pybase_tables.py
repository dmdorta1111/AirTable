#!/usr/bin/env python3
"""Check pybase schema tables."""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DB_URL = os.getenv("DATABASE_URL", "postgresql://pybase:pybase@localhost:5432/pybase")
if "+asyncpg" in DB_URL:
    DB_URL = DB_URL.replace("+asyncpg", "")

engine = create_engine(DB_URL)

with engine.connect() as conn:
    # Check all tables in pybase schema
    print("=== Tables in pybase schema ===")
    result = conn.execute(text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'pybase'
        ORDER BY table_name
    """))
    tables = [row[0] for row in result]
    if tables:
        for table in tables:
            print(f"  - {table}")
    else:
        print("  (No tables found)")

    # Check if alembic_version exists
    print("\n=== Checking alembic_version ===")
    try:
        result = conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'alembic'
            AND table_name = 'alembic_version'
        """))
        if result.fetchone():
            print("  ✓ alembic.alembic_version exists")
            result = conn.execute(text("SELECT version_num FROM alembic.alembic_version"))
            for row in result:
                print(f"    Current version: {row[0]}")
        else:
            print("  ✗ alembic.alembic_version does NOT exist")
    except Exception as e:
        print(f"  ✗ Error checking: {e}")

    # Check for users table more broadly
    print("\n=== Searching for any 'users' table ===")
    result = conn.execute(text("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_name LIKE '%user%'
        ORDER BY table_schema, table_name
    """))
    for row in result:
        print(f"  - {row[0]}.{row[1]}")
