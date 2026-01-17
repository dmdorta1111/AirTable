"""Link field type handler for PyBase.

Link fields create relationships between records in different tables.
They support bidirectional relationships where changes in one table
automatically update the linked table.
"""

from typing import Any
from uuid import UUID

from pybase.fields.base import BaseFieldTypeHandler


class LinkFieldHandler(BaseFieldTypeHandler):
    """
    Handler for link (linked record) fields.

    Link fields store references to records in other tables, enabling
    relational data modeling. They support:
    - One-to-many relationships
    - Many-to-many relationships
    - Bidirectional linking (symmetric relationships)

    Options:
        linked_table_id: UUID of the table to link to (required)
        inverse_field_id: UUID of the inverse link field (auto-created for bidirectional)
        is_symmetric: Whether changes should update the linked table (default: True)
        allow_multiple: Whether to allow linking to multiple records (default: True)
        limit: Maximum number of linked records (optional)

    Storage format:
        List of record UUIDs as strings: ["uuid1", "uuid2", ...]
    """

    field_type = "link"

    @classmethod
    def serialize(cls, value: Any) -> list[str] | None:
        """
        Convert linked records to database format.

        Args:
            value: List of record UUIDs (as UUID objects or strings)

        Returns:
            List of UUID strings or None
        """
        if value is None:
            return None

        if not isinstance(value, list):
            value = [value]

        result = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, UUID):
                result.append(str(item))
            elif isinstance(item, str):
                # Validate UUID format
                try:
                    UUID(item)
                    result.append(item)
                except ValueError:
                    continue
            elif isinstance(item, dict) and "id" in item:
                # Support dict format: {"id": "uuid", "name": "..."}
                result.append(str(item["id"]))

        return result if result else None

    @classmethod
    def deserialize(cls, value: Any) -> list[str] | None:
        """
        Convert database value to list of UUID strings.

        Args:
            value: Database value (list of UUID strings)

        Returns:
            List of UUID strings or None
        """
        if value is None:
            return None

        if isinstance(value, list):
            return [str(v) for v in value if v is not None]

        if isinstance(value, str):
            return [value]

        return None

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate linked record references.

        Args:
            value: Value to validate
            options: Field options including:
                - linked_table_id: Required target table UUID
                - allow_multiple: Whether multiple links are allowed
                - limit: Maximum number of links

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        options = options or {}

        # Ensure linked_table_id is configured
        if "linked_table_id" not in options:
            raise ValueError("Link field must specify linked_table_id in options")

        # Normalize to list
        if not isinstance(value, list):
            value = [value]

        # Check allow_multiple constraint
        if not options.get("allow_multiple", True) and len(value) > 1:
            raise ValueError("This link field only allows a single linked record")

        # Check limit constraint
        limit = options.get("limit")
        if limit is not None and len(value) > limit:
            raise ValueError(f"Maximum {limit} linked records allowed")

        # Validate each UUID
        for item in value:
            if item is None:
                continue

            uuid_str = None
            if isinstance(item, UUID):
                uuid_str = str(item)
            elif isinstance(item, str):
                uuid_str = item
            elif isinstance(item, dict) and "id" in item:
                uuid_str = str(item["id"])
            else:
                raise ValueError(f"Invalid linked record format: {type(item)}")

            # Validate UUID format
            try:
                UUID(uuid_str)
            except ValueError:
                raise ValueError(f"Invalid record UUID: {uuid_str}")

        return True

    @classmethod
    def default(cls) -> list[str] | None:
        """
        Get default value (empty list or None).

        Returns:
            None (no default linked records)
        """
        return None

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format linked records for display.

        This returns a count; actual record names should be resolved
        by the application layer.

        Args:
            value: Linked record UUIDs
            options: Field options

        Returns:
            Display string like "3 linked records"
        """
        if value is None:
            return ""

        if not isinstance(value, list):
            value = [value]

        count = len(value)
        if count == 0:
            return ""
        elif count == 1:
            return "1 linked record"
        else:
            return f"{count} linked records"

    @classmethod
    def create_inverse_field_options(
        cls,
        source_table_id: str,
        source_field_id: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate options for the inverse link field.

        When creating a bidirectional link, this generates the options
        for the automatically created field in the linked table.

        Args:
            source_table_id: UUID of the table creating the link
            source_field_id: UUID of the link field being created
            options: Original field options

        Returns:
            Options dict for the inverse field
        """
        options = options or {}
        return {
            "linked_table_id": source_table_id,
            "inverse_field_id": source_field_id,
            "is_symmetric": options.get("is_symmetric", True),
            "allow_multiple": True,  # Inverse always allows multiple
            "is_inverse": True,  # Mark as auto-created inverse
        }
