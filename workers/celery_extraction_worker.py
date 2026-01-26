#!/usr/bin/env python3
"""
Celery worker for background extraction tasks.

This worker handles multi-format file extraction including PDF, DXF, IFC, STEP, and Werk24.
"""

import sys
import os
from datetime import datetime, timezone
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    print("WARNING: Celery not available. Install: pip install celery")
    sys.exit(1)

# Import worker database helper
from workers.worker_db import run_async, update_job_complete, update_job_start

# Setup logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Create Celery app
app = Celery(
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
    include=["workers.celery_extraction_worker"],
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_default_max_retries=3,  # Default max retries for all tasks
)

# ==============================================================================
# Background Tasks
# ==============================================================================


@app.task(bind=True, name="extract_pdf")
def extract_pdf(self, file_path: str, options: dict = None, job_id: str = None):
    """
    Extract data from PDF file.

    Args:
        self: Celery task instance (for retry support)
        file_path: Path to PDF file
        options: Extraction options (extract_tables, extract_text, use_ocr, etc.)
        job_id: Optional ExtractionJob ID for database tracking

    Returns:
        Dictionary with extraction results
    """
    options = options or {}

    # Update job start in database
    run_async(update_job_start(job_id, self.request.id))

    try:
        from pybase.extraction.pdf.extractor import PDFExtractor

        extractor = PDFExtractor()
        path = Path(file_path)

        logger.info(f"Starting PDF extraction for {file_path} (attempt {self.request.retries + 1})")

        # Run extraction in thread to avoid blocking
        import asyncio

        def run_extraction():
            return extractor.extract(
                str(path),
                extract_tables=options.get("extract_tables", True),
                extract_text=options.get("extract_text", True),
                extract_dimensions=options.get("extract_dimensions", False),
                use_ocr=options.get("use_ocr", False),
                ocr_language=options.get("ocr_language", "eng"),
                pages=options.get("pages"),
            )

        result = asyncio.run(run_extraction())

        # Convert to dict format
        response = {
            "source_file": path.name,
            "source_type": "pdf",
            "success": True,
            "tables": result.tables if hasattr(result, "tables") else [],
            "dimensions": result.dimensions if hasattr(result, "dimensions") else [],
            "text_blocks": result.text_blocks if hasattr(result, "text_blocks") else [],
            "title_block": result.title_block if hasattr(result, "title_block") else None,
            "bom": result.bom if hasattr(result, "bom") else None,
            "metadata": result.metadata if hasattr(result, "metadata") else {},
            "errors": result.errors if hasattr(result, "errors") else [],
            "warnings": result.warnings if hasattr(result, "warnings") else [],
        }

        logger.info(f"PDF extraction completed for {file_path}")

        # Update job complete in database
        run_async(update_job_complete(job_id, "completed", result=response))

        return {"status": "completed", "file_path": file_path, "result": response}

    except ImportError as e:
        logger.error(f"PDF extraction dependencies missing for {file_path}: {e}")
        # Don't retry ImportError - it's a configuration issue
        error_msg = f"PDF extraction not available. Install pdf dependencies: {e}"
        run_async(update_job_complete(job_id, "failed", error_message=error_msg))
        return {
            "status": "failed",
            "file_path": file_path,
            "error": error_msg,
        }
    except Exception as e:
        retry_count = self.request.retries
        max_retries = options.get("max_retries", 3)

        logger.error(f"PDF extraction failed for {file_path} (attempt {retry_count + 1}): {e}")

        if retry_count < max_retries:
            # Exponential backoff: 2^retry_count seconds (1, 2, 4, 8, ...)
            backoff = 2 ** retry_count
            logger.info(f"Retrying PDF extraction for {file_path} in {backoff}s (attempt {retry_count + 1}/{max_retries})")
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(f"PDF extraction failed permanently for {file_path} after {retry_count} attempts")
        run_async(update_job_complete(job_id, "failed", error_message=str(e)))
        return {"status": "failed", "file_path": file_path, "error": str(e)}


