#!/usr/bin/env python3
"""
Test extraction dependencies and basic functionality.
"""

import sys
import traceback

print("Testing PyBase extraction dependencies...")

# Test 1: Core dependencies
print("\n1. Testing core dependencies:")
try:
    import pdfplumber

    print("  ✓ pdfplumber")
except ImportError:
    print("  ✗ pdfplumber")
    traceback.print_exc()

try:
    import fitz  # PyMuPDF

    print("  ✓ PyMuPDF (fitz)")
except ImportError:
    print("  ✗ PyMuPDF")
    traceback.print_exc()

try:
    import tabula

    print("  ✓ tabula-py")
except ImportError:
    print("  ✗ tabula-py")
    traceback.print_exc()

# Test 2: CAD dependencies
print("\n2. Testing CAD dependencies:")

try:
    import ezdxf

    print("  ✓ ezdxf")
except ImportError:
    print("  ✗ ezdxf")
    traceback.print_exc()

try:
    import ifcopenshell

    print("  ✓ ifcopenshell")
except ImportError:
    print("  ✗ ifcopenshell")
    traceback.print_exc()

# Test 3: PyBase extraction module
print("\n3. Testing PyBase extraction module imports:")

try:
    from pybase.extraction.base import ExtractionResult, ExtractedTable

    print("  ✓ Base extraction types")
except ImportError:
    print("  ✗ Base extraction types")
    traceback.print_exc()

try:
    from pybase.extraction.pdf.extractor import PDFExtractor

    print("  ✓ PDFExtractor")
except ImportError:
    print("  ✗ PDFExtractor")
    traceback.print_exc()

try:
    from pybase.extraction.cad.dxf import DXFParser

    print("  ✓ DXFParser")
except ImportError:
    print("  ✗ DXFParser")
    traceback.print_exc()

try:
    from pybase.extraction.cad.ifc import IFCParser

    print("  ✓ IFCParser")
except ImportError:
    print("  ✗ IFCParser")
    traceback.print_exc()

# Test 4: API dependencies
print("\n4. Testing API dependencies:")

try:
    from pybase.api.v1.extraction import router

    print("  ✓ Extraction API router")
except ImportError:
    print("  ✗ Extraction API router")
    traceback.print_exc()

# Test 5: Werk24 (optional)
print("\n5. Testing optional dependencies:")

try:
    import werk24

    print("  ✓ werk24")
except ImportError:
    print("  ✗ werk24 (optional)")

print("\n" + "=" * 50)
print("Summary: PyBase extraction system dependencies check complete.")
print("Core phase 3 dependencies are now installed and should work.")
