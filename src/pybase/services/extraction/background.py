"""
Background extraction task for processing files asynchronously.

This module provides the background task that processes extraction jobs,
downloading files from storage and running the appropriate extractor.
"""

import logging
import tempfile
from pathlib import Path
from typing import Any

from pybase.db.session import get_db_context
from pybase.models.extraction_job import ExtractionJobFormat, ExtractionJobStatus
from pybase.services.extraction_job_service import ExtractionJobService

logger = logging.getLogger(__name__)


async def run_extraction_background(job_id: str) -> None:
    """
    Background task to process an extraction job.

    Downloads the file from storage, runs the appropriate extractor,
    and updates the job status with results or error.

    Args:
        job_id: ExtractionJob UUID to process
    """
    async with get_db_context() as db:
        service = ExtractionJobService(db)

        try:
            # Mark job as processing
            job = await service.start_processing(job_id)
            logger.info(f"Processing extraction job {job_id} for {job.filename}")

            # Download file from storage
            temp_path = await _download_file(job.file_url)

            try:
                # Get extraction options
                options = job.get_options()

                # Run extraction based on format
                result = await _run_extraction(
                    file_path=temp_path,
                    format=ExtractionJobFormat(job.format),
                    filename=job.filename,
                    options=options,
                )

                # Mark job as completed with result
                await service.complete_job(job_id, result)
                logger.info(f"Completed extraction job {job_id}")

            finally:
                # Clean up temp file
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)

        except Exception as e:
            logger.exception(f"Extraction job {job_id} failed: {e}")
            await service.fail_job(
                job_id,
                error_message=str(e),
                schedule_retry=True,
            )


async def _download_file(file_url: str) -> Path:
    """
    Download file from storage URL to temp file.

    Args:
        file_url: S3/B2 URL or remote file path to download

    Returns:
        Path to downloaded temp file
    """
    # Import storage service
    from pybase.services.b2_storage import B2StorageService

    storage = B2StorageService()

    # Create temp file with appropriate suffix
    suffix = Path(file_url).suffix or ".tmp"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_path = Path(temp_file.name)
    temp_file.close()

    try:
        # Extract remote name from URL if it's a full URL
        # B2 URLs look like: https://f000.backblazeb2.com/file/bucket-name/path/to/file.pdf
        # or just the path: path/to/file.pdf
        if file_url.startswith("http"):
            # Parse URL to get the file path
            from urllib.parse import urlparse

            parsed = urlparse(file_url)
            # Path format: /file/bucket-name/path/to/file.pdf
            path_parts = parsed.path.split("/")
            if len(path_parts) > 3 and path_parts[1] == "file":
                # Skip /file/bucket-name/ prefix
                remote_name = "/".join(path_parts[3:])
            else:
                remote_name = parsed.path.lstrip("/")
        else:
            remote_name = file_url

        # Download from storage
        await storage.download_file(remote_name, temp_path)
        return temp_path
    except Exception as e:
        temp_path.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to download file from {file_url}: {e}") from e


async def _run_extraction(
    file_path: Path,
    format: ExtractionJobFormat,
    filename: str,
    options: dict[str, Any],
) -> dict[str, Any]:
    """
    Run extraction based on file format.

    Args:
        file_path: Path to local file
        format: Extraction format
        filename: Original filename
        options: Format-specific extraction options

    Returns:
        Extraction result dict
    """
    if format == ExtractionJobFormat.PDF:
        return await _extract_pdf(file_path, filename, options)
    elif format == ExtractionJobFormat.DXF:
        return await _extract_dxf(file_path, filename, options)
    elif format == ExtractionJobFormat.IFC:
        return await _extract_ifc(file_path, filename, options)
    elif format == ExtractionJobFormat.STEP:
        return await _extract_step(file_path, filename, options)
    elif format == ExtractionJobFormat.WERK24:
        return await _extract_werk24(file_path, filename, options)
    else:
        raise ValueError(f"Unsupported extraction format: {format}")


async def _extract_pdf(
    file_path: Path,
    filename: str,
    options: dict[str, Any],
) -> dict[str, Any]:
    """Extract data from PDF file."""
    try:
        from pybase.extraction import PDFExtractor
    except ImportError as e:
        raise RuntimeError(f"PDF extraction not available: {e}") from e

    extractor = PDFExtractor(
        enable_ocr=options.get("use_ocr", False),
        ocr_language=options.get("ocr_language", "eng"),
    )

    result = extractor.extract(
        str(file_path),
        extract_tables=options.get("extract_tables", True),
        extract_text=options.get("extract_text", True),
        extract_dimensions=options.get("extract_dimensions", False),
        extract_title_block=options.get("extract_title_block", False),
        pages=options.get("pages"),
        use_ocr=options.get("use_ocr", False),
    )

    return _result_to_dict(result, filename, "pdf")


