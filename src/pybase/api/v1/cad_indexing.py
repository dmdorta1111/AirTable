"""
CAD indexing API endpoints.

Handles single and batch indexing of CAD models for multi-modal similarity search.
"""

import asyncio
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.api.deps import CurrentUser, DbSession
from pybase.core.logging import get_logger
from pybase.services.cad_indexing_pipeline import (
    BatchIndexingResult,
    CADIndexingPipeline,
    IndexingResult,
)

logger = get_logger(__name__)

router = APIRouter()

# In-memory job storage (replace with Redis/DB in production)
_indexing_jobs: dict[str, dict[str, Any]] = {}


# =============================================================================
# Schemas
# =============================================================================


class CADIndexingStatus(str):
    """Indexing status values."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# Helper Functions
# =============================================================================


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks."""
    clean = Path(filename).name
    # Remove special characters, keep alphanumeric, dots, hyphens, underscores
    import re
    clean = re.sub(r"[^\w\-.]", "_", clean)
    # Limit length
    clean = clean[:255]
    if not clean or clean.startswith("."):
        clean = f"file_{uuid.uuid4().hex[:8]}"
    return clean


async def save_upload_file(file: UploadFile) -> Path:
    """Save uploaded file to temp directory."""
    safe_filename = sanitize_filename(file.filename or "upload")
    suffix = Path(safe_filename).suffix
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        content = await file.read()
        temp_file.write(content)
        temp_file.close()
        return Path(temp_file.name)
    except Exception as e:
        Path(temp_file.name).unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}",
        )


def result_to_dict(result: IndexingResult) -> dict[str, Any]:
    """Convert IndexingResult to dict for JSON response."""
    return {
        "model_id": result.model_id,
        "file_name": result.file_name,
        "status": result.status,
        "num_views_rendered": result.num_views_rendered,
        "has_text_embedding": result.has_text_embedding,
        "has_image_embedding": result.has_image_embedding,
        "has_geometry_embedding": result.has_geometry_embedding,
        "has_fused_embedding": result.has_fused_embedding,
        "errors": result.errors,
        "warnings": result.warnings,
        "started_at": result.started_at.isoformat() if result.started_at else None,
        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
    }


# =============================================================================
# Single Model Indexing
# =============================================================================


