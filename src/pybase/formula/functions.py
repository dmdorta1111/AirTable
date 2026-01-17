"""Formula functions for PyBase.

Implements all built-in functions available in formulas.
"""

from typing import Any, Callable
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
import math
import re


# Type alias for formula functions
FormulaFunction = Callable[..., Any]

# Registry of formula functions
FORMULA_FUNCTIONS: dict[str, FormulaFunction] = {}


def register_function(name: str) -> Callable[[FormulaFunction], FormulaFunction]:
    """Decorator to register a formula function."""

    def decorator(func: FormulaFunction) -> FormulaFunction:
        FORMULA_FUNCTIONS[name.upper()] = func
        return func

    return decorator


# =============================================================================
# Text Functions
# =============================================================================


@register_function("CONCAT")
@register_function("CONCATENATE")
def func_concat(*args: Any) -> str:
    """Concatenate values into a string."""
    return "".join(str(a) if a is not None else "" for a in args)


@register_function("LEFT")
def func_left(text: Any, count: int = 1) -> str:
    """Return leftmost characters."""
    if text is None:
        return ""
    return str(text)[: int(count)]


@register_function("RIGHT")
def func_right(text: Any, count: int = 1) -> str:
    """Return rightmost characters."""
    if text is None:
        return ""
    return str(text)[-int(count) :] if count > 0 else ""


@register_function("MID")
def func_mid(text: Any, start: int, count: int) -> str:
    """Return substring from middle."""
    if text is None:
        return ""
    # 1-indexed like Excel/Airtable
    start = max(1, int(start))
    return str(text)[start - 1 : start - 1 + int(count)]


@register_function("LEN")
def func_len(text: Any) -> int:
    """Return length of text."""
    if text is None:
        return 0
    return len(str(text))


@register_function("TRIM")
def func_trim(text: Any) -> str:
    """Remove leading/trailing whitespace."""
    if text is None:
        return ""
    return str(text).strip()


@register_function("LOWER")
def func_lower(text: Any) -> str:
    """Convert to lowercase."""
    if text is None:
        return ""
    return str(text).lower()


@register_function("UPPER")
def func_upper(text: Any) -> str:
    """Convert to uppercase."""
    if text is None:
        return ""
    return str(text).upper()


@register_function("PROPER")
def func_proper(text: Any) -> str:
    """Convert to title case."""
    if text is None:
        return ""
    return str(text).title()


@register_function("SUBSTITUTE")
def func_substitute(text: Any, old: str, new: str, count: int | None = None) -> str:
    """Replace occurrences of old with new."""
    if text is None:
        return ""
    if count is None:
        return str(text).replace(str(old), str(new))
    return str(text).replace(str(old), str(new), int(count))


@register_function("REPLACE")
def func_replace(text: Any, start: int, count: int, replacement: str) -> str:
    """Replace characters at position."""
    if text is None:
        return str(replacement)
    s = str(text)
    start = max(1, int(start))
    return s[: start - 1] + str(replacement) + s[start - 1 + int(count) :]


@register_function("REPT")
def func_rept(text: Any, count: int) -> str:
    """Repeat text N times."""
    if text is None:
        return ""
    return str(text) * max(0, int(count))


@register_function("T")
def func_t(value: Any) -> str:
    """Convert to text (returns empty string for non-text)."""
    if isinstance(value, str):
        return value
    return ""


@register_function("VALUE")
def func_value(text: Any) -> float | None:
    """Convert text to number."""
    if text is None:
        return None
    try:
        return float(str(text).replace(",", ""))
    except ValueError:
        return None


@register_function("FIND")
def func_find(search: str, text: Any, start: int = 1) -> int:
    """Find position of search string (case-sensitive, 1-indexed)."""
    if text is None:
        return 0
    try:
        # 1-indexed, returns 0 if not found
        pos = str(text).index(str(search), int(start) - 1)
        return pos + 1
    except ValueError:
        return 0


