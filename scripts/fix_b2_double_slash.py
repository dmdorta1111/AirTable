#!/usr/bin/env python3
"""
Fix double-slash paths in B2 by renaming files.
Y:// -> Y:/  and  S:// -> S:/
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime

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

print("=" * 70)
print("B2 DOUBLE-SLASH PATH FIX")
print("=" * 70)

# Connect to B2
print("\n1. Connecting to B2...")
info = InMemoryAccountInfo()
api = B2Api(info)
api.authorize_account("production", key_id, app_key)
bucket = api.get_bucket_by_name(bucket_name)
print(f"   Connected to bucket: {bucket_name}")

# Scan for files needing rename
print("\n2. Scanning for double-slash files...")
y_double = []
s_double = []

for file_info, _ in bucket.ls(folder_to_list="", recursive=True):
    fname = file_info.file_name
    if fname.startswith("Y://"):
        y_double.append(fname)
    elif fname.startswith("S://"):
        s_double.append(fname)

    # Progress
    total = len(y_double) + len(s_double)
    if total % 10000 == 0 and total > 0:
        print(f"   Found {total:,} files so far...")

print(f"\n   Y:// files: {len(y_double):,}")
print(f"   S:// files: {len(s_double):,}")
print(f"   Total to rename: {len(y_double) + len(s_double):,}")

if len(y_double) + len(s_double) == 0:
    print("\n   No files need renaming!")
    sys.exit(0)

# Auto-confirm (remove this block for manual confirmation)
print(f"\n   Proceeding to rename {len(y_double) + len(s_double):,} files in B2...")

# Rename files
print("\n3. Renaming files...")
total_renamed = 0
errors = []

for old_name in y_double + s_double:
    new_name = old_name.replace("Y://", "Y:/").replace("S://", "S:/")
    if new_name == old_name:
        continue

    try:
        # Get file info
        old_file = bucket.get_file_info_by_name(old_name)

        # Check if target already exists
        try:
            existing = bucket.get_file_info_by_name(new_name)
            print(f"   SKIP: Target exists: {new_name[:60]}...")
            # Delete old (keep new)
            bucket.delete_file_version(old_file.id_, old_name)
            total_renamed += 1
            continue
        except:
            pass  # Target doesn't exist, proceed with rename

        # Download to temp and upload as new name
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            bucket.download_file_by_id(old_file.id_, tmp_path)

            new_file = bucket.upload_local_file(
                local_file=tmp_path,
                file_name=new_name,
                content_type=old_file.content_type,
            )

            bucket.delete_file_version(old_file.id_, old_name)

            total_renamed += 1
            if total_renamed % 100 == 0:
                print(f"   Renamed {total_renamed:,} files...")

        except Exception as e:
            errors.append((old_name, str(e)))
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        errors.append((old_name, str(e)))

# Verify
print("\n4. Verifying results...")
y_double_after = 0
s_double_after = 0

for file_info, _ in bucket.ls(folder_to_list="", recursive=True):
    fname = file_info.file_name
    if fname.startswith("Y://"):
        y_double_after += 1
    elif fname.startswith("S://"):
        s_double_after += 1

print(f"   Y:// remaining: {y_double_after:,}")
print(f"   S:// remaining: {s_double_after:,}")
print(f"   Total renamed: {total_renamed:,}")

if errors:
    print(f"\n   Errors: {len(errors)}")
    for old_name, err in errors[:5]:
        print(f"     - {old_name[:50]}...: {err}")

print("\n" + "=" * 70)
print("B2 RENAME COMPLETE!")
print("=" * 70)
