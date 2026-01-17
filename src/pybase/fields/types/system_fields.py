"""System field type handlers.

These fields are read-only and managed by the system.
They pull values from Record metadata (created_at, updated_at, etc.).
"""

from datetime import datetime, timezone
from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class CreatedTimeFieldHandler(BaseFieldTypeHandler):
    """
    Handler for created_time field type.

    Read-only field showing when the record was created.
    Pulls value from Record.created_at.
    """

    field_type = "created_time"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """System-managed - returns the value as-is."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert to datetime if string."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """Created time is system-managed and always valid."""
        return True

    @classmethod
    def default(cls) -> Any:
        """Default is current time (set by system on record creation)."""
        return None


class ModifiedTimeFieldHandler(BaseFieldTypeHandler):
    """
    Handler for modified_time (last_modified_time) field type.

    Read-only field showing when the record was last updated.
    Pulls value from Record.updated_at.
    """

    field_type = "last_modified_time"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """System-managed - returns the value as-is."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Convert to datetime if string."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """Modified time is system-managed and always valid."""
        return True

    @classmethod
    def default(cls) -> Any:
        """Default is current time (set by system on record update)."""
        return None


class CreatedByFieldHandler(BaseFieldTypeHandler):
    """
    Handler for created_by field type.

    Read-only field showing who created the record.
    Pulls value from Record.created_by_id.
    """

    field_type = "created_by"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """System-managed - stores user ID."""
        if value is None:
            return None
        return str(value)

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Returns user ID as string."""
        if value is None:
            return None
        return str(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """Created by is system-managed and always valid."""
        return True

    @classmethod
    def default(cls) -> Any:
        """Default is None (set by system on record creation)."""
        return None


class ModifiedByFieldHandler(BaseFieldTypeHandler):
    """
    Handler for modified_by (last_modified_by) field type.

    Read-only field showing who last updated the record.
    Pulls value from Record.last_modified_by_id.
    """

    field_type = "last_modified_by"

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """System-managed - stores user ID."""
        if value is None:
            return None
        return str(value)

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """Returns user ID as string."""
        if value is None:
            return None
        return str(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """Modified by is system-managed and always valid."""
        return True

    @classmethod
    def default(cls) -> Any:
        """Default is None (set by system on record update)."""
        return None
