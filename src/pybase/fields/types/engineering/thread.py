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

    # Standard metric coarse pitches (ISO 724)
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
        52: 5,
        56: 5.5,
        60: 5.5,
        64: 6,
        68: 6,
    }

    # Valid metric fine pitches (ISO 262)
    METRIC_FINE_PITCHES = {
        1: [0.2],
        1.2: [0.2],
        1.4: [0.2],
        1.6: [0.2],
        1.8: [0.2],
        2: [0.25],
        2.5: [0.35],
        3: [0.35],
        4: [0.5],
        5: [0.5],
        6: [0.75],
        8: [1, 0.75],
        10: [1.25, 1],
        12: [1.5, 1.25, 1],
        14: [1.5, 1],
        16: [1.5, 1],
        18: [2, 1.5, 1],
        20: [2, 1.5, 1],
        22: [2, 1.5, 1],
        24: [2, 1.5],
        27: [2, 1.5],
        30: [2, 1.5],
        33: [2, 1.5],
        36: [3, 2, 1.5],
        39: [3, 2, 1.5],
        42: [3, 2, 1.5],
        45: [3, 2, 1.5],
        48: [3, 2, 1.5],
        52: [3, 2, 1.5],
        56: [4, 3, 2],
        60: [4, 3, 2],
        64: [4, 3, 2],
        68: [4, 3, 2],
    }

    # Valid metric sizes (ISO 724) - minimum and maximum
    METRIC_SIZE_RANGE = {
        "min": 0.25,
        "max": 68,
        "common": [1, 1.2, 1.4, 1.6, 1.8, 2, 2.5, 3, 3.5, 4, 5, 6, 7, 8, 10, 12, 14, 16, 18, 20, 22, 24, 27, 30, 33, 36, 39, 42, 45, 48, 52, 56, 60, 64, 68],
    }

    # UNC (Unified Coarse) standard sizes and TPI (ANSI B1.1)
    UNC_STANDARD = {
        # Number sizes
        "#1": {"size": 0.073, "tpi": 64},
        "#2": {"size": 0.086, "tpi": 56},
        "#3": {"size": 0.099, "tpi": 48},
        "#4": {"size": 0.112, "tpi": 40},
        "#5": {"size": 0.125, "tpi": 40},
        "#6": {"size": 0.138, "tpi": 32},
        "#8": {"size": 0.164, "tpi": 32},
        "#10": {"size": 0.190, "tpi": 24},
        "#12": {"size": 0.216, "tpi": 24},
        # Fractional sizes
        0.25: 20,    # 1/4-20
        0.3125: 18,  # 5/16-18
        0.375: 16,   # 3/8-16
        0.4375: 14,  # 7/16-14
        0.5: 13,     # 1/2-13
        0.5625: 12,  # 9/16-12
        0.625: 11,   # 5/8-11
        0.75: 10,    # 3/4-10
        0.875: 9,    # 7/8-9
        1: 8,        # 1-8
        1.125: 7,    # 1 1/8-7
        1.25: 7,     # 1 1/4-7
        1.375: 6,    # 1 3/8-6
        1.5: 6,      # 1 1/2-6
        1.75: 5,     # 1 3/4-5
        2: 4.5,      # 2-4.5
    }

    # UNF (Unified Fine) standard sizes and TPI (ANSI B1.1)
    UNF_STANDARD = {
        "#0": {"size": 0.060, "tpi": 80},
        "#1": {"size": 0.073, "tpi": 72},
        "#2": {"size": 0.086, "tpi": 64},
        "#3": {"size": 0.099, "tpi": 56},
        "#4": {"size": 0.112, "tpi": 48},
        "#5": {"size": 0.125, "tpi": 44},
        "#6": {"size": 0.138, "tpi": 40},
        "#8": {"size": 0.164, "tpi": 36},
        "#10": {"size": 0.190, "tpi": 32},
        "#12": {"size": 0.216, "tpi": 28},
        0.25: 28,    # 1/4-28
        0.3125: 24,  # 5/16-24
        0.375: 24,   # 3/8-24
        0.4375: 20,  # 7/16-20
        0.5: 20,     # 1/2-20
        0.5625: 18,  # 9/16-18
        0.625: 18,   # 5/8-18
        0.75: 16,    # 3/4-16
        0.875: 14,   # 7/8-14
        1: 12,       # 1-12
        1.125: 12,   # 1 1/8-12
        1.25: 12,    # 1 1/4-12
        1.375: 12,   # 1 3/8-12
        1.5: 12,     # 1 1/2-12
    }

    # Valid thread classes
    METRIC_THREAD_CLASSES = ["4h", "5h", "6h", "7h", "8h", "4g", "5g", "6g", "7g", "8g"]
    UNIFIED_THREAD_CLASSES = ["1a", "2a", "3a", "1b", "2b", "3b"]

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
        Validate thread specification with comprehensive ISO/ANSI standard checks.

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
        size = parsed.get("size")
        if size is None:
            raise ValueError("Thread must have a size")

        # Validate metric threads (ISO 724, ISO 262)
        if standard == "metric":
            cls._validate_metric_thread(parsed)

        # Validate unified threads (ANSI B1.1)
        elif standard == "unc":
            cls._validate_unc_thread(parsed)

        elif standard == "unf":
            cls._validate_unf_thread(parsed)

        elif standard == "unef":
            cls._validate_unef_thread(parsed)

        # Validate thread class if present
        thread_class = parsed.get("class")
        if thread_class:
            cls._validate_thread_class(thread_class, standard)

        return True

    @classmethod
    def _validate_metric_thread(cls, parsed: dict[str, Any]) -> None:
        """
        Validate metric thread against ISO 724 and ISO 262 standards.

        Args:
            parsed: Parsed thread data

        Raises:
            ValueError: If validation fails
        """
        size = parsed.get("size")
        pitch = parsed.get("pitch")

        # Validate size range (ISO 724)
        if size < cls.METRIC_SIZE_RANGE["min"] or size > cls.METRIC_SIZE_RANGE["max"]:
            raise ValueError(
                f"Metric thread size {size}mm is outside valid range "
                f"({cls.METRIC_SIZE_RANGE['min']}-{cls.METRIC_SIZE_RANGE['max']}mm)"
            )

        # Warn if non-standard size
        if size not in cls.METRIC_SIZE_RANGE["common"]:
            # Allow non-standard sizes but could log warning
            pass

        # Validate pitch
        if pitch is None:
            # Default to coarse pitch if available
            if size in cls.METRIC_COARSE_PITCH:
                parsed["pitch"] = cls.METRIC_COARSE_PITCH[size]
            else:
                raise ValueError(
                    f"No standard coarse pitch defined for M{size}. "
                    f"Please specify pitch explicitly."
                )
        else:
            # Validate pitch is reasonable
            if pitch <= 0:
                raise ValueError(f"Thread pitch must be positive, got {pitch}")

            # Check if pitch matches coarse pitch
            coarse_pitch = cls.METRIC_COARSE_PITCH.get(size)
            if coarse_pitch and abs(pitch - coarse_pitch) < 0.01:
                # It's coarse pitch, which is always valid
                pass
            else:
                # Check if it's a valid fine pitch (ISO 262)
                valid_fine_pitches = cls.METRIC_FINE_PITCHES.get(size, [])
                if valid_fine_pitches:
                    # Check if pitch matches any fine pitch
                    pitch_valid = any(abs(pitch - fp) < 0.01 for fp in valid_fine_pitches)
                    if not pitch_valid:
                        raise ValueError(
                            f"Invalid pitch {pitch}mm for M{size}. "
                            f"Valid pitches: {coarse_pitch} (coarse), {', '.join(map(str, valid_fine_pitches))} (fine)"
                        )
                else:
                    # No fine pitches defined, accept if reasonable
                    if pitch > size:
                        raise ValueError(
                            f"Thread pitch {pitch}mm cannot exceed thread size {size}mm"
                        )

    @classmethod
    def _validate_unc_thread(cls, parsed: dict[str, Any]) -> None:
        """
        Validate UNC thread against ANSI B1.1 standard.

        Args:
            parsed: Parsed thread data

        Raises:
            ValueError: If validation fails
        """
        size = parsed.get("size")
        tpi = parsed.get("tpi")

        if tpi is None:
            raise ValueError("UNC threads require TPI (threads per inch)")

        # Check if size matches standard UNC
        standard_tpi = cls.UNC_STANDARD.get(size)
        if isinstance(standard_tpi, dict):
            standard_tpi = standard_tpi["tpi"]

        if standard_tpi:
            if abs(tpi - standard_tpi) > 0.1:
                raise ValueError(
                    f"Non-standard TPI {tpi} for {size}\" UNC thread. "
                    f"Standard UNC TPI is {standard_tpi}"
                )
        else:
            # Non-standard size, validate TPI is reasonable
            if tpi <= 0:
                raise ValueError(f"TPI must be positive, got {tpi}")
            if tpi > 80:
                raise ValueError(f"TPI {tpi} is unusually high for UNC thread")

    @classmethod
    def _validate_unf_thread(cls, parsed: dict[str, Any]) -> None:
        """
        Validate UNF thread against ANSI B1.1 standard.

        Args:
            parsed: Parsed thread data

        Raises:
            ValueError: If validation fails
        """
        size = parsed.get("size")
        tpi = parsed.get("tpi")

        if tpi is None:
            raise ValueError("UNF threads require TPI (threads per inch)")

        # Check if size matches standard UNF
        standard_tpi = cls.UNF_STANDARD.get(size)
        if isinstance(standard_tpi, dict):
            standard_tpi = standard_tpi["tpi"]

        if standard_tpi:
            if abs(tpi - standard_tpi) > 0.1:
                raise ValueError(
                    f"Non-standard TPI {tpi} for {size}\" UNF thread. "
                    f"Standard UNF TPI is {standard_tpi}"
                )
        else:
            # Non-standard size, validate TPI is reasonable
            if tpi <= 0:
                raise ValueError(f"TPI must be positive, got {tpi}")
            if tpi > 80:
                raise ValueError(f"TPI {tpi} is unusually high for UNF thread")

    @classmethod
    def _validate_unef_thread(cls, parsed: dict[str, Any]) -> None:
        """
        Validate UNEF thread against ANSI B1.1 standard.

        Args:
            parsed: Parsed thread data

        Raises:
            ValueError: If validation fails
        """
        size = parsed.get("size")
        tpi = parsed.get("tpi")

        if tpi is None:
            raise ValueError("UNEF threads require TPI (threads per inch)")

        # UNEF has limited standard sizes, validate TPI is reasonable
        if tpi <= 0:
            raise ValueError(f"TPI must be positive, got {tpi}")
        if tpi > 32:
            raise ValueError(f"TPI {tpi} is unusually high for UNEF thread")

    @classmethod
    def _validate_thread_class(cls, thread_class: str, standard: str) -> None:
        """
        Validate thread class/tolerance grade.

        Args:
            thread_class: Thread class/grade
            standard: Thread standard

        Raises:
            ValueError: If thread class is invalid
        """
        thread_class_lower = thread_class.lower()

        if standard == "metric":
            if thread_class_lower not in cls.METRIC_THREAD_CLASSES:
                raise ValueError(
                    f"Invalid metric thread class '{thread_class}'. "
                    f"Valid classes: {', '.join(cls.METRIC_THREAD_CLASSES)}"
                )
        elif standard in ("unc", "unf", "unef"):
            if thread_class_lower not in cls.UNIFIED_THREAD_CLASSES:
                raise ValueError(
                    f"Invalid unified thread class '{thread_class}'. "
                    f"Valid classes: {', '.join(cls.UNIFIED_THREAD_CLASSES)}"
                )

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
