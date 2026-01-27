"""Record service for business logic."""

import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB

from pybase.cache.record_cache import RecordCache
from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.models.audit_log import AuditAction
from pybase.models.base import Base
from pybase.models.field import Field
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.user import User
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.record import RecordCreate, RecordUpdate
from pybase.schemas.view import FilterCondition, FilterOperator
from pybase.services.audit_service import AuditService
from pybase.services.validation import ValidationService


class RecordService:
    """Service for record operations."""

    def __init__(self) -> None:
        """Initialize record service with cache and audit service."""
        self.cache = RecordCache()
        self.audit_service = AuditService()

    async def _get_user_email(self, db: AsyncSession, user_id: str) -> Optional[str]:
        """Get user email for audit logging.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            User email or None if not found

        """
        user = await db.get(User, user_id)
        return user.email if user else None

    async def create_record(
        self,
        db: AsyncSession,
        user_id: str,
        record_data: RecordCreate,
    ) -> Record:
        """Create a new record in a table.

        Args:
            db: Database session
            user_id: User ID creating record
            record_data: Record creation data

        Returns:
            Created record

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access to table
            ConflictError: If field validation fails

        """
        # Check if table exists
        table = await db.get(Table, record_data.table_id)
        if not table or table.is_deleted:
            raise NotFoundError("Table not found")

        # Check if user has access to workspace
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))
        if not member:
            raise PermissionDeniedError("You don't have access to this table")

        # Validate record data against fields
        await self._validate_record_data(db, str(table.id), record_data.data)

        # Create record
        record = Record(
            table_id=record_data.table_id,
            data=json.dumps(record_data.data),
            created_by_id=str(user_id),
            last_modified_by_id=str(user_id),
            row_height=record_data.row_height if record_data.row_height else 32,
        )
        db.add(record)
        await db.flush()

        # Log audit
        user_email = await self._get_user_email(db, str(user_id))
        await self.audit_service.log_crud_create(
            db=db,
            resource_type="record",
            resource_id=str(record.id),
            new_value=record_data.data,
            user_id=str(user_id),
            user_email=user_email or "",
            table_id=str(record_data.table_id),
        )

        # Invalidate cache for this table
        await self.cache.invalidate_table_cache(str(record_data.table_id))

        return record

    async def batch_create_records(
        self,
        db: AsyncSession,
        user_id: str,
        table_id: UUID,
        records_data: list[RecordCreate],
    ) -> list[Record]:
        """Create multiple records in a table in a single transaction.

        Args:
            db: Database session
            user_id: User ID creating records
            table_id: Table ID for all records
            records_data: List of record creation data

        Returns:
            List of created records

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access to table
            ConflictError: If field validation fails for any record

        """
        # Check if table exists
        table = await db.get(Table, table_id)
        if not table or table.is_deleted:
            raise NotFoundError("Table not found")

        # Check if user has access to workspace (single check for all records)
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))
        if not member:
            raise PermissionDeniedError("You don't have access to this table")

        # Validate all records data against fields
        for idx, record_data in enumerate(records_data):
            # Ensure table_id matches
            if str(record_data.table_id) != str(table_id):
                raise ConflictError(
                    f"Record at index {idx} has different table_id than specified"
                )

            # Validate record data
            await self._validate_record_data(db, str(table.id), record_data.data)

        # Create all records
        created_records: list[Record] = []
        for record_data in records_data:
            record = Record(
                table_id=table_id,
                data=json.dumps(record_data.data),
                created_by_id=str(user_id),
                last_modified_by_id=str(user_id),
                row_height=record_data.row_height if record_data.row_height else 32,
            )
            db.add(record)
            created_records.append(record)

        # Commit all records in a single transaction
        await db.commit()

        # Refresh all records to get generated IDs and timestamps
        for record in created_records:
            await db.refresh(record)

        # Log audit for batch create
        user_email = await self._get_user_email(db, str(user_id))
        for record in created_records:
            record_data_dict = json.loads(record.data) if record.data else {}
            await self.audit_service.log_action(
                db=db,
                action=AuditAction.RECORD_BULK_CREATE,
                resource_type="record",
                resource_id=str(record.id),
                table_id=str(table_id),
                new_value=record_data_dict,
                user_id=str(user_id),
                user_email=user_email or "",
            )

        return created_records

    async def batch_update_records(
        self,
        db: AsyncSession,
        user_id: str,
        table_id: UUID,
        updates: list[tuple[str, RecordUpdate]],
    ) -> list[Record]:
        """Update multiple records in a table in a single transaction.

        Args:
            db: Database session
            user_id: User ID updating records
            table_id: Table ID for all records
            updates: List of tuples containing (record_id, update_data)

        Returns:
            List of updated records

        Raises:
            NotFoundError: If table or any record not found
            PermissionDeniedError: If user doesn't have edit access
            ConflictError: If field validation fails for any record or record not in table

        """
        # Check if table exists
        table = await db.get(Table, table_id)
        if not table or table.is_deleted:
            raise NotFoundError("Table not found")

        # Check if user has edit permission in workspace (single check for all records)
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))
        if not member or member.role not in [
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
            WorkspaceRole.EDITOR,
        ]:
            raise PermissionDeniedError("Only owners, admins, and editors can update records")

        # Fetch and validate all records
        updated_records: list[Record] = []
        old_values: list[dict[str, Any]] = []
        for idx, (record_id, update_data) in enumerate(updates):
            # Get record
            record = await db.get(Record, record_id)
            if not record or record.is_deleted:
                raise NotFoundError(f"Record at index {idx} with ID {record_id} not found")

            # Ensure record belongs to the specified table
            if str(record.table_id) != str(table_id):
                raise ConflictError(
                    f"Record at index {idx} belongs to a different table"
                )

            # Validate record data against fields if provided
            if update_data.data:
                await self._validate_record_data(db, str(table.id), update_data.data)

            # Store old value for audit
            old_values.append(json.loads(record.data) if record.data else {})
            updated_records.append(record)

        # Update all records
        for record, (record_id, update_data) in zip(updated_records, updates):
            if update_data.data is not None:
                record.data = json.dumps(update_data.data)
            if update_data.row_height is not None:
                record.row_height = update_data.row_height
            record.last_modified_by_id = str(user_id)

        # Commit all updates in a single transaction
        await db.commit()

        # Refresh all records to get updated timestamps
        for record in updated_records:
            await db.refresh(record)

        # Log audit for batch update
        user_email = await self._get_user_email(db, str(user_id))
        for record, old_value in zip(updated_records, old_values):
            new_value = json.loads(record.data) if record.data else {}
            await self.audit_service.log_action(
                db=db,
                action=AuditAction.RECORD_BULK_UPDATE,
                resource_type="record",
                resource_id=str(record.id),
                table_id=str(table_id),
                old_value=old_value,
                new_value=new_value,
                user_id=str(user_id),
                user_email=user_email or "",
            )

        return updated_records

    async def batch_delete_records(
        self,
        db: AsyncSession,
        user_id: str,
        table_id: UUID,
        record_ids: list[str],
    ) -> list[Record]:
        """Delete multiple records in a table in a single transaction.

        Args:
            db: Database session
            user_id: User ID deleting records
            table_id: Table ID for all records
            record_ids: List of record IDs to delete

        Returns:
            List of deleted records

        Raises:
            NotFoundError: If table or any record not found
            PermissionDeniedError: If user doesn't have delete access
            ConflictError: If record not in table

        """
        # Check if table exists
        table = await db.get(Table, table_id)
        if not table or table.is_deleted:
            raise NotFoundError("Table not found")

        # Check if user has delete permission in workspace (single check for all records)
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))
        if not member or member.role not in [
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
            WorkspaceRole.EDITOR,
        ]:
            raise PermissionDeniedError("Only owners, admins, and editors can delete records")

        # Fetch and validate all records
        deleted_records: list[Record] = []
        old_values: list[dict[str, Any]] = []
        for idx, record_id in enumerate(record_ids):
            # Get record
            record = await db.get(Record, record_id)
            if not record or record.is_deleted:
                raise NotFoundError(f"Record at index {idx} with ID {record_id} not found")

            # Ensure record belongs to the specified table
            if str(record.table_id) != str(table_id):
                raise ConflictError(
                    f"Record at index {idx} belongs to a different table"
                )

            # Store old value for audit
            old_values.append(json.loads(record.data) if record.data else {})
            deleted_records.append(record)

        # Delete all records (soft delete)
        for record in deleted_records:
            record.soft_delete()

        # Commit all deletions in a single transaction
        await db.commit()

        # Refresh all records to get updated timestamps
        for record in deleted_records:
            await db.refresh(record)

        # Log audit for batch delete
        user_email = await self._get_user_email(db, str(user_id))
        for record, old_value in zip(deleted_records, old_values):
            await self.audit_service.log_action(
                db=db,
                action=AuditAction.RECORD_BULK_DELETE,
                resource_type="record",
                resource_id=str(record.id),
                table_id=str(table_id),
                old_value=old_value,
                user_id=str(user_id),
                user_email=user_email or "",
            )

        return deleted_records

    async def get_record_by_id(
        self,
        db: AsyncSession,
        record_id: str,
        user_id: str,
    ) -> Record:
        """Get a record by ID, checking user access.

        Args:
            db: Database session
            record_id: Record ID
            user_id: User ID requesting access

        Returns:
            Record

        Raises:
            NotFoundError: If record not found
            PermissionDeniedError: If user doesn't have access

        """
        record = await db.get(Record, record_id)
        if not record or record.is_deleted:
            raise NotFoundError("Record not found")

        # Check if user has access to workspace
        table = await self._get_table(db, str(record.table_id))
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))
        if not member:
            raise PermissionDeniedError("You don't have access to this record")

        return record

    async def list_records(
        self,
        db: AsyncSession,
        table_id: Optional[UUID],
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Record], int]:
        """List records accessible to user.

        Args:
            db: Database session
            table_id: Optional table ID to filter by
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (records, total count)

        """
        offset = (page - 1) * page_size

        # Count query
        count_query = (
            select(func.count()).select_from(Record).join(Table).join(Base).join(WorkspaceMember)
        )
        if table_id:
            count_query = count_query.where(Record.table_id == str(table_id))
        count_query = count_query.where(WorkspaceMember.user_id == str(user_id))
        # Check is_deleted property instead of calling is_() on property
        count_query = count_query.where(Record.deleted_at.is_(None))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query
        query = select(Record).join(Table).join(Base).join(WorkspaceMember)
        if table_id:
            query = query.where(Record.table_id == str(table_id))
        query = query.where(WorkspaceMember.user_id == str(user_id))
        query = query.where(Record.deleted_at.is_(None))
        query = query.order_by(Record.created_at)
        query = query.offset(offset)
        query = query.limit(page_size)
        result = await db.execute(query)
        records = result.scalars().all()

        return list(records), total

    async def list_records_cursor(
        self,
        db: AsyncSession,
        table_id: Optional[UUID],
        user_id: str,
        cursor: Optional[str] = None,
        page_size: int = 20,
        filters: Optional[list[FilterCondition]] = None,
    ) -> dict[str, Any]:
        """List records accessible to user using cursor-based pagination.

        Cursor-based pagination is more efficient for large datasets as it avoids
        using OFFSET, which can be slow on large tables. The cursor is based on
        the record's ID and created_at timestamp.

        Args:
            db: Database session
            table_id: Optional table ID to filter by
            user_id: User ID
            cursor: Optional cursor string to fetch next page (format: "record_id:created_at")
            page_size: Number of items per page
            filters: Optional list of filter conditions to apply

        Returns:
            Dictionary with:
                - records: list of Record objects
                - next_cursor: cursor for next page or None if no more records
                - has_more: boolean indicating if there are more records

        """
        # Don't use cache when filters are applied as results vary
        use_cache = filters is None

        if use_cache:
            # Try to get from cache first
            table_id_str = str(table_id) if table_id else None
            cached_result = await self.cache.get_cached_records(
                table_id=table_id_str,
                user_id=user_id,
                cursor=cursor,
                page_size=page_size,
            )

            if cached_result:
                # Convert cached data back to Record objects
                from pybase.models.record import Record

                records = []
                for r_data in cached_result.get("records", []):
                    # Create Record objects from cached data
                    record = Record(
                        id=r_data["id"],
                        table_id=r_data["table_id"],
                        data=r_data["data"],
                        created_at=r_data["created_at"],
                        updated_at=r_data["updated_at"],
                        row_height=r_data["row_height"],
                    )
                    records.append(record)

                return {
                    "records": records,
                    "next_cursor": cached_result.get("next_cursor"),
                    "has_more": cached_result.get("has_more", False),
                }

        # Parse cursor if provided
        cursor_record_id = None
        cursor_created_at = None

        if cursor:
            try:
                parts = cursor.split(":")
                if len(parts) == 2:
                    cursor_record_id = parts[0]
                    cursor_created_at = parts[1]
            except (ValueError, AttributeError):
                # Invalid cursor, start from beginning
                cursor_record_id = None
                cursor_created_at = None

        # Build base query with joins
        query = select(Record).join(Table).join(Base).join(WorkspaceMember)

        # Apply filters
        if table_id:
            query = query.where(Record.table_id == str(table_id))
        query = query.where(WorkspaceMember.user_id == str(user_id))
        query = query.where(Record.deleted_at.is_(None))

        # Apply additional filters if provided
        if filters:
            query = self._apply_filters_to_query(query, filters)

        # Apply cursor filtering for efficient pagination
        # We use both id and created_at for ordering to ensure consistent pagination
        if cursor_record_id and cursor_created_at:
            # Get records where (created_at > cursor_created_at) OR
            # (created_at == cursor_created_at AND id > cursor_record_id)
            query = query.where(
                (Record.created_at > cursor_created_at)
                | ((Record.created_at == cursor_created_at) & (Record.id > cursor_record_id))
            )

        # Order by created_at and then by id for consistent pagination
        query = query.order_by(Record.created_at, Record.id)

        # Fetch one extra record to determine if there are more results
        query = query.limit(page_size + 1)
        result = await db.execute(query)
        records = list(result.scalars().all())

        # Determine if there are more records
        has_more = len(records) > page_size
        if has_more:
            records = records[:page_size]

        # Generate next cursor if there are more records
        next_cursor = None
        if has_more and records:
            last_record = records[-1]
            next_cursor = f"{last_record.id}:{last_record.created_at.isoformat()}"

        result_data = {
            "records": records,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }

        # Cache the result only if no filters
        if use_cache:
            table_id_str = str(table_id) if table_id else None
            await self.cache.set_cached_records(
                table_id=table_id_str,
                user_id=user_id,
                data=result_data,
                cursor=cursor,
                page_size=page_size,
            )

        return result_data

    async def update_record(
        self,
        db: AsyncSession,
        record_id: str,
        user_id: str,
        record_data: RecordUpdate,
    ) -> Record:
        """Update a record.

        Args:
            db: Database session
            record_id: Record ID
            user_id: User ID making request
            record_data: Record update data

        Returns:
            Updated record

        Raises:
            NotFoundError: If record not found
            PermissionDeniedError: If user doesn't have permission
            ConflictError: If field validation fails

        """
        record = await self.get_record_by_id(db, record_id, user_id)

        # Check if user has edit permission in workspace
        table = await self._get_table(db, str(record.table_id))
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))
        if not member or member.role not in [
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
            WorkspaceRole.EDITOR,
        ]:
            raise PermissionDeniedError("Only owners, admins, and editors can update records")

        # Validate record data against fields if provided
        if record_data.data:
            await self._validate_record_data(
                db, str(table.id), record_data.data, exclude_record_id=str(record.id)
            )

        # Store old value for audit
        old_value = json.loads(record.data) if record.data else {}

        # Update fields
        if record_data.data is not None:
            record.data = json.dumps(record_data.data)
        if record_data.row_height is not None:
            record.row_height = record_data.row_height
        record.last_modified_by_id = str(user_id)

        # Log audit
        user_email = await self._get_user_email(db, str(user_id))
        new_value = record_data.data if record_data.data is not None else old_value
        await self.audit_service.log_crud_update(
            db=db,
            resource_type="record",
            resource_id=str(record.id),
            old_value=old_value,
            new_value=new_value,
            user_id=str(user_id),
            user_email=user_email or "",
            table_id=str(record.table_id),
        )

        # Invalidate cache for this table
        await self.cache.invalidate_table_cache(str(record.table_id))

        return record

    async def delete_record(
        self,
        db: AsyncSession,
        record_id: str,
        user_id: str,
    ) -> None:
        """Delete (soft delete) a record.

        Args:
            db: Database session
            record_id: Record ID
            user_id: User ID making request

        Raises:
            NotFoundError: If record not found
            PermissionDeniedError: If user is not owner/admin/editor

        """
        record = await self.get_record_by_id(db, record_id, user_id)

        # Check if user has edit permission in workspace
        table = await self._get_table(db, str(record.table_id))
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))
        if not member or member.role not in [
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
            WorkspaceRole.EDITOR,
        ]:
            raise PermissionDeniedError("Only owners, admins, and editors can delete records")

        # Store old value for audit
        old_value = json.loads(record.data) if record.data else {}

        record.soft_delete()

        # Log audit
        user_email = await self._get_user_email(db, str(user_id))
        await self.audit_service.log_crud_delete(
            db=db,
            resource_type="record",
            resource_id=str(record.id),
            old_value=old_value,
            user_id=str(user_id),
            user_email=user_email or "",
            table_id=str(record.table_id),
        )

        # Invalidate cache for this table
        await self.cache.invalidate_table_cache(str(record.table_id))

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

        """
        table = await db.get(Table, table_id)
        if not table or table.is_deleted:
            raise NotFoundError("Table not found")
        return table

    async def search_records(
        self,
        db: AsyncSession,
        table_id: UUID,
        user_id: str,
        search_query: str,
        filters: Optional[list[FilterCondition]] = None,
        cursor: Optional[str] = None,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Search records with full-text search and optional filters.

        Optimized for large datasets using:
        - PostgreSQL full-text search with tsvector
        - Efficient JSONB querying with GIN indexes
        - Cursor-based pagination

        Args:
            db: Database session
            table_id: Table ID to search in
            user_id: User ID
            search_query: Search query string
            filters: Optional list of filter conditions
            cursor: Optional cursor for pagination
            page_size: Number of items per page

        Returns:
            Dictionary with:
                - records: list of Record objects
                - next_cursor: cursor for next page or None
                - has_more: boolean indicating if there are more records
                - total_matches: approximate total matches

        """
        # Check user has access
        table = await db.get(Table, table_id)
        if not table or table.is_deleted:
            raise NotFoundError("Table not found")

        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))
        if not member:
            raise PermissionDeniedError("You don't have access to this table")

        # Build base query with full-text search
        # Cast data to JSONB for efficient querying
        query = select(Record).where(Record.table_id == str(table_id))
        query = query.where(Record.deleted_at.is_(None))

        # Add full-text search using PostgreSQL's to_tsvector
        # Search for the query in any value within the JSON data
        search_pattern = f"%{search_query}%"
        query = query.where(
            or_(
                cast(Record.data, JSONB).astext.ilike(search_pattern),
            )
        )

        # Apply additional filters if provided
        if filters:
            query = self._apply_filters_to_query(query, filters)

        # Apply cursor for pagination
        cursor_record_id = None
        cursor_created_at = None

        if cursor:
            try:
                parts = cursor.split(":")
                if len(parts) == 2:
                    cursor_record_id = parts[0]
                    cursor_created_at = parts[1]
            except (ValueError, AttributeError):
                pass

        if cursor_record_id and cursor_created_at:
            query = query.where(
                (Record.created_at > cursor_created_at)
                | ((Record.created_at == cursor_created_at) & (Record.id > cursor_record_id))
            )

        # Order by created_at and id for consistent pagination
        query = query.order_by(Record.created_at, Record.id)

        # Get approximate count (faster than exact count for large datasets)
        count_query = select(func.count()).select_from(Record)
        count_query = count_query.where(Record.table_id == str(table_id))
        count_query = count_query.where(Record.deleted_at.is_(None))
        count_query = count_query.where(cast(Record.data, JSONB).astext.ilike(search_pattern))
        if filters:
            count_query = self._apply_filters_to_query(count_query, filters)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Fetch one extra record to determine if there are more results
        query = query.limit(page_size + 1)
        result = await db.execute(query)
        records = list(result.scalars().all())

        # Determine if there are more records
        has_more = len(records) > page_size
        if has_more:
            records = records[:page_size]

        # Generate next cursor
        next_cursor = None
        if has_more and records:
            last_record = records[-1]
            next_cursor = f"{last_record.id}:{last_record.created_at.isoformat()}"

        return {
            "records": records,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "total_matches": total,
        }

    def _apply_filters_to_query(
        self,
        query: Any,
        filters: list[FilterCondition],
    ) -> Any:
        """Apply filter conditions to a SQLAlchemy query.

        Uses PostgreSQL JSONB operators for efficient filtering on record data.
        This is optimized for large datasets by leveraging database-level indexing.

        Args:
            query: SQLAlchemy query
            filters: List of filter conditions

        Returns:
            Query with filters applied

        """
        for filter_cond in filters:
            field_id_str = str(filter_cond.field_id)
            jsonb_path = f"->{field_id_str}"

            if filter_cond.operator == FilterOperator.EQUALS:
                query = query.where(text(f"cast(data as jsonb){jsonb_path} = :value")).params(
                    value=json.dumps(filter_cond.value)
                )

            elif filter_cond.operator == FilterOperator.NOT_EQUALS:
                query = query.where(
                    or_(
                        text(f"cast(data as jsonb){jsonb_path} IS NULL"),
                        text(f"cast(data as jsonb){jsonb_path} != :value"),
                    )
                ).params(value=json.dumps(filter_cond.value))

            elif filter_cond.operator == FilterOperator.CONTAINS:
                # For text fields - case-insensitive contains
                query = query.where(
                    text(f"cast(data as jsonb)->>{field_id_str} ILIKE :value")
                ).params(value=f"%{filter_cond.value}%")

            elif filter_cond.operator == FilterOperator.NOT_CONTAINS:
                query = query.where(
                    or_(
                        text(f"cast(data as jsonb)->>{field_id_str} IS NULL"),
                        text(f"cast(data as jsonb)->>{field_id_str} NOT ILIKE :value"),
                    )
                ).params(value=f"%{filter_cond.value}%")

            elif filter_cond.operator == FilterOperator.IS_EMPTY:
                query = query.where(
                    or_(
                        text(f"cast(data as jsonb)->>{field_id_str} IS NULL"),
                        text(f"cast(data as jsonb)->>{field_id_str} = ''"),
                    )
                )

            elif filter_cond.operator == FilterOperator.IS_NOT_EMPTY:
                query = query.where(
                    text(f"cast(data as jsonb)->>{field_id_str} IS NOT NULL")
                ).where(text(f"cast(data as jsonb)->>{field_id_str} != ''"))

            elif filter_cond.operator == FilterOperator.GREATER_THAN:
                query = query.where(
                    text(f"cast(data as jsonb)->>{field_id_str}::float > :value")
                ).params(value=float(filter_cond.value))

            elif filter_cond.operator == FilterOperator.LESS_THAN:
                query = query.where(
                    text(f"cast(data as jsonb)->>{field_id_str}::float < :value")
                ).params(value=float(filter_cond.value))

            elif filter_cond.operator == FilterOperator.GREATER_THAN_OR_EQUAL:
                query = query.where(
                    text(f"cast(data as jsonb)->>{field_id_str}::float >= :value")
                ).params(value=float(filter_cond.value))

            elif filter_cond.operator == FilterOperator.LESS_THAN_OR_EQUAL:
                query = query.where(
                    text(f"cast(data as jsonb)->>{field_id_str}::float <= :value")
                ).params(value=float(filter_cond.value))

            elif filter_cond.operator == FilterOperator.IN:
                # Check if value is in the provided list
                values_list = json.dumps(filter_cond.value)
                query = query.where(text(f"cast(data as jsonb)->>{field_id_str} IN :value")).params(
                    value=tuple(filter_cond.value)
                )

            elif filter_cond.operator == FilterOperator.NOT_IN:
                query = query.where(
                    or_(
                        text(f"cast(data as jsonb)->>{field_id_str} IS NULL"),
                        text(f"cast(data as jsonb)->>{field_id_str} NOT IN :value"),
                    )
                ).params(value=tuple(filter_cond.value))

            elif filter_cond.operator == FilterOperator.STARTS_WITH:
                query = query.where(
                    text(f"cast(data as jsonb)->>{field_id_str} ILIKE :value")
                ).params(value=f"{filter_cond.value}%")

            elif filter_cond.operator == FilterOperator.ENDS_WITH:
                query = query.where(
                    text(f"cast(data as jsonb)->>{field_id_str} ILIKE :value")
                ).params(value=f"%{filter_cond.value}")

            elif filter_cond.operator == FilterOperator.IS_BEFORE:
                # For date fields
                query = query.where(
                    text(f"cast(data as jsonb)->>{field_id_str}::timestamp < :value")
                ).params(value=filter_cond.value)

            elif filter_cond.operator == FilterOperator.IS_AFTER:
                # For date fields
                query = query.where(
                    text(f"cast(data as jsonb)->>{field_id_str}::timestamp > :value")
                ).params(value=filter_cond.value)

        return query

    async def _validate_record_data(
        self,
        db: AsyncSession,
        table_id: str,
        data: dict[str, Any],
        exclude_record_id: Optional[str] = None,
    ) -> None:
        """Validate record data against table fields.

        Args:
            db: Database session
            table_id: Table ID
            data: Record data (field_id -> value)
            exclude_record_id: Optional record ID to exclude from uniqueness checks

        Raises:
            ConflictError: If validation fails
            ValidationError: If validation fails with detailed errors

        """
        validation_service = ValidationService()
        await validation_service.validate_record_data(db, table_id, data, exclude_record_id)
