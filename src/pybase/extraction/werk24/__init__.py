"""Werk24 API integration module for PyBase.

Provides AI-powered extraction from engineering drawings via the Werk24 API:
- Automatic dimension extraction
- GD&T recognition
- Title block parsing
- BOM extraction
- Part feature identification
"""

from pybase.extraction.werk24.client import Werk24Client, Werk24ExtractionResult

__all__ = [
    "Werk24Client",
    "Werk24ExtractionResult",
]
