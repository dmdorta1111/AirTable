#!/usr/bin/env python3
"""
B4-dxf-extraction-worker.py
Parallel DXF extraction worker using ThreadPoolExecutor.

Similar to B3 but specialized for DXF files using ezdxf:
- Extract layers, blocks, entity counts
- Extract dimension entities
- Extract text entities
- Index into extracted_dimensions

Usage: python B4-dxf-extraction-worker.py [--workers N] [--dry-run] [--limit N]
"""

import sys
import os
import signal
import logging
import argparse
import json
import re
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Event
from collections import defaultdict

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from tqdm import tqdm

# Conditional imports
try:
    import ezdxf
    from ezdxf.entities import DXFEntity

    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False
    print("WARNING: ezdxf not installed. Install with: pip install ezdxf")

try:
    from b2sdk.v2 import InMemoryAccountInfo, B2Api

    HAS_B2 = True
except ImportError:
    HAS_B2 = False
    print("WARNING: b2sdk not installed. Install with: pip install b2sdk")

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(threadName)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
PLAN_DIR = SCRIPT_DIR.parent
CONFIG_FILE = PLAN_DIR / "config.txt"
OUTPUT_DIR = PLAN_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Worker configuration
DEFAULT_WORKERS = 50
WORKER_ID = f"dxf-worker-{uuid.uuid4().hex[:8]}"

# Shutdown event for graceful termination
shutdown_event = Event()

# Material patterns (same as PDF worker)
MATERIAL_PATTERNS = [
    r"\b(304\s*(?:SS|STAINLESS|S\.S\.)?)\b",
    r"\b(316\s*(?:SS|STAINLESS|S\.S\.)?)\b",
    r"\b(STAINLESS\s*STEEL(?:\s*\d{3})?)\b",
    r"\b(ALUMINUM\s*\d{4}(?:-T\d)?)\b",
    r"\b(6061(?:-T6)?)\b",
    r"\b(CARBON\s*STEEL)\b",
    r"\b(MILD\s*STEEL)\b",
    r"\b(BRASS)\b",
    r"\b(BRONZE)\b",
    r"\b(DELRIN)\b",
    r"\b(NYLON)\b",
    r"MATERIAL[:\s]+([A-Z0-9\s\-]+)",
]


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


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Shutdown signal received. Finishing current jobs...")
    shutdown_event.set()


def setup_b2_client(config):
    """Initialize B2 client."""
    if not HAS_B2:
        return None

    key_id = config.get("B2_APPLICATION_KEY_ID")
    app_key = config.get("B2_APPLICATION_KEY")

    if not key_id or not app_key:
        logger.error("B2 credentials not found in config")
        return None

    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", key_id, app_key)

    return b2_api


def download_from_b2(b2_api, bucket_name, cloud_key, local_path):
    """Download file from B2 to local path."""
    try:
        bucket = b2_api.get_bucket_by_name(bucket_name)
        downloaded_file = bucket.download_file_by_name(cloud_key)
        downloaded_file.save_to(local_path)
        return True
    except Exception as e:
        logger.error(f"B2 download failed for {cloud_key}: {e}")
        return False


def extract_materials_from_text(text):
    """Extract material specifications from text."""
    materials = []
    seen = set()

    for pattern in MATERIAL_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            material_name = match.strip().upper()
            if material_name and material_name not in seen and len(material_name) > 2:
                seen.add(material_name)
                materials.append({"material_name": material_name, "raw_match": match})

    return materials


