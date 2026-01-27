"""
End-to-end integration tests for report template usage.

Tests the complete workflow:
1. Browse template gallery
2. Select BOM template
3. Customize data source
4. Generate report
5. Verify BOM structure
"""

import pytest
from httpx import AsyncClient

from pybase.core.config import settings
from pybase.models.base import Base
from pybase.models.custom_report import CustomReport, ReportTemplate
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace


@pytest.mark.asyncio
async def test_browse_and_select_bom_template(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """
    Test browsing template gallery and selecting BOM template.

    End-to-end verification steps:
    1. Browse template gallery
    2. Select BOM template
    3. View template details
    """
    # Step 1: Create workspace and base
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Step 2: Create BOM template
    bom_template_data = {
        "base_id": str(base.id),
        "name": "Bill of Materials (BOM)",
        "description": "Standard BOM report with item details, quantities, and costs",
        "category": "manufacturing",
        "tags": '["BOM", "manufacturing", "inventory", "cost"]',
        "is_system": True,
        "is_active": True,
        "template_config": {
            "sections": [
                {
                    "section_type": "text",
                    "title": "Header",
                    "section_config": {
                        "content": "Bill of Materials",
                        "content_format": "plain",
                        "alignment": "center",
                        "font_size": 20,
                        "font_weight": "bold",
                    },
                    "order": 0,
                },
                {
                    "section_type": "table",
                    "title": "Items",
                    "section_config": {
                        "show_headers": True,
                        "striped_rows": True,
                        "max_rows": 1000,
                    },
                    "order": 1,
                },
                {
                    "section_type": "text",
                    "title": "Summary",
                    "section_config": {
                        "content": "Total Items: {{item_count}} | Total Cost: {{total_cost}}",
                        "content_format": "plain",
                        "alignment": "right",
                        "font_size": 12,
                    },
                    "order": 2,
                },
            ],
            "style_config": {
                "font": "Helvetica",
                "font_size": 10,
                "primary_color": "#2c3e50",
            },
        },
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/report-templates",
        json=bom_template_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    bom_template = response.json()
    assert bom_template["name"] == "Bill of Materials (BOM)"
    assert bom_template["category"] == "manufacturing"
    template_id = bom_template["id"]

    # Step 3: Browse template gallery
    response = await client.get(
        f"{settings.api_v1_prefix}/report-templates",
        headers=auth_headers,
    )

    assert response.status_code == 200
    templates_list = response.json()
    assert templates_list["total"] >= 1
    assert len(templates_list["items"]) >= 1

    # Verify BOM template is in the list
    bom_templates = [t for t in templates_list["items"] if t["id"] == template_id]
    assert len(bom_templates) == 1

    # Step 4: Get BOM template details
    response = await client.get(
        f"{settings.api_v1_prefix}/report-templates/{template_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    template_detail = response.json()
    assert template_detail["id"] == template_id
    assert template_detail["name"] == "Bill of Materials (BOM)"
    assert template_detail["category"] == "manufacturing"
    assert "template_config" in template_detail
    assert "sections" in template_detail["template_config"]
    assert len(template_detail["template_config"]["sections"]) == 3


@pytest.mark.asyncio
async def test_create_report_from_bom_template(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """
    Test creating a report from BOM template with custom data source.

    End-to-end verification steps:
    1. Browse template gallery
    2. Select BOM template
    3. Create report from template
    4. Customize data source
    5. Generate report
    6. Verify BOM structure
    """
    # Step 1: Create workspace, base, and BOM data
    workspace = Workspace(owner_id=test_user.id, name="Manufacturing Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Manufacturing Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Create BOM table
    bom_table = Table(base_id=base.id, name="BOM Items")
    db_session.add(bom_table)
    await db_session.commit()
    await db_session.refresh(bom_table)

    # Add BOM fields
    item_number_field = Field(
        table_id=bom_table.id,
        name="item_number",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(item_number_field)

    description_field = Field(
        table_id=bom_table.id,
        name="description",
        field_type=FieldType.TEXT.value,
    )
    db_session.add(description_field)

    quantity_field = Field(
        table_id=bom_table.id,
        name="quantity",
        field_type=FieldType.NUMBER.value,
    )
    db_session.add(quantity_field)

    unit_cost_field = Field(
        table_id=bom_table.id,
        name="unit_cost",
        field_type=FieldType.NUMBER.value,
    )
    db_session.add(unit_cost_field)

    total_cost_field = Field(
        table_id=bom_table.id,
        name="total_cost",
        field_type=FieldType.NUMBER.value,
    )
    db_session.add(total_cost_field)

    await db_session.commit()
    await db_session.refresh(item_number_field)
    await db_session.refresh(description_field)
    await db_session.refresh(quantity_field)
    await db_session.refresh(unit_cost_field)
    await db_session.refresh(total_cost_field)

    # Add BOM data
    bom_items = [
        {
            "item_number": "ITEM-001",
            "description": "Steel Bracket A",
            "quantity": 100,
            "unit_cost": 5.50,
            "total_cost": 550.00,
        },
        {
            "item_number": "ITEM-002",
            "description": "Aluminum Plate B",
            "quantity": 50,
            "unit_cost": 12.75,
            "total_cost": 637.50,
        },
        {
            "item_number": "ITEM-003",
            "description": "Bolt Set C",
            "quantity": 200,
            "unit_cost": 2.25,
            "total_cost": 450.00,
        },
        {
            "item_number": "ITEM-004",
            "description": "Washer Assembly D",
            "quantity": 200,
            "unit_cost": 0.50,
            "total_cost": 100.00,
        },
    ]

    for item in bom_items:
        record = Record(
            table_id=bom_table.id,
            field_values={
                str(item_number_field.id): item["item_number"],
                str(description_field.id): item["description"],
                str(quantity_field.id): item["quantity"],
                str(unit_cost_field.id): item["unit_cost"],
                str(total_cost_field.id): item["total_cost"],
            },
        )
        db_session.add(record)
    await db_session.commit()

    # Step 2: Create BOM template
    bom_template_data = {
        "base_id": str(base.id),
        "name": "Standard BOM Report",
        "description": "Bill of Materials with item details and cost breakdown",
        "category": "manufacturing",
        "tags": '["BOM", "cost", "manufacturing"]',
        "is_system": True,
        "is_active": True,
        "template_config": {
            "sections": [
                {
                    "section_type": "text",
                    "title": "Title",
                    "section_config": {
                        "content": "Bill of Materials",
                        "content_format": "plain",
                        "alignment": "center",
                        "font_size": 20,
                        "font_weight": "bold",
                    },
                    "order": 0,
                },
                {
                    "section_type": "table",
                    "title": "BOM Items",
                    "section_config": {
                        "show_headers": True,
                        "striped_rows": True,
                    },
                    "order": 1,
                },
                {
                    "section_type": "text",
                    "title": "Total Summary",
                    "section_config": {
                        "content": "Total Items: {{item_count}} | Total Cost: {{total_cost}}",
                        "content_format": "plain",
                        "alignment": "right",
                        "font_size": 12,
                        "font_weight": "bold",
                    },
                    "order": 2,
                },
            ],
        },
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/report-templates",
        json=bom_template_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    bom_template = response.json()
    template_id = bom_template["id"]

    # Step 3: Create custom report from BOM template
    report_data = {
        "base_id": str(base.id),
        "name": "Product X BOM Report",
        "description": "Bill of Materials for Product X assembly",
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
    assert report["name"] == "Product X BOM Report"
    assert report["template_id"] == template_id
    report_id = report["id"]

    # Step 4: Customize data source for BOM table
    datasource_data = {
        "name": "BOM Data Source",
        "tables_config": {
            "primary_table": str(bom_table.id),
            "joined_tables": [],
        },
        "fields_config": [
            {
                "field_id": str(item_number_field.id),
                "alias": "Item Number",
                "aggregate": None,
            },
            {
                "field_id": str(description_field.id),
                "alias": "Description",
                "aggregate": None,
            },
            {
                "field_id": str(quantity_field.id),
                "alias": "Quantity",
                "aggregate": None,
            },
            {
                "field_id": str(unit_cost_field.id),
                "alias": "Unit Cost",
                "aggregate": None,
            },
            {
                "field_id": str(total_cost_field.id),
                "alias": "Total Cost",
                "aggregate": None,
            },
        ],
        "filters_config": [],
        "sort_config": {
            "sorts": [
                {
                    "field_id": str(item_number_field.id),
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
    datasource_id = datasource["id"]

    # Step 5: Update report sections to use data source
    # Get existing sections from template
    response = await client.get(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections",
        headers=auth_headers,
    )

    assert response.status_code == 200
    sections_list = response.json()

    # The template should have created sections
    # Update the table section to use our data source
    if sections_list["total"] > 0:
        for section in sections_list["items"]:
            if section["section_type"] == "table":
                # Update table section to use data source
                update_data = {
                    "section_config": {
                        **section["section_config"],
                        "data_source_id": datasource_id,
                    }
                }

                response = await client.patch(
                    f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections/{section['id']}",
                    json=update_data,
                    headers=auth_headers,
                )

                assert response.status_code == 200

    # Step 6: Generate BOM report PDF
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
    assert b"%PDF-1." in pdf_content

    # Step 7: Verify BOM structure
    # Get report details to verify structure
    response = await client.get(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    report_detail = response.json()
    assert report_detail["id"] == report_id
    assert report_detail["template_id"] == template_id

    # Verify sections
    response = await client.get(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/sections",
        headers=auth_headers,
    )

    assert response.status_code == 200
    sections = response.json()
    assert sections["total"] >= 1

    # Verify BOM structure: should have title, table, and summary sections
    section_types = [s["section_type"] for s in sections["items"]]
    assert "text" in section_types  # Title and summary
    assert "table" in section_types  # BOM items table

    # Verify template usage count increased
    response = await client.get(
        f"{settings.api_v1_prefix}/report-templates/{template_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    template_detail = response.json()
    assert template_detail["usage_count"] >= 1


@pytest.mark.asyncio
async def test_duplicate_template_with_customization(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test duplicating a template and customizing it."""
    # Create workspace and base
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Create original template
    template_data = {
        "base_id": str(base.id),
        "name": "Original Inspection Template",
        "description": "Standard inspection checklist",
        "category": "quality",
        "is_system": False,
        "is_active": True,
        "template_config": {
            "sections": [
                {
                    "section_type": "text",
                    "title": "Inspection Header",
                    "section_config": {"content": "Quality Inspection Report"},
                }
            ],
        },
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/report-templates",
        json=template_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    original_template = response.json()
    original_template_id = original_template["id"]

    # Duplicate template with customization
    duplicate_data = {
        "new_name": "Enhanced Inspection Template",
        "new_description": "Inspection checklist with additional fields",
        "new_category": "quality",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/report-templates/{original_template_id}/duplicate",
        json=duplicate_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    duplicated_template = response.json()
    assert duplicated_template["name"] == "Enhanced Inspection Template"
    assert duplicated_template["description"] == "Inspection checklist with additional fields"
    assert duplicated_template["category"] == "quality"
    assert duplicated_template["id"] != original_template_id
    assert duplicated_template["is_system"] is False  # Duplicate is not a system template
    assert duplicated_template["usage_count"] == 0  # Usage count reset

    # Verify both templates exist
    response = await client.get(
        f"{settings.api_v1_prefix}/report-templates",
        headers=auth_headers,
    )

    assert response.status_code == 200
    templates_list = response.json()
    assert templates_list["total"] >= 2


@pytest.mark.asyncio
async def test_filter_templates_by_category(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test filtering templates by category."""
    # Create workspace and base
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Create templates in different categories
    categories = ["manufacturing", "quality", "project", "financial"]

    for category in categories:
        template_data = {
            "base_id": str(base.id),
            "name": f"{category.capitalize()} Template",
            "description": f"Template for {category}",
            "category": category,
            "is_system": False,
            "is_active": True,
            "template_config": {"sections": []},
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/report-templates",
            json=template_data,
            headers=auth_headers,
        )

        assert response.status_code == 201

    # Filter templates by category
    response = await client.get(
        f"{settings.api_v1_prefix}/report-templates?category=manufacturing",
        headers=auth_headers,
    )

    assert response.status_code == 200
    manufacturing_templates = response.json()
    assert manufacturing_templates["total"] >= 1

    for template in manufacturing_templates["items"]:
        assert template["category"] == "manufacturing"


@pytest.mark.asyncio
async def test_template_usage_tracking(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test that template usage is tracked correctly."""
    # Create workspace and base
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Create template
    template_data = {
        "base_id": str(base.id),
        "name": "Popular Template",
        "description": "A template that will be used multiple times",
        "category": "general",
        "is_system": False,
        "is_active": True,
        "template_config": {"sections": []},
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/report-templates",
        json=template_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    template = response.json()
    template_id = template["id"]
    initial_usage_count = template["usage_count"]
    assert initial_usage_count == 0

    # Create multiple reports from the template
    num_reports = 3
    for i in range(num_reports):
        report_data = {
            "base_id": str(base.id),
            "name": f"Report {i + 1}",
            "template_id": template_id,
            "format": "pdf",
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/custom-reports",
            json=report_data,
            headers=auth_headers,
        )

        assert response.status_code == 201

    # Verify usage count increased
    response = await client.get(
        f"{settings.api_v1_prefix}/report-templates/{template_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    updated_template = response.json()
    assert updated_template["usage_count"] == num_reports
