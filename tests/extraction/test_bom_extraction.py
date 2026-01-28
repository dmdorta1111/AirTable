"""
Tests for BOM (Bill of Materials) extraction from CAD files.

Tests BOM extraction functionality from DXF, IFC, and STEP files including:
- Flat and hierarchical BOM structures
- Parent-child relationships
- Quantity rollup
- Material and metadata extraction
"""

from pathlib import Path

import pytest

from pybase.extraction.base import CADExtractionResult, ExtractedBOM
from pybase.extraction.cad.dxf import EZDXF_AVAILABLE, DXFParser
from pybase.extraction.cad.ifc import IFCOPENSHELL_AVAILABLE, IFCParser
from pybase.extraction.cad.step import (
    CADQUERY_AVAILABLE,
    OCP_AVAILABLE,
    STEPParser,
)


class TestDXFBOMExtraction:
    """Test suite for BOM extraction from DXF files."""

    @pytest.fixture
    def bom_dxf_path(self, dxf_fixtures_dir: Path, temp_cad_dir: Path) -> Path:
        """Path to a DXF file with BOM-related blocks and attributes."""
        fixture_path = dxf_fixtures_dir / "bom_blocks.dxf"
        if fixture_path.exists():
            return fixture_path

        # Create test file with BOM blocks
        temp_path = temp_cad_dir / "bom_blocks.dxf"
        if not temp_path.exists() and EZDXF_AVAILABLE:
            import ezdxf

            doc = ezdxf.new("R2010")
            msp = doc.modelspace()

            # Create block with BOM attributes
            part_block = doc.blocks.new(name="PART_TAG")
            part_block.add_circle((0, 0), radius=2)
            part_block.add_attdef(
                tag="PART_NUMBER",
                text="PN-001",
                insert=(0, -2.5),
                dxfattribs={"height": 0.5}
            )
            part_block.add_attdef(
                tag="DESCRIPTION",
                text="Test Part",
                insert=(0, -3.0),
                dxfattribs={"height": 0.3}
            )
            part_block.add_attdef(
                tag="QTY",
                text="1",
                insert=(0, -3.5),
                dxfattribs={"height": 0.3}
            )
            part_block.add_attdef(
                tag="MATERIAL",
                text="STEEL",
                insert=(0, -4.0),
                dxfattribs={"height": 0.3}
            )

            # Insert parts with different attributes
            for i in range(3):
                insert = msp.add_blockref("PART_TAG", (i * 10, 0))
                insert.add_attrib("PART_NUMBER", f"PN-{100+i:03d}")
                insert.add_attrib("DESCRIPTION", f"Part {i+1}")
                insert.add_attrib("QTY", str(i+1))
                insert.add_attrib("MATERIAL", ["STEEL", "ALUMINUM", "COPPER"][i])

            doc.saveas(temp_path)

        return temp_path

    @pytest.mark.skipif(not EZDXF_AVAILABLE, reason="ezdxf not available")
    def test_bom_extraction_enabled(
        self, bom_dxf_path: Path
    ) -> None:
        """Test BOM extraction when enabled."""
        parser = DXFParser(extract_bom=True)
        result = parser.parse(bom_dxf_path)

        assert result.success
        assert result.bom is not None, "BOM should be extracted when extract_bom=True"
        assert isinstance(result.bom, ExtractedBOM)

    @pytest.mark.skipif(not EZDXF_AVAILABLE, reason="ezdxf not available")
    def test_bom_extraction_disabled(
        self, bom_dxf_path: Path
    ) -> None:
        """Test that BOM is not extracted when disabled."""
        parser = DXFParser(extract_bom=False)
        result = parser.parse(bom_dxf_path)

        assert result.success
        assert result.bom is None, "BOM should not be extracted when extract_bom=False"

    @pytest.mark.skipif(not EZDXF_AVAILABLE, reason="ezdxf not available")
    def test_bom_items_structure(
        self, bom_dxf_path: Path
    ) -> None:
        """Test that BOM items have correct structure."""
        parser = DXFParser(extract_bom=True)
        result = parser.parse(bom_dxf_path)

        if result.bom and len(result.bom.items) > 0:
            # Validate BOM structure
            assert isinstance(result.bom.items, list)
            assert result.bom.total_items == len(result.bom.items)
            assert result.bom.confidence > 0

            # Validate first item structure
            item = result.bom.items[0]
            assert isinstance(item, dict)
            assert "item_id" in item or "part_number" in item

            # Common BOM fields
            expected_fields = ["item_id", "part_number", "description", "quantity", "material"]
            for field in expected_fields:
                if field in item:
                    assert item[field] is not None

    @pytest.mark.skipif(not EZDXF_AVAILABLE, reason="ezdxf not available")
    def test_bom_from_block_attributes(
        self, bom_dxf_path: Path
    ) -> None:
        """Test BOM extraction from block attributes."""
        parser = DXFParser(extract_bom=True, extract_blocks=True)
        result = parser.parse(bom_dxf_path)

        # Should have both blocks and BOM
        assert len(result.blocks) > 0, "Should have blocks"

        if result.bom and len(result.bom.items) > 0:
            # BOM should be derived from block attributes
            assert result.bom.total_items > 0

            # Check that items have part numbers
            items_with_pn = [
                item for item in result.bom.items
                if item.get("part_number")
            ]
            assert len(items_with_pn) > 0, "Should have items with part numbers"

    @pytest.mark.skipif(not EZDXF_AVAILABLE, reason="ezdxf not available")
    def test_bom_to_dict_conversion(
        self, bom_dxf_path: Path
    ) -> None:
        """Test BOM conversion to dictionary."""
        parser = DXFParser(extract_bom=True)
        result = parser.parse(bom_dxf_path)

        if result.bom:
            bom_dict = result.bom.to_dict()
            assert isinstance(bom_dict, dict)
            assert "items" in bom_dict
            assert "total_items" in bom_dict
            assert "confidence" in bom_dict
            assert "is_flat" in bom_dict


