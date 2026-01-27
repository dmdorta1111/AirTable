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
import time

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
from workers.worker_db import run_async, update_job_complete, update_job_progress, update_job_start

# Import Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = None
    Histogram = None
    Gauge = None
    start_http_server = None

# Setup logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# ==============================================================================
# Prometheus Metrics
# ==============================================================================

if PROMETHEUS_AVAILABLE:
    # Task duration histogram
    task_duration = Histogram(
        "celery_extraction_task_duration_seconds",
        "Extraction task duration in seconds",
        ["task_name", "status"],
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0, 3600.0],
    )

    # Task counter
    tasks_total = Counter(
        "celery_extraction_tasks_total",
        "Total number of extraction tasks",
        ["task_name", "status"],
    )

    # Active tasks gauge
    active_tasks = Gauge(
        "celery_extraction_active_tasks",
        "Number of currently running extraction tasks",
        ["task_name"],
    )

    # Task retries counter
    task_retries_total = Counter(
        "celery_extraction_task_retries_total",
        "Total number of extraction task retry attempts",
        ["task_name"],
    )

    logger.info("Prometheus metrics initialized for extraction worker")
else:
    logger.warning("Prometheus client not available. Metrics will not be collected.")
    task_duration = None
    tasks_total = None
    active_tasks = None
    task_retries_total = None

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
# Metrics Helper
# ==============================================================================


class TaskMetrics:
    """Context manager for tracking task metrics."""

    def __init__(self, task_name: str):
        self.task_name = task_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        if PROMETHEUS_AVAILABLE and active_tasks:
            active_tasks.labels(task_name=self.task_name).inc()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        # Determine status
        if exc_type is not None:
            status = "error"
        else:
            status = "success"

        # Record metrics
        if PROMETHEUS_AVAILABLE:
            if task_duration:
                task_duration.labels(task_name=self.task_name, status=status).observe(duration)
            if tasks_total:
                tasks_total.labels(task_name=self.task_name, status=status).inc()
            if active_tasks:
                active_tasks.labels(task_name=self.task_name).dec()

        return False


