#!/usr/bin/env python3
"""
D2-creo-extraction-worker.py
Parallel Creo CAD extraction worker.

Features:
- Claims jobs using row-level locking (FOR UPDATE SKIP LOCKED)
- Downloads CAD files from B2 to local temp directory
- Invokes Creo extraction (PLACEHOLDER - requires Creo API integration)
- Stores extracted JSON in extracted_metadata.raw_data
- Graceful shutdown on Ctrl+C

CREO INTEGRATION STATUS: PLANNED
================================
The actual Creo extraction requires:
1. Creo Parametric running with API DLL loaded
2. Python script executed within Creo's Python environment
3. Model-specific extraction logic

Current implementation provides the worker framework.
The `extract_with_creo()` function is a placeholder that needs
to be replaced with actual Creo API calls.

Usage: python D2-creo-extraction-worker.py [--workers N] [--dry-run] [--limit N]
"""

import sys
import os
import signal
import logging
import argparse
import json
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from tqdm import tqdm

# Conditional imports
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
PROJECT_DIR = SCRIPT_DIR.parent.parent
CONFIG_FILE = PROJECT_DIR / "config.txt"
OUTPUT_DIR = PROJECT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Worker configuration
DEFAULT_WORKERS = 1  # Single worker by default (Creo is typically single-instance)
WORKER_ID = f"creo-worker-{uuid.uuid4().hex[:8]}"

# Shutdown event for graceful termination
shutdown_event = Event()

# ============================================================================
# CREO EXTRACTION PLACEHOLDER
# ============================================================================
#
# TODO: Replace this function with actual Creo API integration
#
# The Creo extraction process typically involves:
# 1. Starting Creo Parametric (or connecting to running instance)
# 2. Loading the model file (.prt or .asm)
# 3. Extracting data via Creo's Python API:
#    - Parameters (designated and user-defined)
#    - BOM (for assemblies)
#    - Feature tree
#    - Mass properties
#    - References/dependencies
# 4. Saving results as JSON
#
# Example Creo API pseudocode:
# ```python
# from creoson import Client
# client = Client()
# client.connect()
# client.file_open(filename)
# params = client.parameter_list()
# bom = client.bom_get_paths() if is_assembly else None
# mass_props = client.file_massprops()
# ```
# ============================================================================


def extract_with_creo(local_file_path: str, job_type: str) -> dict:
    """
    PLACEHOLDER: Extract metadata from Creo CAD file.

    This function should be replaced with actual Creo API integration.

    Args:
        local_file_path: Path to the downloaded .prt or .asm file
        job_type: 'creo_part' or 'creo_asm'

    Returns:
        dict: Extraction result with parameters, BOM, geometry, etc.
    """
    # PLACEHOLDER IMPLEMENTATION
    # Returns a stub result indicating Creo integration is pending

    filename = Path(local_file_path).name

    return {
        "status": "placeholder",
        "message": "Creo extraction not yet integrated - requires Creo API DLL",
        "filename": filename,
        "file_type": job_type,
        "extraction_timestamp": datetime.now().isoformat(),
        # Placeholder structure matching expected Creo output
        "parameters": [],
        "bom": [] if job_type == "creo_asm" else None,
        "mass_properties": None,
        "feature_tree": None,
        "references": [],
        # Integration notes
        "_integration_notes": {
            "required": [
                "Creo Parametric installation",
                "Creo API DLL loaded",
                "Python environment within Creo",
            ],
            "placeholder": True,
        },
    }


# ============================================================================
# WORKER INFRASTRUCTURE (FULLY FUNCTIONAL)
# ============================================================================


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


def claim_job(conn, job_types=("creo_part", "creo_asm")):
    """
    Claim a pending CAD extraction job using row-level locking.
    Returns (job_id, cloud_file_id, cloud_key, job_type) or None.
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
                    AND job_type = ANY(%s)
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id, cloud_file_id, job_type
            """,
                (WORKER_ID, list(job_types)),
            )

            row = cur.fetchone()
            if not row:
                return None

            job_id, cloud_file_id, job_type = row

            # Get the CloudKey for downloading
            cur.execute(
                """
                SELECT "CloudKey", "LocalPath" FROM "CloudFiles" WHERE "ID" = %s
            """,
                (cloud_file_id,),
            )

            cloud_row = cur.fetchone()
            if not cloud_row:
                conn.rollback()
                return None

            cloud_key, local_path = cloud_row
            # Extract just the filename from the full path
            filename = Path(local_path).name if local_path else ""

            conn.commit()
            return (job_id, cloud_file_id, cloud_key, job_type, filename)

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to claim job: {e}")
        return None


