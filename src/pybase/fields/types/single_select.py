"""Single select field type handler."""

from typing import Any
from uuid import uuid4

from pybase.fields.base import BaseFieldTypeHandler


class SingleSelectFieldHandler(BaseFieldTypeHandler):
    """
    Handler for single select field type.

    Allows selection of one option from a predefined list.
    Options:
        - choices: list of {id, name, color} objects
        - allow_new: whether to allow creating new options (default: True)
    """

    field_type = "single_select"

    # Default colors for new options
    DEFAULT_COLORS = [
        "blue",
        "cyan",
        "teal",
        "green",
        "yellow",
        "orange",
        "red",
        "pink",
        "purple",
        "gray",
    ]

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
        Validate single select field value.

        Args:
            value: Value to validate (option name)
            options: Optional dict with:
                - choices: list of {id, name, color} dicts
                - allow_new: whether to allow values not in choices

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        if not isinstance(value, str):
            raise ValueError(
                f"Single select field requires string value, got {type(value).__name__}"
            )

        options = options or {}
        choices = options.get("choices", [])
        allow_new = options.get("allow_new", True)

        # Extract valid choice names
        valid_names = {choice.get("name") for choice in choices if choice.get("name")}

        if value not in valid_names:
            if not allow_new:
                raise ValueError(
                    f"Invalid option '{value}'. Valid options: {', '.join(sorted(valid_names))}"
                )
            # If allow_new is True, any string value is acceptable

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for single select field."""
        return None

    @classmethod
    def add_choice(
        cls,
        options: dict[str, Any],
        name: str,
        color: str | None = None,
    ) -> dict[str, Any]:
        """
        Add a new choice to field options.

        Args:
            options: Current field options
            name: Choice name
            color: Optional color (will auto-assign if not provided)

        Returns:
            Updated options dict
        """
        choices = list(options.get("choices", []))

        # Check for duplicate
        if any(c.get("name") == name for c in choices):
            return options

        # Auto-assign color if not provided
        if color is None:
            used_colors = {c.get("color") for c in choices}
            for default_color in cls.DEFAULT_COLORS:
                if default_color not in used_colors:
                    color = default_color
                    break
            else:
                color = cls.DEFAULT_COLORS[len(choices) % len(cls.DEFAULT_COLORS)]

        choices.append(
            {
                "id": str(uuid4()),
                "name": name,
                "color": color,
            }
        )

        return {**options, "choices": choices}

    @classmethod
    def remove_choice(
        cls,
        options: dict[str, Any],
        name: str,
    ) -> dict[str, Any]:
        """
        Remove a choice from field options.

        Args:
            options: Current field options
            name: Choice name to remove

        Returns:
            Updated options dict
        """
        choices = [c for c in options.get("choices", []) if c.get("name") != name]
        return {**options, "choices": choices}

    @classmethod
    def get_choice_color(
        cls,
        options: dict[str, Any],
        name: str,
    ) -> str | None:
        """
        Get color for a choice.

        Args:
            options: Field options
            name: Choice name

        Returns:
            Color string or None if not found
        """
        for choice in options.get("choices", []):
            if choice.get("name") == name:
                return choice.get("color")
        return None
