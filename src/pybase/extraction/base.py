"""Base types for extraction module."""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class ExtractionType(str, Enum):
    """Type of extraction performed."""

    TABLE = "table"
    TEXT = "text"
    DIMENSION = "dimension"
    TITLE_BLOCK = "title_block"
    BOM = "bom"
    GEOMETRY = "geometry"
    LAYER = "layer"
    BLOCK = "block"


@dataclass
class ExtractedTable:
    """Represents an extracted table from a document."""

    headers: list[str]
    rows: list[list[Any]]
    page: int | None = None
    confidence: float = 1.0
    bbox: tuple[float, float, float, float] | None = None  # x1, y1, x2, y2
    merged_cells: list[dict[str, int]] = field(default_factory=list)  # List of {row, col, rowspan, colspan}

    @property
    def num_rows(self) -> int:
        return len(self.rows)

    @property
    def num_columns(self) -> int:
        return len(self.headers) if self.headers else (len(self.rows[0]) if self.rows else 0)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "headers": self.headers,
            "rows": self.rows,
            "page": self.page,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "num_rows": self.num_rows,
            "num_columns": self.num_columns,
            "merged_cells": self.merged_cells,
        }

    def to_records(self) -> list[dict[str, Any]]:
        """Convert table to list of record dictionaries."""
        if not self.headers:
            return [{"col_" + str(i): v for i, v in enumerate(row)} for row in self.rows]
        return [dict(zip(self.headers, row)) for row in self.rows]


@dataclass
class ExtractedDimension:
    """Represents an extracted dimension from a drawing."""

    value: float
    unit: str = "mm"
    tolerance_plus: float | None = None
    tolerance_minus: float | None = None
    dimension_type: str = "linear"  # linear, angular, radius, diameter
    label: str | None = None
    page: int | None = None
    confidence: float = 1.0
    bbox: tuple[float, float, float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "value": self.value,
            "unit": self.unit,
            "tolerance_plus": self.tolerance_plus,
            "tolerance_minus": self.tolerance_minus,
            "dimension_type": self.dimension_type,
            "label": self.label,
            "page": self.page,
            "confidence": self.confidence,
            "bbox": self.bbox,
        }

    def format_display(self) -> str:
        """Format dimension for display."""
        result = f"{self.value}"
        if self.tolerance_plus is not None and self.tolerance_minus is not None:
            if self.tolerance_plus == self.tolerance_minus:
                result += f" ±{self.tolerance_plus}"
            else:
                result += f" +{self.tolerance_plus}/-{self.tolerance_minus}"
        result += f" {self.unit}"
        return result


@dataclass
class ExtractedText:
    """Represents extracted text from a document."""

    text: str
    page: int | None = None
    confidence: float = 1.0
    bbox: tuple[float, float, float, float] | None = None
    font_size: float | None = None
    is_title: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "page": self.page,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "font_size": self.font_size,
            "is_title": self.is_title,
        }


@dataclass
class ExtractedTitleBlock:
    """Represents extracted title block information."""

    drawing_number: str | None = None
    title: str | None = None
    revision: str | None = None
    date: str | None = None
    author: str | None = None
    company: str | None = None
    scale: str | None = None
    sheet: str | None = None
    material: str | None = None
    finish: str | None = None
    custom_fields: dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        result = {
            "drawing_number": self.drawing_number,
            "title": self.title,
            "revision": self.revision,
            "date": self.date,
            "author": self.author,
            "company": self.company,
            "scale": self.scale,
            "sheet": self.sheet,
            "material": self.material,
            "finish": self.finish,
            "confidence": self.confidence,
        }
        result.update(self.custom_fields)
        return {k: v for k, v in result.items() if v is not None}


@dataclass
class ExtractedBOM:
    """Represents an extracted Bill of Materials."""

    items: list[dict[str, Any]]
    headers: list[str] | None = None
    total_items: int = 0
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": self.items,
            "headers": self.headers,
            "total_items": self.total_items or len(self.items),
            "confidence": self.confidence,
        }


