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
    from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
    from OCP.BRepPrimAPI import (
        BRepPrimAPI_MakeBox,
        BRepPrimAPI_MakeCylinder,
        BRepPrimAPI_MakeSphere,
        BRepPrimAPI_MakeCone,
        BRepPrimAPI_MakeTorus,
    )
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut
    from OCP.gp import gp_Pnt, gp_Vec, gp_Ax2, gp_Dir, gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB
    from OCP.TCollection import TCollection_AsciiString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDocStd import TDocStd_Document
    from OCP.XCAFDoc import (
        XCAFDoc_DocumentTool,
        XCAFDoc_ShapeTool,
        XCAFDoc_ColorTool,
    )
    from OCP.TDF import TDF_LabelSequence, TDF_Label
    from OCP.TopLoc import TopLoc_Location
    from OCP.IFSelect import IFSelect_RetDone

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
# Test Corpus Access Functions
# ==============================================================================


def get_test_dxf_dir() -> Path:
    """Get the directory containing test DXF files.

    Returns:
        Path to the directory containing DXF test files.
    """
    return Path(__file__).parent / "dxf"


def list_test_dxf_files() -> list[Path]:
    """List all available test DXF files.

    Returns:
        List of paths to all DXF test files in the corpus.
    """
    dxf_dir = get_test_dxf_dir()
    if not dxf_dir.exists():
        return []
    return sorted(dxf_dir.glob("*.dxf"))


def get_test_dxf_file(name: str) -> Path:
    """Get path to a specific test DXF file.

    Args:
        name: Name of the test file (with or without .dxf extension).

    Returns:
        Path to the test DXF file.

    Raises:
        FileNotFoundError: If the test file does not exist.
    """
    if not name.endswith(".dxf"):
        name = f"{name}.dxf"

    file_path = get_test_dxf_dir() / name

    if not file_path.exists():
        raise FileNotFoundError(f"Test DXF file not found: {name}")

    return file_path


def get_test_files_by_category() -> dict[str, list[str]]:
    """Categorize test DXF files by their primary feature.

    Returns:
        Dictionary mapping category names to lists of test file names.
    """
    categories = {
        "dimensions": [
            "dimensions_various.dxf",
            "linear_dimensions_only.dxf",
            "radial_dimensions_only.dxf",
            "angular_dimensions_only.dxf",
            "ordinate_dimensions.dxf",
            "dimension_chain.dxf",
            "baseline_dimensions.dxf",
            "dimension_tolerance.dxf",
        ],
        "text": [
            "text_formatting.dxf",
            "mtext_advanced.dxf",
            "special_characters_text.dxf",
        ],
        "blocks": [
            "nested_blocks.dxf",
            "blocks_with_attributes.dxf",
            "scaled_blocks.dxf",
            "rotated_elements.dxf",
        ],
        "layers": [
            "multi_layer_complex.dxf",
        ],
        "title_blocks": [
            "title_block_standard.dxf",
        ],
        "geometry": [
            "geometric_shapes_variety.dxf",
            "polyline_variations.dxf",
            "concentric_circles.dxf",
            "3d_entities.dxf",
        ],
        "annotations": [
            "leader_annotations.dxf",
            "threaded_hole_callout.dxf",
            "surface_finish_symbols.dxf",
            "gdt_feature_control_frame.dxf",
        ],
        "views": [
            "section_view_markers.dxf",
            "detail_view_marker.dxf",
            "isometric_drawing.dxf",
        ],
        "mechanical": [
            "mechanical_part_detailed.dxf",
            "welding_symbols.dxf",
            "assembly_drawing.dxf",
        ],
        "electrical": [
            "electrical_symbols.dxf",
            "pcb_layout.dxf",
        ],
        "architectural": [
            "architectural_floor_plan.dxf",
        ],
        "civil": [
            "survey_map.dxf",
        ],
        "advanced": [
            "hatching_patterns.dxf",
            "viewport_layouts.dxf",
            "tables_grid.dxf",
            "revision_cloud.dxf",
            "construction_lines.dxf",
        ],
        "edge_cases": [
            "empty_drawing.dxf",
            "single_entity.dxf",
            "overlapping_entities.dxf",
        ],
        "versions": [
            "dxf_r2013_version.dxf",
            "dxf_r2018_version.dxf",
        ],
        "references": [
            "xrefs_external.dxf",
            "multiple_sheets_reference.dxf",
        ],
        "basic": [
            "simple_drawing.dxf",
        ],
    }

    return categories


# ==============================================================================
# IFC File Generators
# ==============================================================================


def _create_ifc_base_structure(
    ifc_file: IFCFile,
    project_name: str = "Test Project",
    site_name: str = "Test Site",
    building_name: str = "Test Building",
) -> dict[str, Any]:
    """Create basic IFC spatial structure.

    Args:
        ifc_file: IFC file object.
        project_name: Name of the project.
        site_name: Name of the site.
        building_name: Name of the building.

    Returns:
        Dictionary with created entities (project, site, building, context, etc.)
    """
    # Determine schema version for compatibility
    schema = ifc_file.schema
    is_ifc4 = "IFC4" in schema

    # Create person and organization (schema-compatible)
    if is_ifc4:
        person = ifc_file.createIfcPerson(
            Identification="TestUser",
            FamilyName="User",
            GivenName="Test",
        )
        org = ifc_file.createIfcOrganization(
            Identification="TestOrg",
            Name="Test Organization",
        )
    else:
        # IFC2X3 doesn't have Identification parameter for IfcPerson
        person = ifc_file.createIfcPerson(
            Id="TestUser",
            FamilyName="User",
            GivenName="Test",
        )
        org = ifc_file.createIfcOrganization(
            Id="TestOrg",
            Name="Test Organization",
        )

    person_org = ifc_file.createIfcPersonAndOrganization(
        ThePerson=person,
        TheOrganization=org,
    )

    # Create application and ownership
    app = ifc_file.createIfcApplication(
        ApplicationDeveloper=org,
        Version="1.0",
        ApplicationFullName="PyBase Test Generator",
        ApplicationIdentifier="pybase",
    )
    owner_history = ifc_file.createIfcOwnerHistory(
        OwningUser=person_org,
        OwningApplication=app,
        CreationDate=1609459200,  # 2021-01-01
    )

    # Create project
    project = ifc_file.createIfcProject(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner_history,
        Name=project_name,
    )

    # Create geometric representation context
    context = ifc_file.createIfcGeometricRepresentationContext(
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=1.0e-5,
        WorldCoordinateSystem=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )

    # Create length unit
    length_unit = ifc_file.createIfcSIUnit(
        UnitType="LENGTHUNIT",
        Name="METRE",
    )
    ifc_file.createIfcUnitAssignment(Units=[length_unit])

    # Create site
    site_placement = ifc_file.createIfcLocalPlacement(
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        )
    )
    site = ifc_file.createIfcSite(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner_history,
        Name=site_name,
        ObjectPlacement=site_placement,
    )

    # Create building
    building_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=site_placement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    building = ifc_file.createIfcBuilding(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner_history,
        Name=building_name,
        ObjectPlacement=building_placement,
    )

    # Create relationships
    ifc_file.createIfcRelAggregates(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner_history,
        RelatingObject=project,
        RelatedObjects=[site],
    )
    ifc_file.createIfcRelAggregates(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner_history,
        RelatingObject=site,
        RelatedObjects=[building],
    )

    return {
        "project": project,
        "site": site,
        "building": building,
        "context": context,
        "owner_history": owner_history,
    }


