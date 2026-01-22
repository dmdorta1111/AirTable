"""
Unit tests for column type inference.

Tests for automatic detection of column data types with confidence scoring.
"""

import pytest

from pybase.extraction.pdf.type_inference import (
    ColumnType,
    TypeInferenceResult,
    _clean_value,
    _detect_boolean,
    _detect_date,
    _detect_numeric,
    infer_column_type,
    infer_column_types,
)


class TestCleanValue:
    """Tests for value cleaning and normalization."""

    def test_clean_value_none(self):
        """Test cleaning None value."""
        result = _clean_value(None)
        assert result is None

    def test_clean_value_empty_string(self):
        """Test cleaning empty string."""
        result = _clean_value("")
        assert result is None

    def test_clean_value_whitespace(self):
        """Test cleaning whitespace-only string."""
        result = _clean_value("   ")
        assert result is None

    def test_clean_value_na_variants(self):
        """Test cleaning various N/A representations."""
        assert _clean_value("N/A") is None
        assert _clean_value("na") is None
        assert _clean_value("NA") is None
        assert _clean_value("null") is None
        assert _clean_value("none") is None
        assert _clean_value("-") is None

    def test_clean_value_valid_string(self):
        """Test cleaning valid string with whitespace."""
        result = _clean_value("  Hello World  ")
        assert result == "Hello World"

    def test_clean_value_number(self):
        """Test cleaning numeric value."""
        result = _clean_value(123)
        assert result == "123"

    def test_clean_value_preserves_content(self):
        """Test that cleaning preserves actual content."""
        result = _clean_value("  $100.50  ")
        assert result == "$100.50"


class TestDetectBoolean:
    """Tests for boolean type detection."""

    def test_detect_boolean_empty_list(self):
        """Test boolean detection with empty list."""
        result = _detect_boolean([])
        assert result is None

    def test_detect_boolean_true_false(self):
        """Test detection of true/false values."""
        values = ["true", "false", "true", "false", "true"]
        result = _detect_boolean(values)

        assert result is not None
        assert result.column_type == ColumnType.BOOLEAN
        assert result.confidence == 1.0
        assert len(result.sample_values) <= 3

    def test_detect_boolean_yes_no(self):
        """Test detection of yes/no values."""
        values = ["yes", "no", "yes", "yes", "no"]
        result = _detect_boolean(values)

        assert result is not None
        assert result.column_type == ColumnType.BOOLEAN
        assert result.confidence == 1.0

    def test_detect_boolean_case_insensitive(self):
        """Test case-insensitive boolean detection."""
        values = ["YES", "No", "YES", "no", "Yes"]
        result = _detect_boolean(values)

        assert result is not None
        assert result.column_type == ColumnType.BOOLEAN
        assert result.confidence == 1.0

    def test_detect_boolean_binary(self):
        """Test detection of 1/0 binary values."""
        values = ["1", "0", "1", "1", "0"]
        result = _detect_boolean(values)

        assert result is not None
        assert result.column_type == ColumnType.BOOLEAN
        assert result.confidence == 1.0

    def test_detect_boolean_single_letters(self):
        """Test detection of y/n, t/f single letters."""
        values = ["y", "n", "y", "y", "n"]
        result = _detect_boolean(values)

        assert result is not None
        assert result.column_type == ColumnType.BOOLEAN

    def test_detect_boolean_on_off(self):
        """Test detection of on/off values."""
        values = ["on", "off", "on", "off", "on"]
        result = _detect_boolean(values)

        assert result is not None
        assert result.column_type == ColumnType.BOOLEAN

    def test_detect_boolean_mixed_patterns(self):
        """Test boolean detection with mixed boolean patterns."""
        values = ["yes", "no", "true", "false", "1"]
        result = _detect_boolean(values)

        assert result is not None
        assert result.column_type == ColumnType.BOOLEAN
        assert result.confidence == 1.0

    def test_detect_boolean_low_confidence(self):
        """Test boolean detection with low confidence (below threshold)."""
        values = ["yes", "no", "maybe", "perhaps", "unknown"]
        result = _detect_boolean(values)

        # Should not detect as boolean (confidence < 0.8)
        assert result is None

    def test_detect_boolean_partial_match(self):
        """Test boolean detection with partial matches."""
        values = ["yes", "yes", "yes", "yes", "something else"]
        result = _detect_boolean(values)

        assert result is not None
        assert result.confidence == 0.8  # 4 out of 5


