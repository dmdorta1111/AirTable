"""Unit tests for FormulaDependencyGraph."""

import pytest
from pybase.formula.dependencies import FormulaDependencyGraph


class TestFormulaDependencyGraph:
    """Tests for FormulaDependencyGraph class."""

    def test_initialization(self):
        """Test that graph initializes correctly."""
        graph = FormulaDependencyGraph()
        assert len(graph.dependencies) == 0
        assert len(graph.reverse) == 0

    def test_add_formula_field_no_deps(self):
        """Test adding a formula field with no dependencies."""
        graph = FormulaDependencyGraph()
        success, error = graph.add_formula_field("field_1", set())
        assert success is True
        assert error is None
        assert graph.get_dependencies("field_1") == set()

    def test_add_formula_field_with_deps(self):
        """Test adding a formula field with dependencies."""
        graph = FormulaDependencyGraph()
        success, error = graph.add_formula_field("field_1", {"field_2", "field_3"})
        assert success is True
        assert error is None
        deps = graph.get_dependencies("field_1")
        assert deps == {"field_2", "field_3"}
        assert "field_1" in graph.dependencies["field_2"]
        assert "field_1" in graph.dependencies["field_3"]

    def test_self_circular_reference(self):
        """Test detecting self-referencing formula."""
        graph = FormulaDependencyGraph()
        success, error = graph.add_formula_field("field_1", {"field_1"})
        assert success is False
        assert error == "Circular reference detected in formula dependencies"

    def test_direct_circular_reference(self):
        """Test detecting direct circular reference (A -> B -> A)."""
        graph = FormulaDependencyGraph()
        # Add field A depends on B
        graph.add_formula_field("field_a", {"field_b"})
        # Try to add field B depends on A - should fail
        success, error = graph.add_formula_field("field_b", {"field_a"})
        assert success is False
        assert error == "Circular reference detected in formula dependencies"

    def test_indirect_circular_reference(self):
        """Test detecting indirect circular reference (A -> B -> C -> A)."""
        graph = FormulaDependencyGraph()
        graph.add_formula_field("field_a", {"field_b"})
        graph.add_formula_field("field_b", {"field_c"})
        # field_c depends on field_a should be detected as circular
        success, error = graph.add_formula_field("field_c", {"field_a"})
        assert success is False
        assert error == "Circular reference detected in formula dependencies"

    def test_no_circular_valid_chain(self):
        """Test that valid linear chain doesn't trigger circular detection."""
        graph = FormulaDependencyGraph()
        success1, _ = graph.add_formula_field("field_a", {"field_b"})
        success2, _ = graph.add_formula_field("field_b", {"field_c"})
        success3, _ = graph.add_formula_field("field_c", set())
        assert success1 is True
        assert success2 is True
        assert success3 is True

    def test_remove_formula_field(self):
        """Test removing a formula field."""
        graph = FormulaDependencyGraph()
        graph.add_formula_field("field_1", {"field_2", "field_3"})
        graph.remove_formula_field("field_1")
        assert "field_1" not in graph.reverse
        assert "field_1" not in graph.dependencies["field_2"]
        assert "field_1" not in graph.dependencies["field_3"]

    def test_get_affected_fields_direct(self):
        """Test getting directly affected fields."""
        graph = FormulaDependencyGraph()
        graph.add_formula_field("field_a", {"field_b"})
        graph.add_formula_field("field_c", {"field_b"})

        affected = graph.get_affected_fields("field_b")
        assert set(affected) == {"field_a", "field_c"}

    def test_get_affected_fields_transitive(self):
        """Test getting transitively affected fields."""
        graph = FormulaDependencyGraph()
        # field_d -> field_c -> field_b
        graph.add_formula_field("field_d", {"field_c"})
        graph.add_formula_field("field_c", {"field_b"})

        # field_b changes should affect both c and d
        affected = graph.get_affected_fields("field_b")
        assert set(affected) == {"field_c", "field_d"}

    def test_get_affected_fields_complex(self):
        """Test getting affected fields in complex dependency graph."""
        graph = FormulaDependencyGraph()
        # field_a depends on base1, base2
        graph.add_formula_field("field_a", {"base1", "base2"})
        # field_b, field_c depend on field_a
        graph.add_formula_field("field_b", {"field_a"})
        graph.add_formula_field("field_c", {"field_a"})
        # field_d depends on field_b
        graph.add_formula_field("field_d", {"field_b"})

        # base1 changes should affect a, b, c, d
        affected = graph.get_affected_fields("base1")
        assert set(affected) == {"field_a", "field_b", "field_c", "field_d"}

    def test_get_affected_fields_no_dependents(self):
        """Test getting affected fields for field with no dependents."""
        graph = FormulaDependencyGraph()
        graph.add_formula_field("field_a", {"field_b"})

        affected = graph.get_affected_fields("field_a")
        assert affected == []

    def test_get_evaluation_order_linear(self):
        """Test topological sort for linear dependency chain."""
        graph = FormulaDependencyGraph()
        graph.add_formula_field("field_a", {"field_b"})
        graph.add_formula_field("field_b", {"field_c"})
        graph.add_formula_field("field_c", set())

        order = graph.get_evaluation_order({"field_a", "field_b", "field_c"})
        # Should be c, b, a
        assert order == ["field_c", "field_b", "field_a"]

    def test_get_evaluation_order_parallel(self):
        """Test topological sort for parallel dependencies."""
        graph = FormulaDependencyGraph()
        graph.add_formula_field("field_a", {"base1", "base2"})
        graph.add_formula_field("field_b", {"base1", "base2"})

        order = graph.get_evaluation_order({"field_a", "field_b"})
        # base1, base2 should come before a, b (order within groups doesn't matter)
        assert "base1" in order[:2]
        assert "base2" in order[:2]
        assert "field_a" in order[2:]
        assert "field_b" in order[2:]

    def test_get_evaluation_order_with_cycle(self):
        """Test that cycles return empty list."""
        graph = FormulaDependencyGraph()
        # Create a circular reference that wasn't prevented
        graph.dependencies["field_a"].add("field_b")
        graph.dependencies["field_b"].add("field_a")
        graph.reverse["field_a"] = {"field_b"}
        graph.reverse["field_b"] = {"field_a"}

        order = graph.get_evaluation_order({"field_a", "field_b"})
        assert order == []

    def test_get_dependencies(self):
        """Test getting dependencies of a field."""
        graph = FormulaDependencyGraph()
        graph.add_formula_field("field_1", {"field_2", "field_3"})

        deps = graph.get_dependencies("field_1")
        assert deps == {"field_2", "field_3"}

    def test_get_dependents(self):
        """Test getting dependents of a field."""
        graph = FormulaDependencyGraph()
        graph.add_formula_field("field_1", {"field_base"})
        graph.add_formula_field("field_2", {"field_base"})

        dependents = graph.get_dependents("field_base")
        assert set(dependents) == {"field_1", "field_2"}

    def test_clear(self):
        """Test clearing the graph."""
        graph = FormulaDependencyGraph()
        graph.add_formula_field("field_1", {"field_2"})
        graph.add_formula_field("field_2", set())

        graph.clear()
        assert len(graph.dependencies) == 0
        assert len(graph.reverse) == 0

    def test_update_dependencies(self):
        """Test updating a formula field's dependencies."""
        graph = FormulaDependencyGraph()
        # Initially field_1 depends on field_2
        graph.add_formula_field("field_1", {"field_2"})
        assert "field_1" in graph.dependencies["field_2"]

        # Update to depend on field_3 instead
        success, error = graph.add_formula_field("field_1", {"field_3"})
        assert success is True
        assert error is None
        assert "field_1" not in graph.dependencies["field_2"]
        assert "field_1" in graph.dependencies["field_3"]

    def test_repr(self):
        """Test string representation of graph."""
        graph = FormulaDependencyGraph()
        graph.add_formula_field("field_1", {"field_2"})

        repr_str = repr(graph)
        assert "FormulaDependencyGraph" in repr_str
        assert "fields=1" in repr_str
