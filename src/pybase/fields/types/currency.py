"""Currency field type handler."""

from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class CurrencyFieldHandler(BaseFieldTypeHandler):
    """
    Handler for currency field type.

    Stores monetary values with currency code and precision.
    Options:
        - currency_code: ISO 4217 currency code (default: "USD")
        - precision: decimal places (default: 2)
        - symbol_position: "prefix" or "suffix" (default: "prefix")
        - allow_negative: whether negative values are allowed (default: True)
    """

    field_type = "currency"

    # Common currency symbols for display
    CURRENCY_SYMBOLS = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CNY": "¥",
        "KRW": "₩",
        "INR": "₹",
        "BRL": "R$",
        "CAD": "CA$",
        "AUD": "A$",
        "CHF": "CHF",
        "MXN": "MX$",
    }

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
            raise ValueError(f"Cannot convert {value} to currency value")

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python format."""
        if value is None:
            return None
        return float(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate currency field value.

        Args:
            value: Value to validate
            options: Optional dict with:
                - currency_code: ISO 4217 code
                - precision: decimal places
                - allow_negative: bool
                - min_value: minimum value
                - max_value: maximum value

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
            raise ValueError(f"Currency field requires numeric value, got {value}")

        options = options or {}

        # Check negative values
        allow_negative = options.get("allow_negative", True)
        if not allow_negative and num < 0:
            raise ValueError("Negative currency values are not allowed")

        # Check min/max bounds
        min_value = options.get("min_value")
        if min_value is not None and num < min_value:
            raise ValueError(f"Currency value must be >= {min_value}")

        max_value = options.get("max_value")
        if max_value is not None and num > max_value:
            raise ValueError(f"Currency value must be <= {max_value}")

        # Check precision
        precision = options.get("precision", 2)
        if precision is not None:
            rounded = round(num, precision)
            if abs(num - rounded) > 10 ** (-(precision + 1)):
                raise ValueError(f"Currency value exceeds precision of {precision} decimal places")

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for currency field."""
        return 0.0

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format currency value for display.

        Args:
            value: Currency value
            options: Field options with currency_code, precision, symbol_position

        Returns:
            Formatted string like "$1,234.56" or "1.234,56 €"
        """
        if value is None:
            return ""

        options = options or {}
        currency_code = options.get("currency_code", "USD")
        precision = options.get("precision", 2)
        symbol_position = options.get("symbol_position", "prefix")

        # Get currency symbol
        symbol = cls.CURRENCY_SYMBOLS.get(currency_code, currency_code)

        # Format number with commas and precision
        formatted_num = f"{abs(float(value)):,.{precision}f}"

        # Add negative sign if needed
        negative_prefix = "-" if float(value) < 0 else ""

        # Position symbol
        if symbol_position == "suffix":
            return f"{negative_prefix}{formatted_num} {symbol}"
        else:
            return f"{negative_prefix}{symbol}{formatted_num}"