def track_retry(task_name: str):
    """Track a retry attempt in metrics."""
    if PROMETHEUS_AVAILABLE and task_retries_total:
        task_retries_total.labels(task_name=task_name).inc()


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

    # Start metrics tracking
    metrics = TaskMetrics("extract_pdf")
    metrics.__enter__()

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

        # Close metrics with success status
        metrics.__exit__(None, None, None)

        return {"status": "completed", "file_path": file_path, "result": response}

    except ImportError as e:
        logger.error(f"PDF extraction dependencies missing for {file_path}: {e}")
        # Don't retry ImportError - it's a configuration issue
        error_msg = f"PDF extraction not available. Install pdf dependencies: {e}"
        run_async(update_job_complete(job_id, "failed", error_message=error_msg))
        # Close metrics with error status
        metrics.__exit__(Exception, e, None)
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
            backoff = 2**retry_count

            # Capture stack trace for database
            import traceback

            error_stack = traceback.format_exc()
            error_msg = f"Retry {retry_count + 1}/{max_retries}: {str(e)}"

            # Update database with retry information before raising retry
            run_async(
                update_job_complete(
                    job_id,
                    "retrying",  # Set status to retrying
                    error_message=error_msg,
                    error_stack_trace=error_stack,
                )
            )

            logger.info(
                f"Retrying PDF extraction for {file_path} in {backoff}s (attempt {retry_count + 1}/{max_retries})"
            )
            # Track retry in metrics
            track_retry("extract_pdf")
            # Close metrics before retry
            metrics.__exit__(Exception, e, None)
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(
            f"PDF extraction failed permanently for {file_path} after {retry_count} attempts"
        )

        # Capture full stack trace for final failure
        import traceback

        error_stack = traceback.format_exc()

        run_async(
            update_job_complete(
                job_id, "failed", error_message=str(e), error_stack_trace=error_stack
            )
        )
        # Close metrics with error status
        metrics.__exit__(Exception, e, None)
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

    # Start metrics tracking
    metrics = TaskMetrics("extract_dxf")
    metrics.__enter__()

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
            "geometry_summary": result.geometry_summary
            if hasattr(result, "geometry_summary")
            else None,
            "entities": result.entities if hasattr(result, "entities") else [],
            "metadata": result.metadata if hasattr(result, "metadata") else {},
            "errors": result.errors if hasattr(result, "errors") else [],
            "warnings": result.warnings if hasattr(result, "warnings") else [],
        }

        logger.info(f"DXF extraction completed for {file_path}")

        # Update job complete in database
        run_async(update_job_complete(job_id, "completed", result=response))

        # Close metrics with success status
        metrics.__exit__(None, None, None)

        return {"status": "completed", "file_path": file_path, "result": response}

    except ImportError as e:
        logger.error(f"DXF extraction dependencies missing for {file_path}: {e}")
        # Don't retry ImportError - it's a configuration issue
        error_msg = f"DXF extraction not available. Install CAD dependencies: {e}"
        run_async(update_job_complete(job_id, "failed", error_message=error_msg))
        # Close metrics with error status
        metrics.__exit__(Exception, e, None)
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
            backoff = 2**retry_count

            # Capture stack trace for database
            import traceback

            error_stack = traceback.format_exc()
            error_msg = f"Retry {retry_count + 1}/{max_retries}: {str(e)}"

            # Update database with retry information before raising retry
            run_async(
                update_job_complete(
                    job_id,
                    "retrying",  # Set status to retrying
                    error_message=error_msg,
                    error_stack_trace=error_stack,
                )
            )

            logger.info(
                f"Retrying DXF extraction for {file_path} in {backoff}s (attempt {retry_count + 1}/{max_retries})"
            )
            # Track retry in metrics
            track_retry("extract_dxf")
            # Close metrics before retry
            metrics.__exit__(Exception, e, None)
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(
            f"DXF extraction failed permanently for {file_path} after {retry_count} attempts"
        )

        # Capture full stack trace for final failure
        import traceback

        error_stack = traceback.format_exc()

        run_async(
            update_job_complete(
                job_id, "failed", error_message=str(e), error_stack_trace=error_stack
            )
        )
        # Close metrics with error status
        metrics.__exit__(Exception, e, None)
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

    # Start metrics tracking
    metrics = TaskMetrics("extract_ifc")
    metrics.__enter__()

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

        # Close metrics with success status
        metrics.__exit__(None, None, None)

        return {"status": "completed", "file_path": file_path, "result": response}

    except ImportError as e:
        logger.error(f"IFC extraction dependencies missing for {file_path}: {e}")
        # Don't retry ImportError - it's a configuration issue
        error_msg = f"IFC extraction not available. Install IFC dependencies: {e}"
        run_async(update_job_complete(job_id, "failed", error_message=error_msg))
        # Close metrics with error status
        metrics.__exit__(Exception, e, None)
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
            backoff = 2**retry_count

            # Capture stack trace for database
            import traceback

            error_stack = traceback.format_exc()
            error_msg = f"Retry {retry_count + 1}/{max_retries}: {str(e)}"

            # Update database with retry information before raising retry
            run_async(
                update_job_complete(
                    job_id,
                    "retrying",  # Set status to retrying
                    error_message=error_msg,
                    error_stack_trace=error_stack,
                )
            )

            logger.info(
                f"Retrying IFC extraction for {file_path} in {backoff}s (attempt {retry_count + 1}/{max_retries})"
            )
            # Track retry in metrics
            track_retry("extract_ifc")
            # Close metrics before retry
            metrics.__exit__(Exception, e, None)
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(
            f"IFC extraction failed permanently for {file_path} after {retry_count} attempts"
        )

        # Capture full stack trace for final failure
        import traceback

        error_stack = traceback.format_exc()

        run_async(
            update_job_complete(
                job_id, "failed", error_message=str(e), error_stack_trace=error_stack
            )
        )
        # Close metrics with error status
        metrics.__exit__(Exception, e, None)
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

    # Start metrics tracking
    metrics = TaskMetrics("extract_step")
    metrics.__enter__()

    # Update job start in database
    run_async(update_job_start(job_id, self.request.id))

    try:
        from pybase.extraction.cad.step_parser import STEPParser

        parser = STEPParser()
        path = Path(file_path)

        logger.info(
            f"Starting STEP extraction for {file_path} (attempt {self.request.retries + 1})"
        )

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

        # Close metrics with success status
        metrics.__exit__(None, None, None)

        return {"status": "completed", "file_path": file_path, "result": response}

    except ImportError as e:
        logger.error(f"STEP extraction dependencies missing for {file_path}: {e}")
        # Don't retry ImportError - it's a configuration issue
        error_msg = f"STEP extraction not available. Install STEP dependencies: {e}"
        run_async(update_job_complete(job_id, "failed", error_message=error_msg))
        # Close metrics with error status
        metrics.__exit__(Exception, e, None)
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
            backoff = 2**retry_count

            # Capture stack trace for database
            import traceback

            error_stack = traceback.format_exc()
            error_msg = f"Retry {retry_count + 1}/{max_retries}: {str(e)}"

            # Update database with retry information before raising retry
            run_async(
                update_job_complete(
                    job_id,
                    "retrying",  # Set status to retrying
                    error_message=error_msg,
                    error_stack_trace=error_stack,
                )
            )

            logger.info(
                f"Retrying STEP extraction for {file_path} in {backoff}s (attempt {retry_count + 1}/{max_retries})"
            )
            # Track retry in metrics
            track_retry("extract_step")
            # Close metrics before retry
            metrics.__exit__(Exception, e, None)
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(
            f"STEP extraction failed permanently for {file_path} after {retry_count} attempts"
        )

        # Capture full stack trace for final failure
        import traceback

        error_stack = traceback.format_exc()

        run_async(
            update_job_complete(
                job_id, "failed", error_message=str(e), error_stack_trace=error_stack
            )
        )
        # Close metrics with error status
        metrics.__exit__(Exception, e, None)
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

    # Start metrics tracking
    metrics = TaskMetrics("extract_werk24")
    metrics.__enter__()

    # Update job start in database
    run_async(update_job_start(job_id, self.request.id))

    try:
        from pybase.extraction.werk24.client import Werk24Client

        client = Werk24Client()
        path = Path(file_path)

        logger.info(
            f"Starting Werk24 extraction for {file_path} (attempt {self.request.retries + 1})"
        )

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
            "surface_finishes": result.surface_finishes
            if hasattr(result, "surface_finishes")
            else [],
            "materials": result.materials if hasattr(result, "materials") else [],
            "title_block": result.title_block if hasattr(result, "title_block") else None,
            "metadata": result.metadata if hasattr(result, "metadata") else {},
            "errors": result.errors if hasattr(result, "errors") else [],
            "warnings": result.warnings if hasattr(result, "warnings") else [],
        }

        logger.info(f"Werk24 extraction completed for {file_path}")

        # Update job complete in database
        run_async(update_job_complete(job_id, "completed", result=response))

        # Close metrics with success status
        metrics.__exit__(None, None, None)

        return {"status": "completed", "file_path": file_path, "result": response}

    except ImportError as e:
        logger.error(f"Werk24 extraction dependencies missing for {file_path}: {e}")
        # Don't retry ImportError - it's a configuration issue
        error_msg = f"Werk24 extraction not available. Install werk24 dependencies: {e}"
        run_async(update_job_complete(job_id, "failed", error_message=error_msg))
        # Close metrics with error status
        metrics.__exit__(Exception, e, None)
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
            backoff = 2**retry_count

            # Capture stack trace for database
            import traceback

            error_stack = traceback.format_exc()
            error_msg = f"Retry {retry_count + 1}/{max_retries}: {str(e)}"

            # Update database with retry information before raising retry
            run_async(
                update_job_complete(
                    job_id,
                    "retrying",  # Set status to retrying
                    error_message=error_msg,
                    error_stack_trace=error_stack,
                )
            )

            logger.info(
                f"Retrying Werk24 extraction for {file_path} in {backoff}s (attempt {retry_count + 1}/{max_retries})"
            )
            # Track retry in metrics
            track_retry("extract_werk24")
            # Close metrics before retry
            metrics.__exit__(Exception, e, None)
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(
            f"Werk24 extraction failed permanently for {file_path} after {retry_count} attempts"
        )

        # Capture full stack trace for final failure
        import traceback

        error_stack = traceback.format_exc()

        run_async(
            update_job_complete(
                job_id, "failed", error_message=str(e), error_stack_trace=error_stack
            )
        )
        # Close metrics with error status
        metrics.__exit__(Exception, e, None)
        return {"status": "failed", "file_path": file_path, "error": str(e)}