@app.task(bind=True, name="extract_dxf")
def extract_dxf(self, file_path: str, options: dict = None, job_id: str = None):
    """
    Extract data from DXF/DWG file.

    Args:
        self: Celery task instance (for retry support)
        file_path: Path to DXF/DWG file
        options: Extraction options (extract_layers, extract_blocks, etc.)
        job_id: Optional ExtractionJob ID for database tracking

    Returns:
        Dictionary with extraction results
    """
    options = options or {}

    # Update job start in database
    run_async(update_job_start(job_id, self.request.id))

    try:
        from pybase.extraction.cad.dxf_parser import DXFParser

        parser = DXFParser()
        path = Path(file_path)

        logger.info(f"Starting DXF extraction for {file_path} (attempt {self.request.retries + 1})")

        # Run extraction in thread to avoid blocking
        import asyncio

        def run_extraction():
            return parser.parse(
                str(path),
                extract_layers=options.get("extract_layers", True),
                extract_blocks=options.get("extract_blocks", True),
                extract_dimensions=options.get("extract_dimensions", True),
                extract_text=options.get("extract_text", True),
                extract_title_block=options.get("extract_title_block", True),
                extract_geometry=options.get("extract_geometry", False),
            )

        result = asyncio.run(run_extraction())

        # Convert to dict format
        response = {
            "source_file": path.name,
            "source_type": "dxf",
            "success": True,
            "layers": result.layers if hasattr(result, "layers") else [],
            "blocks": result.blocks if hasattr(result, "blocks") else [],
            "dimensions": result.dimensions if hasattr(result, "dimensions") else [],
            "text_blocks": result.text_blocks if hasattr(result, "text_blocks") else [],
            "title_block": result.title_block if hasattr(result, "title_block") else None,
            "geometry_summary": result.geometry_summary if hasattr(result, "geometry_summary") else None,
            "entities": result.entities if hasattr(result, "entities") else [],
            "metadata": result.metadata if hasattr(result, "metadata") else {},
            "errors": result.errors if hasattr(result, "errors") else [],
            "warnings": result.warnings if hasattr(result, "warnings") else [],
        }

        logger.info(f"DXF extraction completed for {file_path}")

        # Update job complete in database
        run_async(update_job_complete(job_id, "completed", result=response))

        return {"status": "completed", "file_path": file_path, "result": response}

    except ImportError as e:
        logger.error(f"DXF extraction dependencies missing for {file_path}: {e}")
        # Don't retry ImportError - it's a configuration issue
        error_msg = f"DXF extraction not available. Install CAD dependencies: {e}"
        run_async(update_job_complete(job_id, "failed", error_message=error_msg))
        return {
            "status": "failed",
            "file_path": file_path,
            "error": error_msg,
        }
    except Exception as e:
        retry_count = self.request.retries
        max_retries = options.get("max_retries", 3)

        logger.error(f"DXF extraction failed for {file_path} (attempt {retry_count + 1}): {e}")

        if retry_count < max_retries:
            # Exponential backoff: 2^retry_count seconds (1, 2, 4, 8, ...)
            backoff = 2 ** retry_count
            logger.info(f"Retrying DXF extraction for {file_path} in {backoff}s (attempt {retry_count + 1}/{max_retries})")
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(f"DXF extraction failed permanently for {file_path} after {retry_count} attempts")
        run_async(update_job_complete(job_id, "failed", error_message=str(e)))
        return {"status": "failed", "file_path": file_path, "error": str(e)}