async def _extract_dxf(
    file_path: Path,
    filename: str,
    options: dict[str, Any],
) -> dict[str, Any]:
    """Extract data from DXF file."""
    try:
        from pybase.extraction import DXFParser
    except ImportError as e:
        raise RuntimeError(f"DXF extraction not available: {e}") from e

    parser = DXFParser()
    result = parser.parse(
        str(file_path),
        extract_layers=options.get("extract_layers", True),
        extract_blocks=options.get("extract_blocks", True),
        extract_dimensions=options.get("extract_dimensions", True),
        extract_text=options.get("extract_text", True),
        extract_title_block=options.get("extract_title_block", True),
        extract_geometry=options.get("extract_geometry", False),
        include_model_space=options.get("include_model_space", True),
        include_paper_space=options.get("include_paper_space", True),
        layer_filter=options.get("layer_filter"),
    )

    return _result_to_dict(result, filename, "dxf")


async def _extract_ifc(
    file_path: Path,
    filename: str,
    options: dict[str, Any],
) -> dict[str, Any]:
    """Extract data from IFC file."""
    try:
        from pybase.extraction import IFCParser
    except ImportError as e:
        raise RuntimeError(f"IFC extraction not available: {e}") from e

    parser = IFCParser()
    result = parser.parse(
        str(file_path),
        extract_properties=options.get("extract_properties", True),
        extract_quantities=options.get("extract_quantities", True),
        extract_materials=options.get("extract_materials", True),
        extract_spatial_structure=options.get("extract_spatial_structure", True),
        element_types=options.get("element_types"),
        include_geometry=options.get("include_geometry", False),
    )

    return _result_to_dict(result, filename, "ifc")


async def _extract_step(
    file_path: Path,
    filename: str,
    options: dict[str, Any],
) -> dict[str, Any]:
    """Extract data from STEP file."""
    try:
        from pybase.extraction import STEPParser
    except ImportError as e:
        raise RuntimeError(f"STEP extraction not available: {e}") from e

    parser = STEPParser()
    result = parser.parse(
        str(file_path),
        extract_assembly=options.get("extract_assembly", True),
        extract_parts=options.get("extract_parts", True),
        calculate_volumes=options.get("calculate_volumes", True),
        calculate_areas=options.get("calculate_areas", True),
        calculate_centroids=options.get("calculate_centroids", False),
        count_shapes=options.get("count_shapes", True),
    )

    return _result_to_dict(result, filename, "step")


async def _extract_werk24(
    file_path: Path,
    filename: str,
    options: dict[str, Any],
) -> dict[str, Any]:
    """Extract data from file using Werk24 API."""
    try:
        from pybase.extraction import Werk24Client
    except ImportError as e:
        raise RuntimeError(f"Werk24 extraction not available: {e}") from e

    client = Werk24Client()
    result = await client.extract(
        str(file_path),
        extract_dimensions=options.get("extract_dimensions", True),
        extract_gdt=options.get("extract_gdt", True),
        extract_threads=options.get("extract_threads", True),
        extract_surface_finish=options.get("extract_surface_finish", True),
        extract_materials=options.get("extract_materials", True),
        extract_title_block=options.get("extract_title_block", True),
        confidence_threshold=options.get("confidence_threshold", 0.7),
    )

    return _result_to_dict(result, filename, "werk24")


def _result_to_dict(result: Any, filename: str, source_type: str) -> dict[str, Any]:
    """
    Convert extraction result to dict for storage.

    Args:
        result: Extraction result object
        filename: Original filename
        source_type: Type of extraction (pdf, dxf, etc.)

    Returns:
        Dict representation of result
    """
    if hasattr(result, "to_dict"):
        return result.to_dict()

    # Fallback for results without to_dict method
    base = {
        "source_file": filename,
        "source_type": source_type,
        "success": getattr(result, "success", True),
        "errors": getattr(result, "errors", []),
        "warnings": getattr(result, "warnings", []),
        "metadata": getattr(result, "metadata", {}),
    }

    # Add format-specific fields
    if hasattr(result, "tables"):
        base["tables"] = [_serialize_item(t) for t in result.tables]
    if hasattr(result, "dimensions"):
        base["dimensions"] = [_serialize_item(d) for d in result.dimensions]
    if hasattr(result, "text_blocks"):
        base["text_blocks"] = [_serialize_item(t) for t in result.text_blocks]
    if hasattr(result, "title_block") and result.title_block:
        base["title_block"] = _serialize_item(result.title_block)
    if hasattr(result, "layers"):
        base["layers"] = [_serialize_item(l) for l in result.layers]
    if hasattr(result, "blocks"):
        base["blocks"] = [_serialize_item(b) for b in result.blocks]
    if hasattr(result, "geometry_summary") and result.geometry_summary:
        base["geometry_summary"] = _serialize_item(result.geometry_summary)
    if hasattr(result, "entities"):
        base["entities"] = [_serialize_item(e) for e in result.entities]

    return base


def _serialize_item(item: Any) -> dict[str, Any]:
    """Serialize a single item to dict."""
    if hasattr(item, "to_dict"):
        return item.to_dict()
    if hasattr(item, "__dict__"):
        return {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
    return {"value": str(item)}
