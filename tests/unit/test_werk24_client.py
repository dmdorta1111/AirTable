"""Unit tests for Werk24Client."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from pybase.extraction.werk24.client import (
    WERK24_AVAILABLE,
    Werk24AskType,
    Werk24Client,
    Werk24Dimension,
    Werk24ExtractionResult,
    Werk24GDT,
    Werk24SurfaceFinish,
    Werk24Thread,
    extract_drawing,
)


class TestWerk24Dimension:
    """Test Werk24Dimension dataclass."""

    def test_to_extracted_dimension(self):
        """Test conversion to ExtractedDimension."""
        dim = Werk24Dimension(
            nominal_value=10.5,
            unit="mm",
            upper_deviation=0.1,
            lower_deviation=-0.2,
            dimension_type="linear",
            tolerance_grade="h7",
            confidence=0.95,
        )

        extracted = dim.to_extracted_dimension()

        assert extracted.value == 10.5
        assert extracted.unit == "mm"
        assert extracted.tolerance_plus == 0.1
        assert extracted.tolerance_minus == 0.2  # Converted to positive
        assert extracted.dimension_type == "linear"
        assert extracted.label == "h7"
        assert extracted.confidence == 0.95

    def test_to_extracted_dimension_no_tolerance(self):
        """Test conversion without tolerance."""
        dim = Werk24Dimension(nominal_value=25.0)

        extracted = dim.to_extracted_dimension()

        assert extracted.value == 25.0
        assert extracted.unit == "mm"
        assert extracted.tolerance_plus is None
        assert extracted.tolerance_minus is None


class TestWerk24GDT:
    """Test Werk24GDT dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        gdt = Werk24GDT(
            characteristic_type="flatness",
            tolerance_value=0.05,
            tolerance_unit="mm",
            material_condition="MMC",
            datums=["A", "B"],
            composite=False,
            confidence=0.9,
        )

        result = gdt.to_dict()

        assert result["characteristic_type"] == "flatness"
        assert result["tolerance_value"] == 0.05
        assert result["tolerance_unit"] == "mm"
        assert result["material_condition"] == "MMC"
        assert result["datums"] == ["A", "B"]
        assert result["composite"] is False
        assert result["confidence"] == 0.9


class TestWerk24Thread:
    """Test Werk24Thread dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        thread = Werk24Thread(
            standard="ISO",
            designation="M8x1.25",
            nominal_diameter=8.0,
            pitch=1.25,
            thread_class="6g",
            hand="right",
            thread_type="external",
            confidence=0.95,
        )

        result = thread.to_dict()

        assert result["standard"] == "ISO"
        assert result["designation"] == "M8x1.25"
        assert result["nominal_diameter"] == 8.0
        assert result["pitch"] == 1.25
        assert result["thread_class"] == "6g"
        assert result["hand"] == "right"
        assert result["thread_type"] == "external"
        assert result["confidence"] == 0.95


class TestWerk24SurfaceFinish:
    """Test Werk24SurfaceFinish dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        finish = Werk24SurfaceFinish(
            ra_value=3.2,
            unit="μm",
            lay_symbol="=",
            process="machining",
            confidence=0.85,
        )

        result = finish.to_dict()

        assert result["ra_value"] == 3.2
        assert result["unit"] == "μm"
        assert result["lay_symbol"] == "="
        assert result["process"] == "machining"
        assert result["confidence"] == 0.85


class TestWerk24ExtractionResult:
    """Test Werk24ExtractionResult dataclass."""

    def test_creation(self):
        """Test basic creation of Werk24ExtractionResult."""
        result = Werk24ExtractionResult(
            source_file="test.pdf",
            source_type="werk24",
        )

        assert result.source_file == "test.pdf"
        assert result.source_type == "werk24"
        assert len(result.dimensions) == 0
        assert len(result.gdts) == 0
        assert len(result.materials) == 0
        assert result.overall_dimensions is None