@app.task(bind=True, name="extract_ifc")
def extract_ifc(self, file_path: str, options: dict = None, job_id: str = None):
    """
    Extract data from IFC file.

    Args:
        self: Celery task instance (for retry support)
        file_path: Path to IFC file
        options: Extraction options (extract_properties, extract_quantities, etc.)
        job_id: Optional ExtractionJob ID for database tracking

    Returns:
        Dictionary with extraction results
    """
    options = options or {}

    # Update job start in database
    run_async(update_job_start(job_id, self.request.id))

    try:
        from pybase.extraction.cad.ifc_parser import IFCParser

        parser = IFCParser()
        path = Path(file_path)

        logger.info(f"Starting IFC extraction for {file_path} (attempt {self.request.retries + 1})")

        # Run extraction in thread to avoid blocking
        import asyncio

        def run_extraction():
            return parser.parse(
                str(path),
                extract_properties=options.get("extract_properties", True),
                extract_quantities=options.get("extract_quantities", True),
                extract_materials=options.get("extract_materials", True),
                extract_spatial_structure=options.get("extract_spatial_structure", True),
            )

        result = asyncio.run(run_extraction())

        # Convert to dict format
        response = {
            "source_file": path.name,
            "source_type": "ifc",
            "success": True,
            "layers": [],
            "blocks": [],
            "dimensions": [],
            "text_blocks": [],
            "title_block": None,
            "geometry_summary": None,
            "entities": result.entities if hasattr(result, "entities") else [],
            "metadata": result.metadata if hasattr(result, "metadata") else {},
            "errors": result.errors if hasattr(result, "errors") else [],
            "warnings": result.warnings if hasattr(result, "warnings") else [],
        }

        logger.info(f"IFC extraction completed for {file_path}")

        # Update job complete in database
        run_async(update_job_complete(job_id, "completed", result=response))

        return {"status": "completed", "file_path": file_path, "result": response}

    except ImportError as e:
        logger.error(f"IFC extraction dependencies missing for {file_path}: {e}")
        # Don't retry ImportError - it's a configuration issue
        error_msg = f"IFC extraction not available. Install IFC dependencies: {e}"
        run_async(update_job_complete(job_id, "failed", error_message=error_msg))
        return {
            "status": "failed",
            "file_path": file_path,
            "error": error_msg,
        }
    except Exception as e:
        retry_count = self.request.retries
        max_retries = options.get("max_retries", 3)

        logger.error(f"IFC extraction failed for {file_path} (attempt {retry_count + 1}): {e}")

        if retry_count < max_retries:
            # Exponential backoff: 2^retry_count seconds (1, 2, 4, 8, ...)
            backoff = 2 ** retry_count
            logger.info(f"Retrying IFC extraction for {file_path} in {backoff}s (attempt {retry_count + 1}/{max_retries})")
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(f"IFC extraction failed permanently for {file_path} after {retry_count} attempts")
        run_async(update_job_complete(job_id, "failed", error_message=str(e)))
        return {"status": "failed", "file_path": file_path, "error": str(e)}


@app.task(bind=True, name="extract_step")
def extract_step(self, file_path: str, options: dict = None, job_id: str = None):
    """
    Extract data from STEP file.

    Args:
        self: Celery task instance (for retry support)
        file_path: Path to STEP file
        options: Extraction options (extract_assembly, extract_parts, etc.)
        job_id: Optional ExtractionJob ID for database tracking

    Returns:
        Dictionary with extraction results
    """
    options = options or {}

    # Update job start in database
    run_async(update_job_start(job_id, self.request.id))

    try:
        from pybase.extraction.cad.step_parser import STEPParser

        parser = STEPParser()
        path = Path(file_path)

        logger.info(f"Starting STEP extraction for {file_path} (attempt {self.request.retries + 1})")

        # Run extraction in thread to avoid blocking
        import asyncio

        def run_extraction():
            return parser.parse(
                str(path),
                extract_assembly=options.get("extract_assembly", True),
                extract_parts=options.get("extract_parts", True),
                calculate_volumes=options.get("calculate_volumes", True),
                calculate_areas=options.get("calculate_areas", True),
            )

        result = asyncio.run(run_extraction())

        # Convert to dict format
        response = {
            "source_file": path.name,
            "source_type": "step",
            "success": True,
            "layers": [],
            "blocks": [],
            "dimensions": [],
            "text_blocks": [],
            "title_block": None,
            "geometry_summary": None,
            "entities": result.entities if hasattr(result, "entities") else [],
            "metadata": result.metadata if hasattr(result, "metadata") else {},
            "errors": result.errors if hasattr(result, "errors") else [],
            "warnings": result.warnings if hasattr(result, "warnings") else [],
        }

        logger.info(f"STEP extraction completed for {file_path}")

        # Update job complete in database
        run_async(update_job_complete(job_id, "completed", result=response))

        return {"status": "completed", "file_path": file_path, "result": response}

    except ImportError as e:
        logger.error(f"STEP extraction dependencies missing for {file_path}: {e}")
        # Don't retry ImportError - it's a configuration issue
        error_msg = f"STEP extraction not available. Install STEP dependencies: {e}"
        run_async(update_job_complete(job_id, "failed", error_message=error_msg))
        return {
            "status": "failed",
            "file_path": file_path,
            "error": error_msg,
        }
    except Exception as e:
        retry_count = self.request.retries
        max_retries = options.get("max_retries", 3)

        logger.error(f"STEP extraction failed for {file_path} (attempt {retry_count + 1}): {e}")

        if retry_count < max_retries:
            # Exponential backoff: 2^retry_count seconds (1, 2, 4, 8, ...)
            backoff = 2 ** retry_count
            logger.info(f"Retrying STEP extraction for {file_path} in {backoff}s (attempt {retry_count + 1}/{max_retries})")
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(f"STEP extraction failed permanently for {file_path} after {retry_count} attempts")
        run_async(update_job_complete(job_id, "failed", error_message=str(e)))
        return {"status": "failed", "file_path": file_path, "error": str(e)}


