"""Helper functions for generating test CAD files.

Provides reusable functions to create sample DXF, IFC, and STEP files for testing
extraction accuracy. These helpers ensure consistent test data generation across
different test modules.

Example:
    from tests.extraction.fixtures.sample_files import create_simple_dxf

    # Create a simple DXF file for testing
    file_path = tmp_path / "test.dxf"
    create_simple_dxf(file_path)

    # Use with parser
    parser = DXFParser()
    result = parser.parse(file_path)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Try to import CAD libraries
try:
    import ezdxf
    from ezdxf.document import Drawing

    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False
    Drawing = Any

try:
    import ifcopenshell
    from ifcopenshell.file import file as IFCFile

    IFCOPENSHELL_AVAILABLE = True
except ImportError:
    IFCOPENSHELL_AVAILABLE = False
    IFCFile = Any

try:
    from OCP.STEPControl import STEPControl_Writer
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

    OCP_AVAILABLE = True
except ImportError:
    OCP_AVAILABLE = False


# ==============================================================================
# DXF File Generators
# ==============================================================================


def create_simple_dxf(file_path: str | Path, version: str = "R2010") -> Path:
    """Create a simple DXF file with basic entities.

    Creates a DXF file containing:
    - A line from (0,0) to (10,10)
    - A circle at (5,5) with radius 3
    - Text "Test Drawing" at default position
    - Basic layer structure

    Args:
        file_path: Path where the DXF file should be created.
        version: DXF version string (default "R2010").

    Returns:
        Path to the created DXF file.

    Raises:
        ImportError: If ezdxf is not available.
    """
    if not EZDXF_AVAILABLE:
        raise ImportError("ezdxf is required for DXF file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.new(version)
    msp = doc.modelspace()

    # Add basic geometry
    msp.add_line((0, 0), (10, 10))
    msp.add_circle((5, 5), radius=3)
    msp.add_text("Test Drawing", dxfattribs={"height": 2.5})

    doc.saveas(file_path)
    logger.debug("Created simple DXF file: %s", file_path)
    return file_path


def create_dimensions_dxf(file_path: str | Path, version: str = "R2010") -> Path:
    """Create a DXF file with various dimension types.

    Creates a DXF file containing:
    - Rectangle geometry (10x5 units)
    - Linear dimension (horizontal)
    - Aligned dimension (vertical)
    - Radius dimension (on circle)
    - Angular dimension (optional)

    Args:
        file_path: Path where the DXF file should be created.
        version: DXF version string (default "R2010").

    Returns:
        Path to the created DXF file.

    Raises:
        ImportError: If ezdxf is not available.
    """
    if not EZDXF_AVAILABLE:
        raise ImportError("ezdxf is required for DXF file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.new(version)
    msp = doc.modelspace()

    # Add rectangle geometry
    msp.add_lwpolyline([(0, 0), (10, 0), (10, 5), (0, 5), (0, 0)])

    # Linear dimension (horizontal)
    msp.add_linear_dim(
        base=(5, -2),
        p1=(0, 0),
        p2=(10, 0),
        dimstyle="EZDXF",
    )

    # Aligned dimension (vertical)
    msp.add_aligned_dim(
        p1=(10, 0),
        p2=(10, 5),
        distance=2,
        dimstyle="EZDXF",
    )

    # Add circle with radius dimension
    msp.add_circle((15, 2.5), radius=2)
    msp.add_radius_dim(
        center=(15, 2.5),
        radius=2,
        angle=45,
        dimstyle="EZDXF",
    )

    # Add diameter dimension
    msp.add_circle((25, 2.5), radius=1.5)
    msp.add_diameter_dim(
        center=(25, 2.5),
        radius=1.5,
        angle=135,
        dimstyle="EZDXF",
    )

    doc.saveas(file_path)
    logger.debug("Created dimensions DXF file: %s", file_path)
    return file_path


def create_text_dxf(file_path: str | Path, version: str = "R2010") -> Path:
    """Create a DXF file with various text entities.

    Creates a DXF file containing:
    - Simple TEXT entity
    - Large title text
    - MTEXT with formatting and multiple lines
    - Small annotation text
    - Text with different heights and styles

    Args:
        file_path: Path where the DXF file should be created.
        version: DXF version string (default "R2010").

    Returns:
        Path to the created DXF file.

    Raises:
        ImportError: If ezdxf is not available.
    """
    if not EZDXF_AVAILABLE:
        raise ImportError("ezdxf is required for DXF file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.new(version)
    msp = doc.modelspace()

    # Regular TEXT entities with different heights
    msp.add_text("Simple Text", dxfattribs={"height": 1.0}).set_placement((0, 0))
    msp.add_text("DRAWING TITLE", dxfattribs={"height": 5.0}).set_placement((0, 5))
    msp.add_text("Note: Small annotation", dxfattribs={"height": 0.5}).set_placement((0, 15))

    # MTEXT with formatting
    msp.add_mtext(
        "Multi-line text\\Pwith paragraph\\Pand formatting",
        dxfattribs={"char_height": 1.5, "width": 20},
    ).set_location((0, 10))

    # Technical text
    msp.add_text("Material: AISI 304", dxfattribs={"height": 1.2}).set_placement((0, 20))
    msp.add_text("Tolerance: ±0.1mm", dxfattribs={"height": 1.0}).set_placement((0, 22))

    doc.saveas(file_path)
    logger.debug("Created text DXF file: %s", file_path)
    return file_path


def create_blocks_dxf(file_path: str | Path, version: str = "R2010") -> Path:
    """Create a DXF file with block definitions and inserts.

    Creates a DXF file containing:
    - Simple block definition (MARKER)
    - Block with attributes (PART)
    - Multiple block inserts at different locations
    - Block inserts with attribute values
    - Nested blocks (optional)

    Args:
        file_path: Path where the DXF file should be created.
        version: DXF version string (default "R2010").

    Returns:
        Path to the created DXF file.

    Raises:
        ImportError: If ezdxf is not available.
    """
    if not EZDXF_AVAILABLE:
        raise ImportError("ezdxf is required for DXF file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.new(version)
    msp = doc.modelspace()

    # Create a simple marker block
    marker_block = doc.blocks.new(name="MARKER")
    marker_block.add_circle((0, 0), radius=0.5)
    marker_block.add_line((-1, 0), (1, 0))
    marker_block.add_line((0, -1), (0, 1))

    # Create block with attributes
    part_block = doc.blocks.new(name="PART")
    part_block.add_circle((0, 0), radius=1)
    part_block.add_attdef(
        tag="PART_NUMBER",
        text="P-001",
        insert=(0, -1.5),
        dxfattribs={"height": 0.5},
    )
    part_block.add_attdef(
        tag="DESCRIPTION",
        text="Part Description",
        insert=(0, -2.0),
        dxfattribs={"height": 0.3},
    )

    # Insert marker blocks at different locations
    msp.add_blockref("MARKER", (0, 0))
    msp.add_blockref("MARKER", (10, 10))
    msp.add_blockref("MARKER", (20, 0))

    # Insert part block with attributes
    part_insert = msp.add_blockref(
        "PART",
        (5, 5),
        dxfattribs={
            "xscale": 1.5,
            "yscale": 1.5,
        },
    )
    part_insert.add_attrib("PART_NUMBER", "P-123")
    part_insert.add_attrib("DESCRIPTION", "Test Part")

    doc.saveas(file_path)
    logger.debug("Created blocks DXF file: %s", file_path)
    return file_path


def create_layers_dxf(file_path: str | Path, version: str = "R2010") -> Path:
    """Create a DXF file with multiple layers.

    Creates a DXF file containing:
    - Multiple layers with different properties
    - Entities distributed across layers
    - Different layer colors and linetypes
    - Some layers frozen/locked

    Args:
        file_path: Path where the DXF file should be created.
        version: DXF version string (default "R2010").

    Returns:
        Path to the created DXF file.

    Raises:
        ImportError: If ezdxf is not available.
    """
    if not EZDXF_AVAILABLE:
        raise ImportError("ezdxf is required for DXF file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.new(version)
    msp = doc.modelspace()

    # Create layers with different properties
    doc.layers.add("DIMENSIONS", color=1, linetype="CONTINUOUS")  # Red
    doc.layers.add("TEXT", color=3, linetype="CONTINUOUS")  # Green
    doc.layers.add("GEOMETRY", color=5, linetype="CONTINUOUS")  # Blue
    doc.layers.add("HIDDEN", color=8, linetype="DASHED")  # Gray, dashed
    doc.layers.add("CENTERLINE", color=6, linetype="CENTER")  # Magenta, center

    # Add entities on different layers
    msp.add_line((0, 0), (10, 0), dxfattribs={"layer": "GEOMETRY"})
    msp.add_line((10, 0), (10, 5), dxfattribs={"layer": "GEOMETRY"})
    msp.add_line((10, 5), (0, 5), dxfattribs={"layer": "GEOMETRY"})
    msp.add_line((0, 5), (0, 0), dxfattribs={"layer": "GEOMETRY"})

    msp.add_text("Main Drawing", dxfattribs={"layer": "TEXT", "height": 2.0})
    msp.add_linear_dim(
        base=(5, -2),
        p1=(0, 0),
        p2=(10, 0),
        dimstyle="EZDXF",
        dxfattribs={"layer": "DIMENSIONS"},
    )

    msp.add_circle((5, 2.5), radius=1, dxfattribs={"layer": "GEOMETRY"})
    msp.add_line((-2, 2.5), (12, 2.5), dxfattribs={"layer": "CENTERLINE"})
    msp.add_line((15, 0), (20, 5), dxfattribs={"layer": "HIDDEN"})

    doc.saveas(file_path)
    logger.debug("Created layers DXF file: %s", file_path)
    return file_path


def create_title_block_dxf(file_path: str | Path, version: str = "R2010") -> Path:
    """Create a DXF file with a title block.

    Creates a DXF file containing:
    - Drawing border
    - Title block with standard fields
    - Project information
    - Revision block

    Args:
        file_path: Path where the DXF file should be created.
        version: DXF version string (default "R2010").

    Returns:
        Path to the created DXF file.

    Raises:
        ImportError: If ezdxf is not available.
    """
    if not EZDXF_AVAILABLE:
        raise ImportError("ezdxf is required for DXF file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.new(version)
    msp = doc.modelspace()

    # Create title block layer
    doc.layers.add("TITLEBLOCK", color=7)

    # Drawing border (A3 size: 420x297mm)
    border_width = 420
    border_height = 297
    msp.add_lwpolyline(
        [
            (0, 0),
            (border_width, 0),
            (border_width, border_height),
            (0, border_height),
            (0, 0),
        ],
        dxfattribs={"layer": "TITLEBLOCK"},
    )

    # Title block rectangle (bottom right corner)
    tb_x = border_width - 180
    tb_y = 10
    tb_width = 170
    tb_height = 50

    msp.add_lwpolyline(
        [
            (tb_x, tb_y),
            (tb_x + tb_width, tb_y),
            (tb_x + tb_width, tb_y + tb_height),
            (tb_x, tb_y + tb_height),
            (tb_x, tb_y),
        ],
        dxfattribs={"layer": "TITLEBLOCK"},
    )

    # Title block fields
    msp.add_text(
        "TITLE: Test Drawing",
        dxfattribs={"layer": "TITLEBLOCK", "height": 5.0},
    ).set_placement((tb_x + 5, tb_y + 35))

    msp.add_text(
        "PART NUMBER: DRW-001",
        dxfattribs={"layer": "TITLEBLOCK", "height": 2.5},
    ).set_placement((tb_x + 5, tb_y + 25))

    msp.add_text(
        "MATERIAL: AISI 304",
        dxfattribs={"layer": "TITLEBLOCK", "height": 2.0},
    ).set_placement((tb_x + 5, tb_y + 20))

    msp.add_text(
        "SCALE: 1:1",
        dxfattribs={"layer": "TITLEBLOCK", "height": 2.0},
    ).set_placement((tb_x + 5, tb_y + 15))

    msp.add_text(
        "DATE: 2024-01-01",
        dxfattribs={"layer": "TITLEBLOCK", "height": 2.0},
    ).set_placement((tb_x + 90, tb_y + 15))

    msp.add_text(
        "REV: A",
        dxfattribs={"layer": "TITLEBLOCK", "height": 2.0},
    ).set_placement((tb_x + 150, tb_y + 15))

    # Add some drawing content
    msp.add_circle((100, 150), radius=30)
    msp.add_line((50, 150), (150, 150), dxfattribs={"layer": "CENTERLINE"})

    doc.saveas(file_path)
    logger.debug("Created title block DXF file: %s", file_path)
    return file_path


def create_complex_dxf(file_path: str | Path, version: str = "R2010") -> Path:
    """Create a complex DXF file with all features.

    Creates a comprehensive DXF file containing:
    - Multiple layers
    - Various dimensions (linear, aligned, radius, diameter)
    - Text entities (TEXT and MTEXT)
    - Block definitions and inserts
    - Title block
    - Various geometry types

    Args:
        file_path: Path where the DXF file should be created.
        version: DXF version string (default "R2010").

    Returns:
        Path to the created DXF file.

    Raises:
        ImportError: If ezdxf is not available.
    """
    if not EZDXF_AVAILABLE:
        raise ImportError("ezdxf is required for DXF file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.new(version)
    msp = doc.modelspace()

    # Create layers
    doc.layers.add("DIMENSIONS", color=1)
    doc.layers.add("TEXT", color=3)
    doc.layers.add("GEOMETRY", color=5)
    doc.layers.add("BLOCKS", color=4)
    doc.layers.add("TITLEBLOCK", color=7)

    # Add geometry
    msp.add_lwpolyline(
        [(10, 10), (50, 10), (50, 30), (10, 30), (10, 10)],
        dxfattribs={"layer": "GEOMETRY"},
    )

    # Add dimensions
    msp.add_linear_dim(
        base=(30, 5),
        p1=(10, 10),
        p2=(50, 10),
        dimstyle="EZDXF",
        dxfattribs={"layer": "DIMENSIONS"},
    )

    msp.add_aligned_dim(
        p1=(50, 10),
        p2=(50, 30),
        distance=5,
        dimstyle="EZDXF",
        dxfattribs={"layer": "DIMENSIONS"},
    )

    # Add circle with radius dimension
    msp.add_circle((70, 20), radius=8, dxfattribs={"layer": "GEOMETRY"})
    msp.add_radius_dim(
        center=(70, 20),
        radius=8,
        angle=45,
        dimstyle="EZDXF",
        dxfattribs={"layer": "DIMENSIONS"},
    )

    # Add text
    msp.add_text(
        "COMPLEX DRAWING",
        dxfattribs={"layer": "TEXT", "height": 4.0},
    ).set_placement((10, 40))

    # Add block
    bolt_block = doc.blocks.new(name="BOLT")
    bolt_block.add_circle((0, 0), radius=2)
    bolt_block.add_circle((0, 0), radius=0.5)

    # Insert blocks
    msp.add_blockref("BOLT", (20, 20), dxfattribs={"layer": "BLOCKS"})
    msp.add_blockref("BOLT", (40, 20), dxfattribs={"layer": "BLOCKS"})

    doc.saveas(file_path)
    logger.debug("Created complex DXF file: %s", file_path)
    return file_path


# ==============================================================================
# IFC File Generators (Placeholder for Phase 2)
# ==============================================================================


def create_simple_ifc(file_path: str | Path) -> Path:
    """Create a simple IFC file with basic building elements.

    Note:
        This is a placeholder for Phase 2 implementation.

    Args:
        file_path: Path where the IFC file should be created.

    Returns:
        Path to the created IFC file.

    Raises:
        ImportError: If ifcopenshell is not available.
        NotImplementedError: Currently not implemented.
    """
    if not IFCOPENSHELL_AVAILABLE:
        raise ImportError("ifcopenshell is required for IFC file generation")

    raise NotImplementedError("IFC file generation will be implemented in Phase 2")


# ==============================================================================
# STEP File Generators (Placeholder for Phase 2)
# ==============================================================================


def create_simple_step(file_path: str | Path) -> Path:
    """Create a simple STEP file with basic geometry.

    Note:
        This is a placeholder for Phase 2 implementation.

    Args:
        file_path: Path where the STEP file should be created.

    Returns:
        Path to the created STEP file.

    Raises:
        ImportError: If OCP is not available.
        NotImplementedError: Currently not implemented.
    """
    if not OCP_AVAILABLE:
        raise ImportError("OCP (OpenCascade) is required for STEP file generation")

    raise NotImplementedError("STEP file generation will be implemented in Phase 2")