@router.post(
    "/index",
    response_model=dict[str, Any],
    summary="Index a single CAD model",
    description="Upload and index a CAD model for multi-modal similarity search.",
    tags=["CAD Indexing"],
    responses={
        200: {
            "description": "Indexing successful",
            "content": {
                "application/json": {
                    "example": {
                        "model_id": "550e8400-e29b-41d4-a716-446655440000",
                        "file_name": "bracket.step",
                        "status": "completed",
                        "num_views_rendered": 10,
                        "has_text_embedding": True,
                        "has_image_embedding": True,
                        "has_geometry_embedding": True,
                        "has_fused_embedding": True,
                        "errors": [],
                        "warnings": ["Genome extraction: placeholder implementation"],
                    }
                }
            }
        }
    },
)
async def index_cad_model(
    file: Annotated[
        UploadFile,
        File(description="CAD file to index (STEP, IGES, STL, etc.)")
    ],
    current_user: CurrentUser,
    db: DbSession,
    description: Annotated[
        str | None,
        Form(description="Optional description for the model")
    ] = None,
    category_label: Annotated[
        str | None,
        Form(description="Category label (e.g., 'bracket', 'fastener')")
    ] = None,
    tags: Annotated[
        str | None,
        Form(description="Comma-separated tags")
    ] = None,
    workspace_id: Annotated[
        str | None,
        Form(description="Optional workspace ID")
    ] = None,
    skip_existing: Annotated[
        bool,
        Form(description="Skip if model already indexed (by file hash)")
    ] = True,
) -> dict[str, Any]:
    """
    Index a single CAD model for similarity search.

    **Pipeline Steps:**
    1. Extract B-Rep genome (placeholder for Subagent 3)
    2. Generate description from metadata
    3. Render canonical 2D views (placeholder)
    4. Upload views to B2 (placeholder)
    5. Extract point cloud
    6. Compute embeddings (text, image, geometry, fused)
    7. Store embeddings in database
    8. Update model status

    **Supported Formats:**
    - STEP (.stp, .step)
    - IGES (.igs, .iges)
    - STL (.stl)
    - DXF (.dxf)
    - IFC (.ifc)

    **Usage Examples:**

    **cURL:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/cad/index" \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -F "file=@bracket.step" \\
      -F "description=Mounting bracket M10" \\
      -F "category_label=bracket" \\
      -F "tags=metal,standard"
    ```

    **Python:**
    ```python
    import requests

    url = "http://localhost:8000/api/v1/cad/index"
    headers = {"Authorization": "Bearer YOUR_TOKEN"}
    files = {"file": open("bracket.step", "rb")}
    data = {
        "description": "Mounting bracket M10",
        "category_label": "bracket",
        "tags": "metal,standard"
    }

    response = requests.post(url, headers=headers, files=files, data=data)
    result = response.json()
    model_id = result["model_id"]
    print(f"Indexed model: {model_id}")
    ```

    Args:
        file: CAD file to index
        description: Optional description (auto-generated if not provided)
        category_label: Category label for classification
        tags: Comma-separated tags
        workspace_id: Optional workspace ID
        skip_existing: Skip if file hash matches existing model

    Returns:
        Indexing result with model ID and status
    """
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Parse tags
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    # Save uploaded file
    temp_path = await save_upload_file(file)
    try:
        # Initialize pipeline
        pipeline = CADIndexingPipeline()

        # Index model
        result = await pipeline.index_model(
            db=db,
            user_id=str(current_user.id),
            file_path=str(temp_path),
            workspace_id=workspace_id,
            description=description,
            category_label=category_label,
            tags=tag_list,
            skip_existing=skip_existing,
        )

        return result_to_dict(result)

    finally:
        # Cleanup temp file
        temp_path.unlink(missing_ok=True)


# =============================================================================
# Batch Indexing
# =============================================================================


