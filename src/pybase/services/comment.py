"""Comment service for business logic."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pybase.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
)
from pybase.models.base import Base
from pybase.models.comment import Comment
from pybase.models.record import Record
from pybase.models.table import Table
from pybase.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from pybase.schemas.comment import CommentCreate, CommentUpdate


class CommentService:
    """Service for comment operations."""

    async def create_comment(
        self,
        db: AsyncSession,
        user_id: str,
        comment_data: CommentCreate,
    ) -> Comment:
        """Create a new comment on a record.

        Args:
            db: Database session
            user_id: User ID creating comment
            comment_data: Comment creation data

        Returns:
            Created comment

        Raises:
            NotFoundError: If record not found
            PermissionDeniedError: If user doesn't have access to record

        """
        # Check if record exists
        record = await db.get(Record, comment_data.record_id)
        if not record or record.is_deleted:
            raise NotFoundError("Record not found")

        # Check if user has access to workspace
        table = await self._get_table(db, str(record.table_id))
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))
        if not member:
            raise PermissionDeniedError("You don't have access to this record")

        # Create comment
        comment = Comment(
            record_id=comment_data.record_id,
            user_id=str(user_id),
            content=comment_data.content,
            is_edited=False,
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)

        return comment

    async def get_comment_by_id(
        self,
        db: AsyncSession,
        comment_id: str,
        user_id: str,
    ) -> Comment:
        """Get a comment by ID, checking user access.

        Args:
            db: Database session
            comment_id: Comment ID
            user_id: User ID requesting access

        Returns:
            Comment

        Raises:
            NotFoundError: If comment not found
            PermissionDeniedError: If user doesn't have access

        """
        comment = await db.get(Comment, comment_id)
        if not comment or comment.is_deleted:
            raise NotFoundError("Comment not found")

        # Check if user has access to workspace via record
        record = await self._get_record(db, str(comment.record_id))
        table = await self._get_table(db, str(record.table_id))
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))
        if not member:
            raise PermissionDeniedError("You don't have access to this comment")

        return comment

    async def list_comments(
        self,
        db: AsyncSession,
        record_id: Optional[UUID],
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Comment], int]:
        """List comments accessible to user.

        Args:
            db: Database session
            record_id: Optional record ID to filter by
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (comments, total count)

        """
        offset = (page - 1) * page_size

        # Count query
        count_query = (
            select(func.count())
            .select_from(Comment)
            .join(Record)
            .join(Table)
            .join(Base)
            .join(WorkspaceMember)
        )
        if record_id:
            count_query = count_query.where(Comment.record_id == str(record_id))
        count_query = count_query.where(WorkspaceMember.user_id == str(user_id))
        count_query = count_query.where(Comment.deleted_at.is_(None))
        count_query = count_query.where(Record.deleted_at.is_(None))
        count_query = count_query.where(Table.deleted_at.is_(None))
        count_query = count_query.where(Base.deleted_at.is_(None))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query
        query = select(Comment).join(Record).join(Table).join(Base).join(WorkspaceMember)
        if record_id:
            query = query.where(Comment.record_id == str(record_id))
        query = query.where(WorkspaceMember.user_id == str(user_id))
        query = query.where(Comment.deleted_at.is_(None))
        query = query.where(Record.deleted_at.is_(None))
        query = query.where(Table.deleted_at.is_(None))
        query = query.where(Base.deleted_at.is_(None))
        query = query.order_by(Comment.created_at)
        query = query.offset(offset)
        query = query.limit(page_size)
        result = await db.execute(query)
        comments = result.scalars().all()

        return list(comments), total

    async def update_comment(
        self,
        db: AsyncSession,
        comment_id: str,
        user_id: str,
        comment_data: CommentUpdate,
    ) -> Comment:
        """Update a comment.

        Args:
            db: Database session
            comment_id: Comment ID
            user_id: User ID making request
            comment_data: Comment update data

        Returns:
            Updated comment

        Raises:
            NotFoundError: If comment not found
            PermissionDeniedError: If user doesn't have permission

        """
        comment = await self.get_comment_by_id(db, comment_id, user_id)

        # Check if user has permission to edit
        # Users can edit their own comments, or workspace admins/owners can edit any comment
        record = await self._get_record(db, str(comment.record_id))
        table = await self._get_table(db, str(record.table_id))
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))

        is_owner = str(comment.user_id) == str(user_id)
        is_admin = member and member.role in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]

        if not is_owner and not is_admin:
            raise PermissionDeniedError(
                "Only comment author or workspace admins/owners can update comments"
            )

        # Update comment content
        comment.content = comment_data.content
        comment.mark_as_edited(datetime.now(timezone.utc))

        await db.commit()
        await db.refresh(comment)

        return comment

    async def delete_comment(
        self,
        db: AsyncSession,
        comment_id: str,
        user_id: str,
    ) -> None:
        """Delete (soft delete) a comment.

        Args:
            db: Database session
            comment_id: Comment ID
            user_id: User ID making request

        Raises:
            NotFoundError: If comment not found
            PermissionDeniedError: If user doesn't have permission

        """
        comment = await self.get_comment_by_id(db, comment_id, user_id)

        # Check if user has permission to delete
        # Users can delete their own comments, or workspace admins/owners can delete any comment
        record = await self._get_record(db, str(comment.record_id))
        table = await self._get_table(db, str(record.table_id))
        base = await self._get_base(db, str(table.base_id))
        workspace = await self._get_workspace(db, str(base.workspace_id))
        member = await self._get_workspace_member(db, str(workspace.id), str(user_id))

        is_owner = str(comment.user_id) == str(user_id)
        is_admin = member and member.role in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]

        if not is_owner and not is_admin:
            raise PermissionDeniedError(
                "Only comment author or workspace admins/owners can delete comments"
            )

        comment.soft_delete()
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

    async def _get_record(
        self,
        db: AsyncSession,
        record_id: str,
    ) -> Record:
        """Get record by ID.

        Args:
            db: Database session
            record_id: Record ID

        Returns:
            Record

        Raises:
            NotFoundError: If record not found

        """
        record = await db.get(Record, record_id)
        if not record or record.is_deleted:
            raise NotFoundError("Record not found")
        return record
