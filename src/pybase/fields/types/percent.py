"""Percent field type handler."""

from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class PercentFieldHandler(BaseFieldTypeHandler):
    """
    Handler for percent field type.

    Stores percentage values as decimals (50% stored as 0.5).
    Options:
        - precision: decimal places for display (default: 2)
        - store_as_decimal: if True, 50 input -> 0.5 stored (default: True)
        - min_value: minimum percentage (as decimal)
        - max_value: maximum percentage (as decimal)
    """

    field_type = "percent"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """
        Convert Python value to database-storable format.

        Stores as decimal (e.g., 50% -> 0.5).
        """
        if value is None:
            return None

        try:
            num = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert {value} to percent value")

        # If value > 1, assume it's a percentage (50 means 50%)
        # and convert to decimal. Otherwise assume already decimal.
        if abs(num) > 1:
            return num / 100.0
        return num

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python format (decimal)."""
        if value is None:
            return None
        return float(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate percent field value.

        Args:
            value: Value to validate (can be 0.5 or 50 for 50%)
            options: Optional dict with:
                - min_value: minimum as decimal (e.g., 0 for 0%)
                - max_value: maximum as decimal (e.g., 1 for 100%)
                - allow_negative: whether negative values are allowed

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
            raise ValueError(f"Percent field requires numeric value, got {value}")

        options = options or {}

        # Normalize to decimal if needed
        if abs(num) > 1:
            num = num / 100.0

        # Check negative values
        allow_negative = options.get("allow_negative", True)
        if not allow_negative and num < 0:
            raise ValueError("Negative percent values are not allowed")

        # Check bounds (in decimal form)
        min_value = options.get("min_value")
        if min_value is not None and num < min_value:
            raise ValueError(f"Percent value must be >= {min_value * 100}%")

        max_value = options.get("max_value")
        if max_value is not None and num > max_value:
            raise ValueError(f"Percent value must be <= {max_value * 100}%")

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for percent field."""
        return 0.0

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format percent value for display.

        Args:
            value: Percent value as decimal (0.5 = 50%)
            options: Field options with precision

        Returns:
            Formatted string like "50.00%"
        """
        if value is None:
            return ""

        options = options or {}
        precision = options.get("precision", 2)

        # Convert decimal to percentage for display
        percentage = float(value) * 100
        return f"{percentage:.{precision}f}%"