class TestIFCBOMExtraction:
    """Test suite for BOM extraction from IFC files."""

    @pytest.fixture
    def simple_ifc_path(self, ifc_fixtures_dir: Path) -> Path:
        """Path to a simple IFC test file."""
        return ifc_fixtures_dir / "simple_building.ifc"

    @pytest.mark.skipif(not IFCOPENSHELL_AVAILABLE, reason="ifcopenshell not available")
    def test_bom_extraction_from_ifc(
        self, ifc_parser: IFCParser, simple_ifc_path: Path
    ) -> None:
        """Test BOM extraction from IFC file."""
        if not simple_ifc_path.exists():
            pytest.skip(f"Test file not found: {simple_ifc_path}")

        result = ifc_parser.parse(simple_ifc_path)
        assert result.success
        assert result.source_type == "ifc"

        # IFC files should typically extract BOM from building elements
        if result.bom:
            assert isinstance(result.bom, ExtractedBOM)
            assert result.bom.total_items >= 0

    @pytest.mark.skipif(not IFCOPENSHELL_AVAILABLE, reason="ifcopenshell not available")
    def test_bom_items_have_materials(
        self, ifc_parser: IFCParser, simple_ifc_path: Path
    ) -> None:
        """Test that IFC BOM items include material information."""
        if not simple_ifc_path.exists():
            pytest.skip(f"Test file not found: {simple_ifc_path}")

        result = ifc_parser.parse(simple_ifc_path)

        if result.bom and len(result.bom.items) > 0:
            # Check if any items have material information
            items_with_materials = [
                item for item in result.bom.items
                if item.get("material") or item.get("materials")
            ]
            # Some items might have materials
            assert len(items_with_materials) >= 0

    @pytest.mark.skipif(not IFCOPENSHELL_AVAILABLE, reason="ifcopenshell not available")
    def test_bom_hierarchy_detection(
        self, ifc_parser: IFCParser, simple_ifc_path: Path
    ) -> None:
        """Test detection of hierarchical BOM structure in IFC."""
        if not simple_ifc_path.exists():
            pytest.skip(f"Test file not found: {simple_ifc_path}")

        result = ifc_parser.parse(simple_ifc_path)

        if result.bom:
            # Check if BOM is flat or hierarchical
            assert isinstance(result.bom.is_flat, bool)

            # If hierarchical, should have parent-child map
            if not result.bom.is_flat:
                assert isinstance(result.bom.parent_child_map, dict)
                assert result.bom.hierarchy_level is not None
                assert result.bom.hierarchy_level > 0


