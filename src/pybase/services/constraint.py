"""Constraint service for business logic."""

from typing import Optional

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
from pybase.models.unique_constraint import (
    UniqueConstraint,
    UniqueConstraintStatus,
)
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.constraint import UniqueConstraintCreate, UniqueConstraintUpdate


class ConstraintService:
    """Service for unique constraint operations."""

    async def create_constraint(
        self,
        db: AsyncSession,
        user_id: str,
        constraint_data: UniqueConstraintCreate,
    ) -> UniqueConstraint:
        """Create a new unique constraint on a field.

        Args:
            db: Database session
            user_id: User ID creating constraint
            constraint_data: Constraint creation data

        Returns:
            Created constraint

        Raises:
            NotFoundError: If field not found
            PermissionDeniedError: If user doesn't have access to field
            ConflictError: If constraint already exists for field

        """
        # Check if field exists and get access info
        field = await db.get(Field, str(constraint_data.field_id))
        if not field or field.is_deleted:
            raise NotFoundError("Field not found")

        # Check if user has access to workspace
        table = await self._get_table(db, field.table_id)
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, workspace.id, user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this field")

        # Check if constraint already exists for this field
        existing_constraint = await self._get_constraint_by_field(
            db, str(constraint_data.field_id)
        )
        if existing_constraint:
            raise ConflictError(
                "A unique constraint already exists for this field. "
                "Only one constraint per field is allowed."
            )

        # Create constraint
        constraint = UniqueConstraint(
            field_id=str(constraint_data.field_id),
            status=constraint_data.status,
            case_sensitive=constraint_data.case_sensitive,
            error_message=constraint_data.error_message,
        )
        db.add(constraint)
        await db.commit()
        await db.refresh(constraint)

        return constraint

    async def get_constraint_by_id(
        self,
        db: AsyncSession,
        constraint_id: str,
        user_id: str,
    ) -> UniqueConstraint:
        """Get a constraint by ID, checking user access.

        Args:
            db: Database session
            constraint_id: Constraint ID
            user_id: User ID requesting access

        Returns:
            UniqueConstraint

        Raises:
            NotFoundError: If constraint not found
            PermissionDeniedError: If user doesn't have access

        """
        constraint = await db.get(UniqueConstraint, constraint_id)
        if not constraint:
            raise NotFoundError("Constraint not found")

        # Check if user has access to workspace
        field = await self._get_field(db, constraint.field_id)
        table = await self._get_table(db, field.table_id)
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, workspace.id, user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this constraint")

        return constraint

    async def list_constraints(
        self,
        db: AsyncSession,
        field_id: Optional[str],
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[UniqueConstraint], int]:
        """List constraints accessible to user.

        Args:
            db: Database session
            field_id: Optional field ID to filter by
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (constraints, total count)

        """
        offset = (page - 1) * page_size

        # Count query
        count_query = (
            select(func.count())
            .select_from(UniqueConstraint)
            .join(Field)
            .join(Table)
            .join(Base)
            .join(WorkspaceMember)
        )
        if field_id:
            count_query = count_query.where(UniqueConstraint.field_id == field_id)
        count_query = count_query.where(WorkspaceMember.user_id == user_id)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query
        query = (
            select(UniqueConstraint)
            .join(Field)
            .join(Table)
            .join(Base)
            .join(WorkspaceMember)
        )
        if field_id:
            query = query.where(UniqueConstraint.field_id == field_id)
        query = query.where(WorkspaceMember.user_id == user_id)
        query = query.order_by(UniqueConstraint.created_at.desc())
        query = query.offset(offset)
        query = query.limit(page_size)
        result = await db.execute(query)
        constraints = result.scalars().all()

        return list(constraints), total

    async def update_constraint(
        self,
        db: AsyncSession,
        constraint_id: str,
        user_id: str,
        constraint_data: UniqueConstraintUpdate,
    ) -> UniqueConstraint:
        """Update a constraint.

        Args:
            db: Database session
            constraint_id: Constraint ID
            user_id: User ID making request
            constraint_data: Constraint update data

        Returns:
            Updated constraint

        Raises:
            NotFoundError: If constraint not found
            PermissionDeniedError: If user doesn't have permission

        """
        constraint = await self.get_constraint_by_id(db, constraint_id, user_id)

        # Check if user has admin or owner role in workspace
        field = await self._get_field(db, constraint.field_id)
        table = await self._get_table(db, field.table_id)
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, workspace.id, user_id)
        if not member or member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
            raise PermissionDeniedError(
                "Only owners and admins can update constraints"
            )

        # Update fields
        if constraint_data.status is not None:
            # Validate status
            try:
                UniqueConstraintStatus(constraint_data.status)
            except ValueError:
                raise ConflictError(f"Invalid constraint status: {constraint_data.status}")
            constraint.status = constraint_data.status

        if constraint_data.case_sensitive is not None:
            constraint.case_sensitive = constraint_data.case_sensitive

        if constraint_data.error_message is not None:
            constraint.error_message = constraint_data.error_message

        await db.commit()
        await db.refresh(constraint)

        return constraint

    async def delete_constraint(
        self,
        db: AsyncSession,
        constraint_id: str,
        user_id: str,
    ) -> None:
        """Delete a constraint.

        Args:
            db: Database session
            constraint_id: Constraint ID
            user_id: User ID making request

        Raises:
            NotFoundError: If constraint not found
            PermissionDeniedError: If user is not owner

        """
        constraint = await self.get_constraint_by_id(db, constraint_id, user_id)

        # Only workspace owner can delete constraints
        field = await self._get_field(db, constraint.field_id)
        table = await self._get_table(db, field.table_id)
        base = await self._get_base(db, table.base_id)
        workspace = await self._get_workspace(db, base.workspace_id)
        if workspace.owner_id != user_id:
            raise PermissionDeniedError("Only workspace owner can delete constraints")

        await db.delete(constraint)
        await db.commit()

    async def get_constraint_by_field(
        self,
        db: AsyncSession,
        field_id: str,
    ) -> Optional[UniqueConstraint]:
        """Get constraint for a specific field.

        Args:
            db: Database session
            field_id: Field ID

        Returns:
            UniqueConstraint or None

        """
        query = select(UniqueConstraint).where(
            UniqueConstraint.field_id == field_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

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

    async def _get_field(
        self,
        db: AsyncSession,
        field_id: str,
    ) -> Field:
        """Get field by ID.

        Args:
            db: Database session
            field_id: Field ID

        Returns:
            Field

        """
        field = await db.get(Field, field_id)
        if not field or field.is_deleted:
            raise NotFoundError("Field not found")
        return field

    async def _get_constraint_by_field(
        self,
        db: AsyncSession,
        field_id: str,
    ) -> Optional[UniqueConstraint]:
        """Get constraint for a field.

        Args:
            db: Database session
            field_id: Field ID

        Returns:
            UniqueConstraint or None

        """
        query = select(UniqueConstraint).where(
            UniqueConstraint.field_id == field_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
