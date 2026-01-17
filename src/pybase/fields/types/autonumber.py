"""Autonumber field type handler."""

from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class AutonumberFieldHandler(BaseFieldTypeHandler):
    """
    Handler for autonumber field type.

    Automatically generates sequential numbers for records.
    Options:
        - prefix: string prefix (e.g., "INV-")
        - start_value: starting number (default: 1)
        - padding: zero-padding digits (default: 4)
    """

    field_type = "autonumber"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """
        Convert Python value to database-storable format.

        Stores the raw integer value; formatting is done on display.
        """
        if value is None:
            return None
        if isinstance(value, str):
            # Extract number from formatted string like "INV-0001"
            import re

            match = re.search(r"\d+", value)
            if match:
                return int(match.group())
            raise ValueError(f"Cannot extract number from {value}")
        return int(value)

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python format."""
        if value is None:
            return None
        return int(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate autonumber field value.

        Note: Autonumber values are system-generated and typically not user-editable.

        Args:
            value: Value to validate
            options: Optional dict (unused)

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        try:
            num = int(value) if not isinstance(value, int) else value
            if isinstance(value, str):
                # Try to extract number from formatted string
                import re

                match = re.search(r"\d+", value)
                if match:
                    num = int(match.group())
                else:
                    raise ValueError("No number found")
        except (ValueError, TypeError):
            raise ValueError(f"Autonumber must be an integer, got {type(value).__name__}")

        if num < 0:
            raise ValueError("Autonumber cannot be negative")

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for autonumber field."""
        return None  # Will be assigned by the system

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format autonumber for display.

        Args:
            value: Integer value
            options: Field options with prefix, padding

        Returns:
            Formatted string like "INV-0001"
        """
        if value is None:
            return ""

        options = options or {}
        prefix = options.get("prefix", "")
        padding = options.get("padding", 4)

        return f"{prefix}{int(value):0{padding}d}"

    @classmethod
    def generate_next(
        cls,
        current_max: int | None,
        options: dict[str, Any] | None = None,
    ) -> int:
        """
        Generate the next autonumber value.

        Args:
            current_max: Current maximum value in the table (or None if no records)
            options: Field options with start_value

        Returns:
            Next autonumber value
        """
        options = options or {}
        start_value = options.get("start_value", 1)

        if current_max is None:
            return start_value

        return current_max + 1
