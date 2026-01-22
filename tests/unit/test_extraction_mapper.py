"""Unit tests for ExtractionMapperService."""

import pytest

from pybase.services.extraction_mapper import ExtractionMapperService


class TestExtractionMapperService:
    """Test ExtractionMapperService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mapper = ExtractionMapperService()

    # ===== Dimension Mapping Tests =====

    def test_map_dimension_werk24_format(self):
        """Test mapping dimension from Werk24Dimension format."""
        dimension_data = {
            "nominal_value": 10.5,
            "unit": "mm",
            "upper_deviation": 0.2,
            "lower_deviation": -0.1,
            "dimension_type": "linear",
            "tolerance_grade": "h7",
        }

        result = self.mapper.map_dimension(dimension_data)

        assert result is not None
        assert result["value"] == 10.5
        assert result["tolerance_plus"] == 0.2
        assert result["tolerance_minus"] == 0.1  # Converted to positive
        assert result["unit"] == "mm"

    def test_map_dimension_extracted_format(self):
        """Test mapping dimension from ExtractedDimension format."""
        dimension_data = {
            "value": 25.0,
            "tolerance_plus": 0.05,
            "tolerance_minus": 0.03,
            "unit": "in",
        }

        result = self.mapper.map_dimension(dimension_data)

        assert result is not None
        assert result["value"] == 25.0
        assert result["tolerance_plus"] == 0.05
        assert result["tolerance_minus"] == 0.03
        assert result["unit"] == "in"

    def test_map_dimension_no_tolerance(self):
        """Test mapping dimension without tolerance values."""
        dimension_data = {
            "nominal_value": 15.0,
            "unit": "mm",
        }

        result = self.mapper.map_dimension(dimension_data)

        assert result is not None
        assert result["value"] == 15.0
        assert result["tolerance_plus"] == 0
        assert result["tolerance_minus"] == 0
        assert result["unit"] == "mm"

    def test_map_dimension_default_unit(self):
        """Test mapping dimension with default unit."""
        dimension_data = {
            "nominal_value": 20.0,
        }

        result = self.mapper.map_dimension(dimension_data)

        assert result is not None
        assert result["unit"] == "mm"  # Default unit

    def test_map_dimension_none_input(self):
        """Test mapping dimension with None input."""
        result = self.mapper.map_dimension(None)
        assert result is None

    def test_map_dimension_empty_dict(self):
        """Test mapping dimension with empty dictionary."""
        result = self.mapper.map_dimension({})
        assert result is None

    def test_map_dimension_negative_lower_deviation(self):
        """Test mapping dimension with negative lower deviation."""
        dimension_data = {
            "nominal_value": 10.0,
            "upper_deviation": 0.15,
            "lower_deviation": -0.25,
        }

        result = self.mapper.map_dimension(dimension_data)

        assert result is not None
        assert result["tolerance_minus"] == 0.25  # Absolute value

    # ===== GD&T Mapping Tests =====

    def test_map_gdt_position(self):
        """Test mapping position tolerance."""
        gdt_data = {
            "characteristic_type": "position",
            "tolerance_value": 0.05,
            "tolerance_unit": "mm",
            "material_condition": "MMC",
            "datums": ["A", "B", "C"],
        }

        result = self.mapper.map_gdt(gdt_data)

        assert result is not None
        assert result["type"] == "position"
        assert result["tolerance"] == 0.05
        assert result["diameter_zone"] is True  # Position uses diameter zone
        assert result["material_condition"] == "MMC"
        assert result["datums"] == ["A", "B", "C"]

    def test_map_gdt_flatness(self):
        """Test mapping flatness tolerance."""
        gdt_data = {
            "characteristic_type": "flatness",
            "tolerance_value": 0.02,
            "tolerance_unit": "mm",
        }

        result = self.mapper.map_gdt(gdt_data)

        assert result is not None
        assert result["type"] == "flatness"
        assert result["tolerance"] == 0.02
        assert result["diameter_zone"] is False
        assert result["material_condition"] == "RFS"  # Default
        assert result["datums"] == []

    def test_map_gdt_perpendicularity(self):
        """Test mapping perpendicularity tolerance."""
        gdt_data = {
            "characteristic_type": "perpendicularity",
            "tolerance_value": 0.1,
            "material_condition": "LMC",
            "datums": ["A"],
        }

        result = self.mapper.map_gdt(gdt_data)

        assert result is not None
        assert result["type"] == "perpendicularity"
        assert result["tolerance"] == 0.1
        assert result["material_condition"] == "LMC"
        assert result["datums"] == ["A"]

    def test_map_gdt_type_alias_roundness(self):
        """Test mapping GD&T with type alias (roundness -> circularity)."""
        gdt_data = {
            "characteristic_type": "roundness",
            "tolerance_value": 0.03,
        }

        result = self.mapper.map_gdt(gdt_data)

        assert result is not None
        assert result["type"] == "circularity"  # Normalized

    def test_map_gdt_type_alias_line_profile(self):
        """Test mapping GD&T with type alias (line_profile -> profile_line)."""
        gdt_data = {
            "characteristic_type": "line_profile",
            "tolerance_value": 0.05,
        }

        result = self.mapper.map_gdt(gdt_data)

        assert result is not None
        assert result["type"] == "profile_line"  # Normalized

    def test_map_gdt_type_alias_surface_profile(self):
        """Test mapping GD&T with type alias (surface_profile -> profile_surface)."""
        gdt_data = {
            "characteristic_type": "surface_profile",
            "tolerance_value": 0.08,
        }

        result = self.mapper.map_gdt(gdt_data)

        assert result is not None
        assert result["type"] == "profile_surface"  # Normalized

    def test_map_gdt_concentricity_diameter_zone(self):
        """Test mapping concentricity uses diameter zone."""
        gdt_data = {
            "characteristic_type": "concentricity",
            "tolerance_value": 0.02,
            "datums": ["A"],
        }

        result = self.mapper.map_gdt(gdt_data)

        assert result is not None
        assert result["type"] == "concentricity"
        assert result["diameter_zone"] is True  # Concentricity uses diameter zone

    def test_map_gdt_invalid_material_condition(self):
        """Test mapping GD&T with invalid material condition."""
        gdt_data = {
            "characteristic_type": "flatness",
            "tolerance_value": 0.05,
            "material_condition": "INVALID",
        }

        result = self.mapper.map_gdt(gdt_data)

        assert result is not None
        assert result["material_condition"] == "RFS"  # Default to RFS

    def test_map_gdt_empty_material_condition(self):
        """Test mapping GD&T with empty material condition."""
        gdt_data = {
            "characteristic_type": "parallelism",
            "tolerance_value": 0.04,
            "material_condition": "",
        }

        result = self.mapper.map_gdt(gdt_data)

        assert result is not None
        assert result["material_condition"] == "RFS"  # Default to RFS

    def test_map_gdt_none_material_condition(self):
        """Test mapping GD&T with None material condition."""
        gdt_data = {
            "characteristic_type": "angularity",
            "tolerance_value": 0.06,
            "material_condition": None,
        }

        result = self.mapper.map_gdt(gdt_data)

        assert result is not None
        assert result["material_condition"] == "RFS"  # Default to RFS

    def test_map_gdt_none_input(self):
        """Test mapping GD&T with None input."""
        result = self.mapper.map_gdt(None)
        assert result is None

    def test_map_gdt_empty_dict(self):
        """Test mapping GD&T with empty dictionary."""
        result = self.mapper.map_gdt({})
        # Empty dict is falsy, so map_gdt returns None
        assert result is None

    # ===== Material Mapping Tests =====

    def test_map_material_full_data(self):
        """Test mapping material with full data."""
        material_data = {
            "designation": "AISI 304",
            "standard": "ASTM",
            "material_type": "stainless_steel",
            "condition": "annealed",
            "properties": {"yield_strength": 215, "tensile_strength": 505},
            "notes": "Food grade",
        }

        result = self.mapper.map_material(material_data)

        assert result is not None
        assert result["designation"] == "AISI 304"
        assert result["standard"] == "ASTM"
        assert result["family"] == "stainless_steel"
        assert result["condition"] == "annealed"
        assert result["properties"]["yield_strength"] == 215
        assert result["notes"] == "Food grade"

    def test_map_material_family_normalization(self):
        """Test mapping material with family name normalization."""
        material_data = {
            "designation": "6061-T6",
            "material_type": "Aluminum Alloy",
        }

        result = self.mapper.map_material(material_data)

        assert result is not None
        assert result["family"] == "aluminum_alloy"  # Normalized

    def test_map_material_family_from_family_field(self):
        """Test mapping material with family instead of material_type."""
        material_data = {
            "designation": "1018",
            "family": "carbon_steel",
        }

        result = self.mapper.map_material(material_data)

        assert result is not None
        assert result["family"] == "carbon_steel"

    def test_map_material_minimal_data(self):
        """Test mapping material with minimal data."""
        material_data = {
            "designation": "Steel",
        }

        result = self.mapper.map_material(material_data)

        assert result is not None
        assert result["designation"] == "Steel"
        assert result["standard"] is None
        assert result["family"] is None
        assert result["properties"] == {}

    def test_map_material_none_input(self):
        """Test mapping material with None input."""
        result = self.mapper.map_material(None)
        assert result is None

    def test_map_material_empty_dict(self):
        """Test mapping material with empty dictionary."""
        result = self.mapper.map_material({})
        # Empty dict is falsy, so map_material returns None
        assert result is None

    # ===== Thread Mapping Tests =====

    def test_map_thread_metric(self):
        """Test mapping metric thread."""
        thread_data = {
            "standard": "ISO",
            "designation": "M8x1.25",
            "nominal_diameter": 8.0,
            "pitch": 1.25,
            "thread_class": "6g",
            "hand": "right",
            "thread_type": "external",
        }

        result = self.mapper.map_thread(thread_data)

        assert result is not None
        assert result["standard"] == "metric"  # ISO -> metric
        assert result["size"] == 8.0
        assert result["pitch"] == 1.25
        assert result["class"] == "6g"
        assert result["internal"] is False  # external
        assert result["left_hand"] is False  # right hand

    def test_map_thread_unc(self):
        """Test mapping UNC thread."""
        thread_data = {
            "standard": "UN",
            "nominal_diameter": 0.25,
            "pitch": 20,
            "thread_class": "2A",
            "thread_type": "external",
        }

        result = self.mapper.map_thread(thread_data)

        assert result is not None
        assert result["standard"] == "unc"  # UN -> unc
        assert result["size"] == 0.25
        assert result["pitch"] == 20

    def test_map_thread_internal(self):
        """Test mapping internal thread."""
        thread_data = {
            "standard": "metric",
            "nominal_diameter": 10.0,
            "thread_type": "internal",
        }

        result = self.mapper.map_thread(thread_data)

        assert result is not None
        assert result["internal"] is True

    def test_map_thread_tapped_hole(self):
        """Test mapping tapped hole thread."""
        thread_data = {
            "standard": "metric",
            "nominal_diameter": 6.0,
            "thread_type": "tapped",
        }

        result = self.mapper.map_thread(thread_data)

        assert result is not None
        assert result["internal"] is True  # tapped is internal

    def test_map_thread_left_hand(self):
        """Test mapping left hand thread."""
        thread_data = {
            "standard": "metric",
            "nominal_diameter": 12.0,
            "hand": "left",
        }

        result = self.mapper.map_thread(thread_data)

        assert result is not None
        assert result["left_hand"] is True

    def test_map_thread_left_hand_abbreviation(self):
        """Test mapping left hand thread with abbreviation."""
        thread_data = {
            "standard": "metric",
            "nominal_diameter": 10.0,
            "hand": "LH",
        }

        result = self.mapper.map_thread(thread_data)

        assert result is not None
        assert result["left_hand"] is True

    def test_map_thread_standard_normalization(self):
        """Test mapping thread with standard normalization."""
        test_cases = [
            ("DIN", "metric"),
            ("unified", "unc"),
            ("UNF", "unf"),
            ("UNEF", "unef"),
            ("BSP", "bsp"),
            ("NPT", "npt"),
        ]

        for input_std, expected_std in test_cases:
            thread_data = {
                "standard": input_std,
                "nominal_diameter": 10.0,
            }

            result = self.mapper.map_thread(thread_data)

            assert result is not None
            assert result["standard"] == expected_std

    def test_map_thread_size_from_size_field(self):
        """Test mapping thread with size instead of nominal_diameter."""
        thread_data = {
            "standard": "metric",
            "size": 12.0,
            "pitch": 1.75,
        }

        result = self.mapper.map_thread(thread_data)

        assert result is not None
        assert result["size"] == 12.0

    def test_map_thread_class_from_class_field(self):
        """Test mapping thread with class instead of thread_class."""
        thread_data = {
            "standard": "unc",
            "nominal_diameter": 0.5,
            "class": "2B",
        }

        result = self.mapper.map_thread(thread_data)

        assert result is not None
        assert result["class"] == "2B"

    def test_map_thread_none_input(self):
        """Test mapping thread with None input."""
        result = self.mapper.map_thread(None)
        assert result is None

    def test_map_thread_empty_dict(self):
        """Test mapping thread with empty dictionary."""
        result = self.mapper.map_thread({})
        # Empty dict is falsy, so map_thread returns None
        assert result is None

    # ===== Surface Finish Mapping Tests =====

    def test_map_surface_finish_ra(self):
        """Test mapping surface finish with Ra parameter."""
        surface_finish_data = {
            "ra_value": 1.6,
            "unit": "μm",
            "process": "ground",
            "lay_symbol": "perpendicular",
        }

        result = self.mapper.map_surface_finish(surface_finish_data)

        assert result is not None
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6
        assert result["unit"] == "μm"
        assert result["process"] == "ground"
        assert result["lay"] == "perpendicular"

    def test_map_surface_finish_rz(self):
        """Test mapping surface finish with Rz parameter."""
        surface_finish_data = {
            "rz_value": 6.3,
            "unit": "μm",
        }

        result = self.mapper.map_surface_finish(surface_finish_data)

        assert result is not None
        assert result["parameter"] == "Rz"
        assert result["value"] == 6.3

    def test_map_surface_finish_generic_value(self):
        """Test mapping surface finish with generic value field."""
        surface_finish_data = {
            "parameter": "Rz",
            "value": 3.2,
            "unit": "μm",
        }

        result = self.mapper.map_surface_finish(surface_finish_data)

        assert result is not None
        assert result["parameter"] == "Rz"
        assert result["value"] == 3.2

    def test_map_surface_finish_lay_symbol_normalization(self):
        """Test mapping surface finish with lay symbol normalization."""
        test_cases = [
            ("⟂", "perpendicular"),
            ("=", "parallel"),
            ("X", "crossed"),
            ("M", "multidirectional"),
            ("C", "circular"),
            ("R", "radial"),
        ]

        for input_lay, expected_lay in test_cases:
            surface_finish_data = {
                "ra_value": 3.2,
                "lay_symbol": input_lay,
            }

            result = self.mapper.map_surface_finish(surface_finish_data)

            assert result is not None
            assert result["lay"] == expected_lay

    def test_map_surface_finish_lay_from_lay_field(self):
        """Test mapping surface finish with lay instead of lay_symbol."""
        surface_finish_data = {
            "ra_value": 0.8,
            "lay": "parallel",
        }

        result = self.mapper.map_surface_finish(surface_finish_data)

        assert result is not None
        assert result["lay"] == "parallel"

    def test_map_surface_finish_default_unit(self):
        """Test mapping surface finish with default unit."""
        surface_finish_data = {
            "ra_value": 3.2,
        }

        result = self.mapper.map_surface_finish(surface_finish_data)

        assert result is not None
        assert result["unit"] == "μm"  # Default unit

    def test_map_surface_finish_none_input(self):
        """Test mapping surface finish with None input."""
        result = self.mapper.map_surface_finish(None)
        assert result is None

    def test_map_surface_finish_empty_dict(self):
        """Test mapping surface finish with empty dictionary."""
        result = self.mapper.map_surface_finish({})
        # Empty dict is falsy, so map_surface_finish returns None
        assert result is None

    # ===== Werk24 Result Mapping Tests =====

    def test_map_werk24_result_complete(self):
        """Test mapping complete Werk24 extraction result."""
        extraction_result = {
            "dimensions": [
                {"nominal_value": 10.0, "upper_deviation": 0.1, "lower_deviation": -0.05},
                {"nominal_value": 20.0},
            ],
            "gdts": [
                {"characteristic_type": "flatness", "tolerance_value": 0.02},
                {"characteristic_type": "position", "tolerance_value": 0.05, "datums": ["A"]},
            ],
            "threads": [
                {"standard": "ISO", "nominal_diameter": 8.0, "pitch": 1.25},
            ],
            "materials": [
                {"designation": "AISI 304", "standard": "ASTM"},
            ],
            "surface_finishes": [
                {"ra_value": 1.6, "unit": "μm"},
            ],
        }

        result = self.mapper.map_werk24_result(extraction_result)

        assert result is not None
        assert len(result["dimensions"]) == 2
        assert len(result["gdts"]) == 2
        assert len(result["threads"]) == 1
        assert len(result["materials"]) == 1
        assert len(result["surface_finishes"]) == 1

        # Check dimension mapping
        assert result["dimensions"][0]["value"] == 10.0
        assert result["dimensions"][0]["tolerance_plus"] == 0.1

        # Check GDT mapping
        assert result["gdts"][0]["type"] == "flatness"
        assert result["gdts"][1]["type"] == "position"

        # Check thread mapping
        assert result["threads"][0]["standard"] == "metric"

        # Check material mapping
        assert result["materials"][0]["designation"] == "AISI 304"

        # Check surface finish mapping
        assert result["surface_finishes"][0]["parameter"] == "Ra"

    def test_map_werk24_result_empty(self):
        """Test mapping empty Werk24 extraction result."""
        extraction_result = {}

        result = self.mapper.map_werk24_result(extraction_result)

        assert result is not None
        assert result["dimensions"] == []
        assert result["gdts"] == []
        assert result["threads"] == []
        assert result["materials"] == []
        assert result["surface_finishes"] == []

    def test_map_werk24_result_skip_invalid_items(self):
        """Test mapping Werk24 result skips invalid items."""
        extraction_result = {
            "dimensions": [
                {"nominal_value": 10.0},
                {},  # Invalid - should be skipped
                None,  # Invalid - should be skipped
            ],
            "gdts": [
                {"characteristic_type": "flatness", "tolerance_value": 0.02},
            ],
        }

        result = self.mapper.map_werk24_result(extraction_result)

        # Only valid dimension should be mapped
        assert len(result["dimensions"]) == 1
        assert result["dimensions"][0]["value"] == 10.0

        # GDT should be mapped
        assert len(result["gdts"]) == 1

    # ===== Validation Tests =====

    def test_validate_mapped_data_dimension_valid(self):
        """Test validating valid dimension data."""
        mapped_data = {
            "value": 10.0,
            "tolerance_plus": 0.1,
            "tolerance_minus": 0.05,
            "unit": "mm",
        }

        is_valid, error = self.mapper.validate_mapped_data(mapped_data, "dimension")

        assert is_valid is True
        assert error is None

    def test_validate_mapped_data_gdt_valid(self):
        """Test validating valid GD&T data."""
        mapped_data = {
            "type": "flatness",
            "tolerance": 0.02,
            "diameter_zone": False,
            "material_condition": "RFS",
            "datums": [],
            "datum_modifiers": {},
        }

        is_valid, error = self.mapper.validate_mapped_data(mapped_data, "gdt")

        assert is_valid is True
        assert error is None

    def test_validate_mapped_data_thread_valid(self):
        """Test validating valid thread data."""
        mapped_data = {
            "standard": "metric",
            "size": 8.0,
            "pitch": 1.25,
            "class": "6g",
            "internal": False,
            "left_hand": False,
        }

        is_valid, error = self.mapper.validate_mapped_data(mapped_data, "thread")

        assert is_valid is True
        assert error is None

    def test_validate_mapped_data_material_valid(self):
        """Test validating valid material data."""
        mapped_data = {
            "designation": "AISI 304",
            "standard": "ASTM",
            "family": "stainless_steel",
            "condition": None,
            "properties": {},
        }

        is_valid, error = self.mapper.validate_mapped_data(mapped_data, "material")

        assert is_valid is True
        assert error is None

    def test_validate_mapped_data_surface_finish_valid(self):
        """Test validating valid surface finish data."""
        mapped_data = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
            "process": None,
            "lay": None,
        }

        is_valid, error = self.mapper.validate_mapped_data(mapped_data, "surface_finish")

        assert is_valid is True
        assert error is None

    def test_validate_mapped_data_unknown_field_type(self):
        """Test validating with unknown field type."""
        mapped_data = {"value": 10.0}

        is_valid, error = self.mapper.validate_mapped_data(mapped_data, "unknown_type")

        assert is_valid is False
        assert "Unknown field type" in error

    def test_validate_mapped_data_invalid_data(self):
        """Test validating invalid dimension data."""
        # Missing required fields
        mapped_data = {}

        is_valid, error = self.mapper.validate_mapped_data(mapped_data, "dimension")

        assert is_valid is False
        assert error is not None
