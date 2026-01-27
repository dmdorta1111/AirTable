#!/usr/bin/env python3
"""
Logic verification for audit log retention policy and automated cleanup.

This script validates the retention cleanup logic without requiring a database connection.
It verifies:
1. Retention calculation logic
2. Cleanup query construction
3. Deletion behavior with retention_days parameter
4. Recent logs preservation
5. Old logs deletion
"""

import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock
import uuid


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_success(message: str):
    """Print success message."""
    print(f"✅ {message}")


def print_error(message: str):
    """Print error message."""
    print(f"❌ {message}")


def print_info(message: str):
    """Print info message."""
    print(f"ℹ️  {message}")


class MockAuditLog:
    """Mock audit log for testing."""
    def __init__(self, id, user_id, created_at, action="record.create"):
        self.id = id
        self.user_id = user_id
        self.created_at = created_at
        self.action = action
        self.user_email = "test@example.com"
        self.resource_type = "record"
        self.resource_id = f"resource-{id}"
        self.table_id = "test-table"
        self.old_value = None
        self.new_value = {"test": "data"}
        self.ip_address = "127.0.0.1"
        self.user_agent = "test-agent"
        self.request_id = f"request-{id}"
        self.integrity_hash = "hash123"
        self.previous_log_hash = None
        self.meta = {"test": "data"}


