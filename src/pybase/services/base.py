"""Base service for business logic."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.models.base import Base
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.base import BaseCreate, BaseUpdate


class BaseService:
    """Service for base operations."""

    async def create_base(
        self,
        db: AsyncSession,
        user_id: str,
        base_data: BaseCreate,
    ) -> Base:
        """Create a new base in a workspace.

        Args:
            db: Database session
            user_id: User ID creating the base
            base_data: Base creation data

        Returns:
            Created base

        Raises:
            NotFoundError: If workspace not found
            PermissionDeniedError: If user doesn't have access to workspace

        """
        # Check if workspace exists and user has access
        workspace = await db.get(Workspace, base_data.workspace_id)
        if not workspace or workspace.is_deleted:
            raise NotFoundError("Workspace not found")

        # Check if user has access to workspace
        member = await self._get_workspace_member(db, base_data.workspace_id, user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this workspace")

        # Create base
        base = Base(
            workspace_id=base_data.workspace_id,
            name=base_data.name,
            description=base_data.description,
            icon=base_data.icon,
        )
        db.add(base)
        await db.commit()
        await db.refresh(base)

        return base

    async def get_base_by_id(
        self,
        db: AsyncSession,
        base_id: str,
        user_id: str,
    ) -> Base:
        """Get a base by ID, checking user access.

        Args:
            db: Database session
            base_id: Base ID
            user_id: User ID requesting access

        Returns:
            Base

        Raises:
            NotFoundError: If base not found
            PermissionDeniedError: If user doesn't have access

        """
        base = await db.get(Base, base_id)
        if not base or base.is_deleted:
            raise NotFoundError("Base not found")

        # Check if user has access to workspace
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, workspace.id, user_id)
        if not member:
            raise PermissionDeniedError("You don't have access to this base")

        return base

    async def list_bases(
        self,
        db: AsyncSession,
        workspace_id: Optional[str],
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Base], int]:
        """List bases accessible to user.

        Args:
            db: Database session
            workspace_id: Optional workspace ID to filter by
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (bases, total count)

        """
        offset = (page - 1) * page_size

        # Count query
        count_query = select(func.count()).select_from(Base).join(WorkspaceMember)
        if workspace_id:
            count_query = count_query.where(Base.workspace_id == workspace_id)
        count_query = count_query.where(WorkspaceMember.user_id == user_id)
        count_query = count_query.where(Base.is_deleted.is_(False))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query
        query = select(Base).join(WorkspaceMember)
        if workspace_id:
            query = query.where(Base.workspace_id == workspace_id)
        query = query.where(WorkspaceMember.user_id == user_id)
        query = query.where(Base.is_deleted.is_(False))
        query = query.order_by(Base.created_at.desc())
        query = query.offset(offset)
        query = query.limit(page_size)
        result = await db.execute(query)
        bases = result.scalars().all()

        return list(bases), total

    async def update_base(
        self,
        db: AsyncSession,
        base_id: str,
        user_id: str,
        base_data: BaseUpdate,
    ) -> Base:
        """Update a base.

        Args:
            db: Database session
            base_id: Base ID
            user_id: User ID making request
            base_data: Base update data

        Returns:
            Updated base

        Raises:
            NotFoundError: If base not found
            PermissionDeniedError: If user doesn't have permission

        """
        base = await self.get_base_by_id(db, base_id, user_id)

        # Check if user has admin or owner role in workspace
        workspace = await self._get_workspace(db, base.workspace_id)
        member = await self._get_workspace_member(db, workspace.id, user_id)
        if not member or member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
            raise PermissionDeniedError("Only owners and admins can update bases")

        # Update fields
        if base_data.name is not None:
            base.name = base_data.name
        if base_data.description is not None:
            base.description = base_data.description
        if base_data.icon is not None:
            base.icon = base_data.icon

        await db.commit()
        await db.refresh(base)

        return base

    async def delete_base(
        self,
        db: AsyncSession,
        base_id: str,
        user_id: str,
    ) -> None:
        """Delete (soft delete) a base.

        Args:
            db: Database session
            base_id: Base ID
            user_id: User ID making request

        Raises:
            NotFoundError: If base not found
            PermissionDeniedError: If user is not owner

        """
        base = await self.get_base_by_id(db, base_id, user_id)

        # Only workspace owner can delete bases
        workspace = await self._get_workspace(db, base.workspace_id)
        if workspace.owner_id != user_id:
            raise PermissionDeniedError("Only workspace owner can delete bases")

        base.is_deleted = True
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
