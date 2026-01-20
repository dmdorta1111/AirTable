#!/usr/bin/env python3
"""
B6-index-materials.py
Parse text blocks for material patterns and index into extracted_materials table.

Processes extracted_metadata.raw_data looking for text_blocks and materials.
Uses regex patterns to identify common engineering material specifications.

Usage: python B6-index-materials.py [--dry-run] [--limit N]
"""

import sys
import logging
import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

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

# Material patterns for extraction
MATERIAL_PATTERNS = [
    # Stainless Steel variants
    (r"\b(304)\s*(?:SS|STAINLESS|S\.S\.)?\b", "304 STAINLESS STEEL"),
    (r"\b(316)\s*(?:SS|STAINLESS|S\.S\.)?\b", "316 STAINLESS STEEL"),
    (r"\b(303)\s*(?:SS|STAINLESS|S\.S\.)?\b", "303 STAINLESS STEEL"),
    (r"\b(17-4\s*PH)\b", "17-4 PH STAINLESS"),
    (r"\bSTAINLESS\s*STEEL\s*(\d{3})?\b", "STAINLESS STEEL"),
    # Aluminum alloys
    (r"\b(6061)(?:-T6)?\b", "6061 ALUMINUM"),
    (r"\b(7075)(?:-T6)?\b", "7075 ALUMINUM"),
    (r"\b(2024)(?:-T3)?\b", "2024 ALUMINUM"),
    (r"\bALUMINUM\s*(\d{4})(?:-T\d)?\b", "ALUMINUM"),
    (r"\bAL\s*(\d{4})\b", "ALUMINUM"),
    # Carbon Steel
    (r"\b(A36)\s*(?:STEEL)?\b", "A36 STEEL"),
    (r"\b(1018)\s*(?:STEEL|CRS)?\b", "1018 STEEL"),
    (r"\b(1045)\s*(?:STEEL)?\b", "1045 STEEL"),
    (r"\b(4140)\s*(?:STEEL)?\b", "4140 STEEL"),
    (r"\b(4340)\s*(?:STEEL)?\b", "4340 STEEL"),
    (r"\bCARBON\s*STEEL\b", "CARBON STEEL"),
    (r"\bMILD\s*STEEL\b", "MILD STEEL"),
    (r"\bCRS\b", "COLD ROLLED STEEL"),
    (r"\bHRS\b", "HOT ROLLED STEEL"),
    # Tool Steel
    (r"\b(A2)\s*(?:TOOL\s*STEEL)?\b", "A2 TOOL STEEL"),
    (r"\b(D2)\s*(?:TOOL\s*STEEL)?\b", "D2 TOOL STEEL"),
    (r"\b(O1)\s*(?:TOOL\s*STEEL)?\b", "O1 TOOL STEEL"),
    (r"\bTOOL\s*STEEL\b", "TOOL STEEL"),
    # Brass and Bronze
    (r"\bBRASS\b", "BRASS"),
    (r"\bBRONZE\b", "BRONZE"),
    (r"\b(C360)\s*(?:BRASS)?\b", "C360 BRASS"),
    (r"\bPHOSPHOR\s*BRONZE\b", "PHOSPHOR BRONZE"),
    # Plastics and Polymers
    (r"\bDELRIN\b", "DELRIN"),
    (r"\bACETAL\b", "ACETAL"),
    (r"\bNYLON\b", "NYLON"),
    (r"\bPTFE\b", "PTFE"),
    (r"\bTEFLON\b", "PTFE"),
    (r"\bHDPE\b", "HDPE"),
    (r"\bUHMW(?:PE)?\b", "UHMW"),
    (r"\bABS\b", "ABS"),
    (r"\bPVC\b", "PVC"),
    (r"\bPOLYCARBONATE\b", "POLYCARBONATE"),
    (r"\bACRYLIC\b", "ACRYLIC"),
    (r"\bPEEK\b", "PEEK"),
    # Rubber and Elastomers
    (r"\bNEOPRENE\b", "NEOPRENE"),
    (r"\bVITON\b", "VITON"),
    (r"\bBUNA-N\b", "BUNA-N"),
    (r"\bSILICONE\b", "SILICONE RUBBER"),
    (r"\bEPDM\b", "EPDM"),
    # Specifications
    (r"\bASTM\s*([A-Z]?\d+)\b", "ASTM SPEC"),
    (r"\bAISI\s*(\d{4})\b", "AISI SPEC"),
    (r"\bSAE\s*(\d{4})\b", "SAE SPEC"),
    # General material callout patterns
    (r"MATERIAL[:\s]+([A-Z0-9\s\-\.]{3,30})", None),  # Extract as-is
    (r"MAT[:\s'L]+([A-Z0-9\s\-\.]{3,30})", None),  # Extract as-is
]


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


def extract_materials(text):
    """
    Extract material specifications from text using regex patterns.
    Returns list of unique material names.
    """
    materials = []
    seen = set()

    text_upper = text.upper()

    for pattern, normalized_name in MATERIAL_PATTERNS:
        try:
            matches = re.findall(pattern, text_upper, re.IGNORECASE)
            for match in matches:
                if normalized_name:
                    material_name = normalized_name
                else:
                    # Use matched text as-is
                    material_name = (
                        match.strip().upper()
                        if isinstance(match, str)
                        else str(match).strip().upper()
                    )

                # Clean up the material name
                material_name = re.sub(r"\s+", " ", material_name).strip()

                if material_name and len(material_name) >= 2 and material_name not in seen:
                    # Filter out noise
                    if not re.match(r"^[0-9]+$", material_name):  # Not just numbers
                        seen.add(material_name)
                        materials.append(material_name)
        except Exception:
            continue

    return materials


