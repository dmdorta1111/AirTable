"""Surface finish field type handler for PyBase.

Handles surface roughness and finish specifications.
"""

from typing import Any
import re

from pybase.fields.base import BaseFieldTypeHandler


class SurfaceFinishFieldHandler(BaseFieldTypeHandler):
    """
    Handler for surface finish fields.

    Surface finish fields store surface roughness specifications including:
    - Roughness value (Ra, Rz, Rq, etc.)
    - Unit (μm, μin)
    - Machining method/process
    - Lay direction

    Options:
        default_parameter: Default roughness parameter (Ra, Rz, etc.)
        default_unit: Default unit (μm, μin)

    Storage format:
        {
            "parameter": "Ra",
            "value": 1.6,
            "unit": "μm",
            "max_value": null,
            "process": "ground",
            "lay": "perpendicular"
        }

    Display format:
        Ra 1.6 μm ⟂ (Ground)
    """

    field_type = "surface_finish"

    # Surface roughness parameters
    PARAMETERS = {
        "Ra": "Arithmetic Average Roughness",
        "Rz": "Average Maximum Height",
        "Rq": "Root Mean Square Roughness",
        "Rt": "Total Height of Profile",
        "Rmax": "Maximum Roughness Depth",
        "Rp": "Maximum Profile Peak Height",
        "Rv": "Maximum Profile Valley Depth",
        "Rsk": "Skewness",
        "Rku": "Kurtosis",
    }

    # Common Ra values (μm) and their N-numbers
    RA_GRADES = {
        50: "N12",
        25: "N11",
        12.5: "N10",
        6.3: "N9",
        3.2: "N8",
        1.6: "N7",
        0.8: "N6",
        0.4: "N5",
        0.2: "N4",
        0.1: "N3",
        0.05: "N2",
        0.025: "N1",
    }

    # Lay symbols
    LAY_SYMBOLS = {
        "parallel": "=",
        "perpendicular": "⟂",
        "crossed": "X",
        "multidirectional": "M",
        "circular": "C",
        "radial": "R",
        "particulate": "P",
    }

    # Machining processes
    PROCESSES = [
        "turned",
        "milled",
        "ground",
        "lapped",
        "honed",
        "polished",
        "superfinished",
        "EDM",
        "cast",
        "forged",
        "rolled",
        "drawn",
        "extruded",
        "sand_blasted",
        "shot_peened",
    ]

    @classmethod
    def serialize(cls, value: Any) -> dict[str, Any] | None:
        """
        Serialize surface finish specification.

        Args:
            value: Surface finish data (dict or string)

        Returns:
            Standardized surface finish dict or None
        """
        if value is None:
            return None

        if isinstance(value, dict):
            return {
                "parameter": value.get("parameter", "Ra"),
                "value": value.get("value"),
                "max_value": value.get("max_value"),
                "unit": value.get("unit", "μm"),
                "process": value.get("process"),
                "lay": value.get("lay"),
            }

        if isinstance(value, (int, float)):
            return {
                "parameter": "Ra",
                "value": float(value),
                "unit": "μm",
            }

        if isinstance(value, str):
            return cls._parse_surface_finish_string(value)

        return None

    @classmethod
    def deserialize(cls, value: Any) -> dict[str, Any] | None:
        """Deserialize surface finish from storage."""
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        return cls.serialize(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate surface finish specification.

        Args:
            value: Value to validate
            options: Field options

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return True

        parsed = cls.serialize(value)
        if parsed is None:
            raise ValueError("Invalid surface finish format")

        # Validate parameter
        param = parsed.get("parameter", "Ra")
        if param not in cls.PARAMETERS:
            raise ValueError(
                f"Invalid roughness parameter '{param}'. "
                f"Supported: {', '.join(cls.PARAMETERS.keys())}"
            )

        # Validate value is positive
        val = parsed.get("value")
        if val is not None and val < 0:
            raise ValueError("Surface roughness value must be positive")

        # Validate unit
        unit = parsed.get("unit", "μm")
        if unit not in ("μm", "μin", "um", "uin"):
            raise ValueError(f"Invalid unit '{unit}'. Use μm or μin")

        # Validate lay if present
        lay = parsed.get("lay")
        if lay and lay not in cls.LAY_SYMBOLS:
            raise ValueError(
                f"Invalid lay direction '{lay}'. Supported: {', '.join(cls.LAY_SYMBOLS.keys())}"
            )

        return True

    @classmethod
    def default(cls) -> dict[str, Any] | None:
        """Get default value."""
        return None

    @classmethod
    def _parse_surface_finish_string(cls, text: str) -> dict[str, Any] | None:
        """
        Parse surface finish from string.

        Supports formats:
        - "Ra 1.6" or "Ra 1.6 μm"
        - "1.6 μm" (assumes Ra)
        - "N7" (N-number grade)
        """
        text = text.strip()

        # N-number pattern
        n_pattern = r"^N(\d+)$"
        match = re.match(n_pattern, text, re.IGNORECASE)
        if match:
            n_num = int(match.group(1))
            # Find corresponding Ra value
            for ra, grade in cls.RA_GRADES.items():
                if grade == f"N{n_num}":
                    return {
                        "parameter": "Ra",
                        "value": ra,
                        "unit": "μm",
                    }
            return None

        # Parameter + value pattern
        param_pattern = r"^(Ra|Rz|Rq|Rt|Rmax|Rp|Rv)\s*([\d.]+)\s*(μm|μin|um|uin)?$"
        match = re.match(param_pattern, text, re.IGNORECASE)
        if match:
            param = match.group(1)
            value = float(match.group(2))
            unit = match.group(3) or "μm"
            # Normalize unit
            unit = "μm" if unit.lower() in ("um", "μm") else "μin"
            return {
                "parameter": param,
                "value": value,
                "unit": unit,
            }

        # Just value with unit
        value_pattern = r"^([\d.]+)\s*(μm|μin|um|uin)?$"
        match = re.match(value_pattern, text)
        if match:
            value = float(match.group(1))
            unit = match.group(2) or "μm"
            unit = "μm" if unit.lower() in ("um", "μm") else "μin"
            return {
                "parameter": "Ra",
                "value": value,
                "unit": unit,
            }

        return None

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format surface finish for display.

        Args:
            value: Surface finish data
            options: Field options

        Returns:
            Formatted string like "Ra 1.6 μm ⟂ (Ground)"
        """
        if value is None:
            return ""

        sf = cls.deserialize(value)
        if sf is None:
            return str(value)

        parts = []

        # Parameter and value
        param = sf.get("parameter", "Ra")
        val = sf.get("value")
        unit = sf.get("unit", "μm")

        if val is not None:
            parts.append(f"{param} {val} {unit}")

        # Max value if specified (for range)
        max_val = sf.get("max_value")
        if max_val is not None:
            parts[-1] = f"{param} {val}-{max_val} {unit}"

        # Lay symbol
        lay = sf.get("lay")
        if lay and lay in cls.LAY_SYMBOLS:
            parts.append(cls.LAY_SYMBOLS[lay])

        # Process
        process = sf.get("process")
        if process:
            parts.append(f"({process.replace('_', ' ').title()})")

        return " ".join(parts)

    @classmethod
    def convert_unit(
        cls,
        value: dict[str, Any],
        target_unit: str,
    ) -> dict[str, Any]:
        """
        Convert surface finish to different unit.

        Args:
            value: Surface finish dict
            target_unit: Target unit (μm or μin)

        Returns:
            Converted surface finish dict
        """
        if value is None:
            return None

        source_unit = value.get("unit", "μm")
        if source_unit == target_unit:
            return value

        # Conversion factor: 1 μm = 39.37 μin
        if source_unit in ("μm", "um") and target_unit in ("μin", "uin"):
            factor = 39.37
        elif source_unit in ("μin", "uin") and target_unit in ("μm", "um"):
            factor = 1 / 39.37
        else:
            raise ValueError(f"Cannot convert between {source_unit} and {target_unit}")

        result = dict(value)
        result["value"] = value["value"] * factor if value.get("value") else None
        result["max_value"] = value["max_value"] * factor if value.get("max_value") else None
        result["unit"] = "μm" if target_unit in ("μm", "um") else "μin"

        return result

    @classmethod
    def get_n_grade(cls, ra_value: float) -> str | None:
        """
        Get N-number grade for Ra value.

        Args:
            ra_value: Ra value in μm

        Returns:
            N-grade string or None
        """
        # Find closest standard value
        closest = min(cls.RA_GRADES.keys(), key=lambda x: abs(x - ra_value))
        if abs(closest - ra_value) / closest < 0.1:  # Within 10%
            return cls.RA_GRADES[closest]
        return None
