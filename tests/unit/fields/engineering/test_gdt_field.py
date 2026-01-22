"""Unit tests for GDTFieldHandler."""

import pytest

from pybase.fields.types.engineering.gdt import GDTFieldHandler


class TestGDTFieldHandler:
    """Tests for GDTFieldHandler class."""

    def test_field_type(self):
        """Test field type identifier."""
        assert GDTFieldHandler.field_type == "gdt"

    def test_gdt_types_defined(self):
        """Test that GD&T types are properly defined."""
        # Form tolerances
        assert "straightness" in GDTFieldHandler.GDT_TYPES
        assert "flatness" in GDTFieldHandler.GDT_TYPES
        assert "circularity" in GDTFieldHandler.GDT_TYPES
        assert "cylindricity" in GDTFieldHandler.GDT_TYPES

        # Orientation tolerances
        assert "perpendicularity" in GDTFieldHandler.GDT_TYPES
        assert "parallelism" in GDTFieldHandler.GDT_TYPES
        assert "angularity" in GDTFieldHandler.GDT_TYPES

        # Location tolerances
        assert "position" in GDTFieldHandler.GDT_TYPES
        assert "concentricity" in GDTFieldHandler.GDT_TYPES
        assert "symmetry" in GDTFieldHandler.GDT_TYPES

        # Runout tolerances
        assert "circular_runout" in GDTFieldHandler.GDT_TYPES
        assert "total_runout" in GDTFieldHandler.GDT_TYPES

        # Profile tolerances
        assert "profile_line" in GDTFieldHandler.GDT_TYPES
        assert "profile_surface" in GDTFieldHandler.GDT_TYPES

    def test_material_conditions_defined(self):
        """Test that material conditions are properly defined."""
        assert "MMC" in GDTFieldHandler.MATERIAL_CONDITIONS
        assert "LMC" in GDTFieldHandler.MATERIAL_CONDITIONS
        assert "RFS" in GDTFieldHandler.MATERIAL_CONDITIONS
        assert GDTFieldHandler.MATERIAL_CONDITIONS["MMC"] == "Ⓜ"
        assert GDTFieldHandler.MATERIAL_CONDITIONS["LMC"] == "Ⓛ"
        assert GDTFieldHandler.MATERIAL_CONDITIONS["RFS"] == ""

    def test_gdt_type_symbols(self):
        """Test that each GD&T type has a symbol."""
        for gdt_type, info in GDTFieldHandler.GDT_TYPES.items():
            assert "symbol" in info
            assert "requires_datum" in info
            assert isinstance(info["symbol"], str)
            assert isinstance(info["requires_datum"], bool)


