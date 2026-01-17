"""Extraction module for PyBase.

This module provides extraction capabilities for:
- PDF documents (tables, text, dimensions)
- CAD files (DXF, IFC, STEP)
- Engineering drawings via Werk24 API
"""

from pybase.extraction.base import (
    ExtractionResult,
    ExtractedTable,
    ExtractedDimension,
    ExtractedText,
    ExtractedTitleBlock,
    ExtractedBOM,
    ExtractedLayer,
    ExtractedBlock,
    ExtractedEntity,
    GeometrySummary,
    CADExtractionResult,
    ExtractionType,
)


# Lazy imports to avoid import errors when optional dependencies are missing
def __getattr__(name: str):
    """Lazy import for optional modules."""
    if name in ("PDFExtractor", "TableExtractor", "OCRExtractor"):
        from pybase.extraction.pdf import PDFExtractor, TableExtractor, OCRExtractor

        return {
            "PDFExtractor": PDFExtractor,
            "TableExtractor": TableExtractor,
            "OCRExtractor": OCRExtractor,
        }[name]
    elif name == "DXFParser":
        from pybase.extraction.cad.dxf import DXFParser

        return DXFParser
    elif name == "IFCParser":
        from pybase.extraction.cad.ifc import IFCParser

        return IFCParser
    elif name == "STEPParser":
        from pybase.extraction.cad.step import STEPParser

        return STEPParser
    elif name == "Werk24Client":
        from pybase.extraction.werk24.client import Werk24Client

        return Werk24Client
    elif name == "Werk24ExtractionResult":
        from pybase.extraction.werk24.client import Werk24ExtractionResult

        return Werk24ExtractionResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Base types
    "ExtractionResult",
    "ExtractedTable",
    "ExtractedDimension",
    "ExtractedText",
    "ExtractedTitleBlock",
    "ExtractedBOM",
    "ExtractedLayer",
    "ExtractedBlock",
    "ExtractedEntity",
    "GeometrySummary",
    "CADExtractionResult",
    "ExtractionType",
    # PDF
    "PDFExtractor",
    "TableExtractor",
    "OCRExtractor",
    # CAD
    "DXFParser",
    "IFCParser",
    "STEPParser",
    # Werk24
    "Werk24Client",
    "Werk24ExtractionResult",
]
