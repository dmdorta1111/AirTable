"""Lookup field type handler for PyBase.

Lookup fields pull values from linked records, creating computed
read-only fields that display data from related tables.
"""

from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class LookupFieldHandler(BaseFieldTypeHandler):
    """
    Handler for lookup fields.

    Lookup fields are computed fields that retrieve values from
    linked records. They are read-only and automatically update
    when the source data changes.

    Options:
        link_field_id: UUID of the link field to look up through (required)
        lookup_field_id: UUID of the field to retrieve from linked records (required)
        result_type: Type of the looked-up field (for display formatting)

    Storage format:
        Lookup fields are computed and don't store data directly.
        When serialized for caching, they store the computed values
        as a list matching the linked records.
    """

    field_type = "lookup"

    @classmethod
    def serialize(cls, value: Any) -> list[Any] | None:
        """
        Serialize looked-up values for caching.

        Args:
            value: Computed lookup values (list of values from linked records)

        Returns:
            List of values or None
        """
        if value is None:
            return None

        if not isinstance(value, list):
            return [value]

        return value

    @classmethod
    def deserialize(cls, value: Any) -> list[Any] | None:
        """
        Deserialize cached lookup values.

        Args:
            value: Cached lookup values

        Returns:
            List of values or None
        """
        if value is None:
            return None

        if isinstance(value, list):
            return value

        return [value]

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate lookup field configuration.

        Note: Lookup values themselves are computed and don't need validation.
        This validates the field configuration.

        Args:
            value: Value (ignored for lookup fields)
            options: Field options including:
                - link_field_id: Required link field reference
                - lookup_field_id: Required target field reference

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        options = options or {}

        # Validate required configuration
        if "link_field_id" not in options:
            raise ValueError("Lookup field must specify link_field_id in options")

        if "lookup_field_id" not in options:
            raise ValueError("Lookup field must specify lookup_field_id in options")

        # Values are computed, so any value is technically valid
        return True

    @classmethod
    def default(cls) -> list[Any] | None:
        """
        Get default value.

        Lookup fields are computed, so default is always None.

        Returns:
            None
        """
        return None

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format lookup values for display.

        Args:
            value: Looked-up values
            options: Field options including result_type for formatting

        Returns:
            Comma-separated string of values
        """
        if value is None:
            return ""

        if not isinstance(value, list):
            value = [value]

        # Filter out None values
        values = [v for v in value if v is not None]

        if not values:
            return ""

        # Format each value as string
        formatted = [str(v) for v in values]

        return ", ".join(formatted)

    @classmethod
    def compute(
        cls,
        linked_records: list[dict[str, Any]],
        lookup_field_id: str,
        options: dict[str, Any] | None = None,
    ) -> list[Any]:
        """
        Compute lookup values from linked records.

        This is the core computation method that extracts values
        from the linked records.

        Args:
            linked_records: List of linked record data dicts
            lookup_field_id: ID of the field to extract
            options: Additional options

        Returns:
            List of extracted values
        """
        if not linked_records:
            return []

        values = []
        for record in linked_records:
            if not isinstance(record, dict):
                continue

            # Try to get field value from record's fields
            fields = record.get("fields", record)
            if lookup_field_id in fields:
                values.append(fields[lookup_field_id])
            elif "values" in record and lookup_field_id in record["values"]:
                values.append(record["values"][lookup_field_id])

        return values

    @classmethod
    def is_computed(cls) -> bool:
        """
        Indicate that this is a computed field type.

        Returns:
            True (lookup fields are always computed)
        """
        return True

    @classmethod
    def is_read_only(cls) -> bool:
        """
        Indicate that this field type is read-only.

        Returns:
            True (lookup fields cannot be directly edited)
        """
        return True
