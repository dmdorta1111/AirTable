"""Formula evaluator for PyBase.

Evaluates parsed formula ASTs against record data.
"""

from typing import Any
from datetime import datetime, date
from decimal import Decimal

from pybase.formula.parser import (
    NumberNode,
    StringNode,
    BooleanNode,
    FieldRefNode,
    FunctionCallNode,
    BinaryOpNode,
    UnaryOpNode,
)
from pybase.formula.functions import FORMULA_FUNCTIONS


class FormulaEvaluator:
    """
    Evaluates formula ASTs against record data.

    Supports all standard operators and built-in functions.
    """

    def __init__(self, fields: dict[str, Any] | None = None):
        """
        Initialize evaluator with optional field values.

        Args:
            fields: Dictionary mapping field names to their values
        """
        self._fields = fields or {}

    def evaluate(
        self,
        ast: Any,
        fields: dict[str, Any] | None = None,
    ) -> Any:
        """
        Evaluate an AST node.

        Args:
            ast: AST node to evaluate
            fields: Optional field values (overrides constructor values)

        Returns:
            Evaluation result
        """
        if fields is not None:
            self._fields = fields

        return self._eval(ast)

    def _eval(self, node: Any) -> Any:
        """Recursively evaluate an AST node."""
        if isinstance(node, NumberNode):
            return node.value

        if isinstance(node, StringNode):
            return node.value

        if isinstance(node, BooleanNode):
            return node.value

        if isinstance(node, FieldRefNode):
            return self._fields.get(node.field_name)

        if isinstance(node, FunctionCallNode):
            return self._eval_function(node)

        if isinstance(node, BinaryOpNode):
            return self._eval_binary(node)

        if isinstance(node, UnaryOpNode):
            return self._eval_unary(node)

        # Unknown node type, return as-is
        return node

    def _eval_function(self, node: FunctionCallNode) -> Any:
        """Evaluate a function call."""
        func = FORMULA_FUNCTIONS.get(node.name)
        if func is None:
            raise ValueError(f"Unknown function: {node.name}")

        # Evaluate arguments
        args = [self._eval(arg) for arg in node.arguments]

        try:
            return func(*args)
        except Exception as e:
            # Return None on error (safe mode)
            return None

    def _eval_binary(self, node: BinaryOpNode) -> Any:
        """Evaluate a binary operation."""
        left = self._eval(node.left)
        right = self._eval(node.right)
        op = node.operator

        # Arithmetic operators
        if op == "+":
            return self._add(left, right)
        if op == "-":
            return self._subtract(left, right)
        if op == "*":
            return self._multiply(left, right)
        if op == "/":
            return self._divide(left, right)
        if op == "%":
            return self._modulo(left, right)
        if op == "^":
            return self._power(left, right)

        # String concatenation
        if op == "&":
            return self._concat(left, right)

        # Comparison operators
        if op == "=":
            return self._equal(left, right)
        if op == "!=":
            return self._not_equal(left, right)
        if op == "<":
            return self._less_than(left, right)
        if op == ">":
            return self._greater_than(left, right)
        if op == "<=":
            return self._less_than_or_equal(left, right)
        if op == ">=":
            return self._greater_than_or_equal(left, right)

        # Logical operators
        if op == "AND":
            return bool(left) and bool(right)
        if op == "OR":
            return bool(left) or bool(right)

        raise ValueError(f"Unknown operator: {op}")

    def _eval_unary(self, node: UnaryOpNode) -> Any:
        """Evaluate a unary operation."""
        operand = self._eval(node.operand)
        op = node.operator

        if op == "-":
            if operand is None:
                return None
            try:
                return -float(operand)
            except (ValueError, TypeError):
                return None

        if op == "NOT":
            return not operand

        raise ValueError(f"Unknown unary operator: {op}")

    # ==========================================================================
    # Operator Implementations
    # ==========================================================================

    def _add(self, left: Any, right: Any) -> Any:
        """Addition with type coercion."""
        if left is None and right is None:
            return None
        if left is None:
            return right
        if right is None:
            return left

        # Date + number = date offset
        if isinstance(left, (date, datetime)) and isinstance(right, (int, float)):
            from datetime import timedelta

            return left + timedelta(days=right)

        # Numeric addition
        try:
            return float(left) + float(right)
        except (ValueError, TypeError):
            # String concatenation fallback
            return str(left) + str(right)

    def _subtract(self, left: Any, right: Any) -> Any:
        """Subtraction with type coercion."""
        if left is None or right is None:
            return None

        # Date - date = days difference
        if isinstance(left, (date, datetime)) and isinstance(right, (date, datetime)):
            return (left - right).days

        # Date - number = date offset
        if isinstance(left, (date, datetime)) and isinstance(right, (int, float)):
            from datetime import timedelta

            return left - timedelta(days=right)

        try:
            return float(left) - float(right)
        except (ValueError, TypeError):
            return None

    def _multiply(self, left: Any, right: Any) -> Any:
        """Multiplication."""
        if left is None or right is None:
            return None
        try:
            return float(left) * float(right)
        except (ValueError, TypeError):
            return None

    def _divide(self, left: Any, right: Any) -> Any:
        """Division."""
        if left is None or right is None:
            return None
        try:
            r = float(right)
            if r == 0:
                return None  # Division by zero returns None
            return float(left) / r
        except (ValueError, TypeError):
            return None

    def _modulo(self, left: Any, right: Any) -> Any:
        """Modulo."""
        if left is None or right is None:
            return None
        try:
            r = float(right)
            if r == 0:
                return None
            return float(left) % r
        except (ValueError, TypeError):
            return None

    def _power(self, left: Any, right: Any) -> Any:
        """Exponentiation."""
        if left is None or right is None:
            return None
        try:
            return float(left) ** float(right)
        except (ValueError, TypeError):
            return None

    def _concat(self, left: Any, right: Any) -> str:
        """String concatenation."""
        l = "" if left is None else str(left)
        r = "" if right is None else str(right)
        return l + r

    def _equal(self, left: Any, right: Any) -> bool:
        """Equality comparison."""
        # Null handling
        if left is None and right is None:
            return True
        if left is None or right is None:
            return False

        # Type coercion for comparison
        if isinstance(left, (int, float)) or isinstance(right, (int, float)):
            try:
                return float(left) == float(right)
            except (ValueError, TypeError):
                pass

        return left == right

    def _not_equal(self, left: Any, right: Any) -> bool:
        """Inequality comparison."""
        return not self._equal(left, right)

    def _less_than(self, left: Any, right: Any) -> bool:
        """Less than comparison."""
        if left is None or right is None:
            return False
        try:
            return float(left) < float(right)
        except (ValueError, TypeError):
            try:
                return str(left) < str(right)
            except TypeError:
                return False

    def _greater_than(self, left: Any, right: Any) -> bool:
        """Greater than comparison."""
        if left is None or right is None:
            return False
        try:
            return float(left) > float(right)
        except (ValueError, TypeError):
            try:
                return str(left) > str(right)
            except TypeError:
                return False

    def _less_than_or_equal(self, left: Any, right: Any) -> bool:
        """Less than or equal comparison."""
        return self._equal(left, right) or self._less_than(left, right)

    def _greater_than_or_equal(self, left: Any, right: Any) -> bool:
        """Greater than or equal comparison."""
        return self._equal(left, right) or self._greater_than(left, right)


def evaluate_formula(
    formula_ast: Any,
    fields: dict[str, Any],
) -> Any:
    """
    Convenience function to evaluate a formula.

    Args:
        formula_ast: Parsed formula AST
        fields: Field values for the record

    Returns:
        Evaluation result
    """
    evaluator = FormulaEvaluator(fields)
    return evaluator.evaluate(formula_ast)
