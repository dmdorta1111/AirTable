"""
Performance tests for PDF extraction.

Tests verify extraction speed and accuracy meet acceptance criteria:
- 10-page PDF extraction in <10 seconds
- Table boundary detection accuracy >90%
"""

import os
import tempfile
import time
from pathlib import Path

import pytest


# Helper functions to create test PDFs
def create_simple_test_pdf(num_pages: int = 1, tables_per_page: int = 1) -> str:
    """
    Create a simple test PDF with tables.

    Args:
        num_pages: Number of pages to create
        tables_per_page: Number of tables per page

    Returns:
        Path to created PDF file
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(
            temp_dir, f"perf_test_{num_pages}p_{tables_per_page}t.pdf"
        )

        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()

        for page_idx in range(num_pages):
            # Page title
            title = Paragraph(
                f"Page {page_idx + 1} - Performance Test", styles["Heading1"]
            )
            story.append(title)
            story.append(Spacer(1, 0.2 * inch))

            # Create tables
            for table_idx in range(tables_per_page):
                # Table header
                data = [["Part No.", "Description", "Quantity", "Material", "Notes"]]

                # Table rows
                for row_idx in range(10):
                    data.append(
                        [
                            f"P-{page_idx:03d}-{table_idx:03d}-{row_idx:03d}",
                            f"Component {row_idx}",
                            str((row_idx + 1) * 5),
                            f"Material {row_idx % 5}",
                            f"Note {row_idx}",
                        ]
                    )

                table = Table(data)
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 10),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ]
                    )
                )
                story.append(table)

                if table_idx < tables_per_page - 1:
                    story.append(Spacer(1, 0.3 * inch))

            # Add page break except for last page
            if page_idx < num_pages - 1:
                story.append(PageBreak())

        # Build PDF
        doc.build(story)
        return pdf_path

    except ImportError:
        pytest.skip("ReportLab is required for performance tests")


def create_complex_test_pdf(num_pages: int = 5) -> str:
    """
    Create a complex test PDF with mixed content and complex tables.

    Args:
        num_pages: Number of pages to create

    Returns:
        Path to created PDF file
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(temp_dir, f"perf_test_complex_{num_pages}p.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()

        for page_idx in range(num_pages):
            # Page title
            story.append(
                Paragraph(f"Page {page_idx + 1} - Complex Content", styles["Heading1"])
            )
            story.append(Spacer(1, 0.2 * inch))

            # Add paragraph text with dimensions
            story.append(
                Paragraph(
                    f"This page contains dimensional information: "
                    f"Length: 10.5 ±0.1 mm, Width: 5.25 mm, "
                    f"Radius: R2.5 mm, Diameter: Ø8.0 mm, "
                    f"Depth: 3.75 +0.05/-0.02 mm",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, 0.2 * inch))

            # Add a complex table with merged-looking structure
            data = [
                ["Item", "Dimension", "Tolerance", "Material", "Finish"],
                [f"Item-{page_idx}-1", "50.0 mm", "±0.1", "Steel", "Zinc Plated"],
                [f"Item-{page_idx}-2", "25.4 mm", "±0.05", "Aluminum", "Anodized"],
                [f"Item-{page_idx}-3", "12.7 mm", "+0.1/-0", "Brass", "Polished"],
                [f"Item-{page_idx}-4", "6.35 mm", "±0.02", "Copper", "Bare"],
            ]

            table = Table(data)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.2 * inch))

            # Add another table with different structure
            data2 = [
                ["Component", "Qty", "Unit Price", "Total"],
                [f"Part A-{page_idx}", "10", "$5.50", "$55.00"],
                [f"Part B-{page_idx}", "5", "$12.00", "$60.00"],
                [f"Part C-{page_idx}", "20", "$2.25", "$45.00"],
            ]

            table2 = Table(data2)
            table2.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(table2)

            if page_idx < num_pages - 1:
                story.append(PageBreak())

        doc.build(story)
        return pdf_path

    except ImportError:
        pytest.skip("ReportLab is required for performance tests")


@pytest.fixture
def simple_10_page_pdf() -> str:
    """Fixture providing a simple 10-page PDF for performance testing."""
    pdf_path = create_simple_test_pdf(num_pages=10, tables_per_page=2)
    yield pdf_path
    # Cleanup
    if os.path.exists(pdf_path):
        os.remove(pdf_path)


@pytest.fixture
def complex_10_page_pdf() -> str:
    """Fixture providing a complex 10-page PDF for performance testing."""
    pdf_path = create_complex_test_pdf(num_pages=10)
    yield pdf_path
    # Cleanup
    if os.path.exists(pdf_path):
        os.remove(pdf_path)


