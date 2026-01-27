"""Audit service for tracking all system changes."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import NotFoundError, PermissionDeniedError
from pybase.models.audit_log import AuditAction, AuditLog
from pybase.models.user import User


class AuditService:
    """Service for audit logging operations."""

    async def log_action(
        self,
        db: AsyncSession,
        action: AuditAction | str,
        resource_type: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        resource_id: Optional[str] = None,
        table_id: Optional[str] = None,
        old_value: Optional[dict[str, Any] | str | list] = None,
        new_value: Optional[dict[str, Any] | str | list] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> AuditLog:
        """Log an action to the audit trail with tamper-evident storage.

        Args:
            db: Database session
            action: Type of action performed (from AuditAction enum or custom string)
            resource_type: Type of resource affected (e.g., "record", "table", "workspace")
            user_id: ID of user who performed the action
            user_email: Email of user (denormalized for historical accuracy)
            resource_id: ID of affected resource
            table_id: ID of table (for record operations)
            old_value: Previous state (for updates/deletes)
            new_value: New state (for creates/updates)
            ip_address: IP address of request
            user_agent: User agent string
            request_id: Request ID for correlation
            meta: Additional metadata

        Returns:
            Created audit log entry

        Raises:
            ValueError: If required fields are missing

        """
        # Validate required fields
        if not action:
            raise ValueError("action is required")
        if not resource_type:
            raise ValueError("resource_type is required")

        # Convert dict values to JSON strings for storage
        old_value_str = None
        if old_value is not None:
            if isinstance(old_value, dict | list):
                old_value_str = json.dumps(old_value)
            else:
                old_value_str = str(old_value)

        new_value_str = None
        if new_value is not None:
            if isinstance(new_value, dict | list):
                new_value_str = json.dumps(new_value)
            else:
                new_value_str = str(new_value)

        # Convert meta to JSON string
        meta_str = "{}"
        if meta is not None:
            meta_str = json.dumps(meta)

        # Get the hash of the previous log entry for tamper-evident chain
        previous_hash = await self._get_previous_log_hash(db)

        # Create audit log entry
        audit_log = AuditLog(
            user_id=user_id,
            user_email=user_email,
            action=str(action),
            resource_type=resource_type,
            resource_id=resource_id,
            table_id=table_id,
            old_value=old_value_str,
            new_value=new_value_str,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            previous_log_hash=previous_hash,
            meta=meta_str,
            integrity_hash="",  # Will be set after computing hash
        )

        # Compute integrity hash for this entry
        audit_log.integrity_hash = self._compute_integrity_hash(audit_log)

        # Save to database
        db.add(audit_log)
        await db.flush()

        return audit_log

    async def log_crud_create(
        self,
        db: AsyncSession,
        resource_type: str,
        resource_id: str,
        new_value: dict[str, Any],
        user_id: str,
        user_email: str,
        table_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        """Log a create operation.

        Args:
            db: Database session
            resource_type: Type of resource created
            resource_id: ID of created resource
            new_value: New resource data
            user_id: ID of user who created the resource
            user_email: Email of user
            table_id: ID of table (for record operations)
            ip_address: IP address of request
            user_agent: User agent string
            request_id: Request ID for correlation

        Returns:
            Created audit log entry

        """
        return await self.log_action(
            db=db,
            action=AuditAction.RECORD_CREATE
            if resource_type == "record"
            else f"{resource_type}.create",
            resource_type=resource_type,
            resource_id=resource_id,
            table_id=table_id,
            new_value=new_value,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

    async def log_crud_update(
        self,
        db: AsyncSession,
        resource_type: str,
        resource_id: str,
        old_value: dict[str, Any],
        new_value: dict[str, Any],
        user_id: str,
        user_email: str,
        table_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        """Log an update operation.

        Args:
            db: Database session
            resource_type: Type of resource updated
            resource_id: ID of updated resource
            old_value: Previous resource data
            new_value: New resource data
            user_id: ID of user who updated the resource
            user_email: Email of user
            table_id: ID of table (for record operations)
            ip_address: IP address of request
            user_agent: User agent string
            request_id: Request ID for correlation

        Returns:
            Created audit log entry

        """
        return await self.log_action(
            db=db,
            action=AuditAction.RECORD_UPDATE
            if resource_type == "record"
            else f"{resource_type}.update",
            resource_type=resource_type,
            resource_id=resource_id,
            table_id=table_id,
            old_value=old_value,
            new_value=new_value,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

    async def log_crud_delete(
        self,
        db: AsyncSession,
        resource_type: str,
        resource_id: str,
        old_value: dict[str, Any],
        user_id: str,
        user_email: str,
        table_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        """Log a delete operation.

        Args:
            db: Database session
            resource_type: Type of resource deleted
            resource_id: ID of deleted resource
            old_value: Previous resource data
            user_id: ID of user who deleted the resource
            user_email: Email of user
            table_id: ID of table (for record operations)
            ip_address: IP address of request
            user_agent: User agent string
            request_id: Request ID for correlation

        Returns:
            Created audit log entry

        """
        return await self.log_action(
            db=db,
            action=AuditAction.RECORD_DELETE
            if resource_type == "record"
            else f"{resource_type}.delete",
            resource_type=resource_type,
            resource_id=resource_id,
            table_id=table_id,
            old_value=old_value,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )

    async def query_logs(
        self,
        db: AsyncSession,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        table_id: Optional[str] = None,
        request_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Query audit logs with filters.

        Args:
            db: Database session
            user_id: Filter by user ID
            action: Filter by action type
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            table_id: Filter by table ID
            request_id: Filter by request ID
            start_date: Filter by start date (inclusive)
            end_date: Filter by end date (inclusive)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of audit log entries matching filters

        """
        query = select(AuditLog)

        # Apply filters
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if action:
            query = query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.where(AuditLog.resource_id == resource_id)
        if table_id:
            query = query.where(AuditLog.table_id == table_id)
        if request_id:
            query = query.where(AuditLog.request_id == request_id)
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)

        # Order by most recent first and paginate
        query = query.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_log_by_id(self, db: AsyncSession, log_id: str) -> AuditLog:
        """Get a specific audit log entry by ID.

        Args:
            db: Database session
            log_id: Audit log ID

        Returns:
            Audit log entry

        Raises:
            NotFoundError: If audit log not found

        """
        audit_log = await db.get(AuditLog, log_id)
        if not audit_log:
            raise NotFoundError("Audit log not found")
        return audit_log

    async def verify_integrity(self, db: AsyncSession, log_id: str) -> bool:
        """Verify the integrity of an audit log entry.

        Checks that the integrity_hash matches the computed hash
        and that the previous_log_hash matches the previous entry's integrity_hash.

        Args:
            db: Database session
            log_id: Audit log ID to verify

        Returns:
            True if integrity is valid, False otherwise

        """
        audit_log = await self.get_log_by_id(db, log_id)

        # Verify integrity hash
        computed_hash = self._compute_integrity_hash(audit_log)
        if computed_hash != audit_log.integrity_hash:
            return False

        # Verify chain integrity (if this is not the first log)
        if audit_log.previous_log_hash:
            # Get the previous log entry
            query = (
                select(AuditLog)
                .where(AuditLog.integrity_hash == audit_log.previous_log_hash)
                .order_by(desc(AuditLog.created_at))
                .limit(1)
            )
            result = await db.execute(query)
            previous_log = result.scalar_one_or_none()

            if not previous_log:
                return False

        return True

    async def delete_old_logs(
        self, db: AsyncSession, retention_days: int
    ) -> int:
        """Delete audit logs older than the retention period.

        This should be called by a scheduled cleanup task.
        Deletion of audit logs should itself be logged.

        Args:
            db: Database session
            retention_days: Number of days to retain logs

        Returns:
            Number of deleted logs

        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Query for logs to delete
        query = (
            select(AuditLog)
            .where(AuditLog.created_at < cutoff_date)
            .order_by(desc(AuditLog.created_at))
        )
        result = await db.execute(query)
        logs_to_delete = list(result.scalars().all())

        # Delete logs
        count = len(logs_to_delete)
        for log in logs_to_delete:
            await db.delete(log)

        return count

    async def export_logs(
        self,
        db: AsyncSession,
        user_id: str,
        user_email: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Export audit logs with filters.

        The export action itself is logged for compliance.

        Args:
            db: Database session
            user_id: ID of user requesting export
            user_email: Email of user requesting export
            start_date: Filter by start date
            end_date: Filter by end date
            filters: Additional filters (user_id, action, resource_type, etc.)

        Returns:
            List of audit log dictionaries

        """
        # Build query parameters
        query_params = {
            "start_date": start_date,
            "end_date": end_date,
        }

        if filters:
            query_params.update(filters)

        # Query logs
        logs = await self.query_logs(db, **query_params, limit=100000)

        # Convert to dictionaries
        export_data = [log.to_dict() for log in logs]

        # Log the export action
        await self.log_action(
            db=db,
            action=AuditAction.AUDIT_LOG_EXPORT,
            resource_type="audit_log",
            user_id=user_id,
            user_email=user_email,
            new_value={"exported_count": len(export_data), "filters": query_params},
            meta={"export_format": "json"},
        )

        return export_data

    async def _get_previous_log_hash(self, db: AsyncSession) -> Optional[str]:
        """Get the integrity hash of the most recent log entry.

        Args:
            db: Database session

        Returns:
            Hash of the most recent log entry, or None if no logs exist

        """
        query = (
            select(AuditLog.integrity_hash)
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _compute_integrity_hash(self, audit_log: AuditLog) -> str:
        """Compute the integrity hash for an audit log entry.

        The hash includes all relevant fields to ensure tamper-evidence.

        Args:
            audit_log: Audit log entry

        Returns:
            SHA-256 hash as hexadecimal string

        """
        # Create a string representation of all relevant fields
        data = f"{audit_log.user_id}|"
        data += f"{audit_log.user_email}|"
        data += f"{audit_log.action}|"
        data += f"{audit_log.resource_type}|"
        data += f"{audit_log.resource_id}|"
        data += f"{audit_log.table_id}|"
        data += f"{audit_log.old_value}|"
        data += f"{audit_log.new_value}|"
        data += f"{audit_log.ip_address}|"
        data += f"{audit_log.user_agent}|"
        data += f"{audit_log.request_id}|"
        data += f"{audit_log.previous_log_hash}|"
        data += f"{audit_log.meta}|"
        data += f"{audit_log.created_at.isoformat() if audit_log.created_at else ''}"

        # Compute SHA-256 hash
        return hashlib.sha256(data.encode()).hexdigest()
