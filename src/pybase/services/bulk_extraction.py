"""Bulk extraction service for parallel multi-file processing."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from pybase.models.extraction_job import ExtractionFormat
from pybase.schemas.extraction import (
    BulkExtractionResponse,
    CADExtractionResponse,
    ExtractionFormat as SchemaExtractionFormat,
    FileExtractionStatus,
    JobStatus,
    PDFExtractionResponse,
    Werk24ExtractionResponse,
)
from pybase.services.extraction_job_service import ExtractionJobService

logger = logging.getLogger(__name__)


class BulkExtractionService:
    """Service for processing multiple files in parallel with database-backed job tracking."""

    def __init__(self, db: AsyncSession, job_id: str) -> None:
        """
        Initialize bulk extraction service with database session and job ID.

        Args:
            db: Async database session for persistence
            job_id: Extraction job ID to track progress in database
        """
        self.db = db
        self.job_id = job_id
        self.job_service = ExtractionJobService(db)
        self.max_concurrent_extractions = 5  # Limit concurrent file processing

    async def process_files(
        self,
        file_paths: list[str],
        format_override: Optional[ExtractionFormat] = None,
        options: Optional[dict[str, Any]] = None,
        auto_detect_format: bool = True,
        continue_on_error: bool = True,
    ) -> BulkExtractionResponse:
        """
        Process multiple files in parallel with progress tracking.

        Args:
            file_paths: List of file paths to extract
            format_override: Optional format to use for all files
            options: Format-specific extraction options
            auto_detect_format: Auto-detect file format from extension
            continue_on_error: Continue processing other files if one fails

        Returns:
            BulkExtractionResponse with per-file status and results

        """
        bulk_job_id = uuid.uuid4()
        created_at = datetime.now(timezone.utc)
        options = options or {}

        # Create database jobs for each file
        file_statuses: list[FileExtractionStatus] = []
        for file_path in file_paths:
            path = Path(file_path)
            detected_format = format_override or self._detect_format(path)

            # Get file size
            try:
                file_size = path.stat().st_size
            except OSError:
                file_size = 0

            # Convert schema format to model format
            format_value = (
                detected_format.value
                if isinstance(detected_format, SchemaExtractionFormat)
                else detected_format
            )

            # Create database job
            try:
                job = await self.job_service.create_job(
                    filename=path.name,
                    file_url=file_path,
                    file_size=file_size,
                    format=format_value,
                    options=options,
                    skip_duplicate_check=True,  # Allow multiple bulk jobs for same files
                )
                db_job_id = job.id
            except Exception as e:
                logger.error(f"Failed to create job for {file_path}: {e}")
                db_job_id = str(uuid.uuid4())

            file_statuses.append(
                FileExtractionStatus(
                    file_path=file_path,
                    filename=path.name,
                    format=detected_format,
                    status=JobStatus.PENDING,
                    job_id=db_job_id,  # Use database job ID
                    progress=0,
                    result=None,
                    error_message=None,
                    started_at=None,
                    completed_at=None,
                )
            )

        # Process files in parallel with concurrency limit
        semaphore = asyncio.Semaphore(self.max_concurrent_extractions)

        async def process_file_with_semaphore(
            file_status: FileExtractionStatus,
        ) -> FileExtractionStatus:
            """Process a single file with semaphore for concurrency control."""
            async with semaphore:
                return await self._process_single_file(
                    file_status=file_status,
                    options=options,
                    continue_on_error=continue_on_error,
                )

        # Process all files
        started_at = datetime.now(timezone.utc)
        processed_statuses = await asyncio.gather(
            *[process_file_with_semaphore(status) for status in file_statuses],
            return_exceptions=continue_on_error,
        )

        # Handle exceptions if continue_on_error is True
        final_statuses: list[FileExtractionStatus] = []
        for i, result in enumerate(processed_statuses):
            if isinstance(result, Exception):
                # Mark as failed
                status = file_statuses[i]
                status.status = JobStatus.FAILED
                status.error_message = str(result)
                status.completed_at = datetime.now(timezone.utc)

                # Update database job status to FAILED
                try:
                    await self.job_service.fail_job(
                        str(status.job_id),
                        str(result),
                        schedule_retry=False,
                    )
                except Exception as e:
                    logger.warning(f"Failed to update job status to FAILED: {e}")

                final_statuses.append(status)
            else:
                final_statuses.append(result)

        completed_at = datetime.now(timezone.utc)

        # Calculate statistics
        files_completed = sum(
            1 for s in final_statuses if s.status == JobStatus.COMPLETED
        )
        files_failed = sum(1 for s in final_statuses if s.status == JobStatus.FAILED)
        files_pending = sum(1 for s in final_statuses if s.status == JobStatus.PENDING)

        # Determine overall status
        if files_failed == len(final_statuses):
            overall_status = JobStatus.FAILED
        elif files_completed == len(final_statuses):
            overall_status = JobStatus.COMPLETED
        elif files_pending > 0:
            overall_status = JobStatus.PROCESSING
        else:
            overall_status = JobStatus.COMPLETED

        # Calculate overall progress
        total_progress = sum(s.progress for s in final_statuses)
        overall_progress = total_progress // len(final_statuses) if final_statuses else 0

        return BulkExtractionResponse(
            bulk_job_id=bulk_job_id,
            total_files=len(file_paths),
            files=final_statuses,
            overall_status=overall_status,
            progress=overall_progress,
            files_completed=files_completed,
            files_failed=files_failed,
            files_pending=files_pending,
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
        )

    async def _process_single_file(
        self,
        file_status: FileExtractionStatus,
        options: dict[str, Any],
        continue_on_error: bool,
    ) -> FileExtractionStatus:
        """
        Process a single file and update its status in the database.

        Args:
            file_status: File status object to update
            options: Extraction options
            continue_on_error: Whether to catch exceptions or raise them

        Returns:
            Updated FileExtractionStatus

        """
        file_status.started_at = datetime.now(timezone.utc)
        file_status.status = JobStatus.PROCESSING
        file_status.progress = 10

        # Update database job status to PROCESSING
        try:
            await self.job_service.start_processing(str(file_status.job_id))
        except Exception as e:
            logger.warning(f"Failed to update job status to PROCESSING: {e}")

        try:
            # Extract based on format
            result: dict[str, Any]
            if file_status.format == SchemaExtractionFormat.PDF:
                result = await self._extract_pdf(file_status.file_path, options)
            elif file_status.format == SchemaExtractionFormat.DXF:
                result = await self._extract_dxf(file_status.file_path, options)
            elif file_status.format == SchemaExtractionFormat.IFC:
                result = await self._extract_ifc(file_status.file_path, options)
            elif file_status.format == SchemaExtractionFormat.STEP:
                result = await self._extract_step(file_status.file_path, options)
            elif file_status.format == SchemaExtractionFormat.WERK24:
                result = await self._extract_werk24(file_status.file_path, options)
            else:
                raise ValueError(f"Unsupported format: {file_status.format}")

            file_status.progress = 90
            file_status.result = result
            file_status.status = JobStatus.COMPLETED
            file_status.progress = 100
            file_status.completed_at = datetime.now(timezone.utc)

            # Update database job status to COMPLETED
            try:
                await self.job_service.complete_job(str(file_status.job_id), result)
            except Exception as e:
                logger.warning(f"Failed to update job status to COMPLETED: {e}")

        except Exception as e:
            file_status.status = JobStatus.FAILED
            file_status.error_message = str(e)
            file_status.progress = 0
            file_status.completed_at = datetime.now(timezone.utc)

            # Update database job status to FAILED
            try:
                await self.job_service.fail_job(
                    str(file_status.job_id),
                    str(e),
                    schedule_retry=False,  # Don't auto-retry in bulk jobs
                )
            except Exception as db_error:
                logger.warning(f"Failed to update job status to FAILED: {db_error}")

            if not continue_on_error:
                raise

        return file_status

    async def _extract_pdf(
        self, file_path: str, options: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract data from PDF file."""
        try:
            from pybase.extraction import PDFExtractor
        except ImportError as e:
            raise ImportError(
                f"PDF extraction not available. Install pdf dependencies: {e}"
            )

        extractor = PDFExtractor()
        path = Path(file_path)

        # Extract with options
        result = await asyncio.to_thread(
            extractor.extract,
            str(path),
            extract_tables=options.get("extract_tables", True),
            extract_text=options.get("extract_text", True),
            extract_dimensions=options.get("extract_dimensions", False),
            use_ocr=options.get("use_ocr", False),
            ocr_language=options.get("ocr_language", "eng"),
            pages=options.get("pages"),
        )

        # Convert to response format
        response = PDFExtractionResponse(
            source_file=path.name,
            source_type="pdf",
            success=True,
            tables=result.tables if hasattr(result, "tables") else [],
            dimensions=result.dimensions if hasattr(result, "dimensions") else [],
            text_blocks=result.text_blocks if hasattr(result, "text_blocks") else [],
            title_block=result.title_block if hasattr(result, "title_block") else None,
            bom=result.bom if hasattr(result, "bom") else None,
            metadata=result.metadata if hasattr(result, "metadata") else {},
            errors=result.errors if hasattr(result, "errors") else [],
            warnings=result.warnings if hasattr(result, "warnings") else [],
        )

        return response.model_dump()

    async def _extract_dxf(
        self, file_path: str, options: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract data from DXF file."""
        try:
            from pybase.extraction import DXFParser
        except ImportError as e:
            raise ImportError(f"DXF extraction not available. Install CAD dependencies: {e}")

        parser = DXFParser()
        path = Path(file_path)

        # Extract with options
        result = await asyncio.to_thread(
            parser.parse,
            str(path),
            extract_layers=options.get("extract_layers", True),
            extract_blocks=options.get("extract_blocks", True),
            extract_dimensions=options.get("extract_dimensions", True),
            extract_text=options.get("extract_text", True),
            extract_title_block=options.get("extract_title_block", True),
            extract_geometry=options.get("extract_geometry", False),
        )

        # Convert to response format
        response = CADExtractionResponse(
            source_file=path.name,
            source_type="dxf",
            success=True,
            layers=result.layers if hasattr(result, "layers") else [],
            blocks=result.blocks if hasattr(result, "blocks") else [],
            dimensions=result.dimensions if hasattr(result, "dimensions") else [],
            text_blocks=result.text_blocks if hasattr(result, "text_blocks") else [],
            title_block=result.title_block if hasattr(result, "title_block") else None,
            geometry_summary=result.geometry_summary if hasattr(result, "geometry_summary") else None,
            entities=result.entities if hasattr(result, "entities") else [],
            metadata=result.metadata if hasattr(result, "metadata") else {},
            errors=result.errors if hasattr(result, "errors") else [],
            warnings=result.warnings if hasattr(result, "warnings") else [],
        )

        return response.model_dump()

    async def _extract_ifc(
        self, file_path: str, options: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract data from IFC file."""
        try:
            from pybase.extraction import IFCParser
        except ImportError as e:
            raise ImportError(f"IFC extraction not available. Install IFC dependencies: {e}")

        parser = IFCParser()
        path = Path(file_path)

        # Extract with options
        result = await asyncio.to_thread(
            parser.parse,
            str(path),
            extract_properties=options.get("extract_properties", True),
            extract_quantities=options.get("extract_quantities", True),
            extract_materials=options.get("extract_materials", True),
            extract_spatial_structure=options.get("extract_spatial_structure", True),
        )

        # Convert to response format
        response = CADExtractionResponse(
            source_file=path.name,
            source_type="ifc",
            success=True,
            layers=[],
            blocks=[],
            dimensions=[],
            text_blocks=[],
            title_block=None,
            geometry_summary=None,
            entities=result.entities if hasattr(result, "entities") else [],
            metadata=result.metadata if hasattr(result, "metadata") else {},
            errors=result.errors if hasattr(result, "errors") else [],
            warnings=result.warnings if hasattr(result, "warnings") else [],
        )

        return response.model_dump()

    async def _extract_step(
        self, file_path: str, options: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract data from STEP file."""
        try:
            from pybase.extraction import STEPParser
        except ImportError as e:
            raise ImportError(
                f"STEP extraction not available. Install STEP dependencies: {e}"
            )

        parser = STEPParser()
        path = Path(file_path)

        # Extract with options
        result = await asyncio.to_thread(
            parser.parse,
            str(path),
            extract_assembly=options.get("extract_assembly", True),
            extract_parts=options.get("extract_parts", True),
            calculate_volumes=options.get("calculate_volumes", True),
            calculate_areas=options.get("calculate_areas", True),
        )

        # Convert to response format
        response = CADExtractionResponse(
            source_file=path.name,
            source_type="step",
            success=True,
            layers=[],
            blocks=[],
            dimensions=[],
            text_blocks=[],
            title_block=None,
            geometry_summary=None,
            entities=result.entities if hasattr(result, "entities") else [],
            metadata=result.metadata if hasattr(result, "metadata") else {},
            errors=result.errors if hasattr(result, "errors") else [],
            warnings=result.warnings if hasattr(result, "warnings") else [],
        )

        return response.model_dump()

    async def _extract_werk24(
        self, file_path: str, options: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract data from engineering drawing using Werk24 API."""
        try:
            from pybase.extraction import Werk24Client
        except ImportError as e:
            raise ImportError(
                f"Werk24 extraction not available. Install werk24 dependencies: {e}"
            )

        client = Werk24Client()
        path = Path(file_path)

        # Extract with options
        result = await asyncio.to_thread(
            client.extract,
            str(path),
            extract_dimensions=options.get("extract_dimensions", True),
            extract_gdt=options.get("extract_gdt", True),
            extract_threads=options.get("extract_threads", True),
            extract_surface_finish=options.get("extract_surface_finish", True),
            extract_materials=options.get("extract_materials", True),
            extract_title_block=options.get("extract_title_block", True),
        )

        # Convert to response format
        response = Werk24ExtractionResponse(
            source_file=path.name,
            source_type="werk24",
            success=True,
            dimensions=result.dimensions if hasattr(result, "dimensions") else [],
            gdt_annotations=result.gdt_annotations if hasattr(result, "gdt_annotations") else [],
            threads=result.threads if hasattr(result, "threads") else [],
            surface_finishes=result.surface_finishes if hasattr(result, "surface_finishes") else [],
            materials=result.materials if hasattr(result, "materials") else [],
            title_block=result.title_block if hasattr(result, "title_block") else None,
            metadata=result.metadata if hasattr(result, "metadata") else {},
            errors=result.errors if hasattr(result, "errors") else [],
            warnings=result.warnings if hasattr(result, "warnings") else [],
        )

        return response.model_dump()

    def _detect_format(self, file_path: Path) -> ExtractionFormat:
        """
        Detect file format from extension.

        Args:
            file_path: Path to the file

        Returns:
            Detected ExtractionFormat

        Raises:
            ValueError: If format cannot be detected

        """
        ext = file_path.suffix.lower()

        format_map = {
            ".pdf": ExtractionFormat.PDF,
            ".dxf": ExtractionFormat.DXF,
            ".dwg": ExtractionFormat.DXF,
            ".ifc": ExtractionFormat.IFC,
            ".stp": ExtractionFormat.STEP,
            ".step": ExtractionFormat.STEP,
            ".png": ExtractionFormat.WERK24,
            ".jpg": ExtractionFormat.WERK24,
            ".jpeg": ExtractionFormat.WERK24,
            ".tif": ExtractionFormat.WERK24,
            ".tiff": ExtractionFormat.WERK24,
        }

        if ext not in format_map:
            raise ValueError(
                f"Cannot detect format for extension '{ext}'. "
                f"Supported: {', '.join(format_map.keys())}"
            )

        return format_map[ext]
