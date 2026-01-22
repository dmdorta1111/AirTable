"""Unit tests for MaterialFieldHandler."""

import pytest

from pybase.fields.types.engineering.material import MaterialFieldHandler


class TestMaterialFieldHandler:
    """Tests for MaterialFieldHandler class."""

    def test_field_type(self):
        """Test field type identifier."""
        assert MaterialFieldHandler.field_type == "material"

    def test_families_defined(self):
        """Test that material families are properly defined."""
        assert "carbon_steel" in MaterialFieldHandler.FAMILIES
        assert "stainless_steel" in MaterialFieldHandler.FAMILIES
        assert "aluminum" in MaterialFieldHandler.FAMILIES
        assert "titanium" in MaterialFieldHandler.FAMILIES
        assert "plastic" in MaterialFieldHandler.FAMILIES

    def test_standards_defined(self):
        """Test that material standards are properly defined."""
        assert "ASTM" in MaterialFieldHandler.STANDARDS
        assert "AISI" in MaterialFieldHandler.STANDARDS
        assert "ISO" in MaterialFieldHandler.STANDARDS
        assert "DIN" in MaterialFieldHandler.STANDARDS
        assert "SAE" in MaterialFieldHandler.STANDARDS

    def test_conditions_defined(self):
        """Test that heat treatment conditions are properly defined."""
        assert "annealed" in MaterialFieldHandler.CONDITIONS
        assert "hardened" in MaterialFieldHandler.CONDITIONS
        assert "cold_worked" in MaterialFieldHandler.CONDITIONS
        assert "as_cast" in MaterialFieldHandler.CONDITIONS

    def test_property_ranges_defined(self):
        """Test that property ranges are properly defined."""
        assert "density" in MaterialFieldHandler.PROPERTY_RANGES
        assert "yield_strength" in MaterialFieldHandler.PROPERTY_RANGES
        assert "tensile_strength" in MaterialFieldHandler.PROPERTY_RANGES
        assert MaterialFieldHandler.PROPERTY_RANGES["density"]["unit"] == "kg/m³"
        assert MaterialFieldHandler.PROPERTY_RANGES["yield_strength"]["unit"] == "MPa"


class TestMaterialSerialization:
    """Tests for material serialization."""

    def test_serialize_none(self):
        """Test serializing None returns None."""
        result = MaterialFieldHandler.serialize(None)
        assert result is None

    def test_serialize_dict_full(self):
        """Test serializing a complete dict."""
        value = {
            "designation": "AISI 304",
            "standard": "AISI",
            "family": "stainless_steel",
            "condition": "annealed",
            "properties": {
                "density": 8000,
                "yield_strength": 215,
            },
            "notes": "Test material",
        }
        result = MaterialFieldHandler.serialize(value)
        assert result["designation"] == "AISI 304"
        assert result["standard"] == "AISI"
        assert result["family"] == "stainless_steel"
        assert result["condition"] == "annealed"
        assert result["properties"]["density"] == 8000
        assert result["notes"] == "Test material"

    def test_serialize_dict_minimal(self):
        """Test serializing minimal dict with only designation."""
        value = {"designation": "AISI 304"}
        result = MaterialFieldHandler.serialize(value)
        assert result["designation"] == "AISI 304"
        assert result["standard"] is None
        assert result["family"] is None
        assert result["condition"] is None
        assert result["properties"] == {}

    def test_serialize_string(self):
        """Test serializing string designation."""
        result = MaterialFieldHandler.serialize("AISI 304")
        assert result["designation"] == "AISI 304"
        assert result["standard"] is None
        assert result["family"] == "stainless_steel"  # Guessed from designation
        assert result["condition"] is None
        assert result["properties"] == {}

    def test_serialize_string_aluminum(self):
        """Test serializing aluminum designation."""
        result = MaterialFieldHandler.serialize("6061-T6")
        assert result["designation"] == "6061-T6"
        assert result["family"] == "aluminum"

    def test_serialize_invalid_type(self):
        """Test serializing invalid type returns None."""
        result = MaterialFieldHandler.serialize([1, 2, 3])
        assert result is None

    def test_serialize_invalid_number(self):
        """Test serializing number returns None."""
        result = MaterialFieldHandler.serialize(123)
        assert result is None


