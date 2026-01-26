"""Text field type handler."""

import re
from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class TextFieldHandler(BaseFieldTypeHandler):
    """
    Handler for text field type.

    Provides validation, serialization, and deserialization for text values.
    Supports advanced validation options including length constraints and
    regex pattern matching.

    Validation Options:
        - min_length: Minimum text length (default: 0)
        - max_length: Maximum text length (default: 255)
        - regex: Regular expression pattern to match against

    Example Usage:
        # Create a text field with length constraints
        TextFieldHandler.validate("Hello World", {
            "min_length": 5,
            "max_length": 50
        })

        # Validate against regex pattern
        TextFieldHandler.validate("ABC-123", {
            "regex": "^[A-Z]{3}-[0-9]{3}$"
        })

        # Combine multiple validation options
        TextFieldHandler.validate("Product_SKU", {
            "min_length": 3,
            "max_length": 20,
            "regex": "^[A-Za-z0-9_]+$"
        })
    """

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

        Examples:
            # Basic length validation
            TextFieldHandler.validate("Hello", {"min_length": 3, "max_length": 10})  # passes
            TextFieldHandler.validate("Hi", {"min_length": 3})  # raises ValueError

            # Regex pattern validation
            TextFieldHandler.validate("ABC123", {"regex": "^[A-Z]{3}[0-9]{3}$"})  # passes
            TextFieldHandler.validate("abc123", {"regex": "^[A-Z]{3}[0-9]{3}$"})  # raises ValueError

            # Combined validation options
            options = {
                "min_length": 5,
                "max_length": 20,
                "regex": "^[A-Za-z0-9_-]+$"
            }
            TextFieldHandler.validate("User_Name-123", options)  # passes

            # Real-world example: Username validation
            username_options = {
                "min_length": 3,
                "max_length": 20,
                "regex": "^[a-z][a-z0-9_]*$"  # start with letter, alphanumeric + underscore
            }
            TextFieldHandler.validate("john_doe", username_options)  # passes

            # Real-world example: Product SKU validation
            sku_options = {
                "regex": "^[A-Z]{3}-[0-9]{4}$",
                "min_length": 8,
                "max_length": 8
            }
            TextFieldHandler.validate("ABC-1234", sku_options)  # passes
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
