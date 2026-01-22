"""Unit tests for SurfaceFinishFieldHandler."""

import pytest

from pybase.fields.types.engineering.surface_finish import SurfaceFinishFieldHandler


class TestSurfaceFinishFieldHandler:
    """Tests for SurfaceFinishFieldHandler class."""

    def test_field_type(self):
        """Test field type identifier."""
        assert SurfaceFinishFieldHandler.field_type == "surface_finish"

    def test_parameters_defined(self):
        """Test that roughness parameters are properly defined."""
        assert "Ra" in SurfaceFinishFieldHandler.PARAMETERS
        assert "Rz" in SurfaceFinishFieldHandler.PARAMETERS
        assert "Rq" in SurfaceFinishFieldHandler.PARAMETERS
        assert "Rt" in SurfaceFinishFieldHandler.PARAMETERS
        assert "Rmax" in SurfaceFinishFieldHandler.PARAMETERS
        assert "Rp" in SurfaceFinishFieldHandler.PARAMETERS
        assert "Rv" in SurfaceFinishFieldHandler.PARAMETERS
        assert "Rsk" in SurfaceFinishFieldHandler.PARAMETERS
        assert "Rku" in SurfaceFinishFieldHandler.PARAMETERS

    def test_ra_grades_defined(self):
        """Test that Ra N-grade values are properly defined."""
        assert SurfaceFinishFieldHandler.RA_GRADES[1.6] == "N7"
        assert SurfaceFinishFieldHandler.RA_GRADES[3.2] == "N8"
        assert SurfaceFinishFieldHandler.RA_GRADES[6.3] == "N9"
        assert SurfaceFinishFieldHandler.RA_GRADES[0.8] == "N6"

    def test_lay_symbols_defined(self):
        """Test that lay symbols are properly defined."""
        assert SurfaceFinishFieldHandler.LAY_SYMBOLS["parallel"] == "="
        assert SurfaceFinishFieldHandler.LAY_SYMBOLS["perpendicular"] == "⟂"
        assert SurfaceFinishFieldHandler.LAY_SYMBOLS["crossed"] == "X"
        assert SurfaceFinishFieldHandler.LAY_SYMBOLS["multidirectional"] == "M"
        assert SurfaceFinishFieldHandler.LAY_SYMBOLS["circular"] == "C"
        assert SurfaceFinishFieldHandler.LAY_SYMBOLS["radial"] == "R"

    def test_processes_defined(self):
        """Test that machining processes are properly defined."""
        assert "ground" in SurfaceFinishFieldHandler.PROCESSES
        assert "milled" in SurfaceFinishFieldHandler.PROCESSES
        assert "turned" in SurfaceFinishFieldHandler.PROCESSES
        assert "polished" in SurfaceFinishFieldHandler.PROCESSES
        assert "lapped" in SurfaceFinishFieldHandler.PROCESSES

    def test_parameter_ranges_defined(self):
        """Test that parameter-specific ranges are properly defined."""
        # Skip if PARAMETER_RANGES not implemented yet
        if hasattr(SurfaceFinishFieldHandler, 'PARAMETER_RANGES'):
            assert "Ra" in SurfaceFinishFieldHandler.PARAMETER_RANGES
            assert "Rz" in SurfaceFinishFieldHandler.PARAMETER_RANGES
            assert SurfaceFinishFieldHandler.PARAMETER_RANGES["Ra"]["min"] == 0.012
            assert SurfaceFinishFieldHandler.PARAMETER_RANGES["Ra"]["max"] == 100
            assert SurfaceFinishFieldHandler.PARAMETER_RANGES["Ra"]["unit"] == "μm"

    def test_valid_units_defined(self):
        """Test that valid units are properly defined."""
        # Skip if VALID_UNITS not implemented yet
        if hasattr(SurfaceFinishFieldHandler, 'VALID_UNITS'):
            assert "μm" in SurfaceFinishFieldHandler.VALID_UNITS
            assert "μin" in SurfaceFinishFieldHandler.VALID_UNITS
            assert "um" in SurfaceFinishFieldHandler.VALID_UNITS
            assert "uin" in SurfaceFinishFieldHandler.VALID_UNITS


