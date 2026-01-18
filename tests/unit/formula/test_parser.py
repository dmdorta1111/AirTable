"""Unit tests for FormulaParser."""

import pytest
from pybase.formula.parser import FormulaParser


class TestFormulaParser:
    """Tests for FormulaParser class."""

    def test_parser_initialization(self):
        """Test that parser initializes correctly."""
        parser = FormulaParser()
        assert parser is not None

    def test_parse_number_literal(self):
        """Test parsing number literals."""
        parser = FormulaParser()
        ast = parser.parse("42")
        assert ast.value == 42

    def test_parse_decimal_literal(self):
        """Test parsing decimal literals."""
        parser = FormulaParser()
        ast = parser.parse("3.14")
        assert ast.value == 3.14

    def test_parse_string_literal(self):
        """Test parsing string literals."""
        parser = FormulaParser()
        ast = parser.parse('"hello world"')
        assert ast.value == "hello world"

    def test_parse_boolean_true(self):
        """Test parsing boolean TRUE."""
        parser = FormulaParser()
        ast = parser.parse("TRUE")
        assert ast.value is True

    def test_parse_boolean_false(self):
        """Test parsing boolean FALSE."""
        parser = FormulaParser()
        ast = parser.parse("FALSE")
        assert ast.value is False

    def test_parse_blank_function(self):
        """Test parsing BLANK() function call."""
        parser = FormulaParser()
        ast = parser.parse("BLANK()")
        assert ast.name == "BLANK"
        assert ast.arguments == []

    def test_parse_field_reference(self):
        """Test parsing field references."""
        parser = FormulaParser()
        ast = parser.parse("{Field Name}")
        assert ast.field_name == "Field Name"

    def test_parse_field_reference_with_spaces(self):
        """Test parsing field references with spaces."""
        parser = FormulaParser()
        ast = parser.parse("{Field Name With Spaces}")
        assert ast.field_name == "Field Name With Spaces"

    def test_parse_arithmetic_addition(self):
        """Test parsing addition."""
        parser = FormulaParser()
        ast = parser.parse("1 + 2")
        assert ast.operator == "+"
        assert ast.left.value == 1
        assert ast.right.value == 2

    def test_parse_arithmetic_subtraction(self):
        """Test parsing subtraction."""
        parser = FormulaParser()
        ast = parser.parse("10 - 5")
        assert ast.operator == "-"
        assert ast.left.value == 10
        assert ast.right.value == 5

    def test_parse_arithmetic_multiplication(self):
        """Test parsing multiplication."""
        parser = FormulaParser()
        ast = parser.parse("3 * 4")
        assert ast.operator == "*"

    def test_parse_arithmetic_division(self):
        """Test parsing division."""
        parser = FormulaParser()
        ast = parser.parse("20 / 4")
        assert ast.operator == "/"

    def test_parse_arithmetic_modulo(self):
        """Test parsing modulo."""
        parser = FormulaParser()
        ast = parser.parse("17 % 5")
        assert ast.operator == "%"

    def test_parse_arithmetic_power(self):
        """Test parsing power."""
        parser = FormulaParser()
        ast = parser.parse("2 ^ 8")
        assert ast.operator == "^"

    def test_parse_comparison_equal(self):
        """Test parsing equality."""
        parser = FormulaParser()
        ast = parser.parse("1 = 1")
        assert ast.operator == "="

    def test_parse_comparison_not_equal(self):
        """Test parsing not equal."""
        parser = FormulaParser()
        ast = parser.parse("1 != 2")
        assert ast.operator == "!="

    def test_parse_comparison_less_than(self):
        """Test parsing less than."""
        parser = FormulaParser()
        ast = parser.parse("1 < 2")
        assert ast.operator == "<"

    def test_parse_comparison_greater_than(self):
        """Test parsing greater than."""
        parser = FormulaParser()
        ast = parser.parse("2 > 1")
        assert ast.operator == ">"

    def test_parse_comparison_less_or_equal(self):
        """Test parsing less or equal."""
        parser = FormulaParser()
        ast = parser.parse("1 <= 2")
        assert ast.operator == "<="

    def test_parse_comparison_greater_or_equal(self):
        """Test parsing greater or equal."""
        parser = FormulaParser()
        ast = parser.parse("2 >= 1")
        assert ast.operator == ">="

    def test_parse_string_concat(self):
        """Test parsing string concatenation."""
        parser = FormulaParser()
        ast = parser.parse('"hello" & "world"')
        assert ast.operator == "&"

    def test_parse_logical_and(self):
        """Test parsing AND operator."""
        parser = FormulaParser()
        ast = parser.parse("TRUE AND FALSE")
        assert ast.operator == "AND"

    def test_parse_logical_or(self):
        """Test parsing OR operator."""
        parser = FormulaParser()
        ast = parser.parse("TRUE OR FALSE")
        assert ast.operator == "OR"

    def test_parse_logical_not(self):
        """Test parsing NOT operator."""
        parser = FormulaParser()
        ast = parser.parse("NOT TRUE")
        assert ast.operator == "NOT"

    def test_parse_unary_negative(self):
        """Test parsing unary negative."""
        parser = FormulaParser()
        ast = parser.parse("-5")
        assert ast.operator == "-"
        assert ast.operand.value == 5

    def test_parse_function_call_no_args(self):
        """Test parsing function call with no arguments."""
        parser = FormulaParser()
        ast = parser.parse("TODAY()")
        assert ast.name == "TODAY"
        assert ast.arguments == []

    def test_parse_function_call_one_arg(self):
        """Test parsing function call with one argument."""
        parser = FormulaParser()
        ast = parser.parse('UPPER("hello")')
        assert ast.name == "UPPER"
        assert len(ast.arguments) == 1

    def test_parse_function_call_multiple_args(self):
        """Test parsing function call with multiple arguments."""
        parser = FormulaParser()
        ast = parser.parse('LEFT("hello", 3)')
        assert ast.name == "LEFT"
        assert len(ast.arguments) == 2

    def test_parse_parentheses(self):
        """Test parsing parentheses."""
        parser = FormulaParser()
        ast = parser.parse("(1 + 2) * 3")
        # Should be (1 + 2) * 3
        assert ast.operator == "*"

    def test_parse_complex_expression(self):
        """Test parsing complex expression."""
        parser = FormulaParser()
        ast = parser.parse("1 + 2 * 3 - 4 / 2")
        # Should be ((1 + (2 * 3)) - (4 / 2)) due to left-to-right evaluation
        assert ast.operator == "-"

    def test_validate_valid_formula(self):
        """Test validating a valid formula."""
        parser = FormulaParser()
        is_valid, error = parser.validate("1 + 2")
        assert is_valid is True
        assert error is None

    def test_validate_invalid_formula_syntax(self):
        """Test validating formula with syntax error."""
        parser = FormulaParser()
        is_valid, error = parser.validate("1 + +")
        assert is_valid is False
        assert error is not None

    def test_get_field_references(self):
        """Test extracting field references from formula."""
        parser = FormulaParser()
        fields = parser.get_field_references("{Field A} + {Field B}")
        assert set(fields) == {"Field A", "Field B"}

    def test_get_field_references_none(self):
        """Test extracting field references when none exist."""
        parser = FormulaParser()
        fields = parser.get_field_references("1 + 2")
        assert fields == []

    def test_get_field_references_in_function(self):
        """Test extracting field references in function."""
        parser = FormulaParser()
        fields = parser.get_field_references("SUM({Field A}, {Field B})")
        assert set(fields) == {"Field A", "Field B"}

    def test_case_insensitive_function_names(self):
        """Test that function names are case-insensitive."""
        parser = FormulaParser()
        ast1 = parser.parse("TODAY()")
        ast2 = parser.parse("today()")
        assert ast1.name == "TODAY"
        assert ast2.name == "TODAY"

    def test_case_insensitive_boolean(self):
        """Test that boolean literals are case-insensitive."""
        parser = FormulaParser()
        ast1 = parser.parse("TRUE")
        ast2 = parser.parse("true")
        assert ast1.value is True
        assert ast2.value is True

    def test_case_insensitive_operators(self):
        """Test that logical operators are case-insensitive."""
        parser = FormulaParser()
        ast1 = parser.parse("TRUE AND FALSE")
        ast2 = parser.parse("true and false")
        assert ast1.operator == "AND"
        assert ast2.operator == "AND"

    def test_scientific_notation(self):
        """Test parsing scientific notation."""
        parser = FormulaParser()
        ast = parser.parse("1.5e10")
        assert abs(ast.value - 1.5e10) < 1e6

    def test_negative_number(self):
        """Test parsing negative numbers."""
        parser = FormulaParser()
        ast = parser.parse("-42")
        assert ast.operator == "-"
        assert ast.operand.value == 42

    def test_negative_decimal(self):
        """Test parsing negative decimals."""
        parser = FormulaParser()
        ast = parser.parse("-3.14")
        assert ast.operator == "-"
        assert ast.operand.value == 3.14

    def test_single_quotes_string(self):
        """Test parsing single-quoted strings."""
        parser = FormulaParser()
        ast = parser.parse("'hello world'")
        assert ast.value == "hello world"

    def test_empty_string(self):
        """Test parsing empty string."""
        parser = FormulaParser()
        ast = parser.parse('""')
        assert ast.value == ""
