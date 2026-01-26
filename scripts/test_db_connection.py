#!/usr/bin/env python3
"""
Quick test of database connection and CloudFiles table
"""

import sys
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    print("ERROR: psycopg not installed")
    sys.exit(1)

# Load config
config_file = Path(__file__).parent.parent / "unified-doc-intelligence-deploy" / "config.txt"
config = {}
with open(config_file) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            config[key.strip()] = value.strip()

db_url = config.get("NEON_DATABASE_URL")
print(f"Connecting to database...")

try:
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Test query
            cur.execute('SELECT COUNT(*) as total FROM "CloudFiles"')
            result = cur.fetchone()
            print("OK Connected successfully!")
            print(f"  Total CloudFiles records: {result['total']:,}")

            # Check for path issues
            cur.execute("""
                SELECT COUNT(*) as count
                FROM "CloudFiles"
                WHERE "CloudKey" LIKE '%//%'
            """)
            double_slash = cur.fetchone()['count']
            print(f"  Records with // in CloudKey: {double_slash:,}")

            cur.execute("""
                SELECT COUNT(*) as count
                FROM "CloudFiles"
                WHERE "CloudKey" LIKE '%\\\\%'
            """)
            backslash = cur.fetchone()['count']
            print(f"  Records with \\ in CloudKey: {backslash:,}")

            # Get sample
            cur.execute("""
                SELECT "ID", "CloudKey"
                FROM "CloudFiles"
                WHERE "CloudKey" LIKE '%//%' OR "CloudKey" LIKE '%\\\\%'
                LIMIT 5
            """)
            samples = cur.fetchall()

            print(f"\n  Sample problematic paths:")
            for s in samples:
                print(f"    ID {s['ID']}: {s['CloudKey'][:100]}...")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
