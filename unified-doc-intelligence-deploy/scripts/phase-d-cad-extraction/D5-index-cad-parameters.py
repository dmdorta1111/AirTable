#!/usr/bin/env python3
"""
D5-index-cad-parameters.py
Index CAD parameters from extracted_metadata.raw_data into extracted_parameters table.

Features:
- Reads raw_data JSONB from extracted_metadata
- Parses parameters section (adapts to various JSON structures)
- Inserts into extracted_parameters table for search indexing
- Handles numeric value extraction for range queries
- Categorizes parameters (material, weight, custom, etc.)
- Dry-run mode for testing

Usage: python D5-index-cad-parameters.py [--dry-run] [--limit N] [--reindex]
"""

import sys
import re
import argparse
import json
import logging
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

# Parameter categorization patterns
CATEGORY_PATTERNS = {
    "material": [
        r"^material$",
        r"^mat$",
        r"^matl$",
        r"^material_?name$",
        r"^pro_mp_material$",
        r"^mp_material$",
    ],
    "weight": [
        r"^weight$",
        r"^mass$",
        r"^pro_mp_mass$",
        r"^mp_mass$",
        r"^total_?weight$",
        r"^net_?weight$",
    ],
    "density": [
        r"^density$",
        r"^pro_mp_density$",
        r"^mp_density$",
    ],
    "volume": [
        r"^volume$",
        r"^pro_mp_volume$",
        r"^mp_volume$",
    ],
    "surface_area": [
        r"^surface_?area$",
        r"^pro_mp_area$",
        r"^mp_area$",
    ],
    "description": [
        r"^description$",
        r"^desc$",
        r"^part_?desc$",
    ],
    "part_number": [
        r"^part_?number$",
        r"^part_?no$",
        r"^pn$",
        r"^p/n$",
    ],
    "revision": [
        r"^revision$",
        r"^rev$",
        r"^version$",
    ],
    "finish": [
        r"^finish$",
        r"^surface_?finish$",
        r"^coating$",
    ],
    "tolerance": [
        r"^tolerance$",
        r"^tol$",
        r"^general_?tol$",
    ],
}


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


def categorize_parameter(name: str) -> str:
    """
    Categorize a parameter based on its name.
    Returns category string or 'custom'.
    """
    name_lower = name.lower()

    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, name_lower):
                return category

    return "custom"


def extract_numeric_value(value: str) -> tuple:
    """
    Try to extract a numeric value from a string.
    Returns (numeric_value, units) or (None, None).
    """
    if value is None:
        return None, None

    value_str = str(value).strip()

    # Try direct float conversion
    try:
        return float(value_str), None
    except ValueError:
        pass

    # Try to extract number with units (e.g., "2.45 kg", "100 mm")
    match = re.match(r"^([-+]?\d*\.?\d+)\s*([a-zA-Z]+)?$", value_str)
    if match:
        try:
            num = float(match.group(1))
            units = match.group(2)
            return num, units
        except ValueError:
            pass

    return None, None


