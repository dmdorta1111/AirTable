#!/usr/bin/env python3
"""
Verify job persistence across worker restart using API.

This script tests that jobs survive worker restarts by:
1. Creating a bulk extraction job via API
2. Waiting for worker to start processing
3. Prompting user to restart worker
4. Verifying job continues and completes via API
"""

import sys
import time
import requests
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
AUTH_TOKEN = None  # Will be obtained via login


def login(username: str = "admin", password: str = "admin") -> str:
    """Login and get auth token."""
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={"username": username, "password": password}
    )

    if response.status_code != 200:
        print(f"✗ Login failed: {response.status_code}")
        print(f"  {response.text}")
        sys.exit(1)

    data = response.json()
    token = data.get("access_token")
    print(f"✓ Logged in as {username}")
    return token


def create_bulk_job(token: str) -> str:
    """
    Create a bulk extraction job via API.

    Uses a small test file that will trigger extraction.
    """
    # Create a minimal test PDF file
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pdf", delete=False) as f:
        # Write minimal PDF header
        f.write("%PDF-1.4\n")
        f.write("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
        f.write("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
        f.write("3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n")
        f.write("xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n")
        f.write("trailer\n<< /Size 4 /Root 1 0 R >>\n")
        f.write("startxref\n0\n")
        f.write("%%EOF\n")
        temp_path = f.name

    try:
        # Submit bulk extraction job
        with open(temp_path, "rb") as f:
            files = {"files": ("test.pdf", f, "application/pdf")}
            data = {
                "format": "pdf",
                "extract_tables": True,
                "extract_text": True,
            }

            response = requests.post(
                f"{API_BASE_URL}/extraction/bulk",
                headers={"Authorization": f"Bearer {token}"},
                files=files,
                data=data,
            )

        if response.status_code != 202:
            print(f"✗ Failed to create job: {response.status_code}")
            print(f"  {response.text}")
            sys.exit(1)

        result = response.json()
        job_id = result.get("job_id")

        print(f"✓ Created bulk job: {job_id}")
        print(f"  Format: PDF")
        print(f"  Files: 1 test PDF")

        return job_id

    finally:
        # Cleanup temp file
        Path(temp_path).unlink(missing_ok=True)


def get_job_status(token: str, job_id: str) -> dict:
    """Get job status via API."""
    response = requests.get(
        f"{API_BASE_URL}/extraction/bulk/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 404:
        return None
    elif response.status_code != 200:
        print(f"✗ Failed to get job status: {response.status_code}")
        print(f"  {response.text}")
        return None

    return response.json()


def wait_for_processing(token: str, job_id: str, timeout: int = 30) -> bool:
    """Wait for job to reach PROCESSING status."""
    print(f"\nWaiting for job to reach PROCESSING status (timeout: {timeout}s)...")

    start_time = time.time()

    while time.time() - start_time < timeout:
        status = get_job_status(token, job_id)

        if not status:
            print(f"✗ Job {job_id} not found")
            return False

        job_status = status.get("status", "").lower()

        if job_status == "processing":
            elapsed = time.time() - start_time
            print(f"✓ Job reached PROCESSING status after {elapsed:.1f}s")
            print(f"  Progress: {status.get('progress', 0)}%")
            return True

        if job_status in ["completed", "failed", "cancelled"]:
            print(f"✗ Job reached terminal state {job_status.upper()} before restart")
            return False

        time.sleep(0.5)

    print(f"✗ Timeout: Job did not reach PROCESSING within {timeout}s")
    return False


def monitor_after_restart(token: str, job_id: str, timeout: int = 120) -> dict:
    """Monitor job after worker restart."""
    print(f"\nMonitoring job after restart (timeout: {timeout}s)...")
    print("-" * 60)

    start_time = time.time()
    last_status = None
    last_progress = None
    restart_detected = False

    # Get initial state
    status = get_job_status(token, job_id)
    if status:
        print(f"Initial state after restart:")
        print(f"  Status: {status.get('status')}")
        print(f"  Progress: {status.get('progress', 0)}%")
        print(f"  Retry count: {status.get('retry_count', 0)}")
        last_status = status.get("status")
        last_progress = status.get("progress", 0)

    # Monitor for changes
    while time.time() - start_time < timeout:
        status = get_job_status(token, job_id)

        if not status:
            print(f"✗ Job {job_id} not found")
            return {"success": False, "error": "Job not found"}

        current_status = status.get("status", "").lower()
        current_progress = status.get("progress", 0)

        # Detect status changes
        if current_status != last_status:
            elapsed = time.time() - start_time
            print(f"[{elapsed:.1f}s] Status: {last_status} → {current_status}")
            last_status = current_status

            if current_status == "processing":
                restart_detected = True
                print(f"✓ Worker picked up job after restart")

        # Detect progress updates
        if current_progress != last_progress:
            elapsed = time.time() - start_time
            print(f"[{elapsed:.1f}s] Progress: {last_progress}% → {current_progress}%")
            last_progress = current_progress

        # Check terminal state
        if current_status in ["completed", "failed", "cancelled"]:
            elapsed = time.time() - start_time
            print(f"\n✓ Job reached terminal state: {current_status.upper()}")
            print(f"  Time since restart: {elapsed:.1f}s")
            print(f"  Final progress: {current_progress}%")

            if status.get("error_message"):
                print(f"  Error: {status['error_message']}")

            return {
                "success": True,
                "final_status": current_status,
                "restart_detected": restart_detected,
                "time_to_complete": elapsed,
                "status_data": status,
            }

        time.sleep(1.0)

    # Timeout
    print(f"\n✗ Timeout after {timeout}s")
    return {
        "success": False,
        "error": "Timeout",
        "last_status": last_status,
        "restart_detected": restart_detected,
    }


def main():
    """Main verification workflow."""
    print("=" * 60)
    print("Worker Restart Persistence Verification (API-based)")
    print("=" * 60)

    # Check API availability
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("✗ API health check failed")
            print(f"  Status: {response.status_code}")
            print("\n  Make sure FastAPI server is running:")
            print("    uvicorn pybase.main:app --reload")
            return 1
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to API server")
        print("\n  Start FastAPI server:")
        print("    uvicorn pybase.main:app --reload")
        return 1

    print("✓ API server is running")

    # Login
    print("\n[Step 1] Authenticating...")
    token = login()

    # Create bulk job
    print("\n[Step 2] Creating bulk extraction job...")
    job_id = create_bulk_job(token)

    # Wait for processing
    print("\n[Step 3] Waiting for worker to pick up job...")
    print("  Make sure Celery worker is running:")
    print("    celery -A workers.celery_extraction_worker worker -l INFO")
    print()

    if not wait_for_processing(token, job_id, timeout=30):
        print("\n✗ VERIFICATION FAILED: Job did not reach PROCESSING state")
        print("  Make sure worker is running and can connect to Redis")
        return 1

    # Prompt for restart
    print("\n" + "=" * 60)
    print("ACTION REQUIRED: Restart the Celery worker now")
    print("=" * 60)
    print("\nSteps:")
    print("  1. In another terminal, find the worker process:")
    print("     ps aux | grep celery")
    print("     # or on Windows: tasklist | findstr celery")
    print("  2. Kill the worker:")
    print("     pkill -f celery")
    print("     # or on Windows: taskkill /F /IM celery.exe")
    print("  3. Start the worker again:")
    print("     celery -A workers.celery_extraction_worker worker -l INFO")
    print("\n  After restarting, press Enter to continue...")
    print("=" * 60)

    input()

    # Monitor after restart
    print("\n[Step 4] Monitoring job after worker restart...")
    result = monitor_after_restart(token, job_id, timeout=120)

    # Report results
    print("\n[Step 5] Verification Results")
    print("-" * 60)

    if result["success"]:
        print("✓ Job completed after worker restart")

        if result["restart_detected"]:
            print("✓ Worker successfully picked up job after restart")
        else:
            print("⚠ Job completed but restart detection unclear")

        print(f"✓ Final status: {result['final_status'].upper()}")
        print(f"✓ Time to complete after restart: {result['time_to_complete']:.1f}s")

        print("\n✅ VERIFICATION PASSED: Job persists across worker restart")
        return 0
    else:
        print(f"✗ VERIFICATION FAILED: {result.get('error', 'Unknown error')}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n✗ Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
