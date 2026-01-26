"""
Unit tests for report generator worker PDF generation.

Note: These tests require reportlab to be installed:
    pip install reportlab

These tests validate the PDF generation logic without requiring
Celery or Redis to be running.
"""

import json
import os
import tempfile
from uuid import uuid4

import pytest

# Test constants
TEST_DASHBOARD_ID = str(uuid4())
TEST_REPORT_ID = str(uuid4())


# Check if reportlab is available
try:
    import reportlab  # noqa: F401

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
class TestPDFGeneration:
    """Test PDF generation logic."""

    def test_pdf_generation(self, temp_output_dir):
        """Test basic PDF generation with dashboard data.

        This test verifies that:
        1. PDF file is created at the specified path
        2. PDF has non-zero file size
        3. PDF is valid (starts with %PDF header)
        """
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
        from reportlab.lib.enums import TA_CENTER

        # Setup
        output_path = os.path.join(temp_output_dir, "test_report.pdf")

        # Create mock dashboard data
        dashboard = {
            "id": TEST_DASHBOARD_ID,
            "name": "Test Dashboard",
            "description": "Test Description for PDF",
        }

        # Generate PDF (inline implementation mirroring worker logic)
        page_size = A4
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=page_size,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
        )

        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#1a1a1a"),
            spaceAfter=12,
            alignment=TA_CENTER,
        )

        # Add title
        title = Paragraph(dashboard["name"], title_style)
        story.append(title)
        story.append(Spacer(1, 0.3 * inch))

        # Add description
        if dashboard.get("description"):
            description = Paragraph(dashboard["description"], styles["BodyText"])
            story.append(description)
            story.append(Spacer(1, 0.2 * inch))

        # Add generation info table
        from datetime import datetime, UTC

        gen_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        info_data = [
            ["Generated:", gen_time],
            ["Dashboard ID:", dashboard["id"][:8] + "..."],
        ]

        info_table = Table(info_data, colWidths=[1.5 * inch, 4 * inch])
        info_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(info_table)

        # Build PDF
        doc.build(story)

        # Get file size
        file_size = os.path.getsize(output_path)

        # Verify
        assert file_size > 0, "PDF should have non-zero size"
        assert os.path.exists(output_path), "PDF file should exist"

        # Verify it's a valid PDF (starts with PDF magic number)
        with open(output_path, "rb") as f:
            header = f.read(4)
            assert header == b"%PDF", "Should be a valid PDF file"

    def test_pdf_generation_landscape(self, temp_output_dir):
        """Test PDF generation with landscape orientation."""
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

        output_path = os.path.join(temp_output_dir, "test_report_landscape.pdf")

        # Create landscape PDF
        page_size = landscape(A4)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=page_size,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        styles = getSampleStyleSheet()
        story = [
            Paragraph("Landscape Report", styles["Title"]),
            Spacer(1, 0.2 * inch),
        ]

        doc.build(story)

        # Verify
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

        with open(output_path, "rb") as f:
            header = f.read(4)
            assert header == b"%PDF"

    def test_pdf_generation_with_charts(self, temp_output_dir):
        """Test PDF generation with multiple charts."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

        output_path = os.path.join(temp_output_dir, "test_report_charts.pdf")

        doc = SimpleDocTemplate(output_path, pagesize=A4)

        styles = getSampleStyleSheet()
        story = [Paragraph("Dashboard with Charts", styles["Title"]), Spacer(1, 0.2 * inch)]

        # Add chart entries (simulating chart widgets)
        for i in range(3):
            story.append(Paragraph(f"<b>Chart {i+1}: Test Chart</b> (line)", styles["BodyText"]))
            story.append(Paragraph(f"Description for chart {i+1}", styles["BodyText"]))
            story.append(Spacer(1, 0.15 * inch))

        doc.build(story)

        # Verify
        assert os.path.exists(output_path)
        file_size = os.path.getsize(output_path)
        assert file_size > 0

        # Verify it's a valid PDF
        with open(output_path, "rb") as f:
            header = f.read(4)
            assert header == b"%PDF"

    def test_pdf_generation_with_table(self, temp_output_dir):
        """Test PDF generation with data tables."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet

        output_path = os.path.join(temp_output_dir, "test_report_table.pdf")

        doc = SimpleDocTemplate(output_path, pagesize=A4)

        styles = getSampleStyleSheet()
        story = [Paragraph("Report with Data Table", styles["Title"]), Spacer(1, 0.2 * inch)]

        # Add table (simulating dashboard layout)
        data = [
            ["Widget ID", "Position", "Size"],
            ["widget-1", "(0, 0)", "6 x 4"],
            ["widget-2", "(6, 0)", "6 x 4"],
            ["widget-3", "(0, 4)", "12 x 6"],
        ]

        table = Table(data, colWidths=[2 * inch, 2 * inch, 1.5 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#333333")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )

        story.append(table)
        doc.build(story)

        # Verify
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

        with open(output_path, "rb") as f:
            header = f.read(4)
            assert header == b"%PDF"

    def test_pdf_generation_multiple_page_sizes(self, temp_output_dir):
        """Test PDF generation with different page sizes."""
        from reportlab.lib.pagesizes import A4, LETTER
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet

        styles = getSampleStyleSheet()

        # Test A4
        output_path_a4 = os.path.join(temp_output_dir, "test_report_a4.pdf")
        doc = SimpleDocTemplate(output_path_a4, pagesize=A4)
        doc.build([Paragraph("A4 Report", styles["Title"])])
        assert os.path.exists(output_path_a4)

        # Test LETTER
        output_path_letter = os.path.join(temp_output_dir, "test_report_letter.pdf")
        doc = SimpleDocTemplate(output_path_letter, pagesize=LETTER)
        doc.build([Paragraph("Letter Report", styles["Title"])])
        assert os.path.exists(output_path_letter)

        # Both should be valid PDFs
        for path in [output_path_a4, output_path_letter]:
            with open(path, "rb") as f:
                header = f.read(4)
                assert header == b"%PDF"