def create_simple_ifc(file_path: str | Path) -> Path:
    """Create a simple IFC file with basic building elements.

    Creates an IFC file containing:
    - Basic spatial structure (project, site, building, storey)
    - Simple wall element
    - Basic properties

    Args:
        file_path: Path where the IFC file should be created.

    Returns:
        Path to the created IFC file.

    Raises:
        ImportError: If ifcopenshell is not available.
    """
    if not IFCOPENSHELL_AVAILABLE:
        raise ImportError("ifcopenshell is required for IFC file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create IFC file
    ifc_file = ifcopenshell.file(schema="IFC4")

    # Create base structure
    base = _create_ifc_base_structure(ifc_file, "Simple Building Project")

    # Create building storey
    storey_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=base["building"].ObjectPlacement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    storey = ifc_file.createIfcBuildingStorey(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Ground Floor",
        ObjectPlacement=storey_placement,
        Elevation=0.0,
    )

    # Relate storey to building
    ifc_file.createIfcRelAggregates(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingObject=base["building"],
        RelatedObjects=[storey],
    )

    # Create a simple wall
    wall_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=storey_placement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    wall = ifc_file.createIfcWall(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Wall-001",
        ObjectPlacement=wall_placement,
    )

    # Relate wall to storey
    ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingStructure=storey,
        RelatedElements=[wall],
    )

    # Write file
    ifc_file.write(str(file_path))
    logger.debug("Created simple IFC file: %s", file_path)
    return file_path


def create_complex_ifc(file_path: str | Path) -> Path:
    """Create a complex IFC file with multiple building elements.

    Creates an IFC file containing:
    - Multiple storeys
    - Various building elements (walls, doors, windows, slabs)
    - Properties and property sets
    - Materials

    Args:
        file_path: Path where the IFC file should be created.

    Returns:
        Path to the created IFC file.

    Raises:
        ImportError: If ifcopenshell is not available.
    """
    if not IFCOPENSHELL_AVAILABLE:
        raise ImportError("ifcopenshell is required for IFC file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create IFC file
    ifc_file = ifcopenshell.file(schema="IFC4")

    # Create base structure
    base = _create_ifc_base_structure(ifc_file, "Complex Building Project")

    # Create multiple storeys
    storeys = []
    for i in range(3):
        storey_placement = ifc_file.createIfcLocalPlacement(
            PlacementRelTo=base["building"].ObjectPlacement,
            RelativePlacement=ifc_file.createIfcAxis2Placement3D(
                Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, i * 3.0))
            ),
        )
        storey = ifc_file.createIfcBuildingStorey(
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=base["owner_history"],
            Name=f"Floor {i+1}",
            ObjectPlacement=storey_placement,
            Elevation=i * 3.0,
        )
        storeys.append(storey)

        # Relate storey to building
        ifc_file.createIfcRelAggregates(
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=base["owner_history"],
            RelatingObject=base["building"],
            RelatedObjects=[storey],
        )

    # Add elements to first storey
    elements = []
    storey = storeys[0]

    # Create walls
    for i in range(4):
        wall_placement = ifc_file.createIfcLocalPlacement(
            PlacementRelTo=storey.ObjectPlacement,
            RelativePlacement=ifc_file.createIfcAxis2Placement3D(
                Location=ifc_file.createIfcCartesianPoint((i * 5.0, 0.0, 0.0))
            ),
        )
        wall = ifc_file.createIfcWall(
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=base["owner_history"],
            Name=f"Wall-{i+1:03d}",
            ObjectPlacement=wall_placement,
        )
        elements.append(wall)

    # Create doors
    for i in range(2):
        door_placement = ifc_file.createIfcLocalPlacement(
            PlacementRelTo=storey.ObjectPlacement,
            RelativePlacement=ifc_file.createIfcAxis2Placement3D(
                Location=ifc_file.createIfcCartesianPoint((i * 10.0, 0.0, 0.0))
            ),
        )
        door = ifc_file.createIfcDoor(
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=base["owner_history"],
            Name=f"Door-{i+1:03d}",
            ObjectPlacement=door_placement,
        )
        elements.append(door)

    # Create windows
    for i in range(3):
        window_placement = ifc_file.createIfcLocalPlacement(
            PlacementRelTo=storey.ObjectPlacement,
            RelativePlacement=ifc_file.createIfcAxis2Placement3D(
                Location=ifc_file.createIfcCartesianPoint((i * 7.0, 0.0, 1.5))
            ),
        )
        window = ifc_file.createIfcWindow(
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=base["owner_history"],
            Name=f"Window-{i+1:03d}",
            ObjectPlacement=window_placement,
        )
        elements.append(window)

    # Create slab
    slab_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=storey.ObjectPlacement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    slab = ifc_file.createIfcSlab(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Floor Slab",
        ObjectPlacement=slab_placement,
    )
    elements.append(slab)

    # Relate elements to storey
    ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingStructure=storey,
        RelatedElements=elements,
    )

    # Write file
    ifc_file.write(str(file_path))
    logger.debug("Created complex IFC file: %s", file_path)
    return file_path


def create_ifc_with_properties(file_path: str | Path) -> Path:
    """Create IFC file with property sets and quantities.

    Args:
        file_path: Path where the IFC file should be created.

    Returns:
        Path to the created IFC file.

    Raises:
        ImportError: If ifcopenshell is not available.
    """
    if not IFCOPENSHELL_AVAILABLE:
        raise ImportError("ifcopenshell is required for IFC file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    ifc_file = ifcopenshell.file(schema="IFC4")
    base = _create_ifc_base_structure(ifc_file, "Properties Test Project")

    # Create storey
    storey_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=base["building"].ObjectPlacement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    storey = ifc_file.createIfcBuildingStorey(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Ground Floor",
        ObjectPlacement=storey_placement,
        Elevation=0.0,
    )

    ifc_file.createIfcRelAggregates(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingObject=base["building"],
        RelatedObjects=[storey],
    )

    # Create wall with properties
    wall_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=storey_placement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    wall = ifc_file.createIfcWall(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Wall with Properties",
        ObjectPlacement=wall_placement,
    )

    # Create property set
    property_values = [
        ifc_file.createIfcPropertySingleValue(
            Name="LoadBearing",
            NominalValue=ifc_file.createIfcBoolean(True),
        ),
        ifc_file.createIfcPropertySingleValue(
            Name="FireRating",
            NominalValue=ifc_file.createIfcLabel("120 min"),
        ),
        ifc_file.createIfcPropertySingleValue(
            Name="ThermalTransmittance",
            NominalValue=ifc_file.createIfcReal(0.24),
        ),
    ]

    property_set = ifc_file.createIfcPropertySet(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Pset_WallCommon",
        HasProperties=property_values,
    )

    ifc_file.createIfcRelDefinesByProperties(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatedObjects=[wall],
        RelatingPropertyDefinition=property_set,
    )

    # Relate to storey
    ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingStructure=storey,
        RelatedElements=[wall],
    )

    ifc_file.write(str(file_path))
    logger.debug("Created IFC file with properties: %s", file_path)
    return file_path


