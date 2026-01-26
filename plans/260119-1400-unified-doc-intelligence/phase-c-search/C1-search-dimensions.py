#!/usr/bin/env python3
"""
C1-search-dimensions.py
Search for engineering dimensions across extracted documents.

Usage:
    python C1-search-dimensions.py --value 45.5 --tolerance 0.1 --unit mm
    python C1-search-dimensions.py --min 40 --max 50 --unit mm
    python C1-search-dimensions.py --label "HOLE*" --limit 20

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

# Paths - go up to repo root, then to unified-doc-intelligence-deploy
SCRIPT_DIR = Path(__file__).parent.parent.parent / "unified-doc-intelligence-deploy"
CONFIG_FILE = SCRIPT_DIR / "config.txt"


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


def search_dimensions(
    conn,
    value=None,
    tolerance=None,
    min_val=None,
    max_val=None,
    unit=None,
    label=None,
    dimension_type=None,
    limit=100,
    offset=0,
):
    """
    Search extracted_dimensions table with various filters.

    Returns documents grouped by DocumentGroup with matching files and dimensions.
    """
    conditions = []
    params = []

    # Value with tolerance search
    if value is not None:
        if tolerance is not None:
            conditions.append("ed.value BETWEEN %s AND %s")
            params.extend([value - tolerance, value + tolerance])
        else:
            conditions.append("ed.value = %s")
            params.append(value)

    # Range search
    if min_val is not None:
        conditions.append("ed.value >= %s")
        params.append(min_val)
    if max_val is not None:
        conditions.append("ed.value <= %s")
        params.append(max_val)

    # Unit filter
    if unit:
        conditions.append("LOWER(ed.unit) = LOWER(%s)")
        params.append(unit)

    # Label filter (supports wildcards with ILIKE)
    if label:
        if "*" in label or "%" in label:
            label_pattern = label.replace("*", "%")
            conditions.append("ed.label ILIKE %s")
            params.append(label_pattern)
        else:
            conditions.append("ed.label ILIKE %s")
            params.append(f"%{label}%")

    # Dimension type filter
    if dimension_type:
        conditions.append("ed.dimension_type = %s::dimension_type")
        params.append(dimension_type)

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    # Main query: Get dimensions with DocumentGroup info
    query = f"""
        WITH matching_dimensions AS (
            SELECT 
                ed.id AS dimension_id,
                ed.value,
                ed.unit,
                ed.tolerance_plus,
                ed.tolerance_minus,
                ed.tolerance_type,
                ed.label,
                ed.dimension_type,
                ed.layer,
                ed.source_page,
                ed.cloud_file_id,
                em.id AS metadata_id
            FROM extracted_dimensions ed
            JOIN extracted_metadata em ON ed.metadata_id = em.id
            WHERE {where_clause}
            ORDER BY ed.value
            LIMIT %s OFFSET %s
        ),
        dimension_files AS (
            SELECT DISTINCT
                md.dimension_id,
                md.value,
                md.unit,
                md.tolerance_plus,
                md.tolerance_minus,
                md.tolerance_type,
                md.label,
                md.dimension_type,
                md.layer,
                md.source_page,
                cf."ID" AS file_id,
                cf."FileType" AS file_type,
                cf."LocalPath" AS file_path,
                cf."CloudKey" AS filename,
                cf.document_group_id,
                dg.id AS group_id,
                dg.name AS group_name,
                dg.project_code,
                dg.item_number
            FROM matching_dimensions md
            JOIN "CloudFiles" cf ON md.cloud_file_id = cf."ID"
            LEFT JOIN document_groups dg ON cf.document_group_id = dg.id
        )
        SELECT * FROM dimension_files
        ORDER BY group_id NULLS LAST, file_id
    """

    params.extend([limit, offset])

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

        # Get total count
        count_query = f"""
            SELECT COUNT(*) 
            FROM extracted_dimensions ed
            JOIN extracted_metadata em ON ed.metadata_id = em.id
            WHERE {where_clause}
        """
        cur.execute(count_query, params[:-2])  # Exclude limit/offset
        total = cur.fetchone()["count"]

    # Group results by DocumentGroup
    groups = {}
    for row in rows:
        group_id = row["group_id"] or f"ungrouped_{row['file_id']}"

        if group_id not in groups:
            groups[group_id] = {
                "document_group": {
                    "id": row["group_id"],
                    "name": row["group_name"],
                    "project_code": row["project_code"],
                    "item_number": row["item_number"],
                }
                if row["group_id"]
                else None,
                "files": {},
                "matches": [],
            }

        # Add file if not already present
        file_id = row["file_id"]
        if file_id not in groups[group_id]["files"]:
            groups[group_id]["files"][file_id] = {
                "id": file_id,
                "type": row["file_type"],
                "path": row["file_path"],
                "filename": row["filename"],
                "match_details": [],
            }

        # Add dimension match
        match_detail = {
            "dimension_id": row["dimension_id"],
            "value": row["value"],
            "unit": row["unit"],
            "label": row["label"],
            "dimension_type": row["dimension_type"],
            "layer": row["layer"],
            "page": row["source_page"],
        }

        if row["tolerance_plus"] or row["tolerance_minus"]:
            match_detail["tolerance"] = {
                "plus": row["tolerance_plus"],
                "minus": row["tolerance_minus"],
                "type": row["tolerance_type"],
            }

        groups[group_id]["files"][file_id]["match_details"].append(match_detail)

    # Convert files dict to list
    results = []
    for group_data in groups.values():
        group_data["files"] = list(group_data["files"].values())
        results.append(group_data)

    return {
        "query": {
            "type": "dimension",
            "value": value,
            "tolerance": tolerance,
            "min": min_val,
            "max": max_val,
            "unit": unit,
            "label": label,
            "dimension_type": dimension_type,
        },
        "pagination": {"limit": limit, "offset": offset, "total": total},
        "result_count": len(results),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Search engineering dimensions across extracted documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for exact dimension with tolerance
  python C1-search-dimensions.py --value 45.5 --tolerance 0.1 --unit mm

  # Search dimension range
  python C1-search-dimensions.py --min 40 --max 50 --unit mm

  # Search by label pattern
  python C1-search-dimensions.py --label "HOLE*"

  # Search diameter dimensions
  python C1-search-dimensions.py --type diameter --min 10
        """,
    )

    # Value search options
    parser.add_argument("--value", "-v", type=float, help="Exact dimension value to search")
    parser.add_argument(
        "--tolerance",
        "-t",
        type=float,
        default=None,
        help="Tolerance around value (e.g., 0.1 means +/- 0.1)",
    )

    # Range search options
    parser.add_argument("--min", type=float, dest="min_val", help="Minimum dimension value")
    parser.add_argument("--max", type=float, dest="max_val", help="Maximum dimension value")

    # Filter options
    parser.add_argument(
        "--unit", "-u", type=str, default=None, help="Unit filter (mm, in, deg, etc.)"
    )
    parser.add_argument("--label", "-l", type=str, help="Label pattern (supports * wildcards)")
    parser.add_argument(
        "--type",
        dest="dimension_type",
        type=str,
        choices=["linear", "angular", "radial", "diameter", "ordinate", "arc_length", "tolerance"],
        help="Dimension type filter",
    )

    # Pagination
    parser.add_argument("--limit", type=int, default=100, help="Maximum results (default: 100)")
    parser.add_argument("--offset", type=int, default=0, help="Result offset for pagination")

    # Output options
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    args = parser.parse_args()

    # Validate arguments
    if args.value is None and args.min_val is None and args.max_val is None and args.label is None:
        parser.error("At least one search criterion required: --value, --min, --max, or --label")

    # Load config and connect
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        logger.error("NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    try:
        conn = psycopg2.connect(db_url)
        logger.info("Connected to database")

        results = search_dimensions(
            conn,
            value=args.value,
            tolerance=args.tolerance,
            min_val=args.min_val,
            max_val=args.max_val,
            unit=args.unit,
            label=args.label,
            dimension_type=args.dimension_type,
            limit=args.limit,
            offset=args.offset,
        )

        conn.close()

        # Output JSON
        indent = 2 if args.pretty else None
        print(json.dumps(results, indent=indent, default=decimal_default))

        logger.info(
            f"Found {results['pagination']['total']} total matches, "
            f"returned {results['result_count']} groups"
        )

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        error_result = {"error": str(e), "query": vars(args)}
        print(json.dumps(error_result))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
