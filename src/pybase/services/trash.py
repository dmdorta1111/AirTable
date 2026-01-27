"""Trash service for managing deleted records."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.cache.record_cache import RecordCache
from pybase.core.exceptions import NotFoundError, PermissionDeniedError
from pybase.models.base import Base
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


class TrashService:
    """Service for trash bin operations."""

    def __init__(self) -> None:
        """Initialize trash service with cache."""
        self.cache = RecordCache()

    async def list_trash(
        self,
        db: AsyncSession,
        user_id: str,
        table_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Record], int]:
        """List deleted records in trash accessible to user.

        Args:
            db: Database session
            user_id: User ID
            table_id: Optional table ID to filter by
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (deleted records, total count)

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access to table
        """
        offset = (page - 1) * page_size

        # If table_id is provided, check access to that specific table
        if table_id:
            table = await db.get(Table, table_id)
            if not table or table.is_deleted:
                raise NotFoundError("Table not found")

            # Check if user has access to workspace
            base = await self._get_base(db, table.base_id)
            workspace = await self._get_workspace(db, base.workspace_id)
            member = await self._get_workspace_member(db, str(workspace.id), str(user_id))
            if not member:
                raise PermissionDeniedError("You don't have access to this table")

            # Count query for specific table
            count_query = select(func.count()).select_from(Record).where(
                Record.table_id == str(table_id)
            )
            count_query = count_query.where(Record.deleted_at.is_not(None))
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0

            # Data query for specific table
            query = select(Record).where(Record.table_id == str(table_id))
            query = query.where(Record.deleted_at.is_not(None))
            query = query.order_by(Record.deleted_at.desc())
            query = query.offset(offset)
            query = query.limit(page_size)
            result = await db.execute(query)
            records = result.scalars().all()
        else:
            # Get all tables the user has access to
            # Join through workspace membership
            base_query = (
                select(Record)
                .join(Table)
                .join(Base)
                .join(Workspace)
                .join(WorkspaceMember)
            )
            base_query = base_query.where(WorkspaceMember.user_id == str(user_id))
            base_query = base_query.where(Record.deleted_at.is_not(None))

            # Count query
            count_query = select(func.count()).select_from(Record).join(Table).join(Base).join(
                Workspace
            ).join(WorkspaceMember)
            count_query = count_query.where(WorkspaceMember.user_id == str(user_id))
            count_query = count_query.where(Record.deleted_at.is_not(None))
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0

            # Data query
            query = base_query
            query = query.order_by(Record.deleted_at.desc())
            query = query.offset(offset)
            query = query.limit(page_size)
            result = await db.execute(query)
            records = result.scalars().all()

        return list(records), total

    async def restore_record(
        self,
        db: AsyncSession,
        record_id: str,
        user_id: str,
    ) -> Record:
        """Restore a deleted record from trash.

        Args:
            db: Database session
            record_id: Record ID to restore
            user_id: User ID performing the restore

        Returns:
            Restored record

        Raises:
            NotFoundError: If record not found or not deleted
            PermissionDeniedError: If user doesn't have access
        """
        # Get record (including deleted ones)
        query = select(Record).where(Record.id == record_id)
        result = await db.execute(query)
        record = result.scalar_one_or_none()

        if not record:
            raise NotFoundError("Record not found")

        if not record.is_deleted:
            raise NotFoundError("Record is not in trash")

        # Check if user has access to workspace
        table = await self._get_table(db, str(record.table_id))
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))
        if not member:
            raise PermissionDeniedError("You don't have access to this record")

        # Restore record
        record.restore()

        # Invalidate cache for this table
        await self.cache.invalidate_table_cache(str(record.table_id))

        return record

    async def batch_restore_records(
        self,
        db: AsyncSession,
        user_id: str,
        record_ids: list[str],
    ) -> list[Record]:
        """Restore multiple deleted records from trash in a single transaction.

        Args:
            db: Database session
            user_id: User ID performing the restore
            record_ids: List of record IDs to restore

        Returns:
            List of restored records

        Raises:
            NotFoundError: If any record not found or not deleted
            PermissionDeniedError: If user doesn't have access
        """
        restored_records: list[Record] = []

        for idx, record_id in enumerate(record_ids):
            # Get record (including deleted ones)
            query = select(Record).where(Record.id == record_id)
            result = await db.execute(query)
            record = result.scalar_one_or_none()

            if not record:
                raise NotFoundError(f"Record at index {idx} with ID {record_id} not found")

            if not record.is_deleted:
                raise NotFoundError(
                    f"Record at index {idx} with ID {record_id} is not in trash"
                )

            # Check if user has access to workspace (first record sets the workspace)
            if idx == 0:
                table = await self._get_table(db, str(record.table_id))
                base = await self._get_base(db, str(table.base_id))
                workspace = await self._get_workspace(db, str(base.workspace_id))
                member = await self._get_workspace_member(db, str(workspace.id), str(user_id))
                if not member:
                    raise PermissionDeniedError("You don't have access to these records")

            restored_records.append(record)

        # Restore all records
        for record in restored_records:
            record.restore()

        # Commit all restores in a single transaction
        await db.commit()

        # Refresh all records to get updated timestamps
        for record in restored_records:
            await db.refresh(record)

        # Invalidate cache for affected tables
        table_ids = set(str(record.table_id) for record in restored_records)
        for table_id in table_ids:
            await self.cache.invalidate_table_cache(table_id)

        return restored_records

    async def permanent_delete_record(
        self,
        db: AsyncSession,
        record_id: str,
        user_id: str,
    ) -> None:
        """Permanently delete a record from trash.

        This action cannot be undone.

        Args:
            db: Database session
            record_id: Record ID to permanently delete
            user_id: User ID performing the deletion

        Raises:
            NotFoundError: If record not found
            PermissionDeniedError: If user doesn't have access
        """
        # Get record (including deleted ones)
        query = select(Record).where(Record.id == record_id)
        result = await db.execute(query)
        record = result.scalar_one_or_none()

        if not record:
            raise NotFoundError("Record not found")

        # Check if user has access to workspace
        table = await self._get_table(db, str(record.table_id))
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))

        if not member or member.role not in [
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
        ]:
            raise PermissionDeniedError("Only owners and admins can permanently delete records")

        # Permanently delete record (hard delete)
        await db.delete(record)

        # Invalidate cache for this table
        await self.cache.invalidate_table_cache(str(record.table_id))

    async def batch_permanent_delete_records(
        self,
        db: AsyncSession,
        user_id: str,
        record_ids: list[str],
    ) -> int:
        """Permanently delete multiple records from trash in a single transaction.

        This action cannot be undone.

        Args:
            db: Database session
            user_id: User ID performing the deletion
            record_ids: List of record IDs to permanently delete

        Returns:
            Number of records permanently deleted

        Raises:
            NotFoundError: If any record not found
            PermissionDeniedError: If user doesn't have admin access
        """
        deleted_count = 0
        table_ids_to_invalidate = set()

        for idx, record_id in enumerate(record_ids):
            # Get record (including deleted ones)
            query = select(Record).where(Record.id == record_id)
            result = await db.execute(query)
            record = result.scalar_one_or_none()

            if not record:
                raise NotFoundError(f"Record at index {idx} with ID {record_id} not found")

            # Check if user has admin access (first record sets the workspace)
            if idx == 0:
                table = await self._get_table(db, str(record.table_id))
                base = await self._get_base(db, str(table.base_id))
                workspace = await self._get_workspace(db, str(base.workspace_id))
                member = await self._get_workspace_member(db, str(workspace.id), str(user_id))

                if not member or member.role not in [
                    WorkspaceRole.OWNER,
                    WorkspaceRole.ADMIN,
                ]:
                    raise PermissionDeniedError(
                        "Only owners and admins can permanently delete records"
                    )

            # Track table for cache invalidation
            table_ids_to_invalidate.add(str(record.table_id))

            # Permanently delete record (hard delete)
            await db.delete(record)
            deleted_count += 1

        # Commit all deletions in a single transaction
        await db.commit()

        # Invalidate cache for affected tables
        for table_id in table_ids_to_invalidate:
            await self.cache.invalidate_table_cache(table_id)

        return deleted_count

    async def purge_old_records(
        self,
        db: AsyncSession,
        retention_days: int = 30,
    ) -> int:
        """Permanently delete records older than retention period.

        This is typically called by a background worker/maintenance task.

        Args:
            db: Database session
            retention_days: Number of days to retain deleted records

        Returns:
            Number of records purged
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        # Find all records deleted before cutoff date
        query = select(Record).where(
            and_(
                Record.deleted_at.is_not(None),
                Record.deleted_at < cutoff_date,
            )
        )
        result = await db.execute(query)
        old_records = result.scalars().all()

        # Permanently delete old records
        purged_count = 0
        table_ids_to_invalidate = set()

        for record in old_records:
            table_ids_to_invalidate.add(str(record.table_id))
            await db.delete(record)
            purged_count += 1

        # Commit all deletions
        await db.commit()

        # Invalidate cache for affected tables
        for table_id in table_ids_to_invalidate:
            await self.cache.invalidate_table_cache(table_id)

        return purged_count

    async def _get_workspace(
        self,
        db: AsyncSession,
        workspace_id: str,
    ) -> Workspace:
        """Get workspace by ID.

        Args:
            db: Database session
            workspace_id: Workspace ID

        Returns:
            Workspace

        Raises:
            NotFoundError: If workspace not found
        """
        workspace = await db.get(Workspace, workspace_id)
        if not workspace or workspace.is_deleted:
            raise NotFoundError("Workspace not found")
        return workspace

    async def _get_workspace_member(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
    ) -> Optional[WorkspaceMember]:
        """Get workspace member.

        Args:
            db: Database session
            workspace_id: Workspace ID
            user_id: User ID

        Returns:
            WorkspaceMember or None
        """
        query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _get_base(
        self,
        db: AsyncSession,
        base_id: str,
    ) -> Base:
        """Get base by ID.

        Args:
            db: Database session
            base_id: Base ID

        Returns:
            Base

        Raises:
            NotFoundError: If base not found
        """
        base = await db.get(Base, base_id)
        if not base or base.is_deleted:
            raise NotFoundError("Base not found")
        return base

    async def _get_table(
        self,
        db: AsyncSession,
        table_id: str,
    ) -> Table:
        """Get table by ID.

        Args:
            db: Database session
            table_id: Table ID

        Returns:
            Table

        Raises:
            NotFoundError: If table not found
        """
        table = await db.get(Table, table_id)
        if not table or table.is_deleted:
            raise NotFoundError("Table not found")
        return table
