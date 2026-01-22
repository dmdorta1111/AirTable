#!/usr/bin/env python3
"""
B10-update-metadata-fields.py
Extract and update PDF metadata fields (title, creator, producer, pages)
directly in extracted_metadata table.

Adds columns to extracted_metadata:
- pdf_title: Document title
- pdf_creator: Software that created the PDF
- pdf_producer: PDF producer
- pdf_pages: Page count
- dxf_version: DXF/AutoCAD version
- entity_count: Total entities in DXF

Usage: python B10-update-metadata-fields.py [--dry-run] [--limit N]
"""

import sys
import logging
import argparse
import json
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


def add_columns(conn):
    """Add new columns to extracted_metadata if they don't exist."""
    columns = [
        ("pdf_title", "VARCHAR(500)"),
        ("pdf_creator", "VARCHAR(255)"),
        ("pdf_producer", "VARCHAR(255)"),
        ("pdf_pages", "INTEGER"),
        ("dxf_version", "VARCHAR(20)"),
        ("entity_count", "INTEGER"),
    ]

    with conn.cursor() as cur:
        for col_name, col_type in columns:
            try:
                cur.execute(f"""
                    ALTER TABLE extracted_metadata 
                    ADD COLUMN IF NOT EXISTS {col_name} {col_type}
                """)
            except Exception as e:
                logger.warning(f"Column {col_name} may already exist: {e}")
                conn.rollback()
                continue

    conn.commit()

    # Create indexes for searchable fields
    with conn.cursor() as cur:
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_metadata_pdf_title 
            ON extracted_metadata(pdf_title)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_metadata_pdf_creator 
            ON extracted_metadata(pdf_creator)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_metadata_dxf_version 
            ON extracted_metadata(dxf_version)
        """)

    conn.commit()
    logger.info("Added metadata columns and indexes")


def update_pdf_metadata(conn, limit=None, dry_run=False):
    """Update PDF metadata fields from raw_data."""

    # Find PDFs that need updating
    query = """
        SELECT id, raw_data
        FROM extracted_metadata
        WHERE source_type = 'pdf'
        AND extraction_status = 'completed'
        AND raw_data IS NOT NULL
        AND pdf_title IS NULL
        ORDER BY id
    """

    if limit:
        query += f" LIMIT {limit}"

    with conn.cursor() as cur:
        cur.execute(query)
        records = cur.fetchall()

    print(f"  PDFs to update: {len(records):,}")

    if dry_run or not records:
        return len(records)

    updated = 0
    for metadata_id, raw_data in records:
        if not raw_data:
            continue

        title = raw_data.get("title", "")[:500] if raw_data.get("title") else None
        creator = raw_data.get("creator", "")[:255] if raw_data.get("creator") else None
        producer = raw_data.get("producer", "")[:255] if raw_data.get("producer") else None
        pages = raw_data.get("pages")

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE extracted_metadata
                SET pdf_title = %s,
                    pdf_creator = %s,
                    pdf_producer = %s,
                    pdf_pages = %s
                WHERE id = %s
            """,
                (title, creator, producer, pages, metadata_id),
            )

        updated += 1

        if updated % 10000 == 0:
            conn.commit()
            print(f"    Updated {updated:,} PDFs...")

    conn.commit()
    return updated


def update_dxf_metadata(conn, limit=None, dry_run=False):
    """Update DXF metadata fields from raw_data."""

    # Find DXFs that need updating
    query = """
        SELECT id, raw_data
        FROM extracted_metadata
        WHERE source_type = 'dxf'
        AND extraction_status = 'completed'
        AND raw_data IS NOT NULL
        AND dxf_version IS NULL
        ORDER BY id
    """

    if limit:
        query += f" LIMIT {limit}"

    with conn.cursor() as cur:
        cur.execute(query)
        records = cur.fetchall()

    print(f"  DXFs to update: {len(records):,}")

    if dry_run or not records:
        return len(records)

    updated = 0
    for metadata_id, raw_data in records:
        if not raw_data:
            continue

        dxf_version = raw_data.get("dxf_version", "")[:20] if raw_data.get("dxf_version") else None
        entity_count = raw_data.get("total_entities")

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE extracted_metadata
                SET dxf_version = %s,
                    entity_count = %s
                WHERE id = %s
            """,
                (dxf_version, entity_count, metadata_id),
            )

        updated += 1

        if updated % 50000 == 0:
            conn.commit()
            print(f"    Updated {updated:,} DXFs...")

    conn.commit()
    return updated


def main():
    parser = argparse.ArgumentParser(description="Update metadata fields from raw_data")
    parser.add_argument("--dry-run", action="store_true", help="Count only, don't update")
    parser.add_argument("--limit", type=int, default=0, help="Limit records to process (0 = all)")
    args = parser.parse_args()

    print("=" * 70)
    print("B10: UPDATE METADATA FIELDS")
    print("=" * 70)
    if args.dry_run:
        print("MODE: DRY RUN")
    if args.limit > 0:
        print(f"LIMIT: {args.limit}")
    print("=" * 70)

    # Load config
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        logger.error("NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    conn = psycopg2.connect(db_url)

    # Add columns
    if not args.dry_run:
        add_columns(conn)

    # Update PDF metadata
    print("\n--- Updating PDF metadata ---")
    pdf_updated = update_pdf_metadata(conn, args.limit if args.limit > 0 else None, args.dry_run)

    # Update DXF metadata
    print("\n--- Updating DXF metadata ---")
    dxf_updated = update_dxf_metadata(conn, args.limit if args.limit > 0 else None, args.dry_run)

    conn.close()

    print("\n" + "=" * 70)
    print(f"{'Would update' if args.dry_run else 'Updated'}:")
    print(f"  PDF records: {pdf_updated:,}")
    print(f"  DXF records: {dxf_updated:,}")
    print("=" * 70)

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "pdf_updated": pdf_updated,
        "dxf_updated": dxf_updated,
    }

    report_file = (
        OUTPUT_DIR / f"B10-metadata-update-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
