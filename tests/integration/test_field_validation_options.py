"""
Integration tests for advanced field validation options.

Tests validation options (min_length, max_length, regex) through
the record service API endpoints.
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.table import Table
from pybase.models.workspace import Workspace
from pybase.models.user import User


@pytest.mark.asyncio
async def test_create_record_with_min_length_validation_pass(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a record with min_length validation that passes."""
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

    # Create field with min_length validation
    field = Field(
        table_id=table.id,
        name="Username",
        field_type=FieldType.TEXT.value,
        options='{"min_length": 3}',
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create record with valid value (meets min_length)
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): "john"},
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["table_id"] == str(table.id)
    assert data["data"][str(field.id)] == "john"


@pytest.mark.asyncio
async def test_create_record_with_min_length_validation_fail(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a record with min_length validation that fails."""
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

    # Create field with min_length validation
    field = Field(
        table_id=table.id,
        name="Username",
        field_type=FieldType.TEXT.value,
        options='{"min_length": 5}',
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Try to create record with value below min_length
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): "joe"},
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "min length" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_record_with_max_length_validation_pass(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a record with max_length validation that passes."""
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

    # Create field with max_length validation
    field = Field(
        table_id=table.id,
        name="Short Code",
        field_type=FieldType.TEXT.value,
        options='{"max_length": 10}',
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create record with valid value (within max_length)
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): "ABC123"},
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["data"][str(field.id)] == "ABC123"


@pytest.mark.asyncio
async def test_create_record_with_max_length_validation_fail(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a record with max_length validation that fails."""
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

    # Create field with max_length validation
    field = Field(
        table_id=table.id,
        name="Short Code",
        field_type=FieldType.TEXT.value,
        options='{"max_length": 5}',
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Try to create record with value exceeding max_length
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): "TOOLONGVALUE"},
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "max length" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_record_with_regex_validation_pass(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a record with regex validation that passes."""
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

    # Create field with regex validation (alphanumeric only)
    field = Field(
        table_id=table.id,
        name="Product Code",
        field_type=FieldType.TEXT.value,
        options='{"regex": "^[A-Z]{3}-[0-9]{3}$"}',
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create record with valid value matching regex
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): "ABC-123"},
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["data"][str(field.id)] == "ABC-123"


@pytest.mark.asyncio
async def test_create_record_with_regex_validation_fail(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a record with regex validation that fails."""
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

    # Create field with regex validation
    field = Field(
        table_id=table.id,
        name="Product Code",
        field_type=FieldType.TEXT.value,
        options='{"regex": "^[A-Z]{3}-[0-9]{3}$"}',
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Try to create record with value not matching regex
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): "abc-123"},  # lowercase, should fail
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "pattern" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_record_with_combined_validation_pass(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a record with combined validation options that passes."""
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

    # Create field with combined validation (min_length, max_length, regex)
    field = Field(
        table_id=table.id,
        name="Username",
        field_type=FieldType.TEXT.value,
        options='{"min_length": 3, "max_length": 20, "regex": "^[a-z][a-z0-9_]*$"}',
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create record with valid value meeting all constraints
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): "john_doe"},
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["data"][str(field.id)] == "john_doe"


@pytest.mark.asyncio
async def test_create_record_with_combined_validation_fail_min_length(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test combined validation fails on min_length constraint."""
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

    # Create field with combined validation
    field = Field(
        table_id=table.id,
        name="Username",
        field_type=FieldType.TEXT.value,
        options='{"min_length": 3, "max_length": 20, "regex": "^[a-z][a-z0-9_]*$"}',
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Try to create record with value below min_length
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): "ab"},  # too short
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_create_record_with_combined_validation_fail_regex(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test combined validation fails on regex constraint."""
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

    # Create field with combined validation
    field = Field(
        table_id=table.id,
        name="Username",
        field_type=FieldType.TEXT.value,
        options='{"min_length": 3, "max_length": 20, "regex": "^[a-z][a-z0-9_]*$"}',
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Try to create record with value not matching regex (starts with uppercase)
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): "John_Doe"},  # starts with uppercase
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_update_record_with_validation_pass(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a record with validation options that passes."""
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

    # Create field with validation
    field = Field(
        table_id=table.id,
        name="Username",
        field_type=FieldType.TEXT.value,
        options='{"min_length": 3, "regex": "^[a-z][a-z0-9_]*$"}',
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create initial record
    create_response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): "john"},
        },
        headers=auth_headers,
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    record_id = create_response.json()["id"]

    # Update record with valid value
    update_response = await client.patch(
        f"/api/v1/records/{record_id}",
        json={
            "data": {str(field.id): "jane_doe"},
        },
        headers=auth_headers,
    )

    assert update_response.status_code == status.HTTP_200_OK
    data = update_response.json()
    assert data["data"][str(field.id)] == "jane_doe"


@pytest.mark.asyncio
async def test_update_record_with_validation_fail(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test updating a record with validation options that fails."""
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

    # Create field with validation
    field = Field(
        table_id=table.id,
        name="Username",
        field_type=FieldType.TEXT.value,
        options='{"min_length": 3, "regex": "^[a-z][a-z0-9_]*$"}',
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create initial record
    create_response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): "john"},
        },
        headers=auth_headers,
    )
    assert create_response.status_code == status.HTTP_201_CREATED
    record_id = create_response.json()["id"]

    # Try to update record with invalid value (too short)
    update_response = await client.patch(
        f"/api/v1/records/{record_id}",
        json={
            "data": {str(field.id): "ab"},
        },
        headers=auth_headers,
    )

    assert update_response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_create_record_with_none_value_bypasses_validation(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test that None values bypass validation for non-required fields."""
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

    # Create field with strict validation but not required
    field = Field(
        table_id=table.id,
        name="Optional Field",
        field_type=FieldType.TEXT.value,
        options='{"min_length": 10, "regex": "^[A-Z]+$"}',
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create record with None value (should pass even with strict validation)
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): None},
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["data"][str(field.id)] is None


@pytest.mark.asyncio
async def test_create_record_with_email_pattern_validation(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test creating a record with email pattern validation."""
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

    # Create field with email regex pattern
    field = Field(
        table_id=table.id,
        name="Email",
        field_type=FieldType.TEXT.value,
        options='{"regex": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,}$"}',
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Test valid email
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): "test@example.com"},
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED

    # Test invalid email
    response = await client.post(
        "/api/v1/records",
        json={
            "table_id": str(table.id),
            "data": {str(field.id): "invalid-email"},
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
