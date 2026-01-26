#!/usr/bin/env python3
"""
Verify all CloudFiles in Neon database against B2 bucket.
Ensures every file path in the database exists in B2.
"""

import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    print("ERROR: psycopg not installed")
    sys.exit(1)

try:
    from b2sdk.v2 import B2Api, InMemoryAccountInfo
except ImportError:
    print("ERROR: b2sdk not installed")
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
key_id = config.get("B2_APPLICATION_KEY_ID")
app_key = config.get("B2_APPLICATION_KEY")
bucket_name = config.get("B2_BUCKET_NAME")

print("=" * 70)
print("B2 CLOUDFILES VERIFICATION")
print("=" * 70)

# Step 1: Connect to B2 and build file index
print("\n1. Connecting to B2 and building file index...")
info = InMemoryAccountInfo()
api = B2Api(info)
api.authorize_account("production", key_id, app_key)
bucket = api.get_bucket_by_name(bucket_name)

b2_files = set()
b2_file_sizes = {}

count = 0
for file_info, _ in bucket.ls(folder_to_list="", recursive=True):
    fname = file_info.file_name
    b2_files.add(fname)
    b2_file_sizes[fname] = file_info.size
    count += 1
    if count % 100000 == 0:
        print(f"   Scanned {count:,} files...")

print(f"   B2 total files: {len(b2_files):,}")

# Step 2: Check all database files
print("\n2. Verifying database files against B2...")
with psycopg.connect(db_url, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        # Get total count
        cur.execute('SELECT COUNT(*) as total FROM "CloudFiles"')
        total = cur.fetchone()["total"]
        print(f"   Database total files: {total:,}")

        # Check each file
        cur.execute("""
            SELECT "ID", "CloudKey", "FileSize"
            FROM "CloudFiles"
            WHERE "CloudKey" IS NOT NULL
        """)

        verified = 0
        missing = 0
        size_mismatch = 0
        missing_files = []
        mismatch_files = []

        for i, record in enumerate(cur):
            cloudkey = record["CloudKey"]
            filesize = record["FileSize"] or 0

            if cloudkey in b2_files:
                verified += 1
                # Check size
                if filesize != b2_file_sizes[cloudkey]:
                    size_mismatch += 1
                    if len(mismatch_files) < 50:
                        mismatch_files.append({
                            "id": record["ID"],
                            "cloudkey": cloudkey,
                            "db_size": filesize,
                            "b2_size": b2_file_sizes[cloudkey]
                        })
            else:
                missing += 1
                if len(missing_files) < 50:
                    missing_files.append({
                        "id": record["ID"],
                        "cloudkey": cloudkey,
                        "filesize": filesize
                    })

            if (i + 1) % 50000 == 0:
                print(f"   Verified {i + 1:,} / {total:,} files...")

# Step 3: Print summary
print("\n" + "=" * 70)
print("VERIFICATION SUMMARY")
print("=" * 70)
print(f"\nTotal DB files: {total:,}")
print(f"Verified in B2: {verified:,}")
print(f"Missing in B2: {missing:,}")
print(f"Size mismatches: {size_mismatch:,}")

if missing_files:
    print(f"\nSample missing files (first 20):")
    for i, f in enumerate(missing_files[:20], 1):
        print(f"  {i}. ID={f['id']}: {f['cloudkey'][:80]}...")

if mismatch_files:
    print(f"\nSample size mismatches (first 10):")
    for i, f in enumerate(mismatch_files[:10], 1):
        print(f"  {i}. ID={f['id']}: {f['cloudkey'][:60]}... DB:{f['db_size']} B2:{f['b2_size']}")

print("\n" + "=" * 70)