def generate_ifc_test_corpus(output_dir: str | Path) -> list[Path]:
    """Generate comprehensive IFC test corpus with 30+ files.

    Creates diverse IFC test files covering:
    - Different building element types
    - Various spatial structures
    - Property sets and quantities
    - Materials and classifications
    - Different complexity levels

    Args:
        output_dir: Directory where test files should be created.

    Returns:
        List of paths to all created test files.

    Raises:
        ImportError: If ifcopenshell is not available.
    """
    if not IFCOPENSHELL_AVAILABLE:
        raise ImportError("ifcopenshell is required for IFC file generation")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    created_files = []

    # Template for generating multiple similar files with variations
    building_elements = [
        ("walls", "IfcWall", "Wall"),
        ("doors", "IfcDoor", "Door"),
        ("windows", "IfcWindow", "Window"),
        ("slabs", "IfcSlab", "Slab"),
        ("beams", "IfcBeam", "Beam"),
        ("columns", "IfcColumn", "Column"),
        ("stairs", "IfcStair", "Stair"),
        ("roofs", "IfcRoof", "Roof"),
        ("railings", "IfcRailing", "Railing"),
        ("curtainwalls", "IfcCurtainWall", "Curtain Wall"),
    ]

    # Generate files with specific element types
    for i, (elem_type, ifc_class, elem_name) in enumerate(building_elements):
        file_path = output_dir / f"{i+1:02d}_{elem_type}_only.ifc"
        _create_ifc_with_element_type(file_path, ifc_class, elem_name, count=5)
        created_files.append(file_path)

    # Generate multi-storey buildings
    for i, storey_count in enumerate([2, 3, 5, 10]):
        file_path = output_dir / f"{11+i:02d}_building_{storey_count}_storeys.ifc"
        _create_multi_storey_building(file_path, storey_count)
        created_files.append(file_path)

    # Generate files with properties
    file_path = output_dir / "15_with_properties.ifc"
    create_ifc_with_properties(file_path)
    created_files.append(file_path)

    # Generate files with materials
    file_path = output_dir / "16_with_materials.ifc"
    _create_ifc_with_materials(file_path)
    created_files.append(file_path)

    # Generate files with spaces
    file_path = output_dir / "17_with_spaces.ifc"
    _create_ifc_with_spaces(file_path)
    created_files.append(file_path)

    # Generate mixed element files
    for i in range(5):
        file_path = output_dir / f"{18+i:02d}_mixed_elements_{i+1}.ifc"
        _create_mixed_elements_building(file_path, seed=i)
        created_files.append(file_path)

    # Generate files with different schemas
    for i, schema in enumerate(["IFC2X3", "IFC4"]):
        file_path = output_dir / f"{23+i:02d}_schema_{schema}.ifc"
        _create_ifc_schema_variant(file_path, schema)
        created_files.append(file_path)

    # Generate complex structure
    file_path = output_dir / "25_complex_structure.ifc"
    create_complex_ifc(file_path)
    created_files.append(file_path)

    # Generate simple building
    file_path = output_dir / "26_simple_building.ifc"
    create_simple_ifc(file_path)
    created_files.append(file_path)

    # Generate additional specialized files
    specialized_files = [
        ("27_with_openings.ifc", _create_ifc_with_openings),
        ("28_with_type_objects.ifc", _create_ifc_with_type_objects),
        ("29_residential_building.ifc", _create_residential_building),
        ("30_office_building.ifc", _create_office_building),
        ("31_warehouse.ifc", _create_warehouse),
    ]

    for filename, generator_func in specialized_files:
        file_path = output_dir / filename
        generator_func(file_path)
        created_files.append(file_path)

    logger.info(f"Generated {len(created_files)} IFC test files in {output_dir}")
    return created_files


def _create_ifc_with_element_type(
    file_path: Path, ifc_class: str, elem_name: str, count: int = 5
) -> Path:
    """Create IFC file with specific element type."""
    ifc_file = ifcopenshell.file(schema="IFC4")
    base = _create_ifc_base_structure(ifc_file, f"{elem_name} Test Project")

    storey_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=base["building"].ObjectPlacement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    storey = ifc_file.createIfcBuildingStorey(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Ground Floor",
        ObjectPlacement=storey_placement,
        Elevation=0.0,
    )

    ifc_file.createIfcRelAggregates(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingObject=base["building"],
        RelatedObjects=[storey],
    )

    elements = []
    for i in range(count):
        elem_placement = ifc_file.createIfcLocalPlacement(
            PlacementRelTo=storey_placement,
            RelativePlacement=ifc_file.createIfcAxis2Placement3D(
                Location=ifc_file.createIfcCartesianPoint((i * 3.0, 0.0, 0.0))
            ),
        )

        elem = ifc_file.create_entity(
            ifc_class,
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=base["owner_history"],
            Name=f"{elem_name}-{i+1:03d}",
            ObjectPlacement=elem_placement,
        )
        elements.append(elem)

    ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingStructure=storey,
        RelatedElements=elements,
    )

    ifc_file.write(str(file_path))
    logger.debug(f"Created IFC file with {ifc_class}: %s", file_path)
    return file_path


def _create_multi_storey_building(file_path: Path, storey_count: int) -> Path:
    """Create IFC file with multiple storeys."""
    ifc_file = ifcopenshell.file(schema="IFC4")
    base = _create_ifc_base_structure(
        ifc_file, f"Building with {storey_count} Storeys"
    )

    for i in range(storey_count):
        storey_placement = ifc_file.createIfcLocalPlacement(
            PlacementRelTo=base["building"].ObjectPlacement,
            RelativePlacement=ifc_file.createIfcAxis2Placement3D(
                Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, i * 3.5))
            ),
        )
        storey = ifc_file.createIfcBuildingStorey(
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=base["owner_history"],
            Name=f"Floor {i+1}",
            ObjectPlacement=storey_placement,
            Elevation=i * 3.5,
        )

        ifc_file.createIfcRelAggregates(
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=base["owner_history"],
            RelatingObject=base["building"],
            RelatedObjects=[storey],
        )

    ifc_file.write(str(file_path))
    logger.debug(f"Created multi-storey IFC file: %s", file_path)
    return file_path


def _create_ifc_with_materials(file_path: Path) -> Path:
    """Create IFC file with material definitions."""
    ifc_file = ifcopenshell.file(schema="IFC4")
    base = _create_ifc_base_structure(ifc_file, "Materials Test Project")

    storey_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=base["building"].ObjectPlacement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    storey = ifc_file.createIfcBuildingStorey(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Ground Floor",
        ObjectPlacement=storey_placement,
        Elevation=0.0,
    )

    ifc_file.createIfcRelAggregates(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingObject=base["building"],
        RelatedObjects=[storey],
    )

    # Create wall
    wall_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=storey_placement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    wall = ifc_file.createIfcWall(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Wall with Material",
        ObjectPlacement=wall_placement,
    )

    # Create material
    material = ifc_file.createIfcMaterial(Name="Concrete")

    # Associate material with wall
    ifc_file.createIfcRelAssociatesMaterial(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatedObjects=[wall],
        RelatingMaterial=material,
    )

    ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingStructure=storey,
        RelatedElements=[wall],
    )

    ifc_file.write(str(file_path))
    logger.debug(f"Created IFC file with materials: %s", file_path)
    return file_path


def _create_ifc_with_spaces(file_path: Path) -> Path:
    """Create IFC file with space elements."""
    ifc_file = ifcopenshell.file(schema="IFC4")
    base = _create_ifc_base_structure(ifc_file, "Spaces Test Project")

    storey_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=base["building"].ObjectPlacement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    storey = ifc_file.createIfcBuildingStorey(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Ground Floor",
        ObjectPlacement=storey_placement,
        Elevation=0.0,
    )

    ifc_file.createIfcRelAggregates(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingObject=base["building"],
        RelatedObjects=[storey],
    )

    # Create spaces
    space_names = ["Office 1", "Office 2", "Conference Room", "Corridor"]
    spaces = []

    for i, space_name in enumerate(space_names):
        space_placement = ifc_file.createIfcLocalPlacement(
            PlacementRelTo=storey_placement,
            RelativePlacement=ifc_file.createIfcAxis2Placement3D(
                Location=ifc_file.createIfcCartesianPoint((i * 5.0, 0.0, 0.0))
            ),
        )
        space = ifc_file.createIfcSpace(
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=base["owner_history"],
            Name=space_name,
            ObjectPlacement=space_placement,
        )
        spaces.append(space)

    ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingStructure=storey,
        RelatedElements=spaces,
    )

    ifc_file.write(str(file_path))
    logger.debug(f"Created IFC file with spaces: %s", file_path)
    return file_path


