#!/usr/bin/env python3
"""
Import versioned Creo files (.prt.*, .asm.*) into CloudFiles database.
Reads from the CSV scan results and inserts/updates database records.
"""

import sys
import csv
from pathlib import Path
from datetime import datetime

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

# Find latest CSV
reports_dir = Path(__file__).parent.parent / "plans" / "reports"
csv_files = sorted(reports_dir.glob("creo-versions-*.csv"), reverse=True)

if not csv_files:
    print("ERROR: No creo-versions CSV file found")
    sys.exit(1)

csv_file = csv_files[0]
print(f"Using CSV: {csv_file}")

print("=" * 70)
print("IMPORT VERSIONED CREO FILES TO DATABASE")
print("=" * 70)

# Read CSV
print(f"\n1. Reading CSV file...")
versioned_files = []
with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        versioned_files.append({
            'type': row['Type'],
            'base_name': row['BaseName'],
            'version': int(row['Version']),
            'path': row['Path'],
            'size': int(row['Size']),
            'b2_id': row['B2_ID']
        })

print(f"   Loaded {len(versioned_files):,} versioned files")

# Analyze current database state
print("\n2. Analyzing current database...")
with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        # Check how many versioned paths already exist
        cur.execute(r"""
            SELECT COUNT(*) FROM "CloudFiles"
            WHERE "CloudKey" ~ '\.prt\.[0-9]+$' OR "CloudKey" ~ '\.asm\.[0-9]+$'
        """)
        existing_versioned = cur.fetchone()[0]
        print(f"   Existing versioned records in DB: {existing_versioned:,}")

        # Check how many non-versioned .prt/.asm exist
        cur.execute(r"""
            SELECT COUNT(*) FROM "CloudFiles"
            WHERE ("CloudKey" ~ '\.prt$' OR "CloudKey" ~ '\.asm$')
              AND "CloudKey" NOT LIKE '%.prt.%' AND "CloudKey" NOT LIKE '%.asm.%'
        """)
        non_versioned = cur.fetchone()[0]
        print(f"   Non-versioned .prt/.asm in DB: {non_versioned:,}")

# Import versioned files
print("\n3. Importing versioned files...")
inserted = 0
skipped = 0
errors = []

with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        # First, get all existing CloudKeys to avoid duplicate checks
        print("   Loading existing CloudKeys...")
        cur.execute('SELECT "CloudKey" FROM "CloudFiles"')
        existing_keys = set(row[0] for row in cur.fetchall())
        print(f"   Loaded {len(existing_keys):,} existing keys")

        # Now insert new ones
        batch_size = 500
        batch = []

        for i, file_data in enumerate(versioned_files):
            cloudkey = file_data['path']
            size = file_data['size']

            if cloudkey in existing_keys:
                skipped += 1
            else:
                batch.append((
                    cloudkey,        # CloudKey (versioned)
                    cloudkey,        # LocalPath (same as CloudKey)
                    size,            # FileSize
                    ''               # FileHash (empty string for now)
                ))

                if len(batch) >= batch_size:
                    try:
                        cur.executemany(r'''
                            INSERT INTO "CloudFiles" ("CloudKey", "LocalPath", "FileSize", "FileHash")
                            VALUES (%s, %s, %s, %s)
                        ''', batch)
                        conn.commit()
                        inserted += len(batch)
                        print(f"   Inserted {inserted:,} records...")
                        batch = []
                    except Exception as e:
                        print(f"   ERROR: {e}")
                        conn.rollback()
                        batch = []

            if (i + 1) % 10000 == 0:
                print(f"   Processed {i + 1:,} / {len(versioned_files):,} files...")

        # Final batch
        if batch:
            try:
                cur.executemany(r'''
                    INSERT INTO "CloudFiles" ("CloudKey", "LocalPath", "FileSize", "FileHash")
                    VALUES (%s, %s, %s, %s)
                ''', batch)
                conn.commit()
                inserted += len(batch)
                print(f"   Inserted {inserted:,} records (final batch)...")
            except Exception as e:
                print(f"   ERROR: {e}")
                conn.rollback()

print(f"\n   Inserted: {inserted:,}")
print(f"   Skipped (already exists): {skipped:,}")

# Verify
print("\n4. Verifying results...")
with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        cur.execute(r"""
            SELECT COUNT(*) FROM "CloudFiles"
            WHERE "CloudKey" ~ '\.prt\.[0-9]+$' OR "CloudKey" ~ '\.asm\.[0-9]+$'
        """)
        total_versioned = cur.fetchone()[0]
        print(f"   Total versioned records in DB: {total_versioned:,}")

        # Show sample
        cur.execute(r"""
            SELECT "ID", "CloudKey" FROM "CloudFiles"
            WHERE "CloudKey" ~ '\.prt\.[0-9]+$' OR "CloudKey" ~ '\.asm\.[0-9]+$'
            ORDER BY "ID" DESC
            LIMIT 5
        """)
        print(f"\n   Sample imported records:")
        for r in cur.fetchall():
            print(f"     ID {r[0]}: {r[1][:80]}...")

print("\n" + "=" * 70)
print("IMPORT COMPLETE!")
print("=" * 70)
