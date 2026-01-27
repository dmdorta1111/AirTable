"""
End-to-end tests for trash bin flow: Delete → Verify in trash → Restore/Permanent Delete → Verify result.

This test suite validates the complete trash bin workflow:
1. Create a test record via API
2. Delete the record via API
3. Call GET /api/v1/trash and verify record appears with deleted_at and deleted_by
4. Either restore the record or permanently delete it
5. Verify the final state (restored accessible, permanently deleted removed)
6. Verify deleted_by_id is set correctly throughout
7. Test auto-purge worker functionality for retention-based cleanup
"""

import json
from datetime import datetime, UTC, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from pybase.core.config import settings
from pybase.models.base import Base
from pybase.models.table import Table
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.user import User
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


@pytest_asyncio.fixture
async def test_workspace(db_session: AsyncSession, test_user: User) -> Workspace:
    """Create a test workspace with user as owner."""
    workspace = Workspace(
        owner_id=test_user.id,
        name="Trash Test Workspace",
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
async def test_base(db_session: AsyncSession, test_workspace: Workspace) -> Base:
    """Create a test base for trash testing."""
    base = Base(
        workspace_id=test_workspace.id,
        name="Trash Test Base",
        description="Base for trash E2E testing",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def test_table(db_session: AsyncSession, test_base: Base, test_user: User) -> Table:
    """Create a test table with fields for trash testing."""
    # Create table
    table = Table(
        base_id=test_base.id,
        name="Test Records",
        description="Table for trash bin testing",
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
            name="Description",
            field_type=FieldType.TEXT,
            order=1,
        ),
        Field(
            table_id=table.id,
            name="Quantity",
            field_type=FieldType.NUMBER,
            order=2,
        ),
    ]
    for field in fields:
        db_session.add(field)
    await db_session.commit()

    # Refresh to get field IDs
    for field in fields:
        await db_session.refresh(field)

    return table


@pytest.mark.asyncio
class TestTrashFlow:
    """End-to-end test suite for complete trash bin workflow including auto-purge functionality."""

    async def test_delete_restore_flow(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_base: Base,
        test_table: Table,
        test_user: User,
        db_session: AsyncSession,
    ):
        """
        Test the complete trash bin flow:
        1. Create a record
        2. Delete the record (soft delete)
        3. Verify record appears in trash with deleted_at and deleted_by
        4. Restore the record from trash
        5. Verify record is restored and accessible
        6. Verify deleted_by_id is set correctly throughout
        """
        # Step 1: Create a test record via API
        record_data = {
            "table_id": str(test_table.id),
            "data": {
                "Name": "Test Part",
                "Description": "A test part for trash bin",
                "Quantity": 100,
            },
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/records",
            headers=auth_headers,
            json=record_data,
        )
        assert response.status_code == 201, f"Record creation failed: {response.text}"
        record = response.json()
        assert record["data"]["Name"] == "Test Part"
        assert "id" in record
        record_id = record["id"]

        # Verify record is accessible immediately after creation
        response = await client.get(
            f"{settings.api_v1_prefix}/records/{record_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Record retrieval failed: {response.text}"
        created_record = response.json()
        assert created_record["data"]["Name"] == "Test Part"

        # Step 2: Delete the record via API (soft delete)
        response = await client.delete(
            f"{settings.api_v1_prefix}/records/{record_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204, f"Record deletion failed: {response.text}"

        # Verify record is no longer accessible via normal records endpoint
        response = await client.get(
            f"{settings.api_v1_prefix}/records/{record_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404, "Deleted record should not be found"

        # Step 3: Call GET /api/v1/trash and verify record appears with deleted_at and deleted_by
        response = await client.get(
            f"{settings.api_v1_prefix}/trash",
            headers=auth_headers,
            params={"table_id": str(test_table.id)},
        )
        assert response.status_code == 200, f"Trash list retrieval failed: {response.text}"
        trash_list = response.json()

        # Verify trash list structure
        assert "items" in trash_list
        assert "total" in trash_list
        assert trash_list["total"] >= 1

        # Find our deleted record in trash
        deleted_record = None
        for item in trash_list["items"]:
            if item["id"] == record_id:
                deleted_record = item
                break

        assert deleted_record is not None, "Deleted record should appear in trash"

        # Verify deleted_at timestamp is set
        assert "deleted_at" in deleted_record
        assert deleted_record["deleted_at"] is not None
        deleted_at = datetime.fromisoformat(deleted_record["deleted_at"].replace("Z", "+00:00"))
        assert deleted_at <= datetime.now(UTC), "deleted_at should be in the past"

        # Verify deleted_by_id is set correctly
        assert "deleted_by_id" in deleted_record
        assert deleted_record["deleted_by_id"] == str(test_user.id), "deleted_by_id should match the user who deleted"

        # Verify record data is preserved
        assert deleted_record["data"]["Name"] == "Test Part"
        assert deleted_record["data"]["Quantity"] == 100

        # Verify table_id is preserved
        assert deleted_record["table_id"] == str(test_table.id)

        # Step 4: Call POST /api/v1/trash/{id}/restore
        response = await client.post(
            f"{settings.api_v1_prefix}/trash/{record_id}/restore",
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Record restore failed: {response.text}"
        restore_response = response.json()

        # Verify restore response structure
        assert "id" in restore_response
        assert "message" in restore_response
        assert restore_response["id"] == record_id
        assert restore_response["message"] == "Record restored successfully"

        # Step 5: Call GET /api/v1/records/{id} and verify record is restored
        response = await client.get(
            f"{settings.api_v1_prefix}/records/{record_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Restored record retrieval failed: {response.text}"
        restored_record = response.json()

        # Verify record data is intact after restoration
        assert restored_record["id"] == record_id
        assert restored_record["data"]["Name"] == "Test Part"
        assert restored_record["data"]["Description"] == "A test part for trash bin"
        assert restored_record["data"]["Quantity"] == 100
        assert restored_record["table_id"] == str(test_table.id)

        # Step 6: Verify deleted_by_id is cleared after restoration
        # Query the record directly from database to check soft delete fields
        result = await db_session.execute(
            f"SELECT deleted_at, is_deleted, deleted_by_id FROM records WHERE id = '{record_id}'"
        )
        row = result.fetchone()
        assert row is not None, "Record should exist in database"

        deleted_at_db, is_deleted_db, deleted_by_id_db = row
        assert is_deleted_db is False, "is_deleted should be False after restoration"
        assert deleted_at_db is None, "deleted_at should be None after restoration"
        assert deleted_by_id_db is None, "deleted_by_id should be None after restoration"

        # Verify record no longer appears in trash
        response = await client.get(
            f"{settings.api_v1_prefix}/trash",
            headers=auth_headers,
            params={"table_id": str(test_table.id)},
        )
        assert response.status_code == 200
        trash_list_after = response.json()

        # Our record should not be in trash anymore
        for item in trash_list_after["items"]:
            assert item["id"] != record_id, "Restored record should not appear in trash"

    async def test_multiple_records_delete_restore(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
        test_user: User,
    ):
        """Test deleting and restoring multiple records."""
        # Create multiple test records
        record_ids = []
        for i in range(3):
            record_data = {
                "table_id": str(test_table.id),
                "data": {
                    "Name": f"Test Part {i}",
                    "Description": f"Test description {i}",
                    "Quantity": i * 10,
                },
            }
            response = await client.post(
                f"{settings.api_v1_prefix}/records",
                headers=auth_headers,
                json=record_data,
            )
            assert response.status_code == 201
            record_ids.append(response.json()["id"])

        # Delete all records
        for record_id in record_ids:
            response = await client.delete(
                f"{settings.api_v1_prefix}/records/{record_id}",
                headers=auth_headers,
            )
            assert response.status_code == 204

        # Verify all records appear in trash
        response = await client.get(
            f"{settings.api_v1_prefix}/trash",
            headers=auth_headers,
            params={"table_id": str(test_table.id)},
        )
        assert response.status_code == 200
        trash_list = response.json()
        assert trash_list["total"] >= 3

        # Restore all records using batch restore
        response = await client.post(
            f"{settings.api_v1_prefix}/trash/batch/restore",
            headers=auth_headers,
            json={"record_ids": record_ids},
        )
        assert response.status_code == 200
        batch_result = response.json()

        # Verify batch restore response
        assert batch_result["total"] == 3
        assert batch_result["successful"] == 3
        assert batch_result["failed"] == 0
        assert len(batch_result["results"]) == 3

        # Verify all records are accessible again
        for record_id in record_ids:
            response = await client.get(
                f"{settings.api_v1_prefix}/records/{record_id}",
                headers=auth_headers,
            )
            assert response.status_code == 200, f"Record {record_id} should be restored"
            record = response.json()
            assert record["data"]["Name"].startswith("Test Part")

    async def test_trash_with_table_filtering(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_base: Base,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test that trash list can be filtered by table_id."""
        # Create two tables
        table1 = test_base  # Use the existing table

        table2 = Table(
            base_id=test_base.id,
            name="Second Table",
            description="Second test table",
        )
        db_session.add(table2)
        await db_session.commit()
        await db_session.refresh(table2)

        # Add fields to table2
        field = Field(
            table_id=table2.id,
            name="Title",
            field_type=FieldType.TEXT,
            order=0,
        )
        db_session.add(field)
        await db_session.commit()

        # Create records in both tables
        record1_data = {
            "table_id": str(table1.id),
            "data": {"Name": "Record in Table 1", "Description": "Test", "Quantity": 1},
        }
        response = await client.post(
            f"{settings.api_v1_prefix}/records",
            headers=auth_headers,
            json=record1_data,
        )
        assert response.status_code == 201
        record1_id = response.json()["id"]

        record2_data = {
            "table_id": str(table2.id),
            "data": {"Title": "Record in Table 2"},
        }
        response = await client.post(
            f"{settings.api_v1_prefix}/records",
            headers=auth_headers,
            json=record2_data,
        )
        assert response.status_code == 201
        record2_id = response.json()["id"]

        # Delete both records
        await client.delete(
            f"{settings.api_v1_prefix}/records/{record1_id}",
            headers=auth_headers,
        )
        await client.delete(
            f"{settings.api_v1_prefix}/records/{record2_id}",
            headers=auth_headers,
        )

        # Get all trash (no filter)
        response = await client.get(
            f"{settings.api_v1_prefix}/trash",
            headers=auth_headers,
        )
        assert response.status_code == 200
        all_trash = response.json()
        assert all_trash["total"] >= 2

        # Filter by table1
        response = await client.get(
            f"{settings.api_v1_prefix}/trash",
            headers=auth_headers,
            params={"table_id": str(table1.id)},
        )
        assert response.status_code == 200
        table1_trash = response.json()
        assert any(item["id"] == record1_id for item in table1_trash["items"])
        assert not any(item["id"] == record2_id for item in table1_trash["items"])

        # Filter by table2
        response = await client.get(
            f"{settings.api_v1_prefix}/trash",
            headers=auth_headers,
            params={"table_id": str(table2.id)},
        )
        assert response.status_code == 200
        table2_trash = response.json()
        assert not any(item["id"] == record1_id for item in table2_trash["items"])
        assert any(item["id"] == record2_id for item in table2_trash["items"])

        # Cleanup: restore both records
        await client.post(
            f"{settings.api_v1_prefix}/trash/{record1_id}/restore",
            headers=auth_headers,
        )
        await client.post(
            f"{settings.api_v1_prefix}/trash/{record2_id}/restore",
            headers=auth_headers,
        )

    async def test_permanent_delete_from_trash(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
        test_user: User,
        db_session: AsyncSession,
    ):
        """
        Test permanent delete from trash:
        1. Create a test record via API
        2. Delete the record via API (soft delete)
        3. Call DELETE /api/v1/trash/{id}/permanent
        4. Verify record no longer exists in database (hard deleted)
        5. Verify record no longer appears in trash list
        """
        # Step 1: Create a test record via API
        record_data = {
            "table_id": str(test_table.id),
            "data": {
                "Name": "Permanent Delete Test Part",
                "Description": "This will be permanently deleted",
                "Quantity": 50,
            },
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/records",
            headers=auth_headers,
            json=record_data,
        )
        assert response.status_code == 201, f"Record creation failed: {response.text}"
        record = response.json()
        assert record["data"]["Name"] == "Permanent Delete Test Part"
        record_id = record["id"]

        # Step 2: Delete the record via API (soft delete)
        response = await client.delete(
            f"{settings.api_v1_prefix}/records/{record_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204, f"Record deletion failed: {response.text}"

        # Verify record appears in trash
        response = await client.get(
            f"{settings.api_v1_prefix}/trash",
            headers=auth_headers,
            params={"table_id": str(test_table.id)},
        )
        assert response.status_code == 200
        trash_list = response.json()
        assert trash_list["total"] >= 1
        assert any(item["id"] == record_id for item in trash_list["items"])

        # Step 3: Call DELETE /api/v1/trash/{id}/permanent
        response = await client.delete(
            f"{settings.api_v1_prefix}/trash/{record_id}/permanent",
            headers=auth_headers,
        )
        assert response.status_code == 204, f"Permanent delete failed: {response.text}"

        # Step 4: Verify record no longer exists in database (hard deleted)
        result = await db_session.execute(
            f"SELECT id, is_deleted FROM records WHERE id = '{record_id}'"
        )
        row = result.fetchone()
        assert row is None, "Record should be permanently deleted from database"

        # Step 5: Verify record no longer appears in trash list
        response = await client.get(
            f"{settings.api_v1_prefix}/trash",
            headers=auth_headers,
            params={"table_id": str(test_table.id)},
        )
        assert response.status_code == 200
        trash_list_after = response.json()

        # Record should not be in trash
        assert not any(
            item["id"] == record_id for item in trash_list_after["items"]
        ), "Permanently deleted record should not appear in trash"

    async def test_batch_permanent_delete_from_trash(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
        test_user: User,
        db_session: AsyncSession,
    ):
        """
        Test batch permanent delete from trash:
        1. Create multiple test records via API
        2. Delete all records via API (soft delete)
        3. Call DELETE /api/v1/trash/batch/permanent
        4. Verify all records no longer exist in database (hard deleted)
        5. Verify records no longer appear in trash list
        """
        # Step 1: Create multiple test records
        record_ids = []
        for i in range(3):
            record_data = {
                "table_id": str(test_table.id),
                "data": {
                    "Name": f"Batch Delete Test Part {i}",
                    "Description": f"Test part {i} for batch permanent delete",
                    "Quantity": i * 10,
                },
            }
            response = await client.post(
                f"{settings.api_v1_prefix}/records",
                headers=auth_headers,
                json=record_data,
            )
            assert response.status_code == 201, f"Record {i} creation failed: {response.text}"
            record_ids.append(response.json()["id"])

        # Step 2: Delete all records (soft delete)
        for record_id in record_ids:
            response = await client.delete(
                f"{settings.api_v1_prefix}/records/{record_id}",
                headers=auth_headers,
            )
            assert response.status_code == 204

        # Verify all records appear in trash
        response = await client.get(
            f"{settings.api_v1_prefix}/trash",
            headers=auth_headers,
            params={"table_id": str(test_table.id)},
        )
        assert response.status_code == 200
        trash_list = response.json()
        assert trash_list["total"] >= 3

        # Step 3: Call DELETE /api/v1/trash/batch/permanent
        response = await client.delete(
            f"{settings.api_v1_prefix}/trash/batch/permanent",
            headers=auth_headers,
            json={"record_ids": record_ids},
        )
        assert response.status_code == 200, f"Batch permanent delete failed: {response.text}"
        batch_result = response.json()

        # Verify batch permanent delete response
        assert batch_result["total"] == 3
        assert batch_result["successful"] == 3
        assert batch_result["failed"] == 0
        assert len(batch_result["results"]) == 3

        # Step 4: Verify all records no longer exist in database (hard deleted)
        for record_id in record_ids:
            result = await db_session.execute(
                f"SELECT id, is_deleted FROM records WHERE id = '{record_id}'"
            )
            row = result.fetchone()
            assert row is None, f"Record {record_id} should be permanently deleted from database"

        # Step 5: Verify records no longer appear in trash list
        response = await client.get(
            f"{settings.api_v1_prefix}/trash",
            headers=auth_headers,
            params={"table_id": str(test_table.id)},
        )
        assert response.status_code == 200
        trash_list_after = response.json()

        # None of the permanently deleted records should be in trash
        for record_id in record_ids:
            assert not any(
                item["id"] == record_id for item in trash_list_after["items"]
            ), f"Permanently deleted record {record_id} should not appear in trash"

    async def test_auto_purge_worker_functionality(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
        test_user: User,
        db_session: AsyncSession,
    ):
        """
        Test auto-purge worker functionality:
        1. Create test records and delete them (set deleted_at to 35 days ago for old records)
        2. Create test records and delete them (set deleted_at to recent date for recent records)
        3. Run purge_old_trash task manually
        4. Verify old records (older than 30 days) are permanently deleted from database
        5. Verify recent deleted records (within 30 days) are not purged
        """
        from workers.celery_maintenance_worker import purge_old_trash

        # Step 1: Create old deleted records (35 days ago)
        old_record_ids = []
        for i in range(2):
            record_data = {
                "table_id": str(test_table.id),
                "data": {
                    "Name": f"Old Record {i}",
                    "Description": "Deleted 35 days ago",
                    "Quantity": i * 10,
                },
            }
            response = await client.post(
                f"{settings.api_v1_prefix}/records",
                headers=auth_headers,
                json=record_data,
            )
            assert response.status_code == 201, f"Old record {i} creation failed: {response.text}"
            old_record_ids.append(response.json()["id"])

        # Soft delete old records and manually set deleted_at to 35 days ago
        old_deleted_at = datetime.now(UTC) - timedelta(days=35)
        for record_id in old_record_ids:
            # First soft delete normally
            response = await client.delete(
                f"{settings.api_v1_prefix}/records/{record_id}",
                headers=auth_headers,
            )
            assert response.status_code == 204

            # Then update deleted_at to 35 days ago to simulate old deleted records
            await db_session.execute(
                update(Record)
                .where(Record.id == record_id)
                .values(deleted_at=old_deleted_at)
            )
            await db_session.commit()

        # Step 2: Create recent deleted records (5 days ago)
        recent_record_ids = []
        for i in range(2):
            record_data = {
                "table_id": str(test_table.id),
                "data": {
                    "Name": f"Recent Record {i}",
                    "Description": "Deleted 5 days ago",
                    "Quantity": i * 20,
                },
            }
            response = await client.post(
                f"{settings.api_v1_prefix}/records",
                headers=auth_headers,
                json=record_data,
            )
            assert response.status_code == 201, f"Recent record {i} creation failed: {response.text}"
            recent_record_ids.append(response.json()["id"])

        # Soft delete recent records (deleted_at will be set to current time)
        for record_id in recent_record_ids:
            response = await client.delete(
                f"{settings.api_v1_prefix}/records/{record_id}",
                headers=auth_headers,
            )
            assert response.status_code == 204

        # Verify all records appear in trash before purge
        response = await client.get(
            f"{settings.api_v1_prefix}/trash",
            headers=auth_headers,
            params={"table_id": str(test_table.id)},
        )
        assert response.status_code == 200
        trash_list_before = response.json()
        assert trash_list_before["total"] >= 4, "Should have at least 4 deleted records"

        # Verify old records have deleted_at set to 35 days ago
        for record_id in old_record_ids:
            result = await db_session.execute(
                f"SELECT deleted_at FROM records WHERE id = '{record_id}'"
            )
            row = result.fetchone()
            assert row is not None
            deleted_at_db = row[0]
            assert deleted_at_db is not None
            # Check that deleted_at is approximately 35 days ago (allow 1 minute tolerance)
            days_diff = (datetime.now(UTC) - deleted_at_db).days
            assert days_diff >= 34 and days_diff <= 35, f"Old record should be deleted ~35 days ago, got {days_diff} days"

        # Verify recent records have deleted_at set to recent time
        for record_id in recent_record_ids:
            result = await db_session.execute(
                f"SELECT deleted_at FROM records WHERE id = '{record_id}'"
            )
            row = result.fetchone()
            assert row is not None
            deleted_at_db = row[0]
            assert deleted_at_db is not None
            # Check that deleted_at is recent (less than 1 day ago)
            days_diff = (datetime.now(UTC) - deleted_at_db).days
            assert days_diff == 0, f"Recent record should be deleted recently, got {days_diff} days ago"

        # Step 3: Run purge_old_trash task manually with 30 day retention
        purge_result = purge_old_trash(retention_days=30, dry_run=False)

        # Verify purge task completed successfully
        assert purge_result is not None, "Purge task should return a result"
        assert purge_result["status"] == "completed", f"Purge task should complete successfully, got: {purge_result}"
        assert "purged_count" in purge_result, "Purge result should include purged_count"
        assert purge_result["purged_count"] >= 2, f"Should purge at least 2 old records, purged: {purge_result['purged_count']}"

        # Step 4: Verify old records (older than 30 days) are permanently deleted from database
        for record_id in old_record_ids:
            result = await db_session.execute(
                f"SELECT id, is_deleted FROM records WHERE id = '{record_id}'"
            )
            row = result.fetchone()
            assert row is None, f"Old record {record_id} should be permanently deleted from database"

        # Step 5: Verify recent deleted records (within 30 days) are not purged
        for record_id in recent_record_ids:
            # Verify record still exists in database (soft deleted)
            result = await db_session.execute(
                f"SELECT id, is_deleted, deleted_at FROM records WHERE id = '{record_id}'"
            )
            row = result.fetchone()
            assert row is not None, f"Recent record {record_id} should still exist in database"
            record_id_db, is_deleted_db, deleted_at_db = row
            assert is_deleted_db is True, f"Recent record should still be soft deleted"
            assert deleted_at_db is not None, f"Recent record should have deleted_at set"

            # Verify record still appears in trash
            response = await client.get(
                f"{settings.api_v1_prefix}/trash",
                headers=auth_headers,
                params={"table_id": str(test_table.id)},
            )
            assert response.status_code == 200
            trash_list_after = response.json()

            # Find this recent record in trash
            found_in_trash = any(
                item["id"] == record_id for item in trash_list_after["items"]
            )
            assert found_in_trash, f"Recent record {record_id} should still appear in trash"

        # Verify trash list count decreased appropriately
        # Before purge: at least 4 records (2 old + 2 recent)
        # After purge: at least 2 records (2 recent, old ones purged)
        response = await client.get(
            f"{settings.api_v1_prefix}/trash",
            headers=auth_headers,
            params={"table_id": str(test_table.id)},
        )
        assert response.status_code == 200
        trash_list_final = response.json()

        # Old records should not be in trash
        for record_id in old_record_ids:
            assert not any(
                item["id"] == record_id for item in trash_list_final["items"]
            ), f"Old purged record {record_id} should not appear in trash"

        # Recent records should still be in trash
        for record_id in recent_record_ids:
            assert any(
                item["id"] == record_id for item in trash_list_final["items"]
            ), f"Recent record {record_id} should still appear in trash"
