"""Number field type handler."""

from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class NumberFieldHandler(BaseFieldTypeHandler):
    """Handler for number field type."""

    field_type = "number"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """Convert Python value to database-storable format."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert {value} to number")

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python format."""
        if value is None:
            return None
        return float(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate number field value.

        Args:
            value: Value to validate
            options: Optional dict with 'min_value', 'max_value', 'precision' keys

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        try:
            num = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Number field requires numeric value, got {value}")

        if options:
            min_value = options.get("min_value")
            if min_value is not None and num < min_value:
                raise ValueError(f"Number value must be >= {min_value}")

            max_value = options.get("max_value")
            if max_value is not None and num > max_value:
                raise ValueError(f"Number value must be <= {max_value}")

            precision = options.get("precision")
            if precision is not None and not isinstance(num, int):
                rounded = round(num, precision)
                if abs(num - rounded) > 10 ** (-precision):
                    raise ValueError(
                        f"Number value exceeds precision of {precision} decimal places"
                    )

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for number field."""
        return 0.0
