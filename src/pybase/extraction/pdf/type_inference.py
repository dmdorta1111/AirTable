"""Column type inference for extracted table data.

Automatically detects column data types (numeric, date, text) with confidence scoring.
"""

import re
from typing import Any
from enum import Enum

# Optional dependencies
try:
    from dateutil import parser as date_parser

    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False
    date_parser = None


class ColumnType(str, Enum):
    """Detected column data types."""

    INTEGER = "integer"
    FLOAT = "float"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    DATE = "date"
    DATETIME = "datetime"
    TEXT = "text"
    BOOLEAN = "boolean"
    EMPTY = "empty"


class TypeInferenceResult:
    """Result of column type inference.

    Attributes:
        column_type: Detected type from ColumnType enum
        confidence: Confidence score (0.0 to 1.0)
        sample_values: Sample values used for inference
        metadata: Additional type-specific metadata
    """

    def __init__(
        self,
        column_type: ColumnType,
        confidence: float,
        sample_values: list[Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.column_type = column_type
        self.confidence = confidence
        self.sample_values = sample_values or []
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "type": self.column_type.value,
            "confidence": self.confidence,
            "sample_values": self.sample_values,
            "metadata": self.metadata,
        }


def _clean_value(value: Any) -> str | None:
    """
    Clean and normalize a value for type detection.

    Args:
        value: Raw value from table cell

    Returns:
        Cleaned string value or None if empty
    """
    if value is None:
        return None

    # Convert to string and strip whitespace
    str_value = str(value).strip()

    # Return None for empty values
    if not str_value or str_value.lower() in ("", "n/a", "na", "null", "none", "-"):
        return None

    return str_value


def _detect_boolean(values: list[str]) -> TypeInferenceResult | None:
    """
    Detect if column contains boolean values.

    Args:
        values: List of cleaned string values

    Returns:
        TypeInferenceResult if boolean type detected, None otherwise
    """
    if not values:
        return None

    boolean_patterns = {
        "true",
        "false",
        "yes",
        "no",
        "y",
        "n",
        "t",
        "f",
        "1",
        "0",
        "on",
        "off",
    }

    matches = sum(1 for v in values if v.lower() in boolean_patterns)
    confidence = matches / len(values)

    if confidence >= 0.8:
        return TypeInferenceResult(
            column_type=ColumnType.BOOLEAN,
            confidence=confidence,
            sample_values=values[:3],
            metadata={"pattern": "boolean"},
        )

    return None


def _detect_numeric(values: list[str]) -> TypeInferenceResult | None:
    """
    Detect numeric types (integer, float, currency, percentage).

    Args:
        values: List of cleaned string values

    Returns:
        TypeInferenceResult if numeric type detected, None otherwise
    """
    if not values:
        return None

    # Patterns for numeric types
    currency_pattern = re.compile(r"^[$€£¥₹]?\s*-?\d{1,3}(?:,\d{3})*(?:\.\d+)?$")
    percentage_pattern = re.compile(r"^-?\d+(?:\.\d+)?%$")
    float_pattern = re.compile(r"^-?\d+\.\d+$")
    integer_pattern = re.compile(r"^-?\d+$")

    currency_matches = 0
    percentage_matches = 0
    float_matches = 0
    integer_matches = 0

    for value in values:
        # Remove common separators for analysis
        clean_val = value.replace(",", "").replace(" ", "")

        if currency_pattern.match(value):
            currency_matches += 1
        elif percentage_pattern.match(value):
            percentage_matches += 1
        elif float_pattern.match(clean_val):
            float_matches += 1
        elif integer_pattern.match(clean_val):
            integer_matches += 1

    total = len(values)

    # Check currency (highest priority for numeric)
    if currency_matches / total >= 0.8:
        return TypeInferenceResult(
            column_type=ColumnType.CURRENCY,
            confidence=currency_matches / total,
            sample_values=values[:3],
            metadata={"pattern": "currency"},
        )

    # Check percentage
    if percentage_matches / total >= 0.8:
        return TypeInferenceResult(
            column_type=ColumnType.PERCENTAGE,
            confidence=percentage_matches / total,
            sample_values=values[:3],
            metadata={"pattern": "percentage"},
        )

    # Check float
    if float_matches / total >= 0.8:
        return TypeInferenceResult(
            column_type=ColumnType.FLOAT,
            confidence=float_matches / total,
            sample_values=values[:3],
            metadata={"pattern": "float"},
        )

    # Check integer
    if integer_matches / total >= 0.8:
        return TypeInferenceResult(
            column_type=ColumnType.INTEGER,
            confidence=integer_matches / total,
            sample_values=values[:3],
            metadata={"pattern": "integer"},
        )

    return None


def _detect_date(values: list[str]) -> TypeInferenceResult | None:
    """
    Detect date and datetime types.

    Args:
        values: List of cleaned string values

    Returns:
        TypeInferenceResult if date type detected, None otherwise
    """
    if not values:
        return None

    # Common date patterns
    date_patterns = [
        re.compile(r"^\d{4}-\d{2}-\d{2}$"),  # 2024-01-15
        re.compile(r"^\d{2}/\d{2}/\d{4}$"),  # 01/15/2024
        re.compile(r"^\d{2}-\d{2}-\d{4}$"),  # 01-15-2024
        re.compile(r"^\d{4}/\d{2}/\d{2}$"),  # 2024/01/15
        re.compile(r"^\d{1,2}\s+\w+\s+\d{4}$"),  # 15 Jan 2024
        re.compile(r"^\w+\s+\d{1,2},?\s+\d{4}$"),  # Jan 15, 2024
    ]

    datetime_patterns = [
        re.compile(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}"),  # 2024-01-15 14:30
        re.compile(r"^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}"),  # 01/15/2024 14:30
    ]

    date_matches = 0
    datetime_matches = 0
    fuzzy_matches = 0

    for value in values:
        # Check datetime patterns first (more specific)
        if any(pattern.match(value) for pattern in datetime_patterns):
            datetime_matches += 1
            continue

        # Check date patterns
        if any(pattern.match(value) for pattern in date_patterns):
            date_matches += 1
            continue

        # Fuzzy date parsing if dateutil available
        if DATEUTIL_AVAILABLE:
            try:
                # Try to parse as date
                date_parser.parse(value, fuzzy=False)
                fuzzy_matches += 1
            except (ValueError, TypeError, OverflowError):
                pass

    total = len(values)

    # Check datetime
    if datetime_matches / total >= 0.8:
        return TypeInferenceResult(
            column_type=ColumnType.DATETIME,
            confidence=datetime_matches / total,
            sample_values=values[:3],
            metadata={"pattern": "datetime"},
        )

    # Check date (including fuzzy matches)
    total_date_matches = date_matches + fuzzy_matches
    if total_date_matches / total >= 0.8:
        confidence = total_date_matches / total
        return TypeInferenceResult(
            column_type=ColumnType.DATE,
            confidence=confidence,
            sample_values=values[:3],
            metadata={"pattern": "date", "fuzzy_parsing": fuzzy_matches > 0},
        )

    return None


def infer_column_type(column_values: list[Any]) -> TypeInferenceResult:
    """
    Infer the data type of a single column.

    Analyzes column values and detects the most likely data type with confidence score.
    Detection order: boolean, numeric (currency, percentage, float, integer), date, text.

    Args:
        column_values: List of values from a single column

    Returns:
        TypeInferenceResult with detected type and confidence score

    Example:
        >>> values = ["$10.50", "$20.00", "$15.75"]
        >>> result = infer_column_type(values)
        >>> result.column_type
        ColumnType.CURRENCY
        >>> result.confidence
        1.0
    """
    # Clean values and filter out None/empty
    cleaned_values = [_clean_value(v) for v in column_values]
    non_empty_values = [v for v in cleaned_values if v is not None]

    # Handle empty column
    if not non_empty_values:
        return TypeInferenceResult(
            column_type=ColumnType.EMPTY,
            confidence=1.0,
            sample_values=[],
            metadata={"total_values": len(column_values), "empty_count": len(column_values)},
        )

    # Calculate empty ratio for metadata
    empty_ratio = 1.0 - (len(non_empty_values) / len(column_values))

    # Try boolean detection
    boolean_result = _detect_boolean(non_empty_values)
    if boolean_result:
        boolean_result.metadata["empty_ratio"] = empty_ratio
        return boolean_result

    # Try numeric detection
    numeric_result = _detect_numeric(non_empty_values)
    if numeric_result:
        numeric_result.metadata["empty_ratio"] = empty_ratio
        return numeric_result

    # Try date detection
    date_result = _detect_date(non_empty_values)
    if date_result:
        date_result.metadata["empty_ratio"] = empty_ratio
        return date_result

    # Default to text
    return TypeInferenceResult(
        column_type=ColumnType.TEXT,
        confidence=1.0,
        sample_values=non_empty_values[:3],
        metadata={"empty_ratio": empty_ratio, "pattern": "text"},
    )


def infer_column_types(
    headers: list[str],
    rows: list[list[Any]],
    sample_size: int | None = None,
) -> list[dict[str, Any]]:
    """
    Infer data types for all columns in a table.

    Args:
        headers: List of column headers
        rows: List of row data (list of lists)
        sample_size: Optional limit on number of rows to sample (None = all rows)

    Returns:
        List of type inference results, one per column

    Example:
        >>> headers = ["ID", "Price", "Date", "Description"]
        >>> rows = [
        ...     [1, "$10.50", "2024-01-15", "Item A"],
        ...     [2, "$20.00", "2024-01-16", "Item B"],
        ... ]
        >>> types = infer_column_types(headers, rows)
        >>> len(types)
        4
        >>> types[1]["type"]
        "currency"
    """
    if not headers or not rows:
        return []

    # Determine sample size
    rows_to_analyze = rows if sample_size is None else rows[:sample_size]

    # Get number of columns
    num_columns = len(headers)

    # Extract column values
    results = []
    for col_idx in range(num_columns):
        # Extract all values for this column
        column_values = []
        for row in rows_to_analyze:
            # Handle rows with fewer columns
            if col_idx < len(row):
                column_values.append(row[col_idx])
            else:
                column_values.append(None)

        # Infer type for this column
        result = infer_column_type(column_values)

        # Add column name to result
        result_dict = result.to_dict()
        result_dict["column_name"] = headers[col_idx]
        result_dict["column_index"] = col_idx

        results.append(result_dict)

    return results
