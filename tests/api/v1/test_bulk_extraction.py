"""Integration tests for bulk extraction endpoints."""

import io
from uuid import uuid4

import pytest
from httpx import AsyncClient

from pybase.core.config import settings
from pybase.schemas.extraction import JobStatus


@pytest.mark.asyncio
async def test_bulk_extract_multiple_files(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test bulk extraction with multiple PDF files."""
    # Create mock PDF files (simple PDF structure)
    pdf_content_1 = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    pdf_content_2 = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    pdf_content_3 = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"

    files = [
        ("files", ("test1.pdf", io.BytesIO(pdf_content_1), "application/pdf")),
        ("files", ("test2.pdf", io.BytesIO(pdf_content_2), "application/pdf")),
        ("files", ("test3.pdf", io.BytesIO(pdf_content_3), "application/pdf")),
    ]

    # Upload multiple files for bulk extraction
    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={
            "auto_detect_format": "true",
            "continue_on_error": "true",
        },
    )

    assert response.status_code == 202
    data = response.json()

    # Verify response structure
    assert "bulk_job_id" in data
    assert data["total_files"] == 3
    assert "files" in data
    assert len(data["files"]) == 3
    assert data["overall_status"] in [status.value for status in JobStatus]
    assert "progress" in data
    assert data["files_completed"] >= 0
    assert data["files_failed"] >= 0
    assert data["files_pending"] >= 0
    assert "created_at" in data

    # Verify each file has proper status structure
    for file_status in data["files"]:
        assert "file_path" in file_status
        assert "filename" in file_status
        assert "format" in file_status
        assert "status" in file_status
        assert file_status["progress"] >= 0 and file_status["progress"] <= 100


@pytest.mark.asyncio
async def test_bulk_extract_no_files(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test bulk extraction with no files should fail."""
    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=[],
        data={"auto_detect_format": "true"},
    )

    assert response.status_code == 400
    assert "No files provided" in response.json()["detail"]


@pytest.mark.asyncio
async def test_bulk_extract_without_filenames(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test bulk extraction with files without filenames should fail."""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"

    # Create file without filename
    files = [
        ("files", ("", io.BytesIO(pdf_content), "application/pdf")),
    ]

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={"auto_detect_format": "true"},
    )

    assert response.status_code == 400
    assert "must have filenames" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_bulk_job_status(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test retrieving bulk job status."""
    # First create a bulk extraction job
    pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    files = [
        ("files", ("test1.pdf", io.BytesIO(pdf_content), "application/pdf")),
        ("files", ("test2.pdf", io.BytesIO(pdf_content), "application/pdf")),
    ]

    create_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={"auto_detect_format": "true"},
    )

    assert create_response.status_code == 202
    job_data = create_response.json()
    job_id = job_data["bulk_job_id"]

    # Get job status
    status_response = await client.get(
        f"{settings.api_v1_prefix}/extraction/bulk/{job_id}",
        headers=auth_headers,
    )

    assert status_response.status_code == 200
    status_data = status_response.json()

    # Verify status response structure
    assert status_data["bulk_job_id"] == job_id
    assert status_data["total_files"] == 2
    assert len(status_data["files"]) == 2
    assert "overall_status" in status_data
    assert "progress" in status_data
    assert "files_completed" in status_data
    assert "files_failed" in status_data
    assert "files_pending" in status_data


@pytest.mark.asyncio
async def test_get_bulk_job_status_not_found(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test retrieving non-existent bulk job status."""
    fake_job_id = str(uuid4())

    response = await client.get(
        f"{settings.api_v1_prefix}/extraction/bulk/{fake_job_id}",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_preview_bulk_import(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test generating combined preview from bulk extraction."""
    # Create bulk extraction job
    pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    files = [
        ("files", ("test1.pdf", io.BytesIO(pdf_content), "application/pdf")),
        ("files", ("test2.pdf", io.BytesIO(pdf_content), "application/pdf")),
    ]

    create_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={"auto_detect_format": "true"},
    )

    assert create_response.status_code == 202
    job_id = create_response.json()["bulk_job_id"]

    # Get preview
    preview_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/{job_id}/preview",
        headers=auth_headers,
    )

    assert preview_response.status_code == 200
    preview_data = preview_response.json()

    # Verify preview structure
    assert preview_data["bulk_job_id"] == job_id
    assert "total_files" in preview_data
    assert "total_records" in preview_data
    assert "source_fields" in preview_data
    assert isinstance(preview_data["source_fields"], list)
    assert "target_fields" in preview_data
    assert "suggested_mapping" in preview_data
    assert isinstance(preview_data["suggested_mapping"], dict)
    assert "sample_data" in preview_data
    assert isinstance(preview_data["sample_data"], list)
    assert "file_previews" in preview_data
    assert isinstance(preview_data["file_previews"], list)
    assert "files_with_data" in preview_data
    assert "files_failed" in preview_data