def extract_dxf(dxf_path):
    """
    Extract metadata, dimensions, text, and layer info from a DXF file.
    Returns extraction result dict.
    """
    if not HAS_EZDXF:
        return {"error": "ezdxf not installed"}

    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()

        result = {
            "dxf_version": doc.dxfversion,
            "layers": [],
            "blocks": [],
            "entity_counts": {},
            "dimensions": [],
            "text_entities": [],
            "materials": [],
            "total_entities": 0,
            "extraction_timestamp": datetime.now().isoformat(),
        }

        # Extract layers
        for layer in doc.layers:
            layer_name = layer.dxf.name
            if not layer_name.startswith("*"):  # Skip internal layers
                result["layers"].append(
                    {
                        "name": layer_name,
                        "color": layer.dxf.color,
                        "is_on": layer.is_on(),
                        "is_frozen": layer.is_frozen(),
                    }
                )

        # Extract blocks (non-internal)
        for block in doc.blocks:
            block_name = block.name
            if not block_name.startswith("*"):  # Skip internal blocks
                result["blocks"].append({"name": block_name, "entity_count": len(list(block))})

        # Process modelspace entities
        all_text = []

        for entity in msp:
            etype = entity.dxftype()
            result["entity_counts"][etype] = result["entity_counts"].get(etype, 0) + 1
            result["total_entities"] += 1

            # Extract dimensions
            if etype == "DIMENSION":
                try:
                    dim_value = entity.dxf.actual_measurement
                    dim_type = "linear"

                    # Determine dimension type
                    dim_type_code = getattr(entity.dxf, "dimtype", 0) & 0x0F
                    if dim_type_code == 2:
                        dim_type = "angular"
                    elif dim_type_code == 3:
                        dim_type = "diameter"
                    elif dim_type_code == 4:
                        dim_type = "radial"
                    elif dim_type_code == 5:
                        dim_type = "angular"  # 3-point angular
                    elif dim_type_code == 6:
                        dim_type = "ordinate"

                    if dim_value and 0.001 <= abs(dim_value) <= 100000:
                        result["dimensions"].append(
                            {
                                "value": round(dim_value, 6),
                                "type": dim_type,
                                "layer": entity.dxf.layer,
                            }
                        )
                except (AttributeError, TypeError):
                    pass

            # Extract text entities
            elif etype == "TEXT":
                try:
                    text_content = entity.dxf.text
                    if text_content and text_content.strip():
                        result["text_entities"].append(
                            {
                                "text": text_content.strip()[:500],
                                "layer": entity.dxf.layer,
                                "height": getattr(entity.dxf, "height", None),
                            }
                        )
                        all_text.append(text_content)
                except AttributeError:
                    pass

            elif etype == "MTEXT":
                try:
                    text_content = entity.text
                    if text_content and text_content.strip():
                        # Clean up MTEXT formatting codes
                        clean_text = re.sub(r"\\[A-Za-z][^;]*;", "", text_content)
                        clean_text = re.sub(r"\{|\}", "", clean_text)
                        result["text_entities"].append(
                            {
                                "text": clean_text.strip()[:500],
                                "layer": entity.dxf.layer,
                                "type": "mtext",
                            }
                        )
                        all_text.append(clean_text)
                except AttributeError:
                    pass

        # Extract materials from all text
        full_text = "\n".join(all_text)
        result["materials"] = extract_materials_from_text(full_text)

        # Deduplicate dimensions by value
        seen_values = set()
        unique_dims = []
        for dim in result["dimensions"]:
            key = (dim["value"], dim["type"])
            if key not in seen_values:
                seen_values.add(key)
                unique_dims.append(dim)
        result["dimensions"] = unique_dims

        return result

    except Exception as e:
        return {"error": str(e)}


def claim_job(conn, job_type="dxf_extract"):
    """
    Claim a pending job using row-level locking.
    Returns (job_id, cloud_file_id, cloud_key) or None if no jobs available.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE extraction_jobs
                SET status = 'processing',
                    worker_id = %s,
                    started_at = NOW()
                WHERE id = (
                    SELECT id FROM extraction_jobs
                    WHERE status = 'pending' 
                    AND job_type = %s
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id, cloud_file_id
            """,
                (WORKER_ID, job_type),
            )

            row = cur.fetchone()
            if not row:
                return None

            job_id, cloud_file_id = row

            # Get the CloudKey for downloading
            cur.execute(
                """
                SELECT "CloudKey" FROM "CloudFiles" WHERE "ID" = %s
            """,
                (cloud_file_id,),
            )

            cloud_row = cur.fetchone()
            cloud_key = cloud_row[0] if cloud_row else None

            conn.commit()
            return (job_id, cloud_file_id, cloud_key)

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to claim job: {e}")
        return None


