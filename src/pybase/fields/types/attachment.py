"""Attachment field type handler."""

from typing import Any
from uuid import uuid4

from pybase.fields.base import BaseFieldTypeHandler


class AttachmentFieldHandler(BaseFieldTypeHandler):
    """
    Handler for attachment field type.

    Stores file attachments with metadata.
    Options:
        - allowed_types: list of allowed MIME types (e.g., ["image/*", "application/pdf"])
        - max_size_mb: maximum file size in MB (default: 10)
        - max_files: maximum number of files (default: None = unlimited)

    Value structure (list of attachment objects):
    [
        {
            "id": "uuid",
            "filename": "drawing.pdf",
            "url": "https://s3.../...",
            "size": 1024000,
            "mime_type": "application/pdf",
            "thumbnails": {
                "small": {"url": "...", "width": 100, "height": 100},
                "large": {"url": "...", "width": 500, "height": 500}
            }
        }
    ]
    """

    field_type = "attachment"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """Convert Python value to database-storable format."""
        if value is None:
            return []
        if isinstance(value, dict):
            return [value]
        if isinstance(value, list):
            return value
        raise ValueError(f"Cannot convert {type(value).__name__} to attachment list")

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert database value to Python format."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate attachment field value.

        Args:
            value: Value to validate (list of attachment objects)
            options: Optional dict with:
                - allowed_types: list of allowed MIME types
                - max_size_mb: maximum file size
                - max_files: maximum number of files

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None or value == []:
            return True

        # Normalize to list
        if isinstance(value, dict):
            value = [value]
        elif not isinstance(value, list):
            raise ValueError(f"Attachment field requires list value, got {type(value).__name__}")

        options = options or {}

        # Check max files
        max_files = options.get("max_files")
        if max_files is not None and len(value) > max_files:
            raise ValueError(f"Maximum {max_files} attachments allowed")

        allowed_types = options.get("allowed_types", [])
        max_size_mb = options.get("max_size_mb", 10)
        max_size_bytes = max_size_mb * 1024 * 1024

        for attachment in value:
            if not isinstance(attachment, dict):
                raise ValueError("Each attachment must be an object")

            # Validate required fields
            if "filename" not in attachment:
                raise ValueError("Attachment must have 'filename'")

            # Validate size if present
            size = attachment.get("size")
            if size is not None and size > max_size_bytes:
                raise ValueError(
                    f"File '{attachment['filename']}' exceeds maximum size of {max_size_mb}MB"
                )

            # Validate MIME type if restrictions exist
            if allowed_types:
                mime_type = attachment.get("mime_type", "")
                if not cls._mime_type_allowed(mime_type, allowed_types):
                    raise ValueError(
                        f"File type '{mime_type}' not allowed. Allowed: {', '.join(allowed_types)}"
                    )

        return True

    @classmethod
    def _mime_type_allowed(cls, mime_type: str, allowed_types: list[str]) -> bool:
        """Check if MIME type matches any allowed pattern."""
        if not mime_type:
            return False

        for pattern in allowed_types:
            if pattern == "*/*":
                return True
            if pattern.endswith("/*"):
                # Match type category (e.g., "image/*")
                category = pattern[:-2]
                if mime_type.startswith(category + "/"):
                    return True
            elif pattern == mime_type:
                return True

        return False

    @classmethod
    def default(cls) -> Any:
        """Get default value for attachment field."""
        return []

    @classmethod
    def create_attachment_object(
        cls,
        filename: str,
        url: str,
        size: int,
        mime_type: str,
        thumbnails: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a properly formatted attachment object.

        Args:
            filename: Original filename
            url: URL to access the file
            size: File size in bytes
            mime_type: MIME type of the file
            thumbnails: Optional thumbnail URLs

        Returns:
            Attachment object dict
        """
        return {
            "id": str(uuid4()),
            "filename": filename,
            "url": url,
            "size": size,
            "mime_type": mime_type,
            "thumbnails": thumbnails or {},
        }

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format attachment field for display.

        Args:
            value: List of attachments
            options: Field options

        Returns:
            Summary string like "3 attachments"
        """
        if not value:
            return ""

        count = len(value)
        if count == 1:
            return value[0].get("filename", "1 attachment")
        return f"{count} attachments"
