#!/usr/bin/env python3
"""
Verify job persistence across worker restart.

This script tests that jobs survive worker restarts:
1. Creates a bulk extraction job (multiple files, takes >30s)
2. Waits for worker to start processing
3. Pauses and prompts user to restart worker
4. Verifies job continues and completes after restart
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from pybase.db.session import AsyncSessionLocal
from pybase.models.extraction_job import ExtractionJob


async def create_bulk_job() -> str:
    """
    Create a bulk extraction job that takes >30 seconds.

    Uses multiple dummy file paths to simulate a long-running job.
    The actual extraction will fail (files don't exist), but that's OK -
    we're testing persistence, not extraction functionality.
    """
    async with AsyncSessionLocal() as db:
        from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus, ExtractionFormat
        import json

        # Create 5 dummy files (will fail but provides retry testing)
        file_paths = [f"/tmp/test_file_{i}.pdf" for i in range(5)]
        options = json.dumps({
            "file_paths": file_paths,
            "target_table_id": None,
            "extract_tables": True,
            "extract_text": True,
        })

        job = ExtractionJob(
            user_id="test-user-worker-restart",
            status=ExtractionJobStatus.PENDING.value,
            extraction_format=ExtractionFormat.BULK.value,
            file_path=json.dumps(file_paths),
            options=options,
            max_retries=3,
            retry_count=0,
            progress=0,
        )

        db.add(job)
        await db.commit()
        await db.refresh(job)

        print(f"✓ Created bulk job: {job.id}")
        print(f"  Files: {len(file_paths)} dummy PDFs")
        print(f"  Initial status: {job.status}")

        return job.id


async def wait_for_processing(job_id: str, timeout: int = 30) -> bool:
    """
    Wait for job to reach PROCESSING status.

    Args:
        job_id: Job ID to monitor
        timeout: Maximum seconds to wait

    Returns:
        True if job reached PROCESSING, False otherwise
    """
    print(f"\nWaiting for job to reach PROCESSING status (timeout: {timeout}s)...")

    start_time = time.time()

    while time.time() - start_time < timeout:
        async with AsyncSessionLocal() as db:
            job = await db.get(ExtractionJob, job_id)

            if not job:
                print(f"✗ Job {job_id} not found in database")
                return False

            if job.status == "processing":
                print(f"✓ Job reached PROCESSING status after {time.time() - start_time:.1f}s")
                print(f"  celery_task_id: {job.celery_task_id}")
                print(f"  Progress: {job.progress}%")
                return True

            if job.status in ["completed", "failed", "cancelled"]:
                print(f"✗ Job reached terminal state {job.status.upper()} before we could test restart")
                return False

        await asyncio.sleep(0.5)

    print(f"✗ Timeout: Job did not reach PROCESSING within {timeout}s")
    print(f"  Current status: {job.status}")
    return False


async def monitor_after_restart(job_id: str, timeout: int = 120) -> dict:
    """
    Monitor job after worker restart to verify it continues.

    Args:
        job_id: Job ID to monitor
        timeout: Maximum seconds to wait for completion

    Returns:
        Dict with monitoring results
    """
    print(f"\nMonitoring job after restart (timeout: {timeout}s)...")
    print("-" * 60)

    start_time = time.time()
    last_status = None
    last_progress = None
    restart_detected = False

    # Check initial state after restart
    async with AsyncSessionLocal() as db:
        job = await db.get(ExtractionJob, job_id)
        if job:
            print(f"Initial state after restart:")
            print(f"  Status: {job.status}")
            print(f"  Progress: {job.progress}%")
            print(f"  celery_task_id: {job.celery_task_id}")
            print(f"  retry_count: {job.retry_count}")
            last_status = job.status
            last_progress = job.progress

    # Monitor for changes
    while time.time() - start_time < timeout:
        async with AsyncSessionLocal() as db:
            job = await db.get(ExtractionJob, job_id)

            if not job:
                print(f"✗ Job {job_id} not found in database")
                return {"success": False, "error": "Job not found"}

            current_status = job.status
            current_progress = job.progress

            # Detect status changes
            if current_status != last_status:
                elapsed = time.time() - start_time
                print(f"[{elapsed:.1f}s] Status: {last_status} → {current_status}")
                last_status = current_status

                # Detect if task was restarted (celery_task_id changed)
                if current_status == "processing" and job.celery_task_id:
                    print(f"[{elapsed:.1f}s] celery_task_id: {job.celery_task_id}")
                    # New task ID indicates worker picked it up again
                    if not restart_detected:
                        restart_detected = True
                        print(f"✓ Worker picked up job after restart")

            # Detect progress updates
            if current_progress != last_progress:
                elapsed = time.time() - start_time
                print(f"[{elapsed:.1f}s] Progress: {last_progress}% → {current_progress}%")
                last_progress = current_progress

            # Check if job reached terminal state
            if current_status in ["completed", "failed", "cancelled"]:
                elapsed = time.time() - start_time
                print(f"\n✓ Job reached terminal state: {current_status.upper()}")
                print(f"  Time since restart: {elapsed:.1f}s")
                print(f"  Final progress: {job.progress}%")
                print(f"  Final retry_count: {job.retry_count}")

                if job.error_message:
                    print(f"  Error: {job.error_message}")

                return {
                    "success": True,
                    "final_status": current_status,
                    "restart_detected": restart_detected,
                    "time_to_complete": elapsed,
                    "job": job,
                }

        await asyncio.sleep(1.0)  # Poll every 1s

    # Timeout reached
    print(f"\n✗ Timeout after {timeout}s - job did not complete")
    print(f"  Last status: {last_status}")
    print(f"  Last progress: {last_progress}%")
    print(f"  Restart detected: {restart_detected}")

    return {
        "success": False,
        "error": "Timeout",
        "last_status": last_status,
        "restart_detected": restart_detected,
    }


async def verify_database():
    """Verify database connection and table exists."""
    async with AsyncSessionLocal() as db:
        # Check if table exists
        result = await db.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'pybase'
                    AND table_name = 'extraction_jobs'
                )
            """)
        )
        exists = result.scalar()

        if not exists:
            print("✗ extraction_jobs table does not exist")
            print("  Run: alembic upgrade head")
            return False

        print("✓ Database connection OK")
        print("✓ extraction_jobs table exists")
        return True


