"""Base class for field type handlers."""

import re
from abc import ABC, abstractmethod
from typing import Any


class BaseFieldTypeHandler(ABC):
    """
    Base class for field type handlers.

    Each field type (text, number, date, etc.) should implement this class
    to provide serialization, deserialization, and validation logic.
    """

    field_type: str

    @classmethod
    @abstractmethod
    def serialize(cls, value: Any) -> Any:
        """
        Convert Python value to database-storable format.

        Args:
            value: Python value to serialize

        Returns:
            Database-storable value (JSON-serializable)
        """
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, value: Any) -> Any:
        """
        Convert database value to Python format.

        Args:
            value: Database value to deserialize

        Returns:
            Python value
        """
        pass

    @classmethod
    @abstractmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate value against field type requirements.

        Args:
            value: Value to validate
            options: Field type-specific options

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        pass

    @classmethod
    @abstractmethod
    def default(cls) -> Any:
        """
        Get default value for field type.

        Returns:
            Default value (JSON-serializable)
        """
        pass

    @classmethod
    def _validate_regex(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Helper method to validate value against regex pattern from options.

        This method can be called by concrete field type implementations to provide
        regex validation support via the options dict.

        Args:
            value: Value to validate
            options: Optional dict with 'regex' key containing regex pattern string

        Returns:
            True if valid or no regex specified

        Raises:
            ValueError: If value doesn't match regex pattern or regex is invalid
        """
        if not options or "regex" not in options:
            return True

        if value is None or value == "":
            return True

        regex_pattern = options["regex"]
        if not regex_pattern:
            return True

        try:
            pattern = re.compile(regex_pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {regex_pattern} - {str(e)}")

        value_str = str(value)
        if not pattern.match(value_str):
            raise ValueError(f"Value '{value_str}' does not match required pattern: {regex_pattern}")

        return True