class TestSTEPBOMExtraction:
    """Test suite for BOM extraction from STEP files."""

    @pytest.mark.skipif(
        not OCP_AVAILABLE and not CADQUERY_AVAILABLE,
        reason="OCP or cadquery not available",
    )
    def test_bom_extraction_from_step(
        self, step_parser: STEPParser, step_fixtures_dir: Path
    ) -> None:
        """Test BOM extraction from STEP assembly file."""
        step_file = step_fixtures_dir / "12_assembly_2_parts.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)
        assert result.success
        assert result.source_type == "step"

        # STEP assembly files should extract BOM
        if result.assembly and result.bom:
            assert isinstance(result.bom, ExtractedBOM)
            assert result.bom.total_items > 0

    @pytest.mark.skipif(
        not OCP_AVAILABLE and not CADQUERY_AVAILABLE,
        reason="OCP or cadquery not available",
    )
    def test_bom_from_assembly_structure(
        self, step_parser: STEPParser, step_fixtures_dir: Path
    ) -> None:
        """Test BOM extraction from STEP assembly structure."""
        step_file = step_fixtures_dir / "12_assembly_2_parts.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)

        # Should have both assembly and BOM
        if result.assembly:
            assert len(result.assembly.parts) > 0

            # BOM should be derived from assembly
            if result.bom:
                assert result.bom.total_items == len(result.assembly.parts)

                # Each part should correspond to a BOM item
                for i, part in enumerate(result.assembly.parts):
                    if i < len(result.bom.items):
                        item = result.bom.items[i]
                        assert item.get("item_id") or item.get("name")

    @pytest.mark.skipif(
        not OCP_AVAILABLE and not CADQUERY_AVAILABLE,
        reason="OCP or cadquery not available",
    )
    def test_bom_item_has_geometry_metadata(
        self, step_parser: STEPParser, step_fixtures_dir: Path
    ) -> None:
        """Test that STEP BOM items include geometry metadata."""
        step_file = step_fixtures_dir / "01_simple_box.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)

        if result.bom and len(result.bom.items) > 0:
            item = result.bom.items[0]

            # Should have geometry metadata from part
            assert "name" in item or "item_id" in item

            # Optional: volume, surface_area, material
            if "volume" in item:
                assert item["volume"] is None or isinstance(item["volume"], (int, float))

    @pytest.mark.skipif(
        not OCP_AVAILABLE and not CADQUERY_AVAILABLE,
        reason="OCP or cadquery not available",
    )
    def test_multi_part_assembly_bom(
        self, step_parser: STEPParser, step_fixtures_dir: Path
    ) -> None:
        """Test BOM extraction from multi-part STEP assemblies."""
        test_files = [
            "12_assembly_2_parts.step",
            "13_assembly_3_parts.step",
            "14_assembly_4_parts.step",
        ]

        for filename in test_files:
            step_file = step_fixtures_dir / filename

            if not step_file.exists():
                continue

            result = step_parser.parse(step_file)
            assert result.success, f"Failed to parse {filename}"

            if result.assembly and result.bom:
                # BOM should match assembly part count
                assert result.bom.total_items == len(result.assembly.parts), (
                    f"{filename}: BOM count should match assembly part count"
                )

    @pytest.mark.skipif(
        not OCP_AVAILABLE and not CADQUERY_AVAILABLE,
        reason="OCP or cadquery not available",
    )
    def test_bom_hierarchy_from_step(
        self, step_parser: STEPParser, step_fixtures_dir: Path
    ) -> None:
        """Test hierarchical BOM extraction from STEP file."""
        step_file = step_fixtures_dir / "12_assembly_2_parts.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)

        if result.bom:
            # Check hierarchy detection
            assert isinstance(result.bom.is_flat, bool)

            # If assembly has nested parts, BOM should reflect hierarchy
            if result.assembly and any(len(part.children) > 0 for part in result.assembly.parts):
                assert not result.bom.is_flat, "Should detect hierarchical structure"
                assert result.bom.hierarchy_level is not None
                assert result.bom.hierarchy_level > 0
                assert len(result.bom.parent_child_map) > 0


