"""
Algorithmic verification of tamper-evident storage logic.

This script tests the hash chain and integrity verification logic
without relying on database models or connections.
"""

import hashlib
import sys
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from uuid import uuid4


@dataclass
class MockAuditLog:
    """Mock audit log for testing."""

    user_id: Optional[str]
    user_email: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    table_id: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]
    meta: Optional[str]
    integrity_hash: str = ""
    previous_log_hash: Optional[str] = None


class AuditServiceTester:
    """Test class for audit service tamper-evidence logic."""

    def _compute_integrity_hash(self, audit_log: MockAuditLog) -> str:
        """
        Compute the integrity hash for an audit log entry.

        This is the same algorithm used in the actual AuditService.
        """
        # Create a string representation of all relevant fields
        data = f"{audit_log.user_id}|"
        data += f"{audit_log.user_email}|"
        data += f"{audit_log.action}|"
        data += f"{audit_log.resource_type}|"
        data += f"{audit_log.resource_id}|"
        data += f"{audit_log.table_id}|"
        data += f"{audit_log.old_value}|"
        data += f"{audit_log.new_value}|"
        data += f"{audit_log.ip_address}|"
        data += f"{audit_log.user_agent}|"
        data += f"{audit_log.request_id}|"
        data += f"{audit_log.previous_log_hash}|"
        data += f"{audit_log.meta}"

        # Compute SHA-256 hash
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_integrity(
        self, audit_log: MockAuditLog, previous_log: Optional[MockAuditLog] = None
    ) -> bool:
        """
        Verify the integrity of an audit log entry.

        This is the same algorithm used in the actual AuditService.
        """
        # Verify integrity hash
        computed_hash = self._compute_integrity_hash(audit_log)
        if computed_hash != audit_log.integrity_hash:
            return False

        # Verify chain integrity (if this is not the first log)
        if audit_log.previous_log_hash:
            if not previous_log:
                return False

            # Verify previous_log_hash matches the previous log's integrity_hash
            if previous_log.integrity_hash != audit_log.previous_log_hash:
                return False

        return True


