"""Multi select field type handler."""

from typing import Any

from pybase.fields.types.single_select import SingleSelectFieldHandler


class MultiSelectFieldHandler(SingleSelectFieldHandler):
    """
    Handler for multi select field type.

    Allows selection of multiple options from a predefined list.
    Options:
        - choices: list of {id, name, color} objects
        - allow_new: whether to allow creating new options (default: True)
        - max_selections: maximum number of selections allowed (optional)
    """

    field_type = "multi_select"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """Convert Python value to database-storable format."""
        if value is None:
            return None
        if isinstance(value, str):
            # Single value provided as string
            return [value]
        if isinstance(value, (list, tuple, set)):
            return [str(v) for v in value]
        raise ValueError(f"Cannot convert {type(value).__name__} to multi select value")

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python format."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [value]
        return list(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate multi select field value.

        Args:
            value: Value to validate (list of option names)
            options: Optional dict with:
                - choices: list of {id, name, color} dicts
                - allow_new: whether to allow values not in choices
                - max_selections: maximum number of selections

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        # Normalize to list
        if isinstance(value, str):
            value = [value]
        elif not isinstance(value, (list, tuple, set)):
            raise ValueError(f"Multi select field requires list value, got {type(value).__name__}")

        value = list(value)
        options = options or {}

        # Check max selections
        max_selections = options.get("max_selections")
        if max_selections is not None and len(value) > max_selections:
            raise ValueError(
                f"Multi select allows maximum {max_selections} selections, got {len(value)}"
            )

        # Check each value
        choices = options.get("choices", [])
        valid_names = {choice.get("name") for choice in choices if choice.get("name")}
        allow_new = options.get("allow_new", True)

        for item in value:
            if not isinstance(item, str):
                raise ValueError(
                    f"All multi select values must be strings, got {type(item).__name__}"
                )
            if item not in valid_names and not allow_new:
                raise ValueError(
                    f"Invalid option '{item}'. Valid options: {', '.join(sorted(valid_names))}"
                )

        # Check for duplicates
        if len(value) != len(set(value)):
            raise ValueError("Multi select values must be unique")

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for multi select field."""
        return []

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format multi select value for display.

        Args:
            value: List of selected values
            options: Field options

        Returns:
            Comma-separated string of selections
        """
        if not value:
            return ""
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)
