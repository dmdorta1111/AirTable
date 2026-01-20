#!/usr/bin/env python3
"""
C2-search-parameters.py
Search for CAD parameters across extracted documents.

Usage:
    python C2-search-parameters.py --name MATERIAL --value "304*"
    python C2-search-parameters.py --name WEIGHT --numeric-min 10 --numeric-max 100
    python C2-search-parameters.py --category material --limit 50

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


def search_parameters(
    conn,
    name=None,
    value=None,
    numeric_min=None,
    numeric_max=None,
    category=None,
    designated_only=False,
    limit=100,
    offset=0,
):
    """
    Search extracted_parameters table with various filters.

    Supports:
    - Name matching (exact, ILIKE with wildcards)
    - Value matching (text with wildcards)
    - Numeric range queries
    - Category filtering
    - Designated parameter filtering
    """
    conditions = []
    params = []

    # Name filter (supports wildcards)
    if name:
        if "*" in name or "%" in name:
            name_pattern = name.replace("*", "%")
            conditions.append("ep.name ILIKE %s")
            params.append(name_pattern)
        else:
            # Exact match (case-insensitive)
            conditions.append("LOWER(ep.name) = LOWER(%s)")
            params.append(name)

    # Value filter (supports wildcards)
    if value:
        if "*" in value or "%" in value:
            value_pattern = value.replace("*", "%")
            conditions.append("ep.value ILIKE %s")
            params.append(value_pattern)
        else:
            # Fuzzy match using trigram similarity
            conditions.append("(ep.value ILIKE %s OR similarity(ep.value, %s) > 0.3)")
            params.extend([f"%{value}%", value])

    # Numeric range queries
    if numeric_min is not None:
        conditions.append("ep.value_numeric >= %s")
        params.append(numeric_min)
    if numeric_max is not None:
        conditions.append("ep.value_numeric <= %s")
        params.append(numeric_max)

    # Category filter
    if category:
        conditions.append("LOWER(ep.category) = LOWER(%s)")
        params.append(category)

    # Designated parameters only
    if designated_only:
        conditions.append("ep.is_designated = TRUE")

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    # Main query
    query = f"""
        WITH matching_params AS (
            SELECT 
                ep.id AS param_id,
                ep.name,
                ep.value,
                ep.value_numeric,
                ep.value_type,
                ep.category,
                ep.is_designated,
                ep.units,
                em.id AS metadata_id,
                em.cloud_file_id,
                em.cad_model_id
            FROM extracted_parameters ep
            JOIN extracted_metadata em ON ep.metadata_id = em.id
            WHERE {where_clause}
            ORDER BY ep.name, ep.value
            LIMIT %s OFFSET %s
        ),
        param_files AS (
            SELECT 
                mp.*,
                cf."ID" AS file_id,
                cf."Type" AS file_type,
                cf."FullPath" AS file_path,
                cf."Filename" AS filename,
                cf.document_group_id,
                dg.id AS group_id,
                dg.name AS group_name,
                dg.project_code,
                dg.item_number
            FROM matching_params mp
            LEFT JOIN "CloudFiles" cf ON mp.cloud_file_id = cf."ID"
            LEFT JOIN document_groups dg ON cf.document_group_id = dg.id
        )
        SELECT * FROM param_files
        ORDER BY group_id NULLS LAST, file_id NULLS LAST
    """

    params.extend([limit, offset])

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

        # Get total count
        count_query = f"""
            SELECT COUNT(*) 
            FROM extracted_parameters ep
            JOIN extracted_metadata em ON ep.metadata_id = em.id
            WHERE {where_clause}
        """
        cur.execute(count_query, params[:-2])  # Exclude limit/offset
        total = cur.fetchone()["count"]

    # Group results by DocumentGroup
    groups = {}
    for row in rows:
        group_id = row["group_id"] or f"ungrouped_{row['file_id'] or row['cad_model_id']}"

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
                "parameters": [],
            }

        # Add file if present
        file_id = row["file_id"]
        if file_id and file_id not in groups[group_id]["files"]:
            groups[group_id]["files"][file_id] = {
                "id": file_id,
                "type": row["file_type"],
                "path": row["file_path"],
                "filename": row["filename"],
                "match_details": [],
            }

        # Add parameter match
        param_match = {
            "param_id": row["param_id"],
            "name": row["name"],
            "value": row["value"],
            "value_numeric": row["value_numeric"],
            "value_type": row["value_type"],
            "category": row["category"],
            "is_designated": row["is_designated"],
            "units": row["units"],
        }

        if file_id and file_id in groups[group_id]["files"]:
            groups[group_id]["files"][file_id]["match_details"].append(param_match)

        groups[group_id]["parameters"].append(param_match)

    # Convert files dict to list
    results = []
    for group_data in groups.values():
        group_data["files"] = list(group_data["files"].values())
        results.append(group_data)

    return {
        "query": {
            "type": "parameter",
            "name": name,
            "value": value,
            "numeric_min": numeric_min,
            "numeric_max": numeric_max,
            "category": category,
            "designated_only": designated_only,
        },
        "pagination": {"limit": limit, "offset": offset, "total": total},
        "result_count": len(results),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Search CAD parameters across extracted documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search by parameter name
  python C2-search-parameters.py --name MATERIAL

  # Search by name and value (with wildcard)
  python C2-search-parameters.py --name MATERIAL --value "304*"

  # Search numeric parameters in range
  python C2-search-parameters.py --name WEIGHT --numeric-min 10 --numeric-max 100

  # Search by category
  python C2-search-parameters.py --category material

  # Search designated parameters only
  python C2-search-parameters.py --designated
        """,
    )

    # Search options
    parser.add_argument("--name", "-n", type=str, help="Parameter name (supports * wildcards)")
    parser.add_argument("--value", "-v", type=str, help="Parameter value (supports * wildcards)")

    # Numeric range
    parser.add_argument("--numeric-min", type=float, help="Minimum numeric value")
    parser.add_argument("--numeric-max", type=float, help="Maximum numeric value")

    # Filter options
    parser.add_argument(
        "--category", "-c", type=str, help="Category filter (e.g., material, weight)"
    )
    parser.add_argument(
        "--designated",
        "-d",
        action="store_true",
        dest="designated_only",
        help="Show only designated (primary) parameters",
    )

    # Pagination
    parser.add_argument("--limit", type=int, default=100, help="Maximum results (default: 100)")
    parser.add_argument("--offset", type=int, default=0, help="Result offset for pagination")

    # Output options
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    args = parser.parse_args()

    # Validate arguments
    if not any(
        [
            args.name,
            args.value,
            args.numeric_min is not None,
            args.numeric_max is not None,
            args.category,
            args.designated_only,
        ]
    ):
        parser.error("At least one search criterion required")

    # Load config and connect
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        logger.error("NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    try:
        conn = psycopg2.connect(db_url)
        logger.info("Connected to database")

        results = search_parameters(
            conn,
            name=args.name,
            value=args.value,
            numeric_min=args.numeric_min,
            numeric_max=args.numeric_max,
            category=args.category,
            designated_only=args.designated_only,
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