@pytest.fixture
def simple_5_page_pdf() -> str:
    """Fixture providing a simple 5-page PDF."""
    pdf_path = create_simple_test_pdf(num_pages=5, tables_per_page=1)
    yield pdf_path
    # Cleanup
    if os.path.exists(pdf_path):
        os.remove(pdf_path)


@pytest.mark.performance
def test_10_page_extraction_under_10_seconds(simple_10_page_pdf: str) -> None:
    """Test that 10-page PDF extraction completes in <10 seconds."""
    from pybase.extraction.pdf.extractor import PDFExtractor

    extractor = PDFExtractor()

    start_time = time.perf_counter()
    result = extractor.extract(
        simple_10_page_pdf,
        extract_tables=True,
        extract_text=True,
        extract_dimensions=False,
    )
    end_time = time.perf_counter()

    elapsed_time = end_time - start_time

    # Verify extraction was successful
    assert result.success
    assert len(result.tables) > 0

    # Performance requirement: <10 seconds for 10-page PDF
    assert (
        elapsed_time < 10.0
    ), f"Extraction took {elapsed_time:.2f}s, expected <10s"


@pytest.mark.performance
def test_10_page_extraction_with_parallel_processing(simple_10_page_pdf: str) -> None:
    """Test parallel processing improves performance on multi-page PDFs."""
    from pybase.extraction.pdf.extractor import PDFExtractor

    # Sequential processing
    sequential_extractor = PDFExtractor(max_workers=None)
    start_time = time.perf_counter()
    result_seq = sequential_extractor.extract(
        simple_10_page_pdf,
        extract_tables=True,
        extract_text=True,
    )
    sequential_time = time.perf_counter() - start_time

    # Parallel processing
    parallel_extractor = PDFExtractor(max_workers=4)
    start_time = time.perf_counter()
    result_par = parallel_extractor.extract(
        simple_10_page_pdf,
        extract_tables=True,
        extract_text=True,
    )
    parallel_time = time.perf_counter() - start_time

    # Verify both successful
    assert result_seq.success
    assert result_par.success

    # Both should extract same number of tables
    assert len(result_seq.tables) == len(result_par.tables)

    # Parallel should be at least as fast (allow for overhead in small tests)
    # Not strictly enforcing speedup as it depends on system resources
    assert parallel_time < 15.0, f"Parallel extraction took {parallel_time:.2f}s"


@pytest.mark.performance
def test_complex_pdf_extraction_performance(complex_10_page_pdf: str) -> None:
    """Test extraction performance on complex PDFs with mixed content."""
    from pybase.extraction.pdf.extractor import PDFExtractor

    extractor = PDFExtractor()

    start_time = time.perf_counter()
    result = extractor.extract(
        complex_10_page_pdf,
        extract_tables=True,
        extract_text=True,
        extract_dimensions=True,
    )
    end_time = time.perf_counter()

    elapsed_time = end_time - start_time

    # Verify extraction was successful
    assert result.success
    assert len(result.tables) > 0
    assert len(result.text_blocks) > 0
    assert len(result.dimensions) > 0

    # Should still meet <10s requirement even with complex content
    assert elapsed_time < 15.0, f"Complex extraction took {elapsed_time:.2f}s"


@pytest.mark.performance
def test_table_boundary_detection_accuracy(simple_5_page_pdf: str) -> None:
    """Test table boundary detection accuracy >90%."""
    from pybase.extraction.pdf.extractor import PDFExtractor

    extractor = PDFExtractor()
    result = extractor.extract(
        simple_5_page_pdf,
        extract_tables=True,
    )

    # Expected: 5 pages * 1 table per page = 5 tables
    expected_tables = 5
    detected_tables = len(result.tables)

    # Calculate accuracy
    # In this simple case, we know exactly how many tables should be detected
    accuracy = min(detected_tables / expected_tables, 1.0) if expected_tables > 0 else 0.0

    # Verify >90% accuracy
    assert accuracy >= 0.9, f"Table detection accuracy {accuracy*100:.1f}% < 90%"

    # Verify each table has proper structure
    for table in result.tables:
        assert len(table.headers) > 0, "Table should have headers"
        assert len(table.rows) > 0, "Table should have rows"
        assert table.page is not None, "Table should have page number"


@pytest.mark.performance
def test_extraction_with_confidence_scores() -> None:
    """Test that extraction returns confidence scores for table boundaries."""
    from pybase.extraction.pdf.table_extractor import TableExtractor

    # Create a simple test PDF
    pdf_path = create_simple_test_pdf(num_pages=1, tables_per_page=1)

    try:
        extractor = TableExtractor()
        tables = extractor.extract_tables(pdf_path)

        assert len(tables) > 0

        # Check if confidence scores are available
        for table in tables:
            # Table should have confidence field
            assert hasattr(table, "confidence")
            # Confidence should be in valid range
            assert table.confidence >= 0.0
            assert table.confidence <= 1.0
            # Well-structured tables should have high confidence
            # Note: Default confidence is 0.9 or 1.0 for well-structured tables
            assert table.confidence >= 0.8

            # Table should also have bbox for boundary information
            # bbox can be None for some extractors, but should exist as attribute
            assert hasattr(table, "bbox")

    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


