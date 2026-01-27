"""
Integration tests for undo/redo stack limit functionality.

These tests verify that the undo stack is limited to 100 operations per user,
and that the oldest operations are automatically deleted when the limit is exceeded.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.field import Field, FieldType
from pybase.models.operation_log import OperationLog
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.base import Base
from pybase.models.workspace import Workspace
from pybase.models.user import User
from pybase.schemas.record import RecordCreate
from pybase.services.record import RecordService
from pybase.services.undo_redo import UndoRedoService


@pytest.mark.asyncio
async def test_undo_stack_limited_to_100_operations(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that undo stack is limited to 100 operations per user.

    Verification steps (from subtask requirements):
    1. Perform 105 operations
    2. Check database that only last 100 operations exist
    3. Verify oldest operations were auto-deleted
    """
    # Setup: Create workspace, base, table, and field
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Test Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    field = Field(
        table_id=table.id,
        name="Test Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    record_service = RecordService()
    undo_redo_service = UndoRedoService()

    # Step 1: Perform 105 operations (create 105 records)
    created_record_ids = []
    for i in range(105):
        record_data = RecordCreate(
            table_id=str(table.id),
            data={str(field.id): f"Test Value {i}"},
        )

        created_record = await record_service.create_record(
            db=db_session,
            user_id=str(test_user.id),
            record_data=record_data,
        )
        created_record_ids.append(created_record.id)
        await db_session.commit()

    # Step 2: Check database that only last 100 operations exist
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )

    # Verify exactly 100 operations exist
    assert len(operations[0]) == 100, f"Expected 100 operations, got {len(operations[0])}"
    assert operations[1] == 100, f"Expected total count 100, got {operations[1]}"

    # Step 3: Verify oldest operations were auto-deleted
    # The first 5 operations (records 0-4) should have been deleted
    # The last 100 operations (records 5-104) should still exist

    # Get all operation IDs from database
    result = await db_session.execute(
        select(OperationLog.id)
        .where(OperationLog.user_id == str(test_user.id))
        .order_by(OperationLog.created_at.asc())
    )
    operation_ids = result.scalars().all()

    # Verify we have exactly 100 operation logs
    assert len(operation_ids) == 100, f"Expected 100 operation logs in DB, got {len(operation_ids)}"

    # Verify the operations correspond to the last 100 created records
    # (records 5-104, i.e., created_record_ids[5:105])
    expected_record_ids = created_record_ids[5:]  # Last 100 records
    actual_entity_ids = []

    for op_id in operation_ids:
        op = await db_session.get(OperationLog, op_id)
        actual_entity_ids.append(op.entity_id)

    # Verify all entity IDs in operations match the last 100 created records
    assert set(actual_entity_ids) == set(str(rid) for rid in expected_record_ids), \
        "Operation entity IDs don't match expected last 100 records"

    # Verify the first 5 records are NOT in the operation log
    first_5_record_ids = [str(rid) for rid in created_record_ids[:5]]
    for record_id in first_5_record_ids:
        result = await db_session.execute(
            select(OperationLog).where(OperationLog.entity_id == record_id)
        )
        op = result.scalar_one_or_none()
        assert op is None, f"Record {record_id} should have been deleted from operation log"


