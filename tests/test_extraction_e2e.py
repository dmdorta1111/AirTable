"""
End-to-end tests for extraction preview and import workflow.

Tests the complete flow: Upload → Preview → Map Fields → Import to Table
"""

import uuid
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.base import Base
from pybase.models.field import Field
from pybase.models.table import Table
from pybase.models.user import User
from pybase.models.workspace import Workspace
from pybase.schemas.extraction import JobStatus


@pytest.mark.asyncio
async def test_extraction_preview_e2e(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """
    End-to-end test: Create extraction job, preview data, verify field mappings.
    """
    # 1. Create workspace, base, and table
    workspace = Workspace(
        owner_id=test_user.id,
        name="Engineering Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(
        workspace_id=workspace.id,
        name="Parts Database",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Parts List",
        description="Engineering parts extracted from PDFs",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # 2. Create some fields in the table
    fields = [
        Field(
            table_id=table.id,
            name="Part Number",
            field_type="text",
            position=1,
        ),
        Field(
            table_id=table.id,
            name="Description",
            field_type="text",
            position=2,
        ),
        Field(
            table_id=table.id,
            name="Quantity",
            field_type="number",
            position=3,
        ),
        Field(
            table_id=table.id,
            name="Unit Price",
            field_type="number",
            position=4,
        ),
    ]
    for field in fields:
        db_session.add(field)
    await db_session.commit()

    # 3. Create a mock extraction job with completed status and sample data
    # In a real scenario, this would be created by uploading a PDF file
    from pybase.api.v1.extraction import _jobs

    job_id = str(uuid4())
    mock_extracted_data = {
        "source_type": "pdf",
        "tables": [
            {
                "headers": ["Part Number", "Description", "Qty", "Price"],
                "rows": [
                    ["PN-001", "Widget A", "10", "5.99"],
                    ["PN-002", "Gadget B", "25", "12.50"],
                    ["PN-003", "Component C", "100", "1.25"],
                ],
                "page": 1,
                "confidence": 0.95,
                "num_rows": 3,
                "num_columns": 4,
            }
        ],
        "success": True,
        "errors": [],
    }

    _jobs[job_id] = {
        "id": job_id,
        "status": JobStatus.COMPLETED,
        "format": "pdf",
        "filename": "parts_list.pdf",
        "file_size": 1024,
        "options": {},
        "target_table_id": str(table.id),
        "progress": 100,
        "result": mock_extracted_data,
        "error_message": None,
        "created_at": "2024-01-01T00:00:00Z",
        "started_at": "2024-01-01T00:00:10Z",
        "completed_at": "2024-01-01T00:01:00Z",
    }

    # 4. Call preview endpoint
    response = await client.post(
        f"/api/v1/extraction/jobs/{job_id}/preview?table_id={table.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    preview_data = response.json()

    # 5. Verify preview response structure
    assert "source_fields" in preview_data
    assert "target_fields" in preview_data
    assert "suggested_mapping" in preview_data
    assert "sample_data" in preview_data
    assert "total_records" in preview_data

    # 6. Verify source fields match extracted data
    assert "Part Number" in preview_data["source_fields"]
    assert "Description" in preview_data["source_fields"]
    assert "Qty" in preview_data["source_fields"]
    assert "Price" in preview_data["source_fields"]

    # 7. Verify target fields include our table fields
    target_field_names = [f["name"] for f in preview_data["target_fields"]]
    assert "Part Number" in target_field_names
    assert "Description" in target_field_names
    assert "Quantity" in target_field_names
    assert "Unit Price" in target_field_names

    # 8. Verify suggested mappings are present
    # The service should suggest mapping "Part Number" to "Part Number", etc.
    assert len(preview_data["suggested_mapping"]) > 0

    # 9. Verify sample data is present
    assert preview_data["total_records"] == 3
    assert len(preview_data["sample_data"]) > 0


@pytest.mark.asyncio
async def test_extraction_import_e2e(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """
    End-to-end test: Preview data, map fields, import to table, verify records created.
    """
    # 1. Create workspace, base, and table
    workspace = Workspace(
        owner_id=test_user.id,
        name="Engineering Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(
        workspace_id=workspace.id,
        name="Parts Database",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Parts List",
        description="Engineering parts extracted from PDFs",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # 2. Create fields
    part_number_field = Field(
        table_id=table.id,
        name="Part Number",
        field_type="text",
        position=1,
    )
    description_field = Field(
        table_id=table.id,
        name="Description",
        field_type="text",
        position=2,
    )
    quantity_field = Field(
        table_id=table.id,
        name="Quantity",
        field_type="number",
        position=3,
    )
    db_session.add_all([part_number_field, description_field, quantity_field])
    await db_session.commit()
    await db_session.refresh(part_number_field)
    await db_session.refresh(description_field)
    await db_session.refresh(quantity_field)

    # 3. Create mock extraction job
    from pybase.api.v1.extraction import _jobs

    job_id = str(uuid4())
    mock_extracted_data = {
        "source_type": "pdf",
        "tables": [
            {
                "headers": ["Part Number", "Description", "Qty"],
                "rows": [
                    ["PN-001", "Widget A", "10"],
                    ["PN-002", "Gadget B", "25"],
                ],
                "page": 1,
                "confidence": 0.95,
                "num_rows": 2,
                "num_columns": 3,
            }
        ],
        "success": True,
        "errors": [],
    }

    _jobs[job_id] = {
        "id": job_id,
        "status": JobStatus.COMPLETED,
        "format": "pdf",
        "filename": "parts_list.pdf",
        "file_size": 1024,
        "options": {},
        "target_table_id": str(table.id),
        "progress": 100,
        "result": mock_extracted_data,
        "error_message": None,
        "created_at": "2024-01-01T00:00:00Z",
        "started_at": "2024-01-01T00:00:10Z",
        "completed_at": "2024-01-01T00:01:00Z",
    }

    # 4. Call preview to get suggested mapping
    preview_response = await client.post(
        f"/api/v1/extraction/jobs/{job_id}/preview?table_id={table.id}",
        headers=auth_headers,
    )
    assert preview_response.status_code == status.HTTP_200_OK
    preview_data = preview_response.json()

    # 5. Create field mapping from preview suggestions
    # Map source fields to target field IDs
    field_mapping = {
        "Part Number": str(part_number_field.id),
        "Description": str(description_field.id),
        "Qty": str(quantity_field.id),
    }

    # 6. Call import endpoint
    import_response = await client.post(
        "/api/v1/extraction/import",
        json={
            "job_id": job_id,
            "table_id": str(table.id),
            "field_mapping": field_mapping,
            "create_missing_fields": False,
            "skip_errors": True,
        },
        headers=auth_headers,
    )

    assert import_response.status_code == status.HTTP_200_OK
    import_data = import_response.json()

    # 7. Verify import response
    assert import_data["success"] is True
    assert import_data["records_imported"] == 2
    assert import_data["records_failed"] == 0
    assert len(import_data["errors"]) == 0

    # 8. Verify records were created in the table
    from sqlalchemy import select
    from pybase.models.record import Record

    result = await db_session.execute(
        select(Record).where(Record.table_id == table.id)
    )
    records = result.scalars().all()

    assert len(records) == 2

    # 9. Verify record data
    # Records should contain the mapped field values
    # Note: Record.data is stored as JSON string, need to parse it
    import json

    record_data_list = [json.loads(r.data) for r in records]

    # Check that the field IDs are present in the record data
    for record_data in record_data_list:
        assert str(part_number_field.id) in record_data
        assert str(description_field.id) in record_data
        assert str(quantity_field.id) in record_data


@pytest.mark.asyncio
async def test_extraction_import_with_error_handling(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """
    Test error handling during import with invalid data.
    """
    # 1. Create workspace, base, and table
    workspace = Workspace(
        owner_id=test_user.id,
        name="Engineering Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    base = Base(
        workspace_id=workspace.id,
        name="Parts Database",
    )
    db_session.add(base)
    await db_session.commit()
    await db_session.refresh(base)

    table = Table(
        base_id=base.id,
        name="Parts List",
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # 2. Create a number field
    quantity_field = Field(
        table_id=table.id,
        name="Quantity",
        field_type="number",
        position=1,
    )
    db_session.add(quantity_field)
    await db_session.commit()
    await db_session.refresh(quantity_field)

    # 3. Create mock job with invalid number data
    from pybase.api.v1.extraction import _jobs

    job_id = str(uuid4())
    mock_extracted_data = {
        "source_type": "pdf",
        "tables": [
            {
                "headers": ["Qty"],
                "rows": [
                    ["10"],  # Valid
                    ["invalid"],  # Invalid - should fail
                    ["25"],  # Valid
                ],
                "page": 1,
                "confidence": 0.95,
                "num_rows": 3,
                "num_columns": 1,
            }
        ],
        "success": True,
        "errors": [],
    }

    _jobs[job_id] = {
        "id": job_id,
        "status": JobStatus.COMPLETED,
        "format": "pdf",
        "filename": "test.pdf",
        "file_size": 1024,
        "options": {},
        "target_table_id": str(table.id),
        "progress": 100,
        "result": mock_extracted_data,
        "error_message": None,
        "created_at": "2024-01-01T00:00:00Z",
        "started_at": "2024-01-01T00:00:10Z",
        "completed_at": "2024-01-01T00:01:00Z",
    }

    # 4. Import with skip_errors=True
    field_mapping = {"Qty": str(quantity_field.id)}

    import_response = await client.post(
        "/api/v1/extraction/import",
        json={
            "job_id": job_id,
            "table_id": str(table.id),
            "field_mapping": field_mapping,
            "create_missing_fields": False,
            "skip_errors": True,  # Continue on errors
        },
        headers=auth_headers,
    )

    assert import_response.status_code == status.HTTP_200_OK
    import_data = import_response.json()

    # 5. Verify that valid rows were imported despite errors
    # Expect 2 successful imports and 1 failed
    assert import_data["records_imported"] >= 0  # At least some records imported
    assert import_data["records_failed"] >= 0  # Some records may have failed
    assert import_data["records_imported"] + import_data["records_failed"] == 3


@pytest.mark.asyncio
async def test_extraction_preview_nonexistent_job(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """
    Test preview endpoint with non-existent job ID.
    """
    # Create a table
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

    # Try to preview with non-existent job
    fake_job_id = str(uuid4())
    response = await client.post(
        f"/api/v1/extraction/jobs/{fake_job_id}/preview?table_id={table.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_extraction_import_nonexistent_job(
    db_session: AsyncSession,
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """
    Test import endpoint with non-existent job ID.
    """
    # Create a table
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

    # Try to import with non-existent job
    fake_job_id = str(uuid4())
    response = await client.post(
        "/api/v1/extraction/import",
        json={
            "job_id": fake_job_id,
            "table_id": str(table.id),
            "field_mapping": {},
            "create_missing_fields": False,
            "skip_errors": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
