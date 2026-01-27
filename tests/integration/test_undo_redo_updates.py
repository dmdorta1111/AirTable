"""
Integration tests for undo/redo functionality on record update operations.

These tests verify end-to-end undo/redo behavior for record updates,
ensuring field value changes are properly logged, undone, and redone.
Tests cover single field updates, multiple field updates, partial updates,
and multiple undo/redo cycles.
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
from pybase.schemas.record import RecordCreate, RecordUpdate
from pybase.services.record import RecordService
from pybase.services.undo_redo import UndoRedoService


@pytest.mark.asyncio
async def test_undo_redo_single_field_update_full_cycle(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test end-to-end undo/redo for single field update: update -> undo -> redo."""
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

    # Verify initial value
    record_data_json = json.loads(initial_record.data)
    assert record_data_json.get(str(field.id)) == "Initial Value"

    # Step 1: Update record field to new value
    updated_record = await record_service.update_record(
        db=db_session,
        record_id=str(initial_record.id),
        user_id=str(test_user.id),
        record_data=RecordUpdate(
            data={str(field.id): "New Value"},
        ),
    )
    await db_session.commit()
    await db_session.refresh(updated_record)

    # Verify new value in database
    result = await db_session.execute(
        select(Record).where(Record.id == initial_record.id)
    )
    record = result.scalar_one()
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field.id)) == "New Value"

    # Verify operation was logged
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    update_operation = [op for op in operations[0] if op.operation_type == "update"][0]
    assert update_operation.entity_id == str(initial_record.id)

    # Verify new value is what UI would display
    assert updated_record.data == record.data

    # Step 2: Press Ctrl+Z to undo (simulate keyboard shortcut)
    undone_operation = await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_operation.id),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify old value is restored in database
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field.id)) == "Initial Value"

    # Verify UI would show old value
    assert undone_operation.id == update_operation.id

    # Step 3: Press Ctrl+Shift+Z to redo (simulate keyboard shortcut)
    redone_operation = await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_operation.id),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify new value is restored in database
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field.id)) == "New Value"

    # Verify UI would show new value
    assert redone_operation.id == update_operation.id


@pytest.mark.asyncio
async def test_undo_redo_multiple_fields_update_single_operation(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test undo/redo when updating multiple fields in a single operation."""
    # Setup: Create workspace, base, table, and multiple fields
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

    field1 = Field(
        table_id=table.id,
        name="Field 1",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field1)
    await db_session.commit()
    await db_session.refresh(field1)

    field2 = Field(
        table_id=table.id,
        name="Field 2",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field2)
    await db_session.commit()
    await db_session.refresh(field2)

    field3 = Field(
        table_id=table.id,
        name="Field 3",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field3)
    await db_session.commit()
    await db_session.refresh(field3)

    record_service = RecordService()
    undo_redo_service = UndoRedoService()

    # Create initial record
    initial_record = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={
                str(field1.id): "Value 1",
                str(field2.id): "Value 2",
                str(field3.id): "Value 3",
            },
        ),
    )
    await db_session.commit()
    await db_session.refresh(initial_record)

    # Step 1: Update all fields in single operation
    updated_record = await record_service.update_record(
        db=db_session,
        record_id=str(initial_record.id),
        user_id=str(test_user.id),
        record_data=RecordUpdate(
            data={
                str(field1.id): "New Value 1",
                str(field2.id): "New Value 2",
                str(field3.id): "New Value 3",
            },
        ),
    )
    await db_session.commit()
    await db_session.refresh(updated_record)

    # Verify all new values
    result = await db_session.execute(
        select(Record).where(Record.id == initial_record.id)
    )
    record = result.scalar_one()
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field1.id)) == "New Value 1"
    assert record_data_json.get(str(field2.id)) == "New Value 2"
    assert record_data_json.get(str(field3.id)) == "New Value 3"

    # Get the update operation
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    update_operation = [op for op in operations[0] if op.operation_type == "update"][0]

    # Step 2: Undo the update
    await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_operation.id),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify all old values are restored
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field1.id)) == "Value 1"
    assert record_data_json.get(str(field2.id)) == "Value 2"
    assert record_data_json.get(str(field3.id)) == "Value 3"

    # Step 3: Redo the update
    await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_operation.id),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify all new values are restored
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field1.id)) == "New Value 1"
    assert record_data_json.get(str(field2.id)) == "New Value 2"
    assert record_data_json.get(str(field3.id)) == "New Value 3"


@pytest.mark.asyncio
async def test_undo_redo_partial_field_update(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test undo/redo when updating only some fields of a record."""
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

    field1 = Field(
        table_id=table.id,
        name="Field 1",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field1)
    await db_session.commit()
    await db_session.refresh(field1)

    field2 = Field(
        table_id=table.id,
        name="Field 2",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field2)
    await db_session.commit()
    await db_session.refresh(field2)

    record_service = RecordService()
    undo_redo_service = UndoRedoService()

    # Create initial record with both fields
    initial_record = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={
                str(field1.id): "Value 1",
                str(field2.id): "Value 2",
            },
        ),
    )
    await db_session.commit()
    await db_session.refresh(initial_record)

    # Step 1: Update only field1 (partial update)
    updated_record = await record_service.update_record(
        db=db_session,
        record_id=str(initial_record.id),
        user_id=str(test_user.id),
        record_data=RecordUpdate(
            data={str(field1.id): "Updated Value 1"},
        ),
    )
    await db_session.commit()
    await db_session.refresh(updated_record)

    # Verify field1 updated, field2 unchanged
    result = await db_session.execute(
        select(Record).where(Record.id == initial_record.id)
    )
    record = result.scalar_one()
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field1.id)) == "Updated Value 1"
    assert record_data_json.get(str(field2.id)) == "Value 2"

    # Get the update operation
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    update_operation = [op for op in operations[0] if op.operation_type == "update"][0]

    # Step 2: Undo the partial update
    await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_operation.id),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify field1 reverted, field2 unchanged
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field1.id)) == "Value 1"
    assert record_data_json.get(str(field2.id)) == "Value 2"

    # Step 3: Redo the partial update
    await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_operation.id),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify field1 updated again, field2 still unchanged
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field1.id)) == "Updated Value 1"
    assert record_data_json.get(str(field2.id)) == "Value 2"


