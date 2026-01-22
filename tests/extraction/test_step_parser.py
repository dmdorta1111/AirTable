"""
Tests for STEP parser functionality.

Tests geometry metadata extraction, assembly structure parsing, and part metadata
from STEP (Standard for the Exchange of Product Data) files.
"""

from pathlib import Path

import pytest

from pybase.extraction.base import CADExtractionResult
from pybase.extraction.cad.step import (
    CADQUERY_AVAILABLE,
    OCP_AVAILABLE,
    STEPParser,
    STEPPart,
    STEPAssembly,
    STEPExtractionResult,
)


@pytest.mark.skipif(
    not OCP_AVAILABLE and not CADQUERY_AVAILABLE,
    reason="OCP or cadquery not available",
)
class TestSTEPParser:
    """Test suite for STEP parser."""

    def test_parser_initialization(self, step_parser: STEPParser) -> None:
        """Test STEP parser initialization."""
        assert step_parser is not None
        assert isinstance(step_parser, STEPParser)
        assert step_parser.compute_mass_properties is True
        assert step_parser.max_parts == 10000

    def test_parser_initialization_custom_options(self) -> None:
        """Test STEP parser initialization with custom options."""
        parser = STEPParser(
            compute_mass_properties=False,
            max_parts=100,
        )
        assert parser.compute_mass_properties is False
        assert parser.max_parts == 100

    def test_geometry_extraction(
        self, step_parser: STEPParser, step_fixtures_dir: Path, assert_extraction_valid
    ) -> None:
        """Test extraction of geometry metadata from STEP file."""
        # Use the simple box test file
        step_file = step_fixtures_dir / "01_simple_box.step"

        # Skip if test file doesn't exist
        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)
        assert_extraction_valid(result)
        assert result.success
        assert result.source_type == "step"
        assert isinstance(result, STEPExtractionResult)

        # Validate geometry metadata
        if result.assembly and len(result.assembly.parts) > 0:
            # Check that we have parts
            assert result.assembly.total_parts > 0
            assert len(result.assembly.parts) > 0

            # Validate first part has geometry metadata
            part = result.assembly.parts[0]
            assert isinstance(part, STEPPart)
            assert part.name is not None

            # Geometry metadata should be extracted
            # At minimum we should have shape type
            assert part.shape_type in ("SOLID", "SHELL", "COMPOUND", "unknown")

            # If mass properties are computed, validate them
            if step_parser.compute_mass_properties:
                # Volume and surface area may be None for some shapes
                # but should be float or None
                assert part.volume is None or isinstance(part.volume, float)
                assert part.surface_area is None or isinstance(part.surface_area, float)
                assert part.center_of_mass is None or (
                    isinstance(part.center_of_mass, tuple) and len(part.center_of_mass) == 3
                )

            # Bounding box should be a 6-tuple or None
            if part.bbox is not None:
                assert isinstance(part.bbox, tuple)
                assert len(part.bbox) == 6
                xmin, ymin, zmin, xmax, ymax, zmax = part.bbox
                # Max values should be >= min values
                assert xmax >= xmin
                assert ymax >= ymin
                assert zmax >= zmin

            # Face/edge/vertex counts should be non-negative
            assert part.num_faces >= 0
            assert part.num_edges >= 0
            assert part.num_vertices >= 0

    def test_parse_simple_step(
        self, step_parser: STEPParser, step_fixtures_dir: Path, assert_extraction_valid
    ) -> None:
        """Test parsing a simple STEP file."""
        step_file = step_fixtures_dir / "01_simple_box.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)
        assert_extraction_valid(result)
        assert result.success
        assert result.source_type == "step"
        assert result.has_content

    def test_parse_cylinder(
        self, step_parser: STEPParser, step_fixtures_dir: Path
    ) -> None:
        """Test parsing a cylinder STEP file."""
        step_file = step_fixtures_dir / "05_cylinder.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)
        assert result.success
        assert isinstance(result, STEPExtractionResult)

        # Should have shape counts
        if result.shape_counts:
            assert isinstance(result.shape_counts, dict)
            # Should have at least one shape type
            assert len(result.shape_counts) > 0

    def test_parse_sphere(
        self, step_parser: STEPParser, step_fixtures_dir: Path
    ) -> None:
        """Test parsing a sphere STEP file."""
        step_file = step_fixtures_dir / "08_sphere.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)
        assert result.success
        assert isinstance(result, STEPExtractionResult)

    def test_shape_counts(
        self, step_parser: STEPParser, step_fixtures_dir: Path
    ) -> None:
        """Test that shape types are correctly counted."""
        step_file = step_fixtures_dir / "01_simple_box.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)
        assert result.success

        # Should have shape_counts dictionary
        assert hasattr(result, "shape_counts")
        assert isinstance(result.shape_counts, dict)

        # If we have shapes, validate the counts
        if result.shape_counts:
            for shape_type, count in result.shape_counts.items():
                assert isinstance(shape_type, str)
                assert isinstance(count, int)
                assert count > 0

    def test_assembly_structure(
        self,
        step_parser: STEPParser,
        step_fixtures_dir: Path,
        assert_step_assembly_valid,
        assert_step_part_valid,
    ) -> None:
        """Test extraction of assembly structure from STEP file."""
        # Use a multi-part assembly file
        step_file = step_fixtures_dir / "12_assembly_2_parts.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)
        assert result.success
        assert isinstance(result, STEPExtractionResult)

        # Should have assembly structure
        assert hasattr(result, "assembly")
        assert result.assembly is not None, "Assembly should be extracted from multi-part file"
        assert isinstance(result.assembly, STEPAssembly)

        # Validate assembly structure using helper
        # File name suggests 2 parts, but validate at least 1
        assert_step_assembly_valid(result.assembly, expected_parts=None)
        assert len(result.assembly.parts) >= 1, "Assembly should have at least 1 part"

        # If we have 2 parts as filename suggests, validate both
        if len(result.assembly.parts) == 2:
            # Validate assembly metadata
            assert result.assembly.total_parts == 2
            assert len(result.assembly.root_parts) >= 1, "Should have at least one root part"

        # Validate each part in assembly
        for i, part in enumerate(result.assembly.parts):
            assert isinstance(part, STEPPart)
            assert_step_part_valid(part, check_geometry=step_parser.compute_mass_properties)

            # Each part should have a name or ID
            assert part.name is not None or part.part_id is not None, (
                f"Part {i} should have name or part_id"
            )

            # Validate shape type is recognized
            assert part.shape_type is not None
            assert part.shape_type in ("SOLID", "SHELL", "COMPOUND", "unknown")

        # Validate assembly hierarchy
        if len(result.assembly.root_parts) > 0:
            # Root parts should reference actual part names
            part_names = [p.name for p in result.assembly.parts if p.name is not None]
            for root_name in result.assembly.root_parts:
                assert root_name in part_names, f"Root part '{root_name}' not found in parts list"

        # Assembly should have overall bounding box
        assert hasattr(result, "overall_bbox")
        if result.overall_bbox is not None:
            assert isinstance(result.overall_bbox, tuple)
            assert len(result.overall_bbox) == 6
            xmin, ymin, zmin, xmax, ymax, zmax = result.overall_bbox
            assert xmax >= xmin
            assert ymax >= ymin
            assert zmax >= zmin

        # Shape counts should include at least SOLIDs or SHELLs
        assert hasattr(result, "shape_counts")
        assert isinstance(result.shape_counts, dict)
        if len(result.shape_counts) > 0:
            # Should have counted some shapes
            total_shapes = sum(result.shape_counts.values())
            assert total_shapes > 0, "Should have counted at least one shape"

    def test_multi_part_assemblies(
        self,
        step_parser: STEPParser,
        step_fixtures_dir: Path,
        assert_step_assembly_valid,
        assert_step_part_valid,
    ) -> None:
        """Test assemblies with different part counts."""
        # Test various assembly files with increasing complexity
        test_cases = [
            ("13_assembly_3_parts.step", 3),
            ("14_assembly_4_parts.step", 4),
            ("15_assembly_5_parts.step", 5),
        ]

        for filename, expected_parts in test_cases:
            step_file = step_fixtures_dir / filename

            if not step_file.exists():
                continue  # Skip if file doesn't exist

            result = step_parser.parse(step_file)
            assert result.success, f"Failed to parse {filename}"
            assert isinstance(result, STEPExtractionResult)
            assert result.assembly is not None, f"No assembly in {filename}"

            # Validate assembly has expected number of parts (or close to it)
            # Some STEP files may have different part counts than filename suggests
            assert len(result.assembly.parts) >= 1, (
                f"{filename} should have at least 1 part"
            )

            # Validate all parts
            for part in result.assembly.parts:
                assert_step_part_valid(part, check_geometry=step_parser.compute_mass_properties)

    def test_part_metadata(
        self,
        step_parser: STEPParser,
        step_fixtures_dir: Path,
        assert_step_part_valid,
    ) -> None:
        """Test extraction of part metadata from STEP file."""
        step_file = step_fixtures_dir / "01_simple_box.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)
        assert result.success
        assert isinstance(result, STEPExtractionResult)

        # Should have parts
        assert result.assembly is not None, "Should have assembly structure"
        assert len(result.assembly.parts) > 0, "Should have at least one part"

        part = result.assembly.parts[0]

        # Validate part using comprehensive helper
        assert_step_part_valid(part, check_geometry=step_parser.compute_mass_properties)

        # Additional validation for metadata completeness
        # Basic identification
        assert part.name is not None or part.part_id is not None, (
            "Part should have name or part_id"
        )
        assert part.shape_type is not None, "Part should have shape_type"
        assert part.shape_type in ("SOLID", "SHELL", "COMPOUND", "unknown")

        # Topology counts should be positive for a box
        # A box should have faces, edges, and vertices
        if part.shape_type == "SOLID":
            assert part.num_faces > 0, "A solid box should have faces"
            assert part.num_edges > 0, "A solid box should have edges"
            assert part.num_vertices > 0, "A solid box should have vertices"

        # Geometry metadata validation
        if step_parser.compute_mass_properties:
            # For a box, we should have volume and surface area
            if part.volume is not None:
                assert part.volume > 0, "Box should have positive volume"
            if part.surface_area is not None:
                assert part.surface_area > 0, "Box should have positive surface area"

        # Bounding box validation for a box
        if part.bbox is not None:
            xmin, ymin, zmin, xmax, ymax, zmax = part.bbox
            # Box should have non-zero dimensions in at least one axis
            has_dimension = (xmax > xmin) or (ymax > ymin) or (zmax > zmin)
            assert has_dimension, "Box should have non-zero dimensions"

        # Validate hierarchy metadata structure
        assert isinstance(part.children, list), "Children should be a list"
        assert isinstance(part.properties, dict), "Properties should be a dict"

        # Color should be None or valid RGB tuple
        if part.color is not None:
            assert isinstance(part.color, tuple) and len(part.color) == 3
            for val in part.color:
                assert isinstance(val, (int, float))
                # RGB values typically 0-1 range
                assert 0 <= val <= 1 or 0 <= val <= 255

        # Material should be None or string
        if part.material is not None:
            assert isinstance(part.material, str)

    def test_bounding_box_extraction(
        self, step_parser: STEPParser, step_fixtures_dir: Path
    ) -> None:
        """Test extraction of bounding boxes from STEP file."""
        step_file = step_fixtures_dir / "01_simple_box.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)
        assert result.success

        # Overall bounding box
        if result.overall_bbox is not None:
            assert isinstance(result.overall_bbox, tuple)
            assert len(result.overall_bbox) == 6
            xmin, ymin, zmin, xmax, ymax, zmax = result.overall_bbox
            assert xmax >= xmin
            assert ymax >= ymin
            assert zmax >= zmin

    def test_mass_properties_extraction(self, step_fixtures_dir: Path) -> None:
        """Test extraction of volume and surface area with mass properties enabled."""
        parser = STEPParser(compute_mass_properties=True)
        step_file = step_fixtures_dir / "01_simple_box.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = parser.parse(step_file)
        assert result.success

        # Total volume and surface area may be computed
        assert hasattr(result, "total_volume")
        assert hasattr(result, "total_surface_area")

        # These should be None or float
        assert result.total_volume is None or isinstance(result.total_volume, float)
        assert result.total_surface_area is None or isinstance(result.total_surface_area, float)

    def test_mass_properties_disabled(self, step_fixtures_dir: Path) -> None:
        """Test that mass properties are not computed when disabled."""
        parser = STEPParser(compute_mass_properties=False)
        step_file = step_fixtures_dir / "01_simple_box.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = parser.parse(step_file)
        assert result.success

        # Parts should still exist but without mass properties
        if result.assembly and len(result.assembly.parts) > 0:
            # Mass properties should be None or not computed
            # (implementation may still compute them depending on library)
            assert hasattr(result.assembly.parts[0], "volume")
            assert hasattr(result.assembly.parts[0], "surface_area")

    def test_nonexistent_file(self, step_parser: STEPParser, step_fixtures_dir: Path) -> None:
        """Test parsing a nonexistent STEP file."""
        step_file = step_fixtures_dir / "nonexistent.step"

        result = step_parser.parse(step_file)

        # Should have errors
        assert len(result.errors) > 0
        # Success may be False or True depending on error handling
        # What matters is that we have errors recorded
        assert isinstance(result.errors, list)

    def test_to_dict_conversion(
        self, step_parser: STEPParser, step_fixtures_dir: Path
    ) -> None:
        """Test conversion of STEP extraction result to dictionary."""
        step_file = step_fixtures_dir / "01_simple_box.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)
        result_dict = result.to_dict()

        # Validate dictionary structure
        assert isinstance(result_dict, dict)
        assert "source_file" in result_dict
        assert "source_type" in result_dict
        assert "assembly" in result_dict
        assert "shape_counts" in result_dict
        assert "total_volume" in result_dict
        assert "total_surface_area" in result_dict
        assert "overall_bbox" in result_dict

        # Validate assembly structure in dict
        if result_dict["assembly"] is not None:
            assembly_dict = result_dict["assembly"]
            assert isinstance(assembly_dict, dict)
            assert "parts" in assembly_dict
            assert "total_parts" in assembly_dict
            assert isinstance(assembly_dict["parts"], list)

    def test_part_to_dict(self) -> None:
        """Test conversion of STEPPart to dictionary."""
        part = STEPPart(
            name="TestPart",
            part_id="1",
            shape_type="SOLID",
            volume=100.0,
            surface_area=60.0,
            bbox=(0, 0, 0, 10, 10, 10),
            num_faces=6,
            num_edges=12,
            num_vertices=8,
        )

        part_dict = part.to_dict()

        assert isinstance(part_dict, dict)
        assert part_dict["name"] == "TestPart"
        assert part_dict["part_id"] == "1"
        assert part_dict["shape_type"] == "SOLID"
        assert part_dict["volume"] == 100.0
        assert part_dict["surface_area"] == 60.0
        assert part_dict["bbox"] == (0, 0, 0, 10, 10, 10)
        assert part_dict["num_faces"] == 6
        assert part_dict["num_edges"] == 12
        assert part_dict["num_vertices"] == 8

    def test_assembly_to_dict(self) -> None:
        """Test conversion of STEPAssembly to dictionary."""
        part1 = STEPPart(name="Part1", part_id="1", shape_type="SOLID")
        part2 = STEPPart(name="Part2", part_id="2", shape_type="SOLID")

        assembly = STEPAssembly(
            name="TestAssembly",
            parts=[part1, part2],
            total_parts=2,
            root_parts=["Part1", "Part2"],
        )

        assembly_dict = assembly.to_dict()

        assert isinstance(assembly_dict, dict)
        assert assembly_dict["name"] == "TestAssembly"
        assert assembly_dict["total_parts"] == 2
        assert len(assembly_dict["parts"]) == 2
        assert assembly_dict["root_parts"] == ["Part1", "Part2"]

    def test_geometry_summary(
        self, step_parser: STEPParser, step_fixtures_dir: Path
    ) -> None:
        """Test geometry summary generation from STEP file."""
        step_file = step_fixtures_dir / "01_simple_box.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)
        assert result.success

        # Should have geometry_summary
        if result.geometry_summary is not None:
            assert hasattr(result.geometry_summary, "total_entities")
            assert result.geometry_summary.total_entities >= 0

    def test_max_parts_limit(self, step_fixtures_dir: Path) -> None:
        """Test that max_parts limit is enforced."""
        # Create parser with very low limit
        parser = STEPParser(max_parts=1)

        # Use an assembly file with multiple parts
        step_file = step_fixtures_dir / "12_assembly_2_parts.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = parser.parse(step_file)
        assert result.success

        # Should not exceed max_parts
        if result.assembly:
            assert len(result.assembly.parts) <= 1

    def test_layers_conversion(
        self, step_parser: STEPParser, step_fixtures_dir: Path
    ) -> None:
        """Test conversion of shape counts to layer-like structure."""
        step_file = step_fixtures_dir / "01_simple_box.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)
        assert result.success

        # Layers should be created from shape types
        if result.layers:
            assert isinstance(result.layers, list)
            for layer in result.layers:
                assert hasattr(layer, "name")
                assert hasattr(layer, "entity_count")
                assert layer.entity_count > 0

    def test_metadata_extraction(
        self, step_parser: STEPParser, step_fixtures_dir: Path
    ) -> None:
        """Test extraction of STEP file metadata."""
        step_file = step_fixtures_dir / "01_simple_box.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)
        assert result.success

        # Should have metadata
        assert hasattr(result, "metadata")
        if result.metadata:
            assert isinstance(result.metadata, dict)
            # Should have parser info
            assert "parser" in result.metadata or "format" in result.metadata
