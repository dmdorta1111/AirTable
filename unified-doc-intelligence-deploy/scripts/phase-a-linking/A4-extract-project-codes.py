#!/usr/bin/env python3
"""
A4-extract-project-codes.py
Parses CloudKey paths to extract project codes and item numbers.

Path pattern: "JOBS CUSTOM FAB\\88000\\88617_PROJECT_NAME\\..." → project_code = "88617"
Filename pattern: "88617-001-BRACKET.pdf" → item_number = "88617-001"

Updates DocumentGroups with extracted project_code and item_number.

Usage: python A4-extract-project-codes.py
"""

import sys
import logging
import json
import re
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

# Regex patterns for project code extraction
PROJECT_CODE_PATTERNS = [
    # Pattern 1: "88000\88617_PROJECT_NAME" → 88617
    r"\\(\d{5,6})_",
    # Pattern 2: "JOBS CUSTOM FAB/88617/" → 88617
    r"/(\d{5,6})/",
    # Pattern 3: folder name is just the code "88617"
    r"[/\\](\d{5,6})[/\\]",
]

# Regex patterns for item number extraction from filenames
ITEM_NUMBER_PATTERNS = [
    # Pattern 1: "88617-001" (5-6 digit code, dash, 2-4 digit item)
    r"^(\d{5,6}-\d{2,4})",
    # Pattern 2: "PRJ-12345-001" (prefix, code, item)
    r"^([A-Z]{2,4}-\d{4,6}-\d{2,4})",
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


def extract_project_code(path):
    """Extract project code from a file path."""
    if not path:
        return None

    for pattern in PROJECT_CODE_PATTERNS:
        match = re.search(pattern, path)
        if match:
            return match.group(1)

    return None


def extract_item_number(basename):
    """Extract item number from a file basename (name without extension)."""
    if not basename:
        return None

    for pattern in ITEM_NUMBER_PATTERNS:
        match = re.match(pattern, basename)
        if match:
            return match.group(1)

    return None


def main():
    print("=" * 70)
    print("A4: EXTRACT PROJECT CODES")
    print("=" * 70)
    print("Parsing paths to extract project codes and item numbers")
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

        with conn.cursor() as cur:
            # Step 1: Get all DocumentGroups with their member file paths
            logger.info("Fetching DocumentGroups with member paths...")
            cur.execute("""
                SELECT 
                    dg.id,
                    dg.name,
                    dg.project_code,
                    dg.item_number,
                    ARRAY_AGG(cf."CloudKey") as cloud_keys
                FROM document_groups dg
                LEFT JOIN document_group_members dgm ON dg.id = dgm.group_id
                LEFT JOIN "CloudFiles" cf ON dgm.cloud_file_id = cf."ID"
                GROUP BY dg.id, dg.name, dg.project_code, dg.item_number
            """)

            groups = cur.fetchall()
            logger.info(f"Found {len(groups):,} DocumentGroups")

            # Step 2: Extract project codes and item numbers
            updates = []
            project_codes_found = 0
            item_numbers_found = 0

            for group_id, name, existing_project, existing_item, cloud_keys in tqdm(
                groups, desc="Extracting"
            ):
                project_code = existing_project
                item_number = existing_item

                # Try to extract from cloud_keys if not already set
                if not project_code and cloud_keys:
                    for key in cloud_keys:
                        if key:
                            extracted = extract_project_code(key)
                            if extracted:
                                project_code = extracted
                                project_codes_found += 1
                                break

                # Try to extract item number from group name
                if not item_number and name:
                    extracted = extract_item_number(name)
                    if extracted:
                        item_number = extracted
                        item_numbers_found += 1

                # Only update if we found something new
                if (project_code and project_code != existing_project) or (
                    item_number and item_number != existing_item
                ):
                    updates.append((project_code, item_number, group_id))

            # Step 3: Apply updates
            if updates:
                logger.info(f"Updating {len(updates):,} DocumentGroups...")

                for project_code, item_number, group_id in tqdm(updates, desc="Updating"):
                    cur.execute(
                        """
                        UPDATE document_groups
                        SET project_code = COALESCE(%s, project_code),
                            item_number = COALESCE(%s, item_number),
                            updated_at = NOW()
                        WHERE id = %s
                    """,
                        (project_code, item_number, group_id),
                    )

                conn.commit()
                logger.info("Updates committed successfully")
            else:
                logger.info("No updates needed")

            # Step 4: Generate statistics
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(project_code) as with_project_code,
                    COUNT(item_number) as with_item_number,
                    COUNT(CASE WHEN project_code IS NOT NULL AND item_number IS NOT NULL THEN 1 END) as with_both
                FROM document_groups
            """)

            stats = cur.fetchone()
            total, with_project, with_item, with_both = stats

            # Get project code distribution
            cur.execute("""
                SELECT project_code, COUNT(*) as cnt
                FROM document_groups
                WHERE project_code IS NOT NULL
                GROUP BY project_code
                ORDER BY cnt DESC
                LIMIT 20
            """)

            project_distribution = cur.fetchall()

            # Print summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Total DocumentGroups:       {total:,}")
            print(
                f"With project_code:          {with_project:,} ({100 * with_project / total:.1f}%)"
            )
            print(f"With item_number:           {with_item:,} ({100 * with_item / total:.1f}%)")
            print(f"With both:                  {with_both:,} ({100 * with_both / total:.1f}%)")
            print(f"\nNewly extracted:")
            print(f"  Project codes:            {project_codes_found:,}")
            print(f"  Item numbers:             {item_numbers_found:,}")

            if project_distribution:
                print(f"\nTop Project Codes:")
                for code, count in project_distribution[:10]:
                    print(f"  {code}: {count:,} groups")

        conn.close()

        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_groups": total,
            "with_project_code": with_project,
            "with_item_number": with_item,
            "with_both": with_both,
            "newly_extracted_project_codes": project_codes_found,
            "newly_extracted_item_numbers": item_numbers_found,
            "updates_applied": len(updates),
            "top_project_codes": {code: count for code, count in project_distribution},
        }

        report_file = OUTPUT_DIR / "A4-project-codes.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n✓ Report saved to: {report_file}")

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
