"""Werk24 API client for PyBase.

Provides integration with the Werk24 API for AI-powered engineering drawing analysis:
- Automatic dimension extraction with tolerances
- GD&T (Geometric Dimensioning and Tolerancing) recognition
- Title block parsing
- BOM (Bill of Materials) extraction
- Thread specification detection
- Surface finish recognition
- Material callouts

API Documentation: https://werk24.io/docs
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, Literal, TYPE_CHECKING
from enum import Enum

from pybase.extraction.base import (
    ExtractionResult,
    ExtractedDimension,
    ExtractedTable,
    ExtractedText,
    ExtractedTitleBlock,
    ExtractedBOM,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Try to import werk24 SDK
try:
    from werk24 import Hook, W24TechRead, W24AskType
    from werk24.models.ask import (
        W24AskCanvasThumbnail,
        W24AskPageThumbnail,
        W24AskSheetThumbnail,
        W24AskPartOverallDimensions,
        W24AskVariantMeasures,
        W24AskVariantGDTs,
        W24AskTitleBlock,
        W24AskPartMaterial,
        W24AskPartManufacturingPMI,
    )

    WERK24_AVAILABLE = True
except ImportError:
    WERK24_AVAILABLE = False
    Hook = None
    W24TechRead = None


class Werk24AskType(str, Enum):
    """Types of information to request from Werk24 API."""

    DIMENSIONS = "dimensions"
    GDTS = "gdts"
    TITLE_BLOCK = "title_block"
    MATERIAL = "material"
    THREADS = "threads"
    SURFACE_FINISH = "surface_finish"
    OVERALL_DIMENSIONS = "overall_dimensions"
    THUMBNAIL = "thumbnail"
    PMI = "pmi"  # Product Manufacturing Information


@dataclass
class Werk24Dimension:
    """Dimension extracted by Werk24."""

    nominal_value: float
    unit: str = "mm"
    tolerance_type: str | None = None  # general, fit, iso, etc.
    tolerance_grade: str | None = None  # e.g., "h7", "H8"
    upper_deviation: float | None = None
    lower_deviation: float | None = None
    dimension_type: str = "linear"  # linear, angular, radius, diameter
    feature_type: str | None = None  # shaft, hole, etc.
    confidence: float = 1.0

    def to_extracted_dimension(self) -> ExtractedDimension:
        """Convert to standard ExtractedDimension."""
        return ExtractedDimension(
            value=self.nominal_value,
            unit=self.unit,
            tolerance_plus=self.upper_deviation,
            tolerance_minus=abs(self.lower_deviation) if self.lower_deviation else None,
            dimension_type=self.dimension_type,
            label=self.tolerance_grade,
            confidence=self.confidence,
        )


@dataclass
class Werk24GDT:
    """GD&T frame extracted by Werk24."""

    characteristic_type: str  # position, flatness, circularity, etc.
    tolerance_value: float
    tolerance_unit: str = "mm"
    material_condition: str | None = None  # MMC, LMC, RFS
    datums: list[str] = field(default_factory=list)
    composite: bool = False
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "characteristic_type": self.characteristic_type,
            "tolerance_value": self.tolerance_value,
            "tolerance_unit": self.tolerance_unit,
            "material_condition": self.material_condition,
            "datums": self.datums,
            "composite": self.composite,
            "confidence": self.confidence,
        }


@dataclass
class Werk24Thread:
    """Thread specification extracted by Werk24."""

    standard: str  # ISO, UN, Whitworth, etc.
    designation: str  # e.g., "M8x1.25"
    nominal_diameter: float
    pitch: float | None = None
    thread_class: str | None = None  # e.g., "6g", "2A"
    hand: str = "right"  # left, right
    thread_type: str = "external"  # external, internal
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "standard": self.standard,
            "designation": self.designation,
            "nominal_diameter": self.nominal_diameter,
            "pitch": self.pitch,
            "thread_class": self.thread_class,
            "hand": self.hand,
            "thread_type": self.thread_type,
            "confidence": self.confidence,
        }


@dataclass
class Werk24SurfaceFinish:
    """Surface finish extracted by Werk24."""

    ra_value: float | None = None
    rz_value: float | None = None
    unit: str = "μm"
    machining_allowance: float | None = None
    lay_symbol: str | None = None
    process: str | None = None
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ra_value": self.ra_value,
            "rz_value": self.rz_value,
            "unit": self.unit,
            "machining_allowance": self.machining_allowance,
            "lay_symbol": self.lay_symbol,
            "process": self.process,
            "confidence": self.confidence,
        }


@dataclass
class Werk24ExtractionResult(ExtractionResult):
    """Extended result for Werk24 extraction."""

    dimensions: list[Werk24Dimension] = field(default_factory=list)
    gdts: list[Werk24GDT] = field(default_factory=list)
    threads: list[Werk24Thread] = field(default_factory=list)
    surface_finishes: list[Werk24SurfaceFinish] = field(default_factory=list)
    overall_dimensions: dict[str, float] | None = None  # length, width, height
    materials: list[dict[str, Any]] = field(default_factory=list)
    thumbnails: dict[str, bytes] = field(default_factory=dict)
    raw_responses: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "dimensions": [d.to_extracted_dimension().to_dict() for d in self.dimensions],
                "gdts": [g.to_dict() for g in self.gdts],
                "threads": [t.to_dict() for t in self.threads],
                "surface_finishes": [s.to_dict() for s in self.surface_finishes],
                "overall_dimensions": self.overall_dimensions,
                "materials": self.materials,
            }
        )
        return base


class Werk24Client:
    """Client for the Werk24 engineering drawing analysis API.

    Provides AI-powered extraction of engineering information from technical drawings
    including dimensions, GD&T, threads, materials, and more.

    Example:
        client = Werk24Client(api_key="your-api-key")

        # Synchronous usage
        result = client.extract("drawing.pdf")

        # Async usage
        result = await client.extract_async("drawing.pdf")

        # Access extracted data
        for dim in result.dimensions:
            print(f"{dim.nominal_value} {dim.unit}")
    """

    DEFAULT_BASE_URL = "https://api.werk24.io/v1"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 300.0,
    ):
        """Initialize the Werk24 client.

        Args:
            api_key: Werk24 API key. If not provided, reads from WERK24_API_KEY env var.
            base_url: Base URL for the API. Defaults to production API.
            timeout: Request timeout in seconds.
        """
        import os

        self.api_key = api_key or os.environ.get("WERK24_API_KEY")
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.timeout = timeout

        if not WERK24_AVAILABLE:
            logger.warning("werk24 SDK not available. Install with: pip install werk24")

    def extract(
        self,
        source: str | Path | BinaryIO,
        ask_types: list[Werk24AskType] | None = None,
        db: "AsyncSession | None" = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
        file_size: int | None = None,
        file_type: str | None = None,
        request_ip: str | None = None,
        user_agent: str | None = None,
    ) -> Werk24ExtractionResult:
        """Extract information from an engineering drawing (synchronous).

        Args:
            source: File path or file-like object containing the drawing.
            ask_types: Types of information to extract. Defaults to all types.
            db: Optional database session for usage tracking.
            user_id: Optional user ID for usage tracking.
            workspace_id: Optional workspace ID for usage tracking.
            file_size: Optional file size in bytes for usage tracking.
            file_type: Optional file type for usage tracking.
            request_ip: Optional request IP address for usage tracking.
            user_agent: Optional user agent string for usage tracking.

        Returns:
            Werk24ExtractionResult with extracted information.
        """
        return asyncio.run(
            self.extract_async(
                source,
                ask_types,
                db=db,
                user_id=user_id,
                workspace_id=workspace_id,
                file_size=file_size,
                file_type=file_type,
                request_ip=request_ip,
                user_agent=user_agent,
            )
        )

    async def extract_async(
        self,
        source: str | Path | BinaryIO,
        ask_types: list[Werk24AskType] | None = None,
        db: "AsyncSession | None" = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
        file_size: int | None = None,
        file_type: str | None = None,
        request_ip: str | None = None,
        user_agent: str | None = None,
    ) -> Werk24ExtractionResult:
        """Extract information from an engineering drawing (asynchronous).

        Args:
            source: File path or file-like object containing the drawing.
            ask_types: Types of information to extract. Defaults to all types.
            db: Optional database session for usage tracking.
            user_id: Optional user ID for usage tracking.
            workspace_id: Optional workspace ID for usage tracking.
            file_size: Optional file size in bytes for usage tracking.
            file_type: Optional file type for usage tracking.
            request_ip: Optional request IP address for usage tracking.
            user_agent: Optional user agent string for usage tracking.

        Returns:
            Werk24ExtractionResult with extracted information.
        """
        source_file = str(source) if isinstance(source, (str, Path)) else "<stream>"

        result = Werk24ExtractionResult(
            source_file=source_file,
            source_type="werk24",
        )

        # Initialize usage tracking variables
        usage_record = None
        usage_service = None
        start_time = time.time()

        if not self.api_key:
            result.errors.append("Werk24 API key not configured")
            return result

        if not WERK24_AVAILABLE:
            result.errors.append("werk24 SDK not installed. Install with: pip install werk24")
            return result

        # Default to all ask types
        if ask_types is None:
            ask_types = [
                Werk24AskType.DIMENSIONS,
                Werk24AskType.GDTS,
                Werk24AskType.TITLE_BLOCK,
                Werk24AskType.MATERIAL,
                Werk24AskType.OVERALL_DIMENSIONS,
            ]

        # Create usage tracking record if db and user_id provided
        if db and user_id:
            try:
                from pybase.services.werk24 import Werk24Service

                usage_service = Werk24Service()
                usage_record = await usage_service.create_usage_record(
                    db=db,
                    user_id=user_id,
                    request_type="extract_async",
                    ask_types=[str(at.value) for at in ask_types],
                    workspace_id=workspace_id,
                    source_file=source_file,
                    file_size_bytes=file_size,
                    file_type=file_type,
                    api_key_used=self.api_key[:12] if self.api_key else None,
                    request_ip=request_ip,
                    user_agent=user_agent,
                )
            except Exception as e:
                logger.warning(f"Failed to create usage tracking record: {e}", exc_info=True)

        try:
            # Read file content
            if isinstance(source, (str, Path)):
                with open(source, "rb") as f:
                    file_content = f.read()
            else:
                file_content = source.read()

            # Build asks
            asks = self._build_asks(ask_types)

            # Create hooks to collect responses
            collected_data: dict[str, Any] = {
                "dimensions": [],
                "gdts": [],
                "title_block": None,
                "materials": [],
                "overall_dimensions": None,
                "thumbnails": {},
            }

            hooks = self._build_hooks(collected_data)

            # Execute the API call
            async with W24TechRead(
                license_key=self.api_key,
            ) as techread:
                await techread.read_drawing(
                    file_content,
                    asks,
                    hooks,
                )

            # Process collected data
            self._process_collected_data(collected_data, result)

            # Update usage tracking record with success
            if usage_record and usage_service and db and user_id:
                try:
                    processing_time_ms = int((time.time() - start_time) * 1000)
                    await usage_service.update_usage_record(
                        db=db,
                        usage_id=str(usage_record.id),
                        user_id=user_id,
                        success=True,
                        status_code=200,
                        processing_time_ms=processing_time_ms,
                        dimensions_extracted=len(result.dimensions),
                        gdts_extracted=len(result.gdts),
                        materials_extracted=len(result.materials),
                        threads_extracted=len(result.threads),
                    )
                except Exception as e:
                    logger.warning(f"Failed to update usage tracking record: {e}", exc_info=True)

        except Exception as e:
            result.errors.append(f"Werk24 API error: {e}")
            logger.exception("Error calling Werk24 API")

            # Update usage tracking record with failure
            if usage_record and usage_service and db and user_id:
                try:
                    processing_time_ms = int((time.time() - start_time) * 1000)
                    await usage_service.update_usage_record(
                        db=db,
                        usage_id=str(usage_record.id),
                        user_id=user_id,
                        success=False,
                        error_message=str(e),
                        processing_time_ms=processing_time_ms,
                    )
                except Exception as update_error:
                    logger.warning(f"Failed to update usage tracking record: {update_error}", exc_info=True)

        return result

    def _build_asks(self, ask_types: list[Werk24AskType]) -> list[Any]:
        """Build the list of asks for the API."""
        asks = []

        for ask_type in ask_types:
            if ask_type == Werk24AskType.DIMENSIONS:
                asks.append(W24AskVariantMeasures())
            elif ask_type == Werk24AskType.GDTS:
                asks.append(W24AskVariantGDTs())
            elif ask_type == Werk24AskType.TITLE_BLOCK:
                asks.append(W24AskTitleBlock())
            elif ask_type == Werk24AskType.MATERIAL:
                asks.append(W24AskPartMaterial())
            elif ask_type == Werk24AskType.OVERALL_DIMENSIONS:
                asks.append(W24AskPartOverallDimensions())
            elif ask_type == Werk24AskType.PMI:
                asks.append(W24AskPartManufacturingPMI())
            elif ask_type == Werk24AskType.THUMBNAIL:
                asks.append(W24AskCanvasThumbnail())

        return asks

    def _build_hooks(self, collected_data: dict[str, Any]) -> list[Hook]:
        """Build hooks to collect API responses."""
        hooks = []

        # Measures hook
        async def on_measures(message: Any) -> None:
            if hasattr(message, "payload") and message.payload:
                for measure in message.payload.measures or []:
                    dim_data = self._parse_measure(measure)
                    if dim_data:
                        collected_data["dimensions"].append(dim_data)

        hooks.append(Hook(message_type=W24AskType.VARIANT_MEASURES, function=on_measures))

        # GDTs hook
        async def on_gdts(message: Any) -> None:
            if hasattr(message, "payload") and message.payload:
                for gdt in message.payload.gdts or []:
                    gdt_data = self._parse_gdt(gdt)
                    if gdt_data:
                        collected_data["gdts"].append(gdt_data)

        hooks.append(Hook(message_type=W24AskType.VARIANT_GDTS, function=on_gdts))

        # Title block hook
        async def on_title_block(message: Any) -> None:
            if hasattr(message, "payload") and message.payload:
                collected_data["title_block"] = self._parse_title_block(message.payload)

        hooks.append(Hook(message_type=W24AskType.TITLE_BLOCK, function=on_title_block))

        # Material hook
        async def on_material(message: Any) -> None:
            if hasattr(message, "payload") and message.payload:
                material = self._parse_material(message.payload)
                if material:
                    collected_data["materials"].append(material)

        hooks.append(Hook(message_type=W24AskType.PART_MATERIAL, function=on_material))

        # Overall dimensions hook
        async def on_overall_dimensions(message: Any) -> None:
            if hasattr(message, "payload") and message.payload:
                collected_data["overall_dimensions"] = self._parse_overall_dimensions(
                    message.payload
                )

        hooks.append(
            Hook(
                message_type=W24AskType.PART_OVERALL_DIMENSIONS,
                function=on_overall_dimensions,
            )
        )

        return hooks

    def _parse_measure(self, measure: Any) -> Werk24Dimension | None:
        """Parse a measure response into a Werk24Dimension."""
        try:
            dim = Werk24Dimension(
                nominal_value=measure.nominal_size.value,
                unit=str(measure.nominal_size.unit) if measure.nominal_size.unit else "mm",
            )

            # Parse tolerance
            if hasattr(measure, "tolerance") and measure.tolerance:
                tol = measure.tolerance
                if hasattr(tol, "deviation_upper"):
                    dim.upper_deviation = tol.deviation_upper
                if hasattr(tol, "deviation_lower"):
                    dim.lower_deviation = tol.deviation_lower
                if hasattr(tol, "iso_tolerance_class"):
                    dim.tolerance_grade = tol.iso_tolerance_class
                    dim.tolerance_type = "iso"

            # Dimension type
            if hasattr(measure, "measure_type"):
                mtype = str(measure.measure_type).lower()
                if "diameter" in mtype:
                    dim.dimension_type = "diameter"
                elif "radius" in mtype:
                    dim.dimension_type = "radius"
                elif "angle" in mtype or "angular" in mtype:
                    dim.dimension_type = "angular"

            return dim

        except Exception as e:
            logger.debug("Error parsing measure: %s", e)
            return None

    def _parse_gdt(self, gdt: Any) -> Werk24GDT | None:
        """Parse a GDT response into a Werk24GDT."""
        try:
            result = Werk24GDT(
                characteristic_type=str(gdt.characteristic_type).lower(),
                tolerance_value=gdt.tolerance.value if gdt.tolerance else 0.0,
            )

            if hasattr(gdt, "material_condition") and gdt.material_condition:
                result.material_condition = str(gdt.material_condition)

            if hasattr(gdt, "datums") and gdt.datums:
                result.datums = [str(d.letter) for d in gdt.datums]

            return result

        except Exception as e:
            logger.debug("Error parsing GDT: %s", e)
            return None

    def _parse_title_block(self, payload: Any) -> ExtractedTitleBlock:
        """Parse title block response."""
        title_block = ExtractedTitleBlock()

        try:
            if hasattr(payload, "drawing_number"):
                title_block.drawing_number = payload.drawing_number
            if hasattr(payload, "title"):
                title_block.title = payload.title
            if hasattr(payload, "revision"):
                title_block.revision = payload.revision
            if hasattr(payload, "date"):
                title_block.date = str(payload.date)
            if hasattr(payload, "author") or hasattr(payload, "designer"):
                title_block.author = getattr(payload, "author", None) or getattr(
                    payload, "designer", None
                )
            if hasattr(payload, "company"):
                title_block.company = payload.company
            if hasattr(payload, "scale"):
                title_block.scale = str(payload.scale)
            if hasattr(payload, "material"):
                title_block.material = payload.material

        except Exception as e:
            logger.debug("Error parsing title block: %s", e)

        return title_block

    def _parse_material(self, payload: Any) -> dict[str, Any] | None:
        """Parse material response."""
        try:
            material = {
                "designation": getattr(payload, "designation", None),
                "standard": getattr(payload, "standard", None),
                "material_type": getattr(payload, "material_type", None),
            }
            return {k: v for k, v in material.items() if v is not None}

        except Exception as e:
            logger.debug("Error parsing material: %s", e)
            return None

    def _parse_overall_dimensions(self, payload: Any) -> dict[str, float] | None:
        """Parse overall dimensions response."""
        try:
            dims = {}
            if hasattr(payload, "length") and payload.length:
                dims["length"] = payload.length.value
            if hasattr(payload, "width") and payload.width:
                dims["width"] = payload.width.value
            if hasattr(payload, "height") and payload.height:
                dims["height"] = payload.height.value
            return dims if dims else None

        except Exception as e:
            logger.debug("Error parsing overall dimensions: %s", e)
            return None

    def _process_collected_data(
        self, collected_data: dict[str, Any], result: Werk24ExtractionResult
    ) -> None:
        """Process collected API responses into the result."""
        # Dimensions
        result.dimensions = collected_data.get("dimensions", [])

        # GDTs
        result.gdts = collected_data.get("gdts", [])

        # Title block
        if collected_data.get("title_block"):
            result.title_block = collected_data["title_block"]

        # Materials
        result.materials = collected_data.get("materials", [])

        # Overall dimensions
        result.overall_dimensions = collected_data.get("overall_dimensions")

        # Thumbnails
        result.thumbnails = collected_data.get("thumbnails", {})

        # Also populate the base class dimensions list
        result.dimensions_list = [d.to_extracted_dimension() for d in result.dimensions]


# Simplified sync wrapper for common use case
def extract_drawing(
    file_path: str | Path,
    api_key: str | None = None,
) -> Werk24ExtractionResult:
    """Convenience function to extract from a drawing file.

    Args:
        file_path: Path to the drawing file (PDF, PNG, etc.)
        api_key: Werk24 API key. If not provided, reads from WERK24_API_KEY env var.

    Returns:
        Werk24ExtractionResult with extracted information.
    """
    client = Werk24Client(api_key=api_key)
    return client.extract(file_path)