@app.task(bind=True, name="extract_werk24")
def extract_werk24(self, file_path: str, options: dict = None, job_id: str = None):
    """
    Extract data from engineering drawing using Werk24 API.

    Args:
        self: Celery task instance (for retry support)
        file_path: Path to drawing file (PNG, JPG, TIF, PDF)
        options: Extraction options (extract_dimensions, extract_gdt, etc.)
        job_id: Optional ExtractionJob ID for database tracking

    Returns:
        Dictionary with extraction results
    """
    options = options or {}

    # Update job start in database
    run_async(update_job_start(job_id, self.request.id))

    try:
        from pybase.extraction.werk24.client import Werk24Client

        client = Werk24Client()
        path = Path(file_path)

        logger.info(f"Starting Werk24 extraction for {file_path} (attempt {self.request.retries + 1})")

        # Run extraction in thread to avoid blocking
        import asyncio

        def run_extraction():
            return client.extract(
                str(path),
                extract_dimensions=options.get("extract_dimensions", True),
                extract_gdt=options.get("extract_gdt", True),
                extract_threads=options.get("extract_threads", True),
                extract_surface_finish=options.get("extract_surface_finish", True),
                extract_materials=options.get("extract_materials", True),
                extract_title_block=options.get("extract_title_block", True),
            )

        result = asyncio.run(run_extraction())

        # Convert to dict format
        response = {
            "source_file": path.name,
            "source_type": "werk24",
            "success": True,
            "dimensions": result.dimensions if hasattr(result, "dimensions") else [],
            "gdt_annotations": result.gdt_annotations if hasattr(result, "gdt_annotations") else [],
            "threads": result.threads if hasattr(result, "threads") else [],
            "surface_finishes": result.surface_finishes if hasattr(result, "surface_finishes") else [],
            "materials": result.materials if hasattr(result, "materials") else [],
            "title_block": result.title_block if hasattr(result, "title_block") else None,
            "metadata": result.metadata if hasattr(result, "metadata") else {},
            "errors": result.errors if hasattr(result, "errors") else [],
            "warnings": result.warnings if hasattr(result, "warnings") else [],
        }

        logger.info(f"Werk24 extraction completed for {file_path}")

        # Update job complete in database
        run_async(update_job_complete(job_id, "completed", result=response))

        return {"status": "completed", "file_path": file_path, "result": response}

    except ImportError as e:
        logger.error(f"Werk24 extraction dependencies missing for {file_path}: {e}")
        # Don't retry ImportError - it's a configuration issue
        error_msg = f"Werk24 extraction not available. Install werk24 dependencies: {e}"
        run_async(update_job_complete(job_id, "failed", error_message=error_msg))
        return {
            "status": "failed",
            "file_path": file_path,
            "error": error_msg,
        }
    except Exception as e:
        retry_count = self.request.retries
        max_retries = options.get("max_retries", 3)

        logger.error(f"Werk24 extraction failed for {file_path} (attempt {retry_count + 1}): {e}")

        if retry_count < max_retries:
            # Exponential backoff: 2^retry_count seconds (1, 2, 4, 8, ...)
            backoff = 2 ** retry_count
            logger.info(f"Retrying Werk24 extraction for {file_path} in {backoff}s (attempt {retry_count + 1}/{max_retries})")
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(f"Werk24 extraction failed permanently for {file_path} after {retry_count} attempts")
        run_async(update_job_complete(job_id, "failed", error_message=str(e)))
        return {"status": "failed", "file_path": file_path, "error": str(e)}


