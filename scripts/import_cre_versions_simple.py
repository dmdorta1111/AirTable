#!/usr/bin/env python3
"""
Simple import - one record at a time with fresh connections.
"""

import sys
import csv
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

# Find latest CSV
reports_dir = Path(__file__).parent.parent / "plans" / "reports"
csv_files = sorted(reports_dir.glob("creo-versions-*.csv"), reverse=True)
csv_file = csv_files[0]

print("=" * 70)
print("SIMPLE IMPORT OF VERSIONED CREO FILES")
print("=" * 70)
print(f"\nUsing CSV: {csv_file}")

# Read CSV
print("\n1. Reading CSV...")
versioned_files = []
with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        path = row['Path']
        # Extract version number from path (e.g., .prt.24 -> 24)
        version = int(row['Version'])
        versioned_files.append({
            'path': path,
            'size': int(row['Size']),
            'version': version
        })

print(f"   Loaded {len(versioned_files):,} files")

# Import one by one with fresh connection per batch
print("\n2. Importing...")
inserted = 0
skipped = 0
batch_size = 100

for start_idx in range(0, len(versioned_files), batch_size):
    batch = versioned_files[start_idx:start_idx + batch_size]

    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                for file_data in batch:
                    cloudkey = file_data['path']
                    size = file_data['size']
                    version = file_data['version']

                    # Check if exists
                    cur.execute('SELECT COUNT(*) FROM "CloudFiles" WHERE "CloudKey" = %s', (cloudkey,))
                    if cur.fetchone()[0] > 0:
                        skipped += 1
                        continue

                    # Insert with all required fields
                    cur.execute('''
                        INSERT INTO "CloudFiles" ("CloudKey", "LocalPath", "FileSize", "FileHash", "Version", "IsCurrent")
                        VALUES (%s, %s, %s, %s, %s, %s)
                    ''', (cloudkey, cloudkey, size, '', version, False))

                    inserted += 1

                conn.commit()

        if (start_idx + batch_size) % 1000 == 0:
            print(f"   Processed {start_idx + batch_size:,} / {len(versioned_files):,} - Inserted: {inserted:,}")

    except Exception as e:
        print(f"   ERROR at {start_idx}: {e}")

print(f"\n   Inserted: {inserted:,}")
print(f"   Skipped: {skipped:,}")

# Verify
print("\n3. Verifying...")
with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        cur.execute(r'''
            SELECT COUNT(*) FROM "CloudFiles"
            WHERE "CloudKey" ~ '\.prt\.[0-9]+$' OR "CloudKey" ~ '\.asm\.[0-9]+$'
        ''')
        total = cur.fetchone()[0]
        print(f"   Total versioned records in DB: {total:,}")

        cur.execute(r'''
            SELECT "ID", "CloudKey" FROM "CloudFiles"
            WHERE "CloudKey" ~ '\.prt\.[0-9]+$' OR "CloudKey" ~ '\.asm\.[0-9]+$'
            ORDER BY "ID" DESC
            LIMIT 5
        ''')
        print(f"\n   Sample records:")
        for r in cur.fetchall():
            print(f"     ID {r[0]}: {r[1][:70]}...")

print("\n" + "=" * 70)
print("IMPORT COMPLETE!")
print("=" * 70)