@pytest.mark.asyncio
async def test_undo_redo_multiple_update_cycles(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test multiple update/undo/redo cycles on the same field."""
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

    # Create initial record
    record = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Initial"},
        ),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Cycle 1: Update to "Value 1"
    await record_service.update_record(
        db=db_session,
        record_id=str(record.id),
        user_id=str(test_user.id),
        record_data=RecordUpdate(data={str(field.id): "Value 1"}),
    )
    await db_session.commit()

    # Cycle 2: Update to "Value 2"
    await record_service.update_record(
        db=db_session,
        record_id=str(record.id),
        user_id=str(test_user.id),
        record_data=RecordUpdate(data={str(field.id): "Value 2"}),
    )
    await db_session.commit()

    # Cycle 3: Update to "Value 3"
    await record_service.update_record(
        db=db_session,
        record_id=str(record.id),
        user_id=str(test_user.id),
        record_data=RecordUpdate(data={str(field.id): "Value 3"}),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify current value is "Value 3"
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field.id)) == "Value 3"

    # Get all update operations (most recent first)
    operations, _ = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    update_ops = [op for op in operations if op.operation_type == "update"]
    assert len(update_ops) == 3

    # Undo most recent (Value 3 -> Value 2)
    await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_ops[0].id),
    )
    await db_session.commit()
    await db_session.refresh(record)
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field.id)) == "Value 2"

    # Undo again (Value 2 -> Value 1)
    await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_ops[1].id),
    )
    await db_session.commit()
    await db_session.refresh(record)
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field.id)) == "Value 1"

    # Redo (Value 1 -> Value 2)
    await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_ops[1].id),
    )
    await db_session.commit()
    await db_session.refresh(record)
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field.id)) == "Value 2"

    # Redo again (Value 2 -> Value 3)
    await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_ops[0].id),
    )
    await db_session.commit()
    await db_session.refresh(record)
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field.id)) == "Value 3"


@pytest.mark.asyncio
async def test_undo_redo_update_different_field_types(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test undo/redo for updates on different field types."""
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

    # Create different field types
    text_field = Field(
        table_id=table.id,
        name="Text Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(text_field)
    await db_session.commit()
    await db_session.refresh(text_field)

    number_field = Field(
        table_id=table.id,
        name="Number Field",
        field_type=FieldType.NUMBER.value,
    )
    db_session.add(number_field)
    await db_session.commit()
    await db_session.refresh(number_field)

    email_field = Field(
        table_id=table.id,
        name="Email Field",
        field_type=FieldType.EMAIL.value,
    )
    db_session.add(email_field)
    await db_session.commit()
    await db_session.refresh(email_field)

    record_service = RecordService()
    undo_redo_service = UndoRedoService()

    # Create initial record
    record = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={
                str(text_field.id): "Original Text",
                str(number_field.id): 100,
                str(email_field.id): "old@example.com",
            },
        ),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Update all fields
    await record_service.update_record(
        db=db_session,
        record_id=str(record.id),
        user_id=str(test_user.id),
        record_data=RecordUpdate(
            data={
                str(text_field.id): "Updated Text",
                str(number_field.id): 200,
                str(email_field.id): "new@example.com",
            },
        ),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify new values
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(text_field.id)) == "Updated Text"
    assert record_data_json.get(str(number_field.id)) == 200
    assert record_data_json.get(str(email_field.id)) == "new@example.com"

    # Get the update operation
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    update_operation = [op for op in operations[0] if op.operation_type == "update"][0]

    # Undo
    await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_operation.id),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify all field types restored correctly
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(text_field.id)) == "Original Text"
    assert record_data_json.get(str(number_field.id)) == 100
    assert record_data_json.get(str(email_field.id)) == "old@example.com"

    # Redo
    await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_operation.id),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify all field types updated correctly
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(text_field.id)) == "Updated Text"
    assert record_data_json.get(str(number_field.id)) == 200
    assert record_data_json.get(str(email_field.id)) == "new@example.com"


@pytest.mark.asyncio
async def test_undo_redo_update_preserves_record_metadata(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that undo/redo of updates preserves record metadata like timestamps."""
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
            data={str(field.id): "Initial"},
        ),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Store metadata
    original_created_at = record.created_at
    original_created_by_id = record.created_by_id

    # Update record
    await record_service.update_record(
        db=db_session,
        record_id=str(record.id),
        user_id=str(test_user.id),
        record_data=RecordUpdate(data={str(field.id): "Updated"}),
    )
    await db_session.commit()
    await db_session.refresh(record)

    updated_at = record.updated_at

    # Get the update operation
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    update_operation = [op for op in operations[0] if op.operation_type == "update"][0]

    # Undo
    await undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_operation.id),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify metadata preserved
    assert record.created_at == original_created_at
    assert record.created_by_id == original_created_by_id

    # Redo
    await undo_redo_service.redo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=str(update_operation.id),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify metadata still preserved
    assert record.created_at == original_created_at
    assert record.created_by_id == original_created_by_id
    assert record.updated_at >= updated_at  # updated_at may change