def complete_job(conn, job_id, cloud_file_id, result, success=True):
    """Mark job as completed and store extraction results."""
    try:
        with conn.cursor() as cur:
            is_placeholder = result.get("status") == "placeholder"

            if success and "error" not in result:
                # Determine status based on whether this is real or placeholder
                status = "completed" if not is_placeholder else "pending"

                # Count extracted items
                param_count = len(result.get("parameters", []))
                has_bom = bool(result.get("bom"))

                # Determine source type
                source_type = result.get("file_type", "creo_part")

                # Insert or update extracted_metadata
                cur.execute(
                    """
                    INSERT INTO extracted_metadata 
                    (cloud_file_id, source_type, extraction_type, extraction_status, 
                     raw_data, has_parameters, has_bom, parameter_count, worker_id)
                    VALUES (%s, %s, 'full', %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cloud_file_id) WHERE cloud_file_id IS NOT NULL
                    DO UPDATE SET
                        extraction_status = EXCLUDED.extraction_status,
                        raw_data = EXCLUDED.raw_data,
                        has_parameters = EXCLUDED.has_parameters,
                        has_bom = EXCLUDED.has_bom,
                        parameter_count = EXCLUDED.parameter_count,
                        worker_id = EXCLUDED.worker_id,
                        updated_at = NOW()
                    RETURNING id
                """,
                    (
                        cloud_file_id,
                        source_type,
                        status,
                        json.dumps(result),
                        param_count > 0,
                        has_bom,
                        param_count,
                        WORKER_ID,
                    ),
                )

                # Update job status
                job_status = "completed" if not is_placeholder else "skipped"
                cur.execute(
                    """
                    UPDATE extraction_jobs
                    SET status = %s, 
                        completed_at = NOW(), 
                        error = %s
                    WHERE id = %s
                """,
                    (
                        job_status,
                        "Placeholder - Creo integration pending" if is_placeholder else None,
                        job_id,
                    ),
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
    """Process a single CAD extraction job."""
    job_id, cloud_file_id, cloud_key, job_type, filename = job_data

    if not cloud_key:
        return {"job_id": job_id, "success": False, "error": "No CloudKey"}

    # Determine file extension for temp file
    ext = ".prt" if job_type == "creo_part" else ".asm"

    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Download from B2
        if not download_from_b2(b2_api, bucket_name, cloud_key, tmp_path):
            return {"job_id": job_id, "success": False, "error": "Download failed"}

        # Extract using Creo (PLACEHOLDER)
        result = extract_with_creo(tmp_path, job_type)

        # Add file metadata
        result["cloud_file_id"] = cloud_file_id
        result["cloud_key"] = cloud_key
        result["original_filename"] = filename

        return {
            "job_id": job_id,
            "cloud_file_id": cloud_file_id,
            "success": "error" not in result,
            "result": result,
        }

    except Exception as e:
        return {"job_id": job_id, "success": False, "error": str(e)}

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
            job_data = claim_job(conn)

            if not job_data:
                pool.putconn(conn)
                # No jobs available, wait a bit
                shutdown_event.wait(2)
                continue

            job_id, cloud_file_id, cloud_key, job_type, filename = job_data
            logger.info(f"Processing: {filename} ({job_type})")

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
                if extraction_result.get("status") == "placeholder":
                    stats["placeholder"] += 1
                else:
                    stats["completed"] += 1
            else:
                stats["failed"] += 1

        except Exception as e:
            logger.error(f"Worker error: {e}")
            if conn:
                pool.putconn(conn)
            shutdown_event.wait(2)


def main():
    parser = argparse.ArgumentParser(description="Parallel Creo CAD extraction worker")
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
    print("D2: CREO CAD EXTRACTION WORKER")
    print("=" * 70)
    print(f"Worker ID: {WORKER_ID}")
    print(f"Workers: {args.workers}")
    print()
    print("NOTE: Creo extraction is currently a PLACEHOLDER.")
    print("      Actual extraction requires Creo API integration.")
    print("      Jobs will be marked as 'skipped' until integrated.")
    print()
    if args.dry_run:
        print("MODE: DRY RUN")
    if args.limit > 0:
        print(f"LIMIT: {args.limit:,} jobs")
    print("=" * 70)

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
            WHERE status = 'pending' 
            AND job_type IN ('creo_part', 'creo_asm')
        """)
        pending_count = cur.fetchone()[0]

    conn.close()

    logger.info(f"Pending CAD extraction jobs: {pending_count:,}")

    if pending_count == 0:
        print("\nNo pending CAD jobs. Run D1-queue-cad-jobs.py first.")
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
    stats = {"completed": 0, "failed": 0, "placeholder": 0}

    # Progress bar
    pbar = tqdm(total=total_jobs, desc="Extracting CAD", unit="files")

    try:
        logger.info(f"Starting {args.workers} worker threads...")

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            # Submit worker threads
            futures = [
                executor.submit(worker_thread, pool, config, b2_api, bucket_name, pbar, stats)
                for _ in range(args.workers)
            ]

            # Wait for shutdown or completion
            while not shutdown_event.is_set():
                processed = stats["completed"] + stats["failed"] + stats["placeholder"]

                if args.limit > 0 and processed >= args.limit:
                    logger.info("Limit reached. Shutting down...")
                    shutdown_event.set()
                    break

                # Check if all jobs are done
                conn = pool.getconn()
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COUNT(*) FROM extraction_jobs 
                        WHERE status = 'pending' 
                        AND job_type IN ('creo_part', 'creo_asm')
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
    print(f"Completed (real):     {stats['completed']:,}")
    print(f"Placeholder (stub):   {stats['placeholder']:,}")
    print(f"Failed:               {stats['failed']:,}")
    print(f"Total processed:      {stats['completed'] + stats['placeholder'] + stats['failed']:,}")

    if stats["placeholder"] > 0:
        print()
        print("NOTE: Placeholder jobs need Creo API integration to extract real data.")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "worker_id": WORKER_ID,
        "workers": args.workers,
        "completed": stats["completed"],
        "placeholder": stats["placeholder"],
        "failed": stats["failed"],
        "total_processed": stats["completed"] + stats["placeholder"] + stats["failed"],
        "creo_integrated": False,
    }

    report_file = OUTPUT_DIR / f"D2-creo-extraction-{WORKER_ID}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