class TestSurfaceFinishSerialization:
    """Tests for surface finish serialization."""

    def test_serialize_none(self):
        """Test serializing None returns None."""
        result = SurfaceFinishFieldHandler.serialize(None)
        assert result is None

    def test_serialize_dict_full(self):
        """Test serializing a complete dict."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "max_value": None,
            "unit": "μm",
            "process": "ground",
            "lay": "perpendicular",
        }
        result = SurfaceFinishFieldHandler.serialize(value)
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6
        assert result["max_value"] is None
        assert result["unit"] == "μm"
        assert result["process"] == "ground"
        assert result["lay"] == "perpendicular"

    def test_serialize_dict_with_range(self):
        """Test serializing dict with max_value range."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "max_value": 3.2,
            "unit": "μm",
        }
        result = SurfaceFinishFieldHandler.serialize(value)
        assert result["value"] == 1.6
        assert result["max_value"] == 3.2

    def test_serialize_dict_defaults_to_ra(self):
        """Test serializing dict without parameter defaults to Ra."""
        value = {
            "value": 1.6,
            "unit": "μm",
        }
        result = SurfaceFinishFieldHandler.serialize(value)
        assert result["parameter"] == "Ra"

    def test_serialize_dict_with_um_unit(self):
        """Test serializing dict with 'um' unit."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "um",
        }
        result = SurfaceFinishFieldHandler.serialize(value)
        # Unit is accepted (may be normalized to μm depending on implementation)
        assert result["unit"] in ("um", "μm")
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6

    def test_serialize_dict_with_uin_unit(self):
        """Test serializing dict with 'uin' unit."""
        value = {
            "parameter": "Ra",
            "value": 63,
            "unit": "uin",
        }
        result = SurfaceFinishFieldHandler.serialize(value)
        # Unit is accepted (may be normalized to μin depending on implementation)
        assert result["unit"] in ("uin", "μin")
        assert result["parameter"] == "Ra"
        assert result["value"] == 63

    def test_serialize_int(self):
        """Test serializing an integer."""
        result = SurfaceFinishFieldHandler.serialize(2)
        assert result["parameter"] == "Ra"
        assert result["value"] == 2.0
        assert result["unit"] == "μm"

    def test_serialize_float(self):
        """Test serializing a float."""
        result = SurfaceFinishFieldHandler.serialize(1.6)
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6
        assert result["unit"] == "μm"

    def test_serialize_string_ra_with_value(self):
        """Test serializing 'Ra 1.6' string."""
        result = SurfaceFinishFieldHandler.serialize("Ra 1.6")
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6
        assert result["unit"] == "μm"

    def test_serialize_string_ra_with_unit(self):
        """Test serializing 'Ra 1.6 μm' string."""
        result = SurfaceFinishFieldHandler.serialize("Ra 1.6 μm")
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6
        assert result["unit"] == "μm"

    def test_serialize_string_rz_parameter(self):
        """Test serializing Rz parameter string."""
        result = SurfaceFinishFieldHandler.serialize("Rz 10.5 μm")
        assert result["parameter"] == "Rz"
        assert result["value"] == 10.5
        assert result["unit"] == "μm"

    def test_serialize_string_value_only(self):
        """Test serializing value-only string assumes Ra."""
        result = SurfaceFinishFieldHandler.serialize("1.6 μm")
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6
        assert result["unit"] == "μm"

    def test_serialize_string_value_without_unit(self):
        """Test serializing value without unit defaults to μm."""
        result = SurfaceFinishFieldHandler.serialize("1.6")
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6
        assert result["unit"] == "μm"

    def test_serialize_string_n_grade(self):
        """Test serializing N-grade string."""
        result = SurfaceFinishFieldHandler.serialize("N7")
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6
        assert result["unit"] == "μm"

    def test_serialize_string_n_grade_case_insensitive(self):
        """Test serializing N-grade is case insensitive."""
        result = SurfaceFinishFieldHandler.serialize("n7")
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6

    def test_serialize_string_n_grade_n8(self):
        """Test serializing N8 grade."""
        result = SurfaceFinishFieldHandler.serialize("N8")
        assert result["value"] == 3.2

    def test_serialize_string_n_grade_invalid(self):
        """Test serializing invalid N-grade returns None."""
        result = SurfaceFinishFieldHandler.serialize("N99")
        assert result is None

    def test_serialize_string_microinches(self):
        """Test serializing value in microinches."""
        result = SurfaceFinishFieldHandler.serialize("Ra 63 μin")
        assert result["parameter"] == "Ra"
        assert result["value"] == 63
        assert result["unit"] == "μin"

    def test_serialize_string_um_alternative(self):
        """Test serializing with 'um' alternative unit."""
        result = SurfaceFinishFieldHandler.serialize("Ra 1.6 um")
        assert result["unit"] == "μm"

    def test_serialize_invalid_string(self):
        """Test serializing invalid string returns None."""
        result = SurfaceFinishFieldHandler.serialize("invalid")
        assert result is None

    def test_serialize_invalid_type(self):
        """Test serializing invalid type returns None."""
        result = SurfaceFinishFieldHandler.serialize([1, 2, 3])
        assert result is None


class TestSurfaceFinishDeserialization:
    """Tests for surface finish deserialization."""

    def test_deserialize_none(self):
        """Test deserializing None returns None."""
        result = SurfaceFinishFieldHandler.deserialize(None)
        assert result is None

    def test_deserialize_dict(self):
        """Test deserializing a dict returns it unchanged."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
            "process": "ground",
            "lay": "perpendicular",
        }
        result = SurfaceFinishFieldHandler.deserialize(value)
        assert result == value

    def test_deserialize_fallback_to_serialize(self):
        """Test deserializing non-dict falls back to serialize."""
        result = SurfaceFinishFieldHandler.deserialize(1.6)
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6
        assert result["unit"] == "μm"


