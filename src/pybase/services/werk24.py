"""Werk24 usage tracking service for business logic."""

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
)
from pybase.db.base import utc_now
from pybase.models.werk24_usage import Werk24Usage
from pybase.models.workspace import WorkspaceMember


class Werk24Service:
    """Service for Werk24 API usage tracking operations."""

    async def create_usage_record(
        self,
        db: AsyncSession,
        user_id: str,
        request_type: str,
        ask_types: list[str],
        workspace_id: str | None = None,
        source_file: str | None = None,
        file_size_bytes: int | None = None,
        file_type: str | None = None,
        api_key_used: str | None = None,
        request_ip: str | None = None,
        user_agent: str | None = None,
    ) -> Werk24Usage:
        """Create a new usage tracking record.

        Args:
            db: Database session
            user_id: User ID making the request
            request_type: Type of request (e.g., "extract_async")
            ask_types: List of ask types requested
            workspace_id: Optional workspace ID
            source_file: Source file path or name
            file_size_bytes: Size of file in bytes
            file_type: File type (e.g., "pdf", "png")
            api_key_used: Prefix or identifier of API key
            request_ip: IP address of request
            user_agent: User agent string

        Returns:
            Created Werk24Usage record

        """
        usage = Werk24Usage(
            user_id=user_id,
            workspace_id=workspace_id,
            request_type=request_type,
            ask_types=ask_types,
            source_file=source_file,
            file_size_bytes=file_size_bytes,
            file_type=file_type,
            api_key_used=api_key_used,
            request_ip=request_ip,
            user_agent=user_agent,
        )
        db.add(usage)
        await db.commit()
        await db.refresh(usage)

        return usage

    async def update_usage_record(
        self,
        db: AsyncSession,
        usage_id: str,
        user_id: str,
        success: bool,
        status_code: int | None = None,
        error_message: str | None = None,
        processing_time_ms: int | None = None,
        tokens_used: int | None = None,
        cost_units: float | None = None,
        quota_remaining: int | None = None,
        dimensions_extracted: int = 0,
        gdts_extracted: int = 0,
        materials_extracted: int = 0,
        threads_extracted: int = 0,
    ) -> Werk24Usage:
        """Update a usage record with results.

        Args:
            db: Database session
            usage_id: Usage record ID
            user_id: User ID (for permission check)
            success: Whether the API call succeeded
            status_code: HTTP status code
            error_message: Error message if failed
            processing_time_ms: Processing time in milliseconds
            tokens_used: Number of tokens used
            cost_units: API cost units
            quota_remaining: Remaining quota
            dimensions_extracted: Number of dimensions extracted
            gdts_extracted: Number of GD&T features extracted
            materials_extracted: Number of materials extracted
            threads_extracted: Number of threads extracted

        Returns:
            Updated Werk24Usage record

        Raises:
            NotFoundError: If usage record not found
            PermissionDeniedError: If user doesn't own the record

        """
        usage = await db.get(Werk24Usage, usage_id)
        if not usage:
            raise NotFoundError("Usage record not found")

        # Check if user owns this usage record
        if usage.user_id != user_id:
            raise PermissionDeniedError("You don't have access to this usage record")

        # Update fields
        usage.mark_completed(success=success, error=error_message)
        usage.status_code = status_code
        usage.processing_time_ms = processing_time_ms
        usage.tokens_used = tokens_used
        usage.cost_units = cost_units
        usage.quota_remaining = quota_remaining

        # Update extraction counts
        usage.record_extraction_counts(
            dimensions=dimensions_extracted,
            gdts=gdts_extracted,
            materials=materials_extracted,
            threads=threads_extracted,
        )

        await db.commit()
        await db.refresh(usage)

        return usage

    async def get_usage_by_id(
        self,
        db: AsyncSession,
        usage_id: str,
        user_id: str,
    ) -> Werk24Usage:
        """Get a usage record by ID, checking user access.

        Args:
            db: Database session
            usage_id: Usage record ID
            user_id: User ID requesting access

        Returns:
            Werk24Usage record

        Raises:
            NotFoundError: If usage record not found
            PermissionDeniedError: If user doesn't have access

        """
        usage = await db.get(Werk24Usage, usage_id)
        if not usage:
            raise NotFoundError("Usage record not found")

        # Check if user owns this usage record
        if usage.user_id != user_id:
            raise PermissionDeniedError("You don't have access to this usage record")

        return usage

    async def list_usage(
        self,
        db: AsyncSession,
        user_id: str,
        workspace_id: str | None = None,
        request_type: str | None = None,
        success_only: bool | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Werk24Usage], int]:
        """List usage records accessible to user.

        Args:
            db: Database session
            user_id: User ID
            workspace_id: Optional workspace ID to filter by
            request_type: Optional request type to filter by
            success_only: If True, only return successful requests
            start_date: Optional start date filter
            end_date: Optional end date filter
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (usage records, total count)

        """
        offset = (page - 1) * page_size

        # Build base query
        count_query = select(func.count()).select_from(Werk24Usage)
        data_query = select(Werk24Usage)

        # Filter by user
        count_query = count_query.where(Werk24Usage.user_id == user_id)
        data_query = data_query.where(Werk24Usage.user_id == user_id)

        # Optional filters
        if workspace_id:
            count_query = count_query.where(Werk24Usage.workspace_id == workspace_id)
            data_query = data_query.where(Werk24Usage.workspace_id == workspace_id)

        if request_type:
            count_query = count_query.where(Werk24Usage.request_type == request_type)
            data_query = data_query.where(Werk24Usage.request_type == request_type)

        if success_only is not None:
            count_query = count_query.where(Werk24Usage.success == success_only)
            data_query = data_query.where(Werk24Usage.success == success_only)

        if start_date:
            count_query = count_query.where(Werk24Usage.created_at >= start_date)
            data_query = data_query.where(Werk24Usage.created_at >= start_date)

        if end_date:
            count_query = count_query.where(Werk24Usage.created_at <= end_date)
            data_query = data_query.where(Werk24Usage.created_at <= end_date)

        # Execute count query
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Execute data query
        data_query = data_query.order_by(Werk24Usage.created_at.desc())
        data_query = data_query.offset(offset)
        data_query = data_query.limit(page_size)
        result = await db.execute(data_query)
        usage_records = result.scalars().all()

        return list(usage_records), total

    async def get_usage_statistics(
        self,
        db: AsyncSession,
        user_id: str,
        workspace_id: str | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get usage statistics for quota management.

        Args:
            db: Database session
            user_id: User ID
            workspace_id: Optional workspace ID to filter by
            days: Number of days to look back

        Returns:
            Dictionary with usage statistics

        """
        # Calculate start date
        start_date = utc_now() - timedelta(days=days)

        # Build query
        query = select(Werk24Usage).where(Werk24Usage.user_id == user_id)
        query = query.where(Werk24Usage.created_at >= start_date)

        if workspace_id:
            query = query.where(Werk24Usage.workspace_id == workspace_id)

        result = await db.execute(query)
        usage_records = result.scalars().all()

        # Calculate statistics
        total_requests = len(usage_records)
        successful_requests = sum(1 for r in usage_records if r.success)
        failed_requests = total_requests - successful_requests

        total_dimensions = sum(r.dimensions_extracted for r in usage_records)
        total_gdts = sum(r.gdts_extracted for r in usage_records)
        total_materials = sum(r.materials_extracted for r in usage_records)
        total_threads = sum(r.threads_extracted for r in usage_records)

        total_cost = sum(r.cost_units or 0.0 for r in usage_records)
        avg_processing_time = (
            sum(r.processing_time_ms or 0 for r in usage_records) / total_requests
            if total_requests > 0
            else 0
        )

        # Get most recent quota remaining
        recent_quota = None
        for record in sorted(usage_records, key=lambda r: r.created_at, reverse=True):
            if record.quota_remaining is not None:
                recent_quota = record.quota_remaining
                break

        # Request type breakdown
        request_type_counts: dict[str, int] = {}
        for record in usage_records:
            request_type_counts[record.request_type] = (
                request_type_counts.get(record.request_type, 0) + 1
            )

        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": utc_now().isoformat(),
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": successful_requests / total_requests if total_requests > 0 else 0.0,
            "total_extractions": {
                "dimensions": total_dimensions,
                "gdts": total_gdts,
                "materials": total_materials,
                "threads": total_threads,
                "total": total_dimensions + total_gdts + total_materials + total_threads,
            },
            "cost": {
                "total_units": total_cost,
                "average_per_request": total_cost / total_requests if total_requests > 0 else 0.0,
            },
            "performance": {
                "average_processing_time_ms": avg_processing_time,
            },
            "quota": {
                "remaining": recent_quota,
            },
            "request_types": request_type_counts,
        }

    async def get_workspace_usage_statistics(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get workspace-wide usage statistics.

        Args:
            db: Database session
            workspace_id: Workspace ID
            user_id: User ID (for permission check)
            days: Number of days to look back

        Returns:
            Dictionary with workspace usage statistics

        Raises:
            PermissionDeniedError: If user doesn't have access to workspace

        """
        # Check if user has access to workspace
        member = await self._get_workspace_member(db, workspace_id, user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this workspace")

        # Calculate start date
        start_date = utc_now() - timedelta(days=days)

        # Build query for all workspace usage
        query = select(Werk24Usage).where(Werk24Usage.workspace_id == workspace_id)
        query = query.where(Werk24Usage.created_at >= start_date)

        result = await db.execute(query)
        usage_records = result.scalars().all()

        # Calculate statistics
        total_requests = len(usage_records)
        successful_requests = sum(1 for r in usage_records if r.success)
        failed_requests = total_requests - successful_requests

        total_dimensions = sum(r.dimensions_extracted for r in usage_records)
        total_gdts = sum(r.gdts_extracted for r in usage_records)
        total_materials = sum(r.materials_extracted for r in usage_records)
        total_threads = sum(r.threads_extracted for r in usage_records)

        total_cost = sum(r.cost_units or 0.0 for r in usage_records)

        # Per-user breakdown
        user_usage: dict[str, dict[str, Any]] = {}
        for record in usage_records:
            if record.user_id not in user_usage:
                user_usage[record.user_id] = {
                    "requests": 0,
                    "successful": 0,
                    "cost_units": 0.0,
                }
            user_usage[record.user_id]["requests"] += 1
            if record.success:
                user_usage[record.user_id]["successful"] += 1
            user_usage[record.user_id]["cost_units"] += record.cost_units or 0.0

        return {
            "workspace_id": workspace_id,
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": utc_now().isoformat(),
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": successful_requests / total_requests if total_requests > 0 else 0.0,
            "total_extractions": {
                "dimensions": total_dimensions,
                "gdts": total_gdts,
                "materials": total_materials,
                "threads": total_threads,
                "total": total_dimensions + total_gdts + total_materials + total_threads,
            },
            "cost": {
                "total_units": total_cost,
                "average_per_request": total_cost / total_requests if total_requests > 0 else 0.0,
            },
            "user_breakdown": user_usage,
        }

    async def _get_workspace_member(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
    ) -> WorkspaceMember | None:
        """Get workspace member record.

        Args:
            db: Database session
            workspace_id: Workspace ID
            user_id: User ID

        Returns:
            WorkspaceMember or None if not found

        """
        query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
