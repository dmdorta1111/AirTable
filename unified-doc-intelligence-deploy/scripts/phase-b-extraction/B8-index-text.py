#!/usr/bin/env python3
"""
B8-index-text.py
Index text content from PDF text_blocks and DXF text_entities for full-text search.

Creates extracted_text table with:
- Full text content from PDFs (OCR text blocks)
- Text entities from DXFs (MTEXT, TEXT)
- Full-text search index using PostgreSQL tsvector

Usage: python B8-index-text.py [--dry-run] [--limit N] [--batch-size N]
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
    """Create extracted_text table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS extracted_text (
                id SERIAL PRIMARY KEY,
                metadata_id INTEGER REFERENCES extracted_metadata(id),
                cloud_file_id INTEGER,
                source_type VARCHAR(20),
                text_type VARCHAR(20),
                page_number INTEGER,
                layer VARCHAR(255),
                text_content TEXT,
                text_search tsvector,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Create indexes
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_text_metadata_id 
            ON extracted_text(metadata_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_text_cloud_file_id 
            ON extracted_text(cloud_file_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_text_source_type 
            ON extracted_text(source_type)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_text_search 
            ON extracted_text USING GIN(text_search)
        """)

    conn.commit()
    logger.info("Created extracted_text table and indexes")


def get_unindexed_metadata(conn, source_type, limit=None):
    """Get metadata records that haven't been text-indexed yet."""
    query = """
        SELECT em.id, em.cloud_file_id, em.raw_data
        FROM extracted_metadata em
        WHERE em.source_type = %s
        AND em.extraction_status = 'completed'
        AND em.raw_data IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM extracted_text et
            WHERE et.metadata_id = em.id
        )
        ORDER BY em.id
    """

    if limit:
        query += f" LIMIT {limit}"

    with conn.cursor() as cur:
        cur.execute(query, (source_type,))
        return cur.fetchall()


def extract_pdf_text(raw_data):
    """Extract text entries from PDF raw_data."""
    texts = []

    text_blocks = raw_data.get("text_blocks", [])
    for block in text_blocks:
        if isinstance(block, dict):
            text = block.get("text", "")
            page = block.get("page", 1)
            if text and len(text.strip()) > 0:
                texts.append(
                    {
                        "text_type": "text_block",
                        "page_number": page,
                        "layer": None,
                        "text_content": text.strip()[:50000],  # Limit size
                    }
                )
        elif isinstance(block, str) and block.strip():
            texts.append(
                {
                    "text_type": "text_block",
                    "page_number": 1,
                    "layer": None,
                    "text_content": block.strip()[:50000],
                }
            )

    return texts


def extract_dxf_text(raw_data):
    """Extract text entries from DXF raw_data."""
    texts = []

    text_entities = raw_data.get("text_entities", [])
    for entity in text_entities:
        if isinstance(entity, dict):
            text = entity.get("text", "")
            layer = entity.get("layer", "0")
            text_type = entity.get("type", "text")
            if text and len(text.strip()) > 0:
                texts.append(
                    {
                        "text_type": text_type,
                        "page_number": None,
                        "layer": layer[:255] if layer else None,
                        "text_content": text.strip()[:50000],
                    }
                )

    return texts


def index_batch(conn, batch, source_type, dry_run=False):
    """Index a batch of metadata records."""
    if dry_run:
        return sum(
            len(extract_pdf_text(r[2]) if source_type == "pdf" else extract_dxf_text(r[2]))
            for r in batch
        )

    all_texts = []

    for metadata_id, cloud_file_id, raw_data in batch:
        if not raw_data:
            continue

        if source_type == "pdf":
            texts = extract_pdf_text(raw_data)
        else:
            texts = extract_dxf_text(raw_data)

        for t in texts:
            all_texts.append(
                (
                    metadata_id,
                    cloud_file_id,
                    source_type,
                    t["text_type"],
                    t["page_number"],
                    t["layer"],
                    t["text_content"],
                )
            )

    if not all_texts:
        return 0

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO extracted_text 
            (metadata_id, cloud_file_id, source_type, text_type, page_number, layer, text_content, text_search)
            VALUES %s
            """,
            all_texts,
            template="(%s, %s, %s, %s, %s, %s, %s, to_tsvector('english', %s))",
            page_size=500,
        )
        inserted = cur.rowcount

    conn.commit()
    return inserted


def main():
    parser = argparse.ArgumentParser(description="Index text content for full-text search")
    parser.add_argument("--dry-run", action="store_true", help="Count only, don't insert")
    parser.add_argument("--limit", type=int, default=0, help="Limit records to process (0 = all)")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for processing")
    parser.add_argument(
        "--source", choices=["pdf", "dxf", "all"], default="all", help="Source type to process"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("B8: INDEX TEXT CONTENT")
    print("=" * 70)
    if args.dry_run:
        print("MODE: DRY RUN")
    if args.limit > 0:
        print(f"LIMIT: {args.limit}")
    print(f"SOURCE: {args.source}")
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
        cur.execute("SELECT COUNT(*) FROM extracted_text")
        existing = cur.fetchone()[0]
    print(f"\nExisting text records: {existing:,}")

    sources = ["pdf", "dxf"] if args.source == "all" else [args.source]
    total_indexed = 0

    for source_type in sources:
        print(f"\n--- Processing {source_type.upper()} ---")

        # Get unindexed records
        records = get_unindexed_metadata(conn, source_type, args.limit if args.limit > 0 else None)
        print(f"Records to process: {len(records):,}")

        if not records:
            continue

        # Process in batches
        indexed = 0
        for i in range(0, len(records), args.batch_size):
            batch = records[i : i + args.batch_size]
            count = index_batch(conn, batch, source_type, args.dry_run)
            indexed += count

            if (i + args.batch_size) % 5000 == 0 or i + args.batch_size >= len(records):
                print(
                    f"  Processed {min(i + args.batch_size, len(records)):,}/{len(records):,} records, {indexed:,} text entries"
                )

        print(
            f"  {'Would index' if args.dry_run else 'Indexed'}: {indexed:,} text entries from {source_type.upper()}"
        )
        total_indexed += indexed

    conn.close()

    print("\n" + "=" * 70)
    print(f"TOTAL: {'Would index' if args.dry_run else 'Indexed'} {total_indexed:,} text entries")
    print("=" * 70)

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "total_indexed": total_indexed,
        "sources": sources,
    }

    report_file = OUTPUT_DIR / f"B8-text-indexing-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
