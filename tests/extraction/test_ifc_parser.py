"""
Tests for IFC parser functionality.

Tests building element extraction, spatial structure parsing, property extraction,
and material information from IFC (BIM) files.
"""

from pathlib import Path

import pytest

from pybase.extraction.base import CADExtractionResult
from pybase.extraction.cad.ifc import (
    IFCOPENSHELL_AVAILABLE,
    IFCElement,
    IFCExtractionResult,
    IFCParser,
    IFCSpatialStructure,
)


@pytest.mark.skipif(not IFCOPENSHELL_AVAILABLE, reason="ifcopenshell not available")
class TestIFCParser:
    """Test suite for IFC parser."""

    def test_parser_initialization(self, ifc_parser: IFCParser) -> None:
        """Test IFC parser initialization."""
        assert ifc_parser is not None
        assert isinstance(ifc_parser, IFCParser)
        assert ifc_parser.extract_properties is True
        assert ifc_parser.extract_quantities is True
        assert ifc_parser.extract_materials is True
        assert ifc_parser.max_elements == 50000

    def test_parser_initialization_custom_options(self) -> None:
        """Test IFC parser initialization with custom options."""
        parser = IFCParser(
            extract_properties=False,
            extract_quantities=False,
            extract_materials=False,
            max_elements=1000,
        )
        assert parser.extract_properties is False
        assert parser.extract_quantities is False
        assert parser.extract_materials is False
        assert parser.max_elements == 1000

    def test_element_extraction(
        self, ifc_parser: IFCParser, temp_cad_dir: Path
    ) -> None:
        """Test extraction of various building elements from IFC file."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create a simple IFC file with building elements
        ifc_file = ifcopenshell.file()

        # Create project structure
        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="Test Project",
        )

        # Create spatial structure
        site = ifc_file.createIfcSite(
            ifcopenshell.guid.new(),
            Name="Test Site",
        )

        building = ifc_file.createIfcBuilding(
            ifcopenshell.guid.new(),
            Name="Test Building",
        )

        storey = ifc_file.createIfcBuildingStorey(
            ifcopenshell.guid.new(),
            Name="Ground Floor",
        )

        # Create building elements
        wall = ifc_file.createIfcWall(
            ifcopenshell.guid.new(),
            Name="Wall-001",
            Description="Exterior Wall",
            ObjectType="LoadBearing",
        )

        door = ifc_file.createIfcDoor(
            ifcopenshell.guid.new(),
            Name="Door-001",
            Description="Entry Door",
            ObjectType="Single",
        )

        window = ifc_file.createIfcWindow(
            ifcopenshell.guid.new(),
            Name="Window-001",
            Description="Standard Window",
            ObjectType="Fixed",
        )

        slab = ifc_file.createIfcSlab(
            ifcopenshell.guid.new(),
            Name="Slab-001",
            Description="Ground Slab",
            ObjectType="Floor",
        )

        # Save test file
        test_file_path = temp_cad_dir / "test_elements.ifc"
        ifc_file.write(str(test_file_path))

        # Parse the file
        result = ifc_parser.parse(test_file_path)

        # Verify basic extraction
        assert isinstance(result, IFCExtractionResult)
        assert result.success
        assert result.source_type == "ifc"
        assert len(result.errors) == 0

        # Verify elements were extracted
        assert len(result.elements) > 0

        # Check for specific element types
        element_classes = {elem.ifc_class for elem in result.elements}

        # Should have the elements we created
        assert "IfcWall" in element_classes
        assert "IfcDoor" in element_classes
        assert "IfcWindow" in element_classes
        assert "IfcSlab" in element_classes

        # Verify element properties
        wall_elements = [e for e in result.elements if e.ifc_class == "IfcWall"]
        assert len(wall_elements) > 0

        wall = wall_elements[0]
        assert isinstance(wall, IFCElement)
        assert wall.global_id is not None
        assert wall.name == "Wall-001"
        assert wall.description == "Exterior Wall"
        assert wall.object_type == "LoadBearing"

        # Verify door element
        door_elements = [e for e in result.elements if e.ifc_class == "IfcDoor"]
        assert len(door_elements) > 0

        door_elem = door_elements[0]
        assert door_elem.name == "Door-001"
        assert door_elem.description == "Entry Door"
        assert door_elem.object_type == "Single"

        # Verify element counts
        assert result.element_counts is not None
        assert isinstance(result.element_counts, dict)
        assert "IfcWall" in result.element_counts
        assert result.element_counts["IfcWall"] >= 1

    def test_parse_simple_ifc(
        self, ifc_parser: IFCParser, temp_cad_dir: Path
    ) -> None:
        """Test parsing a simple IFC file."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create minimal IFC file
        ifc_file = ifcopenshell.file()
        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="Simple Project",
        )

        test_file_path = temp_cad_dir / "simple.ifc"
        ifc_file.write(str(test_file_path))

        # Parse
        result = ifc_parser.parse(test_file_path)

        assert result.success
        assert result.source_type == "ifc"
        # Note: A file with only a project has no building elements, so has_content may be False

    def test_spatial_structure_extraction(
        self, ifc_parser: IFCParser, temp_cad_dir: Path
    ) -> None:
        """Test extraction of spatial hierarchy."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create IFC with spatial structure
        ifc_file = ifcopenshell.file()

        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="Spatial Test Project",
        )

        site = ifc_file.createIfcSite(
            ifcopenshell.guid.new(),
            Name="Site Alpha",
        )

        building = ifc_file.createIfcBuilding(
            ifcopenshell.guid.new(),
            Name="Building A",
        )

        storey1 = ifc_file.createIfcBuildingStorey(
            ifcopenshell.guid.new(),
            Name="Level 1",
        )

        storey2 = ifc_file.createIfcBuildingStorey(
            ifcopenshell.guid.new(),
            Name="Level 2",
        )

        test_file_path = temp_cad_dir / "spatial_structure.ifc"
        ifc_file.write(str(test_file_path))

        # Parse
        result = ifc_parser.parse(test_file_path)

        assert result.success
        assert result.spatial_structure is not None
        assert isinstance(result.spatial_structure, IFCSpatialStructure)

        # Verify project name
        assert result.spatial_structure.project == "Spatial Test Project"

        # Verify sites
        assert len(result.spatial_structure.sites) > 0
        site_names = [s["name"] for s in result.spatial_structure.sites]
        assert "Site Alpha" in site_names

        # Verify buildings
        assert len(result.spatial_structure.buildings) > 0
        building_names = [b["name"] for b in result.spatial_structure.buildings]
        assert "Building A" in building_names

        # Verify storeys
        assert len(result.spatial_structure.storeys) > 0
        storey_names = [s["name"] for s in result.spatial_structure.storeys]
        assert "Level 1" in storey_names
        assert "Level 2" in storey_names

    def test_element_counts(
        self, ifc_parser: IFCParser, temp_cad_dir: Path
    ) -> None:
        """Test that element counts are correctly calculated."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create IFC with multiple elements
        ifc_file = ifcopenshell.file()

        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="Count Test",
        )

        # Create multiple walls
        for i in range(5):
            ifc_file.createIfcWall(
                ifcopenshell.guid.new(),
                Name=f"Wall-{i:03d}",
            )

        # Create multiple doors
        for i in range(3):
            ifc_file.createIfcDoor(
                ifcopenshell.guid.new(),
                Name=f"Door-{i:03d}",
            )

        test_file_path = temp_cad_dir / "element_counts.ifc"
        ifc_file.write(str(test_file_path))

        # Parse
        result = ifc_parser.parse(test_file_path)

        assert result.success
        assert result.element_counts is not None

        # Verify counts
        assert "IfcWall" in result.element_counts
        assert result.element_counts["IfcWall"] == 5

        assert "IfcDoor" in result.element_counts
        assert result.element_counts["IfcDoor"] == 3

        # Verify total elements
        total_elements = sum(result.element_counts.values())
        assert total_elements >= 8

    def test_parse_nonexistent_file(self, ifc_parser: IFCParser) -> None:
        """Test parsing a nonexistent file."""
        result = ifc_parser.parse("nonexistent_file.ifc")
        assert not result.success
        assert len(result.errors) > 0

    def test_to_dict_conversion(
        self, ifc_parser: IFCParser, temp_cad_dir: Path
    ) -> None:
        """Test conversion of extraction result to dictionary."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create simple IFC
        ifc_file = ifcopenshell.file()
        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="Dict Test",
        )

        wall = ifc_file.createIfcWall(
            ifcopenshell.guid.new(),
            Name="Test Wall",
        )

        test_file_path = temp_cad_dir / "to_dict.ifc"
        ifc_file.write(str(test_file_path))

        # Parse
        result = ifc_parser.parse(test_file_path)
        assert result.success

        # Convert to dict
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "source_file" in result_dict
        assert "source_type" in result_dict
        assert "elements" in result_dict
        assert "spatial_structure" in result_dict
        assert "element_counts" in result_dict
        assert "property_sets" in result_dict
        assert "type_objects" in result_dict
        assert "success" in result_dict
        assert result_dict["success"] is True

        # Verify elements in dict
        assert isinstance(result_dict["elements"], list)
        assert len(result_dict["elements"]) > 0

        # Verify element structure
        element = result_dict["elements"][0]
        assert "global_id" in element
        assert "ifc_class" in element
        assert "name" in element

    def test_selective_extraction(self, temp_cad_dir: Path) -> None:
        """Test parser with selective extraction options."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create IFC file
        ifc_file = ifcopenshell.file()
        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="Selective Test",
        )

        wall = ifc_file.createIfcWall(
            ifcopenshell.guid.new(),
            Name="Test Wall",
        )

        test_file_path = temp_cad_dir / "selective.ifc"
        ifc_file.write(str(test_file_path))

        # Parse with properties disabled
        parser = IFCParser(
            extract_properties=False,
            extract_quantities=False,
            extract_materials=False,
        )
        result = parser.parse(test_file_path)

        assert result.success
        # Elements should still be extracted
        assert len(result.elements) > 0

    def test_empty_ifc(self, ifc_parser: IFCParser, temp_cad_dir: Path) -> None:
        """Test parsing an empty IFC file."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create empty IFC (just project)
        ifc_file = ifcopenshell.file()
        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="Empty Project",
        )

        test_file_path = temp_cad_dir / "empty.ifc"
        ifc_file.write(str(test_file_path))

        # Parse
        result = ifc_parser.parse(test_file_path)

        assert result.success
        # Should have minimal or no elements
        assert isinstance(result.elements, list)

    def test_multiple_element_types(
        self, ifc_parser: IFCParser, temp_cad_dir: Path
    ) -> None:
        """Test extraction of multiple element types."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create IFC with various element types
        ifc_file = ifcopenshell.file()

        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="Multi-Element Test",
        )

        # Create various elements
        ifc_file.createIfcWall(ifcopenshell.guid.new(), Name="Wall")
        ifc_file.createIfcDoor(ifcopenshell.guid.new(), Name="Door")
        ifc_file.createIfcWindow(ifcopenshell.guid.new(), Name="Window")
        ifc_file.createIfcSlab(ifcopenshell.guid.new(), Name="Slab")
        ifc_file.createIfcBeam(ifcopenshell.guid.new(), Name="Beam")
        ifc_file.createIfcColumn(ifcopenshell.guid.new(), Name="Column")
        ifc_file.createIfcStair(ifcopenshell.guid.new(), Name="Stair")
        ifc_file.createIfcRoof(ifcopenshell.guid.new(), Name="Roof")

        test_file_path = temp_cad_dir / "multi_elements.ifc"
        ifc_file.write(str(test_file_path))

        # Parse
        result = ifc_parser.parse(test_file_path)

        assert result.success
        assert len(result.elements) >= 8

        # Verify all element types are present
        element_classes = {elem.ifc_class for elem in result.elements}

        assert "IfcWall" in element_classes
        assert "IfcDoor" in element_classes
        assert "IfcWindow" in element_classes
        assert "IfcSlab" in element_classes
        assert "IfcBeam" in element_classes
        assert "IfcColumn" in element_classes
        assert "IfcStair" in element_classes
        assert "IfcRoof" in element_classes

    def test_element_data_structure(
        self, ifc_parser: IFCParser, temp_cad_dir: Path
    ) -> None:
        """Test IFCElement data structure."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create IFC
        ifc_file = ifcopenshell.file()
        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="Element Structure Test",
        )

        wall = ifc_file.createIfcWall(
            ifcopenshell.guid.new(),
            Name="Test Wall",
            Description="Test Description",
            ObjectType="Exterior",
        )

        test_file_path = temp_cad_dir / "element_structure.ifc"
        ifc_file.write(str(test_file_path))

        # Parse
        result = ifc_parser.parse(test_file_path)
        assert result.success

        # Get wall element
        wall_elements = [e for e in result.elements if e.ifc_class == "IfcWall"]
        assert len(wall_elements) > 0

        wall_elem = wall_elements[0]

        # Verify IFCElement structure
        assert isinstance(wall_elem, IFCElement)
        assert wall_elem.global_id is not None
        assert isinstance(wall_elem.global_id, str)
        assert wall_elem.ifc_class == "IfcWall"
        assert wall_elem.name == "Test Wall"
        assert wall_elem.description == "Test Description"
        assert wall_elem.object_type == "Exterior"
        assert isinstance(wall_elem.properties, dict)
        assert isinstance(wall_elem.quantities, dict)
        assert isinstance(wall_elem.materials, list)

        # Test to_dict method
        elem_dict = wall_elem.to_dict()
        assert isinstance(elem_dict, dict)
        assert elem_dict["global_id"] == wall_elem.global_id
        assert elem_dict["ifc_class"] == "IfcWall"
        assert elem_dict["name"] == "Test Wall"

    def test_max_elements_limit(self, temp_cad_dir: Path) -> None:
        """Test that max_elements limit is respected."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create IFC with many elements
        ifc_file = ifcopenshell.file()
        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="Limit Test",
        )

        # Create 100 walls
        for i in range(100):
            ifc_file.createIfcWall(
                ifcopenshell.guid.new(),
                Name=f"Wall-{i:03d}",
            )

        test_file_path = temp_cad_dir / "many_elements.ifc"
        ifc_file.write(str(test_file_path))

        # Parse with low limit
        parser = IFCParser(max_elements=10)
        result = parser.parse(test_file_path)

        assert result.success
        # Should not exceed max_elements
        assert len(result.elements) <= 10

    def test_spatial_structure(
        self, ifc_parser: IFCParser, temp_cad_dir: Path
    ) -> None:
        """Test spatial structure extraction with comprehensive hierarchy."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create IFC with complete spatial hierarchy
        ifc_file = ifcopenshell.file()

        # Create project
        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="Comprehensive Spatial Test",
        )

        # Create site
        site = ifc_file.createIfcSite(
            ifcopenshell.guid.new(),
            Name="Main Site",
            Description="Project site",
        )

        # Create building
        building = ifc_file.createIfcBuilding(
            ifcopenshell.guid.new(),
            Name="Office Building",
            Description="Main office building",
        )

        # Create multiple storeys
        ground_floor = ifc_file.createIfcBuildingStorey(
            ifcopenshell.guid.new(),
            Name="Ground Floor",
            Description="First level",
        )

        first_floor = ifc_file.createIfcBuildingStorey(
            ifcopenshell.guid.new(),
            Name="First Floor",
            Description="Second level",
        )

        # Create spaces
        space1 = ifc_file.createIfcSpace(
            ifcopenshell.guid.new(),
            Name="Room 101",
            Description="Conference room",
        )

        space2 = ifc_file.createIfcSpace(
            ifcopenshell.guid.new(),
            Name="Room 102",
            Description="Office space",
        )

        test_file_path = temp_cad_dir / "spatial_test.ifc"
        ifc_file.write(str(test_file_path))

        # Parse
        result = ifc_parser.parse(test_file_path)

        # Verify success
        assert result.success
        assert result.spatial_structure is not None
        assert isinstance(result.spatial_structure, IFCSpatialStructure)

        # Verify project
        assert result.spatial_structure.project == "Comprehensive Spatial Test"

        # Verify sites
        assert len(result.spatial_structure.sites) == 1
        site_data = result.spatial_structure.sites[0]
        assert site_data["name"] == "Main Site"
        assert site_data["description"] == "Project site"
        assert "global_id" in site_data

        # Verify buildings
        assert len(result.spatial_structure.buildings) == 1
        building_data = result.spatial_structure.buildings[0]
        assert building_data["name"] == "Office Building"
        assert building_data["description"] == "Main office building"
        assert "global_id" in building_data

        # Verify storeys
        assert len(result.spatial_structure.storeys) == 2
        storey_names = [s["name"] for s in result.spatial_structure.storeys]
        assert "Ground Floor" in storey_names
        assert "First Floor" in storey_names

        # Verify spaces
        assert len(result.spatial_structure.spaces) == 2
        space_names = [s["name"] for s in result.spatial_structure.spaces]
        assert "Room 101" in space_names
        assert "Room 102" in space_names

        # Verify spatial structure to_dict method
        structure_dict = result.spatial_structure.to_dict()
        assert isinstance(structure_dict, dict)
        assert "project" in structure_dict
        assert "sites" in structure_dict
        assert "buildings" in structure_dict
        assert "storeys" in structure_dict
        assert "spaces" in structure_dict

    def test_property_extraction(
        self, ifc_parser: IFCParser, temp_cad_dir: Path
    ) -> None:
        """Test extraction of properties from IFC elements."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create IFC file with elements that have properties
        ifc_file = ifcopenshell.file()

        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="Property Test",
        )

        # Create a wall
        wall = ifc_file.createIfcWall(
            ifcopenshell.guid.new(),
            Name="Test Wall",
            Description="Wall with properties",
        )

        # Note: Creating actual property sets in ifcopenshell requires more complex setup
        # For now, test that the parser handles elements and attempts property extraction

        test_file_path = temp_cad_dir / "properties.ifc"
        ifc_file.write(str(test_file_path))

        # Parse with property extraction enabled (default)
        result = ifc_parser.parse(test_file_path)

        assert result.success
        assert len(result.elements) > 0

        # Verify that elements have properties dict (even if empty)
        wall_elem = [e for e in result.elements if e.ifc_class == "IfcWall"][0]
        assert isinstance(wall_elem.properties, dict)

    def test_property_extraction_disabled(
        self, temp_cad_dir: Path
    ) -> None:
        """Test that property extraction can be disabled."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create IFC file
        ifc_file = ifcopenshell.file()
        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="No Properties Test",
        )

        wall = ifc_file.createIfcWall(
            ifcopenshell.guid.new(),
            Name="Test Wall",
        )

        test_file_path = temp_cad_dir / "no_properties.ifc"
        ifc_file.write(str(test_file_path))

        # Parse with properties disabled
        parser = IFCParser(extract_properties=False)
        result = parser.parse(test_file_path)

        assert result.success
        assert len(result.elements) > 0

        # Properties dict should still exist but be empty
        wall_elem = [e for e in result.elements if e.ifc_class == "IfcWall"][0]
        assert isinstance(wall_elem.properties, dict)
        assert len(wall_elem.properties) == 0

    def test_property_set_definitions(
        self, ifc_parser: IFCParser, temp_cad_dir: Path
    ) -> None:
        """Test extraction of property set definitions."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create IFC file
        ifc_file = ifcopenshell.file()
        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="PropertySet Test",
        )

        # Create a simple wall
        wall = ifc_file.createIfcWall(
            ifcopenshell.guid.new(),
            Name="Test Wall",
        )

        test_file_path = temp_cad_dir / "pset_defs.ifc"
        ifc_file.write(str(test_file_path))

        # Parse
        result = ifc_parser.parse(test_file_path)

        assert result.success
        # property_sets should be a list (even if empty for this simple file)
        assert isinstance(result.property_sets, list)

    def test_quantity_extraction(
        self, ifc_parser: IFCParser, temp_cad_dir: Path
    ) -> None:
        """Test extraction of quantities from IFC elements."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create IFC file
        ifc_file = ifcopenshell.file()
        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="Quantity Test",
        )

        wall = ifc_file.createIfcWall(
            ifcopenshell.guid.new(),
            Name="Test Wall",
        )

        test_file_path = temp_cad_dir / "quantities.ifc"
        ifc_file.write(str(test_file_path))

        # Parse with quantity extraction enabled (default)
        result = ifc_parser.parse(test_file_path)

        assert result.success
        assert len(result.elements) > 0

        # Verify that elements have quantities dict
        wall_elem = [e for e in result.elements if e.ifc_class == "IfcWall"][0]
        assert isinstance(wall_elem.quantities, dict)

    def test_quantity_extraction_disabled(
        self, temp_cad_dir: Path
    ) -> None:
        """Test that quantity extraction can be disabled."""
        if not IFCOPENSHELL_AVAILABLE:
            pytest.skip("ifcopenshell not available")

        import ifcopenshell

        # Create IFC file
        ifc_file = ifcopenshell.file()
        project = ifc_file.createIfcProject(
            ifcopenshell.guid.new(),
            Name="No Quantities Test",
        )

        wall = ifc_file.createIfcWall(
            ifcopenshell.guid.new(),
            Name="Test Wall",
        )

        test_file_path = temp_cad_dir / "no_quantities.ifc"
        ifc_file.write(str(test_file_path))

        # Parse with quantities disabled
        parser = IFCParser(extract_quantities=False)
        result = parser.parse(test_file_path)

        assert result.success
        assert len(result.elements) > 0

        # Quantities dict should be empty
        wall_elem = [e for e in result.elements if e.ifc_class == "IfcWall"][0]
        assert isinstance(wall_elem.quantities, dict)
        assert len(wall_elem.quantities) == 0