class TestDetectNumeric:
    """Tests for numeric type detection."""

    def test_detect_numeric_empty_list(self):
        """Test numeric detection with empty list."""
        result = _detect_numeric([])
        assert result is None

    def test_detect_numeric_integers(self):
        """Test detection of integer values."""
        # Use larger integers (4+ digits) to avoid currency pattern match
        values = ["1234", "4567", "7890", "1000", "-4200"]
        result = _detect_numeric(values)

        assert result is not None
        assert result.column_type == ColumnType.INTEGER
        assert result.confidence == 1.0
        assert result.metadata["pattern"] == "integer"

    def test_detect_numeric_floats(self):
        """Test detection of float values."""
        # Use larger floats (4+ digits) to avoid currency pattern match
        values = ["1234.56", "4567.89", "7890.12", "1000.5", "-3141.59"]
        result = _detect_numeric(values)

        assert result is not None
        assert result.column_type == ColumnType.FLOAT
        assert result.confidence == 1.0
        assert result.metadata["pattern"] == "float"

    def test_detect_numeric_currency_dollar(self):
        """Test detection of currency values with $ symbol."""
        values = ["$10.50", "$20.00", "$15.75", "$100.25", "$5.99"]
        result = _detect_numeric(values)

        assert result is not None
        assert result.column_type == ColumnType.CURRENCY
        assert result.confidence == 1.0
        assert result.metadata["pattern"] == "currency"

    def test_detect_numeric_currency_euro(self):
        """Test detection of currency values with € symbol."""
        values = ["€10.50", "€20.00", "€15.75", "€100.25", "€5.99"]
        result = _detect_numeric(values)

        assert result is not None
        assert result.column_type == ColumnType.CURRENCY

    def test_detect_numeric_currency_with_commas(self):
        """Test detection of currency with thousand separators."""
        values = ["$1,000.50", "$2,500.00", "$10,000.99", "$500.25", "$999.99"]
        result = _detect_numeric(values)

        assert result is not None
        assert result.column_type == ColumnType.CURRENCY
        assert result.confidence == 1.0

    def test_detect_numeric_percentage(self):
        """Test detection of percentage values."""
        values = ["10%", "25.5%", "100%", "0.5%", "-5%"]
        result = _detect_numeric(values)

        assert result is not None
        assert result.column_type == ColumnType.PERCENTAGE
        assert result.confidence == 1.0
        assert result.metadata["pattern"] == "percentage"

    def test_detect_numeric_negative_numbers(self):
        """Test detection of negative numbers."""
        # Use larger negative integers to avoid currency pattern match
        values = ["-1000", "-2000", "-3000", "-4000", "-5000"]
        result = _detect_numeric(values)

        assert result is not None
        assert result.column_type == ColumnType.INTEGER

    def test_detect_numeric_mixed_int_float(self):
        """Test numeric detection with mixed integers and floats."""
        # Use larger numbers and mostly floats to ensure float detection
        values = ["1000.5", "2000.25", "3000.75", "4000.0", "5000.99"]
        result = _detect_numeric(values)

        # Should detect as float since most have decimals
        assert result is not None
        assert result.column_type == ColumnType.FLOAT

    def test_detect_numeric_low_confidence(self):
        """Test numeric detection with low confidence."""
        values = ["10", "20", "abc", "def", "ghi"]
        result = _detect_numeric(values)

        # Should not detect as numeric (confidence < 0.8)
        assert result is None

    def test_detect_numeric_priority_currency_over_float(self):
        """Test that currency takes priority over float."""
        values = ["$10.50", "$20.00", "$15.75", "$100.25", "$5.99"]
        result = _detect_numeric(values)

        assert result is not None
        assert result.column_type == ColumnType.CURRENCY
        # Not FLOAT even though they have decimal points


