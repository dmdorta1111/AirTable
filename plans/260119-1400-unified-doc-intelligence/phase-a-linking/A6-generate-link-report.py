#!/usr/bin/env python3
"""
A6-generate-link-report.py
Generates comprehensive summary statistics for the linking phase.

Outputs: output/linking-report.json

Usage: python A6-generate-link-report.py
"""

import sys
import logging
import json
from datetime import datetime
from pathlib import Path

import psycopg2
from tabulate import tabulate

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
    print("A6: GENERATE LINK REPORT")
    print("=" * 70)
    print("Generating comprehensive linking statistics")
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
        conn.autocommit = True

        logger.info("Connected successfully!")

        report = {
            "timestamp": datetime.now().isoformat(),
            "phase": "A - Auto-Linking",
            "summary": {},
            "by_linking_method": {},
            "by_confidence_level": {},
            "by_role": {},
            "by_project_code": {},
            "orphan_files": {},
            "review_queue": {},
        }

        with conn.cursor() as cur:
            # 1. Overall Summary
            logger.info("Gathering overall statistics...")

            cur.execute('SELECT COUNT(*) FROM "CloudFiles"')
            total_files = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM document_groups")
            total_groups = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM document_group_members")
            total_members = cur.fetchone()[0]

            cur.execute('SELECT COUNT(*) FROM "CloudFiles" WHERE document_group_id IS NOT NULL')
            linked_files = cur.fetchone()[0]

            cur.execute('SELECT COUNT(*) FROM "CloudFiles" WHERE document_group_id IS NULL')
            orphan_files = cur.fetchone()[0]

            report["summary"] = {
                "total_files": total_files,
                "total_groups": total_groups,
                "total_members": total_members,
                "linked_files": linked_files,
                "orphan_files": orphan_files,
                "link_rate_percent": round(100 * linked_files / total_files, 2)
                if total_files > 0
                else 0,
            }

            # 2. By Linking Method
            logger.info("Gathering statistics by linking method...")

            cur.execute("""
                SELECT 
                    linking_method::text,
                    COUNT(*) as group_count,
                    AVG(linking_confidence) as avg_confidence,
                    SUM(CASE WHEN needs_review THEN 1 ELSE 0 END) as needs_review
                FROM document_groups
                GROUP BY linking_method
                ORDER BY group_count DESC
            """)

            for method, count, avg_conf, needs_rev in cur.fetchall():
                report["by_linking_method"][method] = {
                    "group_count": count,
                    "avg_confidence": round(float(avg_conf), 3) if avg_conf else 0,
                    "needs_review": needs_rev,
                }

            # 3. By Confidence Level
            logger.info("Gathering statistics by confidence level...")

            cur.execute("""
                SELECT 
                    CASE 
                        WHEN linking_confidence >= 0.95 THEN 'high (>=0.95)'
                        WHEN linking_confidence >= 0.80 THEN 'medium (0.80-0.94)'
                        WHEN linking_confidence >= 0.70 THEN 'low (0.70-0.79)'
                        ELSE 'very_low (<0.70)'
                    END as confidence_level,
                    COUNT(*) as group_count
                FROM document_groups
                GROUP BY 1
                ORDER BY 1
            """)

            for level, count in cur.fetchall():
                report["by_confidence_level"][level] = count

            # 4. By Role
            logger.info("Gathering statistics by document role...")

            cur.execute("""
                SELECT 
                    role::text,
                    COUNT(*) as member_count,
                    COUNT(DISTINCT group_id) as group_count
                FROM document_group_members
                GROUP BY role
                ORDER BY member_count DESC
            """)

            for role, member_count, group_count in cur.fetchall():
                report["by_role"][role] = {"member_count": member_count, "group_count": group_count}

            # 5. Top Project Codes
            logger.info("Gathering top project codes...")

            cur.execute("""
                SELECT 
                    project_code,
                    COUNT(*) as group_count
                FROM document_groups
                WHERE project_code IS NOT NULL
                GROUP BY project_code
                ORDER BY group_count DESC
                LIMIT 25
            """)

            for code, count in cur.fetchall():
                report["by_project_code"][code] = count

            # 6. Orphan Files Analysis
            logger.info("Analyzing orphan files...")

            cur.execute("""
                SELECT 
                    LOWER(
                        CASE 
                            WHEN "CloudKey" LIKE '%.%' 
                            THEN SUBSTRING("CloudKey" FROM '\.([^.]+)$')
                            ELSE 'no_extension'
                        END
                    ) as ext,
                    COUNT(*) as file_count
                FROM "CloudFiles"
                WHERE document_group_id IS NULL
                GROUP BY 1
                ORDER BY file_count DESC
                LIMIT 20
            """)

            orphan_by_ext = {}
            for ext, count in cur.fetchall():
                orphan_by_ext[ext or "no_extension"] = count

            report["orphan_files"] = {"total": orphan_files, "by_extension": orphan_by_ext}

            # 7. Review Queue Summary
            logger.info("Gathering review queue statistics...")

            cur.execute("""
                SELECT 
                    COUNT(*) as total_needing_review,
                    AVG(linking_confidence) as avg_confidence
                FROM document_groups
                WHERE needs_review = TRUE
            """)

            review_total, review_avg_conf = cur.fetchone()

            cur.execute("""
                SELECT 
                    linking_method::text,
                    COUNT(*) as count
                FROM document_groups
                WHERE needs_review = TRUE
                GROUP BY linking_method
            """)

            review_by_method = {method: count for method, count in cur.fetchall()}

            report["review_queue"] = {
                "total_needing_review": review_total or 0,
                "avg_confidence": round(float(review_avg_conf), 3) if review_avg_conf else 0,
                "by_linking_method": review_by_method,
            }

        conn.close()

        # Print Summary Report
        print("\n" + "=" * 70)
        print("LINKING REPORT SUMMARY")
        print("=" * 70)

        summary = report["summary"]
        print(f"\n{'=' * 40}")
        print("OVERALL STATISTICS")
        print(f"{'=' * 40}")
        print(f"Total CloudFiles:         {summary['total_files']:,}")
        print(f"DocumentGroups created:   {summary['total_groups']:,}")
        print(f"Files linked:             {summary['linked_files']:,}")
        print(f"Orphan files:             {summary['orphan_files']:,}")
        print(f"Link rate:                {summary['link_rate_percent']:.1f}%")

        print(f"\n{'=' * 40}")
        print("BY LINKING METHOD")
        print(f"{'=' * 40}")
        method_table = [
            [method, data["group_count"], f"{data['avg_confidence']:.2f}", data["needs_review"]]
            for method, data in report["by_linking_method"].items()
        ]
        print(
            tabulate(
                method_table, headers=["Method", "Groups", "Avg Conf", "Review"], tablefmt="simple"
            )
        )

        print(f"\n{'=' * 40}")
        print("BY CONFIDENCE LEVEL")
        print(f"{'=' * 40}")
        for level, count in report["by_confidence_level"].items():
            print(f"  {level}: {count:,}")

        print(f"\n{'=' * 40}")
        print("BY DOCUMENT ROLE")
        print(f"{'=' * 40}")
        role_table = [
            [role, data["member_count"], data["group_count"]]
            for role, data in report["by_role"].items()
        ]
        print(tabulate(role_table, headers=["Role", "Members", "Groups"], tablefmt="simple"))

        print(f"\n{'=' * 40}")
        print("REVIEW QUEUE")
        print(f"{'=' * 40}")
        rq = report["review_queue"]
        print(f"Total needing review:     {rq['total_needing_review']:,}")
        print(f"Average confidence:       {rq['avg_confidence']:.2f}")

        print(f"\n{'=' * 40}")
        print("TOP 10 PROJECT CODES")
        print(f"{'=' * 40}")
        for i, (code, count) in enumerate(list(report["by_project_code"].items())[:10], 1):
            print(f"  {i:2}. {code}: {count:,} groups")

        # Save report
        report_file = OUTPUT_DIR / "linking-report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n{'=' * 70}")
        print(f"✓ Full report saved to: {report_file}")
        print(f"{'=' * 70}")

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.close()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
