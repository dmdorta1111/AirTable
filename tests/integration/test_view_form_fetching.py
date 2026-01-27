"""
Integration tests for form view field fetching.

Tests the GET /{view_id}/form endpoint to ensure it returns
actual field definitions with proper ordering, hidden field filtering,
and required field marking.
"""

import json

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.table import Table
from pybase.models.view import View, ViewType
from pybase.models.workspace import Workspace
from pybase.models.user import User


@pytest.mark.asyncio
async def test_form_view_fetching_returns_actual_fields(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test fetching form view returns actual field definitions."""
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
        "success_message": "Thank you!",
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

    # Fetch form view configuration
    response = await client.get(
        f"/api/v1/views/{view.id}/form",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify basic structure
    assert "view_id" in data
    assert "table_id" in data
    assert "title" in data
    assert "description" in data
    assert "fields" in data
    assert "required_fields" in data
    assert "field_order" in data
    assert "hidden_fields" in data

    # Verify form configuration
    assert data["title"] == "Contact Form"
    assert data["description"] == "Send us a message"
    assert data["submit_button_text"] == "Send"
    assert data["success_message"] == "Thank you!"

    # Verify fields are returned (not placeholders)
    assert len(data["fields"]) == 3
    field_ids = [f["id"] for f in data["fields"]]

    # Check that actual field data is present
    name_field_data = next(f for f in data["fields"] if f["name"] == "Name")
    assert name_field_data["field_type"] == FieldType.TEXT.value
    assert name_field_data["is_required"] is True
    assert name_field_data["is_visible"] is True

    email_field_data = next(f for f in data["fields"] if f["name"] == "Email")
    assert email_field_data["field_type"] == FieldType.TEXT.value
    assert email_field_data["is_required"] is True

    message_field_data = next(f for f in data["fields"] if f["name"] == "Message")
    assert message_field_data["field_type"] == FieldType.TEXT.value
    assert message_field_data["is_required"] is False


@pytest.mark.asyncio
async def test_form_view_field_ordering_matches_configuration(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test field ordering matches view configuration."""
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

    # Create fields in reverse order
    field_c = Field(
        table_id=table.id,
        name="Field C",
        field_type=FieldType.TEXT.value,
        is_required=False,
        position=3,
    )
    db_session.add(field_c)
    await db_session.commit()
    await db_session.refresh(field_c)

    field_b = Field(
        table_id=table.id,
        name="Field B",
        field_type=FieldType.TEXT.value,
        is_required=False,
        position=2,
    )
    db_session.add(field_b)
    await db_session.commit()
    await db_session.refresh(field_b)

    field_a = Field(
        table_id=table.id,
        name="Field A",
        field_type=FieldType.TEXT.value,
        is_required=False,
        position=1,
    )
    db_session.add(field_a)
    await db_session.commit()
    await db_session.refresh(field_a)

    # Create form view with custom field order
    field_config = {
        "field_order": [str(field_c.id), str(field_a.id), str(field_b.id)],
        "hidden_fields": [],
    }
    type_config = {
        "title": "Custom Order Form",
        "required_fields": [],
    }

    view = View(
        table_id=table.id,
        created_by_id=test_user.id,
        name="Custom Order Form",
        view_type=ViewType.FORM.value,
        field_config=json.dumps(field_config),
        type_config=json.dumps(type_config),
        position=1,
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Fetch form view configuration
    response = await client.get(
        f"/api/v1/views/{view.id}/form",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify fields are in custom order (C, A, B)
    assert len(data["fields"]) == 3
    assert data["fields"][0]["name"] == "Field C"
    assert data["fields"][1]["name"] == "Field A"
    assert data["fields"][2]["name"] == "Field B"

    # Verify field_order in response matches configuration
    assert data["field_order"] == [str(field_c.id), str(field_a.id), str(field_b.id)]


@pytest.mark.asyncio
async def test_form_view_hidden_fields_are_excluded(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test hidden fields are excluded from form response."""
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

    another_visible_field = Field(
        table_id=table.id,
        name="Another Visible Field",
        field_type=FieldType.TEXT.value,
        is_required=False,
        position=3,
    )
    db_session.add(another_visible_field)
    await db_session.commit()
    await db_session.refresh(another_visible_field)

    # Create form view with hidden field
    field_config = {
        "field_order": [
            str(visible_field.id),
            str(hidden_field.id),
            str(another_visible_field.id),
        ],
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

    # Fetch form view configuration
    response = await client.get(
        f"/api/v1/views/{view.id}/form",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify only visible fields are returned
    assert len(data["fields"]) == 2
    field_names = [f["name"] for f in data["fields"]]
    assert "Visible Field" in field_names
    assert "Another Visible Field" in field_names
    assert "Hidden Field" not in field_names

    # Verify hidden_fields is properly set in response
    assert data["hidden_fields"] == [str(hidden_field.id)]


@pytest.mark.asyncio
async def test_form_view_required_fields_are_marked(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test required fields are properly marked in form response."""
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
    required_field1 = Field(
        table_id=table.id,
        name="Required Field 1",
        field_type=FieldType.TEXT.value,
        is_required=True,
        position=1,
    )
    db_session.add(required_field1)
    await db_session.commit()
    await db_session.refresh(required_field1)

    optional_field = Field(
        table_id=table.id,
        name="Optional Field",
        field_type=FieldType.TEXT.value,
        is_required=False,
        position=2,
    )
    db_session.add(optional_field)
    await db_session.commit()
    await db_session.refresh(optional_field)

    required_field2 = Field(
        table_id=table.id,
        name="Required Field 2",
        field_type=FieldType.TEXT.value,
        is_required=True,
        position=3,
    )
    db_session.add(required_field2)
    await db_session.commit()
    await db_session.refresh(required_field2)

    # Create form view with required fields specified
    field_config = {
        "field_order": [
            str(required_field1.id),
            str(optional_field.id),
            str(required_field2.id),
        ],
        "hidden_fields": [],
    }
    type_config = {
        "title": "Form with Required Fields",
        "required_fields": [
            str(required_field1.id),
            str(required_field2.id),
        ],
    }

    view = View(
        table_id=table.id,
        created_by_id=test_user.id,
        name="Form with Required Fields",
        view_type=ViewType.FORM.value,
        field_config=json.dumps(field_config),
        type_config=json.dumps(type_config),
        position=1,
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Fetch form view configuration
    response = await client.get(
        f"/api/v1/views/{view.id}/form",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify required_fields list in response
    assert len(data["required_fields"]) == 2
    assert str(required_field1.id) in data["required_fields"]
    assert str(required_field2.id) in data["required_fields"]
    assert str(optional_field.id) not in data["required_fields"]

    # Verify is_required flag on each field
    for field in data["fields"]:
        if field["name"] == "Required Field 1":
            assert field["is_required"] is True
        elif field["name"] == "Required Field 2":
            assert field["is_required"] is True
        elif field["name"] == "Optional Field":
            assert field["is_required"] is False


@pytest.mark.asyncio
async def test_form_view_fetching_fails_for_non_form_view(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test that fetching form config for non-form view fails."""
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

    # Try to fetch form configuration for grid view
    response = await client.get(
        f"/api/v1/views/{view.id}/form",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "only for form views" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_form_view_with_empty_fields_list(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test form view with no fields returns empty fields array."""
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

    # Create form view with no fields (all hidden or no fields in table)
    field_config = {
        "field_order": [],
        "hidden_fields": [],
    }
    type_config = {
        "title": "Empty Form",
        "required_fields": [],
    }

    view = View(
        table_id=table.id,
        created_by_id=test_user.id,
        name="Empty Form",
        view_type=ViewType.FORM.value,
        field_config=json.dumps(field_config),
        type_config=json.dumps(type_config),
        position=1,
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Fetch form view configuration
    response = await client.get(
        f"/api/v1/views/{view.id}/form",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify fields array is empty
    assert data["fields"] == []
    assert data["field_order"] == []
    assert data["hidden_fields"] == []
    assert data["required_fields"] == []


@pytest.mark.asyncio
async def test_form_view_includes_all_field_properties(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test form view includes all relevant field properties."""
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

    # Create field with various properties
    field = Field(
        table_id=table.id,
        name="Test Field",
        description="Field description",
        field_type=FieldType.TEXT.value,
        options='{"min_length": 5, "max_length": 100}',
        is_required=True,
        is_unique=False,
        position=1,
        width=200,
        is_visible=True,
        is_primary=False,
        is_computed=False,
        is_locked=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create form view
    field_config = {
        "field_order": [str(field.id)],
        "hidden_fields": [],
    }
    type_config = {
        "title": "Detailed Form",
        "required_fields": [str(field.id)],
    }

    view = View(
        table_id=table.id,
        created_by_id=test_user.id,
        name="Detailed Form",
        view_type=ViewType.FORM.value,
        field_config=json.dumps(field_config),
        type_config=json.dumps(type_config),
        position=1,
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Fetch form view configuration
    response = await client.get(
        f"/api/v1/views/{view.id}/form",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify field has all expected properties
    assert len(data["fields"]) == 1
    field_data = data["fields"][0]

    # Check all expected properties are present
    assert "id" in field_data
    assert "table_id" in field_data
    assert field_data["name"] == "Test Field"
    assert field_data["description"] == "Field description"
    assert field_data["field_type"] == FieldType.TEXT.value
    assert "options" in field_data
    assert field_data["is_required"] is True
    assert field_data["is_unique"] is False
    assert field_data["position"] == 1
    assert field_data["width"] == 200
    assert field_data["is_visible"] is True
    assert field_data["is_primary"] is False
    assert field_data["is_computed"] is False
    assert field_data["is_locked"] is False
    assert "created_at" in field_data
    assert "updated_at" in field_data

    # Verify options are parsed correctly
    assert field_data["options"]["min_length"] == 5
    assert field_data["options"]["max_length"] == 100
