"""Integration tests for formula fields in database context."""

import pytest
from uuid import uuid4

from pybase.fields.types.formula import FormulaFieldHandler
from pybase.formula.dependencies import FormulaDependencyGraph
from pybase.formula.parser import FormulaParser


class TestFormulaFieldIntegration:
    """Integration tests for formula field functionality."""

    def test_formula_field_basic_computation(self):
        """Test basic formula field computation."""
        fields = {"price": 100, "quantity": 5}
        result = FormulaFieldHandler.compute("{price} * {quantity}", fields)
        assert result == 500

    def test_formula_field_with_function(self):
        """Test formula field with function call."""
        fields = {"text": "hello world"}
        result = FormulaFieldHandler.compute("UPPER({text})", fields)
        assert result == "HELLO WORLD"

    def test_formula_field_with_conditional(self):
        """Test formula field with conditional logic."""
        fields = {"score": 85}
        result = FormulaFieldHandler.compute(
            'IF({score} >= 90, "A", IF({score} >= 70, "B", "C"))', fields
        )
        assert result == "B"

    def test_formula_field_with_date_function(self):
        """Test formula field with date function."""
        fields = {}
        result = FormulaFieldHandler.compute("TODAY()", fields)
        from datetime import date

        assert isinstance(result, date)

    def test_get_referenced_fields_simple(self):
        """Test getting referenced fields from simple formula."""
        refs = FormulaFieldHandler.get_referenced_fields("{field_a} + {field_b}")
        assert set(refs) == {"field_a", "field_b"}

    def test_get_referenced_fields_in_function(self):
        """Test getting referenced fields from function."""
        refs = FormulaFieldHandler.get_referenced_fields("SUM({field_a}, {field_b}, {field_c})")
        assert set(refs) == {"field_a", "field_b", "field_c"}

    def test_validate_formula_syntax_valid(self):
        """Test validating valid formula syntax."""
        is_valid, error = FormulaFieldHandler.validate_formula_syntax("{field} + 1")
        assert is_valid is True
        assert error is None

    def test_validate_formula_syntax_invalid(self):
        """Test validating invalid formula syntax."""
        is_valid, error = FormulaFieldHandler.validate_formula_syntax("{field} + +")
        assert is_valid is False
        assert error is not None

    def test_formula_cache(self):
        """Test that formula parsing is cached."""
        formula = "{field_a} + {field_b}"

        # First computation should parse
        fields1 = {"field_a": 10, "field_b": 20}
        result1 = FormulaFieldHandler.compute(formula, fields1)

        # Second computation should use cached AST
        fields2 = {"field_a": 5, "field_b": 10}
        result2 = FormulaFieldHandler.compute(formula, fields2)

        assert result1 == 30
        assert result2 == 15

    def test_dependency_graph_basic(self):
        """Test dependency graph basic usage."""
        graph = FormulaDependencyGraph()

        # Add fields
        success, _ = graph.add_formula_field("field_total", {"price", "quantity"})
        assert success

        success, _ = graph.add_formula_field("field_grand", {"field_total"})

        # Check dependencies
        deps = graph.get_dependencies("field_total")
        assert "price" in deps
        assert "quantity" in deps

    def test_dependency_graph_affected_fields(self):
        """Test getting affected fields when dependency changes."""
        graph = FormulaDependencyGraph()

        graph.add_formula_field("field_total", {"price", "quantity"})
        graph.add_formula_field("field_grand", {"field_total"})
        graph.add_formula_field("field_final", {"field_grand"})

        # When price changes, grand and final should need recalc
        affected = graph.get_affected_fields("price")
        assert "field_total" in affected
        assert "field_grand" in affected
        assert "field_final" in affected

    def test_dependency_graph_circular_detection(self):
        """Test circular reference detection."""
        graph = FormulaDependencyGraph()

        # Create linear dependency
        graph.add_formula_field("a", {"b"})
        graph.add_formula_field("b", {"c"})

        # Try to create cycle
        success, error = graph.add_formula_field("c", {"a"})
        assert not success
        assert "Circular reference detected" in error

    def test_dependency_graph_evaluation_order(self):
        """Test getting evaluation order."""
        graph = FormulaDependencyGraph()

        graph.add_formula_field("total", {"a", "b"})
        graph.add_formula_field("grand", {"total"})
        graph.add_formula_field("final", {"grand"})

        # Evaluation order: a, b, total, grand, final
        order = graph.get_evaluation_order({"final", "grand", "total", "a", "b"})
        assert len(order) == 5

        # a and b should be first (no dependencies)
        assert order[:2] == ["a", "b"] or order[:2] == ["b", "a"]
        # total should come before grand
        assert order.index("total") < order.index("grand")
        # grand should come before final
        assert order.index("grand") < order.index("final")

    def test_dependency_graph_remove(self):
        """Test removing formula from graph."""
        graph = FormulaDependencyGraph()

        graph.add_formula_field("a", {"b"})
        graph.add_formula_field("c", {"a"})

        # Remove c
        graph.remove_formula_field("c")

        # a should no longer have c as dependent
        dependents = graph.get_dependents("a")
        assert "c" not in dependents

    def test_dependency_graph_update_dependencies(self):
        """Test updating field dependencies."""
        graph = FormulaDependencyGraph()

        # Initially a depends on b
        graph.add_formula_field("a", {"b"})

        # Update to depend on c instead
        graph.add_formula_field("a", {"c"})

        # Check old dependency is removed
        dependents_of_b = graph.get_dependents("b")
        assert "a" not in dependents_of_b

        # Check new dependency is added
        dependents_of_c = graph.get_dependents("c")
        assert "a" in dependents_of_c

    def test_complex_formula_with_multiple_functions(self):
        """Test complex formula with multiple nested functions."""
        fields = {
            "field1": 10,
            "field2": 20,
            "field3": 30,
        }
        result = FormulaFieldHandler.compute(
            "SUM(ROUND({field1}, 0), ROUND(AVG({field2}, {field3}), 0))",
            fields,
        )
        # ROUND(10, 0) = 10, AVG(20, 30) = 25, ROUND(25, 0) = 25
        # SUM(10, 25) = 35
        assert result == 35

    def test_formula_result_type_conversion_number(self):
        """Test formula result type conversion to number."""
        fields = {"value": "42.5"}
        options = {"result_type": "number", "precision": 2}
        result = FormulaFieldHandler.compute("{value}", fields, options)
        assert result == 42.5

    def test_formula_result_type_conversion_boolean(self):
        """Test formula result type conversion to boolean."""
        fields = {"value": "truthy"}
        options = {"result_type": "boolean"}
        result = FormulaFieldHandler.compute("{value} != BLANK()", fields, options)
        assert result is True

    def test_formula_with_field_not_in_context(self):
        """Test formula with missing field in context."""
        fields = {"field1": 10}
        result = FormulaFieldHandler.compute("{field1} + {field2}", fields)
        # Missing fields are treated as None; addition with None returns the non-None value
        assert result == 10

    def test_formula_display_formatting(self):
        """Test formula display formatting."""
        options = {"precision": 2}
        result = FormulaFieldHandler.format_display(3.14159, options)
        assert result == "3.14"

    def test_formula_display_formatting_date(self):
        """Test formula display formatting for dates."""
        from datetime import datetime

        value = datetime(2024, 1, 15, 10, 30)
        result = FormulaFieldHandler.format_display(value, {"date_format": "%Y-%m-%d %H:%M"})
        assert result == "2024-01-15 10:30"

    def test_formula_read_only(self):
        """Test that formula field is marked as read-only and computed."""
        assert FormulaFieldHandler.is_read_only() is True
        assert FormulaFieldHandler.is_computed() is True

    def test_formula_with_regex_functions(self):
        """Test formula with regex functions."""
        fields = {"text": "hello@example.com"}
        result = FormulaFieldHandler.compute('REGEX_EXTRACT({text}, "[^@]+")', fields)
        assert result == "hello"

    def test_formula_with_array_functions(self):
        """Test formula with array functions."""
        # Test SUM with multiple arguments
        fields = {"a": 1, "b": 2, "c": 3}
        result = FormulaFieldHandler.compute(
            "SUM({a}, {b}, {c})",
            fields,
        )
        assert result == 6  # 1 + 2 + 3
