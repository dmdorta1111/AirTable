"""
Tests for ExtractionJob model.

Tests the ExtractionJob ORM model including:
- Model creation and field validation
- Status and format enums
- JSON serialization for options/result fields
- Property methods
"""

import json
from datetime import datetime, timezone

import pytest

from pybase.models.extraction_job import (
    ExtractionJob,
    ExtractionJobFormat,
    ExtractionJobStatus,
)


class TestExtractionJobStatus:
    """Tests for ExtractionJobStatus enum."""

    def test_status_values(self):
        """Test all status enum values exist."""
        assert ExtractionJobStatus.PENDING.value == "pending"
        assert ExtractionJobStatus.PROCESSING.value == "processing"
        assert ExtractionJobStatus.COMPLETED.value == "completed"
        assert ExtractionJobStatus.FAILED.value == "failed"
        assert ExtractionJobStatus.CANCELLED.value == "cancelled"

    def test_status_from_string(self):
        """Test creating status from string value."""
        assert ExtractionJobStatus("pending") == ExtractionJobStatus.PENDING
        assert ExtractionJobStatus("completed") == ExtractionJobStatus.COMPLETED

    def test_invalid_status_raises(self):
        """Test invalid status raises ValueError."""
        with pytest.raises(ValueError):
            ExtractionJobStatus("invalid_status")


class TestExtractionJobFormat:
    """Tests for ExtractionJobFormat enum."""

    def test_format_values(self):
        """Test all format enum values exist."""
        assert ExtractionJobFormat.PDF.value == "pdf"
        assert ExtractionJobFormat.DXF.value == "dxf"
        assert ExtractionJobFormat.IFC.value == "ifc"
        assert ExtractionJobFormat.STEP.value == "step"
        assert ExtractionJobFormat.WERK24.value == "werk24"

    def test_format_from_string(self):
        """Test creating format from string value."""
        assert ExtractionJobFormat("pdf") == ExtractionJobFormat.PDF
        assert ExtractionJobFormat("werk24") == ExtractionJobFormat.WERK24

    def test_invalid_format_raises(self):
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError):
            ExtractionJobFormat("invalid_format")


class TestExtractionJobModel:
    """Tests for ExtractionJob model."""

    def test_create_minimal_job(self):
        """Test creating job with minimal required fields."""
        job = ExtractionJob(
            id="test-uuid-123",
            filename="test.pdf",
            file_url="s3://bucket/test.pdf",
            file_size=1024,
            format=ExtractionJobFormat.PDF.value,
        )

        assert job.id == "test-uuid-123"
        assert job.filename == "test.pdf"
        assert job.file_url == "s3://bucket/test.pdf"
        assert job.file_size == 1024
        assert job.format == "pdf"
        assert job.status == ExtractionJobStatus.PENDING.value
        assert job.retry_count == 0
        assert job.max_retries == 3

    def test_create_job_with_all_fields(self):
        """Test creating job with all optional fields."""
        now = datetime.now(timezone.utc)
        job = ExtractionJob(
            id="test-uuid-456",
            filename="drawing.dxf",
            file_url="s3://bucket/drawing.dxf",
            file_size=2048,
            format=ExtractionJobFormat.DXF.value,
            status=ExtractionJobStatus.PROCESSING.value,
            record_id="record-uuid",
            field_id="field-uuid",
            attachment_id="attachment-uuid",
            created_by_id="user-uuid",
            retry_count=1,
            max_retries=5,
            started_at=now,
            error_message="Test error",
        )

        assert job.format == "dxf"
        assert job.status == "processing"
        assert job.record_id == "record-uuid"
        assert job.field_id == "field-uuid"
        assert job.attachment_id == "attachment-uuid"
        assert job.created_by_id == "user-uuid"
        assert job.retry_count == 1
        assert job.max_retries == 5
        assert job.started_at == now
        assert job.error_message == "Test error"

    def test_status_enum_property(self):
        """Test status_enum property returns correct enum."""
        job = ExtractionJob(
            id="test",
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
            status="completed",
        )

        assert job.status_enum == ExtractionJobStatus.COMPLETED
        assert isinstance(job.status_enum, ExtractionJobStatus)

    def test_format_enum_property(self):
        """Test format_enum property returns correct enum."""
        job = ExtractionJob(
            id="test",
            filename="test.ifc",
            file_url="s3://test",
            file_size=100,
            format="ifc",
        )

        assert job.format_enum == ExtractionJobFormat.IFC
        assert isinstance(job.format_enum, ExtractionJobFormat)

    def test_repr(self):
        """Test string representation."""
        job = ExtractionJob(
            id="abc123",
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
            status="pending",
        )

        assert repr(job) == "<ExtractionJob abc123 (pending)>"


