#!/usr/bin/env python3
"""
Simple manual verification script for retry logic with exponential backoff.

This is a simplified version that provides step-by-step instructions
for manual verification of retry behavior.

Usage:
    python scripts/verify_retry_manual.py
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import httpx


def print_header(title: str):
    """Print formatted header."""
    print(f"\n{'=' * 80}")
    print(f"{title:^80}")
    print(f"{'=' * 80}\n")


def print_step(step_num: int, title: str):
    """Print formatted step."""
    print(f"\n{'─' * 80}")
    print(f"STEP {step_num}: {title}")
    print(f"{'─' * 80}")


async def check_api_status(api_base_url: str = "http://localhost:8000") -> bool:
    """Check if FastAPI server is running."""
    print_step(1, "Check FastAPI Server Status")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_base_url}/api/v1/health", timeout=5.0)

            if response.status_code == 200:
                print("✅ FastAPI server is running")
                return True
            else:
                print(f"⚠️  FastAPI server returned status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to FastAPI server: {e}")
        print(f"   Start server: uvicorn pybase.main:app --reload")
        return False


async def check_redis_status() -> bool:
    """Check if Redis server is running."""
    print_step(2, "Check Redis Server Status")

    try:
        import redis

        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis server is running")
        return True
    except Exception as e:
        print(f"❌ Cannot connect to Redis server: {e}")
        print(f"   Start Redis: redis-server")
        return False


async def authenticate(
    api_base_url: str = "http://localhost:8000",
    username: str = "admin",
    password: str = "admin"
) -> str:
    """Authenticate and get token."""
    print_step(3, "Authenticate")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_base_url}/api/v1/auth/login",
                json={"username": username, "password": password},
                timeout=10.0
            )

            if response.status_code == 200:
                token = response.json().get("access_token")
                print("✅ Authentication successful")
                return token
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return None

    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None


async def create_test_job(
    token: str,
    api_base_url: str = "http://localhost:8000"
) -> str:
    """Create a test job that will fail 3 times then succeed."""
    print_step(4, "Create Test Extraction Job")

    # Create dummy test file
    test_file = "/tmp/test_retry_manual.txt"
    with open(test_file, "w") as f:
        f.write("Test file for retry logic verification\n")

    print(f"📄 Created test file: {test_file}")

    try:
        import json

        async with httpx.AsyncClient() as client:
            with open(test_file, "rb") as f:
                files = {"file": ("test_retry_manual.txt", f, "text/plain")}
                data = {
                    "format": "pdf",
                    "options": json.dumps({
                        "fail_attempts": 3,
                        "max_retries": 3
                    })
                }

                headers = {"Authorization": f"Bearer {token}"}

                response = await client.post(
                    f"{api_base_url}/api/v1/extraction/jobs",
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=30.0
                )

            if response.status_code == 202:
                job_id = response.json().get("job_id")
                print(f"✅ Job created successfully")
                print(f"   Job ID: {job_id}")
                print(f"   Status: pending")
                print(f"\n   ⚠️  IMPORTANT: This job will use the standard PDF extraction task.")
                print(f"   ⚠️  To test retry behavior, use the dedicated test task instead:")
                print(f"   ⚠️  See README_SUBTASK_5_4.md for detailed instructions.")
                return job_id
            else:
                print(f"❌ Job creation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None

    except Exception as e:
        print(f"❌ Job creation error: {e}")
        return None


async def query_job_status(
    job_id: str,
    token: str,
    api_base_url: str = "http://localhost:8000"
):
    """Query current job status."""
    print_step(5, "Query Job Status")

    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}

            response = await client.get(
                f"{api_base_url}/api/v1/extraction/jobs/{job_id}",
                headers=headers,
                timeout=10.0
            )

            if response.status_code == 200:
                job = response.json()

                print(f"📊 Job Status:")
                print(f"   Job ID: {job.get('job_id')}")
                print(f"   Status: {job.get('status')}")
                print(f"   Retry count: {job.get('retry_count', 0)}")
                print(f"   Progress: {job.get('progress', 0)}%")
                print(f"   Created at: {job.get('created_at')}")
                print(f"   Started at: {job.get('started_at')}")
                print(f"   Completed at: {job.get('completed_at')}")
                print(f"   Celery task ID: {job.get('celery_task_id')}")
                print(f"   Error message: {job.get('error_message', 'None')}")

                return job
            else:
                print(f"❌ Failed to query job: {response.status_code}")
                return None

    except Exception as e:
        print(f"❌ Query error: {e}")
        return None


async def main():
    """Main verification workflow."""
    print_header("MANUAL RETRY LOGIC VERIFICATION")

    print("This script provides step-by-step guidance for verifying retry logic.")
    print("For automated verification with the test task, see: verify_retry_logic.py")
    print("\nPrerequisites:")
    print("  1. FastAPI server running: uvicorn pybase.main:app --reload")
    print("  2. Redis server running: redis-server")
    print("  3. Celery worker with test task: celery -A workers.test_retry_task worker -l INFO")
    print("\nFor detailed instructions, see: scripts/README_SUBTASK_5_4.md")

    # Check prerequisites
    api_ok = await check_api_status()
    redis_ok = await check_redis_status()

    if not (api_ok and redis_ok):
        print("\n❌ Prerequisites not met. Please start required services.")
        return False

    # Authenticate
    token = await authenticate()
    if not token:
        print("\n❌ Authentication failed. Please check credentials.")
        return False

    # Create test job
    job_id = await create_test_job(token)
    if not job_id:
        print("\n❌ Failed to create test job.")
        return False

    # Query initial status
    await query_job_status(job_id, token)

    # Provide next steps
    print_step(6, "Next Steps - Manual Verification")
    print("\n✅ Test job created and ready.")
    print("\n📝 Manual verification steps:")
    print(f"   1. Trigger test task manually:")
    print(f"      python -c \"from celery import Celery; app = Celery('test', broker='redis://localhost:6379/1');")
    print(f"      task = app.send_task('test_extraction_retry', args=['/tmp/test_retry_manual.txt', {{'fail_attempts': 3, 'max_retries': 3}}, '{job_id}']); print(f'Task ID: {{task.id}}')\"")
    print(f"\n   2. Watch Celery worker logs for retry attempts:")
    print(f"      You should see:")
    print(f"      - Attempt 1: Fail, retry in 1s (2^0)")
    print(f"      - Attempt 2: Fail, retry in 2s (2^1)")
    print(f"      - Attempt 3: Fail, retry in 4s (2^2)")
    print(f"      - Attempt 4: Success!")
    print(f"\n   3. Monitor job status via API:")
    print(f"      curl -H \"Authorization: Bearer {token}\" \\")
    print(f"           http://localhost:8000/api/v1/extraction/jobs/{job_id}")
    print(f"\n   4. Query database directly:")
    print(f"      SELECT retry_count, status, error_message, started_at, completed_at")
    print(f"      FROM pybase.extraction_jobs")
    print(f"      WHERE id = '{job_id}';")
    print(f"\n   5. Verify:")
    print(f"      ✓ retry_count increments with each attempt")
    print(f"      ✓ Status transitions: pending → processing → retrying → completed")
    print(f"      ✓ Timing between retries follows exponential backoff (1s, 2s, 4s)")
    print(f"      ✓ Job succeeds after 3 retries")

    print_step(7, "Automated Verification Alternative")
    print("\nFor automated verification with detailed timing analysis:")
    print("   python scripts/verify_retry_logic.py")

    print(f"\n{'=' * 80}\n")

    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
        sys.exit(1)
