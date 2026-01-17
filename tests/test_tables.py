"""
Tests for table endpoints.
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.models.field import Field
from pybase.models.user import User


@pytest.mark.asyncio
async def test_create_table(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a table."""
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

    response = await client.post(
        "/api/v1/tables",
        json={
            "base_id": str(base.id),
            "name": "Test Table",
            "description": "A test table",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Test Table"
    assert data["description"] == "A test table"
    assert data["base_id"] == str(base.id)
    assert data["position"] == 1
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_table_unauthorized(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Test creating a table without authentication."""
    response = await client.post(
        "/api/v1/tables",
        json={
            "base_id": str(uuid4()),
            "name": "Test Table",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_table_invalid_base(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a table in non-existent base."""
    response = await client.post(
        "/api/v1/tables",
        json={
            "base_id": str(uuid4()),
            "name": "Test Table",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_table_with_primary_field(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a table with a primary field."""
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

    # Create a field first
    field = Field(
        table_id=base.id,
        name="ID",
        field_type="text",
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    response = await client.post(
        "/api/v1/tables",
        json={
            "base_id": str(base.id),
            "name": "Test Table",
            "primary_field_id": str(field.id),
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["primary_field_id"] == str(field.id)


@pytest.mark.asyncio
async def test_list_tables_empty(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing tables when user has none."""
    response = await client.get(
        "/api/v1/tables",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_list_tables(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing tables."""
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

    table = Table(
        base_id=base.id,
        name="Test Table",
    )
    db_session.add(table)
    await db_session.commit()

    response = await client.get(
        "/api/v1/tables",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Test Table"


@pytest.mark.asyncio
async def test_list_tables_filter_by_base(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing tables filtered by base."""
    # Create two bases with tables
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base1 = Base(
        workspace_id=workspace.id,
        name="Base 1",
    )
    db_session.add(base1)
    await db_session.commit()

    base2 = Base(
        workspace_id=workspace.id,
        name="Base 2",
    )
    db_session.add(base2)
    await db_session.commit()

    table1 = Table(
        base_id=base1.id,
        name="Table 1",
    )
    db_session.add(table1)
    await db_session.commit()

    table2 = Table(
        base_id=base2.id,
        name="Table 2",
    )
    db_session.add(table2)
    await db_session.commit()

    # Filter by first base
    response = await client.get(
        f"/api/v1/tables?base_id={base1.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Table 1"


@pytest.mark.asyncio
async def test_get_table(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a table by ID."""
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

    table = Table(
        base_id=base.id,
        name="Test Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    response = await client.get(
        f"/api/v1/tables/{table.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(table.id)
    assert data["name"] == "Test Table"


@pytest.mark.asyncio
async def test_get_table_not_found(
    db_session: AsyncSession,
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a non-existent table."""
    response = await client.get(
        f"/api/v1/tables/{uuid4()}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_table_invalid_id(
    db_session: AsyncSession,
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a table with invalid ID format."""
    response = await client.get(
        "/api/v1/tables/invalid-uuid",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_table(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a table."""
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

    table = Table(
        base_id=base.id,
        name="Test Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    response = await client.patch(
        f"/api/v1/tables/{table.id}",
        json={
            "name": "Updated Table",
            "description": "Updated description",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated Table"
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_update_table_non_member(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a table where user is not a member."""
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

    table = Table(
        base_id=base.id,
        name="Other Table",
    )
    db_session.add(table)
    await db_session.commit()

    response = await client.patch(
        f"/api/v1/tables/{table.id}",
        json={"name": "Updated Table"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_delete_table(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test deleting a table."""
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

    table = Table(
        base_id=base.id,
        name="Test Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    response = await client.delete(
        f"/api/v1/tables/{table.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify soft delete
    from sqlalchemy import select

    result = await db_session.execute(select(Table).where(Table.id == table.id))
    deleted_table = result.scalar_one_or_none()
    assert deleted_table is not None
    assert deleted_table.is_deleted is True


@pytest.mark.asyncio
async def test_delete_table_non_owner(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test deleting a table where user is not workspace owner."""
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

    table = Table(
        base_id=base.id,
        name="Other Table",
    )
    db_session.add(table)
    await db_session.commit()

    response = await client.delete(
        f"/api/v1/tables/{table.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