@dataclass
class ExtractedLayer:
    """Represents a layer extracted from a CAD file."""

    name: str
    color: int | str | None = None  # ACI color code or name
    linetype: str | None = None
    lineweight: float | None = None
    is_on: bool = True
    is_frozen: bool = False
    is_locked: bool = False
    entity_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "color": self.color,
            "linetype": self.linetype,
            "lineweight": self.lineweight,
            "is_on": self.is_on,
            "is_frozen": self.is_frozen,
            "is_locked": self.is_locked,
            "entity_count": self.entity_count,
        }


@dataclass
class ExtractedBlock:
    """Represents a block definition extracted from a CAD file."""

    name: str
    insert_count: int = 0
    base_point: tuple[float, float, float] | None = None
    attributes: list[dict[str, Any]] = field(default_factory=list)
    entity_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "insert_count": self.insert_count,
            "base_point": self.base_point,
            "attributes": self.attributes,
            "entity_count": self.entity_count,
        }


@dataclass
class ExtractedEntity:
    """Represents a generic entity extracted from a CAD file."""

    entity_type: str
    layer: str | None = None
    color: int | str | None = None
    linetype: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    bbox: tuple[float, float, float, float] | None = None  # x1, y1, x2, y2

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "layer": self.layer,
            "color": self.color,
            "linetype": self.linetype,
            "properties": self.properties,
            "bbox": self.bbox,
        }


@dataclass
class GeometrySummary:
    """Summary of geometry entities in a CAD file."""

    lines: int = 0
    circles: int = 0
    arcs: int = 0
    polylines: int = 0
    splines: int = 0
    ellipses: int = 0
    points: int = 0
    hatches: int = 0
    solids: int = 0
    meshes: int = 0
    total_entities: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "lines": self.lines,
            "circles": self.circles,
            "arcs": self.arcs,
            "polylines": self.polylines,
            "splines": self.splines,
            "ellipses": self.ellipses,
            "points": self.points,
            "hatches": self.hatches,
            "solids": self.solids,
            "meshes": self.meshes,
            "total_entities": self.total_entities,
        }


@dataclass
class CADExtractionResult:
    """Result of a CAD file extraction operation."""

    source_file: str
    source_type: str  # dxf, ifc, step
    layers: list[ExtractedLayer] = field(default_factory=list)
    blocks: list[ExtractedBlock] = field(default_factory=list)
    dimensions: list[ExtractedDimension] = field(default_factory=list)
    text_blocks: list[ExtractedText] = field(default_factory=list)
    title_block: ExtractedTitleBlock | None = None
    geometry_summary: GeometrySummary | None = None
    entities: list[ExtractedEntity] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def has_content(self) -> bool:
        return bool(
            self.layers or self.blocks or self.dimensions or self.text_blocks or self.entities
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "source_type": self.source_type,
            "success": self.success,
            "layers": [l.to_dict() for l in self.layers],
            "blocks": [b.to_dict() for b in self.blocks],
            "dimensions": [d.to_dict() for d in self.dimensions],
            "text_blocks": [t.to_dict() for t in self.text_blocks],
            "title_block": self.title_block.to_dict() if self.title_block else None,
            "geometry_summary": self.geometry_summary.to_dict() if self.geometry_summary else None,
            "entities": [e.to_dict() for e in self.entities],
            "metadata": self.metadata,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class ExtractionResult:
    """Result of an extraction operation."""

    source_file: str
    source_type: str  # pdf, dxf, ifc, step
    tables: list[ExtractedTable] = field(default_factory=list)
    dimensions: list[ExtractedDimension] = field(default_factory=list)
    text_blocks: list[ExtractedText] = field(default_factory=list)
    title_block: ExtractedTitleBlock | None = None
    bom: ExtractedBOM | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def has_content(self) -> bool:
        return bool(
            self.tables or self.dimensions or self.text_blocks or self.title_block or self.bom
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "source_type": self.source_type,
            "success": self.success,
            "tables": [t.to_dict() for t in self.tables],
            "dimensions": [d.to_dict() for d in self.dimensions],
            "text_blocks": [t.to_dict() for t in self.text_blocks],
            "title_block": self.title_block.to_dict() if self.title_block else None,
            "bom": self.bom.to_dict() if self.bom else None,
            "metadata": self.metadata,
            "errors": self.errors,
            "warnings": self.warnings,
        }
