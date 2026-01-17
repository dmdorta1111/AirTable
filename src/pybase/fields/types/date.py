"""Date field type handler."""

from datetime import date, datetime
from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class DateFieldHandler(BaseFieldTypeHandler):
    """Handler for date field type."""

    field_type = "date"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """Convert Python value to database-storable format."""
        if value is None:
            return None

        if isinstance(value, date):
            return value.isoformat()

        if isinstance(value, datetime):
            return value.date().isoformat()

        if isinstance(value, str):
            try:
                # Try parsing ISO format
                parsed = datetime.fromisoformat(value)
                return parsed.date().isoformat()
            except ValueError:
                raise ValueError(f"Invalid date format: {value}")

        raise ValueError(
            f"Cannot convert {type(value).__name__} to date, expected date or ISO string"
        )

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python format."""
        if value is None:
            return None

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                raise ValueError(f"Invalid date format: {value}")

        raise ValueError(f"Cannot deserialize {type(value).__name__} to date")

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate date field value.

        Args:
            value: Value to validate
            options: Optional dict with 'min_date', 'max_date' keys

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        # Try to convert to date
        try:
            if isinstance(value, date):
                date_value = value
            elif isinstance(value, datetime):
                date_value = value.date()
            elif isinstance(value, str):
                date_value = datetime.fromisoformat(value).date()
            else:
                raise ValueError(
                    f"Date field requires date, datetime, or ISO string, got {type(value).__name__}"
                )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid date value: {value}") from e

        # Check min/max date constraints
        if options:
            min_date_str = options.get("min_date")
            if min_date_str:
                min_date = date.fromisoformat(min_date_str)
                if date_value < min_date:
                    raise ValueError(f"Date must be on or after {min_date_str}")

            max_date_str = options.get("max_date")
            if max_date_str:
                max_date = date.fromisoformat(max_date_str)
                if date_value > max_date:
                    raise ValueError(f"Date must be on or before {max_date_str}")

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for date field."""
        return None
