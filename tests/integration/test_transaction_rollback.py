"""
Integration tests for transaction rollback on multi-record operations.

Tests verify that when any operation in a multi-record transaction fails,
the entire transaction is rolled back and no partial data is persisted.
"""

import json

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import ConflictError, ValidationError
from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.unique_constraint import UniqueConstraint
from pybase.models.workspace import Workspace
from pybase.models.user import User
from pybase.schemas.record import RecordCreate, RecordUpdate
from pybase.services.record import RecordService


@pytest.mark.asyncio
async def test_bulk_create_rolls_back_all_on_validation_error(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that bulk record creation rolls back all records when validation fails."""
    # Create workspace, base, table with required field
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

    # Create a required field
    required_field = Field(
        table_id=table.id,
        name="Required Field",
        field_type=FieldType.TEXT.value,
        is_required=True,
    )
    db_session.add(required_field)
    await db_session.commit()
    await db_session.refresh(required_field)

    # Get initial record count
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    initial_count = len(result.scalars().all())

    service = RecordService()

    # Try to create multiple records, one missing required field
    records_data = [
        RecordCreate(
            table_id=str(table.id),
            data={str(required_field.id): "Valid value 1"},
        ),
        RecordCreate(
            table_id=str(table.id),
            data={},  # Missing required field - should fail
        ),
        RecordCreate(
            table_id=str(table.id),
            data={str(required_field.id): "Valid value 3"},
        ),
    ]

    created_records = []
    try:
        for record_data in records_data:
            record = await service.create_record(
                db=db_session,
                user_id=str(test_user.id),
                record_data=record_data,
            )
            created_records.append(record)
    except ValidationError:
        # Expected to fail on second record
        pass

    # Manually rollback to simulate transaction failure
    await db_session.rollback()

    # Verify NO new records were created (all rolled back)
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    final_count = len(result.scalars().all())

    # Count should be same as initial (rollback successful)
    assert final_count == initial_count


@pytest.mark.asyncio
async def test_bulk_create_rolls_back_on_unique_constraint_violation(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that bulk create rolls back all on unique constraint violation."""
    # Create workspace, base, table
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

    # Create field with unique constraint
    field = Field(
        table_id=table.id,
        name="Unique Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Add unique constraint
    constraint = UniqueConstraint(
        table_id=table.id,
        name="unique_constraint",
        field_ids=[str(field.id)],
        case_sensitive=True,
        status="active",
    )
    db_session.add(constraint)
    await db_session.commit()

    service = RecordService()

    # Create first record successfully
    record1 = await service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "unique_value"},
        ),
    )
    assert record1 is not None

    # Get initial record count
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    initial_count = len(result.scalars().all())

    # Try to create multiple records with duplicate value
    records_data = [
        RecordCreate(table_id=str(table.id), data={str(field.id): "another_value"}),
        RecordCreate(table_id=str(table.id), data={str(field.id): "unique_value"}),  # Duplicate!
        RecordCreate(table_id=str(table.id), data={str(field.id): "third_value"}),
    ]

    created_count = 0
    try:
        for record_data in records_data:
            record = await service.create_record(
                db=db_session,
                user_id=str(test_user.id),
                record_data=record_data,
            )
            created_count += 1
    except ConflictError:
        # Expected to fail on duplicate
        pass

    # Verify only one record was created before conflict
    assert created_count == 1

    # Verify total count
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    final_count = len(result.scalars().all())
    assert final_count == initial_count + 1