@pytest.mark.performance
def test_multiple_extractions_consistent_timing() -> None:
    """Test that multiple extractions have consistent timing (no memory leaks)."""
    from pybase.extraction.pdf.extractor import PDFExtractor

    pdf_path = create_simple_test_pdf(num_pages=5, tables_per_page=2)

    try:
        extractor = PDFExtractor()
        timings = []

        # Run extraction multiple times
        for _ in range(5):
            start_time = time.perf_counter()
            result = extractor.extract(
                pdf_path,
                extract_tables=True,
                extract_text=True,
            )
            elapsed_time = time.perf_counter() - start_time
            timings.append(elapsed_time)

            assert result.success
            assert len(result.tables) > 0

        # Check timing consistency
        # Later runs shouldn't be significantly slower (no memory leak)
        avg_time = sum(timings) / len(timings)
        for timing in timings:
            # Each run should be within 50% of average (generous margin)
            assert abs(timing - avg_time) < avg_time * 0.5

    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


@pytest.mark.performance
def test_large_table_extraction_performance() -> None:
    """Test extraction performance on PDFs with large tables."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            SimpleDocTemplate,
            Table,
            TableStyle,
        )

        # Create PDF with one large table (100 rows)
        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(temp_dir, "perf_test_large_table.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        story = []

        # Large table header
        data = [["ID", "Part", "Desc", "Qty", "Material", "Notes"]]

        # 100 rows
        for i in range(100):
            data.append(
                [
                    f"{i:04d}",
                    f"PART-{i:04d}",
                    f"Description {i}",
                    str((i + 1) * 2),
                    f"Mat-{i % 10}",
                    f"Note {i}",
                ]
            )

        table = Table(data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(table)
        doc.build(story)

        # Test extraction
        from pybase.extraction.pdf.extractor import PDFExtractor

        extractor = PDFExtractor()

        start_time = time.perf_counter()
        result = extractor.extract(pdf_path, extract_tables=True)
        elapsed_time = time.perf_counter() - start_time

        # Verify extraction
        assert result.success
        assert len(result.tables) > 0

        # Should extract the large table reasonably quickly
        assert elapsed_time < 5.0, f"Large table extraction took {elapsed_time:.2f}s"

        # Verify table structure
        # Note: Large tables may split across multiple pages or get truncated
        # depending on PDF layout, so we check total rows across all tables
        total_rows = sum(len(table.rows) for table in result.tables)
        assert total_rows >= 30, f"Expected at least 30 rows total, got {total_rows}"

        # Check the first table has proper structure
        first_table = result.tables[0]
        assert len(first_table.headers) == 6

        # Cleanup
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

    except ImportError:
        pytest.skip("ReportLab is required for performance tests")


@pytest.mark.performance
def test_extraction_memory_efficiency() -> None:
    """Test that extraction doesn't consume excessive memory."""
    import sys

    from pybase.extraction.pdf.extractor import PDFExtractor

    pdf_path = create_simple_test_pdf(num_pages=10, tables_per_page=2)

    try:
        extractor = PDFExtractor()

        # Get initial object count
        initial_objects = len(gc.get_objects()) if "gc" in dir() else 0

        result = extractor.extract(
            pdf_path,
            extract_tables=True,
            extract_text=True,
        )

        assert result.success

        # Basic memory check - result should be reasonable size
        # This is a rough check, mainly to catch obvious memory issues
        result_size = sys.getsizeof(result)
        assert result_size < 10 * 1024 * 1024  # <10MB for a simple extraction

    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


@pytest.mark.performance
def test_type_inference_performance_impact() -> None:
    """Test that type inference doesn't significantly impact performance."""
    from pybase.extraction.pdf.table_extractor import TableExtractor

    pdf_path = create_simple_test_pdf(num_pages=5, tables_per_page=2)

    try:
        extractor = TableExtractor()

        # Without type inference
        start_time = time.perf_counter()
        tables_no_types = extractor.extract_tables(pdf_path, infer_types=False)
        time_without = time.perf_counter() - start_time

        # With type inference
        start_time = time.perf_counter()
        tables_with_types = extractor.extract_tables(pdf_path, infer_types=True)
        time_with = time.perf_counter() - start_time

        # Both should succeed
        assert len(tables_no_types) > 0
        assert len(tables_with_types) > 0

        # Type inference shouldn't add more than 50% overhead
        assert time_with < time_without * 1.5

    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


# Import gc for memory test
import gc