@register_function("SEARCH")
def func_search(search: str, text: Any, start: int = 1) -> int:
    """Find position of search string (case-insensitive, 1-indexed)."""
    if text is None:
        return 0
    try:
        pos = str(text).lower().index(str(search).lower(), int(start) - 1)
        return pos + 1
    except ValueError:
        return 0


@register_function("REGEX_MATCH")
def func_regex_match(text: Any, pattern: str) -> bool:
    """Check if text matches regex pattern."""
    if text is None:
        return False
    try:
        return bool(re.search(pattern, str(text)))
    except re.error:
        return False


@register_function("REGEX_EXTRACT")
def func_regex_extract(text: Any, pattern: str) -> str | None:
    """Extract first regex match."""
    if text is None:
        return None
    try:
        match = re.search(pattern, str(text))
        return match.group(0) if match else None
    except re.error:
        return None


@register_function("REGEX_REPLACE")
def func_regex_replace(text: Any, pattern: str, replacement: str) -> str:
    """Replace regex matches."""
    if text is None:
        return ""
    try:
        return re.sub(pattern, replacement, str(text))
    except re.error:
        return str(text)


# =============================================================================
# Numeric Functions
# =============================================================================


@register_function("SUM")
def func_sum(*args: Any) -> float | int:
    """Sum of numeric values."""
    total = 0
    for arg in args:
        if isinstance(arg, (list, tuple)):
            total += func_sum(*arg)
        elif arg is not None:
            try:
                total += float(arg)
            except (ValueError, TypeError):
                pass
    return total if isinstance(total, int) else float(total)


@register_function("AVG")
@register_function("AVERAGE")
def func_avg(*args: Any) -> float | None:
    """Average of numeric values."""
    values = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            values.extend(arg)
        elif arg is not None:
            try:
                values.append(float(arg))
            except (ValueError, TypeError):
                pass
    if not values:
        return None
    return sum(values) / len(values)


@register_function("MIN")
def func_min(*args: Any) -> Any:
    """Minimum value."""
    values = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            values.extend(a for a in arg if a is not None)
        elif arg is not None:
            values.append(arg)
    if not values:
        return None
    try:
        return min(values)
    except TypeError:
        # Mixed types, try numeric
        numeric = []
        for v in values:
            try:
                numeric.append(float(v))
            except (ValueError, TypeError):
                pass
        return min(numeric) if numeric else None


@register_function("MAX")
def func_max(*args: Any) -> Any:
    """Maximum value."""
    values = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            values.extend(a for a in arg if a is not None)
        elif arg is not None:
            values.append(arg)
    if not values:
        return None
    try:
        return max(values)
    except TypeError:
        numeric = []
        for v in values:
            try:
                numeric.append(float(v))
            except (ValueError, TypeError):
                pass
        return max(numeric) if numeric else None


@register_function("COUNT")
def func_count(*args: Any) -> int:
    """Count of numeric values."""
    count = 0
    for arg in args:
        if isinstance(arg, (list, tuple)):
            count += func_count(*arg)
        elif arg is not None:
            try:
                float(arg)
                count += 1
            except (ValueError, TypeError):
                pass
    return count


@register_function("COUNTA")
def func_counta(*args: Any) -> int:
    """Count of non-empty values."""
    count = 0
    for arg in args:
        if isinstance(arg, (list, tuple)):
            count += func_counta(*arg)
        elif arg is not None and arg != "":
            count += 1
    return count


@register_function("COUNTBLANK")
def func_countblank(*args: Any) -> int:
    """Count of empty/blank values."""
    count = 0
    for arg in args:
        if isinstance(arg, (list, tuple)):
            count += func_countblank(*arg)
        elif arg is None or arg == "":
            count += 1
    return count