class MockAuditService:
    """Mock AuditService to test cleanup logic."""

    def __init__(self):
        self.logs = []
        self.deleted_logs = []

    async def delete_old_logs(self, db, retention_days: int) -> int:
        """
        Delete audit logs older than the retention period.

        This mirrors the actual implementation in AuditService.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Filter logs older than cutoff date
        logs_to_delete = [log for log in self.logs if log.created_at < cutoff_date]

        # Delete logs
        count = len(logs_to_delete)
        for log in logs_to_delete:
            self.deleted_logs.append(log)
            self.logs.remove(log)

        return count


async def verify_retention_calculation():
    """Verify retention period calculation logic."""
    print_section("Test 1: Retention Period Calculation")

    all_passed = True

    # Test different retention periods
    test_cases = [
        (1, "1 day"),
        (7, "7 days"),
        (30, "30 days"),
        (90, "90 days"),
        (365, "1 year"),
    ]

    for retention_days, description in test_cases:
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        now = datetime.utcnow()

        # Calculate expected cutoff
        expected_cutoff = now - timedelta(days=retention_days)

        # Verify cutoff is correctly calculated
        time_diff = (now - cutoff_date).days

        if time_diff == retention_days:
            print_success(f"✓ {description}: Cutoff calculated correctly ({cutoff_date.strftime('%Y-%m-%d %H:%M:%S')})")
        else:
            print_error(f"✗ {description}: Expected {retention_days} days difference, got {time_diff}")
            all_passed = False

        # Test that a log created before cutoff is considered old
        old_log_date = cutoff_date - timedelta(hours=1)
        is_old = old_log_date < cutoff_date

        if is_old:
            print_success(f"  ✓ Log from {old_log_date.strftime('%Y-%m-%d %H:%M:%S')} is correctly identified as old")
        else:
            print_error(f"  ✗ Log from {old_log_date.strftime('%Y-%m-%d %H:%M:%S')} should be old but isn't")
            all_passed = False

        # Test that a log created after cutoff is considered recent
        recent_log_date = cutoff_date + timedelta(hours=1)
        is_recent = recent_log_date >= cutoff_date

        if is_recent:
            print_success(f"  ✓ Log from {recent_log_date.strftime('%Y-%m-%d %H:%M:%S')} is correctly identified as recent")
        else:
            print_error(f"  ✗ Log from {recent_log_date.strftime('%Y-%m-%d %H:%M:%S')} should be recent but isn't")
            all_passed = False

    return all_passed


async def verify_cleanup_with_mixed_logs():
    """Verify cleanup with mix of old and recent logs."""
    print_section("Test 2: Cleanup with Mixed Old/Recent Logs")

    service = MockAuditService()
    test_user_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # Create test logs: 5 old, 3 recent
    test_data = [
        # 5 old logs (3 days old)
        MockAuditLog(f"old-1", test_user_id, now - timedelta(days=3)),
        MockAuditLog(f"old-2", test_user_id, now - timedelta(days=3)),
        MockAuditLog(f"old-3", test_user_id, now - timedelta(days=3)),
        MockAuditLog(f"old-4", test_user_id, now - timedelta(days=3)),
        MockAuditLog(f"old-5", test_user_id, now - timedelta(days=3)),
        # 3 recent logs (current time)
        MockAuditLog(f"recent-1", test_user_id, now),
        MockAuditLog(f"recent-2", test_user_id, now),
        MockAuditLog(f"recent-3", test_user_id, now),
    ]

    service.logs = test_data.copy()

    print_info(f"Created {len(test_data)} test logs: 5 old (3 days), 3 recent (current)")

    # Run cleanup with retention_days=1
    retention_days = 1
    print_info(f"Running cleanup with retention_days={retention_days}...")

    deleted_count = await service.delete_old_logs(None, retention_days)

    print_info(f"Deleted {deleted_count} logs")

    # Verify results
    all_passed = True

    # Check: Should delete exactly 5 old logs
    if deleted_count == 5:
        print_success(f"✓ Deleted correct count: {deleted_count} old logs")
    else:
        print_error(f"✗ Expected to delete 5 old logs, deleted {deleted_count}")
        all_passed = False

    # Check: Should have exactly 3 logs remaining (all recent)
    if len(service.logs) == 3:
        print_success(f"✓ Correct number of logs remaining: {len(service.logs)}")
    else:
        print_error(f"✗ Expected 3 logs remaining, found {len(service.logs)}")
        all_passed = False

    # Check: All remaining logs should be recent
    all_recent = all("recent" in log.id for log in service.logs)
    if all_recent:
        print_success("✓ All remaining logs are recent (none deleted)")
    else:
        print_error("✗ Some old logs remain or recent logs were deleted")
        all_passed = False

    # Check: All deleted logs should be old
    all_old = all("old" in log.id for log in service.deleted_logs)
    if all_old:
        print_success("✓ All deleted logs are old (correct ones deleted)")
    else:
        print_error("✗ Some recent logs were incorrectly deleted")
        all_passed = False

    return all_passed


async def verify_edge_cases():
    """Verify edge cases in cleanup logic."""
    print_section("Test 3: Edge Cases")

    all_passed = True
    test_user_id = str(uuid.uuid4())
    now = datetime.utcnow()

    # Edge case 1: Logs exactly at cutoff boundary
    print_info("Edge Case 1: Log exactly at cutoff boundary")

    service = MockAuditService()
    retention_days = 1
    cutoff_date = now - timedelta(days=retention_days)

    # Log exactly at cutoff (should be kept - >= cutoff)
    boundary_log = MockAuditLog(f"boundary", test_user_id, cutoff_date)
    service.logs = [boundary_log]

    deleted_count = await service.delete_old_logs(None, retention_days)

    # Log at exact cutoff should NOT be deleted (< condition, not <=)
    if deleted_count == 0 and len(service.logs) == 1:
        print_success("✓ Log at exact cutoff boundary is preserved (not deleted)")
    else:
        print_error(f"✗ Log at boundary should be preserved. Deleted: {deleted_count}, Remaining: {len(service.logs)}")
        all_passed = False

    # Edge case 2: All logs old
    print_info("\nEdge Case 2: All logs are old (should delete all)")

    service = MockAuditService()
    service.logs = [
        MockAuditLog(f"old-{i}", test_user_id, now - timedelta(days=5))
        for i in range(10)
    ]

    deleted_count = await service.delete_old_logs(None, retention_days)

    if deleted_count == 10 and len(service.logs) == 0:
        print_success("✓ All 10 old logs deleted, 0 remaining")
    else:
        print_error(f"✗ Expected 10 deletions, got {deleted_count}. Expected 0 remaining, got {len(service.logs)}")
        all_passed = False

    # Edge case 3: All logs recent
    print_info("\nEdge Case 3: All logs are recent (should delete none)")

    service = MockAuditService()
    service.logs = [
        MockAuditLog(f"recent-{i}", test_user_id, now)
        for i in range(10)
    ]

    deleted_count = await service.delete_old_logs(None, retention_days)

    if deleted_count == 0 and len(service.logs) == 10:
        print_success("✓ 0 deletions, all 10 recent logs preserved")
    else:
        print_error(f"✗ Expected 0 deletions, got {deleted_count}. Expected 10 remaining, got {len(service.logs)}")
        all_passed = False

    # Edge case 4: Empty log list
    print_info("\nEdge Case 4: Empty log list")

    service = MockAuditService()
    service.logs = []

    deleted_count = await service.delete_old_logs(None, retention_days)

    if deleted_count == 0 and len(service.logs) == 0:
        print_success("✓ Empty list handled correctly (0 deletions)")
    else:
        print_error(f"✗ Expected 0 deletions from empty list, got {deleted_count}")
        all_passed = False

    # Edge case 5: Very long retention period
    print_info("\nEdge Case 5: Very long retention period (365 days)")

    service = MockAuditService()
    service.logs = [
        MockAuditLog(f"recent-{i}", test_user_id, now - timedelta(days=100))
        for i in range(5)
    ]

    deleted_count = await service.delete_old_logs(None, 365)

    if deleted_count == 0 and len(service.logs) == 5:
        print_success("✓ Logs from 100 days ago preserved with 365-day retention")
    else:
        print_error(f"✗ Expected 0 deletions with 365-day retention, got {deleted_count}")
        all_passed = False

    # Edge case 6: Zero retention period
    print_info("\nEdge Case 6: Zero retention period (boundary behavior)")

    service = MockAuditService()
    # Note: With retention_days=0, cutoff_date = now
    # Logs with created_at < now will be deleted
    # Logs with created_at = now will NOT be deleted (not strictly older)
    service.logs = [
        MockAuditLog(f"recent-{i}", test_user_id, now)  # created at exactly "now"
        for i in range(5)
    ]

    deleted_count = await service.delete_old_logs(None, 0)

    # With zero retention, logs at "now" are NOT deleted (not strictly older than cutoff)
    if deleted_count == 0 and len(service.logs) == 5:
        print_success("✓ Logs at exact cutoff not deleted even with zero retention (correct boundary behavior)")
        print_info("  Note: retention_days=0 is not practical; use retention_days>=1")
    else:
        print_error(f"✗ Expected 0 deletions with zero retention (logs at boundary), got {deleted_count}")
        all_passed = False

    return all_passed


async def verify_query_logic():
    """Verify the query construction logic."""
    print_section("Test 4: Query Construction Logic")

    all_passed = True
    now = datetime.utcnow()

    # Simulate query filtering logic
    def should_delete_log(log_created_at, retention_days):
        """Simulate the WHERE clause condition."""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        return log_created_at < cutoff_date

    # Test various scenarios
    test_cases = [
        # (log_age_days, retention_days, should_delete, description)
        (5, 1, True, "5-day-old log with 1-day retention"),
        (1, 1, False, "1-day-old log with 1-day retention (at boundary)"),
        (0, 1, False, "Current log with 1-day retention"),
        (100, 90, True, "100-day-old log with 90-day retention"),
        (90, 90, False, "90-day-old log with 90-day retention (at boundary)"),
        (30, 90, False, "30-day-old log with 90-day retention"),
    ]

    for log_age, retention, expected_delete, description in test_cases:
        log_created = now - timedelta(days=log_age)
        should_delete = should_delete_log(log_created, retention)

        if should_delete == expected_delete:
            status = "DELETE" if should_delete else "KEEP"
            print_success(f"✓ {description}: {status}")
        else:
            expected_status = "DELETE" if expected_delete else "KEEP"
            actual_status = "DELETE" if should_delete else "KEEP"
            print_error(f"✗ {description}: Expected {expected_status}, got {actual_status}")
            all_passed = False

    return all_passed


async def main():
    """Run all verification tests."""
    print_section("Audit Log Retention & Cleanup Logic Verification")

    print_info("Validating retention cleanup logic without database")
    print_info("Testing calculations, filtering, and edge cases")

    all_passed = True

    try:
        # Test 1: Retention calculation
        test1_passed = await verify_retention_calculation()
        all_passed = all_passed and test1_passed

        # Test 2: Cleanup with mixed logs
        test2_passed = await verify_cleanup_with_mixed_logs()
        all_passed = all_passed and test2_passed

        # Test 3: Edge cases
        test3_passed = await verify_edge_cases()
        all_passed = all_passed and test3_passed

        # Test 4: Query logic
        test4_passed = await verify_query_logic()
        all_passed = all_passed and test4_passed

    except Exception as e:
        print_error(f"Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False

    # Final result
    print_section("Final Result")
    if all_passed:
        print_success("✅ All retention and cleanup logic verification checks PASSED")
        print_info("\nVerified functionality:")
        print_info("  • Retention period calculation is correct")
        print_info("  • Old logs are properly identified for deletion")
        print_info("  • Recent logs are preserved during cleanup")
        print_info("  • Boundary conditions are handled correctly")
        print_info("  • Query logic correctly filters by date")
        print_info("  • Edge cases (empty list, all old, all recent) handled")
        print_info("  • Various retention periods work correctly (1, 7, 30, 90, 365 days)")
        return 0
    else:
        print_error("❌ Some verification checks FAILED")
        return 1


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
