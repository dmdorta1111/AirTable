"""Dimension field type handler for PyBase.

Handles engineering dimensions with values, tolerances, and units.
"""

from typing import Any
import re
from decimal import Decimal, InvalidOperation

from pybase.fields.base import BaseFieldTypeHandler


class DimensionFieldHandler(BaseFieldTypeHandler):
    """
    Handler for dimension fields.

    Dimension fields store engineering measurements with:
    - Nominal value
    - Tolerance (symmetric or asymmetric)
    - Unit of measurement

    Options:
        unit: Default unit (mm, in, m, cm, etc.)
        precision: Decimal places (default: 3)
        tolerance_type: 'symmetric', 'asymmetric', 'limits' (default: symmetric)

    Storage format:
        {
            "value": 10.5,
            "tolerance_plus": 0.1,
            "tolerance_minus": 0.1,
            "unit": "mm"
        }

    Display format examples:
        - "10.5 ±0.1 mm" (symmetric)
        - "10.5 +0.2/-0.1 mm" (asymmetric)
        - "10.4 - 10.6 mm" (limits)
    """

    field_type = "dimension"

    # Common units
    UNITS = {
        "mm": "millimeter",
        "cm": "centimeter",
        "m": "meter",
        "in": "inch",
        "ft": "foot",
        "μm": "micrometer",
        "mil": "thousandth inch",
    }

    # Conversion factors to mm
    TO_MM = {
        "mm": 1.0,
        "cm": 10.0,
        "m": 1000.0,
        "in": 25.4,
        "ft": 304.8,
        "μm": 0.001,
        "mil": 0.0254,
    }

    @classmethod
    def serialize(cls, value: Any) -> dict[str, Any] | None:
        """
        Serialize dimension to storage format.

        Args:
            value: Dimension value (dict, string, or number)

        Returns:
            Standardized dimension dict or None
        """
        if value is None:
            return None

        if isinstance(value, dict):
            return {
                "value": value.get("value"),
                "tolerance_plus": value.get("tolerance_plus", value.get("tolerance", 0)),
                "tolerance_minus": value.get("tolerance_minus", value.get("tolerance", 0)),
                "unit": value.get("unit", "mm"),
            }

        if isinstance(value, (int, float, Decimal)):
            return {
                "value": float(value),
                "tolerance_plus": 0,
                "tolerance_minus": 0,
                "unit": "mm",
            }

        if isinstance(value, str):
            return cls._parse_dimension_string(value)

        return None

    @classmethod
    def deserialize(cls, value: Any) -> dict[str, Any] | None:
        """
        Deserialize dimension from storage.

        Args:
            value: Stored dimension data

        Returns:
            Dimension dict or None
        """
        if value is None:
            return None

        if isinstance(value, dict):
            return value

        return cls.serialize(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate dimension value.

        Args:
            value: Value to validate
            options: Field options with:
                - min_value: minimum allowed value
                - max_value: maximum allowed value
                - precision: decimal places to enforce

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        parsed = cls.serialize(value)
        if parsed is None:
            raise ValueError("Invalid dimension format")

        # Validate value is numeric
        if parsed["value"] is None:
            raise ValueError("Dimension must have a numeric value")

        dim_value = float(parsed["value"])

        # Validate tolerances are non-negative
        if parsed["tolerance_plus"] < 0 or parsed["tolerance_minus"] < 0:
            raise ValueError("Tolerances must be non-negative")

        # Validate unit
        unit = parsed.get("unit", "mm")
        if unit not in cls.UNITS:
            raise ValueError(f"Invalid unit '{unit}'. Supported: {', '.join(cls.UNITS.keys())}")

        # Apply range and precision validation if options provided
        if options:
            # Check minimum value
            min_value = options.get("min_value")
            if min_value is not None and dim_value < min_value:
                raise ValueError(f"Dimension value must be >= {min_value}")

            # Check maximum value
            max_value = options.get("max_value")
            if max_value is not None and dim_value > max_value:
                raise ValueError(f"Dimension value must be <= {max_value}")

            # Check precision
            precision = options.get("precision")
            if precision is not None and not isinstance(dim_value, int):
                rounded = round(dim_value, precision)
                if abs(dim_value - rounded) > 10 ** (-(precision + 1)):
                    raise ValueError(
                        f"Dimension value exceeds precision of {precision} decimal places"
                    )

        return True

    @classmethod
    def default(cls) -> dict[str, Any] | None:
        """Get default value."""
        return None

    @classmethod
    def _parse_dimension_string(cls, text: str) -> dict[str, Any] | None:
        """
        Parse dimension from string like "10.5 ±0.1 mm" or "10.5 +0.2/-0.1 mm".
        """
        text = text.strip()

        # Pattern: value ±tolerance unit
        symmetric_pattern = r"^([\d.]+)\s*[±]\s*([\d.]+)\s*(\w+)?$"
        match = re.match(symmetric_pattern, text)
        if match:
            return {
                "value": float(match.group(1)),
                "tolerance_plus": float(match.group(2)),
                "tolerance_minus": float(match.group(2)),
                "unit": match.group(3) or "mm",
            }

        # Pattern: value +plus/-minus unit
        asymmetric_pattern = r"^([\d.]+)\s*\+([\d.]+)\s*/\s*-\s*([\d.]+)\s*(\w+)?$"
        match = re.match(asymmetric_pattern, text)
        if match:
            return {
                "value": float(match.group(1)),
                "tolerance_plus": float(match.group(2)),
                "tolerance_minus": float(match.group(3)),
                "unit": match.group(4) or "mm",
            }

        # Pattern: min - max unit (limits)
        limits_pattern = r"^([\d.]+)\s*-\s*([\d.]+)\s*(\w+)?$"
        match = re.match(limits_pattern, text)
        if match:
            min_val = float(match.group(1))
            max_val = float(match.group(2))
            nominal = (min_val + max_val) / 2
            tolerance = (max_val - min_val) / 2
            return {
                "value": nominal,
                "tolerance_plus": tolerance,
                "tolerance_minus": tolerance,
                "unit": match.group(3) or "mm",
            }

        # Pattern: just a number with optional unit
        simple_pattern = r"^([\d.]+)\s*(\w+)?$"
        match = re.match(simple_pattern, text)
        if match:
            return {
                "value": float(match.group(1)),
                "tolerance_plus": 0,
                "tolerance_minus": 0,
                "unit": match.group(2) or "mm",
            }

        return None

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format dimension for display.

        Args:
            value: Dimension data
            options: Field options including:
                - precision: Decimal places
                - tolerance_type: Display format

        Returns:
            Formatted string like "10.500 ±0.100 mm"
        """
        if value is None:
            return ""

        options = options or {}
        precision = options.get("precision", 3)
        tolerance_type = options.get("tolerance_type", "symmetric")

        dim = cls.deserialize(value)
        if dim is None:
            return str(value)

        val = dim.get("value", 0)
        tol_plus = dim.get("tolerance_plus", 0)
        tol_minus = dim.get("tolerance_minus", 0)
        unit = dim.get("unit", "mm")

        # Format based on tolerance type
        if tol_plus == 0 and tol_minus == 0:
            return f"{val:.{precision}f} {unit}"

        if tolerance_type == "limits":
            min_val = val - tol_minus
            max_val = val + tol_plus
            return f"{min_val:.{precision}f} - {max_val:.{precision}f} {unit}"

        if tol_plus == tol_minus:
            return f"{val:.{precision}f} ±{tol_plus:.{precision}f} {unit}"

        return f"{val:.{precision}f} +{tol_plus:.{precision}f}/-{tol_minus:.{precision}f} {unit}"

    @classmethod
    def convert_unit(
        cls,
        value: dict[str, Any],
        target_unit: str,
    ) -> dict[str, Any]:
        """
        Convert dimension to different unit.

        Args:
            value: Dimension dict
            target_unit: Target unit

        Returns:
            Converted dimension dict
        """
        if value is None:
            return None

        source_unit = value.get("unit", "mm")
        if source_unit == target_unit:
            return value

        if source_unit not in cls.TO_MM or target_unit not in cls.TO_MM:
            raise ValueError(f"Cannot convert between {source_unit} and {target_unit}")

        # Convert to mm, then to target
        factor = cls.TO_MM[source_unit] / cls.TO_MM[target_unit]

        return {
            "value": value["value"] * factor,
            "tolerance_plus": value["tolerance_plus"] * factor,
            "tolerance_minus": value["tolerance_minus"] * factor,
            "unit": target_unit,
        }

    @classmethod
    def is_within_tolerance(cls, actual: float, dimension: dict[str, Any]) -> bool:
        """
        Check if actual value is within tolerance.

        Args:
            actual: Measured value
            dimension: Dimension specification

        Returns:
            True if within tolerance
        """
        if dimension is None:
            return True

        nominal = dimension.get("value", 0)
        tol_plus = dimension.get("tolerance_plus", 0)
        tol_minus = dimension.get("tolerance_minus", 0)

        min_val = nominal - tol_minus
        max_val = nominal + tol_plus

        return min_val <= actual <= max_val
