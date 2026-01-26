#!/usr/bin/env python3
"""
CloudFiles Path Normalization Script

This script:
1. Examines CloudFiles table structure in Neon database
2. Updates all paths to use single forward slashes (converts // to / and \ to /)
3. Verifies all files exist in B2 after update
4. Reports any mismatches or missing files
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install psycopg[binary,pool]")
    sys.exit(1)

try:
    from b2sdk.v2 import B2Api, InMemoryAccountInfo
except ImportError:
    print("ERROR: b2sdk not installed. Run: pip install b2sdk")
    sys.exit(1)


# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "plans" / "reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, str]:
    """Load configuration from unified-doc-intelligence-deploy/config.txt"""
    config_file = Path(__file__).parent.parent / "unified-doc-intelligence-deploy" / "config.txt"
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


def examine_table_structure(db_url: str) -> Dict:
    """Examine CloudFiles table structure."""
    print("\n" + "=" * 70)
    print("EXAMINING CloudFiles TABLE STRUCTURE")
    print("=" * 70)

    structure = {
        "columns": [],
        "sample_records": [],
        "total_count": 0,
        "path_issues": {
            "double_slash": 0,
            "backslash": 0,
            "mixed": 0
        }
    }

    try:
        with psycopg.connect(db_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Get column info
                cur.execute("""
                    SELECT column_name, data_type, is_nullable, character_maximum_length
                    FROM information_schema.columns
                    WHERE table_name = 'CloudFiles'
                    ORDER BY ordinal_position
                """)
                columns = cur.fetchall()
                structure["columns"] = [
                    {
                        "name": c["column_name"],
                        "type": c["data_type"],
                        "nullable": c["is_nullable"] == "YES",
                        "max_length": c["character_maximum_length"]
                    }
                    for c in columns
                ]

                print("\nTable Columns:")
                for col in structure["columns"]:
                    nullable = "NULL" if col["nullable"] else "NOT NULL"
                    length = f"({col['max_length']})" if col["max_length"] else ""
                    print(f"  - {col['name']}: {col['type']}{length} {nullable}")

                # Get total count
                cur.execute('SELECT COUNT(*) as total FROM "CloudFiles"')
                structure["total_count"] = cur.fetchone()["total"]
                print(f"\nTotal records: {structure['total_count']:,}")

                # Get sample records
                cur.execute("""
                    SELECT "ID", "CloudKey", "LocalPath", "FileHash", "FileSize"
                    FROM "CloudFiles"
                    ORDER BY "ID"
                    LIMIT 5
                """)
                structure["sample_records"] = [dict(r) for r in cur.fetchall()]

                print("\nSample records:")
                for i, rec in enumerate(structure["sample_records"], 1):
                    print(f"\n  Record {i} (ID: {rec['ID']}):")
                    print(f"    CloudKey: {rec['CloudKey'][:80]}..." if len(rec.get('CloudKey', '')) > 80 else f"    CloudKey: {rec.get('CloudKey', 'NULL')}")
                    print(f"    LocalPath: {rec['LocalPath'][:80]}..." if len(rec.get('LocalPath', '')) > 80 else f"    LocalPath: {rec.get('LocalPath', 'NULL')}")

                # Analyze path issues
                print("\nAnalyzing path issues...")

                # Check for double slashes
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM "CloudFiles"
                    WHERE CloudKey LIKE '%//%' OR LocalPath LIKE '%//%'
                """)
                structure["path_issues"]["double_slash"] = cur.fetchone()["count"]

                # Check for backslashes
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM "CloudFiles"
                    WHERE CloudKey LIKE '%\\%' OR LocalPath LIKE '%\\%'
                """)
                structure["path_issues"]["backslash"] = cur.fetchone()["count"]

                # Check for mixed issues
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM "CloudFiles"
                    WHERE (CloudKey LIKE '%//%' OR LocalPath LIKE '%//%')
                      AND (CloudKey LIKE '%\\%' OR LocalPath LIKE '%\\%')
                """)
                structure["path_issues"]["mixed"] = cur.fetchone()["count"]

                print(f"\nPath Issues Found:")
                print(f"  - Double slashes (//): {structure['path_issues']['double_slash']:,}")
                print(f"  - Backslashes (\\): {structure['path_issues']['backslash']:,}")
                print(f"  - Mixed issues: {structure['path_issues']['mixed']:,}")

    except Exception as e:
        print(f"\nERROR examining table: {e}")
        import traceback
        traceback.print_exc()

    return structure


