#!/usr/bin/env python3
"""
B2 File Audit Script
Audits B2 bucket for:
1. Files with double slashes in path (Y://, S://, etc.)
2. Duplicate files (same FileHash)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

try:
    from b2sdk.v2 import B2Api, InMemoryAccountInfo
except ImportError:
    print("ERROR: b2sdk not installed. Run: pip install b2sdk")
    sys.exit(1)

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg")
    sys.exit(1)

# Output directory
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_config():
    """Load configuration from config.txt file."""
    config_file = Path(__file__).parent / "config.txt"
    if not config_file.exists():
        print(f"ERROR: Config file not found at {config_file}")
        sys.exit(1)

    config = {}
    with open(config_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    return config


def audit_neon_database(db_url):
    """Audit Neon PostgreSQL database for double slash and duplicate issues."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "double_slash": {
            "Y://": {"count": 0, "samples": []},
            "S://": {"count": 0, "samples": []},
            "OTHER://": {"count": 0, "samples": []}
        },
        "duplicates": {
            "by_file_hash": {"count": 0, "groups": []},
            "by_cloud_key": {"count": 0, "groups": []}
        },
        "total_files": 0,
        "unique_files": 0,
        "errors": []
    }

    print("Connecting to Neon database...")

    try:
        with psycopg.connect(db_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Get total count
                cur.execute('SELECT COUNT(*) as total FROM "CloudFiles"')
                results["total_files"] = cur.fetchone()["total"]
                print(f"  Total files: {results['total_files']}")

                # Check for double slashes in CloudKey
                print("\n  Checking for double slashes in CloudKey...")

                # Y:// pattern
                cur.execute("""
                    SELECT CloudKey, LocalPath, FileHash, FileSize
                    FROM "CloudFiles"
                    WHERE CloudKey LIKE 'Y://%%'
                    LIMIT 100
                """)
                y_slash = cur.fetchall()
                results["double_slash"]["Y://"]["count"] = len(y_slash)
                results["double_slash"]["Y://"]["samples"] = [
                    {
                        "CloudKey": r["cloudkey"],
                        "LocalPath": r["localpath"],
                        "FileHash": r["filehash"],
                        "FileSize": r["filesize"]
                    } for r in y_slash[:20]
                ]
                print(f"    Y:// : {len(y_slash)} files")

                # S:// pattern
                cur.execute("""
                    SELECT CloudKey, LocalPath, FileHash, FileSize
                    FROM "CloudFiles"
                    WHERE CloudKey LIKE 'S://%%'
                    LIMIT 100
                """)
                s_slash = cur.fetchall()
                results["double_slash"]["S://"]["count"] = len(s_slash)
                results["double_slash"]["S://"]["samples"] = [
                    {
                        "CloudKey": r["cloudkey"],
                        "LocalPath": r["localpath"],
                        "FileHash": r["filehash"],
                        "FileSize": r["filesize"]
                    } for r in s_slash[:20]
                ]
                print(f"    S:// : {len(s_slash)} files")

                # Other double slash patterns
                cur.execute("""
                    SELECT CloudKey, LocalPath, FileHash, FileSize
                    FROM "CloudFiles"
                    WHERE CloudKey ~ '^[A-Z]+://'
                      AND CloudKey NOT LIKE 'Y://%%'
                      AND CloudKey NOT LIKE 'S://%%'
                    """)
                other_slash = cur.fetchall()
                results["double_slash"]["OTHER://"]["count"] = len(other_slash)
                results["double_slash"]["OTHER://"]["samples"] = [
                    {
                        "CloudKey": r["cloudkey"],
                        "LocalPath": r["localpath"],
                        "FileHash": r["filehash"],
                        "FileSize": r["filesize"]
                    } for r in other_slash[:20]
                ]
                if other_slash:
                    print(f"    OTHER:// : {len(other_slash)} files")

                # Check for duplicates by FileHash
                print("\n  Checking for duplicates by FileHash...")
                cur.execute("""
                    SELECT FileHash, COUNT(*) as count,
                           array_agg(CloudKey) as keys,
                           array_agg(ID) as ids,
                           SUM(FileSize) as total_size
                    FROM "CloudFiles"
                    WHERE FileHash IS NOT NULL
                    GROUP BY FileHash
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC
                    LIMIT 50
                """)
                dup_hash = cur.fetchall()
                results["duplicates"]["by_file_hash"]["count"] = len(dup_hash)
                results["duplicates"]["by_file_hash"]["groups"] = [
                    {
                        "FileHash": r["filehash"],
                        "count": r["count"],
                        "total_size_bytes": r["total_size"],
                        "sample_ids": r["ids"][:10],
                        "sample_keys": r["keys"][:10]
                    } for r in dup_hash[:20]
                ]
                print(f"    Found {len(dup_hash)} duplicate groups by FileHash")
                if dup_hash:
                    print(f"    Top duplicate: {dup_hash[0]['filehash'][:16]}... ({dup_hash[0]['count']} copies)")

                # Check for duplicate CloudKeys
                print("\n  Checking for duplicate CloudKeys...")
                cur.execute("""
                    SELECT CloudKey, COUNT(*) as count,
                           array_agg(ID) as ids,
                           SUM(FileSize) as total_size
                    FROM "CloudFiles"
                    WHERE CloudKey IS NOT NULL
                    GROUP BY CloudKey
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC
                    LIMIT 50
                """)
                dup_key = cur.fetchall()
                results["duplicates"]["by_cloud_key"]["count"] = len(dup_key)
                results["duplicates"]["by_cloud_key"]["groups"] = [
                    {
                        "CloudKey": r["cloudkey"],
                        "count": r["count"],
                        "total_size_bytes": r["total_size"],
                        "sample_ids": r["ids"][:10]
                    } for r in dup_key[:20]
                ]
                print(f"    Found {len(dup_key)} duplicate CloudKeys")
                if dup_key:
                    print(f"    Top duplicate: {dup_key[0]['cloudkey'][:60]}... ({dup_key[0]['count']} copies)")

                # Get unique file count
                cur.execute('SELECT COUNT(DISTINCT FileHash) as unique FROM "CloudFiles" WHERE FileHash IS NOT NULL')
                results["unique_files"] = cur.fetchone()["unique"]
                print(f"\n  Unique files (by hash): {results['unique_files']}")

    except Exception as e:
        results["errors"].append(f"Database error: {e}")
        import traceback
        traceback.print_exc()

    return results


def audit_b2_bucket(b2_api, bucket_name, max_files=50000):
    """Audit B2 bucket directly for file patterns."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "bucket_name": bucket_name,
        "double_slash": {
            "Y://": {"count": 0, "samples": []},
            "S://": {"count": 0, "samples": []},
            "OTHER://": {"count": 0, "samples": []}
        },
        "total_files_scanned": 0,
        "errors": []
    }

    try:
        bucket = b2_api.get_bucket_by_name(bucket_name)
        print(f"\nAuditing B2 bucket: {bucket_name}")
    except Exception as e:
        results["errors"].append(f"Bucket error: {e}")
        return results

    print(f"Scanning files (max {max_files})...")
    file_count = 0

    try:
        for file_version, folder_name in bucket.ls(recursive=True):
            file_count += 1
            file_name = file_version.file_name
            results["total_files_scanned"] += 1

            # Check for double slash patterns
            if file_name.startswith("Y://"):
                results["double_slash"]["Y://"]["count"] += 1
                if len(results["double_slash"]["Y://"]["samples"]) < 20:
                    results["double_slash"]["Y://"]["samples"].append({
                        "path": file_name,
                        "size": file_version.size,
                        "id": file_version.id_
                    })
            elif file_name.startswith("S://"):
                results["double_slash"]["S://"]["count"] += 1
                if len(results["double_slash"]["S://"]["samples"]) < 20:
                    results["double_slash"]["S://"]["samples"].append({
                        "path": file_name,
                        "size": file_version.size,
                        "id": file_version.id_
                    })
            elif "://" in file_name[:10]:
                # Other double slash patterns (catch all)
                prefix = file_name.split("://")[0] + "://"
                if prefix not in results["double_slash"]:
                    results["double_slash"][prefix] = {"count": 0, "samples": []}
                results["double_slash"][prefix]["count"] += 1
                if len(results["double_slash"][prefix]["samples"]) < 5:
                    results["double_slash"][prefix]["samples"].append({
                        "path": file_name,
                        "size": file_version.size
                    })

            # Progress update
            if file_count % 5000 == 0:
                y_count = results["double_slash"]["Y://"]["count"]
                s_count = results["double_slash"]["S://"]["count"]
                print(f"  Scanned {file_count} files, Y://={y_count}, S://={s_count}...")

            if file_count >= max_files:
                print(f"  Reached max file limit ({max_files})")
                break

    except Exception as e:
        results["errors"].append(f"Scan error: {e}")

    return results


def main():
    print("=" * 70)
    print("B2 FILE AUDIT - DOUBLE SLASH & DUPLICATES")
    print("=" * 70)

    config = load_config()

    db_url = config.get("NEON_DATABASE_URL")
    key_id = config.get("B2_APPLICATION_KEY_ID")
    app_key = config.get("B2_APPLICATION_KEY")
    bucket_name = config.get("B2_BUCKET_NAME")

    if not all([db_url, key_id, app_key, bucket_name]):
        print("ERROR: Missing configuration in config.txt")
        sys.exit(1)

    all_results = {
        "timestamp": datetime.now().isoformat(),
        "database_audit": None,
        "b2_audit": None
    }

    # Audit Neon Database
    print("\n" + "=" * 70)
    print("STEP 1: AUDIT NEON DATABASE")
    print("=" * 70)
    db_results = audit_neon_database(db_url)
    all_results["database_audit"] = db_results

    # Audit B2 Bucket
    print("\n" + "=" * 70)
    print("STEP 2: AUDIT B2 BUCKET")
    print("=" * 70)
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", key_id, app_key)
        print("Authenticated successfully!")

        b2_results = audit_b2_bucket(b2_api, bucket_name, max_files=100000)
        all_results["b2_audit"] = b2_results

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    # Save results
    output_file = OUTPUT_DIR / f"b2-audit-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("AUDIT SUMMARY")
    print("=" * 70)

    if all_results["database_audit"]:
        db = all_results["database_audit"]
        print(f"\nNEON DATABASE:")
        print(f"  Total files: {db['total_files']:,}")
        print(f"  Unique files (by hash): {db['unique_files']:,}")
        print(f"\n  DOUBLE SLASH ISSUES:")
        print(f"    Y://  : {db['double_slash']['Y://']['count']:,} files")
        print(f"    S://  : {db['double_slash']['S://']['count']:,} files")
        if db['double_slash']['OTHER://']['count'] > 0:
            print(f"    OTHER: {db['double_slash']['OTHER://']['count']:,} files")
        print(f"\n  DUPLICATES:")
        print(f"    By FileHash    : {db['duplicates']['by_file_hash']['count']:,} groups")
        print(f"    By CloudKey    : {db['duplicates']['by_cloud_key']['count']:,} groups")

        # Calculate potential storage savings
        if db['duplicates']['by_file_hash']['groups']:
            dup_storage = sum(g.get('total_size_bytes', 0) for g in db['duplicates']['by_file_hash']['groups'])
            # Only count extra copies beyond the first
            dup_groups = db['duplicates']['by_file_hash']['groups']
            total_waste = 0
            for g in dup_groups:
                count = g.get('count', 1)
                size = g.get('total_size_bytes', 0) // count  # avg size
                total_waste += size * (count - 1)
            print(f"    Est. waste     : {total_waste / 1024 / 1024 / 1024:.2f} GB")

    if all_results["b2_audit"]:
        b2 = all_results["b2_audit"]
        print(f"\nB2 BUCKET:")
        print(f"  Files scanned: {b2['total_files_scanned']:,}")
        print(f"\n  DOUBLE SLASH ISSUES:")
        print(f"    Y://  : {b2['double_slash']['Y://']['count']:,} files")
        print(f"    S://  : {b2['double_slash']['S://']['count']:,} files")
        for prefix, data in b2['double_slash'].items():
            if prefix not in ["Y://", "S://"] and data["count"] > 0:
                print(f"    {prefix}: {data['count']:,} files")


if __name__ == "__main__":
    main()
