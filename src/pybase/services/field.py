"""Field service for business logic."""

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
from pybase.models.field import Field, FieldType
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.field import FieldCreate, FieldUpdate


class FieldService:
    """Service for field operations."""

    async def create_field(
        self,
        db: AsyncSession,
        user_id: str,
        field_data: FieldCreate,
    ) -> Field:
        """Create a new field in a table.

        Args:
            db: Database session
            user_id: User ID creating field
            field_data: Field creation data

        Returns:
            Created field

        Raises:
            NotFoundError: If table not found
            PermissionDeniedError: If user doesn't have access to table
            ConflictError: If primary field already exists or field type invalid

        """
        # Check if table exists
        table = await db.get(Table, field_data.table_id)
        if not table or table.is_deleted:
            raise NotFoundError("Table not found")

        # Check if user has access to workspace
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, workspace.id, user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this table")

        # Validate field type
        try:
            FieldType(field_data.field_type)
        except ValueError:
            raise ConflictError(f"Invalid field type: {field_data.field_type}")

        # Check primary field constraint
        if field_data.options and field_data.options.get("is_primary", False):
            existing_primary = await self._get_primary_field(db, str(field_data.table_id))
            if existing_primary:
                raise ConflictError(
                    "Table already has a primary field. Only one primary field is allowed."
                )

        # Determine position (append to end)
        max_position_query = select(func.max(Field.position)).where(
            Field.table_id == field_data.table_id,
            Field.deleted_at.is_(None),
        )
        result = await db.execute(max_position_query)
        max_position = result.scalar() or 0

        # Create field
        field = Field(
            table_id=str(field_data.table_id),
            name=field_data.name,
            description=field_data.description,
            field_type=field_data.field_type.value,
            options=json.dumps(field_data.options) if field_data.options else "{}",
            is_required=field_data.is_required,
            is_unique=field_data.is_unique,
            position=field_data.position if field_data.position else max_position + 1,
            is_primary=field_data.options.get("is_primary", False) if field_data.options else False,
        )
        db.add(field)
        await db.refresh(field)

        # Update table primary_field_id if this is primary
        if field.is_primary:
            table.primary_field_id = field.id
            await db.refresh(table)

        return field

    async def get_field_by_id(
        self,
        db: AsyncSession,
        field_id: str,
        user_id: str,
    ) -> Field:
        """Get a field by ID, checking user access.

        Args:
            db: Database session
            field_id: Field ID
            user_id: User ID requesting access

        Returns:
            Field

        Raises:
            NotFoundError: If field not found
            PermissionDeniedError: If user doesn't have access

        """
        field = await db.get(Field, field_id)
        if not field or field.is_deleted:
            raise NotFoundError("Field not found")

        # Check if user has access to workspace
        table = await self._get_table(db, field.table_id)
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, workspace.id, user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this field")

        return field

    async def list_fields(
        self,
        db: AsyncSession,
        table_id: Optional[UUID],
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Field], int]:
        """List fields accessible to user.

        Args:
            db: Database session
            table_id: Optional table ID to filter by
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (fields, total count)

        """
        offset = (page - 1) * page_size

        # Count query
        count_query = (
            select(func.count()).select_from(Field).join(Table).join(Base).join(WorkspaceMember)
        )
        if table_id:
            count_query = count_query.where(Field.table_id == table_id)
        count_query = count_query.where(WorkspaceMember.user_id == user_id)
        count_query = count_query.where(Field.deleted_at.is_(None))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query
        query = select(Field).join(Table).join(Base).join(WorkspaceMember)
        if table_id:
            query = query.where(Field.table_id == table_id)
        query = query.where(WorkspaceMember.user_id == user_id)
        query = query.where(Field.deleted_at.is_(None))
        query = query.order_by(Field.position)
        query = query.offset(offset)
        query = query.limit(page_size)
        result = await db.execute(query)
        fields = result.scalars().all()

        return list(fields), total

    async def update_field(
        self,
        db: AsyncSession,
        field_id: str,
        user_id: str,
        field_data: FieldUpdate,
    ) -> Field:
        """Update a field.

        Args:
            db: Database session
            field_id: Field ID
            user_id: User ID making request
            field_data: Field update data

        Returns:
            Updated field

        Raises:
            NotFoundError: If field not found
            PermissionDeniedError: If user doesn't have permission
            ConflictError: If primary field constraint violated

        """
        field = await self.get_field_by_id(db, field_id, user_id)

        # Check if user has admin or owner role in workspace
        table = await self._get_table(db, field.table_id)
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, workspace.id, user_id)
        if not member or member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
            raise PermissionDeniedError("Only owners and admins can update fields")

        # Check primary field constraint if setting as primary
        if field_data.is_primary and not field.is_primary:
            existing_primary = await self._get_primary_field(db, field.table_id)
            if existing_primary and existing_primary.id != field_id:
                raise ConflictError(
                    "Table already has a primary field. Only one primary field is allowed."
                )

        # Update fields
        if field_data.name is not None:
            field.name = field_data.name
        if field_data.description is not None:
            field.description = field_data.description
        if field_data.options is not None:
            field.options = json.dumps(field_data.options)
        if field_data.is_required is not None:
            field.is_required = field_data.is_required
        if field_data.is_unique is not None:
            field.is_unique = field_data.is_unique
        if field_data.width is not None:
            field.width = field_data.width
        if field_data.is_visible is not None:
            field.is_visible = field_data.is_visible
        if field_data.is_primary is not None:
            field.is_primary = field_data.is_primary

        await db.refresh(field)

        # Update table primary_field_id if this is primary
        if field.is_primary:
            table.primary_field_id = field.id
            await db.refresh(table)

        return field

    async def delete_field(
        self,
        db: AsyncSession,
        field_id: str,
        user_id: str,
    ) -> None:
        """Delete (soft delete) a field.

        Args:
            db: Database session
            field_id: Field ID
            user_id: User ID making request

        Raises:
            NotFoundError: If field not found
            PermissionDeniedError: If user is not owner

        """
        field = await self.get_field_by_id(db, field_id, user_id)

        # Only workspace owner can delete fields
        table = await self._get_table(db, field.table_id)
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        if workspace.owner_id != user_id:
            raise PermissionDeniedError("Only workspace owner can delete fields")

        field.soft_delete()

        # Clear table primary_field_id if this was primary
        if field.is_primary:
            table.primary_field_id = None

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

    async def _get_primary_field(
        self,
        db: AsyncSession,
        table_id: str,
    ) -> Optional[Field]:
        """Get primary field for table.

        Args:
            db: Database session
            table_id: Table ID

        Returns:
            Primary field or None

        """
        query = select(Field).where(
            Field.table_id == table_id,
            Field.is_primary.is_(True),
            Field.deleted_at.is_(None),
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
