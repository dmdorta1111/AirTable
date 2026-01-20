#!/usr/bin/env python3
"""
D6-cad-extraction-report.py
Generate comprehensive CAD extraction statistics and reports.

Features:
- Overall extraction progress
- Job queue status by type and status
- Parameter indexing statistics
- DocumentGroup linking coverage
- Error analysis
- Export to JSON and console

Usage: python D6-cad-extraction-report.py [--output-format json|text] [--detailed]
"""

import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

import psycopg2

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
CONFIG_FILE = PROJECT_DIR / "config.txt"
OUTPUT_DIR = PROJECT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def load_config():
    """Load configuration from config.txt file."""
    if not CONFIG_FILE.exists():
        print(f"ERROR: Config file not found: {CONFIG_FILE}")
        sys.exit(1)

    config = {}
    with open(CONFIG_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
    return config


def get_cad_file_counts(conn) -> dict:
    """Get counts of CAD files in CloudFiles."""
    with conn.cursor() as cur:
        # Total CAD files
        cur.execute("""
            SELECT 
                SUM(CASE WHEN LOWER("LocalPath") LIKE '%%.prt%%' THEN 1 ELSE 0 END) as prt_count,
                SUM(CASE WHEN LOWER("LocalPath") LIKE '%%.asm%%' THEN 1 ELSE 0 END) as asm_count
            FROM "CloudFiles"
            WHERE LOWER("LocalPath") LIKE '%%.prt%%' 
               OR LOWER("LocalPath") LIKE '%%.asm%%'
        """)
        row = cur.fetchone()

        return {
            "prt_files": row[0] or 0,
            "asm_files": row[1] or 0,
            "total": (row[0] or 0) + (row[1] or 0),
        }


def get_job_queue_status(conn) -> dict:
    """Get extraction job queue statistics."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                job_type,
                status,
                COUNT(*) as count
            FROM extraction_jobs
            WHERE job_type IN ('creo_part', 'creo_asm')
            GROUP BY job_type, status
            ORDER BY job_type, status
        """)
        rows = cur.fetchall()

        result = {
            "by_type_status": [],
            "totals": {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "skipped": 0,
            },
        }

        for job_type, status, count in rows:
            result["by_type_status"].append(
                {
                    "job_type": job_type,
                    "status": status,
                    "count": count,
                }
            )
            if status in result["totals"]:
                result["totals"][status] += count

        result["totals"]["total"] = sum(result["totals"].values())

        return result


def get_extraction_metadata_stats(conn) -> dict:
    """Get extracted_metadata statistics for CAD files."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                source_type,
                extraction_status,
                COUNT(*) as count,
                SUM(CASE WHEN has_parameters THEN 1 ELSE 0 END) as with_params,
                SUM(CASE WHEN has_bom THEN 1 ELSE 0 END) as with_bom,
                AVG(parameter_count) as avg_params
            FROM extracted_metadata
            WHERE source_type IN ('creo_part', 'creo_asm')
            GROUP BY source_type, extraction_status
            ORDER BY source_type, extraction_status
        """)
        rows = cur.fetchall()

        result = {
            "by_type_status": [],
            "totals": {
                "total": 0,
                "with_parameters": 0,
                "with_bom": 0,
            },
        }

        for source_type, status, count, with_params, with_bom, avg_params in rows:
            result["by_type_status"].append(
                {
                    "source_type": source_type,
                    "status": status,
                    "count": count,
                    "with_parameters": with_params or 0,
                    "with_bom": with_bom or 0,
                    "avg_parameters": round(avg_params or 0, 1),
                }
            )
            result["totals"]["total"] += count
            result["totals"]["with_parameters"] += with_params or 0
            result["totals"]["with_bom"] += with_bom or 0

        return result