class TestGDTSerialization:
    """Tests for GD&T serialization."""

    def test_serialize_none(self):
        """Test serializing None returns None."""
        result = GDTFieldHandler.serialize(None)
        assert result is None

    def test_serialize_dict_full(self):
        """Test serializing a complete dict."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "diameter_zone": True,
            "material_condition": "MMC",
            "datums": ["A", "B", "C"],
            "datum_modifiers": {"A": "MMC"},
        }
        result = GDTFieldHandler.serialize(value)
        assert result["type"] == "position"
        assert result["tolerance"] == 0.05
        assert result["diameter_zone"] is True
        assert result["material_condition"] == "MMC"
        assert result["datums"] == ["A", "B", "C"]
        assert result["datum_modifiers"] == {"A": "MMC"}

    def test_serialize_dict_minimal(self):
        """Test serializing minimal dict with defaults."""
        value = {
            "type": "flatness",
            "tolerance": 0.01,
        }
        result = GDTFieldHandler.serialize(value)
        assert result["type"] == "flatness"
        assert result["tolerance"] == 0.01
        assert result["diameter_zone"] is False
        assert result["material_condition"] == "RFS"
        assert result["datums"] == []
        assert result["datum_modifiers"] == {}

    def test_serialize_dict_missing_material_condition(self):
        """Test serializing dict with missing material condition defaults to RFS."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "datums": ["A"],
        }
        result = GDTFieldHandler.serialize(value)
        assert result["material_condition"] == "RFS"

    def test_serialize_dict_missing_diameter_zone(self):
        """Test serializing dict with missing diameter_zone defaults to False."""
        value = {
            "type": "position",
            "tolerance": 0.05,
        }
        result = GDTFieldHandler.serialize(value)
        assert result["diameter_zone"] is False

    def test_serialize_dict_missing_datums(self):
        """Test serializing dict with missing datums defaults to empty list."""
        value = {
            "type": "flatness",
            "tolerance": 0.01,
        }
        result = GDTFieldHandler.serialize(value)
        assert result["datums"] == []

    def test_serialize_string(self):
        """Test serializing string creates custom type."""
        result = GDTFieldHandler.serialize("⌖ ⌀0.05 Ⓜ | A | B | C")
        assert result["type"] == "custom"
        assert result["display_text"] == "⌖ ⌀0.05 Ⓜ | A | B | C"
        assert result["tolerance"] is None
        assert result["diameter_zone"] is False
        assert result["material_condition"] == "RFS"
        assert result["datums"] == []

    def test_serialize_invalid_type(self):
        """Test serializing invalid type returns None."""
        result = GDTFieldHandler.serialize([1, 2, 3])
        assert result is None


class TestGDTDeserialization:
    """Tests for GD&T deserialization."""

    def test_deserialize_none(self):
        """Test deserializing None returns None."""
        result = GDTFieldHandler.deserialize(None)
        assert result is None

    def test_deserialize_dict(self):
        """Test deserializing a dict returns it unchanged."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "diameter_zone": True,
            "material_condition": "MMC",
            "datums": ["A", "B", "C"],
        }
        result = GDTFieldHandler.deserialize(value)
        assert result == value

    def test_deserialize_fallback_to_serialize(self):
        """Test deserializing non-dict falls back to serialize."""
        result = GDTFieldHandler.deserialize("⌖ ⌀0.05")
        assert result["type"] == "custom"
        assert result["display_text"] == "⌖ ⌀0.05"


class TestGDTValidation:
    """Tests for GD&T validation."""

    def test_validate_none(self):
        """Test validating None is allowed."""
        assert GDTFieldHandler.validate(None) is True

    def test_validate_valid_dict(self):
        """Test validating valid GD&T dict."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "diameter_zone": True,
            "material_condition": "MMC",
            "datums": ["A", "B", "C"],
        }
        assert GDTFieldHandler.validate(value) is True

    def test_validate_form_tolerance_without_datum(self):
        """Test validating form tolerance without datum is valid."""
        value = {
            "type": "flatness",
            "tolerance": 0.01,
        }
        assert GDTFieldHandler.validate(value) is True

    def test_validate_invalid_gdt_type(self):
        """Test validating invalid GD&T type raises error."""
        value = {
            "type": "invalid_type",
            "tolerance": 0.05,
        }
        with pytest.raises(ValueError, match="Invalid GD&T type"):
            GDTFieldHandler.validate(value)

    def test_validate_negative_tolerance(self):
        """Test validating negative tolerance raises error."""
        value = {
            "type": "flatness",
            "tolerance": -0.01,
        }
        with pytest.raises(ValueError, match="must be positive"):
            GDTFieldHandler.validate(value)

    def test_validate_invalid_material_condition(self):
        """Test validating invalid material condition raises error."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "material_condition": "INVALID",
            "datums": ["A"],
        }
        with pytest.raises(ValueError, match="Invalid material condition"):
            GDTFieldHandler.validate(value)

    def test_validate_datum_required_missing(self):
        """Test validating datum-required type without datum raises error."""
        value = {
            "type": "position",
            "tolerance": 0.05,
        }
        with pytest.raises(ValueError, match="requires datum reference"):
            GDTFieldHandler.validate(value)

    def test_validate_datum_required_with_option_disabled(self):
        """Test validating datum requirement can be disabled via options."""
        value = {
            "type": "position",
            "tolerance": 0.05,
        }
        options = {"require_datums": False}
        assert GDTFieldHandler.validate(value, options) is True

    def test_validate_datums_as_list(self):
        """Test validating datums as proper list."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "datums": ["A", "B", "C"],
        }
        # Should pass validation
        assert GDTFieldHandler.validate(value) is True

    def test_validate_single_datum(self):
        """Test validating single datum in list."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "datums": ["A"],
        }
        # Should pass validation
        assert GDTFieldHandler.validate(value) is True

    def test_validate_alphanumeric_datums(self):
        """Test validating alphanumeric datum names."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "datums": ["A1", "B2", "C3"],
        }
        # Should pass validation
        assert GDTFieldHandler.validate(value) is True

    def test_validate_valid_datum_modifiers(self):
        """Test validating valid datum modifiers."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "datums": ["A", "B"],
            "datum_modifiers": {"A": "MMC", "B": "LMC"},
        }
        assert GDTFieldHandler.validate(value) is True

    def test_validate_composite_datum_with_hyphen(self):
        """Test validating composite datum with hyphen is valid."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "datums": ["A-B"],
        }
        assert GDTFieldHandler.validate(value) is True

    def test_validate_composite_datum_with_underscore(self):
        """Test validating composite datum with underscore is valid."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "datums": ["A_B"],
        }
        assert GDTFieldHandler.validate(value) is True

    def test_validate_alphanumeric_datum(self):
        """Test validating alphanumeric datum is valid."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "datums": ["A1", "B2"],
        }
        assert GDTFieldHandler.validate(value) is True


