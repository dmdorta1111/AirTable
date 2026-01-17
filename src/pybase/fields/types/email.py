"""Email field type handler."""

import re
from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class EmailFieldHandler(BaseFieldTypeHandler):
    """
    Handler for email field type.

    Validates and stores email addresses.
    Options:
        - allow_multiple: whether to allow comma-separated emails (default: False)
    """

    field_type = "email"

    # RFC 5322 simplified email regex
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """Convert Python value to database-storable format."""
        if value is None:
            return None
        if isinstance(value, list):
            return [str(v).strip().lower() for v in value]
        return str(value).strip().lower()

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python format."""
        return value

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate email field value.

        Args:
            value: Value to validate
            options: Optional dict with:
                - allow_multiple: allow comma-separated emails

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None or value == "":
            return True

        options = options or {}
        allow_multiple = options.get("allow_multiple", False)

        # Handle list input
        if isinstance(value, list):
            if not allow_multiple and len(value) > 1:
                raise ValueError("Multiple emails not allowed")
            emails = value
        elif allow_multiple and "," in str(value):
            emails = [e.strip() for e in str(value).split(",")]
        else:
            emails = [str(value)]

        for email in emails:
            email = email.strip()
            if not email:
                continue
            if not cls.EMAIL_PATTERN.match(email):
                raise ValueError(f"Invalid email format: {email}")

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for email field."""
        return None
