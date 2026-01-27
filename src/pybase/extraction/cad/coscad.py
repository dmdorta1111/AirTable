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

logger = logging.getLogger(__name__)


class CosCADExtractor:
    """Parser for CosCAD files via gRPC service.

    Extracts geometry, dimensions, annotations, and metadata from CosCAD files
    using the external CosCAD extraction service.

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
        """Convert CosCAD dimension to standard format."""
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

            # Normalize unit
            unit = data.get("unit", "mm")
            if unit not in ("mm", "inch", "degree"):
                unit = "mm"  # Default to mm

            return ExtractedDimension(
                value=float(data["value"]) if data.get("value") is not None else 0.0,
                unit=unit,
                tolerance_plus=data.get("tolerance_plus"),
                tolerance_minus=data.get("tolerance_minus"),
                dimension_type=data.get("dimension_type", "linear"),
                label=data.get("label"),
                bbox=data.get("bbox"),
            )
        except Exception as e:
            logger.debug("Error converting dimension: %s", e)
            return ExtractedDimension(value=0.0)

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
