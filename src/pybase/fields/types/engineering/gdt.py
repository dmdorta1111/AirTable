"""GD&T (Geometric Dimensioning and Tolerancing) field type handler.

Handles geometric tolerancing specifications per ASME Y14.5 / ISO 1101.
"""

from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class GDTFieldHandler(BaseFieldTypeHandler):
    """
    Handler for GD&T fields.

    GD&T fields store geometric tolerancing specifications including:
    - Tolerance type (flatness, parallelism, position, etc.)
    - Tolerance zone value
    - Material condition modifiers (MMC, LMC, RFS)
    - Datum references

    Options:
        allowed_types: List of allowed GD&T types
        require_datums: Whether datum references are required

    Storage format:
        {
            "type": "position",
            "tolerance": 0.05,
            "diameter_zone": true,
            "material_condition": "MMC",
            "datums": ["A", "B", "C"]
        }

    Display format:
        ⌖ ⌀0.05 Ⓜ | A | B | C
    """

    field_type = "gdt"

    # GD&T characteristic symbols and types
    GDT_TYPES = {
        # Form tolerances (no datum required)
        "straightness": {"symbol": "⏤", "requires_datum": False},
        "flatness": {"symbol": "⏥", "requires_datum": False},
        "circularity": {"symbol": "○", "requires_datum": False},
        "cylindricity": {"symbol": "⌭", "requires_datum": False},
        # Orientation tolerances (datum required)
        "perpendicularity": {"symbol": "⟂", "requires_datum": True},
        "parallelism": {"symbol": "∥", "requires_datum": True},
        "angularity": {"symbol": "∠", "requires_datum": True},
        # Location tolerances (datum required)
        "position": {"symbol": "⌖", "requires_datum": True},
        "concentricity": {"symbol": "◎", "requires_datum": True},
        "symmetry": {"symbol": "⌯", "requires_datum": True},
        # Runout tolerances (datum required)
        "circular_runout": {"symbol": "↗", "requires_datum": True},
        "total_runout": {"symbol": "⌰", "requires_datum": True},
        # Profile tolerances
        "profile_line": {"symbol": "⌒", "requires_datum": False},
        "profile_surface": {"symbol": "⌓", "requires_datum": False},
    }

    # Material condition modifiers
    MATERIAL_CONDITIONS = {
        "MMC": "Ⓜ",  # Maximum Material Condition
        "LMC": "Ⓛ",  # Least Material Condition
        "RFS": "",  # Regardless of Feature Size (default, no symbol)
    }

    @classmethod
    def serialize(cls, value: Any) -> dict[str, Any] | None:
        """
        Serialize GD&T specification to storage format.

        Args:
            value: GD&T data (dict or string)

        Returns:
            Standardized GD&T dict or None
        """
        if value is None:
            return None

        if isinstance(value, dict):
            return {
                "type": value.get("type"),
                "tolerance": value.get("tolerance"),
                "diameter_zone": value.get("diameter_zone", False),
                "material_condition": value.get("material_condition", "RFS"),
                "datums": value.get("datums", []),
                "datum_modifiers": value.get("datum_modifiers", {}),
            }

        if isinstance(value, str):
            # Basic string parsing - just store as display text
            return {
                "type": "custom",
                "display_text": value,
                "tolerance": None,
                "diameter_zone": False,
                "material_condition": "RFS",
                "datums": [],
            }

        return None

    @classmethod
    def deserialize(cls, value: Any) -> dict[str, Any] | None:
        """Deserialize GD&T from storage."""
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        return cls.serialize(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate GD&T specification with comprehensive datum and material condition checks.

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
            raise ValueError("Invalid GD&T format")

        gdt_type = parsed.get("type")
        if gdt_type and gdt_type != "custom" and gdt_type not in cls.GDT_TYPES:
            raise ValueError(
                f"Invalid GD&T type '{gdt_type}'. Supported: {', '.join(cls.GDT_TYPES.keys())}"
            )

        # Validate tolerance is positive
        tolerance = parsed.get("tolerance")
        if tolerance is not None and tolerance < 0:
            raise ValueError("GD&T tolerance must be positive")

        # Validate material condition
        mc = parsed.get("material_condition", "RFS")
        if mc and mc not in cls.MATERIAL_CONDITIONS:
            raise ValueError(
                f"Invalid material condition '{mc}'. "
                f"Supported: {', '.join(cls.MATERIAL_CONDITIONS.keys())}"
            )

        # Comprehensive datum validation
        datums = parsed.get("datums", [])
        if datums:
            # Check if datums is a list
            if not isinstance(datums, list):
                raise ValueError("Datums must be a list")

            # Validate each datum
            seen_datums = set()
            for datum in datums:
                if not isinstance(datum, str):
                    raise ValueError(f"Datum must be a string, got {type(datum).__name__}")

                # Check for valid datum format (typically uppercase letters)
                if not datum or not datum.strip():
                    raise ValueError("Datum cannot be empty")

                # Datum should be alphanumeric (allowing dash/underscore for composite datums)
                if not datum.replace("-", "").replace("_", "").isalnum():
                    raise ValueError(f"Invalid datum format: '{datum}'")

                # Check for duplicate datums
                if datum in seen_datums:
                    raise ValueError(f"Duplicate datum reference: '{datum}'")
                seen_datums.add(datum)

        # Comprehensive datum modifier validation
        datum_modifiers = parsed.get("datum_modifiers", {})
        if datum_modifiers:
            if not isinstance(datum_modifiers, dict):
                raise ValueError("Datum modifiers must be a dictionary")

            for datum, modifier in datum_modifiers.items():
                # Check if datum exists in datums list
                if datum not in datums:
                    raise ValueError(f"Datum modifier references non-existent datum: '{datum}'")

                # Validate modifier is a valid material condition
                if modifier not in cls.MATERIAL_CONDITIONS:
                    raise ValueError(
                        f"Invalid datum modifier '{modifier}' for datum '{datum}'. "
                        f"Supported: {', '.join(cls.MATERIAL_CONDITIONS.keys())}"
                    )

        # Validate datum requirements based on GD&T type
        if gdt_type and gdt_type in cls.GDT_TYPES:
            type_info = cls.GDT_TYPES[gdt_type]
            if type_info["requires_datum"] and not datums:
                options = options or {}
                if options.get("require_datums", True):
                    raise ValueError(f"{gdt_type} requires datum reference(s)")

        return True

    @classmethod
    def default(cls) -> dict[str, Any] | None:
        """Get default value."""
        return None

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format GD&T for display using standard symbols.

        Args:
            value: GD&T data
            options: Field options

        Returns:
            Formatted string with GD&T symbols
        """
        if value is None:
            return ""

        gdt = cls.deserialize(value)
        if gdt is None:
            return str(value)

        # Custom display text
        if gdt.get("display_text"):
            return gdt["display_text"]

        gdt_type = gdt.get("type")
        if not gdt_type or gdt_type not in cls.GDT_TYPES:
            return str(value)

        # Build feature control frame
        parts = []

        # Symbol
        symbol = cls.GDT_TYPES[gdt_type]["symbol"]
        parts.append(symbol)

        # Tolerance zone
        tolerance = gdt.get("tolerance")
        if tolerance is not None:
            zone_str = ""
            if gdt.get("diameter_zone"):
                zone_str = "⌀"
            zone_str += f"{tolerance}"

            # Material condition modifier
            mc = gdt.get("material_condition", "RFS")
            if mc in cls.MATERIAL_CONDITIONS and cls.MATERIAL_CONDITIONS[mc]:
                zone_str += f" {cls.MATERIAL_CONDITIONS[mc]}"

            parts.append(zone_str)

        # Datum references
        datums = gdt.get("datums", [])
        datum_modifiers = gdt.get("datum_modifiers", {})
        for datum in datums:
            datum_str = datum
            if datum in datum_modifiers:
                modifier = datum_modifiers[datum]
                if modifier in cls.MATERIAL_CONDITIONS:
                    datum_str += f" {cls.MATERIAL_CONDITIONS[modifier]}"
            parts.append(datum_str)

        return " | ".join(parts)

    @classmethod
    def get_symbol(cls, gdt_type: str) -> str | None:
        """
        Get the GD&T symbol for a type.

        Args:
            gdt_type: GD&T type name

        Returns:
            Symbol character or None
        """
        if gdt_type in cls.GDT_TYPES:
            return cls.GDT_TYPES[gdt_type]["symbol"]
        return None

    @classmethod
    def requires_datum(cls, gdt_type: str) -> bool:
        """
        Check if GD&T type requires datum reference.

        Args:
            gdt_type: GD&T type name

        Returns:
            True if datum required
        """
        if gdt_type in cls.GDT_TYPES:
            return cls.GDT_TYPES[gdt_type]["requires_datum"]
        return False
