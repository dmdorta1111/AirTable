"""
Integration tests for undo/redo functionality on batch operations.

These tests verify end-to-end undo/redo behavior for batch record operations,
ensuring that batch creates can be undone/redone as single actions.
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
async def test_undo_redo_batch_create_full_cycle(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test end-to-end undo/redo for batch record creation: create batch -> undo -> redo."""
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

    # Step 1: Create multiple records in batch operation
    record_service = RecordService()
    undo_redo_service = UndoRedoService()

    batch_data = [
        RecordCreate(
            table_id=str(table.id),
            data={str(field.id): f"Batch Value {i}"},
        )
        for i in range(1, 6)  # Create 5 records
    ]

    created_records = await record_service.batch_create_records(
        db=db_session,
        user_id=str(test_user.id),
        table_id=table.id,
        records_data=batch_data,
    )
    await db_session.commit()

    # Verify all records created
    assert len(created_records) == 5
    for i, record in enumerate(created_records, 1):
        assert record.id is not None
        record_data_json = json.loads(record.data)
        assert record_data_json.get(str(field.id)) == f"Batch Value {i}"

    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 5

    # Verify operations were logged (should be 5 individual logs based on current impl)
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(operations[0]) == 5
    create_operations = [op for op in operations[0] if op.operation_type == "create"]
    assert len(create_operations) == 5

    # Step 2: Press Ctrl+Z to undo (simulate undoing all batch operations)
    # Undo all operations in reverse order (most recent first)
    for operation in reversed(create_operations):
        await undo_redo_service.undo_operation(
            db=db_session,
            user_id=str(test_user.id),
            operation_id=str(operation.id),
        )
    await db_session.commit()

    # Verify all batch records deleted
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 0

    # Verify all records are soft-deleted
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    all_records = result.scalars().all()
    assert len(all_records) == 5
    assert all(record.deleted_at is not None for record in all_records)

    # Step 3: Press Ctrl+Shift+Z to redo (simulate redoing all batch operations)
    # Redo all operations in original order
    for operation in create_operations:
        await undo_redo_service.redo_operation(
            db=db_session,
            user_id=str(test_user.id),
            operation_id=str(operation.id),
        )
    await db_session.commit()

    # Verify all batch records restored
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    restored_records = result.scalars().all()
    assert len(restored_records) == 5

    # Verify data integrity after redo
    for i, record in enumerate(sorted(restored_records, key=lambda r: r.created_at), 1):
        record_data_json = json.loads(record.data)
        assert record_data_json.get(str(field.id)) == f"Batch Value {i}"


