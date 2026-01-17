"""
Tests for field endpoints.
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.models.user import User


@pytest.mark.asyncio
async def test_create_field(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a field."""
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

    response = await client.post(
        "/api/v1/fields",
        json={
            "table_id": str(table.id),
            "name": "Test Field",
            "field_type": FieldType.TEXT.value,
            "description": "A test field",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Test Field"
    assert data["field_type"] == FieldType.TEXT.value
    assert data["description"] == "A test field"
    assert data["table_id"] == str(table.id)
    assert data["position"] == 1
    assert data["is_required"] is False
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_field_unauthorized(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Test creating a field without authentication."""
    response = await client.post(
        "/api/v1/fields",
        json={
            "table_id": str(uuid4()),
            "name": "Test Field",
            "field_type": FieldType.TEXT.value,
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_field_invalid_table(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a field in non-existent table."""
    response = await client.post(
        "/api/v1/fields",
        json={
            "table_id": str(uuid4()),
            "name": "Test Field",
            "field_type": FieldType.TEXT.value,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_field_invalid_type(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a field with invalid field type."""
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

    response = await client.post(
        "/api/v1/fields",
        json={
            "table_id": str(table.id),
            "name": "Test Field",
            "field_type": "invalid_type",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_create_field_with_options(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a field with options."""
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

    response = await client.post(
        "/api/v1/fields",
        json={
            "table_id": str(table.id),
            "name": "Test Field",
            "field_type": FieldType.NUMBER.value,
            "options": {"min_value": 0, "max_value": 100},
            "is_required": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["options"] == {"min_value": 0, "max_value": 100}
    assert data["is_required"] is True


@pytest.mark.asyncio
async def test_list_fields_empty(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing fields when user has none."""
    response = await client.get(
        "/api/v1/fields",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_list_fields(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing fields."""
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

    field = Field(
        table_id=table.id,
        name="Test Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()

    response = await client.get(
        "/api/v1/fields",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Test Field"


@pytest.mark.asyncio
async def test_list_fields_filter_by_table(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing fields filtered by table."""
    # Create a workspace, base, and two tables with fields
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

    table1 = Table(
        base_id=base.id,
        name="Table 1",
    )
    db_session.add(table1)
    await db_session.commit()

    table2 = Table(
        base_id=base.id,
        name="Table 2",
    )
    db_session.add(table2)
    await db_session.commit()

    field1 = Field(
        table_id=table1.id,
        name="Field 1",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field1)
    await db_session.commit()

    field2 = Field(
        table_id=table2.id,
        name="Field 2",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field2)
    await db_session.commit()

    # Filter by first table
    response = await client.get(
        f"/api/v1/fields?table_id={table1.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Field 1"


@pytest.mark.asyncio
async def test_get_field(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a field by ID."""
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

    field = Field(
        table_id=table.id,
        name="Test Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    response = await client.get(
        f"/api/v1/fields/{field.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(field.id)
    assert data["name"] == "Test Field"


@pytest.mark.asyncio
async def test_get_field_not_found(
    db_session: AsyncSession,
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a non-existent field."""
    response = await client.get(
        f"/api/v1/fields/{uuid4()}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_field_invalid_id(
    db_session: AsyncSession,
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a field with invalid ID format."""
    response = await client.get(
        "/api/v1/fields/invalid-uuid",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_field(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a field."""
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

    field = Field(
        table_id=table.id,
        name="Test Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    response = await client.patch(
        f"/api/v1/fields/{field.id}",
        json={
            "name": "Updated Field",
            "description": "Updated description",
            "width": 300,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated Field"
    assert data["description"] == "Updated description"
    assert data["width"] == 300


@pytest.mark.asyncio
async def test_update_field_non_member(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a field where user is not a member."""
    # Create workspace for a different user
    other_user = User(
        email="other@example.com",
        hashed_password=test_user.hashed_password,
        name="Other User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    workspace = Workspace(
        owner_id=other_user.id,
        name="Other Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(
        workspace_id=workspace.id,
        name="Other Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Other Table",
    )
    db_session.add(table)
    await db_session.commit()

    field = Field(
        table_id=table.id,
        name="Other Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()

    response = await client.patch(
        f"/api/v1/fields/{field.id}",
        json={"name": "Updated Field"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_delete_field(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test deleting a field."""
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

    field = Field(
        table_id=table.id,
        name="Test Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    response = await client.delete(
        f"/api/v1/fields/{field.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify soft delete
    from sqlalchemy import select

    result = await db_session.execute(select(Field).where(Field.id == field.id))
    deleted_field = result.scalar_one_or_none()
    assert deleted_field is not None
    assert deleted_field.is_deleted is True


@pytest.mark.asyncio
async def test_delete_field_non_owner(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test deleting a field where user is not workspace owner."""
    # Create workspace for a different user
    other_user = User(
        email="other@example.com",
        hashed_password=test_user.hashed_password,
        name="Other User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    workspace = Workspace(
        owner_id=other_user.id,
        name="Other Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(
        workspace_id=workspace.id,
        name="Other Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Other Table",
    )
    db_session.add(table)
    await db_session.commit()

    field = Field(
        table_id=table.id,
        name="Other Field",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(field)
    await db_session.commit()

    response = await client.delete(
        f"/api/v1/fields/{field.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_create_field_with_position(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a field with explicit position."""
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

    response = await client.post(
        "/api/v1/fields",
        json={
            "table_id": str(table.id),
            "name": "Test Field",
            "field_type": FieldType.TEXT.value,
            "position": 5,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["position"] == 5
