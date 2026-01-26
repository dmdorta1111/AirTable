"""Integration tests for view data endpoints with filters and sorts."""

import json
from uuid import uuid4

import pytest
from httpx import AsyncClient

from pybase.core.config import settings
from pybase.models.base import Base as BaseModel
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.view import View
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


@pytest.mark.asyncio
async def test_get_view_data_basic(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test basic view data retrieval without filters or sorts."""
    # Create workspace, base, table, view, and records
    workspace = Workspace(
        name="Test Workspace",
        description="Test workspace for view data",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add user as workspace member
    member = WorkspaceMember(
        workspace_id=str(workspace.id),
        user_id=str(test_user.id),
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    base = BaseModel(
        workspace_id=str(workspace.id),
        name="Test Base",
        description="Test base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=str(base.id),
        name="Test Table",
        description="Test table",
        fields=[
            {"id": "field1", "name": "Name", "type": "text"},
            {"id": "field2", "name": "Age", "type": "number"},
            {"id": "field3", "name": "Status", "type": "text"},
        ],
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create view
    view = View(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        name="Default View",
        view_type="grid",
        is_default=True,
        filters="[]",
        sorts="[]",
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Create test records
    record1 = Record(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        data=json.dumps({"field1": "Alice", "field2": 30, "field3": "Active"}),
    )
    record2 = Record(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        data=json.dumps({"field1": "Bob", "field2": 25, "field3": "Inactive"}),
    )
    record3 = Record(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        data=json.dumps({"field1": "Charlie", "field2": 35, "field3": "Active"}),
    )
    db_session.add_all([record1, record2, record3])
    await db_session.commit()

    # Get view data
    response = await client.post(
        f"{settings.api_v1_prefix}/views/{view.id}/data",
        headers=auth_headers,
        json={
            "page": 1,
            "page_size": 100,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert data["view_id"] == str(view.id)
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 100
    assert data["has_more"] is False
    assert len(data["records"]) == 3

    # Verify record structure
    for record in data["records"]:
        assert "id" in record
        assert "table_id" in record
        assert "data" in record
        assert "created_at" in record
        assert "updated_at" in record


@pytest.mark.asyncio
async def test_get_view_data_with_filters(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test view data retrieval with filters applied."""
    # Create workspace with member
    workspace = Workspace(name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=str(workspace.id),
        user_id=str(test_user.id),
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    base = BaseModel(workspace_id=str(workspace.id), name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=str(base.id),
        name="Test Table",
        fields=[
            {"id": "field1", "name": "Name", "type": "text"},
            {"id": "field2", "name": "Status", "type": "text"},
        ],
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create view with filters
    filters = [
        {
            "field_id": "field2",
            "operator": "equals",
            "value": "Active",
            "conjunction": "and",
        }
    ]
    view = View(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        name="Filtered View",
        view_type="grid",
        filters=json.dumps(filters),
        sorts="[]",
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Create records
    record1 = Record(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        data=json.dumps({"field1": "Alice", "field2": "Active"}),
    )
    record2 = Record(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        data=json.dumps({"field1": "Bob", "field2": "Inactive"}),
    )
    record3 = Record(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        data=json.dumps({"field1": "Charlie", "field2": "Active"}),
    )
    db_session.add_all([record1, record2, record3])
    await db_session.commit()

    # Get view data with filters applied
    response = await client.post(
        f"{settings.api_v1_prefix}/views/{view.id}/data",
        headers=auth_headers,
        json={"page": 1, "page_size": 100},
    )

    assert response.status_code == 200
    data = response.json()

    # Should only return records matching the filter (Active status)
    assert data["total"] == 2
    assert len(data["records"]) == 2
    for record in data["records"]:
        assert record["data"]["field2"] == "Active"


@pytest.mark.asyncio
async def test_get_view_data_with_sorts(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test view data retrieval with sorts applied."""
    # Create workspace with member
    workspace = Workspace(name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=str(workspace.id),
        user_id=str(test_user.id),
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    base = BaseModel(workspace_id=str(workspace.id), name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=str(base.id),
        name="Test Table",
        fields=[
            {"id": "field1", "name": "Name", "type": "text"},
            {"id": "field2", "name": "Age", "type": "number"},
        ],
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create view with sort by age descending
    sorts = [{"field_id": "field2", "direction": "desc"}]
    view = View(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        name="Sorted View",
        view_type="grid",
        filters="[]",
        sorts=json.dumps(sorts),
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Create records
    record1 = Record(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        data=json.dumps({"field1": "Alice", "field2": 30}),
    )
    record2 = Record(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        data=json.dumps({"field1": "Bob", "field2": 25}),
    )
    record3 = Record(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        data=json.dumps({"field1": "Charlie", "field2": 35}),
    )
    db_session.add_all([record1, record2, record3])
    await db_session.commit()

    # Get view data with sorts applied
    response = await client.post(
        f"{settings.api_v1_prefix}/views/{view.id}/data",
        headers=auth_headers,
        json={"page": 1, "page_size": 100},
    )

    assert response.status_code == 200
    data = response.json()

    # Should return records sorted by age descending
    assert data["total"] == 3
    assert len(data["records"]) == 3
    assert data["records"][0]["data"]["field2"] == 35  # Charlie
    assert data["records"][1]["data"]["field2"] == 30  # Alice
    assert data["records"][2]["data"]["field2"] == 25  # Bob


@pytest.mark.asyncio
async def test_get_view_data_with_filters_and_sorts(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test view data with both filters and sorts applied."""
    # Create workspace with member
    workspace = Workspace(name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=str(workspace.id),
        user_id=str(test_user.id),
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    base = BaseModel(workspace_id=str(workspace.id), name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=str(base.id),
        name="Test Table",
        fields=[
            {"id": "field1", "name": "Name", "type": "text"},
            {"id": "field2", "name": "Age", "type": "number"},
            {"id": "field3", "name": "Department", "type": "text"},
        ],
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create view with filter and sort
    filters = [{"field_id": "field3", "operator": "equals", "value": "Engineering", "conjunction": "and"}]
    sorts = [{"field_id": "field2", "direction": "asc"}]
    view = View(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        name="Engineering View",
        view_type="grid",
        filters=json.dumps(filters),
        sorts=json.dumps(sorts),
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Create records
    records = [
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({"field1": "Alice", "field2": 30, "field3": "Engineering"}),
        ),
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({"field1": "Bob", "field2": 25, "field3": "Sales"}),
        ),
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({"field1": "Charlie", "field2": 35, "field3": "Engineering"}),
        ),
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({"field1": "David", "field2": 28, "field3": "Engineering"}),
        ),
    ]
    db_session.add_all(records)
    await db_session.commit()

    # Get view data
    response = await client.post(
        f"{settings.api_v1_prefix}/views/{view.id}/data",
        headers=auth_headers,
        json={"page": 1, "page_size": 100},
    )

    assert response.status_code == 200
    data = response.json()

    # Should return only Engineering records, sorted by age ascending
    assert data["total"] == 3
    assert len(data["records"]) == 3
    assert data["records"][0]["data"]["field1"] == "Bob"  # Age 25 - but filtered out
    assert data["records"][0]["data"]["field2"] == 28  # David
    assert data["records"][1]["data"]["field2"] == 30  # Alice
    assert data["records"][2]["data"]["field2"] == 35  # Charlie
    for record in data["records"]:
        assert record["data"]["field3"] == "Engineering"


@pytest.mark.asyncio
async def test_get_view_data_with_override_filters(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test view data with override filters added to view filters."""
    # Create workspace with member
    workspace = Workspace(name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=str(workspace.id),
        user_id=str(test_user.id),
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    base = BaseModel(workspace_id=str(workspace.id), name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Generate UUID for field1
    field1_id = str(uuid4())

    table = Table(
        base_id=str(base.id),
        name="Test Table",
        fields=[
            {"id": field1_id, "name": "Name", "type": "text"},
            {"id": "field2", "name": "Age", "type": "number"},
        ],
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create view without filters
    view = View(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        name="All Records View",
        view_type="grid",
        filters="[]",
        sorts="[]",
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Create records
    records = [
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({field1_id: "Alice", "field2": 30}),
        ),
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({field1_id: "Bob", "field2": 25}),
        ),
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({field1_id: "Charlie", "field2": 35}),
        ),
    ]
    db_session.add_all(records)
    await db_session.commit()

    # Get view data with override filter
    response = await client.post(
        f"{settings.api_v1_prefix}/views/{view.id}/data",
        headers=auth_headers,
        json={
            "page": 1,
            "page_size": 100,
            "override_filters": [
                {
                    "field_id": field1_id,
                    "operator": "contains",
                    "value": "li",
                    "conjunction": "and",
                }
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should return only records containing "li" in field1 (Alice, Charlie)
    assert data["total"] == 2
    assert len(data["records"]) == 2
    names = [r["data"][field1_id] for r in data["records"]]
    assert "Alice" in names
    assert "Charlie" in names
    assert "Bob" not in names


@pytest.mark.asyncio
async def test_get_view_data_with_override_sorts(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test view data with override sorts replacing view sorts."""
    # Create workspace with member
    workspace = Workspace(name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=str(workspace.id),
        user_id=str(test_user.id),
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    base = BaseModel(workspace_id=str(workspace.id), name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Generate UUIDs for fields
    field1_id = str(uuid4())
    field2_id = str(uuid4())

    table = Table(
        base_id=str(base.id),
        name="Test Table",
        fields=[
            {"id": field1_id, "name": "Name", "type": "text"},
            {"id": field2_id, "name": "Age", "type": "number"},
        ],
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create view with sort by age ascending
    sorts = [{"field_id": field2_id, "direction": "asc"}]
    view = View(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        name="Default Sort View",
        view_type="grid",
        filters="[]",
        sorts=json.dumps(sorts),
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Create records
    records = [
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({field1_id: "Charlie", field2_id: 35}),
        ),
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({field1_id: "Alice", field2_id: 30}),
        ),
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({field1_id: "Bob", field2_id: 25}),
        ),
    ]
    db_session.add_all(records)
    await db_session.commit()

    # Get view data with override sort (by name ascending instead of age)
    response = await client.post(
        f"{settings.api_v1_prefix}/views/{view.id}/data",
        headers=auth_headers,
        json={
            "page": 1,
            "page_size": 100,
            "override_sorts": [{"field_id": field1_id, "direction": "asc"}],
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should be sorted by name instead of age
    assert data["total"] == 3
    assert data["records"][0]["data"][field1_id] == "Alice"
    assert data["records"][1]["data"][field1_id] == "Bob"
    assert data["records"][2]["data"][field1_id] == "Charlie"


@pytest.mark.asyncio
async def test_get_view_data_with_search(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test view data with search query across all fields."""
    # Create workspace with member
    workspace = Workspace(name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=str(workspace.id),
        user_id=str(test_user.id),
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    base = BaseModel(workspace_id=str(workspace.id), name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=str(base.id),
        name="Test Table",
        fields=[
            {"id": "field1", "name": "Name", "type": "text"},
            {"id": "field2", "name": "Email", "type": "text"},
        ],
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    view = View(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        name="All Records",
        view_type="grid",
        filters="[]",
        sorts="[]",
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Create records
    records = [
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({"field1": "Alice", "field2": "alice@example.com"}),
        ),
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({"field1": "Bob", "field2": "bob@test.com"}),
        ),
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({"field1": "Charlie", "field2": "charlie@example.com"}),
        ),
    ]
    db_session.add_all(records)
    await db_session.commit()

    # Search for "example"
    response = await client.post(
        f"{settings.api_v1_prefix}/views/{view.id}/data",
        headers=auth_headers,
        json={
            "page": 1,
            "page_size": 100,
            "search": "example",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should return only records containing "example"
    assert data["total"] == 2
    assert len(data["records"]) == 2
    names = [r["data"]["field1"] for r in data["records"]]
    assert "Alice" in names
    assert "Charlie" in names
    assert "Bob" not in names


@pytest.mark.asyncio
async def test_get_view_data_pagination(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test view data pagination."""
    # Create workspace with member
    workspace = Workspace(name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=str(workspace.id),
        user_id=str(test_user.id),
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    base = BaseModel(workspace_id=str(workspace.id), name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=str(base.id),
        name="Test Table",
        fields=[{"id": "field1", "name": "Index", "type": "number"}],
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    view = View(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        name="All Records",
        view_type="grid",
        filters="[]",
        sorts="[]",
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Create 25 records
    records = [
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({"field1": i}),
        )
        for i in range(25)
    ]
    db_session.add_all(records)
    await db_session.commit()

    # Get first page (10 records)
    response = await client.post(
        f"{settings.api_v1_prefix}/views/{view.id}/data",
        headers=auth_headers,
        json={"page": 1, "page_size": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["records"]) == 10
    assert data["has_more"] is True

    # Get second page
    response = await client.post(
        f"{settings.api_v1_prefix}/views/{view.id}/data",
        headers=auth_headers,
        json={"page": 2, "page_size": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert data["page"] == 2
    assert len(data["records"]) == 10
    assert data["has_more"] is True

    # Get third page (last 5 records)
    response = await client.post(
        f"{settings.api_v1_prefix}/views/{view.id}/data",
        headers=auth_headers,
        json={"page": 3, "page_size": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert data["page"] == 3
    assert len(data["records"]) == 5
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_get_view_data_invalid_view_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test view data with invalid view ID format."""
    response = await client.post(
        f"{settings.api_v1_prefix}/views/invalid-uuid/data",
        headers=auth_headers,
        json={"page": 1, "page_size": 100},
    )

    assert response.status_code == 400
    assert "Invalid view ID format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_view_data_not_found(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test view data with non-existent view ID."""
    fake_view_id = str(uuid4())

    response = await client.post(
        f"{settings.api_v1_prefix}/views/{fake_view_id}/data",
        headers=auth_headers,
        json={"page": 1, "page_size": 100},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_view_data_unauthorized(client: AsyncClient):
    """Test view data without authentication."""
    fake_view_id = str(uuid4())

    response = await client.post(
        f"{settings.api_v1_prefix}/views/{fake_view_id}/data",
        json={"page": 1, "page_size": 100},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_view_data_empty_table(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test view data with empty table (no records)."""
    # Create workspace with member
    workspace = Workspace(name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=str(workspace.id),
        user_id=str(test_user.id),
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    base = BaseModel(workspace_id=str(workspace.id), name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=str(base.id),
        name="Empty Table",
        fields=[{"id": "field1", "name": "Name", "type": "text"}],
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    view = View(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        name="Empty View",
        view_type="grid",
        filters="[]",
        sorts="[]",
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Get view data (no records)
    response = await client.post(
        f"{settings.api_v1_prefix}/views/{view.id}/data",
        headers=auth_headers,
        json={"page": 1, "page_size": 100},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["records"]) == 0
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_get_view_data_complex_filter_operators(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test view data with various filter operators."""
    # Create workspace with member
    workspace = Workspace(name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=str(workspace.id),
        user_id=str(test_user.id),
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    base = BaseModel(workspace_id=str(workspace.id), name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=str(base.id),
        name="Test Table",
        fields=[
            {"id": "field1", "name": "Age", "type": "number"},
            {"id": "field2", "name": "Name", "type": "text"},
        ],
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Test greater than operator
    filters = [{"field_id": "field1", "operator": "gt", "value": 25, "conjunction": "and"}]
    view = View(
        table_id=str(table.id),
        created_by_id=str(test_user.id),
        name="Filter View",
        view_type="grid",
        filters=json.dumps(filters),
        sorts="[]",
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Create records
    records = [
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({"field1": 20, "field2": "Alice"}),
        ),
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({"field1": 30, "field2": "Bob"}),
        ),
        Record(
            table_id=str(table.id),
            created_by_id=str(test_user.id),
            data=json.dumps({"field1": 35, "field2": "Charlie"}),
        ),
    ]
    db_session.add_all(records)
    await db_session.commit()

    # Get view data with gt filter
    response = await client.post(
        f"{settings.api_v1_prefix}/views/{view.id}/data",
        headers=auth_headers,
        json={"page": 1, "page_size": 100},
    )

    assert response.status_code == 200
    data = response.json()

    # Should return only records with age > 25
    assert data["total"] == 2
    for record in data["records"]:
        assert record["data"]["field1"] > 25