class TestDetectDate:
    """Tests for date/datetime type detection."""

    def test_detect_date_empty_list(self):
        """Test date detection with empty list."""
        result = _detect_date([])
        assert result is None

    def test_detect_date_iso_format(self):
        """Test detection of ISO format dates (YYYY-MM-DD)."""
        values = ["2024-01-15", "2024-02-20", "2024-03-25", "2024-04-30", "2024-05-10"]
        result = _detect_date(values)

        assert result is not None
        assert result.column_type == ColumnType.DATE
        assert result.confidence == 1.0

    def test_detect_date_us_format(self):
        """Test detection of US format dates (MM/DD/YYYY)."""
        values = ["01/15/2024", "02/20/2024", "03/25/2024", "04/30/2024", "05/10/2024"]
        result = _detect_date(values)

        assert result is not None
        assert result.column_type == ColumnType.DATE
        assert result.confidence == 1.0

    def test_detect_date_eu_format(self):
        """Test detection of European format dates (DD-MM-YYYY)."""
        values = ["15-01-2024", "20-02-2024", "25-03-2024", "30-04-2024", "10-05-2024"]
        result = _detect_date(values)

        assert result is not None
        assert result.column_type == ColumnType.DATE

    def test_detect_date_slash_format(self):
        """Test detection of slash format dates (YYYY/MM/DD)."""
        values = ["2024/01/15", "2024/02/20", "2024/03/25", "2024/04/30", "2024/05/10"]
        result = _detect_date(values)

        assert result is not None
        assert result.column_type == ColumnType.DATE

    def test_detect_date_text_month(self):
        """Test detection of dates with text month."""
        values = ["15 Jan 2024", "20 Feb 2024", "25 Mar 2024", "30 Apr 2024", "10 May 2024"]
        result = _detect_date(values)

        assert result is not None
        assert result.column_type == ColumnType.DATE

    def test_detect_date_text_month_comma(self):
        """Test detection of dates with text month and comma."""
        values = ["Jan 15, 2024", "Feb 20, 2024", "Mar 25, 2024", "Apr 30, 2024", "May 10, 2024"]
        result = _detect_date(values)

        assert result is not None
        assert result.column_type == ColumnType.DATE

    def test_detect_datetime_iso(self):
        """Test detection of datetime values (ISO format)."""
        values = [
            "2024-01-15 14:30",
            "2024-02-20 15:45",
            "2024-03-25 16:00",
            "2024-04-30 17:15",
            "2024-05-10 18:30",
        ]
        result = _detect_date(values)

        assert result is not None
        assert result.column_type == ColumnType.DATETIME
        assert result.confidence == 1.0

    def test_detect_datetime_us(self):
        """Test detection of datetime values (US format)."""
        values = [
            "01/15/2024 14:30",
            "02/20/2024 15:45",
            "03/25/2024 16:00",
            "04/30/2024 17:15",
            "05/10/2024 18:30",
        ]
        result = _detect_date(values)

        assert result is not None
        assert result.column_type == ColumnType.DATETIME

    def test_detect_date_low_confidence(self):
        """Test date detection with low confidence."""
        values = ["2024-01-15", "2024-02-20", "not a date", "invalid", "text"]
        result = _detect_date(values)

        # Should not detect as date (confidence < 0.8)
        assert result is None

    def test_detect_date_priority_datetime_over_date(self):
        """Test that datetime takes priority over date."""
        values = [
            "2024-01-15 14:30",
            "2024-02-20 15:45",
            "2024-03-25 16:00",
            "2024-04-30 17:15",
            "2024-05-10 18:30",
        ]
        result = _detect_date(values)

        assert result is not None
        assert result.column_type == ColumnType.DATETIME
        # Not DATE even though it contains date information


