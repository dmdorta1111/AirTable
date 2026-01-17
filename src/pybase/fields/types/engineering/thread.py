"""Thread field type handler for PyBase.

Handles thread specifications for fasteners and threaded features.
"""

from typing import Any
import re

from pybase.fields.base import BaseFieldTypeHandler


class ThreadFieldHandler(BaseFieldTypeHandler):
    """
    Handler for thread fields.

    Thread fields store thread specifications including:
    - Thread standard (Metric, UNC, UNF, etc.)
    - Nominal size
    - Pitch/TPI
    - Thread class/fit
    - Internal/External

    Options:
        standards: List of allowed thread standards
        default_standard: Default standard to assume

    Storage format:
        {
            "standard": "metric",
            "size": 8,
            "pitch": 1.25,
            "class": "6g",
            "internal": false,
            "left_hand": false
        }

    Display format examples:
        - "M8x1.25-6g" (Metric external)
        - "M8x1.25-6H" (Metric internal)
        - "1/4-20 UNC-2A" (Unified external)
        - "1/4-20 UNC-2B" (Unified internal)
    """

    field_type = "thread"

    # Thread standards
    STANDARDS = {
        "metric": "ISO Metric (M)",
        "unc": "Unified Coarse (UNC)",
        "unf": "Unified Fine (UNF)",
        "unef": "Unified Extra Fine (UNEF)",
        "bsp": "British Standard Pipe (BSP)",
        "npt": "National Pipe Thread (NPT)",
        "acme": "ACME",
        "buttress": "Buttress",
    }

    # Standard metric coarse pitches
    METRIC_COARSE_PITCH = {
        1: 0.25,
        1.2: 0.25,
        1.4: 0.3,
        1.6: 0.35,
        1.8: 0.35,
        2: 0.4,
        2.5: 0.45,
        3: 0.5,
        3.5: 0.6,
        4: 0.7,
        5: 0.8,
        6: 1,
        7: 1,
        8: 1.25,
        10: 1.5,
        12: 1.75,
        14: 2,
        16: 2,
        18: 2.5,
        20: 2.5,
        22: 2.5,
        24: 3,
        27: 3,
        30: 3.5,
        33: 3.5,
        36: 4,
        39: 4,
        42: 4.5,
        45: 4.5,
        48: 5,
    }

    @classmethod
    def serialize(cls, value: Any) -> dict[str, Any] | None:
        """
        Serialize thread specification.

        Args:
            value: Thread data (dict or string)

        Returns:
            Standardized thread dict or None
        """
        if value is None:
            return None

        if isinstance(value, dict):
            return {
                "standard": value.get("standard", "metric"),
                "size": value.get("size"),
                "pitch": value.get("pitch"),
                "tpi": value.get("tpi"),  # Threads per inch (unified)
                "class": value.get("class"),
                "internal": value.get("internal", False),
                "left_hand": value.get("left_hand", False),
            }

        if isinstance(value, str):
            return cls._parse_thread_string(value)

        return None

    @classmethod
    def deserialize(cls, value: Any) -> dict[str, Any] | None:
        """Deserialize thread from storage."""
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        return cls.serialize(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate thread specification.

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
            raise ValueError("Invalid thread format")

        # Validate standard
        standard = parsed.get("standard", "metric")
        if standard not in cls.STANDARDS:
            raise ValueError(
                f"Invalid thread standard '{standard}'. "
                f"Supported: {', '.join(cls.STANDARDS.keys())}"
            )

        # Validate size is present
        if parsed.get("size") is None:
            raise ValueError("Thread must have a size")

        # Validate pitch/tpi for standard
        if standard == "metric" and parsed.get("pitch") is None:
            # Default to coarse pitch
            size = parsed.get("size")
            if size in cls.METRIC_COARSE_PITCH:
                parsed["pitch"] = cls.METRIC_COARSE_PITCH[size]

        if standard in ("unc", "unf", "unef") and parsed.get("tpi") is None:
            raise ValueError(f"{standard.upper()} threads require TPI")

        return True

    @classmethod
    def default(cls) -> dict[str, Any] | None:
        """Get default value."""
        return None

    @classmethod
    def _parse_thread_string(cls, text: str) -> dict[str, Any] | None:
        """
        Parse thread from string.

        Supports formats:
        - M8x1.25 or M8x1.25-6g (Metric)
        - 1/4-20 UNC or 1/4-20 UNC-2A (Unified)
        """
        text = text.strip().upper()

        # Metric pattern: M<size>x<pitch>[-<class>]
        metric_pattern = r"^M([\d.]+)(?:X([\d.]+))?(?:-(\dG|\dH))?(?:\s*(LH))?$"
        match = re.match(metric_pattern, text, re.IGNORECASE)
        if match:
            size = float(match.group(1))
            pitch = float(match.group(2)) if match.group(2) else None
            thread_class = match.group(3)
            left_hand = match.group(4) is not None

            # Default to coarse pitch if not specified
            if pitch is None and size in cls.METRIC_COARSE_PITCH:
                pitch = cls.METRIC_COARSE_PITCH[size]

            # Determine internal/external from class
            internal = thread_class and thread_class[-1].upper() == "H"

            return {
                "standard": "metric",
                "size": size,
                "pitch": pitch,
                "class": thread_class.lower() if thread_class else None,
                "internal": internal,
                "left_hand": left_hand,
            }

        # Unified pattern: <size>-<tpi> <standard>[-<class>]
        unified_pattern = r"^([\d/]+)-([\d]+)\s*(UNC|UNF|UNEF)(?:-(\d[AB]))?(?:\s*(LH))?$"
        match = re.match(unified_pattern, text, re.IGNORECASE)
        if match:
            size_str = match.group(1)
            # Convert fractional sizes
            if "/" in size_str:
                parts = size_str.split("/")
                size = float(parts[0]) / float(parts[1])
            else:
                size = float(size_str)

            tpi = int(match.group(2))
            standard = match.group(3).lower()
            thread_class = match.group(4)
            left_hand = match.group(5) is not None

            # Determine internal/external from class
            internal = thread_class and thread_class[-1].upper() == "B"

            return {
                "standard": standard,
                "size": size,
                "tpi": tpi,
                "class": thread_class,
                "internal": internal,
                "left_hand": left_hand,
            }

        return None

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format thread for display.

        Args:
            value: Thread data
            options: Field options

        Returns:
            Formatted thread string
        """
        if value is None:
            return ""

        thread = cls.deserialize(value)
        if thread is None:
            return str(value)

        standard = thread.get("standard", "metric")
        size = thread.get("size")
        pitch = thread.get("pitch")
        tpi = thread.get("tpi")
        thread_class = thread.get("class")
        left_hand = thread.get("left_hand", False)

        if standard == "metric":
            result = f"M{size}"
            if pitch:
                result += f"x{pitch}"
            if thread_class:
                result += f"-{thread_class}"
            if left_hand:
                result += " LH"
            return result

        if standard in ("unc", "unf", "unef"):
            # Format fractional sizes
            if size < 1:
                # Convert decimal to fraction if common size
                fraction_map = {
                    0.25: "1/4",
                    0.3125: "5/16",
                    0.375: "3/8",
                    0.4375: "7/16",
                    0.5: "1/2",
                    0.5625: "9/16",
                    0.625: "5/8",
                    0.75: "3/4",
                    0.875: "7/8",
                }
                size_str = fraction_map.get(size, f"{size:.4f}")
            else:
                size_str = str(int(size)) if size == int(size) else str(size)

            result = f"{size_str}-{tpi} {standard.upper()}"
            if thread_class:
                result += f"-{thread_class}"
            if left_hand:
                result += " LH"
            return result

        # Generic format for other standards
        result = f"{size} {standard.upper()}"
        if pitch:
            result += f" P{pitch}"
        if thread_class:
            result += f"-{thread_class}"
        if left_hand:
            result += " LH"

        return result

    @classmethod
    def get_coarse_pitch(cls, size: float) -> float | None:
        """
        Get standard coarse pitch for metric size.

        Args:
            size: Metric thread nominal diameter

        Returns:
            Coarse pitch or None
        """
        return cls.METRIC_COARSE_PITCH.get(size)
