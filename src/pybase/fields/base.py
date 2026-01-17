"""Base class for field type handlers."""

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
