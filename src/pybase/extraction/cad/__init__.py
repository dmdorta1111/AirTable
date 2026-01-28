"""CAD extraction module for PyBase.

Provides parsers for various CAD file formats:
- DXF: AutoCAD Drawing Exchange Format
- IFC: Industry Foundation Classes (BIM)
- STEP: Standard for the Exchange of Product Data
- CosCAD: CosCAD gRPC-based extraction service
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pybase.extraction.cad.coscad import CosCADExtractor
    from pybase.extraction.cad.dxf import DXFParser
    from pybase.extraction.cad.ifc import IFCParser
    from pybase.extraction.cad.step import STEPParser


def __getattr__(name: str):
    """Lazy import for CAD parsers to avoid import errors when dependencies are missing."""
    if name == "CosCADExtractor":
        from pybase.extraction.cad.coscad import CosCADExtractor

        return CosCADExtractor
    elif name == "DXFParser":
        from pybase.extraction.cad.dxf import DXFParser

        return DXFParser
    elif name == "IFCParser":
        from pybase.extraction.cad.ifc import IFCParser

        return IFCParser
    elif name == "STEPParser":
        from pybase.extraction.cad.step import STEPParser

        return STEPParser
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CosCADExtractor",
    "DXFParser",
    "IFCParser",
    "STEPParser",
]
