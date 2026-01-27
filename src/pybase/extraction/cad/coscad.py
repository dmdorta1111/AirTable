"""CosCAD file parser for PyBase.

Uses CosCAD gRPC service to extract information from CosCAD files:
- Geometry metadata (faces, edges, vertices, surfaces)
- Dimensions (linear, angular, radial, diameter with tolerances)
- GD&T symbols (geometric dimensioning and tolerancing)
- Annotations (text labels, notes, leaders)
- Title block information
- Material specifications
- File metadata
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from pybase.extraction.base import (
    CADExtractionResult,
    ExtractedDimension,
    ExtractedLayer,
    ExtractedText,
    ExtractedTitleBlock,
    GeometrySummary,
)
from pybase.extraction.cad.coscad_client import CosCADClient
from pybase.extraction.cad.coscad_grpc_stub import CosCADUnit, convert_to_base_units

logger = logging.getLogger(__name__)


class CosCADExtractor:
    """Parser for CosCAD files via gRPC service.

    Extracts geometry, dimensions, annotations, and metadata from CosCAD files
    using the external CosCAD extraction service.

    Unit Conversion:
        Uses the CosCAD unit system (CosCADUnit enum) for consistent unit handling.
        Linear dimensions are converted to millimeters (mm) or inches (inch) using
        the convert_to_base_units() function from the gRPC stub. Angular dimensions
        are kept in degrees. Supported CosCAD units: mm, inch, micrometer, centimeter,
        meter.

    Example:
        extractor = CosCADExtractor()
        result = extractor.parse("model.coscad")

        # Access dimensions
        for dim in result.dimensions:
            print(f"{dim.dimension_type}: {dim.value} {dim.unit}")

        # Access geometry summary
        print(f"Solids: {result.geometry_summary.solids}")
    """

    def __init__(
        self,
        service_host: str | None = None,
        service_port: int | None = None,
        timeout: int = 300,
        extract_geometry: bool = True,
        extract_dimensions: bool = True,
        extract_annotations: bool = True,
        extract_metadata: bool = True,
    ):
        """Initialize the CosCAD extractor.

        Args:
            service_host: CosCAD service host (default: from env or localhost).
            service_port: CosCAD service port (default: from env or 50051).
            timeout: Request timeout in seconds.
            extract_geometry: Whether to extract geometry information.
            extract_dimensions: Whether to extract dimension entities.
            extract_annotations: Whether to extract text annotations.
            extract_metadata: Whether to extract file metadata.
        """
        self.service_host = service_host
        self.service_port = service_port
        self.timeout = timeout
        self.extract_geometry = extract_geometry
        self.extract_dimensions = extract_dimensions
        self.extract_annotations = extract_annotations
        self.extract_metadata = extract_metadata

        # Initialize client (will be created on first use)
        self._client: CosCADClient | None = None

    @property
    def client(self) -> CosCADClient:
        """Get or create the CosCAD client."""
        if self._client is None:
            self._client = CosCADClient(
                host=self.service_host,
                port=self.service_port,
                timeout=self.timeout,
            )
        return self._client

    def parse(
        self,
        source: str | Path,
        extract_geometry: bool | None = None,
        extract_dimensions: bool | None = None,
        extract_annotations: bool | None = None,
        extract_metadata: bool | None = None,
    ) -> CADExtractionResult:
        """Parse a CosCAD file and extract information.

        Args:
            source: File path to the CosCAD file.
            extract_geometry: Whether to extract geometry information.
            extract_dimensions: Whether to extract dimension entities.
            extract_annotations: Whether to extract text annotations.
            extract_metadata: Whether to extract file metadata.

        Returns:
            CADExtractionResult with extracted data.
        """
        source_file = str(source)

        # Use instance defaults if not specified
        if extract_geometry is None:
            extract_geometry = self.extract_geometry
        if extract_dimensions is None:
            extract_dimensions = self.extract_dimensions
        if extract_annotations is None:
            extract_annotations = self.extract_annotations
        if extract_metadata is None:
            extract_metadata = self.extract_metadata

        result = CADExtractionResult(
            source_file=source_file,
            source_type="coscad",
        )

        try:
            # Extract metadata
            if extract_metadata:
                try:
                    metadata_response = self.client.extract_metadata(source_file)
                    if metadata_response.metadata:
                        result.metadata = metadata_response.metadata.to_dict()
                        # Extract title block if available
                        if metadata_response.title_block:
                            result.title_block = self._convert_title_block(
                                metadata_response.title_block
                            )
                except Exception as e:
                    logger.warning("Error extracting metadata: %s", e)
                    result.errors.append(f"Metadata extraction error: {e}")

            # Extract geometry
            if extract_geometry:
                try:
                    geometry_response = self.client.extract_geometry(source_file)
                    if geometry_response.geometry:
                        result.layers = self._convert_geometry_to_layers(
                            geometry_response.geometry
                        )
                        result.geometry_summary = self._convert_geometry_summary(
                            geometry_response.geometry
                        )
                except Exception as e:
                    logger.warning("Error extracting geometry: %s", e)
                    result.errors.append(f"Geometry extraction error: {e}")

            # Extract dimensions
            if extract_dimensions:
                try:
                    dimensions_response = self.client.extract_dimensions(source_file)
                    if dimensions_response.dimensions:
                        result.dimensions = [
                            self._convert_dimension(dim)
                            for dim in dimensions_response.dimensions
                        ]
                except Exception as e:
                    logger.warning("Error extracting dimensions: %s", e)
                    result.errors.append(f"Dimensions extraction error: {e}")

            # Extract annotations
            if extract_annotations:
                try:
                    annotations_response = self.client.extract_annotations(source_file)
                    if annotations_response.annotations:
                        result.text_blocks = [
                            self._convert_annotation(ann)
                            for ann in annotations_response.annotations
                        ]
                except Exception as e:
                    logger.warning("Error extracting annotations: %s", e)
                    result.errors.append(f"Annotations extraction error: {e}")

        except Exception as e:
            result.errors.append(f"Unexpected error: {e}")
            logger.exception("Unexpected error parsing CosCAD: %s", source_file)

        return result

    def _convert_title_block(self, title_block: Any) -> ExtractedTitleBlock:
        """Convert CosCAD title block to standard format."""
        try:
            # Handle both dataclass and dict formats
            if hasattr(title_block, "to_dict"):
                data = title_block.to_dict()
            elif isinstance(title_block, dict):
                data = title_block
            else:
                data = {k: getattr(title_block, k, None) for k in [
                    "drawing_number", "title", "revision", "date",
                    "author", "company", "scale", "sheet", "material", "finish"
                ]}

            return ExtractedTitleBlock(
                drawing_number=data.get("drawing_number"),
                title=data.get("title"),
                revision=data.get("revision"),
                date=data.get("date"),
                author=data.get("author"),
                company=data.get("company"),
                scale=data.get("scale"),
                sheet=data.get("sheet"),
                material=data.get("material"),
                finish=data.get("finish"),
            )
        except Exception as e:
            logger.debug("Error converting title block: %s", e)
            return ExtractedTitleBlock()

    def _convert_dimension(self, dimension: Any) -> ExtractedDimension:
        """Convert CosCAD dimension to standard format.

        Handles unit conversion from CosCAD internal units to standard units (mm/inch/degree)
        and parses tolerance information from various formats.
        """
        try:
            # Handle both dataclass and dict formats
            if hasattr(dimension, "to_dict"):
                data = dimension.to_dict()
            elif isinstance(dimension, dict):
                data = dimension
            else:
                data = {
                    "value": getattr(dimension, "value", None),
                    "unit": getattr(dimension, "unit", "mm"),
                    "tolerance_plus": getattr(dimension, "tolerance_plus", None),
                    "tolerance_minus": getattr(dimension, "tolerance_minus", None),
                    "dimension_type": getattr(dimension, "dimension_type", "linear"),
                    "label": getattr(dimension, "label", None),
                    "bbox": getattr(dimension, "bbox", None),
                }

            # Get raw value and unit
            raw_value = data.get("value")
            raw_unit = data.get("unit", "mm")
            dimension_type = data.get("dimension_type", "linear")

            # Skip dimensions with invalid values
            if raw_value is None:
                logger.debug("Skipping dimension with missing value")
                return ExtractedDimension(value=0.0)

            # Convert value to float and apply unit conversion
            try:
                value = float(raw_value)
            except (ValueError, TypeError):
                logger.debug("Could not convert dimension value to float: %s", raw_value)
                return ExtractedDimension(value=0.0)

            # Determine if this is an angular dimension
            is_angular = dimension_type in ("angular", "angular3point")

            # Normalize and convert unit
            unit, value = self._normalize_unit(raw_unit, value, is_angular)

            # Extract and convert tolerances
            tolerance_plus = data.get("tolerance_plus")
            tolerance_minus = data.get("tolerance_minus")

            # If tolerances are not explicitly provided, try to parse from label
            label = data.get("label")
            if label and (tolerance_plus is None or tolerance_minus is None):
                parsed_tolerance = self._parse_tolerance_from_label(label, raw_unit, is_angular)
                if parsed_tolerance:
                    if tolerance_plus is None:
                        tolerance_plus = parsed_tolerance[0]
                    if tolerance_minus is None:
                        tolerance_minus = parsed_tolerance[1]

            # Convert tolerance values to standard units
            if tolerance_plus is not None:
                tolerance_plus = self._convert_tolerance_value(tolerance_plus, raw_unit, is_angular)
            if tolerance_minus is not None:
                tolerance_minus = self._convert_tolerance_value(tolerance_minus, raw_unit, is_angular)

            return ExtractedDimension(
                value=value,
                unit=unit,
                tolerance_plus=tolerance_plus,
                tolerance_minus=tolerance_minus,
                dimension_type=dimension_type,
                label=label,
                bbox=data.get("bbox"),
            )
        except Exception as e:
            logger.debug("Error converting dimension: %s", e)
            return ExtractedDimension(value=0.0)

    def _normalize_unit(self, raw_unit: str, value: float, is_angular: bool) -> tuple[str, float]:
        """Normalize CosCAD unit to standard unit (mm/inch/degree) and convert value.

        Uses CosCADUnit enum and convert_to_base_units() function for consistency
        with the gRPC service's unit system.

        Args:
            raw_unit: The unit string from CosCAD.
            value: The value in the original unit.
            is_angular: Whether this is an angular dimension.

        Returns:
            Tuple of (standard_unit, converted_value).
        """
        # Normalize unit string (lowercase, strip whitespace)
        unit_key = raw_unit.lower().strip() if raw_unit else "mm"

        # For angular dimensions, convert to degrees
        if is_angular:
            if unit_key in ("deg", "degree", "degrees"):
                return ("degree", value)
            elif unit_key in ("rad", "radian", "radians"):
                # Convert radians to degrees
                return ("degree", value * 57.2958)
            else:
                # Assume degrees for angular dimensions
                return ("degree", value)

        # For linear dimensions, use CosCAD unit system
        # Map unit string to CosCADUnit enum
        unit_map = {
            "mm": CosCADUnit.MILLIMETER,
            "millimeter": CosCADUnit.MILLIMETER,
            "millimeters": CosCADUnit.MILLIMETER,
            "inch": CosCADUnit.INCH,
            "in": CosCADUnit.INCH,
            "inches": CosCADUnit.INCH,
            "um": CosCADUnit.MICROMETER,
            "micrometer": CosCADUnit.MICROMETER,
            "micrometers": CosCADUnit.MICROMETER,
            "cm": CosCADUnit.CENTIMETER,
            "centimeter": CosCADUnit.CENTIMETER,
            "centimeters": CosCADUnit.CENTIMETER,
            "m": CosCADUnit.METER,
            "meter": CosCADUnit.METER,
            "meters": CosCADUnit.METER,
        }

        # Get CosCADUnit enum value
        coscad_unit = unit_map.get(unit_key, CosCADUnit.MILLIMETER)

        # Convert to base units (millimeters) using gRPC stub function
        value_mm = convert_to_base_units(value, coscad_unit)

        # Determine standard output unit
        # Use mm for most engineering drawings (international standard)
        # Use inch only if original unit was explicitly inch
        if coscad_unit == CosCADUnit.INCH:
            # Keep as inch with original value (no conversion)
            return ("inch", value)
        else:
            # Convert all other units to mm
            return ("mm", value_mm)

    def _convert_tolerance_value(
        self,
        tolerance: Any,
        raw_unit: str,
        is_angular: bool
    ) -> float | None:
        """Convert tolerance value to standard units using CosCAD unit system.

        Args:
            tolerance: The tolerance value (can be string, float, or dict).
            raw_unit: The unit of the parent dimension.
            is_angular: Whether this is an angular dimension.

        Returns:
            Converted tolerance value in standard units (mm/inch/degree), or None if conversion fails.
        """
        if tolerance is None:
            return None

        try:
            # Handle dict format (e.g., {"value": 0.1, "unit": "mm"})
            if isinstance(tolerance, dict):
                tol_value = tolerance.get("value")
                tol_unit = tolerance.get("unit", raw_unit)
                if tol_value is not None:
                    value = float(tol_value)
                    unit, converted = self._normalize_unit(tol_unit, value, is_angular)
                    return converted

            # Handle string format (e.g., "0.1" or "0.1mm")
            if isinstance(tolerance, str):
                # Extract numeric value
                match = re.search(r"[-+]?\d*\.?\d+", tolerance)
                if match:
                    value = float(match.group())
                    unit, converted = self._normalize_unit(raw_unit, value, is_angular)
                    return converted
                return None

            # Handle numeric value (assume same unit as dimension)
            value = float(tolerance)
            unit, converted = self._normalize_unit(raw_unit, value, is_angular)
            return converted

        except (ValueError, TypeError):
            logger.debug("Could not convert tolerance value: %s", tolerance)
            return None

    def _parse_tolerance_from_label(
        self,
        label: str,
        raw_unit: str,
        is_angular: bool
    ) -> tuple[float, float] | None:
        """Parse tolerance information from dimension label text.

        Supports formats like:
        - "10 ±0.1" (symmetric tolerance)
        - "10 +0.1/-0.05" (asymmetric tolerance)
        - "10±0.1"
        - "10 +0.1 -0.05"

        Args:
            label: The dimension label text.
            raw_unit: The unit of the dimension.
            is_angular: Whether this is an angular dimension.

        Returns:
            Tuple of (tolerance_plus, tolerance_minus) or None if no tolerance found.
        """
        if not label:
            return None

        try:
            # Pattern 1: Symmetric tolerance with ± symbol
            symmetric = re.search(r"±\s*([\d.]+)", label)
            if symmetric:
                tol_value = float(symmetric.group(1))
                converted = self._convert_tolerance_value(tol_value, raw_unit, is_angular)
                if converted is not None:
                    return (converted, converted)

            # Pattern 2: Asymmetric tolerance +tol/-tol
            asymmetric = re.search(r"\+\s*([\d.]+)\s*/\s*-\s*([\d.]+)", label)
            if asymmetric:
                tol_plus = float(asymmetric.group(1))
                tol_minus = float(asymmetric.group(2))
                converted_plus = self._convert_tolerance_value(tol_plus, raw_unit, is_angular)
                converted_minus = self._convert_tolerance_value(tol_minus, raw_unit, is_angular)
                if converted_plus is not None and converted_minus is not None:
                    return (converted_plus, converted_minus)

            # Pattern 3: Space-separated +tol -tol
            separated = re.search(r"\+\s*([\d.]+)\s+-\s*([\d.]+)", label)
            if separated:
                tol_plus = float(separated.group(1))
                tol_minus = float(separated.group(2))
                converted_plus = self._convert_tolerance_value(tol_plus, raw_unit, is_angular)
                converted_minus = self._convert_tolerance_value(tol_minus, raw_unit, is_angular)
                if converted_plus is not None and converted_minus is not None:
                    return (converted_plus, converted_minus)

        except (ValueError, TypeError, AttributeError):
            logger.debug("Could not parse tolerance from label: %s", label)

        return None

    def _convert_annotation(self, annotation: Any) -> ExtractedText:
        """Convert CosCAD annotation to standard format."""
        try:
            # Handle both dataclass and dict formats
            if hasattr(annotation, "to_dict"):
                data = annotation.to_dict()
            elif isinstance(annotation, dict):
                data = annotation
            else:
                data = {
                    "text": getattr(annotation, "text", ""),
                    "bbox": getattr(annotation, "bbox", None),
                    "font_size": getattr(annotation, "font_size", None),
                }

            return ExtractedText(
                text=data.get("text", ""),
                bbox=data.get("bbox"),
                font_size=data.get("font_size"),
            )
        except Exception as e:
            logger.debug("Error converting annotation: %s", e)
            return ExtractedText(text="")

    def _convert_geometry_to_layers(self, geometry: Any) -> list[ExtractedLayer]:
        """Convert geometry data to layer-like structure."""
        layers: list[ExtractedLayer] = []

        try:
            # Handle both dataclass and dict formats
            if hasattr(geometry, "to_dict"):
                data = geometry.to_dict()
            elif isinstance(geometry, dict):
                data = geometry
            else:
                data = {
                    "num_faces": getattr(geometry, "num_faces", 0),
                    "num_edges": getattr(geometry, "num_edges", 0),
                    "num_vertices": getattr(geometry, "num_vertices", 0),
                    "num_surfaces": getattr(geometry, "num_surfaces", 0),
                    "num_solids": getattr(geometry, "num_solids", 0),
                }

            # Create layers for different geometry types
            if data.get("num_solids", 0) > 0:
                layers.append(
                    ExtractedLayer(
                        name="Solids",
                        entity_count=data["num_solids"],
                        is_on=True,
                    )
                )

            if data.get("num_surfaces", 0) > 0:
                layers.append(
                    ExtractedLayer(
                        name="Surfaces",
                        entity_count=data["num_surfaces"],
                        is_on=True,
                    )
                )

            if data.get("num_faces", 0) > 0:
                layers.append(
                    ExtractedLayer(
                        name="Faces",
                        entity_count=data["num_faces"],
                        is_on=True,
                    )
                )

            if data.get("num_edges", 0) > 0:
                layers.append(
                    ExtractedLayer(
                        name="Edges",
                        entity_count=data["num_edges"],
                        is_on=True,
                    )
                )

            if data.get("num_vertices", 0) > 0:
                layers.append(
                    ExtractedLayer(
                        name="Vertices",
                        entity_count=data["num_vertices"],
                        is_on=True,
                    )
                )

        except Exception as e:
            logger.warning("Error converting geometry to layers: %s", e)

        return layers

    def _convert_geometry_summary(self, geometry: Any) -> GeometrySummary:
        """Convert geometry data to geometry summary."""
        try:
            # Handle both dataclass and dict formats
            if hasattr(geometry, "to_dict"):
                data = geometry.to_dict()
            elif isinstance(geometry, dict):
                data = geometry
            else:
                data = {
                    "num_faces": getattr(geometry, "num_faces", 0),
                    "num_edges": getattr(geometry, "num_edges", 0),
                    "num_vertices": getattr(geometry, "num_vertices", 0),
                    "num_surfaces": getattr(geometry, "num_surfaces", 0),
                    "num_solids": getattr(geometry, "num_solids", 0),
                }

            total_entities = (
                data.get("num_faces", 0)
                + data.get("num_edges", 0)
                + data.get("num_vertices", 0)
                + data.get("num_surfaces", 0)
                + data.get("num_solids", 0)
            )

            return GeometrySummary(
                solids=data.get("num_solids", 0),
                total_entities=total_entities,
            )
        except Exception as e:
            logger.warning("Error converting geometry summary: %s", e)
            return GeometrySummary()