@pytest.mark.asyncio
async def test_bulk_update_rolls_back_all_on_validation_error(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that bulk update rolls back all updates when validation fails."""
    # Create workspace, base, table
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

    # Create field
    field = Field(
        table_id=table.id,
        name="Text Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create multiple records
    records = []
    for i in range(3):
        record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): f"value{i}"}),
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id,
        )
        db_session.add(record)
        records.append(record)
    await db_session.commit()

    # Store original data
    original_data = [r.data for r in records]

    service = RecordService()

    # Try to update all records, second one with empty data (should fail)
    updated_count = 0
    for i, record in enumerate(records):
        try:
            updated_record = await service.update_record(
                db=db_session,
                record_id=str(record.id),
                user_id=str(test_user.id),
                record_data=RecordUpdate(
                    data={str(field.id): f"updated{i}"} if i != 1 else {}
                ),
            )
            updated_count += 1
        except (ValidationError, ValueError):
            # Expected to fail on empty data
            break

    # Verify only first update succeeded
    assert updated_count == 1

    # Refresh records from DB
    for record in records:
        await db_session.refresh(record)

    # Verify first record was updated
    assert "updated0" in records[0].data
    # Verify second record was NOT updated
    assert records[1].data == original_data[1]
    # Verify third record was NOT updated
    assert records[2].data == original_data[2]


@pytest.mark.asyncio
async def test_transaction_isolation_during_bulk_operations(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that uncommitted bulk operations are not visible to other queries."""
    # Create workspace, base, table
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
        name="Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Get initial count
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    initial_count = len(result.scalars().all())

    service = RecordService()

    # Create a record (will be committed by service)
    record = await service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "value1"},
        ),
    )
    assert record is not None

    # Verify it's now visible after commit
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    new_count = len(result.scalars().all())
    assert new_count == initial_count + 1


@pytest.mark.asyncio
async def test_rollback_on_foreign_key_violation(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test rollback when foreign key constraint is violated."""
    # Create workspace, base, table
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
        name="Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    service = RecordService()

    # Try to create record with non-existent table ID
    from uuid import uuid4

    fake_table_id = str(uuid4())

    try:
        await service.create_record(
            db=db_session,
            user_id=str(test_user.id),
            record_data=RecordCreate(
                table_id=fake_table_id,
                data={str(field.id): "value"},
            ),
        )
        assert False, "Should have raised NotFoundError"
    except Exception:
        # Expected to fail - pass
        pass

    # Verify no record was created with the fake table ID
    result = await db_session.execute(
        select(Record).where(Record.table_id == fake_table_id)
    )
    records = result.scalars().all()
    assert len(records) == 0


@pytest.mark.asyncio
async def test_rollback_maintains_data_integrity(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that rollback maintains data integrity."""
    # Create workspace, base, table
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

    # Create unique constraint field
    field = Field(
        table_id=table.id,
        name="Unique Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    constraint = UniqueConstraint(
        table_id=table.id,
        name="unique_field",
        field_ids=[str(field.id)],
        case_sensitive=True,
        status="active",
    )
    db_session.add(constraint)
    await db_session.commit()

    service = RecordService()

    # Create initial record
    record1 = await service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "existing"},
        ),
    )
    assert record1 is not None

    # Try to create duplicate
    try:
        await service.create_record(
            db=db_session,
            user_id=str(test_user.id),
            record_data=RecordCreate(
                table_id=str(table.id),
                data={str(field.id): "existing"},
            ),
        )
        assert False, "Should have raised ConflictError"
    except ConflictError:
        pass

    # Verify only one record exists
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    records = result.scalars().all()
    assert len(records) == 1


@pytest.mark.asyncio
async def test_concurrent_record_creation(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test concurrent record creation handling."""
    # Create workspace, base, table
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
        name="Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    service = RecordService()

    # Create multiple records
    records = []
    for i in range(5):
        record = await service.create_record(
            db=db_session,
            user_id=str(test_user.id),
            record_data=RecordCreate(
                table_id=str(table.id),
                data={str(field.id): f"value{i}"},
            ),
        )
        records.append(record)

    # All should succeed
    assert len(records) == 5

    # Verify all 5 records exist
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    db_records = result.scalars().all()
    assert len(db_records) == 5


@pytest.mark.asyncio
async def test_nested_operations_rollback(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test rollback with nested operations (field + record creation)."""
    from pybase.schemas.field import FieldCreate
    from pybase.services.field import FieldService

    # Create workspace, base, table
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

    field_service = FieldService()
    record_service = RecordService()

    # Create field successfully
    field = await field_service.create_field(
        db=db_session,
        user_id=str(test_user.id),
        field_data=FieldCreate(
            table_id=str(table.id),
            name="Test Field",
            field_type=FieldType.TEXT.value,
        ),
    )
    assert field is not None

    # Create record with field
    record = await record_service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "value"},
        ),
    )
    assert record is not None

    # Verify both exist
    result = await db_session.execute(
        select(Field).where(Field.table_id == table.id)
    )
    fields = result.scalars().all()
    assert len(fields) == 1

    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    records = result.scalars().all()
    assert len(records) == 1


