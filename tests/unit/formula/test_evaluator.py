"""Unit tests for FormulaEvaluator."""

import pytest
from pybase.formula.parser import FormulaParser
from pybase.formula.evaluator import FormulaEvaluator


class TestFormulaEvaluator:
    """Tests for FormulaEvaluator class."""

    def test_evaluator_initialization(self):
        """Test that evaluator initializes correctly."""
        evaluator = FormulaEvaluator()
        assert evaluator is not None
        assert evaluator._fields == {}

    def test_evaluator_with_fields(self):
        """Test evaluator with initial fields."""
        fields = {"field1": 42, "field2": "hello"}
        evaluator = FormulaEvaluator(fields)
        assert evaluator._fields == fields

    def test_evaluate_number_literal(self):
        """Test evaluating number literal."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("42")
        result = evaluator.evaluate(ast)
        assert result == 42

    def test_evaluate_string_literal(self):
        """Test evaluating string literal."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse('"hello"')
        result = evaluator.evaluate(ast)
        assert result == "hello"

    def test_evaluate_boolean_true(self):
        """Test evaluating boolean TRUE."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("TRUE")
        result = evaluator.evaluate(ast)
        assert result is True

    def test_evaluate_boolean_false(self):
        """Test evaluating boolean FALSE."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("FALSE")
        result = evaluator.evaluate(ast)
        assert result is False

    def test_evaluate_field_reference(self):
        """Test evaluating field reference."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator({"myfield": 42})
        ast = parser.parse("{myfield}")
        result = evaluator.evaluate(ast)
        assert result == 42

    def test_evaluate_field_reference_missing(self):
        """Test evaluating missing field reference."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("{missing}")
        result = evaluator.evaluate(ast)
        assert result is None

    def test_evaluate_field_reference_override(self):
        """Test evaluating field reference with override."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator({"field1": 10})
        ast = parser.parse("{field1}")
        result = evaluator.evaluate(ast, fields={"field1": 20})
        assert result == 20

    def test_evaluate_addition(self):
        """Test evaluating addition."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("1 + 2")
        result = evaluator.evaluate(ast)
        assert result == 3

    def test_evaluate_subtraction(self):
        """Test evaluating subtraction."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("10 - 4")
        result = evaluator.evaluate(ast)
        assert result == 6

    def test_evaluate_multiplication(self):
        """Test evaluating multiplication."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("3 * 4")
        result = evaluator.evaluate(ast)
        assert result == 12

    def test_evaluate_division(self):
        """Test evaluating division."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("20 / 4")
        result = evaluator.evaluate(ast)
        assert result == 5.0

    def test_evaluate_division_by_zero(self):
        """Test evaluating division by zero."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("10 / 0")
        result = evaluator.evaluate(ast)
        # Should handle division by zero gracefully
        assert result is None or result == float("inf")

    def test_evaluate_modulo(self):
        """Test evaluating modulo."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("17 % 5")
        result = evaluator.evaluate(ast)
        assert result == 2

    def test_evaluate_power(self):
        """Test evaluating power."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("2 ^ 3")
        result = evaluator.evaluate(ast)
        assert result == 8

    def test_evaluate_string_concat(self):
        """Test evaluating string concatenation."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse('"hello" & "world"')
        result = evaluator.evaluate(ast)
        assert result == "helloworld"

    def test_evaluate_concat_with_none(self):
        """Test evaluating concatenation with None (using BLANK() function)."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse('"hello" & BLANK()')
        result = evaluator.evaluate(ast)
        assert result == "hello"

    def test_evaluate_equality(self):
        """Test evaluating equality."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("1 = 1")
        result = evaluator.evaluate(ast)
        assert result is True

    def test_evaluate_inequality(self):
        """Test evaluating inequality."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("1 != 2")
        result = evaluator.evaluate(ast)
        assert result is True

    def test_evaluate_less_than(self):
        """Test evaluating less than."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("1 < 2")
        result = evaluator.evaluate(ast)
        assert result is True

    def test_evaluate_greater_than(self):
        """Test evaluating greater than."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("2 > 1")
        result = evaluator.evaluate(ast)
        assert result is True

    def test_evaluate_less_or_equal(self):
        """Test evaluating less or equal."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("1 <= 2")
        result = evaluator.evaluate(ast)
        assert result is True

    def test_evaluate_greater_or_equal(self):
        """Test evaluating greater or equal."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("2 >= 2")
        result = evaluator.evaluate(ast)
        assert result is True

    def test_evaluate_logical_and(self):
        """Test evaluating AND."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("TRUE AND TRUE")
        result = evaluator.evaluate(ast)
        assert result is True

    def test_evaluate_logical_and_false(self):
        """Test evaluating AND with false."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("TRUE AND FALSE")
        result = evaluator.evaluate(ast)
        assert result is False

    def test_evaluate_logical_or(self):
        """Test evaluating OR."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("FALSE OR TRUE")
        result = evaluator.evaluate(ast)
        assert result is True

    def test_evaluate_logical_or_false(self):
        """Test evaluating OR with false."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("FALSE OR FALSE")
        result = evaluator.evaluate(ast)
        assert result is False

    def test_evaluate_logical_not(self):
        """Test evaluating NOT."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("NOT TRUE")
        result = evaluator.evaluate(ast)
        assert result is False

    def test_evaluate_unary_negative(self):
        """Test evaluating unary negative."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("-5")
        result = evaluator.evaluate(ast)
        assert result == -5

    def test_evaluate_function_call_sum(self):
        """Test evaluating SUM function."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("SUM(1, 2, 3)")
        result = evaluator.evaluate(ast)
        assert result == 6

    def test_evaluate_function_call_upper(self):
        """Test evaluating UPPER function."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse('UPPER("hello")')
        result = evaluator.evaluate(ast)
        assert result == "HELLO"

    def test_evaluate_function_call_if(self):
        """Test evaluating IF function."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse('IF(TRUE, "yes", "no")')
        result = evaluator.evaluate(ast)
        assert result == "yes"

    def test_evaluate_function_call_if_false(self):
        """Test evaluating IF function with false condition."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse('IF(FALSE, "yes", "no")')
        result = evaluator.evaluate(ast)
        assert result == "no"

    def test_evaluate_function_call_today(self):
        """Test evaluating TODAY function."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("TODAY()")
        result = evaluator.evaluate(ast)
        from datetime import date

        assert isinstance(result, date)

    def test_evaluate_unknown_function(self):
        """Test evaluating unknown function."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse('UNKNOWNFUNC("test")')
        result = evaluator.evaluate(ast)
        # Unknown functions should return None in safe mode
        assert result is None

    def test_evaluate_operator_precedence(self):
        """Test operator precedence (multiplication before addition)."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse("1 + 2 * 3")
        result = evaluator.evaluate(ast)
        # Should be 1 + (2 * 3) = 7, not (1 + 2) * 3 = 9
        assert result == 7

    def test_evaluate_complex_expression(self):
        """Test evaluating complex expression."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator({"field_a": 10, "field_b": 5})
        ast = parser.parse("{field_a} + {field_b} * 2")
        result = evaluator.evaluate(ast)
        assert result == 20

    def test_evaluate_nested_function_call(self):
        """Test evaluating nested function calls."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator()
        ast = parser.parse('UPPER(LEFT("hello", 3))')
        result = evaluator.evaluate(ast)
        assert result == "HEL"

    def test_evaluate_with_field_in_function(self):
        """Test evaluating field reference in function."""
        parser = FormulaParser()
        evaluator = FormulaEvaluator({"name": "john"})
        ast = parser.parse("UPPER({name})")
        result = evaluator.evaluate(ast)
        assert result == "JOHN"