def main():
    parser = argparse.ArgumentParser(description="Index materials from extracted metadata")
    parser.add_argument("--dry-run", action="store_true", help="Count only, don't insert")
    parser.add_argument("--limit", type=int, default=0, help="Limit records to process (0 = all)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")
    parser.add_argument(
        "--reprocess", action="store_true", help="Reprocess all, including already indexed"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("B6: INDEX MATERIALS")
    print("=" * 70)
    if args.dry_run:
        print("MODE: DRY RUN")
    if args.reprocess:
        print("MODE: REPROCESS ALL")
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
            "materials_found": 0,
            "materials_inserted": 0,
            "duplicates_skipped": 0,
            "errors": 0,
        }

        material_counts = defaultdict(int)

        with conn.cursor() as cur:
            # Find extractions with text content
            logger.info("Finding extractions with text content...")

            # Build query based on options
            if args.reprocess:
                query = """
                    SELECT em.id, em.cloud_file_id, em.raw_data, em.source_type
                    FROM extracted_metadata em
                    WHERE em.extraction_status IN ('completed', 'skipped')
                    AND em.raw_data IS NOT NULL
                """
            else:
                # Only process records not yet checked for materials
                query = """
                    SELECT em.id, em.cloud_file_id, em.raw_data, em.source_type
                    FROM extracted_metadata em
                    WHERE em.extraction_status IN ('completed', 'skipped')
                    AND em.raw_data IS NOT NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM extracted_materials emat
                        WHERE emat.metadata_id = em.id
                    )
                """

            if args.limit > 0:
                query += f" LIMIT {args.limit}"

            cur.execute(query)
            records = cur.fetchall()

            logger.info(f"Found {len(records):,} records to process")

            if not records:
                print("\nNo records to process.")
                conn.close()
                return

            # Process each record
            for metadata_id, cloud_file_id, raw_data, source_type in tqdm(records, desc="Indexing"):
                try:
                    if not raw_data:
                        continue

                    data = raw_data if isinstance(raw_data, dict) else json.loads(raw_data)

                    # Collect all text content
                    all_text = []

                    # From text_blocks
                    text_blocks = data.get("text_blocks", [])
                    for block in text_blocks:
                        if isinstance(block, dict):
                            all_text.append(block.get("text", ""))
                        elif isinstance(block, str):
                            all_text.append(block)

                    # From text_entities (DXF)
                    text_entities = data.get("text_entities", [])
                    for entity in text_entities:
                        if isinstance(entity, dict):
                            all_text.append(entity.get("text", ""))
                        elif isinstance(entity, str):
                            all_text.append(entity)

                    # Pre-extracted materials
                    pre_materials = data.get("materials", [])
                    for mat in pre_materials:
                        if isinstance(mat, dict):
                            all_text.append(mat.get("material_name", ""))
                        elif isinstance(mat, str):
                            all_text.append(mat)

                    if not all_text:
                        continue

                    full_text = "\n".join(all_text)
                    materials = extract_materials(full_text)

                    if not materials:
                        continue

                    stats["records_processed"] += 1
                    stats["materials_found"] += len(materials)

                    # Track material frequency
                    for mat in materials:
                        material_counts[mat] += 1

                    if args.dry_run:
                        continue

                    # Insert materials
                    for material_name in materials[:20]:  # Limit per file
                        try:
                            cur.execute(
                                """
                                INSERT INTO extracted_materials 
                                (metadata_id, cloud_file_id, material_name)
                                VALUES (%s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """,
                                (metadata_id, cloud_file_id, material_name[:255]),
                            )

                            if cur.rowcount > 0:
                                stats["materials_inserted"] += 1
                            else:
                                stats["duplicates_skipped"] += 1

                        except Exception as e:
                            stats["errors"] += 1
                            logger.debug(f"Error inserting material: {e}")

                    # Commit in batches
                    if stats["records_processed"] % args.batch_size == 0:
                        conn.commit()

                except Exception as e:
                    stats["errors"] += 1
                    logger.warning(f"Error processing metadata {metadata_id}: {e}")

            # Final commit
            if not args.dry_run:
                conn.commit()

                # Update has_parameters flag on metadata records
                logger.info("Updating material flags...")
                cur.execute("""
                    UPDATE extracted_metadata em
                    SET has_parameters = EXISTS (
                        SELECT 1 FROM extracted_materials emat
                        WHERE emat.metadata_id = em.id
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
        print(f"Materials found:       {stats['materials_found']:,}")

        if args.dry_run:
            print(f"\nDRY RUN - No materials inserted")
        else:
            print(f"Materials inserted:    {stats['materials_inserted']:,}")
            print(f"Duplicates skipped:    {stats['duplicates_skipped']:,}")

        if stats["errors"] > 0:
            print(f"Errors:                {stats['errors']:,}")

        # Top materials found
        if material_counts:
            print("\n" + "=" * 70)
            print("TOP 20 MATERIALS FOUND")
            print("=" * 70)
            sorted_materials = sorted(material_counts.items(), key=lambda x: -x[1])[:20]
            for mat, count in sorted_materials:
                print(f"  {mat}: {count:,}")

        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": args.dry_run,
            "stats": stats,
            "top_materials": dict(sorted(material_counts.items(), key=lambda x: -x[1])[:50]),
        }

        report_file = OUTPUT_DIR / "B6-index-materials.json"
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
