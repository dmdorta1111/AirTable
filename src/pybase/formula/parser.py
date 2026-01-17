"""Formula parser for PyBase.

Parses formula strings into an AST using Lark parser.
"""

from typing import Any
from dataclasses import dataclass

try:
    from lark import Lark, Transformer, v_args, Token

    LARK_AVAILABLE = True
except ImportError:
    LARK_AVAILABLE = False
    Lark = None
    Transformer = object
    v_args = lambda *args, **kwargs: lambda x: x
    Token = None

from pybase.formula.grammar import FORMULA_GRAMMAR


# AST Node types
@dataclass
class NumberNode:
    value: float | int


@dataclass
class StringNode:
    value: str


@dataclass
class BooleanNode:
    value: bool | None  # None represents BLANK


@dataclass
class FieldRefNode:
    field_name: str


@dataclass
class FunctionCallNode:
    name: str
    arguments: list[Any]


@dataclass
class BinaryOpNode:
    operator: str
    left: Any
    right: Any


@dataclass
class UnaryOpNode:
    operator: str
    operand: Any


class FormulaTransformer(Transformer if LARK_AVAILABLE else object):
    """Transform Lark parse tree into AST nodes."""

    @v_args(inline=True)
    def number(self, token):
        value = float(token)
        # Keep as int if no decimal
        if value == int(value):
            value = int(value)
        return NumberNode(value)

    @v_args(inline=True)
    def string(self, token):
        # Remove quotes
        s = str(token)
        return StringNode(s[1:-1])

    @v_args(inline=True)
    def boolean(self, token):
        val = str(token).upper()
        if val == "TRUE":
            return BooleanNode(True)
        elif val == "FALSE":
            return BooleanNode(False)
        else:  # BLANK
            return BooleanNode(None)

    @v_args(inline=True)
    def field_ref(self, token):
        # Extract field name from {Field Name}
        field_name = str(token)[1:-1]
        return FieldRefNode(field_name)

    def function_call(self, items):
        name = str(items[0]).upper()
        args = list(items[1]) if len(items) > 1 and items[1] else []
        return FunctionCallNode(name, args)

    def arguments(self, items):
        return list(items)

    # Binary operators
    @v_args(inline=True)
    def add(self, left, right):
        return BinaryOpNode("+", left, right)

    @v_args(inline=True)
    def sub(self, left, right):
        return BinaryOpNode("-", left, right)

    @v_args(inline=True)
    def mul(self, left, right):
        return BinaryOpNode("*", left, right)

    @v_args(inline=True)
    def div(self, left, right):
        return BinaryOpNode("/", left, right)

    @v_args(inline=True)
    def mod(self, left, right):
        return BinaryOpNode("%", left, right)

    @v_args(inline=True)
    def pow(self, left, right):
        return BinaryOpNode("^", left, right)

    @v_args(inline=True)
    def string_concat(self, left, right):
        return BinaryOpNode("&", left, right)

    # Comparison operators
    @v_args(inline=True)
    def eq(self, left, right):
        return BinaryOpNode("=", left, right)

    @v_args(inline=True)
    def ne(self, left, right):
        return BinaryOpNode("!=", left, right)

    @v_args(inline=True)
    def lt(self, left, right):
        return BinaryOpNode("<", left, right)

    @v_args(inline=True)
    def gt(self, left, right):
        return BinaryOpNode(">", left, right)

    @v_args(inline=True)
    def le(self, left, right):
        return BinaryOpNode("<=", left, right)

    @v_args(inline=True)
    def ge(self, left, right):
        return BinaryOpNode(">=", left, right)

    # Logical operators
    @v_args(inline=True)
    def and_op(self, left, right):
        return BinaryOpNode("AND", left, right)

    @v_args(inline=True)
    def or_op(self, left, right):
        return BinaryOpNode("OR", left, right)

    @v_args(inline=True)
    def not_op(self, operand):
        return UnaryOpNode("NOT", operand)

    # Unary operators
    @v_args(inline=True)
    def neg(self, operand):
        return UnaryOpNode("-", operand)

    @v_args(inline=True)
    def pos(self, operand):
        return operand  # Positive is a no-op


class FormulaParser:
    """
    Parser for PyBase formulas.

    Parses formula strings into an AST that can be evaluated.
    """

    def __init__(self):
        if not LARK_AVAILABLE:
            raise ImportError(
                "Lark parser library is required for formula support. "
                "Install it with: pip install lark"
            )
        self._parser = Lark(
            FORMULA_GRAMMAR,
            parser="lalr",
            transformer=FormulaTransformer(),
        )

    def parse(self, formula: str) -> Any:
        """
        Parse a formula string into an AST.

        Args:
            formula: Formula string to parse

        Returns:
            AST root node

        Raises:
            ValueError: If formula syntax is invalid
        """
        try:
            return self._parser.parse(formula)
        except Exception as e:
            raise ValueError(f"Invalid formula syntax: {e}")

    def validate(self, formula: str) -> tuple[bool, str | None]:
        """
        Validate formula syntax without full parsing.

        Args:
            formula: Formula string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            self.parse(formula)
            return True, None
        except ValueError as e:
            return False, str(e)

    def get_field_references(self, formula: str) -> list[str]:
        """
        Extract all field references from a formula.

        Args:
            formula: Formula string

        Returns:
            List of field names referenced in the formula
        """
        ast = self.parse(formula)
        fields: list[str] = []
        self._collect_fields(ast, fields)
        return list(set(fields))

    def _collect_fields(self, node: Any, fields: list[str]) -> None:
        """Recursively collect field references from AST."""
        if isinstance(node, FieldRefNode):
            fields.append(node.field_name)
        elif isinstance(node, BinaryOpNode):
            self._collect_fields(node.left, fields)
            self._collect_fields(node.right, fields)
        elif isinstance(node, UnaryOpNode):
            self._collect_fields(node.operand, fields)
        elif isinstance(node, FunctionCallNode):
            for arg in node.arguments:
                self._collect_fields(arg, fields)