def complete_job(conn, job_id, cloud_file_id, result, success=True):
    """Mark job as completed and store extraction results."""
    try:
        with conn.cursor() as cur:
            if success and "error" not in result:
                status = "completed"

                # Insert or update extracted_metadata
                cur.execute(
                    """
                    INSERT INTO extracted_metadata 
                    (cloud_file_id, source_type, extraction_type, extraction_status, 
                     raw_data, has_dimensions, has_parameters, dimension_count, worker_id)
                    VALUES (%s, 'dxf', 'full', %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cloud_file_id) WHERE cloud_file_id IS NOT NULL
                    DO UPDATE SET
                        extraction_status = EXCLUDED.extraction_status,
                        raw_data = EXCLUDED.raw_data,
                        has_dimensions = EXCLUDED.has_dimensions,
                        dimension_count = EXCLUDED.dimension_count,
                        worker_id = EXCLUDED.worker_id,
                        updated_at = NOW()
                    RETURNING id
                """,
                    (
                        cloud_file_id,
                        status,
                        json.dumps(result),
                        len(result.get("dimensions", [])) > 0,
                        len(result.get("materials", [])) > 0,
                        len(result.get("dimensions", [])),
                        WORKER_ID,
                    ),
                )

                metadata_row = cur.fetchone()
                metadata_id = metadata_row[0] if metadata_row else None

                # Index dimensions
                if metadata_id and result.get("dimensions"):
                    for dim in result["dimensions"][:200]:  # Limit to 200 dims per file
                        dim_type = dim.get("type", "linear")
                        cur.execute(
                            """
                            INSERT INTO extracted_dimensions 
                            (metadata_id, cloud_file_id, value, unit, dimension_type, layer)
                            VALUES (%s, %s, %s, 'mm', %s, %s)
                            ON CONFLICT DO NOTHING
                        """,
                            (metadata_id, cloud_file_id, dim["value"], dim_type, dim.get("layer")),
                        )

                # Index materials
                if metadata_id and result.get("materials"):
                    for mat in result["materials"][:20]:
                        cur.execute(
                            """
                            INSERT INTO extracted_materials 
                            (metadata_id, cloud_file_id, material_name)
                            VALUES (%s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """,
                            (metadata_id, cloud_file_id, mat["material_name"][:255]),
                        )

                # Update job status
                cur.execute(
                    """
                    UPDATE extraction_jobs
                    SET status = %s, completed_at = NOW(), error = NULL
                    WHERE id = %s
                """,
                    (status, job_id),
                )

                # Update CloudFiles extraction_status
                cur.execute(
                    """
                    UPDATE "CloudFiles"
                    SET extraction_status = %s
                    WHERE "ID" = %s
                """,
                    (status, cloud_file_id),
                )

            else:
                # Failed extraction
                error_msg = result.get("error", "Unknown error")

                cur.execute(
                    """
                    UPDATE extraction_jobs
                    SET status = 'failed', 
                        completed_at = NOW(), 
                        error = %s,
                        retry_count = retry_count + 1
                    WHERE id = %s
                """,
                    (error_msg[:500], job_id),
                )

                cur.execute(
                    """
                    UPDATE "CloudFiles"
                    SET extraction_status = 'failed'
                    WHERE "ID" = %s
                """,
                    (cloud_file_id,),
                )

            conn.commit()
            return True

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to complete job {job_id}: {e}")
        return False


def process_job(job_data, config, b2_api, bucket_name):
    """Process a single DXF extraction job."""
    job_id, cloud_file_id, cloud_key = job_data

    if not cloud_key:
        return {"job_id": job_id, "success": False, "error": "No CloudKey"}

    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Download from B2
        if not download_from_b2(b2_api, bucket_name, cloud_key, tmp_path):
            return {"job_id": job_id, "success": False, "error": "Download failed"}

        # Extract DXF
        result = extract_dxf(tmp_path)

        return {
            "job_id": job_id,
            "cloud_file_id": cloud_file_id,
            "success": "error" not in result,
            "result": result,
        }

    finally:
        # Cleanup temp file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def worker_thread(pool, config, b2_api, bucket_name, pbar, stats):
    """Worker thread that continuously processes jobs."""
    while not shutdown_event.is_set():
        conn = None
        try:
            conn = pool.getconn()

            # Claim a job
            job_data = claim_job(conn, "dxf_extract")

            if not job_data:
                pool.putconn(conn)
                # No jobs available, wait a bit
                shutdown_event.wait(1)
                continue

            job_id, cloud_file_id, cloud_key = job_data

            # Process the job
            result = process_job(job_data, config, b2_api, bucket_name)

            # Complete the job
            success = result.get("success", False)
            extraction_result = result.get("result", {"error": result.get("error", "Unknown")})

            complete_job(conn, job_id, cloud_file_id, extraction_result, success)

            pool.putconn(conn)

            # Update progress
            pbar.update(1)
            if success:
                stats["completed"] += 1
            else:
                stats["failed"] += 1

        except Exception as e:
            logger.error(f"Worker error: {e}")
            if conn:
                pool.putconn(conn)
            shutdown_event.wait(1)


