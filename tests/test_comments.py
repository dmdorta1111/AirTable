"""
Tests for comment endpoints.
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.comment import Comment
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.user import User
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


@pytest.mark.asyncio
async def test_create_comment(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a comment on a record."""
    # Create workspace, base, table, and record
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

    record = Record(
        table_id=table.id,
        data={str(field.id): "Test data"},
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    response = await client.post(
        "/api/v1/comments",
        json={
            "record_id": str(record.id),
            "content": "This is a test comment",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["record_id"] == str(record.id)
    assert data["user_id"] == str(test_user.id)
    assert data["content"] == "This is a test comment"
    assert data["is_edited"] is False
    assert data["edited_at"] is None
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_comment_unauthorized(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Test creating a comment without authentication."""
    response = await client.post(
        "/api/v1/comments",
        json={
            "record_id": str(uuid4()),
            "content": "Test comment",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_create_comment_invalid_record(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a comment on non-existent record."""
    response = await client.post(
        "/api/v1/comments",
        json={
            "record_id": str(uuid4()),
            "content": "Test comment",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_create_comment_no_permission(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a comment on record user doesn't have access to."""
    # Create a different user and their workspace
    other_user = User(
        email="other@example.com",
        hashed_password="hashed",
        name="Other User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

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

    record = Record(
        table_id=table.id,
        data={str(field.id): "Test data"},
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    response = await client.post(
        "/api/v1/comments",
        json={
            "record_id": str(record.id),
            "content": "Test comment",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_comment(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a comment by ID."""
    # Create workspace, base, table, record, and comment
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

    record = Record(
        table_id=table.id,
        data={str(field.id): "Test data"},
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    comment = Comment(
        record_id=str(record.id),
        user_id=str(test_user.id),
        content="Test comment",
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)

    response = await client.get(
        f"/api/v1/comments/{comment.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(comment.id)
    assert data["record_id"] == str(record.id)
    assert data["user_id"] == str(test_user.id)
    assert data["content"] == "Test comment"


@pytest.mark.asyncio
async def test_get_comment_unauthorized(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Test getting a comment without authentication."""
    response = await client.get(f"/api/v1/comments/{uuid4()}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_comment_not_found(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a non-existent comment."""
    response = await client.get(
        f"/api/v1/comments/{uuid4()}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_comment_invalid_id_format(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a comment with invalid ID format."""
    response = await client.get(
        "/api/v1/comments/invalid-uuid",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_get_comment_no_permission(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test getting a comment user doesn't have access to."""
    # Create a different user and their workspace
    other_user = User(
        email="other@example.com",
        hashed_password="hashed",
        name="Other User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

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

    record = Record(
        table_id=table.id,
        data={str(field.id): "Test data"},
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    comment = Comment(
        record_id=str(record.id),
        user_id=str(other_user.id),
        content="Test comment",
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)

    response = await client.get(
        f"/api/v1/comments/{comment.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_list_comments_empty(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing comments when none exist."""
    # Create workspace, base, table, and record but no comments
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    response = await client.get(
        "/api/v1/comments",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_list_comments(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing comments."""
    # Create workspace, base, table, record, and comments
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

    record = Record(
        table_id=table.id,
        data={str(field.id): "Test data"},
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    # Create multiple comments
    comment1 = Comment(
        record_id=str(record.id),
        user_id=str(test_user.id),
        content="First comment",
    )
    comment2 = Comment(
        record_id=str(record.id),
        user_id=str(test_user.id),
        content="Second comment",
    )
    db_session.add_all([comment1, comment2])
    await db_session.commit()

    response = await client.get(
        "/api/v1/comments",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 20


@pytest.mark.asyncio
async def test_list_comments_filter_by_record(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing comments filtered by record ID."""
    # Create workspace, base, table, and records
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

    record1 = Record(
        table_id=table.id,
        data={str(field.id): "Test data 1"},
    )
    record2 = Record(
        table_id=table.id,
        data={str(field.id): "Test data 2"},
    )
    db_session.add_all([record1, record2])
    await db_session.commit()
    await db_session.refresh(record1)
    await db_session.refresh(record2)

    # Create comments for both records
    comment1 = Comment(
        record_id=str(record1.id),
        user_id=str(test_user.id),
        content="Comment on record 1",
    )
    comment2 = Comment(
        record_id=str(record2.id),
        user_id=str(test_user.id),
        content="Comment on record 2",
    )
    db_session.add_all([comment1, comment2])
    await db_session.commit()

    response = await client.get(
        f"/api/v1/comments?record_id={record1.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["record_id"] == str(record1.id)
    assert data["items"][0]["content"] == "Comment on record 1"
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_list_comments_pagination(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test comment list pagination."""
    # Create workspace, base, table, record, and multiple comments
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

    record = Record(
        table_id=table.id,
        data={str(field.id): "Test data"},
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    # Create 5 comments
    comments = [
        Comment(
            record_id=str(record.id),
            user_id=str(test_user.id),
            content=f"Comment {i}",
        )
        for i in range(5)
    ]
    db_session.add_all(comments)
    await db_session.commit()

    # Test first page
    response = await client.get(
        "/api/v1/comments?page=1&page_size=2",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2

    # Test second page
    response = await client.get(
        "/api/v1/comments?page=2&page_size=2",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["page"] == 2
    assert data["page_size"] == 2


@pytest.mark.asyncio
async def test_list_comments_invalid_record_id_format(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test listing comments with invalid record ID format."""
    response = await client.get(
        "/api/v1/comments?record_id=invalid-uuid",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_comment(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a comment by its author."""
    # Create workspace, base, table, record, and comment
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

    record = Record(
        table_id=table.id,
        data={str(field.id): "Test data"},
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    comment = Comment(
        record_id=str(record.id),
        user_id=str(test_user.id),
        content="Original comment",
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)

    response = await client.patch(
        f"/api/v1/comments/{comment.id}",
        json={"content": "Updated comment"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(comment.id)
    assert data["content"] == "Updated comment"
    assert data["is_edited"] is True
    assert data["edited_at"] is not None


@pytest.mark.asyncio
async def test_update_comment_unauthorized(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Test updating a comment without authentication."""
    response = await client.patch(
        f"/api/v1/comments/{uuid4()}",
        json={"content": "Updated comment"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_update_comment_not_found(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a non-existent comment."""
    response = await client.patch(
        f"/api/v1/comments/{uuid4()}",
        json={"content": "Updated comment"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_comment_invalid_id_format(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a comment with invalid ID format."""
    response = await client.patch(
        "/api/v1/comments/invalid-uuid",
        json={"content": "Updated comment"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_update_comment_by_workspace_owner_on_other_user_comment(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test that workspace owner can update comments by other users."""
    # Create another user
    other_user = User(
        email="other@example.com",
        hashed_password="hashed",
        name="Other User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    # Create workspace and add both users
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add other_user as member (not admin)
    member = WorkspaceMember(
        workspace_id=str(workspace.id),
        user_id=str(other_user.id),
        role=WorkspaceRole.MEMBER,
    )
    db_session.add(member)
    await db_session.commit()

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

    record = Record(
        table_id=table.id,
        data={str(field.id): "Test data"},
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    # Create comment by other_user
    comment = Comment(
        record_id=str(record.id),
        user_id=str(other_user.id),
        content="Original comment",
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)

    # Update with test_user (who is workspace owner and can update any comment)
    response = await client.patch(
        f"/api/v1/comments/{comment.id}",
        json={"content": "Updated comment"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_update_comment_by_workspace_admin(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test that workspace admin can update any comment."""
    # Create another user
    other_user = User(
        email="other@example.com",
        hashed_password="hashed",
        name="Other User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    # Create workspace with test_user as owner
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add other_user as member
    member = WorkspaceMember(
        workspace_id=str(workspace.id),
        user_id=str(other_user.id),
        role=WorkspaceRole.MEMBER,
    )
    db_session.add(member)
    await db_session.commit()

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

    record = Record(
        table_id=table.id,
        data={str(field.id): "Test data"},
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    # Create comment by other_user
    comment = Comment(
        record_id=str(record.id),
        user_id=str(other_user.id),
        content="Original comment",
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)

    # test_user is workspace owner, so they can update
    response = await client.patch(
        f"/api/v1/comments/{comment.id}",
        json={"content": "Admin updated comment"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["content"] == "Admin updated comment"
    assert data["is_edited"] is True


@pytest.mark.asyncio
async def test_delete_comment(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test deleting a comment by its author."""
    # Create workspace, base, table, record, and comment
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

    record = Record(
        table_id=table.id,
        data={str(field.id): "Test data"},
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    comment = Comment(
        record_id=str(record.id),
        user_id=str(test_user.id),
        content="Test comment",
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)

    response = await client.delete(
        f"/api/v1/comments/{comment.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify comment is soft deleted
    await db_session.refresh(comment)
    assert comment.is_deleted is True


@pytest.mark.asyncio
async def test_delete_comment_unauthorized(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Test deleting a comment without authentication."""
    response = await client.delete(f"/api/v1/comments/{uuid4()}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_delete_comment_not_found(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test deleting a non-existent comment."""
    response = await client.delete(
        f"/api/v1/comments/{uuid4()}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_comment_invalid_id_format(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test deleting a comment with invalid ID format."""
    response = await client.delete(
        "/api/v1/comments/invalid-uuid",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_delete_comment_by_workspace_admin(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test that workspace admin can delete any comment."""
    # Create another user
    other_user = User(
        email="other@example.com",
        hashed_password="hashed",
        name="Other User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    # Create workspace with test_user as owner
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add other_user as member
    member = WorkspaceMember(
        workspace_id=str(workspace.id),
        user_id=str(other_user.id),
        role=WorkspaceRole.MEMBER,
    )
    db_session.add(member)
    await db_session.commit()

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

    record = Record(
        table_id=table.id,
        data={str(field.id): "Test data"},
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    # Create comment by other_user
    comment = Comment(
        record_id=str(record.id),
        user_id=str(other_user.id),
        content="Test comment",
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)

    # test_user is workspace owner, so they can delete
    response = await client.delete(
        f"/api/v1/comments/{comment.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify comment is soft deleted
    await db_session.refresh(comment)
    assert comment.is_deleted is True
