"""Extraction mapper service for PyBase.

Maps extraction results (from Werk24 and other sources) to PyBase field types.
"""

from typing import Any

from pybase.fields.types.engineering.dimension import DimensionFieldHandler
from pybase.fields.types.engineering.gdt import GDTFieldHandler
from pybase.fields.types.engineering.material import MaterialFieldHandler
from pybase.fields.types.engineering.surface_finish import SurfaceFinishFieldHandler
from pybase.fields.types.engineering.thread import ThreadFieldHandler


class ExtractionMapperService:
    """Service for mapping extraction results to field types.

    Maps AI extraction results (Werk24, etc.) to standardized PyBase field formats
    for dimensions, GD&T, threads, materials, and surface finishes.

    Example:
        mapper = ExtractionMapperService()

        # Map individual items
        dimension_field = mapper.map_dimension(werk24_dimension)
        gdt_field = mapper.map_gdt(werk24_gdt)

        # Map full result
        mapped_data = mapper.map_werk24_result(extraction_result)
    """

    def _validate_dimension_value(self, value: float | None) -> float | None:
        """Validate dimension value is finite and non-negative.

        Args:
            value: Dimension value to validate

        Returns:
            Validated value (absolute value if negative) or None if invalid

        Raises:
            ValueError: If value is infinite, NaN, or otherwise invalid
        """
        if value is None:
            return None

        import math

        # Check for NaN or infinity
        if not math.isfinite(value):
            raise ValueError(
                f"Invalid dimension value: {value}. "
                "Dimensions must be finite numbers (not NaN or infinity)."
            )

        # Handle negative dimensions: take absolute value
        # Negative dimensions can occur from OCR errors or coordinate-based extraction
        # For engineering dimensions, we use the absolute value
        if value < 0:
            value = abs(value)

        return value

    def map_dimension(self, dimension_data: dict[str, Any]) -> dict[str, Any] | None:
        """Map dimension extraction to DimensionFieldHandler format.

        Args:
            dimension_data: Dimension data from extraction (Werk24Dimension or similar)

        Returns:
            Mapped dimension data suitable for DimensionFieldHandler or None

        Example input (Werk24Dimension):
            {
                "nominal_value": 10.5,
                "unit": "mm",
                "upper_deviation": 0.2,
                "lower_deviation": -0.1,
                "dimension_type": "linear",
                "tolerance_grade": "h7"
            }

        Example output:
            {
                "value": 10.5,
                "tolerance_plus": 0.2,
                "tolerance_minus": 0.1,
                "unit": "mm"
            }
        """
        if not dimension_data:
            return None

        # Handle Werk24Dimension format
        if "nominal_value" in dimension_data:
            value = self._validate_dimension_value(dimension_data.get("nominal_value"))
            if value is None:
                return None

            upper_dev = dimension_data.get("upper_deviation", 0)
            lower_dev = dimension_data.get("lower_deviation", 0)

            # Validate tolerance values too
            upper_dev = self._validate_dimension_value(upper_dev) or 0
            lower_dev = self._validate_dimension_value(lower_dev) or 0

            # Convert lower deviation to positive tolerance value
            tolerance_minus = abs(lower_dev)

            return DimensionFieldHandler.serialize(
                {
                    "value": value,
                    "tolerance_plus": upper_dev,
                    "tolerance_minus": tolerance_minus,
                    "unit": dimension_data.get("unit", "mm"),
                }
            )

        # Handle ExtractedDimension format
        if "value" in dimension_data:
            value = self._validate_dimension_value(dimension_data.get("value"))
            if value is None:
                return None

            result = dict(dimension_data)
            result["value"] = value

            # Also validate tolerance values if present
            if "tolerance_plus" in result:
                result["tolerance_plus"] = self._validate_dimension_value(
                    result["tolerance_plus"]
                ) or 0
            if "tolerance_minus" in result:
                result["tolerance_minus"] = self._validate_dimension_value(
                    result["tolerance_minus"]
                ) or 0

            return DimensionFieldHandler.serialize(result)

        return None

    def map_gdt(self, gdt_data: dict[str, Any]) -> dict[str, Any] | None:
        """Map GD&T extraction to GDTFieldHandler format.

        Args:
            gdt_data: GD&T data from extraction (Werk24GDT or similar)

        Returns:
            Mapped GD&T data suitable for GDTFieldHandler or None

        Example input (Werk24GDT):
            {
                "characteristic_type": "position",
                "tolerance_value": 0.05,
                "tolerance_unit": "mm",
                "material_condition": "MMC",
                "datums": ["A", "B", "C"],
                "composite": false
            }

        Example output:
            {
                "type": "position",
                "tolerance": 0.05,
                "diameter_zone": true,
                "material_condition": "MMC",
                "datums": ["A", "B", "C"]
            }
        """
        if not gdt_data:
            return None

        # Map characteristic type
        characteristic_type = gdt_data.get("characteristic_type", "").lower()

        # Normalize characteristic type names
        type_mapping = {
            "straightness": "straightness",
            "flatness": "flatness",
            "circularity": "circularity",
            "roundness": "circularity",
            "cylindricity": "cylindricity",
            "perpendicularity": "perpendicularity",
            "parallelism": "parallelism",
            "angularity": "angularity",
            "position": "position",
            "concentricity": "concentricity",
            "symmetry": "symmetry",
            "circular_runout": "circular_runout",
            "total_runout": "total_runout",
            "profile_line": "profile_line",
            "line_profile": "profile_line",
            "profile_surface": "profile_surface",
            "surface_profile": "profile_surface",
        }

        gdt_type = type_mapping.get(characteristic_type, characteristic_type)

        # Map material condition
        material_condition = gdt_data.get("material_condition") or "RFS"
        if material_condition:
            material_condition = material_condition.upper()
            if material_condition not in ("MMC", "LMC", "RFS"):
                material_condition = "RFS"
        else:
            material_condition = "RFS"

        # Position tolerances typically use diameter zones
        diameter_zone = gdt_type in ("position", "concentricity")

        return GDTFieldHandler.serialize(
            {
                "type": gdt_type,
                "tolerance": gdt_data.get("tolerance_value"),
                "diameter_zone": diameter_zone,
                "material_condition": material_condition,
                "datums": gdt_data.get("datums", []),
                "datum_modifiers": {},
            }
        )

    def map_material(self, material_data: dict[str, Any]) -> dict[str, Any] | None:
        """Map material extraction to MaterialFieldHandler format.

        Args:
            material_data: Material data from extraction (Werk24 or similar)

        Returns:
            Mapped material data suitable for MaterialFieldHandler or None

        Example input:
            {
                "designation": "AISI 304",
                "standard": "ASTM",
                "material_type": "stainless_steel"
            }

        Example output:
            {
                "designation": "AISI 304",
                "standard": "ASTM",
                "family": "stainless_steel",
                "condition": null,
                "properties": {}
            }
        """
        if not material_data:
            return None

        # Map material_type to family
        family = material_data.get("material_type") or material_data.get("family")

        # Normalize family names
        if family:
            family = family.lower().replace(" ", "_")

        return MaterialFieldHandler.serialize(
            {
                "designation": material_data.get("designation"),
                "standard": material_data.get("standard"),
                "family": family,
                "condition": material_data.get("condition"),
                "properties": material_data.get("properties", {}),
                "notes": material_data.get("notes"),
            }
        )

    def map_thread(self, thread_data: dict[str, Any]) -> dict[str, Any] | None:
        """Map thread extraction to ThreadFieldHandler format.

        Args:
            thread_data: Thread data from extraction (Werk24Thread or similar)

        Returns:
            Mapped thread data suitable for ThreadFieldHandler or None

        Example input (Werk24Thread):
            {
                "standard": "ISO",
                "designation": "M8x1.25",
                "nominal_diameter": 8,
                "pitch": 1.25,
                "thread_class": "6g",
                "hand": "right",
                "thread_type": "external"
            }

        Example output:
            {
                "standard": "metric",
                "size": 8,
                "pitch": 1.25,
                "class": "6g",
                "internal": false,
                "left_hand": false
            }
        """
        if not thread_data:
            return None

        # Map standard names
        standard = thread_data.get("standard", "").lower()
        standard_mapping = {
            "iso": "metric",
            "metric": "metric",
            "din": "metric",
            "un": "unc",
            "unified": "unc",
            "unc": "unc",
            "unf": "unf",
            "unef": "unef",
            "bsp": "bsp",
            "npt": "npt",
        }
        mapped_standard = standard_mapping.get(standard, "metric")

        # Determine internal/external
        thread_type = thread_data.get("thread_type", "external").lower()
        internal = thread_type in ("internal", "hole", "tapped")

        # Determine left/right hand
        hand = thread_data.get("hand", "right").lower()
        left_hand = hand in ("left", "lh", "left_hand")

        # Get size and pitch
        size = thread_data.get("nominal_diameter") or thread_data.get("size")
        pitch = thread_data.get("pitch")

        # Get thread class
        thread_class = thread_data.get("thread_class") or thread_data.get("class")

        return ThreadFieldHandler.serialize(
            {
                "standard": mapped_standard,
                "size": size,
                "pitch": pitch,
                "class": thread_class,
                "internal": internal,
                "left_hand": left_hand,
            }
        )

    def map_surface_finish(
        self, surface_finish_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Map surface finish extraction to SurfaceFinishFieldHandler format.

        Args:
            surface_finish_data: Surface finish data from extraction (Werk24 or similar)

        Returns:
            Mapped surface finish data suitable for SurfaceFinishFieldHandler or None

        Example input (Werk24SurfaceFinish):
            {
                "ra_value": 1.6,
                "unit": "μm",
                "process": "ground",
                "lay_symbol": "perpendicular"
            }

        Example output:
            {
                "parameter": "Ra",
                "value": 1.6,
                "unit": "μm",
                "process": "ground",
                "lay": "perpendicular"
            }
        """
        if not surface_finish_data:
            return None

        # Determine parameter (Ra, Rz, etc.)
        parameter = "Ra"  # Default
        value = None

        if "ra_value" in surface_finish_data:
            parameter = "Ra"
            value = surface_finish_data["ra_value"]
        elif "rz_value" in surface_finish_data:
            parameter = "Rz"
            value = surface_finish_data["rz_value"]
        elif "value" in surface_finish_data:
            parameter = surface_finish_data.get("parameter", "Ra")
            value = surface_finish_data["value"]

        # Get lay direction
        lay = surface_finish_data.get("lay_symbol") or surface_finish_data.get("lay")

        # Normalize lay names
        if lay:
            lay_mapping = {
                "perpendicular": "perpendicular",
                "⟂": "perpendicular",
                "parallel": "parallel",
                "=": "parallel",
                "crossed": "crossed",
                "x": "crossed",
                "multidirectional": "multidirectional",
                "m": "multidirectional",
                "circular": "circular",
                "c": "circular",
                "radial": "radial",
                "r": "radial",
            }
            lay = lay_mapping.get(lay.lower(), lay)

        # Get process
        process = surface_finish_data.get("process")

        return SurfaceFinishFieldHandler.serialize(
            {
                "parameter": parameter,
                "value": value,
                "unit": surface_finish_data.get("unit", "μm"),
                "process": process,
                "lay": lay,
            }
        )

    def map_werk24_result(
        self, extraction_result: dict[str, Any]
    ) -> dict[str, list[dict[str, Any]]]:
        """Map complete Werk24ExtractionResult to field formats.

        Args:
            extraction_result: Complete Werk24ExtractionResult or dict representation

        Returns:
            Dict with mapped data by field type:
            {
                "dimensions": [...],
                "gdts": [...],
                "threads": [...],
                "materials": [...],
                "surface_finishes": [...]
            }

        Example:
            mapper = ExtractionMapperService()
            result = werk24_client.extract_async("drawing.pdf")
            mapped = mapper.map_werk24_result(result.to_dict())

            # Use mapped data to populate fields
            for dim in mapped["dimensions"]:
                # Create dimension field with dim data
                pass
        """
        result = {
            "dimensions": [],
            "gdts": [],
            "threads": [],
            "materials": [],
            "surface_finishes": [],
        }

        # Map dimensions
        dimensions = extraction_result.get("dimensions", [])
        for dim in dimensions:
            mapped = self.map_dimension(dim)
            if mapped:
                result["dimensions"].append(mapped)

        # Map GD&Ts
        gdts = extraction_result.get("gdts", [])
        for gdt in gdts:
            mapped = self.map_gdt(gdt)
            if mapped:
                result["gdts"].append(mapped)

        # Map threads
        threads = extraction_result.get("threads", [])
        for thread in threads:
            mapped = self.map_thread(thread)
            if mapped:
                result["threads"].append(mapped)

        # Map materials
        materials = extraction_result.get("materials", [])
        for material in materials:
            mapped = self.map_material(material)
            if mapped:
                result["materials"].append(mapped)

        # Map surface finishes
        surface_finishes = extraction_result.get("surface_finishes", [])
        for sf in surface_finishes:
            mapped = self.map_surface_finish(sf)
            if mapped:
                result["surface_finishes"].append(mapped)

        return result

    def validate_mapped_data(
        self, mapped_data: dict[str, Any], field_type: str
    ) -> tuple[bool, str | None]:
        """Validate mapped data against field type handler.

        Args:
            mapped_data: Mapped field data
            field_type: Field type (dimension, gdt, thread, material, surface_finish)

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            mapper = ExtractionMapperService()
            mapped_dim = mapper.map_dimension(werk24_dimension)
            is_valid, error = mapper.validate_mapped_data(mapped_dim, "dimension")
            if not is_valid:
                print(f"Validation error: {error}")
        """
        handlers = {
            "dimension": DimensionFieldHandler,
            "gdt": GDTFieldHandler,
            "thread": ThreadFieldHandler,
            "material": MaterialFieldHandler,
            "surface_finish": SurfaceFinishFieldHandler,
        }

        handler = handlers.get(field_type)
        if not handler:
            return False, f"Unknown field type: {field_type}"

        try:
            handler.validate(mapped_data)
            return True, None
        except ValueError as e:
            return False, str(e)
