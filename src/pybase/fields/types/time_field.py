"""Time field type handler."""

from datetime import time
from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class TimeFieldHandler(BaseFieldTypeHandler):
    """
    Handler for time field type.

    Stores time as HH:MM:SS string.
    Options:
        - time_format: "12h" or "24h" (default: "24h")
        - include_seconds: whether to include seconds (default: True)
    """

    field_type = "time"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """
        Convert Python value to database-storable format.

        Stores as HH:MM:SS string.
        """
        if value is None:
            return None

        if isinstance(value, time):
            return value.strftime("%H:%M:%S")

        if isinstance(value, str):
            # Validate by parsing
            parsed = cls._parse_time(value)
            return parsed.strftime("%H:%M:%S")

        raise ValueError(f"Cannot convert {type(value).__name__} to time")

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python time."""
        if value is None:
            return None

        if isinstance(value, time):
            return value

        if isinstance(value, str):
            return cls._parse_time(value)

        raise ValueError(f"Cannot deserialize {type(value).__name__} to time")

    @classmethod
    def _parse_time(cls, value: str) -> time:
        """Parse time string in various formats."""
        value = value.strip()

        # Try common formats
        formats = [
            "%H:%M:%S",  # 14:30:00
            "%H:%M",  # 14:30
            "%I:%M:%S %p",  # 02:30:00 PM
            "%I:%M %p",  # 02:30 PM
            "%I:%M:%S%p",  # 02:30:00PM
            "%I:%M%p",  # 02:30PM
        ]

        for fmt in formats:
            try:
                from datetime import datetime

                parsed = datetime.strptime(value.upper(), fmt)
                return parsed.time()
            except ValueError:
                continue

        raise ValueError(f"Invalid time format: {value}")

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate time field value.

        Args:
            value: Value to validate (time object or string)
            options: Optional dict (currently unused)

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        try:
            if isinstance(value, str):
                cls._parse_time(value)
            elif not isinstance(value, time):
                raise ValueError(f"Time field requires time or string, got {type(value).__name__}")
        except ValueError as e:
            raise ValueError(f"Invalid time: {e}")

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for time field."""
        return None

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format time value for display.

        Args:
            value: Time value
            options: Field options with time_format, include_seconds

        Returns:
            Formatted string like "2:30 PM" or "14:30"
        """
        if value is None:
            return ""

        options = options or {}
        time_format = options.get("time_format", "24h")
        include_seconds = options.get("include_seconds", False)

        if isinstance(value, str):
            value = cls._parse_time(value)

        if time_format == "12h":
            if include_seconds:
                return value.strftime("%I:%M:%S %p").lstrip("0")
            else:
                return value.strftime("%I:%M %p").lstrip("0")
        else:
            if include_seconds:
                return value.strftime("%H:%M:%S")
            else:
                return value.strftime("%H:%M")