def get_parameter_stats(conn) -> dict:
    """Get extracted_parameters statistics."""
    with conn.cursor() as cur:
        # Total parameters
        cur.execute("SELECT COUNT(*) FROM extracted_parameters")
        total = cur.fetchone()[0]

        # By category
        cur.execute("""
            SELECT category, COUNT(*) 
            FROM extracted_parameters
            GROUP BY category
            ORDER BY COUNT(*) DESC
        """)
        by_category = cur.fetchall()

        # Designated parameters
        cur.execute("""
            SELECT COUNT(*) FROM extracted_parameters
            WHERE is_designated = TRUE
        """)
        designated = cur.fetchone()[0]

        # Numeric parameters
        cur.execute("""
            SELECT COUNT(*) FROM extracted_parameters
            WHERE value_numeric IS NOT NULL
        """)
        numeric = cur.fetchone()[0]

        return {
            "total": total,
            "designated": designated,
            "numeric": numeric,
            "by_category": [{"category": c, "count": n} for c, n in by_category],
        }


def get_linking_stats(conn) -> dict:
    """Get CAD-to-DocumentGroup linking statistics."""
    with conn.cursor() as cur:
        # CAD files linked to groups
        cur.execute("""
            SELECT COUNT(*) FROM document_group_members
            WHERE role = 'source_cad'
        """)
        linked = cur.fetchone()[0]

        # DocumentGroups with CAD files
        cur.execute("""
            SELECT COUNT(DISTINCT group_id) FROM document_group_members
            WHERE role = 'source_cad'
        """)
        groups_with_cad = cur.fetchone()[0]

        # Total DocumentGroups
        cur.execute("SELECT COUNT(*) FROM document_groups")
        total_groups = cur.fetchone()[0]

        return {
            "cad_files_linked": linked,
            "groups_with_cad": groups_with_cad,
            "total_groups": total_groups,
            "coverage_percent": round(100 * groups_with_cad / total_groups, 1)
            if total_groups > 0
            else 0,
        }


def get_error_summary(conn) -> dict:
    """Get summary of extraction errors."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT error, COUNT(*) as count
            FROM extraction_jobs
            WHERE job_type IN ('creo_part', 'creo_asm')
            AND status = 'failed'
            AND error IS NOT NULL
            GROUP BY error
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        rows = cur.fetchall()

        return {
            "top_errors": [{"error": e[:100], "count": c} for e, c in rows],
        }


def get_worker_activity(conn) -> dict:
    """Get worker activity statistics."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                worker_id,
                COUNT(*) as jobs_processed,
                MIN(started_at) as first_job,
                MAX(completed_at) as last_job
            FROM extraction_jobs
            WHERE job_type IN ('creo_part', 'creo_asm')
            AND worker_id IS NOT NULL
            GROUP BY worker_id
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        rows = cur.fetchall()

        return {
            "workers": [
                {
                    "worker_id": w,
                    "jobs_processed": j,
                    "first_job": f.isoformat() if f else None,
                    "last_job": l.isoformat() if l else None,
                }
                for w, j, f, l in rows
            ]
        }