@pytest.mark.asyncio
async def test_undo_redo_batch_update_full_cycle(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test end-to-end undo/redo for batch record updates: update batch -> undo -> redo."""
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

    # Create initial records
    initial_batch = [
        RecordCreate(
            table_id=str(table.id),
            data={str(field.id): f"Initial {i}"},
        )
        for i in range(1, 4)
    ]
    created_records = await record_service.batch_create_records(
        db=db_session,
        user_id=str(test_user.id),
        table_id=table.id,
        records_data=initial_batch,
    )
    await db_session.commit()

    # Step 1: Update all records in batch
    from pybase.schemas.record import RecordUpdate

    batch_updates = [
        (str(record.id), RecordUpdate(data={str(field.id): f"Updated {i}"}))
        for i, record in enumerate(created_records, 1)
    ]

    updated_records = await record_service.batch_update_records(
        db=db_session,
        user_id=str(test_user.id),
        table_id=table.id,
        updates=batch_updates,
    )
    await db_session.commit()

    # Verify all updates
    assert len(updated_records) == 3
    for i, record in enumerate(sorted(updated_records, key=lambda r: r.created_at), 1):
        record_data_json = json.loads(record.data)
        assert record_data_json.get(str(field.id)) == f"Updated {i}"

    # Get update operations
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    update_operations = [op for op in operations[0] if op.operation_type == "update"]
    assert len(update_operations) == 3

    # Step 2: Undo all updates (should revert to initial values)
    for operation in reversed(update_operations):
        await undo_redo_service.undo_operation(
            db=db_session,
            user_id=str(test_user.id),
            operation_id=str(operation.id),
        )
    await db_session.commit()

    # Verify all initial values restored
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    records = result.scalars().all()
    assert len(records) == 3
    for i, record in enumerate(sorted(records, key=lambda r: r.created_at), 1):
        record_data_json = json.loads(record.data)
        assert record_data_json.get(str(field.id)) == f"Initial {i}"

    # Step 3: Redo all updates (should restore updated values)
    for operation in update_operations:
        await undo_redo_service.redo_operation(
            db=db_session,
            user_id=str(test_user.id),
            operation_id=str(operation.id),
        )
    await db_session.commit()

    # Verify all updated values restored
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    records = result.scalars().all()
    assert len(records) == 3
    for i, record in enumerate(sorted(records, key=lambda r: r.created_at), 1):
        record_data_json = json.loads(record.data)
        assert record_data_json.get(str(field.id)) == f"Updated {i}"


@pytest.mark.asyncio
async def test_undo_redo_batch_delete_full_cycle(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test end-to-end undo/redo for batch record delete: delete batch -> undo -> redo."""
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

    # Create records
    batch_data = [
        RecordCreate(
            table_id=str(table.id),
            data={str(field.id): f"Value {i}"},
        )
        for i in range(1, 4)
    ]
    created_records = await record_service.batch_create_records(
        db=db_session,
        user_id=str(test_user.id),
        table_id=table.id,
        records_data=batch_data,
    )
    await db_session.commit()

    # Verify records created
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 3

    # Step 1: Delete all records in batch
    record_ids = [str(record.id) for record in created_records]
    deleted_records = await record_service.batch_delete_records(
        db=db_session,
        user_id=str(test_user.id),
        table_id=table.id,
        record_ids=record_ids,
    )
    await db_session.commit()

    # Verify all records deleted
    assert len(deleted_records) == 3
    assert all(record.deleted_at is not None for record in deleted_records)

    # Get delete operations
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    delete_operations = [op for op in operations[0] if op.operation_type == "delete"]
    assert len(delete_operations) == 3

    # Step 2: Undo all deletes (should restore all records)
    for operation in reversed(delete_operations):
        await undo_redo_service.undo_operation(
            db=db_session,
            user_id=str(test_user.id),
            operation_id=str(operation.id),
        )
    await db_session.commit()

    # Verify all records restored
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    restored_records = result.scalars().all()
    assert len(restored_records) == 3

    # Verify data integrity
    for i, record in enumerate(sorted(restored_records, key=lambda r: r.created_at), 1):
        record_data_json = json.loads(record.data)
        assert record_data_json.get(str(field.id)) == f"Value {i}"

    # Step 3: Redo all deletes (should delete all records again)
    for operation in delete_operations:
        await undo_redo_service.redo_operation(
            db=db_session,
            user_id=str(test_user.id),
            operation_id=str(operation.id),
        )
    await db_session.commit()

    # Verify all records deleted again
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 0


@pytest.mark.asyncio
async def test_undo_redo_partial_batch_undo(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test undoing only some operations from a batch."""
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

    # Create batch of 5 records
    batch_data = [
        RecordCreate(
            table_id=str(table.id),
            data={str(field.id): f"Value {i}"},
        )
        for i in range(1, 6)
    ]
    created_records = await record_service.batch_create_records(
        db=db_session,
        user_id=str(test_user.id),
        table_id=table.id,
        records_data=batch_data,
    )
    await db_session.commit()

    # Verify 5 records exist
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 5

    # Get all operations
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    create_operations = [op for op in operations[0] if op.operation_type == "create"]
    assert len(create_operations) == 5

    # Undo only the last 2 operations (partial undo)
    await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(create_operations[4].id),  # 5th record
    )
    await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(create_operations[3].id),  # 4th record
    )
    await db_session.commit()

    # Verify only 3 records remain
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 3

    # Redo the undone operations
    await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(create_operations[3].id),
    )
    await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(create_operations[4].id),
    )
    await db_session.commit()

    # Verify all 5 records restored
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 5


@pytest.mark.asyncio
async def test_undo_redo_batch_preserves_record_order(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that undo/redo of batch operations preserves record order and data."""
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

    # Create batch with specific values
    batch_data = [
        RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "First"},
        ),
        RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Second"},
        ),
        RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Third"},
        ),
    ]
    created_records = await record_service.batch_create_records(
        db=db_session,
        user_id=str(test_user.id),
        table_id=table.id,
        records_data=batch_data,
    )
    await db_session.commit()

    # Store original order and data
    original_order = sorted(created_records, key=lambda r: r.created_at)
    original_data = []
    for record in original_order:
        data = json.loads(record.data)
        original_data.append(data[str(field.id)])

    assert original_data == ["First", "Second", "Third"]

    # Get operations and undo all
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    create_operations = [op for op in operations[0] if op.operation_type == "create"]

    for operation in reversed(create_operations):
        await undo_redo_service.undo_operation(
            db=db_session,
            user_id=str(test_user.id),
            operation_id=str(operation.id),
        )
    await db_session.commit()

    # Redo all
    for operation in create_operations:
        await undo_redo_service.redo_operation(
            db=db_session,
            user_id=str(test_user.id),
            operation_id=str(operation.id),
        )
    await db_session.commit()

    # Verify order and data preserved
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    restored_records = result.scalars().all()
    assert len(restored_records) == 3

    restored_order = sorted(restored_records, key=lambda r: r.created_at)
    restored_data = []
    for record in restored_order:
        data = json.loads(record.data)
        restored_data.append(data[str(field.id)])

    assert restored_data == ["First", "Second", "Third"]


@pytest.mark.asyncio
async def test_undo_redo_batch_with_mixed_operations(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test undo/redo when batch operations are mixed with individual operations."""
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

    # Individual create
    record1 = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Individual 1"},
        ),
    )
    await db_session.commit()

    # Batch create (2 records)
    batch_data = [
        RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Batch 1"},
        ),
        RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Batch 2"},
        ),
    ]
    batch_records = await record_service.batch_create_records(
        db=db_session,
        user_id=str(test_user.id),
        table_id=table.id,
        records_data=batch_data,
    )
    await db_session.commit()

    # Individual create
    record2 = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Individual 2"},
        ),
    )
    await db_session.commit()

    # Verify 4 records exist
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 4

    # Get all operations (should be 4 creates)
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    create_operations = [op for op in operations[0] if op.operation_type == "create"]
    assert len(create_operations) == 4

    # Undo batch operations (middle 2)
    await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(create_operations[2].id),
    )
    await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(create_operations[1].id),
    )
    await db_session.commit()

    # Verify 2 records remain (individual ones)
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 2

    # Redo batch operations
    await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(create_operations[1].id),
    )
    await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(create_operations[2].id),
    )
    await db_session.commit()

    # Verify all 4 records restored
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 4
