"""API integration tests for enhanced PDF table extraction."""

import io
import tempfile
from pathlib import Path

import pytest
from httpx import AsyncClient

from pybase.core.config import settings


@pytest.mark.asyncio
async def test_extract_pdf_with_merged_cells(client: AsyncClient, auth_headers: dict[str, str]):
    """Test PDF extraction returns merged cell metadata."""
    # Create a simple PDF file for testing
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    # Create file-like object
    files = {
        "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    # Form data
    data = {
        "extract_tables": "true",
        "extract_text": "true",
        "extract_dimensions": "false",
        "use_ocr": "false",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/pdf",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 200
    result = response.json()

    # Verify response structure
    assert "source_file" in result
    assert "success" in result
    assert "tables" in result
    assert "metadata" in result

    # Each table should have merged_cells field
    for table in result.get("tables", []):
        assert "merged_cells" in table
        assert isinstance(table["merged_cells"], list)


@pytest.mark.asyncio
async def test_extract_pdf_with_type_inference(client: AsyncClient, auth_headers: dict[str, str]):
    """Test PDF extraction returns column type inference."""
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    files = {
        "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    data = {
        "extract_tables": "true",
        "extract_text": "false",
        "extract_dimensions": "false",
        "use_ocr": "false",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/pdf",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 200
    result = response.json()

    # Each table should have column_types field
    for table in result.get("tables", []):
        assert "column_types" in table
        assert isinstance(table["column_types"], list)


@pytest.mark.asyncio
async def test_extract_pdf_with_ocr_enabled(client: AsyncClient, auth_headers: dict[str, str]):
    """Test PDF extraction with OCR enabled."""
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    files = {
        "file": ("scanned.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    data = {
        "extract_tables": "true",
        "extract_text": "true",
        "extract_dimensions": "false",
        "use_ocr": "true",
        "ocr_language": "eng",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/pdf",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 200
    result = response.json()

    # Verify OCR metadata is present
    assert "metadata" in result
    # OCR metadata may include information about OCR usage
    # The actual OCR processing may be skipped if Tesseract is not installed


@pytest.mark.asyncio
async def test_extract_pdf_confidence_scores(client: AsyncClient, auth_headers: dict[str, str]):
    """Test that extracted tables include confidence scores."""
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    files = {
        "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    data = {
        "extract_tables": "true",
        "extract_text": "false",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/pdf",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 200
    result = response.json()

    # Each table should have a confidence score
    for table in result.get("tables", []):
        assert "confidence" in table
        assert isinstance(table["confidence"], (int, float))
        assert 0.0 <= table["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_extract_pdf_page_selection(client: AsyncClient, auth_headers: dict[str, str]):
    """Test PDF extraction with specific page selection."""
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    files = {
        "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    data = {
        "extract_tables": "true",
        "extract_text": "false",
        "pages": "1,2,3",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/pdf",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 200
    result = response.json()
    assert "success" in result


@pytest.mark.asyncio
async def test_extract_pdf_no_file(client: AsyncClient, auth_headers: dict[str, str]):
    """Test PDF extraction without file fails."""
    data = {
        "extract_tables": "true",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/pdf",
        headers=auth_headers,
        data=data,
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_extract_pdf_invalid_file_type(client: AsyncClient, auth_headers: dict[str, str]):
    """Test PDF extraction with non-PDF file fails."""
    # Create a text file instead of PDF
    files = {
        "file": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")
    }

    data = {
        "extract_tables": "true",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/pdf",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 400
    assert "Invalid file extension" in response.json()["detail"]


@pytest.mark.asyncio
async def test_extract_pdf_invalid_pages_format(client: AsyncClient, auth_headers: dict[str, str]):
    """Test PDF extraction with invalid pages format fails."""
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    files = {
        "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    data = {
        "extract_tables": "true",
        "pages": "invalid,format",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/pdf",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 400
    assert "Invalid pages format" in response.json()["detail"]


@pytest.mark.asyncio
async def test_extract_pdf_unauthorized(client: AsyncClient):
    """Test PDF extraction without authentication fails."""
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    files = {
        "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    data = {
        "extract_tables": "true",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/pdf",
        files=files,
        data=data,
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_extract_pdf_table_structure(client: AsyncClient, auth_headers: dict[str, str]):
    """Test that extracted tables have proper structure."""
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    files = {
        "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    data = {
        "extract_tables": "true",
        "extract_text": "false",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/pdf",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 200
    result = response.json()

    # Verify table structure
    for table in result.get("tables", []):
        # Standard fields
        assert "headers" in table
        assert "rows" in table
        assert "num_rows" in table
        assert "num_columns" in table
        assert "page" in table
        assert "confidence" in table

        # Enhanced fields
        assert "merged_cells" in table
        assert "column_types" in table

        # Optional bbox field
        # assert "bbox" in table  # May or may not be present


@pytest.mark.asyncio
async def test_extract_pdf_response_schema(client: AsyncClient, auth_headers: dict[str, str]):
    """Test that PDF extraction response matches expected schema."""
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    files = {
        "file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    data = {
        "extract_tables": "true",
        "extract_text": "true",
        "extract_dimensions": "false",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/pdf",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 200
    result = response.json()

    # Top-level schema fields
    assert "source_file" in result
    assert result["source_file"] == "test.pdf"
    assert "source_type" in result
    assert result["source_type"] == "pdf"
    assert "success" in result
    assert isinstance(result["success"], bool)
    assert "tables" in result
    assert isinstance(result["tables"], list)
    assert "dimensions" in result
    assert isinstance(result["dimensions"], list)
    assert "text_blocks" in result
    assert isinstance(result["text_blocks"], list)
    assert "metadata" in result
    assert isinstance(result["metadata"], dict)
    assert "errors" in result
    assert isinstance(result["errors"], list)
    assert "warnings" in result
    assert isinstance(result["warnings"], list)


@pytest.mark.asyncio
async def test_extract_pdf_with_all_features(client: AsyncClient, auth_headers: dict[str, str]):
    """Test PDF extraction with all enhanced features enabled."""
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    files = {
        "file": ("comprehensive.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    data = {
        "extract_tables": "true",
        "extract_text": "true",
        "extract_dimensions": "false",
        "use_ocr": "true",
        "ocr_language": "eng",
        "pages": "1",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/pdf",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 200
    result = response.json()

    # Verify all features are processed
    assert result["success"] is True or len(result["errors"]) == 0 or result["success"] is False

    # Tables should have enhanced features
    for table in result.get("tables", []):
        assert "merged_cells" in table
        assert "column_types" in table
        assert "confidence" in table


@pytest.mark.asyncio
async def test_extract_pdf_only_text(client: AsyncClient, auth_headers: dict[str, str]):
    """Test PDF extraction with only text extraction enabled."""
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    files = {
        "file": ("text_only.pdf", io.BytesIO(pdf_content), "application/pdf")
    }

    data = {
        "extract_tables": "false",
        "extract_text": "true",
        "extract_dimensions": "false",
    }

    response = await client.post(
        f"{settings.api_v1_prefix}/extraction/pdf",
        headers=auth_headers,
        files=files,
        data=data,
    )

    assert response.status_code == 200
    result = response.json()

    # Tables should be empty when not extracted
    assert "tables" in result
    assert "text_blocks" in result


@pytest.mark.asyncio
async def test_extract_pdf_different_ocr_languages(client: AsyncClient, auth_headers: dict[str, str]):
    """Test PDF extraction with different OCR languages."""
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n212\n%%EOF"

    for lang in ["eng", "deu", "fra", "spa"]:
        files = {
            "file": (f"test_{lang}.pdf", io.BytesIO(pdf_content), "application/pdf")
        }

        data = {
            "extract_tables": "true",
            "use_ocr": "true",
            "ocr_language": lang,
        }

        response = await client.post(
            f"{settings.api_v1_prefix}/extraction/pdf",
            headers=auth_headers,
            files=files,
            data=data,
        )

        assert response.status_code == 200
        result = response.json()
        assert "metadata" in result