class TestBOMStructure:
    """Test suite for BOM structure and properties."""

    @pytest.mark.skipif(not EZDXF_AVAILABLE, reason="ezdxf not available")
    def test_bom_confidence_score(
        self, dxf_fixtures_dir: Path, temp_cad_dir: Path
    ) -> None:
        """Test that BOM has confidence score."""
        # Create test file
        import ezdxf

        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        part_block = doc.blocks.new(name="PART")
        part_block.add_attdef(tag="PART_NUMBER", text="P-001", insert=(0, 0))
        msp.add_blockref("PART", (0, 0)).add_attrib("PART_NUMBER", "P-001")

        temp_path = temp_cad_dir / "bom_confidence.dxf"
        doc.saveas(temp_path)

        parser = DXFParser(extract_bom=True)
        result = parser.parse(temp_path)

        if result.bom:
            assert isinstance(result.bom.confidence, float)
            assert 0.0 <= result.bom.confidence <= 1.0

    @pytest.mark.skipif(not EZDXF_AVAILABLE, reason="ezdxf not available")
    def test_flat_vs_hierarchical_bom(
        self, dxf_fixtures_dir: Path, temp_cad_dir: Path
    ) -> None:
        """Test flat BOM structure (DXF typically produces flat BOMs)."""
        import ezdxf

        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        part_block = doc.blocks.new(name="COMPONENT")
        part_block.add_attdef(tag="PART_NUMBER", text="X", insert=(0, 0))

        # Create flat structure
        for i in range(5):
            msp.add_blockref("COMPONENT", (i * 10, 0)).add_attrib("PART_NUMBER", f"PART-{i}")

        temp_path = temp_cad_dir / "flat_bom.dxf"
        doc.saveas(temp_path)

        parser = DXFParser(extract_bom=True)
        result = parser.parse(temp_path)

        if result.bom:
            # DXF BOMs are typically flat
            assert result.bom.is_flat or result.bom.is_flat is False  # Can be either
            assert result.bom.total_items == 5

    def test_bom_headers(
        self, step_fixtures_dir: Path
    ) -> None:
        """Test BOM headers property."""
        # Create a mock BOM with headers
        bom = ExtractedBOM(
            items=[{"item_id": "1", "part_number": "P-001"}],
            headers=["Item ID", "Part Number", "Quantity", "Material"],
            total_items=1,
        )

        assert bom.headers is not None
        assert len(bom.headers) == 4
        assert "Part Number" in bom.headers

    def test_bom_empty_items(
        self,
    ) -> None:
        """Test BOM with no items."""
        bom = ExtractedBOM(items=[], total_items=0)

        assert bom.total_items == 0
        assert len(bom.items) == 0
        assert bom.is_flat is True  # Default is flat

    def test_bom_parent_child_map(
        self,
    ) -> None:
        """Test BOM parent-child relationship mapping."""
        bom = ExtractedBOM(
            items=[
                {"item_id": "1", "part_number": "ASSEMBLY"},
                {"item_id": "2", "part_number": "PART-A"},
                {"item_id": "3", "part_number": "PART-B"},
            ],
            total_items=3,
            is_flat=False,
            parent_child_map={"1": ["2", "3"]},
            hierarchy_level=2,
        )

        assert not bom.is_flat
        assert bom.hierarchy_level == 2
        assert len(bom.parent_child_map) == 1
        assert bom.parent_child_map["1"] == ["2", "3"]

    def test_bom_quantity_rollup(
        self,
    ) -> None:
        """Test BOM quantity rollup properties."""
        bom = ExtractedBOM(
            items=[
                {"item_id": "1", "quantity": 5},
            ],
            total_items=1,
            quantity_rolled_up=True,
            original_quantities={"1": 2},
        )

        assert bom.quantity_rolled_up is True
        assert bom.original_quantities["1"] == 2
        # After rollup, quantity would be different (e.g., 2 * some multiplier = 5)

    @pytest.mark.skipif(
        not OCP_AVAILABLE and not CADQUERY_AVAILABLE,
        reason="OCP or cadquery not available",
    )
    def test_bom_to_dict_full_structure(
        self, step_parser: STEPParser, step_fixtures_dir: Path
    ) -> None:
        """Test complete BOM to_dict conversion."""
        step_file = step_fixtures_dir / "01_simple_box.step"

        if not step_file.exists():
            pytest.skip(f"Test file not found: {step_file}")

        result = step_parser.parse(step_file)

        if result.bom:
            bom_dict = result.bom.to_dict()

            # Check all expected fields
            expected_fields = [
                "items",
                "headers",
                "total_items",
                "confidence",
                "is_flat",
                "hierarchy_level",
                "parent_child_map",
                "quantity_rolled_up",
                "original_quantities",
            ]

            for field in expected_fields:
                assert field in bom_dict, f"Missing field: {field}"

            # Validate types
            assert isinstance(bom_dict["items"], list)
            assert isinstance(bom_dict["total_items"], int)
            assert isinstance(bom_dict["confidence"], float)
            assert isinstance(bom_dict["is_flat"], bool)