def _create_mixed_elements_building(file_path: Path, seed: int = 0) -> Path:
    """Create IFC file with mixed building elements."""
    ifc_file = ifcopenshell.file(schema="IFC4")
    base = _create_ifc_base_structure(ifc_file, f"Mixed Elements Building {seed+1}")

    storey_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=base["building"].ObjectPlacement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    storey = ifc_file.createIfcBuildingStorey(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Ground Floor",
        ObjectPlacement=storey_placement,
        Elevation=0.0,
    )

    ifc_file.createIfcRelAggregates(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingObject=base["building"],
        RelatedObjects=[storey],
    )

    elements = []
    element_types = [
        ("IfcWall", "Wall"),
        ("IfcDoor", "Door"),
        ("IfcWindow", "Window"),
        ("IfcColumn", "Column"),
        ("IfcBeam", "Beam"),
    ]

    for i, (ifc_class, elem_name) in enumerate(element_types):
        elem_placement = ifc_file.createIfcLocalPlacement(
            PlacementRelTo=storey_placement,
            RelativePlacement=ifc_file.createIfcAxis2Placement3D(
                Location=ifc_file.createIfcCartesianPoint(
                    ((i + seed) * 2.0, seed * 1.0, 0.0)
                )
            ),
        )

        elem = ifc_file.create_entity(
            ifc_class,
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=base["owner_history"],
            Name=f"{elem_name}-{i+1:03d}",
            ObjectPlacement=elem_placement,
        )
        elements.append(elem)

    ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingStructure=storey,
        RelatedElements=elements,
    )

    ifc_file.write(str(file_path))
    logger.debug(f"Created mixed elements IFC file: %s", file_path)
    return file_path


def _create_ifc_schema_variant(file_path: Path, schema: str) -> Path:
    """Create IFC file with specific schema version."""
    ifc_file = ifcopenshell.file(schema=schema)
    base = _create_ifc_base_structure(ifc_file, f"Schema {schema} Test")

    storey_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=base["building"].ObjectPlacement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    storey = ifc_file.createIfcBuildingStorey(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Ground Floor",
        ObjectPlacement=storey_placement,
        Elevation=0.0,
    )

    ifc_file.createIfcRelAggregates(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingObject=base["building"],
        RelatedObjects=[storey],
    )

    wall_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=storey_placement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    wall = ifc_file.createIfcWall(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Sample Wall",
        ObjectPlacement=wall_placement,
    )

    ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingStructure=storey,
        RelatedElements=[wall],
    )

    ifc_file.write(str(file_path))
    logger.debug(f"Created IFC file with schema {schema}: %s", file_path)
    return file_path


def _create_ifc_with_openings(file_path: Path) -> Path:
    """Create IFC file with opening elements."""
    ifc_file = ifcopenshell.file(schema="IFC4")
    base = _create_ifc_base_structure(ifc_file, "Openings Test Project")

    storey_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=base["building"].ObjectPlacement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    storey = ifc_file.createIfcBuildingStorey(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Ground Floor",
        ObjectPlacement=storey_placement,
        Elevation=0.0,
    )

    ifc_file.createIfcRelAggregates(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingObject=base["building"],
        RelatedObjects=[storey],
    )

    wall_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=storey_placement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    wall = ifc_file.createIfcWall(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Wall with Opening",
        ObjectPlacement=wall_placement,
    )

    opening_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=wall_placement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((1.0, 0.0, 1.0))
        ),
    )
    opening = ifc_file.createIfcOpeningElement(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Door Opening",
        ObjectPlacement=opening_placement,
    )

    ifc_file.createIfcRelVoidsElement(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingBuildingElement=wall,
        RelatedOpeningElement=opening,
    )

    ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingStructure=storey,
        RelatedElements=[wall],
    )

    ifc_file.write(str(file_path))
    logger.debug(f"Created IFC file with openings: %s", file_path)
    return file_path


def _create_ifc_with_type_objects(file_path: Path) -> Path:
    """Create IFC file with type objects."""
    ifc_file = ifcopenshell.file(schema="IFC4")
    base = _create_ifc_base_structure(ifc_file, "Type Objects Test Project")

    storey_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=base["building"].ObjectPlacement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    storey = ifc_file.createIfcBuildingStorey(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Ground Floor",
        ObjectPlacement=storey_placement,
        Elevation=0.0,
    )

    ifc_file.createIfcRelAggregates(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingObject=base["building"],
        RelatedObjects=[storey],
    )

    # Create door type
    door_type = ifc_file.createIfcDoorType(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Standard Door 900x2100",
    )

    # Create door instances
    doors = []
    for i in range(3):
        door_placement = ifc_file.createIfcLocalPlacement(
            PlacementRelTo=storey_placement,
            RelativePlacement=ifc_file.createIfcAxis2Placement3D(
                Location=ifc_file.createIfcCartesianPoint((i * 5.0, 0.0, 0.0))
            ),
        )
        door = ifc_file.createIfcDoor(
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=base["owner_history"],
            Name=f"Door-{i+1:03d}",
            ObjectPlacement=door_placement,
        )
        doors.append(door)

    # Relate doors to type
    ifc_file.createIfcRelDefinesByType(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatedObjects=doors,
        RelatingType=door_type,
    )

    ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingStructure=storey,
        RelatedElements=doors,
    )

    ifc_file.write(str(file_path))
    logger.debug(f"Created IFC file with type objects: %s", file_path)
    return file_path


def _create_residential_building(file_path: Path) -> Path:
    """Create residential building IFC file."""
    ifc_file = ifcopenshell.file(schema="IFC4")
    base = _create_ifc_base_structure(ifc_file, "Residential Building")

    storey_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=base["building"].ObjectPlacement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    storey = ifc_file.createIfcBuildingStorey(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Apartment Floor",
        ObjectPlacement=storey_placement,
        Elevation=0.0,
    )

    ifc_file.createIfcRelAggregates(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingObject=base["building"],
        RelatedObjects=[storey],
    )

    elements = []

    # Add residential-specific elements
    residential_elements = [
        ("IfcWall", "Exterior Wall", 4),
        ("IfcDoor", "Entry Door", 2),
        ("IfcWindow", "Window", 6),
        ("IfcSlab", "Floor Slab", 1),
        ("IfcStair", "Staircase", 1),
    ]

    offset_x = 0.0
    for ifc_class, elem_name, count in residential_elements:
        for i in range(count):
            elem_placement = ifc_file.createIfcLocalPlacement(
                PlacementRelTo=storey_placement,
                RelativePlacement=ifc_file.createIfcAxis2Placement3D(
                    Location=ifc_file.createIfcCartesianPoint((offset_x, 0.0, 0.0))
                ),
            )

            elem = ifc_file.create_entity(
                ifc_class,
                GlobalId=ifcopenshell.guid.new(),
                OwnerHistory=base["owner_history"],
                Name=f"{elem_name}-{i+1}",
                ObjectPlacement=elem_placement,
            )
            elements.append(elem)
            offset_x += 2.0

    ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingStructure=storey,
        RelatedElements=elements,
    )

    ifc_file.write(str(file_path))
    logger.debug(f"Created residential building IFC file: %s", file_path)
    return file_path