def print_report(report: dict, detailed: bool = False):
    """Print report to console."""
    print("=" * 70)
    print("PHASE D: CAD EXTRACTION REPORT")
    print(f"Generated: {report['timestamp']}")
    print("=" * 70)

    # CAD Files
    cad = report["cad_files"]
    print("\n## CAD Files in CloudFiles")
    print(f"  .prt (parts):      {cad['prt_files']:,}")
    print(f"  .asm (assemblies): {cad['asm_files']:,}")
    print(f"  Total:             {cad['total']:,}")

    # Job Queue
    jobs = report["job_queue"]
    print("\n## Extraction Job Queue")
    print(f"  Pending:    {jobs['totals']['pending']:,}")
    print(f"  Processing: {jobs['totals']['processing']:,}")
    print(f"  Completed:  {jobs['totals']['completed']:,}")
    print(f"  Failed:     {jobs['totals']['failed']:,}")
    print(f"  Skipped:    {jobs['totals']['skipped']:,}")
    print(f"  Total:      {jobs['totals']['total']:,}")

    if detailed and jobs["by_type_status"]:
        print("\n  By Type and Status:")
        for item in jobs["by_type_status"]:
            print(f"    {item['job_type']:12} | {item['status']:12} | {item['count']:,}")

    # Extracted Metadata
    meta = report["extracted_metadata"]
    print("\n## Extracted Metadata")
    print(f"  Total records:      {meta['totals']['total']:,}")
    print(f"  With parameters:    {meta['totals']['with_parameters']:,}")
    print(f"  With BOM:           {meta['totals']['with_bom']:,}")

    if detailed and meta["by_type_status"]:
        print("\n  By Type and Status:")
        for item in meta["by_type_status"]:
            print(
                f"    {item['source_type']:12} | {item['status']:12} | {item['count']:,} | params: {item['with_parameters']:,}"
            )

    # Parameters
    params = report["parameters"]
    print("\n## Indexed Parameters")
    print(f"  Total parameters:   {params['total']:,}")
    print(f"  Designated:         {params['designated']:,}")
    print(f"  Numeric values:     {params['numeric']:,}")

    if detailed and params["by_category"]:
        print("\n  By Category:")
        for item in params["by_category"][:10]:
            print(f"    {item['category']:20} {item['count']:,}")

    # Linking
    linking = report["linking"]
    print("\n## DocumentGroup Linking")
    print(f"  CAD files linked:   {linking['cad_files_linked']:,}")
    print(f"  Groups with CAD:    {linking['groups_with_cad']:,}")
    print(f"  Total groups:       {linking['total_groups']:,}")
    print(f"  Coverage:           {linking['coverage_percent']}%")

    # Errors
    errors = report["errors"]
    if errors["top_errors"]:
        print("\n## Top Errors")
        for item in errors["top_errors"][:5]:
            print(f"  [{item['count']:,}] {item['error'][:60]}...")

    # Workers
    if detailed:
        workers = report["workers"]
        if workers["workers"]:
            print("\n## Worker Activity")
            for w in workers["workers"][:5]:
                print(f"  {w['worker_id']}: {w['jobs_processed']:,} jobs")

    # Integration Status
    print("\n## Creo Integration Status")
    print("  Status: PLACEHOLDER")
    print("  The D2 worker framework is ready but requires Creo API integration.")
    print("  Use D3 to import existing JSON files from Creo extraction.")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Generate CAD extraction report")
    parser.add_argument(
        "--output-format",
        "-f",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument("--detailed", "-d", action="store_true", help="Include detailed breakdowns")
    parser.add_argument(
        "--output-file", "-o", type=str, help="Output file path (default: auto-generated)"
    )
    args = parser.parse_args()

    # Load config and connect
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")

    if not db_url:
        print("ERROR: NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    conn = psycopg2.connect(db_url)

    # Gather all statistics
    report = {
        "timestamp": datetime.now().isoformat(),
        "cad_files": get_cad_file_counts(conn),
        "job_queue": get_job_queue_status(conn),
        "extracted_metadata": get_extraction_metadata_stats(conn),
        "parameters": get_parameter_stats(conn),
        "linking": get_linking_stats(conn),
        "errors": get_error_summary(conn),
        "workers": get_worker_activity(conn),
        "creo_integration": {
            "status": "placeholder",
            "message": "Creo API integration pending - use D3 to import existing JSON",
        },
    }

    conn.close()

    # Output
    if args.output_format == "json":
        output_file = args.output_file or (
            OUTPUT_DIR / f"D6-cad-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to: {output_file}")
    else:
        print_report(report, detailed=args.detailed)

        # Also save JSON
        output_file = OUTPUT_DIR / f"D6-cad-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nJSON report saved to: {output_file}")


if __name__ == "__main__":
    main()
