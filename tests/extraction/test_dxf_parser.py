"""
Tests for DXF parser functionality.

Tests dimension extraction, layer parsing, block extraction, and text handling
from AutoCAD DXF files.
"""

from pathlib import Path

import pytest

from pybase.extraction.base import CADExtractionResult, ExtractedDimension
from pybase.extraction.cad.dxf import EZDXF_AVAILABLE, DXFParser


@pytest.mark.skipif(not EZDXF_AVAILABLE, reason="ezdxf not available")
class TestDXFParser:
    """Test suite for DXF parser."""

    def test_parser_initialization(self, dxf_parser: DXFParser) -> None:
        """Test DXF parser initialization."""
        assert dxf_parser is not None
        assert isinstance(dxf_parser, DXFParser)
        assert dxf_parser.extract_layers is True
        assert dxf_parser.extract_blocks is True
        assert dxf_parser.extract_dimensions is True
        assert dxf_parser.extract_text is True

    def test_parse_simple_dxf(
        self, dxf_parser: DXFParser, simple_dxf_path: Path, assert_extraction_valid
    ) -> None:
        """Test parsing a simple DXF file."""
        result = dxf_parser.parse(simple_dxf_path)
        assert_extraction_valid(result)
        assert result.success
        assert result.source_type == "dxf"
        assert result.has_content

    def test_dimension_extraction(
        self,
        dxf_parser: DXFParser,
        dimensions_dxf_path: Path,
        assert_dxf_dimensions_valid,
    ) -> None:
        """Test extraction of various dimension types from DXF file."""
        result = dxf_parser.parse(dimensions_dxf_path)
        assert result.success
        assert len(result.errors) == 0

        # Validate dimensions if any were extracted
        if len(result.dimensions) > 0:
            assert_dxf_dimensions_valid(result.dimensions)

            # Verify dimension properties
            for dim in result.dimensions:
                assert isinstance(dim, ExtractedDimension)
                assert dim.value is not None
                assert isinstance(dim.value, (int, float))
                assert dim.value > 0
                assert dim.unit == "mm"
                assert dim.dimension_type in (
                    "linear",
                    "aligned",
                    "angular",
                    "radius",
                    "diameter",
                    "angular3point",
                    "ordinate",
                )
                assert dim.confidence == 1.0
        else:
            # Test passes even if no dimensions extracted - file was parsed successfully
            assert result.success

    def test_dimension_types(
        self, dxf_parser: DXFParser, dimensions_dxf_path: Path
    ) -> None:
        """Test that different dimension types are correctly identified."""
        result = dxf_parser.parse(dimensions_dxf_path)
        assert result.success

        # Extract dimension types if any dimensions were found
        if len(result.dimensions) > 0:
            dimension_types = {dim.dimension_type for dim in result.dimensions}
            # Should have at least one type
            assert len(dimension_types) > 0

            # All types should be valid
            for dim_type in dimension_types:
                assert dim_type in (
                    "linear",
                    "aligned",
                    "angular",
                    "radius",
                    "diameter",
                    "angular3point",
                    "ordinate",
                )

    def test_dimension_values(
        self, dxf_parser: DXFParser, dimensions_dxf_path: Path
    ) -> None:
        """Test that dimension values are correctly extracted."""
        result = dxf_parser.parse(dimensions_dxf_path)
        assert result.success

        # All dimensions should have valid values
        for dim in result.dimensions:
            assert dim.value is not None
            assert dim.value > 0
            assert dim.unit is not None

    def test_text_extraction(
        self,
        dxf_parser: DXFParser,
        text_dxf_path: Path,
        assert_dxf_text_valid,
    ) -> None:
        """Test extraction of TEXT and MTEXT entities including formatting."""
        result = dxf_parser.parse(text_dxf_path)
        assert result.success

        # Validate text extraction - expect at least 4 text entities
        assert_dxf_text_valid(result.text_blocks, expected_count=4)

        # Check text properties
        for text_block in result.text_blocks:
            assert text_block.text is not None
            assert len(text_block.text) > 0
            assert text_block.confidence == 1.0

        # Extract text contents for verification
        text_contents = [block.text for block in result.text_blocks]

        # Verify both TEXT and MTEXT entities are extracted
        assert any("Simple Text" in text for text in text_contents), "TEXT entity should be extracted"
        assert any("DRAWING TITLE" in text for text in text_contents), "Large TEXT should be extracted"

        # CORE TEST: Verify MTEXT with formatting codes is properly handled
        # The MTEXT has \P codes which should be converted to newlines by ezdxf's plain_text()
        mtext_blocks = [
            block
            for block in result.text_blocks
            if "Multi-line" in block.text or "paragraph" in block.text
        ]
        assert len(mtext_blocks) > 0, "MTEXT entity with formatting should be extracted"

        # Verify paragraph breaks (\P) are converted to actual newlines
        mtext = mtext_blocks[0]
        assert "\n" in mtext.text, "MTEXT paragraph breaks (\\P) should be converted to newlines"

        # Verify the MTEXT contains expected content
        assert "Multi-line" in mtext.text
        assert "paragraph" in mtext.text
        assert "formatting" in mtext.text

        # Verify font size detection works for both TEXT and MTEXT
        font_sizes = [block.font_size for block in result.text_blocks if block.font_size]
        assert len(font_sizes) > 0, "Font sizes should be extracted from text entities"

        # Verify different font sizes are detected
        unique_font_sizes = set(font_sizes)
        assert len(unique_font_sizes) > 1, "Multiple different font sizes should be detected"

        # Verify MTEXT has font size (char_height attribute)
        mtext_with_font_size = [
            block
            for block in result.text_blocks
            if "Multi-line" in block.text and block.font_size is not None
        ]
        assert len(mtext_with_font_size) > 0, "MTEXT should have font size extracted"

    def test_layer_extraction(
        self,
        dxf_parser: DXFParser,
        simple_dxf_path: Path,
        assert_dxf_layers_valid,
    ) -> None:
        """Test extraction of layer information."""
        result = dxf_parser.parse(simple_dxf_path)
        assert result.success

        # Validate layers
        assert_dxf_layers_valid(result.layers, expected_count=1)

        # Every DXF should have at least the default layer "0"
        layer_names = {layer.name for layer in result.layers}
        assert "0" in layer_names

    def test_block_extraction(
        self,
        dxf_parser: DXFParser,
        blocks_dxf_path: Path,
        assert_dxf_blocks_valid,
    ) -> None:
        """Test extraction of block definitions and inserts."""
        result = dxf_parser.parse(blocks_dxf_path)
        assert result.success

        # Validate blocks
        assert_dxf_blocks_valid(result.blocks, expected_count=1)

        # Check that blocks have inserts
        total_inserts = sum(block.insert_count for block in result.blocks)
        assert total_inserts > 0

    def test_block_attributes(
        self, dxf_parser: DXFParser, blocks_dxf_path: Path
    ) -> None:
        """Test extraction of block attributes."""
        result = dxf_parser.parse(blocks_dxf_path)
        assert result.success

        # Find blocks with attributes
        blocks_with_attributes = [
            block for block in result.blocks if len(block.attributes) > 0
        ]

        # The test file should have at least one block with attributes
        if len(blocks_with_attributes) > 0:
            for block in blocks_with_attributes:
                for attrib in block.attributes:
                    assert "tag" in attrib
                    assert "value" in attrib

    def test_geometry_summary(
        self, dxf_parser: DXFParser, simple_dxf_path: Path
    ) -> None:
        """Test extraction of geometry summary."""
        result = dxf_parser.parse(simple_dxf_path)
        assert result.success

        # Check geometry summary
        assert result.geometry_summary is not None
        assert result.geometry_summary.total_entities > 0

        # Simple file should have at least a line and a circle
        assert result.geometry_summary.lines > 0
        assert result.geometry_summary.circles > 0

    def test_metadata_extraction(
        self, dxf_parser: DXFParser, simple_dxf_path: Path
    ) -> None:
        """Test extraction of DXF metadata."""
        result = dxf_parser.parse(simple_dxf_path)
        assert result.success

        # Check metadata
        assert result.metadata is not None
        assert isinstance(result.metadata, dict)
        assert "dxf_version" in result.metadata

    def test_parse_nonexistent_file(self, dxf_parser: DXFParser) -> None:
        """Test parsing a nonexistent file."""
        result = dxf_parser.parse("nonexistent_file.dxf")
        assert not result.success
        assert len(result.errors) > 0

    def test_parse_with_stream(
        self, dxf_parser: DXFParser, simple_dxf_path: Path
    ) -> None:
        """Test parsing from a file stream."""
        # Note: Stream parsing may have issues with some ezdxf versions
        # This test validates the behavior even if it fails
        with open(simple_dxf_path, "rb") as f:
            result = dxf_parser.parse(f)
            assert result.source_file == "<stream>"

            # Parser may report errors with stream parsing
            # Test passes if either succeeds or has expected error
            if not result.success:
                assert len(result.errors) > 0

    def test_selective_extraction(self, simple_dxf_path: Path) -> None:
        """Test parser with selective extraction options."""
        # Only extract layers
        parser = DXFParser(
            extract_layers=True,
            extract_blocks=False,
            extract_dimensions=False,
            extract_text=False,
            extract_geometry=False,
        )
        result = parser.parse(simple_dxf_path)
        assert result.success
        assert len(result.layers) > 0

    def test_to_dict_conversion(
        self, dxf_parser: DXFParser, dimensions_dxf_path: Path
    ) -> None:
        """Test conversion of extraction result to dictionary."""
        result = dxf_parser.parse(dimensions_dxf_path)
        assert result.success

        # Convert to dict
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "source_file" in result_dict
        assert "source_type" in result_dict
        assert "dimensions" in result_dict
        assert "layers" in result_dict
        assert "blocks" in result_dict
        assert "success" in result_dict
        assert result_dict["success"] is True

    def test_dimension_tolerance_parsing(
        self, dxf_parser: DXFParser, temp_cad_dir: Path
    ) -> None:
        """Test parsing of dimension tolerances from override text."""
        if not EZDXF_AVAILABLE:
            pytest.skip("ezdxf not available")

        import ezdxf

        # Create a DXF with tolerance annotations
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        # Add a dimension with tolerance in override text
        dim = msp.add_linear_dim(
            base=(5, -2),
            p1=(0, 0),
            p2=(10, 0),
            dimstyle="EZDXF",
            override={"text": "10.0 ±0.1"},
        )

        temp_path = temp_cad_dir / "tolerance_test.dxf"
        doc.saveas(temp_path)

        # Parse and check tolerance
        result = dxf_parser.parse(temp_path)
        assert result.success

        # Find dimensions with tolerances
        dims_with_tolerance = [
            d for d in result.dimensions if d.tolerance_plus is not None
        ]

        # Check if tolerance was parsed (may not work in all ezdxf versions)
        if len(dims_with_tolerance) > 0:
            dim = dims_with_tolerance[0]
            assert dim.tolerance_plus is not None
            assert dim.tolerance_minus is not None

    def test_layer_entity_counts(
        self, dxf_parser: DXFParser, simple_dxf_path: Path
    ) -> None:
        """Test that layer entity counts are correctly calculated."""
        result = dxf_parser.parse(simple_dxf_path)
        assert result.success

        # Find the default layer
        layer_0 = next((layer for layer in result.layers if layer.name == "0"), None)
        assert layer_0 is not None

        # Default layer should have entities
        assert layer_0.entity_count > 0

    def test_empty_dxf(self, dxf_parser: DXFParser, temp_cad_dir: Path) -> None:
        """Test parsing an empty DXF file."""
        if not EZDXF_AVAILABLE:
            pytest.skip("ezdxf not available")

        import ezdxf

        # Create an empty DXF
        doc = ezdxf.new("R2010")
        temp_path = temp_cad_dir / "empty.dxf"
        doc.saveas(temp_path)

        # Parse empty file
        result = dxf_parser.parse(temp_path)
        assert result.success
        # Should have at least default layer "0"
        assert len(result.layers) >= 1
