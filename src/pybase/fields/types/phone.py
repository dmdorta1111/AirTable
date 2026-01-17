"""Phone field type handler."""

import re
from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class PhoneFieldHandler(BaseFieldTypeHandler):
    """
    Handler for phone field type.

    Stores and validates phone numbers.
    Options:
        - default_country_code: default country code (e.g., "+1")
        - format: display format style
    """

    field_type = "phone"

    # Basic phone pattern (allows various formats)
    PHONE_PATTERN = re.compile(r"^\+?[\d\s\-\(\)\.]{7,20}$")

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """
        Convert Python value to database-storable format.

        Stores the normalized phone number.
        """
        if value is None:
            return None
        # Remove formatting but keep + for country code
        normalized = re.sub(r"[\s\-\(\)\.]", "", str(value))
        return normalized

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python format."""
        return value

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate phone field value.

        Args:
            value: Value to validate
            options: Optional dict (currently unused)

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None or value == "":
            return True

        phone_str = str(value).strip()

        if not cls.PHONE_PATTERN.match(phone_str):
            raise ValueError(f"Invalid phone number format: {phone_str}")

        # Check minimum digits (at least 7 after removing formatting)
        digits_only = re.sub(r"\D", "", phone_str)
        if len(digits_only) < 7:
            raise ValueError("Phone number must have at least 7 digits")

        if len(digits_only) > 15:
            raise ValueError("Phone number too long (max 15 digits)")

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for phone field."""
        return None

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format phone number for display.

        Args:
            value: Phone number
            options: Field options

        Returns:
            Formatted phone string
        """
        if not value:
            return ""

        # Simple US format if 10 digits
        digits = re.sub(r"\D", "", str(value))
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == "1":
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

        # Return as-is for other formats
        return str(value)
