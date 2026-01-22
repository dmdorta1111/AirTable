"""Material field type handler for PyBase.

Handles material specifications for engineering applications.
"""

from typing import Any

from pybase.fields.base import BaseFieldTypeHandler


class MaterialFieldHandler(BaseFieldTypeHandler):
    """
    Handler for material fields.

    Material fields store material specifications including:
    - Material designation/grade
    - Standard (ASTM, ISO, DIN, etc.)
    - Material type/family
    - Key properties (density, yield strength, etc.)
    - Heat treatment/condition

    Options:
        allowed_types: List of allowed material families
        require_standard: Whether standard is required

    Storage format:
        {
            "designation": "AISI 304",
            "standard": "ASTM",
            "family": "stainless_steel",
            "condition": "annealed",
            "properties": {
                "density": 8000,
                "yield_strength": 215,
                "tensile_strength": 505,
                "elongation": 40,
                "hardness": "HRB 92"
            }
        }

    Display format:
        AISI 304 Stainless Steel (Annealed)
    """

    field_type = "material"

    # Material families
    FAMILIES = {
        "carbon_steel": "Carbon Steel",
        "alloy_steel": "Alloy Steel",
        "stainless_steel": "Stainless Steel",
        "tool_steel": "Tool Steel",
        "aluminum": "Aluminum",
        "copper": "Copper",
        "brass": "Brass",
        "bronze": "Bronze",
        "titanium": "Titanium",
        "nickel": "Nickel Alloy",
        "magnesium": "Magnesium",
        "zinc": "Zinc",
        "cast_iron": "Cast Iron",
        "plastic": "Plastic/Polymer",
        "composite": "Composite",
        "ceramic": "Ceramic",
        "rubber": "Rubber/Elastomer",
    }

    # Material standards
    STANDARDS = {
        "ASTM": "American Society for Testing and Materials",
        "AISI": "American Iron and Steel Institute",
        "SAE": "Society of Automotive Engineers",
        "ISO": "International Organization for Standardization",
        "DIN": "German Institute for Standardization",
        "JIS": "Japanese Industrial Standards",
        "EN": "European Standard",
        "BS": "British Standard",
        "GB": "Chinese National Standard",
        "UNS": "Unified Numbering System",
    }

    # Common heat treatment conditions
    CONDITIONS = {
        "annealed": "Annealed",
        "normalized": "Normalized",
        "hardened": "Hardened",
        "tempered": "Hardened & Tempered",
        "quenched": "Quenched",
        "cold_worked": "Cold Worked",
        "hot_rolled": "Hot Rolled",
        "cold_rolled": "Cold Rolled",
        "solution_treated": "Solution Treated",
        "age_hardened": "Age Hardened",
        "stress_relieved": "Stress Relieved",
        "as_cast": "As Cast",
        "as_forged": "As Forged",
    }

    # Property ranges for validation (based on engineering standards)
    # Ranges are intentionally broad to accommodate wide variety of materials
    PROPERTY_RANGES = {
        "density": {
            "min": 0.5,  # kg/m³ (some foams and polymers)
            "max": 22600,  # kg/m³ (osmium, densest natural element)
            "unit": "kg/m³",
        },
        "yield_strength": {
            "min": 0.1,  # MPa (soft elastomers)
            "max": 5000,  # MPa (ultra-high strength steels)
            "unit": "MPa",
        },
        "tensile_strength": {
            "min": 0.5,  # MPa (soft elastomers)
            "max": 6000,  # MPa (advanced composites, ceramics)
            "unit": "MPa",
        },
        "elongation": {
            "min": 0,  # % (brittle materials like ceramics)
            "max": 1000,  # % (some elastomers can stretch 10x)
            "unit": "%",
        },
        "modulus": {
            "min": 0.001,  # GPa (soft rubbers)
            "max": 1200,  # GPa (diamond)
            "unit": "GPa",
        },
        "thermal_conductivity": {
            "min": 0.01,  # W/m·K (aerogels)
            "max": 2000,  # W/m·K (diamond)
            "unit": "W/m·K",
        },
        "melting_point": {
            "min": -200,  # °C (some low-melting alloys)
            "max": 3700,  # °C (tungsten)
            "unit": "°C",
        },
        "thermal_expansion": {
            "min": 0,  # μm/m·K (near-zero expansion materials)
            "max": 200,  # μm/m·K (some polymers)
            "unit": "μm/m·K",
        },
        "poisson_ratio": {
            "min": -1.0,  # (auxetic materials)
            "max": 0.5,  # (incompressible materials)
            "unit": None,  # dimensionless
        },
        "hardness_hb": {
            "min": 1,  # HB (soft materials)
            "max": 650,  # HB (very hard steels)
            "unit": "HB",
        },
        "hardness_hrc": {
            "min": 20,  # HRC (lower bound for Rockwell C scale)
            "max": 70,  # HRC (hardened tool steels)
            "unit": "HRC",
        },
        "hardness_hrb": {
            "min": 0,  # HRB (softer materials)
            "max": 100,  # HRB (maximum for Rockwell B scale)
            "unit": "HRB",
        },
    }

    # Standard-family compatibility mapping
    # Some standards are specific to certain material families
    STANDARD_FAMILY_COMPATIBILITY = {
        "AISI": ["carbon_steel", "alloy_steel", "stainless_steel", "tool_steel"],
        "SAE": ["carbon_steel", "alloy_steel", "stainless_steel", "tool_steel"],
        "ASTM": None,  # ASTM covers all materials
        "ISO": None,  # ISO covers all materials
        "DIN": None,  # DIN covers all materials
        "JIS": None,  # JIS covers all materials
        "EN": None,  # EN covers all materials
        "BS": None,  # BS covers all materials
        "GB": None,  # GB covers all materials
        "UNS": None,  # UNS covers all materials
    }

    @classmethod
    def serialize(cls, value: Any) -> dict[str, Any] | None:
        """
        Serialize material specification.

        Args:
            value: Material data (dict or string)

        Returns:
            Standardized material dict or None
        """
        if value is None:
            return None

        if isinstance(value, dict):
            return {
                "designation": value.get("designation"),
                "standard": value.get("standard"),
                "family": value.get("family"),
                "condition": value.get("condition"),
                "properties": value.get("properties", {}),
                "notes": value.get("notes"),
            }

        if isinstance(value, str):
            # Simple string - store as designation
            return {
                "designation": value,
                "standard": None,
                "family": cls._guess_family(value),
                "condition": None,
                "properties": {},
            }

        return None

    @classmethod
    def deserialize(cls, value: Any) -> dict[str, Any] | None:
        """Deserialize material from storage."""
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        return cls.serialize(value)

    @classmethod
    def validate(cls, value: Any, options: dict[str, Any] | None = None) -> bool:
        """
        Validate material specification.

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
            raise ValueError("Invalid material format")

        # Validate designation is present
        if not parsed.get("designation"):
            raise ValueError("Material must have a designation")

        # Validate family if present
        family = parsed.get("family")
        if family and family not in cls.FAMILIES:
            raise ValueError(
                f"Invalid material family '{family}'. Supported: {', '.join(cls.FAMILIES.keys())}"
            )

        # Validate standard if present
        standard = parsed.get("standard")
        if standard and standard not in cls.STANDARDS:
            raise ValueError(
                f"Invalid standard '{standard}'. Supported: {', '.join(cls.STANDARDS.keys())}"
            )

        # Validate condition if present
        condition = parsed.get("condition")
        if condition and condition not in cls.CONDITIONS:
            raise ValueError(
                f"Invalid condition '{condition}'. Supported: {', '.join(cls.CONDITIONS.keys())}"
            )

        # Validate properties are numeric where expected
        props = parsed.get("properties", {})
        numeric_props = [
            "density",
            "yield_strength",
            "tensile_strength",
            "elongation",
            "modulus",
            "thermal_conductivity",
            "melting_point",
            "thermal_expansion",
            "poisson_ratio",
            "hardness_hb",
            "hardness_hrc",
            "hardness_hrb",
        ]
        for prop in numeric_props:
            if prop in props and props[prop] is not None:
                try:
                    prop_value = float(props[prop])
                except (ValueError, TypeError):
                    raise ValueError(f"Property '{prop}' must be numeric")

                # Validate property ranges if defined
                if prop in cls.PROPERTY_RANGES:
                    prop_range = cls.PROPERTY_RANGES[prop]
                    min_val = prop_range["min"]
                    max_val = prop_range["max"]

                    if prop_value < min_val or prop_value > max_val:
                        unit = prop_range["unit"]
                        unit_str = f" {unit}" if unit else ""
                        raise ValueError(
                            f"Property '{prop}' value {value}{unit_str} is out of valid range "
                            f"({min_val}{unit_str} to {max_val}{unit_str})"
                        )

        # Validate standard-family compatibility if both are specified
        if standard and family:
            compatible_families = cls.STANDARD_FAMILY_COMPATIBILITY.get(standard)
            if compatible_families is not None and family not in compatible_families:
                raise ValueError(
                    f"Standard '{standard}' is not typically used for material family '{family}'. "
                    f"Compatible families: {', '.join(compatible_families)}"
                )

        # Validate options if provided
        if options:
            # Check allowed material families
            allowed_families = options.get("allowed_families")
            if allowed_families and family and family not in allowed_families:
                raise ValueError(
                    f"Material family '{family}' is not allowed. "
                    f"Allowed families: {', '.join(allowed_families)}"
                )

            # Check if standard is required
            require_standard = options.get("require_standard", False)
            if require_standard and not standard:
                raise ValueError("Material standard is required")

            # Check if properties are required
            require_properties = options.get("require_properties", False)
            if require_properties and not props:
                raise ValueError("Material properties are required")

            # Check required specific properties
            required_props = options.get("required_properties", [])
            if required_props:
                missing_props = [p for p in required_props if p not in props]
                if missing_props:
                    raise ValueError(f"Missing required properties: {', '.join(missing_props)}")

        return True

    @classmethod
    def default(cls) -> dict[str, Any] | None:
        """Get default value."""
        return None

    @classmethod
    def _guess_family(cls, designation: str) -> str | None:
        """Guess material family from designation."""
        designation = designation.upper()

        # Stainless steel indicators
        if any(x in designation for x in ["304", "316", "303", "201", "430"]):
            return "stainless_steel"

        # Aluminum indicators
        if designation.startswith(("6061", "7075", "2024", "5052", "AL")):
            return "aluminum"

        # Carbon/alloy steel
        if designation.startswith(("1018", "1045", "4140", "4340", "8620")):
            return "alloy_steel"

        # Tool steel
        if designation.startswith(("A2", "D2", "O1", "S7", "H13", "M2")):
            return "tool_steel"

        # Titanium
        if "TI" in designation or designation.startswith("GRADE"):
            return "titanium"

        # Brass
        if "BRASS" in designation or designation.startswith(("C26", "C27", "C36")):
            return "brass"

        return None

    @classmethod
    def format_display(cls, value: Any, options: dict[str, Any] | None = None) -> str:
        """
        Format material for display.

        Args:
            value: Material data
            options: Field options

        Returns:
            Formatted string like "AISI 304 Stainless Steel (Annealed)"
        """
        if value is None:
            return ""

        mat = cls.deserialize(value)
        if mat is None:
            return str(value)

        parts = []

        # Standard and designation
        standard = mat.get("standard")
        designation = mat.get("designation", "")

        if standard and not designation.startswith(standard):
            parts.append(f"{standard} {designation}")
        else:
            parts.append(designation)

        # Family name
        family = mat.get("family")
        if family and family in cls.FAMILIES:
            parts.append(cls.FAMILIES[family])

        # Condition
        condition = mat.get("condition")
        if condition and condition in cls.CONDITIONS:
            parts.append(f"({cls.CONDITIONS[condition]})")

        return " ".join(parts)

    @classmethod
    def format_properties(cls, value: dict[str, Any], options: dict[str, Any] | None = None) -> str:
        """
        Format material properties for display.

        Args:
            value: Material data
            options: Field options

        Returns:
            Formatted properties string
        """
        if value is None:
            return ""

        mat = cls.deserialize(value)
        if mat is None or not mat.get("properties"):
            return ""

        props = mat["properties"]
        lines = []

        # Format each property
        prop_formats = {
            "density": ("Density", "kg/m³"),
            "yield_strength": ("Yield Strength", "MPa"),
            "tensile_strength": ("Tensile Strength", "MPa"),
            "elongation": ("Elongation", "%"),
            "modulus": ("Elastic Modulus", "GPa"),
            "hardness": ("Hardness", ""),
            "thermal_conductivity": ("Thermal Conductivity", "W/m·K"),
            "melting_point": ("Melting Point", "°C"),
        }

        for key, (label, unit) in prop_formats.items():
            if key in props and props[key] is not None:
                val = props[key]
                if unit:
                    lines.append(f"{label}: {val} {unit}")
                else:
                    lines.append(f"{label}: {val}")

        return "\n".join(lines)

    @classmethod
    def get_common_materials(cls, family: str) -> list[dict[str, Any]]:
        """
        Get common materials for a family.

        Args:
            family: Material family

        Returns:
            List of common material specifications
        """
        materials = {
            "stainless_steel": [
                {"designation": "304", "standard": "AISI", "family": "stainless_steel"},
                {"designation": "316", "standard": "AISI", "family": "stainless_steel"},
                {"designation": "303", "standard": "AISI", "family": "stainless_steel"},
                {"designation": "17-4 PH", "standard": "AISI", "family": "stainless_steel"},
            ],
            "aluminum": [
                {"designation": "6061-T6", "standard": "AA", "family": "aluminum"},
                {"designation": "7075-T6", "standard": "AA", "family": "aluminum"},
                {"designation": "2024-T3", "standard": "AA", "family": "aluminum"},
                {"designation": "5052-H32", "standard": "AA", "family": "aluminum"},
            ],
            "alloy_steel": [
                {"designation": "4140", "standard": "AISI", "family": "alloy_steel"},
                {"designation": "4340", "standard": "AISI", "family": "alloy_steel"},
                {"designation": "8620", "standard": "AISI", "family": "alloy_steel"},
                {"designation": "1045", "standard": "AISI", "family": "alloy_steel"},
            ],
            "tool_steel": [
                {"designation": "A2", "standard": "AISI", "family": "tool_steel"},
                {"designation": "D2", "standard": "AISI", "family": "tool_steel"},
                {"designation": "O1", "standard": "AISI", "family": "tool_steel"},
                {"designation": "H13", "standard": "AISI", "family": "tool_steel"},
            ],
        }

        return materials.get(family, [])