@router.post(
    "/index/batch",
    response_model=dict[str, Any],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Index multiple CAD models",
    description="Upload and index multiple CAD models in parallel.",
    tags=["CAD Indexing"],
)
async def index_cad_batch(
    files: Annotated[
        list[UploadFile],
        File(description="Multiple CAD files to index")
    ],
    current_user: CurrentUser,
    db: DbSession,
    workspace_id: Annotated[
        str | None,
        Form(description="Optional workspace ID")
    ] = None,
    continue_on_error: Annotated[
        bool,
        Form(description="Continue processing if one file fails")
    ] = True,
) -> dict[str, Any]:
    """
    Index multiple CAD models in parallel.

    Processes up to 5 files concurrently with progress tracking.
    Returns 202 Accepted with job_id for status polling.

    **Usage Example:**

    **cURL:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/cad/index/batch" \\
      -H "Authorization: Bearer YOUR_TOKEN" \\
      -F "files=@part1.step" \\
      -F "files=@part2.step" \\
      -F "files=@assembly.step"
    ```

    **Python:**
    ```python
    import requests
    import time

    url = "http://localhost:8000/api/v1/cad/index/batch"
    headers = {"Authorization": "Bearer YOUR_TOKEN"}

    files = [
        ("files", open("part1.step", "rb")),
        ("files", open("part2.step", "rb")),
    ]

    response = requests.post(url, headers=headers, files=files)
    result = response.json()
    job_id = result["job_id"]

    # Poll for status
    while True:
        status_response = requests.get(
            f"http://localhost:8000/api/v1/cad/index/status/{job_id}",
            headers=headers
        )
        status = status_response.json()
        print(f"Progress: {status['completed']}/{status['total_models']}")

        if status["completed_at"]:
            break
        time.sleep(2)
    ```

    Args:
        files: Multiple CAD files to index
        workspace_id: Optional workspace ID
        continue_on_error: Continue if one file fails

    Returns:
        Batch indexing result with job_id and per-model status
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided",
        )

    # Save all uploaded files
    temp_paths = []
    file_names = []
    try:
        for file in files:
            if not file.filename:
                continue
            temp_path = await save_upload_file(file)
            temp_paths.append(temp_path)
            file_names.append(file.filename)

        if not temp_paths:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid files provided",
            )

        # Initialize pipeline
        pipeline = CADIndexingPipeline()

        # Index batch (this runs synchronously, but respects concurrency limit)
        batch_result = await pipeline.index_batch(
            db=db,
            user_id=str(current_user.id),
            file_paths=[str(p) for p in temp_paths],
            workspace_id=workspace_id,
            continue_on_error=continue_on_error,
        )

        # Store job for status polling
        job_data = {
            "job_id": batch_result.job_id,
            "total_models": batch_result.total_models,
            "completed": batch_result.completed,
            "failed": batch_result.failed,
            "pending": batch_result.pending,
            "results": [result_to_dict(r) for r in batch_result.results],
            "started_at": batch_result.started_at.isoformat() if batch_result.started_at else None,
            "completed_at": batch_result.completed_at.isoformat() if batch_result.completed_at else None,
        }
        _indexing_jobs[batch_result.job_id] = job_data

        return job_data

    finally:
        # Cleanup temp files
        for temp_path in temp_paths:
            temp_path.unlink(missing_ok=True)


# =============================================================================
# Status Check
# =============================================================================


@router.get(
    "/index/status/{job_id}",
    response_model=dict[str, Any],
    summary="Get indexing job status",
    description="Check the status and progress of a batch indexing job.",
    tags=["CAD Indexing"],
)
async def get_indexing_status(
    job_id: str,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """
    Get batch indexing job status and results.

    Returns per-file status and overall progress.

    **Response Structure:**
    ```json
    {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "total_models": 3,
        "completed": 2,
        "failed": 1,
        "pending": 0,
        "results": [
            {
                "model_id": "...",
                "file_name": "part1.step",
                "status": "completed",
                "errors": []
            },
            ...
        ],
        "started_at": "2024-01-20T10:30:00Z",
        "completed_at": "2024-01-20T10:30:15Z"
    }
    ```

    Args:
        job_id: Batch job ID from /index/batch response

    Returns:
        Job status and per-file results
    """
    job = _indexing_jobs.get(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return job


# =============================================================================
# List Indexed Models
# =============================================================================


@router.get(
    "/models",
    response_model=dict[str, Any],
    summary="List indexed CAD models",
    description="Get list of CAD models indexed for the current user.",
    tags=["CAD Indexing"],
)
async def list_indexed_models(
    current_user: CurrentUser,
    db: DbSession,
    status_filter: Annotated[
        str | None,
        Query(alias="status", description="Filter by status")
    ] = None,
    category_filter: Annotated[
        str | None,
        Query(alias="category", description="Filter by category")
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum number of results")
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Offset for pagination")
    ] = 0,
) -> dict[str, Any]:
    """
    List CAD models indexed by the current user.

    Supports filtering by status and category.

    **Usage Example:**

    ```bash
    curl -X GET "http://localhost:8000/api/v1/cad/models?status=completed&category=bracket&limit=10" \\
      -H "Authorization: Bearer YOUR_TOKEN"
    ```

    Args:
        status_filter: Optional status filter (pending, processing, completed, failed)
        category_filter: Optional category filter
        limit: Maximum results (1-100, default 20)
        offset: Pagination offset

    Returns:
        List of CAD models with metadata
    """
    from sqlalchemy import select
    from pybase.models.cad_model import CADModel

    # Build query
    stmt = select(CADModel).where(
        CADModel.user_id == str(current_user.id),
        CADModel.is_deleted.is_(False),
    )

    if status_filter:
        stmt = stmt.where(CADModel.status == status_filter)

    if category_filter:
        stmt = stmt.where(CADModel.category_label == category_filter)

    # Order by most recent
    stmt = stmt.order_by(CADModel.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(stmt)
    models = result.scalars().all()

    # Get total count
    from sqlalchemy import func
    count_stmt = select(func.count(CADModel.id)).where(
        CADModel.user_id == str(current_user.id),
        CADModel.is_deleted.is_(False),
    )
    if status_filter:
        count_stmt = count_stmt.where(CADModel.status == status_filter)
    if category_filter:
        count_stmt = count_stmt.where(CADModel.category_label == category_filter)

    count_result = await db.execute(count_stmt)
    total = count_result.scalar()

    # Convert to response
    items = []
    for model in models:
        items.append({
            "id": str(model.id),
            "file_name": model.file_name,
            "file_type": model.file_type,
            "status": getattr(model, "status", "unknown"),
            "category_label": model.category_label,
            "tags": model.tags or [],
            "created_at": model.created_at.isoformat() if model.created_at else None,
            "has_embeddings": bool(model.embeddings),
        })

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# =============================================================================
# Get Model Details
# =============================================================================


@router.get(
    "/models/{model_id}",
    response_model=dict[str, Any],
    summary="Get CAD model details",
    description="Get detailed information about a specific indexed CAD model.",
    tags=["CAD Indexing"],
)
async def get_model_details(
    model_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    """
    Get detailed information about a specific CAD model.

    Includes metadata, embeddings status, and rendered views.

    Args:
        model_id: CAD model UUID

    Returns:
        Model details with embeddings and views
    """
    from uuid import UUID
    from sqlalchemy import select
    from pybase.models.cad_model import CADModel, CADModelEmbedding, CADRenderedView

    # Get model
    try:
        model_uuid = UUID(model_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid model ID format",
        )

    stmt = select(CADModel).where(
        CADModel.id == model_uuid,
        CADModel.user_id == str(current_user.id),
        CADModel.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Get embeddings
    embeddings_data = None
    if model.embeddings:
        emb = model.embeddings
        embeddings_data = {
            "has_text_embedding": emb.clip_text_embedding is not None,
            "has_image_embedding": emb.clip_image_embedding is not None,
            "has_geometry_embedding": emb.geometry_embedding is not None,
            "has_fused_embedding": emb.fused_embedding is not None,
            "model_version": emb.model_version,
        }

    # Get rendered views
    views = []
    for view in model.rendered_views:
        views.append({
            "view_type": view.view_type,
            "storage_path": view.storage_path,
            "resolution": view.resolution,
        })

    return {
        "id": str(model.id),
        "file_name": model.file_name,
        "file_type": model.file_type,
        "file_size_bytes": model.file_size_bytes,
        "file_hash": model.file_hash,
        "storage_path": model.storage_path,
        "status": getattr(model, "status", "unknown"),
        "category_label": model.category_label,
        "tags": model.tags or [],
        "material": model.material,
        "mass_kg": model.mass_kg,
        "volume_cm3": model.volume_cm3,
        "surface_area_cm2": model.surface_area_cm2,
        "bounding_box": model.bounding_box,
        "source_system": model.source_system,
        "created_at": model.created_at.isoformat() if model.created_at else None,
        "updated_at": model.updated_at.isoformat() if model.updated_at else None,
        "embeddings": embeddings_data,
        "rendered_views": views,
        "face_count": model.face_count,
        "edge_count": model.edge_count,
        "vertex_count": model.vertex_count,
    }


# =============================================================================
# Delete Model
# =============================================================================


@router.delete(
    "/models/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a CAD model",
    description="Soft-delete a CAD model and its embeddings.",
    tags=["CAD Indexing"],
)
async def delete_model(
    model_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """
    Delete a CAD model (soft delete).

    Args:
        model_id: CAD model UUID

    Raises:
        HTTPException 404: If model not found
    """
    from uuid import UUID
    from sqlalchemy import select
    from pybase.models.cad_model import CADModel

    try:
        model_uuid = UUID(model_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid model ID format",
        )

    stmt = select(CADModel).where(
        CADModel.id == model_uuid,
        CADModel.user_id == str(current_user.id),
        CADModel.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    model = result.scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Soft delete
    model.is_deleted = True
    model.deleted_at = datetime.now(timezone.utc)
    await db.commit()
