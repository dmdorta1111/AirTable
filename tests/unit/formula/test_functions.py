"""Unit tests for formula functions."""

from datetime import date, datetime
import pytest
from pybase.formula.functions import (
    # Text
    func_concat,
    func_left,
    func_right,
    func_mid,
    func_len,
    func_trim,
    func_lower,
    func_upper,
    func_proper,
    # Numeric
    func_sum,
    func_avg,
    func_min,
    func_max,
    func_count,
    func_round,
    func_abs,
    func_sqrt,
    func_power,
    func_log,
    func_ln,
    # Logical
    func_if,
    func_and,
    func_or,
    func_not,
    func_isblank,
    # Date
    func_today,
    func_now,
    func_year,
    func_month,
    func_day,
    func_dateadd,
    func_datediff,
    # Array
    func_arraycompact,
    func_arrayflatten,
    func_arrayunique,
    func_arrayjoin,
)


class TestTextFunctions:
    """Tests for text functions."""

    def test_concat(self):
        """Test CONCAT function."""
        result = func_concat("hello", " ", "world")
        assert result == "hello world"

    def test_concat_with_none(self):
        """Test CONCAT with None values."""
        result = func_concat("hello", None, "world")
        assert result == "helloworld"

    def test_left(self):
        """Test LEFT function."""
        result = func_left("hello world", 5)
        assert result == "hello"

    def test_right(self):
        """Test RIGHT function."""
        result = func_right("hello world", 5)
        assert result == "world"

    def test_mid(self):
        """Test MID function."""
        result = func_mid("hello world", 7, 5)
        assert result == "world"

    def test_len(self):
        """Test LEN function."""
        result = func_len("hello")
        assert result == 5

    def test_len_with_none(self):
        """Test LEN with None."""
        result = func_len(None)
        assert result == 0

    def test_trim(self):
        """Test TRIM function."""
        result = func_trim("  hello  ")
        assert result == "hello"

    def test_upper(self):
        """Test UPPER function."""
        result = func_upper("hello")
        assert result == "HELLO"

    def test_lower(self):
        """Test LOWER function."""
        result = func_lower("HELLO")
        assert result == "hello"

    def test_proper(self):
        """Test PROPER function."""
        result = func_proper("hello world")
        assert result == "Hello World"


class TestNumericFunctions:
    """Tests for numeric functions."""

    def test_sum(self):
        """Test SUM function."""
        result = func_sum(1, 2, 3, 4, 5)
        assert result == 15

    def test_sum_with_list(self):
        """Test SUM with list."""
        result = func_sum([1, 2, 3])
        assert result == 9

    def test_sum_with_none(self):
        """Test SUM ignores None."""
        result = func_sum(1, None, 3)
        assert result == 4

    def test_avg(self):
        """Test AVG function."""
        result = func_avg(2, 4, 6, 8)
        assert result == 5.0

    def test_avg_with_none(self):
        """Test AVG ignores None."""
        result = func_avg(2, None, 6)
        assert result == 4.0

    def test_avg_empty(self):
        """Test AVG with no values."""
        result = func_avg()
        assert result is None

    def test_min(self):
        """Test MIN function."""
        result = func_min(5, 3, 9, 1)
        assert result == 1

    def test_max(self):
        """Test MAX function."""
        result = func_max(5, 3, 9, 1)
        assert result == 9

    def test_count(self):
        """Test COUNT function."""
        result = func_count(1, "text", 3, None)
        assert result == 3

    def test_counta(self):
        """Test COUNTA function."""
        result = func_counta(1, "text", 3, None)
        assert result == 3

    def test_countblank(self):
        """Test COUNTBLANK function."""
        result = func_countblank(1, None, "text", "")
        assert result == 2

    def test_round(self):
        """Test ROUND function."""
        result = func_round(3.14159, 2)
        assert result == 3.14

    def test_round_no_decimals(self):
        """Test ROUND with no decimals."""
        result = func_round(3.7)
        assert result == 4

    def test_abs(self):
        """Test ABS function."""
        result = func_abs(-5)
        assert result == 5

    def test_sqrt(self):
        """Test SQRT function."""
        result = func_sqrt(16)
        assert result == 4.0

    def test_sqrt_negative(self):
        """Test SQRT with negative."""
        result = func_sqrt(-4)
        assert result is None

    def test_power(self):
        """Test POWER function."""
        result = func_power(2, 3)
        assert result == 8

    def test_log(self):
        """Test LOG function."""
        result = func_log(100, 10)
        assert result == 2.0

    def test_ln(self):
        """Test LN function."""
        import math

        result = func_ln(math.e)
        assert abs(result - 1.0) < 0.01

    def test_log_negative(self):
        """Test LOG with negative."""
        result = func_log(-10)
        assert result is None