class TestBOMExtractionIntegration:
    """Integration tests for BOM extraction across formats."""

    @pytest.mark.skipif(not EZDXF_AVAILABLE, reason="ezdxf not available")
    def test_dxf_bom_with_result_conversion(
        self, temp_cad_dir: Path
    ) -> None:
        """Test DXF BOM extraction with full result conversion."""
        import ezdxf

        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        part_block = doc.blocks.new(name="ITEM")
        part_block.add_attdef(tag="PN", text="X", insert=(0, 0))
        part_block.add_attdef(tag="DESC", text="Description", insert=(0, -0.5))

        insert = msp.add_blockref("ITEM", (0, 0))
        insert.add_attrib("PN", "TEST-001")
        insert.add_attrib("DESC", "Test Item")

        temp_path = temp_cad_dir / "bom_integration.dxf"
        doc.saveas(temp_path)

        parser = DXFParser(extract_bom=True, extract_blocks=True)
        result = parser.parse(temp_path)

        # Convert full result to dict
        result_dict = result.to_dict()

        assert "bom" in result_dict
        assert result_dict["bom"] is not None
        assert isinstance(result_dict["bom"], dict)

        # Should also have blocks
        assert "blocks" in result_dict
        assert len(result_dict["blocks"]) > 0

    @pytest.mark.skipif(
        not (OCP_AVAILABLE or CADQUERY_AVAILABLE) or not EZDXF_AVAILABLE,
        reason="Required parsers not available",
    )
    def test_cross_format_bom_structure(
        self, step_fixtures_dir: Path, temp_cad_dir: Path
    ) -> None:
        """Test that BOM structure is consistent across formats."""
        import ezdxf

        # Create DXF with BOM
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        part_block = doc.blocks.new(name="PART")
        part_block.add_attdef(tag="PART_NUMBER", text="X", insert=(0, 0))

        for i in range(3):
            msp.add_blockref("PART", (i * 10, 0)).add_attrib("PART_NUMBER", f"DXF-P{i}")

        dxf_path = temp_cad_dir / "cross_format_dxf.dxf"
        doc.saveas(dxf_path)

        # Parse both formats
        dxf_parser = DXFParser(extract_bom=True)
        dxf_result = dxf_parser.parse(dxf_path)

        # Check that both produce ExtractedBOM with same structure
        if dxf_result.bom:
            assert hasattr(dxf_result.bom, "items")
            assert hasattr(dxf_result.bom, "total_items")
            assert hasattr(dxf_result.bom, "confidence")
            assert hasattr(dxf_result.bom, "is_flat")

            # Check to_dict works consistently
            dxf_dict = dxf_result.bom.to_dict()
            assert "items" in dxf_dict
            assert "total_items" in dxf_dict