class TestGDTDefault:
    """Tests for GD&T default value."""

    def test_default(self):
        """Test default value is None."""
        result = GDTFieldHandler.default()
        assert result is None


class TestGDTDisplayFormatting:
    """Tests for GD&T display formatting."""

    def test_format_display_none(self):
        """Test formatting None returns empty string."""
        result = GDTFieldHandler.format_display(None)
        assert result == ""

    def test_format_display_custom_text(self):
        """Test formatting custom display text."""
        value = {
            "type": "custom",
            "display_text": "Custom GD&T",
        }
        result = GDTFieldHandler.format_display(value)
        assert result == "Custom GD&T"

    def test_format_display_flatness(self):
        """Test formatting flatness (form tolerance)."""
        value = {
            "type": "flatness",
            "tolerance": 0.01,
        }
        result = GDTFieldHandler.format_display(value)
        assert "⏥" in result  # flatness symbol
        assert "0.01" in result

    def test_format_display_position_with_diameter(self):
        """Test formatting position with diameter zone."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "diameter_zone": True,
            "datums": ["A", "B", "C"],
        }
        result = GDTFieldHandler.format_display(value)
        assert "⌖" in result  # position symbol
        assert "⌀" in result  # diameter symbol
        assert "0.05" in result
        assert "A" in result
        assert "B" in result
        assert "C" in result

    def test_format_display_position_with_mmc(self):
        """Test formatting position with MMC modifier."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "diameter_zone": True,
            "material_condition": "MMC",
            "datums": ["A", "B", "C"],
        }
        result = GDTFieldHandler.format_display(value)
        assert "⌖" in result
        assert "⌀" in result
        assert "0.05" in result
        assert "Ⓜ" in result  # MMC symbol
        assert "A" in result

    def test_format_display_position_with_lmc(self):
        """Test formatting position with LMC modifier."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "diameter_zone": True,
            "material_condition": "LMC",
            "datums": ["A"],
        }
        result = GDTFieldHandler.format_display(value)
        assert "Ⓛ" in result  # LMC symbol

    def test_format_display_position_with_rfs(self):
        """Test formatting position with RFS (no symbol)."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "diameter_zone": True,
            "material_condition": "RFS",
            "datums": ["A"],
        }
        result = GDTFieldHandler.format_display(value)
        # RFS should not add a symbol
        assert "Ⓜ" not in result
        assert "Ⓛ" not in result

    def test_format_display_with_datum_modifiers(self):
        """Test formatting with datum modifiers."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "diameter_zone": True,
            "material_condition": "MMC",
            "datums": ["A", "B"],
            "datum_modifiers": {"A": "MMC", "B": "LMC"},
        }
        result = GDTFieldHandler.format_display(value)
        # Should contain datum A with MMC modifier and datum B with LMC modifier
        assert "A" in result
        assert "B" in result
        # Check that modifiers are present (though exact format may vary)
        assert result.count("Ⓜ") >= 1  # At least one MMC symbol (tolerance + datum A)
        assert "Ⓛ" in result  # LMC symbol for datum B

    def test_format_display_perpendicularity(self):
        """Test formatting perpendicularity."""
        value = {
            "type": "perpendicularity",
            "tolerance": 0.02,
            "datums": ["A"],
        }
        result = GDTFieldHandler.format_display(value)
        assert "⟂" in result  # perpendicularity symbol
        assert "0.02" in result
        assert "A" in result

    def test_format_display_parallelism(self):
        """Test formatting parallelism."""
        value = {
            "type": "parallelism",
            "tolerance": 0.03,
            "datums": ["A"],
        }
        result = GDTFieldHandler.format_display(value)
        assert "∥" in result  # parallelism symbol
        assert "0.03" in result

    def test_format_display_circular_runout(self):
        """Test formatting circular runout."""
        value = {
            "type": "circular_runout",
            "tolerance": 0.05,
            "datums": ["A"],
        }
        result = GDTFieldHandler.format_display(value)
        assert "↗" in result  # circular runout symbol
        assert "0.05" in result

    def test_format_display_profile_surface(self):
        """Test formatting profile of a surface."""
        value = {
            "type": "profile_surface",
            "tolerance": 0.1,
        }
        result = GDTFieldHandler.format_display(value)
        assert "⌓" in result  # profile surface symbol
        assert "0.1" in result

    def test_format_display_invalid_type(self):
        """Test formatting invalid type returns string representation."""
        value = "invalid"
        result = GDTFieldHandler.format_display(value)
        assert result == "invalid"

    def test_format_display_unknown_gdt_type(self):
        """Test formatting unknown GD&T type returns string representation."""
        value = {
            "type": "unknown_type",
            "tolerance": 0.05,
        }
        result = GDTFieldHandler.format_display(value)
        assert isinstance(result, str)


class TestGDTHelperMethods:
    """Tests for GD&T helper methods."""

    def test_get_symbol_valid_type(self):
        """Test getting symbol for valid GD&T type."""
        assert GDTFieldHandler.get_symbol("flatness") == "⏥"
        assert GDTFieldHandler.get_symbol("position") == "⌖"
        assert GDTFieldHandler.get_symbol("perpendicularity") == "⟂"
        assert GDTFieldHandler.get_symbol("parallelism") == "∥"

    def test_get_symbol_invalid_type(self):
        """Test getting symbol for invalid type returns None."""
        result = GDTFieldHandler.get_symbol("invalid_type")
        assert result is None

    def test_requires_datum_form_tolerance(self):
        """Test form tolerances don't require datum."""
        assert GDTFieldHandler.requires_datum("straightness") is False
        assert GDTFieldHandler.requires_datum("flatness") is False
        assert GDTFieldHandler.requires_datum("circularity") is False
        assert GDTFieldHandler.requires_datum("cylindricity") is False

    def test_requires_datum_orientation_tolerance(self):
        """Test orientation tolerances require datum."""
        assert GDTFieldHandler.requires_datum("perpendicularity") is True
        assert GDTFieldHandler.requires_datum("parallelism") is True
        assert GDTFieldHandler.requires_datum("angularity") is True

    def test_requires_datum_location_tolerance(self):
        """Test location tolerances require datum."""
        assert GDTFieldHandler.requires_datum("position") is True
        assert GDTFieldHandler.requires_datum("concentricity") is True
        assert GDTFieldHandler.requires_datum("symmetry") is True

    def test_requires_datum_runout_tolerance(self):
        """Test runout tolerances require datum."""
        assert GDTFieldHandler.requires_datum("circular_runout") is True
        assert GDTFieldHandler.requires_datum("total_runout") is True

    def test_requires_datum_profile_tolerance(self):
        """Test profile tolerances don't require datum."""
        assert GDTFieldHandler.requires_datum("profile_line") is False
        assert GDTFieldHandler.requires_datum("profile_surface") is False

    def test_requires_datum_invalid_type(self):
        """Test requires_datum for invalid type returns False."""
        assert GDTFieldHandler.requires_datum("invalid_type") is False


