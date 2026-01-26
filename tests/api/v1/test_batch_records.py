"""Integration tests for batch record operations endpoints."""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.user import User
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


@pytest.mark.asyncio
async def test_batch_create_records_success(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test successful batch creation of multiple records."""
    # Create workspace, base, table, and field
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

    # Batch create 3 records
    response = await client.post(
        "/api/v1/records/batch/create",
        json={
            "records": [
                {
                    "table_id": str(table.id),
                    "data": {str(field.id): "Value 1"},
                },
                {
                    "table_id": str(table.id),
                    "data": {str(field.id): "Value 2"},
                },
                {
                    "table_id": str(table.id),
                    "data": {str(field.id): "Value 3"},
                },
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify response structure
    assert data["total"] == 3
    assert data["successful"] == 3
    assert data["failed"] == 0
    assert len(data["results"]) == 3

    # Verify each result
    for result in data["results"]:
        assert result["success"] is True
        assert result["error"] is None
        assert result["error_code"] is None
        assert result["record"] is not None
        assert result["record"]["table_id"] == str(table.id)
        assert "id" in result["record"]
        assert "created_at" in result["record"]


@pytest.mark.asyncio
async def test_batch_create_records_unauthorized(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Test batch create without authentication."""
    response = await client.post(
        "/api/v1/records/batch/create",
        json={
            "records": [
                {
                    "table_id": str(uuid4()),
                    "data": {},
                }
            ]
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_batch_create_records_invalid_table(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch create with non-existent table."""
    fake_table_id = str(uuid4())

    response = await client.post(
        "/api/v1/records/batch/create",
        json={
            "records": [
                {
                    "table_id": fake_table_id,
                    "data": {},
                },
                {
                    "table_id": fake_table_id,
                    "data": {},
                },
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All records should fail
    assert data["total"] == 2
    assert data["successful"] == 0
    assert data["failed"] == 2
    assert len(data["results"]) == 2

    for result in data["results"]:
        assert result["success"] is False
        assert result["error"] is not None
        assert result["error_code"] == "NOT_FOUND"
        assert result["record"] is None


@pytest.mark.asyncio
async def test_batch_create_records_mixed_table_ids(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch create with records from different tables should fail."""
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
        name="Test Table 1",
    )
    table2 = Table(
        base_id=base.id,
        name="Test Table 2",
    )
    db_session.add_all([table1, table2])
    await db_session.commit()
    await db_session.refresh(table1)
    await db_session.refresh(table2)

    # Try to create records from different tables
    response = await client.post(
        "/api/v1/records/batch/create",
        json={
            "records": [
                {
                    "table_id": str(table1.id),
                    "data": {},
                },
                {
                    "table_id": str(table2.id),
                    "data": {},
                },
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "same table" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_batch_create_records_max_size_exceeded(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch create with more than 100 records should fail."""
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

    # Try to create 101 records
    records = [
        {
            "table_id": str(table.id),
            "data": {},
        }
        for _ in range(101)
    ]

    response = await client.post(
        "/api/v1/records/batch/create",
        json={"records": records},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_batch_create_records_validation_error(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch create with field validation errors."""
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

    # Try to create records without the required field
    response = await client.post(
        "/api/v1/records/batch/create",
        json={
            "records": [
                {
                    "table_id": str(table.id),
                    "data": {},  # Missing required field
                },
                {
                    "table_id": str(table.id),
                    "data": {},  # Missing required field
                },
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All records should fail due to validation
    assert data["total"] == 2
    assert data["successful"] == 0
    assert data["failed"] == 2


@pytest.mark.asyncio
async def test_batch_update_records_success(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test successful batch update of multiple records."""
    # Create workspace, base, table, and field
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

    # Create initial records
    records = []
    for i in range(3):
        record = Record(
            table_id=table.id,
            data={str(field.id): f"Original Value {i}"},
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id,
        )
        db_session.add(record)
        records.append(record)

    await db_session.commit()
    for record in records:
        await db_session.refresh(record)

    # Batch update records
    response = await client.patch(
        f"/api/v1/records/batch/update?table_id={str(table.id)}",
        json={
            "records": [
                {
                    "record_id": str(records[0].id),
                    "data": {str(field.id): "Updated Value 1"},
                },
                {
                    "record_id": str(records[1].id),
                    "data": {str(field.id): "Updated Value 2"},
                },
                {
                    "record_id": str(records[2].id),
                    "data": {str(field.id): "Updated Value 3"},
                    "row_height": 64,
                },
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify response structure
    assert data["total"] == 3
    assert data["successful"] == 3
    assert data["failed"] == 0
    assert len(data["results"]) == 3

    # Verify updates
    for i, result in enumerate(data["results"]):
        assert result["success"] is True
        assert result["error"] is None
        assert result["record"] is not None
        assert result["record"]["data"][str(field.id)] == f"Updated Value {i + 1}"

    # Verify row_height update
    assert data["results"][2]["record"]["row_height"] == 64


@pytest.mark.asyncio
async def test_batch_update_records_unauthorized(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Test batch update without authentication."""
    response = await client.patch(
        f"/api/v1/records/batch/update?table_id={str(uuid4())}",
        json={
            "records": [
                {
                    "record_id": str(uuid4()),
                    "data": {},
                }
            ]
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_batch_update_records_invalid_table(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch update with non-existent table."""
    fake_table_id = str(uuid4())

    response = await client.patch(
        f"/api/v1/records/batch/update?table_id={fake_table_id}",
        json={
            "records": [
                {
                    "record_id": str(uuid4()),
                    "data": {},
                },
                {
                    "record_id": str(uuid4()),
                    "data": {},
                },
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All records should fail
    assert data["total"] == 2
    assert data["successful"] == 0
    assert data["failed"] == 2


@pytest.mark.asyncio
async def test_batch_update_records_invalid_record_ids(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch update with non-existent record IDs."""
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

    # Try to update non-existent records
    response = await client.patch(
        f"/api/v1/records/batch/update?table_id={str(table.id)}",
        json={
            "records": [
                {
                    "record_id": str(uuid4()),
                    "data": {},
                },
                {
                    "record_id": str(uuid4()),
                    "data": {},
                },
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All records should fail
    assert data["total"] == 2
    assert data["successful"] == 0
    assert data["failed"] == 2


@pytest.mark.asyncio
async def test_batch_update_records_max_size_exceeded(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch update with more than 100 records should fail."""
    fake_table_id = str(uuid4())

    # Try to update 101 records
    records = [
        {
            "record_id": str(uuid4()),
            "data": {},
        }
        for _ in range(101)
    ]

    response = await client.patch(
        f"/api/v1/records/batch/update?table_id={fake_table_id}",
        json={"records": records},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_batch_delete_records_success(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test successful batch deletion of multiple records."""
    # Create workspace, base, table, and field
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

    # Create records to delete
    records = []
    for i in range(3):
        record = Record(
            table_id=table.id,
            data={str(field.id): f"Value {i}"},
            created_by_id=test_user.id,
            last_modified_by_id=test_user.id,
        )
        db_session.add(record)
        records.append(record)

    await db_session.commit()
    for record in records:
        await db_session.refresh(record)

    # Batch delete records
    response = await client.delete(
        f"/api/v1/records/batch/delete?table_id={str(table.id)}",
        json={
            "record_ids": [str(r.id) for r in records]
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify response structure
    assert data["total"] == 3
    assert data["successful"] == 3
    assert data["failed"] == 0
    assert len(data["results"]) == 3

    # Verify each deletion
    for result in data["results"]:
        assert result["success"] is True
        assert result["error"] is None
        assert result["error_code"] is None


@pytest.mark.asyncio
async def test_batch_delete_records_unauthorized(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Test batch delete without authentication."""
    response = await client.delete(
        f"/api/v1/records/batch/delete?table_id={str(uuid4())}",
        json={
            "record_ids": [str(uuid4())]
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_batch_delete_records_invalid_table(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch delete with non-existent table."""
    fake_table_id = str(uuid4())

    response = await client.delete(
        f"/api/v1/records/batch/delete?table_id={fake_table_id}",
        json={
            "record_ids": [str(uuid4()), str(uuid4())]
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All records should fail
    assert data["total"] == 2
    assert data["successful"] == 0
    assert data["failed"] == 2


@pytest.mark.asyncio
async def test_batch_delete_records_invalid_record_ids(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch delete with non-existent record IDs."""
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

    # Try to delete non-existent records
    response = await client.delete(
        f"/api/v1/records/batch/delete?table_id={str(table.id)}",
        json={
            "record_ids": [str(uuid4()), str(uuid4())]
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All records should fail
    assert data["total"] == 2
    assert data["successful"] == 0
    assert data["failed"] == 2


@pytest.mark.asyncio
async def test_batch_delete_records_max_size_exceeded(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch delete with more than 100 records should fail."""
    fake_table_id = str(uuid4())

    # Try to delete 101 records
    record_ids = [str(uuid4()) for _ in range(101)]

    response = await client.delete(
        f"/api/v1/records/batch/delete?table_id={fake_table_id}",
        json={"record_ids": record_ids},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_batch_create_empty_records_list(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch create with empty records list should fail."""
    response = await client.post(
        "/api/v1/records/batch/create",
        json={"records": []},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_batch_update_empty_records_list(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch update with empty records list should fail."""
    response = await client.patch(
        f"/api/v1/records/batch/update?table_id={str(uuid4())}",
        json={"records": []},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_batch_delete_empty_records_list(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch delete with empty record IDs list should fail."""
    response = await client.delete(
        f"/api/v1/records/batch/delete?table_id={str(uuid4())}",
        json={"record_ids": []},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_batch_operations_permission_denied(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch operations with insufficient permissions."""
    # Create a workspace owned by another user
    other_user = User(
        email="other@example.com",
        hashed_password="hashedpass",
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

    # Try to create records in a workspace the user doesn't have access to
    response = await client.post(
        "/api/v1/records/batch/create",
        json={
            "records": [
                {
                    "table_id": str(table.id),
                    "data": {},
                }
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All records should fail due to permission
    assert data["total"] == 1
    assert data["successful"] == 0
    assert data["failed"] == 1
    assert data["results"][0]["error_code"] == "PERMISSION_DENIED"
