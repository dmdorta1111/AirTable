#!/usr/bin/env python3
"""
B2-queue-extraction-jobs.py
Queries CloudFiles for all PDFs and DXFs and queues them for extraction.

Skips files that already have extraction_status = 'completed'.
Inserts into extraction_jobs table with appropriate job_type and priority.

Usage: python B2-queue-extraction-jobs.py [--dry-run] [--limit N]
"""

import sys
import logging
import argparse
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import psycopg2
from psycopg2.extras import execute_values
from tqdm import tqdm

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
PLAN_DIR = SCRIPT_DIR.parent
CONFIG_FILE = PLAN_DIR / "config.txt"
OUTPUT_DIR = PLAN_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# File types to process
PDF_EXTENSIONS = (".pdf",)
DXF_EXTENSIONS = (".dxf",)

# Job priorities
DEFAULT_PRIORITY = 5


def load_config():
    """Load configuration from config.txt file."""
    if not CONFIG_FILE.exists():
        logger.error(f"Config file not found: {CONFIG_FILE}")
        logger.info("Please copy config-template.txt to config.txt and fill in your credentials")
        sys.exit(1)

    config = {}
    with open(CONFIG_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


def get_extension(filepath):
    """Extract lowercase extension from a path."""
    if not filepath:
        return None
    if "." in filepath:
        return "." + filepath.rsplit(".", 1)[1].lower()
    return None


def main():
    parser = argparse.ArgumentParser(description="Queue extraction jobs for PDFs and DXFs")
    parser.add_argument("--dry-run", action="store_true", help="Count files but don't create jobs")
    parser.add_argument(
        "--limit", type=int, default=0, help="Limit number of jobs to queue (0 = no limit)"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("B2: QUEUE EXTRACTION JOBS")
    print("=" * 70)
    if args.dry_run:
        print("MODE: DRY RUN (count only)")
    if args.limit > 0:
        print(f"LIMIT: {args.limit:,} jobs")
    print("=" * 70)

    # Load config
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        logger.error("NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    # Connect to database
    logger.info("Connecting to Neon PostgreSQL...")

    conn = None
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False

        logger.info("Connected successfully!")

        stats = defaultdict(int)

        with conn.cursor() as cur:
            # Step 1: Get files that need extraction
            logger.info("Querying CloudFiles for PDFs and DXFs...")

            # Find files NOT already completed or already queued
            cur.execute("""
                SELECT cf."ID", cf."CloudKey", cf."LocalPath"
                FROM "CloudFiles" cf
                WHERE (
                    cf.extraction_status IS NULL 
                    OR cf.extraction_status IN ('pending', 'failed')
                )
                AND (
                    LOWER(cf."CloudKey") LIKE '%%.pdf'
                    OR LOWER(cf."CloudKey") LIKE '%%.dxf'
                    OR LOWER(cf."LocalPath") LIKE '%%.pdf'
                    OR LOWER(cf."LocalPath") LIKE '%%.dxf'
                )
                AND NOT EXISTS (
                    SELECT 1 FROM extraction_jobs ej 
                    WHERE ej.cloud_file_id = cf."ID" 
                    AND ej.status IN ('pending', 'processing')
                )
                ORDER BY cf."ID"
            """)

            files = cur.fetchall()
            logger.info(f"Found {len(files):,} files needing extraction")

            # Step 2: Categorize files
            pdf_jobs = []
            dxf_jobs = []

            for file_id, cloud_key, local_path in tqdm(files, desc="Categorizing files"):
                filepath = cloud_key or local_path
                ext = get_extension(filepath)

                if ext in PDF_EXTENSIONS:
                    pdf_jobs.append((file_id, "pdf_extract", DEFAULT_PRIORITY, "pending"))
                    stats["pdf_count"] += 1
                elif ext in DXF_EXTENSIONS:
                    dxf_jobs.append((file_id, "dxf_extract", DEFAULT_PRIORITY, "pending"))
                    stats["dxf_count"] += 1

            # Apply limit if specified
            if args.limit > 0:
                total_jobs = len(pdf_jobs) + len(dxf_jobs)
                if total_jobs > args.limit:
                    # Proportionally limit
                    pdf_ratio = len(pdf_jobs) / total_jobs
                    pdf_limit = int(args.limit * pdf_ratio)
                    dxf_limit = args.limit - pdf_limit

                    pdf_jobs = pdf_jobs[:pdf_limit]
                    dxf_jobs = dxf_jobs[:dxf_limit]

                    logger.info(f"Limited to {len(pdf_jobs)} PDFs and {len(dxf_jobs)} DXFs")

            # Step 3: Insert jobs (if not dry run)
            if not args.dry_run:
                logger.info("Inserting extraction jobs...")

                all_jobs = pdf_jobs + dxf_jobs

                if all_jobs:
                    # Batch insert
                    execute_values(
                        cur,
                        """
                        INSERT INTO extraction_jobs 
                        (cloud_file_id, job_type, priority, status)
                        VALUES %s
                        ON CONFLICT DO NOTHING
                        """,
                        all_jobs,
                        page_size=1000,
                    )

                    stats["jobs_created"] = cur.rowcount
                    logger.info(f"Created {cur.rowcount:,} extraction jobs")

                    # Update CloudFiles extraction_status to 'pending'
                    file_ids = [job[0] for job in all_jobs]

                    # Batch update in chunks
                    chunk_size = 1000
                    for i in range(0, len(file_ids), chunk_size):
                        chunk = file_ids[i : i + chunk_size]
                        cur.execute(
                            """
                            UPDATE "CloudFiles"
                            SET extraction_status = 'pending'
                            WHERE "ID" = ANY(%s)
                            AND (extraction_status IS NULL OR extraction_status != 'completed')
                        """,
                            (chunk,),
                        )

                    logger.info("Updated CloudFiles extraction_status")

                conn.commit()
            else:
                stats["jobs_created"] = 0

            # Step 4: Get current queue status
            cur.execute("""
                SELECT job_type, status, COUNT(*) 
                FROM extraction_jobs 
                GROUP BY job_type, status
                ORDER BY job_type, status
            """)

            queue_status = {}
            for job_type, status, count in cur.fetchall():
                if job_type not in queue_status:
                    queue_status[job_type] = {}
                queue_status[job_type][status] = count

        conn.close()

        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Total files found:       {len(files):,}")
        print(f"  - PDFs:                {stats['pdf_count']:,}")
        print(f"  - DXFs:                {stats['dxf_count']:,}")

        if args.dry_run:
            print(f"\nDRY RUN - No jobs created")
            print(f"Would create:            {len(pdf_jobs) + len(dxf_jobs):,} jobs")
        else:
            print(f"\nJobs created:            {stats['jobs_created']:,}")

        print("\n" + "=" * 70)
        print("CURRENT QUEUE STATUS")
        print("=" * 70)

        for job_type, statuses in sorted(queue_status.items()):
            print(f"\n{job_type}:")
            for status, count in sorted(statuses.items()):
                print(f"  {status}: {count:,}")

        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": args.dry_run,
            "limit": args.limit,
            "files_found": len(files),
            "pdf_count": stats["pdf_count"],
            "dxf_count": stats["dxf_count"],
            "jobs_queued": len(pdf_jobs) + len(dxf_jobs) if not args.dry_run else 0,
            "queue_status": queue_status,
        }

        report_file = OUTPUT_DIR / "B2-queue-jobs.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n{'=' * 70}")
        print(f"Report saved to: {report_file}")
        print("=" * 70)

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