def _create_office_building(file_path: Path) -> Path:
    """Create office building IFC file."""
    ifc_file = ifcopenshell.file(schema="IFC4")
    base = _create_ifc_base_structure(ifc_file, "Office Building")

    storey_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=base["building"].ObjectPlacement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    storey = ifc_file.createIfcBuildingStorey(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Office Floor",
        ObjectPlacement=storey_placement,
        Elevation=0.0,
    )

    ifc_file.createIfcRelAggregates(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingObject=base["building"],
        RelatedObjects=[storey],
    )

    elements = []

    # Add office-specific elements
    office_elements = [
        ("IfcCurtainWall", "Glass Facade", 2),
        ("IfcColumn", "Structural Column", 8),
        ("IfcBeam", "Structural Beam", 6),
        ("IfcSlab", "Raised Floor", 1),
        ("IfcCovering", "Ceiling", 1),
    ]

    offset_x = 0.0
    for ifc_class, elem_name, count in office_elements:
        for i in range(count):
            elem_placement = ifc_file.createIfcLocalPlacement(
                PlacementRelTo=storey_placement,
                RelativePlacement=ifc_file.createIfcAxis2Placement3D(
                    Location=ifc_file.createIfcCartesianPoint((offset_x, 0.0, 0.0))
                ),
            )

            elem = ifc_file.create_entity(
                ifc_class,
                GlobalId=ifcopenshell.guid.new(),
                OwnerHistory=base["owner_history"],
                Name=f"{elem_name}-{i+1}",
                ObjectPlacement=elem_placement,
            )
            elements.append(elem)
            offset_x += 3.0

    ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingStructure=storey,
        RelatedElements=elements,
    )

    ifc_file.write(str(file_path))
    logger.debug(f"Created office building IFC file: %s", file_path)
    return file_path


def _create_warehouse(file_path: Path) -> Path:
    """Create warehouse IFC file."""
    ifc_file = ifcopenshell.file(schema="IFC4")
    base = _create_ifc_base_structure(ifc_file, "Warehouse")

    storey_placement = ifc_file.createIfcLocalPlacement(
        PlacementRelTo=base["building"].ObjectPlacement,
        RelativePlacement=ifc_file.createIfcAxis2Placement3D(
            Location=ifc_file.createIfcCartesianPoint((0.0, 0.0, 0.0))
        ),
    )
    storey = ifc_file.createIfcBuildingStorey(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        Name="Main Floor",
        ObjectPlacement=storey_placement,
        Elevation=0.0,
    )

    ifc_file.createIfcRelAggregates(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingObject=base["building"],
        RelatedObjects=[storey],
    )

    elements = []

    # Add warehouse-specific elements
    warehouse_elements = [
        ("IfcColumn", "Steel Column", 12),
        ("IfcBeam", "Steel Beam", 10),
        ("IfcRoof", "Metal Roof", 1),
        ("IfcDoor", "Loading Door", 4),
        ("IfcRamp", "Loading Ramp", 2),
    ]

    offset_x = 0.0
    for ifc_class, elem_name, count in warehouse_elements:
        for i in range(count):
            elem_placement = ifc_file.createIfcLocalPlacement(
                PlacementRelTo=storey_placement,
                RelativePlacement=ifc_file.createIfcAxis2Placement3D(
                    Location=ifc_file.createIfcCartesianPoint((offset_x, 0.0, 0.0))
                ),
            )

            elem = ifc_file.create_entity(
                ifc_class,
                GlobalId=ifcopenshell.guid.new(),
                OwnerHistory=base["owner_history"],
                Name=f"{elem_name}-{i+1}",
                ObjectPlacement=elem_placement,
            )
            elements.append(elem)
            offset_x += 4.0

    ifc_file.createIfcRelContainedInSpatialStructure(
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=base["owner_history"],
        RelatingStructure=storey,
        RelatedElements=elements,
    )

    ifc_file.write(str(file_path))
    logger.debug(f"Created warehouse IFC file: %s", file_path)
    return file_path


def get_test_ifc_dir() -> Path:
    """Get the directory containing test IFC files.

    Returns:
        Path to the directory containing IFC test files.
    """
    return Path(__file__).parent / "ifc"


def list_test_ifc_files() -> list[Path]:
    """List all available test IFC files.

    Returns:
        List of paths to all IFC test files in the corpus.
    """
    ifc_dir = get_test_ifc_dir()
    if not ifc_dir.exists():
        return []
    return sorted(ifc_dir.glob("*.ifc"))


# ==============================================================================
# STEP File Generators
# ==============================================================================


def create_simple_step(file_path: str | Path) -> Path:
    """Create a simple STEP file with a box.

    Creates a STEP file containing:
    - Single box solid (10x10x10 mm)
    - Basic part structure

    Args:
        file_path: Path where the STEP file should be created.

    Returns:
        Path to the created STEP file.

    Raises:
        ImportError: If OCP is not available.
    """
    if not OCP_AVAILABLE:
        raise ImportError("OCP (OpenCascade) is required for STEP file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create a simple box
    box = BRepPrimAPI_MakeBox(10.0, 10.0, 10.0).Shape()

    # Write to STEP file
    writer = STEPControl_Writer()
    writer.Transfer(box, STEPControl_AsIs)
    status = writer.Write(str(file_path))

    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created simple STEP file: %s", file_path)
    return file_path


def create_cylinder_step(file_path: str | Path) -> Path:
    """Create a STEP file with a cylinder.

    Creates a STEP file containing:
    - Cylinder (radius 5mm, height 20mm)

    Args:
        file_path: Path where the STEP file should be created.

    Returns:
        Path to the created STEP file.

    Raises:
        ImportError: If OCP is not available.
    """
    if not OCP_AVAILABLE:
        raise ImportError("OCP (OpenCascade) is required for STEP file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create cylinder
    cylinder = BRepPrimAPI_MakeCylinder(5.0, 20.0).Shape()

    # Write to STEP file
    writer = STEPControl_Writer()
    writer.Transfer(cylinder, STEPControl_AsIs)
    status = writer.Write(str(file_path))

    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created cylinder STEP file: %s", file_path)
    return file_path


def create_sphere_step(file_path: str | Path) -> Path:
    """Create a STEP file with a sphere.

    Creates a STEP file containing:
    - Sphere (radius 8mm)

    Args:
        file_path: Path where the STEP file should be created.

    Returns:
        Path to the created STEP file.

    Raises:
        ImportError: If OCP is not available.
    """
    if not OCP_AVAILABLE:
        raise ImportError("OCP (OpenCascade) is required for STEP file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create sphere
    sphere = BRepPrimAPI_MakeSphere(8.0).Shape()

    # Write to STEP file
    writer = STEPControl_Writer()
    writer.Transfer(sphere, STEPControl_AsIs)
    status = writer.Write(str(file_path))

    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created sphere STEP file: %s", file_path)
    return file_path


def create_cone_step(file_path: str | Path) -> Path:
    """Create a STEP file with a cone.

    Creates a STEP file containing:
    - Cone (bottom radius 6mm, top radius 2mm, height 15mm)

    Args:
        file_path: Path where the STEP file should be created.

    Returns:
        Path to the created STEP file.

    Raises:
        ImportError: If OCP is not available.
    """
    if not OCP_AVAILABLE:
        raise ImportError("OCP (OpenCascade) is required for STEP file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create cone
    cone = BRepPrimAPI_MakeCone(6.0, 2.0, 15.0).Shape()

    # Write to STEP file
    writer = STEPControl_Writer()
    writer.Transfer(cone, STEPControl_AsIs)
    status = writer.Write(str(file_path))

    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created cone STEP file: %s", file_path)
    return file_path


def create_torus_step(file_path: str | Path) -> Path:
    """Create a STEP file with a torus.

    Creates a STEP file containing:
    - Torus (major radius 10mm, minor radius 3mm)

    Args:
        file_path: Path where the STEP file should be created.

    Returns:
        Path to the created STEP file.

    Raises:
        ImportError: If OCP is not available.
    """
    if not OCP_AVAILABLE:
        raise ImportError("OCP (OpenCascade) is required for STEP file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create torus
    torus = BRepPrimAPI_MakeTorus(10.0, 3.0).Shape()

    # Write to STEP file
    writer = STEPControl_Writer()
    writer.Transfer(torus, STEPControl_AsIs)
    status = writer.Write(str(file_path))

    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created torus STEP file: %s", file_path)
    return file_path


def create_multi_part_step(file_path: str | Path) -> Path:
    """Create a STEP file with multiple parts.

    Creates a STEP file containing:
    - Multiple separate solids (box, cylinder, sphere)
    - No assembly structure (separate parts)

    Args:
        file_path: Path where the STEP file should be created.

    Returns:
        Path to the created STEP file.

    Raises:
        ImportError: If OCP is not available.
    """
    if not OCP_AVAILABLE:
        raise ImportError("OCP (OpenCascade) is required for STEP file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create multiple parts
    box = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), 5.0, 5.0, 5.0).Shape()
    cylinder = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(15, 0, 0), gp_Dir(0, 0, 1)), 3.0, 10.0).Shape()
    sphere = BRepPrimAPI_MakeSphere(gp_Pnt(30, 0, 0), 4.0).Shape()

    # Write to STEP file
    writer = STEPControl_Writer()
    writer.Transfer(box, STEPControl_AsIs)
    writer.Transfer(cylinder, STEPControl_AsIs)
    writer.Transfer(sphere, STEPControl_AsIs)
    status = writer.Write(str(file_path))

    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created multi-part STEP file: %s", file_path)
    return file_path


def create_boolean_union_step(file_path: str | Path) -> Path:
    """Create a STEP file with boolean union.

    Creates a STEP file containing:
    - Two boxes fused together
    - Single resulting solid

    Args:
        file_path: Path where the STEP file should be created.

    Returns:
        Path to the created STEP file.

    Raises:
        ImportError: If OCP is not available.
    """
    if not OCP_AVAILABLE:
        raise ImportError("OCP (OpenCascade) is required for STEP file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create two overlapping boxes
    box1 = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), 10.0, 10.0, 10.0).Shape()
    box2 = BRepPrimAPI_MakeBox(gp_Pnt(5, 5, 5), 10.0, 10.0, 10.0).Shape()

    # Perform boolean union
    fused = BRepAlgoAPI_Fuse(box1, box2).Shape()

    # Write to STEP file
    writer = STEPControl_Writer()
    writer.Transfer(fused, STEPControl_AsIs)
    status = writer.Write(str(file_path))

    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created boolean union STEP file: %s", file_path)
    return file_path


def create_boolean_cut_step(file_path: str | Path) -> Path:
    """Create a STEP file with boolean cut (hole).

    Creates a STEP file containing:
    - Box with cylindrical hole cut through it
    - Single resulting solid with cavity

    Args:
        file_path: Path where the STEP file should be created.

    Returns:
        Path to the created STEP file.

    Raises:
        ImportError: If OCP is not available.
    """
    if not OCP_AVAILABLE:
        raise ImportError("OCP (OpenCascade) is required for STEP file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create box
    box = BRepPrimAPI_MakeBox(20.0, 20.0, 20.0).Shape()

    # Create cylinder to cut
    cylinder = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(10, 10, -1), gp_Dir(0, 0, 1)), 4.0, 22.0).Shape()

    # Perform boolean cut
    cut = BRepAlgoAPI_Cut(box, cylinder).Shape()

    # Write to STEP file
    writer = STEPControl_Writer()
    writer.Transfer(cut, STEPControl_AsIs)
    status = writer.Write(str(file_path))

    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created boolean cut STEP file: %s", file_path)
    return file_path


