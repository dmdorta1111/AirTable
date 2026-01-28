"""
End-to-end integration tests for custom report creation flow.

Tests the complete workflow:
1. Create custom report via API
2. Add table section with data source
3. Add text section
4. Add chart section
5. Export to PDF
6. Verify PDF content
"""

import io

import pytest
from httpx import AsyncClient

from pybase.core.config import settings
from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace


@pytest.mark.asyncio
async def test_create_custom_report_with_all_sections(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test creating a custom report with table, text, and chart sections."""
    # Step 1: Create workspace, base, and table with data
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Products")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Add fields
    name_field = Field(
        table_id=table.id,
        name="name",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(name_field)

    price_field = Field(
        table_id=table.id,
        name="price",
        field_type=FieldType.NUMBER.value,
    )
    db_session.add(price_field)

    quantity_field = Field(
        table_id=table.id,
        name="quantity",
        field_type=FieldType.NUMBER.value,
    )
    db_session.add(quantity_field)
    await db_session.commit()
    await db_session.refresh(name_field)
    await db_session.refresh(price_field)
    await db_session.refresh(quantity_field)

    # Add test data
    record1 = Record(
        table_id=table.id,
        field_values={
            str(name_field.id): "Widget A",
            str(price_field.id): 29.99,
            str(quantity_field.id): 100,
        },
    )
    record2 = Record(
        table_id=table.id,
        field_values={
            str(name_field.id): "Widget B",
            str(price_field.id): 49.99,
            str(quantity_field.id): 50,
        },
    )
    record3 = Record(
        table_id=table.id,
        field_values={
            str(name_field.id): "Widget C",
            str(price_field.id): 19.99,
            str(quantity_field.id): 200,
        },
    )
    db_session.add(record1)
    db_session.add(record2)
    db_session.add(record3)
    await db_session.commit()

    # Step 2: Create custom report
    report_data = {
        "base_id": str(base.id),
        "name": "Product Catalog Report",
        "description": "A comprehensive product catalog with pricing",
        "format": "pdf",
        "layout_config": {
            "page_size": "A4",
            "orientation": "portrait",
            "margin_top": 20,
            "margin_bottom": 20,
            "margin_left": 20,
            "margin_right": 20,
        },
        "style_config": {
            "font": "Helvetica",
            "font_size": 10,
            "primary_color": "#0066cc",
        },
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports",
        json=report_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    report = response.json()
    assert report["name"] == "Product Catalog Report"
    assert report["base_id"] == str(base.id)
    report_id = report["id"]

    # Step 3: Add text section (title/header)
    text_section_data = {
        "section_type": "text",
        "title": "Report Header",
        "section_config": {
            "content": "Product Catalog - Q1 2024",
            "content_format": "plain",
            "alignment": "center",
            "font_size": 18,
            "font_weight": "bold",
        },
        "order": 0,
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections",
        json=text_section_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    text_section = response.json()
    assert text_section["section_type"] == "text"
    text_section_id = text_section["id"]

    # Step 4: Add data source for table section
    datasource_data = {
        "name": "Products Data Source",
        "tables_config": {
            "primary_table": str(table.id),
            "joined_tables": [],
        },
        "fields_config": [
            {
                "field_id": str(name_field.id),
                "alias": "Product Name",
                "aggregate": None,
            },
            {
                "field_id": str(price_field.id),
                "alias": "Price",
                "aggregate": None,
            },
            {
                "field_id": str(quantity_field.id),
                "alias": "Quantity",
                "aggregate": None,
            },
        ],
        "filters_config": [],
        "sort_config": {
            "sorts": [
                {
                    "field_id": str(name_field.id),
                    "direction": "asc",
                }
            ],
            "group_by": [],
        },
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/datasources",
        json=datasource_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    datasource = response.json()
    assert datasource["name"] == "Products Data Source"
    datasource_id = datasource["id"]

    # Step 5: Add table section
    table_section_data = {
        "section_type": "table",
        "title": "Products Table",
        "section_config": {
            "data_source_id": datasource_id,
            "show_headers": True,
            "striped_rows": True,
            "max_rows": 100,
        },
        "order": 1,
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections",
        json=table_section_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    table_section = response.json()
    assert table_section["section_type"] == "table"
    table_section_id = table_section["id"]

    # Step 6: Add chart section
    chart_section_data = {
        "section_type": "chart",
        "title": "Price Distribution",
        "section_config": {
            "chart_type": "bar",
            "data_source_id": datasource_id,
            "x_axis_field": str(name_field.id),
            "y_axis_field": str(price_field.id),
            "width": 600,
            "height": 400,
        },
        "order": 2,
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections",
        json=chart_section_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    chart_section = response.json()
    assert chart_section["section_type"] == "chart"
    chart_section_id = chart_section["id"]

    # Step 7: Verify all sections are listed
    response = await client.get(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections",
        headers=auth_headers,
    )

    assert response.status_code == 200
    sections_list = response.json()
    assert sections_list["total"] == 3
    assert len(sections_list["items"]) == 3

    # Verify sections are in correct order
    section_types = [s["section_type"] for s in sections_list["items"]]
    assert section_types == ["text", "table", "chart"]

    # Step 8: Export to PDF
    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/export/pdf",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"

    # Verify PDF content
    pdf_content = response.content
    assert len(pdf_content) > 0
    assert pdf_content.startswith(b"%PDF-")

    # Verify PDF has minimal structure (PDF header)
    assert b"%PDF-1." in pdf_content

    # Step 9: Verify report metadata
    response = await client.get(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    report_detail = response.json()
    assert report_detail["id"] == report_id
    assert report_detail["name"] == "Product Catalog Report"
    assert report_detail["section_count"] == 3


@pytest.mark.asyncio
async def test_custom_report_create_with_template(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test creating a custom report from a template."""
    # Create workspace and base
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Step 1: Create a report template
    template_data = {
        "base_id": str(base.id),
        "name": "BOM Template",
        "description": "Bill of Materials template",
        "category": "manufacturing",
        "is_system": True,
        "is_active": True,
        "template_config": {
            "sections": [
                {
                    "section_type": "text",
                    "title": "Title",
                    "section_config": {"content": "Bill of Materials", "alignment": "center"},
                },
                {
                    "section_type": "table",
                    "title": "Items",
                    "section_config": {"show_headers": True, "striped_rows": True},
                },
            ]
        },
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/report-templates",
        json=template_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    template = response.json()
    template_id = template["id"]

    # Step 2: Create custom report from template
    report_data = {
        "base_id": str(base.id),
        "name": "Product BOM Report",
        "description": "Bill of Materials for Product X",
        "template_id": template_id,
        "format": "pdf",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports",
        json=report_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    report = response.json()
    assert report["name"] == "Product BOM Report"
    assert report["template_id"] == template_id


@pytest.mark.asyncio
async def test_custom_report_section_reorder(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test reordering sections in a custom report."""
    # Create workspace and base
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Create report
    report_data = {
        "base_id": str(base.id),
        "name": "Reorder Test Report",
        "format": "pdf",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports",
        json=report_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    report = response.json()
    report_id = report["id"]

    # Add three sections
    section_ids = []

    for i in range(3):
        section_data = {
            "section_type": "text",
            "title": f"Section {i}",
            "section_config": {"content": f"Content {i}"},
            "order": i,
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections",
            json=section_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        section = response.json()
        section_ids.append(section["id"])

    # Reorder sections (reverse order)
    reorder_data = {
        "section_orders": [
            {"section_id": section_ids[2], "order": 0},
            {"section_id": section_ids[1], "order": 1},
            {"section_id": section_ids[0], "order": 2},
        ]
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections/reorder",
        json=reorder_data,
        headers=auth_headers,
    )

    assert response.status_code == 200

    # Verify new order
    response = await client.get(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections",
        headers=auth_headers,
    )

    assert response.status_code == 200
    sections_list = response.json()
    assert sections_list["items"][0]["id"] == section_ids[2]
    assert sections_list["items"][1]["id"] == section_ids[1]
    assert sections_list["items"][2]["id"] == section_ids[0]


@pytest.mark.asyncio
async def test_custom_report_update_and_delete_sections(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test updating and deleting sections in a custom report."""
    # Create workspace and base
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Create report
    report_data = {
        "base_id": str(base.id),
        "name": "Update Delete Test Report",
        "format": "pdf",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports",
        json=report_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    report = response.json()
    report_id = report["id"]

    # Add a section
    section_data = {
        "section_type": "text",
        "title": "Original Title",
        "section_config": {"content": "Original Content"},
        "order": 0,
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections",
        json=section_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    section = response.json()
    section_id = section["id"]

    # Update the section
    update_data = {
        "title": "Updated Title",
        "section_config": {"content": "Updated Content"},
    }

    response = await client.patch(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections/{section_id}",
        json=update_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    updated_section = response.json()
    assert updated_section["title"] == "Updated Title"
    assert updated_section["section_config"]["content"] == "Updated Content"

    # Delete the section
    response = await client.delete(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections/{section_id}",
        headers=auth_headers,
    )

    assert response.status_code == 204

    # Verify section is deleted
    response = await client.get(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections",
        headers=auth_headers,
    )

    assert response.status_code == 200
    sections_list = response.json()
    assert sections_list["total"] == 0


@pytest.mark.asyncio
async def test_custom_report_duplicate(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test duplicating a custom report."""
    # Create workspace and base
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Create report with sections
    report_data = {
        "base_id": str(base.id),
        "name": "Original Report",
        "description": "Report to be duplicated",
        "format": "pdf",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports",
        json=report_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    report = response.json()
    report_id = report["id"]

    # Add a section
    section_data = {
        "section_type": "text",
        "title": "Test Section",
        "section_config": {"content": "Test Content"},
        "order": 0,
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections",
        json=section_data,
        headers=auth_headers,
    )

    assert response.status_code == 201

    # Duplicate the report
    duplicate_data = {
        "new_name": "Duplicated Report",
        "new_description": "This is a duplicate",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/duplicate",
        json=duplicate_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    duplicated_report = response.json()
    assert duplicated_report["name"] == "Duplicated Report"
    assert duplicated_report["description"] == "This is a duplicate"
    assert duplicated_report["id"] != report_id

    # Verify duplicated report has sections
    response = await client.get(
        f"{settings.api_v1_prefix}/custom-reports/{duplicated_report['id']}/sections",
        headers=auth_headers,
    )

    assert response.status_code == 200
    sections_list = response.json()
    assert sections_list["total"] == 1
