"""Workspace service for business logic."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from pybase.models.user import User
from pybase.models.workspace import (
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)
from pybase.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


class WorkspaceService:
    """Service for workspace operations."""

    async def create_workspace(
        self,
        db: AsyncSession,
        owner_id: str,
        workspace_data: WorkspaceCreate,
    ) -> Workspace:
        """Create a new workspace.

        Args:
            db: Database session
            owner_id: Owner user ID
            workspace_data: Workspace creation data

        Returns:
            Created workspace

        """
        workspace = Workspace(
            owner_id=owner_id,
            name=workspace_data.name,
            description=workspace_data.description,
        )
        db.add(workspace)

        # Add owner as workspace member with owner role
        owner_member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=owner_id,
            role=WorkspaceRole.OWNER,
        )
        db.add(owner_member)

        await db.commit()
        await db.refresh(workspace)

        return workspace

    async def get_workspace_by_id(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
    ) -> Workspace:
        """Get a workspace by ID, checking user access.

        Args:
            db: Database session
            workspace_id: Workspace ID
            user_id: User ID requesting access

        Returns:
            Workspace

        Raises:
            NotFoundError: If workspace not found
            PermissionDeniedError: If user doesn't have access

        """
        workspace = await db.get(Workspace, workspace_id)
        if not workspace or workspace.is_deleted:
            raise NotFoundError("Workspace not found")

        # Check if user has access to workspace
        has_access = await self._check_workspace_access(db, workspace_id, user_id)
        if not has_access:
            raise PermissionDeniedError("You don't have access to this workspace")

        return workspace

    async def list_workspaces(
        self,
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Workspace], int]:
        """List workspaces accessible to user.

        Args:
            db: Database session
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (workspaces, total count)

        """
        offset = (page - 1) * page_size

        # Count query
        count_query = (
            select(func.count())
            .select_from(Workspace)
            .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
            .where(WorkspaceMember.user_id == user_id)
            .where(Workspace.deleted_at.is_(None))
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query
        query = (
            select(Workspace)
            .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
            .where(WorkspaceMember.user_id == user_id)
            .where(Workspace.deleted_at.is_(None))
            .order_by(Workspace.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        workspaces = result.scalars().all()

        return list(workspaces), total

    async def update_workspace(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
        workspace_data: WorkspaceUpdate,
    ) -> Workspace:
        """Update a workspace.

        Args:
            db: Database session
            workspace_id: Workspace ID
            user_id: User ID making the request
            workspace_data: Workspace update data

        Returns:
            Updated workspace

        Raises:
            NotFoundError: If workspace not found
            PermissionDeniedError: If user doesn't have permission

        """
        workspace = await self.get_workspace_by_id(db, workspace_id, user_id)

        # Check if user has admin or owner role
        member = await self._get_workspace_member(db, workspace_id, user_id)
        if member and member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
            raise PermissionDeniedError("Only owners and admins can update workspaces")

        # Update fields
        if workspace_data.name is not None:
            workspace.name = workspace_data.name
        if workspace_data.description is not None:
            workspace.description = workspace_data.description

        await db.commit()
        await db.refresh(workspace)

        return workspace

    async def delete_workspace(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
    ) -> None:
        """Delete (soft delete) a workspace.

        Args:
            db: Database session
            workspace_id: Workspace ID
            user_id: User ID making the request

        Raises:
            NotFoundError: If workspace not found
            PermissionDeniedError: If user is not owner

        """
        workspace = await self.get_workspace_by_id(db, workspace_id, user_id)

        # Only owner can delete workspace
        if workspace.owner_id != user_id:
            raise PermissionDeniedError("Only the workspace owner can delete it")

        workspace.soft_delete()
        await db.commit()

    async def add_member(
        self,
        db: AsyncSession,
        workspace_id: str,
        owner_id: str,
        user_id: str,
        role: WorkspaceRole,
    ) -> WorkspaceMember:
        """Add a member to workspace.

        Args:
            db: Database session
            workspace_id: Workspace ID
            owner_id: User ID making the request
            user_id: User ID to add
            role: Role to assign

        Returns:
            Created workspace member

        Raises:
            NotFoundError: If workspace or user not found
            PermissionDeniedError: If requester not authorized
            ConflictError: If user already member

        """
        workspace = await self.get_workspace_by_id(db, workspace_id, owner_id)

        # Only owner and admin can add members
        member = await self._get_workspace_member(db, workspace_id, owner_id)
        if not member or member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
            raise PermissionDeniedError("Only owners and admins can add members")

        # Check if user exists
        user = await db.get(User, user_id)
        if not user:
            raise NotFoundError("User not found")

        # Check if user already member
        existing_member = await self._get_workspace_member(db, workspace_id, user_id)
        if existing_member:
            raise ConflictError("User is already a member of this workspace")

        # Create member
        new_member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )
        db.add(new_member)
        await db.commit()
        await db.refresh(new_member)

        return new_member

    async def update_member_role(
        self,
        db: AsyncSession,
        workspace_id: str,
        requester_id: str,
        member_id: str,
        role: WorkspaceRole,
    ) -> WorkspaceMember:
        """Update a member's role.

        Args:
            db: Database session
            workspace_id: Workspace ID
            requester_id: User ID making the request
            member_id: WorkspaceMember ID
            role: New role

        Returns:
            Updated workspace member

        Raises:
            NotFoundError: If workspace or member not found
            PermissionDeniedError: If requester not authorized

        """
        workspace = await self.get_workspace_by_id(db, workspace_id, requester_id)

        # Only owner can update roles
        if workspace.owner_id != requester_id:
            raise PermissionDeniedError("Only the workspace owner can update roles")

        member = await db.get(WorkspaceMember, member_id)
        if not member or member.workspace_id != workspace_id:
            raise NotFoundError("Workspace member not found")

        # Cannot change owner role
        if member.role == WorkspaceRole.OWNER:
            raise PermissionDeniedError("Cannot change owner role")

        member.role = role
        await db.commit()
        await db.refresh(member)

        return member

    async def remove_member(
        self,
        db: AsyncSession,
        workspace_id: str,
        owner_id: str,
        member_id: str,
    ) -> None:
        """Remove a member from workspace.

        Args:
            db: Database session
            workspace_id: Workspace ID
            owner_id: User ID making the request
            member_id: WorkspaceMember ID

        Raises:
            NotFoundError: If workspace or member not found
            PermissionDeniedError: If requester not authorized

        """
        workspace = await self.get_workspace_by_id(db, workspace_id, owner_id)

        # Only owner can remove members
        if workspace.owner_id != owner_id:
            raise PermissionDeniedError("Only workspace owner can remove members")

        member = await db.get(WorkspaceMember, member_id)
        if not member or member.workspace_id != workspace_id:
            raise NotFoundError("Workspace member not found")

        # Cannot remove owner
        if member.role == WorkspaceRole.OWNER:
            raise PermissionDeniedError("Cannot remove workspace owner")

        await db.delete(member)
        await db.commit()

    async def list_workspace_members(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
    ) -> list[WorkspaceMember]:
        """List members of a workspace.

        Args:
            db: Database session
            workspace_id: Workspace ID
            user_id: User ID requesting access

        Returns:
            List of workspace members

        Raises:
            NotFoundError: If workspace not found
            PermissionDeniedError: If user doesn't have access

        """
        workspace = await self.get_workspace_by_id(db, workspace_id, user_id)

        query = (
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .join(User, WorkspaceMember.user_id == User.id)
            .where(User.deleted_at.is_(None))
            .order_by(WorkspaceMember.created_at)
        )
        result = await db.execute(query)
        members = result.scalars().all()

        return list(members)

    async def _check_workspace_access(
        self,
        db: AsyncSession,
        workspace_id: str,
        user_id: str,
    ) -> bool:
        """Check if user has access to workspace.

        Args:
            db: Database session
            workspace_id: Workspace ID
            user_id: User ID

        Returns:
            True if user has access

        """
        query = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None

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