class TestExtractionJobOptions:
    """Tests for options JSON field methods."""

    def test_get_options_empty(self):
        """Test get_options with empty/null options."""
        job = ExtractionJob(
            id="test",
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
        )
        job.options = None

        assert job.get_options() == {}

    def test_get_options_empty_string(self):
        """Test get_options with empty JSON string."""
        job = ExtractionJob(
            id="test",
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
        )
        job.options = "{}"

        assert job.get_options() == {}

    def test_get_options_with_data(self):
        """Test get_options with actual data."""
        job = ExtractionJob(
            id="test",
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
        )
        job.options = json.dumps(
            {
                "extract_tables": True,
                "extract_text": False,
                "pages": [1, 2, 3],
            }
        )

        options = job.get_options()
        assert options["extract_tables"] is True
        assert options["extract_text"] is False
        assert options["pages"] == [1, 2, 3]

    def test_get_options_invalid_json(self):
        """Test get_options with invalid JSON returns empty dict."""
        job = ExtractionJob(
            id="test",
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
        )
        job.options = "not valid json"

        assert job.get_options() == {}

    def test_set_options(self):
        """Test set_options serializes dict to JSON."""
        job = ExtractionJob(
            id="test",
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
        )

        job.set_options(
            {
                "extract_dimensions": True,
                "confidence_threshold": 0.8,
            }
        )

        assert job.options is not None
        parsed = json.loads(job.options)
        assert parsed["extract_dimensions"] is True
        assert parsed["confidence_threshold"] == 0.8


class TestExtractionJobResult:
    """Tests for result JSON field methods."""

    def test_get_result_empty(self):
        """Test get_result with empty/null result."""
        job = ExtractionJob(
            id="test",
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
        )
        job.result = None

        assert job.get_result() == {}

    def test_get_result_with_data(self):
        """Test get_result with actual extraction result."""
        job = ExtractionJob(
            id="test",
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
        )
        job.result = json.dumps(
            {
                "success": True,
                "tables": [{"headers": ["A", "B"], "rows": [["1", "2"]]}],
                "dimensions": [],
                "errors": [],
            }
        )

        result = job.get_result()
        assert result["success"] is True
        assert len(result["tables"]) == 1
        assert result["tables"][0]["headers"] == ["A", "B"]

    def test_get_result_invalid_json(self):
        """Test get_result with invalid JSON returns empty dict."""
        job = ExtractionJob(
            id="test",
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
        )
        job.result = "{invalid json"

        assert job.get_result() == {}

    def test_set_result(self):
        """Test set_result serializes dict to JSON."""
        job = ExtractionJob(
            id="test",
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
        )

        job.set_result(
            {
                "success": True,
                "layers": [{"name": "0", "entity_count": 50}],
                "metadata": {"version": "R2010"},
            }
        )

        assert job.result is not None
        parsed = json.loads(job.result)
        assert parsed["success"] is True
        assert parsed["layers"][0]["name"] == "0"
        assert parsed["metadata"]["version"] == "R2010"

    def test_set_result_complex_data(self):
        """Test set_result with complex nested data."""
        job = ExtractionJob(
            id="test",
            filename="test.pdf",
            file_url="s3://test",
            file_size=100,
            format="pdf",
        )

        complex_result = {
            "success": True,
            "dimensions": [
                {
                    "value": 10.5,
                    "unit": "mm",
                    "tolerance_plus": 0.1,
                    "tolerance_minus": 0.1,
                    "dimension_type": "linear",
                    "confidence": 0.95,
                    "bbox": [100, 200, 150, 220],
                }
            ],
            "title_block": {
                "drawing_number": "DRW-001",
                "revision": "A",
                "date": "2024-01-20",
            },
            "metadata": {
                "processing_time_ms": 1250,
                "extractor_version": "1.0.0",
            },
        }

        job.set_result(complex_result)

        # Verify round-trip
        parsed = job.get_result()
        assert parsed["dimensions"][0]["value"] == 10.5
        assert parsed["title_block"]["drawing_number"] == "DRW-001"
        assert parsed["metadata"]["processing_time_ms"] == 1250