def main():
    parser = argparse.ArgumentParser(description="Parallel DXF extraction worker")
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of parallel workers (default: {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show pending jobs without processing"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Limit total jobs to process (0 = unlimited)"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("B4: DXF EXTRACTION WORKER")
    print("=" * 70)
    print(f"Worker ID: {WORKER_ID}")
    print(f"Workers: {args.workers}")
    if args.dry_run:
        print("MODE: DRY RUN")
    if args.limit > 0:
        print(f"LIMIT: {args.limit:,} jobs")
    print("=" * 70)

    # Check dependencies
    if not HAS_EZDXF:
        logger.error("ezdxf is required. Install with: pip install ezdxf")
        sys.exit(1)

    if not HAS_B2:
        logger.error("b2sdk is required. Install with: pip install b2sdk")
        sys.exit(1)

    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Load config
    config = load_config()
    db_url = config.get("NEON_DATABASE_URL")
    bucket_name = config.get("B2_BUCKET_NAME", "EmjacDB")

    if not db_url:
        logger.error("NEON_DATABASE_URL not found in config.txt")
        sys.exit(1)

    # Initialize B2
    logger.info("Initializing B2 client...")
    b2_api = setup_b2_client(config)
    if not b2_api:
        logger.error("Failed to initialize B2 client")
        sys.exit(1)

    # Get pending job count
    logger.info("Connecting to database...")
    conn = psycopg2.connect(db_url)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM extraction_jobs 
            WHERE status = 'pending' AND job_type = 'dxf_extract'
        """)
        pending_count = cur.fetchone()[0]

    conn.close()

    logger.info(f"Pending DXF extraction jobs: {pending_count:,}")

    if pending_count == 0:
        print("\nNo pending jobs. Nothing to process.")
        return

    if args.dry_run:
        print(
            f"\nDRY RUN: Would process up to {min(pending_count, args.limit) if args.limit else pending_count:,} jobs"
        )
        return

    # Calculate total jobs to process
    total_jobs = min(pending_count, args.limit) if args.limit > 0 else pending_count

    # Create connection pool
    logger.info(f"Creating connection pool with {args.workers + 2} connections...")
    pool = ThreadedConnectionPool(minconn=2, maxconn=args.workers + 2, dsn=db_url)

    # Stats tracking
    stats = {"completed": 0, "failed": 0}

    # Progress bar
    pbar = tqdm(total=total_jobs, desc="Extracting DXFs", unit="files")

    try:
        logger.info(f"Starting {args.workers} worker threads...")

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            # Submit worker threads
            futures = [
                executor.submit(worker_thread, pool, config, b2_api, bucket_name, pbar, stats)
                for _ in range(args.workers)
            ]

            # Wait for shutdown or completion
            processed = 0
            while not shutdown_event.is_set():
                processed = stats["completed"] + stats["failed"]

                if args.limit > 0 and processed >= args.limit:
                    logger.info("Limit reached. Shutting down...")
                    shutdown_event.set()
                    break

                # Check if all jobs are done
                conn = pool.getconn()
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COUNT(*) FROM extraction_jobs 
                        WHERE status = 'pending' AND job_type = 'dxf_extract'
                    """)
                    remaining = cur.fetchone()[0]
                pool.putconn(conn)

                if remaining == 0:
                    logger.info("All jobs completed!")
                    shutdown_event.set()
                    break

                shutdown_event.wait(2)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        shutdown_event.set()
    finally:
        pbar.close()
        pool.closeall()

    # Print summary
    print("\n" + "=" * 70)
    print("EXTRACTION SUMMARY")
    print("=" * 70)
    print(f"Completed:       {stats['completed']:,}")
    print(f"Failed:          {stats['failed']:,}")
    print(f"Total processed: {stats['completed'] + stats['failed']:,}")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "worker_id": WORKER_ID,
        "workers": args.workers,
        "completed": stats["completed"],
        "failed": stats["failed"],
        "total_processed": stats["completed"] + stats["failed"],
    }

    report_file = OUTPUT_DIR / f"B4-dxf-extraction-{WORKER_ID}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