class TestMaterialDeserialization:
    """Tests for material deserialization."""

    def test_deserialize_none(self):
        """Test deserializing None returns None."""
        result = MaterialFieldHandler.deserialize(None)
        assert result is None

    def test_deserialize_dict(self):
        """Test deserializing a dict returns it unchanged."""
        value = {
            "designation": "AISI 304",
            "standard": "AISI",
            "family": "stainless_steel",
            "condition": "annealed",
            "properties": {},
        }
        result = MaterialFieldHandler.deserialize(value)
        assert result == value

    def test_deserialize_fallback_to_serialize(self):
        """Test deserializing non-dict falls back to serialize."""
        result = MaterialFieldHandler.deserialize("AISI 304")
        assert result["designation"] == "AISI 304"
        assert result["family"] == "stainless_steel"


class TestMaterialValidation:
    """Tests for material validation."""

    def test_validate_none(self):
        """Test validating None is allowed."""
        assert MaterialFieldHandler.validate(None) is True

    def test_validate_valid_dict(self):
        """Test validating valid material dict."""
        value = {
            "designation": "AISI 304",
            "standard": "AISI",
            "family": "stainless_steel",
            "condition": "annealed",
            "properties": {"density": 8000},
        }
        assert MaterialFieldHandler.validate(value) is True

    def test_validate_valid_string(self):
        """Test validating valid string."""
        assert MaterialFieldHandler.validate("AISI 304") is True

    def test_validate_missing_designation(self):
        """Test validating dict without designation raises error."""
        value = {
            "standard": "AISI",
            "family": "stainless_steel",
        }
        with pytest.raises(ValueError, match="must have a designation"):
            MaterialFieldHandler.validate(value)

    def test_validate_invalid_family(self):
        """Test validating invalid family raises error."""
        value = {
            "designation": "AISI 304",
            "family": "invalid_family",
        }
        with pytest.raises(ValueError, match="Invalid material family"):
            MaterialFieldHandler.validate(value)

    def test_validate_invalid_standard(self):
        """Test validating invalid standard raises error."""
        value = {
            "designation": "AISI 304",
            "standard": "INVALID",
        }
        with pytest.raises(ValueError, match="Invalid standard"):
            MaterialFieldHandler.validate(value)

    def test_validate_invalid_condition(self):
        """Test validating invalid condition raises error."""
        value = {
            "designation": "AISI 304",
            "condition": "invalid_condition",
        }
        with pytest.raises(ValueError, match="Invalid condition"):
            MaterialFieldHandler.validate(value)

    def test_validate_invalid_property_type(self):
        """Test validating non-numeric property raises error."""
        value = {
            "designation": "AISI 304",
            "properties": {"density": "not_a_number"},
        }
        with pytest.raises(ValueError, match="must be numeric"):
            MaterialFieldHandler.validate(value)

    def test_validate_property_below_range(self):
        """Test validating property below valid range raises error."""
        value = {
            "designation": "AISI 304",
            "properties": {"density": 0.1},  # Below min of 0.5
        }
        with pytest.raises(ValueError, match="out of valid range"):
            MaterialFieldHandler.validate(value)

    def test_validate_property_above_range(self):
        """Test validating property above valid range raises error."""
        value = {
            "designation": "AISI 304",
            "properties": {"density": 30000},  # Above max of 22600
        }
        with pytest.raises(ValueError, match="out of valid range"):
            MaterialFieldHandler.validate(value)

    def test_validate_property_within_range(self):
        """Test validating property within valid range passes."""
        value = {
            "designation": "AISI 304",
            "properties": {
                "density": 8000,
                "yield_strength": 215,
                "tensile_strength": 505,
            },
        }
        assert MaterialFieldHandler.validate(value) is True

    def test_validate_hardness_properties(self):
        """Test validating different hardness scales."""
        # Valid hardness values
        value = {
            "designation": "AISI 304",
            "properties": {
                "hardness_hb": 150,
                "hardness_hrc": 25,
                "hardness_hrb": 92,
            },
        }
        assert MaterialFieldHandler.validate(value) is True

    def test_validate_hardness_hrc_out_of_range(self):
        """Test validating HRC hardness out of range raises error."""
        value = {
            "designation": "Tool Steel",
            "properties": {"hardness_hrc": 75},  # Above max of 70
        }
        with pytest.raises(ValueError, match="out of valid range"):
            MaterialFieldHandler.validate(value)

    def test_validate_standard_family_compatibility_valid(self):
        """Test validating compatible standard-family combination."""
        value = {
            "designation": "304",
            "standard": "AISI",
            "family": "stainless_steel",
        }
        assert MaterialFieldHandler.validate(value) is True

    def test_validate_standard_family_compatibility_invalid(self):
        """Test validating incompatible standard-family combination raises error."""
        value = {
            "designation": "6061",
            "standard": "AISI",  # AISI is for steels, not aluminum
            "family": "aluminum",
        }
        with pytest.raises(ValueError, match="not typically used for"):
            MaterialFieldHandler.validate(value)

    def test_validate_standard_family_compatibility_universal(self):
        """Test universal standards (ASTM, ISO) work with all families."""
        value = {
            "designation": "6061",
            "standard": "ASTM",
            "family": "aluminum",
        }
        assert MaterialFieldHandler.validate(value) is True

        value = {
            "designation": "304",
            "standard": "ISO",
            "family": "stainless_steel",
        }
        assert MaterialFieldHandler.validate(value) is True

    def test_validate_with_allowed_families_pass(self):
        """Test validation passes with allowed families."""
        value = {
            "designation": "AISI 304",
            "family": "stainless_steel",
        }
        options = {"allowed_families": ["stainless_steel", "aluminum"]}
        assert MaterialFieldHandler.validate(value, options) is True

    def test_validate_with_allowed_families_fail(self):
        """Test validation fails with disallowed family."""
        value = {
            "designation": "Ti-6Al-4V",
            "family": "titanium",
        }
        options = {"allowed_families": ["stainless_steel", "aluminum"]}
        with pytest.raises(ValueError, match="not allowed"):
            MaterialFieldHandler.validate(value, options)

    def test_validate_require_standard_pass(self):
        """Test validation passes with required standard present."""
        value = {
            "designation": "304",
            "standard": "AISI",
        }
        options = {"require_standard": True}
        assert MaterialFieldHandler.validate(value, options) is True

    def test_validate_require_standard_fail(self):
        """Test validation fails when standard is required but missing."""
        value = {"designation": "304"}
        options = {"require_standard": True}
        with pytest.raises(ValueError, match="standard is required"):
            MaterialFieldHandler.validate(value, options)

    def test_validate_require_properties_pass(self):
        """Test validation passes with required properties present."""
        value = {
            "designation": "304",
            "properties": {"density": 8000},
        }
        options = {"require_properties": True}
        assert MaterialFieldHandler.validate(value, options) is True

    def test_validate_require_properties_fail(self):
        """Test validation fails when properties are required but missing."""
        value = {"designation": "304"}
        options = {"require_properties": True}
        with pytest.raises(ValueError, match="properties are required"):
            MaterialFieldHandler.validate(value, options)

    def test_validate_required_specific_properties_pass(self):
        """Test validation passes with specific required properties."""
        value = {
            "designation": "304",
            "properties": {
                "density": 8000,
                "yield_strength": 215,
            },
        }
        options = {"required_properties": ["density", "yield_strength"]}
        assert MaterialFieldHandler.validate(value, options) is True

    def test_validate_required_specific_properties_fail(self):
        """Test validation fails when specific required properties are missing."""
        value = {
            "designation": "304",
            "properties": {"density": 8000},
        }
        options = {"required_properties": ["density", "yield_strength"]}
        with pytest.raises(ValueError, match="Missing required properties"):
            MaterialFieldHandler.validate(value, options)

    def test_validate_invalid_format(self):
        """Test validating invalid format raises error."""
        with pytest.raises(ValueError, match="Invalid material format"):
            MaterialFieldHandler.validate([1, 2, 3])


