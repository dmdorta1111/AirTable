"""CosCAD gRPC service stub definitions for PyBase.

Provides stub definitions and data types for the CosCAD extraction service gRPC API.
This module defines the service interface and message types used for communicating
with the CosCAD gRPC extraction service.

CosCAD is a CAD format used in aerospace and automotive industries. The gRPC service
provides extraction capabilities for:
- Geometry metadata (faces, edges, vertices, surfaces)
- Dimensions with tolerances and units
- Annotations and text elements
- Title blocks and metadata
- Material specifications
- GD&T (Geometric Dimensioning and Tolerancing) symbols

Note: This is a stub module. The actual gRPC service must be implemented separately.
The protobuf definitions should be compiled with: python -m grpc_tools.protoc -I.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Try to import grpc
try:
    import grpc
    from grpc import aio as aio_grpc

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    grpc = None
    aio_grpc = None


class CosCADExtractionType(str, Enum):
    """Types of extraction requests supported by CosCAD service."""

    GEOMETRY = "geometry"
    DIMENSIONS = "dimensions"
    ANNOTATIONS = "annotations"
    METADATA = "metadata"
    TITLE_BLOCK = "title_block"
    MATERIALS = "materials"
    GDT = "gdt"  # GD&T symbols
    ALL = "all"


class CosCADUnit(str, Enum):
    """Unit systems supported by CosCAD."""

    MILLIMETER = "mm"
    INCH = "inch"
    MICROMETER = "um"
    CENTIMETER = "cm"
    METER = "m"


class CosCADGeometryType(str, Enum):
    """Geometry entity types in CosCAD files."""

    FACE = "face"
    EDGE = "edge"
    VERTEX = "vertex"
    CURVE = "curve"
    SURFACE = "surface"
    SOLID = "solid"
    SHELL = "shell"
    WIRE = "wire"


class CosCADDimensionType(str, Enum):
    """Dimension types in CosCAD files."""

    LINEAR = "linear"
    ANGULAR = "angular"
    RADIAL = "radial"
    DIAMETER = "diameter"
    ORDINATE = "ordinate"
    CHAMFER = "chamfer"


@dataclass
class CosCADPoint3D:
    """3D point in CosCAD space."""

    x: float
    y: float
    z: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass
class CosCADBoundingBox:
    """Bounding box for geometry elements."""

    min_point: "CosCADPoint3D"
    max_point: "CosCADPoint3D"

    def to_dict(self) -> dict[str, Any]:
        return {
            "min": self.min_point.to_dict(),
            "max": self.max_point.to_dict(),
        }


@dataclass
class CosCADGeometry:
    """Geometry entity extracted from CosCAD file."""

    entity_id: str
    geometry_type: "CosCADGeometryType"
    bbox: "CosCADBoundingBox | None" = None
    surface_area: float | None = None
    volume: float | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "geometry_type": self.geometry_type.value,
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "surface_area": self.surface_area,
            "volume": self.volume,
            "properties": self.properties,
            "confidence": self.confidence,
        }


@dataclass
class CosCADDimension:
    """Dimension extracted from CosCAD file."""

    nominal_value: float
    unit: "CosCADUnit" = CosCADUnit.MILLIMETER
    dimension_type: "CosCADDimensionType" = CosCADDimensionType.LINEAR
    tolerance_upper: float | None = None
    tolerance_lower: float | None = None
    tolerance_class: str | None = None  # e.g., "H7", "g6"
    label: str | None = None
    attachment_points: list["CosCADPoint3D"] = field(default_factory=list)
    confidence: float = 1.0

    def to_extracted_dimension(self):  # Removed type hint to avoid forward reference issues
        """Convert to standard ExtractedDimension."""
        from pybase.extraction.base import ExtractedDimension

        return ExtractedDimension(
            value=self.nominal_value,
            unit=self.unit.value,
            tolerance_plus=self.tolerance_upper,
            tolerance_minus=abs(self.tolerance_lower) if self.tolerance_lower else None,
            dimension_type=self.dimension_type.value,
            label=self.tolerance_class or self.label,
            confidence=self.confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "nominal_value": self.nominal_value,
            "unit": self.unit.value,
            "dimension_type": self.dimension_type.value,
            "tolerance_upper": self.tolerance_upper,
            "tolerance_lower": self.tolerance_lower,
            "tolerance_class": self.tolerance_class,
            "label": self.label,
            "attachment_points": [p.to_dict() for p in self.attachment_points],
            "confidence": self.confidence,
        }


@dataclass
class CosCADGDT:
    """GD&T (Geometric Dimensioning and Tolerancing) symbol from CosCAD."""

    symbol_id: str
    characteristic_type: str  # position, flatness, circularity, perpendicularity, etc.
    tolerance_value: float
    tolerance_unit: "CosCADUnit" = CosCADUnit.MILLIMETER
    material_condition: str | None = None  # MMC, LMC, RFS
    datums: list[str] = field(default_factory=list)  # A, B, C, etc.
    affected_features: list[str] = field(default_factory=list)
    placement_point: "CosCADPoint3D | None" = None
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol_id": self.symbol_id,
            "characteristic_type": self.characteristic_type,
            "tolerance_value": self.tolerance_value,
            "tolerance_unit": self.tolerance_unit.value,
            "material_condition": self.material_condition,
            "datums": self.datums,
            "affected_features": self.affected_features,
            "placement_point": self.placement_point.to_dict() if self.placement_point else None,
            "confidence": self.confidence,
        }


@dataclass
class CosCADAnnotation:
    """Text annotation from CosCAD file."""

    text: str
    position: "CosCADPoint3D"
    height: float | None = None
    angle: float = 0.0  # Rotation angle in degrees
    font_name: str | None = None
    annotation_type: str = "text"  # text, leader, note, label
    confidence: float = 1.0

    def to_extracted_text(self):  # Removed type hint to avoid forward reference issues
        """Convert to standard ExtractedText."""
        from pybase.extraction.base import ExtractedText

        return ExtractedText(
            text=self.text,
            confidence=self.confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "position": self.position.to_dict(),
            "height": self.height,
            "angle": self.angle,
            "font_name": self.font_name,
            "annotation_type": self.annotation_type,
            "confidence": self.confidence,
        }


@dataclass
class CosCADMaterial:
    """Material specification from CosCAD file."""

    name: str
    designation: str | None = None  # e.g., "Al 6061-T6"
    standard: str | None = None  # e.g., "ASTM B221"
    properties: dict[str, Any] = field(default_factory=dict)  # density, strength, etc.
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "designation": self.designation,
            "standard": self.standard,
            "properties": self.properties,
            "confidence": self.confidence,
        }


@dataclass
class CosCADMetadata:
    """Metadata extracted from CosCAD file."""

    file_version: str | None = None
    created_by: str | None = None  # Software that created the file
    created_date: str | None = None
    modified_date: str | None = None
    author: str | None = None
    organization: str | None = None
    units: "CosCADUnit" = CosCADUnit.MILLIMETER
    custom_properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_version": self.file_version,
            "created_by": self.created_by,
            "created_date": self.created_date,
            "modified_date": self.modified_date,
            "author": self.author,
            "organization": self.organization,
            "units": self.units.value,
            "custom_properties": self.custom_properties,
        }


@dataclass
class CosCADExtractionRequest:
    """Request message for CosCAD extraction service."""

    file_content: bytes  # CosCAD file binary data
    extraction_types: list["CosCADExtractionType"] = field(default_factory=list)
    request_id: str | None = None
    options: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "extraction_types": [et.value for et in self.extraction_types],
            "request_id": self.request_id,
            "options": self.options,
            # Note: file_content is excluded from dict for logging
        }


@dataclass
class CosCADExtractionResponse:
    """Response message from CosCAD extraction service."""

    request_id: str | None = None
    success: bool = True
    error_message: str | None = None
    error_code: str | None = None
    geometries: list["CosCADGeometry"] = field(default_factory=list)
    dimensions: list["CosCADDimension"] = field(default_factory=list)
    gdts: list["CosCADGDT"] = field(default_factory=list)
    annotations: list["CosCADAnnotation"] = field(default_factory=list)
    materials: list["CosCADMaterial"] = field(default_factory=list)
    metadata: "CosCADMetadata | None" = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "success": self.success,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "geometries": [g.to_dict() for g in self.geometries],
            "dimensions": [d.to_dict() for d in self.dimensions],
            "gdts": [g.to_dict() for g in self.gdts],
            "annotations": [a.to_dict() for a in self.annotations],
            "materials": [m.to_dict() for m in self.materials],
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "warnings": self.warnings,
        }


class CosCADServiceStub:
    """Stub for CosCAD gRPC extraction service.

    This class provides the interface definition for the CosCAD extraction service.
    The actual implementation should be generated from protobuf definitions using:
        python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. coscad.proto

    Example protobuf definition:
        syntax = "proto3";
        package coscad;
        service CosCADExtraction {
            rpc Extract(ExtractionRequest) returns (ExtractionResponse);
            rpc ExtractGeometry(GeometryRequest) returns (GeometryResponse);
            rpc ExtractDimensions(DimensionRequest) returns (DimensionResponse);
        }

    Service endpoint configuration:
        - Default host: localhost
        - Default port: 50051
        - Use environment variables: COSCAD_SERVICE_HOST, COSCAD_SERVICE_PORT
    """

    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 50051
    SERVICE_NAME = "coscad.CosCADExtraction"

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout: float = 300.0,
    ):
        """Initialize the CosCAD service stub.

        Args:
            host: CosCAD service host. Defaults to localhost.
            port: CosCAD service port. Defaults to 50051.
            timeout: Request timeout in seconds.
        """
        import os

        self.host = host or os.environ.get("COSCAD_SERVICE_HOST", self.DEFAULT_HOST)
        self.port = port or int(os.environ.get("COSCAD_SERVICE_PORT", str(self.DEFAULT_PORT)))
        self.timeout = timeout
        self._channel = None

        if not GRPC_AVAILABLE:
            logger.warning("grpcio not available. Install with: pip install grpcio>=1.60.0")

    @property
    def address(self) -> str:
        """Get the service address."""
        return f"{self.host}:{self.port}"

    def create_channel(self) -> "grpc.Channel | None":
        """Create a gRPC channel to the CosCAD service.

        Returns:
            gRPC channel or None if grpc is not available.
        """
        if not GRPC_AVAILABLE:
            logger.error("Cannot create channel: grpcio not installed")
            return None

        try:
            # Create insecure channel (for internal networks)
            # For production, use secure_channel with SSL credentials
            self._channel = grpc.insecure_channel(self.address)
            logger.info(f"Created gRPC channel to {self.address}")
            return self._channel
        except Exception as e:
            logger.error(f"Failed to create gRPC channel: {e}")
            return None

    async def create_async_channel(self) -> "aio_grpc.Channel | None":
        """Create an async gRPC channel to the CosCAD service.

        Returns:
            Async gRPC channel or None if grpc is not available.
        """
        if not GRPC_AVAILABLE:
            logger.error("Cannot create async channel: grpcio not installed")
            return None

        try:
            self._channel = await aio_grpc.insecure_channel(self.address)
            logger.info(f"Created async gRPC channel to {self.address}")
            return self._channel
        except Exception as e:
            logger.error(f"Failed to create async gRPC channel: {e}")
            return None

    def close_channel(self) -> None:
        """Close the gRPC channel."""
        if self._channel:
            try:
                self._channel.close()
                logger.info(f"Closed gRPC channel to {self.address}")
            except Exception as e:
                logger.warning(f"Error closing gRPC channel: {e}")
            finally:
                self._channel = None

    async def close_async_channel(self) -> None:
        """Close the async gRPC channel."""
        if self._channel:
            try:
                await self._channel.close()
                logger.info(f"Closed async gRPC channel to {self.address}")
            except Exception as e:
                logger.warning(f"Error closing async gRPC channel: {e}")
            finally:
                self._channel = None

    def extract(self, request: CosCADExtractionRequest) -> CosCADExtractionResponse:
        """Extract data from CosCAD file (synchronous stub).

        This is a stub method. The actual implementation should use the generated
        gRPC stub from protobuf compilation.

        Args:
            request: Extraction request with file content and options.

        Returns:
            Extraction response with geometry, dimensions, annotations, etc.

        Raises:
            NotImplementedError: This is a stub only.
        """
        raise NotImplementedError(
            "CosCADServiceStub.extract() is a stub method. "
            "Use the CosCADClient class instead, which implements the actual gRPC calls."
        )

    async def extract_async(self, request: CosCADExtractionRequest) -> CosCADExtractionResponse:
        """Extract data from CosCAD file (asynchronous stub).

        This is a stub method. The actual implementation should use the generated
        gRPC async stub from protobuf compilation.

        Args:
            request: Extraction request with file content and options.

        Returns:
            Extraction response with geometry, dimensions, annotations, etc.

        Raises:
            NotImplementedError: This is a stub only.
        """
        raise NotImplementedError(
            "CosCADServiceStub.extract_async() is a stub method. "
            "Use the CosCADClient class instead, which implements the actual gRPC calls."
        )


# Error codes for CosCAD service
class CosCADCErrorCode(str, Enum):
    """Error codes returned by CosCAD extraction service."""

    SUCCESS = "SUCCESS"
    INVALID_REQUEST = "INVALID_REQUEST"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    PARSE_ERROR = "PARSE_ERROR"
    EXTRACTION_ERROR = "EXTRACTION_ERROR"
    TIMEOUT = "TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Service health check
def check_service_availability(host: str | None = None, port: int | None = None) -> bool:
    """Check if CosCAD gRPC service is available.

    Args:
        host: Service host. Defaults to localhost.
        port: Service port. Defaults to 50051.

    Returns:
        True if service is available, False otherwise.
    """
    if not GRPC_AVAILABLE:
        return False

    import os

    host = host or os.environ.get("COSCAD_SERVICE_HOST", CosCADServiceStub.DEFAULT_HOST)
    port = port or int(os.environ.get("COSCAD_SERVICE_PORT", str(CosCADServiceStub.DEFAULT_PORT)))
    address = f"{host}:{port}"

    try:
        with grpc.insecure_channel(address) as channel:
            grpc.channel_ready_future(channel).result(timeout=5)
            logger.info(f"CosCAD service is available at {address}")
            return True
    except Exception as e:
        logger.warning(f"CosCAD service not available at {address}: {e}")
        return False


# Module-level convenience functions
def create_request(
    file_content: bytes,
    extraction_types: list[CosCADExtractionType] | None = None,
    **options,
) -> CosCADExtractionRequest:
    """Create a CosCAD extraction request.

    Args:
        file_content: Binary content of CosCAD file.
        extraction_types: List of extraction types to perform.
        **options: Additional options for the extraction.

    Returns:
        Configured extraction request.
    """
    if extraction_types is None:
        extraction_types = [CosCADExtractionType.ALL]

    return CosCADExtractionRequest(
        file_content=file_content,
        extraction_types=extraction_types,
        options=options,
    )


def convert_to_base_units(value: float, unit: CosCADUnit) -> float:
    """Convert value to millimeters (base unit for PyBase).

    Args:
        value: Value to convert.
        unit: Current unit of the value.

    Returns:
        Value in millimeters.
    """
    conversion_factors = {
        CosCADUnit.MILLIMETER: 1.0,
        CosCADUnit.INCH: 25.4,
        CosCADUnit.MICROMETER: 0.001,
        CosCADUnit.CENTIMETER: 10.0,
        CosCADUnit.METER: 1000.0,
    }
    return value * conversion_factors.get(unit, 1.0)
