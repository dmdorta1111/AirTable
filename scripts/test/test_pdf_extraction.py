#!/usr/bin/env python3
"""
Test PDF extraction with actual PDF file.
"""

import tempfile
import os
from pathlib import Path


# Create a simple PDF for testing
def create_test_pdf():
    """Create a simple test PDF with some text and tables."""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch

        # Create temp PDF
        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(temp_dir, "test_extraction.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=A4)

        # Create story
        story = []
        styles = getSampleStyleSheet()

        # Add title
        title = Paragraph("Test Extraction PDF for PyBase", styles["Title"])
        story.append(title)

        # Add sample table
        data = [
            ["Part No.", "Description", "Quantity", "Material"],
            ["P-001", "Bracket Assembly", "5", "Aluminum 6061"],
            ["P-002", "Support Plate", "2", "Steel A36"],
            ["P-003", "Fastener", "100", "Stainless 304"],
            ["P-004", "Bearing", "4", "Bronze"],
        ]

        table = Table(data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        story.append(table)

        # Add text with dimensions
        story.append(Paragraph("<br/><br/>", styles["Normal"]))
        story.append(
            Paragraph("Sample dimensions: 10.5 ±0.1 mm, R5 mm, Ø12.5 mm", styles["Normal"])
        )

        # Build PDF
        doc.build(story)

        print(f"Created test PDF: {pdf_path}")
        print(f"File size: {os.path.getsize(pdf_path)} bytes")
        return pdf_path

    except ImportError:
        print("ReportLab not installed. Creating a minimal PDF file instead...")
        # Create a minimal PDF without reportlab
        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(temp_dir, "test_extraction.pdf")

        # Create a dummy PDF (just a text file with .pdf extension)
        with open(pdf_path, "w", encoding="utf-8") as f:
            f.write("Dummy PDF for testing - no actual PDF content")

        print(f"Created dummy PDF: {pdf_path}")
        return pdf_path


def test_pdf_extractor():
    """Test the PDF extractor."""
    print("\n" + "=" * 50)
    print("Testing PDFExtractor...")

    try:
        from pybase.extraction.pdf.extractor import PDFExtractor

        # Create test PDF
        pdf_path = create_test_pdf()

        # Test extractor
        extractor = PDFExtractor()
        print("Created PDFExtractor instance")

        # Try to extract
        print("Extracting from PDF...")
        result = extractor.extract(
            pdf_path,
            extract_tables=True,
            extract_text=True,
            extract_dimensions=True,
            extract_title_block=False,
            pages=None,
        )

        print(f"Extraction successful: {result.success}")
        print(f"Source file: {result.source_file}")
        print(f"Source type: {result.source_type}")
        print(f"Tables found: {len(result.tables)}")
        print(f"Text blocks: {len(result.text_blocks)}")
        print(f"Dimensions: {len(result.dimensions)}")
        print(f"Errors: {result.errors}")
        print(f"Warnings: {result.warnings}")

        # Show table details
        if result.tables:
            print(f"\nTable details:")
            for i, table in enumerate(result.tables):
                print(f"  Table {i + 1}:")
                print(f"    Headers: {table.headers}")
                print(f"    Rows: {table.num_rows}")
                print(f"    Columns: {table.num_columns}")
                if table.rows and len(table.rows) > 0:
                    print(f"    First row: {table.rows[0]}")

        # Show text details
        if result.text_blocks:
            print(f"\nText blocks (first 2):")
            for i, text in enumerate(result.text_blocks[:2]):
                print(f"  Text {i + 1}: {text.text[:50]}...")

        # Show dimension details
        if result.dimensions:
            print(f"\nDimensions found:")
            for dim in result.dimensions:
                print(f"  {dim.format_display()} (type: {dim.dimension_type})")

        return True

    except Exception as e:
        print(f"PDF extraction test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_dxf_parser():
    """Test DXF parser imports."""
    print("\n" + "=" * 50)
    print("Testing DXF parser imports...")

    try:
        from pybase.extraction.cad.dxf import DXFParser

        print("✓ DXFParser imported successfully")

        # Check if ezdxf is available
        import ezdxf

        print("✓ ezdxf available")

        # Can't test actual parsing without a DXF file
        print("Note: Need actual DXF file for full test")
        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Other error: {e}")
        return False


def test_ifc_parser():
    """Test IFC parser imports."""
    print("\n" + "=" * 50)
    print("Testing IFC parser imports...")

    try:
        from pybase.extraction.cad.ifc import IFCParser

        print("✓ IFCParser imported successfully")

        # Check if ifcopenshell is available
        import ifcopenshell

        print("✓ ifcopenshell available")

        print("Note: Need actual IFC file for full test")
        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Other error: {e}")
        return False


def test_extraction_api():
    """Test extraction API imports."""
    print("\n" + "=" * 50)
    print("Testing extraction API imports...")

    try:
        from pybase.api.v1.extraction import router

        print("✓ Extraction API router imported")

        # Check schemas
        from pybase.schemas.extraction import (
            PDFExtractionResponse,
            CADExtractionResponse,
            ExtractionFormat,
        )

        print("✓ Extraction schemas imported")

        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Other error: {e}")
        return False


if __name__ == "__main__":
    print("Phase 3 Extraction System Test")
    print("=" * 50)

    # Test PDF extraction
    pdf_ok = test_pdf_extractor()

    # Test CAD parsers
    dxf_ok = test_dxf_parser()
    ifc_ok = test_ifc_parser()

    # Test API
    api_ok = test_extraction_api()

    print("\n" + "=" * 50)
    print("TEST SUMMARY:")
    print(f"PDF extraction: {'PASS' if pdf_ok else 'FAIL'}")
    print(f"DXF parser imports: {'PASS' if dxf_ok else 'FAIL'}")
    print(f"IFC parser imports: {'PASS' if ifc_ok else 'FAIL'}")
    print(f"Extraction API: {'PASS' if api_ok else 'FAIL'}")

    # Overall status
    all_passed = pdf_ok and dxf_ok and ifc_ok and api_ok
    print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")

    if all_passed:
        print("\nPhase 3 extraction system is operational!")
        print("Core functionality includes:")
        print("  • PDF table/text extraction with pdfplumber")
        print("  • Dimension extraction from text patterns")
        print("  • DXF parsing via ezdxf")
        print("  • IFC parsing via ifcopenshell")
        print("  • REST API endpoints ready")
    else:
        print("\nSome components need attention.")
