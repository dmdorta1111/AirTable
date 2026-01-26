"""Base class for field type handlers."""

import re
from abc import ABC, abstractmethod
from typing import Any, Callable


class BaseFieldTypeHandler(ABC):
    """
    Base class for field type handlers.

    Each field type (text, number, date, etc.) should implement this class
    to provide serialization, deserialization, and validation logic.

    Validation Options:
        Field types can support various validation options via the options dict
        parameter in the validate() method. Common options include:

        - regex: Regex pattern string for pattern matching
        - custom_validator: Custom validation callable or expression string

        Use the helper methods _validate_regex() and _validate_custom() to
        implement these validations in concrete field type handlers.

    Example:
        class MyFieldHandler(BaseFieldTypeHandler):
            @classmethod
            def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
                # Basic field-specific validation
                if value is None:
                    return True

                # Use helper methods for common validation patterns
                cls._validate_regex(value, options)
                cls._validate_custom(value, options)

                return True
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

    @classmethod
    def _validate_custom(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Helper method to validate value using custom validator from options.

        This method can be called by concrete field type implementations to provide
        custom validation support via the options dict.

        Args:
            value: Value to validate
            options: Optional dict with 'custom_validator' key containing:
                - Callable: A function that takes the value and returns bool or raises ValueError
                - str: A simple expression string (e.g., "len(value) > 5")
                       Note: Expression strings use eval() and should be used with caution.
                       Prefer using callable functions for security.

        Returns:
            True if valid or no custom_validator specified

        Raises:
            ValueError: If custom validation fails
            TypeError: If custom_validator is not callable or string

        Example:
            # Using a callable
            def validate_even(value):
                if value % 2 != 0:
                    raise ValueError("Value must be even")
                return True

            options = {"custom_validator": validate_even}
            cls._validate_custom(42, options)  # passes

            # Using an expression string (caution: less safe)
            options = {"custom_validator": "len(value) >= 3"}
            cls._validate_custom("abc", options)  # passes
        """
        if not options or "custom_validator" not in options:
            return True

        if value is None or value == "":
            return True

        custom_validator = options["custom_validator"]
        if not custom_validator:
            return True

        # Handle callable validator
        if callable(custom_validator):
            try:
                result = custom_validator(value)
                # If it returns False or raises ValueError, validation fails
                if result is False:
                    raise ValueError(f"Custom validation failed for value: {value}")
                return True
            except ValueError:
                # Re-raise ValueError from the custom validator
                raise
            except Exception as e:
                # Wrap other exceptions as ValueError
                raise ValueError(f"Custom validator error: {str(e)}")

        # Handle expression string validator
        if isinstance(custom_validator, str):
            try:
                # Create a safe evaluation context with limited builtins
                safe_context = {
                    "__builtins__": {
                        "len": len,
                        "str": str,
                        "int": int,
                        "float": float,
                        "bool": bool,
                        "abs": abs,
                        "min": min,
                        "max": max,
                    },
                    "value": value,
                }
                result = eval(custom_validator, safe_context)
                if not result:
                    raise ValueError(
                        f"Custom validation failed: '{custom_validator}' returned False for value: {value}"
                    )
                return True
            except ValueError:
                raise
            except Exception as e:
                raise ValueError(f"Custom validator expression error: {str(e)}")

        # Invalid validator type
        raise TypeError(
            f"custom_validator must be callable or string, got {type(custom_validator).__name__}"
        )