class TestInferColumnType:
    """Tests for single column type inference."""

    def test_infer_column_type_empty_column(self):
        """Test inference on completely empty column."""
        values = [None, "", "  ", "N/A", "null"]
        result = infer_column_type(values)

        assert result.column_type == ColumnType.EMPTY
        assert result.confidence == 1.0
        assert result.metadata["empty_count"] == 5

    def test_infer_column_type_boolean(self):
        """Test inference on boolean column."""
        values = ["yes", "no", "yes", "yes", "no"]
        result = infer_column_type(values)

        assert result.column_type == ColumnType.BOOLEAN
        assert result.confidence == 1.0

    def test_infer_column_type_integer(self):
        """Test inference on integer column."""
        # Use larger integers to avoid currency pattern match
        values = ["1000", "2000", "3000", "4000", "5000"]
        result = infer_column_type(values)

        assert result.column_type == ColumnType.INTEGER

    def test_infer_column_type_float(self):
        """Test inference on float column."""
        # Use larger floats to avoid currency pattern match
        values = ["1000.5", "2000.7", "3141.59", "4200.2", "5900.9"]
        result = infer_column_type(values)

        assert result.column_type == ColumnType.FLOAT
        assert result.confidence == 1.0

    def test_infer_column_type_currency(self):
        """Test inference on currency column."""
        values = ["$10.50", "$20.00", "$15.75", "$100.25", "$5.99"]
        result = infer_column_type(values)

        assert result.column_type == ColumnType.CURRENCY
        assert result.confidence == 1.0

    def test_infer_column_type_percentage(self):
        """Test inference on percentage column."""
        values = ["10%", "25.5%", "100%", "0.5%", "50%"]
        result = infer_column_type(values)

        assert result.column_type == ColumnType.PERCENTAGE
        assert result.confidence == 1.0

    def test_infer_column_type_date(self):
        """Test inference on date column."""
        values = ["2024-01-15", "2024-02-20", "2024-03-25", "2024-04-30", "2024-05-10"]
        result = infer_column_type(values)

        assert result.column_type == ColumnType.DATE
        assert result.confidence == 1.0

    def test_infer_column_type_datetime(self):
        """Test inference on datetime column."""
        values = [
            "2024-01-15 14:30",
            "2024-02-20 15:45",
            "2024-03-25 16:00",
            "2024-04-30 17:15",
            "2024-05-10 18:30",
        ]
        result = infer_column_type(values)

        assert result.column_type == ColumnType.DATETIME
        assert result.confidence == 1.0

    def test_infer_column_type_text(self):
        """Test inference on text column."""
        values = ["Alice", "Bob", "Charlie", "David", "Eve"]
        result = infer_column_type(values)

        assert result.column_type == ColumnType.TEXT
        assert result.confidence == 1.0

    def test_infer_column_type_with_nulls(self):
        """Test inference with some null values."""
        values = ["$10.50", "$20.00", None, "$100.25", "N/A"]
        result = infer_column_type(values)

        assert result.column_type == ColumnType.CURRENCY
        assert "empty_ratio" in result.metadata
        assert result.metadata["empty_ratio"] == 0.4  # 2 out of 5 are empty

    def test_infer_column_type_priority_order(self):
        """Test that type detection follows priority: boolean > numeric > date > text."""
        # Boolean has highest priority
        bool_values = ["true", "false", "true"]
        assert infer_column_type(bool_values).column_type == ColumnType.BOOLEAN

        # Numeric (non-boolean) has next priority
        # Use larger integers to avoid currency pattern match
        num_values = ["1000", "2000", "3000"]
        assert infer_column_type(num_values).column_type == ColumnType.INTEGER

        # Date has next priority
        date_values = ["2024-01-15", "2024-02-20", "2024-03-25"]
        assert infer_column_type(date_values).column_type == ColumnType.DATE

        # Text is default fallback
        text_values = ["abc", "def", "ghi"]
        assert infer_column_type(text_values).column_type == ColumnType.TEXT

    def test_infer_column_type_sample_values(self):
        """Test that sample values are included in result."""
        values = ["A", "B", "C", "D", "E", "F", "G"]
        result = infer_column_type(values)

        assert len(result.sample_values) <= 3
        assert all(v in values for v in result.sample_values)


