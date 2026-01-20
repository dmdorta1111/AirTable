#!/usr/bin/env python3
"""
B7-extraction-report.py
Generate comprehensive extraction summary report.

Outputs: output/extraction-report.json

Stats included:
- Total files processed by type
- Status breakdown (completed, skipped, failed, pending)
- Content type breakdown (vector vs raster PDFs)
- Dimension and material counts
- Top extracted materials
- Processing performance metrics

Usage: python B7-extraction-report.py
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
    print("B7: EXTRACTION REPORT")
    print("=" * 70)
    print("Generating comprehensive extraction statistics")
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
            "phase": "B - PDF/DXF Extraction",
            "summary": {},
            "jobs": {},
            "extractions": {},
            "dimensions": {},
            "materials": {},
            "content_types": {},
            "performance": {},
        }

        with conn.cursor() as cur:
            # ============================================
            # 1. OVERALL SUMMARY
            # ============================================
            logger.info("Gathering overall statistics...")

            # Total CloudFiles
            cur.execute('SELECT COUNT(*) FROM "CloudFiles"')
            total_files = cur.fetchone()[0]

            # PDFs and DXFs
            cur.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE LOWER("CloudKey") LIKE '%%.pdf') as pdf_count,
                    COUNT(*) FILTER (WHERE LOWER("CloudKey") LIKE '%%.dxf') as dxf_count
                FROM "CloudFiles"
            """)
            row = cur.fetchone()
            pdf_count, dxf_count = row

            # Files with extraction_status
            cur.execute("""
                SELECT extraction_status, COUNT(*)
                FROM "CloudFiles"
                WHERE extraction_status IS NOT NULL
                GROUP BY extraction_status
            """)
            status_counts = {status: count for status, count in cur.fetchall()}

            report["summary"] = {
                "total_cloudfiles": total_files,
                "total_pdfs": pdf_count,
                "total_dxfs": dxf_count,
                "extraction_status_counts": status_counts,
            }

            # ============================================
            # 2. EXTRACTION JOBS STATUS
            # ============================================
            logger.info("Gathering job queue statistics...")

            cur.execute("""
                SELECT 
                    job_type,
                    status,
                    COUNT(*) as count,
                    MIN(created_at) as oldest,
                    MAX(completed_at) as newest_completed
                FROM extraction_jobs
                GROUP BY job_type, status
                ORDER BY job_type, status
            """)

            jobs_by_type = {}
            for job_type, status, count, oldest, newest in cur.fetchall():
                if job_type not in jobs_by_type:
                    jobs_by_type[job_type] = {}
                jobs_by_type[job_type][status] = {
                    "count": count,
                    "oldest": oldest.isoformat() if oldest else None,
                    "newest_completed": newest.isoformat() if newest else None,
                }

            # Total jobs
            cur.execute("SELECT COUNT(*) FROM extraction_jobs")
            total_jobs = cur.fetchone()[0]

            # Failed jobs with retry potential
            cur.execute("""
                SELECT COUNT(*) FROM extraction_jobs 
                WHERE status = 'failed' AND retry_count < max_retries
            """)
            retriable_jobs = cur.fetchone()[0]

            report["jobs"] = {
                "total": total_jobs,
                "by_type_and_status": jobs_by_type,
                "retriable_failed": retriable_jobs,
            }

            # ============================================
            # 3. EXTRACTED METADATA STATISTICS
            # ============================================
            logger.info("Gathering extraction metadata statistics...")

            cur.execute("""
                SELECT 
                    source_type::text,
                    extraction_status::text,
                    COUNT(*) as count,
                    SUM(dimension_count) as total_dims,
                    AVG(dimension_count) as avg_dims,
                    COUNT(*) FILTER (WHERE has_dimensions) as with_dims,
                    COUNT(*) FILTER (WHERE has_parameters) as with_materials
                FROM extracted_metadata
                GROUP BY source_type, extraction_status
                ORDER BY source_type, extraction_status
            """)

            extractions_by_type = {}
            for (
                source_type,
                status,
                count,
                total_dims,
                avg_dims,
                with_dims,
                with_mats,
            ) in cur.fetchall():
                if source_type not in extractions_by_type:
                    extractions_by_type[source_type] = {}
                extractions_by_type[source_type][status] = {
                    "count": count,
                    "total_dimensions": int(total_dims) if total_dims else 0,
                    "avg_dimensions": round(float(avg_dims), 2) if avg_dims else 0,
                    "files_with_dimensions": with_dims,
                    "files_with_materials": with_mats,
                }

            # Total extractions
            cur.execute("SELECT COUNT(*) FROM extracted_metadata")
            total_extractions = cur.fetchone()[0]

            report["extractions"] = {
                "total": total_extractions,
                "by_source_type": extractions_by_type,
            }

            # ============================================
            # 4. CONTENT TYPE BREAKDOWN (PDF)
            # ============================================
            logger.info("Analyzing PDF content types...")

            cur.execute("""
                SELECT 
                    raw_data->>'content_type' as content_type,
                    COUNT(*) as count
                FROM extracted_metadata
                WHERE source_type = 'pdf'
                AND raw_data IS NOT NULL
                GROUP BY raw_data->>'content_type'
            """)

            content_types = {ct or "unknown": count for ct, count in cur.fetchall()}
            report["content_types"] = content_types

            # ============================================
            # 5. DIMENSIONS STATISTICS
            # ============================================
            logger.info("Gathering dimension statistics...")

            cur.execute("SELECT COUNT(*) FROM extracted_dimensions")
            total_dimensions = cur.fetchone()[0]

            cur.execute("""
                SELECT dimension_type::text, COUNT(*)
                FROM extracted_dimensions
                GROUP BY dimension_type
                ORDER BY COUNT(*) DESC
            """)
            dims_by_type = {dtype: count for dtype, count in cur.fetchall()}

            # Dimension value distribution
            cur.execute("""
                SELECT 
                    CASE 
                        WHEN value < 1 THEN '<1mm'
                        WHEN value < 10 THEN '1-10mm'
                        WHEN value < 50 THEN '10-50mm'
                        WHEN value < 100 THEN '50-100mm'
                        WHEN value < 500 THEN '100-500mm'
                        ELSE '>500mm'
                    END as range,
                    COUNT(*)
                FROM extracted_dimensions
                GROUP BY 1
                ORDER BY 1
            """)
            dims_by_range = {r: count for r, count in cur.fetchall()}

            report["dimensions"] = {
                "total": total_dimensions,
                "by_type": dims_by_type,
                "by_value_range": dims_by_range,
            }

            # ============================================
            # 6. MATERIALS STATISTICS
            # ============================================
            logger.info("Gathering material statistics...")

            cur.execute("SELECT COUNT(*) FROM extracted_materials")
            total_materials = cur.fetchone()[0]

            cur.execute("SELECT COUNT(DISTINCT material_name) FROM extracted_materials")
            unique_materials = cur.fetchone()[0]

            # Top materials
            cur.execute("""
                SELECT material_name, COUNT(*) as count
                FROM extracted_materials
                GROUP BY material_name
                ORDER BY count DESC
                LIMIT 30
            """)
            top_materials = {name: count for name, count in cur.fetchall()}

            report["materials"] = {
                "total_entries": total_materials,
                "unique_materials": unique_materials,
                "top_30": top_materials,
            }

            # ============================================
            # 7. PERFORMANCE METRICS
            # ============================================
            logger.info("Calculating performance metrics...")

            # Average processing time
            cur.execute("""
                SELECT 
                    job_type,
                    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_seconds,
                    MIN(EXTRACT(EPOCH FROM (completed_at - started_at))) as min_seconds,
                    MAX(EXTRACT(EPOCH FROM (completed_at - started_at))) as max_seconds,
                    COUNT(*)
                FROM extraction_jobs
                WHERE status = 'completed'
                AND started_at IS NOT NULL
                AND completed_at IS NOT NULL
                GROUP BY job_type
            """)

            perf_by_type = {}
            for job_type, avg_sec, min_sec, max_sec, count in cur.fetchall():
                perf_by_type[job_type] = {
                    "count": count,
                    "avg_seconds": round(avg_sec, 3) if avg_sec else 0,
                    "min_seconds": round(min_sec, 3) if min_sec else 0,
                    "max_seconds": round(max_sec, 3) if max_sec else 0,
                }

            # Workers that processed files
            cur.execute("""
                SELECT worker_id, COUNT(*) as files_processed
                FROM extraction_jobs
                WHERE worker_id IS NOT NULL
                GROUP BY worker_id
                ORDER BY files_processed DESC
                LIMIT 10
            """)
            top_workers = {wid: count for wid, count in cur.fetchall()}

            report["performance"] = {"by_job_type": perf_by_type, "top_workers": top_workers}

        conn.close()

        # ============================================
        # PRINT REPORT
        # ============================================
        print("\n" + "=" * 70)
        print("EXTRACTION REPORT SUMMARY")
        print("=" * 70)

        # Summary
        s = report["summary"]
        print(f"\n{'=' * 40}")
        print("OVERALL")
        print(f"{'=' * 40}")
        print(f"Total CloudFiles:        {s['total_cloudfiles']:,}")
        print(f"Total PDFs:              {s['total_pdfs']:,}")
        print(f"Total DXFs:              {s['total_dxfs']:,}")

        if s["extraction_status_counts"]:
            print("\nCloudFiles by extraction_status:")
            for status, count in sorted(s["extraction_status_counts"].items()):
                print(f"  {status}: {count:,}")

        # Jobs
        print(f"\n{'=' * 40}")
        print("EXTRACTION JOBS")
        print(f"{'=' * 40}")
        print(f"Total jobs:              {report['jobs']['total']:,}")
        print(f"Retriable failed:        {report['jobs']['retriable_failed']:,}")

        job_table = []
        for job_type, statuses in report["jobs"]["by_type_and_status"].items():
            for status, data in statuses.items():
                job_table.append([job_type, status, data["count"]])

        if job_table:
            print("\nBy Type and Status:")
            print(tabulate(job_table, headers=["Type", "Status", "Count"], tablefmt="simple"))

        # Extractions
        print(f"\n{'=' * 40}")
        print("EXTRACTED METADATA")
        print(f"{'=' * 40}")
        print(f"Total extractions:       {report['extractions']['total']:,}")

        ext_table = []
        for src_type, statuses in report["extractions"]["by_source_type"].items():
            for status, data in statuses.items():
                ext_table.append(
                    [
                        src_type,
                        status,
                        data["count"],
                        data["total_dimensions"],
                        data["files_with_dimensions"],
                        data["files_with_materials"],
                    ]
                )

        if ext_table:
            print(
                tabulate(
                    ext_table,
                    headers=["Source", "Status", "Files", "Dims", "W/Dims", "W/Mat"],
                    tablefmt="simple",
                )
            )

        # Content Types
        if report["content_types"]:
            print(f"\n{'=' * 40}")
            print("PDF CONTENT TYPES")
            print(f"{'=' * 40}")
            for ct, count in sorted(report["content_types"].items(), key=lambda x: -x[1]):
                print(f"  {ct}: {count:,}")

        # Dimensions
        print(f"\n{'=' * 40}")
        print("DIMENSIONS")
        print(f"{'=' * 40}")
        print(f"Total indexed:           {report['dimensions']['total']:,}")

        if report["dimensions"]["by_type"]:
            print("\nBy Type:")
            for dtype, count in sorted(
                report["dimensions"]["by_type"].items(), key=lambda x: -x[1]
            ):
                print(f"  {dtype}: {count:,}")

        if report["dimensions"]["by_value_range"]:
            print("\nBy Value Range:")
            for rng, count in sorted(report["dimensions"]["by_value_range"].items()):
                print(f"  {rng}: {count:,}")

        # Materials
        print(f"\n{'=' * 40}")
        print("MATERIALS")
        print(f"{'=' * 40}")
        print(f"Total entries:           {report['materials']['total_entries']:,}")
        print(f"Unique materials:        {report['materials']['unique_materials']:,}")

        if report["materials"]["top_30"]:
            print("\nTop 15 Materials:")
            for i, (mat, count) in enumerate(list(report["materials"]["top_30"].items())[:15], 1):
                print(f"  {i:2}. {mat}: {count:,}")

        # Performance
        if report["performance"]["by_job_type"]:
            print(f"\n{'=' * 40}")
            print("PERFORMANCE")
            print(f"{'=' * 40}")
            perf_table = []
            for job_type, data in report["performance"]["by_job_type"].items():
                perf_table.append(
                    [
                        job_type,
                        data["count"],
                        f"{data['avg_seconds']:.2f}s",
                        f"{data['min_seconds']:.2f}s",
                        f"{data['max_seconds']:.2f}s",
                    ]
                )
            print(
                tabulate(
                    perf_table, headers=["Type", "Count", "Avg", "Min", "Max"], tablefmt="simple"
                )
            )

        # Save report
        report_file = OUTPUT_DIR / "extraction-report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\n{'=' * 70}")
        print(f"Full report saved to: {report_file}")
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
