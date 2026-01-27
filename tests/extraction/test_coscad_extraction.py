"""Unit tests for CosCAD extractor with mocked gRPC service.

Tests the CosCADExtractor class and its integration with the CosCAD gRPC client.
Uses unittest.mock to simulate gRPC service responses without requiring an actual service.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from pybase.extraction.base import (
    CADExtractionResult,
    ExtractedDimension,
    ExtractedLayer,
    ExtractedText,
    ExtractedTitleBlock,
    GeometrySummary,
)
from pybase.extraction.cad.coscad import CosCADExtractor
from pybase.extraction.cad.coscad_grpc_stub import (
    CosCADAnnotation,
    CosCADBoundingBox,
    CosCADDimension,
    CosCADDimensionType,
    CosCADExtractionType,
    CosCADGeometry,
    CosCADMetadata,
    CosCADPoint3D,
    CosCADUnit,
)


# =============================================================================
# Mock Response Builders
# =============================================================================


def create_mock_geometry(
    num_faces: int = 10,
    num_edges: int = 20,
    num_vertices: int = 15,
    num_surfaces: int = 5,
    num_solids: int = 2,
) -> Mock:
    """Create a mock CosCAD geometry response."""
    geometry = Mock(spec=CosCADGeometry)
    geometry.num_faces = num_faces
    geometry.num_edges = num_edges
    geometry.num_vertices = num_vertices
    geometry.num_surfaces = num_surfaces
    geometry.num_solids = num_solids

    # Mock to_dict() method
    geometry.to_dict.return_value = {
        "num_faces": num_faces,
        "num_edges": num_edges,
        "num_vertices": num_vertices,
        "num_surfaces": num_surfaces,
        "num_solids": num_solids,
    }

    return geometry


def create_mock_dimension(
    value: float,
    unit: str = "mm",
    dimension_type: str = "linear",
    tolerance_plus: float | None = None,
    tolerance_minus: float | None = None,
    label: str | None = None,
) -> Mock:
    """Create a mock CosCAD dimension response."""
    dimension = Mock(spec=CosCADDimension)
    dimension.nominal_value = value
    dimension.unit = CosCADUnit(unit)
    dimension.dimension_type = CosCADDimensionType(dimension_type)
    dimension.tolerance_upper = tolerance_plus
    dimension.tolerance_lower = tolerance_minus
    dimension.label = label
    dimension.bbox = {"min": {"x": 0.0, "y": 0.0, "z": 0.0}, "max": {"x": 10.0, "y": 10.0, "z": 10.0}}

    # Mock to_dict() method
    dimension.to_dict.return_value = {
        "value": value,
        "unit": unit,
        "dimension_type": dimension_type,
        "tolerance_plus": tolerance_plus,
        "tolerance_minus": tolerance_minus,
        "label": label,
        "bbox": dimension.bbox,
    }

    return dimension


def create_mock_annotation(
    text: str,
    font_size: float | None = None,
    bbox: dict | None = None,
) -> Mock:
    """Create a mock CosCAD annotation response."""
    annotation = Mock(spec=CosCADAnnotation)
    annotation.text = text
    annotation.font_size = font_size
    annotation.bbox = bbox or {"min": {"x": 0.0, "y": 0.0, "z": 0.0}, "max": {"x": 10.0, "y": 10.0, "z": 10.0}}

    # Mock to_dict() method
    annotation.to_dict.return_value = {
        "text": text,
        "font_size": font_size,
        "bbox": annotation.bbox,
    }

    return annotation


def create_mock_metadata(
    author: str | None = None,
    title: str | None = None,
    drawing_number: str | None = None,
    revision: str | None = None,
    custom_properties: dict | None = None,
) -> Mock:
    """Create a mock CosCAD metadata response."""
    metadata = Mock(spec=CosCADMetadata)
    metadata.author = author
    metadata.title = title
    metadata.drawing_number = drawing_number
    metadata.revision = revision
    metadata.custom_properties = custom_properties or {}

    # Mock to_dict() method
    metadata.to_dict.return_value = {
        "author": author,
        "title": title,
        "drawing_number": drawing_number,
        "revision": revision,
        "custom_properties": custom_properties or {},
    }

    return metadata


def create_mock_title_block(
    drawing_number: str | None = None,
    title: str | None = None,
    revision: str | None = None,
    date: str | None = None,
    author: str | None = None,
    company: str | None = None,
    scale: str | None = None,
    sheet: str | None = None,
    material: str | None = None,
    finish: str | None = None,
) -> Mock:
    """Create a mock title block response."""
    title_block = Mock()
    title_block.drawing_number = drawing_number
    title_block.title = title
    title_block.revision = revision
    title_block.date = date
    title_block.author = author
    title_block.company = company
    title_block.scale = scale
    title_block.sheet = sheet
    title_block.material = material
    title_block.finish = finish

    # Mock to_dict() method
    title_block.to_dict.return_value = {
        "drawing_number": drawing_number,
        "title": title,
        "revision": revision,
        "date": date,
        "author": author,
        "company": company,
        "scale": scale,
        "sheet": sheet,
        "material": material,
        "finish": finish,
    }

    return title_block


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def coscad_extractor() -> CosCADExtractor:
    """Create a CosCADExtractor instance for testing."""
    return CosCADExtractor(
        service_host="localhost",
        service_port=50051,
        timeout=300,
        extract_geometry=True,
        extract_dimensions=True,
        extract_annotations=True,
        extract_metadata=True,
    )


@pytest.fixture
def sample_coscad_file(tmp_path: Path) -> Path:
    """Create a sample CosCAD test file path."""
    # Create an empty file (actual content doesn't matter for mocked tests)
    test_file = tmp_path / "test_model.coscad"
    test_file.write_text("mock coscad content")
    return test_file


# =============================================================================
# Geometry Extraction Tests
# =============================================================================


class TestCosCADGeometryExtraction:
    """Test geometry extraction from CosCAD files."""

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_extract_geometry_basic(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test basic geometry extraction."""
        # Setup mock response
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_geometry_response = Mock()
        mock_geometry_response.geometry = create_mock_geometry(
            num_faces=10,
            num_edges=20,
            num_vertices=15,
            num_surfaces=5,
            num_solids=2,
        )
        mock_client.extract_geometry.return_value = mock_geometry_response

        # Mock metadata response (optional)
        mock_metadata_response = Mock()
        mock_metadata_response.metadata = None
        mock_metadata_response.title_block = None
        mock_client.extract_metadata.return_value = mock_metadata_response

        # Mock dimensions response (optional)
        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = None
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        # Mock annotations response (optional)
        mock_annotations_response = Mock()
        mock_annotations_response.annotations = None
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Execute
        result = coscad_extractor.parse(sample_coscad_file)

        # Verify
        assert result.success is True
        assert len(result.errors) == 0
        assert result.source_type == "coscad"

        # Check geometry layers
        assert len(result.layers) == 5
        layer_names = {layer.name for layer in result.layers}
        assert "Solids" in layer_names
        assert "Surfaces" in layer_names
        assert "Faces" in layer_names
        assert "Edges" in layer_names
        assert "Vertices" in layer_names

        # Check geometry summary
        assert result.geometry_summary is not None
        assert result.geometry_summary.solids == 2
        assert result.geometry_summary.total_entities == 52  # 10+20+15+5+2

        # Verify client was called correctly
        mock_client.extract_geometry.assert_called_once_with(str(sample_coscad_file))

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_extract_geometry_with_zero_entities(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test geometry extraction with empty geometry."""
        # Setup mock response
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_geometry_response = Mock()
        mock_geometry_response.geometry = create_mock_geometry(
            num_faces=0,
            num_edges=0,
            num_vertices=0,
            num_surfaces=0,
            num_solids=0,
        )
        mock_client.extract_geometry.return_value = mock_geometry_response

        # Mock other responses
        mock_metadata_response = Mock()
        mock_metadata_response.metadata = None
        mock_client.extract_metadata.return_value = mock_metadata_response

        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = None
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        mock_annotations_response = Mock()
        mock_annotations_response.annotations = None
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Execute
        result = coscad_extractor.parse(sample_coscad_file)

        # Verify - should succeed but with no layers
        assert result.success is True
        assert len(result.layers) == 0  # No layers created for zero counts
        assert result.geometry_summary is not None
        assert result.geometry_summary.solids == 0
        assert result.geometry_summary.total_entities == 0


# =============================================================================
# Dimension Extraction Tests
# =============================================================================


class TestCosCADDimensionExtraction:
    """Test dimension extraction from CosCAD files."""

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_extract_dimensions_basic(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test basic dimension extraction."""
        # Setup mock response
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = [
            create_mock_dimension(
                value=10.0,
                unit="mm",
                dimension_type="linear",
                tolerance_plus=0.1,
                tolerance_minus=0.05,
                label="LENGTH",
            ),
            create_mock_dimension(
                value=5.5,
                unit="mm",
                dimension_type="radial",
                tolerance_plus=0.02,
                tolerance_minus=None,
                label="RADIUS",
            ),
        ]
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        # Mock other responses
        mock_geometry_response = Mock()
        mock_geometry_response.geometry = None
        mock_client.extract_geometry.return_value = mock_geometry_response

        mock_metadata_response = Mock()
        mock_metadata_response.metadata = None
        mock_client.extract_metadata.return_value = mock_metadata_response

        mock_annotations_response = Mock()
        mock_annotations_response.annotations = None
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Execute
        result = coscad_extractor.parse(sample_coscad_file)

        # Verify
        assert result.success is True
        assert len(result.dimensions) == 2

        # Check first dimension
        dim1 = result.dimensions[0]
        assert isinstance(dim1, ExtractedDimension)
        assert dim1.value == 10.0
        assert dim1.unit == "mm"
        assert dim1.dimension_type == "linear"
        assert dim1.tolerance_plus is not None
        assert dim1.tolerance_plus == 0.1
        assert dim1.tolerance_minus is not None
        assert dim1.tolerance_minus == 0.05

        # Check second dimension
        dim2 = result.dimensions[1]
        assert isinstance(dim2, ExtractedDimension)
        assert dim2.value == 5.5
        assert dim2.unit == "mm"
        assert dim2.dimension_type == "radial"
        assert dim2.tolerance_plus == 0.02
        assert dim2.tolerance_minus is None

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_extract_dimensions_unit_conversion(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test dimension unit conversion from various CosCAD units."""
        # Setup mock response
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = [
            create_mock_dimension(value=100.0, unit="mm"),  # Should stay as mm
            create_mock_dimension(value=1.0, unit="inch"),  # Should stay as inch
            create_mock_dimension(value=1000.0, unit="um"),  # Should convert to mm (1.0 mm)
            create_mock_dimension(value=10.0, unit="cm"),  # Should convert to mm (100.0 mm)
        ]
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        # Mock other responses
        mock_geometry_response = Mock()
        mock_geometry_response.geometry = None
        mock_client.extract_geometry.return_value = mock_geometry_response

        mock_metadata_response = Mock()
        mock_metadata_response.metadata = None
        mock_client.extract_metadata.return_value = mock_metadata_response

        mock_annotations_response = Mock()
        mock_annotations_response.annotations = None
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Execute
        result = coscad_extractor.parse(sample_coscad_file)

        # Verify unit conversions
        assert len(result.dimensions) == 4

        # Millimeter - should stay the same
        assert result.dimensions[0].value == 100.0
        assert result.dimensions[0].unit == "mm"

        # Inch - should stay the same
        assert result.dimensions[1].value == 1.0
        assert result.dimensions[1].unit == "inch"

        # Micrometer - should convert to mm
        assert result.dimensions[2].value == 1.0
        assert result.dimensions[2].unit == "mm"

        # Centimeter - should convert to mm
        assert result.dimensions[3].value == 100.0  # 10 cm = 100 mm
        assert result.dimensions[3].unit == "mm"

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_extract_dimensions_from_label(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test parsing tolerances from dimension label text."""
        # Setup mock response
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = [
            create_mock_dimension(
                value=10.0,
                unit="mm",
                label="10 \u00B10.1",  # "10 ±0.1"
            ),
            create_mock_dimension(
                value=20.0,
                unit="mm",
                label="20 +0.1/-0.05",
            ),
        ]
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        # Mock other responses
        mock_geometry_response = Mock()
        mock_geometry_response.geometry = None
        mock_client.extract_geometry.return_value = mock_geometry_response

        mock_metadata_response = Mock()
        mock_metadata_response.metadata = None
        mock_client.extract_metadata.return_value = mock_metadata_response

        mock_annotations_response = Mock()
        mock_annotations_response.annotations = None
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Execute
        result = coscad_extractor.parse(sample_coscad_file)

        # Verify parsed tolerances
        assert len(result.dimensions) == 2

        # Symmetric tolerance from ± symbol
        assert result.dimensions[0].value == 10.0
        assert result.dimensions[0].tolerance_plus == 0.1
        assert result.dimensions[0].tolerance_minus == 0.1

        # Asymmetric tolerance
        assert result.dimensions[1].value == 20.0
        assert result.dimensions[1].tolerance_plus == 0.1
        assert result.dimensions[1].tolerance_minus == 0.05


# =============================================================================
# Annotation Extraction Tests
# =============================================================================


class TestCosCADAnnotationExtraction:
    """Test annotation extraction from CosCAD files."""

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_extract_annotations_basic(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test basic annotation extraction."""
        # Setup mock response
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_annotations_response = Mock()
        mock_annotations_response.annotations = [
            create_mock_annotation(
                text="NOTE: This is a test annotation",
                font_size=2.5,
            ),
            create_mock_annotation(
                text="TITLE BLOCK",
                font_size=5.0,
            ),
        ]
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Mock other responses
        mock_geometry_response = Mock()
        mock_geometry_response.geometry = None
        mock_client.extract_geometry.return_value = mock_geometry_response

        mock_metadata_response = Mock()
        mock_metadata_response.metadata = None
        mock_client.extract_metadata.return_value = mock_metadata_response

        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = None
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        # Execute
        result = coscad_extractor.parse(sample_coscad_file)

        # Verify
        assert result.success is True
        assert len(result.text_blocks) == 2

        # Check first annotation
        text1 = result.text_blocks[0]
        assert isinstance(text1, ExtractedText)
        assert text1.text == "NOTE: This is a test annotation"
        assert text1.font_size == 2.5

        # Check second annotation
        text2 = result.text_blocks[1]
        assert isinstance(text2, ExtractedText)
        assert text2.text == "TITLE BLOCK"
        assert text2.font_size == 5.0


# =============================================================================
# Metadata Extraction Tests
# =============================================================================


class TestCosCADMetadataExtraction:
    """Test metadata extraction from CosCAD files."""

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_extract_metadata_basic(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test basic metadata extraction."""
        # Setup mock response
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_metadata_response = Mock()
        mock_metadata_response.metadata = create_mock_metadata(
            author="Test Author",
            title="Test Drawing",
            drawing_number="DWG-001",
            revision="A",
            custom_properties={"project": "Test Project", "material": "Aluminum"},
        )
        mock_metadata_response.title_block = None
        mock_client.extract_metadata.return_value = mock_metadata_response

        # Mock other responses
        mock_geometry_response = Mock()
        mock_geometry_response.geometry = None
        mock_client.extract_geometry.return_value = mock_geometry_response

        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = None
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        mock_annotations_response = Mock()
        mock_annotations_response.annotations = None
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Execute
        result = coscad_extractor.parse(sample_coscad_file)

        # Verify
        assert result.success is True
        assert result.metadata is not None
        assert result.metadata.get("author") == "Test Author"
        assert result.metadata.get("title") == "Test Drawing"
        assert result.metadata.get("drawing_number") == "DWG-001"
        assert result.metadata.get("revision") == "A"
        assert result.metadata.get("custom_properties") == {
            "project": "Test Project",
            "material": "Aluminum",
        }

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_extract_title_block(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test title block extraction from metadata."""
        # Setup mock response
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_title_block = create_mock_title_block(
            drawing_number="DWG-12345",
            title="Aerospace Bracket Assembly",
            revision="C",
            date="2024-01-15",
            author="John Doe",
            company="Acme Aerospace",
            scale="1:1",
            sheet="1 of 2",
            material="7075-T6 Aluminum",
            finish="Anodized",
        )

        mock_metadata_response = Mock()
        mock_metadata_response.metadata = create_mock_metadata()  # Set some metadata so title_block is processed
        mock_metadata_response.title_block = mock_title_block
        mock_client.extract_metadata.return_value = mock_metadata_response

        # Mock other responses
        mock_geometry_response = Mock()
        mock_geometry_response.geometry = None
        mock_client.extract_geometry.return_value = mock_geometry_response

        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = None
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        mock_annotations_response = Mock()
        mock_annotations_response.annotations = None
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Execute
        result = coscad_extractor.parse(sample_coscad_file)

        # Verify
        assert result.success is True
        assert result.title_block is not None
        assert isinstance(result.title_block, ExtractedTitleBlock)
        assert result.title_block.drawing_number == "DWG-12345"
        assert result.title_block.title == "Aerospace Bracket Assembly"
        assert result.title_block.revision == "C"
        assert result.title_block.date == "2024-01-15"
        assert result.title_block.author == "John Doe"
        assert result.title_block.company == "Acme Aerospace"
        assert result.title_block.scale == "1:1"
        assert result.title_block.sheet == "1 of 2"
        assert result.title_block.material == "7075-T6 Aluminum"
        assert result.title_block.finish == "Anodized"


# =============================================================================
# Selective Extraction Tests
# =============================================================================


class TestCosCADSelectiveExtraction:
    """Test selective extraction (geometry/dimensions/annotations/metadata flags)."""

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_extract_geometry_only(
        self, mock_client_class: Mock, sample_coscad_file: Path
    ) -> None:
        """Test extraction with geometry only (dimensions/annotations/metadata disabled)."""
        # Setup mock response
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_geometry_response = Mock()
        mock_geometry_response.geometry = create_mock_geometry(num_faces=5, num_edges=10, num_vertices=8, num_surfaces=3, num_solids=1)
        mock_client.extract_geometry.return_value = mock_geometry_response

        # Create extractor with geometry only
        extractor = CosCADExtractor(
            extract_geometry=True,
            extract_dimensions=False,
            extract_annotations=False,
            extract_metadata=False,
        )

        # Execute
        result = extractor.parse(sample_coscad_file)

        # Verify
        assert result.success is True
        assert len(result.layers) > 0
        assert result.geometry_summary is not None
        assert len(result.dimensions) == 0  # Dimensions not extracted
        assert len(result.text_blocks) == 0  # Annotations not extracted
        assert result.metadata == {}  # Metadata not extracted (empty dict)

        # Verify only geometry method was called
        mock_client.extract_geometry.assert_called_once()
        mock_client.extract_dimensions.assert_not_called()
        mock_client.extract_annotations.assert_not_called()
        mock_client.extract_metadata.assert_not_called()

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_extract_dimensions_only(
        self, mock_client_class: Mock, sample_coscad_file: Path
    ) -> None:
        """Test extraction with dimensions only."""
        # Setup mock response
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = [
            create_mock_dimension(value=10.0, unit="mm"),
        ]
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        # Mock geometry response (returns None)
        mock_geometry_response = Mock()
        mock_geometry_response.geometry = None
        mock_client.extract_geometry.return_value = mock_geometry_response

        # Mock metadata response (returns None)
        mock_metadata_response = Mock()
        mock_metadata_response.metadata = None
        mock_client.extract_metadata.return_value = mock_metadata_response

        # Mock annotations response (returns None)
        mock_annotations_response = Mock()
        mock_annotations_response.annotations = None
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Create extractor with dimensions only
        extractor = CosCADExtractor(
            extract_geometry=False,
            extract_dimensions=True,
            extract_annotations=False,
            extract_metadata=False,
        )

        # Execute
        result = extractor.parse(sample_coscad_file)

        # Verify
        assert result.success is True
        assert len(result.dimensions) == 1
        assert len(result.layers) == 0  # Geometry not extracted
        assert len(result.text_blocks) == 0  # Annotations not extracted
        assert result.metadata == {}  # Metadata not extracted (empty dict)

        # Verify only dimensions method was called
        mock_client.extract_geometry.assert_not_called()
        mock_client.extract_dimensions.assert_called_once()
        mock_client.extract_annotations.assert_not_called()
        mock_client.extract_metadata.assert_not_called()


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestCosCADErrorHandling:
    """Test error handling in CosCAD extraction."""

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_geometry_extraction_error(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test handling of geometry extraction errors."""
        # Setup mock to raise exception
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.extract_geometry.side_effect = Exception("Geometry extraction failed")

        # Mock other responses
        mock_metadata_response = Mock()
        mock_metadata_response.metadata = None
        mock_client.extract_metadata.return_value = mock_metadata_response

        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = None
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        mock_annotations_response = Mock()
        mock_annotations_response.annotations = None
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Execute
        result = coscad_extractor.parse(sample_coscad_file)

        # Verify error was captured
        assert result.success is False  # Errors present, so success is False
        assert len(result.errors) == 1
        assert "Geometry extraction error" in result.errors[0]
        assert len(result.layers) == 0
        assert result.geometry_summary is None

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_dimension_extraction_error(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test handling of dimension extraction errors."""
        # Setup mock to raise exception
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.extract_dimensions.side_effect = Exception("Dimension extraction failed")

        # Mock other responses
        mock_geometry_response = Mock()
        mock_geometry_response.geometry = create_mock_geometry(num_faces=5, num_edges=10)
        mock_client.extract_geometry.return_value = mock_geometry_response

        mock_metadata_response = Mock()
        mock_metadata_response.metadata = None
        mock_client.extract_metadata.return_value = mock_metadata_response

        mock_annotations_response = Mock()
        mock_annotations_response.annotations = None
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Execute
        result = coscad_extractor.parse(sample_coscad_file)

        # Verify error was captured
        assert result.success is False  # Errors present
        assert len(result.errors) == 1
        assert "Dimensions extraction error" in result.errors[0]
        assert len(result.dimensions) == 0

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_annotation_extraction_error(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test handling of annotation extraction errors."""
        # Setup mock to raise exception
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.extract_annotations.side_effect = Exception("Annotation extraction failed")

        # Mock other responses
        mock_geometry_response = Mock()
        mock_geometry_response.geometry = None
        mock_client.extract_geometry.return_value = mock_geometry_response

        mock_metadata_response = Mock()
        mock_metadata_response.metadata = None
        mock_client.extract_metadata.return_value = mock_metadata_response

        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = None
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        # Execute
        result = coscad_extractor.parse(sample_coscad_file)

        # Verify error was captured
        assert result.success is False  # Errors present
        assert len(result.errors) == 1
        assert "Annotations extraction error" in result.errors[0]
        assert len(result.text_blocks) == 0

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_metadata_extraction_error(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test handling of metadata extraction errors."""
        # Setup mock to raise exception
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.extract_metadata.side_effect = Exception("Metadata extraction failed")

        # Mock other responses
        mock_geometry_response = Mock()
        mock_geometry_response.geometry = None
        mock_client.extract_geometry.return_value = mock_geometry_response

        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = None
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        mock_annotations_response = Mock()
        mock_annotations_response.annotations = None
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Execute
        result = coscad_extractor.parse(sample_coscad_file)

        # Verify error was captured
        assert result.success is False  # Errors present
        assert len(result.errors) == 1
        assert "Metadata extraction error" in result.errors[0]
        assert result.metadata == {}  # Empty dict (default value)

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_multiple_extraction_errors(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test handling of multiple extraction errors simultaneously."""
        # Setup mock to raise exceptions
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.extract_geometry.side_effect = Exception("Geometry failed")
        mock_client.extract_dimensions.side_effect = Exception("Dimensions failed")
        mock_client.extract_metadata.side_effect = Exception("Metadata failed")

        # Mock only annotations to succeed
        mock_annotations_response = Mock()
        mock_annotations_response.annotations = [
            create_mock_annotation(text="Only annotation extracted"),
        ]
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Execute
        result = coscad_extractor.parse(sample_coscad_file)

        # Verify all errors were captured
        assert result.success is False  # Errors present
        assert len(result.errors) == 3
        assert any("Geometry" in e for e in result.errors)
        assert any("Dimensions" in e for e in result.errors)
        assert any("Metadata" in e for e in result.errors)
        assert len(result.text_blocks) == 1  # Annotations still extracted


# =============================================================================
# Override Extraction Flags Tests
# =============================================================================


class TestCosCADOverrideFlags:
    """Test overriding extraction flags at parse() time."""

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_parse_time_override_disable_geometry(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test disabling geometry extraction at parse time via parameter."""
        # Setup mock response
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = [
            create_mock_dimension(value=10.0, unit="mm"),
        ]
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        # Mock other responses
        mock_geometry_response = Mock()
        mock_geometry_response.geometry = None
        mock_client.extract_geometry.return_value = mock_geometry_response

        mock_metadata_response = Mock()
        mock_metadata_response.metadata = None
        mock_client.extract_metadata.return_value = mock_metadata_response

        mock_annotations_response = Mock()
        mock_annotations_response.annotations = None
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Execute with geometry disabled at parse time
        result = coscad_extractor.parse(sample_coscad_file, extract_geometry=False)

        # Verify geometry was not extracted but dimensions were
        assert len(result.layers) == 0
        assert len(result.dimensions) == 1

        # Verify geometry method was not called
        mock_client.extract_geometry.assert_not_called()
        mock_client.extract_dimensions.assert_called_once()

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_parse_time_override_enable_only_metadata(
        self, mock_client_class: Mock, sample_coscad_file: Path
    ) -> None:
        """Test enabling only metadata extraction at parse time."""
        # Setup mock response
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_metadata_response = Mock()
        mock_metadata_response.metadata = create_mock_metadata(
            author="Test Author",
            title="Test",
        )
        mock_metadata_response.title_block = None
        mock_client.extract_metadata.return_value = mock_metadata_response

        # Mock other responses
        mock_geometry_response = Mock()
        mock_geometry_response.geometry = None
        mock_client.extract_geometry.return_value = mock_geometry_response

        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = None
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        mock_annotations_response = Mock()
        mock_annotations_response.annotations = None
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Create extractor with all disabled
        extractor = CosCADExtractor(
            extract_geometry=False,
            extract_dimensions=False,
            extract_annotations=False,
            extract_metadata=False,
        )

        # Execute with only metadata enabled at parse time
        result = extractor.parse(
            sample_coscad_file,
            extract_geometry=False,
            extract_dimensions=False,
            extract_annotations=False,
            extract_metadata=True,
        )

        # Verify only metadata was extracted
        assert result.metadata is not None
        assert len(result.layers) == 0
        assert len(result.dimensions) == 0
        assert len(result.text_blocks) == 0

        # Verify only metadata method was called
        mock_client.extract_geometry.assert_not_called()
        mock_client.extract_dimensions.assert_not_called()
        mock_client.extract_annotations.assert_not_called()
        mock_client.extract_metadata.assert_called_once()


# =============================================================================
# Comprehensive Integration Test
# =============================================================================


class TestCosCADComprehensiveIntegration:
    """Comprehensive integration test with all extraction types."""

    @patch("pybase.extraction.cad.coscad.CosCADClient")
    def test_full_extraction(
        self, mock_client_class: Mock, coscad_extractor: CosCADExtractor, sample_coscad_file: Path
    ) -> None:
        """Test comprehensive extraction with all data types."""
        # Setup mock responses
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Geometry
        mock_geometry_response = Mock()
        mock_geometry_response.geometry = create_mock_geometry(
            num_faces=100,
            num_edges=200,
            num_vertices=150,
            num_surfaces=50,
            num_solids=10,
        )
        mock_client.extract_geometry.return_value = mock_geometry_response

        # Dimensions
        mock_dimensions_response = Mock()
        mock_dimensions_response.dimensions = [
            create_mock_dimension(
                value=100.0,
                unit="mm",
                dimension_type="linear",
                tolerance_plus=0.1,
                tolerance_minus=0.05,
                label="OVERALL_LENGTH",
            ),
            create_mock_dimension(
                value=50.0,
                unit="mm",
                dimension_type="linear",
                tolerance_plus=0.05,
                tolerance_minus=None,
                label="WIDTH",
            ),
            create_mock_dimension(
                value=25.0,
                unit="mm",
                dimension_type="diameter",
                tolerance_plus=0.02,
                tolerance_minus=0.01,
                label="BORE_DIA",
            ),
            create_mock_dimension(
                value=45.0,
                unit="mm",  # Angular dims use linear unit in CosCAD, converted by dimension_type
                dimension_type="angular",
                tolerance_plus=0.5,
                tolerance_minus=0.5,
                label="ANGLE",
            ),
        ]
        mock_client.extract_dimensions.return_value = mock_dimensions_response

        # Annotations
        mock_annotations_response = Mock()
        mock_annotations_response.annotations = [
            create_mock_annotation(
                text="NOTE: All dimensions in millimeters",
                font_size=2.0,
            ),
            create_mock_annotation(
                text="TOLERANCES: ±0.1mm unless specified",
                font_size=1.5,
            ),
            create_mock_annotation(
                text="MATERIAL: 6061-T6 ALUMINUM",
                font_size=2.5,
            ),
        ]
        mock_client.extract_annotations.return_value = mock_annotations_response

        # Metadata
        mock_title_block = create_mock_title_block(
            drawing_number="ASM-2024-001",
            title="Aerospace Bracket Assembly",
            revision="B",
            date="2024-01-20",
            author="Jane Engineer",
            company="Aerospace Corp",
            scale="1:1",
            sheet="1 of 1",
            material="6061-T6",
            finish="Anodized Clear",
        )

        mock_metadata_response = Mock()
        mock_metadata_response.metadata = create_mock_metadata(
            author="Jane Engineer",
            title="Aerospace Bracket Assembly",
            drawing_number="ASM-2024-001",
            revision="B",
            custom_properties={
                "project": "X-15 Program",
                "material": "6061-T6 Aluminum",
                "finish": "Anodized",
            },
        )
        mock_metadata_response.title_block = mock_title_block
        mock_client.extract_metadata.return_value = mock_metadata_response

        # Execute
        result = coscad_extractor.parse(sample_coscad_file)

        # Verify comprehensive result
        assert result.success is True
        assert len(result.errors) == 0
        assert result.source_type == "coscad"

        # Verify geometry
        assert len(result.layers) == 5
        assert result.geometry_summary is not None
        assert result.geometry_summary.solids == 10
        assert result.geometry_summary.total_entities == 510

        # Verify dimensions
        assert len(result.dimensions) == 4
        assert all(isinstance(d, ExtractedDimension) for d in result.dimensions)

        # Check linear dimension
        linear_dim = [d for d in result.dimensions if d.dimension_type == "linear"][0]
        assert linear_dim.value == 100.0
        assert linear_dim.unit == "mm"
        assert linear_dim.label == "OVERALL_LENGTH"

        # Check diameter dimension
        diameter_dim = [d for d in result.dimensions if d.dimension_type == "diameter"][0]
        assert diameter_dim.value == 25.0

        # Check angular dimension
        angular_dim = [d for d in result.dimensions if d.dimension_type == "angular"][0]
        assert angular_dim.value == 45.0
        assert angular_dim.unit == "degree"

        # Verify annotations
        assert len(result.text_blocks) == 3
        assert all(isinstance(t, ExtractedText) for t in result.text_blocks)
        assert any("All dimensions in millimeters" in t.text for t in result.text_blocks)
        assert any("6061-T6 ALUMINUM" in t.text for t in result.text_blocks)

        # Verify metadata
        assert result.metadata is not None
        assert result.metadata.get("author") == "Jane Engineer"
        assert result.metadata.get("drawing_number") == "ASM-2024-001"
        assert result.metadata.get("custom_properties") == {
            "project": "X-15 Program",
            "material": "6061-T6 Aluminum",
            "finish": "Anodized",
        }

        # Verify title block
        assert result.title_block is not None
        assert result.title_block.drawing_number == "ASM-2024-001"
        assert result.title_block.title == "Aerospace Bracket Assembly"
        assert result.title_block.author == "Jane Engineer"
        assert result.title_block.material == "6061-T6"
        assert result.title_block.finish == "Anodized Clear"

        # Verify all client methods were called once
        mock_client.extract_metadata.assert_called_once()
        mock_client.extract_geometry.assert_called_once()
        mock_client.extract_dimensions.assert_called_once()
        mock_client.extract_annotations.assert_called_once()
