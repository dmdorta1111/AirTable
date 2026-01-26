#!/usr/bin/env python3
"""
CloudFiles Path Fix - Simple Direct Version

Fixes double slashes in CloudKey and LocalPath fields.
Y:// -> Y:/  and  // -> /
"""

import sys
from datetime import datetime
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    print("ERROR: psycopg not installed")
    sys.exit(1)

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "plans" / "reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

def normalize_path(path):
    """Convert double slashes to single slashes."""
    if not path:
        return path
    # Replace double slashes with single slashes
    while '//' in path:
        path = path.replace('//', '/')
    return path

print("=" * 70)
print("CloudFiles Path Normalization")
print("=" * 70)

print(f"\nConnecting to database...")

try:
    # Use autocommit for batch updates
    with psycopg.connect(db_url, row_factory=dict_row, autocommit=True) as conn:
        with conn.cursor() as cur:
            # Step 1: Count affected records
            print("\n1. Counting records with double slashes...")
            cur.execute("""
                SELECT COUNT(*) as count
                FROM "CloudFiles"
                WHERE "CloudKey" LIKE '%//%'
            """)
            cloudkey_count = cur.fetchone()['count']
            print(f"   CloudKey fields with //: {cloudkey_count:,}")

            cur.execute("""
                SELECT COUNT(*) as count
                FROM "CloudFiles"
                WHERE "LocalPath" LIKE '%//%'
            """)
            localpath_count = cur.fetchone()['count']
            print(f"   LocalPath fields with //: {localpath_count:,}")

            # Step 2: Sample before update
            print("\n2. Sample records before update:")
            cur.execute("""
                SELECT "ID", "CloudKey"
                FROM "CloudFiles"
                WHERE "CloudKey" LIKE '%//%'
                LIMIT 3
            """)
            for record in cur.fetchall():
                print(f"   ID {record['ID']}: {record['CloudKey'][:80]}...")

            # Step 3: Update CloudKey
            print(f"\n3. Updating CloudKey fields...")
            # Get all records with double slashes
            cur.execute("""
                SELECT "ID", "CloudKey"
                FROM "CloudFiles"
                WHERE "CloudKey" LIKE '%//%'
            """)

            updated_cloudkey = 0
            for record in cur:
                new_key = normalize_path(record['CloudKey'])
                if new_key != record['CloudKey']:
                    # Update using a new cursor
                    with conn.cursor() as update_cur:
                        update_cur.execute("""
                            UPDATE "CloudFiles"
                            SET "CloudKey" = %s
                            WHERE "ID" = %s
                        """, (new_key, record['ID']))
                    updated_cloudkey += 1

                if updated_cloudkey % 10000 == 0:
                    print(f"   Updated {updated_cloudkey:,} CloudKey records...")

            print(f"   Total CloudKey updates: {updated_cloudkey:,}")

            # Step 4: Update LocalPath
            print(f"\n4. Updating LocalPath fields...")
            cur.execute("""
                SELECT "ID", "LocalPath"
                FROM "CloudFiles"
                WHERE "LocalPath" LIKE '%//%'
                   AND "LocalPath" IS NOT NULL
            """)

            updated_localpath = 0
            for record in cur:
                new_path = normalize_path(record['LocalPath'])
                if new_path != record['LocalPath']:
                    # Update using a new cursor
                    with conn.cursor() as update_cur:
                        update_cur.execute("""
                            UPDATE "CloudFiles"
                            SET "LocalPath" = %s
                            WHERE "ID" = %s
                        """, (new_path, record['ID']))
                    updated_localpath += 1

                if updated_localpath % 10000 == 0:
                    print(f"   Updated {updated_localpath:,} LocalPath records...")

            print(f"   Total LocalPath updates: {updated_localpath:,}")

            # Step 5: Verify results
            print("\n5. Verifying results...")
            cur.execute("""
                SELECT COUNT(*) as count
                FROM "CloudFiles"
                WHERE "CloudKey" LIKE '%//%'
            """)
            remaining = cur.fetchone()['count']
            print(f"   Remaining CloudKey with //: {remaining:,}")

            cur.execute("""
                SELECT COUNT(*) as count
                FROM "CloudFiles"
                WHERE "LocalPath" LIKE '%//%'
            """)
            remaining = cur.fetchone()['count']
            print(f"   Remaining LocalPath with //: {remaining:,}")

            # Step 6: Sample after update
            print("\n6. Sample records after update:")
            cur.execute("""
                SELECT "ID", "CloudKey"
                FROM "CloudFiles"
                WHERE "CloudKey" LIKE 'Y:/%'
                LIMIT 3
            """)
            for record in cur.fetchall():
                print(f"   ID {record['ID']}: {record['CloudKey'][:80]}...")

            print("\n" + "=" * 70)
            print("UPDATE COMPLETE")
            print("=" * 70)
            print(f"Updated {updated_cloudkey:,} CloudKey fields")
            print(f"Updated {updated_localpath:,} LocalPath fields")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
