"""Formula field type handler for PyBase.

Formula fields compute values based on expressions that can
reference other fields and use built-in functions.
"""

from typing import Any
from datetime import datetime, date

from pybase.fields.base import BaseFieldTypeHandler

# Late imports to avoid circular dependencies
_parser = None
_evaluator = None


def _get_parser():
    """Lazy load parser to avoid import issues."""
    global _parser
    if _parser is None:
        from pybase.formula.parser import FormulaParser

        _parser = FormulaParser()
    return _parser


def _get_evaluator():
    """Lazy load evaluator."""
    global _evaluator
    if _evaluator is None:
        from pybase.formula.evaluator import FormulaEvaluator

        _evaluator = FormulaEvaluator()
    return _evaluator


class FormulaFieldHandler(BaseFieldTypeHandler):
    """
    Handler for formula fields.

    Formula fields are computed fields that evaluate expressions
    to produce their values. They can reference other fields and
    use a rich set of built-in functions.

    Options:
        formula: The formula expression string (required)
        result_type: Expected result type ('text', 'number', 'date', 'datetime', 'boolean')
        precision: Decimal places for numeric results (default: 2)
        date_format: Format string for date results

    Storage format:
        Formula fields are computed. When cached, values are stored
        in their natural type (string, number, date, etc.)
    """

    field_type = "formula"

    # Parsed formula cache (formula_string -> AST)
    _formula_cache: dict[str, Any] = {}

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """
        Serialize formula result for storage.

        Args:
            value: Computed formula result

        Returns:
            JSON-serializable value
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, date):
            return value.isoformat()

        if isinstance(value, (list, tuple)):
            return [cls.serialize(v) for v in value]

        return value

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """
        Deserialize cached formula value.

        Args:
            value: Cached value

        Returns:
            Deserialized value
        """
        # Values are already in usable format
        return value

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate formula field configuration.

        Args:
            value: Value (ignored for formula fields)
            options: Field options including:
                - formula: Required formula expression

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        options = options or {}

        if "formula" not in options:
            raise ValueError("Formula field must specify 'formula' in options")

        formula = options["formula"]

        # Validate formula syntax
        try:
            parser = _get_parser()
            parser.parse(formula)
        except Exception as e:
            raise ValueError(f"Invalid formula syntax: {e}")

        # Validate result_type if specified
        result_type = options.get("result_type")
        if result_type and result_type not in (
            "text",
            "number",
            "date",
            "datetime",
            "boolean",
            "auto",
        ):
            raise ValueError(
                f"Invalid result_type '{result_type}'. "
                "Must be one of: text, number, date, datetime, boolean, auto"
            )

        return True

    @classmethod
    def default(cls) -> Any:
        """
        Get default value.

        Formula fields are computed, so default is None.

        Returns:
            None
        """
        return None

    @classmethod
    def compute(
        cls,
        formula: str,
        fields: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> Any:
        """
        Compute formula value.

        Args:
            formula: Formula expression string
            fields: Dictionary of field values
            options: Field options (for result formatting)

        Returns:
            Computed formula result
        """
        options = options or {}

        try:
            # Parse formula (with caching)
            if formula not in cls._formula_cache:
                parser = _get_parser()
                cls._formula_cache[formula] = parser.parse(formula)

            ast = cls._formula_cache[formula]

            # Evaluate
            evaluator = _get_evaluator()
            result = evaluator.evaluate(ast, fields)

            # Apply result type conversion
            result_type = options.get("result_type", "auto")
            result = cls._convert_result(result, result_type, options)

            return result
        except Exception as e:
            # Return None for invalid formulas in safe mode
            return None

    @classmethod
    def _convert_result(
        cls,
        value: Any,
        result_type: str,
        options: dict[str, Any],
    ) -> Any:
        """Convert result to expected type."""
        if value is None:
            return None

        if result_type == "auto":
            return value

        if result_type == "text":
            return str(value)

        if result_type == "number":
            try:
                v = float(value)
                precision = options.get("precision", 2)
                if precision is not None:
                    v = round(v, precision)
                return v
            except (ValueError, TypeError):
                return None

        if result_type == "boolean":
            return bool(value)

        if result_type in ("date", "datetime"):
            if isinstance(value, datetime):
                return value if result_type == "datetime" else value.date()
            if isinstance(value, date):
                return value
            # Try parsing string
            if isinstance(value, str):
                try:
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    return dt if result_type == "datetime" else dt.date()
                except ValueError:
                    pass
            return None

        return value

    @classmethod
    def get_referenced_fields(cls, formula: str) -> list[str]:
        """
        Get list of field names referenced in formula.

        Args:
            formula: Formula expression string

        Returns:
            List of field names
        """
        try:
            parser = _get_parser()
            return parser.get_field_references(formula)
        except Exception:
            return []

    @classmethod
    def validate_formula_syntax(cls, formula: str) -> tuple[bool, str | None]:
        """
        Validate formula syntax.

        Args:
            formula: Formula expression string

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            parser = _get_parser()
            return parser.validate(formula)
        except Exception as e:
            return False, str(e)

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format formula result for display.

        Args:
            value: Formula result
            options: Field options

        Returns:
            Formatted display string
        """
        if value is None:
            return ""

        options = options or {}
        result_type = options.get("result_type", "auto")

        if result_type == "number" or isinstance(value, float):
            precision = options.get("precision", 2)
            if precision is not None and isinstance(value, float):
                return f"{value:.{precision}f}"
            return str(value)

        if isinstance(value, datetime):
            date_format = options.get("date_format", "%Y-%m-%d %H:%M:%S")
            return value.strftime(date_format)

        if isinstance(value, date):
            date_format = options.get("date_format", "%Y-%m-%d")
            return value.strftime(date_format)

        if isinstance(value, bool):
            return "Yes" if value else "No"

        if isinstance(value, (list, tuple)):
            return ", ".join(str(v) for v in value if v is not None)

        return str(value)

    @classmethod
    def is_computed(cls) -> bool:
        """
        Indicate that this is a computed field type.

        Returns:
            True (formula fields are always computed)
        """
        return True

    @classmethod
    def is_read_only(cls) -> bool:
        """
        Indicate that this field type is read-only.

        Returns:
            True (formula fields cannot be directly edited)
        """
        return True
