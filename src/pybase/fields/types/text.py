"""Text field type handler."""

from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class TextFieldHandler(BaseFieldTypeHandler):
    """Handler for text field type."""

    field_type = "text"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """Convert Python value to database-storable format."""
        if value is None:
            return None
        return str(value)

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python format."""
        if value is None:
            return None
        return str(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate text field value.

        Args:
            value: Value to validate
            options: Optional dict with 'max_length' and 'min_length' keys

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        max_length = options.get("max_length", 255) if options else 255
        min_length = options.get("min_length", 0) if options else 0

        if not isinstance(value, str):
            raise ValueError(f"Text field requires string value, got {type(value).__name__}")

        if len(value) > max_length:
            raise ValueError(f"Text value exceeds max length of {max_length}")

        if len(value) < min_length:
            raise ValueError(f"Text value is below min length of {min_length}")

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for text field."""
        return ""
