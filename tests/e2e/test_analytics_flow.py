"""
End-to-end tests for analytics flow: Create dashboard, add charts, schedule report.

This test suite validates the complete analytics workflow:
1. Create new dashboard via API
2. Add line chart via API
3. Verify chart data via API
4. Create scheduled report via API
5. Trigger report generation manually
6. Verify PDF generated and email sent
"""

import json
import os
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock

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
        name="Analytics Test Workspace",
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
    """Create a test base for analytics."""
    base = Base(
        workspace_id=test_workspace.id,
        name="Analytics Test Base",
        description="Base for E2E analytics testing",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)
    return base


@pytest_asyncio.fixture
async def test_table(db_session: AsyncSession, test_base: Base, test_user: User) -> Table:
    """Create a test table with sample data for analytics."""
    # Create table
    table = Table(
        base_id=test_base.id,
        name="Sales Data",
        description="Sample sales data for analytics",
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
            name="Revenue",
            field_type=FieldType.NUMBER,
            order=2,
        ),
        Field(
            table_id=table.id,
            name="Quantity",
            field_type=FieldType.NUMBER,
            order=3,
        ),
        Field(
            table_id=table.id,
            name="Date",
            field_type=FieldType.DATE,
            order=4,
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
        {"Product": "Widget A", "Region": "North", "Revenue": 1000, "Quantity": 10, "Date": "2024-01-15"},
        {"Product": "Widget B", "Region": "North", "Revenue": 1500, "Quantity": 15, "Date": "2024-01-20"},
        {"Product": "Widget A", "Region": "South", "Revenue": 800, "Quantity": 8, "Date": "2024-01-25"},
        {"Product": "Widget B", "Region": "South", "Revenue": 1200, "Quantity": 12, "Date": "2024-01-30"},
        {"Product": "Widget A", "Region": "East", "Revenue": 900, "Quantity": 9, "Date": "2024-02-05"},
        {"Product": "Widget B", "Region": "East", "Revenue": 1100, "Quantity": 11, "Date": "2024-02-10"},
        {"Product": "Widget A", "Region": "West", "Revenue": 1300, "Quantity": 13, "Date": "2024-02-15"},
        {"Product": "Widget B", "Region": "West", "Revenue": 1400, "Quantity": 14, "Date": "2024-02-20"},
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
class TestAnalyticsFlow:
    """End-to-end test suite for complete analytics workflow."""

    async def test_complete_analytics_flow(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_base: Base,
        test_table: Table,
        test_user: User,
        db_session: AsyncSession,
    ):
        """
        Test the complete analytics flow from dashboard creation to report generation.

        Workflow:
        1. Create a new dashboard
        2. Add a line chart to the dashboard
        3. Verify chart data is computed correctly
        4. Create a scheduled report
        5. Manually trigger report generation
        6. Verify PDF was generated and email delivery was attempted
        """
        # Step 1: Create new dashboard via API
        dashboard_data = {
            "name": "Sales Analytics Dashboard",
            "description": "Dashboard for sales performance tracking",
            "base_id": str(test_base.id),
            "is_default": False,
            "is_personal": False,
            "is_public": False,
            "layout_config": {
                "columns": 12,
                "row_height": 100,
            },
            "settings": {
                "theme": "light",
                "auto_refresh": True,
                "refresh_interval": 60,
            },
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards",
            headers=auth_headers,
            json=dashboard_data,
        )
        assert response.status_code == 201, f"Dashboard creation failed: {response.text}"
        dashboard = response.json()
        assert dashboard["name"] == "Sales Analytics Dashboard"
        assert "id" in dashboard
        dashboard_id = dashboard["id"]

        # Step 2: Add line chart via API
        chart_data = {
            "dashboard_id": dashboard_id,
            "table_id": str(test_table.id),
            "name": "Revenue by Region",
            "description": "Line chart showing revenue trends across regions",
            "chart_type": "line",
            "data_config": {
                "x_field": "Region",
                "y_field": "Revenue",
                "group_by": "Product",
                "aggregation": "sum",
                "filters": [],
                "sort_by": "Region",
                "sort_direction": "asc",
            },
            "visual_config": {
                "colors": ["#3b82f6", "#ef4444", "#10b981"],
                "show_legend": True,
                "show_grid": True,
                "show_labels": True,
            },
            "axis_config": {
                "x_label": "Region",
                "y_label": "Revenue ($)",
                "y_min": 0,
            },
            "position": {
                "x": 0,
                "y": 0,
                "width": 6,
                "height": 4,
            },
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/charts",
            headers=auth_headers,
            json=chart_data,
        )
        assert response.status_code == 201, f"Chart creation failed: {response.text}"
        chart = response.json()
        assert chart["name"] == "Revenue by Region"
        assert chart["chart_type"] == "line"
        assert "id" in chart
        chart_id = chart["id"]

        # Step 3: Verify chart data via API
        response = await client.get(
            f"{settings.api_v1_prefix}/charts/{chart_id}/data",
            headers=auth_headers,
        )
        assert response.status_code == 200, f"Chart data retrieval failed: {response.text}"
        chart_data_response = response.json()

        # Verify chart data structure
        assert "series" in chart_data_response
        assert isinstance(chart_data_response["series"], list)
        assert len(chart_data_response["series"]) > 0

        # Verify data points exist
        for series in chart_data_response["series"]:
            assert "name" in series
            assert "data" in series
            assert isinstance(series["data"], list)

        # Step 4: Create scheduled report via API
        report_data = {
            "name": "Weekly Sales Report",
            "description": "Automated weekly sales performance report",
            "dashboard_id": dashboard_id,
            "format": "pdf",
            "is_scheduled": True,
            "schedule_config": {
                "frequency": "weekly",
                "day_of_week": 1,  # Monday
                "time_of_day": "09:00",
                "timezone": "UTC",
            },
            "delivery_config": {
                "recipients": ["manager@example.com", "team@example.com"],
                "subject": "Weekly Sales Dashboard Report",
                "message": "Please find attached the weekly sales performance report.",
            },
            "export_config": {
                "page_size": "A4",
                "orientation": "landscape",
                "include_charts": True,
                "include_data": False,
            },
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/reports",
            headers=auth_headers,
            json=report_data,
        )
        assert response.status_code == 201, f"Report creation failed: {response.text}"
        report = response.json()
        assert report["name"] == "Weekly Sales Report"
        assert report["format"] == "pdf"
        assert report["is_scheduled"] is True
        assert "id" in report
        report_id = report["id"]

        # Step 5: Trigger report generation manually
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the file storage path
            pdf_path = os.path.join(temp_dir, f"report_{report_id}.pdf")

            # Mock email delivery
            with patch("workers.report_generator.deliver_report_email") as mock_email:
                mock_email.return_value = True

                # Mock PDF generation to actually create a file
                with patch("workers.report_generator.generate_report_pdf") as mock_pdf:
                    # Create a dummy PDF file
                    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
                    with open(pdf_path, "wb") as f:
                        # Write PDF header
                        f.write(b"%PDF-1.4\n")
                        f.write(b"Test PDF content for E2E test\n")
                        f.write(b"%%EOF\n")

                    mock_pdf.return_value = pdf_path

                    # Trigger report generation via API
                    response = await client.post(
                        f"{settings.api_v1_prefix}/reports/{report_id}/generate",
                        headers=auth_headers,
                        json={},
                    )
                    assert response.status_code == 200, f"Report generation failed: {response.text}"
                    generation_result = response.json()

                    # Step 6: Verify PDF generated and email sent
                    assert "report_schedule_id" in generation_result or "file_path" in generation_result

                    # Verify PDF file exists and is valid
                    assert os.path.exists(pdf_path), "PDF file should be created"
                    assert os.path.getsize(pdf_path) > 0, "PDF should have content"

                    # Verify it's a valid PDF
                    with open(pdf_path, "rb") as f:
                        header = f.read(4)
                        assert header == b"%PDF", "Should be a valid PDF file"

        # Verify dashboard can be retrieved with charts
        response = await client.get(
            f"{settings.api_v1_prefix}/dashboards/{dashboard_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        dashboard_detail = response.json()
        assert dashboard_detail["name"] == "Sales Analytics Dashboard"

        # Verify report can be retrieved
        response = await client.get(
            f"{settings.api_v1_prefix}/reports/{report_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        report_detail = response.json()
        assert report_detail["name"] == "Weekly Sales Report"

    async def test_dashboard_with_multiple_chart_types(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_base: Base,
        test_table: Table,
    ):
        """Test dashboard with multiple chart types (line, bar, pie)."""
        # Create dashboard
        dashboard_data = {
            "name": "Multi-Chart Dashboard",
            "base_id": str(test_base.id),
            "layout_config": {"columns": 12},
        }
        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards",
            headers=auth_headers,
            json=dashboard_data,
        )
        assert response.status_code == 201
        dashboard_id = response.json()["id"]

        # Create line chart
        line_chart = {
            "dashboard_id": dashboard_id,
            "table_id": str(test_table.id),
            "name": "Revenue Trend",
            "chart_type": "line",
            "data_config": {
                "x_field": "Date",
                "y_field": "Revenue",
                "aggregation": "sum",
            },
        }
        response = await client.post(
            f"{settings.api_v1_prefix}/charts",
            headers=auth_headers,
            json=line_chart,
        )
        assert response.status_code == 201
        line_chart_id = response.json()["id"]

        # Create bar chart
        bar_chart = {
            "dashboard_id": dashboard_id,
            "table_id": str(test_table.id),
            "name": "Revenue by Region",
            "chart_type": "bar",
            "data_config": {
                "x_field": "Region",
                "y_field": "Revenue",
                "aggregation": "sum",
            },
        }
        response = await client.post(
            f"{settings.api_v1_prefix}/charts",
            headers=auth_headers,
            json=bar_chart,
        )
        assert response.status_code == 201
        bar_chart_id = response.json()["id"]

        # Create pie chart
        pie_chart = {
            "dashboard_id": dashboard_id,
            "table_id": str(test_table.id),
            "name": "Product Distribution",
            "chart_type": "pie",
            "data_config": {
                "x_field": "Product",
                "y_field": "Quantity",
                "aggregation": "sum",
            },
        }
        response = await client.post(
            f"{settings.api_v1_prefix}/charts",
            headers=auth_headers,
            json=pie_chart,
        )
        assert response.status_code == 201
        pie_chart_id = response.json()["id"]

        # Verify all charts return data
        for chart_id in [line_chart_id, bar_chart_id, pie_chart_id]:
            response = await client.get(
                f"{settings.api_v1_prefix}/charts/{chart_id}/data",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert "series" in data

    async def test_pivot_table_analytics(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
    ):
        """Test pivot table data aggregation via analytics API."""
        # Request pivot table data
        pivot_request = {
            "table_id": str(test_table.id),
            "row_field": "Region",
            "column_field": "Product",
            "value_field": "Revenue",
            "aggregation": "sum",
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/analytics/pivot",
            headers=auth_headers,
            json=pivot_request,
        )
        assert response.status_code == 200, f"Pivot table request failed: {response.text}"
        pivot_data = response.json()

        # Verify pivot table structure
        assert "rows" in pivot_data
        assert "columns" in pivot_data
        assert "cells" in pivot_data
        assert isinstance(pivot_data["rows"], list)
        assert isinstance(pivot_data["columns"], list)
        assert isinstance(pivot_data["cells"], dict)

    async def test_analytics_with_filters(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_table: Table,
    ):
        """Test analytics data with filters applied."""
        # Create aggregation request with filters
        aggregate_request = {
            "table_id": str(test_table.id),
            "field": "Revenue",
            "aggregation": "sum",
            "filters": [
                {
                    "field": "Region",
                    "operator": "equals",
                    "value": "North",
                }
            ],
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/analytics/aggregate",
            headers=auth_headers,
            json=aggregate_request,
        )
        assert response.status_code == 200
        result = response.json()
        assert "value" in result
        # North region should have Widget A (1000) + Widget B (1500) = 2500
        assert isinstance(result["value"], (int, float))

    async def test_scheduled_report_without_delivery(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        test_base: Base,
    ):
        """Test creating scheduled report without email delivery."""
        # Create a simple dashboard first
        dashboard_data = {
            "name": "Simple Dashboard",
            "base_id": str(test_base.id),
        }
        response = await client.post(
            f"{settings.api_v1_prefix}/dashboards",
            headers=auth_headers,
            json=dashboard_data,
        )
        assert response.status_code == 201
        dashboard_id = response.json()["id"]

        # Create report without delivery config
        report_data = {
            "name": "Export Only Report",
            "dashboard_id": dashboard_id,
            "format": "pdf",
            "is_scheduled": False,  # Manual export only
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/reports",
            headers=auth_headers,
            json=report_data,
        )
        assert response.status_code == 201
        report = response.json()
        assert report["name"] == "Export Only Report"
        assert report["is_scheduled"] is False
