"""URL field type handler."""

import re
from typing import Any
from urllib.parse import urlparse

from pybase.fields.base import BaseFieldTypeHandler


class URLFieldHandler(BaseFieldTypeHandler):
    """
    Handler for URL field type.

    Validates and stores URLs.
    Options:
        - allowed_protocols: list of allowed protocols (default: ["http", "https"])
        - require_protocol: whether URL must have protocol (default: True)
    """

    field_type = "url"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """Convert Python value to database-storable format."""
        if value is None:
            return None
        url = str(value).strip()
        # Add https:// if no protocol specified
        if url and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
            url = "https://" + url
        return url

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python format."""
        return value

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate URL field value.

        Args:
            value: Value to validate
            options: Optional dict with:
                - allowed_protocols: list of allowed protocols
                - require_protocol: whether protocol is required

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None or value == "":
            return True

        url = str(value).strip()
        options = options or {}
        allowed_protocols = options.get("allowed_protocols", ["http", "https"])
        require_protocol = options.get("require_protocol", True)

        # Add default protocol if missing and not required
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
            if require_protocol:
                raise ValueError("URL must include protocol (e.g., https://)")
            url = "https://" + url

        try:
            parsed = urlparse(url)

            # Check protocol
            if parsed.scheme.lower() not in allowed_protocols:
                raise ValueError(f"URL protocol must be one of: {', '.join(allowed_protocols)}")

            # Check for valid netloc (domain)
            if not parsed.netloc:
                raise ValueError("URL must have a valid domain")

            # Basic domain validation
            domain = parsed.netloc.split(":")[0]  # Remove port if present
            if not re.match(
                r"^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*$",
                domain,
            ):
                # Allow localhost and IP addresses
                if domain not in ["localhost"] and not re.match(
                    r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", domain
                ):
                    raise ValueError(f"Invalid domain: {domain}")

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Invalid URL: {e}")

        return True

    @classmethod
    def default(cls) -> Any:
        """Get default value for URL field."""
        return None

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format URL for display.

        Args:
            value: URL value
            options: Field options

        Returns:
            URL string
        """
        if not value:
            return ""
        return str(value)