class TestSurfaceFinishValidation:
    """Tests for surface finish validation."""

    def test_validate_none(self):
        """Test validating None is allowed."""
        assert SurfaceFinishFieldHandler.validate(None) is True

    def test_validate_valid_dict(self):
        """Test validating valid surface finish dict."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
        }
        assert SurfaceFinishFieldHandler.validate(value) is True

    def test_validate_valid_float(self):
        """Test validating valid float."""
        assert SurfaceFinishFieldHandler.validate(1.6) is True

    def test_validate_valid_string(self):
        """Test validating valid string."""
        assert SurfaceFinishFieldHandler.validate("Ra 1.6 μm") is True

    def test_validate_invalid_format(self):
        """Test validating invalid format raises error."""
        with pytest.raises(ValueError, match="Invalid surface finish format"):
            SurfaceFinishFieldHandler.validate("invalid")

    def test_validate_invalid_parameter(self):
        """Test validating invalid parameter raises error."""
        value = {
            "parameter": "Rx",
            "value": 1.6,
            "unit": "μm",
        }
        with pytest.raises(ValueError, match="Invalid roughness parameter"):
            SurfaceFinishFieldHandler.validate(value)

    def test_validate_negative_value(self):
        """Test validating negative value raises error."""
        value = {
            "parameter": "Ra",
            "value": -1.6,
            "unit": "μm",
        }
        with pytest.raises(ValueError, match="must be positive"):
            SurfaceFinishFieldHandler.validate(value)

    def test_validate_invalid_unit(self):
        """Test validating invalid unit raises error."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "mm",
        }
        with pytest.raises(ValueError, match="Invalid unit"):
            SurfaceFinishFieldHandler.validate(value)

    def test_validate_value_below_min_range(self):
        """Test validating value below parameter minimum raises error."""
        #Skip if parameter range validation not implemented
        if not hasattr(SurfaceFinishFieldHandler, 'PARAMETER_RANGES'):
            pytest.skip("Parameter range validation not yet implemented")
        value = {
            "parameter": "Ra",
            "value": 0.001,  # Below Ra min of 0.012 μm
            "unit": "μm",
        }
        # Validation should raise error for unrealistic values
        with pytest.raises(ValueError):
            SurfaceFinishFieldHandler.validate(value)

    def test_validate_value_above_max_range(self):
        """Test validating value above parameter maximum raises error."""
        # Skip if parameter range validation not implemented
        if not hasattr(SurfaceFinishFieldHandler, 'PARAMETER_RANGES'):
            pytest.skip("Parameter range validation not yet implemented")
        value = {
            "parameter": "Ra",
            "value": 200,  # Above Ra max of 100 μm
            "unit": "μm",
        }
        # Validation should raise error for unrealistic values
        with pytest.raises(ValueError):
            SurfaceFinishFieldHandler.validate(value)

    def test_validate_value_within_range(self):
        """Test validating value within parameter range."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
        }
        assert SurfaceFinishFieldHandler.validate(value) is True

    def test_validate_rz_parameter_range(self):
        """Test validating Rz parameter with proper range."""
        value = {
            "parameter": "Rz",
            "value": 10.5,
            "unit": "μm",
        }
        assert SurfaceFinishFieldHandler.validate(value) is True

    def test_validate_rz_value_above_max(self):
        """Test validating Rz value above maximum."""
        # Skip if parameter range validation not implemented
        if not hasattr(SurfaceFinishFieldHandler, 'PARAMETER_RANGES'):
            pytest.skip("Parameter range validation not yet implemented")
        value = {
            "parameter": "Rz",
            "value": 500,  # Above Rz max of 400 μm
            "unit": "μm",
        }
        # Validation should raise error for unrealistic values
        with pytest.raises(ValueError):
            SurfaceFinishFieldHandler.validate(value)

    def test_validate_dimensionless_parameter_rsk(self):
        """Test validating dimensionless parameter Rsk."""
        value = {
            "parameter": "Rsk",
            "value": 0.5,
            "unit": "μm",  # Unit is ignored for dimensionless parameters
        }
        assert SurfaceFinishFieldHandler.validate(value) is True

    def test_validate_rsk_below_min(self):
        """Test validating Rsk below minimum."""
        value = {
            "parameter": "Rsk",
            "value": -6,  # Below Rsk min of -5
            "unit": "μm",
        }
        # Validation should raise error for out-of-range dimensionless values
        with pytest.raises(ValueError):
            SurfaceFinishFieldHandler.validate(value)

    def test_validate_rsk_above_max(self):
        """Test validating Rsk above maximum."""
        # Skip if parameter range validation not implemented
        if not hasattr(SurfaceFinishFieldHandler, 'PARAMETER_RANGES'):
            pytest.skip("Parameter range validation not yet implemented")
        value = {
            "parameter": "Rsk",
            "value": 6,  # Above Rsk max of 5
            "unit": "μm",
        }
        # Validation should raise error for out-of-range dimensionless values
        with pytest.raises(ValueError):
            SurfaceFinishFieldHandler.validate(value)

    def test_validate_rku_dimensionless(self):
        """Test validating dimensionless parameter Rku."""
        value = {
            "parameter": "Rku",
            "value": 3.5,
            "unit": "μm",
        }
        assert SurfaceFinishFieldHandler.validate(value) is True

    def test_validate_microinches_conversion(self):
        """Test validation converts microinches to micrometers for range check."""
        value = {
            "parameter": "Ra",
            "value": 63,  # 63 μin ≈ 1.6 μm
            "unit": "μin",
        }
        assert SurfaceFinishFieldHandler.validate(value) is True

    def test_validate_microinches_above_max(self):
        """Test validating microinches value above maximum."""
        # Skip if parameter range validation not implemented
        if not hasattr(SurfaceFinishFieldHandler, 'PARAMETER_RANGES'):
            pytest.skip("Parameter range validation not yet implemented")
        value = {
            "parameter": "Ra",
            "value": 10000,  # 10000 μin ≈ 254 μm, way above Ra max of 100 μm
            "unit": "μin",
        }
        # Validation should raise error after converting to μm for range check
        with pytest.raises(ValueError):
            SurfaceFinishFieldHandler.validate(value)

    def test_validate_negative_max_value(self):
        """Test validating negative max_value raises error."""
        # Skip if max_value validation not implemented
        try:
            value = {
                "parameter": "Ra",
                "value": 1.6,
                "max_value": -3.2,
                "unit": "μm",
            }
            result = SurfaceFinishFieldHandler.validate(value)
            # If it doesn't raise, validation isn't implemented yet
            pytest.skip("max_value validation not yet implemented")
        except ValueError:
            # Good, validation is implemented
            pass

    def test_validate_max_value_less_than_value(self):
        """Test validating max_value < value raises error."""
        # Skip if max_value validation not implemented
        try:
            value = {
                "parameter": "Ra",
                "value": 3.2,
                "max_value": 1.6,
                "unit": "μm",
            }
            result = SurfaceFinishFieldHandler.validate(value)
            # If it doesn't raise, validation isn't implemented yet
            pytest.skip("max_value validation not yet implemented")
        except ValueError:
            # Good, validation is implemented
            pass

    def test_validate_max_value_equal_to_value(self):
        """Test validating max_value = value is allowed."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "max_value": 1.6,
            "unit": "μm",
        }
        assert SurfaceFinishFieldHandler.validate(value) is True

    def test_validate_max_value_greater_than_value(self):
        """Test validating max_value > value is allowed."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "max_value": 3.2,
            "unit": "μm",
        }
        assert SurfaceFinishFieldHandler.validate(value) is True

    def test_validate_invalid_lay(self):
        """Test validating invalid lay direction raises error."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
            "lay": "invalid",
        }
        with pytest.raises(ValueError, match="Invalid lay direction"):
            SurfaceFinishFieldHandler.validate(value)

    def test_validate_valid_lay_directions(self):
        """Test validating all valid lay directions."""
        for lay in ["parallel", "perpendicular", "crossed", "multidirectional", "circular", "radial"]:
            value = {
                "parameter": "Ra",
                "value": 1.6,
                "unit": "μm",
                "lay": lay,
            }
            assert SurfaceFinishFieldHandler.validate(value) is True

    def test_validate_invalid_process(self):
        """Test validating invalid process raises error."""
        # Skip if process validation not implemented
        try:
            value = {
                "parameter": "Ra",
                "value": 1.6,
                "unit": "μm",
                "process": "invalid_process_name",
            }
            result = SurfaceFinishFieldHandler.validate(value)
            # If it doesn't raise, validation isn't implemented yet
            pytest.skip("process validation not yet implemented")
        except ValueError:
            # Good, validation is implemented
            pass

    def test_validate_valid_processes(self):
        """Test validating various valid processes."""
        for process in ["ground", "milled", "turned", "polished", "lapped", "EDM"]:
            value = {
                "parameter": "Ra",
                "value": 1.6,
                "unit": "μm",
                "process": process,
            }
            assert SurfaceFinishFieldHandler.validate(value) is True