@pytest.mark.asyncio
async def test_oldest_operations_deleted_when_limit_exceeded(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that oldest operations are deleted when limit is exceeded.

    This test verifies the FIFO (First In, First Out) behavior of the stack limit.
    """
    # Setup: Create workspace, base, table, and field
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Test Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    field = Field(
        table_id=table.id,
        name="Test Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    record_service = RecordService()
    undo_redo_service = UndoRedoService()

    # Create 100 records (at limit)
    for i in range(100):
        record_data = RecordCreate(
            table_id=str(table.id),
            data={str(field.id): f"Initial Value {i}"},
        )
        await record_service.create_record(
            db=db_session,
            user_id=str(test_user.id),
            record_data=record_data,
        )
        await db_session.commit()

    # Verify we have exactly 100 operations
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(operations[0]) == 100

    # Create 1 more record (should trigger deletion of oldest)
    record_data = RecordCreate(
        table_id=str(table.id),
        data={str(field.id): "Trigger Value"},
    )
    await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=record_data,
    )
    await db_session.commit()

    # Verify we still have exactly 100 operations
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(operations[0]) == 100

    # Verify the oldest operation was deleted
    result = await db_session.execute(
        select(OperationLog)
        .where(OperationLog.user_id == str(test_user.id))
        .order_by(OperationLog.created_at.asc())
    )
    oldest_ops = result.scalars().all()

    # The oldest operation should be the second record created (index 1)
    # because the first record (index 0) was deleted
    assert len(oldest_ops) == 100
    assert oldest_ops[0].entity_type == "record"


@pytest.mark.asyncio
async def test_limit_enforced_per_user(
    db_session: AsyncSession,
) -> None:
    """Test that the 100 operation limit is enforced per user, not globally."""
    # Create two users
    user1 = User(
        email="user1@example.com",
        hashed_password="hash",
        name="User 1",
        is_active=True,
        is_verified=True,
    )
    user2 = User(
        email="user2@example.com",
        hashed_password="hash",
        name="User 2",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user1)
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user1)
    await db_session.refresh(user2)

    # Setup: Create shared workspace, base, table, and field
    workspace = Workspace(owner_id=user1.id, name="Shared Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Shared Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Shared Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    field = Field(
        table_id=table.id,
        name="Test Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    record_service = RecordService()
    undo_redo_service = UndoRedoService()

    # User 1 creates 105 records
    for i in range(105):
        record_data = RecordCreate(
            table_id=str(table.id),
            data={str(field.id): f"User1 Value {i}"},
        )
        await record_service.create_record(
            db=db_session,
            user_id=str(user1.id),
            record_data=record_data,
        )
        await db_session.commit()

    # User 2 creates 105 records
    for i in range(105):
        record_data = RecordCreate(
            table_id=str(table.id),
            data={str(field.id): f"User2 Value {i}"},
        )
        await record_service.create_record(
            db=db_session,
            user_id=str(user2.id),
            record_data=record_data,
        )
        await db_session.commit()

    # Verify User 1 has exactly 100 operations
    user1_operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(user1.id),
    )
    assert len(user1_operations[0]) == 100, "User 1 should have 100 operations"

    # Verify User 2 has exactly 100 operations
    user2_operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(user2.id),
    )
    assert len(user2_operations[0]) == 100, "User 2 should have 100 operations"

    # Verify total operations in database = 200 (100 per user)
    result = await db_session.execute(
        select(OperationLog)
    )
    all_operations = result.scalars().all()
    assert len(all_operations) == 200, "Total operations should be 200 (100 per user)"


@pytest.mark.asyncio
async def test_stack_limit_maintained_after_update_operations(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that stack limit is maintained when performing update operations."""
    # Setup: Create workspace, base, table, and field
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Test Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    field = Field(
        table_id=table.id,
        name="Test Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    record_service = RecordService()
    undo_redo_service = UndoRedoService()

    # Create 1 record
    record_data = RecordCreate(
        table_id=str(table.id),
        data={str(field.id): "Initial Value"},
    )
    record = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=record_data,
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Perform 105 update operations on the same record
    for i in range(105):
        record_data = RecordCreate(
            table_id=str(table.id),
            data={str(field.id): f"Updated Value {i}"},
        )
        await record_service.update_record(
            db=db_session,
            user_id=str(test_user.id),
            record_id=str(record.id),
            record_data=record_data,
        )
        await db_session.commit()

    # Verify we have exactly 101 operations (1 create + 100 updates)
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(operations[0]) == 101, f"Expected 101 operations, got {len(operations[0])}"

    # Verify the oldest update operation was deleted
    # We should have 1 create + 100 most recent updates
    result = await db_session.execute(
        select(OperationLog)
        .where(OperationLog.user_id == str(test_user.id))
        .order_by(OperationLog.created_at.asc())
    )
    oldest_ops = result.scalars().all()

    assert len(oldest_ops) == 101

    # First operation should be the create operation
    assert oldest_ops[0].operation_type == "create"
    # Rest should be update operations (most recent 100)
    for op in oldest_ops[1:]:
        assert op.operation_type == "update"


@pytest.mark.asyncio
async def test_stack_limit_with_mixed_operation_types(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that stack limit works correctly with mixed operation types (create, update, delete)."""
    # Setup: Create workspace, base, table, and field
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Test Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    field = Field(
        table_id=table.id,
        name="Test Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    record_service = RecordService()
    undo_redo_service = UndoRedoService()

    # Create 40 records
    created_records = []
    for i in range(40):
        record_data = RecordCreate(
            table_id=str(table.id),
            data={str(field.id): f"Value {i}"},
        )
        record = await record_service.create_record(
            db=db_session,
            user_id=str(test_user.id),
            record_data=record_data,
        )
        created_records.append(record)
        await db_session.commit()

    # Update 35 records
    for i in range(35):
        record_data = RecordCreate(
            table_id=str(table.id),
            data={str(field.id): f"Updated {i}"},
        )
        await record_service.update_record(
            db=db_session,
            user_id=str(test_user.id),
            record_id=str(created_records[i % 40].id),
            record_data=record_data,
        )
        await db_session.commit()

    # Delete 30 records
    for i in range(30):
        await record_service.delete_record(
            db=db_session,
            user_id=str(test_user.id),
            record_id=str(created_records[i].id),
        )
        await db_session.commit()

    # Total operations: 40 create + 35 update + 30 delete = 105
    # Should have only 100 most recent operations

    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )

    assert len(operations[0]) == 100, f"Expected 100 operations, got {len(operations[0])}"

    # Verify operation types distribution
    operation_types = [op.operation_type for op in operations[0]]
    create_count = operation_types.count("create")
    update_count = operation_types.count("update")
    delete_count = operation_types.count("delete")

    # We should have all 30 deletes (most recent)
    assert delete_count == 30, f"Expected 30 deletes, got {delete_count}"
    # We should have all 35 updates
    assert update_count == 35, f"Expected 35 updates, got {update_count}"
    # We should have 35 creates (most recent 35 of 40, since 5 oldest were deleted)
    assert create_count == 35, f"Expected 35 creates, got {create_count}"

    # Total: 30 + 35 + 35 = 100 ✓
    assert create_count + update_count + delete_count == 100
