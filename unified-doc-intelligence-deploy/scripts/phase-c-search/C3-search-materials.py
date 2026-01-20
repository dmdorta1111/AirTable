#!/usr/bin/env python3
"""
C3-search-materials.py
Search for materials across extracted documents with fuzzy matching.

Usage:
    python C3-search-materials.py --material "304 SS"
    python C3-search-materials.py --material "stainless" --threshold 0.3
    python C3-search-materials.py --spec "ASTM*"

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


def search_materials(
    conn,
    material=None,
    spec=None,
    finish=None,
    thickness_min=None,
    thickness_max=None,
    similarity_threshold=0.3,
    limit=100,
    offset=0,
):
    """
    Search extracted_materials table with fuzzy matching.

    Uses PostgreSQL pg_trgm extension for trigram similarity search.

    Args:
        material: Material name to search (fuzzy match)
        spec: Material specification (e.g., ASTM A240)
        finish: Surface finish specification
        thickness_min/max: Thickness range filter
        similarity_threshold: Minimum similarity score (0.0-1.0)
    """
    conditions = []
    params = []
    order_clause = "emat.material_name"

    # Material name fuzzy search
    if material:
        if "*" in material or "%" in material:
            # Wildcard search
            pattern = material.replace("*", "%")
            conditions.append("emat.material_name ILIKE %s")
            params.append(pattern)
        else:
            # Trigram similarity search
            conditions.append("""
                (emat.material_name ILIKE %s 
                 OR similarity(emat.material_name, %s) > %s)
            """)
            params.extend([f"%{material}%", material, similarity_threshold])
            order_clause = f"similarity(emat.material_name, '{material}') DESC, emat.material_name"

    # Specification filter
    if spec:
        if "*" in spec or "%" in spec:
            spec_pattern = spec.replace("*", "%")
            conditions.append("emat.material_spec ILIKE %s")
            params.append(spec_pattern)
        else:
            conditions.append("emat.material_spec ILIKE %s")
            params.append(f"%{spec}%")

    # Finish filter
    if finish:
        conditions.append("emat.finish ILIKE %s")
        params.append(f"%{finish}%")

    # Thickness range
    if thickness_min is not None:
        conditions.append("emat.thickness >= %s")
        params.append(thickness_min)
    if thickness_max is not None:
        conditions.append("emat.thickness <= %s")
        params.append(thickness_max)

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    # Build similarity score expression if searching by material
    similarity_expr = "1.0 AS similarity_score"
    if material and "*" not in material and "%" not in material:
        similarity_expr = f"similarity(emat.material_name, %s) AS similarity_score"

    # Main query
    query = f"""
        WITH matching_materials AS (
            SELECT 
                emat.id AS material_id,
                emat.material_name,
                emat.material_spec,
                emat.finish,
                emat.thickness,
                emat.thickness_unit,
                emat.properties,
                {"similarity(emat.material_name, %s)" if material and "*" not in material and "%" not in material else "1.0"} AS similarity_score,
                em.id AS metadata_id,
                em.cloud_file_id
            FROM extracted_materials emat
            JOIN extracted_metadata em ON emat.metadata_id = em.id
            WHERE {where_clause}
            ORDER BY {order_clause}
            LIMIT %s OFFSET %s
        ),
        material_files AS (
            SELECT 
                mm.*,
                cf."ID" AS file_id,
                cf."Type" AS file_type,
                cf."FullPath" AS file_path,
                cf."Filename" AS filename,
                cf.document_group_id,
                dg.id AS group_id,
                dg.name AS group_name,
                dg.project_code,
                dg.item_number
            FROM matching_materials mm
            LEFT JOIN "CloudFiles" cf ON mm.cloud_file_id = cf."ID"
            LEFT JOIN document_groups dg ON cf.document_group_id = dg.id
        )
        SELECT * FROM material_files
        ORDER BY similarity_score DESC, group_id NULLS LAST
    """

    # Add material param for similarity if needed
    query_params = []
    if material and "*" not in material and "%" not in material:
        query_params.append(material)  # For similarity expression
    query_params.extend(params)
    query_params.extend([limit, offset])

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, query_params)
        rows = cur.fetchall()

        # Get total count
        count_query = f"""
            SELECT COUNT(*) 
            FROM extracted_materials emat
            JOIN extracted_metadata em ON emat.metadata_id = em.id
            WHERE {where_clause}
        """
        cur.execute(count_query, params)
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
                "materials": [],
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

        # Add material match
        material_match = {
            "material_id": row["material_id"],
            "material_name": row["material_name"],
            "material_spec": row["material_spec"],
            "finish": row["finish"],
            "thickness": row["thickness"],
            "thickness_unit": row["thickness_unit"],
            "properties": row["properties"],
            "similarity_score": row["similarity_score"],
        }

        if file_id and file_id in groups[group_id]["files"]:
            groups[group_id]["files"][file_id]["match_details"].append(material_match)

        groups[group_id]["materials"].append(material_match)

    # Convert files dict to list
    results = []
    for group_data in groups.values():
        group_data["files"] = list(group_data["files"].values())
        results.append(group_data)

    return {
        "query": {
            "type": "material",
            "material": material,
            "spec": spec,
            "finish": finish,
            "thickness_min": thickness_min,
            "thickness_max": thickness_max,
            "similarity_threshold": similarity_threshold,
        },
        "pagination": {"limit": limit, "offset": offset, "total": total},
        "result_count": len(results),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Search materials across extracted documents with fuzzy matching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fuzzy search for stainless steel
  python C3-search-materials.py --material "304 SS"

  # Search with lower similarity threshold for broader matches
  python C3-search-materials.py --material "stainless" --threshold 0.2

  # Search by specification
  python C3-search-materials.py --spec "ASTM A240"

  # Search by specification with wildcard
  python C3-search-materials.py --spec "ASTM*"

  # Search by finish
  python C3-search-materials.py --finish "brushed"

  # Search by thickness range
  python C3-search-materials.py --thickness-min 1.0 --thickness-max 3.0
        """,
    )

    # Search options
    parser.add_argument(
        "--material", "-m", type=str, help="Material name (fuzzy match, supports * wildcards)"
    )
    parser.add_argument("--spec", "-s", type=str, help="Material specification (e.g., ASTM A240)")
    parser.add_argument("--finish", "-f", type=str, help="Surface finish specification")

    # Thickness range
    parser.add_argument("--thickness-min", type=float, help="Minimum thickness")
    parser.add_argument("--thickness-max", type=float, help="Maximum thickness")

    # Similarity options
    parser.add_argument(
        "--threshold", type=float, default=0.3, help="Similarity threshold 0.0-1.0 (default: 0.3)"
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
            args.material,
            args.spec,
            args.finish,
            args.thickness_min is not None,
            args.thickness_max is not None,
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

        results = search_materials(
            conn,
            material=args.material,
            spec=args.spec,
            finish=args.finish,
            thickness_min=args.thickness_min,
            thickness_max=args.thickness_max,
            similarity_threshold=args.threshold,
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
