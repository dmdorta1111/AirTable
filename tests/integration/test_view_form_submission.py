"""
Integration tests for form view submission.

Tests the POST /{view_id}/form/submit endpoint to ensure it:
- Creates records with proper validation
- Handles required fields correctly
- Filters out hidden fields
- Rejects invalid field IDs
- Works only for form views
"""

import json

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.view import View, ViewType
from pybase.models.workspace import Workspace
from pybase.models.user import User


@pytest.mark.asyncio
async def test_form_submission_creates_record_successfully(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test successful form submission creates a record."""
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

    # Create fields
    name_field = Field(
        table_id=table.id,
        name="Name",
        field_type=FieldType.TEXT.value,
        is_required=True,
        position=1,
    )
    db_session.add(name_field)
    await db_session.commit()
    await db_session.refresh(name_field)

    email_field = Field(
        table_id=table.id,
        name="Email",
        field_type=FieldType.TEXT.value,
        is_required=True,
        position=2,
    )
    db_session.add(email_field)
    await db_session.commit()
    await db_session.refresh(email_field)

    message_field = Field(
        table_id=table.id,
        name="Message",
        field_type=FieldType.TEXT.value,
        is_required=False,
        position=3,
    )
    db_session.add(message_field)
    await db_session.commit()
    await db_session.refresh(message_field)

    # Create form view
    field_config = {
        "field_order": [str(name_field.id), str(email_field.id), str(message_field.id)],
        "hidden_fields": [],
    }
    type_config = {
        "title": "Contact Form",
        "description": "Send us a message",
        "submit_button_text": "Send",
        "success_message": "Thank you for contacting us!",
        "required_fields": [str(name_field.id), str(email_field.id)],
    }

    view = View(
        table_id=table.id,
        created_by_id=test_user.id,
        name="Contact Form",
        description="Contact form view",
        view_type=ViewType.FORM.value,
        field_config=json.dumps(field_config),
        type_config=json.dumps(type_config),
        position=1,
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Submit form data
    form_data = {
        "data": {
            str(name_field.id): "John Doe",
            str(email_field.id): "john@example.com",
            str(message_field.id): "This is a test message",
        }
    }

    response = await client.post(
        f"/api/v1/views/{view.id}/form/submit",
        headers=auth_headers,
        json=form_data,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # Verify response structure
    assert "success" in data
    assert "message" in data
    assert "record_id" in data
    assert data["success"] is True
    assert data["message"] == "Thank you for contacting us!"
    assert data["record_id"] is not None

    # Verify record was created in database
    records = await db_session.execute(
        f"SELECT * FROM records WHERE table_id = '{table.id}'"
    )
    # For async sessions, we need to use the execute method differently
    from sqlalchemy import select
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    records = result.scalars().all()

    assert len(records) == 1
    record = records[0]
    assert record.created_by_id == test_user.id
    assert str(name_field.id) in record.data
    assert record.data[str(name_field.id)] == "John Doe"
    assert record.data[str(email_field.id)] == "john@example.com"
    assert record.data[str(message_field.id)] == "This is a test message"


@pytest.mark.asyncio
async def test_form_submission_with_missing_required_field_fails(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test form submission fails when required field is missing."""
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

    # Create fields
    name_field = Field(
        table_id=table.id,
        name="Name",
        field_type=FieldType.TEXT.value,
        is_required=True,
        position=1,
    )
    db_session.add(name_field)
    await db_session.commit()
    await db_session.refresh(name_field)

    email_field = Field(
        table_id=table.id,
        name="Email",
        field_type=FieldType.TEXT.value,
        is_required=True,
        position=2,
    )
    db_session.add(email_field)
    await db_session.commit()
    await db_session.refresh(email_field)

    # Create form view with both fields required
    field_config = {
        "field_order": [str(name_field.id), str(email_field.id)],
        "hidden_fields": [],
    }
    type_config = {
        "title": "Contact Form",
        "required_fields": [str(name_field.id), str(email_field.id)],
    }

    view = View(
        table_id=table.id,
        created_by_id=test_user.id,
        name="Contact Form",
        view_type=ViewType.FORM.value,
        field_config=json.dumps(field_config),
        type_config=json.dumps(type_config),
        position=1,
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Submit form data without email (required field)
    form_data = {
        "data": {
            str(name_field.id): "John Doe",
            # Missing email_field
        }
    }

    response = await client.post(
        f"/api/v1/views/{view.id}/form/submit",
        headers=auth_headers,
        json=form_data,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()

    # Verify error response
    assert "detail" in data
    assert "Required fields missing" in str(data["detail"]) or "errors" in str(data["detail"])


@pytest.mark.asyncio
async def test_form_submission_ignores_hidden_fields(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test form submission ignores hidden fields."""
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

    # Create fields
    visible_field = Field(
        table_id=table.id,
        name="Visible Field",
        field_type=FieldType.TEXT.value,
        is_required=False,
        position=1,
    )
    db_session.add(visible_field)
    await db_session.commit()
    await db_session.refresh(visible_field)

    hidden_field = Field(
        table_id=table.id,
        name="Hidden Field",
        field_type=FieldType.TEXT.value,
        is_required=False,
        position=2,
    )
    db_session.add(hidden_field)
    await db_session.commit()
    await db_session.refresh(hidden_field)

    # Create form view with hidden field
    field_config = {
        "field_order": [str(visible_field.id), str(hidden_field.id)],
        "hidden_fields": [str(hidden_field.id)],
    }
    type_config = {
        "title": "Form with Hidden Field",
        "required_fields": [],
    }

    view = View(
        table_id=table.id,
        created_by_id=test_user.id,
        name="Form with Hidden Field",
        view_type=ViewType.FORM.value,
        field_config=json.dumps(field_config),
        type_config=json.dumps(type_config),
        position=1,
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Submit form data including hidden field (should be ignored)
    form_data = {
        "data": {
            str(visible_field.id): "Visible data",
            str(hidden_field.id): "Hidden data",  # This should be ignored
        }
    }

    response = await client.post(
        f"/api/v1/views/{view.id}/form/submit",
        headers=auth_headers,
        json=form_data,
    )

    assert response.status_code == status.HTTP_201_CREATED

    # Verify record was created without hidden field data
    from sqlalchemy import select
    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    records = result.scalars().all()

    assert len(records) == 1
    record = records[0]
    assert str(visible_field.id) in record.data
    assert record.data[str(visible_field.id)] == "Visible data"
    assert str(hidden_field.id) not in record.data  # Hidden field should not be saved


@pytest.mark.asyncio
async def test_form_submission_with_invalid_field_id_fails(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test form submission fails with invalid field ID."""
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

    # Create field
    valid_field = Field(
        table_id=table.id,
        name="Valid Field",
        field_type=FieldType.TEXT.value,
        is_required=False,
        position=1,
    )
    db_session.add(valid_field)
    await db_session.commit()
    await db_session.refresh(valid_field)

    # Create form view
    field_config = {
        "field_order": [str(valid_field.id)],
        "hidden_fields": [],
    }
    type_config = {
        "title": "Simple Form",
        "required_fields": [],
    }

    view = View(
        table_id=table.id,
        created_by_id=test_user.id,
        name="Simple Form",
        view_type=ViewType.FORM.value,
        field_config=json.dumps(field_config),
        type_config=json.dumps(type_config),
        position=1,
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Submit form data with invalid field ID
    invalid_field_id = "00000000-0000-0000-0000-000000000000"
    form_data = {
        "data": {
            str(valid_field.id): "Valid data",
            invalid_field_id: "Invalid field data",  # This field doesn't exist
        }
    }

    response = await client.post(
        f"/api/v1/views/{view.id}/form/submit",
        headers=auth_headers,
        json=form_data,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()

    # Verify error response mentions invalid field
    assert "detail" in data
    assert "not part of this form" in str(data["detail"]).lower() or "validation" in str(data["detail"]).lower()


@pytest.mark.asyncio
async def test_form_submission_to_non_form_view_fails(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test form submission fails for non-form views."""
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

    # Create field
    field = Field(
        table_id=table.id,
        name="Test Field",
        field_type=FieldType.TEXT.value,
        is_required=False,
        position=1,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create grid view (not form)
    view = View(
        table_id=table.id,
        created_by_id=test_user.id,
        name="Grid View",
        view_type=ViewType.GRID.value,
        position=1,
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Try to submit form data to grid view
    form_data = {
        "data": {
            str(field.id): "Test data",
        }
    }

    response = await client.post(
        f"/api/v1/views/{view.id}/form/submit",
        headers=auth_headers,
        json=form_data,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()

    # Verify error response
    assert "detail" in data
    assert "only for form views" in data["detail"].lower()


@pytest.mark.asyncio
async def test_form_submission_with_empty_required_field_fails(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test form submission fails when required field has empty value."""
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

    # Create fields
    required_field = Field(
        table_id=table.id,
        name="Required Field",
        field_type=FieldType.TEXT.value,
        is_required=True,
        position=1,
    )
    db_session.add(required_field)
    await db_session.commit()
    await db_session.refresh(required_field)

    # Create form view
    field_config = {
        "field_order": [str(required_field.id)],
        "hidden_fields": [],
    }
    type_config = {
        "title": "Form with Required Field",
        "required_fields": [str(required_field.id)],
    }

    view = View(
        table_id=table.id,
        created_by_id=test_user.id,
        name="Form with Required Field",
        view_type=ViewType.FORM.value,
        field_config=json.dumps(field_config),
        type_config=json.dumps(type_config),
        position=1,
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Submit form data with empty string for required field
    form_data = {
        "data": {
            str(required_field.id): "",  # Empty string
        }
    }

    response = await client.post(
        f"/api/v1/views/{view.id}/form/submit",
        headers=auth_headers,
        json=form_data,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()

    # Verify error response
    assert "detail" in data
    assert "required" in str(data["detail"]).lower() or "errors" in str(data["detail"])


@pytest.mark.asyncio
async def test_form_submission_returns_default_success_message(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test form submission returns default success message when not configured."""
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

    # Create field
    field = Field(
        table_id=table.id,
        name="Name",
        field_type=FieldType.TEXT.value,
        is_required=True,
        position=1,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create form view without custom success message
    field_config = {
        "field_order": [str(field.id)],
        "hidden_fields": [],
    }
    type_config = {
        "title": "Basic Form",
        "required_fields": [str(field.id)],
        # No success_message configured
    }

    view = View(
        table_id=table.id,
        created_by_id=test_user.id,
        name="Basic Form",
        view_type=ViewType.FORM.value,
        field_config=json.dumps(field_config),
        type_config=json.dumps(type_config),
        position=1,
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Submit form data
    form_data = {
        "data": {
            str(field.id): "John Doe",
        }
    }

    response = await client.post(
        f"/api/v1/views/{view.id}/form/submit",
        headers=auth_headers,
        json=form_data,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # Verify default success message is returned
    assert data["success"] is True
    assert "message" in data
    assert "thank you" in data["message"].lower() or "received" in data["message"].lower()
    assert "record_id" in data