class TestGDTComplexScenarios:
    """Tests for complex GD&T scenarios."""

    def test_complete_feature_control_frame(self):
        """Test complete feature control frame with all elements."""
        value = {
            "type": "position",
            "tolerance": 0.05,
            "diameter_zone": True,
            "material_condition": "MMC",
            "datums": ["A", "B", "C"],
            "datum_modifiers": {"A": "MMC", "B": "MMC"},
        }
        # Should validate successfully
        assert GDTFieldHandler.validate(value) is True

        # Should serialize properly
        serialized = GDTFieldHandler.serialize(value)
        assert serialized["type"] == "position"
        assert serialized["tolerance"] == 0.05
        assert serialized["diameter_zone"] is True
        assert serialized["material_condition"] == "MMC"

        # Should format for display
        display = GDTFieldHandler.format_display(value)
        assert "⌖" in display
        assert "⌀" in display
        assert "0.05" in display
        assert "Ⓜ" in display

    def test_form_tolerance_complete(self):
        """Test form tolerance without datums."""
        value = {
            "type": "flatness",
            "tolerance": 0.01,
            "diameter_zone": False,
            "material_condition": "RFS",
            "datums": [],
        }
        assert GDTFieldHandler.validate(value) is True

        display = GDTFieldHandler.format_display(value)
        assert "⏥" in display
        assert "0.01" in display

    def test_multiple_datums_with_mixed_modifiers(self):
        """Test multiple datums with mixed modifiers."""
        value = {
            "type": "position",
            "tolerance": 0.1,
            "diameter_zone": True,
            "material_condition": "MMC",
            "datums": ["A", "B", "C"],
            "datum_modifiers": {"A": "MMC", "C": "LMC"},
        }
        assert GDTFieldHandler.validate(value) is True

        display = GDTFieldHandler.format_display(value)
        assert "A" in display
        assert "B" in display
        assert "C" in display

    def test_roundtrip_serialization(self):
        """Test that serialize -> deserialize preserves data."""
        original = {
            "type": "perpendicularity",
            "tolerance": 0.02,
            "diameter_zone": False,
            "material_condition": "RFS",
            "datums": ["A"],
            "datum_modifiers": {},
        }
        serialized = GDTFieldHandler.serialize(original)
        deserialized = GDTFieldHandler.deserialize(serialized)
        assert deserialized == serialized

    def test_zero_tolerance(self):
        """Test zero tolerance is valid."""
        value = {
            "type": "flatness",
            "tolerance": 0,
        }
        assert GDTFieldHandler.validate(value) is True

    def test_very_small_tolerance(self):
        """Test very small tolerance values."""
        value = {
            "type": "flatness",
            "tolerance": 0.0001,
        }
        assert GDTFieldHandler.validate(value) is True

        display = GDTFieldHandler.format_display(value)
        assert "0.0001" in display
