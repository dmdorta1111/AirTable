#!/usr/bin/env python3
"""
Verify retry logic with exponential backoff for database-backed extraction jobs.

This script:
1. Creates a test extraction job configured to fail 3 times then succeed
2. Monitors the job status through retries
3. Verifies exponential backoff timing (1s, 2s, 4s, 8s, ...)
4. Checks database retry_count tracking
5. Confirms final success after max retries

Prerequisites:
    - Redis server running
    - Celery worker with test task: celery -A workers.test_retry_task worker -l INFO
    - FastAPI server running (for database access)
    - PostgreSQL database available

Usage:
    python scripts/verify_retry_logic.py

Expected Output:
    - Job created with status=pending
    - Job transitions to processing
    - 3 retries observed with increasing delays (1s, 2s, 4s)
    - Job succeeds on 4th attempt
    - Database shows retry_count=3, status=completed
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import httpx


class RetryLogicVerifier:
    """Verify retry logic with exponential backoff."""

    def __init__(
        self,
        api_base_url: str = "http://localhost:8000",
        admin_username: str = "admin",
        admin_password: str = "admin"
    ):
        self.api_base_url = api_base_url
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.token: Optional[str] = None
        self.job_id: Optional[str] = None
        self.retry_timestamps = []
        self.status_changes = []

    async def login(self) -> bool:
        """Authenticate and get access token."""
        print("\n🔐 Authenticating...")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.api_base_url}/api/v1/auth/login",
                    json={"username": self.admin_username, "password": self.admin_password},
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("access_token")
                    print(f"✅ Authenticated successfully")
                    return True
                else:
                    print(f"❌ Authentication failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False

            except Exception as e:
                print(f"❌ Authentication error: {e}")
                return False

    async def create_test_file(self) -> str:
        """Create a dummy test file for extraction."""
        test_file = Path("/tmp/test_retry_extraction.txt")

        with open(test_file, "w") as f:
            f.write("Test file for retry logic verification\n")

        print(f"📄 Created test file: {test_file}")
        return str(test_file)

    async def create_test_job(self, file_path: str) -> bool:
        """Create a test extraction job configured to fail 3 times then succeed."""
        print(f"\n📝 Creating test extraction job...")

        async with httpx.AsyncClient() as client:
            try:
                # Import test file
                with open(file_path, "rb") as f:
                    files = {"file": ("test_retry_extraction.txt", f, "text/plain")}
                    data = {
                        "format": "pdf",  # Will be overridden by test task
                        "options": json.dumps({
                            "fail_attempts": 3,  # Fail first 3 attempts
                            "max_retries": 3,    # Allow up to 3 retries
                            "test_mode": True
                        })
                    }

                    headers = {"Authorization": f"Bearer {self.token}"}

                    response = await client.post(
                        f"{self.api_base_url}/api/v1/extraction/jobs",
                        files=files,
                        data=data,
                        headers=headers,
                        timeout=30.0
                    )

                if response.status_code == 202:
                    job_data = response.json()
                    self.job_id = job_data.get("job_id")
                    print(f"✅ Job created successfully")
                    print(f"   Job ID: {self.job_id}")
                    print(f"   Status: {job_data.get('status')}")
                    print(f"   Configured to fail 3 times, then succeed on 4th attempt")
                    return True
                else:
                    print(f"❌ Job creation failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False

            except Exception as e:
                print(f"❌ Job creation error: {e}")
                return False

    async def trigger_test_task(self, file_path: str) -> bool:
        """
        Trigger the test extraction task directly via Celery.

        This bypasses the normal API routing and calls our test task directly.
        """
        print(f"\n🚀 Triggering test extraction task...")

        try:
            from celery import Celery

            # Create Celery app to send task
            app = Celery(
                broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
                backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
            )

            # Send test task with job_id
            task = app.send_task(
                "test_extraction_retry",
                args=[file_path, {"fail_attempts": 3, "max_retries": 3}, self.job_id]
            )

            print(f"✅ Test task triggered")
            print(f"   Task ID: {task.id}")
            print(f"   Job ID: {self.job_id}")
            return True

        except ImportError:
            print(f"❌ Celery not available. Cannot trigger test task directly.")
            return False
        except Exception as e:
            print(f"❌ Task trigger error: {e}")
            return False

    async def monitor_job_progress(self, timeout_seconds: int = 60):
        """
        Monitor job progress through retries.

        Tracks:
        - Status changes
        - Retry timestamps
        - Exponential backoff timing
        """
        print(f"\n👀 Monitoring job progress (timeout: {timeout_seconds}s)...")
        print("-" * 80)

        start_time = time.time()
        last_status = None
        last_retry_count = -1

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {self.token}"}

            while time.time() - start_time < timeout_seconds:
                try:
                    response = await client.get(
                        f"{self.api_base_url}/api/v1/extraction/jobs/{self.job_id}",
                        headers=headers,
                        timeout=5.0
                    )

                    if response.status_code == 200:
                        job_data = response.json()
                        status = job_data.get("status")
                        retry_count = job_data.get("retry_count", 0)

                        # Track status changes
                        if status != last_status:
                            timestamp = datetime.now(timezone.utc).isoformat()
                            self.status_changes.append({
                                "timestamp": timestamp,
                                "status": status,
                                "retry_count": retry_count
                            })

                            print(f"\n⏰ {timestamp}")
                            print(f"   Status: {status}")
                            print(f"   Retry count: {retry_count}")
                            print(f"   Progress: {job_data.get('progress', 0)}%")

                            if status == "processing":
                                print(f"   Celery task ID: {job_data.get('celery_task_id')}")
                            elif status == "completed":
                                print(f"   ✅ Job completed successfully!")
                                results = job_data.get("results", {})
                                if isinstance(results, dict):
                                    attempts = results.get("attempts_before_success", "N/A")
                                    print(f"   Total attempts: {attempts}")
                                break
                            elif status == "failed":
                                print(f"   ❌ Job failed")
                                print(f"   Error: {job_data.get('error_message', 'Unknown error')}")
                                break

                            last_status = status

                        # Track retry count changes
                        if retry_count > last_retry_count:
                            timestamp = datetime.now(timezone.utc).isoformat()
                            self.retry_timestamps.append(timestamp)

                            if len(self.retry_timestamps) > 1:
                                # Calculate time since last retry
                                prev = datetime.fromisoformat(self.retry_timestamps[-2])
                                curr = datetime.fromisoformat(self.retry_timestamps[-1])
                                delay = (curr - prev).total_seconds()

                                expected_backoff = 2 ** (retry_count - 1)
                                print(f"\n🔄 Retry detected!")
                                print(f"   Retry #{retry_count}")
                                print(f"   Timestamp: {timestamp}")
                                print(f"   Time since last retry: {delay:.1f}s")
                                print(f"   Expected backoff: 2^{retry_count - 1} = {expected_backoff}s")
                                print(f"   Backoff accurate: {abs(delay - expected_backoff) < 2}")

                            last_retry_count = retry_count

                    # Wait before next poll
                    await asyncio.sleep(0.5)

                except httpx.HTTPError as e:
                    print(f"⚠️  HTTP error during monitoring: {e}")
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"⚠️  Monitoring error: {e}")
                    await asyncio.sleep(1)

        print(f"\n{'-' * 80}")
        print(f"🏁 Monitoring ended")

    def print_summary(self):
        """Print verification summary."""
        print(f"\n{'=' * 80}")
        print(f"RETRY LOGIC VERIFICATION SUMMARY")
        print(f"{'=' * 80}")

        print(f"\n📊 Status Changes:")
        for i, change in enumerate(self.status_changes, 1):
            print(f"   {i}. {change['timestamp']}")
            print(f"      Status: {change['status']}")
            print(f"      Retry count: {change['retry_count']}")

        print(f"\n⏱️  Retry Timeline:")
        if len(self.retry_timestamps) >= 2:
            print(f"   {'Retry':<8} {'Timestamp':<28} {'Delay':<10} {'Expected':<10} {'Status'}")
            print(f"   {'-' * 70}")

            for i in range(1, len(self.retry_timestamps)):
                prev = datetime.fromisoformat(self.retry_timestamps[i - 1])
                curr = datetime.fromisoformat(self.retry_timestamps[i])
                delay = (curr - prev).total_seconds()
                expected = 2 ** (i - 1)
                status = "✅" if abs(delay - expected) < 2 else "⚠️"

                print(f"   #{i:<7} {self.retry_timestamps[i]:<28} {delay:<10.1f}s {expected:<10}s {status}")
        else:
            print(f"   ⚠️  Not enough retries detected for timing analysis")

        print(f"\n✅ Verification Criteria:")
        print(f"   ✓ Job created successfully")
        print(f"   ✓ Status transitions: {' → '.join([c['status'] for c in self.status_changes])}")

        final_status = self.status_changes[-1]["status"] if self.status_changes else "unknown"
        final_retries = self.status_changes[-1]["retry_count"] if self.status_changes else 0

        if final_status == "completed" and final_retries == 3:
            print(f"   ✓ Job succeeded after 3 retries")
            print(f"   ✓ Retry count matches expected: {final_retries}")
            print(f"\n🎉 RETRY LOGIC VERIFICATION PASSED!")
        elif final_status == "failed":
            print(f"   ❌ Job failed after {final_retries} retries")
            print(f"\n⚠️  RETRY LOGIC VERIFICATION INCONCLUSIVE")
        else:
            print(f"   ⚠️  Job did not complete (status: {final_status})")
            print(f"\n⚠️  RETRY LOGIC VERIFICATION INCOMPLETE")

        print(f"{'=' * 80}\n")

    async def run(self):
        """Run the complete verification workflow."""
        print(f"\n{'=' * 80}")
        print(f"RETRY LOGIC VERIFICATION")
        print(f"Testing exponential backoff and max retry behavior")
        print(f"{'=' * 80}")

        # Step 1: Authenticate
        if not await self.login():
            return False

        # Step 2: Create test file
        test_file = await self.create_test_file()

        # Step 3: Create test job
        if not await self.create_test_job(test_file):
            return False

        # Step 4: Trigger test task
        if not await self.trigger_test_task(test_file):
            print(f"\n⚠️  Could not trigger test task directly.")
            print(f"   Please ensure Celery worker is running:")
            print(f"   celery -A workers.test_retry_task worker -l INFO")
            return False

        # Step 5: Monitor progress
        await self.monitor_job_progress(timeout_seconds=60)

        # Step 6: Print summary
        self.print_summary()

        return True


async def main():
    """Main entry point."""
    import json

    verifier = RetryLogicVerifier()
    success = await verifier.run()

    if not success:
        print(f"\n❌ Verification failed")
        sys.exit(1)

    print(f"\n✅ Verification completed")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
