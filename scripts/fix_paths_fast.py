#!/usr/bin/env python3
"""
Fast CloudFiles path normalization using batch updates.
Processes records in ID chunks for maximum performance on Neon.
"""

import sys
from pathlib import Path

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg not installed")
    sys.exit(1)

from dotenv import load_dotenv
import os

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

def normalize_path(path: str) -> str:
    """Convert double slashes and backslashes to single forward slashes."""
    if not path:
        return path
    path = path.replace('\\', '/')
    while '//' in path:
        path = path.replace('//', '/')
    return path

print("=" * 70)
print("FAST CLOUDFILES PATH NORMALIZATION")
print("=" * 70)

# Step 1: Get max ID
print("\n1. Analyzing data...")
with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM "CloudFiles" WHERE "CloudKey" ~ \'[/]{2,}\'')
        count = cur.fetchone()[0]
        print(f"   Records with double slashes: {count:,}")

        cur.execute('SELECT MAX("ID") as max_id FROM "CloudFiles"')
        max_id = cur.fetchone()[0]
        print(f"   Max ID: {max_id:,}")

        if count == 0:
            print("   No updates needed!")
            sys.exit(0)

# Step 2: Process in chunks
print("\n2. Processing updates in chunks...")
chunk_size = 10000
total_updated = 0
offset = 0

while offset < max_id:
    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            # Fetch a chunk
            cur.execute('''
                SELECT "ID", "CloudKey"
                FROM "CloudFiles"
                WHERE "CloudKey" ~ '[/]{2,}'
                  AND "ID" >= %s AND "ID" < %s
                ORDER BY "ID"
                LIMIT %s
            ''', (offset, offset + chunk_size, chunk_size))

            records = cur.fetchall()
            if not records:
                offset += chunk_size
                continue

            # Build update batch
            updates = []
            for record_id, cloudkey in records:
                new_key = normalize_path(cloudkey)
                if new_key != cloudkey:
                    updates.append((new_key, record_id))

            # Batch update
            if updates:
                with conn.cursor() as update_cur:
                    update_cur.executemany('''
                        UPDATE "CloudFiles"
                        SET "CloudKey" = %s
                        WHERE "ID" = %s
                    ''', updates)
                total_updated += len(updates)
                print(f"   Updated {total_updated:,} records... (chunk {offset:,}-{offset+chunk_size:,})")

    offset += chunk_size

print(f"\n   Total updated: {total_updated:,}")

# Step 3: Verify
print("\n3. Verifying results...")
with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM "CloudFiles" WHERE "CloudKey" ~ \'[/]{2,}\'')
        remaining = cur.fetchone()[0]
        print(f"   Remaining with double slashes: {remaining:,}")

        cur.execute('SELECT "ID", "CloudKey" FROM "CloudFiles" WHERE "CloudKey" LIKE \'Y:/%\' LIMIT 3')
        print("\n   Sample paths:")
        for r in cur.fetchall():
            print(f"     ID {r[0]}: {r[1][:80]}...")

print("\n" + "=" * 70)
print("UPDATE COMPLETE!")
print("=" * 70)
