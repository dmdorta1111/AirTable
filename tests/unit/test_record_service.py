"""
Unit tests for RecordService filter and search functionality.
"""

from uuid import uuid4
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.models.user import User
from pybase.services.record import RecordService
from pybase.schemas.view import FilterCondition, FilterOperator, Conjunction


@pytest.mark.asyncio
async def test_filter_records_by_equals(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test filtering records with equals operator."""
    # Create workspace, base, and table
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(
        workspace_id=workspace.id,
        name="Test Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Test Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create a text field
    field = Field(
        table_id=table.id,
        name="Status",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create records with different status values
    record1 = Record(
        table_id=table.id,
        data=f'{{"{field.id}": "active"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record1)

    record2 = Record(
        table_id=table.id,
        data=f'{{"{field.id}": "inactive"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record2)

    record3 = Record(
        table_id=table.id,
        data=f'{{"{field.id}": "active"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record3)

    await db_session.commit()

    # Test filtering with equals operator
    service = RecordService()
    filters = [
        FilterCondition(
            field_id=field.id,
            operator=FilterOperator.EQUALS,
            value="active",
        )
    ]

    result = await service.list_records_cursor(
        db=db_session,
        table_id=table.id,
        user_id=str(test_user.id),
        page_size=20,
        filters=filters,
    )

    assert len(result["records"]) == 2
    assert result["has_more"] is False
    # Verify all returned records have status="active"
    for record in result["records"]:
        import json
        data = json.loads(record.data)
        assert data[str(field.id)] == "active"


@pytest.mark.asyncio
async def test_filter_records_by_contains(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test filtering records with contains operator."""
    # Create workspace, base, and table
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(
        workspace_id=workspace.id,
        name="Test Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Test Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create a text field
    field = Field(
        table_id=table.id,
        name="Description",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create records
    record1 = Record(
        table_id=table.id,
        data=f'{{"{field.id}": "Apple iPhone 15"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record1)

    record2 = Record(
        table_id=table.id,
        data=f'{{"{field.id}": "Samsung Galaxy"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record2)

    record3 = Record(
        table_id=table.id,
        data=f'{{"{field.id}": "Apple MacBook"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record3)

    await db_session.commit()

    # Test filtering with contains operator
    service = RecordService()
    filters = [
        FilterCondition(
            field_id=field.id,
            operator=FilterOperator.CONTAINS,
            value="Apple",
        )
    ]

    result = await service.list_records_cursor(
        db=db_session,
        table_id=table.id,
        user_id=str(test_user.id),
        page_size=20,
        filters=filters,
    )

    assert len(result["records"]) == 2
    assert result["has_more"] is False


@pytest.mark.asyncio
async def test_filter_records_by_greater_than(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test filtering records with greater than operator."""
    # Create workspace, base, and table
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(
        workspace_id=workspace.id,
        name="Test Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Test Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create a number field
    field = Field(
        table_id=table.id,
        name="Price",
        field_type=FieldType.NUMBER.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create records with different prices
    for price in [10, 25, 50, 75, 100]:
        record = Record(
            table_id=table.id,
            data=f'{{"{field.id}": {price}}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id,
        )
        db_session.add(record)

    await db_session.commit()

    # Test filtering with greater than operator
    service = RecordService()
    filters = [
        FilterCondition(
            field_id=field.id,
            operator=FilterOperator.GREATER_THAN,
            value=50,
        )
    ]

    result = await service.list_records_cursor(
        db=db_session,
        table_id=table.id,
        user_id=str(test_user.id),
        page_size=20,
        filters=filters,
    )

    assert len(result["records"]) == 2  # 75 and 100
    assert result["has_more"] is False


@pytest.mark.asyncio
async def test_filter_records_by_is_empty(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test filtering records with is_empty operator."""
    # Create workspace, base, and table
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(
        workspace_id=workspace.id,
        name="Test Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Test Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create a text field
    field = Field(
        table_id=table.id,
        name="Notes",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create records - some with empty notes
    record1 = Record(
        table_id=table.id,
        data=f'{{"{field.id}": "Some notes"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record1)

    record2 = Record(
        table_id=table.id,
        data='{}',  # Empty data
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record2)

    record3 = Record(
        table_id=table.id,
        data=f'{{"{field.id}": ""}}',  # Empty string
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record3)

    await db_session.commit()

    # Test filtering with is_empty operator
    service = RecordService()
    filters = [
        FilterCondition(
            field_id=field.id,
            operator=FilterOperator.IS_EMPTY,
            value=None,
        )
    ]

    result = await service.list_records_cursor(
        db=db_session,
        table_id=table.id,
        user_id=str(test_user.id),
        page_size=20,
        filters=filters,
    )

    assert len(result["records"]) == 2  # record2 and record3
    assert result["has_more"] is False


@pytest.mark.asyncio
async def test_search_records(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test searching records with full-text search."""
    # Create workspace, base, and table
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(
        workspace_id=workspace.id,
        name="Test Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Test Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create fields
    name_field = Field(
        table_id=table.id,
        name="Name",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(name_field)
    await db_session.commit()
    await db_session.refresh(name_field)

    desc_field = Field(
        table_id=table.id,
        name="Description",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(desc_field)
    await db_session.commit()
    await db_session.refresh(desc_field)

    # Create records
    record1 = Record(
        table_id=table.id,
        data=f'{{"{name_field.id}": "iPhone 15", "{desc_field.id}": "Latest Apple smartphone"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record1)

    record2 = Record(
        table_id=table.id,
        data=f'{{"{name_field.id}": "Samsung Galaxy", "{desc_field.id}": "Android phone"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record2)

    record3 = Record(
        table_id=table.id,
        data=f'{{"{name_field.id}": "MacBook Pro", "{desc_field.id}": "Apple laptop"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record3)

    await db_session.commit()

    # Test searching for "Apple"
    service = RecordService()
    result = await service.search_records(
        db=db_session,
        table_id=table.id,
        user_id=str(test_user.id),
        search_query="Apple",
        page_size=20,
    )

    assert len(result["records"]) == 2  # iPhone and MacBook
    assert result["total_matches"] == 2
    assert result["has_more"] is False


@pytest.mark.asyncio
async def test_search_with_filters(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test searching records with both search query and filters."""
    # Create workspace, base, and table
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(
        workspace_id=workspace.id,
        name="Test Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Test Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create fields
    name_field = Field(
        table_id=table.id,
        name="Name",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(name_field)
    await db_session.commit()
    await db_session.refresh(name_field)

    status_field = Field(
        table_id=table.id,
        name="Status",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(status_field)
    await db_session.commit()
    await db_session.refresh(status_field)

    # Create records
    record1 = Record(
        table_id=table.id,
        data=f'{{"{name_field.id}": "Apple iPhone", "{status_field.id}": "active"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record1)

    record2 = Record(
        table_id=table.id,
        data=f'{{"{name_field.id}": "Apple iPad", "{status_field.id}": "inactive"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record2)

    record3 = Record(
        table_id=table.id,
        data=f'{{"{name_field.id}": "Samsung Galaxy", "{status_field.id}": "active"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record3)

    await db_session.commit()

    # Test searching for "Apple" with status="active" filter
    service = RecordService()
    filters = [
        FilterCondition(
            field_id=status_field.id,
            operator=FilterOperator.EQUALS,
            value="active",
        )
    ]

    result = await service.search_records(
        db=db_session,
        table_id=table.id,
        user_id=str(test_user.id),
        search_query="Apple",
        filters=filters,
        page_size=20,
    )

    assert len(result["records"]) == 1  # Only iPhone (active)
    assert result["total_matches"] == 1
    assert result["has_more"] is False


@pytest.mark.asyncio
async def test_filter_with_cursor_pagination(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that filters work correctly with cursor-based pagination."""
    # Create workspace, base, and table
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(
        workspace_id=workspace.id,
        name="Test Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Test Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create a status field
    field = Field(
        table_id=table.id,
        name="Status",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create 30 records - 15 active, 15 inactive
    for i in range(30):
        status = "active" if i % 2 == 0 else "inactive"
        record = Record(
            table_id=table.id,
            data=f'{{"{field.id}": "{status}"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id,
        )
        db_session.add(record)

    await db_session.commit()

    # Test cursor pagination with filter
    service = RecordService()
    filters = [
        FilterCondition(
            field_id=field.id,
            operator=FilterOperator.EQUALS,
            value="active",
        )
    ]

    # Get first page
    page1 = await service.list_records_cursor(
        db=db_session,
        table_id=table.id,
        user_id=str(test_user.id),
        page_size=10,
        filters=filters,
    )

    assert len(page1["records"]) == 10
    assert page1["has_more"] is True
    assert page1["next_cursor"] is not None

    # Get second page
    page2 = await service.list_records_cursor(
        db=db_session,
        table_id=table.id,
        user_id=str(test_user.id),
        cursor=page1["next_cursor"],
        page_size=10,
        filters=filters,
    )

    assert len(page2["records"]) == 5  # Remaining 5 active records
    assert page2["has_more"] is False
    assert page2["next_cursor"] is None


@pytest.mark.asyncio
async def test_filter_records_permission_denied(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that filters respect workspace permissions."""
    # Create workspace as test_user
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(
        workspace_id=workspace.id,
        name="Test Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Test Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    field = Field(
        table_id=table.id,
        name="Status",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create some records
    for i in range(5):
        record = Record(
            table_id=table.id,
            data=f'{{"{field.id}": "active"}}',
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id,
        )
        db_session.add(record)

    await db_session.commit()

    # Create another user who is NOT a member of the workspace
    other_user = User(
        email="other@example.com",
        hashed_password="hashed_password",
        full_name="Other User",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    # Try to filter records as non-member
    service = RecordService()
    filters = [
        FilterCondition(
            field_id=field.id,
            operator=FilterOperator.EQUALS,
            value="active",
        )
    ]

    with pytest.raises(Exception) as exc_info:
        await service.list_records_cursor(
            db=db_session,
            table_id=table.id,
            user_id=str(other_user.id),
            page_size=20,
            filters=filters,
        )

    assert "don't have access" in str(exc_info.value).lower()