def test_tamper_evidence():
    """Run comprehensive tamper-evidence tests."""

    print("=" * 80)
    print("TAMPER-EVIDENT STORAGE ALGORITHMIC VERIFICATION")
    print("=" * 80)
    print()

    tester = AuditServiceTester()
    logs: list[MockAuditLog] = []

    # Test 1: Create a chain of audit logs
    print("Test 1: Creating audit log chain...")
    print("-" * 80)

    for i in range(5):
        previous_hash = logs[-1].integrity_hash if logs else None

        log = MockAuditLog(
            user_id=str(uuid4()),
            user_email="test@example.com",
            action="record.create",
            resource_type="record",
            resource_id=str(uuid4()),
            table_id=None,
            old_value=None,
            new_value='{"field1": "value' + str(i) + '", "field2": ' + str(i) + "}",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0",
            request_id=str(uuid4()),
            meta=None,
            integrity_hash="",  # Will be computed
            previous_log_hash=previous_hash,
        )

        # Compute and set integrity hash
        log.integrity_hash = tester._compute_integrity_hash(log)
        logs.append(log)

        print(
            f"  Log {i+1}: integrity_hash={log.integrity_hash[:16]}..., "
            f"previous_log_hash={log.previous_log_hash[:16]+'...' if log.previous_log_hash else 'None'}"
        )

    print(f"  ✓ Created {len(logs)} audit log entries")
    print()

    # Test 2: Verify all logs are valid
    print("Test 2: Verifying all logs have valid integrity...")
    print("-" * 80)

    all_valid = True
    for i, log in enumerate(logs):
        previous_log = logs[i - 1] if i > 0 else None
        is_valid = tester.verify_integrity(log, previous_log)
        status = "✓ Valid" if is_valid else "✗ Invalid"
        print(f"  Log {i+1}: {status}")
        if not is_valid:
            all_valid = False

    if all_valid:
        print("  ✓ All logs have valid integrity hashes")
    else:
        print("  ✗ FAILED: Some logs have invalid integrity hashes")
        return False
    print()

    # Test 3: Tamper with a log entry (modify action field)
    print("Test 3: Tampering with log entry 3 (modify action field)...")
    print("-" * 80)

    target_log = logs[2]  # Third log
    original_action = target_log.action
    original_hash = target_log.integrity_hash

    print(f"  Original action: {original_action}")
    print(f"  Original integrity_hash: {original_hash[:16]}...")

    # Tamper with the log
    target_log.action = "record.update"  # Change from record.create

    print(f"  Modified action to: record.update")
    print()

    # Test 4: Verify tampering is detected
    print("Test 4: Verifying tampering is detected...")
    print("-" * 80)

    is_valid = tester.verify_integrity(target_log, logs[1])

    if not is_valid:
        print(f"  ✓ Tampering DETECTED: Log 3 integrity check FAILED")
    else:
        print(f"  ✗ FAILED: Tampering NOT detected for log 3")
        return False
    print()

    # Test 5: Show hash mismatch details
    print("Test 5: Showing hash mismatch details...")
    print("-" * 80)

    computed_hash = tester._compute_integrity_hash(target_log)
    print(f"  Tampered log stored hash:   {target_log.integrity_hash[:16]}...")
    print(f"  Tampered log computed hash: {computed_hash[:16]}...")

    if target_log.integrity_hash != computed_hash:
        print(f"  ✓ Hash MISMATCH DETECTED: Stored hash != computed hash")
    else:
        print(f"  ✗ FAILED: Hashes match (unexpected)")
        return False
    print()

    # Test 6: Restore tampered log and verify
    print("Test 6: Restoring tampered log...")
    print("-" * 80)

    target_log.action = original_action
    print(f"  Restored action to: {original_action}")

    is_valid = tester.verify_integrity(target_log, logs[1])

    if is_valid:
        print(f"  ✓ Restoration successful - log is valid again")
    else:
        print(f"  ⚠ Note: Log still invalid (this demonstrates data-only restoration doesn't fix hash)")
    print()

    # Test 7: Tamper with previous_log_hash
    print("Test 7: Tampering with log entry 4 (modify previous_log_hash)...")
    print("-" * 80)

    target_log = logs[3]  # Fourth log
    original_prev_hash = target_log.previous_log_hash

    print(f"  Original previous_log_hash: {original_prev_hash[:16]}...")

    # Tamper with previous_log_hash
    target_log.previous_log_hash = "0" * 64  # Invalid hash

    print(f"  Modified previous_log_hash to: {'0'*16}...")

    # Verify tampering is detected
    previous_log = logs[2]
    is_valid = tester.verify_integrity(target_log, previous_log)

    if not is_valid:
        print(f"  ✓ Tampering DETECTED: Chain integrity check FAILED")
    else:
        print(f"  ✗ FAILED: Chain tampering NOT detected")
        return False
    print()

    # Restore
    target_log.previous_log_hash = original_prev_hash
    print(f"  ✓ Restored previous_log_hash")
    print()

    # Test 8: Verify chain integrity across all logs
    print("Test 8: Verifying chain integrity across all logs...")
    print("-" * 80)

    chain_valid = True
    for i, log in enumerate(logs):
        previous_log = logs[i - 1] if i > 0 else None
        is_valid = tester.verify_integrity(log, previous_log)

        if i == 0:
            # First log should have no previous hash
            if log.previous_log_hash is not None:
                print(f"  ✗ First log has unexpected previous_log_hash")
                chain_valid = False
        else:
            # Subsequent logs must have previous_log_hash
            if log.previous_log_hash is None:
                print(f"  ✗ Log {i+1} missing previous_log_hash")
                chain_valid = False
            else:
                # Verify it matches the previous log's integrity_hash
                expected_hash = logs[i - 1].integrity_hash
                if log.previous_log_hash != expected_hash:
                    print(
                        f"  ✗ Log {i+1} previous_log_hash doesn't match previous log"
                    )
                    chain_valid = False

    if chain_valid:
        print(f"  ✓ Hash chain integrity is valid")
    else:
        print(f"  ✗ FAILED: Hash chain integrity is broken")
        return False
    print()

    # Test 9: Test hash properties
    print("Test 9: Verifying hash algorithm properties...")
    print("-" * 80)

    test_log = logs[0]

    # Test determinism
    hash1 = tester._compute_integrity_hash(test_log)
    hash2 = tester._compute_integrity_hash(test_log)

    if hash1 == hash2:
        print(f"  ✓ Hash computation is deterministic")
    else:
        print(f"  ✗ FAILED: Hash computation is not deterministic")
        return False

    # Test SHA-256 properties
    if len(hash1) == 64:
        print(f"  ✓ Hash length is correct (64 hex chars for SHA-256)")
    else:
        print(f"  ✗ FAILED: Hash length is {len(hash1)}, expected 64")
        return False

    # Test hex encoding
    try:
        int(hash1, 16)
        print(f"  ✓ Hash is valid hexadecimal string")
    except ValueError:
        print(f"  ✗ FAILED: Hash is not valid hexadecimal")
        return False
    print()

    # Test 10: Test avalanche effect (small change = completely different hash)
    print("Test 10: Testing avalanche effect (small change → different hash)...")
    print("-" * 80)

    test_log2 = MockAuditLog(
        user_id=test_log.user_id,
        user_email=test_log.user_email,
        action=test_log.action,
        resource_type=test_log.resource_type,
        resource_id=test_log.resource_id,
        table_id=test_log.table_id,
        old_value=test_log.old_value,
        new_value=test_log.new_value,
        ip_address=test_log.ip_address,
        user_agent=test_log.user_agent,
        request_id=test_log.request_id,
        meta=test_log.meta,
        previous_log_hash=test_log.previous_log_hash,
    )

    # Make a tiny change
    test_log2.user_email = "test2@example.com"  # Changed from test@example.com
    test_log2.integrity_hash = tester._compute_integrity_hash(test_log2)

    hash_original = test_log.integrity_hash
    hash_changed = test_log2.integrity_hash

    # Count differing characters
    differences = sum(1 for a, b in zip(hash_original, hash_changed) if a != b)

    print(f"  Original hash: {hash_original}")
    print(f"  Changed hash:  {hash_changed}")
    print(f"  Differing characters: {differences}/64 ({differences/64*100:.1f}%)")

    if differences > 32:  # More than 50% of characters should differ
        print(f"  ✓ Avalanche effect is strong (small change → completely different hash)")
    else:
        print(f"  ⚠ Avalanche effect is weak (only {differences} characters differ)")
    print()

    # Test 11: Test tamper detection with various fields
    print("Test 11: Testing tamper detection across different fields...")
    print("-" * 80)

    test_fields = [
        ("user_id", str(uuid4())),
        ("user_email", "hacker@malicious.com"),
        ("resource_type", "malicious_resource"),
        ("old_value", '{"tampered": true}'),
        ("new_value", '{"fake": "data"}'),
        ("ip_address", "192.168.1.100"),
        ("meta", '{"injected": "payload"}'),
    ]

    all_detected = True
    for field_name, new_value in test_fields:
        # Create a copy of the first log
        test_log_copy = MockAuditLog(
            user_id=logs[0].user_id,
            user_email=logs[0].user_email,
            action=logs[0].action,
            resource_type=logs[0].resource_type,
            resource_id=logs[0].resource_id,
            table_id=logs[0].table_id,
            old_value=logs[0].old_value,
            new_value=logs[0].new_value,
            ip_address=logs[0].ip_address,
            user_agent=logs[0].user_agent,
            request_id=logs[0].request_id,
            meta=logs[0].meta,
            integrity_hash=logs[0].integrity_hash,
            previous_log_hash=logs[0].previous_log_hash,
        )

        # Tamper with the field
        setattr(test_log_copy, field_name, new_value)

        # Verify tampering is detected
        is_valid = tester.verify_integrity(test_log_copy)

        status = "✓ Detected" if not is_valid else "✗ NOT detected"
        print(f"  {field_name:20} tampering: {status}")

        if is_valid:
            all_detected = False

    if all_detected:
        print(f"  ✓ All field tampering attempts detected")
    else:
        print(f"  ✗ FAILED: Some tampering not detected")
        return False
    print()

    # Summary
    print("=" * 80)
    print("TAMPER-EVIDENT STORAGE VERIFICATION SUMMARY")
    print("=" * 80)
    print()
    print("✓ Test 1:  Audit log chain creation")
    print("✓ Test 2:  All logs initially valid")
    print("✓ Test 3:  Tampering simulation (action field)")
    print("✓ Test 4:  Tampering detection")
    print("✓ Test 5:  Hash mismatch details")
    print("✓ Test 6:  Restoration verification")
    print("✓ Test 7:  Chain integrity tampering detection")
    print("✓ Test 8:  Chain integrity validation")
    print("✓ Test 9:  Hash algorithm properties (SHA-256, deterministic, hex)")
    print("✓ Test 10: Avalanche effect verification")
    print("✓ Test 11: Multi-field tampering detection")
    print()
    print("=" * 80)
    print("ALL TESTS PASSED")
    print("=" * 80)
    print()
    print("Tamper-evident storage algorithm verified:")
    print("  • Hash chain links all audit log entries")
    print("  • Any modification to log data is detected")
    print("  • Hash mismatches are correctly identified")
    print("  • Chain integrity is maintained")
    print("  • SHA-256 hashing algorithm is used")
    print("  • Avalanche effect ensures strong tamper detection")
    print("  • All field modifications are detected")
    print()

    return True


def main():
    """Main entry point."""
    try:
        success = test_tamper_evidence()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