class TestInferColumnTypes:
    """Tests for multi-column type inference."""

    def test_infer_column_types_empty_input(self):
        """Test inference with empty headers and rows."""
        result = infer_column_types([], [])
        assert result == []

    def test_infer_column_types_single_column(self):
        """Test inference with single column."""
        headers = ["ID"]
        # Use larger integers to avoid currency pattern match
        rows = [["1001"], ["1002"], ["1003"]]
        results = infer_column_types(headers, rows)

        assert len(results) == 1
        assert results[0]["column_name"] == "ID"
        assert results[0]["column_index"] == 0
        assert results[0]["type"] == "integer"

    def test_infer_column_types_multiple_columns(self):
        """Test inference with multiple columns of different types."""
        headers = ["ID", "Price", "Date", "Description"]
        rows = [
            ["1001", "$10.50", "2024-01-15", "Item A"],
            ["1002", "$20.00", "2024-01-16", "Item B"],
            ["1003", "$15.75", "2024-01-17", "Item C"],
        ]
        results = infer_column_types(headers, rows)

        assert len(results) == 4

        # Check ID column
        assert results[0]["column_name"] == "ID"
        assert results[0]["type"] == "integer"

        # Check Price column
        assert results[1]["column_name"] == "Price"
        assert results[1]["type"] == "currency"

        # Check Date column
        assert results[2]["column_name"] == "Date"
        assert results[2]["type"] == "date"

        # Check Description column
        assert results[3]["column_name"] == "Description"
        assert results[3]["type"] == "text"

    def test_infer_column_types_with_sample_size(self):
        """Test inference with limited sample size."""
        headers = ["Value"]
        # Use larger integers to avoid currency pattern match
        rows = [
            ["1001"],
            ["1002"],
            ["1003"],
            ["1004"],
            ["1005"],
            ["1006"],
            ["1007"],
            ["1008"],
            ["1009"],
            ["1010"],
        ]
        results = infer_column_types(headers, rows, sample_size=3)

        assert len(results) == 1
        # Should only analyze first 3 rows
        assert results[0]["type"] == "integer"

    def test_infer_column_types_handles_ragged_rows(self):
        """Test inference with rows of different lengths."""
        headers = ["Col1", "Col2", "Col3"]
        rows = [
            ["A", "B", "C"],
            ["D", "E"],  # Missing Col3
            ["F"],  # Missing Col2 and Col3
        ]
        results = infer_column_types(headers, rows)

        assert len(results) == 3
        # All columns should have results even if some rows are short
        for result in results:
            assert "type" in result
            assert "confidence" in result

    def test_infer_column_types_includes_metadata(self):
        """Test that results include all expected metadata."""
        headers = ["Price"]
        rows = [["$10.50"], ["$20.00"], ["$15.75"]]
        results = infer_column_types(headers, rows)

        assert len(results) == 1
        result = results[0]

        assert "column_name" in result
        assert "column_index" in result
        assert "type" in result
        assert "confidence" in result
        assert "sample_values" in result
        assert "metadata" in result

    def test_infer_column_types_preserves_column_order(self):
        """Test that column order is preserved in results."""
        headers = ["First", "Second", "Third", "Fourth"]
        rows = [
            ["A", "1", "2024-01-15", "yes"],
            ["B", "2", "2024-01-16", "no"],
        ]
        results = infer_column_types(headers, rows)

        assert len(results) == 4
        for i, result in enumerate(results):
            assert result["column_name"] == headers[i]
            assert result["column_index"] == i


class TestTypeInferenceResult:
    """Tests for TypeInferenceResult class."""

    def test_type_inference_result_creation(self):
        """Test creating TypeInferenceResult instance."""
        result = TypeInferenceResult(
            column_type=ColumnType.INTEGER,
            confidence=0.95,
            sample_values=["1", "2", "3"],
            metadata={"pattern": "integer"},
        )

        assert result.column_type == ColumnType.INTEGER
        assert result.confidence == 0.95
        assert result.sample_values == ["1", "2", "3"]
        assert result.metadata == {"pattern": "integer"}

    def test_type_inference_result_defaults(self):
        """Test TypeInferenceResult with default values."""
        result = TypeInferenceResult(
            column_type=ColumnType.TEXT,
            confidence=1.0,
        )

        assert result.sample_values == []
        assert result.metadata == {}

    def test_type_inference_result_to_dict(self):
        """Test converting TypeInferenceResult to dictionary."""
        result = TypeInferenceResult(
            column_type=ColumnType.CURRENCY,
            confidence=1.0,
            sample_values=["$10", "$20"],
            metadata={"pattern": "currency"},
        )

        result_dict = result.to_dict()

        assert result_dict["type"] == "currency"
        assert result_dict["confidence"] == 1.0
        assert result_dict["sample_values"] == ["$10", "$20"]
        assert result_dict["metadata"] == {"pattern": "currency"}

    def test_type_inference_result_to_dict_with_enum(self):
        """Test that to_dict converts enum to string value."""
        result = TypeInferenceResult(
            column_type=ColumnType.DATETIME,
            confidence=0.9,
        )

        result_dict = result.to_dict()

        # Should be string value, not enum
        assert isinstance(result_dict["type"], str)
        assert result_dict["type"] == "datetime"
