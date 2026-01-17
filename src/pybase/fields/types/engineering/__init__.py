"""Engineering-specific field types for PyBase.

This module provides specialized field types for engineering and
manufacturing data, including:
- Dimension with tolerances
- GD&T (Geometric Dimensioning and Tolerancing)
- Thread specifications
- Surface finish
- Material specifications
"""

from pybase.fields.types.engineering.dimension import DimensionFieldHandler
from pybase.fields.types.engineering.gdt import GDTFieldHandler
from pybase.fields.types.engineering.thread import ThreadFieldHandler
from pybase.fields.types.engineering.surface_finish import SurfaceFinishFieldHandler
from pybase.fields.types.engineering.material import MaterialFieldHandler

__all__ = [
    "DimensionFieldHandler",
    "GDTFieldHandler",
    "ThreadFieldHandler",
    "SurfaceFinishFieldHandler",
    "MaterialFieldHandler",
]
