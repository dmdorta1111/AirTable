"""Unit tests for FormulaFieldHandler."""

import pytest
from pybase.fields.types.formula import FormulaFieldHandler


class TestFormulaFieldHandler:
    """Tests for FormulaFieldHandler class."""

    def test_field_type(self):
        """Test that field type is correct."""
        assert FormulaFieldHandler.field_type == "formula"

    def test_is_computed(self):
        """Test that formula field is computed."""
        assert FormulaFieldHandler.is_computed() is True

    def test_is_read_only(self):
        """Test that formula field is read-only."""
        assert FormulaFieldHandler.is_read_only() is True

    def test_serialize_none(self):
        """Test serializing None."""
        result = FormulaFieldHandler.serialize(None)
        assert result is None

    def test_serialize_number(self):
        """Test serializing number."""
        result = FormulaFieldHandler.serialize(42.5)
        assert result == 42.5

    def test_deserialize_number(self):
        """Test deserializing number."""
        result = FormulaFieldHandler.deserialize(42.5)
        assert result == 42.5

    def test_deserialize_none(self):
        """Test deserializing None."""
        result = FormulaFieldHandler.deserialize(None)
        assert result is None

    def test_default(self):
        """Test getting default value."""
        result = FormulaFieldHandler.default()
        assert result is None

    def test_validate_no_formula(self):
        """Test validating field without formula."""
        with pytest.raises(ValueError, match="must specify 'formula'"):
            FormulaFieldHandler.validate(None, {})

    def test_validate_with_formula(self):
        """Test validating field with valid formula."""
        result = FormulaFieldHandler.validate(None, {"formula": "{field} + 1"})
        assert result is True

    def test_validate_invalid_syntax(self):
        """Test validating field with invalid syntax."""
        with pytest.raises(ValueError, match="Invalid formula syntax"):
            FormulaFieldHandler.validate(None, {"formula": "1 + * 2"})

    def test_validate_invalid_result_type(self):
        """Test validating field with invalid result type."""
        with pytest.raises(ValueError, match="Invalid result_type"):
            FormulaFieldHandler.validate(None, {"formula": "1", "result_type": "invalid"})

    def test_validate_valid_result_types(self):
        """Test validating field with valid result types."""
        for result_type in ["text", "number", "date", "datetime", "boolean", "auto"]:
            result = FormulaFieldHandler.validate(
                None, {"formula": "1", "result_type": result_type}
            )
            assert result is True

    def test_get_referenced_fields(self):
        """Test extracting referenced fields."""
        fields = FormulaFieldHandler.get_referenced_fields("{Field A} + {Field B}")
        assert set(fields) == {"Field A", "Field B"}

    def test_get_referenced_fields_none(self):
        """Test extracting referenced fields with none."""
        fields = FormulaFieldHandler.get_referenced_fields("1 + 2")
        assert fields == []

    def test_get_referenced_fields_in_function(self):
        """Test extracting referenced fields in function."""
        fields = FormulaFieldHandler.get_referenced_fields("SUM({Field A}, {Field B})")
        assert set(fields) == {"Field A", "Field B"}

    def test_validate_formula_syntax_valid(self):
        """Test validating valid formula syntax."""
        is_valid, error = FormulaFieldHandler.validate_formula_syntax("1 + 2")
        assert is_valid is True
        assert error is None

    def test_validate_formula_syntax_invalid(self):
        """Test validating invalid formula syntax."""
        is_valid, error = FormulaFieldHandler.validate_formula_syntax("1 + * 2")
        assert is_valid is False
        assert error is not None

    def test_compute_simple_addition(self):
        """Test computing simple addition."""
        fields = {"field1": 10, "field2": 20}
        result = FormulaFieldHandler.compute("{field1} + {field2}", fields)
        assert result == 30

    def test_compute_with_field_ref(self):
        """Test computing with field reference."""
        fields = {"price": 100, "quantity": 5}
        result = FormulaFieldHandler.compute("{price} * {quantity}", fields)
        assert result == 500

    def test_compute_function_call(self):
        """Test computing function call."""
        fields = {}
        result = FormulaFieldHandler.compute('UPPER("hello")', fields)
        assert result == "HELLO"

    def test_compute_invalid_formula(self):
        """Test computing invalid formula."""
        fields = {}
        result = FormulaFieldHandler.compute("1 + * 2", fields)
        # Should return error string or None
        assert result is None or isinstance(result, str)

    def test_format_display_string(self):
        """Test formatting string for display."""
        result = FormulaFieldHandler.format_display("hello")
        assert result == "hello"

    def test_format_display_number_with_precision(self):
        """Test formatting number with precision."""
        options = {"precision": 2}
        result = FormulaFieldHandler.format_display(3.14159, options)
        assert result == "3.14"

    def test_format_display_none(self):
        """Test formatting None."""
        result = FormulaFieldHandler.format_display(None)
        assert result == ""

    def test_format_display_boolean(self):
        """Test formatting boolean."""
        assert FormulaFieldHandler.format_display(True) == "Yes"
        assert FormulaFieldHandler.format_display(False) == "No"

    def test_format_display_list(self):
        """Test formatting list."""
        result = FormulaFieldHandler.format_display([1, 2, 3])
        assert result == "1, 2, 3"

    def test_format_display_list_with_none(self):
        """Test formatting list with None values."""
        result = FormulaFieldHandler.format_display([1, None, 3])
        assert result == "1, 3"

    def test_convert_result_auto(self):
        """Test converting result with auto type."""
        result = FormulaFieldHandler._convert_result(42, "auto", {})
        assert result == 42

    def test_convert_result_text(self):
        """Test converting result to text."""
        result = FormulaFieldHandler._convert_result(42, "text", {})
        assert result == "42"

    def test_convert_result_number(self):
        """Test converting result to number."""
        result = FormulaFieldHandler._convert_result("3.14", "number", {})
        assert result == 3.14

    def test_convert_result_boolean(self):
        """Test converting result to boolean."""
        assert FormulaFieldHandler._convert_result(1, "boolean", {}) is True
        assert FormulaFieldHandler._convert_result(0, "boolean", {}) is False

    def test_convert_result_number_precision(self):
        """Test converting result to number with precision."""
        options = {"precision": 2}
        result = FormulaFieldHandler._convert_result(3.14159, "number", options)
        assert result == 3.14
