"""Record service for business logic."""

import json
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.models.base import Base
from pybase.models.field import Field
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.record import RecordCreate, RecordUpdate


class RecordService:
    """Service for record operations."""

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
        await db.commit()
        await db.refresh(record)

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

            deleted_records.append(record)

        # Delete all records (soft delete)
        for record in deleted_records:
            record.soft_delete()

        # Commit all deletions in a single transaction
        await db.commit()

        # Refresh all records to get updated timestamps
        for record in deleted_records:
            await db.refresh(record)

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
            await self._validate_record_data(db, str(table.id), record_data.data)

        # Update fields
        if record_data.data is not None:
            record.data = json.dumps(record_data.data)
        if record_data.row_height is not None:
            record.row_height = record_data.row_height
        record.last_modified_by_id = str(user_id)

        await db.commit()
        await db.refresh(record)

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

        record.soft_delete()
        await db.commit()

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

    async def _validate_record_data(
        self,
        db: AsyncSession,
        table_id: str,
        data: dict[str, Any],
    ) -> None:
        """Validate record data against table fields.

        Args:
            db: Database session
            table_id: Table ID
            data: Record data (field_id -> value)

        Raises:
            ConflictError: If validation fails

        """
        # Get all fields for table
        fields_query = select(Field).where(
            Field.table_id == table_id,
            Field.deleted_at.is_(None),
        )
        result = await db.execute(fields_query)
        fields = result.scalars().all()
        fields_dict = {str(f.id): f for f in fields}

        # Validate each field in data
        for field_id, value in data.items():
            if field_id not in fields_dict:
                raise ConflictError(f"Field {field_id} does not exist in table")

            field = fields_dict[field_id]

            # Check required fields
            if field.is_required and value is None:
                raise ConflictError(f"Field '{field.name}' is required")

            # Validate using field handler if available
            from pybase.fields import get_field_handler

            handler = get_field_handler(field.field_type)
            if handler:
                # Parse field options
                options = None
                if field.options:
                    try:
                        options = json.loads(field.options)
                    except (json.JSONDecodeError, TypeError):
                        options = {}

                # Validate value
                try:
                    handler.validate(value, options)
                except ValueError as e:
                    raise ConflictError(f"Invalid value for field '{field.name}': {e}")
