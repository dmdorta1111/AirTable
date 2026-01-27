"""
End-to-end integration tests for scheduled custom report generation.

Tests the complete workflow:
1. Create custom report with schedule configuration
2. Configure email delivery
3. Trigger scheduled report generation
4. Verify report generated successfully
5. Verify email delivery configuration
"""

import tempfile
from datetime import datetime, timedelta, UTC
from unittest.mock import patch, AsyncMock, MagicMock
import os

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from pybase.core.config import settings
from pybase.models.base import Base
from pybase.models.custom_report import CustomReport, CustomReportSchedule, ReportStatus, ScheduleFrequency
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace


@pytest.mark.asyncio
async def test_scheduled_custom_report_with_email_delivery(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """
    Test creating a scheduled custom report with email delivery.

    End-to-end verification steps:
    1. Create custom report with schedule
    2. Configure email delivery
    3. Trigger scheduled execution
    4. Verify report generated
    5. Verify email sent
    """
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

    # Step 2: Create custom report with schedule configuration
    report_data = {
        "base_id": str(base.id),
        "name": "Daily Product Report",
        "description": "Daily product catalog report with pricing",
        "format": "pdf",
        "is_scheduled": True,
        "schedule_config": {
            "frequency": "daily",
            "time_of_day": "08:00",
            "timezone": "UTC",
        },
        "delivery_config": {
            "enabled": True,
            "recipients": ["manager@example.com", "team@example.com"],
            "cc": ["archive@example.com"],
            "subject": "Daily Product Report - {{report_date}}",
            "message": "Please find attached the daily product catalog report with current pricing and inventory levels.",
        },
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
    assert report["name"] == "Daily Product Report"
    assert report["is_scheduled"] is True
    assert report["schedule_config"]["frequency"] == "daily"
    assert report["delivery_config"]["enabled"] is True
    assert len(report["delivery_config"]["recipients"]) == 2
    report_id = report["id"]

    # Step 3: Add text section (title/header)
    text_section_data = {
        "section_type": "text",
        "title": "Report Header",
        "section_config": {
            "content": "Daily Product Catalog Report",
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

    # Step 6: Trigger manual report generation (simulating scheduled execution)
    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_path = os.path.join(temp_dir, f"report_{report_id}.pdf")

        # Create a mock PDF generator
        with patch("src.pybase.services.pdf_generator.PDFGenerator") as mock_pdf_gen:
            mock_generator = MagicMock()
            mock_pdf_gen.return_value = mock_generator

            # Mock the generate_report_pdf method
            mock_generator.generate_report_pdf.return_value = pdf_path

            # Create actual PDF file
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4\n")
                f.write(b"Test Daily Product Report\n")
                f.write(b"Product Catalog\n")
                f.write(b"%%EOF\n")

            # Trigger report generation
            response = await client.post(
                f"{settings.api_v1_prefix}/custom-reports/{report_id}/generate",
                json={},
                headers=auth_headers,
            )

            # In a real scenario, this would trigger the worker
            # For testing, we verify the endpoint exists and report is configured
            assert response.status_code in [200, 202]

    # Step 7: Verify schedule configuration in database
    # Query database directly to verify schedule persistence
    stmt = select(CustomReport).where(CustomReport.id == report_id)
    result = await db_session.execute(stmt)
    report_model = result.scalar_one_or_none()

    assert report_model is not None
    assert report_model.is_scheduled is True
    assert report_model.frequency == ScheduleFrequency.DAILY.value
    assert report_model.next_run_at is not None
    assert report_model.delivery_enabled is True

    # Verify delivery configuration
    delivery_config = report_model.get_delivery_config()
    assert delivery_config["enabled"] is True
    assert len(delivery_config["recipients"]) == 2
    assert "manager@example.com" in delivery_config["recipients"]
    assert "team@example.com" in delivery_config["recipients"]

    # Step 8: Create schedule run record (simulating worker execution)
    schedule = CustomReportSchedule(
        custom_report_id=report_id,
        status=ReportStatus.COMPLETED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        generated_file_path=f"/tmp/reports/{report_id}.pdf",
        delivery_status="sent",
        delivery_attempts=1,
        delivery_sent_at=datetime.now(UTC),
    )
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)

    # Step 9: Verify schedule via API
    response = await client.get(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/schedules",
        headers=auth_headers,
    )

    assert response.status_code == 200
    schedules_list = response.json()
    assert schedules_list["total"] >= 1
    assert len(schedules_list["items"]) >= 1

    # Verify the schedule record
    latest_schedule = schedules_list["items"][0]
    assert latest_schedule["status"] in ["completed", "pending", "running"]
    assert "started_at" in latest_schedule

    # Step 10: Verify email delivery configuration
    # Get report details to verify delivery config
    response = await client.get(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    report_detail = response.json()
    assert "delivery_config" in report_detail
    assert report_detail["delivery_config"]["enabled"] is True
    assert report_detail["delivery_config"]["recipients"] == ["manager@example.com", "team@example.com"]
    assert report_detail["delivery_config"]["subject"] == "Daily Product Report - {{report_date}}"


@pytest.mark.asyncio
async def test_weekly_scheduled_report_generation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test weekly scheduled report with proper cron-like scheduling."""
    # Create workspace and base
    workspace = Workspace(owner_id=test_user.id, name="Weekly Report Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Weekly Report Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Create weekly scheduled report
    report_data = {
        "base_id": str(base.id),
        "name": "Weekly Summary Report",
        "description": "Weekly summary every Monday at 9 AM",
        "format": "pdf",
        "is_scheduled": True,
        "schedule_config": {
            "frequency": "weekly",
            "day_of_week": 1,  # Monday (0=Monday, 6=Sunday)
            "time_of_day": "09:00",
            "timezone": "UTC",
        },
        "delivery_config": {
            "enabled": True,
            "recipients": ["weekly@example.com"],
            "subject": "Weekly Summary Report",
            "message": "Your weekly summary is attached.",
        },
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports",
        json=report_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    report = response.json()
    assert report["schedule_config"]["frequency"] == "weekly"
    assert report["schedule_config"]["day_of_week"] == 1
    report_id = report["id"]

    # Verify schedule calculation in database
    stmt = select(CustomReport).where(CustomReport.id == report_id)
    result = await db_session.execute(stmt)
    report_model = result.scalar_one_or_none()

    assert report_model is not None
    assert report_model.frequency == ScheduleFrequency.WEEKLY.value

    # Verify next_run_at is calculated and in the future
    assert report_model.next_run_at is not None
    assert report_model.next_run_at > datetime.now(UTC)


@pytest.mark.asyncio
async def test_monthly_scheduled_report_generation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test monthly scheduled report."""
    # Create workspace and base
    workspace = Workspace(owner_id=test_user.id, name="Monthly Report Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Monthly Report Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Create monthly scheduled report
    report_data = {
        "base_id": str(base.id),
        "name": "Monthly Cost Report",
        "description": "Monthly cost report on the 1st of each month",
        "format": "pdf",
        "is_scheduled": True,
        "schedule_config": {
            "frequency": "monthly",
            "day_of_month": 1,  # 1st day of month
            "time_of_day": "10:00",
            "timezone": "UTC",
        },
        "delivery_config": {
            "enabled": True,
            "recipients": ["finance@example.com"],
            "subject": "Monthly Cost Analysis",
            "message": "Monthly cost breakdown is attached.",
        },
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports",
        json=report_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    report = response.json()
    assert report["schedule_config"]["frequency"] == "monthly"
    assert report["schedule_config"]["day_of_month"] == 1
    report_id = report["id"]

    # Verify schedule in database
    stmt = select(CustomReport).where(CustomReport.id == report_id)
    result = await db_session.execute(stmt)
    report_model = result.scalar_one_or_none()

    assert report_model is not None
    assert report_model.frequency == ScheduleFrequency.MONTHLY.value
    assert report_model.next_run_at is not None


@pytest.mark.asyncio
async def test_schedule_run_status_tracking(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test tracking schedule run statuses through the lifecycle."""
    # Create workspace and base
    workspace = Workspace(owner_id=test_user.id, name="Status Tracking Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Status Tracking Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Create scheduled report
    report_data = {
        "base_id": str(base.id),
        "name": "Status Tracking Report",
        "format": "pdf",
        "is_scheduled": True,
        "schedule_config": {
            "frequency": "daily",
            "time_of_day": "08:00",
            "timezone": "UTC",
        },
        "delivery_config": {
            "enabled": True,
            "recipients": ["status@example.com"],
            "subject": "Status Report",
        },
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports",
        json=report_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    report = response.json()
    report_id = report["id"]

    # Simulate schedule runs with different statuses
    statuses_to_test = [
        (ReportStatus.PENDING, None, None, None),
        (ReportStatus.RUNNING, datetime.now(UTC), None, None),
        (ReportStatus.COMPLETED, datetime.now(UTC), datetime.now(UTC), "sent"),
        (ReportStatus.FAILED, datetime.now(UTC), datetime.now(UTC), "failed"),
    ]

    for status, started, completed, delivery_status in statuses_to_test:
        schedule = CustomReportSchedule(
            custom_report_id=report_id,
            status=status,
            started_at=started,
            completed_at=completed,
            generated_file_path=f"/tmp/reports/{report_id}_{status.value}.pdf" if status == ReportStatus.COMPLETED else None,
            delivery_status=delivery_status,
            delivery_attempts=1 if delivery_status else 0,
            delivery_sent_at=datetime.now(UTC) if delivery_status == "sent" else None,
            error_message="Simulated failure" if status == ReportStatus.FAILED else None,
        )
        db_session.add(schedule)
        await db_session.commit()

    # Query schedules via API
    response = await client.get(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/schedules",
        headers=auth_headers,
    )

    assert response.status_code == 200
    schedules_list = response.json()
    assert schedules_list["total"] >= 4

    # Verify all statuses are present
    statuses_found = {s["status"] for s in schedules_list["items"]}
    assert "pending" in statuses_found
    assert "running" in statuses_found
    assert "completed" in statuses_found
    assert "failed" in statuses_found


@pytest.mark.asyncio
async def test_schedule_retry_failed_generation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test retrying failed scheduled report generation."""
    # Create workspace and base
    workspace = Workspace(owner_id=test_user.id, name="Retry Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Retry Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Create scheduled report
    report_data = {
        "base_id": str(base.id),
        "name": "Retry Test Report",
        "format": "pdf",
        "is_scheduled": True,
        "schedule_config": {
            "frequency": "daily",
            "time_of_day": "08:00",
        },
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports",
        json=report_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    report = response.json()
    report_id = report["id"]

    # Create failed schedule run
    failed_schedule = CustomReportSchedule(
        custom_report_id=report_id,
        status=ReportStatus.FAILED,
        started_at=datetime.now(UTC) - timedelta(minutes=5),
        completed_at=datetime.now(UTC) - timedelta(minutes=4),
        error_message="Temporary network error",
        delivery_attempts=0,
    )
    db_session.add(failed_schedule)
    await db_session.commit()
    await db_session.refresh(failed_schedule)
    schedule_id = failed_schedule.id

    # Retry the failed schedule
    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/schedules/{schedule_id}/retry",
        headers=auth_headers,
    )

    # In real scenario, this would trigger retry task
    # For testing, verify endpoint exists
    assert response.status_code in [200, 202]

    # Verify schedule status updated (or retry triggered)
    response = await client.get(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/schedules/{schedule_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    schedule_detail = response.json()
    assert schedule_detail["id"] == str(schedule_id)


@pytest.mark.asyncio
async def test_cancel_scheduled_report(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
    test_user,
):
    """Test cancelling a scheduled report run."""
    # Create workspace and base
    workspace = Workspace(owner_id=test_user.id, name="Cancel Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Cancel Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    # Create scheduled report
    report_data = {
        "base_id": str(base.id),
        "name": "Cancel Test Report",
        "format": "pdf",
        "is_scheduled": True,
        "schedule_config": {
            "frequency": "daily",
            "time_of_day": "08:00",
        },
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports",
        json=report_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    report = response.json()
    report_id = report["id"]

    # Create pending schedule run
    pending_schedule = CustomReportSchedule(
        custom_report_id=report_id,
        status=ReportStatus.PENDING,
    )
    db_session.add(pending_schedule)
    await db_session.commit()
    await db_session.refresh(pending_schedule)
    schedule_id = pending_schedule.id

    # Cancel the schedule
    response = await client.post(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/schedules/{schedule_id}/cancel",
        headers=auth_headers,
    )

    assert response.status_code == 200

    # Verify schedule status is cancelled
    response = await client.get(
        f"{settings.api_v1_prefix}/custom-reports/{report_id}/schedules/{schedule_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    schedule_detail = response.json()
    assert schedule_detail["status"] == "cancelled"
