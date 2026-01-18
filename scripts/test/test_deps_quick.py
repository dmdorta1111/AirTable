"""Quick test to verify FormulaDependencyGraph works."""

# Add src to path
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pybase.formula.dependencies import FormulaDependencyGraph


def test_basic_usage():
    """Test basic FormulaDependencyGraph usage."""
    graph = FormulaDependencyGraph()

    # Test adding fields
    success, error = graph.add_formula_field("field_a", {"field_b", "field_c"})
    assert success, f"Should succeed: {error}"
    print("✓ Add field with dependencies")

    # Test getting affected fields
    affected = graph.get_affected_fields("field_b")
    assert "field_a" in affected
    print("✓ Get affected fields")

    # Test topological sort
    order = graph.get_evaluation_order({"field_a", "field_b", "field_c"})
    assert len(order) == 3
    assert order[-1] == "field_a"  # field_a depends on others
    print("✓ Get evaluation order")

    # Test circular detection
    graph2 = FormulaDependencyGraph()
    success, error = graph2.add_formula_field("field_x", {"field_x"})
    assert not success
    assert error == "Circular reference detected in formula dependencies"
    print("✓ Detect circular reference")

    print("\n✅ All FormulaDependencyGraph tests passed!")


if __name__ == "__main__":
    test_basic_usage()