class TestMaterialDefault:
    """Tests for material default value."""

    def test_default(self):
        """Test default value is None."""
        result = MaterialFieldHandler.default()
        assert result is None


class TestMaterialGuesFamily:
    """Tests for _guess_family helper method."""

    def test_guess_family_stainless_steel_304(self):
        """Test guessing stainless steel from 304."""
        result = MaterialFieldHandler._guess_family("304")
        assert result == "stainless_steel"

    def test_guess_family_stainless_steel_316(self):
        """Test guessing stainless steel from 316."""
        result = MaterialFieldHandler._guess_family("316L")
        assert result == "stainless_steel"

    def test_guess_family_aluminum_6061(self):
        """Test guessing aluminum from 6061."""
        result = MaterialFieldHandler._guess_family("6061-T6")
        assert result == "aluminum"

    def test_guess_family_aluminum_7075(self):
        """Test guessing aluminum from 7075."""
        result = MaterialFieldHandler._guess_family("7075-T6")
        assert result == "aluminum"

    def test_guess_family_alloy_steel_4140(self):
        """Test guessing alloy steel from 4140."""
        result = MaterialFieldHandler._guess_family("4140")
        assert result == "alloy_steel"

    def test_guess_family_alloy_steel_1045(self):
        """Test guessing alloy steel from 1045."""
        result = MaterialFieldHandler._guess_family("1045")
        assert result == "alloy_steel"

    def test_guess_family_tool_steel_a2(self):
        """Test guessing tool steel from A2."""
        result = MaterialFieldHandler._guess_family("A2")
        assert result == "tool_steel"

    def test_guess_family_tool_steel_d2(self):
        """Test guessing tool steel from D2."""
        result = MaterialFieldHandler._guess_family("D2")
        assert result == "tool_steel"

    def test_guess_family_titanium(self):
        """Test guessing titanium from designation."""
        result = MaterialFieldHandler._guess_family("Ti-6Al-4V")
        assert result == "titanium"

    def test_guess_family_titanium_grade(self):
        """Test guessing titanium from grade designation."""
        result = MaterialFieldHandler._guess_family("GRADE 5")
        assert result == "titanium"

    def test_guess_family_brass(self):
        """Test guessing brass from designation."""
        result = MaterialFieldHandler._guess_family("C260 BRASS")
        assert result == "brass"

    def test_guess_family_brass_c36(self):
        """Test guessing brass from C36x designation."""
        result = MaterialFieldHandler._guess_family("C360")
        assert result == "brass"

    def test_guess_family_unknown(self):
        """Test guessing returns None for unknown designation."""
        result = MaterialFieldHandler._guess_family("UNKNOWN MATERIAL")
        assert result is None

    def test_guess_family_case_insensitive(self):
        """Test guessing is case insensitive."""
        result = MaterialFieldHandler._guess_family("aisi 304")
        assert result == "stainless_steel"


