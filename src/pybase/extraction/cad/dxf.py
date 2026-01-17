"""DXF file parser for PyBase.

Uses ezdxf library to extract information from AutoCAD DXF files:
- Layers (name, color, linetype, state)
- Blocks (definitions, inserts, attributes)
- Dimensions (linear, angular, radial, diameter)
- Text entities (TEXT, MTEXT)
- Geometry summary (lines, circles, arcs, polylines, etc.)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, BinaryIO

from pybase.extraction.base import (
    CADExtractionResult,
    ExtractedBlock,
    ExtractedDimension,
    ExtractedEntity,
    ExtractedLayer,
    ExtractedText,
    ExtractedTitleBlock,
    GeometrySummary,
)

logger = logging.getLogger(__name__)

# Try to import ezdxf
try:
    import ezdxf
    from ezdxf.document import Drawing
    from ezdxf.entities import DXFEntity
    from ezdxf.layouts import Modelspace

    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False
    Drawing = Any
    DXFEntity = Any
    Modelspace = Any


class DXFParser:
    """Parser for AutoCAD DXF files.

    Extracts layers, blocks, dimensions, text, and geometry from DXF files.

    Example:
        parser = DXFParser()
        result = parser.parse("drawing.dxf")

        # Access layers
        for layer in result.layers:
            print(f"{layer.name}: {layer.entity_count} entities")

        # Access dimensions
        for dim in result.dimensions:
            print(f"{dim.dimension_type}: {dim.value} {dim.unit}")
    """

    # ACI (AutoCAD Color Index) to color name mapping (common colors)
    ACI_COLORS: dict[int, str] = {
        0: "ByBlock",
        1: "Red",
        2: "Yellow",
        3: "Green",
        4: "Cyan",
        5: "Blue",
        6: "Magenta",
        7: "White",
        256: "ByLayer",
    }

    def __init__(self, extract_entities: bool = False, max_entities: int = 10000):
        """Initialize the DXF parser.

        Args:
            extract_entities: Whether to extract individual entities (can be large).
            max_entities: Maximum number of entities to extract when extract_entities is True.
        """
        self.extract_entities = extract_entities
        self.max_entities = max_entities

        if not EZDXF_AVAILABLE:
            raise ImportError("ezdxf is required for DXF parsing. Install with: pip install ezdxf")

    def parse(self, source: str | Path | BinaryIO) -> CADExtractionResult:
        """Parse a DXF file and extract information.

        Args:
            source: File path or file-like object containing DXF data.

        Returns:
            CADExtractionResult with extracted layers, blocks, dimensions, text, etc.
        """
        source_file = str(source) if isinstance(source, (str, Path)) else "<stream>"

        result = CADExtractionResult(
            source_file=source_file,
            source_type="dxf",
        )

        try:
            # Load the DXF document
            if isinstance(source, (str, Path)):
                doc = ezdxf.readfile(str(source))
            else:
                doc = ezdxf.read(source)

            # Extract metadata
            result.metadata = self._extract_metadata(doc)

            # Extract layers
            result.layers = self._extract_layers(doc)

            # Extract blocks
            result.blocks = self._extract_blocks(doc)

            # Get modelspace for entity extraction
            msp = doc.modelspace()

            # Extract dimensions
            result.dimensions = self._extract_dimensions(msp)

            # Extract text
            result.text_blocks = self._extract_text(msp)

            # Extract title block (from known block names or specific locations)
            result.title_block = self._extract_title_block(doc, msp)

            # Extract geometry summary
            result.geometry_summary = self._extract_geometry_summary(msp)

            # Optionally extract individual entities
            if self.extract_entities:
                result.entities = self._extract_entities(msp)

            # Update layer entity counts
            self._update_layer_entity_counts(msp, result.layers)

        except ezdxf.DXFError as e:
            result.errors.append(f"DXF parsing error: {e}")
            logger.error("DXF parsing error for %s: %s", source_file, e)
        except Exception as e:
            result.errors.append(f"Unexpected error: {e}")
            logger.exception("Unexpected error parsing DXF: %s", source_file)

        return result

    def _extract_metadata(self, doc: Drawing) -> dict[str, Any]:
        """Extract document metadata from DXF header."""
        metadata: dict[str, Any] = {}

        try:
            header = doc.header

            # Version info
            metadata["dxf_version"] = doc.dxfversion
            metadata["acad_version"] = getattr(doc, "acad_release", None)

            # Drawing units
            if "$INSUNITS" in header:
                units_map = {
                    0: "Unitless",
                    1: "Inches",
                    2: "Feet",
                    3: "Miles",
                    4: "Millimeters",
                    5: "Centimeters",
                    6: "Meters",
                    7: "Kilometers",
                    8: "Microinches",
                    9: "Mils",
                    10: "Yards",
                    11: "Angstroms",
                    12: "Nanometers",
                    13: "Microns",
                    14: "Decimeters",
                    15: "Decameters",
                    16: "Hectometers",
                    17: "Gigameters",
                    18: "Astronomical Units",
                    19: "Light Years",
                    20: "Parsecs",
                }
                unit_code = header.get("$INSUNITS", 0)
                metadata["units"] = units_map.get(unit_code, f"Unknown ({unit_code})")
                metadata["units_code"] = unit_code

            # Drawing limits
            if "$LIMMIN" in header and "$LIMMAX" in header:
                limmin = header.get("$LIMMIN")
                limmax = header.get("$LIMMAX")
                if limmin and limmax:
                    metadata["limits"] = {
                        "min": (limmin[0], limmin[1]),
                        "max": (limmax[0], limmax[1]),
                    }

            # Created/modified info
            if "$TDCREATE" in header:
                metadata["created"] = str(header.get("$TDCREATE"))
            if "$TDUPDATE" in header:
                metadata["modified"] = str(header.get("$TDUPDATE"))

            # Author/comments from DWGPROPS if available
            if hasattr(doc, "ezdxf_metadata"):
                md = doc.ezdxf_metadata
                if hasattr(md, "custom_properties"):
                    metadata["custom_properties"] = dict(md.custom_properties)

        except Exception as e:
            logger.warning("Error extracting DXF metadata: %s", e)

        return metadata

    def _extract_layers(self, doc: Drawing) -> list[ExtractedLayer]:
        """Extract layer information from the document."""
        layers: list[ExtractedLayer] = []

        try:
            for layer in doc.layers:
                color = layer.color
                color_name = self.ACI_COLORS.get(color, str(color))

                extracted = ExtractedLayer(
                    name=layer.dxf.name,
                    color=color_name if color in self.ACI_COLORS else color,
                    linetype=layer.dxf.linetype,
                    lineweight=getattr(layer.dxf, "lineweight", None),
                    is_on=layer.is_on(),
                    is_frozen=layer.is_frozen(),
                    is_locked=layer.is_locked(),
                )
                layers.append(extracted)

        except Exception as e:
            logger.warning("Error extracting layers: %s", e)

        return layers

    def _extract_blocks(self, doc: Drawing) -> list[ExtractedBlock]:
        """Extract block definitions and their usage."""
        blocks: list[ExtractedBlock] = []

        try:
            # Get insert counts
            msp = doc.modelspace()
            insert_counts: dict[str, int] = {}
            for insert in msp.query("INSERT"):
                block_name = insert.dxf.name
                insert_counts[block_name] = insert_counts.get(block_name, 0) + 1

            # Process block definitions
            for block in doc.blocks:
                # Skip model and paper space blocks
                if block.name.startswith("*"):
                    continue

                # Get block attributes from first insert
                attributes: list[dict[str, Any]] = []
                for insert in msp.query(f'INSERT[name=="{block.name}"]'):
                    if insert.attribs:
                        for attrib in insert.attribs:
                            attributes.append(
                                {
                                    "tag": attrib.dxf.tag,
                                    "value": attrib.dxf.text,
                                }
                            )
                        break  # Only get attributes from first insert

                base_point = None
                if hasattr(block, "base_point"):
                    bp = block.base_point
                    base_point = (bp.x, bp.y, bp.z)

                extracted = ExtractedBlock(
                    name=block.name,
                    insert_count=insert_counts.get(block.name, 0),
                    base_point=base_point,
                    attributes=attributes,
                    entity_count=len(list(block)),
                )
                blocks.append(extracted)

        except Exception as e:
            logger.warning("Error extracting blocks: %s", e)

        return blocks

    def _extract_dimensions(self, msp: Modelspace) -> list[ExtractedDimension]:
        """Extract dimension entities from modelspace."""
        dimensions: list[ExtractedDimension] = []

        try:
            for dim in msp.query("DIMENSION"):
                dim_type = self._get_dimension_type(dim)
                value = self._get_dimension_value(dim)

                if value is None:
                    continue

                # Parse tolerance from override text if present
                tolerance_plus = None
                tolerance_minus = None
                override_text = getattr(dim.dxf, "text", "")

                if override_text:
                    tolerance = self._parse_tolerance(override_text)
                    if tolerance:
                        tolerance_plus, tolerance_minus = tolerance

                # Get bounding box if available
                bbox = None
                try:
                    bbox_obj = dim.bbox()
                    if bbox_obj:
                        bbox = (
                            bbox_obj.extmin.x,
                            bbox_obj.extmin.y,
                            bbox_obj.extmax.x,
                            bbox_obj.extmax.y,
                        )
                except Exception:
                    pass

                extracted = ExtractedDimension(
                    value=value,
                    unit="mm",  # DXF dimensions are typically unitless, assume mm
                    tolerance_plus=tolerance_plus,
                    tolerance_minus=tolerance_minus,
                    dimension_type=dim_type,
                    label=override_text if override_text and override_text != "<>" else None,
                    confidence=1.0,
                    bbox=bbox,
                )
                dimensions.append(extracted)

        except Exception as e:
            logger.warning("Error extracting dimensions: %s", e)

        return dimensions

    def _get_dimension_type(self, dim: DXFEntity) -> str:
        """Determine the type of dimension."""
        dim_type_code = getattr(dim.dxf, "dimtype", 0) & 0x0F

        type_map = {
            0: "linear",  # Rotated, horizontal, or vertical
            1: "aligned",
            2: "angular",
            3: "diameter",
            4: "radius",
            5: "angular3point",
            6: "ordinate",
        }
        return type_map.get(dim_type_code, "linear")

    def _get_dimension_value(self, dim: DXFEntity) -> float | None:
        """Extract the measurement value from a dimension."""
        try:
            # Primary method: actual_measurement property
            if hasattr(dim, "actual_measurement"):
                return dim.actual_measurement

            # Fallback: measurement attribute
            if hasattr(dim.dxf, "actual_measurement"):
                return dim.dxf.actual_measurement

            # Try to calculate from geometry
            if hasattr(dim, "measure"):
                return dim.measure()

            return None

        except Exception:
            return None

    def _parse_tolerance(self, text: str) -> tuple[float, float] | None:
        """Parse tolerance from dimension text override."""
        # Pattern: value ±tolerance or value +tol/-tol
        symmetric = re.search(r"[±]\s*([\d.]+)", text)
        if symmetric:
            tol = float(symmetric.group(1))
            return (tol, tol)

        asymmetric = re.search(r"\+\s*([\d.]+)\s*/\s*-\s*([\d.]+)", text)
        if asymmetric:
            return (float(asymmetric.group(1)), float(asymmetric.group(2)))

        return None

    def _extract_text(self, msp: Modelspace) -> list[ExtractedText]:
        """Extract TEXT and MTEXT entities from modelspace."""
        text_blocks: list[ExtractedText] = []

        try:
            # Extract TEXT entities
            for text in msp.query("TEXT"):
                content = text.dxf.text
                if not content or not content.strip():
                    continue

                bbox = None
                try:
                    bbox_obj = text.bbox()
                    if bbox_obj:
                        bbox = (
                            bbox_obj.extmin.x,
                            bbox_obj.extmin.y,
                            bbox_obj.extmax.x,
                            bbox_obj.extmax.y,
                        )
                except Exception:
                    pass

                font_size = getattr(text.dxf, "height", None)

                extracted = ExtractedText(
                    text=content,
                    confidence=1.0,
                    bbox=bbox,
                    font_size=font_size,
                    is_title=font_size is not None and font_size > 5,  # Heuristic
                )
                text_blocks.append(extracted)

            # Extract MTEXT entities
            for mtext in msp.query("MTEXT"):
                content = mtext.plain_text()
                if not content or not content.strip():
                    continue

                bbox = None
                try:
                    bbox_obj = mtext.bbox()
                    if bbox_obj:
                        bbox = (
                            bbox_obj.extmin.x,
                            bbox_obj.extmin.y,
                            bbox_obj.extmax.x,
                            bbox_obj.extmax.y,
                        )
                except Exception:
                    pass

                font_size = getattr(mtext.dxf, "char_height", None)

                extracted = ExtractedText(
                    text=content,
                    confidence=1.0,
                    bbox=bbox,
                    font_size=font_size,
                    is_title=font_size is not None and font_size > 5,
                )
                text_blocks.append(extracted)

        except Exception as e:
            logger.warning("Error extracting text: %s", e)

        return text_blocks

    def _extract_title_block(self, doc: Drawing, msp: Modelspace) -> ExtractedTitleBlock | None:
        """Attempt to extract title block information."""
        try:
            title_block = ExtractedTitleBlock()
            found_any = False

            # Common title block block names
            title_block_names = [
                "TITLE BLOCK",
                "TITLEBLOCK",
                "TITLE_BLOCK",
                "A-TITLE",
                "BORDER",
            ]

            # Search for title block inserts
            for insert in msp.query("INSERT"):
                block_name = insert.dxf.name.upper()
                if any(tb in block_name for tb in title_block_names):
                    # Extract attributes from title block
                    for attrib in insert.attribs:
                        tag = attrib.dxf.tag.upper()
                        value = attrib.dxf.text

                        if not value:
                            continue

                        found_any = True

                        if "DWG" in tag or "NUMBER" in tag or "NO" in tag:
                            title_block.drawing_number = value
                        elif "TITLE" in tag or "NAME" in tag:
                            title_block.title = value
                        elif "REV" in tag:
                            title_block.revision = value
                        elif "DATE" in tag:
                            title_block.date = value
                        elif "AUTHOR" in tag or "DRAWN" in tag or "BY" in tag:
                            title_block.author = value
                        elif "COMPANY" in tag or "FIRM" in tag:
                            title_block.company = value
                        elif "SCALE" in tag:
                            title_block.scale = value
                        elif "SHEET" in tag:
                            title_block.sheet = value
                        elif "MATERIAL" in tag or "MAT" in tag:
                            title_block.material = value
                        elif "FINISH" in tag:
                            title_block.finish = value
                        else:
                            title_block.custom_fields[attrib.dxf.tag] = value

                    if found_any:
                        break

            return title_block if found_any else None

        except Exception as e:
            logger.warning("Error extracting title block: %s", e)
            return None

    def _extract_geometry_summary(self, msp: Modelspace) -> GeometrySummary:
        """Count geometry entities in modelspace."""
        summary = GeometrySummary()

        try:
            for entity in msp:
                dxftype = entity.dxftype()
                summary.total_entities += 1

                if dxftype == "LINE":
                    summary.lines += 1
                elif dxftype == "CIRCLE":
                    summary.circles += 1
                elif dxftype == "ARC":
                    summary.arcs += 1
                elif dxftype in ("POLYLINE", "LWPOLYLINE"):
                    summary.polylines += 1
                elif dxftype == "SPLINE":
                    summary.splines += 1
                elif dxftype == "ELLIPSE":
                    summary.ellipses += 1
                elif dxftype == "POINT":
                    summary.points += 1
                elif dxftype == "HATCH":
                    summary.hatches += 1
                elif dxftype in ("3DSOLID", "SOLID"):
                    summary.solids += 1
                elif dxftype in ("MESH", "POLYMESH", "POLYFACE"):
                    summary.meshes += 1

        except Exception as e:
            logger.warning("Error counting geometry: %s", e)

        return summary

    def _extract_entities(self, msp: Modelspace) -> list[ExtractedEntity]:
        """Extract individual entities (limited by max_entities)."""
        entities: list[ExtractedEntity] = []

        try:
            count = 0
            for entity in msp:
                if count >= self.max_entities:
                    break

                dxftype = entity.dxftype()

                # Skip certain entity types
                if dxftype in ("DIMENSION", "TEXT", "MTEXT", "INSERT"):
                    continue

                properties: dict[str, Any] = {}

                # Extract common properties
                if dxftype == "LINE":
                    properties["start"] = (
                        entity.dxf.start.x,
                        entity.dxf.start.y,
                        entity.dxf.start.z,
                    )
                    properties["end"] = (
                        entity.dxf.end.x,
                        entity.dxf.end.y,
                        entity.dxf.end.z,
                    )
                elif dxftype == "CIRCLE":
                    properties["center"] = (
                        entity.dxf.center.x,
                        entity.dxf.center.y,
                        entity.dxf.center.z,
                    )
                    properties["radius"] = entity.dxf.radius
                elif dxftype == "ARC":
                    properties["center"] = (
                        entity.dxf.center.x,
                        entity.dxf.center.y,
                        entity.dxf.center.z,
                    )
                    properties["radius"] = entity.dxf.radius
                    properties["start_angle"] = entity.dxf.start_angle
                    properties["end_angle"] = entity.dxf.end_angle

                # Get bounding box
                bbox = None
                try:
                    bbox_obj = entity.bbox()
                    if bbox_obj:
                        bbox = (
                            bbox_obj.extmin.x,
                            bbox_obj.extmin.y,
                            bbox_obj.extmax.x,
                            bbox_obj.extmax.y,
                        )
                except Exception:
                    pass

                extracted = ExtractedEntity(
                    entity_type=dxftype,
                    layer=entity.dxf.layer,
                    color=entity.dxf.color if hasattr(entity.dxf, "color") else None,
                    linetype=entity.dxf.linetype if hasattr(entity.dxf, "linetype") else None,
                    properties=properties,
                    bbox=bbox,
                )
                entities.append(extracted)
                count += 1

        except Exception as e:
            logger.warning("Error extracting entities: %s", e)

        return entities

    def _update_layer_entity_counts(self, msp: Modelspace, layers: list[ExtractedLayer]) -> None:
        """Update entity counts for each layer."""
        try:
            layer_counts: dict[str, int] = {}

            for entity in msp:
                layer_name = entity.dxf.layer
                layer_counts[layer_name] = layer_counts.get(layer_name, 0) + 1

            for layer in layers:
                layer.entity_count = layer_counts.get(layer.name, 0)

        except Exception as e:
            logger.warning("Error updating layer entity counts: %s", e)
