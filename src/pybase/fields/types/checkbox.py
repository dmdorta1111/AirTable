"""Checkbox field type handler."""

from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class CheckboxFieldHandler(BaseFieldTypeHandler):
    """Handler for checkbox field type."""

    field_type = "checkbox"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """Convert Python value to database-storable format."""
        if value is None:
            return False
        return bool(value)

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python format."""
        if value is None:
            return False
        return bool(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate checkbox field value.

        Args:
            value: Value to validate
            options: Not used for checkbox

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        if not isinstance(value, (bool, int, str)):
            raise ValueError(f"Checkbox field requires boolean value, got {type(value).__name__}")

        # Convert truthy values to bool for validation
        bool_value = bool(value)
        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for checkbox field."""
        return False