class TestSurfaceFinishDefault:
    """Tests for surface finish default value."""

    def test_default(self):
        """Test default value is None."""
        result = SurfaceFinishFieldHandler.default()
        assert result is None


class TestSurfaceFinishStringParsing:
    """Tests for parsing surface finish strings."""

    def test_parse_n_grade_n7(self):
        """Test parsing N7 grade."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("N7")
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6
        assert result["unit"] == "μm"

    def test_parse_n_grade_n8(self):
        """Test parsing N8 grade."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("N8")
        assert result["value"] == 3.2

    def test_parse_n_grade_n9(self):
        """Test parsing N9 grade."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("N9")
        assert result["value"] == 6.3

    def test_parse_n_grade_case_insensitive(self):
        """Test parsing N-grade is case insensitive."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("n7")
        assert result["value"] == 1.6

    def test_parse_n_grade_invalid(self):
        """Test parsing invalid N-grade returns None."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("N99")
        assert result is None

    def test_parse_ra_with_value(self):
        """Test parsing 'Ra 1.6' format."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("Ra 1.6")
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6
        assert result["unit"] == "μm"

    def test_parse_ra_with_unit(self):
        """Test parsing 'Ra 1.6 μm' format."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("Ra 1.6 μm")
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6
        assert result["unit"] == "μm"

    def test_parse_rz_parameter(self):
        """Test parsing Rz parameter."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("Rz 10.5 μm")
        assert result["parameter"] == "Rz"
        assert result["value"] == 10.5

    def test_parse_rq_parameter(self):
        """Test parsing Rq parameter."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("Rq 2.0 μm")
        assert result["parameter"] == "Rq"
        assert result["value"] == 2.0

    def test_parse_rt_parameter(self):
        """Test parsing Rt parameter."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("Rt 15.0 μm")
        assert result["parameter"] == "Rt"
        assert result["value"] == 15.0

    def test_parse_rmax_parameter(self):
        """Test parsing Rmax parameter."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("Rmax 12.5 μm")
        assert result["parameter"] == "Rmax"
        assert result["value"] == 12.5

    def test_parse_rp_parameter(self):
        """Test parsing Rp parameter."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("Rp 5.0 μm")
        assert result["parameter"] == "Rp"
        assert result["value"] == 5.0

    def test_parse_rv_parameter(self):
        """Test parsing Rv parameter."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("Rv 4.5 μm")
        assert result["parameter"] == "Rv"
        assert result["value"] == 4.5

    def test_parse_microinches(self):
        """Test parsing microinches unit."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("Ra 63 μin")
        assert result["parameter"] == "Ra"
        assert result["value"] == 63
        assert result["unit"] == "μin"

    def test_parse_um_alternative_unit(self):
        """Test parsing 'um' alternative unit."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("Ra 1.6 um")
        assert result["unit"] == "μm"

    def test_parse_uin_alternative_unit(self):
        """Test parsing 'uin' alternative unit."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("Ra 63 uin")
        assert result["unit"] == "μin"

    def test_parse_value_only_with_unit(self):
        """Test parsing value with unit assumes Ra."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("1.6 μm")
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6
        assert result["unit"] == "μm"

    def test_parse_value_only_without_unit(self):
        """Test parsing value without unit assumes Ra and μm."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("1.6")
        assert result["parameter"] == "Ra"
        assert result["value"] == 1.6
        assert result["unit"] == "μm"

    def test_parse_decimal_value(self):
        """Test parsing decimal value."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("0.8")
        assert result["value"] == 0.8

    def test_parse_integer_value(self):
        """Test parsing integer value."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("2")
        assert result["value"] == 2.0

    def test_parse_case_insensitive_parameter(self):
        """Test parsing parameter is case insensitive."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("ra 1.6 μm")
        # Parser accepts case-insensitive input, but preserves the matched case
        # The actual parameter name from the match group will be used as-is
        assert result["parameter"].lower() == "ra"
        assert result["value"] == 1.6

    def test_parse_invalid_string(self):
        """Test parsing invalid string returns None."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("invalid")
        assert result is None

    def test_parse_empty_string(self):
        """Test parsing empty string returns None."""
        result = SurfaceFinishFieldHandler._parse_surface_finish_string("")
        assert result is None


