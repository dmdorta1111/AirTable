"""
Integration tests for undo/redo functionality on record operations.

These tests verify end-to-end undo/redo behavior for record creation,
ensuring operations are properly logged, undone, and redone.
"""

import json

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.operation_log import OperationLog
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace
from pybase.models.user import User
from pybase.schemas.record import RecordCreate
from pybase.services.record import RecordService
from pybase.services.undo_redo import UndoRedoService


@pytest.mark.asyncio
async def test_undo_redo_record_create_full_cycle(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test end-to-end undo/redo for record creation: create -> undo -> redo."""
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

    # Step 1: Create a new record
    record_service = RecordService()
    undo_redo_service = UndoRedoService()

    record_data = RecordCreate(
        table_id=str(table.id),
        data={str(field.id): "Test Value"},
    )

    created_record = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=record_data,
    )
    await db_session.commit()
    await db_session.refresh(created_record)

    # Verify record appears in database
    assert created_record is not None
    assert created_record.id is not None

    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    records = result.scalars().all()
    assert len(records) == 1
    assert records[0].id == created_record.id

    # Verify operation was logged
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(operations[0]) == 1
    operation = operations[0][0]
    assert operation.operation_type == "create"
    assert operation.entity_type == "record"
    assert operation.entity_id == str(created_record.id)

    # Step 2: Undo the record creation
    undone_operation = await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(operation.id),
    )
    await db_session.commit()
    await db_session.refresh(created_record)

    # Verify record is soft-deleted (undo successful)
    assert undone_operation.id == operation.id
    assert created_record.deleted_at is not None
    assert created_record.deleted_by_id == test_user.id

    # Verify record no longer appears in queries (is_deleted filter)
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 0

    # Step 3: Redo the record creation
    redone_operation = await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(operation.id),
    )
    await db_session.commit()
    await db_session.refresh(created_record)

    # Verify record is restored (redo successful)
    assert redone_operation.id == operation.id
    assert created_record.deleted_at is None
    assert created_record.deleted_by_id is None

    # Verify record appears in database again
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    restored_records = result.scalars().all()
    assert len(restored_records) == 1
    assert restored_records[0].id == created_record.id

    # Verify data integrity after redo
    record_data_json = json.loads(created_record.data)
    assert record_data_json.get(str(field.id)) == "Test Value"


@pytest.mark.asyncio
async def test_undo_redo_record_update_full_cycle(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test end-to-end undo/redo for record update: update -> undo -> redo."""
    # Setup: Create workspace, base, table, field, and initial record
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

    # Create initial record
    initial_record = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Initial Value"},
        ),
    )
    await db_session.commit()
    await db_session.refresh(initial_record)

    # Step 1: Update the record
    from pybase.schemas.record import RecordUpdate

    updated_record = await record_service.update_record(
        db=db_session,
        record_id=str(initial_record.id),
        user_id=str(test_user.id),
        record_data=RecordUpdate(
            data={str(field.id): "Updated Value"},
        ),
    )
    await db_session.commit()
    await db_session.refresh(updated_record)

    # Verify update in database
    result = await db_session.execute(
        select(Record).where(Record.id == initial_record.id)
    )
    record = result.scalar_one()
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field.id)) == "Updated Value"

    # Get the update operation log
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    update_operation = [op for op in operations[0] if op.operation_type == "update"][0]

    # Step 2: Undo the update (should revert to "Initial Value")
    await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_operation.id),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify old value is restored
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field.id)) == "Initial Value"

    # Step 3: Redo the update (should restore "Updated Value")
    await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_operation.id),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify new value is restored
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field.id)) == "Updated Value"


@pytest.mark.asyncio
async def test_undo_redo_record_delete_full_cycle(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test end-to-end undo/redo for record delete: delete -> undo -> redo."""
    # Setup: Create workspace, base, table, field, and record
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

    # Create record
    record = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Test Value"},
        ),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Step 1: Delete the record
    deleted_record = await record_service.delete_record(
        db=db_session,
        record_id=str(record.id),
        user_id=str(test_user.id),
    )
    await db_session.commit()
    await db_session.refresh(deleted_record)

    # Verify record is soft-deleted
    assert deleted_record.deleted_at is not None

    # Get the delete operation log
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    delete_operation = [op for op in operations[0] if op.operation_type == "delete"][0]

    # Step 2: Undo the delete (should restore the record)
    await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(delete_operation.id),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify record is restored
    assert record.deleted_at is None
    assert record.deleted_by_id is None

    # Verify record appears in active queries
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 1

    # Step 3: Redo the delete (should delete the record again)
    await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(delete_operation.id),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify record is deleted again
    assert record.deleted_at is not None
    assert record.deleted_by_id == test_user.id


@pytest.mark.asyncio
async def test_undo_redo_multiple_operations_sequential(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test undo/redo with multiple operations in sequence."""
    # Setup
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

    # Create multiple records
    record1 = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Value 1"},
        ),
    )
    await db_session.commit()

    record2 = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Value 2"},
        ),
    )
    await db_session.commit()

    record3 = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Value 3"},
        ),
    )
    await db_session.commit()

    # Verify 3 records exist
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    records = result.scalars().all()
    assert len(records) == 3

    # Get all operations (most recent first)
    operations, _ = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(operations) == 3

    # Undo most recent operation (record3 creation)
    await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(operations[0].id),  # Most recent
    )
    await db_session.commit()

    # Verify only 2 records remain
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 2

    # Redo the operation
    await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(operations[0].id),
    )
    await db_session.commit()

    # Verify 3 records exist again
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 3


@pytest.mark.asyncio
async def test_undo_operation_requires_ownership(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that users can only undo their own operations."""
    # Setup
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

    # Create another user
    from pybase.core.security import hash_password

    other_user = User(
        email="other@example.com",
        hashed_password=hash_password("otherpass123"),
        name="Other User",
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    record_service = RecordService()
    undo_redo_service = UndoRedoService()

    # Create record as test_user
    record = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Test Value"},
        ),
    )
    await db_session.commit()

    # Get the operation
    operations, _ = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    operation = operations[0]

    # Try to undo as other_user (should fail)
    from pybase.core.exceptions import PermissionDeniedError

    with pytest.raises(PermissionDeniedError):
        await undo_redo_service.undo_operation(
            db=db_session,
            user_id=str(other_user.id),
            operation_id=str(operation.id),
        )


@pytest.mark.asyncio
async def test_undo_redo_preserves_operation_log(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that undo/redo operations preserve the operation log."""
    # Setup
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

    # Create record
    record = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Test Value"},
        ),
    )
    await db_session.commit()

    # Get initial operation count
    operations_before, _ = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    initial_count = len(operations_before)
    operation_id = operations_before[0].id

    # Undo
    await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(operation_id),
    )
    await db_session.commit()

    # Verify operation log still exists
    operations_after_undo, _ = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(operations_after_undo) == initial_count

    # Redo
    await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(operation_id),
    )
    await db_session.commit()

    # Verify operation log still exists
    operations_after_redo, _ = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(operations_after_redo) == initial_count
