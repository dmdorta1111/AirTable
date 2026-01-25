"""
Tests for record endpoints.
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.models.user import User


@pytest.mark.asyncio
async def test_create_record(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a record."""
    # Create a workspace, base, table, and field
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
        name="Test Field",
        field_type=FieldType.TEXT.value,
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): "Test value"},
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["table_id"] == str(table.id)
    assert data["data"] == {str(field.id): "Test value"}
    assert data["row_height"] == 32
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_record_unauthorized(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Test creating a record without authentication."""
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(uuid4()),
            "data": {},
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_record_invalid_table_id_format(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a record with invalid table ID format."""
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": "test",  # Invalid UUID format
            "data": {},
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_create_record_invalid_table(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a record in non-existent table."""
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(uuid4()),
            "data": {},
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_record_with_validation_error(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a record with field validation error."""
    # Create a workspace, base, table, and field
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

    # Create a required field
    field = Field(
        table_id=table.id,
        name="Required Field",
        field_type=FieldType.TEXT.value,
        is_required=True,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Try to create record without the required field
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {},  # Missing required field
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_list_records_empty(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing records when none exist."""
    # Create a workspace, base, and table
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

    response = await client.get(
        "/api/v1/records",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_records(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing records."""
    # Create a workspace, base, table, and field
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
        name="Test Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create multiple records
    record1 = Record(
        table_id=table.id,
        data='{"test_field": "Value 1"}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record1)

    record2 = Record(
        table_id=table.id,
        data='{"test_field": "Value 2"}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record2)

    await db_session.commit()

    response = await client.get(
        "/api/v1/records",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_records_filter_by_table(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing records filtered by table."""
    # Create a workspace and base
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

    # Create two tables
    table1 = Table(
        base_id=base.id,
        name="Table 1",
    )
    db_session.add(table1)
    await db_session.commit()
    await db_session.refresh(table1)

    table2 = Table(
        base_id=base.id,
        name="Table 2",
    )
    db_session.add(table2)
    await db_session.commit()
    await db_session.refresh(table2)

    # Create records in both tables
    record1 = Record(
        table_id=table1.id,
        data="{}",
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record1)

    record2 = Record(
        table_id=table2.id,
        data="{}",
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record2)

    await db_session.commit()

    # List records for table 1
    response = await client.get(
        f"/api/v1/records?table_id={table1.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["table_id"] == str(table1.id)


@pytest.mark.asyncio
async def test_get_record(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a record by ID."""
    # Create a workspace, base, and table
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

    # Create a record
    record = Record(
        table_id=table.id,
        data='{"test": "value"}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    response = await client.get(
        f"/api/v1/records/{record.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(record.id)
    assert data["table_id"] == str(table.id)


@pytest.mark.asyncio
async def test_get_record_not_found(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a non-existent record."""
    response = await client.get(
        f"/api/v1/records/{uuid4()}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_record_invalid_id(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a record with invalid ID format."""
    response = await client.get(
        "/api/v1/records/invalid-uuid",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_update_record(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a record."""
    # Create a workspace, base, and table
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

    # Create a record
    record = Record(
        table_id=table.id,
        data='{"test": "old value"}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    response = await client.patch(
        f"/api/v1/records/{record.id}",
        json={
            "data": {"test": "new value"},
            "row_height": 48,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(record.id)
    assert "new value" in str(data["data"])


@pytest.mark.asyncio
async def test_update_record_non_member(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a record by non-member."""
    # Create workspace and record as user 1
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

    record = Record(
        table_id=table.id,
        data="{}",
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    # Create another user
    other_user = User(
        email="other@example.com",
        hashed_password="hashed_password",
        full_name="Other User",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    # Try to update with other user (not a workspace member)
    other_auth_headers = {"Authorization": f"Bearer fake_token"}

    response = await client.patch(
        f"/api/v1/records/{record.id}",
        json={"data": {"test": "value"}},
        headers=other_auth_headers,
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_delete_record(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test deleting (soft delete) a record."""
    # Create a workspace, base, and table
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

    # Create a record
    record = Record(
        table_id=table.id,
        data="{}",
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    response = await client.delete(
        f"/api/v1/records/{record.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify record is soft deleted
    await db_session.refresh(record)
    assert record.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_record_non_member(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test deleting a record by non-member."""
    # Create workspace and record as user 1
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

    record = Record(
        table_id=table.id,
        data="{}",
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    # Create another user
    other_user = User(
        email="other@example.com",
        hashed_password="hashed_password",
        full_name="Other User",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    # Try to delete with other user (not a workspace member)
    other_auth_headers = {"Authorization": f"Bearer fake_token"}

    response = await client.delete(
        f"/api/v1/records/{record.id}",
        headers=other_auth_headers,
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
