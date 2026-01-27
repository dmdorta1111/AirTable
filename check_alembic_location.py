#!/usr/bin/env python3
"""Check alembic_version table location."""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DB_URL = os.getenv("DATABASE_URL", "postgresql://pybase:pybase@localhost:5432/pybase")
if "+asyncpg" in DB_URL:
    DB_URL = DB_URL.replace("+asyncpg", "")

engine = create_engine(DB_URL)

with engine.connect() as conn:
    # Find alembic_version table in any schema
    print("=== Finding alembic_version table ===")
    result = conn.execute(text("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_name = 'alembic_version'
        ORDER BY table_schema
    """))
    for row in result:
        print(f"  - {row[0]}.{row[1]}")

    # Check pybase.alembic_version contents
    print("\n=== pybase.alembic_version contents ===")
    try:
        result = conn.execute(text("SELECT * FROM pybase.alembic_version"))
        rows = result.fetchall()
        if rows:
            for row in rows:
                print(f"  {row}")
        else:
            print("  (empty)")
    except Exception as e:
        print(f"  Error: {e}")

    # Check public.alembic_version contents
    print("\n=== public.alembic_version contents ===")
    try:
        result = conn.execute(text("SELECT * FROM public.alembic_version"))
        rows = result.fetchall()
        if rows:
            for row in rows:
                print(f"  {row}")
        else:
            print("  (empty)")
    except Exception as e:
        print(f"  Table doesn't exist or error: {e}")