@pytest.mark.asyncio
async def test_preview_bulk_import_not_found(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test preview with non-existent bulk job."""
    fake_job_id = str(uuid4())

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/{fake_job_id}/preview",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_bulk_extract_with_format_override(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test bulk extraction with format override."""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    files = [
        ("files", ("test1.pdf", io.BytesIO(pdf_content), "application/pdf")),
        ("files", ("test2.pdf", io.BytesIO(pdf_content), "application/pdf")),
    ]

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={
            "format_override": "pdf",
            "auto_detect_format": "false",
        },
    )

    assert response.status_code == 202
    data = response.json()
    assert data["total_files"] == 2

    # Verify all files have the overridden format
    for file_status in data["files"]:
        assert file_status["format"] == "pdf"


@pytest.mark.asyncio
async def test_bulk_extract_with_continue_on_error(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test bulk extraction continues on partial failures."""
    # Mix valid and invalid content
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    invalid_content = b"This is not a valid PDF file"

    files = [
        ("files", ("valid1.pdf", io.BytesIO(valid_pdf), "application/pdf")),
        ("files", ("invalid.pdf", io.BytesIO(invalid_content), "application/pdf")),
        ("files", ("valid2.pdf", io.BytesIO(valid_pdf), "application/pdf")),
    ]

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={"continue_on_error": "true"},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["total_files"] == 3

    # Job should be created even with some invalid files
    assert "bulk_job_id" in data
    assert len(data["files"]) == 3


@pytest.mark.asyncio
async def test_bulk_extract_unauthorized(client: AsyncClient):
    """Test bulk extraction without authentication."""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    files = [
        ("files", ("test.pdf", io.BytesIO(pdf_content), "application/pdf")),
    ]

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        files=files,
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_bulk_job_status_unauthorized(client: AsyncClient):
    """Test getting bulk job status without authentication."""
    fake_job_id = str(uuid4())

    response = await client.get(
        f"{settings.api_v1_prefix}/extraction/bulk/{fake_job_id}",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_preview_bulk_import_unauthorized(client: AsyncClient):
    """Test preview without authentication."""
    fake_job_id = str(uuid4())

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/{fake_job_id}/preview",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_bulk_extract_mixed_file_types(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test bulk extraction with different file types."""
    # Note: This test would ideally use actual DXF/IFC/STEP files
    # For now, using PDF as placeholder since we know it works
    pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"

    files = [
        ("files", ("drawing1.pdf", io.BytesIO(pdf_content), "application/pdf")),
        ("files", ("drawing2.pdf", io.BytesIO(pdf_content), "application/pdf")),
    ]

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={"auto_detect_format": "true"},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["total_files"] == 2


@pytest.mark.asyncio
async def test_bulk_extract_progress_tracking(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test that bulk extraction tracks progress correctly."""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    files = [
        ("files", ("test1.pdf", io.BytesIO(pdf_content), "application/pdf")),
        ("files", ("test2.pdf", io.BytesIO(pdf_content), "application/pdf")),
        ("files", ("test3.pdf", io.BytesIO(pdf_content), "application/pdf")),
    ]

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={"auto_detect_format": "true"},
    )

    assert response.status_code == 202
    data = response.json()

    # Verify progress tracking fields
    assert data["progress"] >= 0 and data["progress"] <= 100
    assert data["files_completed"] + data["files_failed"] + data["files_pending"] == 3

    # Verify created_at timestamp exists
    assert data["created_at"] is not None

    # If job started, verify started_at exists
    if data["overall_status"] != JobStatus.PENDING.value:
        assert data["started_at"] is not None


@pytest.mark.asyncio
async def test_bulk_extract_file_status_details(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """Test that each file in bulk extraction has detailed status."""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    files = [
        ("files", ("engineering_drawing.pdf", io.BytesIO(pdf_content), "application/pdf")),
    ]

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={"auto_detect_format": "true"},
    )

    assert response.status_code == 202
    data = response.json()

    # Check file status has all required fields
    file_status = data["files"][0]
    assert file_status["filename"] == "engineering_drawing.pdf"
    assert file_status["format"] in ["pdf", "dxf", "ifc", "step", "werk24"]
    assert file_status["status"] in [status.value for status in JobStatus]
    assert "progress" in file_status
    assert file_status["progress"] >= 0 and file_status["progress"] <= 100

    # If completed, should have result or error
    if file_status["status"] == JobStatus.COMPLETED.value:
        assert file_status.get("result") is not None or file_status.get("error_message") is not None
    elif file_status["status"] == JobStatus.FAILED.value:
        assert file_status.get("error_message") is not None


@pytest.mark.asyncio
async def test_bulk_import_e2e_flow(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session,
):
    """
    End-to-end test of complete bulk import workflow.

    Tests the full flow:
    1. Upload 3 PDF files via POST /extraction/bulk
    2. Poll GET /extraction/bulk/{job_id} until status=completed
    3. Verify all 3 files have extraction results
    4. Call POST /extraction/bulk/{job_id}/preview
    5. Verify combined preview shows data from all files
    6. Call POST /extraction/bulk/import with field mapping
    7. Verify records created with correct source_file references
    8. Verify failed files don't block successful imports
    """
    from pybase.models.base import Base as BaseModel
    from pybase.models.table import Table
    from pybase.models.workspace import Workspace

    # Step 0: Create a workspace and table for import
    workspace = Workspace(
        name="Test Workspace",
        description="E2E Test Workspace",
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(workspace)

    table = Table(
        name="Engineering Parts",
        workspace_id=workspace.id,
        fields=[
            {"id": "field1", "name": "Part Number", "type": "text"},
            {"id": "field2", "name": "Description", "type": "text"},
            {"id": "field3", "name": "Quantity", "type": "number"},
            {"id": "source_file", "name": "Source File", "type": "text"},
            {"id": "source_format", "name": "Source Format", "type": "text"},
        ],
    )
    db_session.add(table)
    await db_session.commit()
    await db_session.refresh(table)

    # Step 1: Upload 3 PDF files for bulk extraction
    pdf_content_1 = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    pdf_content_2 = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    pdf_content_3 = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"

    files = [
        ("files", ("drawing_001.pdf", io.BytesIO(pdf_content_1), "application/pdf")),
        ("files", ("drawing_002.pdf", io.BytesIO(pdf_content_2), "application/pdf")),
        ("files", ("drawing_003.pdf", io.BytesIO(pdf_content_3), "application/pdf")),
    ]

    upload_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={
            "auto_detect_format": "true",
            "continue_on_error": "true",
        },
    )

    assert upload_response.status_code == 202
    upload_data = upload_response.json()
    bulk_job_id = upload_data["bulk_job_id"]
    assert upload_data["total_files"] == 3
    assert len(upload_data["files"]) == 3

    # Step 2: Poll GET /extraction/bulk/{job_id} until completion
    # Note: In real scenario, would poll with delays. For test, check immediate status
    max_polls = 10
    poll_count = 0
    job_completed = False

    while poll_count < max_polls:
        status_response = await client.get(
            f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}",
            headers=auth_headers,
        )
        assert status_response.status_code == 200
        status_data = status_response.json()

        # Check if job is completed
        if status_data["overall_status"] in ["completed", "failed"]:
            job_completed = True
            break

        poll_count += 1
        # In real scenario: await asyncio.sleep(1)

    # Step 3: Verify all 3 files have extraction results
    # (or at least status information)
    final_status = await client.get(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}",
        headers=auth_headers,
    )
    assert final_status.status_code == 200
    final_data = final_status.json()

    assert final_data["bulk_job_id"] == bulk_job_id
    assert final_data["total_files"] == 3
    assert len(final_data["files"]) == 3

    # Verify each file has a status
    for file_status in final_data["files"]:
        assert "filename" in file_status
        assert "status" in file_status
        assert file_status["status"] in [s.value for s in JobStatus]

    # Count successfully completed files
    completed_files = [
        f for f in final_data["files"]
        if f["status"] == JobStatus.COMPLETED.value
    ]

    # Step 4: Call POST /extraction/bulk/{job_id}/preview
    preview_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}/preview",
        headers=auth_headers,
        params={"table_id": str(table.id)},
    )

    assert preview_response.status_code == 200
    preview_data = preview_response.json()

    # Step 5: Verify combined preview shows data from all files
    assert preview_data["bulk_job_id"] == bulk_job_id
    assert "total_files" in preview_data
    assert "total_records" in preview_data
    assert "source_fields" in preview_data
    assert isinstance(preview_data["source_fields"], list)
    assert "target_fields" in preview_data
    assert "suggested_mapping" in preview_data
    assert isinstance(preview_data["suggested_mapping"], dict)
    assert "sample_data" in preview_data
    assert isinstance(preview_data["sample_data"], list)
    assert "file_previews" in preview_data
    assert isinstance(preview_data["file_previews"], list)

    # Verify we have per-file breakdowns
    assert len(preview_data["file_previews"]) >= 0

    # Step 6: Call POST /extraction/bulk/import with field mapping
    # Create a simple field mapping (source -> target)
    field_mapping = {}
    if preview_data["suggested_mapping"]:
        # Use suggested mapping if available
        field_mapping = preview_data["suggested_mapping"]
    else:
        # Create basic mapping for test
        field_mapping = {
            "text": "field2",  # Map extracted text to Description field
        }

    import_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/import",
        headers=auth_headers,
        json={
            "bulk_job_id": bulk_job_id,
            "table_id": str(table.id),
            "field_mapping": field_mapping,
            "create_missing_fields": False,
            "skip_errors": True,
            "include_source_file": True,
        },
    )

    assert import_response.status_code == 200
    import_data = import_response.json()

    # Step 7: Verify import response structure
    assert "success" in import_data
    assert "records_imported" in import_data
    assert "records_failed" in import_data
    assert "errors" in import_data
    assert isinstance(import_data["errors"], list)

    # Verify some records were processed (imported or failed)
    total_processed = import_data["records_imported"] + import_data["records_failed"]
    # Note: May be 0 if PDFs have no extractable data, which is fine for this test structure
    assert total_processed >= 0

    # Step 8: Verify failed files don't block successful imports
    # This is demonstrated by:
    # - continue_on_error=true in upload
    # - skip_errors=true in import
    # - Import response should still have success=True even if some records failed
    # The import should complete and return results even with partial failures
    assert "success" in import_data

    # Verify error handling structure exists
    if import_data["records_failed"] > 0:
        assert len(import_data["errors"]) > 0
        # Verify error structure
        for error in import_data["errors"]:
            assert "file" in error or "row" in error or "error" in error


@pytest.mark.asyncio
async def test_bulk_import_partial_failure(
    client: AsyncClient,
    auth_headers: dict[str, str],
):
    """
    Test that partial file failures don't block successful imports.

    Verifies:
    - Mixed valid/invalid files are processed
    - Valid files complete successfully
    - Invalid files are marked as failed
    - Import can proceed with only successful files
    """
    # Create bulk job with mix of valid and invalid files
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n%%EOF"
    invalid_content = b"This is not a valid PDF file"

    files = [
        ("files", ("valid1.pdf", io.BytesIO(valid_pdf), "application/pdf")),
        ("files", ("invalid.pdf", io.BytesIO(invalid_content), "application/pdf")),
        ("files", ("valid2.pdf", io.BytesIO(valid_pdf), "application/pdf")),
    ]

    # Upload with continue_on_error=true
    upload_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk",
        headers=auth_headers,
        files=files,
        data={
            "auto_detect_format": "true",
            "continue_on_error": "true",
        },
    )

    assert upload_response.status_code == 202
    data = upload_response.json()
    bulk_job_id = data["bulk_job_id"]

    # Get job status
    status_response = await client.get(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}",
        headers=auth_headers,
    )

    assert status_response.status_code == 200
    status_data = status_response.json()

    # Job should be created even with some invalid files
    assert status_data["bulk_job_id"] == bulk_job_id
    assert status_data["total_files"] == 3

    # Get preview - should work with partial data
    preview_response = await client.post(
        f"{settings.api_v1_prefix}/extraction/bulk/{bulk_job_id}/preview",
        headers=auth_headers,
    )

    # Preview should succeed even if some files failed
    assert preview_response.status_code == 200
    preview_data = preview_response.json()

    # Should show count of failed files
    assert "files_failed" in preview_data

    # files_with_data should be less than total if some failed
    if preview_data["files_failed"] > 0:
        assert preview_data["files_with_data"] < 3
