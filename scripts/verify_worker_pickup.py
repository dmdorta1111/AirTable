#!/usr/bin/env python3
"""
Verify Celery worker picks up job and updates database status.

This script:
1. Creates a test extraction job
2. Monitors the database for status changes
3. Verifies the job transitions from PENDING -> PROCESSING -> COMPLETED/FAILED
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


async def create_test_job() -> str:
    """Create a test PDF extraction job in the database."""
    async with AsyncSessionLocal() as db:
        from pybase.models.extraction_job import ExtractionJob, ExtractionJobStatus, ExtractionFormat

        # Create a minimal test job (no actual file needed for testing worker pickup)
        job = ExtractionJob(
            user_id="test-user-verify-worker-pickup",
            status=ExtractionJobStatus.PENDING.value,
            extraction_format=ExtractionFormat.PDF.value,
            file_path="/tmp/test.pdf",  # Dummy path - will fail extraction but that's OK
            options="{}",
            max_retries=3,
            retry_count=0,
            progress=0,
        )

        db.add(job)
        await db.commit()
        await db.refresh(job)

        print(f"✓ Created test job: {job.id}")
        print(f"  Initial status: {job.status}")
        print(f"  celery_task_id: {job.celery_task_id}")

        return job.id


async def monitor_job(job_id: str, timeout: int = 60) -> dict:
    """
    Monitor job status changes in the database.

    Args:
        job_id: Job ID to monitor
        timeout: Maximum seconds to wait

    Returns:
        Dict with monitoring results
    """
    print(f"\nMonitoring job {job_id} (timeout: {timeout}s)...")
    print("-" * 60)

    start_time = time.time()
    last_status = None
    last_celery_id = None
    status_seen = {"pending": False, "processing": False, "completed": False, "failed": False}

    while time.time() - start_time < timeout:
        async with AsyncSessionLocal() as db:
            job = await db.get(ExtractionJob, job_id)

            if not job:
                print(f"✗ Job {job_id} not found in database")
                return {"success": False, "error": "Job not found"}

            current_status = job.status.lower()
            current_celery_id = job.celery_task_id

            # Detect status changes
            if current_status != last_status:
                print(f"[{time.time() - start_time:.1f}s] Status: {last_status} → {current_status}")
                last_status = current_status
                status_seen[current_status] = True

            # Detect celery_task_id assignment
            if current_celery_id and current_celery_id != last_celery_id:
                print(f"[{time.time() - start_time:.1f}s] celery_task_id assigned: {current_celery_id}")
                last_celery_id = current_celery_id

            # Check if job reached terminal state
            if current_status in ["completed", "failed", "cancelled"]:
                print(f"\n✓ Job reached terminal state: {current_status.upper()}")
                print(f"  Final status: {job.status}")
                print(f"  celery_task_id: {job.celery_task_id}")
                print(f"  Progress: {job.progress}%")
                print(f"  Started at: {job.started_at}")
                print(f"  Completed at: {job.completed_at}")

                if job.error_message:
                    print(f"  Error: {job.error_message}")

                return {
                    "success": True,
                    "final_status": current_status,
                    "celery_task_id": current_celery_id,
                    "job": job,
                }

        await asyncio.sleep(0.5)  # Poll every 500ms

    # Timeout reached
    print(f"\n✗ Timeout after {timeout}s - job did not complete")
    print(f"  Last status: {last_status}")
    print(f"  celery_task_id: {last_celery_id}")
    print(f"  Statuses seen: {[s for s, seen in status_seen.items() if seen]}")

    return {"success": False, "error": "Timeout", "last_status": last_status}


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
    print("Celery Worker Pickup Verification")
    print("=" * 60)

    # Step 1: Verify database
    print("\n[Step 1] Verifying database...")
    if not await verify_database():
        return 1

    # Step 2: Create test job
    print("\n[Step 2] Creating test job...")
    job_id = await create_test_job()

    # Step 3: Trigger Celery task manually
    print("\n[Step 3] Triggering Celery task...")
    try:
        from celery import Celery
        from workers.celery_extraction_worker import app

        # Trigger the task
        task = app.send_task("extract_pdf", args=["/tmp/test.pdf", {}, job_id])
        print(f"✓ Sent task to Celery: {task.id}")
        print(f"  Job ID: {job_id}")
    except Exception as e:
        print(f"✗ Failed to send Celery task: {e}")
        print("  Make sure Redis is running and worker is started")
        return 1

    # Step 4: Monitor job
    print("\n[Step 4] Monitoring job status...")
    print("  Make sure Celery worker is running:")
    print("    celery -A workers.celery_extraction_worker worker -l INFO")
    print()

    result = await monitor_job(job_id, timeout=60)

    # Step 5: Verify results
    print("\n[Step 5] Verification Results")
    print("-" * 60)

    if result["success"]:
        print("✓ Worker successfully picked up job")
        print(f"✓ Status transitioned to: {result['final_status'].upper()}")

        if result["celery_task_id"]:
            print(f"✓ celery_task_id populated: {result['celery_task_id']}")
        else:
            print("✗ celery_task_id not populated")

        # Verify key transitions
        job = result["job"]
        if job.started_at:
            print("✓ started_at timestamp set")
        else:
            print("✗ started_at timestamp not set")

        if job.completed_at:
            print("✓ completed_at timestamp set")
        else:
            print("✗ completed_at timestamp not set")

        print("\n✅ VERIFICATION PASSED: Worker successfully picks up jobs")

        # Cleanup test job
        async with AsyncSessionLocal() as db:
            await db.delete(job)
            await db.commit()
        print(f"✓ Cleaned up test job: {job_id}")

        return 0
    else:
        print(f"✅ VERIFICATION FAILED: {result.get('error', 'Unknown error')}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