@register_function("ROUND")
def func_round(value: Any, decimals: int = 0) -> float | None:
    """Round to specified decimals."""
    if value is None:
        return None
    try:
        return round(float(value), int(decimals))
    except (ValueError, TypeError):
        return None


@register_function("ROUNDUP")
def func_roundup(value: Any, decimals: int = 0) -> float | None:
    """Round up (away from zero)."""
    if value is None:
        return None
    try:
        v = float(value)
        multiplier = 10 ** int(decimals)
        if v >= 0:
            return math.ceil(v * multiplier) / multiplier
        else:
            return math.floor(v * multiplier) / multiplier
    except (ValueError, TypeError):
        return None


@register_function("ROUNDDOWN")
def func_rounddown(value: Any, decimals: int = 0) -> float | None:
    """Round down (toward zero)."""
    if value is None:
        return None
    try:
        v = float(value)
        multiplier = 10 ** int(decimals)
        if v >= 0:
            return math.floor(v * multiplier) / multiplier
        else:
            return math.ceil(v * multiplier) / multiplier
    except (ValueError, TypeError):
        return None


@register_function("CEILING")
def func_ceiling(value: Any, significance: float = 1) -> float | None:
    """Round up to nearest significance."""
    if value is None:
        return None
    try:
        v = float(value)
        s = float(significance)
        if s == 0:
            return 0
        return math.ceil(v / s) * s
    except (ValueError, TypeError):
        return None


@register_function("FLOOR")
def func_floor(value: Any, significance: float = 1) -> float | None:
    """Round down to nearest significance."""
    if value is None:
        return None
    try:
        v = float(value)
        s = float(significance)
        if s == 0:
            return 0
        return math.floor(v / s) * s
    except (ValueError, TypeError):
        return None


@register_function("ABS")
def func_abs(value: Any) -> float | None:
    """Absolute value."""
    if value is None:
        return None
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return None


@register_function("SQRT")
def func_sqrt(value: Any) -> float | None:
    """Square root."""
    if value is None:
        return None
    try:
        v = float(value)
        if v < 0:
            return None
        return math.sqrt(v)
    except (ValueError, TypeError):
        return None


@register_function("POWER")
def func_power(base: Any, exponent: Any) -> float | None:
    """Raise to power."""
    if base is None or exponent is None:
        return None
    try:
        return math.pow(float(base), float(exponent))
    except (ValueError, TypeError):
        return None


@register_function("EXP")
def func_exp(value: Any) -> float | None:
    """e raised to power."""
    if value is None:
        return None
    try:
        return math.exp(float(value))
    except (ValueError, TypeError):
        return None


@register_function("LOG")
def func_log(value: Any, base: float = 10) -> float | None:
    """Logarithm."""
    if value is None:
        return None
    try:
        v = float(value)
        b = float(base)
        if v <= 0 or b <= 0 or b == 1:
            return None
        return math.log(v, b)
    except (ValueError, TypeError):
        return None


@register_function("LN")
def func_ln(value: Any) -> float | None:
    """Natural logarithm."""
    if value is None:
        return None
    try:
        v = float(value)
        if v <= 0:
            return None
        return math.log(v)
    except (ValueError, TypeError):
        return None


@register_function("MOD")
def func_mod(value: Any, divisor: Any) -> float | None:
    """Modulo (remainder)."""
    if value is None or divisor is None:
        return None
    try:
        d = float(divisor)
        if d == 0:
            return None
        return float(value) % d
    except (ValueError, TypeError):
        return None


