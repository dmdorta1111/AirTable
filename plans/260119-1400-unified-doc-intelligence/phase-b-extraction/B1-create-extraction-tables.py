#!/usr/bin/env python3
"""
B1-create-extraction-tables.py
Verifies extraction tables exist (from schema migration) and adds any missing indexes.

Usage: python B1-create-extraction-tables.py [--dry-run]
"""

import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path

import psycopg2

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
PLAN_DIR = SCRIPT_DIR.parent
CONFIG_FILE = PLAN_DIR / "config.txt"
OUTPUT_DIR = PLAN_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Required tables for extraction
REQUIRED_TABLES = [
    "extraction_jobs",
    "extracted_metadata",
    "extracted_dimensions",
    "extracted_parameters",
    "extracted_materials",
    "extracted_bom_items",
]

# Required indexes for extraction performance
REQUIRED_INDEXES = [
    # extraction_jobs indexes for job claiming
    (
        "idx_ej_pending_priority",
        "extraction_jobs",
        "(priority DESC, created_at ASC) WHERE status = 'pending'",
    ),
    (
        "idx_ej_processing_worker",
        "extraction_jobs",
        "(worker_id, started_at) WHERE status = 'processing'",
    ),
    # extracted_metadata indexes
    (
        "idx_em_pending_extraction",
        "extracted_metadata",
        "(extraction_status) WHERE extraction_status = 'pending'",
    ),
]


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


def check_table_exists(cur, table_name):
    """Check if a table exists in the database."""
    cur.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        )
    """,
        (table_name,),
    )
    return cur.fetchone()[0]


def check_index_exists(cur, index_name):
    """Check if an index exists in the database."""
    cur.execute(
        """
        SELECT EXISTS (
            SELECT FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname = %s
        )
    """,
        (index_name,),
    )
    return cur.fetchone()[0]


def get_table_row_count(cur, table_name):
    """Get approximate row count for a table."""
    cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
    return cur.fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description="Verify extraction tables exist")
    parser.add_argument(
        "--dry-run", action="store_true", help="Check only, don't create missing indexes"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("B1: CREATE/VERIFY EXTRACTION TABLES")
    print("=" * 70)
    if args.dry_run:
        print("MODE: DRY RUN (check only)")
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

        missing_tables = []
        existing_tables = []
        missing_indexes = []
        existing_indexes = []
        table_stats = {}

        with conn.cursor() as cur:
            # Check required tables
            logger.info("Checking required tables...")

            for table in REQUIRED_TABLES:
                if check_table_exists(cur, table):
                    existing_tables.append(table)
                    try:
                        count = get_table_row_count(cur, table)
                        table_stats[table] = count
                    except Exception:
                        table_stats[table] = "N/A"
                else:
                    missing_tables.append(table)

            # Check required indexes
            logger.info("Checking required indexes...")

            for idx_name, table, idx_def in REQUIRED_INDEXES:
                if check_index_exists(cur, idx_name):
                    existing_indexes.append(idx_name)
                else:
                    missing_indexes.append((idx_name, table, idx_def))

            # Create missing indexes if not dry run
            if missing_indexes and not args.dry_run:
                logger.info(f"Creating {len(missing_indexes)} missing indexes...")

                for idx_name, table, idx_def in missing_indexes:
                    try:
                        sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} {idx_def}"
                        cur.execute(sql)
                        logger.info(f"  Created index: {idx_name}")
                    except psycopg2.Error as e:
                        logger.warning(f"  Failed to create {idx_name}: {e}")

                conn.commit()

            # Check CloudFiles extraction_status column
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'CloudFiles' 
                    AND column_name = 'extraction_status'
                )
            """)
            has_extraction_status = cur.fetchone()[0]

        conn.close()

        # Print report
        print("\n" + "=" * 70)
        print("TABLE STATUS")
        print("=" * 70)

        for table in REQUIRED_TABLES:
            if table in existing_tables:
                count = table_stats.get(table, "N/A")
                print(
                    f"  [OK] {table}: {count:,} rows"
                    if isinstance(count, int)
                    else f"  [OK] {table}: {count}"
                )
            else:
                print(f"  [MISSING] {table}")

        print("\n" + "=" * 70)
        print("INDEX STATUS")
        print("=" * 70)

        for idx_name, table, _ in REQUIRED_INDEXES:
            if idx_name in existing_indexes:
                print(f"  [OK] {idx_name} on {table}")
            else:
                if args.dry_run:
                    print(f"  [MISSING] {idx_name} on {table}")
                else:
                    print(f"  [CREATED] {idx_name} on {table}")

        print("\n" + "=" * 70)
        print("CLOUDFILES EXTENSION")
        print("=" * 70)
        print(f"  extraction_status column: {'[OK]' if has_extraction_status else '[MISSING]'}")

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        if missing_tables:
            print(f"  [ERROR] Missing tables: {', '.join(missing_tables)}")
            print("  Run A1-migrate-schema.py first to create required tables")
            status = "FAILED"
        elif missing_indexes and args.dry_run:
            print(f"  [WARNING] {len(missing_indexes)} indexes need to be created")
            print("  Run without --dry-run to create them")
            status = "NEEDS_INDEXES"
        else:
            print("  All extraction tables and indexes are ready!")
            status = "READY"

        print(f"\n  Status: {status}")
        print("=" * 70)

        # Write status file
        status_file = OUTPUT_DIR / "B1-table-status.json"
        import json

        report = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "existing_tables": existing_tables,
            "missing_tables": missing_tables,
            "existing_indexes": existing_indexes,
            "missing_indexes": [idx[0] for idx in missing_indexes],
            "table_stats": table_stats,
            "has_extraction_status_column": has_extraction_status,
        }
        with open(status_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved to: {status_file}")

        if missing_tables:
            sys.exit(1)

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
