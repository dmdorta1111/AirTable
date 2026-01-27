"""
Pytest configuration and fixtures for CAD extraction tests.

Provides fixtures for testing DXF, IFC, and STEP file parsing including:
- Parser instances
- Sample CAD files
- Temporary directories for test files
- Helper utilities for extraction testing
- ExtractionJob model and service fixtures
"""

import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.extraction.base import CADExtractionResult
from pybase.extraction.cad.dxf import EZDXF_AVAILABLE, DXFParser
from pybase.models.extraction_job import (
    ExtractionJob,
    ExtractionFormat,
    ExtractionJobStatus,
)
from pybase.services.extraction_job_service import ExtractionJobService

# Try to import parsers (they may not be available without optional dependencies)
try:
    from pybase.extraction.cad.ifc import IFCOPENSHELL_AVAILABLE, IFCParser
except ImportError:
    IFCOPENSHELL_AVAILABLE = False
    IFCParser = None  # type: ignore

try:
    from pybase.extraction.cad.step import (
        CADQUERY_AVAILABLE,
        OCP_AVAILABLE,
        STEPParser,
    )
except ImportError:
    CADQUERY_AVAILABLE = False
    OCP_AVAILABLE = False
    STEPParser = None  # type: ignore


@pytest.fixture(scope="session")
def temp_cad_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for CAD test files."""
    with tempfile.TemporaryDirectory(prefix="pybase_cad_test_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Path to the fixtures directory for test CAD files."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def dxf_fixtures_dir(fixtures_dir: Path) -> Path:
    """Path to DXF test fixtures directory."""
    dxf_dir = fixtures_dir / "dxf"
    dxf_dir.mkdir(parents=True, exist_ok=True)
    return dxf_dir


@pytest.fixture(scope="session")
def ifc_fixtures_dir(fixtures_dir: Path) -> Path:
    """Path to IFC test fixtures directory."""
    ifc_dir = fixtures_dir / "ifc"
    ifc_dir.mkdir(parents=True, exist_ok=True)
    return ifc_dir


@pytest.fixture(scope="session")
def step_fixtures_dir(fixtures_dir: Path) -> Path:
    """Path to STEP test fixtures directory."""
    step_dir = fixtures_dir / "step"
    step_dir.mkdir(parents=True, exist_ok=True)
    return step_dir


@pytest.fixture
def dxf_parser() -> DXFParser | None:
    """Create a DXF parser instance if ezdxf is available."""
    if not EZDXF_AVAILABLE:
        pytest.skip("ezdxf not available")
    return DXFParser(
        extract_layers=True,
        extract_blocks=True,
        extract_dimensions=True,
        extract_text=True,
        extract_title_block=True,
        extract_geometry=True,
    )


@pytest.fixture
def ifc_parser() -> Any:
    """Create an IFC parser instance if ifcopenshell is available."""
    if not IFCOPENSHELL_AVAILABLE or IFCParser is None:
        pytest.skip("ifcopenshell not available")
    return IFCParser()


@pytest.fixture
def step_parser() -> Any:
    """Create a STEP parser instance if OCP or cadquery is available."""
    if (not OCP_AVAILABLE and not CADQUERY_AVAILABLE) or STEPParser is None:
        pytest.skip("OCP or cadquery not available")
    return STEPParser()


@pytest.fixture
def simple_dxf_path(dxf_fixtures_dir: Path, temp_cad_dir: Path) -> Path:
    """Path to a simple DXF test file (created on demand)."""
    # First check if fixture exists
    fixture_path = dxf_fixtures_dir / "simple_drawing.dxf"
    if fixture_path.exists():
        return fixture_path

    # Otherwise create in temp directory
    temp_path = temp_cad_dir / "simple_drawing.dxf"
    if not temp_path.exists() and EZDXF_AVAILABLE:
        import ezdxf

        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        # Add a simple line
        msp.add_line((0, 0), (10, 10))

        # Add text
        msp.add_text("Test Drawing", dxfattribs={"height": 2.5})

        # Add a circle
        msp.add_circle((5, 5), radius=3)

        doc.saveas(temp_path)

    return temp_path


@pytest.fixture
def dimensions_dxf_path(dxf_fixtures_dir: Path, temp_cad_dir: Path) -> Path:
    """Path to a DXF file with various dimension types."""
    fixture_path = dxf_fixtures_dir / "dimensions_various.dxf"
    if fixture_path.exists():
        return fixture_path

    temp_path = temp_cad_dir / "dimensions_various.dxf"
    if not temp_path.exists() and EZDXF_AVAILABLE:
        import ezdxf

        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        # Add geometry with dimensions
        # Rectangle
        msp.add_lwpolyline([(0, 0), (10, 0), (10, 5), (0, 5), (0, 0)])

        # Linear dimension
        dim = msp.add_linear_dim(
            base=(5, -2),
            p1=(0, 0),
            p2=(10, 0),
            dimstyle="EZDXF",
        )

        # Aligned dimension
        msp.add_aligned_dim(
            p1=(10, 0),
            p2=(10, 5),
            distance=2,
            dimstyle="EZDXF",
        )

        # Radius dimension
        circle = msp.add_circle((15, 2.5), radius=2)
        msp.add_radius_dim(
            center=(15, 2.5),
            radius=2,
            angle=45,
            dimstyle="EZDXF",
        )

        doc.saveas(temp_path)

    return temp_path


@pytest.fixture
def text_dxf_path(dxf_fixtures_dir: Path, temp_cad_dir: Path) -> Path:
    """Path to a DXF file with various text entities."""
    fixture_path = dxf_fixtures_dir / "text_formatting.dxf"
    if fixture_path.exists():
        return fixture_path

    temp_path = temp_cad_dir / "text_formatting.dxf"
    if not temp_path.exists() and EZDXF_AVAILABLE:
        import ezdxf

        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        # Regular TEXT
        msp.add_text("Simple Text", dxfattribs={"height": 1.0}).set_placement((0, 0))

        # Large title text
        msp.add_text("DRAWING TITLE", dxfattribs={"height": 5.0}).set_placement((0, 5))

        # MTEXT with formatting
        msp.add_mtext(
            "Multi-line text\\Pwith paragraph\\Pand formatting",
            dxfattribs={"char_height": 1.5, "width": 20},
        ).set_location((0, 10))

        # Small annotation text
        msp.add_text("Note: Small annotation", dxfattribs={"height": 0.5}).set_placement((0, 15))

        doc.saveas(temp_path)

    return temp_path


@pytest.fixture
def blocks_dxf_path(dxf_fixtures_dir: Path, temp_cad_dir: Path) -> Path:
    """Path to a DXF file with block definitions and inserts."""
    fixture_path = dxf_fixtures_dir / "nested_blocks.dxf"
    if fixture_path.exists():
        return fixture_path

    temp_path = temp_cad_dir / "nested_blocks.dxf"
    if not temp_path.exists() and EZDXF_AVAILABLE:
        import ezdxf

        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        # Create a simple block
        block = doc.blocks.new(name="MARKER")
        block.add_circle((0, 0), radius=0.5)
        block.add_line((-1, 0), (1, 0))
        block.add_line((0, -1), (0, 1))

        # Create block with attributes
        block_with_attrib = doc.blocks.new(name="PART")
        block_with_attrib.add_circle((0, 0), radius=1)
        block_with_attrib.add_attdef(
            tag="PART_NUMBER", text="P-001", insert=(0, -1.5), dxfattribs={"height": 0.5}
        )
        block_with_attrib.add_attdef(
            tag="DESCRIPTION", text="Part Description", insert=(0, -2.0), dxfattribs={"height": 0.3}
        )

        # Insert blocks
        msp.add_blockref("MARKER", (0, 0))
        msp.add_blockref("MARKER", (10, 10))
        msp.add_blockref("MARKER", (20, 0))

        # Insert block with attributes
        insert = msp.add_blockref(
            "PART",
            (5, 5),
            dxfattribs={
                "xscale": 1.5,
                "yscale": 1.5,
            },
        )
        insert.add_attrib("PART_NUMBER", "P-123")
        insert.add_attrib("DESCRIPTION", "Test Part")

        doc.saveas(temp_path)

    return temp_path


@pytest.fixture
def simple_ifc_path(ifc_fixtures_dir: Path) -> Path:
    """Path to a simple IFC test file."""
    # This will be created in phase 2
    return ifc_fixtures_dir / "simple_building.ifc"


@pytest.fixture
def simple_step_path(step_fixtures_dir: Path) -> Path:
    """Path to a simple STEP test file."""
    # This will be created in phase 2
    return step_fixtures_dir / "simple_part.step"


@pytest.fixture
def large_dxf_path(dxf_fixtures_dir: Path, temp_cad_dir: Path) -> Path:
    """Path to a large DXF file (~1MB) for performance testing."""
    fixture_path = dxf_fixtures_dir / "large_performance_test.dxf"
    if fixture_path.exists():
        return fixture_path

    temp_path = temp_cad_dir / "large_performance_test.dxf"
    if not temp_path.exists() and EZDXF_AVAILABLE:
        import ezdxf

        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        # Create a large drawing with many entities to reach ~1MB
        # Add multiple layers with different entity types
        for layer_num in range(20):
            layer_name = f"LAYER_{layer_num:02d}"
            doc.layers.add(layer_name)

            # Add lines (100 per layer)
            for i in range(100):
                x1, y1 = i * 10, layer_num * 100
                x2, y2 = x1 + 8, y1 + 8
                msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": layer_name})

            # Add circles (50 per layer)
            for i in range(50):
                cx, cy = i * 15, layer_num * 100 + 50
                radius = 2 + (i % 5)
                msp.add_circle((cx, cy), radius=radius, dxfattribs={"layer": layer_name})

            # Add polylines (30 per layer)
            for i in range(30):
                start_x, start_y = i * 20, layer_num * 100 + 75
                points = [
                    (start_x, start_y),
                    (start_x + 5, start_y + 5),
                    (start_x + 10, start_y),
                    (start_x + 15, start_y + 7),
                    (start_x, start_y),
                ]
                msp.add_lwpolyline(points, dxfattribs={"layer": layer_name})

            # Add text (40 per layer)
            for i in range(40):
                tx, ty = i * 12, layer_num * 100 + 25
                text = f"Layer {layer_name} Text {i:03d} - Sample annotation text"
                msp.add_text(text, dxfattribs={"height": 1.5, "layer": layer_name}).set_placement(
                    (tx, ty)
                )

            # Add dimensions (10 per layer)
            for i in range(10):
                base_x = i * 25
                base_y = layer_num * 100 + 90
                msp.add_linear_dim(
                    base=(base_x + 12.5, base_y - 2),
                    p1=(base_x, base_y),
                    p2=(base_x + 25, base_y),
                    dimstyle="EZDXF",
                    dxfattribs={"layer": layer_name},
                )

        # Add some blocks with multiple inserts
        for block_num in range(10):
            block_name = f"COMPONENT_{block_num:02d}"
            block = doc.blocks.new(name=block_name)

            # Add entities to block
            block.add_circle((0, 0), radius=5)
            block.add_line((-5, 0), (5, 0))
            block.add_line((0, -5), (0, 5))
            block.add_text(f"BLK{block_num}", dxfattribs={"height": 2})

            # Insert block multiple times
            for i in range(50):
                x, y = (i % 10) * 30, (i // 10) * 30 + 2000
                msp.add_blockref(
                    block_name,
                    (x, y),
                    dxfattribs={
                        "xscale": 0.8 + (i % 5) * 0.1,
                        "yscale": 0.8 + (i % 5) * 0.1,
                        "rotation": (i * 15) % 360,
                    },
                )

        doc.saveas(temp_path)

    return temp_path


@pytest.fixture
def assert_extraction_valid() -> Any:
    """Helper fixture to validate extraction results."""

    def _assert_valid(result: CADExtractionResult) -> None:
        """Assert that an extraction result is valid."""
        assert result is not None
        assert isinstance(result, CADExtractionResult)
        assert result.source_file is not None
        assert result.source_type in ("dxf", "ifc", "step")
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)

    return _assert_valid


@pytest.fixture
def assert_dxf_dimensions_valid() -> Any:
    """Helper fixture to validate DXF dimension extraction."""

    def _assert_valid(dimensions: list, expected_count: int | None = None) -> None:
        """Assert that extracted dimensions are valid."""
        assert isinstance(dimensions, list)
        if expected_count is not None:
            assert len(dimensions) >= expected_count, (
                f"Expected at least {expected_count} dimensions"
            )

        for dim in dimensions:
            assert dim.value is not None
            assert isinstance(dim.value, (int, float))
            assert dim.unit is not None
            assert dim.dimension_type in (
                "linear",
                "aligned",
                "angular",
                "radius",
                "diameter",
                "angular3point",
                "ordinate",
            )
            assert 0.0 <= dim.confidence <= 1.0

    return _assert_valid


@pytest.fixture
def assert_dxf_text_valid() -> Any:
    """Helper fixture to validate DXF text extraction."""

    def _assert_valid(text_blocks: list, expected_count: int | None = None) -> None:
        """Assert that extracted text blocks are valid."""
        assert isinstance(text_blocks, list)
        if expected_count is not None:
            assert len(text_blocks) >= expected_count, (
                f"Expected at least {expected_count} text blocks"
            )

        for text in text_blocks:
            assert text.text is not None
            assert isinstance(text.text, str)
            assert len(text.text) > 0
            assert 0.0 <= text.confidence <= 1.0

    return _assert_valid


@pytest.fixture
def assert_dxf_blocks_valid() -> Any:
    """Helper fixture to validate DXF block extraction."""

    def _assert_valid(blocks: list, expected_count: int | None = None) -> None:
        """Assert that extracted blocks are valid."""
        assert isinstance(blocks, list)
        if expected_count is not None:
            assert len(blocks) >= expected_count, f"Expected at least {expected_count} blocks"

        for block in blocks:
            assert block.name is not None
            assert isinstance(block.name, str)
            assert block.insert_count >= 0
            assert block.entity_count >= 0

    return _assert_valid


@pytest.fixture
def assert_dxf_layers_valid() -> Any:
    """Helper fixture to validate DXF layer extraction."""

    def _assert_valid(layers: list, expected_count: int | None = None) -> None:
        """Assert that extracted layers are valid."""
        assert isinstance(layers, list)
        if expected_count is not None:
            assert len(layers) >= expected_count, f"Expected at least {expected_count} layers"

        for layer in layers:
            assert layer.name is not None
            assert isinstance(layer.name, str)
            assert isinstance(layer.is_on, bool)
            assert isinstance(layer.is_frozen, bool)
            assert isinstance(layer.is_locked, bool)
            assert layer.entity_count >= 0

    return _assert_valid


@pytest.fixture
def assert_step_assembly_valid() -> Any:
    """Helper fixture to validate STEP assembly structure."""

    def _assert_valid(assembly: Any, expected_parts: int | None = None) -> None:
        """Assert that STEP assembly structure is valid."""
        assert assembly is not None, "Assembly should not be None"
        assert hasattr(assembly, "parts"), "Assembly should have parts attribute"
        assert hasattr(assembly, "total_parts"), "Assembly should have total_parts attribute"
        assert hasattr(assembly, "root_parts"), "Assembly should have root_parts attribute"
        assert isinstance(assembly.parts, list), "Parts should be a list"
        assert isinstance(assembly.total_parts, int), "Total parts should be an integer"
        assert isinstance(assembly.root_parts, list), "Root parts should be a list"

        # Validate total_parts matches actual parts count
        assert assembly.total_parts == len(assembly.parts), (
            f"Total parts ({assembly.total_parts}) should match parts list length ({len(assembly.parts)})"
        )

        # Validate expected count if provided
        if expected_parts is not None:
            assert len(assembly.parts) == expected_parts, (
                f"Expected {expected_parts} parts, got {len(assembly.parts)}"
            )

    return _assert_valid


@pytest.fixture
def assert_step_part_valid() -> Any:
    """Helper fixture to validate STEP part metadata."""

    def _assert_valid(part: Any, check_geometry: bool = True) -> None:
        """Assert that STEP part metadata is valid."""
        assert part is not None, "Part should not be None"

        # Basic metadata
        assert hasattr(part, "name"), "Part should have name attribute"
        assert hasattr(part, "part_id"), "Part should have part_id attribute"
        assert hasattr(part, "shape_type"), "Part should have shape_type attribute"
        assert part.shape_type in ("SOLID", "SHELL", "COMPOUND", "unknown"), (
            f"Invalid shape type: {part.shape_type}"
        )

        # Topology counts (should be non-negative integers)
        assert hasattr(part, "num_faces"), "Part should have num_faces attribute"
        assert hasattr(part, "num_edges"), "Part should have num_edges attribute"
        assert hasattr(part, "num_vertices"), "Part should have num_vertices attribute"
        assert isinstance(part.num_faces, int) and part.num_faces >= 0, (
            f"num_faces should be non-negative integer, got {part.num_faces}"
        )
        assert isinstance(part.num_edges, int) and part.num_edges >= 0, (
            f"num_edges should be non-negative integer, got {part.num_edges}"
        )
        assert isinstance(part.num_vertices, int) and part.num_vertices >= 0, (
            f"num_vertices should be non-negative integer, got {part.num_vertices}"
        )

        # Geometry metadata (optional, but if present should be valid)
        if check_geometry:
            assert hasattr(part, "bbox"), "Part should have bbox attribute"
            assert hasattr(part, "volume"), "Part should have volume attribute"
            assert hasattr(part, "surface_area"), "Part should have surface_area attribute"
            assert hasattr(part, "center_of_mass"), "Part should have center_of_mass attribute"

            # If bbox exists, validate it
            if part.bbox is not None:
                assert isinstance(part.bbox, tuple) and len(part.bbox) == 6, (
                    f"Bounding box should be a 6-tuple, got {type(part.bbox)}"
                )
                xmin, ymin, zmin, xmax, ymax, zmax = part.bbox
                assert xmax >= xmin, f"xmax ({xmax}) should be >= xmin ({xmin})"
                assert ymax >= ymin, f"ymax ({ymax}) should be >= ymin ({ymin})"
                assert zmax >= zmin, f"zmax ({zmax}) should be >= zmin ({zmin})"

            # If volume exists, validate it
            if part.volume is not None:
                assert isinstance(part.volume, (int, float)), (
                    f"Volume should be numeric, got {type(part.volume)}"
                )
                assert part.volume >= 0, f"Volume should be non-negative, got {part.volume}"

            # If surface_area exists, validate it
            if part.surface_area is not None:
                assert isinstance(part.surface_area, (int, float)), (
                    f"Surface area should be numeric, got {type(part.surface_area)}"
                )
                assert part.surface_area >= 0, (
                    f"Surface area should be non-negative, got {part.surface_area}"
                )

            # If center_of_mass exists, validate it
            if part.center_of_mass is not None:
                assert isinstance(part.center_of_mass, tuple) and len(part.center_of_mass) == 3, (
                    f"Center of mass should be a 3-tuple, got {type(part.center_of_mass)}"
                )

        # Hierarchy metadata
        assert hasattr(part, "children"), "Part should have children attribute"
        assert hasattr(part, "properties"), "Part should have properties attribute"
        assert isinstance(part.children, list), "Children should be a list"
        assert isinstance(part.properties, dict), "Properties should be a dictionary"

        # Visual metadata (optional)
        assert hasattr(part, "color"), "Part should have color attribute"
        assert hasattr(part, "material"), "Part should have material attribute"
        if part.color is not None:
            assert isinstance(part.color, tuple) and len(part.color) == 3, (
                f"Color should be RGB 3-tuple, got {type(part.color)}"
            )

    return _assert_valid


# =============================================================================
# ExtractionJob Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def extraction_job_service(db_session: AsyncSession) -> ExtractionJobService:
    """Create an ExtractionJobService instance with test database session."""
    return ExtractionJobService(db_session)


@pytest_asyncio.fixture
async def sample_extraction_job(db_session: AsyncSession) -> ExtractionJob:
    """Create a sample extraction job for testing."""
    job = ExtractionJob(
        id=str(uuid4()),
        filename="test_drawing.pdf",
        file_url="extraction-jobs/test123/test_drawing.pdf",
        file_size=1024000,
        format=ExtractionFormat.PDF.value,
        status=ExtractionJobStatus.PENDING.value,
        max_retries=3,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def completed_extraction_job(db_session: AsyncSession) -> ExtractionJob:
    """Create a completed extraction job with results."""
    from datetime import datetime, timezone

    job = ExtractionJob(
        id=str(uuid4()),
        filename="completed_drawing.dxf",
        file_url="extraction-jobs/test456/completed_drawing.dxf",
        file_size=512000,
        format=ExtractionFormat.DXF.value,
        status=ExtractionJobStatus.COMPLETED.value,
        max_retries=3,
    )
    job.set_result(
        {
            "success": True,
            "layers": [{"name": "0", "entity_count": 10}],
            "dimensions": [],
            "text_blocks": [],
        }
    )
    job.started_at = datetime.now(timezone.utc)
    job.completed_at = datetime.now(timezone.utc)

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def failed_extraction_job(db_session: AsyncSession) -> ExtractionJob:
    """Create a failed extraction job eligible for retry."""
    from datetime import datetime, timezone

    job = ExtractionJob(
        id=str(uuid4()),
        filename="failed_drawing.ifc",
        file_url="extraction-jobs/test789/failed_drawing.ifc",
        file_size=2048000,
        format=ExtractionFormat.IFC.value,
        status=ExtractionJobStatus.FAILED.value,
        error_message="Test error: extraction failed",
        retry_count=1,
        max_retries=3,
    )
    job.started_at = datetime.now(timezone.utc)

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def exhausted_extraction_job(db_session: AsyncSession) -> ExtractionJob:
    """Create a failed extraction job that has exhausted all retries."""
    from datetime import datetime, timezone

    job = ExtractionJob(
        id=str(uuid4()),
        filename="exhausted_drawing.step",
        file_url="extraction-jobs/testabc/exhausted_drawing.step",
        file_size=3072000,
        format=ExtractionFormat.STEP.value,
        status=ExtractionJobStatus.FAILED.value,
        error_message="Test error: max retries exceeded",
        retry_count=3,
        max_retries=3,
    )
    job.started_at = datetime.now(timezone.utc)
    job.completed_at = datetime.now(timezone.utc)

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest_asyncio.fixture
async def multiple_extraction_jobs(db_session: AsyncSession) -> list[ExtractionJob]:
    """Create multiple extraction jobs with various statuses for testing."""
    from datetime import datetime, timezone

    jobs = []

    # Pending jobs
    for i in range(3):
        job = ExtractionJob(
            id=str(uuid4()),
            filename=f"pending_{i}.pdf",
            file_url=f"extraction-jobs/pending{i}/pending_{i}.pdf",
            file_size=100000 * (i + 1),
            format=ExtractionFormat.PDF.value,
            status=ExtractionJobStatus.PENDING.value,
            max_retries=3,
        )
        db_session.add(job)
        jobs.append(job)

    # Processing job
    processing_job = ExtractionJob(
        id=str(uuid4()),
        filename="processing.dxf",
        file_url="extraction-jobs/proc/processing.dxf",
        file_size=500000,
        format=ExtractionFormat.DXF.value,
        status=ExtractionJobStatus.PROCESSING.value,
        max_retries=3,
    )
    processing_job.started_at = datetime.now(timezone.utc)
    db_session.add(processing_job)
    jobs.append(processing_job)

    # Completed jobs
    for i in range(2):
        job = ExtractionJob(
            id=str(uuid4()),
            filename=f"completed_{i}.ifc",
            file_url=f"extraction-jobs/comp{i}/completed_{i}.ifc",
            file_size=200000 * (i + 1),
            format=ExtractionFormat.IFC.value,
            status=ExtractionJobStatus.COMPLETED.value,
            max_retries=3,
        )
        job.set_result({"success": True, "entities": []})
        job.started_at = datetime.now(timezone.utc)
        job.completed_at = datetime.now(timezone.utc)
        db_session.add(job)
        jobs.append(job)

    # Failed job (retryable)
    failed_job = ExtractionJob(
        id=str(uuid4()),
        filename="failed_retryable.step",
        file_url="extraction-jobs/fail/failed_retryable.step",
        file_size=750000,
        format=ExtractionFormat.STEP.value,
        status=ExtractionJobStatus.FAILED.value,
        error_message="Temporary failure",
        retry_count=1,
        max_retries=3,
    )
    db_session.add(failed_job)
    jobs.append(failed_job)

    # Cancelled job
    cancelled_job = ExtractionJob(
        id=str(uuid4()),
        filename="cancelled.pdf",
        file_url="extraction-jobs/cancel/cancelled.pdf",
        file_size=300000,
        format=ExtractionFormat.PDF.value,
        status=ExtractionJobStatus.CANCELLED.value,
        max_retries=3,
    )
    cancelled_job.completed_at = datetime.now(timezone.utc)
    db_session.add(cancelled_job)
    jobs.append(cancelled_job)

    await db_session.commit()

    # Refresh all jobs
    for job in jobs:
        await db_session.refresh(job)

    return jobs