@app.task(bind=True, name="extract_bulk")
def extract_bulk(
    self, file_paths: list, format_override: str = None, options: dict = None, job_id: str = None
):
    """
    Process multiple files in parallel with database-backed progress tracking.

    Uses BulkExtractionService to handle parallel file processing with database
    job tracking, progress updates, and result persistence.

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

    # Lazy imports to avoid circular dependencies
    from pybase.db.session import AsyncSessionLocal
    from pybase.models.extraction_job import ExtractionFormat
    from pybase.services.bulk_extraction import BulkExtractionService

    options = options or {}
    bulk_job_id = str(uuid.uuid4())

    # Update job start in database
    run_async(update_job_start(job_id, self.request.id))

    logger.info(f"Starting bulk extraction job {bulk_job_id} for {len(file_paths)} files")

    async def run_bulk_extraction():
        """Run bulk extraction with database session."""
        async with AsyncSessionLocal() as db:
            try:
                # Convert format_override string to ExtractionFormat enum
                format_enum = None
                if format_override:
                    try:
                        format_enum = ExtractionFormat(format_override.lower())
                    except ValueError:
                        logger.warning(
                            f"Invalid format_override: {format_override}, using auto-detect"
                        )

                # Create bulk extraction service with database session and job_id
                service = BulkExtractionService(db, job_id)

                # Progress callback to update parent bulk job progress
                def update_bulk_progress(file_index: int, total_files: int, progress: int):
                    """Update parent bulk job progress as files complete."""
                    try:
                        run_async(update_job_progress(job_id, progress))
                        logger.info(
                            f"Bulk job {job_id} progress: {file_index + 1}/{total_files} files ({progress}%)"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update bulk job progress: {e}")

                # Process files with database tracking and progress updates
                response = await service.process_files(
                    file_paths=file_paths,
                    format_override=format_enum,
                    options=options,
                    auto_detect_format=True,
                    continue_on_error=True,
                    progress_callback=update_bulk_progress,
                )

                return response

            except Exception as e:
                logger.error(f"Bulk extraction failed: {e}")
                # Re-raise to let Celery handle retries
                raise

    try:
        # Run bulk extraction asynchronously
        response = run_async(run_bulk_extraction())

        # Convert BulkExtractionResponse to dict format
        result_dict = {
            "bulk_job_id": str(response.bulk_job_id),
            "total_files": response.total_files,
            "files": [
                {
                    "file_path": f.file_path,
                    "filename": f.filename,
                    "format": f.format.value if hasattr(f.format, "value") else str(f.format),
                    "status": f.status.value if hasattr(f.status, "value") else str(f.status),
                    "job_id": str(f.job_id),
                    "progress": f.progress,
                    "result": f.result,
                    "error_message": f.error_message,
                    "started_at": f.started_at.isoformat() if f.started_at else None,
                    "completed_at": f.completed_at.isoformat() if f.completed_at else None,
                }
                for f in response.files
            ],
            "overall_status": response.overall_status.value
            if hasattr(response.overall_status, "value")
            else str(response.overall_status),
            "progress": response.progress,
            "files_completed": response.files_completed,
            "files_failed": response.files_failed,
            "files_pending": response.files_pending,
            "created_at": response.created_at.isoformat() if response.created_at else None,
            "started_at": response.started_at.isoformat() if response.started_at else None,
            "completed_at": response.completed_at.isoformat() if response.completed_at else None,
        }

        logger.info(
            f"Bulk extraction job {bulk_job_id} completed: "
            f"{response.files_completed}/{len(file_paths)} successful"
        )

        # Update job complete in database
        run_async(update_job_complete(job_id, "completed", result=result_dict))

        return result_dict

    except ImportError as e:
        logger.error(f"Bulk extraction dependencies missing: {e}")
        error_msg = f"Bulk extraction not available: {e}"
        run_async(update_job_complete(job_id, "failed", error_message=error_msg))
        return {
            "bulk_job_id": bulk_job_id,
            "status": "failed",
            "total_files": len(file_paths),
            "error": error_msg,
        }
    except Exception as e:
        retry_count = self.request.retries
        max_retries = options.get("max_retries", 3)

        logger.error(f"Bulk extraction failed (attempt {retry_count + 1}): {e}")

        if retry_count < max_retries:
            # Exponential backoff: 2^retry_count seconds (1, 2, 4, 8, ...)
            backoff = 2**retry_count

            # Capture stack trace for database
            import traceback

            error_stack = traceback.format_exc()
            error_msg = f"Retry {retry_count + 1}/{max_retries}: {str(e)}"

            # Update database with retry information before raising retry
            run_async(
                update_job_complete(
                    job_id,
                    "retrying",  # Set status to retrying
                    error_message=error_msg,
                    error_stack_trace=error_stack,
                )
            )

            logger.info(
                f"Retrying bulk extraction in {backoff}s (attempt {retry_count + 1}/{max_retries})"
            )
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(f"Bulk extraction failed permanently after {retry_count} attempts")

        # Capture full stack trace for final failure
        import traceback

        error_stack = traceback.format_exc()

        run_async(
            update_job_complete(
                job_id, "failed", error_message=str(e), error_stack_trace=error_stack
            )
        )
        return {
            "bulk_job_id": bulk_job_id,
            "status": "failed",
            "total_files": len(file_paths),
            "error": str(e),
        }


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
    # Start metrics tracking
    metrics = TaskMetrics("extract_file_auto")
    metrics.__enter__()

    try:
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
            error_msg = f"Unsupported file extension: {ext}"
            # Close metrics with error status
            metrics.__exit__(Exception, Exception(error_msg), None)
            return {
                "status": "failed",
                "file_path": file_path,
                "error": error_msg,
            }

        task_name = format_map[ext]
        logger.info(f"Auto-detected format '{ext}' for {file_path}, using task '{task_name}'")

        # Delegate to specific extraction task
        from celery import current_app

        task = current_app.send_task(task_name, args=[file_path, options, job_id])
        result = task.get(timeout=3600)

        # Close metrics with success status
        metrics.__exit__(None, None, None)

        return result
    except Exception as e:
        logger.error(f"Auto-extraction failed for {file_path}: {e}")
        # Close metrics with error status
        metrics.__exit__(Exception, e, None)
        return {
            "status": "failed",
            "file_path": file_path,
            "error": str(e),
        }


# =============================================================================
# Worker Entry Point
# =============================================================================


if __name__ == "__main__":
    logger.info("Starting Celery worker with extraction background tasks")

    # Start Prometheus metrics HTTP server on separate port
    metrics_port = int(os.getenv("PROMETHEUS_METRICS_PORT", "9090"))
    if PROMETHEUS_AVAILABLE and start_http_server:
        try:
            start_http_server(metrics_port)
            logger.info(f"Prometheus metrics HTTP server started on port {metrics_port}")
            logger.info(f"Metrics available at http://localhost:{metrics_port}/metrics")
        except Exception as e:
            logger.warning(f"Failed to start Prometheus HTTP server on port {metrics_port}: {e}")
    else:
        logger.warning("Prometheus client not available. Metrics HTTP server not started.")

    # Run initial setup
    try:
        app.autodiscover_tasks(["workers"])
        logger.info("Celery extraction worker ready")
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        sys.exit(1)
