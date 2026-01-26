"""Text field type handler."""

import re
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
            options: Optional dict with:
                - max_length: maximum length (default: 255)
                - min_length: minimum length (default: 0)
                - regex: regex pattern to match against

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

        # Regex validation
        if options and "regex" in options:
            regex_pattern = options["regex"]
            try:
                pattern = re.compile(regex_pattern)
                if not pattern.match(value):
                    raise ValueError(f"Text value does not match required pattern: {regex_pattern}")
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {regex_pattern} - {e}")

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for text field."""
        return ""
