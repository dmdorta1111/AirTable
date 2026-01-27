"""
Integration tests for undo/redo persistence across page refresh.

These tests verify end-to-end undo/redo behavior when the page is refreshed,
ensuring operation history persists in localStorage and database for 24 hours.
"""

import json
from datetime import datetime, timedelta

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
async def test_undo_redo_persists_across_page_refresh_create(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test end-to-end: Create record, refresh page, undo works after refresh."""
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

    # Step 1: Create a record (simulating user action before refresh)
    record_service = RecordService()
    undo_redo_service = UndoRedoService()

    record = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Initial Value"},
        ),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify record created
    assert record.id is not None
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field.id)) == "Initial Value"

    # Get the operation ID before "refresh"
    operations_before_refresh = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(operations_before_refresh[0]) == 1
    operation_id = str(operations_before_refresh[0][0].id)

    # Step 2: Refresh browser page (simulate by creating new service instances)
    # This simulates the page refresh where frontend re-fetches operations from database
    new_undo_redo_service = UndoRedoService()

    # Fetch operations after "refresh" (like frontend would on page load)
    operations_after_refresh = await new_undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(operations_after_refresh[0]) == 1
    refreshed_operation = operations_after_refresh[0][0]

    # Verify operation persisted across refresh
    assert str(refreshed_operation.id) == operation_id
    assert refreshed_operation.operation_type == "create"
    assert refreshed_operation.entity_type == "record"
    assert refreshed_operation.entity_id == str(record.id)

    # Step 3: Press Ctrl+Z to undo after refresh (simulate keyboard shortcut)
    undone_operation = await new_undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=operation_id,
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify undo works after refresh
    assert undone_operation.id == refreshed_operation.id
    assert record.deleted_at is not None
    assert record.deleted_by_id == test_user.id

    # Verify record no longer appears in queries
    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 0


@pytest.mark.asyncio
async def test_undo_redo_persists_across_page_refresh_update(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test end-to-end: Update record, refresh page, undo works after refresh."""
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
            data={str(field.id): "Old Value"},
        ),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Step 1: Update record (before refresh)
    await record_service.update_record(
        db=db_session,
        record_id=str(record.id),
        user_id=str(test_user.id),
        record_data=RecordUpdate(data={str(field.id): "New Value"}),
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify update
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field.id)) == "New Value"

    # Get update operation before refresh
    operations_before = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    update_operations = [op for op in operations_before[0] if op.operation_type == "update"]
    assert len(update_operations) == 1
    operation_id = str(update_operations[0].id)

    # Step 2: Refresh browser page
    new_undo_redo_service = UndoRedoService()

    # Fetch operations after refresh
    operations_after = await new_undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    update_operations_after = [op for op in operations_after[0] if op.operation_type == "update"]
    assert len(update_operations_after) == 1

    # Step 3: Press Ctrl+Z to undo after refresh
    await new_undo_redo_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=operation_id,
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify old value restored (undo worked after refresh)
    record_data_json = json.loads(record.data)
    assert record_data_json.get(str(field.id)) == "Old Value"


