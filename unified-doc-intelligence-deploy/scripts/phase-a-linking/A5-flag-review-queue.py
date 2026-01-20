#!/usr/bin/env python3
"""
A5-flag-review-queue.py
Flags DocumentGroups that need human review.

Criteria for flagging:
1. linking_confidence < 0.75
2. Groups with conflicting file types (e.g., multiple PDFs)
3. Groups with only one member (orphaned links)

Usage: python A5-flag-review-queue.py
"""

import sys
import logging
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

# Review thresholds
LOW_CONFIDENCE_THRESHOLD = 0.75


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


def main():
    print("=" * 70)
    print("A5: FLAG REVIEW QUEUE")
    print("=" * 70)
    print(f"Flagging groups with confidence < {LOW_CONFIDENCE_THRESHOLD}")
    print("and groups with conflicting file types")
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
            # Reset all needs_review flags first
            logger.info("Resetting existing review flags...")
            cur.execute("UPDATE document_groups SET needs_review = FALSE")

            # Flag 1: Low confidence groups
            logger.info(f"Flagging low confidence groups (< {LOW_CONFIDENCE_THRESHOLD})...")
            cur.execute(
                """
                UPDATE document_groups
                SET needs_review = TRUE
                WHERE linking_confidence < %s
                RETURNING id
            """,
                (LOW_CONFIDENCE_THRESHOLD,),
            )

            low_confidence_count = len(cur.fetchall())
            logger.info(f"  Flagged {low_confidence_count:,} low confidence groups")

            # Flag 2: Groups with multiple files of the same role (conflicts)
            logger.info("Flagging groups with conflicting file types...")
            cur.execute("""
                WITH role_counts AS (
                    SELECT 
                        group_id,
                        role,
                        COUNT(*) as cnt
                    FROM document_group_members
                    GROUP BY group_id, role
                    HAVING COUNT(*) > 1
                )
                UPDATE document_groups dg
                SET needs_review = TRUE
                FROM role_counts rc
                WHERE dg.id = rc.group_id
                AND dg.needs_review = FALSE
                RETURNING dg.id
            """)

            conflict_count = len(cur.fetchall())
            logger.info(f"  Flagged {conflict_count:,} groups with role conflicts")

            # Flag 3: Groups with only one member (orphaned)
            logger.info("Flagging single-member groups...")
            cur.execute("""
                WITH member_counts AS (
                    SELECT 
                        group_id,
                        COUNT(*) as member_count
                    FROM document_group_members
                    GROUP BY group_id
                    HAVING COUNT(*) = 1
                )
                UPDATE document_groups dg
                SET needs_review = TRUE
                FROM member_counts mc
                WHERE dg.id = mc.group_id
                AND dg.needs_review = FALSE
                RETURNING dg.id
            """)

            orphan_count = len(cur.fetchall())
            logger.info(f"  Flagged {orphan_count:,} single-member groups")

            # Commit changes
            conn.commit()

            # Generate statistics
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN needs_review THEN 1 ELSE 0 END) as needs_review,
                    SUM(CASE WHEN NOT needs_review THEN 1 ELSE 0 END) as verified
                FROM document_groups
            """)

            total, needs_review, verified = cur.fetchone()

            # Get breakdown by linking method
            cur.execute("""
                SELECT 
                    linking_method,
                    COUNT(*) as total,
                    SUM(CASE WHEN needs_review THEN 1 ELSE 0 END) as flagged
                FROM document_groups
                GROUP BY linking_method
                ORDER BY linking_method
            """)

            method_breakdown = cur.fetchall()

            # Get sample of flagged groups
            cur.execute("""
                SELECT 
                    dg.id,
                    dg.name,
                    dg.linking_method,
                    dg.linking_confidence,
                    COUNT(dgm.id) as member_count
                FROM document_groups dg
                LEFT JOIN document_group_members dgm ON dg.id = dgm.group_id
                WHERE dg.needs_review = TRUE
                GROUP BY dg.id, dg.name, dg.linking_method, dg.linking_confidence
                ORDER BY dg.linking_confidence ASC
                LIMIT 20
            """)

            sample_flagged = cur.fetchall()

            # Print summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Total DocumentGroups:     {total:,}")
            print(f"Needs review:             {needs_review:,} ({100 * needs_review / total:.1f}%)")
            print(f"Verified (no review):     {verified:,} ({100 * verified / total:.1f}%)")

            print(f"\nFlagging Breakdown:")
            print(f"  Low confidence:         {low_confidence_count:,}")
            print(f"  Role conflicts:         {conflict_count:,}")
            print(f"  Single-member:          {orphan_count:,}")

            print(f"\nBy Linking Method:")
            for method, method_total, flagged in method_breakdown:
                pct = 100 * flagged / method_total if method_total > 0 else 0
                print(f"  {method}: {flagged:,}/{method_total:,} flagged ({pct:.1f}%)")

            if sample_flagged:
                print(f"\nSample Flagged Groups (lowest confidence):")
                for gid, name, method, conf, members in sample_flagged[:10]:
                    print(f"  [{gid}] {name[:40]:<40} conf={conf:.2f} members={members}")

        conn.close()

        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_groups": total,
            "needs_review": needs_review,
            "verified": verified,
            "flagging_breakdown": {
                "low_confidence": low_confidence_count,
                "role_conflicts": conflict_count,
                "single_member": orphan_count,
            },
            "by_linking_method": {
                method: {"total": t, "flagged": f} for method, t, f in method_breakdown
            },
            "sample_flagged": [
                {
                    "id": gid,
                    "name": name,
                    "method": str(method),
                    "confidence": float(conf),
                    "member_count": members,
                }
                for gid, name, method, conf, members in sample_flagged
            ],
        }

        report_file = OUTPUT_DIR / "A5-review-queue.json"
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
