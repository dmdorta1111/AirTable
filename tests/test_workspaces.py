"""
Tests for workspace endpoints.
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.user import User
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


@pytest.mark.asyncio
async def test_create_workspace(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a workspace."""
    response = await client.post(
        "/api/v1/workspaces",
        json={
            "name": "Test Workspace",
            "description": "A test workspace",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Test Workspace"
    assert data["description"] == "A test workspace"
    assert data["owner_id"] == str(test_user.id)
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_workspace_unauthorized(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Test creating a workspace without authentication."""
    response = await client.post(
        "/api/v1/workspaces",
        json={
            "name": "Test Workspace",
            "description": "A test workspace",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_workspace_invalid_name(
    db_session: AsyncSession,
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a workspace with invalid name (too long)."""
    response = await client.post(
        "/api/v1/workspaces",
        json={
            "name": "x" * 300,  # Too long
            "description": "A test workspace",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_list_workspaces_empty(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing workspaces when user has none."""
    response = await client.get(
        "/api/v1/workspaces",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_list_workspaces(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing workspaces."""
    # Create a workspace first
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
        description="A test workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    response = await client.get(
        "/api/v1/workspaces",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Test Workspace"


@pytest.mark.asyncio
async def test_list_workspaces_pagination(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing workspaces with pagination."""
    # Create multiple workspaces
    for i in range(25):
        workspace = Workspace(
            owner_id=test_user.id,
            name=f"Workspace {i}",
            description=f"Description {i}",
        )
        db_session.add(workspace)
    await db_session.commit()

    # Test first page
    response = await client.get(
        "/api/v1/workspaces?page=1&page_size=10",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 25
    assert data["page"] == 1
    assert data["page_size"] == 10

    # Test second page
    response = await client.get(
        "/api/v1/workspaces?page=2&page_size=10",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 10
    assert data["total"] == 25
    assert data["page"] == 2


@pytest.mark.asyncio
async def test_get_workspace(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a workspace by ID."""
    # Create a workspace
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
        description="A test workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    response = await client.get(
        f"/api/v1/workspaces/{workspace.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(workspace.id)
    assert data["name"] == "Test Workspace"
    assert data["description"] == "A test workspace"
    assert "members" in data


@pytest.mark.asyncio
async def test_get_workspace_not_found(
    db_session: AsyncSession,
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a non-existent workspace."""
    response = await client.get(
        f"/api/v1/workspaces/{uuid4()}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_workspace_invalid_id(
    db_session: AsyncSession,
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a workspace with invalid ID format."""
    response = await client.get(
        "/api/v1/workspaces/invalid-uuid",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_workspace(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a workspace."""
    # Create a workspace
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
        description="A test workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    response = await client.patch(
        f"/api/v1/workspaces/{workspace.id}",
        json={
            "name": "Updated Workspace",
            "description": "Updated description",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "Updated Workspace"
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_update_workspace_non_member(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a workspace where user is not a member."""
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

    response = await client.patch(
        f"/api/v1/workspaces/{workspace.id}",
        json={"name": "Updated Workspace"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_delete_workspace(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test deleting a workspace."""
    # Create a workspace
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    response = await client.delete(
        f"/api/v1/workspaces/{workspace.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify soft delete
    from sqlalchemy import select

    result = await db_session.execute(select(Workspace).where(Workspace.id == workspace.id))
    deleted_workspace = result.scalar_one_or_none()
    assert deleted_workspace is not None
    assert deleted_workspace.is_deleted is True


@pytest.mark.asyncio
async def test_delete_workspace_non_owner(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test deleting a workspace where user is not owner."""
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

    response = await client.delete(
        f"/api/v1/workspaces/{workspace.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_add_workspace_member(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test adding a member to workspace."""
    # Create workspace
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Create another user to add
    new_user = User(
        email="member@example.com",
        hashed_password=test_user.hashed_password,
        name="Member User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(new_user)
    await db_session.commit()
    await db_session.refresh(new_user)

    response = await client.post(
        f"/api/v1/workspaces/{workspace.id}/members",
        json={
            "user_id": str(new_user.id),
            "role": WorkspaceRole.EDITOR.value,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["user"]["email"] == "member@example.com"
    assert data["role"] == WorkspaceRole.EDITOR.value


@pytest.mark.asyncio
async def test_add_workspace_member_already_member(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test adding a user who is already a member."""
    # Create workspace (owner is automatically a member)
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    response = await client.post(
        f"/api/v1/workspaces/{workspace.id}/members",
        json={
            "user_id": str(test_user.id),
            "role": WorkspaceRole.EDITOR.value,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_list_workspace_members(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing workspace members."""
    # Create workspace (owner is automatically a member)
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    response = await client.get(
        f"/api/v1/workspaces/{workspace.id}/members",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1  # Owner
    assert data[0]["user"]["email"] == test_user.email
    assert data[0]["role"] == WorkspaceRole.OWNER.value


@pytest.mark.asyncio
async def test_update_workspace_member_role(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a workspace member's role."""
    # Create workspace
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add a member
    new_user = User(
        email="member@example.com",
        hashed_password=test_user.hashed_password,
        name="Member User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(new_user)
    await db_session.commit()
    await db_session.refresh(new_user)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=new_user.id,
        role=WorkspaceRole.EDITOR,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)

    # Update member role
    response = await client.patch(
        f"/api/v1/workspaces/{workspace.id}/members/{member.id}",
        json={"role": WorkspaceRole.ADMIN.value},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["role"] == WorkspaceRole.ADMIN.value


@pytest.mark.asyncio
async def test_update_workspace_member_owner_role(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test that owner role cannot be changed."""
    # Create workspace
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Get owner member
    from sqlalchemy import select

    result = await db_session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == test_user.id,
        )
    )
    owner_member = result.scalar_one()

    response = await client.patch(
        f"/api/v1/workspaces/{workspace.id}/members/{owner_member.id}",
        json={"role": WorkspaceRole.ADMIN.value},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_remove_workspace_member(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test removing a workspace member."""
    # Create workspace
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add a member
    new_user = User(
        email="member@example.com",
        hashed_password=test_user.hashed_password,
        name="Member User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(new_user)
    await db_session.commit()
    await db_session.refresh(new_user)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=new_user.id,
        role=WorkspaceRole.EDITOR,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)

    # Remove member
    response = await client.delete(
        f"/api/v1/workspaces/{workspace.id}/members/{member.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify member is removed
    from sqlalchemy import select

    result = await db_session.execute(
        select(WorkspaceMember).where(WorkspaceMember.id == member.id)
    )
    removed_member = result.scalar_one_or_none()
    assert removed_member is None


@pytest.mark.asyncio
async def test_remove_workspace_member_owner(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test that owner cannot be removed."""
    # Create workspace
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Get owner member
    from sqlalchemy import select

    result = await db_session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == test_user.id,
        )
    )
    owner_member = result.scalar_one()

    response = await client.delete(
        f"/api/v1/workspaces/{workspace.id}/members/{owner_member.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