class TestLogicalFunctions:
    """Tests for logical functions."""

    def test_if_true(self):
        """Test IF with true condition."""
        result = func_if(True, "yes", "no")
        assert result == "yes"

    def test_if_false(self):
        """Test IF with false condition."""
        result = func_if(False, "yes", "no")
        assert result == "no"

    def test_and_all_true(self):
        """Test AND with all true."""
        result = func_and(True, True, True)
        assert result is True

    def test_and_some_false(self):
        """Test AND with some false."""
        result = func_and(True, False, True)
        assert result is False

    def test_or_all_false(self):
        """Test OR with all false."""
        result = func_or(False, False, False)
        assert result is False

    def test_or_some_true(self):
        """Test OR with some true."""
        result = func_or(False, True, False)
        assert result is True

    def test_not_true(self):
        """Test NOT with true."""
        result = func_not(True)
        assert result is False

    def test_not_false(self):
        """Test NOT with false."""
        result = func_not(False)
        assert result is True

    def test_isblank_true(self):
        """Test ISBLANK with None."""
        result = func_isblank(None)
        assert result is True

    def test_isblank_false(self):
        """Test ISBLANK with value."""
        result = func_isblank("test")
        assert result is False


class TestDateFunctions:
    """Tests for date functions."""

    def test_today(self):
        """Test TODAY function."""
        result = func_today()
        assert isinstance(result, date)

    def test_now(self):
        """Test NOW function."""
        result = func_now()
        assert isinstance(result, datetime)

    def test_year(self):
        """Test YEAR function."""
        result = func_year(date(2024, 1, 15))
        assert result == 2024

    def test_month(self):
        """Test MONTH function."""
        result = func_month(date(2024, 1, 15))
        assert result == 1

    def test_day(self):
        """Test DAY function."""
        result = func_day(date(2024, 1, 15))
        assert result == 15

    def test_dateadd_days(self):
        """Test DATEADD with days."""
        result = func_dateadd(date(2024, 1, 15), 7, "days")
        expected = date(2024, 1, 22)
        assert result == expected

    def test_dateadd_months(self):
        """Test DATEADD with months."""
        result = func_dateadd(date(2024, 1, 15), 2, "months")
        expected = date(2024, 3, 15)
        assert result == expected

    def test_dateadd_years(self):
        """Test DATEADD with years."""
        result = func_dateadd(date(2024, 1, 15), 1, "years")
        expected = date(2025, 1, 15)
        assert result == expected

    def test_datediff_days(self):
        """Test DATEDIFF with days."""
        d1 = date(2024, 1, 15)
        d2 = date(2024, 1, 22)
        result = func_datediff(d1, d2, "days")
        assert result == 7

    def test_datediff_months(self):
        """Test DATEDIFF with months."""
        d1 = date(2024, 1, 15)
        d2 = date(2024, 3, 15)
        result = func_datediff(d1, d2, "months")
        assert result == 2

    def test_datediff_years(self):
        """Test DATEDIFF with years."""
        d1 = date(2023, 1, 15)
        d2 = date(2024, 1, 15)
        result = func_datediff(d1, d2, "years")
        assert result == 1


class TestArrayFunctions:
    """Tests for array functions."""

    def test_arraycompact(self):
        """Test ARRAYCOMPACT function."""
        result = func_arraycompact([1, None, 2, "", 3])
        assert result == [1, 2, 3]

    def test_arrayflatten(self):
        """Test ARRAYFLATTEN function."""
        result = func_arrayflatten([1, [2, 3], [[4]]])
        assert result == [1, 2, 3, 4]

    def test_arrayunique(self):
        """Test ARRAYUNIQUE function."""
        result = func_arrayunique([1, 2, 1, 3, 2])
        assert set(result) == {1, 2, 3}

    def test_arrayjoin(self):
        """Test ARRAYJOIN function."""
        result = func_arrayjoin([1, 2, 3], ", ")
        assert result == "1, 2, 3"

    def test_arrayjoin_with_none(self):
        """Test ARRAYJOIN with None values."""
        result = func_arrayjoin([1, None, 3], ", ")
        assert result == "1, 3"
