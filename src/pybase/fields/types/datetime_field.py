"""DateTime field type handler."""

from datetime import datetime, timezone
from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class DateTimeFieldHandler(BaseFieldTypeHandler):
    """
    Handler for datetime field type.

    Stores date and time as ISO 8601 string with timezone.
    Options:
        - include_time: whether to include time (default: True)
        - time_format: "12h" or "24h" (default: "24h")
        - timezone: timezone name (default: "UTC")
        - date_format: strftime format for date part
    """

    field_type = "datetime"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """
        Convert Python value to database-storable format.

        Stores as ISO 8601 string.
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            # Ensure timezone aware
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.isoformat()

        if isinstance(value, str):
            # Validate by parsing
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return parsed.isoformat()
            except ValueError:
                raise ValueError(f"Invalid datetime format: {value}")

        raise ValueError(f"Cannot convert {type(value).__name__} to datetime")

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python datetime."""
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed
            except ValueError:
                raise ValueError(f"Invalid datetime format: {value}")

        raise ValueError(f"Cannot deserialize {type(value).__name__} to datetime")

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate datetime field value.

        Args:
            value: Value to validate (datetime object or ISO string)
            options: Optional dict with:
                - min_date: minimum datetime
                - max_date: maximum datetime

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        # Try to parse/validate
        try:
            if isinstance(value, str):
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            elif isinstance(value, datetime):
                parsed = value
            else:
                raise ValueError(
                    f"DateTime field requires datetime or ISO string, got {type(value).__name__}"
                )
        except ValueError as e:
            raise ValueError(f"Invalid datetime: {e}")

        options = options or {}

        # Check bounds
        min_date = options.get("min_date")
        if min_date is not None:
            if isinstance(min_date, str):
                min_date = datetime.fromisoformat(min_date.replace("Z", "+00:00"))
            if parsed < min_date:
                raise ValueError(f"DateTime must be on or after {min_date.isoformat()}")

        max_date = options.get("max_date")
        if max_date is not None:
            if isinstance(max_date, str):
                max_date = datetime.fromisoformat(max_date.replace("Z", "+00:00"))
            if parsed > max_date:
                raise ValueError(f"DateTime must be on or before {max_date.isoformat()}")

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for datetime field."""
        return None

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format datetime value for display.

        Args:
            value: DateTime value
            options: Field options with time_format, date_format

        Returns:
            Formatted string
        """
        if value is None:
            return ""

        options = options or {}
        time_format = options.get("time_format", "24h")
        include_time = options.get("include_time", True)

        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if include_time:
            if time_format == "12h":
                return value.strftime("%Y-%m-%d %I:%M %p")
            else:
                return value.strftime("%Y-%m-%d %H:%M")
        else:
            return value.strftime("%Y-%m-%d")