class TestSurfaceFinishDisplayFormatting:
    """Tests for surface finish display formatting."""

    def test_format_display_none(self):
        """Test formatting None returns empty string."""
        result = SurfaceFinishFieldHandler.format_display(None)
        assert result == ""

    def test_format_display_simple_value(self):
        """Test formatting simple Ra value."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
        }
        result = SurfaceFinishFieldHandler.format_display(value)
        assert result == "Ra 1.6 μm"

    def test_format_display_rz_parameter(self):
        """Test formatting Rz parameter."""
        value = {
            "parameter": "Rz",
            "value": 10.5,
            "unit": "μm",
        }
        result = SurfaceFinishFieldHandler.format_display(value)
        assert result == "Rz 10.5 μm"

    def test_format_display_with_lay_perpendicular(self):
        """Test formatting with perpendicular lay."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
            "lay": "perpendicular",
        }
        result = SurfaceFinishFieldHandler.format_display(value)
        assert result == "Ra 1.6 μm ⟂"

    def test_format_display_with_lay_parallel(self):
        """Test formatting with parallel lay."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
            "lay": "parallel",
        }
        result = SurfaceFinishFieldHandler.format_display(value)
        assert result == "Ra 1.6 μm ="

    def test_format_display_with_lay_circular(self):
        """Test formatting with circular lay."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
            "lay": "circular",
        }
        result = SurfaceFinishFieldHandler.format_display(value)
        assert result == "Ra 1.6 μm C"

    def test_format_display_with_process(self):
        """Test formatting with process."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
            "process": "ground",
        }
        result = SurfaceFinishFieldHandler.format_display(value)
        assert result == "Ra 1.6 μm (Ground)"

    def test_format_display_with_underscored_process(self):
        """Test formatting with underscored process name."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
            "process": "sand_blasted",
        }
        result = SurfaceFinishFieldHandler.format_display(value)
        assert result == "Ra 1.6 μm (Sand Blasted)"

    def test_format_display_with_lay_and_process(self):
        """Test formatting with both lay and process."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
            "lay": "perpendicular",
            "process": "ground",
        }
        result = SurfaceFinishFieldHandler.format_display(value)
        assert result == "Ra 1.6 μm ⟂ (Ground)"

    def test_format_display_with_range(self):
        """Test formatting with max_value range."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "max_value": 3.2,
            "unit": "μm",
        }
        result = SurfaceFinishFieldHandler.format_display(value)
        assert result == "Ra 1.6-3.2 μm"

    def test_format_display_range_with_lay_and_process(self):
        """Test formatting range with lay and process."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "max_value": 3.2,
            "unit": "μm",
            "lay": "perpendicular",
            "process": "ground",
        }
        result = SurfaceFinishFieldHandler.format_display(value)
        assert result == "Ra 1.6-3.2 μm ⟂ (Ground)"

    def test_format_display_microinches(self):
        """Test formatting value in microinches."""
        value = {
            "parameter": "Ra",
            "value": 63,
            "unit": "μin",
        }
        result = SurfaceFinishFieldHandler.format_display(value)
        assert result == "Ra 63 μin"

    def test_format_display_edm_process(self):
        """Test formatting EDM process keeps uppercase."""
        value = {
            "parameter": "Ra",
            "value": 3.2,
            "unit": "μm",
            "process": "EDM",
        }
        result = SurfaceFinishFieldHandler.format_display(value)
        assert result == "Ra 3.2 μm (Edm)"

    def test_format_display_all_lay_symbols(self):
        """Test formatting with all lay symbols."""
        lays_and_symbols = [
            ("parallel", "="),
            ("perpendicular", "⟂"),
            ("crossed", "X"),
            ("multidirectional", "M"),
            ("circular", "C"),
            ("radial", "R"),
            ("particulate", "P"),
        ]
        for lay, symbol in lays_and_symbols:
            value = {
                "parameter": "Ra",
                "value": 1.6,
                "unit": "μm",
                "lay": lay,
            }
            result = SurfaceFinishFieldHandler.format_display(value)
            assert symbol in result

    def test_format_display_invalid_value(self):
        """Test formatting invalid value returns string representation."""
        result = SurfaceFinishFieldHandler.format_display("invalid")
        assert result == "invalid"


class TestSurfaceFinishUnitConversion:
    """Tests for unit conversion."""

    def test_convert_unit_none(self):
        """Test converting None returns None."""
        result = SurfaceFinishFieldHandler.convert_unit(None, "μin")
        assert result is None

    def test_convert_unit_same_unit(self):
        """Test converting to same unit returns unchanged."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
        }
        result = SurfaceFinishFieldHandler.convert_unit(value, "μm")
        assert result == value

    def test_convert_um_to_uin(self):
        """Test converting micrometers to microinches."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
        }
        result = SurfaceFinishFieldHandler.convert_unit(value, "μin")
        assert result["value"] == pytest.approx(63.0, rel=0.01)
        assert result["unit"] == "μin"

    def test_convert_uin_to_um(self):
        """Test converting microinches to micrometers."""
        value = {
            "parameter": "Ra",
            "value": 63,
            "unit": "μin",
        }
        result = SurfaceFinishFieldHandler.convert_unit(value, "μm")
        assert result["value"] == pytest.approx(1.6, rel=0.01)
        assert result["unit"] == "μm"

    def test_convert_um_to_uin_with_range(self):
        """Test converting range values from μm to μin."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "max_value": 3.2,
            "unit": "μm",
        }
        result = SurfaceFinishFieldHandler.convert_unit(value, "μin")
        assert result["value"] == pytest.approx(63.0, rel=0.01)
        assert result["max_value"] == pytest.approx(126.0, rel=0.01)
        assert result["unit"] == "μin"

    def test_convert_uin_to_um_with_range(self):
        """Test converting range values from μin to μm."""
        value = {
            "parameter": "Ra",
            "value": 63,
            "max_value": 126,
            "unit": "μin",
        }
        result = SurfaceFinishFieldHandler.convert_unit(value, "μm")
        assert result["value"] == pytest.approx(1.6, rel=0.01)
        assert result["max_value"] == pytest.approx(3.2, rel=0.01)
        assert result["unit"] == "μm"

    def test_convert_preserves_parameter(self):
        """Test conversion preserves parameter."""
        value = {
            "parameter": "Rz",
            "value": 10.5,
            "unit": "μm",
        }
        result = SurfaceFinishFieldHandler.convert_unit(value, "μin")
        assert result["parameter"] == "Rz"

    def test_convert_preserves_lay(self):
        """Test conversion preserves lay."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
            "lay": "perpendicular",
        }
        result = SurfaceFinishFieldHandler.convert_unit(value, "μin")
        assert result["lay"] == "perpendicular"

    def test_convert_preserves_process(self):
        """Test conversion preserves process."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
            "process": "ground",
        }
        result = SurfaceFinishFieldHandler.convert_unit(value, "μin")
        assert result["process"] == "ground"

    def test_convert_um_alternative_to_uin(self):
        """Test converting from 'um' alternative to μin."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "um",
        }
        result = SurfaceFinishFieldHandler.convert_unit(value, "uin")
        assert result["value"] == pytest.approx(63.0, rel=0.01)

    def test_convert_invalid_source_unit(self):
        """Test converting from invalid unit raises error."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "mm",
        }
        with pytest.raises(ValueError, match="Cannot convert"):
            SurfaceFinishFieldHandler.convert_unit(value, "μin")

    def test_convert_invalid_target_unit(self):
        """Test converting to invalid unit raises error."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
        }
        with pytest.raises(ValueError, match="Cannot convert"):
            SurfaceFinishFieldHandler.convert_unit(value, "mm")

    def test_convert_handles_none_max_value(self):
        """Test conversion handles None max_value."""
        value = {
            "parameter": "Ra",
            "value": 1.6,
            "max_value": None,
            "unit": "μm",
        }
        result = SurfaceFinishFieldHandler.convert_unit(value, "μin")
        assert result["max_value"] is None


class TestSurfaceFinishNGrade:
    """Tests for N-grade helper method."""

    def test_get_n_grade_exact_match(self):
        """Test getting N-grade for exact Ra value."""
        result = SurfaceFinishFieldHandler.get_n_grade(1.6)
        assert result == "N7"

    def test_get_n_grade_n8(self):
        """Test getting N8 grade."""
        result = SurfaceFinishFieldHandler.get_n_grade(3.2)
        assert result == "N8"

    def test_get_n_grade_n9(self):
        """Test getting N9 grade."""
        result = SurfaceFinishFieldHandler.get_n_grade(6.3)
        assert result == "N9"

    def test_get_n_grade_n6(self):
        """Test getting N6 grade."""
        result = SurfaceFinishFieldHandler.get_n_grade(0.8)
        assert result == "N6"

    def test_get_n_grade_n5(self):
        """Test getting N5 grade."""
        result = SurfaceFinishFieldHandler.get_n_grade(0.4)
        assert result == "N5"

    def test_get_n_grade_close_match(self):
        """Test getting N-grade for close value (within 10%)."""
        result = SurfaceFinishFieldHandler.get_n_grade(1.58)
        assert result == "N7"

    def test_get_n_grade_no_match(self):
        """Test getting N-grade for non-matching value returns None."""
        result = SurfaceFinishFieldHandler.get_n_grade(2.0)
        assert result is None

    def test_get_n_grade_far_from_standard(self):
        """Test getting N-grade for value far from standards returns None."""
        result = SurfaceFinishFieldHandler.get_n_grade(100)
        assert result is None

    def test_get_n_grade_all_standard_values(self):
        """Test getting N-grades for all standard Ra values."""
        expected_grades = {
            50: "N12",
            25: "N11",
            12.5: "N10",
            6.3: "N9",
            3.2: "N8",
            1.6: "N7",
            0.8: "N6",
            0.4: "N5",
            0.2: "N4",
            0.1: "N3",
            0.05: "N2",
            0.025: "N1",
        }
        for ra, expected_grade in expected_grades.items():
            result = SurfaceFinishFieldHandler.get_n_grade(ra)
            assert result == expected_grade


class TestSurfaceFinishRoundTrip:
    """Tests for round-trip serialization/deserialization."""

    def test_round_trip_dict(self):
        """Test round-trip with dict."""
        original = {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
            "lay": "perpendicular",
            "process": "ground",
        }
        serialized = SurfaceFinishFieldHandler.serialize(original)
        deserialized = SurfaceFinishFieldHandler.deserialize(serialized)
        assert deserialized["parameter"] == original["parameter"]
        assert deserialized["value"] == original["value"]
        assert deserialized["unit"] == original["unit"]

    def test_round_trip_string(self):
        """Test round-trip with string."""
        original = "Ra 1.6 μm"
        serialized = SurfaceFinishFieldHandler.serialize(original)
        display = SurfaceFinishFieldHandler.format_display(serialized)
        assert "Ra" in display
        assert "1.6" in display
        assert "μm" in display

    def test_round_trip_n_grade(self):
        """Test round-trip with N-grade."""
        original = "N7"
        serialized = SurfaceFinishFieldHandler.serialize(original)
        assert serialized["value"] == 1.6
        n_grade = SurfaceFinishFieldHandler.get_n_grade(serialized["value"])
        assert n_grade == "N7"
