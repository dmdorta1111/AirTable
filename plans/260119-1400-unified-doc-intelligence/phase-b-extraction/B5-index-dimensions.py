#!/usr/bin/env python3
"""
B5-index-dimensions.py
Read extracted_metadata.raw_data for completed extractions and index dimensions.

This script processes any completed extractions that may have dimensions
not yet indexed into extracted_dimensions table.

Usage: python B5-index-dimensions.py [--dry-run] [--limit N]
"""

import sys
import logging
import argparse
import json
from datetime import datetime
from pathlib import Path

import psycopg2
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


def main():
    parser = argparse.ArgumentParser(description="Index dimensions from extracted metadata")
    parser.add_argument("--dry-run", action="store_true", help="Count only, don't insert")
    parser.add_argument("--limit", type=int, default=0, help="Limit records to process (0 = all)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    args = parser.parse_args()

    print("=" * 70)
    print("B5: INDEX DIMENSIONS")
    print("=" * 70)
    if args.dry_run:
        print("MODE: DRY RUN")
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

        stats = {
            "records_processed": 0,
            "dimensions_found": 0,
            "dimensions_inserted": 0,
            "duplicates_skipped": 0,
            "errors": 0,
        }

        with conn.cursor() as cur:
            # Find completed extractions that have dimensions in raw_data
            # but may not be fully indexed
            logger.info("Finding extractions with dimensions to index...")

            query = """
                SELECT em.id, em.cloud_file_id, em.raw_data, em.source_type
                FROM extracted_metadata em
                WHERE em.extraction_status IN ('completed', 'skipped')
                AND em.raw_data IS NOT NULL
                AND em.raw_data::text LIKE '%%"dimensions"%%'
            """

            if args.limit > 0:
                query += f" LIMIT {args.limit}"

            cur.execute(query)
            records = cur.fetchall()

            logger.info(f"Found {len(records):,} records to process")

            if not records:
                print("\nNo records with dimensions found.")
                conn.close()
                return

            # Process each record
            for metadata_id, cloud_file_id, raw_data, source_type in tqdm(records, desc="Indexing"):
                try:
                    if not raw_data:
                        continue

                    data = raw_data if isinstance(raw_data, dict) else json.loads(raw_data)
                    dimensions = data.get("dimensions", [])

                    if not dimensions:
                        continue

                    stats["records_processed"] += 1
                    stats["dimensions_found"] += len(dimensions)

                    if args.dry_run:
                        continue

                    # Insert dimensions (with conflict handling)
                    for dim in dimensions[:200]:  # Limit per file
                        try:
                            value = dim.get("value")
                            if value is None:
                                continue

                            dim_type = dim.get("type", "linear")
                            layer = dim.get("layer")
                            source_page = dim.get("source_page")
                            unit = "mm"  # Default unit

                            cur.execute(
                                """
                                INSERT INTO extracted_dimensions 
                                (metadata_id, cloud_file_id, value, unit, dimension_type, layer, source_page)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """,
                                (
                                    metadata_id,
                                    cloud_file_id,
                                    value,
                                    unit,
                                    dim_type,
                                    layer,
                                    source_page,
                                ),
                            )

                            if cur.rowcount > 0:
                                stats["dimensions_inserted"] += 1
                            else:
                                stats["duplicates_skipped"] += 1

                        except Exception as e:
                            stats["errors"] += 1
                            logger.debug(f"Error inserting dimension: {e}")

                    # Commit in batches
                    if stats["records_processed"] % args.batch_size == 0:
                        conn.commit()

                except Exception as e:
                    stats["errors"] += 1
                    logger.warning(f"Error processing metadata {metadata_id}: {e}")

            # Final commit
            if not args.dry_run:
                conn.commit()

                # Update dimension counts on metadata records
                logger.info("Updating dimension counts...")
                cur.execute("""
                    UPDATE extracted_metadata em
                    SET dimension_count = (
                        SELECT COUNT(*) FROM extracted_dimensions ed
                        WHERE ed.metadata_id = em.id
                    ),
                    has_dimensions = EXISTS (
                        SELECT 1 FROM extracted_dimensions ed
                        WHERE ed.metadata_id = em.id
                    )
                    WHERE em.extraction_status IN ('completed', 'skipped')
                """)
                conn.commit()

        conn.close()

        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Records processed:     {stats['records_processed']:,}")
        print(f"Dimensions found:      {stats['dimensions_found']:,}")

        if args.dry_run:
            print(f"\nDRY RUN - No dimensions inserted")
        else:
            print(f"Dimensions inserted:   {stats['dimensions_inserted']:,}")
            print(f"Duplicates skipped:    {stats['duplicates_skipped']:,}")

        if stats["errors"] > 0:
            print(f"Errors:                {stats['errors']:,}")

        # Save report
        report = {"timestamp": datetime.now().isoformat(), "dry_run": args.dry_run, "stats": stats}

        report_file = OUTPUT_DIR / "B5-index-dimensions.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved to: {report_file}")

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