class TestWerk24Client:
    """Test Werk24Client class."""

    def test_init_with_api_key(self):
        """Test initialization with explicit API key."""
        client = Werk24Client(api_key="test-key-123")

        assert client.api_key == "test-key-123"
        assert client.base_url == Werk24Client.DEFAULT_BASE_URL
        assert client.timeout == 300.0

    def test_init_with_env_var(self):
        """Test initialization with environment variable."""
        with patch.dict("os.environ", {"WERK24_API_KEY": "env-key-456"}):
            client = Werk24Client()

            assert client.api_key == "env-key-456"

    def test_init_custom_base_url(self):
        """Test initialization with custom base URL."""
        client = Werk24Client(
            api_key="test-key",
            base_url="https://custom.api.werk24.io",
            timeout=600.0,
        )

        assert client.base_url == "https://custom.api.werk24.io"
        assert client.timeout == 600.0

    @pytest.mark.asyncio
    async def test_extract_async_no_api_key(self):
        """Test extraction without API key."""
        with patch.dict("os.environ", {}, clear=True):
            client = Werk24Client(api_key=None)
            result = await client.extract_async("test.pdf")

            assert len(result.errors) > 0
            assert any("API key not configured" in err for err in result.errors)
            assert len(result.dimensions) == 0

    @pytest.mark.asyncio
    async def test_extract_async_sdk_not_available(self):
        """Test extraction when SDK is not installed."""
        client = Werk24Client(api_key="test-key")

        with patch("pybase.extraction.werk24.client.WERK24_AVAILABLE", False):
            result = await client.extract_async("test.pdf")

            assert "SDK not installed" in result.errors[0]
            assert len(result.dimensions) == 0

    @pytest.mark.asyncio
    async def test_extract_async_with_file_path(self):
        """Test extraction with file path."""
        if not WERK24_AVAILABLE:
            pytest.skip("werk24 SDK not available")

        client = Werk24Client(api_key="test-key")

        # Mock file reading
        mock_file_content = b"fake-pdf-content"

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = mock_file_content
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            # Mock W24TechRead
            mock_techread = AsyncMock()
            mock_techread.read_drawing = AsyncMock()

            with patch(
                "pybase.extraction.werk24.client.W24TechRead"
            ) as mock_techread_class:
                mock_techread_class.return_value.__aenter__.return_value = mock_techread
                mock_techread_class.return_value.__aexit__.return_value = AsyncMock()

                result = await client.extract_async("test.pdf")

                assert result.source_file == "test.pdf"
                assert result.source_type == "werk24"
                assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_extract_async_with_usage_tracking(self):
        """Test extraction with usage tracking."""
        if not WERK24_AVAILABLE:
            pytest.skip("werk24 SDK not available")

        client = Werk24Client(api_key="test-key-for-tracking")

        # Mock database session and user
        mock_db = AsyncMock()
        user_id = "user-123"
        workspace_id = "workspace-456"

        # Mock file reading
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b"fake-content"
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            # Mock W24TechRead
            mock_techread = AsyncMock()
            mock_techread.read_drawing = AsyncMock()

            # Mock Werk24Service
            mock_usage_record = MagicMock()
            mock_usage_record.id = "usage-123"

            with (
                patch(
                    "pybase.extraction.werk24.client.W24TechRead"
                ) as mock_techread_class,
                patch(
                    "pybase.extraction.werk24.client.Werk24Service"
                ) as mock_service_class,
            ):
                mock_techread_class.return_value.__aenter__.return_value = mock_techread
                mock_techread_class.return_value.__aexit__.return_value = AsyncMock()

                mock_service = AsyncMock()
                mock_service.create_usage_record = AsyncMock(
                    return_value=mock_usage_record
                )
                mock_service.update_usage_record = AsyncMock()
                mock_service_class.return_value = mock_service

                result = await client.extract_async(
                    "test.pdf",
                    db=mock_db,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    file_size=1024,
                    file_type="pdf",
                )

                # Verify usage tracking was called
                mock_service.create_usage_record.assert_called_once()
                mock_service.update_usage_record.assert_called_once()

                # Verify tracking parameters
                create_call = mock_service.create_usage_record.call_args
                assert create_call[1]["user_id"] == user_id
                assert create_call[1]["workspace_id"] == workspace_id
                assert create_call[1]["request_type"] == "extract_async"

    @pytest.mark.asyncio
    async def test_extract_async_api_error(self):
        """Test extraction with API error."""
        if not WERK24_AVAILABLE:
            pytest.skip("werk24 SDK not available")

        client = Werk24Client(api_key="test-key")

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = b"fake-content"
            mock_file.__enter__.return_value = mock_file
            mock_open.return_value = mock_file

            # Mock W24TechRead to raise exception
            with patch(
                "pybase.extraction.werk24.client.W24TechRead"
            ) as mock_techread_class:
                mock_techread = AsyncMock()
                mock_techread.read_drawing = AsyncMock(
                    side_effect=Exception("API Error")
                )
                mock_techread_class.return_value.__aenter__.return_value = mock_techread
                mock_techread_class.return_value.__aexit__.return_value = AsyncMock()

                result = await client.extract_async("test.pdf")

                assert len(result.errors) > 0
                assert "API Error" in result.errors[0]

    def test_build_asks(self):
        """Test building ask types for API."""
        if not WERK24_AVAILABLE:
            pytest.skip("werk24 SDK not available")

        client = Werk24Client(api_key="test-key")

        ask_types = [
            Werk24AskType.DIMENSIONS,
            Werk24AskType.GDTS,
            Werk24AskType.TITLE_BLOCK,
            Werk24AskType.MATERIAL,
        ]

        asks = client._build_asks(ask_types)

        # Should have 4 asks
        assert len(asks) == 4

    def test_parse_measure(self):
        """Test parsing measure data."""
        if not WERK24_AVAILABLE:
            pytest.skip("werk24 SDK not available")

        client = Werk24Client(api_key="test-key")

        # Create mock measure
        mock_measure = MagicMock()
        mock_measure.nominal_size.value = 10.5
        mock_measure.nominal_size.unit = "mm"
        mock_measure.tolerance.deviation_upper = 0.1
        mock_measure.tolerance.deviation_lower = -0.05
        mock_measure.tolerance.iso_tolerance_class = "h7"
        mock_measure.measure_type = "diameter"

        result = client._parse_measure(mock_measure)

        assert result is not None
        assert result.nominal_value == 10.5
        assert result.unit == "mm"
        assert result.upper_deviation == 0.1
        assert result.lower_deviation == -0.05
        assert result.tolerance_grade == "h7"
        assert result.dimension_type == "diameter"

    def test_parse_measure_error(self):
        """Test parsing measure with error."""
        if not WERK24_AVAILABLE:
            pytest.skip("werk24 SDK not available")

        client = Werk24Client(api_key="test-key")

        # Create invalid mock measure
        mock_measure = MagicMock()
        mock_measure.nominal_size.value = None  # This will cause error

        result = client._parse_measure(mock_measure)

        # Should return None on error
        assert result is None

    def test_parse_gdt(self):
        """Test parsing GD&T data."""
        if not WERK24_AVAILABLE:
            pytest.skip("werk24 SDK not available")

        client = Werk24Client(api_key="test-key")

        # Create mock GDT
        mock_gdt = MagicMock()
        mock_gdt.characteristic_type = "flatness"
        mock_gdt.tolerance.value = 0.05
        mock_gdt.material_condition = "MMC"

        mock_datum1 = MagicMock()
        mock_datum1.letter = "A"
        mock_datum2 = MagicMock()
        mock_datum2.letter = "B"
        mock_gdt.datums = [mock_datum1, mock_datum2]

        result = client._parse_gdt(mock_gdt)

        assert result is not None
        assert result.characteristic_type == "flatness"
        assert result.tolerance_value == 0.05
        assert result.material_condition == "MMC"
        assert result.datums == ["A", "B"]

    def test_parse_title_block(self):
        """Test parsing title block data."""
        if not WERK24_AVAILABLE:
            pytest.skip("werk24 SDK not available")

        client = Werk24Client(api_key="test-key")

        # Create mock title block payload
        mock_payload = MagicMock()
        mock_payload.drawing_number = "DRW-123"
        mock_payload.title = "Test Part"
        mock_payload.revision = "A"
        mock_payload.date = "2024-01-01"
        mock_payload.designer = "John Doe"
        mock_payload.company = "ACME Corp"
        mock_payload.scale = "1:1"
        mock_payload.material = "Steel"

        result = client._parse_title_block(mock_payload)

        assert result.drawing_number == "DRW-123"
        assert result.title == "Test Part"
        assert result.revision == "A"
        assert result.date == "2024-01-01"
        assert result.author == "John Doe"
        assert result.company == "ACME Corp"
        assert result.scale == "1:1"
        assert result.material == "Steel"

    def test_parse_material(self):
        """Test parsing material data."""
        if not WERK24_AVAILABLE:
            pytest.skip("werk24 SDK not available")

        client = Werk24Client(api_key="test-key")

        # Create mock material payload
        mock_payload = MagicMock()
        mock_payload.designation = "AISI 304"
        mock_payload.standard = "AISI"
        mock_payload.material_type = "Stainless Steel"

        result = client._parse_material(mock_payload)

        assert result is not None
        assert result["designation"] == "AISI 304"
        assert result["standard"] == "AISI"
        assert result["material_type"] == "Stainless Steel"

    def test_parse_overall_dimensions(self):
        """Test parsing overall dimensions."""
        if not WERK24_AVAILABLE:
            pytest.skip("werk24 SDK not available")

        client = Werk24Client(api_key="test-key")

        # Create mock overall dimensions payload
        mock_payload = MagicMock()
        mock_payload.length.value = 100.0
        mock_payload.width.value = 50.0
        mock_payload.height.value = 25.0

        result = client._parse_overall_dimensions(mock_payload)

        assert result is not None
        assert result["length"] == 100.0
        assert result["width"] == 50.0
        assert result["height"] == 25.0

    def test_process_collected_data(self):
        """Test processing collected API data."""
        client = Werk24Client(api_key="test-key")

        dim1 = Werk24Dimension(nominal_value=10.0)
        dim2 = Werk24Dimension(nominal_value=20.0)

        gdt1 = Werk24GDT(characteristic_type="flatness", tolerance_value=0.05)

        collected_data = {
            "dimensions": [dim1, dim2],
            "gdts": [gdt1],
            "title_block": MagicMock(drawing_number="DRW-123"),
            "materials": [{"designation": "Steel"}],
            "overall_dimensions": {"length": 100.0},
            "thumbnails": {},
        }

        result = Werk24ExtractionResult(source_file="test.pdf", source_type="werk24")
        client._process_collected_data(collected_data, result)

        assert len(result.dimensions) == 2
        assert len(result.gdts) == 1
        assert result.title_block.drawing_number == "DRW-123"
        assert len(result.materials) == 1
        assert result.overall_dimensions == {"length": 100.0}
        assert len(result.dimensions_list) == 2

    def test_extract_sync(self):
        """Test synchronous extract wrapper."""
        with patch.dict("os.environ", {}, clear=True):
            client = Werk24Client(api_key=None)

            # Should fail without API key
            result = client.extract("test.pdf")

            assert len(result.errors) > 0
            assert any("API key not configured" in err for err in result.errors)


def test_extract_drawing_function():
    """Test convenience extract_drawing function."""
    with patch.dict("os.environ", {"WERK24_API_KEY": "test-key"}):
        # Should fail without real API
        result = extract_drawing("test.pdf")

        # Will have errors but function should work
        assert isinstance(result, Werk24ExtractionResult)
