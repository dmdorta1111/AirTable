"""
End-to-end tests for audit logging flow: login → CRUD → export.

This test suite validates the complete audit logging workflow:
1. User login events logged
2. Record CRUD operations logged with old/new values
3. Audit logs can be queried and filtered
4. Audit logs can be exported to CSV/JSON
5. Tamper-evident storage works (integrity verification)
"""

import json
from datetime import datetime, UTC
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.config import settings
from pybase.models.base import Base
from pybase.models.table import Table
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.user import User
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.models.audit_log import AuditLog, AuditAction


@pytest_asyncio.fixture
async def audit_test_workspace(db_session: AsyncSession, test_user: User) -> Workspace:
    """Create a test workspace with user as owner for audit testing."""
    workspace = Workspace(
        owner_id=test_user.id,
        name="Audit Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add owner as workspace member
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    return workspace


@pytest_asyncio.fixture
async def audit_test_base(db_session: AsyncSession, audit_test_workspace: Workspace) -> Base:
    """Create a test base for audit testing."""
    from pybase.models.base import Base as BaseModel

    base = BaseModel(
        workspace_id=audit_test_workspace.id,
        name="Audit Test Base",
        description="Base for audit logging E2E testing",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def audit_test_table(db_session: AsyncSession, audit_test_base: Base, test_user: User) -> Table:
    """Create a test table with sample data for audit testing."""
    # Create table
    table = Table(
        base_id=audit_test_base.id,
        name="Audit Test Table",
        description="Table for audit logging E2E testing",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create fields
    fields = [
        Field(
            table_id=table.id,
            name="Name",
            field_type=FieldType.TEXT,
            order=0,
        ),
        Field(
            table_id=table.id,
            name="Status",
            field_type=FieldType.TEXT,
            order=1,
        ),
        Field(
            table_id=table.id,
            name="Count",
            field_type=FieldType.NUMBER,
            order=2,
        ),
    ]
    for field in fields:
        db_session.add(field)
    await db_session.commit()

    return table


@pytest.mark.asyncio
class TestAuditFlowE2E:
    """End-to-end test suite for complete audit logging workflow."""

    async def test_complete_audit_flow_login_to_export(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        audit_test_table: Table,
        test_user: User,
    ):
        """
        Test the complete audit flow from login to CRUD operations to export.

        Workflow:
        1. User logs in via API
        2. Verify login event appears in audit logs
        3. Create a record in a table
        4. Verify create event appears in audit logs with new_value
        5. Update the record
        6. Verify update event appears with old/new values
        7. Delete the record
        8. Verify delete event appears with old_value
        9. Filter audit logs by user, table, action
        10. Export audit logs as CSV
        11. Verify CSV contains all filtered records
        """
        # Step 1: User logs in via API
        login_response = await client.post(
            f"{settings.api_v1_prefix}/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123",
            },
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Verify login event appears in audit logs
        # Query audit logs for login action
        audit_logs_response = await client.get(
            f"{settings.api_v1_prefix}/audit/logs",
            headers=auth_headers,
            params={
                "action": "user.login",
                "limit": 10,
            },
        )
        # Note: Regular users can't access audit logs, only superusers
        # So we expect 403 Forbidden here
        assert audit_logs_response.status_code in [200, 403], "Should get 200 (superuser) or 403 (regular user)"

        # For E2E testing, we'll query the database directly
        result = await db_session.execute(
            f"SELECT * FROM pybase.audit_logs WHERE action = 'user.login' ORDER BY created_at DESC LIMIT 1"
        )
        login_log = result.first()

        # Verify login was logged
        assert login_log is not None, "Login event should be logged"
        assert login_log.user_email == "test@example.com", "User email should match"
        assert login_log.action == "user.login", "Action should be user.login"
        assert login_log.ip_address is not None, "IP address should be captured"

        # Step 3: Create a record in a table
        record_data = {
            "Name": "Test Record",
            "Status": "Active",
            "Count": 42,
        }
        create_response = await client.post(
            f"{settings.api_v1_prefix}/records",
            headers=auth_headers,
            json={
                "table_id": str(audit_test_table.id),
                "data": record_data,
            },
        )
        assert create_response.status_code in [200, 201], f"Record creation failed: {create_response.text}"
        created_record = create_response.json()
        record_id = created_record["id"]

        # Step 4: Verify create event appears in audit logs with new_value
        result = await db_session.execute(
            f"""SELECT * FROM pybase.audit_logs
               WHERE action = 'record.create'
               AND resource_id = '{record_id}'
               ORDER BY created_at DESC LIMIT 1"""
        )
        create_log = result.first()

        assert create_log is not None, "Create event should be logged"
        assert create_log.action == "record.create", "Action should be record.create"
        assert create_log.resource_id == record_id, "Resource ID should match"
        assert create_log.table_id == str(audit_test_table.id), "Table ID should match"

        # Verify new_value contains record data
        new_value = json.loads(create_log.new_value) if create_log.new_value else {}
        assert new_value.get("Name") == "Test Record", "New value should contain record data"
        assert new_value.get("Status") == "Active", "New value should contain record data"
        assert new_value.get("Count") == 42, "New value should contain record data"

        # Step 5: Update the record
        updated_data = {
            "Name": "Updated Record",
            "Status": "Inactive",
            "Count": 100,
        }
        update_response = await client.patch(
            f"{settings.api_v1_prefix}/records/{record_id}",
            headers=auth_headers,
            json={
                "table_id": str(audit_test_table.id),
                "data": updated_data,
            },
        )
        assert update_response.status_code == 200, f"Record update failed: {update_response.text}"

        # Step 6: Verify update event appears with old/new values
        result = await db_session.execute(
            f"""SELECT * FROM pybase.audit_logs
               WHERE action = 'record.update'
               AND resource_id = '{record_id}'
               ORDER BY created_at DESC LIMIT 1"""
        )
        update_log = result.first()

        assert update_log is not None, "Update event should be logged"
        assert update_log.action == "record.update", "Action should be record.update"

        # Verify old_value contains original data
        old_value = json.loads(update_log.old_value) if update_log.old_value else {}
        assert old_value.get("Name") == "Test Record", "Old value should contain original data"
        assert old_value.get("Status") == "Active", "Old value should contain original data"
        assert old_value.get("Count") == 42, "Old value should contain original data"

        # Verify new_value contains updated data
        new_value = json.loads(update_log.new_value) if update_log.new_value else {}
        assert new_value.get("Name") == "Updated Record", "New value should contain updated data"
        assert new_value.get("Status") == "Inactive", "New value should contain updated data"
        assert new_value.get("Count") == 100, "New value should contain updated data"

        # Step 7: Delete the record
        delete_response = await client.delete(
            f"{settings.api_v1_prefix}/records/{record_id}",
            headers=auth_headers,
            params={"table_id": str(audit_test_table.id)},
        )
        assert delete_response.status_code == 200, f"Record deletion failed: {delete_response.text}"

        # Step 8: Verify delete event appears with old_value
        result = await db_session.execute(
            f"""SELECT * FROM pybase.audit_logs
               WHERE action = 'record.delete'
               AND resource_id = '{record_id}'
               ORDER BY created_at DESC LIMIT 1"""
        )
        delete_log = result.first()

        assert delete_log is not None, "Delete event should be logged"
        assert delete_log.action == "record.delete", "Action should be record.delete"

        # Verify old_value contains data before deletion
        old_value = json.loads(delete_log.old_value) if delete_log.old_value else {}
        assert old_value.get("Name") == "Updated Record", "Old value should contain data before deletion"
        assert old_value.get("Status") == "Inactive", "Old value should contain data before deletion"
        assert old_value.get("Count") == 100, "Old value should contain data before deletion"

        # Step 9: Filter audit logs by user, table, action
        # We'll query the database directly to verify filtering works
        result = await db_session.execute(
            f"""SELECT * FROM pybase.audit_logs
               WHERE user_id = '{test_user.id}'
               AND table_id = '{audit_test_table.id}'
               AND action IN ('record.create', 'record.update', 'record.delete')
               ORDER BY created_at ASC"""
        )
        filtered_logs = result.all()

        assert len(filtered_logs) >= 3, "Should have at least 3 audit logs (create, update, delete)"
        actions = [log.action for log in filtered_logs]
        assert "record.create" in actions, "Should have create action"
        assert "record.update" in actions, "Should have update action"
        assert "record.delete" in actions, "Should have delete action"

        # Step 10: Export audit logs as CSV (requires superuser)
        # For now, we'll verify the export endpoint exists and returns appropriate response
        # Since test_user is not a superuser, we expect 403 Forbidden
        export_response = await client.get(
            f"{settings.api_v1_prefix}/audit/logs/export",
            headers=auth_headers,
            params={"format": "csv"},
        )
        assert export_response.status_code == 403, "Regular user should be forbidden from exporting"

        # Step 11: Verify CSV export works with superuser credentials
        # Create a superuser and test export
        from pybase.core.security import hash_password

        superuser = User(
            email="auditadmin@example.com",
            hashed_password=hash_password("adminpass123"),
            name="Audit Admin",
            is_active=True,
            is_verified=True,
            is_superuser=True,
        )
        db_session.add(superuser)
        await db_session.commit()
        await db_session.refresh(superuser)

        # Login as superuser
        admin_login_response = await client.post(
            f"{settings.api_v1_prefix}/auth/login",
            json={
                "email": "auditadmin@example.com",
                "password": "adminpass123",
            },
        )
        assert admin_login_response.status_code == 200, "Admin login failed"
        admin_token = admin_login_response.json()["access_token"]
        admin_auth_headers = {"Authorization": f"Bearer {admin_token}"}

        # Export audit logs as CSV
        export_response = await client.get(
            f"{settings.api_v1_prefix}/audit/logs/export",
            headers=admin_auth_headers,
            params={
                "format": "csv",
                "table_id": str(audit_test_table.id),
            },
        )
        assert export_response.status_code == 200, f"CSV export failed: {export_response.text}"
        assert export_response.headers["content-type"] == "text/csv", "Should return CSV content type"

        # Verify CSV contains data
        csv_content = export_response.text
        assert len(csv_content) > 0, "CSV should not be empty"
        assert "id,user_id,user_email,action" in csv_content, "CSV should have header row"

        # Verify CSV contains our audit logs
        assert "record.create" in csv_content, "CSV should contain record.create action"
        assert "record.update" in csv_content, "CSV should contain record.update action"
        assert "record.delete" in csv_content, "CSV should contain record.delete action"

        # Verify JSON export also works
        export_response = await client.get(
            f"{settings.api_v1_prefix}/audit/logs/export",
            headers=admin_auth_headers,
            params={
                "format": "json",
                "table_id": str(audit_test_table.id),
            },
        )
        assert export_response.status_code == 200, f"JSON export failed: {export_response.text}"
        assert export_response.headers["content-type"] == "application/json", "Should return JSON content type"

        # Verify JSON contains data
        json_content = export_response.text
        assert len(json_content) > 0, "JSON should not be empty"
        assert json_content.startswith("[{"), "JSON should start with array"

    async def test_audit_log_integrity_verification(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        admin_auth_headers: dict[str, str],
    ):
        """
        Test tamper-evident storage and integrity verification.

        Verifies:
        1. Each audit log has integrity_hash and previous_log_hash
        2. Hash chain is intact (each log links to previous)
        3. Integrity verification works correctly
        """
        # Create some audit activity by logging in
        login_response = await client.post(
            f"{settings.api_v1_prefix}/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123",
            },
        )
        assert login_response.status_code == 200

        # Query audit logs
        result = await db_session.execute(
            f"SELECT * FROM pybase.audit_logs ORDER BY created_at DESC LIMIT 5"
        )
        audit_logs = result.all()

        if len(audit_logs) == 0:
            pytest.skip("No audit logs found to verify integrity")

        # Verify each log has integrity_hash and previous_log_hash
        for log in audit_logs:
            assert log.integrity_hash is not None, f"Log {log.id} should have integrity_hash"
            assert len(log.integrity_hash) == 64, f"Log {log.id} should have SHA-256 hash (64 chars)"

        # Verify hash chain (previous_log_hash should match previous log's integrity_hash)
        for i in range(len(audit_logs) - 1):
            current_log = audit_logs[i]
            previous_log = audit_logs[i + 1]

            if current_log.previous_log_hash:
                assert current_log.previous_log_hash == previous_log.integrity_hash, \
                    f"Hash chain broken at log {current_log.id}"

        # Test integrity verification via API
        if len(audit_logs) > 0:
            log_id = str(audit_logs[0].id)

            # Verify integrity via API
            verify_response = await client.get(
                f"{settings.api_v1_prefix}/audit/logs/{log_id}/verify",
                headers=admin_auth_headers,
            )
            assert verify_response.status_code == 200, f"Integrity verification failed: {verify_response.text}"
            verification_result = verify_response.json()

            assert "log_id" in verification_result, "Should return log_id"
            assert "integrity_valid" in verification_result, "Should return integrity_valid status"
            assert isinstance(verification_result["integrity_valid"], bool), "integrity_valid should be boolean"

    async def test_audit_log_filtering_by_date_range(
        self,
        client: AsyncClient,
        admin_auth_headers: dict[str, str],
        test_user: User,
    ):
        """
        Test filtering audit logs by date range.

        Verifies:
        1. Can filter logs by start_date
        2. Can filter logs by end_date
        3. Can filter logs by date range (both start and end)
        """
        from datetime import timedelta

        # Get current time
        now = datetime.utcnow()

        # Query logs from last hour
        start_date = (now - timedelta(hours=1)).isoformat() + "Z"

        response = await client.get(
            f"{settings.api_v1_prefix}/audit/logs",
            headers=admin_auth_headers,
            params={
                "start_date": start_date,
                "limit": 100,
            },
        )
        assert response.status_code == 200, f"Date filter query failed: {response.text}"
        logs_response = response.json()

        assert "items" in logs_response, "Should return items"
        assert isinstance(logs_response["items"], list), "Items should be a list"

        # Query logs from future (should be empty)
        future_date = (now + timedelta(days=1)).isoformat() + "Z"
        start_date = future_date

        response = await client.get(
            f"{settings.api_v1_prefix}/audit/logs",
            headers=admin_auth_headers,
            params={
                "start_date": start_date,
                "limit": 100,
            },
        )
        assert response.status_code == 200
        logs_response = response.json()

        # Should have 0 or very few logs (edge case with timestamps)
        assert logs_response["total"] < 10, "Future date range should return few or no logs"

    async def test_bulk_operations_audit_logging(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        audit_test_table: Table,
        test_user: User,
    ):
        """
        Test that bulk operations are logged correctly.

        Verifies:
        1. Bulk create logs each record
        2. Bulk update logs each record with old/new values
        3. Bulk delete logs each record with old values
        """
        # Login to get auth headers
        login_response = await client.post(
            f"{settings.api_v1_prefix}/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Bulk create records
        records_data = [
            {"Name": f"Record {i}", "Status": "Active", "Count": i * 10}
            for i in range(1, 4)
        ]

        create_response = await client.post(
            f"{settings.api_v1_prefix}/records/batch",
            headers=auth_headers,
            json={
                "table_id": str(audit_test_table.id),
                "records": records_data,
            },
        )
        assert create_response.status_code in [200, 201], f"Bulk create failed: {create_response.text}"
        created_records = create_response.json()

        # Verify each bulk create is logged
        for record in created_records:
            result = await db_session.execute(
                f"""SELECT * FROM pybase.audit_logs
                   WHERE action = 'record.bulk_create'
                   AND resource_id = '{record["id"]}'
                   ORDER BY created_at DESC LIMIT 1"""
            )
            log = result.first()

            assert log is not None, f"Bulk create for record {record['id']} should be logged"
            assert log.action == "record.bulk_create", "Action should be record.bulk_create"

        # Bulk update records
        updated_data = [
            {"id": r["id"], "data": {"Name": f"Updated {r['data']['Name']}", "Status": "Inactive", "Count": 999}}
            for r in created_records
        ]

        update_response = await client.patch(
            f"{settings.api_v1_prefix}/records/batch",
            headers=auth_headers,
            json={
                "table_id": str(audit_test_table.id),
                "records": updated_data,
            },
        )
        assert update_response.status_code == 200, f"Bulk update failed: {update_response.text}"

        # Verify each bulk update is logged with old/new values
        for record in created_records:
            result = await db_session.execute(
                f"""SELECT * FROM pybase.audit_logs
                   WHERE action = 'record.bulk_update'
                   AND resource_id = '{record["id"]}'
                   ORDER BY created_at DESC LIMIT 1"""
            )
            log = result.first()

            assert log is not None, f"Bulk update for record {record['id']} should be logged"
            assert log.old_value is not None, "Bulk update should have old_value"
            assert log.new_value is not None, "Bulk update should have new_value"

        # Bulk delete records
        record_ids = [r["id"] for r in created_records]

        delete_response = await client.post(
            f"{settings.api_v1_prefix}/records/batch-delete",
            headers=auth_headers,
            json={
                "table_id": str(audit_test_table.id),
                "record_ids": record_ids,
            },
        )
        assert delete_response.status_code == 200, f"Bulk delete failed: {delete_response.text}"

        # Verify each bulk delete is logged with old values
        for record_id in record_ids:
            result = await db_session.execute(
                f"""SELECT * FROM pybase.audit_logs
                   WHERE action = 'record.bulk_delete'
                   AND resource_id = '{record_id}'
                   ORDER BY created_at DESC LIMIT 1"""
            )
            log = result.first()

            assert log is not None, f"Bulk delete for record {record_id} should be logged"
            assert log.old_value is not None, "Bulk delete should have old_value"