def create_assembly_step(file_path: str | Path, num_parts: int = 5) -> Path:
    """Create a STEP file with assembly structure.

    Creates a STEP file containing:
    - Multiple parts in assembly
    - Different primitive shapes
    - Spatial arrangement

    Args:
        file_path: Path where the STEP file should be created.
        num_parts: Number of parts in assembly.

    Returns:
        Path to the created STEP file.

    Raises:
        ImportError: If OCP is not available.
    """
    if not OCP_AVAILABLE:
        raise ImportError("OCP (OpenCascade) is required for STEP file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    writer = STEPControl_Writer()

    # Create various parts
    shapes = [
        BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), 10.0, 10.0, 2.0).Shape(),  # Base plate
        BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(2, 2, 2), gp_Dir(0, 0, 1)), 1.5, 8.0).Shape(),  # Post 1
        BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(8, 2, 2), gp_Dir(0, 0, 1)), 1.5, 8.0).Shape(),  # Post 2
        BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(2, 8, 2), gp_Dir(0, 0, 1)), 1.5, 8.0).Shape(),  # Post 3
        BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(8, 8, 2), gp_Dir(0, 0, 1)), 1.5, 8.0).Shape(),  # Post 4
    ]

    # Transfer all shapes
    for shape in shapes[:num_parts]:
        writer.Transfer(shape, STEPControl_AsIs)

    status = writer.Write(str(file_path))

    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created assembly STEP file with %d parts: %s", num_parts, file_path)
    return file_path


def create_complex_part_step(file_path: str | Path) -> Path:
    """Create a STEP file with complex geometry.

    Creates a STEP file containing:
    - Complex part with multiple features
    - Boolean operations
    - Various geometry types

    Args:
        file_path: Path where the STEP file should be created.

    Returns:
        Path to the created STEP file.

    Raises:
        ImportError: If OCP is not available.
    """
    if not OCP_AVAILABLE:
        raise ImportError("OCP (OpenCascade) is required for STEP file generation")

    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create base block
    base = BRepPrimAPI_MakeBox(30.0, 20.0, 10.0).Shape()

    # Add cylindrical boss
    boss = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(15, 10, 10), gp_Dir(0, 0, 1)), 6.0, 5.0).Shape()
    part = BRepAlgoAPI_Fuse(base, boss).Shape()

    # Cut holes
    hole1 = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(7, 10, -1), gp_Dir(0, 0, 1)), 2.0, 12.0).Shape()
    part = BRepAlgoAPI_Cut(part, hole1).Shape()

    hole2 = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(23, 10, -1), gp_Dir(0, 0, 1)), 2.0, 12.0).Shape()
    part = BRepAlgoAPI_Cut(part, hole2).Shape()

    # Write to STEP file
    writer = STEPControl_Writer()
    writer.Transfer(part, STEPControl_AsIs)
    status = writer.Write(str(file_path))

    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created complex part STEP file: %s", file_path)
    return file_path


