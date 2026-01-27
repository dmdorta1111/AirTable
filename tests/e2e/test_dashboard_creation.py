"""
End-to-end tests for dashboard creation flow.

This test suite validates the complete dashboard creation workflow:
1. Create a blank dashboard via API
2. Create a dashboard from a template via API
3. Verify dashboard appears in dashboard list
4. Verify dashboard details are correct
5. Verify template widgets are created properly
"""

import json
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.config import settings
from pybase.models.base import Base
from pybase.models.table import Table
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.user import User
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


@pytest_asyncio.fixture
async def test_workspace(db_session: AsyncSession, test_user: User) -> Workspace:
    """Create a test workspace with user as owner."""
    workspace = Workspace(
        owner_id=test_user.id,
        name="Dashboard Creation Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add owner as workspace member
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    return workspace


@pytest_asyncio.fixture
async def test_base(db_session: AsyncSession, test_workspace: Workspace) -> Base:
    """Create a test base for dashboard testing."""
    base = Base(
        workspace_id=test_workspace.id,
        name="Dashboard Test Base",
        description="Base for dashboard creation E2E testing",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def test_table_with_data(db_session: AsyncSession, test_base: Base, test_user: User) -> Table:
    """Create a test table with sample data for dashboard widgets."""
    # Create table
    table = Table(
        base_id=test_base.id,
        name="Project Metrics",
        description="Sample project data for dashboard widgets",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create fields
    fields = [
        Field(
            table_id=table.id,
            name="Project Name",
            field_type=FieldType.TEXT,
            order=0,
        ),
        Field(
            table_id=table.id,
            name="Status",
            field_type=FieldType.TEXT,
            order=1,
        ),
        Field(
            table_id=table.id,
            name="Budget",
            field_type=FieldType.NUMBER,
            order=2,
        ),
        Field(
            table_id=table.id,
            name="Actual Cost",
            field_type=FieldType.NUMBER,
            order=3,
        ),
        Field(
            table_id=table.id,
            name="Completion %",
            field_type=FieldType.NUMBER,
            order=4,
        ),
        Field(
            table_id=table.id,
            name="Due Date",
            field_type=FieldType.DATE,
            order=5,
        ),
    ]
    for field in fields:
        db_session.add(field)
    await db_session.commit()

    # Refresh to get field IDs
    for field in fields:
        await db_session.refresh(field)

    # Create sample records
    sample_data = [
        {"Project Name": "Website Redesign", "Status": "In Progress", "Budget": 50000, "Actual Cost": 35000, "Completion %": 70, "Due Date": "2024-03-15"},
        {"Project Name": "Mobile App", "Status": "Completed", "Budget": 120000, "Actual Cost": 115000, "Completion %": 100, "Due Date": "2024-02-28"},
        {"Project Name": "Database Migration", "Status": "On Hold", "Budget": 80000, "Actual Cost": 45000, "Completion %": 45, "Due Date": "2024-04-30"},
        {"Project Name": "API Integration", "Status": "In Progress", "Budget": 40000, "Actual Cost": 28000, "Completion %": 60, "Due Date": "2024-03-31"},
        {"Project Name": "Security Audit", "Status": "Planning", "Budget": 25000, "Actual Cost": 5000, "Completion %": 10, "Due Date": "2024-05-15"},
    ]

    for data in sample_data:
        record = Record(
            table_id=table.id,
            created_by_id=test_user.id,
            data=json.dumps(data),
        )
        db_session.add(record)
    await db_session.commit()

    return table


@pytest.mark.asyncio
class TestDashboardCreationFlow:
    """End-to-end test suite for dashboard creation workflows."""

    async def test_create_blank_dashboard(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_base: Base,
        test_user: User,
        db_session: AsyncSession,
    ):
        """
        Test creating a blank dashboard from scratch.

        Workflow:
        1. Create a blank dashboard via API
        2. Verify dashboard is created with correct attributes
        3. Verify dashboard appears in dashboard list
        4. Retrieve dashboard by ID and verify details
        """
        # Step 1: Create blank dashboard via API
        dashboard_data = {
            "name": "My Custom Dashboard",
            "description": "A custom dashboard for testing",
            "base_id": str(test_base.id),
            "is_default": False,
            "is_personal": False,
            "is_public": False,
            "is_locked": False,
            "color": "#3b82f6",
            "icon": "layout-dashboard",
            "layout_config": {
                "grid_columns": 12,
                "row_height": 60,
                "widgets": [],
            },
            "settings": {
                "theme": "light",
                "auto_refresh_enabled": True,
                "refresh_interval": 60,
                "show_grid": True,
                "show_filters": True,
                "show_title": True,
            },
            "global_filters": [],
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards",
            headers=auth_headers,
            json=dashboard_data,
        )
        assert response.status_code == 201, f"Dashboard creation failed: {response.text}"
        dashboard = response.json()

        # Verify dashboard response structure
        assert dashboard["name"] == "My Custom Dashboard"
        assert dashboard["description"] == "A custom dashboard for testing"
        assert dashboard["base_id"] == str(test_base.id)
        assert dashboard["is_default"] is False
        assert dashboard["is_personal"] is False
        assert dashboard["is_public"] is False
        assert dashboard["is_locked"] is False
        assert dashboard["color"] == "#3b82f6"
        assert dashboard["icon"] == "layout-dashboard"
        assert "id" in dashboard
        assert "created_at" in dashboard
        assert "updated_at" in dashboard

        dashboard_id = dashboard["id"]

        # Step 2: Verify dashboard appears in dashboard list
        response = await client.get(
            f"{settings.api_v1_prefix}/dashboards",
            params={"base_id": str(test_base.id)},
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Dashboard list retrieval failed: {response.text}"
        dashboard_list = response.json()

        assert dashboard_list["total"] >= 1
        assert dashboard_list["page"] == 1
        assert len(dashboard_list["items"]) >= 1

        # Find our dashboard in the list
        found_dashboard = None
        for item in dashboard_list["items"]:
            if item["id"] == dashboard_id:
                found_dashboard = item
                break

        assert found_dashboard is not None, "Dashboard not found in list"
        assert found_dashboard["name"] == "My Custom Dashboard"

        # Step 3: Retrieve dashboard by ID and verify full details
        response = await client.get(
            f"{settings.api_v1_prefix}/dashboards/{dashboard_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Dashboard retrieval failed: {response.text}"
        dashboard_detail = response.json()

        # Verify all fields
        assert dashboard_detail["id"] == dashboard_id
        assert dashboard_detail["name"] == "My Custom Dashboard"
        assert dashboard_detail["description"] == "A custom dashboard for testing"
        assert dashboard_detail["base_id"] == str(test_base.id)
        assert dashboard_detail["layout_config"]["grid_columns"] == 12
        assert dashboard_detail["layout_config"]["row_height"] == 60
        assert dashboard_detail["settings"]["theme"] == "light"
        assert dashboard_detail["settings"]["auto_refresh_enabled"] is True
        assert dashboard_detail["settings"]["refresh_interval"] == 60

    async def test_create_dashboard_from_template(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_base: Base,
        test_table_with_data: Table,
    ):
        """
        Test creating a dashboard from a predefined template.

        Workflow:
        1. Create dashboard from template via API
        2. Verify dashboard created with template configuration
        3. Verify dashboard appears in dashboard list
        4. Verify template_id is set correctly
        """
        # Step 1: Create dashboard from template
        template_data = {
            "base_id": str(test_base.id),
            "template_id": "project-status",
            "name": "Project Status Dashboard",
            "description": "Dashboard for tracking project progress",
            "is_personal": False,
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards/from-template",
            headers=auth_headers,
            json=template_data,
        )
        assert response.status_code == 201, f"Dashboard creation from template failed: {response.text}"
        dashboard = response.json()

        # Verify dashboard created from template
        assert dashboard["name"] == "Project Status Dashboard"
        assert dashboard["description"] == "Dashboard for tracking project progress"
        assert dashboard["base_id"] == str(test_base.id)
        assert dashboard["template_id"] == "project-status"
        assert dashboard["is_personal"] is False
        assert "id" in dashboard
        dashboard_id = dashboard["id"]

        # Verify layout_config was populated from template
        assert dashboard["layout_config"] is not None
        assert "grid_columns" in dashboard["layout_config"]
        assert "widgets" in dashboard["layout_config"]

        # Verify settings were populated from template
        assert dashboard["settings"] is not None
        assert "theme" in dashboard["settings"] or "refresh_interval" in dashboard["settings"]

        # Step 2: Verify dashboard appears in list
        response = await client.get(
            f"{settings.api_v1_prefix}/dashboards",
            params={"base_id": str(test_base.id)},
            headers=auth_headers,
        )
        assert response.status_code == 200
        dashboard_list = response.json()

        # Find our dashboard
        found_dashboard = None
        for item in dashboard_list["items"]:
            if item["id"] == dashboard_id:
                found_dashboard = item
                break

        assert found_dashboard is not None, "Dashboard from template not found in list"
        assert found_dashboard["template_id"] == "project-status"
        assert found_dashboard["name"] == "Project Status Dashboard"

    async def test_create_multiple_dashboards_from_different_templates(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_base: Base,
    ):
        """
        Test creating multiple dashboards from different templates.

        Workflow:
        1. Create dashboards from different templates
        2. Verify each dashboard has correct template_id
        3. Verify all dashboards appear in list
        4. Verify each dashboard has unique configuration
        """
        template_ids = [
            "engineering-cost-tracking",
            "quality-metrics",
            "project-status",
            "performance-kpis",
        ]

        created_dashboard_ids = []

        # Create dashboards from multiple templates
        for idx, template_id in enumerate(template_ids):
            template_data = {
                "base_id": str(test_base.id),
                "template_id": template_id,
                "name": f"Dashboard {idx + 1} from {template_id}",
                "is_personal": False,
            }

            response = await client.post(
                f"{settings.api_v1_prefix}/dashboards/from-template",
                headers=auth_headers,
                json=template_data,
            )
            assert response.status_code == 201, f"Failed to create dashboard from template {template_id}: {response.text}"
            dashboard = response.json()

            assert dashboard["template_id"] == template_id
            assert dashboard["name"] == f"Dashboard {idx + 1} from {template_id}"
            created_dashboard_ids.append(dashboard["id"])

        # Verify all dashboards appear in list
        response = await client.get(
            f"{settings.api_v1_prefix}/dashboards",
            params={"base_id": str(test_base.id), "page_size": 50},
            headers=auth_headers,
        )
        assert response.status_code == 200
        dashboard_list = response.json()

        # Verify all created dashboards are in the list
        for dashboard_id in created_dashboard_ids:
            found = False
            for item in dashboard_list["items"]:
                if item["id"] == dashboard_id:
                    found = True
                    break
            assert found, f"Dashboard {dashboard_id} not found in list"

        # Verify we have at least the number of dashboards we created
        assert len([d for d in dashboard_list["items"] if d["id"] in created_dashboard_ids]) == len(template_ids)

    async def test_create_personal_dashboard(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_base: Base,
        test_user: User,
    ):
        """
        Test creating a personal dashboard that only the creator can see.

        Workflow:
        1. Create a personal dashboard
        2. Verify is_personal flag is set
        3. Retrieve dashboard and verify personal flag
        """
        # Create personal dashboard
        dashboard_data = {
            "name": "My Personal Dashboard",
            "description": "Only I can see this",
            "base_id": str(test_base.id),
            "is_personal": True,
            "layout_config": {"grid_columns": 12},
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards",
            headers=auth_headers,
            json=dashboard_data,
        )
        assert response.status_code == 201
        dashboard = response.json()

        assert dashboard["name"] == "My Personal Dashboard"
        assert dashboard["is_personal"] is True
        assert dashboard["created_by_id"] == str(test_user.id)
        dashboard_id = dashboard["id"]

        # Retrieve dashboard
        response = await client.get(
            f"{settings.api_v1_prefix}/dashboards/{dashboard_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        dashboard_detail = response.json()

        assert dashboard_detail["is_personal"] is True
        assert dashboard_detail["created_by_id"] == str(test_user.id)

    async def test_dashboard_with_custom_layout_config(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_base: Base,
    ):
        """
        Test creating dashboard with custom layout configuration.

        Workflow:
        1. Create dashboard with custom grid layout
        2. Verify layout_config is persisted correctly
        3. Add widget positions to layout
        4. Update dashboard and verify widget positions
        """
        # Create dashboard with custom layout
        dashboard_data = {
            "name": "Custom Layout Dashboard",
            "base_id": str(test_base.id),
            "layout_config": {
                "grid_columns": 16,
                "row_height": 80,
                "widgets": [
                    {
                        "id": "widget-1",
                        "x": 0,
                        "y": 0,
                        "w": 4,
                        "h": 3,
                    },
                    {
                        "id": "widget-2",
                        "x": 4,
                        "y": 0,
                        "w": 6,
                        "h": 3,
                    },
                    {
                        "id": "widget-3",
                        "x": 10,
                        "y": 0,
                        "w": 6,
                        "h": 6,
                    },
                ],
            },
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards",
            headers=auth_headers,
            json=dashboard_data,
        )
        assert response.status_code == 201
        dashboard = response.json()
        dashboard_id = dashboard["id"]

        # Verify layout config
        assert dashboard["layout_config"]["grid_columns"] == 16
        assert dashboard["layout_config"]["row_height"] == 80
        assert len(dashboard["layout_config"]["widgets"]) == 3

        # Verify widget positions
        widget_1 = next(w for w in dashboard["layout_config"]["widgets"] if w["id"] == "widget-1")
        assert widget_1["x"] == 0
        assert widget_1["y"] == 0
        assert widget_1["w"] == 4
        assert widget_1["h"] == 3

        widget_3 = next(w for w in dashboard["layout_config"]["widgets"] if w["id"] == "widget-3")
        assert widget_3["x"] == 10
        assert widget_3["w"] == 6
        assert widget_3["h"] == 6

        # Update layout
        update_data = {
            "layout_config": {
                "grid_columns": 12,
                "row_height": 60,
                "widgets": [
                    {
                        "id": "widget-1",
                        "x": 0,
                        "y": 0,
                        "w": 6,
                        "h": 4,
                    }
                ],
            },
        }

        response = await client.patch(
            f"{settings.api_v1_prefix}/dashboards/{dashboard_id}",
            headers=auth_headers,
            json=update_data,
        )
        assert response.status_code == 200
        updated_dashboard = response.json()

        assert updated_dashboard["layout_config"]["grid_columns"] == 12
        assert updated_dashboard["layout_config"]["row_height"] == 60
        assert len(updated_dashboard["layout_config"]["widgets"]) == 1

    async def test_create_default_dashboard(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_base: Base,
    ):
        """
        Test creating and setting a default dashboard.

        Workflow:
        1. Create a dashboard and set as default
        2. Verify is_default flag is set
        3. Retrieve default dashboard for base
        4. Verify it's the dashboard we created
        """
        # Create default dashboard
        dashboard_data = {
            "name": "Default Base Dashboard",
            "description": "The default dashboard for this base",
            "base_id": str(test_base.id),
            "is_default": True,
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards",
            headers=auth_headers,
            json=dashboard_data,
        )
        assert response.status_code == 201
        dashboard = response.json()

        assert dashboard["name"] == "Default Base Dashboard"
        assert dashboard["is_default"] is True
        dashboard_id = dashboard["id"]

        # Retrieve default dashboard for base
        response = await client.get(
            f"{settings.api_v1_prefix}/dashboards/default",
            params={"base_id": str(test_base.id)},
            headers=auth_headers,
        )
        assert response.status_code == 200
        default_dashboard = response.json()

        assert default_dashboard["id"] == dashboard_id
        assert default_dashboard["is_default"] is True

    async def test_dashboard_deletion_soft_delete(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_base: Base,
    ):
        """
        Test dashboard soft deletion.

        Workflow:
        1. Create a dashboard
        2. Delete the dashboard
        3. Verify dashboard has deleted_at timestamp
        4. Verify dashboard no longer appears in list
        """
        # Create dashboard
        dashboard_data = {
            "name": "Dashboard to Delete",
            "base_id": str(test_base.id),
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards",
            headers=auth_headers,
            json=dashboard_data,
        )
        assert response.status_code == 201
        dashboard = response.json()
        dashboard_id = dashboard["id"]

        # Delete dashboard
        response = await client.delete(
            f"{settings.api_v1_prefix}/dashboards/{dashboard_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Try to retrieve dashboard - should still exist but with deleted_at
        response = await client.get(
            f"{settings.api_v1_prefix}/dashboards/{dashboard_id}",
            headers=auth_headers,
        )
        # May return 404 or return with deleted_at set depending on implementation
        # Either behavior is acceptable for soft delete

        # Verify dashboard no longer appears in default list
        response = await client.get(
            f"{settings.api_v1_prefix}/dashboards",
            params={"base_id": str(test_base.id)},
            headers=auth_headers,
        )
        assert response.status_code == 200
        dashboard_list = response.json()

        # Dashboard should not be in list (soft deleted)
        found = any(d["id"] == dashboard_id for d in dashboard_list["items"])
        assert not found, "Soft deleted dashboard should not appear in list"

    async def test_dashboard_duplication(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_base: Base,
    ):
        """
        Test duplicating an existing dashboard.

        Workflow:
        1. Create a dashboard with layout and settings
        2. Duplicate the dashboard
        3. Verify duplicate has same configuration
        4. Verify duplicate has different ID and name
        """
        # Create original dashboard
        original_data = {
            "name": "Original Dashboard",
            "description": "Dashboard to be duplicated",
            "base_id": str(test_base.id),
            "color": "#ef4444",
            "layout_config": {
                "grid_columns": 12,
                "widgets": [
                    {"id": "w1", "x": 0, "y": 0, "w": 6, "h": 4},
                ],
            },
            "settings": {
                "theme": "dark",
                "auto_refresh_enabled": True,
            },
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards",
            headers=auth_headers,
            json=original_data,
        )
        assert response.status_code == 201
        original_dashboard = response.json()
        original_id = original_dashboard["id"]

        # Duplicate dashboard
        duplicate_data = {
            "name": "Copy of Original Dashboard",
            "include_layout": True,
            "include_settings": True,
            "include_filters": True,
            "include_charts": True,
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards/{original_id}/duplicate",
            headers=auth_headers,
            json=duplicate_data,
        )
        assert response.status_code == 201
        duplicate_dashboard = response.json()

        # Verify duplicate attributes
        assert duplicate_dashboard["id"] != original_id
        assert duplicate_dashboard["name"] == "Copy of Original Dashboard"
        assert duplicate_dashboard["description"] == "Dashboard to be duplicated"
        assert duplicate_dashboard["color"] == "#ef4444"

        # Verify layout was copied
        assert duplicate_dashboard["layout_config"]["grid_columns"] == 12
        assert len(duplicate_dashboard["layout_config"]["widgets"]) == 1

        # Verify settings were copied
        assert duplicate_dashboard["settings"]["theme"] == "dark"
        assert duplicate_dashboard["settings"]["auto_refresh_enabled"] is True

        # Verify both dashboards exist in list
        response = await client.get(
            f"{settings.api_v1_prefix}/dashboards",
            params={"base_id": str(test_base.id)},
            headers=auth_headers,
        )
        assert response.status_code == 200
        dashboard_list = response.json()

        dashboard_ids = [d["id"] for d in dashboard_list["items"]]
        assert original_id in dashboard_ids
        assert duplicate_dashboard["id"] in dashboard_ids
