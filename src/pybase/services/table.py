"""Table service for business logic."""

from typing import Optional
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
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.table import TableCreate, TableUpdate


class TableService:
    """Service for table operations."""

    async def create_table(
        self,
        db: AsyncSession,
        user_id: str,
        table_data: TableCreate,
    ) -> Table:
        """Create a new table in a base.

        Args:
            db: Database session
            user_id: User ID creating the table
            table_data: Table creation data

        Returns:
            Created table

        Raises:
            NotFoundError: If base not found
            PermissionDeniedError: If user doesn't have access to base
            ConflictError: If primary_field_id is not in the base

        """
        # Check if base exists
        base = await db.get(Base, table_data.base_id)
        if not base or base.is_deleted:
            raise NotFoundError("Base not found")

        # Check if user has access to workspace
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, workspace.id, user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this base")

        # Check primary field if provided
        if table_data.primary_field_id:
            field = await db.get(Field, table_data.primary_field_id)
            if not field or field.is_deleted:
                raise NotFoundError("Field not found")
            if field.table_id != table_data.base_id:
                raise ConflictError("Primary field must be in the same base")

        # Determine position (append to end)
        max_position_query = select(func.max(Table.position)).where(
            Table.base_id == table_data.base_id,
            Table.is_deleted.is_(False),
        )
        result = await db.execute(max_position_query)
        max_position = result.scalar() or 0

        # Create table
        table = Table(
            base_id=table_data.base_id,
            name=table_data.name,
            description=table_data.description,
            primary_field_id=table_data.primary_field_id,
            position=max_position + 1,
        )
        db.add(table)
        await db.refresh(table)

        return table

    async def get_table_by_id(
        self,
        db: AsyncSession,
        table_id: str,
        user_id: str,
    ) -> Table:
        """Get a table by ID, checking user access.

        Args:
            db: Database session
            table_id: Table ID
            user_id: User ID requesting access

        Returns:
            Table

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access

        """
        table = await db.get(Table, table_id)
        if not table or table.is_deleted:
            raise NotFoundError("Table not found")

        # Check if user has access to workspace
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, workspace.id, user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this table")

        return table

    async def list_tables(
        self,
        db: AsyncSession,
        base_id: Optional[UUID],
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Table], int]:
        """List tables accessible to user.

        Args:
            db: Database session
            base_id: Optional base ID to filter by
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (tables, total count)

        """
        offset = (page - 1) * page_size

        # Count query
        count_query = select(func.count()).select_from(Table).join(Base).join(WorkspaceMember)
        if base_id:
            count_query = count_query.where(Table.base_id == base_id)
        count_query = count_query.where(WorkspaceMember.user_id == user_id)
        count_query = count_query.where(Table.is_deleted.is_(False))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query
        query = select(Table).join(Base).join(WorkspaceMember)
        if base_id:
            query = query.where(Table.base_id == base_id)
        query = query.where(WorkspaceMember.user_id == user_id)
        query = query.where(Table.is_deleted.is_(False))
        query = query.order_by(Table.position)
        query = query.offset(offset)
        query = query.limit(page_size)
        result = await db.execute(query)
        tables = result.scalars().all()

        return list(tables), total

    async def update_table(
        self,
        db: AsyncSession,
        table_id: str,
        user_id: str,
        table_data: TableUpdate,
    ) -> Table:
        """Update a table.

        Args:
            db: Database session
            table_id: Table ID
            user_id: User ID making request
            table_data: Table update data

        Returns:
            Updated table

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have permission
            ConflictError: If primary field is invalid

        """
        table = await self.get_table_by_id(db, table_id, user_id)

        # Check primary field if provided
        if table_data.primary_field_id:
            field = await db.get(Field, table_data.primary_field_id)
            if not field or field.is_deleted:
                raise NotFoundError("Field not found")
            if field.table_id != table.base_id:
                raise ConflictError("Primary field must be in the same base")

        # Check if user has admin or owner role in workspace
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, workspace.id, user_id)
        if not member or member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
            raise PermissionDeniedError("Only owners and admins can update tables")

        # Update fields
        if table_data.name is not None:
            table.name = table_data.name
        if table_data.description is not None:
            table.description = table_data.description
        if table_data.primary_field_id is not None:
            table.primary_field_id = table_data.primary_field_id

        await db.refresh(table)

        return table

    async def delete_table(
        self,
        db: AsyncSession,
        table_id: str,
        user_id: str,
    ) -> None:
        """Delete (soft delete) a table.

        Args:
            db: Database session
            table_id: Table ID
            user_id: User ID making request

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user is not owner

        """
        table = await self.get_table_by_id(db, table_id, user_id)

        # Only workspace owner can delete tables
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        if workspace.owner_id != user_id:
            raise PermissionDeniedError("Only workspace owner can delete tables")

        table.is_deleted = True

    async def _get_workspace(
        self,
        db: AsyncSession,
        workspace_id: UUID,
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
        workspace_id: UUID,
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
