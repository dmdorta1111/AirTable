"""
Unit tests for ViewService business logic.
"""

import json
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.user import User
from pybase.models.view import View, ViewType
from pybase.schemas.view import RowHeight
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.services.view import ViewService


@pytest.fixture
def view_service():
    """Create an instance of ViewService."""
    return ViewService()


@pytest_asyncio.fixture
async def test_workspace(db_session: AsyncSession, test_user: User) -> Workspace:
    """Create a test workspace with user as owner."""
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
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
    """Create a test base."""
    base = Base(
        workspace_id=test_workspace.id,
        name="Test Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def test_table(db_session: AsyncSession, test_base: Base) -> Table:
    """Create a test table."""
    table = Table(
        base_id=test_base.id,
        name="Test Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)
    return table


@pytest_asyncio.fixture
async def test_fields(db_session: AsyncSession, test_table: Table) -> list[Field]:
    """Create test fields."""
    fields = [
        Field(
            table_id=test_table.id,
            name="Name",
            field_type=FieldType.TEXT.value,
            is_required=False,
        ),
        Field(
            table_id=test_table.id,
            name="Age",
            field_type=FieldType.NUMBER.value,
            is_required=False,
        ),
        Field(
            table_id=test_table.id,
            name="Status",
            field_type=FieldType.SELECT.value,
            is_required=False,
        ),
    ]
    for field in fields:
        db_session.add(field)
    await db_session.commit()
    for field in fields:
        await db_session.refresh(field)
    return fields


@pytest_asyncio.fixture
async def test_view(
    db_session: AsyncSession, test_table: Table, test_user: User
) -> View:
    """Create a test view."""
    view = View(
        table_id=str(test_table.id),
        created_by_id=str(test_user.id),
        name="Test View",
        view_type=ViewType.GRID.value,
        is_default=True,
        row_height=RowHeight.MEDIUM.value,
        filters="[]",
        sorts="[]",
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)
    return view


@pytest_asyncio.fixture
async def test_records(
    db_session: AsyncSession, test_table: Table, test_fields: list[Field], test_user: User
) -> list[Record]:
    """Create test records with various data."""
    records_data = [
        {"Name": "Alice", "Age": 30, "Status": "Active"},
        {"Name": "Bob", "Age": 25, "Status": "Inactive"},
        {"Name": "Charlie", "Age": 35, "Status": "Active"},
        {"Name": "David", "Age": 28, "Status": "Pending"},
        {"Name": "Eve", "Age": 32, "Status": "Active"},
    ]

    records = []
    for data in records_data:
        # Map field names to field IDs
        record_data = {}
        for field in test_fields:
            if field.name in data:
                record_data[str(field.id)] = data[field.name]

        record = Record(
            table_id=test_table.id,
            data=json.dumps(record_data),
            created_by_id=str(test_user.id),
            last_modified_by_id=str(test_user.id),
        )
        db_session.add(record)
        records.append(record)

    await db_session.commit()
    for record in records:
        await db_session.refresh(record)

    return records


@pytest.mark.asyncio
async def test_apply_filters(
    view_service: ViewService,
):
    """Test filter application logic."""
    # Test data
    records = [
        {
            "id": "1",
            "data": {"field1": "Alice", "field2": 30, "field3": "Active"},
        },
        {
            "id": "2",
            "data": {"field1": "Bob", "field2": 25, "field3": "Inactive"},
        },
        {
            "id": "3",
            "data": {"field1": "Charlie", "field2": 35, "field3": "Active"},
        },
        {
            "id": "4",
            "data": {"field1": "David", "field2": 28, "field3": "Pending"},
        },
    ]

    # Test equals filter
    filters = [{"field_id": "field3", "operator": "equals", "value": "Active", "conjunction": "and"}]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 2
    assert all(r["data"]["field3"] == "Active" for r in result)

    # Test not_equals filter
    filters = [{"field_id": "field3", "operator": "not_equals", "value": "Active", "conjunction": "and"}]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 2
    assert all(r["data"]["field3"] != "Active" for r in result)

    # Test contains filter
    filters = [{"field_id": "field1", "operator": "contains", "value": "li", "conjunction": "and"}]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 2  # Alice and Charlie
    assert all("li" in r["data"]["field1"] for r in result)

    # Test greater than filter
    filters = [{"field_id": "field2", "operator": "gt", "value": 28, "conjunction": "and"}]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 2  # 30 and 35
    assert all(r["data"]["field2"] > 28 for r in result)

    # Test less than filter
    filters = [{"field_id": "field2", "operator": "lt", "value": 30, "conjunction": "and"}]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 2  # 25 and 28
    assert all(r["data"]["field2"] < 30 for r in result)

    # Test greater than or equal filter
    filters = [{"field_id": "field2", "operator": "gte", "value": 30, "conjunction": "and"}]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 2  # 30 and 35
    assert all(r["data"]["field2"] >= 30 for r in result)

    # Test less than or equal filter
    filters = [{"field_id": "field2", "operator": "lte", "value": 28, "conjunction": "and"}]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 2  # 25 and 28
    assert all(r["data"]["field2"] <= 28 for r in result)

    # Test is_empty filter
    records_with_empty = [
        {"id": "1", "data": {"field1": "Alice", "field2": 30}},
        {"id": "2", "data": {"field1": "Bob", "field2": None}},
        {"id": "3", "data": {"field1": "", "field2": 25}},
    ]
    filters = [{"field_id": "field1", "operator": "is_empty", "value": None, "conjunction": "and"}]
    result = view_service._apply_filters(records_with_empty, filters)
    assert len(result) == 1  # Empty string

    # Test is_not_empty filter
    filters = [{"field_id": "field1", "operator": "is_not_empty", "value": None, "conjunction": "and"}]
    result = view_service._apply_filters(records_with_empty, filters)
    assert len(result) == 2  # Alice and empty string is actually not None

    # Test starts_with filter
    filters = [{"field_id": "field1", "operator": "starts_with", "value": "Al", "conjunction": "and"}]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 1
    assert result[0]["data"]["field1"] == "Alice"

    # Test ends_with filter
    filters = [{"field_id": "field1", "operator": "ends_with", "value": "ie", "conjunction": "and"}]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 1
    assert result[0]["data"]["field1"] == "Charlie"

    # Test in filter
    filters = [{"field_id": "field3", "operator": "in", "value": ["Active", "Pending"], "conjunction": "and"}]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 3  # Active (2) + Pending (1)

    # Test not_in filter
    filters = [{"field_id": "field3", "operator": "not_in", "value": ["Active"], "conjunction": "and"}]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 2  # Inactive and Pending

    # Test multiple AND filters
    filters = [
        {"field_id": "field3", "operator": "equals", "value": "Active", "conjunction": "and"},
        {"field_id": "field2", "operator": "gte", "value": 30, "conjunction": "and"},
    ]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 2  # Alice (30) and Charlie (35)

    # Test multiple OR filters
    filters = [
        {"field_id": "field1", "operator": "equals", "value": "Alice", "conjunction": "or"},
        {"field_id": "field1", "operator": "equals", "value": "Bob", "conjunction": "or"},
    ]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 2  # Only Alice and Bob match (OR condition requires at least one match)

    # Test mixed AND/OR filters
    filters = [
        {"field_id": "field3", "operator": "equals", "value": "Active", "conjunction": "and"},
        {"field_id": "field1", "operator": "equals", "value": "Alice", "conjunction": "or"},
    ]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 1  # Only Alice (must match Active AND at least one OR condition)

    # Test empty filters
    result = view_service._apply_filters(records, [])
    assert len(result) == 4  # All records


@pytest.mark.asyncio
async def test_apply_filters_not_contains(view_service: ViewService):
    """Test not_contains filter operator."""
    records = [
        {"id": "1", "data": {"field1": "Hello World"}},
        {"id": "2", "data": {"field1": "Goodbye"}},
        {"id": "3", "data": {"field1": "Hello There"}},
    ]

    filters = [{"field_id": "field1", "operator": "not_contains", "value": "World", "conjunction": "and"}]
    result = view_service._apply_filters(records, filters)
    assert len(result) == 2  # Goodbye and Hello There
    assert all("World" not in r["data"]["field1"] for r in result)


@pytest.mark.asyncio
async def test_record_matches_filters(view_service: ViewService):
    """Test individual record filter matching."""
    record = {
        "id": "1",
        "data": {"name": "Alice", "age": 30, "status": "Active"},
    }

    # Test single filter match
    filters = [{"field_id": "name", "operator": "equals", "value": "Alice", "conjunction": "and"}]
    assert view_service._record_matches_filters(record, filters) is True

    # Test single filter no match
    filters = [{"field_id": "name", "operator": "equals", "value": "Bob", "conjunction": "and"}]
    assert view_service._record_matches_filters(record, filters) is False

    # Test multiple AND filters - all match
    filters = [
        {"field_id": "name", "operator": "equals", "value": "Alice", "conjunction": "and"},
        {"field_id": "age", "operator": "gte", "value": 25, "conjunction": "and"},
    ]
    assert view_service._record_matches_filters(record, filters) is True

    # Test multiple AND filters - one fails
    filters = [
        {"field_id": "name", "operator": "equals", "value": "Alice", "conjunction": "and"},
        {"field_id": "age", "operator": "lt", "value": 25, "conjunction": "and"},
    ]
    assert view_service._record_matches_filters(record, filters) is False

    # Test OR filters - one matches
    filters = [
        {"field_id": "name", "operator": "equals", "value": "Bob", "conjunction": "or"},
        {"field_id": "age", "operator": "equals", "value": 30, "conjunction": "or"},
    ]
    assert view_service._record_matches_filters(record, filters) is True


@pytest.mark.asyncio
async def test_evaluate_filter(view_service: ViewService):
    """Test individual filter evaluation."""
    # Test equals
    assert view_service._evaluate_filter("test", "equals", "test") is True
    assert view_service._evaluate_filter("test", "equals", "other") is False

    # Test not_equals
    assert view_service._evaluate_filter("test", "not_equals", "other") is True
    assert view_service._evaluate_filter("test", "not_equals", "test") is False

    # Test contains
    assert view_service._evaluate_filter("hello world", "contains", "world") is True
    assert view_service._evaluate_filter("hello world", "contains", "test") is False

    # Test numeric comparisons
    assert view_service._evaluate_filter(30, "gt", 25) is True
    assert view_service._evaluate_filter(30, "gt", 35) is False
    assert view_service._evaluate_filter(30, "lt", 35) is True
    assert view_service._evaluate_filter(30, "gte", 30) is True
    assert view_service._evaluate_filter(30, "lte", 30) is True

    # Test is_empty
    assert view_service._evaluate_filter(None, "is_empty", None) is True
    assert view_service._evaluate_filter("", "is_empty", None) is True
    assert view_service._evaluate_filter([], "is_empty", None) is True
    assert view_service._evaluate_filter("test", "is_empty", None) is False

    # Test is_not_empty
    assert view_service._evaluate_filter("test", "is_not_empty", None) is True
    assert view_service._evaluate_filter(None, "is_not_empty", None) is False

    # Test in
    assert view_service._evaluate_filter("active", "in", ["active", "pending"]) is True
    assert view_service._evaluate_filter("inactive", "in", ["active", "pending"]) is False

    # Test unsupported operator (should default to True)
    assert view_service._evaluate_filter("test", "unknown_operator", "value") is True
