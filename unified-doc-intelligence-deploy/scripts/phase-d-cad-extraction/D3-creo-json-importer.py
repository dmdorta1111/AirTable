#!/usr/bin/env python3
"""
D3-creo-json-importer.py
Import existing Creo extraction JSON files into the database.

Features:
- Walks a directory of JSON files
- Matches JSON files to CloudFiles by filename
- Imports extraction data into extracted_metadata
- Supports flexible JSON structure (adapts to your Creo output format)
- Dry-run mode for testing

Usage: python D3-creo-json-importer.py --input-dir /path/to/json/files [--dry-run]
"""

import sys
import os
import argparse
import json
import logging
import re
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


def extract_cad_filename(json_filename: str) -> str:
    """
    Extract the original CAD filename from a JSON filename.

    Examples:
        "88617-001.prt.json" -> "88617-001.prt"
        "88617-001_extracted.json" -> "88617-001"
        "88617-001.json" -> "88617-001"
    """
    name = json_filename

    # Remove .json extension
    if name.lower().endswith(".json"):
        name = name[:-5]

    # Remove common suffixes
    for suffix in ["_extracted", "_export", "_data", "_metadata"]:
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]
            break

    return name


def find_matching_cloud_file(conn, cad_filename: str):
    """
    Find a CloudFile that matches the CAD filename.
    Returns (cloud_file_id, full_filename, source_type) or None.
    """
    # Try exact match first
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT "ID", "LocalPath"
            FROM "CloudFiles"
            WHERE "LocalPath" ILIKE %s
            LIMIT 1
        """,
            (f"%{cad_filename}%",),
        )

        row = cur.fetchone()
        if row:
            cloud_file_id, local_path = row
            # Determine source type
            filename_lower = local_path.lower()
            if ".prt" in filename_lower:
                source_type = "creo_part"
            elif ".asm" in filename_lower:
                source_type = "creo_asm"
            else:
                source_type = "creo_part"  # Default
            return (cloud_file_id, local_path, source_type)

    return None


def analyze_json_structure(data: dict) -> dict:
    """
    Analyze the JSON structure to extract key metadata.
    Adapts to various Creo extraction output formats including enhanced v4.0-geometry.
    """
    result = {
        "has_parameters": False,
        "has_bom": False,
        "has_feature_tree": False,
        "has_geometry": False,
        "parameter_count": 0,
        "bom_count": 0,
        "feature_count": 0,
        "surface_count": 0,
        "model_name": None,
        "serialization_version": None,
    }

    # Check for enhanced Creo format (v4.0-geometry)
    if "serialization_version" in data:
        result["serialization_version"] = data.get("serialization_version")

    if "model_name" in data:
        result["model_name"] = data.get("model_name")

    if "feature_count" in data:
        result["feature_count"] = data.get("feature_count", 0)
        result["has_feature_tree"] = result["feature_count"] > 0

    # Check for features array (enhanced format)
    if "features" in data and isinstance(data["features"], list):
        features = data["features"]
        result["feature_count"] = len(features)
        result["has_feature_tree"] = True

        # Count surfaces and check for geometry
        for feature in features:
            if isinstance(feature, dict):
                geometry = feature.get("feature_geometry")
                if geometry and isinstance(geometry, dict):
                    surfaces = geometry.get("surfaces", [])
                    result["surface_count"] += len(surfaces)
                    if surfaces:
                        result["has_geometry"] = True

                # Count element tree values as parameters
                element_tree = feature.get("element_tree", {})
                if isinstance(element_tree, dict):
                    tree_data = element_tree.get("element_tree", {})
                    elements = tree_data.get("elements", [])
                    for elem in elements:
                        if isinstance(elem, dict):
                            if "double_value" in elem or "string_value" in elem:
                                result["parameter_count"] += 1

        result["has_parameters"] = result["parameter_count"] > 0

    # Check for standard parameters (various key names)
    param_keys = ["parameters", "params", "model_parameters", "designated_parameters"]
    for key in param_keys:
        if key in data and isinstance(data[key], (list, dict)):
            params = data[key]
            if isinstance(params, dict):
                result["parameter_count"] += len(params)
            else:
                result["parameter_count"] += len(params)
            result["has_parameters"] = result["parameter_count"] > 0
            break

    # Check for BOM (various key names)
    bom_keys = ["bom", "bill_of_materials", "components", "assembly_components"]
    for key in bom_keys:
        if key in data and isinstance(data[key], list):
            result["bom_count"] = len(data[key])
            result["has_bom"] = result["bom_count"] > 0
            break

    # Check for feature tree (legacy format)
    feature_keys = ["feature_tree", "model_tree"]
    for key in feature_keys:
        if key in data and isinstance(data[key], list):
            if result["feature_count"] == 0:
                result["feature_count"] = len(data[key])
            result["has_feature_tree"] = True
            break

    return result


def import_json_file(conn, json_path: Path, dry_run: bool = False) -> dict:
    """
    Import a single JSON file into the database.
    Returns status dict.
    """
    result = {
        "file": json_path.name,
        "status": "unknown",
        "cloud_file_id": None,
        "error": None,
    }

    try:
        # Load JSON
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract CAD filename
        cad_filename = extract_cad_filename(json_path.name)

        # Also check if filename is in the JSON itself
        if "filename" in data:
            cad_filename = data["filename"]
        elif "model_name" in data:
            cad_filename = data["model_name"]

        # Find matching CloudFile
        match = find_matching_cloud_file(conn, cad_filename)

        if not match:
            result["status"] = "no_match"
            result["error"] = f"No CloudFile found for: {cad_filename}"
            return result

        cloud_file_id, full_filename, source_type = match
        result["cloud_file_id"] = cloud_file_id

        # Analyze JSON structure
        analysis = analyze_json_structure(data)

        if dry_run:
            result["status"] = "would_import"
            result["analysis"] = analysis
            return result

        # Add import metadata to the JSON
        data["_import_metadata"] = {
            "imported_at": datetime.now().isoformat(),
            "source_file": json_path.name,
            "matched_cloud_file": full_filename,
        }

        # Insert into extracted_metadata
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO extracted_metadata 
                (cloud_file_id, source_type, extraction_type, extraction_status, 
                 raw_data, has_parameters, has_bom, has_feature_tree,
                 parameter_count, feature_count, worker_id)
                VALUES (%s, %s, 'imported', 'completed', %s, %s, %s, %s, %s, %s, 'json-importer')
                ON CONFLICT (cloud_file_id) WHERE cloud_file_id IS NOT NULL
                DO UPDATE SET
                    extraction_status = 'completed',
                    raw_data = EXCLUDED.raw_data,
                    has_parameters = EXCLUDED.has_parameters,
                    has_bom = EXCLUDED.has_bom,
                    has_feature_tree = EXCLUDED.has_feature_tree,
                    parameter_count = EXCLUDED.parameter_count,
                    feature_count = EXCLUDED.feature_count,
                    updated_at = NOW()
                RETURNING id
            """,
                (
                    cloud_file_id,
                    source_type,
                    json.dumps(data),
                    analysis["has_parameters"],
                    analysis["has_bom"],
                    analysis["has_feature_tree"],
                    analysis["parameter_count"],
                    analysis["feature_count"],
                ),
            )

            metadata_id = cur.fetchone()[0]

        # Update CloudFiles extraction_status
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE "CloudFiles"
                SET extraction_status = 'completed'
                WHERE "ID" = %s
            """,
                (cloud_file_id,),
            )

        # Update or create extraction_job as completed
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO extraction_jobs 
                (cloud_file_id, job_type, status, completed_at, worker_id)
                VALUES (%s, %s, 'completed', NOW(), 'json-importer')
                ON CONFLICT DO NOTHING
            """,
                (cloud_file_id, source_type),
            )

        conn.commit()

        result["status"] = "imported"
        result["metadata_id"] = metadata_id
        result["analysis"] = analysis

    except json.JSONDecodeError as e:
        result["status"] = "invalid_json"
        result["error"] = str(e)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        conn.rollback()

    return result


