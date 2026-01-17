"""Rollup field type handler for PyBase.

Rollup fields aggregate values from linked records using various
aggregation functions like sum, average, count, etc.
"""

from typing import Any
from decimal import Decimal, InvalidOperation
from datetime import datetime, date

from pybase.fields.base import BaseFieldTypeHandler


class RollupFieldHandler(BaseFieldTypeHandler):
    """
    Handler for rollup fields.

    Rollup fields aggregate values from linked records using
    specified aggregation functions. They are computed read-only
    fields that update when source data changes.

    Options:
        link_field_id: UUID of the link field to roll up through (required)
        rollup_field_id: UUID of the field to aggregate from linked records (required)
        aggregation: Aggregation function to use (required)

    Supported aggregation functions:
        - sum: Sum of numeric values
        - avg/average: Average of numeric values
        - min: Minimum value
        - max: Maximum value
        - count: Count of linked records (ignores rollup_field_id)
        - counta: Count of non-empty values
        - countall: Count including empty values
        - empty: Count of empty values
        - percent_empty: Percentage of empty values
        - percent_filled: Percentage of non-empty values
        - array_unique: Unique values as list
        - array_compact: Non-empty values as list
        - array_join: Concatenated string with separator
        - and: Logical AND of boolean values
        - or: Logical OR of boolean values
        - xor: Logical XOR of boolean values
        - earliest: Earliest date/datetime
        - latest: Latest date/datetime
        - range: Difference between max and min

    Storage format:
        Rollup fields are computed. Cached values depend on aggregation type.
    """

    field_type = "rollup"

    # Supported aggregation functions
    AGGREGATIONS = {
        "sum",
        "avg",
        "average",
        "min",
        "max",
        "count",
        "counta",
        "countall",
        "empty",
        "percent_empty",
        "percent_filled",
        "array_unique",
        "array_compact",
        "array_join",
        "and",
        "or",
        "xor",
        "earliest",
        "latest",
        "range",
    }

    @classmethod
    def serialize(cls, value: Any) -> Any:
        """
        Serialize rollup result for caching.

        Args:
            value: Computed rollup result

        Returns:
            JSON-serializable value
        """
        if value is None:
            return None

        if isinstance(value, Decimal):
            return float(value)

        if isinstance(value, (datetime, date)):
            return value.isoformat()

        if isinstance(value, (list, tuple)):
            return [cls.serialize(v) for v in value]

        return value

    @classmethod
    def deserialize(cls, value: Any) -> Any:
        """
        Deserialize cached rollup value.

        Args:
            value: Cached rollup value

        Returns:
            Deserialized value
        """
        # Rollup values are already in usable format after serialization
        return value

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate rollup field configuration.

        Args:
            value: Value (ignored for rollup fields)
            options: Field options including:
                - link_field_id: Required link field reference
                - rollup_field_id: Required target field reference
                - aggregation: Required aggregation function

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        options = options or {}

        if "link_field_id" not in options:
            raise ValueError("Rollup field must specify link_field_id in options")

        if "rollup_field_id" not in options:
            raise ValueError("Rollup field must specify rollup_field_id in options")

        if "aggregation" not in options:
            raise ValueError("Rollup field must specify aggregation in options")

        aggregation = options["aggregation"].lower()
        if aggregation not in cls.AGGREGATIONS:
            raise ValueError(
                f"Invalid aggregation '{aggregation}'. "
                f"Supported: {', '.join(sorted(cls.AGGREGATIONS))}"
            )

        return True

    @classmethod
    def default(cls) -> Any:
        """
        Get default value.

        Rollup fields are computed, so default is None.

        Returns:
            None
        """
        return None

    @classmethod
    def compute(
        cls,
        values: list[Any],
        aggregation: str,
        options: dict[str, Any] | None = None,
    ) -> Any:
        """
        Compute rollup result from values.

        Args:
            values: List of values from linked records
            aggregation: Aggregation function name
            options: Additional options (e.g., separator for array_join)

        Returns:
            Computed rollup result
        """
        aggregation = aggregation.lower()
        options = options or {}

        if aggregation == "count":
            return len(values)

        if aggregation == "countall":
            return len(values)

        if aggregation == "counta":
            return len([v for v in values if v is not None and v != ""])

        if aggregation == "empty":
            return len([v for v in values if v is None or v == ""])

        if aggregation == "percent_empty":
            if not values:
                return 0.0
            empty_count = len([v for v in values if v is None or v == ""])
            return (empty_count / len(values)) * 100

        if aggregation == "percent_filled":
            if not values:
                return 0.0
            filled_count = len([v for v in values if v is not None and v != ""])
            return (filled_count / len(values)) * 100

        if aggregation == "array_unique":
            seen = set()
            result = []
            for v in values:
                if v is not None and v not in seen:
                    seen.add(v)
                    result.append(v)
            return result

        if aggregation == "array_compact":
            return [v for v in values if v is not None and v != ""]

        if aggregation == "array_join":
            separator = options.get("separator", ", ")
            non_empty = [str(v) for v in values if v is not None and v != ""]
            return separator.join(non_empty)

        # Filter to non-empty values for numeric/date aggregations
        filtered = [v for v in values if v is not None]

        if not filtered:
            return None

        if aggregation == "sum":
            return cls._numeric_sum(filtered)

        if aggregation in ("avg", "average"):
            return cls._numeric_avg(filtered)

        if aggregation == "min":
            return cls._find_min(filtered)

        if aggregation == "max":
            return cls._find_max(filtered)

        if aggregation == "range":
            min_val = cls._find_min(filtered)
            max_val = cls._find_max(filtered)
            if min_val is not None and max_val is not None:
                try:
                    return max_val - min_val
                except TypeError:
                    return None
            return None

        if aggregation == "earliest":
            return cls._find_min(filtered)

        if aggregation == "latest":
            return cls._find_max(filtered)

        if aggregation == "and":
            return all(bool(v) for v in filtered)

        if aggregation == "or":
            return any(bool(v) for v in filtered)

        if aggregation == "xor":
            true_count = sum(1 for v in filtered if bool(v))
            return true_count % 2 == 1

        return None

    @classmethod
    def _numeric_sum(cls, values: list[Any]) -> float | int | None:
        """Sum numeric values."""
        total = Decimal(0)
        has_values = False

        for v in values:
            try:
                if isinstance(v, (int, float, Decimal)):
                    total += Decimal(str(v))
                    has_values = True
                elif isinstance(v, str):
                    total += Decimal(v)
                    has_values = True
            except (InvalidOperation, ValueError):
                continue

        if not has_values:
            return None

        # Return int if whole number, else float
        if total == total.to_integral_value():
            return int(total)
        return float(total)

    @classmethod
    def _numeric_avg(cls, values: list[Any]) -> float | None:
        """Average of numeric values."""
        total = Decimal(0)
        count = 0

        for v in values:
            try:
                if isinstance(v, (int, float, Decimal)):
                    total += Decimal(str(v))
                    count += 1
                elif isinstance(v, str):
                    total += Decimal(v)
                    count += 1
            except (InvalidOperation, ValueError):
                continue

        if count == 0:
            return None

        return float(total / count)

    @classmethod
    def _find_min(cls, values: list[Any]) -> Any:
        """Find minimum value (works for numbers, dates, strings)."""
        comparable = [v for v in values if v is not None]
        if not comparable:
            return None

        try:
            return min(comparable)
        except TypeError:
            # Mixed types - try to find numeric min
            numeric = []
            for v in comparable:
                try:
                    numeric.append(float(v))
                except (TypeError, ValueError):
                    pass
            return min(numeric) if numeric else None

    @classmethod
    def _find_max(cls, values: list[Any]) -> Any:
        """Find maximum value (works for numbers, dates, strings)."""
        comparable = [v for v in values if v is not None]
        if not comparable:
            return None

        try:
            return max(comparable)
        except TypeError:
            # Mixed types - try to find numeric max
            numeric = []
            for v in comparable:
                try:
                    numeric.append(float(v))
                except (TypeError, ValueError):
                    pass
            return max(numeric) if numeric else None

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format rollup result for display.

        Args:
            value: Rollup result
            options: Field options

        Returns:
            Formatted display string
        """
        if value is None:
            return ""

        options = options or {}
        aggregation = options.get("aggregation", "").lower()

        # Format based on aggregation type
        if aggregation in ("percent_empty", "percent_filled"):
            return f"{value:.1f}%"

        if aggregation in ("array_unique", "array_compact"):
            if isinstance(value, list):
                return ", ".join(str(v) for v in value)

        if isinstance(value, bool):
            return "Yes" if value else "No"

        if isinstance(value, float):
            # Clean up floating point display
            if value == int(value):
                return str(int(value))
            return f"{value:.2f}"

        return str(value)

    @classmethod
    def is_computed(cls) -> bool:
        """
        Indicate that this is a computed field type.

        Returns:
            True (rollup fields are always computed)
        """
        return True

    @classmethod
    def is_read_only(cls) -> bool:
        """
        Indicate that this field type is read-only.

        Returns:
            True (rollup fields cannot be directly edited)
        """
        return True
