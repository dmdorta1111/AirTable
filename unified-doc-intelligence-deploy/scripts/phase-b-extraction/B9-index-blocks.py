#!/usr/bin/env python3
"""
B9-index-blocks.py
Index DXF block references for component/part search.

Creates extracted_blocks table with:
- Block names from DXF files
- Entity counts per block
- Searchable index for finding drawings with specific blocks

Usage: python B9-index-blocks.py [--dry-run] [--limit N] [--batch-size N]
"""

import sys
import logging
import argparse
import json
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


def create_table(conn):
    """Create extracted_blocks table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS extracted_blocks (
                id SERIAL PRIMARY KEY,
                metadata_id INTEGER REFERENCES extracted_metadata(id),
                cloud_file_id INTEGER,
                block_name VARCHAR(255),
                block_name_normalized VARCHAR(255),
                entity_count INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Create indexes
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_blocks_metadata_id 
            ON extracted_blocks(metadata_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_blocks_cloud_file_id 
            ON extracted_blocks(cloud_file_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_blocks_name 
            ON extracted_blocks(block_name)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_blocks_name_normalized 
            ON extracted_blocks(block_name_normalized)
        """)

    conn.commit()
    logger.info("Created extracted_blocks table and indexes")


def normalize_block_name(name):
    """Normalize block name for searching."""
    if not name:
        return None
    # Remove common prefixes, convert to uppercase, strip special chars
    normalized = name.upper().strip()
    # Remove AutoCAD internal prefixes
    for prefix in ["*", "A$C", "_"]:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
    return normalized[:255] if normalized else None


def get_unindexed_metadata(conn, limit=None):
    """Get DXF metadata records that haven't been block-indexed yet."""
    query = """
        SELECT em.id, em.cloud_file_id, em.raw_data
        FROM extracted_metadata em
        WHERE em.source_type = 'dxf'
        AND em.extraction_status = 'completed'
        AND em.raw_data IS NOT NULL
        AND em.raw_data->>'blocks' IS NOT NULL
        AND em.raw_data->>'blocks' != '[]'
        AND NOT EXISTS (
            SELECT 1 FROM extracted_blocks eb
            WHERE eb.metadata_id = em.id
        )
        ORDER BY em.id
    """

    if limit:
        query += f" LIMIT {limit}"

    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()


def extract_blocks(raw_data):
    """Extract block entries from DXF raw_data."""
    blocks = []

    block_list = raw_data.get("blocks", [])
    for block in block_list:
        if isinstance(block, dict):
            name = block.get("name", "")
            entity_count = block.get("entity_count", 0)
            if name and not name.startswith("*"):  # Skip anonymous blocks
                blocks.append(
                    {
                        "block_name": name[:255],
                        "block_name_normalized": normalize_block_name(name),
                        "entity_count": entity_count,
                    }
                )

    return blocks


def index_batch(conn, batch, dry_run=False):
    """Index a batch of metadata records."""
    if dry_run:
        return sum(len(extract_blocks(r[2])) for r in batch)

    all_blocks = []

    for metadata_id, cloud_file_id, raw_data in batch:
        if not raw_data:
            continue

        blocks = extract_blocks(raw_data)

        for b in blocks:
            all_blocks.append(
                (
                    metadata_id,
                    cloud_file_id,
                    b["block_name"],
                    b["block_name_normalized"],
                    b["entity_count"],
                )
            )

    if not all_blocks:
        return 0

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO extracted_blocks 
            (metadata_id, cloud_file_id, block_name, block_name_normalized, entity_count)
            VALUES %s
            """,
            all_blocks,
            template="(%s, %s, %s, %s, %s)",
            page_size=1000,
        )
        inserted = cur.rowcount

    conn.commit()
    return inserted


def main():
    parser = argparse.ArgumentParser(description="Index DXF blocks for search")
    parser.add_argument("--dry-run", action="store_true", help="Count only, don't insert")
    parser.add_argument("--limit", type=int, default=0, help="Limit records to process (0 = all)")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for processing")
    args = parser.parse_args()

    print("=" * 70)
    print("B9: INDEX DXF BLOCKS")
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

    # Create table
    if not args.dry_run:
        create_table(conn)

    # Get current stats
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM extracted_blocks")
        existing = cur.fetchone()[0]
    print(f"\nExisting block records: {existing:,}")

    # Get unindexed records
    records = get_unindexed_metadata(conn, args.limit if args.limit > 0 else None)
    print(f"DXF files with blocks to process: {len(records):,}")

    if not records:
        print("No records to process.")
        conn.close()
        return

    # Process in batches
    indexed = 0
    for i in range(0, len(records), args.batch_size):
        batch = records[i : i + args.batch_size]
        count = index_batch(conn, batch, args.dry_run)
        indexed += count

        if (i + args.batch_size) % 10000 == 0 or i + args.batch_size >= len(records):
            print(
                f"  Processed {min(i + args.batch_size, len(records)):,}/{len(records):,} files, {indexed:,} blocks"
            )

    conn.close()

    print("\n" + "=" * 70)
    print(f"{'Would index' if args.dry_run else 'Indexed'}: {indexed:,} block references")
    print("=" * 70)

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "files_processed": len(records),
        "blocks_indexed": indexed,
    }

    report_file = OUTPUT_DIR / f"B9-blocks-indexing-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