def find_json_files(input_dir: Path) -> list:
    """Find all JSON files in the input directory (recursive)."""
    json_files = []

    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith(".json"):
                json_files.append(Path(root) / file)

    return sorted(json_files)


def main():
    parser = argparse.ArgumentParser(description="Import Creo extraction JSON files")
    parser.add_argument(
        "--input-dir",
        "-i",
        type=str,
        required=True,
        help="Directory containing JSON files to import",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be imported without making changes"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Limit number of files to import (0 = unlimited)"
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)

    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)

    print("=" * 70)
    print("D3: CREO JSON IMPORTER")
    print("=" * 70)
    print(f"Input directory: {input_dir}")
    if args.dry_run:
        print("MODE: DRY RUN")
    if args.limit > 0:
        print(f"LIMIT: {args.limit} files")
    print("=" * 70)

    # Find JSON files
    logger.info("Scanning for JSON files...")
    json_files = find_json_files(input_dir)

    if args.limit > 0:
        json_files = json_files[: args.limit]

    print(f"\nFound {len(json_files)} JSON files")

    if not json_files:
        print("No JSON files found.")
        return

    # Load config and connect
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        logger.error("NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    logger.info("Connecting to database...")
    conn = psycopg2.connect(db_url)

    # Process files
    stats = {
        "imported": 0,
        "would_import": 0,
        "no_match": 0,
        "invalid_json": 0,
        "error": 0,
    }

    results = []

    print("\nProcessing files...")
    for i, json_file in enumerate(json_files, 1):
        result = import_json_file(conn, json_file, dry_run=args.dry_run)
        results.append(result)
        stats[result["status"]] = stats.get(result["status"], 0) + 1

        # Progress indicator
        if i % 100 == 0 or i == len(json_files):
            print(f"  Processed {i}/{len(json_files)} files...")

    conn.close()

    # Print summary
    print("\n" + "=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)

    if args.dry_run:
        print(f"Would import:    {stats.get('would_import', 0):,}")
    else:
        print(f"Imported:        {stats.get('imported', 0):,}")

    print(f"No match found:  {stats.get('no_match', 0):,}")
    print(f"Invalid JSON:    {stats.get('invalid_json', 0):,}")
    print(f"Errors:          {stats.get('error', 0):,}")
    print(f"Total processed: {len(json_files):,}")

    # Show unmatched files
    unmatched = [r for r in results if r["status"] == "no_match"]
    if unmatched and len(unmatched) <= 20:
        print("\nUnmatched files:")
        for r in unmatched:
            print(f"  - {r['file']}")
    elif unmatched:
        print(f"\n{len(unmatched)} files could not be matched to CloudFiles")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "input_dir": str(input_dir),
        "dry_run": args.dry_run,
        "stats": stats,
        "total_files": len(json_files),
        "results": results[:100],  # Limit results in report
    }

    report_file = OUTPUT_DIR / f"D3-json-import-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