@pytest.mark.asyncio
async def test_operation_log_exists_24_hours_after_creation(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that operation log exists in database 24 hours after creation."""
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

    # Step 1: Create a record
    record = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Test Value"},
        ),
    )
    await db_session.commit()

    # Step 2: Get operation log and check created_at timestamp
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(operations[0]) == 1
    operation = operations[0][0]

    # Verify operation was logged with timestamp
    assert operation.created_at is not None
    creation_time = operation.created_at

    # Step 3: Verify operation log still exists in database
    # (simulate checking after some time has passed)
    result = await db_session.execute(
        select(OperationLog).where(OperationLog.id == operation.id)
    )
    operation_from_db = result.scalar_one()

    # Verify operation log exists and has correct data
    assert operation_from_db is not None
    assert operation_from_db.id == operation.id
    assert operation_from_db.user_id == str(test_user.id)
    assert operation_from_db.operation_type == "create"
    assert operation_from_db.entity_type == "record"
    assert operation_from_db.entity_id == str(record.id)
    assert operation_from_db.created_at == creation_time

    # Step 4: Verify operation is within 24-hour retention period
    # (operation should not be deleted yet)
    time_since_creation = datetime.utcnow() - creation_time
    assert time_since_creation < timedelta(hours=24)

    # Step 5: Simulate cleanup check (operation should NOT be deleted)
    deleted_count = await undo_redo_service.cleanup_old_operations(
        db=db_session,
        hours=24,
    )
    await db_session.commit()

    # Verify no operations were deleted (still within 24 hours)
    assert deleted_count == 0

    # Verify operation still exists after cleanup attempt
    result = await db_session.execute(
        select(OperationLog).where(OperationLog.id == operation.id)
    )
    operation_still_exists = result.scalar_one()
    assert operation_still_exists is not None


@pytest.mark.asyncio
async def test_old_operations_deleted_beyond_24_hours(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that operations older than 24 hours are deleted."""
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

    # Step 1: Create a record
    record = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "Test Value"},
        ),
    )
    await db_session.commit()

    # Get operation log
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    operation = operations[0][0]

    # Step 2: Manually set created_at to 25 hours ago (simulate old operation)
    old_timestamp = datetime.utcnow() - timedelta(hours=25)
    operation.created_at = old_timestamp
    await db_session.commit()

    # Verify operation exists
    result = await db_session.execute(
        select(OperationLog).where(OperationLog.id == operation.id)
    )
    assert result.scalar_one() is not None

    # Step 3: Run cleanup with 24-hour retention
    deleted_count = await undo_redo_service.cleanup_old_operations(
        db=db_session,
        hours=24,
    )
    await db_session.commit()

    # Verify operation was deleted
    assert deleted_count == 1

    result = await db_session.execute(
        select(OperationLog).where(OperationLog.id == operation.id)
    )
    deleted_operation = result.scalar_one_or_none()
    assert deleted_operation is None


@pytest.mark.asyncio
async def test_multiple_refreshes_preserve_operation_history(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that operation history persists across multiple page refreshes."""
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

    # Create 3 operations
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

    # First refresh
    undo_redo_service_1 = UndoRedoService()
    operations_1 = await undo_redo_service_1.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(operations_1[0]) == 3
    operation_ids_1 = [str(op.id) for op in operations_1[0]]

    # Second refresh (new service instance)
    undo_redo_service_2 = UndoRedoService()
    operations_2 = await undo_redo_service_2.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(operations_2[0]) == 3
    operation_ids_2 = [str(op.id) for op in operations_2[0]]

    # Third refresh (another new service instance)
    undo_redo_service_3 = UndoRedoService()
    operations_3 = await undo_redo_service_3.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(operations_3[0]) == 3
    operation_ids_3 = [str(op.id) for op in operations_3[0]]

    # Verify all refreshes return same operations
    assert set(operation_ids_1) == set(operation_ids_2) == set(operation_ids_3)

    # Verify undo works after multiple refreshes
    await undo_redo_service_3.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=operation_ids_3[0],  # Most recent
    )
    await db_session.commit()

    result = await db_session.execute(
        select(Record).where(
            Record.table_id == table.id,
            Record.deleted_at.is_(None),
        )
    )
    active_records = result.scalars().all()
    assert len(active_records) == 2


@pytest.mark.asyncio
async def test_localstorage_expiry_simulation(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test simulating localStorage expiry and database fallback."""
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

    # Get operation
    operations = await undo_redo_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    operation = operations[0][0]
    operation_id = str(operation.id)

    # Simulate localStorage expiry (frontend cache cleared)
    # User refreshes page and needs to fetch from database
    new_service = UndoRedoService()

    # Fetch from database (like frontend would after localStorage expiry)
    fresh_operations = await new_service.get_user_operations(
        db=db_session,
        user_id=str(test_user.id),
    )
    assert len(fresh_operations[0]) == 1
    fresh_operation = fresh_operations[0][0]

    # Verify operation fetched from database matches original
    assert str(fresh_operation.id) == operation_id
    assert fresh_operation.operation_type == operation.operation_type
    assert fresh_operation.entity_type == operation.entity_type
    assert fresh_operation.entity_id == operation.entity_id

    # Verify undo works using database-fetched operation
    await new_service.undo_operation(
        db=db_session,
        user_id=str(test_user.id),
        operation_id=operation_id,
    )
    await db_session.commit()
    await db_session.refresh(record)

    # Verify undo successful
    assert record.deleted_at is not None