def determine_value_type(value) -> str:
    """Determine the type of a parameter value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"

    value_str = str(value).strip().lower()

    # Check for boolean strings
    if value_str in ("true", "false", "yes", "no", "1", "0"):
        return "boolean"

    # Check for numeric
    try:
        float(value_str)
        return "number"
    except ValueError:
        pass

    return "string"


def extract_parameters_from_raw_data(raw_data: dict) -> list:
    """
    Extract parameters from raw_data JSONB.
    Adapts to various JSON structures from Creo extraction.
    Returns list of parameter dicts.

    Supports:
    - Standard parameter lists/dicts
    - Enhanced Creo serialization format (v4.0-geometry) with features array
    - Mass properties
    """
    parameters = []

    # Extract model-level metadata
    if "model_name" in raw_data:
        parameters.append(
            {
                "name": "MODEL_NAME",
                "value": str(raw_data["model_name"]),
                "is_designated": True,
                "units": None,
            }
        )

    if "feature_count" in raw_data:
        parameters.append(
            {
                "name": "FEATURE_COUNT",
                "value": str(raw_data["feature_count"]),
                "is_designated": False,
                "units": None,
            }
        )

    if "serialization_version" in raw_data:
        parameters.append(
            {
                "name": "SERIALIZATION_VERSION",
                "value": str(raw_data["serialization_version"]),
                "is_designated": False,
                "units": None,
            }
        )

    # Extract from features array (enhanced Creo format)
    if "features" in raw_data and isinstance(raw_data["features"], list):
        for feature in raw_data["features"]:
            if not isinstance(feature, dict):
                continue

            feature_name = feature.get("name", "")
            feature_id = feature.get("id", "")
            feature_type = feature.get("type", "")

            # Add feature as a parameter
            if feature_name:
                parameters.append(
                    {
                        "name": f"FEATURE_{feature_name}",
                        "value": f"id={feature_id}, type={feature_type}",
                        "is_designated": False,
                        "units": None,
                    }
                )

            # Extract geometry data from feature
            geometry = feature.get("feature_geometry")
            if geometry and isinstance(geometry, dict):
                surfaces = geometry.get("surfaces", [])
                for surf in surfaces:
                    if isinstance(surf, dict):
                        surf_type = surf.get("type", "unknown")
                        centroid = surf.get("centroid", [])
                        normal = surf.get("normal", [])

                        if centroid:
                            parameters.append(
                                {
                                    "name": f"SURFACE_{feature_name}_CENTROID",
                                    "value": str(centroid),
                                    "is_designated": False,
                                    "units": None,
                                }
                            )

                        if normal:
                            parameters.append(
                                {
                                    "name": f"SURFACE_{feature_name}_NORMAL",
                                    "value": str(normal),
                                    "is_designated": False,
                                    "units": None,
                                }
                            )

            # Extract element tree values (dimensions, offsets)
            element_tree = feature.get("element_tree", {})
            if isinstance(element_tree, dict):
                tree_data = element_tree.get("element_tree", {})
                elements = tree_data.get("elements", [])

                for elem in elements:
                    if not isinstance(elem, dict):
                        continue

                    # Extract double values (dimensions)
                    if "double_value" in elem and elem.get("double_value") != 0.0:
                        elem_id = elem.get("elem_id", "unknown")
                        parameters.append(
                            {
                                "name": f"DIM_{feature_name}_{elem_id}",
                                "value": str(elem["double_value"]),
                                "is_designated": False,
                                "units": None,
                            }
                        )

                    # Extract string values
                    if "string_value" in elem:
                        elem_id = elem.get("elem_id", "unknown")
                        parameters.append(
                            {
                                "name": f"STR_{feature_name}_{elem_id}",
                                "value": str(elem["string_value"]),
                                "is_designated": False,
                                "units": None,
                            }
                        )

                    # Extract semantic references
                    selection = elem.get("selection_data", {})
                    if isinstance(selection, dict) and selection.get("has_ref"):
                        ref_name = selection.get("name", "")
                        sem_ref = selection.get("semantic_reference", {})
                        if sem_ref:
                            parameters.append(
                                {
                                    "name": f"REF_{feature_name}_TO_{ref_name}",
                                    "value": f"parent={sem_ref.get('parent_feature_name', '')}, type={sem_ref.get('surface_type', '')}",
                                    "is_designated": False,
                                    "units": None,
                                }
                            )

    # Try various standard parameter key names
    param_keys = [
        "parameters",
        "params",
        "model_parameters",
        "designated_parameters",
        "user_parameters",
    ]

    for key in param_keys:
        if key not in raw_data:
            continue

        params = raw_data[key]

        # Handle list of parameter objects
        if isinstance(params, list):
            for param in params:
                if isinstance(param, dict):
                    name = param.get("name") or param.get("param_name") or param.get("key")
                    value = param.get("value") or param.get("param_value")

                    if name:
                        parameters.append(
                            {
                                "name": str(name),
                                "value": str(value) if value is not None else "",
                                "is_designated": param.get("designated", False)
                                or param.get("is_designated", False),
                                "units": param.get("units") or param.get("unit"),
                            }
                        )

        # Handle dict of name: value pairs
        elif isinstance(params, dict):
            for name, value in params.items():
                if isinstance(value, dict):
                    # Nested structure: {name: {value: x, units: y}}
                    parameters.append(
                        {
                            "name": str(name),
                            "value": str(value.get("value", "")),
                            "is_designated": value.get("designated", False),
                            "units": value.get("units"),
                        }
                    )
                else:
                    # Simple structure: {name: value}
                    parameters.append(
                        {
                            "name": str(name),
                            "value": str(value) if value is not None else "",
                            "is_designated": False,
                            "units": None,
                        }
                    )

    # Also extract mass properties if present
    mass_props_keys = ["mass_properties", "massprops", "mp"]
    for key in mass_props_keys:
        if key in raw_data and isinstance(raw_data[key], dict):
            for prop_name, prop_value in raw_data[key].items():
                if prop_value is not None:
                    parameters.append(
                        {
                            "name": f"mp_{prop_name}",
                            "value": str(prop_value),
                            "is_designated": False,
                            "units": None,
                        }
                    )

    return parameters


def get_metadata_to_index(conn, limit=None, reindex=False):
    """
    Get extracted_metadata records that need parameter indexing.
    Returns list of (metadata_id, cad_model_id, raw_data).
    """
    if reindex:
        # Get all CAD metadata
        query = """
            SELECT id, cad_model_id, raw_data
            FROM extracted_metadata
            WHERE source_type IN ('creo_part', 'creo_asm')
            AND extraction_status = 'completed'
            AND raw_data IS NOT NULL
            ORDER BY id
        """
    else:
        # Get only unindexed metadata
        query = """
            SELECT em.id, em.cad_model_id, em.raw_data
            FROM extracted_metadata em
            WHERE em.source_type IN ('creo_part', 'creo_asm')
            AND em.extraction_status = 'completed'
            AND em.raw_data IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM extracted_parameters ep
                WHERE ep.metadata_id = em.id
            )
            ORDER BY em.id
        """

    if limit:
        query += f" LIMIT {limit}"

    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()


def index_parameters(
    conn, metadata_id: int, cad_model_id: int, raw_data: dict, dry_run: bool = False
) -> int:
    """
    Index parameters from a single metadata record.
    Returns count of parameters indexed.
    """
    parameters = extract_parameters_from_raw_data(raw_data)

    if not parameters:
        return 0

    if dry_run:
        return len(parameters)

    # Prepare batch insert data
    insert_data = []
    for param in parameters:
        name = param["name"][:255]  # Truncate to column limit
        value = param["value"][:10000] if param["value"] else ""  # Reasonable limit

        # Determine value type and extract numeric
        value_type = determine_value_type(param["value"])
        numeric_value, units = extract_numeric_value(param["value"])

        # Use units from param if available
        if param.get("units"):
            units = param["units"]

        # Categorize
        category = categorize_parameter(name)

        insert_data.append(
            (
                metadata_id,
                cad_model_id,
                name,
                value,
                numeric_value,
                value_type,
                category,
                param.get("is_designated", False),
                units,
            )
        )

    try:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO extracted_parameters 
                (metadata_id, cad_model_id, name, value, value_numeric, 
                 value_type, category, is_designated, units)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                insert_data,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            )
            inserted = cur.rowcount

        conn.commit()
        return inserted

    except Exception as e:
        logger.error(f"Failed to index parameters for metadata {metadata_id}: {e}")
        conn.rollback()
        return 0


def get_indexing_statistics(conn):
    """Get current parameter indexing statistics."""
    with conn.cursor() as cur:
        # Total CAD metadata
        cur.execute("""
            SELECT COUNT(*) FROM extracted_metadata
            WHERE source_type IN ('creo_part', 'creo_asm')
            AND extraction_status = 'completed'
        """)
        total_metadata = cur.fetchone()[0]

        # Metadata with indexed parameters
        cur.execute("""
            SELECT COUNT(DISTINCT metadata_id) FROM extracted_parameters
        """)
        indexed_metadata = cur.fetchone()[0]

        # Total parameters indexed
        cur.execute("""
            SELECT COUNT(*) FROM extracted_parameters
        """)
        total_parameters = cur.fetchone()[0]

        # Parameters by category
        cur.execute("""
            SELECT category, COUNT(*) 
            FROM extracted_parameters
            GROUP BY category
            ORDER BY COUNT(*) DESC
        """)
        by_category = cur.fetchall()

        return {
            "total_metadata": total_metadata,
            "indexed_metadata": indexed_metadata,
            "total_parameters": total_parameters,
            "by_category": by_category,
        }


def main():
    parser = argparse.ArgumentParser(description="Index CAD parameters for search")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be indexed without making changes"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of metadata records to process (0 = unlimited)",
    )
    parser.add_argument(
        "--reindex", action="store_true", help="Reindex all parameters (including already indexed)"
    )
    parser.add_argument(
        "--stats-only", action="store_true", help="Only show statistics, don't index"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("D5: INDEX CAD PARAMETERS")
    print("=" * 70)
    if args.dry_run:
        print("MODE: DRY RUN")
    if args.reindex:
        print("MODE: REINDEX ALL")
    if args.limit > 0:
        print(f"LIMIT: {args.limit} records")
    print("=" * 70)

    # Load config and connect
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        logger.error("NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    logger.info("Connecting to database...")
    conn = psycopg2.connect(db_url)

    # Show current statistics
    print("\nCurrent Parameter Indexing Status:")
    print("-" * 50)
    stats = get_indexing_statistics(conn)
    print(f"  CAD metadata records:     {stats['total_metadata']:,}")
    print(f"  Records with parameters:  {stats['indexed_metadata']:,}")
    print(f"  Total parameters indexed: {stats['total_parameters']:,}")

    if stats["by_category"]:
        print("\n  Parameters by category:")
        for category, count in stats["by_category"][:10]:
            print(f"    {category:20} {count:,}")
    print("-" * 50)

    if args.stats_only:
        conn.close()
        return

    # Clear existing parameters if reindexing
    if args.reindex and not args.dry_run:
        logger.info("Clearing existing parameters for reindex...")
        with conn.cursor() as cur:
            cur.execute("DELETE FROM extracted_parameters")
            deleted = cur.rowcount
        conn.commit()
        print(f"Deleted {deleted:,} existing parameters")

    # Get metadata to index
    logger.info("Finding metadata records to index...")
    metadata_records = get_metadata_to_index(
        conn, limit=args.limit if args.limit > 0 else None, reindex=args.reindex
    )

    print(f"\nMetadata records to process: {len(metadata_records):,}")

    if not metadata_records:
        print("No metadata records need indexing.")
        conn.close()
        return

    # Process records
    total_params = 0
    records_with_params = 0

    print("\nIndexing parameters...")
    for i, (metadata_id, cad_model_id, raw_data) in enumerate(metadata_records, 1):
        if raw_data:
            count = index_parameters(
                conn, metadata_id, cad_model_id, raw_data, dry_run=args.dry_run
            )
            total_params += count
            if count > 0:
                records_with_params += 1

        # Progress indicator
        if i % 500 == 0 or i == len(metadata_records):
            print(f"  Processed {i}/{len(metadata_records)} records...")

    conn.close()

    # Print summary
    print("\n" + "=" * 70)
    print("INDEXING SUMMARY")
    print("=" * 70)
    print(f"Records processed:       {len(metadata_records):,}")
    print(f"Records with parameters: {records_with_params:,}")
    print(f"{'Would index' if args.dry_run else 'Indexed'} parameters: {total_params:,}")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "reindex": args.reindex,
        "records_processed": len(metadata_records),
        "records_with_params": records_with_params,
        "total_parameters": total_params,
    }

    report_file = (
        OUTPUT_DIR / f"D5-parameter-indexing-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
