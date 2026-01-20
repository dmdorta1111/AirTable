#!/usr/bin/env python3
"""
D4-link-cad-to-documents.py
Link CAD files to existing DocumentGroups by matching basenames.

Features:
- Finds CAD files (.prt, .asm) with extracted metadata
- Matches to existing DocumentGroups by basename
- Creates document_group_members entries with 'source_cad' role
- Handles version numbers in filenames (e.g., 88617-001.prt.1)
- Dry-run mode for testing

Linking Strategy:
- Extract basename from CAD file (e.g., "88617-001" from "88617-001.prt.1")
- Find DocumentGroup with matching name or item_number
- Add CAD file as member with role='source_cad'

Usage: python D4-link-cad-to-documents.py [--dry-run] [--limit N]
"""

import sys
import re
import argparse
import logging
from datetime import datetime
from pathlib import Path

import psycopg2

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
CONFIG_FILE = PROJECT_DIR / "config.txt"
OUTPUT_DIR = PROJECT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_config():
    """Load configuration from config.txt file."""
    if not CONFIG_FILE.exists():
        logger.error(f"Config file not found: {CONFIG_FILE}")
        sys.exit(1)

    config = {}
    with open(CONFIG_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


def extract_basename(filename: str) -> str:
    """
    Extract the base identifier from a CAD filename.

    Examples:
        "88617-001.prt" -> "88617-001"
        "88617-001.prt.1" -> "88617-001"
        "88617-001.asm.5" -> "88617-001"
        "BRACKET_ASSY.asm" -> "BRACKET_ASSY"
    """
    name = filename

    # Remove version numbers at end (e.g., .1, .5, .12)
    name = re.sub(r"\.\d+$", "", name)

    # Remove CAD extensions
    for ext in [".prt", ".asm", ".drw", ".PRT", ".ASM", ".DRW"]:
        if name.endswith(ext):
            name = name[: -len(ext)]
            break

    return name


def get_cad_files_to_link(conn, limit=None):
    """
    Find CAD files with extracted metadata that aren't linked to DocumentGroups.
    Returns list of (cloud_file_id, filename, basename).
    """
    query = """
        SELECT cf."ID", cf."LocalPath"
        FROM "CloudFiles" cf
        INNER JOIN extracted_metadata em ON em.cloud_file_id = cf."ID"
        WHERE em.source_type IN ('creo_part', 'creo_asm')
        AND em.extraction_status = 'completed'
        AND NOT EXISTS (
            SELECT 1 FROM document_group_members dgm
            WHERE dgm.cloud_file_id = cf."ID"
        )
        ORDER BY cf."ID"
    """

    if limit:
        query += f" LIMIT {limit}"

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    results = []
    for cloud_file_id, local_path in rows:
        # Extract just the filename from the full path
        filename = Path(local_path).name if local_path else ""
        basename = extract_basename(filename)
        results.append((cloud_file_id, filename, basename))

    return results


def find_matching_document_group(conn, basename: str):
    """
    Find a DocumentGroup that matches the basename.
    Returns (group_id, group_name, match_type) or None.
    """
    with conn.cursor() as cur:
        # Try exact match on name
        cur.execute(
            """
            SELECT id, name FROM document_groups
            WHERE name = %s
            LIMIT 1
        """,
            (basename,),
        )

        row = cur.fetchone()
        if row:
            return (row[0], row[1], "exact_name")

        # Try exact match on item_number
        cur.execute(
            """
            SELECT id, name FROM document_groups
            WHERE item_number = %s
            LIMIT 1
        """,
            (basename,),
        )

        row = cur.fetchone()
        if row:
            return (row[0], row[1], "item_number")

        # Try case-insensitive match on name
        cur.execute(
            """
            SELECT id, name FROM document_groups
            WHERE LOWER(name) = LOWER(%s)
            LIMIT 1
        """,
            (basename,),
        )

        row = cur.fetchone()
        if row:
            return (row[0], row[1], "case_insensitive")

        # Try partial match (basename contained in name)
        cur.execute(
            """
            SELECT id, name FROM document_groups
            WHERE name ILIKE %s
            ORDER BY LENGTH(name)
            LIMIT 1
        """,
            (f"%{basename}%",),
        )

        row = cur.fetchone()
        if row:
            return (row[0], row[1], "partial")

    return None


def link_cad_to_group(conn, cloud_file_id: int, group_id: int, dry_run: bool = False) -> bool:
    """
    Create a document_group_members entry linking CAD file to group.
    Returns True if successful.
    """
    if dry_run:
        return True

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO document_group_members 
                (group_id, cloud_file_id, role, is_primary, created_at)
                VALUES (%s, %s, 'source_cad', FALSE, NOW())
                ON CONFLICT DO NOTHING
                RETURNING id
            """,
                (group_id, cloud_file_id),
            )

            result = cur.fetchone()
            conn.commit()
            return result is not None

    except Exception as e:
        logger.error(f"Failed to link CAD file {cloud_file_id} to group {group_id}: {e}")
        conn.rollback()
        return False


def get_linking_statistics(conn):
    """Get current CAD linking statistics."""
    with conn.cursor() as cur:
        # Total CAD files with extraction
        cur.execute("""
            SELECT COUNT(*) FROM extracted_metadata
            WHERE source_type IN ('creo_part', 'creo_asm')
            AND extraction_status = 'completed'
        """)
        total_extracted = cur.fetchone()[0]

        # CAD files already linked
        cur.execute("""
            SELECT COUNT(*) FROM document_group_members
            WHERE role = 'source_cad'
        """)
        already_linked = cur.fetchone()[0]

        # DocumentGroups with CAD files
        cur.execute("""
            SELECT COUNT(DISTINCT group_id) FROM document_group_members
            WHERE role = 'source_cad'
        """)
        groups_with_cad = cur.fetchone()[0]

        return {
            "total_extracted": total_extracted,
            "already_linked": already_linked,
            "groups_with_cad": groups_with_cad,
        }


def main():
    parser = argparse.ArgumentParser(description="Link CAD files to DocumentGroups")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be linked without making changes"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Limit number of files to process (0 = unlimited)"
    )
    parser.add_argument(
        "--stats-only", action="store_true", help="Only show statistics, don't link"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("D4: LINK CAD FILES TO DOCUMENT GROUPS")
    print("=" * 70)
    if args.dry_run:
        print("MODE: DRY RUN")
    if args.limit > 0:
        print(f"LIMIT: {args.limit} files")
    print("=" * 70)

    # Load config and connect
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        logger.error("NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    logger.info("Connecting to database...")
    conn = psycopg2.connect(db_url)

    # Show current statistics
    print("\nCurrent CAD Linking Status:")
    print("-" * 50)
    stats = get_linking_statistics(conn)
    print(f"  CAD files with extraction:  {stats['total_extracted']:,}")
    print(f"  Already linked to groups:   {stats['already_linked']:,}")
    print(f"  DocumentGroups with CAD:    {stats['groups_with_cad']:,}")
    print("-" * 50)

    if args.stats_only:
        conn.close()
        return

    # Find CAD files to link
    logger.info("Finding CAD files to link...")
    cad_files = get_cad_files_to_link(conn, limit=args.limit if args.limit > 0 else None)

    print(f"\nCAD files to process: {len(cad_files):,}")

    if not cad_files:
        print("No CAD files need linking.")
        conn.close()
        return

    # Process files
    results = {
        "linked": 0,
        "no_match": 0,
        "failed": 0,
    }

    match_types = {}
    unmatched = []

    print("\nLinking CAD files to DocumentGroups...")
    for i, (cloud_file_id, filename, basename) in enumerate(cad_files, 1):
        # Find matching DocumentGroup
        match = find_matching_document_group(conn, basename)

        if not match:
            results["no_match"] += 1
            unmatched.append((filename, basename))
            continue

        group_id, group_name, match_type = match

        # Link the file
        success = link_cad_to_group(conn, cloud_file_id, group_id, dry_run=args.dry_run)

        if success:
            results["linked"] += 1
            match_types[match_type] = match_types.get(match_type, 0) + 1
        else:
            results["failed"] += 1

        # Progress indicator
        if i % 500 == 0 or i == len(cad_files):
            print(f"  Processed {i}/{len(cad_files)} files...")

    conn.close()

    # Print summary
    print("\n" + "=" * 70)
    print("LINKING SUMMARY")
    print("=" * 70)
    print(f"{'Would link' if args.dry_run else 'Linked'}:     {results['linked']:,}")
    print(f"No match found:  {results['no_match']:,}")
    print(f"Failed:          {results['failed']:,}")
    print(f"Total processed: {len(cad_files):,}")

    if match_types:
        print("\nMatch types:")
        for match_type, count in sorted(match_types.items(), key=lambda x: -x[1]):
            print(f"  {match_type:20} {count:,}")

    # Show sample unmatched files
    if unmatched and len(unmatched) <= 20:
        print("\nUnmatched CAD files (sample):")
        for filename, basename in unmatched[:20]:
            print(f"  {filename} -> '{basename}'")
    elif unmatched:
        print(f"\n{len(unmatched)} CAD files could not be matched to DocumentGroups")
        print("Consider running Phase A linking scripts to create more DocumentGroups")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "results": results,
        "match_types": match_types,
        "total_processed": len(cad_files),
        "unmatched_sample": [(f, b) for f, b in unmatched[:50]],
    }

    report_file = OUTPUT_DIR / f"D4-cad-linking-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(report_file, "w") as f:
        import json

        json.dump(report, f, indent=2)

    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