@register_function("INT")
def func_int(value: Any) -> int | None:
    """Truncate to integer."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


@register_function("EVEN")
def func_even(value: Any) -> int | None:
    """Round up to next even integer."""
    if value is None:
        return None
    try:
        v = float(value)
        result = math.ceil(v)
        if result % 2 != 0:
            result += 1 if v >= 0 else -1
        return result
    except (ValueError, TypeError):
        return None


@register_function("ODD")
def func_odd(value: Any) -> int | None:
    """Round up to next odd integer."""
    if value is None:
        return None
    try:
        v = float(value)
        result = math.ceil(v)
        if result % 2 == 0:
            result += 1 if v >= 0 else -1
        return result
    except (ValueError, TypeError):
        return None


# =============================================================================
# Logical Functions
# =============================================================================


@register_function("IF")
def func_if(condition: Any, if_true: Any, if_false: Any = None) -> Any:
    """Conditional: IF(condition, value_if_true, value_if_false)."""
    return if_true if condition else if_false


@register_function("IFS")
def func_ifs(*args: Any) -> Any:
    """Multiple conditions: IFS(cond1, val1, cond2, val2, ...)."""
    for i in range(0, len(args) - 1, 2):
        if args[i]:
            return args[i + 1]
    return None


@register_function("SWITCH")
def func_switch(expression: Any, *args: Any) -> Any:
    """Switch: SWITCH(expr, case1, val1, case2, val2, ..., [default])."""
    # args come in pairs, last one may be default
    i = 0
    while i < len(args) - 1:
        if expression == args[i]:
            return args[i + 1]
        i += 2
    # Return default if odd number of remaining args
    if len(args) % 2 == 1:
        return args[-1]
    return None


@register_function("AND")
def func_and(*args: Any) -> bool:
    """Logical AND."""
    for arg in args:
        if isinstance(arg, (list, tuple)):
            if not func_and(*arg):
                return False
        elif not arg:
            return False
    return True


@register_function("OR")
def func_or(*args: Any) -> bool:
    """Logical OR."""
    for arg in args:
        if isinstance(arg, (list, tuple)):
            if func_or(*arg):
                return True
        elif arg:
            return True
    return False


@register_function("NOT")
def func_not(value: Any) -> bool:
    """Logical NOT."""
    return not value


@register_function("XOR")
def func_xor(*args: Any) -> bool:
    """Logical XOR (odd number of true values)."""
    true_count = 0
    for arg in args:
        if isinstance(arg, (list, tuple)):
            for a in arg:
                if a:
                    true_count += 1
        elif arg:
            true_count += 1
    return true_count % 2 == 1


@register_function("BLANK")
def func_blank() -> None:
    """Return blank/null value."""
    return None


@register_function("ERROR")
def func_error(message: str = "Error") -> None:
    """Raise an error (returns None in safe mode)."""
    # In safe evaluation mode, we don't raise exceptions
    return None


@register_function("ISERROR")
def func_iserror(value: Any) -> bool:
    """Check if value is an error."""
    # In our implementation, errors are represented as None
    return value is None


@register_function("ISBLANK")
def func_isblank(value: Any) -> bool:
    """Check if value is blank."""
    return value is None or value == ""


@register_function("ISNUMBER")
def func_isnumber(value: Any) -> bool:
    """Check if value is a number."""
    if value is None:
        return False
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float, Decimal)):
        return True
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


@register_function("ISTEXT")
def func_istext(value: Any) -> bool:
    """Check if value is text."""
    return isinstance(value, str)


# =============================================================================
# Date Functions
# =============================================================================


@register_function("TODAY")
def func_today() -> date:
    """Current date."""
    return date.today()


@register_function("NOW")
def func_now() -> datetime:
    """Current date and time."""
    return datetime.now()


@register_function("YEAR")
def func_year(d: Any) -> int | None:
    """Extract year from date."""
    d = _parse_date(d)
    return d.year if d else None


@register_function("MONTH")
def func_month(d: Any) -> int | None:
    """Extract month from date."""
    d = _parse_date(d)
    return d.month if d else None


@register_function("DAY")
def func_day(d: Any) -> int | None:
    """Extract day from date."""
    d = _parse_date(d)
    return d.day if d else None


@register_function("HOUR")
def func_hour(d: Any) -> int | None:
    """Extract hour from datetime."""
    d = _parse_datetime(d)
    return d.hour if d else None


@register_function("MINUTE")
def func_minute(d: Any) -> int | None:
    """Extract minute from datetime."""
    d = _parse_datetime(d)
    return d.minute if d else None


@register_function("SECOND")
def func_second(d: Any) -> int | None:
    """Extract second from datetime."""
    d = _parse_datetime(d)
    return d.second if d else None


@register_function("WEEKDAY")
def func_weekday(d: Any, start_day: int = 1) -> int | None:
    """Day of week (1=Sunday by default)."""
    d = _parse_date(d)
    if not d:
        return None
    # Python: Monday=0, we want Sunday=1 by default
    dow = d.weekday()  # Monday=0
    if start_day == 1:  # Sunday=1
        return (dow + 2) % 7 or 7
    elif start_day == 2:  # Monday=1
        return dow + 1
    else:
        return dow + 1


@register_function("WEEKNUM")
def func_weeknum(d: Any) -> int | None:
    """Week number of year."""
    d = _parse_date(d)
    return d.isocalendar()[1] if d else None


@register_function("DATEADD")
def func_dateadd(d: Any, count: int, unit: str) -> date | datetime | None:
    """Add time to date: DATEADD(date, count, 'days'|'months'|'years')."""
    d = _parse_date(d)
    if not d:
        return None

    unit = str(unit).lower()
    count = int(count)

    if unit in ("day", "days", "d"):
        return d + timedelta(days=count)
    elif unit in ("week", "weeks", "w"):
        return d + timedelta(weeks=count)
    elif unit in ("month", "months", "m"):
        # Handle month addition
        new_month = d.month + count
        new_year = d.year + (new_month - 1) // 12
        new_month = (new_month - 1) % 12 + 1
        # Handle day overflow (e.g., Jan 31 + 1 month)
        import calendar

        max_day = calendar.monthrange(new_year, new_month)[1]
        new_day = min(d.day, max_day)
        if isinstance(d, datetime):
            return d.replace(year=new_year, month=new_month, day=new_day)
        return date(new_year, new_month, new_day)
    elif unit in ("year", "years", "y"):
        try:
            if isinstance(d, datetime):
                return d.replace(year=d.year + count)
            return date(d.year + count, d.month, d.day)
        except ValueError:
            # Feb 29 on non-leap year
            if isinstance(d, datetime):
                return d.replace(year=d.year + count, day=28)
            return date(d.year + count, d.month, 28)
    elif unit in ("hour", "hours", "h"):
        dt = _parse_datetime(d) or datetime.combine(d, datetime.min.time())
        return dt + timedelta(hours=count)
    elif unit in ("minute", "minutes", "min"):
        dt = _parse_datetime(d) or datetime.combine(d, datetime.min.time())
        return dt + timedelta(minutes=count)
    elif unit in ("second", "seconds", "s", "sec"):
        dt = _parse_datetime(d) or datetime.combine(d, datetime.min.time())
        return dt + timedelta(seconds=count)

    return None


@register_function("DATEDIFF")
@register_function("DATETIME_DIFF")
def func_datediff(d1: Any, d2: Any, unit: str = "days") -> int | None:
    """Difference between dates."""
    d1 = _parse_date(d1)
    d2 = _parse_date(d2)
    if not d1 or not d2:
        return None

    unit = str(unit).lower()

    if unit in ("day", "days", "d"):
        return (d2 - d1).days
    elif unit in ("week", "weeks", "w"):
        return (d2 - d1).days // 7
    elif unit in ("month", "months", "m"):
        return (d2.year - d1.year) * 12 + (d2.month - d1.month)
    elif unit in ("year", "years", "y"):
        return d2.year - d1.year
    elif unit in ("hour", "hours", "h"):
        dt1 = _parse_datetime(d1) or datetime.combine(d1, datetime.min.time())
        dt2 = _parse_datetime(d2) or datetime.combine(d2, datetime.min.time())
        return int((dt2 - dt1).total_seconds() // 3600)
    elif unit in ("minute", "minutes", "min"):
        dt1 = _parse_datetime(d1) or datetime.combine(d1, datetime.min.time())
        dt2 = _parse_datetime(d2) or datetime.combine(d2, datetime.min.time())
        return int((dt2 - dt1).total_seconds() // 60)
    elif unit in ("second", "seconds", "s", "sec"):
        dt1 = _parse_datetime(d1) or datetime.combine(d1, datetime.min.time())
        dt2 = _parse_datetime(d2) or datetime.combine(d2, datetime.min.time())
        return int((dt2 - dt1).total_seconds())

    return None


@register_function("DATETIME_FORMAT")
def func_datetime_format(d: Any, fmt: str = "%Y-%m-%d") -> str | None:
    """Format date/datetime as string."""
    d = _parse_datetime(d) or _parse_date(d)
    if not d:
        return None
    try:
        return d.strftime(fmt)
    except ValueError:
        return None


@register_function("DATETIME_PARSE")
def func_datetime_parse(text: Any, fmt: str = "%Y-%m-%d") -> datetime | None:
    """Parse string to datetime."""
    if text is None:
        return None
    try:
        return datetime.strptime(str(text), fmt)
    except ValueError:
        return None


@register_function("WORKDAY")
def func_workday(d: Any, days: int) -> date | None:
    """Add working days (excluding weekends)."""
    d = _parse_date(d)
    if not d:
        return None

    direction = 1 if days >= 0 else -1
    remaining = abs(int(days))
    current = d

    while remaining > 0:
        current += timedelta(days=direction)
        if current.weekday() < 5:  # Monday=0 to Friday=4
            remaining -= 1

    return current


@register_function("EOMONTH")
def func_eomonth(d: Any, months: int = 0) -> date | None:
    """End of month, optionally offset by months."""
    d = _parse_date(d)
    if not d:
        return None

    import calendar

    # Move to target month
    new_month = d.month + int(months)
    new_year = d.year + (new_month - 1) // 12
    new_month = (new_month - 1) % 12 + 1

    # Get last day of that month
    last_day = calendar.monthrange(new_year, new_month)[1]
    return date(new_year, new_month, last_day)


# =============================================================================
# Array Functions
# =============================================================================


@register_function("ARRAYCOMPACT")
def func_arraycompact(*args: Any) -> list[Any]:
    """Remove empty values from array."""
    result = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            result.extend(a for a in arg if a is not None and a != "")
        elif arg is not None and arg != "":
            result.append(arg)
    return result


@register_function("ARRAYFLATTEN")
def func_arrayflatten(*args: Any) -> list[Any]:
    """Flatten nested arrays."""
    result = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            result.extend(func_arrayflatten(*arg))
        else:
            result.append(arg)
    return result


@register_function("ARRAYUNIQUE")
def func_arrayunique(*args: Any) -> list[Any]:
    """Remove duplicate values."""
    seen = set()
    result = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            for a in arg:
                if a not in seen:
                    seen.add(a)
                    result.append(a)
        elif arg not in seen:
            seen.add(arg)
            result.append(arg)
    return result


@register_function("ARRAYJOIN")
def func_arrayjoin(array: Any, separator: str = ", ") -> str:
    """Join array elements with separator."""
    if not isinstance(array, (list, tuple)):
        return str(array) if array is not None else ""
    return str(separator).join(str(a) for a in array if a is not None)


# =============================================================================
# Helper Functions (not exposed to formulas)
# =============================================================================


def _parse_date(value: Any) -> date | None:
    """Parse various date representations."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        # Try common formats
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        # Try ISO format with time
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            pass
    return None


def _parse_datetime(value: Any) -> datetime | None:
    """Parse various datetime representations."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        # Try ISO format
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
        # Try common formats
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None
