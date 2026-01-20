#!/usr/bin/env python3
"""
C5-search-fulltext.py
Full-text search across all extracted data using PostgreSQL full-text search.

Usage:
    python C5-search-fulltext.py --query "hinge bracket"
    python C5-search-fulltext.py --query "304 stainless" --scope materials
    python C5-search-fulltext.py --query "tolerance" --scope all

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


def prepare_search_query(query_text):
    """
    Prepare search query for PostgreSQL full-text search.

    Converts user query to tsquery format:
    - "hinge bracket" -> 'hinge' & 'bracket' (AND search)
    - "hinge | bracket" -> 'hinge' | 'bracket' (OR search)
    """
    # Check if user explicitly used OR
    if " | " in query_text:
        # User wants OR search
        terms = [t.strip() for t in query_text.split("|")]
        return " | ".join(f"'{t}':*" for t in terms if t)
    else:
        # Default to AND search
        terms = query_text.split()
        return " & ".join(f"'{t}':*" for t in terms if t)


def search_fulltext(conn, query, scope="all", limit=100, offset=0):
    """
    Full-text search across extracted data.

    Uses PostgreSQL to_tsvector and to_tsquery for efficient text search.

    Scopes:
    - all: Search across all extracted data
    - metadata: Search raw_data JSONB field
    - materials: Search material names and specs
    - parameters: Search parameter names and values
    - dimensions: Search dimension labels
    - bom: Search BOM part numbers and descriptions
    """
    ts_query = prepare_search_query(query)

    results_by_scope = {}
    total_matches = 0

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Search materials
        if scope in ("all", "materials"):
            materials_query = """
                WITH material_matches AS (
                    SELECT 
                        emat.id AS match_id,
                        'material' AS match_type,
                        emat.material_name AS matched_text,
                        ts_rank(
                            to_tsvector('english', COALESCE(emat.material_name, '') || ' ' || COALESCE(emat.material_spec, '')),
                            to_tsquery('english', %s)
                        ) AS rank,
                        emat.material_name,
                        emat.material_spec,
                        emat.finish,
                        em.cloud_file_id,
                        cf."ID" AS file_id,
                        cf."Type" AS file_type,
                        cf."FullPath" AS file_path,
                        cf."Filename" AS filename,
                        dg.id AS group_id,
                        dg.name AS group_name,
                        dg.project_code,
                        dg.item_number
                    FROM extracted_materials emat
                    JOIN extracted_metadata em ON emat.metadata_id = em.id
                    LEFT JOIN "CloudFiles" cf ON em.cloud_file_id = cf."ID"
                    LEFT JOIN document_groups dg ON cf.document_group_id = dg.id
                    WHERE to_tsvector('english', COALESCE(emat.material_name, '') || ' ' || COALESCE(emat.material_spec, ''))
                          @@ to_tsquery('english', %s)
                    ORDER BY rank DESC
                    LIMIT %s OFFSET %s
                )
                SELECT * FROM material_matches
            """
            cur.execute(materials_query, [ts_query, ts_query, limit, offset])
            results_by_scope["materials"] = cur.fetchall()

            # Count materials
            cur.execute(
                """
                SELECT COUNT(*) FROM extracted_materials emat
                WHERE to_tsvector('english', COALESCE(material_name, '') || ' ' || COALESCE(material_spec, ''))
                      @@ to_tsquery('english', %s)
            """,
                [ts_query],
            )
            materials_count = cur.fetchone()["count"]
            total_matches += materials_count

        # Search parameters
        if scope in ("all", "parameters"):
            params_query = """
                WITH param_matches AS (
                    SELECT 
                        ep.id AS match_id,
                        'parameter' AS match_type,
                        ep.name || '=' || ep.value AS matched_text,
                        ts_rank(
                            to_tsvector('english', ep.name || ' ' || ep.value),
                            to_tsquery('english', %s)
                        ) AS rank,
                        ep.name AS param_name,
                        ep.value AS param_value,
                        ep.category,
                        em.cloud_file_id,
                        cf."ID" AS file_id,
                        cf."Type" AS file_type,
                        cf."FullPath" AS file_path,
                        cf."Filename" AS filename,
                        dg.id AS group_id,
                        dg.name AS group_name,
                        dg.project_code,
                        dg.item_number
                    FROM extracted_parameters ep
                    JOIN extracted_metadata em ON ep.metadata_id = em.id
                    LEFT JOIN "CloudFiles" cf ON em.cloud_file_id = cf."ID"
                    LEFT JOIN document_groups dg ON cf.document_group_id = dg.id
                    WHERE to_tsvector('english', ep.name || ' ' || ep.value)
                          @@ to_tsquery('english', %s)
                    ORDER BY rank DESC
                    LIMIT %s OFFSET %s
                )
                SELECT * FROM param_matches
            """
            cur.execute(params_query, [ts_query, ts_query, limit, offset])
            results_by_scope["parameters"] = cur.fetchall()

            # Count parameters
            cur.execute(
                """
                SELECT COUNT(*) FROM extracted_parameters ep
                WHERE to_tsvector('english', name || ' ' || value)
                      @@ to_tsquery('english', %s)
            """,
                [ts_query],
            )
            params_count = cur.fetchone()["count"]
            total_matches += params_count

        # Search dimension labels
        if scope in ("all", "dimensions"):
            dims_query = """
                WITH dim_matches AS (
                    SELECT 
                        ed.id AS match_id,
                        'dimension' AS match_type,
                        ed.label AS matched_text,
                        ts_rank(
                            to_tsvector('english', COALESCE(ed.label, '')),
                            to_tsquery('english', %s)
                        ) AS rank,
                        ed.value,
                        ed.unit,
                        ed.label,
                        ed.dimension_type,
                        em.cloud_file_id,
                        cf."ID" AS file_id,
                        cf."Type" AS file_type,
                        cf."FullPath" AS file_path,
                        cf."Filename" AS filename,
                        dg.id AS group_id,
                        dg.name AS group_name,
                        dg.project_code,
                        dg.item_number
                    FROM extracted_dimensions ed
                    JOIN extracted_metadata em ON ed.metadata_id = em.id
                    LEFT JOIN "CloudFiles" cf ON em.cloud_file_id = cf."ID"
                    LEFT JOIN document_groups dg ON cf.document_group_id = dg.id
                    WHERE ed.label IS NOT NULL 
                      AND to_tsvector('english', ed.label) @@ to_tsquery('english', %s)
                    ORDER BY rank DESC
                    LIMIT %s OFFSET %s
                )
                SELECT * FROM dim_matches
            """
            cur.execute(dims_query, [ts_query, ts_query, limit, offset])
            results_by_scope["dimensions"] = cur.fetchall()

            # Count dimensions
            cur.execute(
                """
                SELECT COUNT(*) FROM extracted_dimensions ed
                WHERE label IS NOT NULL 
                  AND to_tsvector('english', label) @@ to_tsquery('english', %s)
            """,
                [ts_query],
            )
            dims_count = cur.fetchone()["count"]
            total_matches += dims_count

        # Search BOM items
        if scope in ("all", "bom"):
            bom_query = """
                WITH bom_matches AS (
                    SELECT 
                        ebom.id AS match_id,
                        'bom' AS match_type,
                        ebom.part_number || ' - ' || COALESCE(ebom.description, '') AS matched_text,
                        ts_rank(
                            to_tsvector('english', 
                                ebom.part_number || ' ' || 
                                COALESCE(ebom.description, '') || ' ' || 
                                COALESCE(ebom.material, '')
                            ),
                            to_tsquery('english', %s)
                        ) AS rank,
                        ebom.item_number,
                        ebom.part_number,
                        ebom.description,
                        ebom.quantity,
                        ebom.material AS bom_material,
                        em.cloud_file_id,
                        cf."ID" AS file_id,
                        cf."Type" AS file_type,
                        cf."FullPath" AS file_path,
                        cf."Filename" AS filename,
                        dg.id AS group_id,
                        dg.name AS group_name,
                        dg.project_code,
                        dg.item_number AS doc_item_number
                    FROM extracted_bom_items ebom
                    JOIN extracted_metadata em ON ebom.metadata_id = em.id
                    LEFT JOIN "CloudFiles" cf ON em.cloud_file_id = cf."ID"
                    LEFT JOIN document_groups dg ON cf.document_group_id = dg.id
                    WHERE to_tsvector('english', 
                            ebom.part_number || ' ' || 
                            COALESCE(ebom.description, '') || ' ' || 
                            COALESCE(ebom.material, '')
                          ) @@ to_tsquery('english', %s)
                    ORDER BY rank DESC
                    LIMIT %s OFFSET %s
                )
                SELECT * FROM bom_matches
            """
            cur.execute(bom_query, [ts_query, ts_query, limit, offset])
            results_by_scope["bom"] = cur.fetchall()

            # Count BOM items
            cur.execute(
                """
                SELECT COUNT(*) FROM extracted_bom_items ebom
                WHERE to_tsvector('english', 
                        part_number || ' ' || 
                        COALESCE(description, '') || ' ' || 
                        COALESCE(material, '')
                      ) @@ to_tsquery('english', %s)
            """,
                [ts_query],
            )
            bom_count = cur.fetchone()["count"]
            total_matches += bom_count

    # Combine and rank all results
    all_matches = []
    for scope_name, matches in results_by_scope.items():
        for match in matches:
            all_matches.append(
                {
                    "match_type": scope_name,
                    "match_id": match["match_id"],
                    "matched_text": match["matched_text"],
                    "relevance_score": float(match["rank"]) if match["rank"] else 0,
                    "document_group": {
                        "id": match["group_id"],
                        "name": match["group_name"],
                        "project_code": match["project_code"],
                        "item_number": match.get("item_number") or match.get("doc_item_number"),
                    }
                    if match["group_id"]
                    else None,
                    "file": {
                        "id": match["file_id"],
                        "type": match["file_type"],
                        "path": match["file_path"],
                        "filename": match["filename"],
                    }
                    if match["file_id"]
                    else None,
                    "match_details": {
                        k: v
                        for k, v in match.items()
                        if k
                        not in (
                            "match_id",
                            "match_type",
                            "matched_text",
                            "rank",
                            "group_id",
                            "group_name",
                            "project_code",
                            "item_number",
                            "doc_item_number",
                            "file_id",
                            "file_type",
                            "file_path",
                            "filename",
                            "cloud_file_id",
                        )
                    },
                }
            )

    # Sort by relevance score
    all_matches.sort(key=lambda x: x["relevance_score"], reverse=True)

    return {
        "query": {"type": "fulltext", "text": query, "tsquery": ts_query, "scope": scope},
        "pagination": {"limit": limit, "offset": offset, "total": total_matches},
        "result_count": len(all_matches),
        "results": all_matches,
        "counts_by_scope": {
            scope_name: len(matches) for scope_name, matches in results_by_scope.items()
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Full-text search across all extracted data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for "hinge bracket" in all data
  python C5-search-fulltext.py --query "hinge bracket"

  # Search only in materials
  python C5-search-fulltext.py --query "304 stainless" --scope materials

  # OR search
  python C5-search-fulltext.py --query "aluminum | steel"

  # Search BOM items
  python C5-search-fulltext.py --query "washer" --scope bom

Scopes:
  all        - Search all extracted data (default)
  materials  - Search material names and specifications
  parameters - Search parameter names and values
  dimensions - Search dimension labels
  bom        - Search BOM part numbers and descriptions
        """,
    )

    # Search options
    parser.add_argument(
        "--query", "-q", type=str, required=True, help="Search query (use | for OR, default is AND)"
    )
    parser.add_argument(
        "--scope",
        "-s",
        type=str,
        default="all",
        choices=["all", "materials", "parameters", "dimensions", "bom"],
        help="Search scope (default: all)",
    )

    # Pagination
    parser.add_argument(
        "--limit", type=int, default=100, help="Maximum results per scope (default: 100)"
    )
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

        results = search_fulltext(
            conn, query=args.query, scope=args.scope, limit=args.limit, offset=args.offset
        )

        conn.close()

        # Output JSON
        indent = 2 if args.pretty else None
        print(json.dumps(results, indent=indent, default=decimal_default))

        logger.info(f"Found {results['pagination']['total']} total matches for '{args.query}'")

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        error_result = {"error": str(e), "query": {"text": args.query, "scope": args.scope}}
        print(json.dumps(error_result))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
