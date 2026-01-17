"""Duration field type handler."""

import re
from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class DurationFieldHandler(BaseFieldTypeHandler):
    """
    Handler for duration field type.

    Stores duration as total seconds (integer).
    Options:
        - format: display format - "h:mm", "h:mm:ss", "compact" (default: "h:mm:ss")
        - max_duration: maximum duration in seconds
    """

    field_type = "duration"

    # Patterns for parsing duration strings
    DURATION_PATTERNS = [
        # 2h 30m 15s, 2h30m15s, 2h 30m, 2h30m
        re.compile(
            r"(?:(\d+)\s*h(?:ours?)?)?\s*(?:(\d+)\s*m(?:in(?:utes?)?)?)?\s*(?:(\d+)\s*s(?:ec(?:onds?)?)?)?",
            re.IGNORECASE,
        ),
        # 2:30:15, 2:30
        re.compile(r"(\d+):(\d{1,2})(?::(\d{1,2}))?"),
    ]

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """
        Convert Python value to database-storable format.

        Stores as total seconds (integer).
        """
        if value is None:
            return None

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        if isinstance(value, str):
            return cls._parse_duration(value)

        raise ValueError(f"Cannot convert {type(value).__name__} to duration")

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python integer (seconds)."""
        if value is None:
            return None
        return int(value)

    @classmethod
    def _parse_duration(cls, value: str) -> int:
        """Parse duration string into total seconds."""
        value = value.strip()

        if not value:
            return 0

        # Try colon format first (2:30:15 or 2:30)
        colon_match = re.match(r"^(\d+):(\d{1,2})(?::(\d{1,2}))?$", value)
        if colon_match:
            hours = int(colon_match.group(1))
            minutes = int(colon_match.group(2))
            seconds = int(colon_match.group(3)) if colon_match.group(3) else 0
            return hours * 3600 + minutes * 60 + seconds

        # Try human format (2h 30m 15s)
        human_match = re.match(
            r"^(?:(\d+)\s*h(?:ours?)?)?\s*(?:(\d+)\s*m(?:in(?:utes?)?)?)?\s*(?:(\d+)\s*s(?:ec(?:onds?)?)?)?$",
            value,
            re.IGNORECASE,
        )
        if human_match and any(human_match.groups()):
            hours = int(human_match.group(1) or 0)
            minutes = int(human_match.group(2) or 0)
            seconds = int(human_match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds

        # Try plain number (assume seconds)
        try:
            return int(float(value))
        except ValueError:
            pass

        raise ValueError(f"Invalid duration format: {value}")

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate duration field value.

        Args:
            value: Value to validate
            options: Optional dict with:
                - max_duration: maximum seconds allowed

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        try:
            seconds = cls.serialize(value)
        except ValueError as e:
            raise ValueError(f"Invalid duration: {e}")

        if seconds < 0:
            raise ValueError("Duration cannot be negative")

        options = options or {}
        max_duration = options.get("max_duration")
        if max_duration is not None and seconds > max_duration:
            raise ValueError(f"Duration exceeds maximum of {max_duration} seconds")

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for duration field."""
        return 0

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format duration value for display.

        Args:
            value: Duration in seconds
            options: Field options with format

        Returns:
            Formatted string like "2h 30m" or "2:30:00"
        """
        if value is None:
            return ""

        seconds = int(value)
        options = options or {}
        fmt = options.get("format", "h:mm:ss")

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if fmt == "compact":
            parts = []
            if hours:
                parts.append(f"{hours}h")
            if minutes:
                parts.append(f"{minutes}m")
            if secs or not parts:
                parts.append(f"{secs}s")
            return " ".join(parts)
        elif fmt == "h:mm":
            return f"{hours}:{minutes:02d}"
        else:  # h:mm:ss
            return f"{hours}:{minutes:02d}:{secs:02d}"
