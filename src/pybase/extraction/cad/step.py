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
        result.metadata = self._extract_ocp_metadata(reader)

        # Count shape types
        result.shape_counts = self._count_shapes_ocp(shape)

        # Create assembly structure
        result.assembly = self._extract_assembly_ocp(shape)

        # Calculate overall bounding box
        result.overall_bbox = self._get_bbox_ocp(shape)

        # Calculate total volume and surface area
        if self.compute_mass_properties:
            result.total_volume = self._get_volume_ocp(shape)
            result.total_surface_area = self._get_surface_area_ocp(shape)

        # Convert to layers (by shape type)
        result.layers = self._shapes_to_layers(result.shape_counts)

        # Geometry summary
        result.geometry_summary = GeometrySummary(
            solids=result.shape_counts.get("SOLID", 0),
            meshes=result.shape_counts.get("SHELL", 0),
            total_entities=sum(result.shape_counts.values()),
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
                result.shape_counts["SOLID"] = len(solids)

                for i, solid in enumerate(solids):
                    part = STEPPart(
                        name=f"Part_{i + 1}",
                        part_id=str(i + 1),
                        shape_type="SOLID",
                    )

                    # Get bounding box
                    try:
                        bbox = solid.BoundingBox()
                        part.bbox = (
                            bbox.xmin,
                            bbox.ymin,
                            bbox.zmin,
                            bbox.xmax,
                            bbox.ymax,
                            bbox.zmax,
                        )
                    except Exception:
                        pass

                    # Get face/edge counts
                    if hasattr(solid, "Faces"):
                        part.num_faces = len(solid.Faces())
                    if hasattr(solid, "Edges"):
                        part.num_edges = len(solid.Edges())
                    if hasattr(solid, "Vertices"):
                        part.num_vertices = len(solid.Vertices())

                    result.assembly.parts.append(part)

                result.assembly.total_parts = len(result.assembly.parts)

            # Get overall bounding box
            if hasattr(shape, "BoundingBox"):
                bbox = shape.BoundingBox()
                result.overall_bbox = (
                    bbox.xmin,
                    bbox.ymin,
                    bbox.zmin,
                    bbox.xmax,
                    bbox.ymax,
                    bbox.zmax,
                )

        except Exception as e:
            result.warnings.append(f"CadQuery processing warning: {e}")

        # Convert to layers
        result.layers = self._shapes_to_layers(result.shape_counts)

        # Geometry summary
        result.geometry_summary = GeometrySummary(
            solids=result.shape_counts.get("SOLID", 0),
            total_entities=sum(result.shape_counts.values()),
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

        shape_types = [
            (TopAbs_COMPOUND, "COMPOUND"),
            (TopAbs_SOLID, "SOLID"),
            (TopAbs_SHELL, "SHELL"),
            (TopAbs_FACE, "FACE"),
            (TopAbs_EDGE, "EDGE"),
            (TopAbs_VERTEX, "VERTEX"),
        ]

        for shape_type, name in shape_types:
            explorer = TopExp_Explorer(shape, shape_type)
            count = 0
            while explorer.More():
                count += 1
                explorer.Next()
            if count > 0:
                counts[name] = count

        return counts

    def _extract_assembly_ocp(self, shape: Any) -> STEPAssembly:
        """Extract assembly structure from OCP shape."""
        assembly = STEPAssembly()
        parts: list[STEPPart] = []

        # Extract solids as parts
        explorer = TopExp_Explorer(shape, TopAbs_SOLID)
        part_num = 0

        while explorer.More() and part_num < self.max_parts:
            solid = explorer.Current()

            part = STEPPart(
                name=f"Solid_{part_num + 1}",
                part_id=str(part_num + 1),
                shape_type="SOLID",
            )

            # Get bounding box
            part.bbox = self._get_bbox_ocp(solid)

            # Get mass properties
            if self.compute_mass_properties:
                part.volume = self._get_volume_ocp(solid)
                part.surface_area = self._get_surface_area_ocp(solid)
                part.center_of_mass = self._get_center_of_mass_ocp(solid)

            # Count sub-shapes
            part.num_faces = self._count_subshapes_ocp(solid, TopAbs_FACE)
            part.num_edges = self._count_subshapes_ocp(solid, TopAbs_EDGE)
            part.num_vertices = self._count_subshapes_ocp(solid, TopAbs_VERTEX)

            parts.append(part)
            assembly.root_parts.append(part.name)

            part_num += 1
            explorer.Next()

        assembly.parts = parts
        assembly.total_parts = len(parts)

        return assembly

    def _count_subshapes_ocp(self, shape: Any, shape_type: Any) -> int:
        """Count sub-shapes of a given type."""
        explorer = TopExp_Explorer(shape, shape_type)
        count = 0
        while explorer.More():
            count += 1
            explorer.Next()
        return count

    def _get_bbox_ocp(self, shape: Any) -> tuple[float, float, float, float, float, float] | None:
        """Get bounding box of a shape."""
        try:
            bbox = Bnd_Box()
            BRepBndLib_AddClose(shape, bbox)

            if bbox.IsVoid():
                return None

            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
            return (xmin, ymin, zmin, xmax, ymax, zmax)

        except Exception as e:
            logger.debug("Error getting bbox: %s", e)
            return None

    def _get_volume_ocp(self, shape: Any) -> float | None:
        """Calculate volume of a shape."""
        try:
            props = GProp_GProps()
            BRepGProp_VolumeProperties(shape, props)
            return props.Mass()

        except Exception as e:
            logger.debug("Error calculating volume: %s", e)
            return None

    def _get_surface_area_ocp(self, shape: Any) -> float | None:
        """Calculate surface area of a shape."""
        try:
            props = GProp_GProps()
            BRepGProp_SurfaceProperties(shape, props)
            return props.Mass()

        except Exception as e:
            logger.debug("Error calculating surface area: %s", e)
            return None

    def _get_center_of_mass_ocp(self, shape: Any) -> tuple[float, float, float] | None:
        """Calculate center of mass of a shape."""
        try:
            props = GProp_GProps()
            BRepGProp_VolumeProperties(shape, props)
            com = props.CentreOfMass()
            return (com.X(), com.Y(), com.Z())

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
