#!/usr/bin/env python3
"""
Celery worker for background export tasks.

This worker handles data export including CSV, Excel, JSON, and XML formats
with support for field selection, filtering, and scheduled exports.
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import logging
import tempfile

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
from workers.worker_db import run_async, update_export_job_start, update_export_job_complete, update_export_job_progress

# Setup logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Create Celery app
app = Celery(
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
    include=["workers.celery_export_worker"],
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


@app.task(bind=True, name="export_data")
def export_data(
    self,
    job_id: str,
    table_id: str,
    user_id: str,
    export_format: str,
    options: dict = None,
):
    """
    Export table data to specified format.

    Args:
        self: Celery task instance (for retry support)
        job_id: ExportJob ID for database tracking
        table_id: Table ID to export
        user_id: User ID requesting export
        export_format: Export format (csv, xlsx, json, xml)
        options: Export options (field_ids, view_id, include_attachments, etc.)

    Returns:
        Dictionary with export results including file path and download URL
    """
    options = options or {}

    logger.info(f"Starting export job {job_id} for table {table_id} (attempt {self.request.retries + 1})")

    # Update job start in database
    run_async(update_export_job_start(job_id, self.request.id))

    try:
        from pybase.services.export_service import ExportService
        from pybase.db.session import AsyncSessionLocal
        from uuid import UUID

        # Parse options
        field_ids = options.get("field_ids")
        if field_ids:
            field_ids = [UUID(fid) for fid in field_ids]

        view_id = options.get("view_id")
        if view_id:
            view_id = UUID(view_id)

        flatten_linked_records = options.get("flatten_linked_records", False)
        include_attachments = options.get("include_attachments", False)

        # Create temporary file for export
        suffix = f".{export_format}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_path = tmp_file.name

        logger.info(f"Exporting to temporary file: {tmp_path}")

        # Run export in async context
        import asyncio

        async def run_export():
            async with AsyncSessionLocal() as db:
                service = ExportService()

                # Count total records first
                from pybase.models.record import Record
                from sqlalchemy import func, select

                count_query = select(func.count(Record.id)).where(
                    Record.table_id == str(table_id),
                    Record.is_deleted == False
                )
                total_result = await db.execute(count_query)
                total_records = total_result.scalar() or 0

                # Update job with total records
                await update_export_job_start(job_id, self.request.id, total_records=total_records)

                # Stream export to file
                record_count = 0
                with open(tmp_path, 'wb') as f:
                    async for chunk in service.export_records(
                        db=db,
                        table_id=UUID(table_id),
                        user_id=user_id,
                        format=export_format,
                        batch_size=1000,
                        field_ids=field_ids,
                        flatten_linked_records=flatten_linked_records,
                        view_id=view_id,
                        include_attachments=include_attachments,
                    ):
                        f.write(chunk)
                        record_count += 1  # Approximate, may not be exact for all formats

                        # Update progress periodically
                        if total_records > 0 and record_count % 100 == 0:
                            progress = min(95, int((record_count / total_records) * 100))
                            await update_export_job_progress(job_id, progress, record_count)

                # Get file size
                file_size = os.path.getsize(tmp_path)

                # Generate download URL (placeholder - actual implementation depends on storage backend)
                # For now, use file:// URL as placeholder
                download_url = f"file://{tmp_path}"

                # Update job complete
                await update_export_job_complete(
                    job_id,
                    "completed",
                    file_path=tmp_path,
                    download_url=download_url,
                    file_size=file_size,
                    record_count=record_count,
                )

                return {
                    "file_path": tmp_path,
                    "download_url": download_url,
                    "file_size": file_size,
                    "record_count": record_count,
                }

        result = asyncio.run(run_export())

        logger.info(f"Export job {job_id} completed successfully: {result['record_count']} records exported")

        return {
            "status": "completed",
            "job_id": job_id,
            "table_id": table_id,
            "format": export_format,
            "result": result,
        }

    except ImportError as e:
        logger.error(f"Export dependencies missing for job {job_id}: {e}")
        error_msg = f"Export not available: {e}"
        run_async(update_export_job_complete(job_id, "failed", error_message=error_msg))
        return {
            "status": "failed",
            "job_id": job_id,
            "error": error_msg,
        }
    except Exception as e:
        retry_count = self.request.retries
        max_retries = options.get("max_retries", 3)

        logger.error(f"Export failed for job {job_id} (attempt {retry_count + 1}): {e}")

        if retry_count < max_retries:
            # Exponential backoff: 2^retry_count seconds (1, 2, 4, 8, ...)
            backoff = 2 ** retry_count
            logger.info(f"Retrying export job {job_id} in {backoff}s (attempt {retry_count + 1}/{max_retries})")
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(f"Export job {job_id} failed permanently after {retry_count} attempts")
        import traceback
        error_stack = traceback.format_exc()
        run_async(update_export_job_complete(
            job_id,
            "failed",
            error_message=str(e),
            error_stack_trace=error_stack,
        ))
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(e),
        }


@app.task(bind=True, name="export_data_scheduled")
def export_data_scheduled(
    self,
    table_id: str,
    user_id: str,
    export_format: str,
    schedule: str,
    options: dict = None,
    storage_config: dict = None,
):
    """
    Scheduled export task that runs periodically.

    Args:
        self: Celery task instance (for retry support)
        table_id: Table ID to export
        user_id: User ID requesting export
        export_format: Export format (csv, xlsx, json, xml)
        schedule: Cron schedule expression
        options: Export options (field_ids, view_id, include_attachments, etc.)
        storage_config: Storage configuration (S3, SFTP, etc.)

    Returns:
        Dictionary with export results
    """
    options = options or {}
    storage_config = storage_config or {}

    logger.info(f"Starting scheduled export for table {table_id} (schedule: {schedule})")

    try:
        # Create a new export job for this scheduled run
        from uuid import uuid4
        from pybase.db.session import AsyncSessionLocal
        from pybase.models.export_job import ExportJob
        from datetime import datetime, timezone

        job_id = str(uuid4())

        async def create_job():
            async with AsyncSessionLocal() as db:
                job = ExportJob(
                    id=job_id,
                    user_id=user_id,
                    table_id=table_id,
                    export_format=export_format,
                    status="pending",
                )
                if options.get("view_id"):
                    job.view_id = options["view_id"]
                job.set_options(options)
                db.add(job)
                await db.commit()
                await db.refresh(job)
                return job

        run_async(create_job())

        # Run the export task synchronously (same process)
        # Use apply() to properly handle the bound task's 'self' parameter
        task_result = export_data.apply(args=[job_id, table_id, user_id, export_format, options])
        result = task_result.get()

        # If storage config provided, upload to external storage
        if storage_config and result.get("status") == "completed":
            try:
                # Use apply() to properly handle the bound task's 'self' parameter
                upload_task = upload_export_to_storage.apply(
                    args=[result["result"]["file_path"], storage_config]
                )
                upload_result = upload_task.get()
                result["storage"] = upload_result
                logger.info(f"Scheduled export uploaded to storage: {upload_result}")
            except Exception as e:
                logger.error(f"Failed to upload scheduled export to storage: {e}")
                result["storage_error"] = str(e)

        logger.info(f"Scheduled export completed: {job_id}")
        return result

    except Exception as e:
        logger.error(f"Scheduled export failed: {e}")
        import traceback
        return {
            "status": "failed",
            "table_id": table_id,
            "error": str(e),
            "stack_trace": traceback.format_exc(),
        }


@app.task(bind=True, name="export_data_background")
def export_data_background(
    self,
    job_id: str,
    table_id: str,
    user_id: str,
    export_format: str,
    options: dict = None,
):
    """
    Background export task for large datasets.

    This task handles large export jobs asynchronously with proper progress tracking
    and retry support. It delegates to the export_data task with proper Celery binding.

    Args:
        self: Celery task instance (for retry support)
        job_id: ExportJob ID for database tracking
        table_id: Table ID to export
        user_id: User ID requesting export
        export_format: Export format (csv, xlsx, json, xml)
        options: Export options (field_ids, view_id, include_attachments, etc.)

    Returns:
        Dictionary with export results including file path and download URL
    """
    options = options or {}

    logger.info(f"Starting background export job {job_id} for table {table_id} (attempt {self.request.retries + 1})")

    # Update job start in database
    run_async(update_export_job_start(job_id, self.request.id))

    try:
        from pybase.services.export_service import ExportService
        from pybase.db.session import AsyncSessionLocal
        from uuid import UUID

        # Parse options
        field_ids = options.get("field_ids")
        if field_ids:
            field_ids = [UUID(fid) for fid in field_ids]

        view_id = options.get("view_id")
        if view_id:
            view_id = UUID(view_id)

        flatten_linked_records = options.get("flatten_linked_records", False)
        include_attachments = options.get("include_attachments", False)

        # Create temporary file for export
        suffix = f".{export_format}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_path = tmp_file.name

        logger.info(f"Background exporting to temporary file: {tmp_path}")

        # Run export in async context
        import asyncio

        async def run_export():
            async with AsyncSessionLocal() as db:
                service = ExportService()

                # Count total records first
                from pybase.models.record import Record
                from sqlalchemy import func, select

                count_query = select(func.count(Record.id)).where(
                    Record.table_id == str(table_id),
                    Record.is_deleted == False
                )
                total_result = await db.execute(count_query)
                total_records = total_result.scalar() or 0

                # Update job with total records
                await update_export_job_start(job_id, self.request.id, total_records=total_records)

                # Stream export to file with enhanced progress tracking for large datasets
                record_count = 0
                last_progress_update = 0

                with open(tmp_path, 'wb') as f:
                    async for chunk in service.export_records(
                        db=db,
                        table_id=UUID(table_id),
                        user_id=user_id,
                        format=export_format,
                        batch_size=1000,
                        field_ids=field_ids,
                        flatten_linked_records=flatten_linked_records,
                        view_id=view_id,
                        include_attachments=include_attachments,
                    ):
                        f.write(chunk)
                        record_count += 1  # Approximate, may not be exact for all formats

                        # Update progress more frequently for large exports (every 50 records)
                        if total_records > 0 and record_count % 50 == 0:
                            progress = min(95, int((record_count / total_records) * 100))
                            # Only update if progress changed by at least 5% to avoid DB spam
                            if progress - last_progress_update >= 5:
                                await update_export_job_progress(job_id, progress, record_count)
                                last_progress_update = progress
                                logger.info(f"Background export job {job_id} progress: {progress}% ({record_count}/{total_records} records)")

                # Get file size
                file_size = os.path.getsize(tmp_path)

                # Generate download URL (placeholder - actual implementation depends on storage backend)
                # For now, use file:// URL as placeholder
                download_url = f"file://{tmp_path}"

                # Update job complete
                await update_export_job_complete(
                    job_id,
                    "completed",
                    file_path=tmp_path,
                    download_url=download_url,
                    file_size=file_size,
                    record_count=record_count,
                )

                return {
                    "file_path": tmp_path,
                    "download_url": download_url,
                    "file_size": file_size,
                    "record_count": record_count,
                }

        result = asyncio.run(run_export())

        logger.info(f"Background export job {job_id} completed successfully: {result['record_count']} records exported")

        return {
            "status": "completed",
            "job_id": job_id,
            "table_id": table_id,
            "format": export_format,
            "result": result,
        }

    except ImportError as e:
        logger.error(f"Background export dependencies missing for job {job_id}: {e}")
        error_msg = f"Background export not available: {e}"
        run_async(update_export_job_complete(job_id, "failed", error_message=error_msg))
        return {
            "status": "failed",
            "job_id": job_id,
            "error": error_msg,
        }
    except Exception as e:
        retry_count = self.request.retries
        max_retries = options.get("max_retries", 3)

        logger.error(f"Background export failed for job {job_id} (attempt {retry_count + 1}): {e}")

        if retry_count < max_retries:
            # Exponential backoff: 2^retry_count seconds (1, 2, 4, 8, ...)
            backoff = 2 ** retry_count
            logger.info(f"Retrying background export job {job_id} in {backoff}s (attempt {retry_count + 1}/{max_retries})")
            raise self.retry(exc=e, countdown=backoff, max_retries=max_retries)

        # Max retries exceeded
        logger.error(f"Background export job {job_id} failed permanently after {retry_count} attempts")
        import traceback
        error_stack = traceback.format_exc()
        run_async(update_export_job_complete(
            job_id,
            "failed",
            error_message=str(e),
            error_stack_trace=error_stack,
        ))
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(e),
        }


@app.task(bind=True, name="upload_export_to_storage")
def upload_export_to_storage(
    self,
    file_path: str,
    storage_config: dict,
):
    """
    Upload exported file to external storage (S3, SFTP, etc.).

    Args:
        self: Celery task instance (for retry support)
        file_path: Path to exported file
        storage_config: Storage configuration (type, credentials, path, etc.)

    Returns:
        Dictionary with upload results including remote URL
    """
    storage_type = storage_config.get("type", "local").lower()

    logger.info(f"Uploading export file {file_path} to {storage_type} storage")

    try:
        if storage_type == "s3":
            return _upload_to_s3(file_path, storage_config)
        elif storage_type == "sftp":
            return _upload_to_sftp(file_path, storage_config)
        elif storage_type == "local":
            return _upload_to_local(file_path, storage_config)
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")

    except Exception as e:
        logger.error(f"Failed to upload {file_path} to {storage_type} storage: {e}")
        raise


def _upload_to_s3(file_path: str, config: dict) -> dict:
    """Upload file to S3."""
    try:
        import boto3
        from botocore.exceptions import ClientError

        s3_client = boto3.client(
            's3',
            aws_access_key_id=config.get("access_key_id"),
            aws_secret_access_key=config.get("secret_access_key"),
            region_name=config.get("region", "us-east-1"),
        )

        file_name = Path(file_path).name
        s3_key = f"{config.get('path', '')}/{file_name}".lstrip("/")

        s3_client.upload_file(
            file_path,
            config["bucket"],
            s3_key,
            ExtraArgs={
                "ContentType": _get_content_type(file_name),
            }
        )

        # Generate presigned URL (valid for 7 days)
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': config["bucket"], 'Key': s3_key},
            ExpiresIn=7 * 24 * 3600
        )

        return {
            "storage_type": "s3",
            "bucket": config["bucket"],
            "key": s3_key,
            "url": url,
        }

    except ImportError:
        raise ImportError("boto3 not installed. Install: pip install boto3")
    except ClientError as e:
        raise Exception(f"S3 upload failed: {e}")


def _upload_to_sftp(file_path: str, config: dict) -> dict:
    """Upload file to SFTP server."""
    try:
        import paramiko

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(
            hostname=config["host"],
            port=config.get("port", 22),
            username=config["username"],
            password=config.get("password"),
            key_filename=config.get("key_filename"),
        )

        sftp = ssh.open_sftp()

        remote_path = f"{config.get('path', '.')}/{Path(file_path).name}"
        sftp.put(file_path, remote_path)

        sftp.close()
        ssh.close()

        return {
            "storage_type": "sftp",
            "host": config["host"],
            "remote_path": remote_path,
        }

    except ImportError:
        raise ImportError("paramiko not installed. Install: pip install paramiko")
    except Exception as e:
        raise Exception(f"SFTP upload failed: {e}")


def _upload_to_local(file_path: str, config: dict) -> dict:
    """Copy file to local storage directory."""
    import shutil

    target_dir = config.get("path", "/tmp/exports")
    os.makedirs(target_dir, exist_ok=True)

    file_name = Path(file_path).name
    target_path = os.path.join(target_dir, file_name)

    shutil.copy2(file_path, target_path)

    return {
        "storage_type": "local",
        "path": target_path,
    }


def _get_content_type(filename: str) -> str:
    """Get MIME content type based on file extension."""
    ext = Path(filename).suffix.lower()
    content_types = {
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".json": "application/json",
        ".xml": "application/xml",
        ".zip": "application/zip",
    }
    return content_types.get(ext, "application/octet-stream")


# =============================================================================
# Worker Entry Point
# =============================================================================


if __name__ == "__main__":
    logger.info("Starting Celery worker with export background tasks")

    # Run initial setup
    try:
        app.autodiscover_tasks(["workers"])
        logger.info("Celery export worker ready")
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        sys.exit(1)
