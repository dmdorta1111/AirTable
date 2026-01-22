"""STEP file parser for PyBase.

Uses build123d/OCP (OpenCascade Python) or cadquery to extract information from STEP files:
- Assembly structure (parts, sub-assemblies)
- Part metadata (names, colors, materials)
- Geometry information (bounding boxes, volumes, surface areas)
- Shape types (solids, shells, faces, edges)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pybase.extraction.base import (
    CADExtractionResult,
    ExtractedLayer,
    GeometrySummary,
)

logger = logging.getLogger(__name__)

# Try to import OCP/build123d or cadquery
OCP_AVAILABLE = False
CADQUERY_AVAILABLE = False

try:
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.TopAbs import (
        TopAbs_SOLID,
        TopAbs_SHELL,
        TopAbs_FACE,
        TopAbs_EDGE,
        TopAbs_VERTEX,
        TopAbs_COMPOUND,
    )
    from OCP.TopExp import TopExp_Explorer
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib_AddClose
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import (
        BRepGProp_SurfaceProperties,
        BRepGProp_VolumeProperties,
    )
    from OCP.TopoDS import TopoDS_Shape

    OCP_AVAILABLE = True
except ImportError:
    pass

if not OCP_AVAILABLE:
    try:
        import cadquery as cq
        from cadquery import importers

        CADQUERY_AVAILABLE = True
    except ImportError:
        pass


@dataclass
class STEPPart:
    """Represents a part extracted from a STEP file."""

    name: str | None = None
    part_id: str | None = None
    shape_type: str = "unknown"
    volume: float | None = None
    surface_area: float | None = None
    center_of_mass: tuple[float, float, float] | None = None
    bbox: tuple[float, float, float, float, float, float] | None = None  # min/max x,y,z
    color: tuple[float, float, float] | None = None  # RGB 0-1
    material: str | None = None
    num_faces: int = 0
    num_edges: int = 0
    num_vertices: int = 0
    children: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "part_id": self.part_id,
            "shape_type": self.shape_type,
            "volume": self.volume,
            "surface_area": self.surface_area,
            "center_of_mass": self.center_of_mass,
            "bbox": self.bbox,
            "color": self.color,
            "material": self.material,
            "num_faces": self.num_faces,
            "num_edges": self.num_edges,
            "num_vertices": self.num_vertices,
            "children": self.children,
            "properties": self.properties,
        }


@dataclass
class STEPAssembly:
    """Represents an assembly structure from a STEP file."""

    name: str | None = None
    parts: list[STEPPart] = field(default_factory=list)
    total_parts: int = 0
    root_parts: list[str] = field(default_factory=list)  # Top-level part names

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "parts": [p.to_dict() for p in self.parts],
            "total_parts": self.total_parts,
            "root_parts": self.root_parts,
        }


@dataclass
class STEPExtractionResult(CADExtractionResult):
    """Extended result for STEP extraction."""

    assembly: STEPAssembly | None = None
    shape_counts: dict[str, int] = field(default_factory=dict)
    total_volume: float | None = None
    total_surface_area: float | None = None
    overall_bbox: tuple[float, float, float, float, float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "assembly": self.assembly.to_dict() if self.assembly else None,
                "shape_counts": self.shape_counts,
                "total_volume": self.total_volume,
                "total_surface_area": self.total_surface_area,
                "overall_bbox": self.overall_bbox,
            }
        )
        return base


class STEPParser:
    """Parser for STEP (Standard for the Exchange of Product Data) files.

    Extracts assembly structure, part geometry, and metadata from STEP files.
    Supports both AP203 and AP214 STEP formats.

    Example:
        parser = STEPParser()
        result = parser.parse("assembly.step")

        # Access assembly structure
        for part in result.assembly.parts:
            print(f"{part.name}: {part.volume} mm³")

        # Access overall geometry
        print(f"Total volume: {result.total_volume}")
    """

    def __init__(
        self,
        compute_mass_properties: bool = True,
        max_parts: int = 10000,
    ):
        """Initialize the STEP parser.

        Args:
            compute_mass_properties: Whether to compute volume/surface area (slower).
            max_parts: Maximum number of parts to extract.
        """
        self.compute_mass_properties = compute_mass_properties
        self.max_parts = max_parts

        if not OCP_AVAILABLE and not CADQUERY_AVAILABLE:
            raise ImportError(
                "build123d/OCP or cadquery is required for STEP parsing. "
                "Install with: pip install build123d  or  pip install cadquery"
            )

    def parse(self, source: str | Path) -> STEPExtractionResult:
        """Parse a STEP file and extract information.

        Args:
            source: File path to the STEP file.

        Returns:
            STEPExtractionResult with extracted assembly, parts, and geometry.
        """
        source_file = str(source)

        result = STEPExtractionResult(
            source_file=source_file,
            source_type="step",
        )

        try:
            if OCP_AVAILABLE:
                self._parse_with_ocp(source_file, result)
            elif CADQUERY_AVAILABLE:
                self._parse_with_cadquery(source_file, result)

        except Exception as e:
            result.errors.append(f"STEP parsing error: {e}")
            logger.exception("Error parsing STEP: %s", source_file)

        return result

    def _parse_with_ocp(self, source_file: str, result: STEPExtractionResult) -> None:
        """Parse STEP file using OCP (OpenCascade Python)."""
        # Read the STEP file
        reader = STEPControl_Reader()
        status = reader.ReadFile(source_file)

        if status != IFSelect_RetDone:
            result.errors.append(f"Failed to read STEP file: status {status}")
            return

        # Transfer to shape
        reader.TransferRoots()
        shape = reader.OneShape()

        if shape.IsNull():
            result.errors.append("No valid shape found in STEP file")
            return

        # Extract metadata
        try:
            result.metadata = self._extract_ocp_metadata(reader)
        except Exception as e:
            logger.warning("Error extracting metadata: %s", e)
            result.metadata = {"parser": "OCP", "format": "STEP"}

        # Count shape types
        try:
            result.shape_counts = self._count_shapes_ocp(shape)
        except Exception as e:
            logger.warning("Error counting shapes: %s", e)
            result.shape_counts = {}

        # Create assembly structure
        try:
            result.assembly = self._extract_assembly_ocp(shape)
        except Exception as e:
            logger.error("Error extracting assembly: %s", e)
            result.errors.append(f"Assembly extraction error: {e}")
            result.assembly = STEPAssembly()

        # Calculate overall bounding box
        try:
            result.overall_bbox = self._get_bbox_ocp(shape)
        except Exception as e:
            logger.warning("Error calculating overall bbox: %s", e)
            result.overall_bbox = None

        # Calculate total volume and surface area
        if self.compute_mass_properties:
            try:
                result.total_volume = self._get_volume_ocp(shape)
            except Exception as e:
                logger.warning("Error calculating total volume: %s", e)
                result.total_volume = None

            try:
                result.total_surface_area = self._get_surface_area_ocp(shape)
            except Exception as e:
                logger.warning("Error calculating total surface area: %s", e)
                result.total_surface_area = None

        # Convert to layers (by shape type)
        try:
            result.layers = self._shapes_to_layers(result.shape_counts)
        except Exception as e:
            logger.warning("Error creating layers: %s", e)
            result.layers = []

        # Geometry summary
        try:
            result.geometry_summary = GeometrySummary(
                solids=result.shape_counts.get("SOLID", 0),
                meshes=result.shape_counts.get("SHELL", 0),
                total_entities=sum(result.shape_counts.values()),
            )
        except Exception as e:
            logger.warning("Error creating geometry summary: %s", e)
            result.geometry_summary = GeometrySummary(
                solids=0,
                meshes=0,
                total_entities=0,
            )

    def _parse_with_cadquery(self, source_file: str, result: STEPExtractionResult) -> None:
        """Parse STEP file using CadQuery."""
        # Import the STEP file
        model = importers.importStep(source_file)

        if model is None:
            result.errors.append("Failed to import STEP file")
            return

        # Extract metadata
        result.metadata = {
            "parser": "cadquery",
            "format": "STEP",
        }

        # Create assembly from compound
        result.assembly = STEPAssembly(name=Path(source_file).stem)

        # Process the model
        try:
            # If it's a Workplane, get the solid(s)
            if hasattr(model, "val"):
                shape = model.val()
            else:
                shape = model

            # Count solids
            if hasattr(shape, "Solids"):
                solids = shape.Solids()
                result.shape_counts["SOLID"] = len(solids) if solids else 0

                for i, solid in enumerate(solids):
                    try:
                        part = STEPPart(
                            name=f"Part_{i + 1}",
                            part_id=str(i + 1),
                            shape_type="SOLID",
                        )

                        # Get bounding box (with error handling)
                        try:
                            bbox = solid.BoundingBox()
                            if bbox is not None:
                                part.bbox = (
                                    bbox.xmin,
                                    bbox.ymin,
                                    bbox.zmin,
                                    bbox.xmax,
                                    bbox.ymax,
                                    bbox.zmax,
                                )
                        except Exception as e:
                            logger.debug("Error getting bbox for part %d: %s", i + 1, e)
                            part.bbox = None

                        # Get face/edge counts (with error handling)
                        try:
                            if hasattr(solid, "Faces"):
                                faces = solid.Faces()
                                part.num_faces = len(faces) if faces else 0
                        except Exception as e:
                            logger.debug("Error counting faces for part %d: %s", i + 1, e)
                            part.num_faces = 0

                        try:
                            if hasattr(solid, "Edges"):
                                edges = solid.Edges()
                                part.num_edges = len(edges) if edges else 0
                        except Exception as e:
                            logger.debug("Error counting edges for part %d: %s", i + 1, e)
                            part.num_edges = 0

                        try:
                            if hasattr(solid, "Vertices"):
                                vertices = solid.Vertices()
                                part.num_vertices = len(vertices) if vertices else 0
                        except Exception as e:
                            logger.debug("Error counting vertices for part %d: %s", i + 1, e)
                            part.num_vertices = 0

                        # Get mass properties if enabled (with error handling)
                        if self.compute_mass_properties:
                            try:
                                # CadQuery may have methods for volume/area
                                if hasattr(solid, "Volume"):
                                    vol = solid.Volume()
                                    part.volume = vol if vol is not None and vol > 0 else None
                            except Exception as e:
                                logger.debug("Error getting volume for part %d: %s", i + 1, e)
                                part.volume = None

                        result.assembly.parts.append(part)

                    except Exception as e:
                        logger.warning("Error processing solid %d: %s", i + 1, e)
                        # Continue processing other solids

                result.assembly.total_parts = len(result.assembly.parts)

                # Update root_parts list with part names
                if result.assembly.parts:
                    result.assembly.root_parts = [
                        part.name for part in result.assembly.parts if part.name
                    ]

            # Get overall bounding box (with error handling and validation)
            try:
                if hasattr(shape, "BoundingBox"):
                    bbox = shape.BoundingBox()
                    if bbox is not None:
                        # Validate bbox values before assignment
                        xmin, ymin, zmin = bbox.xmin, bbox.ymin, bbox.zmin
                        xmax, ymax, zmax = bbox.xmax, bbox.ymax, bbox.zmax

                        if all(isinstance(v, (int, float)) for v in [xmin, ymin, zmin, xmax, ymax, zmax]):
                            if xmax >= xmin and ymax >= ymin and zmax >= zmin:
                                result.overall_bbox = (xmin, ymin, zmin, xmax, ymax, zmax)
                            else:
                                logger.debug("Invalid overall bbox: max values less than min values")
                        else:
                            logger.debug("Invalid overall bbox: non-numeric values")
            except Exception as e:
                logger.debug("Error getting overall bounding box: %s", e)
                result.overall_bbox = None

            # Calculate total volume and surface area from parts if enabled
            if self.compute_mass_properties and result.assembly and result.assembly.parts:
                try:
                    volumes = [p.volume for p in result.assembly.parts if p.volume is not None and p.volume > 0]
                    if volumes:
                        result.total_volume = sum(volumes)
                except Exception as e:
                    logger.debug("Error calculating total volume: %s", e)
                    result.total_volume = None

                try:
                    areas = [p.surface_area for p in result.assembly.parts if p.surface_area is not None and p.surface_area > 0]
                    if areas:
                        result.total_surface_area = sum(areas)
                except Exception as e:
                    logger.debug("Error calculating total surface area: %s", e)
                    result.total_surface_area = None

        except Exception as e:
            result.warnings.append(f"CadQuery processing warning: {e}")
            logger.warning("CadQuery processing error: %s", e)

        # Convert to layers (with error handling)
        try:
            result.layers = self._shapes_to_layers(result.shape_counts)
        except Exception as e:
            logger.warning("Error creating layers: %s", e)
            result.layers = []

        # Geometry summary (with error handling)
        try:
            result.geometry_summary = GeometrySummary(
                solids=result.shape_counts.get("SOLID", 0),
                total_entities=sum(result.shape_counts.values()) if result.shape_counts else 0,
            )
        except Exception as e:
            logger.warning("Error creating geometry summary: %s", e)
            result.geometry_summary = GeometrySummary(
                solids=0,
                total_entities=0,
            )

    def _extract_ocp_metadata(self, reader: Any) -> dict[str, Any]:
        """Extract metadata from STEP reader."""
        metadata: dict[str, Any] = {
            "parser": "OCP",
            "format": "STEP",
        }

        try:
            # Get number of roots
            metadata["num_roots"] = reader.NbRootsForTransfer()

            # Get transfer status
            metadata["shapes_transferred"] = reader.NbShapes()

        except Exception as e:
            logger.debug("Error extracting OCP metadata: %s", e)

        return metadata

    def _count_shapes_ocp(self, shape: Any) -> dict[str, int]:
        """Count shape types in the model."""
        counts: dict[str, int] = {}

        if shape is None or shape.IsNull():
            return counts

        shape_types = [
            (TopAbs_COMPOUND, "COMPOUND"),
            (TopAbs_SOLID, "SOLID"),
            (TopAbs_SHELL, "SHELL"),
            (TopAbs_FACE, "FACE"),
            (TopAbs_EDGE, "EDGE"),
            (TopAbs_VERTEX, "VERTEX"),
        ]

        for shape_type, name in shape_types:
            try:
                explorer = TopExp_Explorer(shape, shape_type)
                count = 0
                while explorer.More():
                    count += 1
                    explorer.Next()
                if count > 0:
                    counts[name] = count
            except Exception as e:
                logger.debug("Error counting %s shapes: %s", name, e)
                # Continue with other shape types

        return counts

    def _extract_assembly_ocp(self, shape: Any) -> STEPAssembly:
        """Extract assembly structure from OCP shape."""
        assembly = STEPAssembly()
        parts: list[STEPPart] = []

        # Extract solids as parts
        explorer = TopExp_Explorer(shape, TopAbs_SOLID)
        part_num = 0

        while explorer.More() and part_num < self.max_parts:
            try:
                solid = explorer.Current()

                part = STEPPart(
                    name=f"Solid_{part_num + 1}",
                    part_id=str(part_num + 1),
                    shape_type="SOLID",
                )

                # Get bounding box (individual error handling)
                try:
                    part.bbox = self._get_bbox_ocp(solid)
                except Exception as e:
                    logger.debug("Error getting bbox for part %d: %s", part_num + 1, e)
                    part.bbox = None

                # Get mass properties (individual error handling)
                if self.compute_mass_properties:
                    try:
                        part.volume = self._get_volume_ocp(solid)
                    except Exception as e:
                        logger.debug("Error getting volume for part %d: %s", part_num + 1, e)
                        part.volume = None

                    try:
                        part.surface_area = self._get_surface_area_ocp(solid)
                    except Exception as e:
                        logger.debug("Error getting surface area for part %d: %s", part_num + 1, e)
                        part.surface_area = None

                    try:
                        part.center_of_mass = self._get_center_of_mass_ocp(solid)
                    except Exception as e:
                        logger.debug("Error getting center of mass for part %d: %s", part_num + 1, e)
                        part.center_of_mass = None

                # Count sub-shapes (individual error handling)
                try:
                    part.num_faces = self._count_subshapes_ocp(solid, TopAbs_FACE)
                except Exception as e:
                    logger.debug("Error counting faces for part %d: %s", part_num + 1, e)
                    part.num_faces = 0

                try:
                    part.num_edges = self._count_subshapes_ocp(solid, TopAbs_EDGE)
                except Exception as e:
                    logger.debug("Error counting edges for part %d: %s", part_num + 1, e)
                    part.num_edges = 0

                try:
                    part.num_vertices = self._count_subshapes_ocp(solid, TopAbs_VERTEX)
                except Exception as e:
                    logger.debug("Error counting vertices for part %d: %s", part_num + 1, e)
                    part.num_vertices = 0

                parts.append(part)
                if part.name:
                    assembly.root_parts.append(part.name)

                part_num += 1

            except Exception as e:
                logger.warning("Error extracting part %d: %s", part_num + 1, e)
                part_num += 1  # Continue to next part

            explorer.Next()

        assembly.parts = parts
        assembly.total_parts = len(parts)

        return assembly

    def _count_subshapes_ocp(self, shape: Any, shape_type: Any) -> int:
        """Count sub-shapes of a given type."""
        try:
            if shape is None or shape.IsNull():
                return 0

            explorer = TopExp_Explorer(shape, shape_type)
            count = 0
            while explorer.More():
                count += 1
                explorer.Next()
            return count
        except Exception as e:
            logger.debug("Error counting subshapes: %s", e)
            return 0

    def _get_bbox_ocp(self, shape: Any) -> tuple[float, float, float, float, float, float] | None:
        """Get bounding box of a shape."""
        try:
            if shape is None or shape.IsNull():
                return None

            bbox = Bnd_Box()
            BRepBndLib_AddClose(shape, bbox)

            if bbox.IsVoid():
                return None

            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

            # Validate bbox values
            if not all(isinstance(v, (int, float)) for v in [xmin, ymin, zmin, xmax, ymax, zmax]):
                logger.debug("Invalid bbox values: non-numeric values detected")
                return None

            # Ensure max >= min for each dimension
            if xmax < xmin or ymax < ymin or zmax < zmin:
                logger.debug("Invalid bbox: max values less than min values")
                return None

            return (xmin, ymin, zmin, xmax, ymax, zmax)

        except Exception as e:
            logger.debug("Error getting bbox: %s", e)
            return None

    def _get_volume_ocp(self, shape: Any) -> float | None:
        """Calculate volume of a shape."""
        try:
            if shape is None or shape.IsNull():
                return None

            props = GProp_GProps()
            BRepGProp_VolumeProperties(shape, props)
            volume = props.Mass()

            # Validate volume
            if volume is None:
                return None

            if not isinstance(volume, (int, float)):
                logger.debug("Invalid volume: non-numeric value")
                return None

            # Volume should be non-negative
            if volume < 0:
                logger.debug("Invalid volume: negative value %f", volume)
                return None

            # Return None for zero or very small volumes (likely invalid)
            if abs(volume) < 1e-10:
                return None

            return float(volume)

        except Exception as e:
            logger.debug("Error calculating volume: %s", e)
            return None

    def _get_surface_area_ocp(self, shape: Any) -> float | None:
        """Calculate surface area of a shape."""
        try:
            if shape is None or shape.IsNull():
                return None

            props = GProp_GProps()
            BRepGProp_SurfaceProperties(shape, props)
            area = props.Mass()

            # Validate surface area
            if area is None:
                return None

            if not isinstance(area, (int, float)):
                logger.debug("Invalid surface area: non-numeric value")
                return None

            # Surface area should be non-negative
            if area < 0:
                logger.debug("Invalid surface area: negative value %f", area)
                return None

            # Return None for zero or very small areas (likely invalid)
            if abs(area) < 1e-10:
                return None

            return float(area)

        except Exception as e:
            logger.debug("Error calculating surface area: %s", e)
            return None

    def _get_center_of_mass_ocp(self, shape: Any) -> tuple[float, float, float] | None:
        """Calculate center of mass of a shape."""
        try:
            if shape is None or shape.IsNull():
                return None

            props = GProp_GProps()
            BRepGProp_VolumeProperties(shape, props)
            com = props.CentreOfMass()

            if com is None:
                return None

            x, y, z = com.X(), com.Y(), com.Z()

            # Validate center of mass coordinates
            if not all(isinstance(v, (int, float)) for v in [x, y, z]):
                logger.debug("Invalid center of mass: non-numeric values")
                return None

            return (float(x), float(y), float(z))

        except Exception as e:
            logger.debug("Error calculating center of mass: %s", e)
            return None

    def _shapes_to_layers(self, shape_counts: dict[str, int]) -> list[ExtractedLayer]:
        """Convert shape counts to layer-like structure."""
        layers: list[ExtractedLayer] = []

        for shape_type, count in shape_counts.items():
            layers.append(
                ExtractedLayer(
                    name=shape_type.title(),
                    entity_count=count,
                    is_on=True,
                )
            )

        return sorted(layers, key=lambda x: x.entity_count, reverse=True)
