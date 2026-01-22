"""
Integration tests for extraction import endpoint.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.field import Field, FieldType
from pybase.models.table import Table
from pybase.models.user import User
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.extraction import ExtractionFormat, JobStatus


@pytest.mark.asyncio
async def test_import_extracted_data_success(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test successful import of extracted data."""
    # Create workspace, base, table, and field
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add user as workspace member
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

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

    field = Field(
        table_id=table.id,
        name="dimension",
        field_type=FieldType.TEXT.value,
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create a completed extraction job with mock result
    job_id = uuid4()
    extraction_result = {
        "source_file": "test.pdf",
        "source_type": "pdf",
        "success": True,
        "tables": [
            {
                "headers": ["dimension", "value"],
                "rows": [
                    ["Length", "100mm"],
                    ["Width", "50mm"],
                ],
                "page": 1,
                "confidence": 0.95,
            }
        ],
        "dimensions": [],
        "text_blocks": [],
        "errors": [],
        "warnings": [],
    }

    # Store job in mock job storage (imported from extraction endpoint)
    from pybase.api.v1.extraction import _jobs

    _jobs[str(job_id)] = {
        "id": job_id,
        "status": JobStatus.COMPLETED,
        "format": ExtractionFormat.PDF,
        "filename": "test.pdf",
        "file_size": 1024,
        "options": {},
        "target_table_id": table.id,
        "progress": 100,
        "result": extraction_result,
        "error_message": None,
        "created_at": datetime.now(timezone.utc),
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    }

    # Import the data
    response = await client.post(
        "/api/v1/extraction/import",
        json={
            "job_id": str(job_id),
            "table_id": str(table.id),
            "field_mapping": {"dimension": str(field.id)},
            "create_missing_fields": False,
            "skip_errors": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["records_imported"] == 2
    assert data["records_failed"] == 0


@pytest.mark.asyncio
async def test_import_job_not_found(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test import with non-existent job."""
    # Create workspace, base, and table
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

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

    response = await client.post(
        "/api/v1/extraction/import",
        json={
            "job_id": str(uuid4()),
            "table_id": str(table.id),
            "field_mapping": {},
            "create_missing_fields": False,
            "skip_errors": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_import_job_not_completed(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test import with pending/processing job."""
    # Create workspace, base, and table
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

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

    # Create a pending job
    job_id = uuid4()
    from pybase.api.v1.extraction import _jobs

    _jobs[str(job_id)] = {
        "id": job_id,
        "status": JobStatus.PENDING,
        "format": ExtractionFormat.PDF,
        "filename": "test.pdf",
        "file_size": 1024,
        "options": {},
        "target_table_id": table.id,
        "progress": 0,
        "result": None,
        "error_message": None,
        "created_at": datetime.now(timezone.utc),
        "started_at": None,
        "completed_at": None,
    }

    response = await client.post(
        "/api/v1/extraction/import",
        json={
            "job_id": str(job_id),
            "table_id": str(table.id),
            "field_mapping": {},
            "create_missing_fields": False,
            "skip_errors": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_import_table_not_found(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test import with non-existent table."""
    # Create a completed extraction job
    job_id = uuid4()
    extraction_result = {
        "source_file": "test.pdf",
        "source_type": "pdf",
        "success": True,
        "tables": [
            {
                "headers": ["field1"],
                "rows": [["value1"]],
                "page": 1,
                "confidence": 0.95,
            }
        ],
        "dimensions": [],
        "text_blocks": [],
        "errors": [],
        "warnings": [],
    }

    from pybase.api.v1.extraction import _jobs

    _jobs[str(job_id)] = {
        "id": job_id,
        "status": JobStatus.COMPLETED,
        "format": ExtractionFormat.PDF,
        "filename": "test.pdf",
        "file_size": 1024,
        "options": {},
        "target_table_id": None,
        "progress": 100,
        "result": extraction_result,
        "error_message": None,
        "created_at": datetime.now(timezone.utc),
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    }

    response = await client.post(
        "/api/v1/extraction/import",
        json={
            "job_id": str(job_id),
            "table_id": str(uuid4()),
            "field_mapping": {},
            "create_missing_fields": False,
            "skip_errors": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_import_with_create_missing_fields(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test import with create_missing_fields flag."""
    # Create workspace, base, and table
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

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

    # Create a job with data that has fields not in the table
    job_id = uuid4()
    extraction_result = {
        "source_file": "test.pdf",
        "source_type": "pdf",
        "success": True,
        "tables": [
            {
                "headers": ["new_field1", "new_field2"],
                "rows": [
                    ["value1", "100"],
                    ["value2", "200"],
                ],
                "page": 1,
                "confidence": 0.95,
            }
        ],
        "dimensions": [],
        "text_blocks": [],
        "errors": [],
        "warnings": [],
    }

    from pybase.api.v1.extraction import _jobs

    _jobs[str(job_id)] = {
        "id": job_id,
        "status": JobStatus.COMPLETED,
        "format": ExtractionFormat.PDF,
        "filename": "test.pdf",
        "file_size": 1024,
        "options": {},
        "target_table_id": table.id,
        "progress": 100,
        "result": extraction_result,
        "error_message": None,
        "created_at": datetime.now(timezone.utc),
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    }

    # Import with create_missing_fields=True
    response = await client.post(
        "/api/v1/extraction/import",
        json={
            "job_id": str(job_id),
            "table_id": str(table.id),
            "field_mapping": {
                "new_field1": "new_field1",
                "new_field2": "new_field2",
            },
            "create_missing_fields": True,
            "skip_errors": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["records_imported"] == 2
    assert data["records_failed"] == 0
    assert data["fields_created"] == 2


@pytest.mark.asyncio
async def test_import_with_dxf_dimensions(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test import of DXF dimension data."""
    # Create workspace, base, table, and fields
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    base = Base(
        workspace_id=workspace.id,
        name="Test Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Dimensions Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    value_field = Field(
        table_id=table.id,
        name="value",
        field_type=FieldType.NUMBER.value,
        is_required=False,
    )
    db_session.add(value_field)

    unit_field = Field(
        table_id=table.id,
        name="unit",
        field_type=FieldType.TEXT.value,
        is_required=False,
    )
    db_session.add(unit_field)
    await db_session.commit()
    await db_session.refresh(value_field)
    await db_session.refresh(unit_field)

    # Create a job with DXF dimension data
    job_id = uuid4()
    extraction_result = {
        "source_file": "test.dxf",
        "source_type": "dxf",
        "success": True,
        "layers": [],
        "blocks": [],
        "dimensions": [
            {
                "value": 100.0,
                "unit": "mm",
                "tolerance_plus": 0.1,
                "tolerance_minus": 0.1,
                "dimension_type": "linear",
                "label": "Length",
                "confidence": 0.95,
            },
            {
                "value": 50.0,
                "unit": "mm",
                "tolerance_plus": 0.05,
                "tolerance_minus": 0.05,
                "dimension_type": "linear",
                "label": "Width",
                "confidence": 0.90,
            },
        ],
        "text_blocks": [],
        "entities": [],
        "errors": [],
        "warnings": [],
    }

    from pybase.api.v1.extraction import _jobs

    _jobs[str(job_id)] = {
        "id": job_id,
        "status": JobStatus.COMPLETED,
        "format": ExtractionFormat.DXF,
        "filename": "test.dxf",
        "file_size": 2048,
        "options": {},
        "target_table_id": table.id,
        "progress": 100,
        "result": extraction_result,
        "error_message": None,
        "created_at": datetime.now(timezone.utc),
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    }

    # Import the dimension data
    response = await client.post(
        "/api/v1/extraction/import",
        json={
            "job_id": str(job_id),
            "table_id": str(table.id),
            "field_mapping": {
                "value": str(value_field.id),
                "unit": str(unit_field.id),
            },
            "create_missing_fields": True,
            "skip_errors": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["records_imported"] == 2
    assert data["records_failed"] == 0


@pytest.mark.asyncio
async def test_import_unauthorized(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    """Test import without authentication."""
    response = await client.post(
        "/api/v1/extraction/import",
        json={
            "job_id": str(uuid4()),
            "table_id": str(uuid4()),
            "field_mapping": {},
            "create_missing_fields": False,
            "skip_errors": True,
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_import_permission_denied(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test import to table user doesn't have access to."""
    # Create workspace owned by another user
    other_user = User(
        email="other@example.com",
        hashed_password="hashed_password",
        name="Other User",
        is_active=True,
        is_verified=True,
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    workspace = Workspace(
        owner_id=other_user.id,
        name="Other Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    # Add other_user as workspace member
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=other_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    base = Base(
        workspace_id=workspace.id,
        name="Other Base",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Other Table",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Create a job
    job_id = uuid4()
    extraction_result = {
        "source_file": "test.pdf",
        "source_type": "pdf",
        "success": True,
        "tables": [
            {
                "headers": ["field1"],
                "rows": [["value1"]],
                "page": 1,
                "confidence": 0.95,
            }
        ],
        "dimensions": [],
        "text_blocks": [],
        "errors": [],
        "warnings": [],
    }

    from pybase.api.v1.extraction import _jobs

    _jobs[str(job_id)] = {
        "id": job_id,
        "status": JobStatus.COMPLETED,
        "format": ExtractionFormat.PDF,
        "filename": "test.pdf",
        "file_size": 1024,
        "options": {},
        "target_table_id": table.id,
        "progress": 100,
        "result": extraction_result,
        "error_message": None,
        "created_at": datetime.now(timezone.utc),
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    }

    # Try to import with test_user (not a member of workspace)
    response = await client.post(
        "/api/v1/extraction/import",
        json={
            "job_id": str(job_id),
            "table_id": str(table.id),
            "field_mapping": {},
            "create_missing_fields": False,
            "skip_errors": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_import_with_skip_errors_false(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test import with skip_errors=False fails on validation errors."""
    # Create workspace, base, table, and required field
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

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

    # Create a required field
    field = Field(
        table_id=table.id,
        name="required_field",
        field_type=FieldType.TEXT.value,
        is_required=True,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create a job with invalid data (missing required field)
    job_id = uuid4()
    extraction_result = {
        "source_file": "test.pdf",
        "source_type": "pdf",
        "success": True,
        "tables": [
            {
                "headers": ["optional_field"],
                "rows": [["value1"]],
                "page": 1,
                "confidence": 0.95,
            }
        ],
        "dimensions": [],
        "text_blocks": [],
        "errors": [],
        "warnings": [],
    }

    from pybase.api.v1.extraction import _jobs

    _jobs[str(job_id)] = {
        "id": job_id,
        "status": JobStatus.COMPLETED,
        "format": ExtractionFormat.PDF,
        "filename": "test.pdf",
        "file_size": 1024,
        "options": {},
        "target_table_id": table.id,
        "progress": 100,
        "result": extraction_result,
        "error_message": None,
        "created_at": datetime.now(timezone.utc),
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    }

    # Import with skip_errors=False should fail
    response = await client.post(
        "/api/v1/extraction/import",
        json={
            "job_id": str(job_id),
            "table_id": str(table.id),
            "field_mapping": {},
            "create_missing_fields": True,
            "skip_errors": False,
        },
        headers=auth_headers,
    )

    # Should still return 200 but with failures reported
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is False or data["records_failed"] > 0


@pytest.mark.asyncio
async def test_import_batch_large_dataset(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test batch import with 100+ records."""
    # Create workspace, base, table, and field
    workspace = Workspace(
        owner_id=test_user.id,
        name="Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=test_user.id,
        role=WorkspaceRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

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

    field = Field(
        table_id=table.id,
        name="item_name",
        field_type=FieldType.TEXT.value,
        is_required=False,
    )
    db_session.add(field)
    await db_session.commit()
    await db_session.refresh(field)

    # Create a job with 100+ records
    job_id = uuid4()
    rows = [[f"Item {i}"] for i in range(150)]
    extraction_result = {
        "source_file": "large_bom.pdf",
        "source_type": "pdf",
        "success": True,
        "tables": [
            {
                "headers": ["item_name"],
                "rows": rows,
                "page": 1,
                "confidence": 0.95,
            }
        ],
        "dimensions": [],
        "text_blocks": [],
        "errors": [],
        "warnings": [],
    }

    from pybase.api.v1.extraction import _jobs

    _jobs[str(job_id)] = {
        "id": job_id,
        "status": JobStatus.COMPLETED,
        "format": ExtractionFormat.PDF,
        "filename": "large_bom.pdf",
        "file_size": 10240,
        "options": {},
        "target_table_id": table.id,
        "progress": 100,
        "result": extraction_result,
        "error_message": None,
        "created_at": datetime.now(timezone.utc),
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    }

    # Import large dataset
    response = await client.post(
        "/api/v1/extraction/import",
        json={
            "job_id": str(job_id),
            "table_id": str(table.id),
            "field_mapping": {"item_name": str(field.id)},
            "create_missing_fields": False,
            "skip_errors": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["records_imported"] == 150
    assert data["records_failed"] == 0
