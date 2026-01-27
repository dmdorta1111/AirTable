"""CosCAD gRPC client for PyBase.

Provides integration with CosCAD extraction service for aerospace/automotive CAD files:
- Geometry metadata extraction (faces, edges, vertices, surfaces)
- Dimension extraction with tolerances and units
- GD&T (Geometric Dimensioning and Tolerancing) recognition
- Annotation and text extraction
- Title block parsing
- Material specification extraction
- Metadata extraction

Service Configuration:
    - Environment variables: COSCAD_SERVICE_HOST, COSCAD_SERVICE_PORT
    - Default host: localhost
    - Default port: 50051
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, BinaryIO, TYPE_CHECKING
from enum import Enum

from pybase.extraction.base import (
    ExtractionResult,
    ExtractedDimension,
    ExtractedText,
    ExtractedTitleBlock,
)
from pybase.extraction.cad.coscad_grpc_stub import (
    CosCADExtractionType,
    CosCADExtractionRequest,
    CosCADExtractionResponse,
    CosCADServiceStub,
    GRPC_AVAILABLE,
    CosCADGeometry,
    CosCADDimension,
    CosCADGDT,
    CosCADAnnotation,
    CosCADMaterial,
    CosCADMetadata,
    check_service_availability,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CosCADExtractionError(str, Enum):
    """Error types for CosCAD extraction."""

    SERVICE_UNAVAILABLE = "service_unavailable"
    CONNECTION_FAILED = "connection_failed"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid_request"
    FILE_CORRUPTED = "file_corrupted"
    UNSUPPORTED_VERSION = "unsupported_version"
    PARSE_ERROR = "parse_error"
    EXTRACTION_ERROR = "extraction_error"
    INTERNAL_ERROR = "internal_error"


@dataclass
class CosCADExtractionResult(ExtractionResult):
    """Extended result for CosCAD extraction."""

    geometries: list[CosCADGeometry] = field(default_factory=list)
    dimensions: list[CosCADDimension] = field(default_factory=list)
    gdts: list[CosCADGDT] = field(default_factory=list)
    annotations: list[CosCADAnnotation] = field(default_factory=list)
    materials: list[CosCADMaterial] = field(default_factory=list)
    metadata: CosCADMetadata | None = None
    raw_responses: list[dict[str, Any]] = field(default_factory=list)
    processing_time_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        base = super().to_dict()
        base.update(
            {
                "geometries": [g.to_dict() for g in self.geometries],
                "dimensions": [d.to_dict() for d in self.dimensions],
                "gdts": [g.to_dict() for g in self.gdts],
                "annotations": [a.to_dict() for a in self.annotations],
                "materials": [m.to_dict() for m in self.materials],
                "metadata": self.metadata.to_dict() if self.metadata else None,
                "processing_time_ms": self.processing_time_ms,
            }
        )
        return base


class CosCADClient:
    """Client for the CosCAD extraction gRPC service.

    Provides extraction capabilities for CosCAD CAD files used in aerospace
    and automotive industries through a gRPC service interface.

    Example:
        client = CosCADClient(host="localhost", port=50051)

        # Synchronous usage
        result = client.extract("drawing.coscad")

        # Async usage
        result = await client.extract_async("drawing.coscad")

        # Access extracted data
        for dim in result.dimensions:
            print(f"{dim.nominal_value} {dim.unit}")

    Service Configuration:
        Use environment variables:
        - COSCAD_SERVICE_HOST: Service host (default: localhost)
        - COSCAD_SERVICE_PORT: Service port (default: 50051)
    """

    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 50051
    DEFAULT_TIMEOUT = 300.0  # 5 minutes
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        retry_delay: float = RETRY_DELAY,
    ):
        """Initialize the CosCAD client.

        Args:
            host: CosCAD service host. If not provided, reads from COSCAD_SERVICE_HOST env var.
            port: CosCAD service port. If not provided, reads from COSCAD_SERVICE_PORT env var.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts for failed requests.
            retry_delay: Delay between retries in seconds.
        """
        import os

        self.host = host or os.environ.get("COSCAD_SERVICE_HOST", self.DEFAULT_HOST)
        self.port = port or int(os.environ.get("COSCAD_SERVICE_PORT", str(self.DEFAULT_PORT)))
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._channel = None
        self._stub = None

        if not GRPC_AVAILABLE:
            logger.warning("grpcio not available. Install with: pip install grpcio>=1.60.0")

    @property
    def address(self) -> str:
        """Get the service address."""
        return f"{self.host}:{self.port}"

    def is_service_available(self) -> bool:
        """Check if the CosCAD service is available.

        Returns:
            True if service is available, False otherwise.
        """
        return check_service_availability(host=self.host, port=self.port)

    def extract(
        self,
        source: str | Path | BinaryIO,
        extraction_types: list[CosCADExtractionType] | None = None,
        db: "AsyncSession | None" = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
        file_size: int | None = None,
        file_type: str | None = None,
        **options,
    ) -> CosCADExtractionResult:
        """Extract information from a CosCAD file (synchronous).

        Args:
            source: File path or file-like object containing the CosCAD file.
            extraction_types: Types of extraction to perform. Defaults to all types.
            db: Optional database session for usage tracking.
            user_id: Optional user ID for usage tracking.
            workspace_id: Optional workspace ID for usage tracking.
            file_size: Optional file size in bytes for usage tracking.
            file_type: Optional file type for usage tracking.
            **options: Additional options for the extraction service.

        Returns:
            CosCADExtractionResult with extracted information.
        """
        return asyncio.run(
            self.extract_async(
                source,
                extraction_types,
                db=db,
                user_id=user_id,
                workspace_id=workspace_id,
                file_size=file_size,
                file_type=file_type,
                **options,
            )
        )

    async def extract_async(
        self,
        source: str | Path | BinaryIO,
        extraction_types: list[CosCADExtractionType] | None = None,
        db: "AsyncSession | None" = None,
        user_id: str | None = None,
        workspace_id: str | None = None,
        file_size: int | None = None,
        file_type: str | None = None,
        **options,
    ) -> CosCADExtractionResult:
        """Extract information from a CosCAD file (asynchronous).

        Args:
            source: File path or file-like object containing the CosCAD file.
            extraction_types: Types of extraction to perform. Defaults to all types.
            db: Optional database session for usage tracking.
            user_id: Optional user ID for usage tracking.
            workspace_id: Optional workspace ID for usage tracking.
            file_size: Optional file size in bytes for usage tracking.
            file_type: Optional file type for usage tracking.
            **options: Additional options for the extraction service.

        Returns:
            CosCADExtractionResult with extracted information.
        """
        source_file = str(source) if isinstance(source, (str, Path)) else "<stream>"

        result = CosCADExtractionResult(
            source_file=source_file,
            source_type="coscad",
        )

        start_time = time.time()

        if not GRPC_AVAILABLE:
            result.errors.append(
                "grpcio not installed. Install with: pip install grpcio>=1.60.0"
            )
            return result

        # Default to all extraction types
        if extraction_types is None:
            extraction_types = [
                CosCADExtractionType.GEOMETRY,
                CosCADExtractionType.DIMENSIONS,
                CosCADExtractionType.ANNOTATIONS,
                CosCADExtractionType.METADATA,
                CosCADExtractionType.TITLE_BLOCK,
                CosCADExtractionType.MATERIALS,
                CosCADExtractionType.GDT,
            ]

        try:
            # Read file content
            file_content = await self._read_file_content(source)

            # Create extraction request
            request = CosCADExtractionRequest(
                file_content=file_content,
                extraction_types=extraction_types,
                options=options,
            )

            # Execute extraction with retries
            response = await self._execute_with_retries(request)

            # Process response
            self._process_response(response, result)

            # Update processing time
            result.processing_time_ms = int((time.time() - start_time) * 1000)

            # Log warnings from service
            if response.warnings:
                for warning in response.warnings:
                    logger.warning(f"CosCAD service warning: {warning}")
                    result.warnings.append(warning)

        except Exception as e:
            result.errors.append(f"CosCAD extraction error: {e}")
            logger.exception("Error extracting from CosCAD file")
            result.processing_time_ms = int((time.time() - start_time) * 1000)

        return result

    async def _read_file_content(self, source: str | Path | BinaryIO) -> bytes:
        """Read file content from path or stream.

        Args:
            source: File path or file-like object.

        Returns:
            File content as bytes.

        Raises:
            FileNotFoundError: If file path doesn't exist.
            IOError: If file cannot be read.
        """
        if isinstance(source, (str, Path)):
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"CosCAD file not found: {source}")
            with open(source, "rb") as f:
                return f.read()
        else:
            return source.read()

    async def _execute_with_retries(
        self, request: CosCADExtractionRequest
    ) -> CosCADExtractionResponse:
        """Execute extraction request with retry logic.

        Args:
            request: Extraction request.

        Returns:
            Extraction response.

        Raises:
            CosCADExtractionError: If all retries fail.
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Create channel if not exists
                if self._channel is None:
                    await self._create_async_channel()

                # Create stub if not exists
                if self._stub is None:
                    self._stub = CosCADServiceStub(
                        host=self.host,
                        port=self.port,
                        timeout=self.timeout,
                    )

                # Execute extraction (mock implementation - replace with actual gRPC call)
                # This is where the actual gRPC call would be made
                # For now, we'll raise NotImplementedError as per the stub
                response = await self._mock_extract(request)

                return response

            except Exception as e:
                last_error = e
                logger.warning(
                    f"CosCAD extraction attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )

                if attempt < self.max_retries - 1:
                    # Close channel and retry
                    await self._close_async_channel()
                    await asyncio.sleep(self.retry_delay)
                else:
                    # All retries exhausted
                    raise CosCADExtractionError.EXTRACTION_ERROR from last_error

        # Should never reach here, but just in case
        raise CosCADExtractionError.EXTRACTION_ERROR from last_error

    async def _mock_extract(
        self, request: CosCADExtractionRequest
    ) -> CosCADExtractionResponse:
        """Mock extraction method for testing.

        This is a placeholder. In production, this would make the actual gRPC call
        using the generated stub from protobuf definitions.

        Args:
            request: Extraction request.

        Returns:
            Mock extraction response.

        Raises:
            NotImplementedError: Always raised as this is a stub implementation.
        """
        # This is where the actual gRPC call would be made
        # Example: response = await self._stub.extract_async(request)
        raise NotImplementedError(
            "CosCAD gRPC client is a stub implementation. "
            "The actual CosCAD extraction service must be implemented separately. "
            "Once implemented, replace this method with the actual gRPC call."
        )

    async def _create_async_channel(self) -> None:
        """Create async gRPC channel."""
        if not GRPC_AVAILABLE:
            raise CosCADExtractionError.SERVICE_UNAVAILABLE

        try:
            import grpc.aio as aio_grpc

            self._channel = aio_grpc.insecure_channel(self.address)
            logger.info(f"Created async gRPC channel to {self.address}")

            # Wait for channel to be ready
            await asyncio.wait_for(
                self._channel.channel_ready(), timeout=5.0
            )
            logger.debug(f"gRPC channel to {self.address} is ready")

        except asyncio.TimeoutError:
            await self._close_async_channel()
            raise CosCADExtractionError.CONNECTION_FAILED(
                f"Timeout connecting to CosCAD service at {self.address}"
            )
        except Exception as e:
            await self._close_async_channel()
            logger.error(f"Failed to create gRPC channel: {e}")
            raise CosCADExtractionError.CONNECTION_FAILED from e

    async def _close_async_channel(self) -> None:
        """Close async gRPC channel."""
        if self._channel:
            try:
                await self._channel.close()
                logger.debug(f"Closed gRPC channel to {self.address}")
            except Exception as e:
                logger.warning(f"Error closing gRPC channel: {e}")
            finally:
                self._channel = None
                self._stub = None

    def _process_response(
        self,
        response: CosCADExtractionResponse,
        result: CosCADExtractionResult,
    ) -> None:
        """Process extraction response into result.

        Args:
            response: gRPC service response.
            result: Result object to populate.
        """
        if not response.success:
            error_msg = response.error_message or "Unknown extraction error"
            result.errors.append(f"CosCAD service error: {error_msg}")
            if response.error_code:
                result.errors.append(f"Error code: {response.error_code}")
            return

        # Extract geometries
        result.geometries = response.geometries

        # Extract dimensions and convert to standard format
        result.dimensions = response.dimensions
        result.dimensions_list = [
            d.to_extracted_dimension() for d in response.dimensions
        ]

        # Extract GD&T
        result.gdts = response.gdts

        # Extract annotations
        result.annotations = response.annotations
        result.text_list = [
            a.to_extracted_text() for a in response.annotations
        ]

        # Extract materials
        result.materials = response.materials

        # Extract metadata
        if response.metadata:
            result.metadata = response.metadata

            # Try to populate title block from metadata
            # This is a simplified mapping - actual implementation would depend on
            # how the CosCAD service structures title block information
            if any(
                field in response.metadata.custom_properties
                for field in ["title", "drawing_number", "revision"]
            ):
                title_block = ExtractedTitleBlock()
                title_block.title = response.metadata.custom_properties.get("title")
                title_block.drawing_number = response.metadata.custom_properties.get(
                    "drawing_number"
                )
                title_block.revision = response.metadata.custom_properties.get("revision")
                title_block.author = response.metadata.author
                title_block.company = response.metadata.organization
                title_block.date = response.metadata.created_date
                result.title_block = title_block

        # Store raw response for debugging
        result.raw_responses.append(response.to_dict())


# Convenience function for simple extraction
def extract_coscad_file(
    file_path: str | Path,
    host: str | None = None,
    port: int | None = None,
) -> CosCADExtractionResult:
    """Convenience function to extract from a CosCAD file.

    Args:
        file_path: Path to the CosCAD file.
        host: Optional CosCAD service host.
        port: Optional CosCAD service port.

    Returns:
        CosCADExtractionResult with extracted information.
    """
    client = CosCADClient(host=host, port=port)
    return client.extract(file_path)
