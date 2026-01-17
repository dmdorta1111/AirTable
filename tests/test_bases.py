"""
Tests for base endpoints.
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.models.user import User


@pytest.mark.asyncio
async def test_create_base(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a base."""
    # Create a workspace first
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    response = await client.post(
        "/api/v1/bases",
        json={
            "workspace_id": str(workspace.id),
            "name": "Test Base",
            "description": "A test base",
            "icon": "📊",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Test Base"
    assert data["description"] == "A test base"
    assert data["icon"] == "📊"
    assert data["workspace_id"] == str(workspace.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_base_unauthorized(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Test creating a base without authentication."""
    response = await client.post(
        "/api/v1/bases",
        json={
            "workspace_id": str(uuid4()),
            "name": "Test Base",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_base_invalid_workspace(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a base in non-existent workspace."""
    response = await client.post(
        "/api/v1/bases",
        json={
            "workspace_id": str(uuid4()),
            "name": "Test Base",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_list_bases_empty(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing bases when user has none."""
    response = await client.get(
        "/api/v1/bases",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_list_bases(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing bases."""
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
        description="A test base",
    )
    db_session.add(base)
    await db_session.commit()

    response = await client.get(
        "/api/v1/bases",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Test Base"


@pytest.mark.asyncio
async def test_list_bases_filter_by_workspace(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing bases filtered by workspace."""
    # Create two workspaces with bases
    workspace1 = Workspace(
        owner_id=test_user.id,
        name="Workspace 1",
    )
    db_session.add(workspace1)
    await db_session.commit()
    await db_session.refresh(workspace1)

    workspace2 = Workspace(
        owner_id=test_user.id,
        name="Workspace 2",
    )
    db_session.add(workspace2)
    await db_session.commit()
    await db_session.refresh(workspace2)

    base1 = Base(
        workspace_id=workspace1.id,
        name="Base 1",
    )
    db_session.add(base1)
    await db_session.commit()

    base2 = Base(
        workspace_id=workspace2.id,
        name="Base 2",
    )
    db_session.add(base2)
    await db_session.commit()

    # Filter by first workspace
    response = await client.get(
        f"/api/v1/bases?workspace_id={workspace1.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Base 1"


@pytest.mark.asyncio
async def test_get_base(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a base by ID."""
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

    response = await client.get(
        f"/api/v1/bases/{base.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(base.id)
    assert data["name"] == "Test Base"


@pytest.mark.asyncio
async def test_get_base_not_found(
    db_session: AsyncSession,
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a non-existent base."""
    response = await client.get(
        f"/api/v1/bases/{uuid4()}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_base_invalid_id(
    db_session: AsyncSession,
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a base with invalid ID format."""
    response = await client.get(
        "/api/v1/bases/invalid-uuid",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_base(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a base."""
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

    response = await client.patch(
        f"/api/v1/bases/{base.id}",
        json={
            "name": "Updated Base",
            "description": "Updated description",
            "icon": "📋",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated Base"
    assert data["description"] == "Updated description"
    assert data["icon"] == "📋"


@pytest.mark.asyncio
async def test_update_base_non_member(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a base where user is not a member."""
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

    response = await client.patch(
        f"/api/v1/bases/{base.id}",
        json={"name": "Updated Base"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_delete_base(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test deleting a base."""
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

    response = await client.delete(
        f"/api/v1/bases/{base.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify soft delete
    from sqlalchemy import select

    result = await db_session.execute(select(Base).where(Base.id == base.id))
    deleted_base = result.scalar_one_or_none()
    assert deleted_base is not None
    assert deleted_base.is_deleted is True


@pytest.mark.asyncio
async def test_delete_base_non_owner(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test deleting a base where user is not workspace owner."""
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

    response = await client.delete(
        f"/api/v1/bases/{base.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