def generate_step_test_corpus(output_dir: str | Path) -> list[Path]:
    """Generate comprehensive STEP test corpus with 30+ files.

    Creates diverse STEP test files covering:
    - Basic primitives (box, cylinder, sphere, cone, torus)
    - Multi-part assemblies
    - Boolean operations (union, cut)
    - Complex geometries
    - Various scales and sizes
    - Different part counts

    Args:
        output_dir: Directory where test files should be created.

    Returns:
        List of paths to all created test files.

    Raises:
        ImportError: If OCP is not available.
    """
    if not OCP_AVAILABLE:
        raise ImportError("OCP (OpenCascade) is required for STEP file generation")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    created_files = []

    # Basic primitives with variations
    primitives = [
        ("01_simple_box.step", lambda p: create_simple_step(p)),
        ("02_small_box.stp", lambda p: _create_box_step(p, 5, 5, 5)),
        ("03_large_box.step", lambda p: _create_box_step(p, 100, 100, 100)),
        ("04_rectangular_box.step", lambda p: _create_box_step(p, 50, 30, 10)),
        ("05_cylinder.step", lambda p: create_cylinder_step(p)),
        ("06_tall_cylinder.stp", lambda p: _create_cylinder_step(p, 3, 30)),
        ("07_wide_cylinder.step", lambda p: _create_cylinder_step(p, 15, 5)),
        ("08_sphere.step", lambda p: create_sphere_step(p)),
        ("09_small_sphere.stp", lambda p: _create_sphere_step(p, 3)),
        ("10_large_sphere.step", lambda p: _create_sphere_step(p, 25)),
        ("11_cone.step", lambda p: create_cone_step(p)),
        ("12_torus.step", lambda p: create_torus_step(p)),
        ("13_small_torus.stp", lambda p: _create_torus_step(p, 5, 1.5)),
    ]

    for filename, generator in primitives:
        file_path = output_dir / filename
        generator(file_path)
        created_files.append(file_path)

    # Multi-part files
    multi_part_files = [
        ("14_multi_part_3.step", lambda p: create_multi_part_step(p)),
        ("15_multi_part_varied.step", lambda p: _create_varied_parts_step(p)),
    ]

    for filename, generator in multi_part_files:
        file_path = output_dir / filename
        generator(file_path)
        created_files.append(file_path)

    # Boolean operations
    boolean_files = [
        ("16_boolean_union.step", lambda p: create_boolean_union_step(p)),
        ("17_boolean_cut.step", lambda p: create_boolean_cut_step(p)),
        ("18_box_with_hole.stp", lambda p: create_boolean_cut_step(p)),
        ("19_intersecting_cylinders.step", lambda p: _create_intersecting_cylinders_step(p)),
    ]

    for filename, generator in boolean_files:
        file_path = output_dir / filename
        generator(file_path)
        created_files.append(file_path)

    # Assemblies with different part counts
    assembly_files = [
        ("20_assembly_2_parts.step", lambda p: create_assembly_step(p, 2)),
        ("21_assembly_3_parts.stp", lambda p: create_assembly_step(p, 3)),
        ("22_assembly_5_parts.step", lambda p: create_assembly_step(p, 5)),
        ("23_assembly_large.step", lambda p: _create_large_assembly_step(p)),
    ]

    for filename, generator in assembly_files:
        file_path = output_dir / filename
        generator(file_path)
        created_files.append(file_path)

    # Complex parts
    complex_files = [
        ("24_complex_part.step", lambda p: create_complex_part_step(p)),
        ("25_bracket.step", lambda p: _create_bracket_step(p)),
        ("26_flange.stp", lambda p: _create_flange_step(p)),
        ("27_shaft.step", lambda p: _create_shaft_step(p)),
        ("28_plate_with_holes.step", lambda p: _create_plate_with_holes_step(p)),
    ]

    for filename, generator in complex_files:
        file_path = output_dir / filename
        generator(file_path)
        created_files.append(file_path)

    # Mechanical components
    mechanical_files = [
        ("29_bearing_housing.step", lambda p: _create_bearing_housing_step(p)),
        ("30_motor_mount.stp", lambda p: _create_motor_mount_step(p)),
        ("31_pipe_fitting.step", lambda p: _create_pipe_fitting_step(p)),
        ("32_gear_blank.step", lambda p: _create_gear_blank_step(p)),
        ("33_washer.step", lambda p: _create_washer_step(p)),
    ]

    for filename, generator in mechanical_files:
        file_path = output_dir / filename
        generator(file_path)
        created_files.append(file_path)

    logger.info(f"Generated {len(created_files)} STEP test files in {output_dir}")
    return created_files


# Helper functions for STEP file generation
def _create_box_step(file_path: Path, dx: float, dy: float, dz: float) -> Path:
    """Create STEP file with box of specific dimensions."""
    box = BRepPrimAPI_MakeBox(dx, dy, dz).Shape()
    writer = STEPControl_Writer()
    writer.Transfer(box, STEPControl_AsIs)
    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")
    logger.debug(f"Created box STEP file ({dx}x{dy}x{dz}): %s", file_path)
    return file_path


def _create_cylinder_step(file_path: Path, radius: float, height: float) -> Path:
    """Create STEP file with cylinder of specific dimensions."""
    cylinder = BRepPrimAPI_MakeCylinder(radius, height).Shape()
    writer = STEPControl_Writer()
    writer.Transfer(cylinder, STEPControl_AsIs)
    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")
    logger.debug(f"Created cylinder STEP file (r={radius}, h={height}): %s", file_path)
    return file_path


def _create_sphere_step(file_path: Path, radius: float) -> Path:
    """Create STEP file with sphere of specific radius."""
    sphere = BRepPrimAPI_MakeSphere(radius).Shape()
    writer = STEPControl_Writer()
    writer.Transfer(sphere, STEPControl_AsIs)
    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")
    logger.debug(f"Created sphere STEP file (r={radius}): %s", file_path)
    return file_path


def _create_torus_step(file_path: Path, major_radius: float, minor_radius: float) -> Path:
    """Create STEP file with torus of specific dimensions."""
    torus = BRepPrimAPI_MakeTorus(major_radius, minor_radius).Shape()
    writer = STEPControl_Writer()
    writer.Transfer(torus, STEPControl_AsIs)
    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")
    logger.debug(f"Created torus STEP file (R={major_radius}, r={minor_radius}): %s", file_path)
    return file_path


def _create_varied_parts_step(file_path: Path) -> Path:
    """Create STEP file with varied primitive shapes."""
    writer = STEPControl_Writer()

    shapes = [
        BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), 8.0, 8.0, 8.0).Shape(),
        BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(20, 0, 0), gp_Dir(0, 0, 1)), 4.0, 12.0).Shape(),
        BRepPrimAPI_MakeSphere(gp_Pnt(40, 0, 0), 5.0).Shape(),
        BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(60, 0, 0), gp_Dir(0, 0, 1)), 5.0, 2.0, 10.0).Shape(),
        BRepPrimAPI_MakeTorus(gp_Ax2(gp_Pnt(80, 0, 0), gp_Dir(0, 0, 1)), 6.0, 2.0).Shape(),
    ]

    for shape in shapes:
        writer.Transfer(shape, STEPControl_AsIs)

    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created varied parts STEP file: %s", file_path)
    return file_path


def _create_intersecting_cylinders_step(file_path: Path) -> Path:
    """Create STEP file with two intersecting cylinders."""
    cyl1 = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), 4.0, 20.0).Shape()
    cyl2 = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(10, 0, 0), gp_Dir(0, 1, 0)), 3.0, 20.0).Shape()

    fused = BRepAlgoAPI_Fuse(cyl1, cyl2).Shape()

    writer = STEPControl_Writer()
    writer.Transfer(fused, STEPControl_AsIs)
    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created intersecting cylinders STEP file: %s", file_path)
    return file_path


def _create_large_assembly_step(file_path: Path) -> Path:
    """Create STEP file with larger assembly (10 parts)."""
    writer = STEPControl_Writer()

    # Create grid of parts
    for i in range(3):
        for j in range(3):
            x = i * 15.0
            y = j * 15.0
            shape = BRepPrimAPI_MakeBox(gp_Pnt(x, y, 0), 10.0, 10.0, 5.0).Shape()
            writer.Transfer(shape, STEPControl_AsIs)

    # Add central cylinder
    cyl = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(15, 15, 5), gp_Dir(0, 0, 1)), 8.0, 10.0).Shape()
    writer.Transfer(cyl, STEPControl_AsIs)

    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created large assembly STEP file: %s", file_path)
    return file_path


def _create_bracket_step(file_path: Path) -> Path:
    """Create STEP file with L-bracket geometry."""
    # Vertical part
    vert = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), 5.0, 20.0, 30.0).Shape()

    # Horizontal part
    horiz = BRepPrimAPI_MakeBox(gp_Pnt(0, 0, 0), 20.0, 20.0, 5.0).Shape()

    # Fuse them
    bracket = BRepAlgoAPI_Fuse(vert, horiz).Shape()

    # Add mounting holes
    hole1 = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(10, 10, -1), gp_Dir(0, 0, 1)), 2.0, 7.0).Shape()
    bracket = BRepAlgoAPI_Cut(bracket, hole1).Shape()

    hole2 = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(2.5, 10, 15), gp_Dir(1, 0, 0)), 2.0, 7.0).Shape()
    bracket = BRepAlgoAPI_Cut(bracket, hole2).Shape()

    writer = STEPControl_Writer()
    writer.Transfer(bracket, STEPControl_AsIs)
    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created bracket STEP file: %s", file_path)
    return file_path


