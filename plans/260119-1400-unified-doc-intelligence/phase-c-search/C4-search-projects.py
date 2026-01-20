#!/usr/bin/env python3
"""
C4-search-projects.py
Search by project code to find all related DocumentGroups and files.

Usage:
    python C4-search-projects.py --code 88617
    python C4-search-projects.py --code "PRJ-2024*" --stats

Outputs JSON results to stdout.
"""

import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

# Setup logging (to stderr to keep stdout clean for JSON)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
PLAN_DIR = SCRIPT_DIR.parent
CONFIG_FILE = PLAN_DIR / "config.txt"


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


def decimal_default(obj):
    """JSON serializer for Decimal objects."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def search_projects(conn, code, include_stats=False, limit=100, offset=0):
    """
    Search by project code to find all DocumentGroups and their files.

    Args:
        code: Project code to search (supports wildcards)
        include_stats: Include file type statistics
    """
    # Build condition based on wildcard presence
    if "*" in code or "%" in code:
        code_pattern = code.replace("*", "%")
        code_condition = "dg.project_code ILIKE %s"
        code_param = code_pattern
    else:
        code_condition = "dg.project_code = %s"
        code_param = code

    # Main query: Get DocumentGroups matching project code
    query = f"""
        WITH matching_groups AS (
            SELECT 
                dg.id,
                dg.name,
                dg.project_code,
                dg.item_number,
                dg.description,
                dg.linking_method,
                dg.linking_confidence,
                dg.needs_review,
                dg.created_at
            FROM document_groups dg
            WHERE {code_condition}
            ORDER BY dg.name
            LIMIT %s OFFSET %s
        ),
        group_members AS (
            SELECT 
                mg.*,
                dgm.id AS member_id,
                dgm.role,
                dgm.is_primary,
                dgm.cloud_file_id,
                cf."ID" AS file_id,
                cf."Type" AS file_type,
                cf."FullPath" AS file_path,
                cf."Filename" AS filename,
                cf."Size" AS file_size,
                cf.extraction_status
            FROM matching_groups mg
            JOIN document_group_members dgm ON mg.id = dgm.group_id
            LEFT JOIN "CloudFiles" cf ON dgm.cloud_file_id = cf."ID"
        )
        SELECT * FROM group_members
        ORDER BY id, role, filename
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, [code_param, limit, offset])
        rows = cur.fetchall()

        # Get total count of groups
        count_query = f"""
            SELECT COUNT(DISTINCT id) 
            FROM document_groups dg
            WHERE {code_condition}
        """
        cur.execute(count_query, [code_param])
        total_groups = cur.fetchone()["count"]

        # Get stats if requested
        stats = None
        if include_stats:
            stats_query = f"""
                SELECT 
                    COUNT(DISTINCT dg.id) AS group_count,
                    COUNT(DISTINCT cf."ID") AS file_count,
                    COUNT(DISTINCT cf."ID") FILTER (WHERE cf."Type" = 'pdf') AS pdf_count,
                    COUNT(DISTINCT cf."ID") FILTER (WHERE cf."Type" = 'dxf') AS dxf_count,
                    COUNT(DISTINCT cf."ID") FILTER (WHERE cf."Type" IN ('prt', 'asm')) AS cad_count,
                    SUM(cf."Size") AS total_size,
                    COUNT(DISTINCT cf."ID") FILTER (WHERE cf.extraction_status = 'completed') AS extracted_count,
                    COUNT(DISTINCT cf."ID") FILTER (WHERE cf.extraction_status = 'pending') AS pending_count
                FROM document_groups dg
                LEFT JOIN document_group_members dgm ON dg.id = dgm.group_id
                LEFT JOIN "CloudFiles" cf ON dgm.cloud_file_id = cf."ID"
                WHERE {code_condition}
            """
            cur.execute(stats_query, [code_param])
            stats_row = cur.fetchone()
            stats = {
                "group_count": stats_row["group_count"],
                "file_count": stats_row["file_count"],
                "by_type": {
                    "pdf": stats_row["pdf_count"],
                    "dxf": stats_row["dxf_count"],
                    "cad": stats_row["cad_count"],
                },
                "total_size_bytes": stats_row["total_size"],
                "extraction": {
                    "completed": stats_row["extracted_count"],
                    "pending": stats_row["pending_count"],
                },
            }

    # Group results by DocumentGroup
    groups = {}
    for row in rows:
        group_id = row["id"]

        if group_id not in groups:
            groups[group_id] = {
                "document_group": {
                    "id": row["id"],
                    "name": row["name"],
                    "project_code": row["project_code"],
                    "item_number": row["item_number"],
                    "description": row["description"],
                    "linking_method": row["linking_method"],
                    "linking_confidence": row["linking_confidence"],
                    "needs_review": row["needs_review"],
                    "created_at": row["created_at"],
                },
                "files": [],
                "primary_file": None,
            }

        # Add file info
        if row["file_id"]:
            file_info = {
                "id": row["file_id"],
                "type": row["file_type"],
                "path": row["file_path"],
                "filename": row["filename"],
                "size": row["file_size"],
                "role": row["role"],
                "extraction_status": row["extraction_status"],
            }

            groups[group_id]["files"].append(file_info)

            if row["is_primary"]:
                groups[group_id]["primary_file"] = file_info

    results = list(groups.values())

    response = {
        "query": {"type": "project", "code": code},
        "pagination": {"limit": limit, "offset": offset, "total": total_groups},
        "result_count": len(results),
        "results": results,
    }

    if stats:
        response["statistics"] = stats

    return response


def main():
    parser = argparse.ArgumentParser(
        description="Search by project code to find all DocumentGroups and files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for exact project code
  python C4-search-projects.py --code 88617

  # Search with wildcard
  python C4-search-projects.py --code "PRJ-2024*"

  # Include file statistics
  python C4-search-projects.py --code 88617 --stats
        """,
    )

    # Search options
    parser.add_argument(
        "--code",
        "-c",
        type=str,
        required=True,
        help="Project code to search (supports * wildcards)",
    )

    # Options
    parser.add_argument(
        "--stats",
        "-s",
        action="store_true",
        dest="include_stats",
        help="Include file type statistics in response",
    )

    # Pagination
    parser.add_argument("--limit", type=int, default=100, help="Maximum results (default: 100)")
    parser.add_argument("--offset", type=int, default=0, help="Result offset for pagination")

    # Output options
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    args = parser.parse_args()

    # Load config and connect
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        logger.error("NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    try:
        conn = psycopg2.connect(db_url)
        logger.info("Connected to database")

        results = search_projects(
            conn,
            code=args.code,
            include_stats=args.include_stats,
            limit=args.limit,
            offset=args.offset,
        )

        conn.close()

        # Output JSON
        indent = 2 if args.pretty else None
        print(json.dumps(results, indent=indent, default=decimal_default))

        logger.info(
            f"Found {results['pagination']['total']} document groups for project '{args.code}'"
        )

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        error_result = {"error": str(e), "query": {"code": args.code}}
        print(json.dumps(error_result))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
