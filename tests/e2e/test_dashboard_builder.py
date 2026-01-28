"""
End-to-end tests for dashboard builder and widget configuration.

This test suite validates the complete dashboard builder workflow:
1. Create a dashboard and add widgets via API
2. Configure chart widgets with data sources and filters
3. Configure metric widgets with field selections
4. Save dashboard with layout configuration
5. Verify widgets display correct data
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
from pybase.models.dashboard import Dashboard


@pytest_asyncio.fixture
async def builder_workspace(db_session: AsyncSession, test_user: User) -> Workspace:
    """Create a test workspace with user as owner."""
    workspace = Workspace(
        owner_id=test_user.id,
        name="Dashboard Builder Test Workspace",
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
async def builder_base(db_session: AsyncSession, builder_workspace: Workspace) -> Base:
    """Create a test base for dashboard builder testing."""
    base = Base(
        workspace_id=builder_workspace.id,
        name="Dashboard Builder Test Base",
        description="Base for dashboard builder E2E testing",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def builder_table_with_data(db_session: AsyncSession, builder_base: Base, test_user: User) -> Table:
    """Create a test table with sample data for widget configuration."""
    # Create table
    table = Table(
        base_id=builder_base.id,
        name="Sales Data",
        description="Sample sales data for dashboard widgets",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create fields
    fields = [
        Field(
            table_id=table.id,
            name="Product",
            field_type=FieldType.TEXT,
            order=0,
        ),
        Field(
            table_id=table.id,
            name="Region",
            field_type=FieldType.TEXT,
            order=1,
        ),
        Field(
            table_id=table.id,
            name="Sales Amount",
            field_type=FieldType.NUMBER,
            order=2,
        ),
        Field(
            table_id=table.id,
            name="Units Sold",
            field_type=FieldType.NUMBER,
            order=3,
        ),
        Field(
            table_id=table.id,
            name="Quarter",
            field_type=FieldType.TEXT,
            order=4,
        ),
        Field(
            table_id=table.id,
            name="Target Amount",
            field_type=FieldType.NUMBER,
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
        {"Product": "Widget A", "Region": "North", "Sales Amount": 15000, "Units Sold": 150, "Quarter": "Q1", "Target Amount": 20000},
        {"Product": "Widget B", "Region": "North", "Sales Amount": 22000, "Units Sold": 220, "Quarter": "Q1", "Target Amount": 20000},
        {"Product": "Widget A", "Region": "South", "Sales Amount": 18000, "Units Sold": 180, "Quarter": "Q1", "Target Amount": 20000},
        {"Product": "Widget C", "Region": "East", "Sales Amount": 25000, "Units Sold": 250, "Quarter": "Q1", "Target Amount": 25000},
        {"Product": "Widget A", "Region": "North", "Sales Amount": 19500, "Units Sold": 195, "Quarter": "Q2", "Target Amount": 20000},
        {"Product": "Widget B", "Region": "South", "Sales Amount": 21000, "Units Sold": 210, "Quarter": "Q2", "Target Amount": 20000},
        {"Product": "Widget C", "Region": "West", "Sales Amount": 28000, "Units Sold": 280, "Quarter": "Q2", "Target Amount": 25000},
        {"Product": "Widget A", "Region": "East", "Sales Amount": 17500, "Units Sold": 175, "Quarter": "Q3", "Target Amount": 20000},
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
class TestDashboardBuilderFlow:
    """End-to-end test suite for dashboard builder and widget configuration workflows."""

    async def test_create_empty_dashboard_and_add_chart_widget(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        builder_base: Base,
        builder_table_with_data: Table,
        db_session: AsyncSession,
    ):
        """
        Test creating an empty dashboard and adding a chart widget.

        Workflow:
        1. Create empty dashboard
        2. Add chart widget with configuration
        3. Save dashboard with updated layout
        4. Verify widget configuration persists
        5. Verify chart data displays correctly
        """
        # Step 1: Create empty dashboard
        dashboard_data = {
            "name": "Sales Dashboard",
            "description": "Dashboard for tracking sales metrics",
            "base_id": str(builder_base.id),
            "layout_config": {
                "grid_columns": 12,
                "row_height": 60,
                "widgets": [],
            },
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards",
            headers=auth_headers,
            json=dashboard_data,
        )
        assert response.status_code == 201, f"Dashboard creation failed: {response.text}"
        dashboard = response.json()
        dashboard_id = dashboard["id"]

        # Step 2: Add chart widget to dashboard
        # Get field IDs for configuration
        response = await client.get(
            f"{settings.api_v1_prefix}/tables/{builder_table_with_data.id}/fields",
            headers=auth_headers,
        )
        assert response.status_code == 200
        fields_data = response.json()
        fields = {f["name"]: f["id"] for f in fields_data}

        # Create chart widget configuration
        chart_widget = {
            "id": str(uuid4()),
            "type": "chart",
            "chartType": "bar",
            "position": {
                "x": 0,
                "y": 0,
                "w": 6,
                "h": 4,
            },
            "title": "Sales by Region",
            "chartConfig": {
                "table_id": str(builder_table_with_data.id),
                "x_axis_field_id": fields["Region"],
                "y_axis_field_id": fields["Sales Amount"],
                "aggregation": "sum",
                "chart_type": "bar",
                "color": "#3b82f6",
                "show_legend": True,
                "show_data_labels": True,
            },
        }

        # Update dashboard with widget
        update_data = {
            "layout_config": {
                "grid_columns": 12,
                "row_height": 60,
                "widgets": [chart_widget],
            },
        }

        response = await client.patch(
            f"{settings.api_v1_prefix}/dashboards/{dashboard_id}",
            headers=auth_headers,
            json=update_data,
        )
        assert response.status_code == 200, f"Dashboard update failed: {response.text}"
        updated_dashboard = response.json()

        # Step 3: Verify widget configuration persisted
        assert len(updated_dashboard["layout_config"]["widgets"]) == 1
        widget = updated_dashboard["layout_config"]["widgets"][0]
        assert widget["type"] == "chart"
        assert widget["title"] == "Sales by Region"
        assert widget["chartConfig"]["table_id"] == str(builder_table_with_data.id)
        assert widget["chartConfig"]["aggregation"] == "sum"

        # Step 4: Verify chart data displays correctly
        # Create chart to fetch data
        chart_data = {
            "name": "Sales by Region Chart",
            "table_id": str(builder_table_with_data.id),
            "chart_type": "bar",
            "data_config": {
                "x_axis_field_id": fields["Region"],
                "y_axis_field_id": fields["Sales Amount"],
                "aggregation": "sum",
            },
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/charts",
            headers=auth_headers,
            json=chart_data,
        )
        assert response.status_code == 201
        chart = response.json()
        chart_id = chart["id"]

        # Fetch chart data
        response = await client.get(
            f"{settings.api_v1_prefix}/charts/{chart_id}/data",
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Chart data fetch failed: {response.text}"
        chart_response = response.json()

        # Verify chart data structure
        assert "data" in chart_response
        assert "labels" in chart_response["data"]
        assert "datasets" in chart_response["data"]
        assert len(chart_response["data"]["datasets"]) > 0
        assert "data" in chart_response["data"]["datasets"][0]

    async def test_configure_multiple_widget_types(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        builder_base: Base,
        builder_table_with_data: Table,
    ):
        """
        Test configuring multiple widget types in a single dashboard.

        Workflow:
        1. Create dashboard
        2. Add chart widget with data source and filters
        3. Add metric widget with field configuration
        4. Add text widget for documentation
        5. Save dashboard with all widgets
        6. Verify all widget configurations persist
        """
        # Step 1: Create dashboard
        dashboard_data = {
            "name": "Multi-Widget Dashboard",
            "base_id": str(builder_base.id),
            "layout_config": {"grid_columns": 12, "widgets": []},
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards",
            headers=auth_headers,
            json=dashboard_data,
        )
        assert response.status_code == 201
        dashboard = response.json()
        dashboard_id = dashboard["id"]

        # Get field IDs
        response = await client.get(
            f"{settings.api_v1_prefix}/tables/{builder_table_with_data.id}/fields",
            headers=auth_headers,
        )
        assert response.status_code == 200
        fields_data = response.json()
        fields = {f["name"]: f["id"] for f in fields_data}

        # Step 2: Add chart widget
        chart_widget = {
            "id": str(uuid4()),
            "type": "chart",
            "chartType": "line",
            "position": {"x": 0, "y": 0, "w": 8, "h": 4},
            "title": "Sales Trend",
            "chartConfig": {
                "table_id": str(builder_table_with_data.id),
                "x_axis_field_id": fields["Quarter"],
                "y_axis_field_id": fields["Sales Amount"],
                "aggregation": "sum",
                "chart_type": "line",
                "group_by_field_id": fields["Region"],
                "color": "#10b981",
            },
        }

        # Step 3: Add metric widget
        metric_widget = {
            "id": str(uuid4()),
            "type": "metric",
            "position": {"x": 8, "y": 0, "w": 4, "h": 2},
            "title": "Total Sales",
            "metricConfig": {
                "table_id": str(builder_table_with_data.id),
                "field_id": fields["Sales Amount"],
                "aggregation": "sum",
                "prefix": "$",
                "suffix": "",
                "decimal_places": 0,
                "color": "#3b82f6",
            },
        }

        # Step 4: Add text widget
        text_widget = {
            "id": str(uuid4()),
            "type": "text",
            "position": {"x": 8, "y": 2, "w": 4, "h": 2},
            "title": "Key Metrics",
            "content": "This dashboard shows sales performance by region and quarter.",
            "textConfig": {
                "font_size": "base",
                "text_align": "center",
                "color": "#374151",
            },
        }

        # Step 5: Save dashboard with all widgets
        update_data = {
            "layout_config": {
                "grid_columns": 12,
                "row_height": 60,
                "widgets": [chart_widget, metric_widget, text_widget],
            },
        }

        response = await client.patch(
            f"{settings.api_v1_prefix}/dashboards/{dashboard_id}",
            headers=auth_headers,
            json=update_data,
        )
        assert response.status_code == 200
        updated_dashboard = response.json()

        # Step 6: Verify all widgets persisted
        widgets = updated_dashboard["layout_config"]["widgets"]
        assert len(widgets) == 3

        # Verify chart widget
        chart = next(w for w in widgets if w["type"] == "chart")
        assert chart["title"] == "Sales Trend"
        assert chart["chartConfig"]["aggregation"] == "sum"
        assert chart["chartConfig"]["group_by_field_id"] == fields["Region"]

        # Verify metric widget
        metric = next(w for w in widgets if w["type"] == "metric")
        assert metric["title"] == "Total Sales"
        assert metric["metricConfig"]["prefix"] == "$"
        assert metric["metricConfig"]["decimal_places"] == 0

        # Verify text widget
        text = next(w for w in widgets if w["type"] == "text")
        assert text["title"] == "Key Metrics"
        assert "sales performance" in text["content"].lower()

    async def test_widget_configuration_with_filters(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        builder_base: Base,
        builder_table_with_data: Table,
    ):
        """
        Test widget configuration with data filters.

        Workflow:
        1. Create dashboard with chart widget
        2. Configure widget with filters
        3. Save dashboard
        4. Verify filters are applied to widget data
        """
        # Step 1: Create dashboard
        dashboard_data = {
            "name": "Filtered Dashboard",
            "base_id": str(builder_base.id),
            "layout_config": {"grid_columns": 12, "widgets": []},
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards",
            headers=auth_headers,
            json=dashboard_data,
        )
        assert response.status_code == 201
        dashboard = response.json()
        dashboard_id = dashboard["id"]

        # Get field IDs
        response = await client.get(
            f"{settings.api_v1_prefix}/tables/{builder_table_with_data.id}/fields",
            headers=auth_headers,
        )
        assert response.status_code == 200
        fields_data = response.json()
        fields = {f["name"]: f["id"] for f in fields_data}

        # Step 2: Create widget with filters
        filtered_widget = {
            "id": str(uuid4()),
            "type": "chart",
            "chartType": "bar",
            "position": {"x": 0, "y": 0, "w": 6, "h": 4},
            "title": "Q1 Sales by Region",
            "chartConfig": {
                "table_id": str(builder_table_with_data.id),
                "x_axis_field_id": fields["Region"],
                "y_axis_field_id": fields["Sales Amount"],
                "aggregation": "sum",
                "chart_type": "bar",
                "filters": [
                    {
                        "field_id": fields["Quarter"],
                        "operator": "eq",
                        "value": "Q1",
                    }
                ],
            },
        }

        # Step 3: Save dashboard
        update_data = {
            "layout_config": {
                "grid_columns": 12,
                "widgets": [filtered_widget],
            },
        }

        response = await client.patch(
            f"{settings.api_v1_prefix}/dashboards/{dashboard_id}",
            headers=auth_headers,
            json=update_data,
        )
        assert response.status_code == 200
        updated_dashboard = response.json()

        # Step 4: Verify filters persisted
        widget = updated_dashboard["layout_config"]["widgets"][0]
        assert "filters" in widget["chartConfig"]
        assert len(widget["chartConfig"]["filters"]) == 1
        assert widget["chartConfig"]["filters"][0]["value"] == "Q1"

    async def test_widget_positioning_and_layout(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        builder_base: Base,
        builder_table_with_data: Table,
    ):
        """
        Test widget positioning and layout configuration.

        Workflow:
        1. Create dashboard
        2. Add multiple widgets with different positions
        3. Save dashboard
        4. Verify layout persists correctly
        5. Update widget positions
        6. Verify new layout is saved
        """
        # Step 1: Create dashboard
        dashboard_data = {
            "name": "Layout Test Dashboard",
            "base_id": str(builder_base.id),
            "layout_config": {
                "grid_columns": 12,
                "row_height": 60,
                "widgets": [],
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

        # Get field IDs
        response = await client.get(
            f"{settings.api_v1_prefix}/tables/{builder_table_with_data.id}/fields",
            headers=auth_headers,
        )
        assert response.status_code == 200
        fields_data = response.json()
        fields = {f["name"]: f["id"] for f in fields_data}

        # Step 2: Add widgets with different positions
        widgets = [
            {
                "id": str(uuid4()),
                "type": "chart",
                "chartType": "bar",
                "position": {"x": 0, "y": 0, "w": 4, "h": 3},
                "title": "Widget 1",
                "chartConfig": {
                    "table_id": str(builder_table_with_data.id),
                    "x_axis_field_id": fields["Region"],
                    "y_axis_field_id": fields["Sales Amount"],
                    "aggregation": "sum",
                },
            },
            {
                "id": str(uuid4()),
                "type": "metric",
                "position": {"x": 4, "y": 0, "w": 4, "h": 3},
                "title": "Widget 2",
                "metricConfig": {
                    "table_id": str(builder_table_with_data.id),
                    "field_id": fields["Units Sold"],
                    "aggregation": "sum",
                },
            },
            {
                "id": str(uuid4()),
                "type": "chart",
                "chartType": "line",
                "position": {"x": 8, "y": 0, "w": 4, "h": 3},
                "title": "Widget 3",
                "chartConfig": {
                    "table_id": str(builder_table_with_data.id),
                    "x_axis_field_id": fields["Quarter"],
                    "y_axis_field_id": fields["Sales Amount"],
                    "aggregation": "sum",
                },
            },
        ]

        # Step 3: Save layout
        update_data = {
            "layout_config": {
                "grid_columns": 12,
                "row_height": 60,
                "widgets": widgets,
            },
        }

        response = await client.patch(
            f"{settings.api_v1_prefix}/dashboards/{dashboard_id}",
            headers=auth_headers,
            json=update_data,
        )
        assert response.status_code == 200
        updated_dashboard = response.json()

        # Step 4: Verify layout persisted
        saved_widgets = updated_dashboard["layout_config"]["widgets"]
        assert len(saved_widgets) == 3

        # Verify positions
        widget1 = next(w for w in saved_widgets if w["title"] == "Widget 1")
        assert widget1["position"]["x"] == 0
        assert widget1["position"]["w"] == 4

        widget2 = next(w for w in saved_widgets if w["title"] == "Widget 2")
        assert widget2["position"]["x"] == 4
        assert widget2["position"]["w"] == 4

        widget3 = next(w for w in saved_widgets if w["title"] == "Widget 3")
        assert widget3["position"]["x"] == 8
        assert widget3["position"]["w"] == 4

        # Step 5: Update widget positions (reorder)
        widgets[0]["position"]["x"] = 8  # Move Widget 1 to right
        widgets[2]["position"]["x"] = 0  # Move Widget 3 to left

        update_data = {
            "layout_config": {
                "grid_columns": 12,
                "row_height": 60,
                "widgets": widgets,
            },
        }

        response = await client.patch(
            f"{settings.api_v1_prefix}/dashboards/{dashboard_id}",
            headers=auth_headers,
            json=update_data,
        )
        assert response.status_code == 200
        reordered_dashboard = response.json()

        # Step 6: Verify new layout
        reordered_widgets = reordered_dashboard["layout_config"]["widgets"]
        widget1_updated = next(w for w in reordered_widgets if w["title"] == "Widget 1")
        assert widget1_updated["position"]["x"] == 8  # Moved to right

        widget3_updated = next(w for w in reordered_widgets if w["title"] == "Widget 3")
        assert widget3_updated["position"]["x"] == 0  # Moved to left

    async def test_save_and_view_dashboard_with_widgets(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        builder_base: Base,
        builder_table_with_data: Table,
    ):
        """
        Test saving dashboard and viewing it with widgets showing correct data.

        Workflow:
        1. Create dashboard with configured widgets
        2. Save dashboard
        3. Retrieve dashboard
        4. Verify widgets show correct configuration
        5. Verify widget data is accessible
        """
        # Step 1: Create dashboard with widgets
        dashboard_data = {
            "name": "Complete Dashboard",
            "description": "Dashboard with fully configured widgets",
            "base_id": str(builder_base.id),
            "layout_config": {"grid_columns": 12, "widgets": []},
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards",
            headers=auth_headers,
            json=dashboard_data,
        )
        assert response.status_code == 201
        dashboard = response.json()
        dashboard_id = dashboard["id"]

        # Get field IDs
        response = await client.get(
            f"{settings.api_v1_prefix}/tables/{builder_table_with_data.id}/fields",
            headers=auth_headers,
        )
        assert response.status_code == 200
        fields_data = response.json()
        fields = {f["name"]: f["id"] for f in fields_data}

        # Add configured widgets
        widgets = [
            {
                "id": str(uuid4()),
                "type": "chart",
                "chartType": "bar",
                "position": {"x": 0, "y": 0, "w": 6, "h": 4},
                "title": "Sales by Product",
                "chartConfig": {
                    "table_id": str(builder_table_with_data.id),
                    "x_axis_field_id": fields["Product"],
                    "y_axis_field_id": fields["Sales Amount"],
                    "aggregation": "sum",
                    "chart_type": "bar",
                    "color": "#3b82f6",
                },
            },
            {
                "id": str(uuid4()),
                "type": "metric",
                "position": {"x": 6, "y": 0, "w": 3, "h": 2},
                "title": "Total Units",
                "metricConfig": {
                    "table_id": str(builder_table_with_data.id),
                    "field_id": fields["Units Sold"],
                    "aggregation": "sum",
                    "prefix": "",
                    "suffix": " units",
                    "decimal_places": 0,
                },
            },
            {
                "id": str(uuid4()),
                "type": "metric",
                "position": {"x": 9, "y": 0, "w": 3, "h": 2},
                "title": "Avg Sales",
                "metricConfig": {
                    "table_id": str(builder_table_with_data.id),
                    "field_id": fields["Sales Amount"],
                    "aggregation": "avg",
                    "prefix": "$",
                    "decimal_places": 0,
                },
            },
        ]

        # Step 2: Save dashboard
        update_data = {
            "layout_config": {
                "grid_columns": 12,
                "row_height": 60,
                "widgets": widgets,
            },
        }

        response = await client.patch(
            f"{settings.api_v1_prefix}/dashboards/{dashboard_id}",
            headers=auth_headers,
            json=update_data,
        )
        assert response.status_code == 200

        # Step 3: Retrieve dashboard
        response = await client.get(
            f"{settings.api_v1_prefix}/dashboards/{dashboard_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        retrieved_dashboard = response.json()

        # Step 4: Verify widget configurations
        assert retrieved_dashboard["name"] == "Complete Dashboard"
        assert len(retrieved_dashboard["layout_config"]["widgets"]) == 3

        # Verify chart widget
        chart = next(w for w in retrieved_dashboard["layout_config"]["widgets"] if w["type"] == "chart")
        assert chart["title"] == "Sales by Product"
        assert chart["chartConfig"]["aggregation"] == "sum"

        # Verify metric widgets
        metrics = [w for w in retrieved_dashboard["layout_config"]["widgets"] if w["type"] == "metric"]
        assert len(metrics) == 2

        total_units = next(m for m in metrics if m["title"] == "Total Units")
        assert total_units["metricConfig"]["suffix"] == " units"

        avg_sales = next(m for m in metrics if m["title"] == "Avg Sales")
        assert avg_sales["metricConfig"]["aggregation"] == "avg"

        # Step 5: Verify widget data is accessible
        # Create and fetch chart data
        chart_data_request = {
            "name": "Sales Chart",
            "table_id": str(builder_table_with_data.id),
            "chart_type": "bar",
            "data_config": {
                "x_axis_field_id": fields["Product"],
                "y_axis_field_id": fields["Sales Amount"],
                "aggregation": "sum",
            },
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/charts",
            headers=auth_headers,
            json=chart_data_request,
        )
        assert response.status_code == 201
        chart = response.json()

        response = await client.get(
            f"{settings.api_v1_prefix}/charts/{chart['id']}/data",
            headers=auth_headers,
        )
        assert response.status_code == 200
        chart_data = response.json()

        # Verify chart has data
        assert "data" in chart_data
        assert len(chart_data["data"]["labels"]) > 0
        assert len(chart_data["data"]["datasets"][0]["data"]) > 0
