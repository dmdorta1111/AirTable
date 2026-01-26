#!/usr/bin/env python3
"""
Scan B2 for versioned Creo files (.prt.*, .asm.*) and prepare for database.
These files have version numbers like .prt.1, .prt.2, .asm.1, .asm.2 etc.
"""

import sys
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

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

key_id = config.get("B2_APPLICATION_KEY_ID")
app_key = config.get("B2_APPLICATION_KEY")
bucket_name = config.get("B2_BUCKET_NAME")

# Output file
output_dir = Path(__file__).parent.parent / "plans" / "reports"
output_dir.mkdir(parents=True, exist_ok=True)
output_csv = output_dir / f"creo-versions-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"

print("=" * 70)
print("B2 CREO VERSIONED FILES SCAN")
print("=" * 70)

# Connect to B2
print("\n1. Connecting to B2...")
info = InMemoryAccountInfo()
api = B2Api(info)
api.authorize_account("production", key_id, app_key)
bucket = api.get_bucket_by_name(bucket_name)
print(f"   Connected to bucket: {bucket_name}")

# Scan for versioned files
print("\n2. Scanning for versioned Creo files...")
prt_files = []
asm_files = []
other_creo = []

count = 0
for file_info, _ in bucket.ls(folder_to_list="", recursive=True):
    fname = file_info.file_name
    count += 1

    # Check for versioned Creo files
    if '.prt.' in fname:
        parts = fname.rsplit('.prt.', 1)
        if len(parts) == 2 and parts[1].isdigit():
            prt_files.append({
                'path': fname,
                'base_name': parts[0] + '.prt',
                'version': int(parts[1]),
                'size': file_info.size,
                'id': file_info.id_
            })
    elif '.asm.' in fname:
        parts = fname.rsplit('.asm.', 1)
        if len(parts) == 2 and parts[1].isdigit():
            asm_files.append({
                'path': fname,
                'base_name': parts[0] + '.asm',
                'version': int(parts[1]),
                'size': file_info.size,
                'id': file_info.id_
            })

    # Progress
    if count % 100000 == 0:
        print(f"   Scanned {count:,} files... Found {len(prt_files):,} .prt.* and {len(asm_files):,} .asm.*")

print(f"\n   Total scanned: {count:,}")
print(f"   Versioned .prt.* files: {len(prt_files):,}")
print(f"   Versioned .asm.* files: {len(asm_files):,}")
print(f"   Total versioned Creo files: {len(prt_files) + len(asm_files):,}")

# Group by base name to find files with multiple versions
print("\n3. Analyzing version groups...")
prt_groups = defaultdict(list)
for f in prt_files:
    prt_groups[f['base_name']].append(f)

asm_groups = defaultdict(list)
for f in asm_files:
    asm_groups[f['base_name']].append(f)

multi_version_prt = {k: v for k, v in prt_groups.items() if len(v) > 1}
multi_version_asm = {k: v for k, v in asm_groups.items() if len(v) > 1}

print(f"   Unique .prt files: {len(prt_groups):,}")
print(f"   .prt files with multiple versions: {len(multi_version_prt):,}")
print(f"   Unique .asm files: {len(asm_groups):,}")
print(f"   .asm files with multiple versions: {len(multi_version_asm):,}")

# Sample multi-version files
if multi_version_prt:
    print(f"\n   Sample .prt with multiple versions:")
    for base, files in list(multi_version_prt.items())[:3]:
        versions = sorted([f['version'] for f in files])
        print(f"     {base}: versions {versions}")

if multi_version_asm:
    print(f"\n   Sample .asm with multiple versions:")
    for base, files in list(multi_version_asm.items())[:3]:
        versions = sorted([f['version'] for f in files])
        print(f"     {base}: versions {versions}")

# Write to CSV
print(f"\n4. Writing to CSV: {output_csv}")
with open(output_csv, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Type', 'BaseName', 'Version', 'Path', 'Size', 'B2_ID'])

    for file_data in prt_files:
        writer.writerow([
            'prt',
            file_data['base_name'],
            file_data['version'],
            file_data['path'],
            file_data['size'],
            file_data['id']
        ])

    for file_data in asm_files:
        writer.writerow([
            'asm',
            file_data['base_name'],
            file_data['version'],
            file_data['path'],
            file_data['size'],
            file_data['id']
        ])

print(f"   Wrote {len(prt_files) + len(asm_files):,} records to CSV")

print("\n" + "=" * 70)
print("SCAN COMPLETE!")
print("=" * 70)
print(f"\nCSV saved to: {output_csv}")
print("\nTo import these into the database, the CloudKey should use the versioned path.")