class TestMaterialFormatDisplay:
    """Tests for material display formatting."""

    def test_format_display_none(self):
        """Test formatting None returns empty string."""
        result = MaterialFieldHandler.format_display(None)
        assert result == ""

    def test_format_display_simple_designation(self):
        """Test formatting simple designation."""
        value = {"designation": "AISI 304"}
        result = MaterialFieldHandler.format_display(value)
        assert "AISI 304" in result

    def test_format_display_with_family(self):
        """Test formatting with family."""
        value = {
            "designation": "304",
            "family": "stainless_steel",
        }
        result = MaterialFieldHandler.format_display(value)
        assert "304" in result
        assert "Stainless Steel" in result

    def test_format_display_with_standard_and_family(self):
        """Test formatting with standard and family."""
        value = {
            "designation": "304",
            "standard": "AISI",
            "family": "stainless_steel",
        }
        result = MaterialFieldHandler.format_display(value)
        assert "AISI 304" in result
        assert "Stainless Steel" in result

    def test_format_display_with_condition(self):
        """Test formatting with condition."""
        value = {
            "designation": "304",
            "family": "stainless_steel",
            "condition": "annealed",
        }
        result = MaterialFieldHandler.format_display(value)
        assert "304" in result
        assert "Stainless Steel" in result
        assert "Annealed" in result

    def test_format_display_full(self):
        """Test formatting complete material specification."""
        value = {
            "designation": "304",
            "standard": "AISI",
            "family": "stainless_steel",
            "condition": "annealed",
        }
        result = MaterialFieldHandler.format_display(value)
        assert "AISI 304" in result
        assert "Stainless Steel" in result
        assert "Annealed" in result

    def test_format_display_designation_with_standard_prefix(self):
        """Test formatting when designation already includes standard."""
        value = {
            "designation": "AISI 304",
            "standard": "AISI",
            "family": "stainless_steel",
        }
        result = MaterialFieldHandler.format_display(value)
        # Should not duplicate "AISI"
        assert result.count("AISI") == 1

    def test_format_display_invalid_value(self):
        """Test formatting invalid value returns string representation."""
        result = MaterialFieldHandler.format_display("invalid")
        assert result == "invalid"

    def test_format_display_string_input(self):
        """Test formatting string input."""
        result = MaterialFieldHandler.format_display("AISI 304")
        assert "304" in result


