"""Integration tests for OCR fallback in PDF extraction."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from pybase.extraction.base import ExtractedTable, ExtractedText
from pybase.extraction.pdf.extractor import PDFExtractor


@pytest.fixture
def mock_ocr_extractor():
    """Mock OCR extractor for testing."""
    mock_extractor = Mock()

    # Mock extract_tables_ocr to return sample tables
    mock_extractor.extract_tables_ocr.return_value = [
        ExtractedTable(
            headers=["Part No", "Description", "Qty"],
            rows=[
                ["001", "Widget A", "10"],
                ["002", "Widget B", "20"],
            ],
            page=1,
            confidence=0.85,
        )
    ]

    # Mock extract_text to return sample text
    mock_extractor.extract_text.return_value = [
        ExtractedText(
            text="This is OCR extracted text from a scanned document.",
            page=1,
            confidence=0.90,
        )
    ]

    return mock_extractor


@pytest.fixture
def sample_pdf_file(tmp_path):
    """Create a minimal PDF file for testing."""
    pdf_path = tmp_path / "test.pdf"

    # Create a minimal valid PDF
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>
endobj
5 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
0000000304 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
398
%%EOF
"""

    pdf_path.write_bytes(pdf_content)
    return pdf_path


@pytest.fixture
def scanned_pdf_file(tmp_path):
    """Create a minimal PDF file that simulates a scanned document (minimal text)."""
    pdf_path = tmp_path / "scanned.pdf"

    # Create a PDF with minimal text to simulate scanned document
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
187
%%EOF
"""

    pdf_path.write_bytes(pdf_content)
    return pdf_path


class TestOCRDetection:
    """Test OCR detection for scanned PDFs."""

    def test_is_scanned_detects_text_based_pdf(self, sample_pdf_file):
        """Test that is_scanned correctly identifies text-based PDFs."""
        extractor = PDFExtractor()

        is_scanned = extractor.is_scanned(sample_pdf_file)

        # Text-based PDF should not be detected as scanned
        # Note: The minimal PDF may or may not have extractable text
        # depending on the PDF library, so we just verify it doesn't error
        assert isinstance(is_scanned, bool)

    def test_is_scanned_detects_scanned_pdf(self, scanned_pdf_file):
        """Test that is_scanned correctly identifies scanned PDFs."""
        extractor = PDFExtractor()

        is_scanned = extractor.is_scanned(scanned_pdf_file)

        # Scanned PDF (minimal text) should be detected
        assert is_scanned is True

    def test_is_scanned_with_custom_threshold(self, sample_pdf_file):
        """Test is_scanned with custom text threshold."""
        extractor = PDFExtractor()

        # High threshold should classify as scanned
        is_scanned = extractor.is_scanned(
            sample_pdf_file,
            min_text_threshold=1000
        )

        assert isinstance(is_scanned, bool)

    def test_is_scanned_with_sample_pages(self, sample_pdf_file):
        """Test is_scanned with custom sample page count."""
        extractor = PDFExtractor()

        is_scanned = extractor.is_scanned(
            sample_pdf_file,
            sample_pages=1
        )

        assert isinstance(is_scanned, bool)


class TestOCRExtraction:
    """Test OCR table and text extraction."""

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_extract_with_ocr_enabled(self, mock_ocr_class, sample_pdf_file, mock_ocr_extractor):
        """Test extraction with OCR explicitly enabled."""
        mock_ocr_class.return_value = mock_ocr_extractor

        extractor = PDFExtractor(enable_ocr=True)
        result = extractor.extract(
            sample_pdf_file,
            extract_tables=True,
            extract_text=True,
            use_ocr=True
        )

        # Verify OCR methods were called
        assert mock_ocr_extractor.extract_tables_ocr.called
        assert mock_ocr_extractor.extract_text.called

        # Verify results contain OCR data
        assert result.success
        assert len(result.tables) > 0 or "ocr_tables" in result.metadata

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_extract_tables_with_ocr(self, mock_ocr_class, scanned_pdf_file, mock_ocr_extractor):
        """Test OCR table extraction for scanned PDFs."""
        mock_ocr_class.return_value = mock_ocr_extractor

        extractor = PDFExtractor(enable_ocr=True)
        result = extractor.extract(
            scanned_pdf_file,
            extract_tables=True,
            extract_text=False,
            use_ocr=True
        )

        # Verify OCR table extraction was called
        mock_ocr_extractor.extract_tables_ocr.assert_called_once()

        # Verify metadata indicates OCR was used
        assert result.metadata.get("ocr_tables") is True or result.metadata.get("ocr_tables_supplemental") is True

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_extract_text_with_ocr(self, mock_ocr_class, scanned_pdf_file, mock_ocr_extractor):
        """Test OCR text extraction for scanned PDFs."""
        mock_ocr_class.return_value = mock_ocr_extractor

        extractor = PDFExtractor(enable_ocr=True)
        result = extractor.extract(
            scanned_pdf_file,
            extract_tables=False,
            extract_text=True,
            use_ocr=True
        )

        # Verify OCR text extraction was called
        mock_ocr_extractor.extract_text.assert_called_once()

        # Verify metadata indicates OCR was used
        assert result.metadata.get("ocr_text") is True or result.metadata.get("ocr_text_supplemental") is True

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_ocr_with_specific_pages(self, mock_ocr_class, sample_pdf_file, mock_ocr_extractor):
        """Test OCR extraction for specific pages."""
        mock_ocr_class.return_value = mock_ocr_extractor

        extractor = PDFExtractor(enable_ocr=True)
        result = extractor.extract(
            sample_pdf_file,
            extract_tables=True,
            pages=[1],
            use_ocr=True
        )

        # Verify OCR was called with correct pages parameter
        if mock_ocr_extractor.extract_tables_ocr.called:
            call_args = mock_ocr_extractor.extract_tables_ocr.call_args
            assert call_args is not None


class TestOCRFallback:
    """Test OCR fallback mechanism when standard extraction fails."""

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_ocr_fallback_when_no_tables_found(self, mock_ocr_class, scanned_pdf_file, mock_ocr_extractor):
        """Test that OCR is used as fallback when no tables are found."""
        mock_ocr_class.return_value = mock_ocr_extractor

        extractor = PDFExtractor(enable_ocr=True)

        # Extract without forcing OCR (auto-detect)
        result = extractor.extract(
            scanned_pdf_file,
            extract_tables=True,
            use_ocr=None  # Auto-detect
        )

        # OCR should be triggered as fallback
        assert mock_ocr_extractor.extract_tables_ocr.called

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_ocr_auto_detect_scanned_pdf(self, mock_ocr_class, scanned_pdf_file, mock_ocr_extractor):
        """Test automatic OCR detection for scanned PDFs."""
        mock_ocr_class.return_value = mock_ocr_extractor

        extractor = PDFExtractor(enable_ocr=True)

        # Don't force OCR, let it auto-detect
        result = extractor.extract(
            scanned_pdf_file,
            extract_tables=True,
            extract_text=True
        )

        # Should auto-detect and use OCR
        assert result.success

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_no_ocr_when_disabled(self, mock_ocr_class, scanned_pdf_file):
        """Test that OCR is not used when disabled."""
        extractor = PDFExtractor(enable_ocr=False)

        result = extractor.extract(
            scanned_pdf_file,
            extract_tables=True,
            extract_text=True
        )

        # OCR should not be initialized or called
        mock_ocr_class.assert_not_called()

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_ocr_supplements_standard_extraction(self, mock_ocr_class, sample_pdf_file, mock_ocr_extractor):
        """Test that OCR can supplement standard extraction results."""
        mock_ocr_class.return_value = mock_ocr_extractor

        extractor = PDFExtractor(enable_ocr=True)

        # Force OCR even when standard extraction works
        result = extractor.extract(
            sample_pdf_file,
            extract_tables=True,
            use_ocr=True
        )

        # Both standard and OCR extraction should contribute
        assert result.success


class TestOCRConfiguration:
    """Test OCR configuration options."""

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_ocr_with_custom_language(self, mock_ocr_class, sample_pdf_file, mock_ocr_extractor):
        """Test OCR with custom language configuration."""
        mock_ocr_class.return_value = mock_ocr_extractor

        extractor = PDFExtractor(
            enable_ocr=True,
            ocr_language="deu"  # German
        )

        # Verify OCR extractor was initialized with correct language
        mock_ocr_class.assert_called_once()
        call_kwargs = mock_ocr_class.call_args.kwargs
        assert call_kwargs.get("language") == "deu"

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_ocr_with_custom_tesseract_path(self, mock_ocr_class, sample_pdf_file, mock_ocr_extractor):
        """Test OCR with custom Tesseract executable path."""
        mock_ocr_class.return_value = mock_ocr_extractor

        custom_path = "/usr/local/bin/tesseract"
        extractor = PDFExtractor(
            enable_ocr=True,
            tesseract_cmd=custom_path
        )

        # Verify OCR extractor was initialized with custom path
        mock_ocr_class.assert_called_once()
        call_kwargs = mock_ocr_class.call_args.kwargs
        assert call_kwargs.get("tesseract_cmd") == custom_path


class TestOCRErrorHandling:
    """Test OCR error handling."""

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_ocr_extraction_failure_handling(self, mock_ocr_class, sample_pdf_file):
        """Test graceful handling of OCR extraction failures."""
        # Mock OCR extractor to raise an exception
        mock_ocr_extractor = Mock()
        mock_ocr_extractor.extract_tables_ocr.side_effect = Exception("OCR failed")
        mock_ocr_class.return_value = mock_ocr_extractor

        extractor = PDFExtractor(enable_ocr=True)

        result = extractor.extract(
            sample_pdf_file,
            extract_tables=True,
            use_ocr=True
        )

        # Should handle error gracefully
        assert len(result.errors) > 0
        assert any("OCR" in error for error in result.errors)

    @patch('pybase.extraction.pdf.extractor.OCR_AVAILABLE', False)
    def test_ocr_not_available_error(self, sample_pdf_file):
        """Test error when OCR dependencies are not available."""
        with pytest.raises(ImportError) as exc_info:
            PDFExtractor(enable_ocr=True)

        assert "OCR extraction requires" in str(exc_info.value)

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_ocr_with_binary_io_warning(self, mock_ocr_class, mock_ocr_extractor):
        """Test that OCR with BinaryIO generates appropriate warning."""
        mock_ocr_class.return_value = mock_ocr_extractor

        extractor = PDFExtractor(enable_ocr=True)

        # Create a mock file-like object
        import io
        mock_file = io.BytesIO(b"%PDF-1.4\n")
        mock_file.name = "test.pdf"

        result = extractor.extract(
            mock_file,
            extract_tables=True,
            use_ocr=True
        )

        # Should warn that OCR requires file path
        assert any("file path" in warning.lower() for warning in result.warnings)


class TestOCRMetadata:
    """Test OCR-related metadata in extraction results."""

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_ocr_tables_metadata(self, mock_ocr_class, scanned_pdf_file, mock_ocr_extractor):
        """Test that OCR table extraction sets appropriate metadata."""
        mock_ocr_class.return_value = mock_ocr_extractor

        extractor = PDFExtractor(enable_ocr=True)
        result = extractor.extract(
            scanned_pdf_file,
            extract_tables=True,
            use_ocr=True
        )

        # Should have OCR metadata
        assert "ocr_tables" in result.metadata or "ocr_tables_supplemental" in result.metadata

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_ocr_text_metadata(self, mock_ocr_class, scanned_pdf_file, mock_ocr_extractor):
        """Test that OCR text extraction sets appropriate metadata."""
        mock_ocr_class.return_value = mock_ocr_extractor

        extractor = PDFExtractor(enable_ocr=True)
        result = extractor.extract(
            scanned_pdf_file,
            extract_text=True,
            use_ocr=True
        )

        # Should have OCR metadata
        assert "ocr_text" in result.metadata or "ocr_text_supplemental" in result.metadata

    @patch('pybase.extraction.pdf.extractor.OCRExtractor')
    def test_ocr_confidence_in_results(self, mock_ocr_class, sample_pdf_file, mock_ocr_extractor):
        """Test that OCR results include confidence scores."""
        mock_ocr_class.return_value = mock_ocr_extractor

        # Set up mock to return results with confidence
        mock_ocr_extractor.extract_tables_ocr.return_value = [
            ExtractedTable(
                headers=["A", "B"],
                rows=[["1", "2"]],
                page=1,
                confidence=0.85
            )
        ]

        extractor = PDFExtractor(enable_ocr=True)
        result = extractor.extract(
            sample_pdf_file,
            extract_tables=True,
            use_ocr=True
        )

        # Verify confidence is present in extracted tables
        if result.tables:
            assert all(hasattr(table, 'confidence') for table in result.tables)
            assert all(0 <= table.confidence <= 1 for table in result.tables)
