"""
Integration tests for Export API endpoints.

Tests all 6 export endpoints including synchronous export, background jobs,
job status retrieval, file downloads, and scheduled exports.
"""

import io
import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from pybase.core.config import settings
from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.view import View
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.models.export_job import ExportJob, ExportJobStatus
from pybase.models.user import User


@pytest.mark.asyncio
async def test_export_records_csv_format(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    test_user: User
):
    """Test synchronous export to CSV format."""
    # Setup workspace, base, and table
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    await db_session.commit()

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Test Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    field = Field(
        table_id=table.id,
        name="Name",
        field_type=FieldType.TEXT.value
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    record = Record(
        table_id=table.id,
        data=f'{{"{field.id}": "Alice"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id
    )
    db_session.add(record)
    await db_session.commit()

    # Export to CSV
    response = await client.post(
        f"{settings.api_v1_prefix}/tables/{table.id}/records/export",
        headers=auth_headers,
        params={"format": "csv"}
    )

    # Verify response
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    csv_data = response.text
    assert "Name" in csv_data
    assert "Alice" in csv_data


@pytest.mark.asyncio
async def test_export_records_json_format(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    test_user: User
):
    """Test synchronous export to JSON format."""
    # Setup
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    await db_session.commit()

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Test Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    field = Field(
        table_id=table.id,
        name="Name",
        field_type=FieldType.TEXT.value
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    record = Record(
        table_id=table.id,
        data=f'{{"{field.id}": "Alice"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id
    )
    db_session.add(record)
    await db_session.commit()

    # Export to JSON
    response = await client.post(
        f"{settings.api_v1_prefix}/tables/{table.id}/records/export",
        headers=auth_headers,
        params={"format": "json"}
    )

    # Verify response
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json; charset=utf-8"
    json_data = response.json()
    assert isinstance(json_data, list)
    assert len(json_data) == 1
    assert json_data[0]["Name"] == "Alice"


@pytest.mark.asyncio
async def test_export_records_with_field_selection(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    test_user: User
):
    """Test export with specific field selection."""
    # Setup
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    await db_session.commit()

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Test Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    field1 = Field(
        table_id=table.id,
        name="Name",
        field_type=FieldType.TEXT.value
    )
    db_session.add(field1)
    await db_session.commit()
    await db_session.refresh(field1)

    field2 = Field(
        table_id=table.id,
        name="Email",
        field_type=FieldType.TEXT.value
    )
    db_session.add(field2)
    await db_session.commit()
    await db_session.refresh(field2)

    record = Record(
        table_id=table.id,
        data=f'{{"{field1.id}": "Alice", "{field2.id}": "alice@example.com"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id
    )
    db_session.add(record)
    await db_session.commit()

    # Export only first field
    response = await client.post(
        f"{settings.api_v1_prefix}/tables/{table.id}/records/export",
        headers=auth_headers,
        params={
            "format": "csv",
            "field_ids": str(field1.id)
        }
    )

    # Verify only selected field is exported
    assert response.status_code == 200
    csv_data = response.text
    assert "Name" in csv_data
    assert "Email" not in csv_data


@pytest.mark.asyncio
async def test_export_records_with_view_filters(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    test_user: User
):
    """Test export applies view filter conditions."""
    # Setup
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    await db_session.commit()

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Test Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    field = Field(
        table_id=table.id,
        name="Status",
        field_type=FieldType.TEXT.value
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create records with different statuses
    record1 = Record(
        table_id=table.id,
        data=f'{{"{field.id}": "active"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id
    )
    db_session.add(record1)

    record2 = Record(
        table_id=table.id,
        data=f'{{"{field.id}": "inactive"}}',
        created_by_id=test_user.id,
        last_modified_by_id=test_user.id
    )
    db_session.add(record2)
    await db_session.commit()

    # Create view with filter
    view = View(
        table_id=table.id,
        name="Active View",
        filters=json.dumps([{
            "field_id": str(field.id),
            "operator": "equals",
            "value": "active"
        }])
    )
    db_session.add(view)
    await db_session.commit()
    await db_session.refresh(view)

    # Export with view filter
    response = await client.post(
        f"{settings.api_v1_prefix}/tables/{table.id}/records/export",
        headers=auth_headers,
        params={
            "format": "csv",
            "view_id": str(view.id)
        }
    )

    # Verify only active records exported
    assert response.status_code == 200
    csv_data = response.text
    assert "active" in csv_data
    assert "inactive" not in csv_data


@pytest.mark.asyncio
async def test_create_background_export_job(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    test_user: User
):
    """Test creating background export job via POST /exports."""
    # Setup
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    await db_session.commit()

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Test Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create background export job
    response = await client.post(
        f"{settings.api_v1_prefix}/exports",
        headers=auth_headers,
        json={
            "table_id": str(table.id),
            "format": "csv"
        }
    )

    # Verify response
    assert response.status_code == 201
    result = response.json()
    assert "id" in result
    assert "status" in result
    assert result["status"] == "pending"

    job_id = result["id"]

    # Verify job in database
    stmt = select(ExportJob).where(ExportJob.id == job_id)
    job_result = await db_session.execute(stmt)
    job = job_result.scalar_one_or_none()

    assert job is not None
    assert job.status == ExportJobStatus.PENDING
    assert job.table_id == str(table.id)


@pytest.mark.asyncio
async def test_get_export_job_status(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    test_user: User
):
    """Test getting export job status via GET /exports/{job_id}."""
    # Setup
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    await db_session.commit()

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Test Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create job
    job = ExportJob(
        user_id=str(test_user.id),
        table_id=str(table.id),
        export_format="csv",
        status=ExportJobStatus.PENDING
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Get job status
    response = await client.get(
        f"{settings.api_v1_prefix}/exports/{job.id}",
        headers=auth_headers
    )

    # Verify response
    assert response.status_code == 200
    result = response.json()
    assert result["id"] == str(job.id)
    assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_get_export_job_status_not_found(
    client: AsyncClient,
    auth_headers: dict[str, str]
):
    """Test getting non-existent job returns 404."""
    fake_job_id = uuid4()

    response = await client.get(
        f"{settings.api_v1_prefix}/exports/{fake_job_id}",
        headers=auth_headers
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_export_job_status_permission_denied(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    test_user: User
):
    """Test getting job owned by another user returns 403."""
    # Create job owned by different user
    other_user = User(
        email="other@example.com",
        hashed_password="hash",
        name="Other User"
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    workspace = Workspace(owner_id=other_user.id, name="Other Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(workspace_id=workspace.id, name="Other Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Other Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    job = ExportJob(
        user_id=str(other_user.id),
        table_id=str(table.id),
        export_format="csv",
        status=ExportJobStatus.PENDING
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Try to get job status as different user
    response = await client.get(
        f"{settings.api_v1_prefix}/exports/{job.id}",
        headers=auth_headers
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_download_export_file(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    test_user: User,
    tmp_path
):
    """Test downloading completed export file via GET /exports/{job_id}/download."""
    # Setup
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    await db_session.commit()

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Test Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create completed job with file
    export_file = tmp_path / "export.csv"
    export_file.write_text("Name\nAlice")

    job = ExportJob(
        user_id=str(test_user.id),
        table_id=str(table.id),
        export_format="csv",
        status=ExportJobStatus.COMPLETED,
        file_path=str(export_file)
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Download file
    response = await client.get(
        f"{settings.api_v1_prefix}/exports/{job.id}/download",
        headers=auth_headers
    )

    # Verify response
    assert response.status_code == 200
    assert "Name" in response.text
    assert "Alice" in response.text


@pytest.mark.asyncio
async def test_download_export_file_pending_job(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    test_user: User
):
    """Test downloading file from pending job returns 403."""
    # Setup
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    await db_session.commit()

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Test Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create pending job
    job = ExportJob(
        user_id=str(test_user.id),
        table_id=str(table.id),
        export_format="csv",
        status=ExportJobStatus.PENDING
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Try to download
    response = await client.get(
        f"{settings.api_v1_prefix}/exports/{job.id}/download",
        headers=auth_headers
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_scheduled_export(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    test_user: User
):
    """Test creating scheduled export via POST /scheduled-exports."""
    # Setup
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    await db_session.commit()

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Test Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create scheduled export
    response = await client.post(
        f"{settings.api_v1_prefix}/scheduled-exports",
        headers=auth_headers,
        json={
            "table_id": str(table.id),
            "schedule": "0 0 * * 0",  # Weekly
            "format": "csv",
            "storage_config": {
                "type": "s3",
                "bucket": "exports",
                "region": "us-east-1"
            }
        }
    )

    # Verify response
    assert response.status_code == 201
    result = response.json()
    assert "id" in result
    assert "schedule" in result
    assert result["schedule"] == "0 0 * * 0"


@pytest.mark.asyncio
async def test_export_invalid_format(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    test_user: User
):
    """Test export with invalid format returns error."""
    # Setup
    workspace = Workspace(owner_id=test_user.id, name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER
    )
    db_session.add(member)
    await db_session.commit()

    base = Base(workspace_id=workspace.id, name="Test Base")
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(base_id=base.id, name="Test Table")
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Try invalid format
    response = await client.post(
        f"{settings.api_v1_prefix}/tables/{table.id}/records/export",
        headers=auth_headers,
        params={"format": "invalid_format"}
    )

    # Should return 400 or 422 for invalid format
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_export_invalid_table_id(
    client: AsyncClient,
    auth_headers: dict[str, str]
):
    """Test export with invalid table ID returns 404."""
    fake_table_id = uuid4()

    response = await client.post(
        f"{settings.api_v1_prefix}/tables/{fake_table_id}/records/export",
        headers=auth_headers,
        params={"format": "csv"}
    )

    assert response.status_code == 404
