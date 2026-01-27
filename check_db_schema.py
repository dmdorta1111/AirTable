#!/usr/bin/env python3
"""Check database schema."""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DB_URL = os.getenv("DATABASE_URL", "postgresql://pybase:pybase@localhost:5432/pybase")
if "+asyncpg" in DB_URL:
    DB_URL = DB_URL.replace("+asyncpg", "")

engine = create_engine(DB_URL)

with engine.connect() as conn:
    # Check all schemas
    result = conn.execute(text("""
        SELECT schema_name FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        ORDER BY schema_name
    """))
    print("=== Schemas ===")
    for row in result:
        print(f"  - {row[0]}")

    # Check for users table
    print("\n=== Searching for users table ===")
    result = conn.execute(text("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_name = 'users'
        ORDER BY table_schema
    """))
    for row in result:
        print(f"  - {row[0]}.{row[1]}")

    # Check all tables in public schema
    print("\n=== Tables in public schema ===")
    result = conn.execute(text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """))
    for row in result:
        print(f"  - {row[0]}")