@app.task(bind=True, name="extract_bulk")
def extract_bulk(self, file_paths: list, format_override: str = None, options: dict = None, job_id: str = None):
    """
    Process multiple files in parallel with progress tracking.

    Args:
        self: Celery task instance (for retry support)
        file_paths: List of file paths to extract
        format_override: Optional format to use for all files (pdf, dxf, ifc, step, werk24)
        options: Format-specific extraction options
        job_id: Optional ExtractionJob ID for database tracking

    Returns:
        Dictionary with bulk extraction results including per-file status
    """
    import uuid

    options = options or {}
    bulk_job_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)

    logger.info(f"Starting bulk extraction job {bulk_job_id} for {len(file_paths)} files")

    # Map file extensions to format names
    format_map = {
        ".pdf": "extract_pdf",
        ".dxf": "extract_dxf",
        ".dwg": "extract_dxf",
        ".ifc": "extract_ifc",
        ".stp": "extract_step",
        ".step": "extract_step",
        ".png": "extract_werk24",
        ".jpg": "extract_werk24",
        ".jpeg": "extract_werk24",
        ".tif": "extract_werk24",
        ".tiff": "extract_werk24",
    }

    # Determine task for each file
    file_tasks = []
    for file_path in file_paths:
        path = Path(file_path)
        ext = path.suffix.lower()

        if format_override:
            task_name = f"extract_{format_override.lower()}"
        elif ext in format_map:
            task_name = format_map[ext]
        else:
            logger.warning(f"Unsupported file format: {ext} for {file_path}")
            continue

        # Create task and store with file info
        from celery import current_app

        task = current_app.send_task(task_name, args=[file_path, options, job_id])
        file_tasks.append({"file_path": file_path, "task_id": task.id, "task": task})

    # Wait for all tasks to complete
    results = []
    completed_count = 0
    failed_count = 0

    for file_task in file_tasks:
        try:
            result = file_task["task"].get(timeout=3600)  # 1 hour timeout
            results.append(result)

            if result.get("status") == "completed":
                completed_count += 1
            else:
                failed_count += 1

        except Exception as e:
            logger.error(f"Task failed for {file_task['file_path']}: {e}")
            results.append({
                "status": "failed",
                "file_path": file_task["file_path"],
                "error": str(e),
            })
            failed_count += 1

    completed_at = datetime.now(timezone.utc)

    # Determine overall status
    if failed_count == len(results):
        overall_status = "failed"
    elif completed_count == len(results):
        overall_status = "completed"
    else:
        overall_status = "partial"

    response = {
        "bulk_job_id": bulk_job_id,
        "total_files": len(file_paths),
        "files": results,
        "overall_status": overall_status,
        "files_completed": completed_count,
        "files_failed": failed_count,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
    }

    logger.info(f"Bulk extraction job {bulk_job_id} completed: {completed_count}/{len(file_paths)} successful")
    return response


@app.task(bind=True, name="extract_file_auto")
def extract_file_auto(self, file_path: str, options: dict = None, job_id: str = None):
    """
    Automatically detect file format and extract data.

    Args:
        self: Celery task instance (for retry support)
        file_path: Path to file
        options: Extraction options
        job_id: Optional ExtractionJob ID for database tracking

    Returns:
        Dictionary with extraction results
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    format_map = {
        ".pdf": "extract_pdf",
        ".dxf": "extract_dxf",
        ".dwg": "extract_dxf",
        ".ifc": "extract_ifc",
        ".stp": "extract_step",
        ".step": "extract_step",
        ".png": "extract_werk24",
        ".jpg": "extract_werk24",
        ".jpeg": "extract_werk24",
        ".tif": "extract_werk24",
        ".tiff": "extract_werk24",
    }

    if ext not in format_map:
        return {
            "status": "failed",
            "file_path": file_path,
            "error": f"Unsupported file extension: {ext}",
        }

    task_name = format_map[ext]
    logger.info(f"Auto-detected format '{ext}' for {file_path}, using task '{task_name}'")

    # Delegate to specific extraction task
    from celery import current_app

    task = current_app.send_task(task_name, args=[file_path, options, job_id])
    return task.get(timeout=3600)


# =============================================================================
# Worker Entry Point
# =============================================================================


if __name__ == "__main__":
    logger.info("Starting Celery worker with extraction background tasks")

    # Run initial setup
    try:
        app.autodiscover_tasks(["workers"])
        logger.info("Celery extraction worker ready")
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        sys.exit(1)