def normalize_path(path: str) -> Tuple[str, List[str]]:
    """
    Normalize path to use single forward slashes.
    Returns (normalized_path, list_of_changes_made)
    """
    if not path:
        return path, []

    original = path
    changes = []

    # Replace backslashes with forward slashes
    if '\\' in path:
        path = path.replace('\\', '/')
        changes.append("backslash_to_forward")

    # Replace double slashes with single slashes
    while '//' in path:
        path = path.replace('//', '/')
        changes.append("double_to_single")

    return path, changes


def update_paths(db_url: str, dry_run: bool = True) -> Dict:
    """Update all paths in CloudFiles to use single forward slashes."""
    print("\n" + "=" * 70)
    print(f"UPDATING PATHS ({'DRY RUN' if dry_run else 'LIVE'})")
    print("=" * 70)

    results = {
        "dry_run": dry_run,
        "records_examined": 0,
        "records_updated": 0,
        "cloudkey_updates": 0,
        "localpath_updates": 0,
        "updates_by_change_type": defaultdict(int),
        "sample_updates": []
    }

    try:
        with psycopg.connect(db_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Get all records that need updating
                cur.execute("""
                    SELECT "ID", "CloudKey", "LocalPath"
                    FROM "CloudFiles"
                    WHERE "CloudKey" LIKE '%//%'
                       OR "CloudKey" LIKE '%\\%'
                       OR "LocalPath" LIKE '%//%'
                       OR "LocalPath" LIKE '%\\%'
                """)

                records_to_update = cur.fetchall()
                results["records_examined"] = len(records_to_update)

                print(f"\nFound {results['records_examined']:,} records needing path normalization")

                if dry_run:
                    print("\nDRY RUN MODE - No changes will be committed")

                # Process updates in batches
                batch_size = 1000
                for i in range(0, len(records_to_update), batch_size):
                    batch = records_to_update[i:i + batch_size]
                    update_batch = []

                    for record in batch:
                        record_id = record["ID"]
                        cloudkey = record["CloudKey"] or ""
                        localpath = record["LocalPath"] or ""

                        new_cloudkey, ck_changes = normalize_path(cloudkey)
                        new_localpath, lp_changes = normalize_path(localpath)

                        if ck_changes or lp_changes:
                            update_data = {
                                "id": record_id,
                                "old_cloudkey": cloudkey,
                                "new_cloudkey": new_cloudkey,
                                "old_localpath": localpath,
                                "new_localpath": new_localpath,
                                "changes": ck_changes + lp_changes
                            }
                            update_batch.append(update_data)

                            # Track statistics
                            if ck_changes:
                                results["cloudkey_updates"] += 1
                            if lp_changes:
                                results["localpath_updates"] += 1

                            for change in (ck_changes + lp_changes):
                                results["updates_by_change_type"][change] += 1

                            # Collect samples
                            if len(results["sample_updates"]) < 20:
                                results["sample_updates"].append(update_data)

                    # Execute batch update
                    if update_batch and not dry_run:
                        for update_data in update_batch:
                            cur.execute("""
                                UPDATE "CloudFiles"
                                SET "CloudKey" = %s,
                                    "LocalPath" = %s
                                WHERE "ID" = %s
                            """, (
                                update_data["new_cloudkey"],
                                update_data["new_localpath"],
                                update_data["id"]
                            ))

                        conn.commit()
                        results["records_updated"] += len(update_batch)

                    if not dry_run:
                        results["records_updated"] = len(update_batch)

                    # Progress
                    processed = min(i + batch_size, len(records_to_update))
                    print(f"  Processed {processed:,} / {len(records_to_update):,} records...")

                if not dry_run and results["records_updated"] > 0:
                    print(f"\n✓ Committed {results['records_updated']:,} updates")
                elif dry_run:
                    print(f"\n✓ Would update {results['records_examined']:,} records")

    except Exception as e:
        print(f"\nERROR updating paths: {e}")
        import traceback
        traceback.print_exc()

    return results


def verify_b2_files(db_url: str, b2_api: B2Api, bucket_name: str, max_files: int = None) -> Dict:
    """Verify all files in database exist in B2."""
    print("\n" + "=" * 70)
    print("VERIFYING FILES AGAINST B2")
    print("=" * 70)

    results = {
        "total_db_files": 0,
        "verified": 0,
        "missing": 0,
        "errors": [],
        "missing_files": []
    }

    try:
        # Get B2 bucket
        bucket = b2_api.get_bucket_by_name(bucket_name)
        print(f"\nConnected to B2 bucket: {bucket_name}")

        # Build set of all B2 file names for fast lookup
        print("Building B2 file index...")
        b2_files = set()
        b2_file_info = {}

        for file_version, _ in bucket.ls(recursive=True):
            file_name = file_version.file_name
            b2_files.add(file_name)
            b2_file_info[file_name] = {
                "size": file_version.size,
                "id": file_version.id_
            }

        print(f"  B2 contains {len(b2_files):,} files")

        # Check all database files
        with psycopg.connect(db_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Get total count
                cur.execute('SELECT COUNT(*) as total FROM "CloudFiles"')
                results["total_db_files"] = cur.fetchone()["total"]
                print(f"\nDatabase contains {results['total_db_files']:,} files")

                # Check each file
                cur.execute("""
                    SELECT "ID", "CloudKey", "LocalPath", "FileSize", "FileHash"
                    FROM "CloudFiles"
                    WHERE "CloudKey" IS NOT NULL
                """)

                for i, record in enumerate(cur):
                    if max_files and i >= max_files:
                        print(f"\n  Reached max file limit ({max_files})")
                        break

                    cloudkey = record["CloudKey"]

                    # Check if file exists in B2
                    if cloudkey in b2_files:
                        results["verified"] += 1

                        # Optional: verify file size matches
                        b2_size = b2_file_info[cloudkey]["size"]
                        db_size = record["FileSize"] or 0
                        if b2_size != db_size:
                            results["errors"].append({
                                "id": record["ID"],
                                "cloudkey": cloudkey,
                                "issue": "size_mismatch",
                                "db_size": db_size,
                                "b2_size": b2_size
                            })
                    else:
                        results["missing"] += 1
                        if len(results["missing_files"]) < 100:
                            results["missing_files"].append({
                                "id": record["ID"],
                                "cloudkey": cloudkey,
                                "localpath": record["LocalPath"],
                                "filesize": record["FileSize"]
                            })

                    # Progress update
                    if (i + 1) % 5000 == 0:
                        print(f"  Verified {i + 1:,} files...")

                print(f"\n  Verified {results['verified']:,} files")
                if results["missing"] > 0:
                    print(f"  ⚠ Missing: {results['missing']:,} files")
                if results["errors"]:
                    print(f"  ⚠ Errors: {len(results['errors']):,} files")

    except Exception as e:
        print(f"\nERROR verifying files: {e}")
        import traceback
        traceback.print_exc()

    return results


def generate_report(structure: Dict, update_results: Dict, verify_results: Dict, output_file: Path):
    """Generate comprehensive report."""
    print("\n" + "=" * 70)
    print("GENERATING REPORT")
    print("=" * 70)

    report = {
        "timestamp": datetime.now().isoformat(),
        "structure": structure,
        "update_results": update_results,
        "verify_results": verify_results
    }

    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n✓ Report saved to: {output_file}")


def print_summary(structure: Dict, update_results: Dict, verify_results: Dict):
    """Print execution summary."""
    print("\n" + "=" * 70)
    print("EXECUTION SUMMARY")
    print("=" * 70)

    print("\n📊 TABLE STRUCTURE:")
    print(f"  Total records: {structure['total_count']:,}")
    print(f"  Columns: {len(structure['columns'])}")

    print("\n🔧 PATH UPDATES:")
    if update_results["dry_run"]:
        print(f"  Mode: DRY RUN (no changes made)")
    else:
        print(f"  Mode: LIVE (changes committed)")
    print(f"  Records examined: {update_results['records_examined']:,}")
    print(f"  CloudKey updates: {update_results['cloudkey_updates']:,}")
    print(f"  LocalPath updates: {update_results['localpath_updates']:,}")

    if update_results['updates_by_change_type']:
        print(f"\n  Changes by type:")
        for change_type, count in update_results['updates_by_change_type'].items():
            print(f"    - {change_type}: {count:,}")

    print("\n✅ B2 VERIFICATION:")
    print(f"  Total DB files: {verify_results['total_db_files']:,}")
    print(f"  Verified in B2: {verify_results['verified']:,}")
    if verify_results['missing'] > 0:
        print(f"  ⚠ Missing: {verify_results['missing']:,}")
    if verify_results['errors']:
        print(f"  ⚠ Size mismatches: {len(verify_results['errors']):,}")

    # Sample updates
    if update_results["sample_updates"]:
        print(f"\n📝 SAMPLE UPDATES (first 5):")
        for i, sample in enumerate(update_results["sample_updates"][:5], 1):
            print(f"\n  Sample {i} (ID: {sample['id']}):")
            if sample["old_cloudkey"] != sample["new_cloudkey"]:
                print(f"    CloudKey:")
                print(f"      OLD: {sample['old_cloudkey'][:80]}...")
                print(f"      NEW: {sample['new_cloudkey'][:80]}...")

    # Missing files samples
    if verify_results["missing_files"]:
        print(f"\n⚠ SAMPLE MISSING FILES (first 10):")
        for i, missing in enumerate(verify_results["missing_files"][:10], 1):
            print(f"  {i}. {missing['cloudkey'][:80]}...")

    print("\n" + "=" * 70)


def main():
    print("=" * 70)
    print("CloudFiles PATH NORMALIZATION & VERIFICATION")
    print("=" * 70)

    # Load configuration
    config = load_config()

    db_url = config.get("NEON_DATABASE_URL")
    key_id = config.get("B2_APPLICATION_KEY_ID")
    app_key = config.get("B2_APPLICATION_KEY")
    bucket_name = config.get("B2_BUCKET_NAME")

    if not all([db_url, key_id, app_key, bucket_name]):
        print("\nERROR: Missing configuration in config.txt")
        sys.exit(1)

    # Step 1: Examine table structure
    structure = examine_table_structure(db_url)

    # Step 2: Dry run update
    print("\n" + "-" * 70)
    print("STEP 1: DRY RUN UPDATE")
    print("-" * 70)
    dry_run_results = update_paths(db_url, dry_run=True)

    # Ask user to proceed
    print("\n" + "=" * 70)
    print("REVIEW DRY RUN RESULTS")
    print("=" * 70)
    print(f"\nThis will update {dry_run_results['records_examined']:,} records:")
    print(f"  - CloudKey changes: {dry_run_results['cloudkey_updates']:,}")
    print(f"  - LocalPath changes: {dry_run_results['localpath_updates']:,}")

    response = input("\nProceed with live update? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("\n❌ Update cancelled by user")
        return

    # Step 3: Live update
    print("\n" + "-" * 70)
    print("STEP 2: LIVE UPDATE")
    print("-" * 70)
    update_results = update_paths(db_url, dry_run=False)

    # Step 4: Initialize B2 API
    print("\n" + "-" * 70)
    print("STEP 3: CONNECT TO B2")
    print("-" * 70)
    try:
        info = InMemoryAccountInfo()
        b2_api = B2Api(info)
        b2_api.authorize_account("production", key_id, app_key)
        print("✓ Authenticated with B2")
    except Exception as e:
        print(f"❌ B2 authentication failed: {e}")
        print("Continuing without B2 verification...")
        b2_api = None

    # Step 5: Verify files against B2
    verify_results = {"total_db_files": 0, "verified": 0, "missing": 0, "errors": [], "missing_files": []}
    if b2_api:
        print("\n" + "-" * 70)
        print("STEP 4: VERIFY FILES AGAINST B2")
        print("-" * 70)

        verify_response = input("\nVerify all files in B2? (this may take time) (yes/no): ").strip().lower()
        if verify_response in ['yes', 'y']:
            verify_results = verify_b2_files(db_url, b2_api, bucket_name)

    # Step 6: Generate report
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    output_file = OUTPUT_DIR / f"fullstack-developer-260123-1142-cloudfile-path-fix-{timestamp}.json"
    generate_report(structure, update_results, verify_results, output_file)

    # Step 7: Print summary
    print_summary(structure, update_results, verify_results)

    print("\n✓ Process complete!")


if __name__ == "__main__":
    main()
