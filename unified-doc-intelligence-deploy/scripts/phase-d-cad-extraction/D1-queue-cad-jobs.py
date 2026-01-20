#!/usr/bin/env python3
"""
D1-queue-cad-jobs.py
Queue Creo CAD files (.prt, .asm) for extraction processing.

Features:
- Scans CloudFiles for .prt and .asm extensions
- Creates extraction_jobs entries for files not yet queued
- Supports priority assignment based on file type
- Dry-run mode for testing

Usage: python D1-queue-cad-jobs.py [--dry-run] [--limit N] [--priority N]
"""

import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
CONFIG_FILE = PROJECT_DIR / "config.txt"
OUTPUT_DIR = PROJECT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# CAD file extensions to process
CAD_EXTENSIONS = {
    ".prt": "creo_part",
    ".asm": "creo_asm",
}


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


def get_cad_files_to_queue(conn, limit=None):
    """
    Find CAD files in CloudFiles that don't have extraction jobs yet.
    Returns list of (cloud_file_id, filename, extension, job_type).
    """
    query = """
        SELECT cf."ID", cf."LocalPath", cf."CloudKey"
        FROM "CloudFiles" cf
        WHERE (
            LOWER(cf."LocalPath") LIKE '%%.prt'
            OR LOWER(cf."LocalPath") LIKE '%%.prt.%%'
            OR LOWER(cf."LocalPath") LIKE '%%.asm'
            OR LOWER(cf."LocalPath") LIKE '%%.asm.%%'
        )
        AND NOT EXISTS (
            SELECT 1 FROM extraction_jobs ej
            WHERE ej.cloud_file_id = cf."ID"
            AND ej.job_type IN ('creo_part', 'creo_asm')
        )
        ORDER BY cf."ID"
    """

    if limit:
        query += f" LIMIT {limit}"

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    results = []
    for cloud_file_id, local_path, cloud_key in rows:
        filename_lower = local_path.lower()

        # Determine job type based on extension
        if ".prt" in filename_lower:
            job_type = "creo_part"
            ext = ".prt"
        elif ".asm" in filename_lower:
            job_type = "creo_asm"
            ext = ".asm"
        else:
            continue

        results.append((cloud_file_id, local_path, ext, job_type))

    return results


def queue_extraction_jobs(conn, files_to_queue, priority=0, dry_run=False):
    """
    Insert extraction jobs for CAD files.
    Returns count of jobs created.
    """
    if not files_to_queue:
        return 0

    if dry_run:
        logger.info(f"DRY RUN: Would queue {len(files_to_queue)} CAD extraction jobs")
        return len(files_to_queue)

    # Prepare batch insert data
    job_data = [
        (cloud_file_id, job_type, priority)
        for cloud_file_id, filename, ext, job_type in files_to_queue
    ]

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO extraction_jobs (cloud_file_id, job_type, priority, status, created_at)
            VALUES %s
            ON CONFLICT DO NOTHING
            """,
            job_data,
            template="(%s, %s, %s, 'pending', NOW())",
        )
        inserted = cur.rowcount

    conn.commit()
    return inserted


def get_queue_statistics(conn):
    """Get current extraction job queue statistics for CAD files."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                job_type,
                status,
                COUNT(*) as count
            FROM extraction_jobs
            WHERE job_type IN ('creo_part', 'creo_asm')
            GROUP BY job_type, status
            ORDER BY job_type, status
        """)
        return cur.fetchall()


def main():
    parser = argparse.ArgumentParser(description="Queue Creo CAD files for extraction")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be queued without making changes"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Limit number of files to queue (0 = unlimited)"
    )
    parser.add_argument(
        "--priority",
        type=int,
        default=0,
        help="Priority for queued jobs (higher = processed first)",
    )
    parser.add_argument(
        "--stats-only", action="store_true", help="Only show queue statistics, don't queue new jobs"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("D1: QUEUE CAD EXTRACTION JOBS")
    print("=" * 70)
    if args.dry_run:
        print("MODE: DRY RUN")
    if args.limit > 0:
        print(f"LIMIT: {args.limit:,} files")
    print(f"PRIORITY: {args.priority}")
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
    print("\nCurrent CAD Extraction Queue Status:")
    print("-" * 50)
    stats = get_queue_statistics(conn)
    if stats:
        for job_type, status, count in stats:
            print(f"  {job_type:15} | {status:12} | {count:,}")
    else:
        print("  No CAD extraction jobs in queue yet")
    print("-" * 50)

    if args.stats_only:
        conn.close()
        return

    # Find CAD files to queue
    logger.info("Scanning CloudFiles for unqueued CAD files...")
    files_to_queue = get_cad_files_to_queue(conn, limit=args.limit if args.limit > 0 else None)

    # Count by type
    prt_count = sum(1 for f in files_to_queue if f[3] == "creo_part")
    asm_count = sum(1 for f in files_to_queue if f[3] == "creo_asm")

    print(f"\nCAD files found to queue:")
    print(f"  .prt (parts):      {prt_count:,}")
    print(f"  .asm (assemblies): {asm_count:,}")
    print(f"  Total:             {len(files_to_queue):,}")

    if not files_to_queue:
        print("\nNo new CAD files to queue.")
        conn.close()
        return

    # Queue the jobs
    logger.info("Queueing extraction jobs...")
    queued = queue_extraction_jobs(
        conn, files_to_queue, priority=args.priority, dry_run=args.dry_run
    )

    print(f"\n{'Would queue' if args.dry_run else 'Queued'}: {queued:,} extraction jobs")

    # Show updated statistics
    if not args.dry_run:
        print("\nUpdated CAD Extraction Queue Status:")
        print("-" * 50)
        stats = get_queue_statistics(conn)
        for job_type, status, count in stats:
            print(f"  {job_type:15} | {status:12} | {count:,}")
        print("-" * 50)

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
