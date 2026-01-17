"""Rating field type handler."""

from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class RatingFieldHandler(BaseFieldTypeHandler):
    """
    Handler for rating field type.

    Stores integer rating values (1 to max).
    Options:
        - max_rating: maximum rating value (default: 5)
        - icon: display icon type (default: "star")
        - allow_half: allow half ratings like 3.5 (default: False)
    """

    field_type = "rating"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """Convert Python value to database-storable format."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert {value} to rating")

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python format."""
        if value is None:
            return None
        return float(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate rating field value.

        Args:
            value: Value to validate
            options: Optional dict with:
                - max_rating: maximum rating (default: 5)
                - allow_half: allow half values (default: False)

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        try:
            rating = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Rating must be a number, got {type(value).__name__}")

        options = options or {}
        max_rating = options.get("max_rating", 5)
        allow_half = options.get("allow_half", False)

        if rating < 0:
            raise ValueError("Rating cannot be negative")

        if rating > max_rating:
            raise ValueError(f"Rating must be <= {max_rating}")

        # Check for valid increments
        if allow_half:
            # Must be a multiple of 0.5
            if rating % 0.5 != 0:
                raise ValueError("Rating must be in increments of 0.5")
        else:
            # Must be a whole number
            if rating != int(rating):
                raise ValueError("Rating must be a whole number")

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for rating field."""
        return None

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format rating for display.

        Args:
            value: Rating value
            options: Field options with max_rating, icon

        Returns:
            Visual representation of rating
        """
        if value is None:
            return ""

        options = options or {}
        max_rating = options.get("max_rating", 5)
        icon = options.get("icon", "star")

        rating = float(value)
        full = int(rating)
        half = rating - full >= 0.5

        icons = {
            "star": ("★", "☆", "⯪"),
            "heart": ("♥", "♡", "♡"),
            "circle": ("●", "○", "◐"),
        }

        filled, empty, half_icon = icons.get(icon, icons["star"])

        result = filled * full
        if half:
            result += half_icon
            full += 1
        result += empty * (max_rating - full)

        return result