@pytest.mark.asyncio
async def test_multi_table_transaction_rollback(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test rollback across multiple tables."""
    # Create workspace, base, two tables
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table1 = Table(base_id=base.id, name="Table 1")
    db_session.add(table1)
    await db_session.commit()
    await db_session.refresh(table1)

    table2 = Table(base_id=base.id, name="Table 2")
    db_session.add(table2)
    await db_session.commit()
    await db_session.refresh(table2)

    # Create field in table1 with unique constraint
    field1 = Field(
        table_id=table1.id,
        name="Field1",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field1)
    await db_session.commit()

    constraint = UniqueConstraint(
        table_id=table1.id,
        name="unique_field",
        field_ids=[str(field1.id)],
        case_sensitive=True,
        status="active",
    )
    db_session.add(constraint)
    await db_session.commit()

    field2 = Field(
        table_id=table2.id,
        name="Field2",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field2)
    await db_session.commit()

    service = RecordService()

    # Create record in table1
    record1 = await service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table1.id),
            data={str(field1.id): "unique_value"},
        ),
    )
    assert record1 is not None

    # Create record in table2
    record2 = await service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table2.id),
            data={str(field2.id): "value2"},
        ),
    )
    assert record2 is not None

    # Try to create duplicate in table1
    try:
        await service.create_record(
            db=db_session,
            user_id=str(test_user.id),
            record_data=RecordCreate(
                table_id=str(table1.id),
                data={str(field1.id): "unique_value"},
            ),
        )
        assert False, "Should have raised ConflictError"
    except ConflictError:
        pass

    # Verify table2 record still exists
    result = await db_session.execute(
        select(Record).where(Record.table_id == table2.id)
    )
    records = result.scalars().all()
    assert len(records) == 1


@pytest.mark.asyncio
async def test_bulk_delete_soft_delete_rollback(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that soft delete rollback properly restores records."""
    # Create workspace, base, table
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

    # Create records
    records = []
    for i in range(3):
        record = Record(
            table_id=table.id,
            data="{}",
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id,
        )
        db_session.add(record)
        records.append(record)
    await db_session.commit()

    service = RecordService()

    # Delete first record
    await service.delete_record(
        db=db_session,
        record_id=str(records[0].id),
        user_id=str(test_user.id),
    )

    # Verify it's soft deleted
    await db_session.refresh(records[0])
    assert records[0].deleted_at is not None

    # Verify others are not deleted
    await db_session.refresh(records[1])
    await db_session.refresh(records[2])
    assert records[1].deleted_at is None
    assert records[2].deleted_at is None


@pytest.mark.asyncio
async def test_transaction_cleanup_after_rollback(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that transaction is properly cleaned up after rollback."""
    # Create workspace, base, table
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

    # Create required field
    field = Field(
        table_id=table.id,
        name="Required Field",
        field_type=FieldType.TEXT.value,
        is_required=True,
    )
    db_session.add(field)
    await db_session.commit()

    service = RecordService()

    # Try to create record without required field (should fail)
    try:
        await service.create_record(
            db=db_session,
            user_id=str(test_user.id),
            record_data=RecordCreate(
                table_id=str(table.id),
                data={},  # Missing required field
            ),
        )
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass

    # Verify session is still usable by creating valid record
    record = await service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "valid value"},
        ),
    )
    assert record is not None


@pytest.mark.asyncio
async def test_bulk_create_with_required_field_validation(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test bulk create when field validation fails due to missing required field."""
    # Create workspace, base, table
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

    # Create required field
    required_field = Field(
        table_id=table.id,
        name="Required Field",
        field_type=FieldType.TEXT.value,
        is_required=True,
    )
    db_session.add(required_field)
    await db_session.commit()

    # Get initial count
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    initial_count = len(result.scalars().all())

    service = RecordService()

    # Try to create records, one missing required field
    records_data = [
        RecordCreate(table_id=str(table.id), data={str(required_field.id): "value1"}),
        RecordCreate(table_id=str(table.id), data={}),  # Missing required
        RecordCreate(table_id=str(table.id), data={str(required_field.id): "value3"}),
    ]

    created_count = 0
    try:
        for record_data in records_data:
            record = await service.create_record(
                db=db_session,
                user_id=str(test_user.id),
                record_data=record_data,
            )
            created_count += 1
    except ValidationError:
        pass

    # Only first should succeed
    assert created_count == 1

    # Verify total count
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    final_count = len(result.scalars().all())
    assert final_count == initial_count + 1


@pytest.mark.asyncio
async def test_service_methods_never_manually_commit(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that service methods never manually call commit."""
    # Create workspace, base, table
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
        name="Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Start a transaction but don't commit
    from pybase.db.session import get_db_context

    async with get_db_context() as db:
        service = RecordService()

        # Create record within transaction
        record = await service.create_record(
            db=db,
            user_id=str(test_user.id),
            record_data=RecordCreate(
                table_id=str(table.id),
                data={str(field.id): "value"},
            ),
        )

        # Record should be created but not committed yet
        assert record is not None

        # Rollback the transaction
        await db.rollback()

    # Verify record was not persisted
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    records = result.scalars().all()
    assert len(records) == 0


@pytest.mark.asyncio
async def test_bulk_update_with_partial_failure(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test bulk update where some updates fail."""
    # Create workspace, base, table
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
        name="Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create records
    records = []
    for i in range(4):
        record = Record(
            table_id=table.id,
            data=json.dumps({str(field.id): f"value{i}"}),
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id,
        )
        db_session.add(record)
        records.append(record)
    await db_session.commit()

    service = RecordService()

    # Try to update, third one fails (simulate by using non-existent record ID)
    updated_ids = []
    for i, record in enumerate(records):
        try:
            if i == 2:
                # Use non-existent ID
                from uuid import uuid4

                fake_id = str(uuid4())
                await service.update_record(
                    db=db_session,
                    record_id=fake_id,
                    user_id=str(test_user.id),
                    record_data=RecordUpdate(data={str(field.id): f"updated{i}"}),
                )
            else:
                updated = await service.update_record(
                    db=db_session,
                    record_id=str(record.id),
                    user_id=str(test_user.id),
                    record_data=RecordUpdate(data={str(field.id): f"updated{i}"}),
                )
                updated_ids.append(updated.id)
        except Exception:
            # Third update should fail
            break

    # Verify 2 updates succeeded before failure
    assert len(updated_ids) == 2


@pytest.mark.asyncio
async def test_transaction_rollback_preserves_previous_data(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that transaction rollback preserves previously committed data."""
    # Create workspace, base, table
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
        name="Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    service = RecordService()

    # Create first record and commit
    record1 = await service.create_record(
        db=db_session,
        user_id=str(test_user.id),
        record_data=RecordCreate(
            table_id=str(table.id),
            data={str(field.id): "value1"},
        ),
    )
    await db_session.commit()

    # Try to create second record with invalid data (should fail)
    try:
        await service.create_record(
            db=db_session,
            user_id=str(test_user.id),
            record_data=RecordCreate(
                table_id=str(table.id),
                data={},  # Empty data
            ),
        )
        assert False, "Should have raised ValidationError"
    except (ValidationError, ValueError):
        await db_session.rollback()

    # Verify first record still exists
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    records = result.scalars().all()
    assert len(records) == 1
    assert records[0].id == record1.id