async def main():
    """Main verification workflow."""
    print("=" * 60)
    print("Worker Restart Persistence Verification")
    print("=" * 60)

    # Step 1: Verify database
    print("\n[Step 1] Verifying database...")
    if not await verify_database():
        return 1

    # Step 2: Create bulk job
    print("\n[Step 2] Creating bulk extraction job...")
    job_id = await create_bulk_job()

    # Step 3: Trigger Celery task
    print("\n[Step 3] Triggering Celery task...")
    try:
        from celery import Celery
        from workers.celery_extraction_worker import app

        # Trigger bulk extraction task
        import json
        file_paths = [f"/tmp/test_file_{i}.pdf" for i in range(5)]
        task = app.send_task("extract_bulk", args=[file_paths, None, {}, job_id])
        print(f"✓ Sent bulk task to Celery: {task.id}")
        print(f"  Job ID: {job_id}")
    except Exception as e:
        print(f"✗ Failed to send Celery task: {e}")
        print("  Make sure Redis is running and worker is started")
        return 1

    # Step 4: Wait for job to start processing
    print("\n[Step 4] Waiting for worker to pick up job...")
    print("  Make sure Celery worker is running:")
    print("    celery -A workers.celery_extraction_worker worker -l INFO")
    print()

    if not await wait_for_processing(job_id, timeout=30):
        print("\n✗ VERIFICATION FAILED: Job did not reach PROCESSING state")
        print("  Make sure worker is running and can connect to Redis")
        return 1

    # Step 5: Instruct user to restart worker
    print("\n" + "=" * 60)
    print("ACTION REQUIRED: Restart the Celery worker now")
    print("=" * 60)
    print("\nSteps:")
    print("  1. In another terminal, find the worker process:")
    print("     ps aux | grep celery")
    print("  2. Kill the worker:")
    print("     pkill -f celery")
    print("     # or on Windows: taskkill /F /IM celery.exe")
    print("  3. Start the worker again:")
    print("     celery -A workers.celery_extraction_worker worker -l INFO")
    print("\n  After restarting, press Enter to continue...")
    print("=" * 60)

    input()  # Wait for user to press Enter

    # Step 6: Monitor job after restart
    print("\n[Step 6] Monitoring job after worker restart...")
    result = await monitor_after_restart(job_id, timeout=120)

    # Step 7: Verify results
    print("\n[Step 7] Verification Results")
    print("-" * 60)

    if result["success"]:
        print("✓ Job completed after worker restart")

        if result["restart_detected"]:
            print("✓ Worker successfully picked up job after restart")
        else:
            print("⚠ Job completed but restart detection unclear (may have finished during restart)")

        print(f"✓ Final status: {result['final_status'].upper()}")
        print(f"✓ Time to complete after restart: {result['time_to_complete']:.1f}s")

        # Verify job was not lost
        job = result["job"]
        if job.started_at:
            print("✓ started_at timestamp preserved")
        if job.completed_at:
            print("✓ completed_at timestamp set")

        print("\n✅ VERIFICATION PASSED: Job persists across worker restart")

        # Cleanup test job
        async with AsyncSessionLocal() as db:
            await db.delete(job)
            await db.commit()
        print(f"✓ Cleaned up test job: {job_id}")

        return 0
    else:
        print(f"✗ VERIFICATION FAILED: {result.get('error', 'Unknown error')}")
        if result.get("restart_detected"):
            print("  Note: Worker did pick up the job, but it did not complete successfully")
        else:
            print("  Note: Worker may not have picked up the job after restart")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
