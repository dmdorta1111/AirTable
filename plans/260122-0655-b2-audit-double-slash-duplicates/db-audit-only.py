#!/usr/bin/env python3
"""
Neon Database Audit Script - Fixed version
Audits CloudFiles table for double slashes and duplicates
"""

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg")
    sys.exit(1)

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_config():
    """Load configuration from config.txt file."""
    config_file = Path(__file__).parent / "config.txt"
    config = {}
    with open(config_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    return config


def audit_database(db_url):
    """Audit database for double slash and duplicate issues."""
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
                print(f"  Total files: {results['total_files']:,}")

                # Check for double slashes in CloudKey
                print("\n  Checking for double slashes in CloudKey...")

                # Y:// pattern
                cur.execute("""
                    SELECT "CloudKey", "LocalPath", "FileHash", "FileSize"
                    FROM "CloudFiles"
                    WHERE "CloudKey" LIKE 'Y://%%'
                    LIMIT 100
                """)
                y_slash = cur.fetchall()
                # Get full count
                cur.execute("""SELECT COUNT(*) as count FROM "CloudFiles" WHERE "CloudKey" LIKE 'Y://%%'""")
                y_count = cur.fetchone()["count"]
                results["double_slash"]["Y://"]["count"] = y_count
                # Access with case-preserved keys
                results["double_slash"]["Y://"]["samples"] = [
                    {
                        "CloudKey": r["CloudKey"],
                        "LocalPath": r.get("LocalPath", ""),
                        "FileHash": r.get("FileHash", ""),
                        "FileSize": r.get("FileSize", 0)
                    } for r in y_slash[:20]
                ]
                print(f"    Y:// : {y_count:,} files")

                # S:// pattern
                cur.execute("""
                    SELECT "CloudKey", "LocalPath", "FileHash", "FileSize"
                    FROM "CloudFiles"
                    WHERE "CloudKey" LIKE 'S://%%'
                    LIMIT 100
                """)
                s_slash = cur.fetchall()
                # Get full count
                cur.execute("""SELECT COUNT(*) as count FROM "CloudFiles" WHERE "CloudKey" LIKE 'S://%%'""")
                s_count = cur.fetchone()["count"]
                results["double_slash"]["S://"]["count"] = s_count
                results["double_slash"]["S://"]["samples"] = [
                    {
                        "CloudKey": r["CloudKey"],
                        "LocalPath": r.get("LocalPath", ""),
                        "FileHash": r.get("FileHash", ""),
                        "FileSize": r.get("FileSize", 0)
                    } for r in s_slash[:20]
                ]
                print(f"    S:// : {s_count:,} files")

                # Other double slash patterns
                cur.execute("""
                    SELECT "CloudKey", "LocalPath", "FileHash", "FileSize"
                    FROM "CloudFiles"
                    WHERE "CloudKey" ~ '^[A-Z]+://'
                      AND "CloudKey" NOT LIKE 'Y://%%'
                      AND "CloudKey" NOT LIKE 'S://%%'
                    LIMIT 100
                """)
                other_slash = cur.fetchall()
                results["double_slash"]["OTHER://"]["count"] = len(other_slash)
                results["double_slash"]["OTHER://"]["samples"] = [
                    {
                        "CloudKey": r["CloudKey"],
                        "LocalPath": r.get("LocalPath", ""),
                        "FileHash": r.get("FileHash", ""),
                        "FileSize": r.get("FileSize", 0)
                    } for r in other_slash[:20]
                ]
                if other_slash:
                    print(f"    OTHER:// : {len(other_slash):,} files")

                # Check for duplicates by FileHash
                print("\n  Checking for duplicates by FileHash...")
                # First get the count
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM (
                        SELECT "FileHash"
                        FROM "CloudFiles"
                        WHERE "FileHash" IS NOT NULL
                        GROUP BY "FileHash"
                        HAVING COUNT(*) > 1
                    ) as dups
                """)
                dup_hash_count = cur.fetchone()["count"]
                # Get sample data
                cur.execute("""
                    SELECT "FileHash", COUNT(*) as count,
                           array_agg("CloudKey") as keys,
                           array_agg("ID") as ids,
                           SUM("FileSize") as total_size
                    FROM "CloudFiles"
                    WHERE "FileHash" IS NOT NULL
                    GROUP BY "FileHash"
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC
                    LIMIT 50
                """)
                dup_hash = cur.fetchall()
                results["duplicates"]["by_file_hash"]["count"] = dup_hash_count
                results["duplicates"]["by_file_hash"]["groups"] = [
                    {
                        "FileHash": r["FileHash"],
                        "count": r["count"],
                        "total_size_bytes": r["total_size"],
                        "sample_ids": r["ids"][:10],
                        "sample_keys": r["keys"][:10]
                    } for r in dup_hash[:20]
                ]
                print(f"    Found {len(dup_hash):,} duplicate groups by FileHash")
                if dup_hash:
                    print(f"    Top duplicate: {dup_hash[0]['FileHash'][:16]}... ({dup_hash[0]['count']} copies)")

                # Check for duplicate CloudKeys
                print("\n  Checking for duplicate CloudKeys...")
                cur.execute("""
                    SELECT "CloudKey", COUNT(*) as count,
                           array_agg("ID") as ids,
                           SUM("FileSize") as total_size
                    FROM "CloudFiles"
                    WHERE "CloudKey" IS NOT NULL
                    GROUP BY "CloudKey"
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC
                    LIMIT 50
                """)
                dup_key = cur.fetchall()
                results["duplicates"]["by_cloud_key"]["count"] = len(dup_key)
                results["duplicates"]["by_cloud_key"]["groups"] = [
                    {
                        "CloudKey": r["CloudKey"],
                        "count": r["count"],
                        "total_size_bytes": r["total_size"],
                        "sample_ids": r["ids"][:10]
                    } for r in dup_key[:20]
                ]
                print(f"    Found {len(dup_key):,} duplicate CloudKeys")
                if dup_key:
                    print(f"    Top duplicate: {dup_key[0]['CloudKey'][:60]}... ({dup_key[0]['count']} copies)")

                # Get unique file count
                cur.execute('SELECT COUNT(DISTINCT "FileHash") as unique FROM "CloudFiles" WHERE "FileHash" IS NOT NULL')
                results["unique_files"] = cur.fetchone()["unique"]
                print(f"\n  Unique files (by hash): {results['unique_files']:,}")

    except Exception as e:
        results["errors"].append(f"Database error: {e}")
        import traceback
        traceback.print_exc()

    return results


def main():
    print("=" * 70)
    print("NEON DATABASE AUDIT - DOUBLE SLASH & DUPLICATES")
    print("=" * 70)

    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        print("ERROR: Missing NEON_DATABASE_URL in config.txt")
        sys.exit(1)

    results = audit_database(db_url)

    # Save results
    output_file = OUTPUT_DIR / f"db-audit-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("AUDIT SUMMARY")
    print("=" * 70)
    print(f"\nNEON DATABASE:")
    print(f"  Total files: {results['total_files']:,}")
    print(f"  Unique files (by hash): {results['unique_files']:,}")
    print(f"\n  DOUBLE SLASH ISSUES:")
    print(f"    Y://  : {results['double_slash']['Y://']['count']:,} files")
    print(f"    S://  : {results['double_slash']['S://']['count']:,} files")
    if results['double_slash']['OTHER://']['count'] > 0:
        print(f"    OTHER: {results['double_slash']['OTHER://']['count']:,} files")
    print(f"\n  DUPLICATES:")
    print(f"    By FileHash    : {results['duplicates']['by_file_hash']['count']:,} groups")
    print(f"    By CloudKey    : {results['duplicates']['by_cloud_key']['count']:,} groups")

    # Calculate potential storage savings
    if results['duplicates']['by_file_hash']['groups']:
        dup_groups = results['duplicates']['by_file_hash']['groups']
        total_waste = 0
        for g in dup_groups:
            count = g.get('count', 1)
            size = g.get('total_size_bytes', 0) // count if count > 0 else 0
            total_waste += size * (count - 1)
        print(f"    Est. waste (sample): {total_waste / 1024 / 1024 / 1024:.2f} GB")

    if results['errors']:
        print(f"\n  ERRORS: {len(results['errors'])}")
        for e in results['errors']:
            print(f"    - {e}")


if __name__ == "__main__":
    main()