def _create_flange_step(file_path: Path) -> Path:
    """Create STEP file with flange geometry."""
    # Main disc
    disc = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 25.0, 5.0).Shape()

    # Central hole
    center_hole = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, -1), gp_Dir(0, 0, 1)), 8.0, 7.0).Shape()
    flange = BRepAlgoAPI_Cut(disc, center_hole).Shape()

    # Bolt holes (4 around circumference)
    import math
    for i in range(4):
        angle = i * math.pi / 2
        x = 18.0 * math.cos(angle)
        y = 18.0 * math.sin(angle)
        bolt_hole = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x, y, -1), gp_Dir(0, 0, 1)), 3.0, 7.0).Shape()
        flange = BRepAlgoAPI_Cut(flange, bolt_hole).Shape()

    writer = STEPControl_Writer()
    writer.Transfer(flange, STEPControl_AsIs)
    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created flange STEP file: %s", file_path)
    return file_path


def _create_shaft_step(file_path: Path) -> Path:
    """Create STEP file with stepped shaft geometry."""
    # Large diameter section
    section1 = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), 8.0, 20.0).Shape()

    # Medium diameter section
    section2 = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(20, 0, 0), gp_Dir(1, 0, 0)), 6.0, 30.0).Shape()

    # Small diameter section
    section3 = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(50, 0, 0), gp_Dir(1, 0, 0)), 4.0, 15.0).Shape()

    # Fuse sections
    shaft = BRepAlgoAPI_Fuse(section1, section2).Shape()
    shaft = BRepAlgoAPI_Fuse(shaft, section3).Shape()

    writer = STEPControl_Writer()
    writer.Transfer(shaft, STEPControl_AsIs)
    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created shaft STEP file: %s", file_path)
    return file_path


def _create_plate_with_holes_step(file_path: Path) -> Path:
    """Create STEP file with plate containing multiple holes."""
    # Base plate
    plate = BRepPrimAPI_MakeBox(40.0, 30.0, 5.0).Shape()

    # Create grid of holes
    for i in range(3):
        for j in range(2):
            x = 10.0 + i * 10.0
            y = 10.0 + j * 10.0
            hole = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x, y, -1), gp_Dir(0, 0, 1)), 2.0, 7.0).Shape()
            plate = BRepAlgoAPI_Cut(plate, hole).Shape()

    writer = STEPControl_Writer()
    writer.Transfer(plate, STEPControl_AsIs)
    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created plate with holes STEP file: %s", file_path)
    return file_path


def _create_bearing_housing_step(file_path: Path) -> Path:
    """Create STEP file with bearing housing geometry."""
    # Outer block
    housing = BRepPrimAPI_MakeBox(30.0, 30.0, 20.0).Shape()

    # Bearing bore
    bore = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(15, 15, -1), gp_Dir(0, 0, 1)), 10.0, 22.0).Shape()
    housing = BRepAlgoAPI_Cut(housing, bore).Shape()

    # Mounting holes
    hole1 = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(5, 5, -1), gp_Dir(0, 0, 1)), 2.5, 22.0).Shape()
    housing = BRepAlgoAPI_Cut(housing, hole1).Shape()

    hole2 = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(25, 5, -1), gp_Dir(0, 0, 1)), 2.5, 22.0).Shape()
    housing = BRepAlgoAPI_Cut(housing, hole2).Shape()

    hole3 = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(5, 25, -1), gp_Dir(0, 0, 1)), 2.5, 22.0).Shape()
    housing = BRepAlgoAPI_Cut(housing, hole3).Shape()

    hole4 = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(25, 25, -1), gp_Dir(0, 0, 1)), 2.5, 22.0).Shape()
    housing = BRepAlgoAPI_Cut(housing, hole4).Shape()

    writer = STEPControl_Writer()
    writer.Transfer(housing, STEPControl_AsIs)
    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created bearing housing STEP file: %s", file_path)
    return file_path


def _create_motor_mount_step(file_path: Path) -> Path:
    """Create STEP file with motor mount geometry."""
    # Base plate
    base = BRepPrimAPI_MakeBox(50.0, 40.0, 8.0).Shape()

    # Central motor bore
    motor_bore = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(25, 20, -1), gp_Dir(0, 0, 1)), 15.0, 10.0).Shape()
    mount = BRepAlgoAPI_Cut(base, motor_bore).Shape()

    # Motor mounting holes (4 corners around bore)
    import math
    for i in range(4):
        angle = i * math.pi / 2 + math.pi / 4
        x = 25.0 + 20.0 * math.cos(angle)
        y = 20.0 + 20.0 * math.sin(angle)
        hole = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x, y, -1), gp_Dir(0, 0, 1)), 2.5, 10.0).Shape()
        mount = BRepAlgoAPI_Cut(mount, hole).Shape()

    writer = STEPControl_Writer()
    writer.Transfer(mount, STEPControl_AsIs)
    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created motor mount STEP file: %s", file_path)
    return file_path


def _create_pipe_fitting_step(file_path: Path) -> Path:
    """Create STEP file with T-pipe fitting geometry."""
    # Main pipe (horizontal)
    main_pipe = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), 5.0, 40.0).Shape()

    # Branch pipe (vertical)
    branch_pipe = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(20, 0, 0), gp_Dir(0, 0, 1)), 4.0, 20.0).Shape()

    # Fuse pipes
    fitting = BRepAlgoAPI_Fuse(main_pipe, branch_pipe).Shape()

    # Hollow out (cut inner diameter)
    main_inner = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(-1, 0, 0), gp_Dir(1, 0, 0)), 3.5, 42.0).Shape()
    fitting = BRepAlgoAPI_Cut(fitting, main_inner).Shape()

    branch_inner = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(20, 0, -1), gp_Dir(0, 0, 1)), 2.5, 22.0).Shape()
    fitting = BRepAlgoAPI_Cut(fitting, branch_inner).Shape()

    writer = STEPControl_Writer()
    writer.Transfer(fitting, STEPControl_AsIs)
    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created pipe fitting STEP file: %s", file_path)
    return file_path


def _create_gear_blank_step(file_path: Path) -> Path:
    """Create STEP file with gear blank (disc with central bore)."""
    # Main disc
    disc = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 20.0, 10.0).Shape()

    # Central bore for shaft
    bore = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, -1), gp_Dir(0, 0, 1)), 6.0, 12.0).Shape()
    gear = BRepAlgoAPI_Cut(disc, bore).Shape()

    # Keyway (rectangular cut)
    keyway = BRepPrimAPI_MakeBox(gp_Pnt(-2, 6, -1), 4.0, 15.0, 5.0).Shape()
    gear = BRepAlgoAPI_Cut(gear, keyway).Shape()

    writer = STEPControl_Writer()
    writer.Transfer(gear, STEPControl_AsIs)
    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created gear blank STEP file: %s", file_path)
    return file_path


def _create_washer_step(file_path: Path) -> Path:
    """Create STEP file with washer geometry."""
    # Outer disc
    outer = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), 12.0, 2.0).Shape()

    # Inner hole
    inner = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, -1), gp_Dir(0, 0, 1)), 5.0, 4.0).Shape()

    # Cut to create washer
    washer = BRepAlgoAPI_Cut(outer, inner).Shape()

    writer = STEPControl_Writer()
    writer.Transfer(washer, STEPControl_AsIs)
    status = writer.Write(str(file_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to write STEP file: {file_path}")

    logger.debug("Created washer STEP file: %s", file_path)
    return file_path


def get_test_step_dir() -> Path:
    """Get the directory containing test STEP files.

    Returns:
        Path to the directory containing STEP test files.
    """
    return Path(__file__).parent / "step"


def list_test_step_files() -> list[Path]:
    """List all available test STEP files.

    Returns:
        List of paths to all STEP test files in the corpus.
    """
    step_dir = get_test_step_dir()
    if not step_dir.exists():
        return []
    return sorted(step_dir.glob("*.step")) + sorted(step_dir.glob("*.stp"))