class TestMaterialFormatProperties:
    """Tests for material properties formatting."""

    def test_format_properties_none(self):
        """Test formatting None returns empty string."""
        result = MaterialFieldHandler.format_properties(None)
        assert result == ""

    def test_format_properties_no_properties(self):
        """Test formatting material without properties returns empty string."""
        value = {"designation": "304"}
        result = MaterialFieldHandler.format_properties(value)
        assert result == ""

    def test_format_properties_density(self):
        """Test formatting density property."""
        value = {
            "designation": "304",
            "properties": {"density": 8000},
        }
        result = MaterialFieldHandler.format_properties(value)
        assert "Density: 8000 kg/m³" in result

    def test_format_properties_multiple(self):
        """Test formatting multiple properties."""
        value = {
            "designation": "304",
            "properties": {
                "density": 8000,
                "yield_strength": 215,
                "tensile_strength": 505,
            },
        }
        result = MaterialFieldHandler.format_properties(value)
        assert "Density: 8000 kg/m³" in result
        assert "Yield Strength: 215 MPa" in result
        assert "Tensile Strength: 505 MPa" in result

    def test_format_properties_hardness(self):
        """Test formatting hardness property."""
        value = {
            "designation": "304",
            "properties": {"hardness": "HRB 92"},
        }
        result = MaterialFieldHandler.format_properties(value)
        assert "Hardness: HRB 92" in result

    def test_format_properties_thermal(self):
        """Test formatting thermal properties."""
        value = {
            "designation": "304",
            "properties": {
                "thermal_conductivity": 16.2,
                "melting_point": 1400,
            },
        }
        result = MaterialFieldHandler.format_properties(value)
        assert "Thermal Conductivity: 16.2 W/m·K" in result
        assert "Melting Point: 1400 °C" in result

    def test_format_properties_all(self):
        """Test formatting all supported properties."""
        value = {
            "designation": "304",
            "properties": {
                "density": 8000,
                "yield_strength": 215,
                "tensile_strength": 505,
                "elongation": 40,
                "modulus": 193,
                "hardness": "HRB 92",
                "thermal_conductivity": 16.2,
                "melting_point": 1400,
            },
        }
        result = MaterialFieldHandler.format_properties(value)
        assert "Density: 8000 kg/m³" in result
        assert "Yield Strength: 215 MPa" in result
        assert "Tensile Strength: 505 MPa" in result
        assert "Elongation: 40 %" in result
        assert "Elastic Modulus: 193 GPa" in result
        assert "Hardness: HRB 92" in result
        assert "Thermal Conductivity: 16.2 W/m·K" in result
        assert "Melting Point: 1400 °C" in result


class TestMaterialGetCommonMaterials:
    """Tests for get_common_materials method."""

    def test_get_common_stainless_steel(self):
        """Test getting common stainless steel materials."""
        result = MaterialFieldHandler.get_common_materials("stainless_steel")
        assert len(result) > 0
        assert any(m["designation"] == "304" for m in result)
        assert any(m["designation"] == "316" for m in result)

    def test_get_common_aluminum(self):
        """Test getting common aluminum materials."""
        result = MaterialFieldHandler.get_common_materials("aluminum")
        assert len(result) > 0
        assert any(m["designation"] == "6061-T6" for m in result)
        assert any(m["designation"] == "7075-T6" for m in result)

    def test_get_common_alloy_steel(self):
        """Test getting common alloy steel materials."""
        result = MaterialFieldHandler.get_common_materials("alloy_steel")
        assert len(result) > 0
        assert any(m["designation"] == "4140" for m in result)
        assert any(m["designation"] == "4340" for m in result)

    def test_get_common_tool_steel(self):
        """Test getting common tool steel materials."""
        result = MaterialFieldHandler.get_common_materials("tool_steel")
        assert len(result) > 0
        assert any(m["designation"] == "A2" for m in result)
        assert any(m["designation"] == "D2" for m in result)

    def test_get_common_unknown_family(self):
        """Test getting common materials for unknown family returns empty list."""
        result = MaterialFieldHandler.get_common_materials("unknown_family")
        assert result == []

    def test_get_common_materials_structure(self):
        """Test common materials have proper structure."""
        result = MaterialFieldHandler.get_common_materials("stainless_steel")
        for material in result:
            assert "designation" in material
            assert "standard" in material
            assert "family" in material
